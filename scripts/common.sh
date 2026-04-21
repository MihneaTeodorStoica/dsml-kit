#!/usr/bin/env bash
set -euo pipefail

image_name="dsml-kit"
base_image="${BASE_IMAGE:-python:3.11-slim-bookworm}"
uv_image="${UV_IMAGE:-ghcr.io/astral-sh/uv:latest}"
build_files=(Dockerfile .dockerignore config/bashrc requirements.txt)

require_repo_root() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  cd "$script_dir"
}

resolve_build_images() {
  docker pull "$base_image" >/dev/null
  docker pull "$uv_image" >/dev/null
}

compute_build_hash() {
  local tmp
  tmp="$({
    printf 'UV_IMAGE=%s\n' "$uv_image"
    printf 'BASE_IMAGE=%s\n' "$base_image"
    docker image inspect --format '{{.Id}}' "$base_image"
    docker image inspect --format '{{.Id}}' "$uv_image"
    for file in "${build_files[@]}"; do
      if [[ -f "$file" ]]; then
        sha256sum "$file"
      fi
    done
  } | sha256sum | cut -d' ' -f1)"
  printf '%s\n' "$tmp"
}

current_build_hash() {
  docker image inspect --format '{{ index .Config.Labels "io.dsml-kit.build-hash" }}' "$image_name" 2>/dev/null || true
}

ensure_image() {
  local desired_hash current_hash

  require_repo_root
  resolve_build_images
  desired_hash="$(compute_build_hash)"
  current_hash="$(current_build_hash)"

  if [[ "$desired_hash" == "$current_hash" ]]; then
    echo "Image '$image_name' is up to date."
    return 0
  fi

  docker build \
    --build-arg "BASE_IMAGE=$base_image" \
    --build-arg "UV_IMAGE=$uv_image" \
    --label "io.dsml-kit.build-hash=$desired_hash" \
    --label "io.dsml-kit.base-image=$base_image" \
    --label "io.dsml-kit.uv-image=$uv_image" \
    -t "$image_name" \
    .
}

print_notebook_hint() {
  echo "Notebook URL: http://127.0.0.1:8888"
}

print_running_notebook_servers() {
  local container_name="$1"
  local server_list

  server_list="$(docker exec "$container_name" sh -lc 'jupyter server list 2>/dev/null | sed 1d' 2>/dev/null || true)"

  if [[ -n "$server_list" ]]; then
    echo "$server_list"
  else
    print_notebook_hint
  fi
}
