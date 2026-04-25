# AGENTS.md

## Repo Shape

- This is a Dockerized JupyterLab DS/ML workspace, not an installable Python app/library.
- Runtime image starts from `quay.io/jupyter/minimal-notebook:python-3.11` and installs pinned notebook/data packages from `requirements.txt`.
- `compose.yaml` is the published-image runtime path; `compose.dev.yaml` only adds local `Dockerfile` build config; `compose.gpu.yaml` is included only when `GPU_ENABLED=true`.
- `workspace/` and `.env` are local runtime state and are git-ignored; do not treat them as source.

## Commands

- Install the local pytest runner with `python3 -m pip install -r requirements-dev.txt` when needed.
- Full local smoke validation: `make test`. It builds `dsml-kit:validate` and runs `python3 -m pytest tests` with the expected `DSML_TEST_*` env vars.
- CI validation equivalent after a separate image build: `DSML_TEST_IMAGE=dsml-kit:validate DSML_TEST_IMAGE_NAME=dsml-kit DSML_TEST_TAG=validate python3 -m pytest tests`.
- Focus one test only after `dsml-kit:validate` exists: `DSML_TEST_IMAGE=dsml-kit:validate DSML_TEST_IMAGE_NAME=dsml-kit DSML_TEST_TAG=validate python3 -m pytest tests/test_image_smoke.py::test_image_starts_and_serves_jupyter_api`.
- `make validate` runs `make test` plus `docker scout quickview` and `docker scout cves`; it requires Docker Scout availability and network access.
- Start the published image path with `make run` or `make start`; force a local build/run with `make run-dev` or `DSML_MODE=dev make run`.

## Runtime And Env Gotchas

- `make run`, `make start`, `make build`, `make pull`, and `make env` may create `.env`; `make env` copies `.env.example` and replaces `JUPYTER_TOKEN` with a random token.
- `make run` and `make start` call `prepare-workspace`, which creates `WORKSPACE_DIR` and may repair ownership via a temporary BusyBox container.
- The Makefile exports the current host UID/GID unless `HOST_UID`/`HOST_GID` are set, so Compose tests assert that files written from Jupyter are owned by the host user.
- In `DSML_MODE=image`, `make build` intentionally skips local builds and `make pull` pulls the selected published image. In `DSML_MODE=dev`, `make build`/`make run` use `compose.dev.yaml` and `make pull` skips.
- `make nuke` is interactive and deletes the configured workspace after the exact confirmation string; avoid it in automation.

## Tests

- Tests require Docker and Docker Compose; they start real containers, allocate localhost ports, and call Jupyter `/api/status` with a token.
- `tests/test_compose_runtime.py` uses `docker compose -f compose.yaml -f compose.dev.yaml up -d --no-build` with `PULL_POLICY=never`, so the referenced test image must already exist locally.
- Import-contract tests are the package contract for the image; update both `tests/test_import_contract.py` and the duplicate import list in `tests/test_compose_runtime.py` when changing key installed packages.

## Image/Build Notes

- `.dockerignore` excludes `.github`, `.env`, notebooks, bytecode, and `workspace/`; files under those paths are not available during Docker builds.
- The image healthcheck only verifies port `8888` accepts TCP connections; pytest adds the stronger Jupyter HTTP API check.
- Publishing paths are GitHub Actions only: `docker-release.yml` publishes `latest`, tag, SHA, and date tags on `main`/`v*`; `docker-refresh.yml` publishes weekly, SHA, and date tags on schedule/manual dispatch.
