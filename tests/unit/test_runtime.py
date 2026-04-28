import subprocess

import pytest
import yaml

from dsml import compose, config, paths, runtime


def completed(args):
    return subprocess.CompletedProcess(args, 0, "", "")


def write_workspace(tmp_path, data=None):
    config.write_config(tmp_path / "dsml.toml", data or config.default_config())


def read_compose_file(tmp_path):
    return yaml.safe_load(paths.compose_path(tmp_path).read_text())


@pytest.fixture(autouse=True)
def compose_available(monkeypatch):
    monkeypatch.setattr(runtime.docker, "compose_cli_exists", lambda: True)
    monkeypatch.setattr(runtime.docker, "nvidia_smi_exists", lambda: False)


def stub_compose_up(monkeypatch, calls):
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: False)
    monkeypatch.setattr(
        runtime.compose,
        "up",
        lambda project_root, compose_file, detach=True: calls.append(("up", compose_file, detach))
        or completed(["docker", "compose", "up"]),
    )
    monkeypatch.setattr(runtime, "wait_for_jupyter", lambda options: True)


def test_up_writes_compose_file_before_starting(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: False)

    def compose_up(project_root, compose_file, detach=True):
        assert compose_file == paths.compose_path(tmp_path)
        assert compose_file.exists()
        calls.append(("up", detach))
        return completed(["docker", "compose", "up"])

    monkeypatch.setattr(runtime.compose, "up", compose_up)
    monkeypatch.setattr(runtime, "wait_for_jupyter", lambda options: True)

    runtime.up()

    model = read_compose_file(tmp_path)
    service = model["services"]["app"]
    assert calls == [("up", True)]
    assert service["image"] == "ghcr.io/mihneateodorstoica/dsml-kit:minimal"
    assert paths.RUN_SIGNATURE_LABEL in service["labels"]


def test_up_builds_dev_image_from_config_before_starting(tmp_path, monkeypatch):
    data = config.default_config(profile="dev", image="dsml-kit:dev")
    data["workspace"]["gpu"] = False
    config.write_config(tmp_path / "dsml.toml", data)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.images,
        "build_image",
        lambda tag=runtime.images.DEFAULT_LOCAL_IMAGE, dev=False: calls.append(("build", tag, dev)),
    )
    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: calls.append(("image_exists", image)) or True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    stub_compose_up(monkeypatch, calls)

    runtime.up()

    assert calls[0] == ("build", "dsml-kit:dev", False)
    assert ("up", paths.compose_path(tmp_path), True) in calls
    assert read_compose_file(tmp_path)["services"]["app"]["image"] == "dsml-kit:dev"


def test_up_pulls_missing_remote_image_before_starting(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    def image_exists(image):
        calls.append(("image_exists", image))
        return len([call for call in calls if call[0] == "image_exists"]) > 1

    monkeypatch.setattr(runtime.docker, "image_exists", image_exists)
    monkeypatch.setattr(runtime.images, "pull_image", lambda image: calls.append(("pull", image)))
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    stub_compose_up(monkeypatch, calls)

    runtime.up()

    assert calls[0][0] == "image_exists"
    assert calls[1] == ("pull", "ghcr.io/mihneateodorstoica/dsml-kit:minimal")
    assert any(call[0] == "up" for call in calls)


def test_up_honors_pull_image_policy_before_starting(tmp_path, monkeypatch):
    data = config.default_config()
    data["workspace"]["image_policy"] = "pull"
    write_workspace(tmp_path, data)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(runtime.images, "pull_image", lambda image: calls.append(("pull", image)))
    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: calls.append(("image_exists", image)) or True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    stub_compose_up(monkeypatch, calls)

    runtime.up()

    assert calls[0] == ("pull", "ghcr.io/mihneateodorstoica/dsml-kit:minimal")
    assert ("up", paths.compose_path(tmp_path), True) in calls


def test_up_honors_build_image_policy_before_starting(tmp_path, monkeypatch):
    data = config.default_config(image="example/dsml-kit:local")
    data["workspace"]["image_policy"] = "build"
    write_workspace(tmp_path, data)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.images,
        "build_image",
        lambda tag=runtime.images.DEFAULT_LOCAL_IMAGE, dev=False: calls.append(("build", tag, dev)),
    )
    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: calls.append(("image_exists", image)) or True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    stub_compose_up(monkeypatch, calls)

    runtime.up()

    assert calls[0] == ("build", "example/dsml-kit:local", False)
    assert ("up", paths.compose_path(tmp_path), True) in calls


