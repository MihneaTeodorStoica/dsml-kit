# AGENTS.md

## Scope

- This repo is a single-image Docker workspace, not a Python package or monorepo. The main artifacts are `Dockerfile`, `compose.yaml`, `requirements.txt`, and the `Makefile` targets that drive them.

## Source Of Truth

- Trust `Dockerfile` over `README.md` for dependency installation details: the image currently installs `requirements.txt` with `pip`, not `mamba`.
- Trust `compose.yaml` for runtime behavior: `make run` starts the `app` service defined there and runs `start-notebook.py` with log levels forced to `CRITICAL`.

## Commands

- Build the image with `make build` (`docker compose build --pull`).
- Run the workspace with `make run`. This does `docker compose up --build -d`, clears the terminal, then attaches to `docker compose logs -f app`.
- Stop and remove local artifacts with `make clean`.
- Local image validation is `make validate`, which first builds and then runs `docker scout quickview` and `docker scout cves`. This is heavier than CI and requires Docker Scout locally.
- Publish manually with `make publish`. It tags `ghcr.io/mihneateodorstoica/dsml-kit` with today's date and `latest`, then pushes both.

## CI / Verification

- CI in `.github/workflows/validate.yml` only verifies that the image builds with `docker/build-push-action`; it does not run `docker scout`.
- Release publishing in `.github/workflows/docker-publish.yml` pushes to GHCR (`ghcr.io/<repo>`) with tags from default-branch `latest`, Git tags, and the current date.

## Runtime Gotchas

- `compose.yaml` reserves an NVIDIA GPU by default via `deploy.resources.reservations.devices`. On machines without NVIDIA Container Toolkit or GPU access, expect `make run` / `docker compose up` to need a local compose edit or override.
- The container port mapping defaults to `8888:8888`, but `IMAGE`, `TAG`, `CONTAINER`, `BUILD_CONTEXT`, `DOCKERFILE`, `HOST_PORT`, and `CONTAINER_PORT` are all overridable through environment variables.

## Dependencies

- Python version intent is `3.11` from the base image `quay.io/jupyter/minimal-notebook:python-3.11`; `.python-version` is `3.11.10`.
- Notebook and editor tooling is pinned in `requirements.txt`; update that file when changing the container toolchain.
