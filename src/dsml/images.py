from __future__ import annotations

from pathlib import Path

from dsml import docker, paths


DEFAULT_LOCAL_IMAGE = "dsml-kit:latest"
DEFAULT_DEV_IMAGE = "dsml-kit:dev"
VALIDATE_IMAGE = "dsml-kit:validate"


def build_image(*, tag: str = DEFAULT_LOCAL_IMAGE, dev: bool = False) -> None:
    image_tag = DEFAULT_DEV_IMAGE if dev and tag == DEFAULT_LOCAL_IMAGE else tag
    docker.run(
        [
            "docker",
            "build",
            "-f",
            str(paths.repo_root() / "images" / "base" / "Dockerfile"),
            "-t",
            image_tag,
            str(paths.repo_root()),
        ]
    )


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
