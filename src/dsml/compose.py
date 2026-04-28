from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

import yaml

from dsml import docker, paths


SERVICE_NAME = "app"
COMPOSE_PROJECT_LABEL = "com.docker.compose.project"


def service_name() -> str:
    return SERVICE_NAME


def compose_path(project_root: Path) -> Path:
    return paths.compose_path(project_root)


def compose_project_name(project_root: Path) -> str:
    return paths.project_name(project_root)


def build_compose_model(options: docker.DockerRunOptions) -> dict[str, Any]:
    labels = {
        paths.PROJECT_LABEL: paths.project_name(options.project_root),
        paths.CONFIG_LABEL: str(options.project_root / paths.CONFIG_FILE),
    }
    if options.run_signature:
        labels[paths.RUN_SIGNATURE_LABEL] = options.run_signature

    environment = {
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

    service: dict[str, Any] = {
        "image": options.image,
        "container_name": options.container_name,
        "labels": labels,
        "restart": options.restart_policy,
        "user": "root",
        "security_opt": ["no-new-privileges:true"],
        "working_dir": options.root_dir,
        "ports": [f"{options.bind_address}:{options.port}:8888"],
        "volumes": [
            {
                "type": "bind",
                "source": str(options.mount_path),
                "target": options.root_dir,
            },
            {
                "type": "volume",
                "source": options.home_volume,
                "target": "/home/jovyan",
            },
        ],
        "environment": environment,
    }

    if options.gpu:
        environment["NVIDIA_VISIBLE_DEVICES"] = "all"
        environment["NVIDIA_DRIVER_CAPABILITIES"] = "all"
        service["deploy"] = {
            "resources": {
                "reservations": {
                    "devices": [
                        {
                            "driver": "nvidia",
                            "count": "all",
                            "capabilities": ["gpu"],
                        }
                    ]
                }
            }
        }

    return {
        "services": {
            SERVICE_NAME: service,
        },
        "volumes": {
            options.home_volume: {
                "name": options.home_volume,
            },
        },
    }


def render_compose_yaml(model: dict[str, Any]) -> str:
    return yaml.safe_dump(model, sort_keys=False, default_flow_style=False)


def write_compose_file(project_root: Path, options: docker.DockerRunOptions) -> Path:
    path = compose_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_compose_yaml(build_compose_model(options)))
    return path


def compose_base_args(project_root: Path, compose_file: Path) -> list[str]:
    return [
        "docker",
        "compose",
        "-p",
        compose_project_name(project_root),
        "-f",
        str(compose_file),
    ]


def compose_up_args(project_root: Path, compose_file: Path, *, detach: bool) -> list[str]:
    args = [*compose_base_args(project_root, compose_file), "up"]
    if detach:
        args.append("-d")
    return args


def compose_stop_args(project_root: Path, compose_file: Path) -> list[str]:
    return [*compose_base_args(project_root, compose_file), "stop"]


def compose_restart_args(project_root: Path, compose_file: Path) -> list[str]:
    return [*compose_base_args(project_root, compose_file), "restart"]


def compose_down_args(project_root: Path, compose_file: Path, *, volumes: bool = False) -> list[str]:
    args = [*compose_base_args(project_root, compose_file), "down"]
    if volumes:
        args.append("-v")
    return args


def compose_logs_args(
    project_root: Path,
    compose_file: Path,
    *,
    follow: bool = False,
    tail: int | None = None,
) -> list[str]:
    args = [*compose_base_args(project_root, compose_file), "logs"]
    if follow:
        args.append("--follow")
    if tail is not None:
        args.extend(["--tail", str(tail)])
    args.append(SERVICE_NAME)
    return args


def compose_exec_args(
    project_root: Path,
    compose_file: Path,
    command: list[str],
    *,
    user: str | None = None,
    interactive: bool = False,
) -> list[str]:
    args = [*compose_base_args(project_root, compose_file), "exec"]
    if not interactive:
        args.append("-T")
    if user:
        args.extend(["--user", user])
    args.extend([SERVICE_NAME, *command])
    return args


def compose_ps_args(project_root: Path, compose_file: Path, *, status: str | None = None) -> list[str]:
    args = [*compose_base_args(project_root, compose_file), "ps", "--services"]
    if status:
        args.extend(["--status", status])
    return args


def up(project_root: Path, compose_file: Path, *, detach: bool = True) -> subprocess.CompletedProcess[str]:
    return docker.run(compose_up_args(project_root, compose_file, detach=detach), check=True, capture=False)


def stop(project_root: Path, compose_file: Path) -> subprocess.CompletedProcess[str]:
    return docker.run(compose_stop_args(project_root, compose_file), check=False, capture=True)


def restart(project_root: Path, compose_file: Path) -> subprocess.CompletedProcess[str]:
    return docker.run(compose_restart_args(project_root, compose_file), check=False, capture=True)


def down(project_root: Path, compose_file: Path, *, volumes: bool = False) -> subprocess.CompletedProcess[str]:
    return docker.run(compose_down_args(project_root, compose_file, volumes=volumes), check=False, capture=True)


def logs(
    project_root: Path,
    compose_file: Path,
    *,
    follow: bool = False,
    tail: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return docker.run(compose_logs_args(project_root, compose_file, follow=follow, tail=tail), check=False)


def exec(
    project_root: Path,
    compose_file: Path,
    command: list[str],
    *,
    user: str | None = None,
    interactive: bool = False,
    capture: bool = False,
    check: bool | None = None,
) -> subprocess.CompletedProcess[str]:
    return docker.run(
        compose_exec_args(project_root, compose_file, command, user=user, interactive=interactive),
        check=(not capture if check is None else check),
        capture=capture,
    )


def service_running(project_root: Path, compose_file: Path) -> bool:
    result = docker.run(compose_ps_args(project_root, compose_file, status="running"), check=False, capture=True)
    if result.returncode != 0:
        return False
    return SERVICE_NAME in {line.strip() for line in result.stdout.splitlines()}
