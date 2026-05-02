# dsml-kit

Profile-based Dockerized JupyterLab workspaces for data science and machine
learning.

`dsml-kit` installs the `dsml` command. `dsml` manages a workspace from a
project-local `dsml.yml`, prepares the runtime image, writes generated Docker
Compose state, mounts your project files into JupyterLab, and keeps
notebook/runtime dependencies out of your host Python environment.

```bash
uv tool install dsml-kit
mkdir my-project
cd my-project
dsml init --profile minimal
dsml up
```

`dsml up` prints the JupyterLab URL when the workspace is ready.

## What You Get

- A simple `dsml` CLI as the product interface.
- Project-local configuration in `dsml.yml`, not `.env`.
- Curated profiles for minimal, base, extended, full, GPU runtime, and maintainer development workspaces.
- A Docker runtime image built from `images/base/Dockerfile`.
- Generated Compose state under `.dsml/`.
- `./workspace/` mounted into the container at `/home/jovyan/work` by default.
- A persistent Docker volume for `/home/jovyan`.
- Host UID/GID passthrough so files written from Jupyter belong to your user.
- `uv` inside the container for fast package installs with `dsml add` and
  `dsml sync`.

## Prerequisites

- Python 3.11 or newer for the CLI.
- Docker Desktop or Docker Engine.
- Docker Compose v2, available as `docker compose`.
- For GPU workspaces: NVIDIA drivers and NVIDIA Container Toolkit.

Check your setup with:

```bash
dsml doctor
```

## Installation

### uv

```bash
uv tool install dsml-kit
dsml --help
```

Upgrade later with:

```bash
uv tool upgrade dsml-kit
```

### pip

```bash
python -m pip install --user dsml-kit
dsml --help
```

Make sure your Python user scripts directory is on `PATH`. If it is not, you can
still run the CLI with:

```bash
python -m dsml --help
```

