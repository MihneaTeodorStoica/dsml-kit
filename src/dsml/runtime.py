from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
import webbrowser

from rich.console import Console

from dsml import compose, config, docker, images, paths, profiles


console = Console()


class RuntimeError(RuntimeError):
    pass


def init_project(
    *,
    project_root: Path,
    profile_name: str,
    port: int,
    gpu: bool | str,
    image: str | None,
    force: bool,
) -> Path:
    profile = profiles.resolve_profile(profile_name)
    data = config.create_project_config(
        profile=profile.name,
        profile_image=profile.image,
        port=port,
        gpu=gpu,
        image=image,
    )
    path = paths.config_path(project_root)
    config.write_config(path, data, overwrite=force, documented=True)
    return path


def load_workspace(start: Path | None = None) -> tuple[Path, Path, dict]:
    config_path = paths.locate_config(start)
    if config_path is None:
        raise RuntimeError("No dsml.toml found. Run 'dsml init' first.")
    project_root = config_path.parent
    return project_root, config_path, config.read_config(config_path)


def run_options(
    project_root: Path,
    data: dict,
    *,
    attach: bool = False,
    dev: bool = False,
) -> docker.DockerRunOptions:
    workspace = data["workspace"]
    jupyter = data["jupyter"]
    profile = profiles.resolve_profile(workspace["profile"])
    image = images.DEFAULT_DEV_IMAGE if dev else workspace.get("image") or profile.image
    container_name = _auto_value(
        workspace.get("container_name"),
        paths.default_container_name(project_root),
    )
    home_volume = _auto_value(
        workspace.get("home_volume"),
        paths.default_home_volume(project_root),
    )
    return docker.DockerRunOptions(
        image=image,
        container_name=container_name,
        project_root=project_root,
        mount_path=paths.resolve_mount_path(project_root, workspace["mount"]),
        home_volume=home_volume,
        port=workspace["port"],
        bind_address=workspace["bind_address"],
        root_dir=jupyter["root_dir"],
        base_url=jupyter["base_url"],
        token=config.resolve_token(data),
        app_log_level=jupyter["app_log_level"],
        server_log_level=jupyter["server_log_level"],
        extra_args=jupyter["extra_args"],
        host_uid=os.getuid(),
        host_gid=os.getgid(),
        gpu=resolve_gpu(workspace["gpu"], profile.gpu),
        detach=not attach,
    )


def ensure_compose_available() -> None:
    if docker.compose_cli_exists():
        return
    raise RuntimeError("Docker Compose v2 is required. Install Docker with the `docker compose` plugin.")


def write_compose_for_workspace(
    project_root: Path,
    data: dict,
    *,
    attach: bool = False,
    dev: bool = False,
) -> tuple[docker.DockerRunOptions, Path]:
    options = run_options(project_root, data, attach=attach, dev=dev)
    return options, compose.write_compose_file(project_root, options)


def options_with_matching_container_token(
    options: docker.DockerRunOptions,
    token_policy: object,
) -> docker.DockerRunOptions:
    if str(token_policy or "auto").strip() != "auto":
        return options
    if not docker.container_exists(options.container_name):
        return options
    current_signature = docker.container_label(options.container_name, paths.RUN_SIGNATURE_LABEL)
    if current_signature != options.run_signature:
        return options
    return options_with_container_token(options)


def remove_legacy_container_for_compose(options: docker.DockerRunOptions) -> None:
    if not docker.container_exists(options.container_name):
        return

    project_name = paths.project_name(options.project_root)
    if docker.container_label(options.container_name, compose.COMPOSE_PROJECT_LABEL) == project_name:
        return
    if docker.container_label(options.container_name, paths.PROJECT_LABEL) != project_name:
        return

    console.print(f"Recreating {options.container_name} under Docker Compose.")
    result = docker.remove_container(options.container_name, force=True)
    ensure_success(result, f"remove legacy container {options.container_name}")


def up(*, attach: bool = False, build: bool = False, pull: bool = False, dev: bool = False) -> None:
    project_root, _, data = load_workspace()
    ensure_compose_available()
    options = run_options(project_root, data, attach=attach, dev=dev)

    prepare_image(
        options.image,
        policy=data["workspace"].get("image_policy", "auto"),
        build=build,
        pull=pull,
        dev=dev,
    )
    options = replace(
        options,
        run_signature=container_signature(
            options,
            image_id=docker.image_id(options.image),
            token_policy=data["workspace"].get("jupyter_token"),
        ),
    )
    options = options_with_matching_container_token(options, data["workspace"].get("jupyter_token"))

    prepare_workspace(options.mount_path)
    remove_legacy_container_for_compose(options)
    compose_file = compose.write_compose_file(project_root, options)
    compose.up(project_root, compose_file, detach=options.detach)
    if attach:
        return

    if wait_for_jupyter(options):
        console.print(f"[green]Started[/green] {options.container_name}")
        console.print(workspace_url(options))
    else:
        console.print(f"[yellow]Started[/yellow] {options.container_name}, but Jupyter did not answer yet.")
        console.print(workspace_url(options))


