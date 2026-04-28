# dsml-kit

Profile-based Dockerized JupyterLab workspaces for data science and machine
learning.

`dsml-kit` installs the `dsml` command. `dsml` manages a workspace from a
project-local `dsml.toml`, prepares the runtime image, writes generated Docker
Compose state, mounts your project files into JupyterLab, and keeps
notebook/runtime dependencies out of your host Python environment.

```bash
pipx install dsml-kit
mkdir my-project
cd my-project
dsml init --profile minimal
dsml up
```

`dsml up` prints the JupyterLab URL when the workspace is ready.

## What You Get

- A simple `dsml` CLI as the product interface.
- Project-local configuration in `dsml.toml`, not `.env`.
- Curated profiles for minimal, full, GPU, and maintainer development workspaces.
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

Choose the installation style that matches how you manage Python CLI tools.

### uv

```bash
uv tool install dsml-kit
dsml --help
```

Upgrade later with:

```bash
uv tool upgrade dsml-kit
```

### pipx

```bash
pipx install dsml-kit
dsml --help
```

Upgrade later with:

```bash
pipx upgrade dsml-kit
```

### pip User Install

```bash
python -m pip install --user dsml-kit
dsml --help
```

Make sure your Python user scripts directory is on `PATH`. If it is not, you can
still run the CLI with:

```bash
python -m dsml --help
```

### Virtual Environment

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
pipx install git+https://github.com/MihneaTeodorStoica/dsml-kit
```

### Local Development

With uv:

```bash
git clone https://github.com/MihneaTeodorStoica/dsml-kit
cd dsml-kit
uv sync
uv run dsml --help
```

With pip and a virtual environment:

```bash
git clone https://github.com/MihneaTeodorStoica/dsml-kit
cd dsml-kit
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
dsml --help
```

## Quick Start

Create a project and initialize a workspace:

```bash
mkdir my-project
cd my-project
dsml init --profile minimal
```

`dsml init` writes `dsml.toml` in the current directory. Useful options:

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
`.dsml/compose.yaml` is generated from `dsml.toml` and should not be edited by
hand.

## Profiles

List bundled profiles:

```bash
dsml profiles
```

Available profiles:

- `minimal`: small JupyterLab data science workspace.
- `full`: batteries-included DS/ML workspace.
- `gpu`: GPU-ready ML workspace.
- `dev`: local development image for dsml-kit maintainers.

Profiles choose the default runtime image and GPU behavior. You can still
override individual settings in `dsml.toml`.

## Images And Builds

For normal project use, `dsml up` uses the image configured in `dsml.toml`.
With the default `image_policy = "auto"`, it pulls missing published images and
builds the local development image when the selected image is `dsml-kit:dev`.

Force an image pull for one run:

```bash
dsml up --pull
```

Force an image build for one run:

```bash
dsml up --build
```

Build the runtime image from this repository:

```bash
uv run dsml image build --tag dsml-kit:latest
```

Build and use the maintainer development image:

```bash
uv run dsml image build --dev
uv run dsml up --dev --build
```

Other image helpers:

```bash
dsml image pull
dsml image pull ghcr.io/mihneateodorstoica/dsml-kit:minimal
dsml image freeze
dsml image remove
```

Use image builds when you are developing the runtime image from a source
checkout. Project-specific Python packages usually belong in `dsml.toml` via
`dsml add`; reusable notebook/runtime packages belong in
`images/base/requirements.txt`.

## Configuration

`dsml.toml` is the workspace config file. It is safe to edit by hand.

```toml
[workspace]
profile = "minimal"
mount = "./workspace"
port = 8888
bind_address = "127.0.0.1"
container_name = "auto"
home_volume = "auto"
gpu = "auto"
image = "ghcr.io/mihneateodorstoica/dsml-kit:minimal"
image_policy = "auto"
jupyter_token = "auto"

[jupyter]
root_dir = "/home/jovyan/work"
base_url = "/"
app_log_level = "WARN"
server_log_level = "WARN"
extra_args = []

[packages]
extra = []
```

Important settings:

- `profile`: bundled profile name, such as `minimal`, `full`, `gpu`, or `dev`.
- `mount`: host path mounted into the container, relative to `dsml.toml`.
- `port` and `bind_address`: where JupyterLab is exposed on the host.
- `container_name`: Docker container name, or `auto` for a project-derived name.
- `home_volume`: Docker volume mounted at `/home/jovyan`, or `auto`.
- `gpu`: `auto`, `true`, or `false`.
- `image`: runtime image used by `dsml up`.
- `image_policy`: `auto`, `pull`, `build`, or `never`.
- `jupyter_token`: a fixed token or `auto`.
- `extra_args`: additional `start-notebook.py` arguments.
- `[packages].extra`: packages installed by `dsml add` or `dsml sync`.

Image policy behavior:

- `auto`: pull missing published images; build the local dev image.
- `pull`: pull before each start.
- `build`: build before each start.
- `never`: require the image to already exist locally.

## Adding Packages

Add project-specific packages to `dsml.toml`:

```bash
dsml add polars optuna
dsml add "scikit-learn>=1.5"
dsml add -r requirements.txt
```

If the container is running, `dsml add` also installs the packages immediately
inside the container with `uv pip install --system`.

Install everything already listed in `[packages].extra` into a running
container:

```bash
dsml sync
```

Requirement files may contain package specifiers and nested `-r other.txt`
includes. General pip options such as `--extra-index-url` are intentionally not
copied into `dsml.toml`.

Keep the dependency split clear:

- CLI dependencies live in `pyproject.toml`.
- Runtime notebook/data packages live in `images/base/requirements.txt`.
- Project-specific additions live in `[packages].extra`.

## GPU Workspaces

Create a GPU workspace:

```bash
dsml init --profile gpu --gpu true
dsml up
```

`gpu = "auto"` uses the profile default. The `gpu` profile requests NVIDIA GPU
access; the `minimal` profile does not.

If GPU startup fails, run:

```bash
dsml doctor
```

It checks Docker, Docker Compose v2, the daemon, `dsml.toml`, the selected
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
python -m pip install -r requirements.txt
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
docker build -f images/base/Dockerfile -t dsml-kit:validate .
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
cat dsml.toml
```
