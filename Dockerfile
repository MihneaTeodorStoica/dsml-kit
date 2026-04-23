FROM quay.io/jupyter/minimal-notebook:python-3.11

COPY --chown=${NB_UID}:${NB_GID} requirements.txt /tmp/requirements.txt
RUN mamba install --yes --channel conda-forge --file /tmp/requirements.txt \
    && mamba clean --all --yes \
    && rm /tmp/requirements.txt
