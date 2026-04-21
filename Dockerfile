ARG BASE_IMAGE=python:3.11-slim-bookworm
ARG UV_IMAGE=ghcr.io/astral-sh/uv:latest

FROM ${UV_IMAGE} AS uv

FROM ${BASE_IMAGE}

COPY --from=uv /uv /uvx /usr/local/bin/
COPY config/bashrc /etc/skel/.bashrc
COPY requirements.txt /tmp/requirements.txt

ARG NB_USER=jovyan
ARG NB_UID=1000
ARG NB_GID=100
ARG PLAYWRIGHT_NODE_VERSION=24.14.1

ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/home/${NB_USER} \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PLAYWRIGHT_BROWSERS_PATH=/home/${NB_USER}/work/.playwright \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SHELL=/bin/bash \
    UV_SYSTEM_PYTHON=1 \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && \
    apt-get upgrade --yes && \
    apt-get install --yes --no-install-recommends bash bash-completion ca-certificates less locales procps tini && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    locale-gen en_US.UTF-8 && \
    useradd --uid "${NB_UID}" --gid "${NB_GID}" --create-home --shell /bin/bash "${NB_USER}" && \
    mkdir -p "${HOME}/work/.playwright" && \
    uv pip install \
    --system \
    --upgrade \
    --strict \
    'Brotli>=1.2.0' \
    'cryptography>=46.0.6' \
    'h11>=0.16.0' \
    'h2>=4.3.0' \
    'pip>=25.3' \
    'urllib3>=2.6.3' \
    'wheel>=0.46.2' \
    'zstandard>=0.25.0' \
      playwright \
      jupyterlab \
      notebook \
      -r /tmp/requirements.txt && \
    playwright install --with-deps chromium && \
    cp /etc/skel/.bashrc "${HOME}/.bashrc" && \
    rm -f /tmp/requirements.txt && \
    chown -R "${NB_UID}:${NB_GID}" "${HOME}"

RUN python - <<'PY'
import pathlib
import shutil
import tarfile
import tempfile
import urllib.request

version = "24.14.1"
url = f"https://nodejs.org/dist/v{version}/node-v{version}-linux-x64.tar.xz"
driver_node = pathlib.Path("/usr/local/lib/python3.11/site-packages/playwright/driver/node")

with tempfile.TemporaryDirectory() as tmpdir:
    archive = pathlib.Path(tmpdir) / "node.tar.xz"
    urllib.request.urlretrieve(url, archive)
    with tarfile.open(archive, "r:xz") as tf:
        member = next(m for m in tf.getmembers() if m.name.endswith("/bin/node"))
        tf.extract(member, tmpdir)
    extracted = next(pathlib.Path(tmpdir).rglob("bin/node"))
    shutil.copy2(extracted, driver_node)
    driver_node.chmod(0o755)
PY

RUN /usr/local/lib/python3.11/site-packages/playwright/driver/node --version

WORKDIR ${HOME}/work

EXPOSE 8888

ENTRYPOINT ["tini", "-g", "--"]

CMD ["jupyter", "lab", "--ServerApp.ip=0.0.0.0", "--ServerApp.port=8888", "--ServerApp.open_browser=False", "--ServerApp.root_dir=/home/jovyan/work"]

USER ${NB_UID}
