from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path


CONFIG_FILE = "dsml.toml"
PROJECT_LABEL = "dsml.project"
CONFIG_LABEL = "dsml.config"


def cwd() -> Path:
    return Path.cwd()


def find_project_root(start: Path | None = None) -> Path:
    current = (start or cwd()).resolve()
    for parent in (current, *current.parents):
        if (parent / CONFIG_FILE).is_file():
            return parent
        if (parent / ".git").exists():
            return parent
    return current


def locate_config(start: Path | None = None) -> Path | None:
    current = (start or cwd()).resolve()
    for parent in (current, *current.parents):
        candidate = parent / CONFIG_FILE
        if candidate.is_file():
            return candidate
    return None


def config_path(project_root: Path | None = None) -> Path:
    return (project_root or find_project_root()) / CONFIG_FILE


def resolve_mount_path(project_root: Path, mount: str | os.PathLike[str]) -> Path:
    path = Path(mount).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def safe_slug(value: str, *, max_length: int = 42) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if not slug:
        slug = "workspace"
    return slug[:max_length].strip("-") or "workspace"


def short_hash(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:6]


def project_name(project_root: Path) -> str:
    return f"{safe_slug(project_root.name)}-{short_hash(project_root)}"


def default_container_name(project_root: Path) -> str:
    return f"dsml-{project_name(project_root)}"


def default_home_volume(project_root: Path) -> str:
    return f"dsml-home-{project_name(project_root)}"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_profile_dir() -> Path:
    return Path(sys.prefix) / "share" / "dsml-kit" / "profiles"
