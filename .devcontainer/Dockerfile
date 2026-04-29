FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

ARG DEBIAN_FRONTEND=noninteractive

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

USER root

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
        gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && . /etc/os-release \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        docker-ce-cli \
        docker-compose-plugin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY docker-socket-permissions.sh /usr/local/share/docker-socket-permissions.sh
RUN chmod +x /usr/local/share/docker-socket-permissions.sh

ENTRYPOINT ["/usr/local/share/docker-socket-permissions.sh"]
CMD ["sleep", "infinity"]
