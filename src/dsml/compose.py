from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

import yaml

from dsml import docker, paths
from dsml.options import RuntimeOptions, WatchRule


SERVICE_NAME = "app"
COMPOSE_PROJECT_LABEL = "com.docker.compose.project"


def service_name() -> str:
    return SERVICE_NAME


def compose_path(project_root: Path) -> Path:
    return paths.compose_path(project_root)


def compose_project_name(project_root: Path) -> str:
    return paths.project_name(project_root)


def build_compose_model(options: RuntimeOptions) -> dict[str, Any]:
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

    if options.build_context is not None:
        build: dict[str, Any] = {
            "context": _project_path(options.project_root, options.build_context),
        }
        if options.build_dockerfile is not None:
            build["dockerfile"] = _context_path(options.build_context, options.build_dockerfile)
        if options.build_target:
            build["target"] = options.build_target
        if options.build_args:
            build["args"] = dict(options.build_args)
        service["build"] = build

    if options.watch:
        service["develop"] = {"watch": [_watch_rule(options.project_root, rule) for rule in options.watch]}

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


def write_compose_file(project_root: Path, options: RuntimeOptions) -> Path:
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
        "--project-directory",
        str(project_root),
    ]


def compose_up_args(
    project_root: Path,
    compose_file: Path,
    *,
    detach: bool,
    force_recreate: bool = False,
) -> list[str]:
    args = [*compose_base_args(project_root, compose_file), "up"]
    if detach:
        args.append("-d")
    if force_recreate:
        args.append("--force-recreate")
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
    since: str | None = None,
    timestamps: bool = False,
) -> list[str]:
    args = [*compose_base_args(project_root, compose_file), "logs"]
    if follow:
        args.append("--follow")
    if tail is not None:
        args.extend(["--tail", str(tail)])
    if since:
        args.extend(["--since", since])
    if timestamps:
        args.append("--timestamps")
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


def compose_ps_args(
    project_root: Path,
    compose_file: Path,
    *,
    status: str | None = None,
    services: bool = False,
) -> list[str]:
    args = [*compose_base_args(project_root, compose_file), "ps"]
    if services:
        args.append("--services")
    if status:
        args.extend(["--status", status])
    return args


def compose_config_args(project_root: Path, compose_file: Path) -> list[str]:
    return [*compose_base_args(project_root, compose_file), "config"]


def compose_watch_args(
    project_root: Path,
    compose_file: Path,
    *,
    no_up: bool = False,
    prune: bool = True,
    quiet: bool = False,
) -> list[str]:
    args = [*compose_base_args(project_root, compose_file), "watch"]
    if no_up:
        args.append("--no-up")
    if not prune:
        args.append("--prune=false")
    if quiet:
        args.append("--quiet")
    args.append(SERVICE_NAME)
    return args


def up(
    project_root: Path,
    compose_file: Path,
    *,
    detach: bool = True,
    force_recreate: bool = False,
) -> subprocess.CompletedProcess[str]:
    return docker.run(
        compose_up_args(project_root, compose_file, detach=detach, force_recreate=force_recreate),
        check=True,
        capture=False,
    )


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
    since: str | None = None,
    timestamps: bool = False,
) -> subprocess.CompletedProcess[str]:
    return docker.run(
        compose_logs_args(
            project_root,
            compose_file,
            follow=follow,
            tail=tail,
            since=since,
            timestamps=timestamps,
        ),
        check=False,
    )


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
    result = docker.run(
        compose_ps_args(project_root, compose_file, status="running", services=True),
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        return False
    return SERVICE_NAME in {line.strip() for line in result.stdout.splitlines()}


def ps(project_root: Path, compose_file: Path) -> subprocess.CompletedProcess[str]:
    return docker.run(compose_ps_args(project_root, compose_file), check=False)


def config(project_root: Path, compose_file: Path) -> subprocess.CompletedProcess[str]:
    return docker.run(compose_config_args(project_root, compose_file), check=False)


def watch(
    project_root: Path,
    compose_file: Path,
    *,
    no_up: bool = False,
    prune: bool = True,
    quiet: bool = False,
) -> subprocess.CompletedProcess[str]:
    return docker.run(
        compose_watch_args(project_root, compose_file, no_up=no_up, prune=prune, quiet=quiet),
        check=True,
        capture=False,
    )


def _project_path(project_root: Path, path: Path) -> str:
    return _relative_or_absolute(project_root, path)


def _context_path(context: Path, path: Path) -> str:
    return _relative_or_absolute(context, path)


def _watch_rule(project_root: Path, rule: WatchRule) -> dict[str, str]:
    return {
        "action": rule.action,
        "path": _project_path(project_root, rule.path),
    }


def _relative_or_absolute(base: Path, path: Path) -> str:
    resolved_base = base.resolve()
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(resolved_base).as_posix() or "."
    except ValueError:
        return str(resolved_path)
