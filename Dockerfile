ARG UV_IMAGE=ghcr.io/astral-sh/uv:latest

FROM ${UV_IMAGE} AS uv

FROM quay.io/jupyter/base-notebook:python-3.11

COPY --from=uv /uv /uvx /usr/local/bin/

USER root

RUN apt-get update && \
    apt-get install --yes --only-upgrade sudo gpgv libgpg-error0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    uv pip install \
      --system \
      --upgrade \
      --strict \
      'h11>=0.16.0' \
      'urllib3>=2.6.3' \
      jupyterlab \
      notebook

USER 1000

ENV UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
