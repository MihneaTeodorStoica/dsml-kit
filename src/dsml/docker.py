from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import shutil
import subprocess

from dsml import paths


@dataclass(frozen=True)
class DockerRunOptions:
    image: str
    container_name: str
    project_root: Path
    mount_path: Path
    home_volume: str
    port: int
    bind_address: str = "127.0.0.1"
    root_dir: str = "/home/jovyan/work"
    base_url: str = "/"
    token: str = ""
    app_log_level: str = "WARN"
    server_log_level: str = "WARN"
    extra_args: list[str] = field(default_factory=list)
    host_uid: int = 1000
    host_gid: int = 1000
    gpu: bool = False
    detach: bool = True
    restart_policy: str = "unless-stopped"
    run_signature: str = ""


def build_run_args(options: DockerRunOptions) -> list[str]:
    args = ["docker", "run"]
    if options.detach:
        args.append("-d")
    else:
        args.extend(["-it"])

    args.extend(
        [
            "--name",
            options.container_name,
            "--label",
            f"{paths.PROJECT_LABEL}={paths.project_name(options.project_root)}",
            "--label",
            f"{paths.CONFIG_LABEL}={options.project_root / paths.CONFIG_FILE}",
            "--restart",
            options.restart_policy,
            "--user",
            "root",
            "--security-opt",
            "no-new-privileges:true",
            "--workdir",
            options.root_dir,
            "-p",
            f"{options.bind_address}:{options.port}:8888",
            "-v",
            f"{options.mount_path}:{options.root_dir}",
            "-v",
            f"{options.home_volume}:/home/jovyan",
        ]
    )
    if options.run_signature:
        args.extend(["--label", f"{paths.RUN_SIGNATURE_LABEL}={options.run_signature}"])

    if options.gpu:
        args.extend(
            [
                "--gpus",
                "all",
                "-e",
                "NVIDIA_VISIBLE_DEVICES=all",
                "-e",
                "NVIDIA_DRIVER_CAPABILITIES=all",
            ]
        )

    env = {
        "JUPYTER_APP_LOG_LEVEL": options.app_log_level,
        "JUPYTER_SERVER_LOG_LEVEL": options.server_log_level,
        "JUPYTER_ROOT_DIR": options.root_dir,
        "JUPYTER_BASE_URL": options.base_url,
        "JUPYTER_EXTRA_ARGS": " ".join(options.extra_args),
        "JUPYTER_TOKEN": options.token,
        "NB_UID": str(options.host_uid),
        "NB_GID": str(options.host_gid),
        "CHOWN_HOME": "yes",
        "CHOWN_HOME_OPTS": "-R",
        "CHOWN_EXTRA": options.root_dir,
        "CHOWN_EXTRA_OPTS": "-R",
        "UV_SYSTEM_PYTHON": "1",
    }
    for key, value in env.items():
        args.extend(["-e", f"{key}={value}"])

    args.append(options.image)
    return args


def run(args: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=check,
        text=True,
        capture_output=capture,
    )


def docker_cli_exists() -> bool:
    return shutil.which("docker") is not None


def daemon_reachable() -> bool:
    if not docker_cli_exists():
        return False
    result = run(["docker", "info"], check=False, capture=True)
    return result.returncode == 0


def compose_cli_exists() -> bool:
    if not docker_cli_exists():
        return False
    result = run(["docker", "compose", "version"], check=False, capture=True)
    return result.returncode == 0


def nvidia_smi_exists() -> bool:
    return shutil.which("nvidia-smi") is not None


def image_exists(image: str) -> bool:
    result = run(["docker", "image", "inspect", image], check=False, capture=True)
    return result.returncode == 0


def image_id(image: str) -> str:
    result = run(["docker", "image", "inspect", "--format={{.Id}}", image], check=False, capture=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def container_exists(container_name: str) -> bool:
    result = run(["docker", "container", "inspect", container_name], check=False, capture=True)
    return result.returncode == 0


def container_running(container_name: str) -> bool:
    result = run(
        ["docker", "inspect", "--format={{.State.Running}}", container_name],
        check=False,
        capture=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def start_container(options: DockerRunOptions) -> subprocess.CompletedProcess[str]:
    return run(build_run_args(options), check=True, capture=options.detach)


def start_existing_container(container_name: str, *, attach: bool = False) -> subprocess.CompletedProcess[str]:
    args = ["docker", "start"]
    if attach:
        args.extend(["-a", "-i"])
    args.append(container_name)
    return run(args, check=True, capture=not attach)


def stop_container(container_name: str) -> subprocess.CompletedProcess[str]:
    return run(["docker", "stop", container_name], check=False, capture=True)


def remove_container(container_name: str, *, force: bool = False) -> subprocess.CompletedProcess[str]:
    args = ["docker", "rm"]
    if force:
        args.append("-f")
    args.append(container_name)
    return run(args, check=False, capture=True)


def container_label(container_name: str, label: str) -> str:
    result = run(
        [
            "docker",
            "inspect",
            f"--format={{{{ with index .Config.Labels {json.dumps(label)} }}}}{{{{ . }}}}{{{{ end }}}}",
            container_name,
        ],
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def container_env_value(container_name: str, key: str) -> str | None:
    result = run(
        ["docker", "inspect", "--format={{range .Config.Env}}{{println .}}{{end}}", container_name],
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        return None
    prefix = f"{key}="
    for line in result.stdout.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return None


def exec_in_container(
    container_name: str,
    command: list[str],
    *,
    user: str | None = None,
    interactive: bool = False,
    capture: bool = False,
    check: bool | None = None,
) -> subprocess.CompletedProcess[str]:
    args = ["docker", "exec"]
    if interactive:
        args.append("-it")
    if user:
        args.extend(["--user", user])
    args.extend([container_name, *command])
    return run(args, check=(not capture if check is None else check), capture=capture)


def logs(container_name: str, *, follow: bool = False, tail: int | None = None) -> subprocess.CompletedProcess[str]:
    args = ["docker", "logs"]
    if follow:
        args.append("-f")
    if tail is not None:
        args.extend(["--tail", str(tail)])
    args.append(container_name)
    return run(args, check=False)


def pull_image(image: str) -> subprocess.CompletedProcess[str]:
    return run(["docker", "pull", image])


def remove_image(image: str) -> subprocess.CompletedProcess[str]:
    return run(["docker", "image", "rm", image], check=False, capture=True)


def list_project_containers(project_root: Path) -> list[str]:
    label = f"{paths.PROJECT_LABEL}={paths.project_name(project_root)}"
    result = run(
        ["docker", "ps", "-a", "--filter", f"label={label}", "--format", "{{.Names}}"],
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def remove_volume(volume_name: str) -> subprocess.CompletedProcess[str]:
    return run(["docker", "volume", "rm", volume_name], check=False, capture=True)
