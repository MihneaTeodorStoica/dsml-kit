from __future__ import annotations

from pathlib import Path
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
import webbrowser

from rich.console import Console

from dsml import config, docker, images, paths, profiles


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


def up(*, attach: bool = False, build: bool = False, pull: bool = False, dev: bool = False) -> None:
    project_root, _, data = load_workspace()
    options = run_options(project_root, data, attach=attach, dev=dev)

    if build or dev:
        images.build_image(tag=options.image, dev=dev)
    if pull:
        images.pull_image(options.image)
    if not docker.image_exists(options.image):
        if options.image == images.DEFAULT_DEV_IMAGE:
            raise RuntimeError(
                f"Image {options.image} is not present locally. "
                "Run 'dsml image build --dev' or start with 'dsml up --dev --build'."
            )
        raise RuntimeError(
            f"Image {options.image} is not present locally. "
            "Run 'dsml image pull' or start with 'dsml up --pull'."
        )

    prepare_workspace(options.mount_path)

    if docker.container_running(options.container_name):
        console.print(f"[green]Running[/green] {options.container_name}")
        console.print(workspace_url(options))
        return

    if docker.container_exists(options.container_name):
        docker.remove_container(options.container_name)

    docker.start_container(options)
    if attach:
        return

    if wait_for_jupyter(options):
        console.print(f"[green]Started[/green] {options.container_name}")
        console.print(workspace_url(options))
    else:
        console.print(f"[yellow]Started[/yellow] {options.container_name}, but Jupyter did not answer yet.")
        console.print(workspace_url(options))


def down() -> None:
    project_root, _, data = load_workspace()
    name = run_options(project_root, data).container_name
    docker.remove_container(name, force=True)
    console.print(f"Removed {name}")


def stop() -> None:
    project_root, _, data = load_workspace()
    name = run_options(project_root, data).container_name
    docker.stop_container(name)
    console.print(f"Stopped {name}")


def restart(*, attach: bool = False) -> None:
    stop()
    up(attach=attach)


def logs(*, follow: bool = False, tail: int | None = None) -> None:
    project_root, _, data = load_workspace()
    name = run_options(project_root, data).container_name
    docker.logs(name, follow=follow, tail=tail)


def shell(command: str | None = None) -> None:
    project_root, _, data = load_workspace()
    name = run_options(project_root, data).container_name
    shell_command = [command] if command else ["/bin/bash"]
    result = docker.exec_in_container(name, shell_command, user="jovyan", interactive=True, check=False)
    if result.returncode != 0 and not command:
        docker.exec_in_container(name, ["/bin/sh"], user="jovyan", interactive=True)


def open_workspace() -> None:
    project_root, _, data = load_workspace()
    options = run_options(project_root, data)
    webbrowser.open(workspace_url(options))
    console.print(workspace_url(options))


def add(packages: list[str]) -> None:
    if not packages:
        raise RuntimeError("Provide at least one package to add.")
    project_root, config_path, data = load_workspace()
    updated = config.add_packages(config_path, packages)
    options = run_options(project_root, updated)
    console.print(f"Updated {config_path.name}")
    if docker.container_running(options.container_name):
        docker.exec_in_container(
            options.container_name,
            ["uv", "pip", "install", "--system", *packages],
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
    if not docker.container_running(options.container_name):
        raise RuntimeError("Container is not running. Run 'dsml up' first.")
    docker.exec_in_container(
        options.container_name,
        ["uv", "pip", "install", "--system", *packages],
        user="root",
    )


def clean(*, image: bool = False, volumes: bool = False) -> None:
    project_root, _, data = load_workspace()
    options = run_options(project_root, data)
    for container in docker.list_project_containers(project_root):
        docker.remove_container(container)
        console.print(f"Removed stopped container {container}")
    if image:
        docker.remove_image(options.image)
        console.print(f"Removed image {options.image}")
    if volumes:
        docker.remove_volume(options.home_volume)
        console.print(f"Removed volume {options.home_volume}")


def nuke(*, confirmation: str) -> None:
    if confirmation != "DELETE":
        console.print("Aborted.")
        return
    project_root, _, data = load_workspace()
    options = run_options(project_root, data)
    docker.remove_container(options.container_name, force=True)
    docker.remove_volume(options.home_volume)
    console.print(f"Deleted container and home volume for {project_root}")


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
