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

The container exposes Jupyter on port `8888` by default.

## Compose Configuration

`compose.yaml` supports a few environment overrides:

- `IMAGE`: image name, default `docker.io/mihneateodorstoica/dsml-kit`
- `TAG`: image tag, default `latest`
- `CONTAINER`: container name, default `dsml`
- `BUILD_CONTEXT`: build context, default `.`
- `DOCKERFILE`: Dockerfile path, default `Dockerfile`
- `HOST_PORT`: host port, default `8888`
- `CONTAINER_PORT`: container port, default `8888`

Example:

```bash
HOST_PORT=9999 CONTAINER=my-dsml make run
```

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

If your machine does not have NVIDIA GPU support configured, you may need to adjust `compose.yaml` before running the stack.

## Make Targets

- `make build`: build the Docker image with `docker compose build --pull`
- `make run`: start the stack in the background and follow app logs
- `make clean`: stop the stack and remove the configured image tag
- `make validate`: build and run `docker scout` checks
- `make publish`: build, tag with today's date, and push the image

## Installed Packages

Key packages pinned in `requirements.txt`:

- `jupyterlab`
- `notebook`
- `ipython`
- `ipykernel`
- `pyright`
- `python-lsp-server`

## Development Notes

- Dependencies are installed with `mamba` during image build.
- The image is intentionally minimal and centered on notebooks rather than a full application scaffold.
