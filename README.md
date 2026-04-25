# dsml-kit

Containerized DS/ML workspace built on `quay.io/jupyter/minimal-notebook:python-3.11`.
It provides a small JupyterLab-based environment with common notebook packages, `pyright`, and `python-lsp-server`.

## What's Included

- Python 3.11 via the Jupyter minimal notebook image
- JupyterLab and notebook tooling
- IPython and kernel packages
- `pyright` for type checking
- `python-lsp-server` for editor and notebook language features

## Prerequisites

- Docker
- Docker Compose
- NVIDIA Container Toolkit if you want GPU access

## Quick Start

Set `DSML_MODE=image` in `.env` to run the published image without building locally:

```bash
make run
```

`make run` creates `.env` if it does not already exist and generates a `JUPYTER_TOKEN`.
With `DSML_MODE=image`, it starts Docker Compose with the published image from `IMAGE_NAME:DSML_TAG`, which defaults to `ghcr.io/mihneateodorstoica/dsml-kit:latest`.
The container exposes Jupyter on port `8888` by default.

Switch `.env` to local development mode to build and run locally:

```bash
DSML_MODE=dev
make run
```

Use `make pull` to refresh the published image explicitly when `DSML_MODE=image`.

## Compose Configuration

`compose.yaml` is the default user/runtime path and defines a single `app` service that runs the published image.
It reads its settings from `.env`, including:

- `COMPOSE_PROJECT_NAME`
- `CONTAINER_NAME`
- `DSML_MODE`
- `GPU_ENABLED`
- `GPU_DEVICES`
- `NVIDIA_DRIVER_CAPABILITIES`
- `IMAGE_NAME`
- `DSML_TAG`
- `PULL_POLICY`
- `RESTART_POLICY`
- `JUPYTER_BIND_ADDRESS`
- `JUPYTER_PORT`
- `WORKSPACE_DIR`
- `JUPYTER_ROOT_DIR`
- `HOST_UID`
- `HOST_GID`
- `JUPYTER_APP_LOG_LEVEL`
- `JUPYTER_SERVER_LOG_LEVEL`
- `JUPYTER_BASE_URL`
- `JUPYTER_EXTRA_ARGS`
- `JUPYTER_TOKEN`

`compose.gpu.yaml` is included automatically when `GPU_ENABLED=true` and requests NVIDIA GPU access through Docker Compose.

`compose.dev.yaml` is the development override and adds the local Docker build configuration used automatically when `DSML_MODE=dev`.

## Environment File

`.env.example` shows the supported configuration keys. `.env` is ignored by git and is generated automatically by `make run` when missing.

Example:

```dotenv
COMPOSE_PROJECT_NAME=dsml-kit
CONTAINER_NAME=dsml-kit
DSML_MODE=image
GPU_ENABLED=false
GPU_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=all
IMAGE_NAME=ghcr.io/mihneateodorstoica/dsml-kit
DSML_TAG=latest
PULL_POLICY=missing
RESTART_POLICY=unless-stopped
JUPYTER_BIND_ADDRESS=127.0.0.1
JUPYTER_PORT=8888
WORKSPACE_DIR=./workspace
JUPYTER_ROOT_DIR=/home/jovyan/work
HOST_UID=1000
HOST_GID=1000
JUPYTER_APP_LOG_LEVEL=WARN
JUPYTER_SERVER_LOG_LEVEL=WARN
JUPYTER_BASE_URL=/
JUPYTER_EXTRA_ARGS=
JUPYTER_TOKEN=replace-me
```

`WORKSPACE_DIR` is mounted into `JUPYTER_ROOT_DIR`, so notebooks and local files persist on the host. `make run` exports the current host UID/GID so the notebook process can write to that mount.

Set `GPU_ENABLED=true` to enable NVIDIA GPU access. This requires NVIDIA Container Toolkit on the host.

## Make Targets

- `make build`: build locally only when `DSML_MODE=dev`; otherwise it skips local build work
- `make build-dev`: build the local development image via `compose.dev.yaml`
- `make pull`: pull the published image referenced by `.env` when `DSML_MODE=image`
- `make prepare-workspace`: create `WORKSPACE_DIR` and repair write permissions when possible
- `make run`: ensure `.env` exists, then run either published-image or local-dev mode based on `DSML_MODE`
- `make start`: same as `make run`, but detached
- `make run-dev` / `make run-image`: optional aliases that force the mode for one command
- `make logs`: follow `app` service logs
- `make shell`: open a shell in the running `app` container
- `make stop`: stop the compose services
- `make clean`: run `docker compose down --remove-orphans`
- `make clean-all`: run `make clean` and remove the selected local image tag
- `make nuke`: prompt for `Yes, do as I say!`, then delete compose resources and remove the host workspace directory configured by `WORKSPACE_DIR`
- `make test`: build the local validation image and run pytest-based image, Compose, package import, HTTP, UID/GID, and workspace write smoke tests
- `make validate`: run `make test`, then run `docker scout quickview` and `docker scout cves`
- `make freeze`: run `pip freeze` inside the selected image without starting JupyterLab
- `make publish`: build, tag the image with today's date, and push both the dated tag and `latest` to GHCR
- `make env`: create `.env` with a random Jupyter token if missing

## Installed Packages

Key packages pinned in `requirements.txt`:

- `jupyterlab`
- `notebook`
- `ipython`
- `ipykernel`
- `pyright`
- `python-lsp-server`

## Development Notes

- Dependencies are installed from `requirements.txt` with `pip` during image build.
- The image sets Jupyter defaults through environment variables, and `compose.yaml` forwards overrides from `.env`.
- The container includes a basic health check that verifies something is listening on port `8888`; `make test` also verifies the Jupyter HTTP API responds.
- The default runtime path uses `DSML_MODE=image`; set `DSML_MODE=dev` in `.env` to switch `make run` to a local build via `compose.dev.yaml`.
- `latest` is the default user-facing tag, while CI also publishes traceable dated and commit-based tags.
- Pushing a `v*` tag publishes the matching release image; GitHub Releases are created manually.
- The host `WORKSPACE_DIR` bind mount is required so notebooks and outputs persist across container rebuilds or upgrades.
- The image is intentionally minimal and centered on notebooks rather than a full application scaffold.

## Testing

Run the full runtime smoke suite locally:

```bash
make test
```

This validates Compose configuration, builds `dsml-kit:validate`, starts the image directly, checks the Jupyter HTTP API, verifies key package imports, starts the real Compose runtime path, and confirms the mounted workspace is writable as the host UID.

The tests use `pytest`. Install the local test runner dependency when needed:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run the smoke suite plus Docker Scout security checks:

```bash
make validate
```

GitHub validation uses the same pytest suite under `tests/`, and release/refresh publishing is gated on those runtime checks.
