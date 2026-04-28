from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def read_repo_file(path):
    return (REPO_ROOT / path).read_text().splitlines()


def test_dockerfile_uses_pinned_base_image_uv_and_healthcheck():
    dockerfile = read_repo_file("images/base/Dockerfile")

    assert dockerfile[0].startswith("FROM quay.io/jupyter/minimal-notebook:python-3.11@sha256:")
    assert any("COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv" in line for line in dockerfile)
    assert any("uv pip install --system -r /tmp/requirements.txt" in line for line in dockerfile)
    assert any(line.startswith("HEALTHCHECK ") for line in dockerfile)
    assert any("socket.create_connection(('127.0.0.1', 8888), 5)" in line for line in dockerfile)


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
