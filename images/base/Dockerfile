ARG PYTHON_VERSION=3.11
ARG UV_VERSION=latest
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv
FROM quay.io/jupyter/minimal-notebook:python-${PYTHON_VERSION}

ARG DSML_EXTRA_APT_PACKAGES=""
ARG DSML_REQUIREMENTS=requirements-base.txt

ENV JUPYTER_APP_LOG_LEVEL=WARN \
    JUPYTER_SERVER_LOG_LEVEL=WARN \
    JUPYTER_ROOT_DIR=/home/jovyan/work \
    JUPYTER_BASE_URL=/ \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

USER root

COPY --from=uv /uv /usr/local/bin/uv
COPY --chown=${NB_UID}:${NB_GID} images/base/requirements*.txt /tmp/dsml-requirements/
RUN mkdir -p /home/${NB_USER}/work \
    && chown ${NB_UID}:${NB_GID} /home/${NB_USER}/work \
    && if [ -n "${DSML_EXTRA_APT_PACKAGES}" ]; then \
        apt-get update \
        && apt-get install -y --no-install-recommends ${DSML_EXTRA_APT_PACKAGES} \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*; \
    fi \
    && uv pip install --system -r "/tmp/dsml-requirements/${DSML_REQUIREMENTS}" \
    && rm -rf /tmp/dsml-requirements \
    && fix-permissions "${CONDA_DIR}" \
    && fix-permissions "/home/${NB_USER}"

USER ${NB_UID}

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8888), 5).close()"

CMD start-notebook.py --Application.log_level="${JUPYTER_APP_LOG_LEVEL}" --ServerApp.log_level="${JUPYTER_SERVER_LOG_LEVEL}" --ServerApp.root_dir="${JUPYTER_ROOT_DIR}" --ServerApp.base_url="${JUPYTER_BASE_URL}" ${JUPYTER_EXTRA_ARGS}
