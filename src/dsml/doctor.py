from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dsml import config, docker, paths, profiles, runtime


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    message: str


def run_checks(start: Path | None = None) -> list[Check]:
    checks: list[Check] = []
    checks.append(_check("Docker CLI", docker.docker_cli_exists(), "Install Docker if this fails."))
    checks.append(_check("Docker daemon", docker.daemon_reachable(), "Start Docker Desktop or the Docker daemon."))
    checks.append(
        _check(
            "Docker Compose v2",
            docker.compose_cli_exists(),
            "Install Docker Compose v2 so `docker compose version` works.",
        )
    )

    config_path = paths.locate_config(start)
    if config_path is None:
        checks.append(Check("dsml.yml", False, "Run 'dsml init' in this project."))
        return checks

    try:
        data = config.read_config(config_path)
        checks.append(Check("dsml.yml", True, str(config_path)))
    except config.ConfigError as exc:
        checks.append(Check("dsml.yml", False, str(exc)))
        return checks

    workspace = data["workspace"]
    try:
        profile = profiles.resolve_profile(workspace["profile"])
        checks.append(Check("Profile", True, profile.name))
    except profiles.ProfileError as exc:
        checks.append(Check("Profile", False, str(exc)))
        return checks

    checks.append(
        _check(
            "Configured port",
            runtime.port_is_free(workspace["bind_address"], workspace["port"]),
            f"{workspace['bind_address']}:{workspace['port']} is already in use.",
        )
    )

    image = workspace.get("image") or profile.image
    if docker.docker_cli_exists() and docker.daemon_reachable():
        policy = workspace.get("image_policy", "auto")
        if policy == "build" or (policy == "auto" and runtime.should_build_image(image)):
            image_message = f"{image} is not present locally. 'dsml up' will build it."
        elif policy == "never":
            image_message = f"{image} is not present locally and image_policy is set to never."
        else:
            image_message = f"{image} is not present locally. 'dsml up' will try to pull it."
        checks.append(
            _check(
                "Image",
                docker.image_exists(image),
                image_message,
            )
        )
    else:
        checks.append(Check("Image", False, "Docker is not reachable, so the image cannot be checked."))

    gpu_requested = runtime.resolve_gpu(workspace["gpu"], profile.gpu)
    if gpu_requested:
        checks.append(_check("nvidia-smi", docker.nvidia_smi_exists(), "Install NVIDIA drivers/toolkit for GPU mode."))
        checks.append(_check("Docker GPU", _docker_gpu_works(), "Check NVIDIA Container Toolkit configuration."))

    return checks


def _check(name: str, ok: bool, failure_message: str) -> Check:
    return Check(name, ok, "ok" if ok else failure_message)


def _docker_gpu_works() -> bool:
    result = docker.run(
        ["docker", "run", "--rm", "--gpus", "all", "nvidia/cuda:12.4.1-base-ubuntu22.04", "nvidia-smi"],
        check=False,
        capture=True,
    )
    return result.returncode == 0