Or install into a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install dsml-kit
dsml --help
```

### From GitHub

```bash
uv tool install git+https://github.com/MihneaTeodorStoica/dsml-kit
```

or:

```bash
python -m pip install git+https://github.com/MihneaTeodorStoica/dsml-kit
```

### Local Development

With uv:

```bash
git clone https://github.com/MihneaTeodorStoica/dsml-kit
cd dsml-kit
uv sync
uv run dsml --help
uv run dsml --version
```

With pip and a virtual environment:

```bash
git clone https://github.com/MihneaTeodorStoica/dsml-kit
cd dsml-kit
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
dsml --help
```

### Development in VS Code Dev Containers

This repository includes a VS Code Dev Container for maintaining `dsml-kit`.
It provides Python 3.11, `uv`, the Docker CLI, and the Docker Compose plugin.
Docker Desktop or Docker Engine must be running on the host because the
container uses the host Docker socket.

1. Install the VS Code Dev Containers extension.
2. Open this repository in VS Code.
3. Run `Dev Containers: Reopen in Container`.
4. Wait for the post-create step to finish; it runs `uv sync`.

Then check the development workflow:

```bash
uv run dsml --help
uv run pytest tests/unit
docker compose version
```

## Quick Start

Create a project and initialize a workspace:

```bash
mkdir my-project
cd my-project
dsml init --profile minimal
```

`dsml init` writes `dsml.yml` in the current directory. Useful options:

```bash
dsml init --profile full
dsml init --profile gpu --gpu true
dsml init --profile minimal --port 8899
dsml init --profile minimal --image ghcr.io/mihneateodorstoica/dsml-kit:minimal
dsml init --profile minimal --force
```

Start JupyterLab:

```bash
dsml up
```

On first start, `dsml up` prepares the runtime image, creates the workspace
mount if needed, writes `.dsml/compose.yaml`, starts the Compose service, waits
for JupyterLab, and prints a URL such as:

```text
http://127.0.0.1:8888/?token=...
```

Open the URL again later:

```bash
dsml open
```

## Daily Workflow

```bash
dsml up
dsml logs --follow
dsml shell
dsml status
dsml restart
dsml stop
dsml down
```

Common command behavior:

- `dsml up` starts the workspace in the background.
- `dsml up --attach` starts and attaches to the container.
- `dsml logs --follow` streams JupyterLab logs.
- `dsml shell` opens `/bin/bash` in the running container as `jovyan`.
- `dsml restart` stops and starts the workspace again.
- `dsml stop` stops the current Compose service.
- `dsml down` is currently the same as `dsml stop`.

The supported interface is the `dsml` command. Runtime state such as
`.dsml/compose.yaml` is generated from `dsml.yml` and should not be edited by
hand.

## Profiles

List bundled profiles:

```bash
dsml profiles
```

Available profiles:

- `minimal`: small JupyterLab workspace.
- `base`: core numeric Python workspace with common data science packages.
- `extended`: broader analytics workspace with columnar, plotting, and stats packages.
- `full`: batteries-included workspace with editor and language tooling.
- `gpu`: full workspace image with GPU access requested at runtime.
- `dev`: local development image for dsml-kit maintainers.

Profiles choose the default runtime image and GPU behavior. GPU is a runtime
setting, not a separate image variant. You can still
override individual settings in `dsml.yml`.

## Images And Builds

For normal project use, `dsml up` uses the image configured in `dsml.yml`.
With the default `image_policy: auto`, it pulls missing published images and
builds the local development image when the selected image is `dsml-kit:dev`.

Force an image pull for one run:

```bash
dsml up --pull
```

Force an image build for one run:

```bash
dsml up --build
```

Other useful runtime options:

```bash
dsml up --recreate
dsml up --no-wait
dsml up --wait-timeout 60
dsml up --dev --build
dsml logs --since 10m --timestamps
dsml shell --root
```

The `--pull` and `--build` flags override the image policy in `dsml.yml` for a single run. `--recreate` forwards to Docker Compose service recreation, and `--no-wait` skips the Jupyter readiness probe when you want the command to return immediately.

For debugging, inspect the generated Compose file:

```bash
cat .dsml/compose.yaml
dsml compose path
dsml compose config
dsml compose ps
```

Build the runtime image from this repository:

```bash
uv run dsml image build --tag dsml-kit:latest
```

Build a custom image from a project-local Dockerfile:

```bash
dsml image build --tag my-dsml:local --context docker --dockerfile Dockerfile --target prod --build-arg PYTHON_VERSION=3.12
```

Build one of the bundled dependency variants locally:

```bash
dsml image build --tag dsml-kit:minimal --variant minimal
dsml image build --tag dsml-kit:base --variant base
dsml image build --tag dsml-kit:extended --variant extended
dsml image build --tag dsml-kit:full --variant full
```

The default Dockerfile is intentionally configurable with build args:

- `PYTHON_VERSION`: `3.10`, `3.11`, or `3.12`
- `UV_VERSION`: uv image tag used for the copied `uv` binary
- `DSML_REQUIREMENTS`: one of the `requirements-*.txt` files
- `DSML_EXTRA_APT_PACKAGES`: optional space-separated apt packages

Build and use the maintainer development image:

```bash
uv run dsml image build --dev
uv run dsml up --dev --build
```

Watch the runtime image source and rebuild the running service when
`images/base/` or `.dockerignore` changes:

```bash
uv run dsml watch --dev
```

When a workspace is configured for local runtime image builds, `dsml up --attach`
also writes the Compose Watch configuration so Docker Compose's attached
`w Enable Watch` shortcut can start watching.

Compose Watch requires Docker Compose 2.22 or newer. The command is intended
for local runtime image development; normal notebook projects should keep using
`dsml up`.

Other image helpers:

```bash
dsml image pull
dsml image pull ghcr.io/mihneateodorstoica/dsml-kit:minimal
dsml image freeze
dsml image remove
```

Use image builds when you are developing the runtime image from a source
checkout. Project-specific Python packages usually belong in `dsml.yml` via
`dsml add`; reusable notebook/runtime packages belong in
`images/base/requirements-*.txt`.

The published image variants are built from the same Dockerfile with different
requirements files:

- `minimal`: `images/base/requirements-minimal.txt`
- `base`: `images/base/requirements-base.txt`
- `extended`: `images/base/requirements-extended.txt`
- `full`: `images/base/requirements-full.txt`

## Configuration

`dsml.yml` is the workspace config file. It is safe to edit by hand.

```yaml
runtime:
  backend: compose

workspace:
  profile: minimal
  mount: ./workspace
  port: 8888
  bind_address: 127.0.0.1
  container_name: auto
  home_volume: auto
  gpu: auto
  image: ghcr.io/mihneateodorstoica/dsml-kit:minimal
  image_policy: auto
  jupyter_token: auto

image_build:
  context: .
  dockerfile: images/base/Dockerfile
  target: ""
  args:
    PYTHON_VERSION: "3.11"
    DSML_REQUIREMENTS: requirements-minimal.txt
  watch:
    - images/base
    - .dockerignore

jupyter:
  root_dir: /home/jovyan/work
  base_url: /
  app_log_level: WARN
  server_log_level: WARN
  extra_args: []

packages:
  extra: []
