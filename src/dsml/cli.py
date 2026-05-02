from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.table import Table

from dsml import __version__
from dsml import config, doctor, images, profiles, runtime


app = typer.Typer(help="Manage profile-based Docker workspaces for data science and ML.")
compose_app = typer.Typer(help="Inspect the generated Docker Compose backend.")
image_app = typer.Typer(help="Build, pull, inspect, and remove runtime images.")
dev_app = typer.Typer(help="Maintainer development commands.")
app.add_typer(compose_app, name="compose")
app.add_typer(image_app, name="image")
app.add_typer(dev_app, name="dev")
console = Console()


def _handle_error(exc: Exception) -> NoReturn:
    console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(1) from exc


def _configured_workspace_image() -> str:
    _, _, data = runtime.load_workspace()
    image = data["workspace"]["image"]
    if not isinstance(image, str):
        raise runtime.RuntimeError("Configured workspace image must be a string.")
    return image


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the dsml-kit version and exit."),
    ] = False,
) -> None:
    """Manage profile-based Docker workspaces for data science and ML."""
    if version:
        console.print(f"dsml-kit {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def init(
    profile: Annotated[str, typer.Option(help="Workspace profile to use.")] = "minimal",
    port: Annotated[int, typer.Option(help="Host port for JupyterLab.")] = 8888,
    gpu: Annotated[str, typer.Option(help="GPU mode: auto, true, or false.")] = "auto",
    image: Annotated[str | None, typer.Option(help="Override the profile image.")] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing dsml.yml.")] = False,
) -> None:
    """Create dsml.yml in the current project."""
    try:
        gpu_value = config.validate_config(config.default_config(gpu=gpu))["workspace"]["gpu"]
        path = runtime.init_project(
            project_root=Path.cwd(),
            profile_name=profile,
            port=port,
            gpu=gpu_value,
            image=image,
            force=force,
        )
    except (config.ConfigError, profiles.ProfileError, runtime.RuntimeError) as exc:
        _handle_error(exc)
    console.print(f"[green]Created[/green] {path}")


@app.command()
def up(
    attach: Annotated[bool, typer.Option(help="Attach to the container instead of starting detached.")] = False,
    build: Annotated[bool, typer.Option(help="Build the image before starting, overriding image_policy.")] = False,
    pull: Annotated[
        bool,
        typer.Option(help="Pull the selected image before starting, overriding image_policy."),
    ] = False,
    dev: Annotated[bool, typer.Option(help="Use and build the development image.")] = False,
    recreate: Annotated[
        bool,
        typer.Option("--recreate", help="Force Docker Compose to recreate the service container."),
    ] = False,
    wait: Annotated[
        bool,
        typer.Option("--wait/--no-wait", help="Wait for Jupyter to answer before returning."),
    ] = True,
    wait_timeout: Annotated[int, typer.Option(help="Seconds to wait for Jupyter.")] = 30,
) -> None:
    """Start the Docker workspace."""
    try:
        runtime.up(
            attach=attach,
            build=build,
            pull=pull,
            dev=dev,
            recreate=recreate,
            wait=wait,
            wait_timeout=wait_timeout,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary.
        _handle_error(exc)


@app.command()
def watch(
    dev: Annotated[bool, typer.Option(help="Use the development image while watching.")] = False,
    no_up: Annotated[
        bool,
        typer.Option("--no-up", help="Do not build and start services before watching."),
    ] = False,
    prune: Annotated[
        bool,
        typer.Option("--prune/--no-prune", help="Prune dangling images after rebuilds."),
    ] = True,
    quiet: Annotated[bool, typer.Option(help="Hide Docker build output.")] = False,
) -> None:
    """Rebuild the local runtime image when its source files change."""
    try:
        runtime.watch(dev=dev, no_up=no_up, prune=prune, quiet=quiet)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command()
def down() -> None:
    """Stop the current project container."""
    try:
        runtime.down()
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command()
def stop() -> None:
    """Stop the current project container."""
    try:
        runtime.stop()
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command()
def restart(
    attach: Annotated[bool, typer.Option(help="Attach after restarting.")] = False,
) -> None:
    """Restart the current project container."""
    try:
        runtime.restart(attach=attach)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command()
def logs(
    follow: Annotated[bool, typer.Option("--follow", "-f", help="Follow log output.")] = False,
    tail: Annotated[int | None, typer.Option(help="Number of log lines to show.")] = None,
    since: Annotated[str | None, typer.Option(help="Show logs since a timestamp or duration, such as 10m.")] = None,
    timestamps: Annotated[bool, typer.Option(help="Show log timestamps.")] = False,
) -> None:
    """Show container logs."""
    try:
        runtime.logs(follow=follow, tail=tail, since=since, timestamps=timestamps)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command()
def shell(
    command: Annotated[str | None, typer.Argument(help="Optional command to run instead of /bin/bash.")] = None,
    user: Annotated[str, typer.Option(help="Container user for the shell command.")] = "jovyan",
    root: Annotated[bool, typer.Option("--root", help="Run the shell command as root.")] = False,
) -> None:
    """Open a shell inside the running container."""
    try:
        runtime.shell(command, user="root" if root else user)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command("open")
def open_command() -> None:
    """Open the JupyterLab workspace URL."""
    try:
        runtime.open_workspace()
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command()
def add(
    packages: Annotated[
        list[str] | None,
        typer.Argument(help="Package names or requirement specifiers."),
    ] = None,
    requirements: Annotated[
        list[Path] | None,
        typer.Option("--requirement", "-r", help="Read package specifiers from a requirements.txt file."),
    ] = None,
) -> None:
    """Add packages to dsml.yml and install them in the running container."""
    try:
        runtime.add(packages or [], requirements)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command()
def sync() -> None:
    """Install configured extra packages in the running container."""
    try:
        runtime.sync()
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command()
def status() -> None:
    """Show workspace backend status."""
    try:
        status_info = runtime.status()
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)
    table = Table(show_header=False)
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Backend", status_info.backend)
    table.add_row("Project", status_info.project_name)
    table.add_row("Container", status_info.container_name)
    table.add_row("Image", status_info.image)
    table.add_row("State", "[green]running[/green]" if status_info.running else "[yellow]stopped[/yellow]")
    table.add_row("URL", status_info.url)
    table.add_row("Config", str(status_info.config_path))
    table.add_row("Compose", str(status_info.compose_file))
    console.print(table)


