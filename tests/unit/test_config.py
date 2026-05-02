import pytest
import yaml

from dsml import config


def test_write_and_read_default_config(tmp_path):
    path = tmp_path / "dsml.yml"
    data = config.create_project_config(
        profile="minimal",
        profile_image="ghcr.io/mihneateodorstoica/dsml-kit:minimal",
        profile_image_build={"args": {"DSML_REQUIREMENTS": "requirements-minimal.txt"}},
        port=8899,
        gpu=False,
        image=None,
    )

    config.write_config(path, data)

    written = yaml.safe_load(path.read_text())
    assert written["runtime"]["backend"] == "compose"
    assert written["workspace"]["profile"] == "minimal"
    assert written["workspace"]["port"] == 8899
    assert written["workspace"]["jupyter_token"] == "auto"
    assert written["workspace"]["image_policy"] == "auto"
    assert written["workspace"]["mount"] == "./workspace"
    assert written["image_build"]["context"] == "."
    assert written["image_build"]["dockerfile"] == "images/base/Dockerfile"
    assert written["image_build"]["args"]["DSML_REQUIREMENTS"] == "requirements-minimal.txt"
    assert written["jupyter"]["root_dir"] == "/home/jovyan/work"
    assert written["packages"]["extra"] == []


def test_write_config_refuses_to_overwrite_without_force(tmp_path):
    path = tmp_path / "dsml.yml"
    path.write_text("workspace:\n")

    with pytest.raises(config.ConfigError, match="already exists"):
        config.write_config(path, config.default_config())


def test_read_config_supports_legacy_toml(tmp_path):
    path = tmp_path / "dsml.toml"
    path.write_text(
        "\n".join(
            [
                "[workspace]",
                'profile = "minimal"',
                'mount = "./workspace"',
                "port = 8899",
                'bind_address = "127.0.0.1"',
                'container_name = "auto"',
                'home_volume = "auto"',
                'gpu = "auto"',
                'image = "example:test"',
                'image_policy = "auto"',
                'jupyter_token = "auto"',
            ]
        )
    )

    data = config.read_config(path)

    assert data["workspace"]["image"] == "example:test"
    assert data["image_build"]["dockerfile"] == "images/base/Dockerfile"


def test_add_packages_preserves_order_and_deduplicates(tmp_path):
    path = tmp_path / "dsml.yml"
    config.write_config(path, config.default_config())

    data = config.add_packages(path, ["polars", "optuna", "polars"])

    assert data["packages"]["extra"] == ["polars", "optuna"]
    assert config.read_config(path)["packages"]["extra"] == ["polars", "optuna"]


def test_read_requirement_specs_ignores_comments_and_deduplicates(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        "\n".join(
            [
                "# local project requirements",
                "polars>=1.0  # dataframe engine",
                "optuna",
                "pkg @ https://example.test/pkg.tar.gz#sha256=abc",
                "polars>=1.0",
                "",
            ]
        )
    )

    assert config.read_requirement_specs([requirements]) == [
        "polars>=1.0",
        "optuna",
        "pkg @ https://example.test/pkg.tar.gz#sha256=abc",
    ]


def test_read_requirement_specs_supports_nested_requirement_files(tmp_path):
    base = tmp_path / "requirements.txt"
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested = nested_dir / "extra.txt"
    base.write_text("-r nested/extra.txt\npolars\n")
    nested.write_text("optuna\n")

    assert config.read_requirement_specs([base]) == ["optuna", "polars"]


def test_read_requirement_specs_rejects_pip_options(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("--extra-index-url https://example.test/simple\n")

    with pytest.raises(config.ConfigError, match="Unsupported requirements option"):
        config.read_requirement_specs([requirements])


def test_invalid_gpu_value_fails_validation():
    data = config.default_config(gpu="sometimes")

    with pytest.raises(config.ConfigError, match="gpu"):
        config.validate_config(data)


def test_invalid_image_policy_fails_validation():
    data = config.default_config()
    data["workspace"]["image_policy"] = "sometimes"

    with pytest.raises(config.ConfigError, match="image_policy"):
        config.validate_config(data)


@pytest.mark.parametrize("port", [True, 8888.5, "not-a-port"])
def test_invalid_port_fails_validation(port):
    data = config.default_config()
    data["workspace"]["port"] = port

    with pytest.raises(config.ConfigError, match="port"):
        config.validate_config(data)


def test_invalid_runtime_backend_fails_validation():
    data = config.default_config()
    data["runtime"]["backend"] = "docker"

    with pytest.raises(config.ConfigError, match="runtime.*backend"):
        config.validate_config(data)
