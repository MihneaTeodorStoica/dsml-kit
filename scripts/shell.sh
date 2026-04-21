#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

container_name="dsml"

ensure_image

current_image_id="$(docker image inspect --format '{{.Id}}' "$image_name")"

if docker container inspect "$container_name" >/dev/null 2>&1; then
  container_image_id="$(docker container inspect --format '{{.Image}}' "$container_name")"

  if [[ "$container_image_id" != "$current_image_id" ]]; then
    docker rm -f "$container_name" >/dev/null
  fi
fi

if docker container inspect "$container_name" >/dev/null 2>&1; then
  if [[ "$(docker container inspect -f '{{.State.Running}}' "$container_name")" != "true" ]]; then
    docker start "$container_name" >/dev/null
  fi

  exec docker exec -it "$container_name" bash -il
fi

exec docker run -it -p 8888:8888 --name "$container_name" "$image_name" bash -il
