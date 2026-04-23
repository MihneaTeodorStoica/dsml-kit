FROM quay.io/jupyter/minimal-notebook:python-3.11

COPY --chown=${NB_UID}:${NB_GID} requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

CMD ["start-notebook.py", "--Application.log_level=CRITICAL", "--ServerApp.log_level=CRITICAL"]
