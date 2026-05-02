# AGENTS.md

## Repo Shape

- This is an installable Python CLI package that manages Dockerized JupyterLab DS/ML workspaces.
- The `dsml` command is the product interface; do not reintroduce Makefile or Compose as the primary UX.
- The Docker image remains the actual notebook/runtime environment and is built from `images/base/Dockerfile`.
- Runtime image packages live in `images/base/requirements-*.txt`; do not put heavy ML/Jupyter dependencies in `pyproject.toml`.
- User workspace config is `dsml.yml`; `.env` is not a user-facing config path.

## Source Of Truth

- `pyproject.toml`: Python package metadata, CLI dependencies, and dev test dependencies.
- `src/dsml/cli.py`: Typer command definitions and user-facing wiring only.
- `src/dsml/config.py`: reading, writing, validating, and updating `dsml.yml`.
- `src/dsml/profiles.py` and `profiles/*.yml`: bundled profile metadata.
- `src/dsml/docker.py`: Docker command construction and subprocess helpers.
- `src/dsml/runtime.py`: high-level workspace operations.
- `src/dsml/doctor.py`: diagnostics.
- `src/dsml/images.py`: maintainer image operations.
- `images/base/requirements-*.txt`: container runtime packages for each image variant.

## Commands

- Install/sync development dependencies with `uv sync`.
- CLI smoke check: `uv run dsml --help`.
- Generate config check: `uv run dsml init --profile minimal --force`.
- Unit tests: `uv run pytest tests/unit`.
- Full tests after a validation image exists: `DSML_TEST_IMAGE=dsml-kit:validate uv run pytest`.
- Build validation image: `docker build -f images/base/Dockerfile --build-arg DSML_REQUIREMENTS=requirements-full.txt -t dsml-kit:validate .`.
- Maintainer validation: `uv run dsml dev validate`.

## Versioning

- Use semantic versions in the form `X.Y.Z`.
- Increment `X` for breaking changes, including backwards-incompatible CLI, config, profile, runtime, or packaging behavior.
- Increment `Y` for backwards-compatible features or behavior changes.
- Increment `Z` for bug fixes, documentation-only release fixes, dependency maintenance, or other backwards-compatible patch work.
- Keep `pyproject.toml` as the package version source of truth. Release tags must be named `vX.Y.Z` and must match the package version at the tagged commit.
- Publish only after validation has passed, from matching `v*` tags that are signed and GitHub-verified.

## Architecture Rules

- Keep Docker command construction out of `cli.py`; make command builders testable without Docker.
- Keep unit tests Docker-free when possible.
- Put real container startup, Jupyter HTTP checks, and import-contract tests under `tests/integration`.
- Update `tests/integration/test_import_contract.py` and any duplicate import contract together when changing key image packages.
- Do not add CLI dependencies to `images/base/requirements-*.txt`.
- Do not add image/runtime dependencies such as numpy, pandas, torch, JupyterLab, scikit-learn, matplotlib, or CUDA packages to `pyproject.toml`.

## Runtime Gotchas

- `dsml up` uses Docker directly, not Compose.
- Host workspace files are mounted from `./workspace/` into `/home/jovyan/work` by default.
- `/home/jovyan` is backed by a Docker volume generated from the project path unless configured explicitly.
- Container names are generated from the project path unless configured explicitly.
- Host UID/GID are passed through `NB_UID` and `NB_GID` so files written from Jupyter are owned by the host user.
- `dsml nuke` is intentionally interactive and requires the exact confirmation phrase `DELETE`.

## Image/Build Notes

- `.dockerignore` excludes local runtime state, notebooks, bytecode, and GitHub metadata from Docker builds.
- The image healthcheck verifies port `8888` accepts TCP connections; pytest adds the stronger Jupyter HTTP API check.
- Publishing paths are GitHub Actions only: release and refresh workflows publish GHCR tags after package and image validation; `pypi-publish.yml` publishes the Python package to PyPI from matching `v*` tags.
