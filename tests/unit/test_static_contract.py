import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def read_repo_text(path):
    return (REPO_ROOT / path).read_text()


def read_repo_file(path):
    return read_repo_text(path).splitlines()


def test_dockerfile_uses_pinned_base_image_uv_and_healthcheck():
    dockerfile = read_repo_file("images/base/Dockerfile")

    assert dockerfile[0] == "ARG PYTHON_VERSION=3.11"
    assert any("FROM quay.io/jupyter/minimal-notebook:python-${PYTHON_VERSION}" in line for line in dockerfile)
    assert any("ARG DSML_REQUIREMENTS=requirements-base.txt" in line for line in dockerfile)
    assert any("ARG DSML_EXTRA_APT_PACKAGES" in line for line in dockerfile)
    assert any("COPY --from=uv /uv /usr/local/bin/uv" in line for line in dockerfile)
    assert any("COPY --chown=${NB_UID}:${NB_GID} images/base/requirements*.txt" in line for line in dockerfile)
    assert any('uv pip install --system -r "/tmp/dsml-requirements/${DSML_REQUIREMENTS}"' in line for line in dockerfile)
    assert any(line.startswith("HEALTHCHECK ") for line in dockerfile)
    assert any("socket.create_connection(('127.0.0.1', 8888), 5)" in line for line in dockerfile)


def test_runtime_image_variants_have_separate_requirements_files():
    for variant in ("minimal", "base", "extended", "full"):
        assert (REPO_ROOT / "images" / "base" / f"requirements-{variant}.txt").is_file()


def test_dockerignore_excludes_local_runtime_state():
    ignored = set(read_repo_file(".dockerignore"))

    assert ".git" in ignored
    assert ".github" in ignored
    assert ".env" in ignored
    assert ".dsml/" in ignored
    assert "workspace/" in ignored
    assert "*.ipynb" in ignored
    assert "__pycache__/" in ignored


def test_gitignore_excludes_generated_test_and_runtime_state():
    ignored = set(read_repo_file(".gitignore"))

    assert ".env" in ignored
    assert ".dsml/" in ignored
    assert ".pytest_cache/" in ignored
    assert "__pycache__/" in ignored
    assert "*.py[cod]" in ignored
    assert ".test-workspace/" in ignored
    assert "workspace/" in ignored


def test_obsolete_product_interfaces_are_removed():
    assert not (REPO_ROOT / "Makefile").exists()
    assert not (REPO_ROOT / "compose.yaml").exists()
    assert not (REPO_ROOT / "compose.dev.yaml").exists()
    assert not (REPO_ROOT / "compose.gpu.yaml").exists()
    assert not (REPO_ROOT / ".env.example").exists()


def test_devcontainer_supports_repo_development_without_docker_engine():
    config_path = REPO_ROOT / ".devcontainer/devcontainer.json"
    dockerfile = read_repo_file(".devcontainer/Dockerfile")
    config = json.loads(read_repo_text(".devcontainer/devcontainer.json"))

    assert config_path.exists()
    assert config["workspaceFolder"] == "/workspaces/dsml-kit"
    assert config["remoteUser"] == "vscode"
    assert config["postCreateCommand"] == "uv sync"
    assert 8888 in config["forwardPorts"]
    assert "unix:///var/run/docker.sock" == config["containerEnv"]["DOCKER_HOST"]
    assert any("/var/run/docker.sock" in mount for mount in config["mounts"])

    extensions = set(config["customizations"]["vscode"]["extensions"])
    assert {
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
        "ms-azuretools.vscode-docker",
        "tamasfe.even-better-toml",
        "redhat.vscode-yaml",
    } <= extensions

    assert dockerfile[0] == "FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm"
    assert any("COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/" in line for line in dockerfile)
    assert any("docker-ce-cli" in line for line in dockerfile)
    assert any("docker-compose-plugin" in line for line in dockerfile)
    assert not any("docker-ce " in line for line in dockerfile)
