import os
import shutil
import socket
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(command, *, env=None, input_text=None, check=True):
    merged_env = os.environ.copy()
    if env:
        merged_env.update({key: str(value) for key, value in env.items()})

    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=merged_env,
        input=input_text,
        text=True,
        capture_output=True,
        check=check,
    )


def assert_run(command, *, env=None, input_text=None):
    result = run(command, env=env, input_text=input_text, check=False)
    if result.returncode != 0:
        pytest.fail(
            "command failed:\n"
            f"$ {' '.join(command)}\n"
            f"exit code: {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def docker_logs(container_name):
    return run(["docker", "logs", container_name], check=False).stdout


def docker_inspect(container_name):
    return run(["docker", "inspect", container_name], check=False).stdout


def wait_for_container_health(container_name, *, attempts=30, sleep_seconds=2):
    for _ in range(attempts):
        result = run(
            [
                "docker",
                "inspect",
                "--format={{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
                container_name,
            ],
            check=False,
        )
        status = result.stdout.strip()
        if status in {"healthy", "running"}:
            return
        if status in {"exited", "dead"}:
            break
        time.sleep(sleep_seconds)

    pytest.fail(
        f"container {container_name} did not become healthy\n"
        f"logs:\n{docker_logs(container_name)}\n"
        f"inspect:\n{docker_inspect(container_name)}"
    )


def wait_for_http(url, *, attempts=30, sleep_seconds=2):
    last_error = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 300:
                    return
        except Exception as exc:  # noqa: BLE001 - surfaced in pytest failure below.
            last_error = exc
        time.sleep(sleep_seconds)

    pytest.fail(f"HTTP endpoint did not become available: {url}\nlast error: {last_error}")


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def image():
    image_name = os.environ.get("DSML_TEST_IMAGE", "dsml-kit:validate")
    if shutil.which("docker") is None:
        pytest.skip("Docker is required for image integration tests.")
    result = run(["docker", "image", "inspect", image_name], check=False)
    if result.returncode != 0:
        pytest.skip(f"Docker image {image_name} is not present. Build it before integration tests.")
    return image_name


@pytest.fixture
def image_container(request):
    container_name = f"dsml-kit-image-smoke-{uuid.uuid4().hex[:8]}"

    def cleanup():
        run(["docker", "rm", "-f", container_name], check=False)

    request.addfinalizer(cleanup)
    cleanup()
    return container_name
