# Contributing

Thanks for helping improve dsml-kit. This project is a Python CLI that manages Dockerized JupyterLab data science workspaces, so changes usually touch either the CLI package, the generated workspace configuration, or the runtime Docker image.

## Development Setup

Install the development environment with uv:

```bash
uv sync
```

Run the CLI from the checkout:

```bash
uv run dsml --help
```

## Validation

Run unit tests before opening a PR:

```bash
uv run pytest tests/unit
```

For changes that affect Docker startup, image packages, Jupyter behavior, GPU wiring, or import contracts, also build the validation image and run integration tests:

```bash
docker build -f images/base/Dockerfile --build-arg DSML_REQUIREMENTS=requirements-full.txt -t dsml-kit:validate .
DSML_TEST_IMAGE=dsml-kit:validate uv run pytest tests/integration
```

Maintainers can run the combined validation command:

```bash
uv run dsml dev validate
```

## Project Boundaries

- Keep the `dsml` CLI as the primary user interface.
- Keep Docker command construction out of `src/dsml/cli.py`; route behavior through runtime, config, Docker, and image helpers.
- Keep heavy runtime packages such as JupyterLab, numpy, pandas, torch, scikit-learn, matplotlib, and CUDA packages in `images/base/requirements-*.txt`, not in `pyproject.toml`.
- Keep unit tests Docker-free where practical. Put real container startup and Jupyter HTTP checks under `tests/integration`.
- Update import-contract tests when changing key image packages.
- Treat `dsml.yml` as workspace config. Do not require `.env` as a user-facing config path.

## Pull Requests

Keep PRs focused and include:

- A short summary of the behavior changed.
- The validation commands you ran.
- Any follow-up work or compatibility notes.

For user-facing CLI changes, update README examples when the command shape changes.
