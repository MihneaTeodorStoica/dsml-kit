#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

local_image="dsml-kit"
remote_image="${1:-docker.io/mihneateodorstoica/dsml-kit:latest}"

ensure_image

docker tag "$local_image" "$remote_image"
docker push "$remote_image"
