from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import os
import tomllib

from dsml import paths


class ProfileError(ValueError):
    pass


@dataclass(frozen=True)
class Profile:
    name: str
    image: str
    description: str
    gpu: bool | str = "auto"


FALLBACK_PROFILES: dict[str, Profile] = {
    "dev": Profile(
        name="dev",
        image="dsml-kit:dev",
        description="Local development image for dsml-kit maintainers.",
        gpu=False,
    ),
    "minimal": Profile(
        name="minimal",
        image="ghcr.io/mihneateodorstoica/dsml-kit:minimal",
        description="Small JupyterLab data science workspace.",
        gpu=False,
    ),
    "gpu": Profile(
        name="gpu",
        image="ghcr.io/mihneateodorstoica/dsml-kit:gpu",
        description="GPU-ready ML workspace.",
        gpu=True,
    ),
    "full": Profile(
        name="full",
        image="ghcr.io/mihneateodorstoica/dsml-kit:full",
        description="Batteries-included DS/ML workspace.",
        gpu="auto",
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
    data = tomllib.loads(path.read_text())
    return Profile(
        name=str(data["name"]),
        image=str(data["image"]),
        description=str(data.get("description", "")),
        gpu=data.get("gpu", "auto"),
    )


def load_profiles() -> dict[str, Profile]:
    loaded: dict[str, Profile] = {}
    for directory in profile_dirs():
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.toml")):
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