```

`runtime` selects the workspace backend:

- `backend`: currently `compose`; `dsml` generates and manages Docker Compose from `dsml.yml`

Important settings:

- `profile`: bundled profile name, such as `minimal`, `base`, `extended`, `full`, `gpu`, or `dev`.
- `mount`: host path mounted into the container, relative to `dsml.yml`.
- `port` and `bind_address`: where JupyterLab is exposed on the host.
- `container_name`: Docker container name, or `auto` for a project-derived name.
- `home_volume`: Docker volume mounted at `/home/jovyan`, or `auto`.
- `gpu`: `auto`, `true`, or `false`.
- `image`: runtime image used by `dsml up`.
- `image_policy`: `auto`, `pull`, `build`, or `never`.
- `image_build`: Docker build context, Dockerfile, optional target, build args, and watch paths used by `image_policy: build`, `dsml up --build`, and `dsml watch`.
- `jupyter_token`: a fixed token or `auto`.
- `extra_args`: additional `start-notebook.py` arguments.
- `packages.extra`: packages installed by `dsml add` or `dsml sync`.

Image policy behavior:

- `auto`: pull missing published images; build the local dev image.
- `pull`: pull before each start.
- `build`: build before each start.
- `never`: require the image to already exist locally.

## Adding Packages

Add project-specific packages to `dsml.yml`:

```bash
dsml add polars optuna
dsml add "scikit-learn>=1.5"
dsml add -r requirements.txt
```

If the container is running, `dsml add` also installs the packages immediately
inside the container with `uv pip install --system`.

Install everything already listed in `packages.extra` into a running
container:

```bash
dsml sync
```

Requirement files may contain package specifiers and nested `-r other.txt`
includes. General pip options such as `--extra-index-url` are intentionally not
copied into `dsml.yml`.

Keep the dependency split clear:

- CLI dependencies live in `pyproject.toml`.
- Runtime notebook/data packages live in `images/base/requirements-*.txt`.
- Project-specific additions live in `packages.extra`.

## GPU Workspaces

Create a GPU workspace:

```bash
dsml init --profile gpu --gpu true
dsml up
```

`gpu: auto` uses the profile default. The `gpu` profile uses the full image and
requests NVIDIA GPU access at runtime; the `minimal` profile does not.

If GPU startup fails, run:

```bash
dsml doctor
```

It checks Docker, Docker Compose v2, the daemon, `dsml.yml`, the selected
profile, the configured port, the selected image, and NVIDIA prerequisites when
GPU mode is enabled.

## Cleanup

Stop the workspace:

```bash
dsml stop
```

Remove the project Compose service and container:

```bash
dsml clean
```

Also remove the selected image or persistent home volume:

```bash
dsml clean --image
dsml clean --volumes
```

Remove the project Compose service and home volume after an explicit
confirmation:

```bash
dsml nuke
```

`dsml nuke` asks you to type `DELETE` before it removes the project runtime and
persistent home volume.

## Maintainer Commands

Install development dependencies:

```bash
uv sync
```

Or, without uv:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the CLI from the checkout:

```bash
uv run dsml --help
```

Run unit tests:

```bash
uv run pytest tests/unit
```

Build the validation image and run integration tests:

```bash
docker build -f images/base/Dockerfile --build-arg DSML_REQUIREMENTS=requirements-full.txt -t dsml-kit:validate .
DSML_TEST_IMAGE=dsml-kit:validate uv run pytest tests/integration
```

Or use the maintainer validation command:

```bash
uv run dsml dev validate
```

Useful maintainer image commands:

```bash
uv run dsml image build --tag dsml-kit:latest
uv run dsml image freeze dsml-kit:latest
uv run dsml image remove dsml-kit:latest
```

## Runtime Backend

The CLI lifecycle is routed through a runtime backend layer. The default and only supported backend is `compose`, which writes `.dsml/compose.yaml` from `dsml.yml` and then calls Docker Compose v2 for `up`, `watch`, `stop`, `logs`, `exec`, `down`, status checks, and debug config rendering.

This keeps the product interface as `dsml` while making the actual workspace lifecycle a normal Compose project under the hood. Dockerfiles still define the runtime image; `dsml.yml` remains the source of truth for workspace settings.

## Troubleshooting

Start with:

```bash
dsml doctor
```

Then check the usual suspects:

- Docker is installed and the daemon is running.
- `docker compose version` works.
- The configured port is free.
- The image exists locally or can be pulled.
- GPU machines have working NVIDIA drivers and container toolkit.
- The workspace mount path is writable.

For live debugging:

```bash
dsml logs --follow
dsml shell
cat dsml.yml
```
