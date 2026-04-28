FROM quay.io/jupyter/minimal-notebook:python-3.11@sha256:1f1fab5b452289aff0ed9c6d85a58f555a4682b773f1dad08c2fdb35273e9ea4

ENV JUPYTER_APP_LOG_LEVEL=WARN \
    JUPYTER_SERVER_LOG_LEVEL=WARN \
    JUPYTER_ROOT_DIR=/home/jovyan/work \
    JUPYTER_BASE_URL=/ \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

USER root

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --chown=${NB_UID}:${NB_GID} images/base/requirements.txt /tmp/requirements.txt
RUN mkdir -p /home/${NB_USER}/work \
    && chown ${NB_UID}:${NB_GID} /home/${NB_USER}/work \
    && uv pip install --system -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt \
    && fix-permissions "${CONDA_DIR}" \
    && fix-permissions "/home/${NB_USER}"

USER ${NB_UID}

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8888), 5).close()"

CMD start-notebook.py --Application.log_level="${JUPYTER_APP_LOG_LEVEL}" --ServerApp.log_level="${JUPYTER_SERVER_LOG_LEVEL}" --ServerApp.root_dir="${JUPYTER_ROOT_DIR}" --ServerApp.base_url="${JUPYTER_BASE_URL}" ${JUPYTER_EXTRA_ARGS}
