# AGENTS.md

## Scope

- This repo is a single-image Docker workspace, not a Python package or monorepo. The main artifacts are `Dockerfile`, `compose.yaml`, `requirements.txt`, and the `Makefile` targets that drive them.

## Source Of Truth

- Trust `Dockerfile` over `README.md` for dependency installation details: the image currently installs `requirements.txt` with `pip`, not `mamba`.
- Trust `Dockerfile` and `Makefile` together for runtime behavior: the container command runs `start-notebook.py` with log levels forced to `CRITICAL`, and `make run` injects `JUPYTER_TOKEN` from `token.txt` before starting `docker compose up --build`.

## Commands

- Build the image with `make build` (`docker compose build`).
- Run the workspace with `make run`. This ensures `token.txt` exists, exports that value as `JUPYTER_TOKEN`, and runs `docker compose up --build` in the foreground.
- Stop and remove local artifacts with `make clean`.
- Local image validation is `make validate`, which first builds and then runs `docker scout quickview` and `docker scout cves`. This is heavier than CI and requires Docker Scout locally.
- Publish manually with `make publish`. It tags `ghcr.io/mihneateodorstoica/dsml-kit` with today's date and pushes both the dated tag and `latest`.

## CI / Verification

- CI in `.github/workflows/validate.yml` only verifies that the image builds with `docker/build-push-action`; it does not run `docker scout`.
- Release publishing in `.github/workflows/docker-publish.yml` pushes to GHCR (`ghcr.io/<repo>`) with tags from default-branch `latest`, Git tags, and the current date.

## Runtime Gotchas

- `compose.yaml` reserves an NVIDIA GPU by default via `deploy.resources.reservations.devices`. On machines without NVIDIA Container Toolkit or GPU access, expect `make run` / `docker compose up` to need a local compose edit or override.
- The current compose file hardcodes image `ghcr.io/mihneateodorstoica/dsml-kit:latest`, container name `dsml`, and port mapping `8888:8888`; those are not parameterized through compose environment substitutions today.
- `make run` depends on `openssl` to generate `token.txt` when it is missing.

## Dependencies

- Python version intent is `3.11` from the base image `quay.io/jupyter/minimal-notebook:python-3.11`; `.python-version` is `3.11.10`.
- Notebook and editor tooling is pinned in `requirements.txt`; update that file when changing the container toolchain.
