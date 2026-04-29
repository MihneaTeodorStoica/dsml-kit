#!/usr/bin/env bash
set -euo pipefail

SOCKET="${DOCKER_HOST:-}"
SOCKET="${SOCKET#unix://}"
SOCKET="${SOCKET:-/var/run/docker.sock}"
REMOTE_USER="${_REMOTE_USER:-${USERNAME:-vscode}}"

if [ "$(id -u)" = "0" ] && [ -S "${SOCKET}" ] && id "${REMOTE_USER}" >/dev/null 2>&1; then
    socket_gid="$(stat -c "%g" "${SOCKET}")"
    group_name="$(awk -F: -v gid="${socket_gid}" '$3 == gid { print $1; exit }' /etc/group)"

    if [ -z "${group_name}" ]; then
        group_name="docker-host"
        if getent group "${group_name}" >/dev/null 2>&1; then
            group_name="docker-host-${socket_gid}"
        fi
        groupadd --gid "${socket_gid}" "${group_name}"
    fi

    usermod -aG "${group_name}" "${REMOTE_USER}"
fi

exec "$@"
