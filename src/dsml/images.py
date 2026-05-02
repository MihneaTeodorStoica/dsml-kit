from __future__ import annotations

from pathlib import Path

from dsml import docker, paths


DEFAULT_LOCAL_IMAGE = "dsml-kit:latest"
DEFAULT_DEV_IMAGE = "dsml-kit:dev"
VALIDATE_IMAGE = "dsml-kit:validate"
DEFAULT_REQUIREMENTS = "requirements-base.txt"
VALIDATE_REQUIREMENTS = "requirements-full.txt"
IMAGE_VARIANTS = {
    "minimal": "requirements-minimal.txt",
    "base": "requirements-base.txt",
    "extended": "requirements-extended.txt",
    "full": "requirements-full.txt",
}


def build_image(
    *,
    tag: str = DEFAULT_LOCAL_IMAGE,
    dev: bool = False,
    context: Path | None = None,
    dockerfile: Path | None = None,
    target: str = "",
    build_args: dict[str, str] | None = None,
) -> None:
    image_tag = DEFAULT_DEV_IMAGE if dev and tag == DEFAULT_LOCAL_IMAGE else tag
    effective_build_args = dict(build_args or {})
    effective_build_args.setdefault("DSML_REQUIREMENTS", DEFAULT_REQUIREMENTS)
    build_context = context or paths.repo_root()
    build_dockerfile = dockerfile or paths.repo_root() / "images" / "base" / "Dockerfile"
    args = [
        "docker",
        "build",
        "-f",
        str(build_dockerfile),
        "-t",
        image_tag,
    ]
    if target:
        args.extend(["--target", target])
    for key, value in effective_build_args.items():
        args.extend(["--build-arg", f"{key}={value}"])
    args.append(str(build_context))
    docker.run(args)


def pull_image(image: str) -> None:
    docker.pull_image(image)


def remove_image(image: str) -> None:
    docker.remove_image(image)


def freeze_packages(image: str) -> None:
    docker.run(["docker", "run", "--rm", "--entrypoint", "python", image, "-m", "pip", "freeze"])


def validation_env() -> dict[str, str]:
    return {
        "DSML_TEST_IMAGE": VALIDATE_IMAGE,
        "DSML_TEST_IMAGE_NAME": "dsml-kit",
        "DSML_TEST_TAG": "validate",
    }


def image_context() -> Path:
    return paths.repo_root()
