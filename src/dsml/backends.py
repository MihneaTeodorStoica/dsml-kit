from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from dsml import compose, docker
from dsml.options import RuntimeOptions

SUPPORTED_BACKENDS = {"compose"}


class BackendError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkspaceContext:
    project_root: Path
    config_path: Path
    data: dict
    options: RuntimeOptions
    compose_file: Path


class RuntimeBackend(Protocol):
    @property
    def name(self) -> str: ...

    def ensure_available(self) -> None: ...

    def write_config(self, context: WorkspaceContext) -> Path: ...

    def up(
        self,
        context: WorkspaceContext,
        *,
        detach: bool,
        force_recreate: bool = False,
    ) -> subprocess.CompletedProcess[str]: ...

    def stop(self, context: WorkspaceContext) -> subprocess.CompletedProcess[str]: ...

    def restart(
        self, context: WorkspaceContext
    ) -> subprocess.CompletedProcess[str]: ...

    def down(
        self, context: WorkspaceContext, *, volumes: bool = False
    ) -> subprocess.CompletedProcess[str]: ...

    def logs(
        self,
        context: WorkspaceContext,
        *,
        follow: bool = False,
        tail: int | None = None,
        since: str | None = None,
        timestamps: bool = False,
    ) -> subprocess.CompletedProcess[str]: ...

    def exec(
        self,
        context: WorkspaceContext,
        command: list[str],
        *,
        user: str | None = None,
        interactive: bool = False,
        capture: bool = False,
        check: bool | None = None,
    ) -> subprocess.CompletedProcess[str]: ...

    def service_running(self, context: WorkspaceContext) -> bool: ...

    def ps(self, context: WorkspaceContext) -> subprocess.CompletedProcess[str]: ...

    def config(self, context: WorkspaceContext) -> subprocess.CompletedProcess[str]: ...

    def watch(
        self,
        context: WorkspaceContext,
        *,
        no_up: bool = False,
        prune: bool = True,
        quiet: bool = False,
    ) -> subprocess.CompletedProcess[str]: ...


@dataclass(frozen=True)
class ComposeBackend:
    name: str = "compose"

    def ensure_available(self) -> None:
        if docker.compose_cli_exists():
            return
        raise BackendError(
            "Docker Compose v2 is required. Install Docker with the `docker compose` plugin."
        )

    def write_config(self, context: WorkspaceContext) -> Path:
        return compose.write_compose_file(context.project_root, context.options)

    def up(
        self,
        context: WorkspaceContext,
        *,
        detach: bool,
        force_recreate: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        kwargs = {"detach": detach}
        if force_recreate:
            kwargs["force_recreate"] = True
        return compose.up(context.project_root, context.compose_file, **kwargs)

    def stop(self, context: WorkspaceContext) -> subprocess.CompletedProcess[str]:
        return compose.stop(context.project_root, context.compose_file)

    def restart(self, context: WorkspaceContext) -> subprocess.CompletedProcess[str]:
        return compose.restart(context.project_root, context.compose_file)

    def down(
        self, context: WorkspaceContext, *, volumes: bool = False
    ) -> subprocess.CompletedProcess[str]:
        return compose.down(context.project_root, context.compose_file, volumes=volumes)

    def logs(
        self,
        context: WorkspaceContext,
        *,
        follow: bool = False,
        tail: int | None = None,
        since: str | None = None,
        timestamps: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        kwargs = {"follow": follow, "tail": tail}
        if since is not None:
            kwargs["since"] = since
        if timestamps:
            kwargs["timestamps"] = True
        return compose.logs(context.project_root, context.compose_file, **kwargs)

    def exec(
        self,
        context: WorkspaceContext,
        command: list[str],
        *,
        user: str | None = None,
        interactive: bool = False,
        capture: bool = False,
        check: bool | None = None,
    ) -> subprocess.CompletedProcess[str]:
        kwargs: dict[str, Any] = {"user": user}
        if interactive:
            kwargs["interactive"] = True
        if capture:
            kwargs["capture"] = True
        if check is not None:
            kwargs["check"] = check
        return compose.exec(
            context.project_root, context.compose_file, command, **kwargs
        )

    def service_running(self, context: WorkspaceContext) -> bool:
        return compose.service_running(context.project_root, context.compose_file)

    def ps(self, context: WorkspaceContext) -> subprocess.CompletedProcess[str]:
        return compose.ps(context.project_root, context.compose_file)

    def config(self, context: WorkspaceContext) -> subprocess.CompletedProcess[str]:
        return compose.config(context.project_root, context.compose_file)

    def watch(
        self,
        context: WorkspaceContext,
        *,
        no_up: bool = False,
        prune: bool = True,
        quiet: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        return compose.watch(
            context.project_root,
            context.compose_file,
            no_up=no_up,
            prune=prune,
            quiet=quiet,
        )


def backend_name(data: dict) -> str:
    runtime = data.get("runtime", {})
    if not isinstance(runtime, dict):
        return "compose"
    return str(runtime.get("backend", "compose")).strip().lower() or "compose"


def resolve_backend(data: dict) -> RuntimeBackend:
    name = backend_name(data)
    if name == "compose":
        return ComposeBackend()
    raise BackendError(f"Unsupported runtime backend: {name}")
