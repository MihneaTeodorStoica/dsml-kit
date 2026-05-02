from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
import os
import tomllib

import yaml

from dsml import paths


class ProfileError(ValueError):
    pass


@dataclass(frozen=True)
class Profile:
    name: str
    image: str
    description: str
    gpu: bool | str = "auto"
    image_build: dict[str, object] = field(default_factory=dict)


FALLBACK_PROFILES: dict[str, Profile] = {
    "dev": Profile(
        name="dev",
        image="dsml-kit:dev",
        description="Local development image for dsml-kit maintainers.",
        gpu=False,
        image_build={"args": {"PYTHON_VERSION": "3.11", "DSML_REQUIREMENTS": "requirements-full.txt"}},
    ),
    "minimal": Profile(
        name="minimal",
        image="ghcr.io/mihneateodorstoica/dsml-kit:minimal",
        description="Small JupyterLab data science workspace.",
        gpu=False,
        image_build={"args": {"PYTHON_VERSION": "3.11", "DSML_REQUIREMENTS": "requirements-minimal.txt"}},
    ),
    "base": Profile(
        name="base",
        image="ghcr.io/mihneateodorstoica/dsml-kit:base",
        description="Core numeric Python workspace with common data science packages.",
        gpu=False,
        image_build={"args": {"PYTHON_VERSION": "3.11", "DSML_REQUIREMENTS": "requirements-base.txt"}},
    ),
    "extended": Profile(
        name="extended",
        image="ghcr.io/mihneateodorstoica/dsml-kit:extended",
        description="Broader analytics workspace with columnar, plotting, and stats packages.",
        gpu=False,
        image_build={"args": {"PYTHON_VERSION": "3.11", "DSML_REQUIREMENTS": "requirements-extended.txt"}},
    ),
    "gpu": Profile(
        name="gpu",
        image="ghcr.io/mihneateodorstoica/dsml-kit:full",
        description="Full workspace with GPU runtime access enabled.",
        gpu=True,
        image_build={"args": {"PYTHON_VERSION": "3.11", "DSML_REQUIREMENTS": "requirements-full.txt"}},
    ),
    "full": Profile(
        name="full",
        image="ghcr.io/mihneateodorstoica/dsml-kit:full",
        description="Batteries-included DS/ML workspace with editor and language tooling.",
        gpu="auto",
        image_build={"args": {"PYTHON_VERSION": "3.11", "DSML_REQUIREMENTS": "requirements-full.txt"}},
    ),
}


def profile_dirs() -> list[Path]:
    configured = os.environ.get("DSML_PROFILE_DIR")
    dirs: list[Path] = []
    if configured:
        dirs.append(Path(configured).expanduser())
    dirs.append(paths.repo_root() / "profiles")
    dirs.append(paths.data_profile_dir())
    return dirs


def _load_profile_file(path: Path) -> Profile:
    if path.suffix.lower() in {".yml", ".yaml"}:
        loaded = yaml.safe_load(path.read_text()) or {}
    else:
        loaded = tomllib.loads(path.read_text())
    if not isinstance(loaded, dict):
        raise ProfileError(f"Profile file must contain a mapping: {path}")
    data = dict(loaded)
    return Profile(
        name=str(data["name"]),
        image=str(data["image"]),
        description=str(data.get("description", "")),
        gpu=data.get("gpu", "auto"),
        image_build=data.get("image_build", {}) if isinstance(data.get("image_build", {}), dict) else {},
    )


def load_profiles() -> dict[str, Profile]:
    loaded: dict[str, Profile] = {}
    for directory in profile_dirs():
        if not directory.is_dir():
            continue
        for path in sorted([*directory.glob("*.yml"), *directory.glob("*.yaml"), *directory.glob("*.toml")]):
            profile = _load_profile_file(path)
            loaded[profile.name] = profile

    return loaded or dict(FALLBACK_PROFILES)


def list_profiles() -> list[Profile]:
    return sorted(load_profiles().values(), key=lambda profile: profile.name)


def profile_names() -> list[str]:
    return [profile.name for profile in list_profiles()]


def resolve_profile(name: str) -> Profile:
    profiles = load_profiles()
    if name not in profiles:
        available = ", ".join(sorted(profiles)) or "none"
        raise ProfileError(f"Unknown profile '{name}'. Available profiles: {available}.")
    return profiles[name]


def validate_profile_name(name: str, *, allowed: Iterable[str] | None = None) -> str:
    allowed_names = set(allowed or load_profiles())
    if name not in allowed_names:
        available = ", ".join(sorted(allowed_names)) or "none"
        raise ProfileError(f"Unknown profile '{name}'. Available profiles: {available}.")
    return name