def down() -> None:
    stop()


def stop() -> None:
    project_root, _, data = load_workspace()
    ensure_compose_available()
    options, compose_file = write_compose_for_workspace(project_root, data)
    result = compose.stop(project_root, compose_file)
    ensure_success(result, f"stop Compose project {compose.compose_project_name(project_root)}")
    console.print(f"Stopped {options.container_name}")


def restart(*, attach: bool = False) -> None:
    stop()
    up(attach=attach)


def logs(*, follow: bool = False, tail: int | None = None) -> None:
    project_root, _, data = load_workspace()
    ensure_compose_available()
    _, compose_file = write_compose_for_workspace(project_root, data)
    compose.logs(project_root, compose_file, follow=follow, tail=tail)


def shell(command: str | None = None) -> None:
    project_root, _, data = load_workspace()
    ensure_compose_available()
    _, compose_file = write_compose_for_workspace(project_root, data)
    shell_command = [command] if command else ["/bin/bash"]
    result = compose.exec(project_root, compose_file, shell_command, user="jovyan", interactive=True, check=False)
    if result.returncode != 0 and not command:
        compose.exec(project_root, compose_file, ["/bin/sh"], user="jovyan", interactive=True)


def open_workspace() -> None:
    project_root, _, data = load_workspace()
    options = run_options(project_root, data)
    webbrowser.open(workspace_url(options))
    console.print(workspace_url(options))


def add(packages: list[str], requirement_files: list[Path] | None = None) -> None:
    project_root, config_path, data = load_workspace()
    requirement_specs = config.read_requirement_specs(requirement_files or [])
    requested = _dedupe([*packages, *requirement_specs])
    if not requested:
        raise RuntimeError("Provide packages or at least one requirements file with package specifiers.")
    updated = config.add_packages(config_path, requested)
    ensure_compose_available()
    _, compose_file = write_compose_for_workspace(project_root, updated)
    console.print(f"Updated {config_path.name}")
    if compose.service_running(project_root, compose_file):
        compose.exec(
            project_root,
            compose_file,
            ["uv", "pip", "install", "--system", *requested],
            user="root",
        )
    else:
        console.print("Container is not running. Run 'dsml up' or 'dsml sync' to install packages.")


def sync() -> None:
    project_root, _, data = load_workspace()
    options = run_options(project_root, data)
    packages = data["packages"]["extra"]
    if not packages:
        console.print("No extra packages configured.")
        return
    ensure_compose_available()
    compose_file = compose.write_compose_file(project_root, options)
    if not compose.service_running(project_root, compose_file):
        raise RuntimeError("Container is not running. Run 'dsml up' first.")
    compose.exec(
        project_root,
        compose_file,
        ["uv", "pip", "install", "--system", *packages],
        user="root",
    )


def clean(*, image: bool = False, volumes: bool = False) -> None:
    project_root, _, data = load_workspace()
    ensure_compose_available()
    options, compose_file = write_compose_for_workspace(project_root, data)
    result = compose.down(project_root, compose_file, volumes=volumes)
    ensure_success(result, f"remove Compose project {compose.compose_project_name(project_root)}")
    console.print(f"Removed Compose project {compose.compose_project_name(project_root)}")
    if image:
        docker.remove_image(options.image)
        console.print(f"Removed image {options.image}")
    if volumes:
        console.print(f"Removed volume {options.home_volume}")


def nuke(*, confirmation: str) -> None:
    if confirmation != "DELETE":
        console.print("Aborted.")
        return
    project_root, _, data = load_workspace()
    ensure_compose_available()
    options, compose_file = write_compose_for_workspace(project_root, data)
    result = compose.down(project_root, compose_file, volumes=True)
    ensure_success(result, f"remove Compose project {compose.compose_project_name(project_root)}")
    docker.remove_volume(options.home_volume)
    console.print(f"Deleted Compose project and home volume for {project_root}")


def prepare_image(
    image: str,
    *,
    policy: str = "auto",
    build: bool = False,
    pull: bool = False,
    dev: bool = False,
) -> None:
    policy = str(policy or "auto").strip().lower()
    if build or dev:
        images.build_image(tag=image, dev=dev)
        if pull:
            images.pull_image(image)
        ensure_local_image(image)
        return

    if pull:
        images.pull_image(image)
        ensure_local_image(image)
        return

    if policy == "build" or (policy == "auto" and should_build_image(image)):
        images.build_image(tag=image)
        ensure_local_image(image)
        return

    if policy == "pull":
        images.pull_image(image)
        ensure_local_image(image)
        return

    ensure_image_available(image, allow_pull=policy == "auto")


