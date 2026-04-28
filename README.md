# dsml-kit

Profile-based ML workspaces with Docker + uv.

```bash
uv tool install dsml-kit
mkdir my-project
cd my-project
dsml init --profile minimal
dsml up
```

`dsml-kit` installs the `dsml` command. `dsml` manages a Dockerized JupyterLab workspace, mounts your project into the container, and uses uv for fast Python installs inside the runtime. Profiles give you curated environments while Docker keeps the notebook environment isolated and reproducible.

## Installation

Install the CLI with uv:

```bash
uv tool install dsml-kit
```

For local development from this repository:

```bash
uv sync
uv run dsml --help
```

Docker is required to run workspaces. GPU profiles require NVIDIA drivers plus NVIDIA Container Toolkit.

## Quick Start

```bash
mkdir my-project
cd my-project
dsml init --profile minimal
dsml up
```

`dsml init` creates `dsml.toml`. `dsml up` starts a container, mounts `./workspace/` at `/home/jovyan/work`, creates a persistent Docker volume for `/home/jovyan`, and prints the JupyterLab URL.

## Profiles

Profiles live in `profiles/*.toml`:

- `minimal`: small JupyterLab data science workspace
- `gpu`: GPU-ready ML workspace
- `full`: batteries-included DS/ML workspace
- `dev`: local development image for dsml-kit maintainers

List profiles:

```bash
dsml profiles
```

During early development the profiles may point at the same image tag; the CLI already supports separate profile images.

## Daily Usage

```bash
dsml up
dsml logs --follow
dsml shell
dsml stop
dsml down
```

Useful options:

```bash
dsml up --attach
dsml up --pull
dsml up --dev --build
```

## Configuration

`dsml.toml` is the workspace config file created by `dsml init`. It is safe to edit by hand.

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

`[workspace]` controls the Docker workspace:

- `profile`: bundled profile name, currently `minimal`, `gpu`, `full`, or `dev`
- `mount`: host path mounted into the container, relative to `dsml.toml`
- `port`: host port mapped to container port `8888`
- `bind_address`: host interface for Jupyter, usually `127.0.0.1`
- `container_name`: Docker container name, or `auto` for a project-derived name
- `home_volume`: Docker volume mounted at `/home/jovyan`, or `auto`
- `gpu`: `auto`, `true`, or `false`
- `image`: Docker image used by `dsml up`
- `jupyter_token`: Jupyter token, or `auto` to generate one at startup

`[jupyter]` controls the server inside the container:

- `root_dir`: container path Jupyter opens, normally `/home/jovyan/work`
- `base_url`: URL prefix, normally `/`
- `app_log_level` and `server_log_level`: Jupyter log levels
- `extra_args`: additional `start-notebook.py` arguments

`[packages]` records project-specific Python additions:

- `extra`: package specifiers installed by `dsml sync` or `dsml add`

## Adding Packages

Add packages to `[packages].extra` in `dsml.toml`:

```bash
dsml add polars optuna
```

If the container is running, `dsml add` also runs:

```bash
uv pip install --system polars optuna
```

Install everything listed in `dsml.toml` into a running container:

```bash
dsml sync
```

Heavy ML and notebook packages belong in `images/base/requirements.txt`, not in the Python CLI dependencies.

## GPU Usage

Create a GPU workspace:

```bash
dsml init --profile gpu --gpu true
dsml up
```

The CLI adds Docker GPU flags when GPU mode resolves to true. Run diagnostics if GPU startup fails:

```bash
dsml doctor
```

## Developer Commands

```bash
uv run pytest
uv run dsml image build
uv run dsml image freeze dsml-kit:latest
uv run dsml dev validate
```

Build the validation image directly:

```bash
docker build -f images/base/Dockerfile -t dsml-kit:validate .
DSML_TEST_IMAGE=dsml-kit:validate uv run pytest tests/integration
```

## Runtime Image

The runtime image is built from `images/base/Dockerfile` and installs pinned notebook/data packages from `images/base/requirements.txt` using uv.

The image keeps the useful runtime contract from the original project:

- Jupyter minimal-notebook base image
- JupyterLab startup through `start-notebook.py`
- `./workspace/` mounted at `/home/jovyan/work`
- `/home/jovyan` backed by a persistent Docker volume
- `JUPYTER_TOKEN` support
- host UID/GID support through `NB_UID` and `NB_GID`
- healthcheck on port `8888`

## Troubleshooting

Run:

```bash
dsml doctor
```

It checks Docker, the daemon, `dsml.toml`, the selected profile, the configured port, the selected image, and GPU prerequisites when requested.

Cleanup commands:

```bash
dsml clean
dsml clean --image
dsml clean --volumes
dsml nuke
```

`dsml nuke` requires typing `DELETE` before it removes the project container and persistent home volume.
