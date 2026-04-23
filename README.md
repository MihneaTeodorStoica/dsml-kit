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

Build the image:

```bash
make build
```

Start JupyterLab with Docker Compose:

```bash
make run
```

`make run` creates `token.txt` if it does not already exist, exports that value as `JUPYTER_TOKEN`, and starts `docker compose up --build`.
The container exposes Jupyter on port `8888` by default.

## Compose Configuration

`compose.yaml` currently defines a single `app` service with:

- image `ghcr.io/mihneateodorstoica/dsml-kit:latest`
- container name `dsml`
- build context `.` with `Dockerfile`
- port mapping `8888:8888`
- optional `JUPYTER_TOKEN` passed through from the environment

## GPU Support

The Compose service reserves an NVIDIA GPU device by default:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          capabilities: [gpu]
```

If your machine does not have NVIDIA GPU support configured, you may need to remove or override the GPU reservation before running the stack.

## Make Targets

- `make build`: build the Docker image with `docker compose build`
- `make run`: ensure `token.txt` exists and run `docker compose up --build`
- `make logs`: follow `app` service logs
- `make shell`: open a shell in the running `app` container
- `make stop`: stop the compose services
- `make clean`: run `docker compose down --remove-orphans` and delete `token.txt`
- `make validate`: build and run `docker scout quickview` and `docker scout cves`
- `make publish`: build, tag the image with today's date, and push both the dated tag and `latest` to GHCR
- `make token`: create `token.txt` with a random hex token if missing

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
- The container starts `start-notebook.py` with both `Application` and `ServerApp` log levels set to `CRITICAL`.
- The image is intentionally minimal and centered on notebooks rather than a full application scaffold.