def ensure_image_available(image: str, *, allow_pull: bool = True) -> None:
    if docker.image_exists(image):
        return
    if not allow_pull:
        raise RuntimeError(
            f"Image {image} is not present locally and [workspace].image_policy is set to never."
        )
    if should_build_image(image):
        raise RuntimeError(
            f"Image {image} is not present locally. "
            "Set [workspace].image_policy to 'build' or run 'dsml image build --dev'."
        )
    console.print(f"Pulling {image} because it is not present locally.")
    try:
        images.pull_image(image)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Image {image} is not present locally and automatic pull failed.") from exc
    if not docker.image_exists(image):
        raise RuntimeError(f"Image {image} is still not present after pull.")


def ensure_local_image(image: str) -> None:
    if docker.image_exists(image):
        return
    raise RuntimeError(f"Image {image} is not present locally.")


def should_build_image(image: str) -> bool:
    return image == images.DEFAULT_DEV_IMAGE


def container_signature(
    options: docker.DockerRunOptions,
    *,
    image_id: str,
    token_policy: object,
) -> str:
    raw_token = str(token_policy or "auto").strip()
    token = "auto" if raw_token == "auto" else options.token
    payload = {
        "app_log_level": options.app_log_level,
        "base_url": options.base_url,
        "bind_address": options.bind_address,
        "container_name": options.container_name,
        "extra_args": options.extra_args,
        "gpu": options.gpu,
        "home_volume": options.home_volume,
        "host_gid": options.host_gid,
        "host_uid": options.host_uid,
        "image": options.image,
        "image_id": image_id,
        "mount_path": str(options.mount_path),
        "port": options.port,
        "project_root": str(options.project_root),
        "restart_policy": options.restart_policy,
        "root_dir": options.root_dir,
        "server_log_level": options.server_log_level,
        "token": token,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def options_with_container_token(options: docker.DockerRunOptions) -> docker.DockerRunOptions:
    token = docker.container_env_value(options.container_name, "JUPYTER_TOKEN")
    if token is None:
        return options
    return replace(options, token=token)


def project_containers(project_root: Path, current_container: str) -> list[str]:
    containers = docker.list_project_containers(project_root)
    if current_container not in containers and docker.container_exists(current_container):
        containers.append(current_container)
    return list(dict.fromkeys(containers))


def stop_container(container_name: str) -> None:
    if not docker.container_exists(container_name):
        console.print(f"No container found for {container_name}.")
        return
    if not docker.container_running(container_name):
        console.print(f"Already stopped {container_name}")
        return
    result = docker.stop_container(container_name)
    ensure_success(result, f"stop container {container_name}")
    console.print(f"Stopped {container_name}")


def ensure_success(result: subprocess.CompletedProcess[str], action: str) -> None:
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout).strip()
    message = f"Failed to {action}."
    if detail:
        message = f"{message} {detail}"
    raise RuntimeError(message)


def resolve_gpu(config_value: bool | str, profile_value: bool | str) -> bool:
    requested = profile_value if config_value == "auto" else config_value
    if requested == "auto":
        return docker.nvidia_smi_exists()
    return bool(requested)


def prepare_workspace(mount_path: Path) -> None:
    mount_path.mkdir(parents=True, exist_ok=True)
    if os.access(mount_path, os.W_OK):
        return
    raise RuntimeError(f"Workspace mount is not writable: {mount_path}")


def wait_for_jupyter(options: docker.DockerRunOptions, *, attempts: int = 30, sleep_seconds: float = 1.0) -> bool:
    url = workspace_url(options, api=True)
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if 200 <= response.status < 300:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(sleep_seconds)
    return False


def workspace_url(options: docker.DockerRunOptions, *, api: bool = False) -> str:
    base = options.base_url if options.base_url.startswith("/") else f"/{options.base_url}"
    path = f"{base.rstrip('/')}/api/status" if api else base
    token = f"?token={options.token}" if options.token else ""
    return f"http://{options.bind_address}:{options.port}{path}{token}"


def port_is_free(bind_address: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((bind_address, port))
        except OSError:
            return False
    return True


def dev_test() -> subprocess.CompletedProcess[str]:
    return subprocess.run(["uv", "run", "pytest"], check=True)


def dev_validate() -> None:
    images.build_image(tag=images.VALIDATE_IMAGE)
    env = os.environ.copy()
    env.update(images.validation_env())
    subprocess.run(["uv", "run", "pytest", "tests/integration"], check=True, env=env)


def _auto_value(value: object, default: str) -> str:
    text = str(value or "auto").strip()
    return default if text == "auto" else text


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
