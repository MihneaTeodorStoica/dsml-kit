# AGENTS.md

## Repo Shape

- This repo builds a single Docker image for a JupyterLab notebook environment; there is no app package layout, test suite, or workspace manager.
- The main sources of truth are `Dockerfile`, `requirements.txt`, `Makefile`, and `.github/workflows/*.yml`.

## Core Commands

- `make build`: build or rebuild the local `dsml-kit` image when the computed build hash changes.
- `make validate`: best verification step after image changes. It auto-builds first, checks installed tool versions, validates the runtime healthcheck, and then runs `docker scout quickview` or `trivy image` if available on the host.
- `make run`: start or attach to the long-lived `dsml` container and print the local Jupyter URL.
- `make run NO_GPU=1`: same as above, but omits `--gpus all`.
- `make shell`: open `bash -il` in the `dsml` container, creating or restarting it if needed.
- `make clean`: remove the persistent `dsml` container.
- `make publish IMAGE_REF=image:tag`: tag and push the local image; the default target is `docker.io/mihneateodorstoica/dsml-kit:latest`.

## Makefile Behavior That Is Easy To Miss

- The Makefile executes Docker operations from the repo root before building or running containers.
- `make build` rebuilds automatically when the computed build hash changes. The hash includes `Dockerfile`, `.dockerignore`, `config/bashrc`, `requirements.txt`, `Makefile`, `BASE_IMAGE`, and the resolved image ID for the pinned base image.
- `make run` and `make shell` reuse a fixed container name, `dsml`. If that container exists but was created from an older image ID, the Makefile deletes and recreates it.
- `make run` and `make shell` default to GPU mode via `--gpus all`; use `NO_GPU=1` on hosts without GPU runtime support.

## Image Contents

- `requirements.txt` currently adds exactly one extra Python package: `jupyterlab-nitro-ai-judge`.
- The Docker image also installs JupyterLab, Notebook, Playwright, Chromium, and a custom Node binary for Playwright's driver.
- The container runs as non-root user `jovyan` with working directory `/home/jovyan/work`.

## CI / Release Notes

- CI validates and publishes the Docker image; there is no separate lint/typecheck/test workflow.
- `.github/workflows/docker-publish.yml` pushes on `main`, Git tags matching `v*`, a weekly Monday schedule, and manual dispatch.
- `.github/workflows/validate.yml` runs `make validate` on pull requests and pushes to `main`.
- Published tags come from Docker metadata action: `latest` on the default branch, the Git tag name for tag builds, and a `YYYY-MM-DD` date tag.

## Working Guidance

- For Dockerfile or dependency edits, prefer `make validate` over ad hoc `docker build` commands so you exercise the same rebuild and runtime checks used in local development and CI.
- Do not assume `docker run` is ephemeral in this repo; the intended local workflow centers on the persistent `dsml` container.
