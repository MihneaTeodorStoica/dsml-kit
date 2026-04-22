# dsml-kit

`dsml-kit` builds a Docker image for a JupyterLab-based data science and machine learning workspace.

The repo is intentionally small: the main sources of truth are `Dockerfile`, `requirements.txt`, and `Makefile`.

## What It Includes

- Python 3.11 on Debian Bookworm slim
- JupyterLab and Notebook
- Playwright with Chromium installed in the image
- A custom Node binary installed for Playwright's driver
- The extra Python package from `requirements.txt`: `jupyterlab-nitro-ai-judge`
- A non-root `jovyan` user with working directory `/home/jovyan/work`

The container exposes JupyterLab on port `8888`.

## Requirements

- Docker
- NVIDIA Container Toolkit if you want to use the default GPU-enabled run flow

## Quick Start

Build the image:

```bash
make build
```

Start or attach to the long-lived `dsml` container:

```bash
make run
```

If your host does not support `--gpus all`, run:

```bash
make run NO_GPU=1
```

Open JupyterLab at `http://127.0.0.1:8888`.

## Common Commands

Build or rebuild the local image:

```bash
make build
```

Validate the image contents and optionally run an image scanner if available:

```bash
make validate
```

Open an interactive shell inside the `dsml` container:

```bash
make shell
```

Remove the persistent `dsml` container:

```bash
make clean
```

Tag and push the local image to Docker Hub, or to a custom image reference:

```bash
make publish
make publish IMAGE_REF=docker.io/your-name/dsml-kit:tag
```

List the available targets:

```bash
make help
```

## How The Makefile Works

- The Makefile switches to the repo root before building or running Docker commands.
- The local image name is always `dsml-kit`.
- `make run` and `make shell` reuse a fixed container name: `dsml`.
- If the existing `dsml` container was created from an older image ID, the Makefile deletes and recreates it.
- `make build` only rebuilds when the computed build hash changes.

The build hash includes:

- `Dockerfile`
- `.dockerignore`
- `config/bashrc`
- `requirements.txt`
- `Makefile`
- `BASE_IMAGE`
- The resolved image ID for the pinned base image

## Modernization Notes

- The base image is pinned by digest for reproducible rebuilds.
- Direct Python dependencies are pinned to exact versions.
- The image now includes a Docker `HEALTHCHECK`.
- The Playwright Node download is checksum-verified before replacing the bundled driver binary.
- CI publishes SBOM and provenance attestations for pushed images.

## Publishing

GitHub Actions publishes `docker.io/mihneateodorstoica/dsml-kit` on:

- Pushes to `main`
- Git tags matching `v*`
- A weekly Monday schedule
- Manual workflow dispatch

Published tags include:

- `latest` on the default branch
- The Git tag name for tag builds
- A date tag in `YYYY-MM-DD` format

Pull requests are validated separately with `make validate` before merge.