def doctor_command() -> None:
    """Print workspace diagnostics."""
    checks = doctor.run_checks()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")
    for check in checks:
        table.add_row(check.name, "[green]ok[/green]" if check.ok else "[red]fail[/red]", check.message)
    console.print(table)
    if any(not check.ok for check in checks):
        raise typer.Exit(1)


app.command("doctor")(doctor_command)


@compose_app.command("path")
def compose_path() -> None:
    """Print the generated Compose file path."""
    try:
        console.print(runtime.compose_path_for_workspace())
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@compose_app.command("config")
def compose_config() -> None:
    """Render Docker Compose's normalized config for this workspace."""
    try:
        runtime.compose_config()
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@compose_app.command("ps")
def compose_ps() -> None:
    """Show Docker Compose services for this workspace."""
    try:
        runtime.compose_ps()
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command()
def clean(
    image: Annotated[bool, typer.Option(help="Also remove the selected image.")] = False,
    volumes: Annotated[bool, typer.Option(help="Also remove the persistent home volume.")] = False,
) -> None:
    """Stop and remove containers for this project."""
    try:
        runtime.clean(image=image, volumes=volumes)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command()
def nuke() -> None:
    """Dangerous full cleanup for this project."""
    confirmation = typer.prompt("Type DELETE to continue")
    try:
        runtime.nuke(confirmation=confirmation)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command("profiles")