def test_up_honors_never_image_policy_for_missing_image(tmp_path, monkeypatch):
    data = config.default_config(image="example/dsml-kit:local")
    data["workspace"]["image_policy"] = "never"
    write_workspace(tmp_path, data)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: False)
    monkeypatch.setattr(runtime.images, "pull_image", lambda image: pytest.fail("should not pull"))
    monkeypatch.setattr(runtime.images, "build_image", lambda tag, dev=False: pytest.fail("should not build"))

    with pytest.raises(runtime.RuntimeError, match="image_policy is set to never"):
        runtime.up()


def test_up_dev_build_uses_dev_image(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.images,
        "build_image",
        lambda tag=runtime.images.DEFAULT_LOCAL_IMAGE, dev=False: calls.append(("build", tag, dev)),
    )
    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    stub_compose_up(monkeypatch, calls)

    runtime.up(dev=True, build=True)

    assert ("build", runtime.images.DEFAULT_DEV_IMAGE, True) in calls
    assert read_compose_file(tmp_path)["services"]["app"]["image"] == runtime.images.DEFAULT_DEV_IMAGE


def test_up_reuses_matching_auto_token_in_compose_file(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    data = config.read_config(tmp_path / "dsml.toml")
    options = runtime.run_options(tmp_path, data)
    signature = runtime.container_signature(options, image_id="sha256:test", token_policy="auto")
    calls = []

    def container_label(name, label):
        if label == paths.RUN_SIGNATURE_LABEL:
            return signature
        if label == compose.COMPOSE_PROJECT_LABEL:
            return compose.compose_project_name(tmp_path)
        return ""

    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: True)
    monkeypatch.setattr(runtime.docker, "container_label", container_label)
    monkeypatch.setattr(runtime.docker, "container_env_value", lambda name, key: "existing-token")
    monkeypatch.setattr(
        runtime.compose,
        "up",
        lambda project_root, compose_file, detach=True: calls.append(("up", detach))
        or completed(["docker", "compose", "up"]),
    )
    monkeypatch.setattr(runtime, "wait_for_jupyter", lambda options: True)

    runtime.up()

    env = read_compose_file(tmp_path)["services"]["app"]["environment"]
    assert calls == [("up", True)]
    assert env["JUPYTER_TOKEN"] == "existing-token"


def test_up_removes_legacy_dsml_container_before_compose_up(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    def container_label(name, label):
        if label == paths.PROJECT_LABEL:
            return paths.project_name(tmp_path)
        return ""

    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: True)
    monkeypatch.setattr(runtime.docker, "container_label", container_label)
    monkeypatch.setattr(
        runtime.docker,
        "remove_container",
        lambda name, force=False: calls.append(("remove", name, force)) or completed(["docker", "rm"]),
    )
    monkeypatch.setattr(
        runtime.compose,
        "up",
        lambda project_root, compose_file, detach=True: calls.append(("up", detach))
        or completed(["docker", "compose", "up"]),
    )
    monkeypatch.setattr(runtime, "wait_for_jupyter", lambda options: True)

    runtime.up()

    assert calls == [("remove", paths.default_container_name(tmp_path), True), ("up", True)]


def test_down_stops_without_removing_project(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.compose,
        "stop",
        lambda project_root, compose_file: calls.append(("stop", compose_file)) or completed(["docker", "compose", "stop"]),
    )
    monkeypatch.setattr(runtime.docker, "remove_container", lambda name, force=False: pytest.fail("should not remove"))

    runtime.down()

    assert calls == [("stop", paths.compose_path(tmp_path))]


