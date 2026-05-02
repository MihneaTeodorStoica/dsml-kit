import tomllib
from pathlib import Path

from dsml import __version__


def test_package_version_comes_from_project_metadata():
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    expected = tomllib.loads(pyproject.read_text())["project"]["version"]

    assert __version__ == expected
