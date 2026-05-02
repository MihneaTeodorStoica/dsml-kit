import subprocess

import pytest
import yaml

from dsml import compose, config, paths, runtime


def completed(args):
    return subprocess.CompletedProcess(args, 0, "", "")


def write_workspace(tmp_path, data=None):
    config.write_config(tmp_path / "dsml.yml", data or config.default_config())


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
    config.write_config(tmp_path / "dsml.yml", data)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.images,
        "build_image",
        lambda tag=runtime.images.DEFAULT_LOCAL_IMAGE, dev=False, **kwargs: calls.append(("build", tag, dev, kwargs)),
    )
    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: calls.append(("image_exists", image)) or True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    stub_compose_up(monkeypatch, calls)

    runtime.up()

    assert calls[0] == ("build", "dsml-kit:dev", True, {})
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
    image_dir = tmp_path / "images" / "base"
    image_dir.mkdir(parents=True)
    (image_dir / "Dockerfile").write_text("FROM example\n")
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.images,
        "build_image",
        lambda tag=runtime.images.DEFAULT_LOCAL_IMAGE, dev=False, **kwargs: calls.append(("build", tag, dev, kwargs)),
    )
    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: calls.append(("image_exists", image)) or True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    stub_compose_up(monkeypatch, calls)

    runtime.up()

    assert calls[0][:3] == ("build", "example/dsml-kit:local", False)
    assert calls[0][3]["context"] == tmp_path
    assert calls[0][3]["dockerfile"] == tmp_path / "images" / "base" / "Dockerfile"
    assert ("up", paths.compose_path(tmp_path), True) in calls


def test_up_build_policy_writes_runtime_watch_metadata(tmp_path, monkeypatch):
    data = config.default_config(image="example/dsml-kit:local")
    data["workspace"]["image_policy"] = "build"
    write_workspace(tmp_path, data)
    image_dir = tmp_path / "images" / "base"
    image_dir.mkdir(parents=True)
    (image_dir / "Dockerfile").write_text("FROM example\n")
    (image_dir / "requirements.txt").write_text("\n")
    (tmp_path / ".dockerignore").write_text(".git\n")
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(runtime.paths, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        runtime.images,
        "build_image",
        lambda tag=runtime.images.DEFAULT_LOCAL_IMAGE, dev=False, **kwargs: calls.append(("build", tag, dev, kwargs)),
    )
    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    stub_compose_up(monkeypatch, calls)

    runtime.up(wait=False)

    service = read_compose_file(tmp_path)["services"]["app"]
    assert service["build"] == {
        "context": ".",
        "dockerfile": "images/base/Dockerfile",
        "args": {
            "PYTHON_VERSION": "3.11",
            "DSML_REQUIREMENTS": "requirements-minimal.txt",
        },
    }
    assert service["develop"]["watch"] == [
        {"action": "rebuild", "path": "images/base"},
        {"action": "rebuild", "path": ".dockerignore"},
    ]


def test_up_build_policy_honors_custom_image_build_config(tmp_path, monkeypatch):
    data = config.default_config(image="example/dsml-kit:custom")
    data["workspace"]["image_policy"] = "build"
    data["image_build"] = {
        "context": "docker",
        "dockerfile": "runtime.Dockerfile",
        "target": "prod",
        "args": {"PYTHON_VERSION": "3.12"},
        "watch": ["docker/runtime.Dockerfile", "docker/requirements.txt"],
    }
    write_workspace(tmp_path, data)
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    (docker_dir / "runtime.Dockerfile").write_text("FROM example AS prod\n")
    (docker_dir / "requirements.txt").write_text("\n")
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.images,
        "build_image",
        lambda tag=runtime.images.DEFAULT_LOCAL_IMAGE, dev=False, **kwargs: calls.append(("build", tag, dev, kwargs)),
    )
    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    stub_compose_up(monkeypatch, calls)

    runtime.up(wait=False)

    assert calls[0][3] == {
        "context": docker_dir,
        "dockerfile": docker_dir / "runtime.Dockerfile",
        "target": "prod",
        "build_args": {"PYTHON_VERSION": "3.12"},
    }
    service = read_compose_file(tmp_path)["services"]["app"]
    assert service["build"] == {
        "context": "docker",
        "dockerfile": "runtime.Dockerfile",
        "target": "prod",
        "args": {"PYTHON_VERSION": "3.12"},
    }
    assert service["develop"]["watch"] == [
        {"action": "rebuild", "path": "docker/runtime.Dockerfile"},
        {"action": "rebuild", "path": "docker/requirements.txt"},
    ]


def test_up_honors_never_image_policy_for_missing_image(tmp_path, monkeypatch):
    data = config.default_config(image="example/dsml-kit:local")
    data["workspace"]["image_policy"] = "never"
    write_workspace(tmp_path, data)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: False)
    monkeypatch.setattr(runtime.images, "pull_image", lambda image: pytest.fail("should not pull"))
    monkeypatch.setattr(runtime.images, "build_image", lambda tag, dev=False, **kwargs: pytest.fail("should not build"))

    with pytest.raises(runtime.RuntimeError, match="image_policy is set to never"):
        runtime.up()


