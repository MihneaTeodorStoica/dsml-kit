SHELL := /usr/bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.SILENT:

IMAGE_NAME ?= dsml-kit
CONTAINER_NAME ?= dsml
IMAGE_REF ?= docker.io/mihneateodorstoica/dsml-kit:latest
BASE_IMAGE ?= python:3.11-slim-bookworm
BUILD_FILES := Dockerfile .dockerignore config/bashrc requirements.txt Makefile

.PHONY: help build run shell clean publish validate

define COMMON_SH
repo_root="$$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$$repo_root"

pull_base_image() {
  if docker pull "$(BASE_IMAGE)" >/dev/null; then
    return 0
  fi

  if [[ "$(BASE_IMAGE)" == dhi.io/* ]]; then
    printf '%s\n' 'Failed to pull Docker Hardened Image. Run: docker login dhi.io'
  fi

  return 1
}

compute_build_hash() {
  {
    printf 'BASE_IMAGE=%s\n' "$(BASE_IMAGE)"
    docker image inspect --format '{{.Id}}' "$(BASE_IMAGE)"
    for file in $(BUILD_FILES); do
      if [[ -f "$$file" ]]; then
        sha256sum "$$file"
      fi
    done
  } | sha256sum | cut -d' ' -f1
}

current_build_hash() {
  docker image inspect --format '{{ index .Config.Labels "io.dsml-kit.build-hash" }}' "$(IMAGE_NAME)" 2>/dev/null || true
}

print_notebook_url() {
  local raw_url token

  raw_url="$$(docker exec "$(CONTAINER_NAME)" sh -lc 'jupyter server list 2>/dev/null | sed 1d | head -n 1 | cut -d" " -f1' 2>/dev/null || true)"

  if [[ -z "$$raw_url" ]]; then
    printf '%s\n' 'http://127.0.0.1:8888'
    return 0
  fi

  token="$${raw_url#*?token=}"
  if [[ "$$token" == "$$raw_url" ]]; then
    printf '%s\n' 'http://127.0.0.1:8888'
    return 0
  fi

  printf 'http://127.0.0.1:8888/?token=%s\n' "$$token"
}

wait_for_notebook_url() {
  local url=''

  for _ in $$(seq 1 30); do
    url="$$(docker exec "$(CONTAINER_NAME)" sh -lc 'jupyter server list 2>/dev/null | sed 1d | head -n 1 | cut -d" " -f1' 2>/dev/null || true)"
    if [[ -n "$$url" ]]; then
      print_notebook_url
      return 0
    fi
    sleep 1
  done

  printf '%s\n' 'http://127.0.0.1:8888'
}

ensure_image() {
  local desired_hash current_hash build_date vcs_ref source_url

  pull_base_image
  desired_hash="$$(compute_build_hash)"
  current_hash="$$(current_build_hash)"

  if [[ "$$desired_hash" == "$$current_hash" ]]; then
    return 0
  fi

  build_date="$$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  vcs_ref="$$(git rev-parse --short=12 HEAD 2>/dev/null || printf unknown)"
  source_url="$$(git config --get remote.origin.url 2>/dev/null || true)"

  docker build \
    --pull \
    --build-arg "BASE_IMAGE=$(BASE_IMAGE)" \
    --label "io.dsml-kit.build-hash=$$desired_hash" \
    --label "io.dsml-kit.base-image=$(BASE_IMAGE)" \
    --label "org.opencontainers.image.created=$$build_date" \
    --label "org.opencontainers.image.revision=$$vcs_ref" \
    --label "org.opencontainers.image.source=$$source_url" \
    --label "org.opencontainers.image.version=local" \
    -t "$(IMAGE_NAME)" \
    .
}

ensure_fresh_container() {
  local current_image_id container_image_id

  current_image_id="$$(docker image inspect --format '{{.Id}}' "$(IMAGE_NAME)")"

  if docker container inspect "$(CONTAINER_NAME)" >/dev/null 2>&1; then
    container_image_id="$$(docker container inspect --format '{{.Image}}' "$(CONTAINER_NAME)")"
    if [[ "$$container_image_id" != "$$current_image_id" ]]; then
      docker rm -f "$(CONTAINER_NAME)" >/dev/null
    fi
  fi
}

container_gpu_args() {
  if [[ "${NO_GPU:-0}" == "1" ]]; then
    return 0
  fi

  printf '%s\n' '--gpus' 'all'
}

create_container() {
  local mode="${1:-detached}"
  local gpu_args=()

  mapfile -t gpu_args < <(container_gpu_args)

  if [[ "$mode" == "interactive" ]]; then
    exec docker run -it -p 8888:8888 --name "$(CONTAINER_NAME)" "$${gpu_args[@]}" "$(IMAGE_NAME)"
  fi

  docker run -d -p 8888:8888 --name "$(CONTAINER_NAME)" "$${gpu_args[@]}" "$(IMAGE_NAME)" >/dev/null
}
endef

help:
	@printf '%s\n' \
	  'make build              Build or refresh the local image' \
	  'make run [NO_GPU=1]    Start or attach to the Jupyter container' \
	  'make shell [NO_GPU=1]  Open a shell inside the container' \
	  'make validate          Validate installed tools and scan if available' \
	  'make clean             Remove the persistent container' \
	  'make publish [IMAGE_REF=repo:tag]  Tag and push the local image'

build:
	$(COMMON_SH)
	ensure_image

run:
	$(COMMON_SH)
	ensure_image
	ensure_fresh_container
	if docker container inspect "$(CONTAINER_NAME)" >/dev/null 2>&1; then
	  if [[ "$$(docker container inspect -f '{{.State.Running}}' "$(CONTAINER_NAME)")" == "true" ]]; then
	    print_notebook_url
	    exec docker attach "$(CONTAINER_NAME)"
	  fi
	  docker start "$(CONTAINER_NAME)" >/dev/null
	  wait_for_notebook_url
	  exec docker attach "$(CONTAINER_NAME)"
	fi
	create_container
	wait_for_notebook_url
	exec docker attach "$(CONTAINER_NAME)"

shell:
	$(COMMON_SH)
	ensure_image
	ensure_fresh_container
	if ! docker container inspect "$(CONTAINER_NAME)" >/dev/null 2>&1; then
	  create_container
	fi
	if [[ "$$(docker container inspect -f '{{.State.Running}}' "$(CONTAINER_NAME)")" != "true" ]]; then
	  docker start "$(CONTAINER_NAME)" >/dev/null
	fi
	exec docker exec -it "$(CONTAINER_NAME)" bash -il

clean:
	$(COMMON_SH)
	if docker container inspect "$(CONTAINER_NAME)" >/dev/null 2>&1; then
	  docker rm -f "$(CONTAINER_NAME)"
	else
	  printf 'Container %s does not exist.\n' "$(CONTAINER_NAME)"
	fi

publish:
	$(COMMON_SH)
	ensure_image
	docker tag "$(IMAGE_NAME)" "$(IMAGE_REF)"
	docker push "$(IMAGE_REF)"

validate:
	$(COMMON_SH)
	ensure_image
	docker run --rm "$(IMAGE_NAME)" sh -lc '
	  echo "Python: $$(python --version 2>&1)"
	  echo "jupyterlab: $$(python -c "import jupyterlab; print(jupyterlab.__version__)")"
	  echo "notebook: $$(python -c "import notebook; print(notebook.__version__)")"
	  echo "h11: $$(python -c "import h11; print(h11.__version__)")"
	  echo "urllib3: $$(python -c "import urllib3; print(urllib3.__version__)")"
	  echo "playwright: $$(python -m playwright --version)"
	  echo "chromium dirs: $$(find /home/jovyan/work/.playwright -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l)"
	  echo "nitro-ai-judge: $$(python -m pip show jupyterlab-nitro-ai-judge >/dev/null 2>&1 && echo installed || echo missing)"
	'
	validation_container="$(IMAGE_NAME)-validate"
	validation_container_id=''
	trap 'if [[ -n "$$validation_container_id" ]]; then docker rm -f "$$validation_container_id" >/dev/null 2>&1 || true; else docker rm -f "$$validation_container" >/dev/null 2>&1 || true; fi' EXIT
	docker rm -f "$$validation_container" >/dev/null 2>&1 || true
	validation_container_id="$$(docker run -d --name "$$validation_container" -p 127.0.0.1::8888 "$(IMAGE_NAME)")"
	for _ in $$(seq 1 30); do
	  if ! docker container inspect "$$validation_container_id" >/dev/null 2>&1; then
	    printf '%s\n' 'validation container exited unexpectedly'
	    exit 1
	  fi
	  health_status="$$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$$validation_container_id")"
	  if [[ "$$health_status" == "healthy" ]]; then
	    printf '%s\n' 'healthcheck: healthy'
	    break
	  fi
	  sleep 2
	done
	if [[ "$${health_status:-unknown}" != "healthy" ]]; then
	  docker inspect --format '{{json .State.Health}}' "$$validation_container_id"
	  exit 1
	fi
	if docker scout version >/dev/null 2>&1; then
	  scout_output="$$(mktemp)"
	  docker scout cves "$(IMAGE_NAME)" --only-fixed >"$$scout_output" 2>&1 || true
	  started=0
	  emitted=0
	  while IFS= read -r line; do
	    if [[ $$started -eq 0 ]]; then
	      if [[ ! "$${line}" =~ ^[[:space:]]*(Target|##\ Overview|##\ Packages\ and\ Vulnerabilities) ]]; then
	        continue
	      fi
	      started=1
	    fi
	    if [[ "$${line}" == "What's next:"* ]]; then
	      break
	    fi
	    if [[ -z "$${line}" && $$emitted -eq 0 ]]; then
	      continue
	    fi
	    printf '%s\n' "$${line}"
	    emitted=1
	  done <"$$scout_output"
	  rm -f "$$scout_output"
	elif command -v trivy >/dev/null 2>&1; then
	  trivy image "$(IMAGE_NAME)"
	else
	  printf '%s\n' 'No scanner available. Install Docker Scout or Trivy to scan the image.'
	fi
