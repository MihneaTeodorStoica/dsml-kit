from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


WatchAction = Literal["rebuild"]


@dataclass(frozen=True)
class WatchRule:
    action: WatchAction
    path: Path


@dataclass(frozen=True)
class RuntimeOptions:
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
    build_context: Path | None = None
    build_dockerfile: Path | None = None
    build_target: str = ""
    build_args: dict[str, str] = field(default_factory=dict)
    watch: list[WatchRule] = field(default_factory=list)