def list_profiles() -> None:
    """List bundled profiles."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("GPU")
    table.add_column("Image")
    table.add_column("Description")
    for profile in profiles.list_profiles():
        table.add_row(profile.name, str(profile.gpu), profile.image, profile.description)
    console.print(table)


@image_app.command("build")
def image_build(
    tag: Annotated[str, typer.Option(help="Image tag to build.")] = images.DEFAULT_LOCAL_IMAGE,
    dev: Annotated[bool, typer.Option(help="Build the development image tag.")] = False,
    variant: Annotated[
        str,
        typer.Option(help="Image variant requirements to use: minimal, base, extended, or full."),
    ] = "base",
    context: Annotated[Path | None, typer.Option(help="Docker build context.")] = None,
    dockerfile: Annotated[Path | None, typer.Option(help="Dockerfile path.")] = None,
    target: Annotated[str, typer.Option(help="Optional Dockerfile stage target.")] = "",
    build_arg: Annotated[
        list[str] | None,
        typer.Option("--build-arg", help="Docker build argument as KEY=VALUE. Can be used more than once."),
    ] = None,
) -> None:
    """Build the runtime image."""
    try:
        if dev and (context is not None or dockerfile is not None or target or build_arg or variant != "base"):
            raise typer.BadParameter("--dev uses the maintainer image defaults; do not combine it with custom build options.")
        build_args = {} if dev else _image_build_args(variant, build_arg or [])
        _validate_image_build_options(dev=dev, context=context, dockerfile=dockerfile, target=target, build_args=build_args)
        images.build_image(
            tag=tag,
            dev=dev,
            context=context,
            dockerfile=dockerfile,
            target=target,
            build_args=build_args,
        )
    except (typer.BadParameter, ValueError) as exc:
        _handle_error(exc)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


def _image_build_args(variant: str, values: list[str]) -> dict[str, str]:
    normalized = variant.strip().lower()
    if normalized not in images.IMAGE_VARIANTS:
        available = ", ".join(sorted(images.IMAGE_VARIANTS))
        raise typer.BadParameter(f"--variant must be one of: {available}.")
    parsed = {"DSML_REQUIREMENTS": images.IMAGE_VARIANTS[normalized]}
    parsed.update(_parse_build_args(values))
    return parsed


def _validate_image_build_options(
    *,
    dev: bool,
    context: Path | None,
    dockerfile: Path | None,
    target: str,
    build_args: dict[str, str],
) -> None:
    if context is not None and not context.exists():
        raise typer.BadParameter(f"Build context does not exist: {context}")
    if dockerfile is not None and not dockerfile.is_file():
        raise typer.BadParameter(f"Dockerfile does not exist: {dockerfile}")
    requirements = build_args.get("DSML_REQUIREMENTS", "")
    if "/" in requirements or "\\" in requirements or requirements.startswith("."):
        raise typer.BadParameter("DSML_REQUIREMENTS must be a requirements file name, not a path.")
    if not requirements.startswith("requirements-") or not requirements.endswith(".txt"):
        raise typer.BadParameter("DSML_REQUIREMENTS must look like requirements-<variant>.txt.")
    python_version = build_args.get("PYTHON_VERSION")
    if python_version is not None and python_version not in {"3.10", "3.11", "3.12"}:
        raise typer.BadParameter("PYTHON_VERSION must be one of: 3.10, 3.11, 3.12.")
    apt_packages = build_args.get("DSML_EXTRA_APT_PACKAGES")
    if apt_packages is not None and not all(char.isalnum() or char in "+_.: -" for char in apt_packages):
        raise typer.BadParameter("DSML_EXTRA_APT_PACKAGES contains unsupported characters.")


def _parse_build_args(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise typer.BadParameter("--build-arg values must use KEY=VALUE.")
        key, build_value = value.split("=", 1)
        key = key.strip()
        if not key:
            raise typer.BadParameter("--build-arg keys cannot be empty.")
        if key.startswith("JUPYTER_TOKEN"):
            raise typer.BadParameter("Do not pass secrets as Docker build args.")
        parsed[key] = build_value
    return parsed


@image_app.command("pull")
def image_pull(
    image: Annotated[str | None, typer.Argument(help="Image to pull.")] = None,
) -> None:
    """Pull the configured or specified runtime image."""
    try:
        selected_image = image if image is not None else _configured_workspace_image()
        images.pull_image(selected_image)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@image_app.command("freeze")
def image_freeze(
    image: Annotated[str | None, typer.Argument(help="Image to inspect.")] = None,
) -> None:
    """Print pip freeze from a runtime image."""
    try:
        selected_image = image if image is not None else _configured_workspace_image()
        images.freeze_packages(selected_image)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@image_app.command("remove")
def image_remove(
    image: Annotated[str | None, typer.Argument(help="Image to remove.")] = None,
) -> None:
    """Remove a local runtime image."""
    try:
        selected_image = image if image is not None else _configured_workspace_image()
        images.remove_image(selected_image)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@dev_app.command("test")
def dev_test() -> None:
    """Run the test suite."""
    try:
        runtime.dev_test()
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@dev_app.command("validate")
def dev_validate() -> None:
    """Build the validation image and run integration tests."""
    try:
        runtime.dev_validate()
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)
