#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

container_name="dsml"
gpu_args=(--gpus all)

ensure_image

if [[ "${1:-}" == "--no-gpu" ]]; then
  gpu_args=()
  shift
fi

if docker container inspect "$container_name" >/dev/null 2>&1; then
  if [[ "$(docker container inspect -f '{{.State.Running}}' "$container_name")" == "true" ]]; then
    print_running_notebook_servers "$container_name"
    exec docker attach "$container_name"
  fi

  print_notebook_hint
  exec docker start -ai "$container_name"
fi

print_notebook_hint
exec docker run -it -p 8888:8888 --name "$container_name" "${gpu_args[@]}" "$image_name"