def test_logs_uses_compose_logs(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.compose,
        "logs",
        lambda project_root, compose_file, follow=False, tail=None: calls.append(("logs", follow, tail))
        or completed(["docker", "compose", "logs"]),
    )

    runtime.logs(follow=True, tail=25)

    assert calls == [("logs", True, 25)]


def test_shell_uses_compose_exec_and_falls_back_to_sh(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    def compose_exec(project_root, compose_file, command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 1 if command == ["/bin/bash"] else 0, "", "")

    monkeypatch.setattr(runtime.compose, "exec", compose_exec)

    runtime.shell()

    assert calls == [
        (["/bin/bash"], {"user": "jovyan", "interactive": True, "check": False}),
        (["/bin/sh"], {"user": "jovyan", "interactive": True}),
    ]


def test_add_updates_config_and_installs_with_compose_exec_when_running(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(runtime.compose, "service_running", lambda project_root, compose_file: True)
    monkeypatch.setattr(
        runtime.compose,
        "exec",
        lambda project_root, compose_file, command, **kwargs: calls.append((command, kwargs))
        or completed(["docker", "compose", "exec"]),
    )

    runtime.add(["polars", "optuna"])

    assert config.read_config(tmp_path / "dsml.toml")["packages"]["extra"] == ["polars", "optuna"]
    assert calls == [
        (
            ["uv", "pip", "install", "--system", "polars", "optuna"],
            {"user": "root"},
        )
    ]


def test_add_reads_requirement_files_and_installs_specs(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("polars>=1.0\noptuna  # tuner\n")
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(runtime.compose, "service_running", lambda project_root, compose_file: True)
    monkeypatch.setattr(
        runtime.compose,
        "exec",
        lambda project_root, compose_file, command, **kwargs: calls.append((command, kwargs))
        or completed(["docker", "compose", "exec"]),
    )

    runtime.add([], [requirements])

    assert config.read_config(tmp_path / "dsml.toml")["packages"]["extra"] == ["polars>=1.0", "optuna"]
    assert calls == [
        (
            ["uv", "pip", "install", "--system", "polars>=1.0", "optuna"],
            {"user": "root"},
        )
    ]


def test_sync_installs_configured_packages_with_compose_exec(tmp_path, monkeypatch):
    data = config.default_config()
    data["packages"]["extra"] = ["polars"]
    write_workspace(tmp_path, data)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(runtime.compose, "service_running", lambda project_root, compose_file: True)
    monkeypatch.setattr(
        runtime.compose,
        "exec",
        lambda project_root, compose_file, command, **kwargs: calls.append((command, kwargs))
        or completed(["docker", "compose", "exec"]),
    )

    runtime.sync()

    assert calls == [(["uv", "pip", "install", "--system", "polars"], {"user": "root"})]


def test_clean_calls_compose_down_and_optional_cleanup(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.compose,
        "down",
        lambda project_root, compose_file, volumes=False: calls.append(("down", volumes))
        or completed(["docker", "compose", "down"]),
    )
    monkeypatch.setattr(runtime.docker, "remove_image", lambda image: calls.append(("image", image)))

    runtime.clean(image=True, volumes=True)

    assert calls == [
        ("down", True),
        ("image", "ghcr.io/mihneateodorstoica/dsml-kit:minimal"),
    ]


def test_nuke_requires_delete_and_removes_compose_project_and_volume(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.compose,
        "down",
        lambda project_root, compose_file, volumes=False: calls.append(("down", volumes))
        or completed(["docker", "compose", "down"]),
    )
    monkeypatch.setattr(runtime.docker, "remove_volume", lambda volume: calls.append(("volume", volume)))

    runtime.nuke(confirmation="nope")
    runtime.nuke(confirmation="DELETE")

    assert calls == [
        ("down", True),
        ("volume", paths.default_home_volume(tmp_path)),
    ]
