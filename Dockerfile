FROM quay.io/jupyter/minimal-notebook:python-3.11

COPY --chown=${NB_UID}:${NB_GID} requirements.txt /tmp/requirements.txt
RUN pip install uv \
    && uv pip install --system -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt
