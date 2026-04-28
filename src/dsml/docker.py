from __future__ import annotations

import json
import shutil
import subprocess


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


def pull_image(image: str) -> subprocess.CompletedProcess[str]:
    return run(["docker", "pull", image])


def remove_image(image: str) -> subprocess.CompletedProcess[str]:
    return run(["docker", "image", "rm", image], check=False, capture=True)


def remove_volume(volume_name: str) -> subprocess.CompletedProcess[str]:
    return run(["docker", "volume", "rm", volume_name], check=False, capture=True)
