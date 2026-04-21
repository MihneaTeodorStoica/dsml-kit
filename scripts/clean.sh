#!/usr/bin/env bash
set -euo pipefail

container_name="dsml"

if docker container inspect "$container_name" >/dev/null 2>&1; then
  docker rm -f "$container_name"
else
  echo "Container '$container_name' does not exist."
fi
