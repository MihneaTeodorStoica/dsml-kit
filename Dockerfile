ARG BASE_IMAGE=python:3.11-slim-bookworm@sha256:4dccdf4c57bcf3e1fe4c8323fb3386b830de328954894ebd3580f1e02fbbd22e

FROM ${BASE_IMAGE}
LABEL org.opencontainers.image.title="dsml-kit" \
      org.opencontainers.image.description="JupyterLab-based data science and machine learning workspace"

COPY config/bashrc /etc/skel/.bashrc
COPY requirements.txt /tmp/requirements.txt

ARG NB_USER=jovyan
ARG NB_UID=1000
ARG NB_GID=100
ARG PLAYWRIGHT_NODE_VERSION=24.15.0
ARG PLAYWRIGHT_NODE_SHA256=472655581fb851559730c48763e0c9d3bc25975c59d518003fc0849d3e4ba0f6

ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/home/${NB_USER} \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/home/${NB_USER}/work/.playwright \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SHELL=/bin/bash

RUN apt-get update && \
    apt-get install --yes --no-install-recommends bash bash-completion ca-certificates less locales procps tini && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    locale-gen en_US.UTF-8 && \
    useradd --uid "${NB_UID}" --gid "${NB_GID}" --create-home --shell /bin/bash "${NB_USER}" && \
    mkdir -p "${HOME}/work/.playwright" && \
    python -m pip install --no-cache-dir --upgrade \
      'Brotli==1.2.0' \
      'cryptography==46.0.7' \
      'h11==0.16.0' \
      'h2==4.3.0' \
      'jupyterlab==4.5.6' \
      'notebook==7.5.5' \
      'pip==26.0' \
      'playwright==1.58.0' \
      'setuptools==82.0.1' \
      'urllib3==2.6.3' \
      'wheel==0.46.2' \
      'zstandard==0.25.0' \
      -r /tmp/requirements.txt && \
    playwright install --with-deps chromium && \
    cp /etc/skel/.bashrc "${HOME}/.bashrc" && \
    rm -f /tmp/requirements.txt && \
    chown -R "${NB_UID}:${NB_GID}" "${HOME}"

RUN python - <<'PY'
import hashlib
import os
import pathlib
import shutil
import tarfile
import tempfile
import urllib.request

version = os.environ["PLAYWRIGHT_NODE_VERSION"]
expected_sha256 = os.environ["PLAYWRIGHT_NODE_SHA256"]
url = f"https://nodejs.org/dist/v{version}/node-v{version}-linux-x64.tar.xz"
driver_node = pathlib.Path(__import__("playwright").__file__).resolve().parent / "driver" / "node"

with tempfile.TemporaryDirectory() as tmpdir:
    archive = pathlib.Path(tmpdir) / "node.tar.xz"
    urllib.request.urlretrieve(url, archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise SystemExit(f"checksum mismatch for {url}: {digest} != {expected_sha256}")
    with tarfile.open(archive, "r:xz") as tf:
        member = next(m for m in tf.getmembers() if m.name.endswith("/bin/node"))
        tf.extract(member, tmpdir)
    extracted = next(pathlib.Path(tmpdir).rglob("bin/node"))
    shutil.copy2(extracted, driver_node)
    driver_node.chmod(0o755)
PY

RUN XDG_CACHE_HOME=/tmp/pip-cache python -m pip check && \
    python - <<'PY'
import subprocess
from pathlib import Path
import playwright

driver_node = Path(playwright.__file__).resolve().parent / "driver" / "node"
subprocess.run([str(driver_node), "--version"], check=True)
Path("/usr/local/bin/node").symlink_to(driver_node)
PY

WORKDIR ${HOME}/work

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8888), 5).close()" || exit 1

ENTRYPOINT ["tini", "-g", "--"]

CMD ["jupyter", "lab", "--ServerApp.ip=0.0.0.0", "--ServerApp.port=8888", "--ServerApp.open_browser=False", "--ServerApp.log_level=CRITICAL", "--LabApp.log_level=CRITICAL", "--ServerApp.root_dir=/home/jovyan/work", "--ServerApp.websocket_ping_interval=30000", "--ServerApp.websocket_ping_timeout=30000"]

USER ${NB_UID}
