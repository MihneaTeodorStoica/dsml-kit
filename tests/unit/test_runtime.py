import subprocess

import pytest

from dsml import config, paths, runtime


def completed(args):
    return subprocess.CompletedProcess(args, 0, "", "")


def write_workspace(tmp_path, data=None):
    config.write_config(tmp_path / "dsml.toml", data or config.default_config())


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
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: False)
    monkeypatch.setattr(runtime.docker, "start_container", lambda options: calls.append(("start", options.image)))
    monkeypatch.setattr(runtime, "wait_for_jupyter", lambda options: True)

    runtime.up()

    assert calls[0] == ("build", "dsml-kit:dev", False)
    assert ("start", "dsml-kit:dev") in calls


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
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: False)
    monkeypatch.setattr(runtime.docker, "start_container", lambda options: calls.append(("start", options)))
    monkeypatch.setattr(runtime, "wait_for_jupyter", lambda options: True)

    runtime.up()

    assert calls[0][0] == "image_exists"
    assert calls[1] == ("pull", "ghcr.io/mihneateodorstoica/dsml-kit:minimal")
    assert any(call[0] == "start" for call in calls)


def test_up_honors_pull_image_policy_before_starting(tmp_path, monkeypatch):
    data = config.default_config()
    data["workspace"]["image_policy"] = "pull"
    write_workspace(tmp_path, data)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(runtime.images, "pull_image", lambda image: calls.append(("pull", image)))
    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: calls.append(("image_exists", image)) or True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: False)
    monkeypatch.setattr(runtime.docker, "start_container", lambda options: calls.append(("start", options.image)))
    monkeypatch.setattr(runtime, "wait_for_jupyter", lambda options: True)

    runtime.up()

    assert calls[0] == ("pull", "ghcr.io/mihneateodorstoica/dsml-kit:minimal")
    assert ("start", "ghcr.io/mihneateodorstoica/dsml-kit:minimal") in calls


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
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: False)
    monkeypatch.setattr(runtime.docker, "start_container", lambda options: calls.append(("start", options.image)))
    monkeypatch.setattr(runtime, "wait_for_jupyter", lambda options: True)

    runtime.up()

    assert calls[0] == ("build", "example/dsml-kit:local", False)
    assert ("start", "example/dsml-kit:local") in calls


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


def test_up_reuses_matching_stopped_container(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    data = config.read_config(tmp_path / "dsml.toml")
    options = runtime.run_options(tmp_path, data)
    signature = runtime.container_signature(options, image_id="sha256:test", token_policy="auto")
    calls = []

    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: True)
    monkeypatch.setattr(runtime.docker, "container_label", lambda name, label: signature)
    monkeypatch.setattr(runtime.docker, "container_env_value", lambda name, key: "existing-token")
    monkeypatch.setattr(runtime.docker, "container_running", lambda name: False)
    monkeypatch.setattr(
        runtime.docker,
        "start_existing_container",
        lambda name, attach=False: calls.append(("start_existing", name, attach)),
    )
    monkeypatch.setattr(runtime.docker, "start_container", lambda options: pytest.fail("should not recreate"))
    monkeypatch.setattr(runtime.docker, "remove_container", lambda name, force=False: pytest.fail("should not remove"))

    def wait_for_jupyter(options):
        assert options.token == "existing-token"
        return True

    monkeypatch.setattr(runtime, "wait_for_jupyter", wait_for_jupyter)

    runtime.up()

    assert calls == [("start_existing", options.container_name, False)]


def test_up_recreates_container_when_signature_changes(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: True)
    monkeypatch.setattr(runtime.docker, "image_id", lambda image: "sha256:test")
    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: True)
    monkeypatch.setattr(runtime.docker, "container_label", lambda name, label: "old-signature")
    monkeypatch.setattr(
        runtime.docker,
        "remove_container",
        lambda name, force=False: calls.append(("remove", name, force)) or completed(["docker", "rm"]),
    )
    monkeypatch.setattr(runtime.docker, "start_container", lambda options: calls.append(("start", options.container_name)))
    monkeypatch.setattr(runtime, "wait_for_jupyter", lambda options: True)

    runtime.up()

    name = paths.default_container_name(tmp_path)
    assert calls == [("remove", name, True), ("start", name)]


def test_down_stops_without_removing_container(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    monkeypatch.setattr(runtime.docker, "container_exists", lambda name: True)
    monkeypatch.setattr(runtime.docker, "container_running", lambda name: True)
    monkeypatch.setattr(
        runtime.docker,
        "stop_container",
        lambda name: calls.append(("stop", name)) or completed(["docker", "stop"]),
    )
    monkeypatch.setattr(runtime.docker, "remove_container", lambda name, force=False: pytest.fail("should not remove"))

    runtime.down()

    assert calls == [("stop", paths.default_container_name(tmp_path))]


def test_clean_stops_then_removes_project_containers(tmp_path, monkeypatch):
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []
    container_name = paths.default_container_name(tmp_path)

    monkeypatch.setattr(runtime.docker, "list_project_containers", lambda project_root: [container_name])
    monkeypatch.setattr(runtime.docker, "container_running", lambda name: True)
    monkeypatch.setattr(
        runtime.docker,
        "stop_container",
        lambda name: calls.append(("stop", name)) or completed(["docker", "stop"]),
    )
    monkeypatch.setattr(
        runtime.docker,
        "remove_container",
        lambda name, force=False: calls.append(("remove", name, force)) or completed(["docker", "rm"]),
    )

    runtime.clean()

    assert calls == [("stop", container_name), ("remove", container_name, False)]