def test_up_dev_build_uses_dev_image(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.images,
        "build_image",
        lambda tag=runtime.images.DEFAULT_LOCAL_IMAGE, dev=False, **kwargs: calls.append(("build", tag, dev, kwargs)),
    )
    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    stub_compose_up(monkeypatch, calls)

    runtime.up(dev=True, build=True)

    assert ("build", runtime.images.DEFAULT_DEV_IMAGE, True, {}) in calls
    assert read_compose_file(tmp_path)["services"]["app"]["image"] == runtime.images.DEFAULT_DEV_IMAGE


def test_up_recreate_passes_force_recreate_and_no_wait_skips_probe(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: False)
    monkeypatch.setattr(
        runtime.compose,
        "up",
        lambda project_root, compose_file, detach=True, force_recreate=False: calls.append(
            ("up", detach, force_recreate)
        )
        or completed(["docker", "compose", "up"]),
    )
    monkeypatch.setattr(runtime, "wait_for_jupyter", lambda options: pytest.fail("should not wait"))

    runtime.up(recreate=True, wait=False)

    assert calls == [("up", True, True)]


def test_up_wait_timeout_controls_jupyter_attempts(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: False)
    monkeypatch.setattr(
        runtime.compose,
        "up",
        lambda project_root, compose_file, detach=True: completed(["docker", "compose", "up"]),
    )

    def wait_for_jupyter(options, *, attempts=30, sleep_seconds=1.0):
        calls.append((attempts, sleep_seconds))
        return True

    monkeypatch.setattr(runtime, "wait_for_jupyter", wait_for_jupyter)

    runtime.up(wait_timeout=7)

    assert calls == [(7, 1.0)]


def test_up_reuses_matching_auto_token_in_compose_file(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    data = config.read_config(tmp_path / "dsml.yml")
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


def test_watch_writes_build_watch_compose_file_and_runs_compose_watch(tmp_path, monkeypatch):
    data = config.default_config(image="dsml-kit:dev")
    data["workspace"]["image_policy"] = "build"
    write_workspace(tmp_path, data)
    image_dir = tmp_path / "images" / "base"
    image_dir.mkdir(parents=True)
    (image_dir / "Dockerfile").write_text("FROM example\n")
    (image_dir / "requirements.txt").write_text("\n")
    (tmp_path / ".dockerignore").write_text(".git\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runtime.paths, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: False)
    calls = []

    monkeypatch.setattr(
        runtime.compose,
        "watch",
        lambda project_root, compose_file, **kwargs: calls.append((project_root, compose_file, kwargs))
        or completed(["docker", "compose", "watch"]),
    )

    runtime.watch(no_up=True, prune=False, quiet=True)

    service = read_compose_file(tmp_path)["services"]["app"]
    assert service["build"] == {"context": ".", "dockerfile": "images/base/Dockerfile"}
    assert service["develop"]["watch"] == [
        {"action": "rebuild", "path": "images/base"},
        {"action": "rebuild", "path": ".dockerignore"},
    ]
    assert calls == [
        (
            tmp_path,
            paths.compose_path(tmp_path),
            {"no_up": True, "prune": False, "quiet": True},
        )
    ]


def test_watch_requires_local_build_image_policy(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(runtime.RuntimeError, match="image_policy"):
        runtime.watch()


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


def test_logs_passes_since_and_timestamps(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.compose,
        "logs",
        lambda project_root, compose_file, **kwargs: calls.append(kwargs)
        or completed(["docker", "compose", "logs"]),
    )

    runtime.logs(since="10m", timestamps=True)

    assert calls == [{"follow": False, "tail": None, "since": "10m", "timestamps": True}]


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

    assert config.read_config(tmp_path / "dsml.yml")["packages"]["extra"] == ["polars", "optuna"]
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

    assert config.read_config(tmp_path / "dsml.yml")["packages"]["extra"] == ["polars>=1.0", "optuna"]
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


def test_status_reports_compose_backend_state(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(runtime.compose, "service_running", lambda project_root, compose_file: True)

    status = runtime.status()

    assert status.backend == "compose"
    assert status.project_name == paths.project_name(tmp_path)
    assert status.container_name == paths.default_container_name(tmp_path)
    assert status.compose_file == paths.compose_path(tmp_path)
    assert status.running is True


def test_compose_debug_runtime_commands_call_backend_wrappers(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(
        runtime.compose,
        "config",
        lambda project_root, compose_file: calls.append(("config", compose_file))
        or completed(["docker", "compose", "config"]),
    )
    monkeypatch.setattr(
        runtime.compose,
        "ps",
        lambda project_root, compose_file: calls.append(("ps", compose_file))
        or completed(["docker", "compose", "ps"]),
    )

    runtime.compose_config()
    runtime.compose_ps()

    assert calls == [
        ("config", paths.compose_path(tmp_path)),
        ("ps", paths.compose_path(tmp_path)),
    ]
