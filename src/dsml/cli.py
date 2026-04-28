from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from dsml import config, doctor, images, profiles, runtime


app = typer.Typer(help="Manage profile-based Docker workspaces for data science and ML.")
image_app = typer.Typer(help="Build, pull, inspect, and remove runtime images.")
dev_app = typer.Typer(help="Maintainer development commands.")
app.add_typer(image_app, name="image")
app.add_typer(dev_app, name="dev")
console = Console()


def _handle_error(exc: Exception) -> None:
    console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(1) from exc


@app.command()
def init(
    profile: Annotated[str, typer.Option(help="Workspace profile to use.")] = "minimal",
    port: Annotated[int, typer.Option(help="Host port for JupyterLab.")] = 8888,
    gpu: Annotated[str, typer.Option(help="GPU mode: auto, true, or false.")] = "auto",
    image: Annotated[str | None, typer.Option(help="Override the profile image.")] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing dsml.toml.")] = False,
) -> None:
    """Create dsml.toml in the current project."""
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
) -> None:
    """Start the Docker workspace."""
    try:
        runtime.up(attach=attach, build=build, pull=pull, dev=dev)
    except Exception as exc:  # noqa: BLE001 - CLI boundary.
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
) -> None:
    """Show container logs."""
    try:
        runtime.logs(follow=follow, tail=tail)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@app.command()
def shell(
    command: Annotated[str | None, typer.Argument(help="Optional command to run instead of /bin/bash.")] = None,
) -> None:
    """Open a shell inside the running container."""
    try:
        runtime.shell(command)
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
    """Add packages to dsml.toml and install them in the running container."""
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
) -> None:
    """Build the runtime image."""
    try:
        images.build_image(tag=tag, dev=dev)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@image_app.command("pull")
def image_pull(
    image: Annotated[str | None, typer.Argument(help="Image to pull.")] = None,
) -> None:
    """Pull the configured or specified runtime image."""
    try:
        if image is None:
            _, _, data = runtime.load_workspace()
            image = data["workspace"]["image"]
        images.pull_image(image)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@image_app.command("freeze")
def image_freeze(
    image: Annotated[str | None, typer.Argument(help="Image to inspect.")] = None,
) -> None:
    """Print pip freeze from a runtime image."""
    try:
        if image is None:
            _, _, data = runtime.load_workspace()
            image = data["workspace"]["image"]
        images.freeze_packages(image)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@image_app.command("remove")
def image_remove(
    image: Annotated[str | None, typer.Argument(help="Image to remove.")] = None,
) -> None:
    """Remove a local runtime image."""
    try:
        if image is None:
            _, _, data = runtime.load_workspace()
            image = data["workspace"]["image"]
        images.remove_image(image)
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
