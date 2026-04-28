from pathlib import Path

import yaml

from dsml import compose, docker, paths


def options(tmp_path, **overrides):
    values = {
        "image": "example/dsml-kit:test",
        "container_name": "dsml-test",
        "project_root": tmp_path,
        "mount_path": tmp_path / "workspace",
        "home_volume": "dsml-home-test",
        "port": 8899,
        "bind_address": "127.0.0.2",
        "root_dir": "/home/jovyan/work",
        "base_url": "/lab/",
        "token": "test-token",
        "app_log_level": "INFO",
        "server_log_level": "DEBUG",
        "extra_args": ["--ServerApp.allow_origin=*", "--NotebookApp.terminals_enabled=True"],
        "host_uid": 1234,
        "host_gid": 4567,
        "run_signature": "signature-test",
    }
    values.update(overrides)
    return docker.DockerRunOptions(**values)


def test_compose_model_captures_runtime_contract(tmp_path):
    model = compose.build_compose_model(options(tmp_path))

    assert list(model["services"]) == ["app"]
    service = model["services"]["app"]
    assert service["image"] == "example/dsml-kit:test"
    assert service["container_name"] == "dsml-test"
    assert service["labels"] == {
        paths.PROJECT_LABEL: paths.project_name(tmp_path),
        paths.CONFIG_LABEL: str(Path(tmp_path) / paths.CONFIG_FILE),
        paths.RUN_SIGNATURE_LABEL: "signature-test",
    }
    assert service["restart"] == "unless-stopped"
    assert service["user"] == "root"
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert service["working_dir"] == "/home/jovyan/work"
    assert service["ports"] == ["127.0.0.2:8899:8888"]
    assert service["volumes"] == [
        {
            "type": "bind",
            "source": str(Path(tmp_path) / "workspace"),
            "target": "/home/jovyan/work",
        },
        {
            "type": "volume",
            "source": "dsml-home-test",
            "target": "/home/jovyan",
        },
    ]
    assert service["environment"] == {
        "JUPYTER_APP_LOG_LEVEL": "INFO",
        "JUPYTER_SERVER_LOG_LEVEL": "DEBUG",
        "JUPYTER_ROOT_DIR": "/home/jovyan/work",
        "JUPYTER_BASE_URL": "/lab/",
        "JUPYTER_EXTRA_ARGS": "--ServerApp.allow_origin=* --NotebookApp.terminals_enabled=True",
        "JUPYTER_TOKEN": "test-token",
        "NB_UID": "1234",
        "NB_GID": "4567",
        "CHOWN_HOME": "yes",
        "CHOWN_HOME_OPTS": "-R",
        "CHOWN_EXTRA": "/home/jovyan/work",
        "CHOWN_EXTRA_OPTS": "-R",
        "UV_SYSTEM_PYTHON": "1",
    }
    assert model["volumes"] == {"dsml-home-test": {"name": "dsml-home-test"}}


def test_compose_model_omits_empty_run_signature_label(tmp_path):
    service = compose.build_compose_model(options(tmp_path, run_signature=""))["services"]["app"]

    assert paths.RUN_SIGNATURE_LABEL not in service["labels"]


def test_gpu_compose_model_adds_nvidia_reservation_and_environment(tmp_path):
    service = compose.build_compose_model(options(tmp_path, gpu=True))["services"]["app"]

    assert service["environment"]["NVIDIA_VISIBLE_DEVICES"] == "all"
    assert service["environment"]["NVIDIA_DRIVER_CAPABILITIES"] == "all"
    assert service["deploy"]["resources"]["reservations"]["devices"] == [
        {
            "driver": "nvidia",
            "count": "all",
            "capabilities": ["gpu"],
        }
    ]


def test_render_compose_yaml_is_deterministic_and_parseable(tmp_path):
    model = compose.build_compose_model(options(tmp_path))
    first = compose.render_compose_yaml(model)
    second = compose.render_compose_yaml(model)

    assert first == second
    assert first.startswith("services:\n  app:\n")
    assert yaml.safe_load(first) == model


def test_write_compose_file_uses_project_state_dir(tmp_path):
    compose_file = compose.write_compose_file(tmp_path, options(tmp_path))

    assert compose_file == paths.compose_path(tmp_path)
    assert compose_file.read_text().startswith("services:\n  app:\n")


def test_compose_command_builders_include_project_and_file(tmp_path):
    compose_file = paths.compose_path(tmp_path)
    base = ["docker", "compose", "-p", paths.project_name(tmp_path), "-f", str(compose_file)]

    assert compose.compose_base_args(tmp_path, compose_file) == base
    assert compose.compose_up_args(tmp_path, compose_file, detach=True) == [*base, "up", "-d"]
    assert compose.compose_up_args(tmp_path, compose_file, detach=False) == [*base, "up"]
    assert compose.compose_stop_args(tmp_path, compose_file) == [*base, "stop"]
    assert compose.compose_down_args(tmp_path, compose_file) == [*base, "down"]
    assert compose.compose_down_args(tmp_path, compose_file, volumes=True) == [*base, "down", "-v"]
    assert compose.compose_logs_args(tmp_path, compose_file, follow=True, tail=20) == [
        *base,
        "logs",
        "--follow",
        "--tail",
        "20",
        "app",
    ]
    assert compose.compose_exec_args(tmp_path, compose_file, ["python", "-V"], user="jovyan") == [
        *base,
        "exec",
        "-T",
        "--user",
        "jovyan",
        "app",
        "python",
        "-V",
    ]
    assert compose.compose_exec_args(
        tmp_path,
        compose_file,
        ["/bin/bash"],
        user="jovyan",
        interactive=True,
    ) == [*base, "exec", "--user", "jovyan", "app", "/bin/bash"]
