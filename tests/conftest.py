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
    return os.environ.get("DSML_TEST_IMAGE", "dsml-kit:validate")


@pytest.fixture
def image_container(request):
    container_name = f"dsml-kit-image-smoke-{uuid.uuid4().hex[:8]}"

    def cleanup():
        run(["docker", "rm", "-f", container_name], check=False)

    request.addfinalizer(cleanup)
    cleanup()
    return container_name


@pytest.fixture
def compose_runtime(request, tmp_path):
    project_name = f"dsml-kit-test-{uuid.uuid4().hex[:8]}"
    container_name = f"dsml-kit-compose-{uuid.uuid4().hex[:8]}"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    port = free_port()
    host_uid = os.getuid()
    host_gid = os.getgid()
    env = {
        "COMPOSE_PROJECT_NAME": project_name,
        "CONTAINER_NAME": container_name,
        "IMAGE_NAME": os.environ.get("DSML_TEST_IMAGE_NAME", "dsml-kit"),
        "DSML_TAG": os.environ.get("DSML_TEST_TAG", "validate"),
        "PULL_POLICY": "never",
        "RESTART_POLICY": "no",
        "WORKSPACE_DIR": str(workspace),
        "JUPYTER_PORT": str(port),
        "JUPYTER_TOKEN": "validate-token",
        "HOST_UID": str(host_uid),
        "HOST_GID": str(host_gid),
    }
    compose = ["docker", "compose", "-f", "compose.yaml", "-f", "compose.dev.yaml"]

    def compose_run(*args, check=True, input_text=None):
        return run([*compose, *args], env=env, input_text=input_text, check=check)

    def diagnostics():
        ps = compose_run("ps", check=False).stdout
        logs = compose_run("logs", "app", check=False).stdout
        inspect = docker_inspect(container_name)
        return f"compose ps:\n{ps}\ncompose logs:\n{logs}\ninspect:\n{inspect}"

    def cleanup():
        compose_run("down", "--remove-orphans", check=False)
        shutil.rmtree(workspace, ignore_errors=True)

    request.addfinalizer(cleanup)
    cleanup()

    return {
        "container_name": container_name,
        "diagnostics": diagnostics,
        "env": env,
        "host_gid": host_gid,
        "host_uid": host_uid,
        "port": port,
        "run": compose_run,
        "token": "validate-token",
        "workspace": workspace,
    }
