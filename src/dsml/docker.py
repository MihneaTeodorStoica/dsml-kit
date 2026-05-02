from __future__ import annotations

import shutil
import subprocess

import docker as docker_sdk
from docker.errors import DockerException, ImageNotFound, NotFound


def run(args: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=check,
        text=True,
        capture_output=capture,
    )


def docker_cli_exists() -> bool:
    return shutil.which("docker") is not None


def sdk_client() -> docker_sdk.DockerClient:
    return docker_sdk.from_env()


def _completed(args: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


def daemon_reachable() -> bool:
    try:
        sdk_client().ping()
    except DockerException:
        return False
    return True


def compose_cli_exists() -> bool:
    if not docker_cli_exists():
        return False
    result = run(["docker", "compose", "version"], check=False, capture=True)
    return result.returncode == 0


def nvidia_smi_exists() -> bool:
    return shutil.which("nvidia-smi") is not None


def image_exists(image: str) -> bool:
    try:
        sdk_client().images.get(image)
    except ImageNotFound:
        return False
    except DockerException:
        return False
    return True


def image_id(image: str) -> str:
    try:
        return str(sdk_client().images.get(image).id or "")
    except (ImageNotFound, DockerException):
        return ""


def container_exists(container_name: str) -> bool:
    try:
        sdk_client().containers.get(container_name)
    except NotFound:
        return False
    except DockerException:
        return False
    return True


def remove_container(container_name: str, *, force: bool = False) -> subprocess.CompletedProcess[str]:
    args = ["docker", "rm", *([] if not force else ["-f"]), container_name]
    try:
        sdk_client().containers.get(container_name).remove(force=force)
    except NotFound:
        return _completed(args, 1, stderr=f"No such container: {container_name}")
    except DockerException as exc:
        return _completed(args, 1, stderr=str(exc))
    return _completed(args)


def container_label(container_name: str, label: str) -> str:
    try:
        labels = sdk_client().containers.get(container_name).attrs.get("Config", {}).get("Labels") or {}
    except (NotFound, DockerException):
        return ""
    return str(labels.get(label, ""))


def container_env_value(container_name: str, key: str) -> str | None:
    try:
        env = sdk_client().containers.get(container_name).attrs.get("Config", {}).get("Env") or []
    except (NotFound, DockerException):
        return None
    prefix = f"{key}="
    for line in env:
        if line.startswith(prefix):
            return line[len(prefix) :]
    return None


def pull_image(image: str) -> subprocess.CompletedProcess[str]:
    args = ["docker", "pull", image]
    try:
        sdk_client().images.pull(image)
    except DockerException as exc:
        return _completed(args, 1, stderr=str(exc))
    return _completed(args)


def remove_image(image: str) -> subprocess.CompletedProcess[str]:
    args = ["docker", "image", "rm", image]
    try:
        sdk_client().images.remove(image)
    except ImageNotFound:
        return _completed(args, 1, stderr=f"No such image: {image}")
    except DockerException as exc:
        return _completed(args, 1, stderr=str(exc))
    return _completed(args)


def remove_volume(volume_name: str) -> subprocess.CompletedProcess[str]:
    args = ["docker", "volume", "rm", volume_name]
    try:
        sdk_client().volumes.get(volume_name).remove()
    except NotFound:
        return _completed(args, 1, stderr=f"No such volume: {volume_name}")
    except DockerException as exc:
        return _completed(args, 1, stderr=str(exc))
    return _completed(args)
