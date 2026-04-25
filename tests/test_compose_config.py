import json

from conftest import assert_run


def compose_config_json(*compose_files, env_file, env):
    result = assert_run(
        [
            "docker",
            "compose",
            "--env-file",
            str(env_file),
            *(arg for compose_file in compose_files for arg in ("-f", compose_file)),
            "config",
            "--format",
            "json",
        ],
        env=env,
    )
    return json.loads(result.stdout)


def write_env_file(tmp_path, **overrides):
    values = {
        "COMPOSE_PROJECT_NAME": "dsml-kit-test",
        "CONTAINER_NAME": "dsml-kit-test-app",
        "GPU_DEVICES": "all",
        "HOST_GID": "4567",
        "HOST_UID": "1234",
        "IMAGE_NAME": "example/dsml-kit",
        "JUPYTER_BASE_URL": "/lab/",
        "JUPYTER_BIND_ADDRESS": "127.0.0.2",
        "JUPYTER_PORT": "8899",
        "JUPYTER_ROOT_DIR": "/home/jovyan/custom-work",
        "JUPYTER_TOKEN": "test-token",
        "NVIDIA_DRIVER_CAPABILITIES": "compute,utility",
        "PULL_POLICY": "never",
        "RESTART_POLICY": "no",
        "DSML_TAG": "test-tag",
        "WORKSPACE_DIR": str(tmp_path / "workspace"),
    }
    values.update(overrides)

    env_file = tmp_path / "compose.env"
    env_file.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
    return env_file, values


def test_default_compose_config_renders():
    assert_run(["docker", "compose", "-f", "compose.yaml", "config"])


def test_dev_compose_config_renders():
    assert_run(["docker", "compose", "-f", "compose.yaml", "-f", "compose.dev.yaml", "config"])


def test_gpu_compose_config_renders():
    assert_run(["docker", "compose", "-f", "compose.yaml", "-f", "compose.gpu.yaml", "config"])


def test_default_compose_config_resolves_runtime_contract(tmp_path):
    env_file, env = write_env_file(tmp_path)
    config = compose_config_json("compose.yaml", env_file=env_file, env=env)
    app = config["services"]["app"]

    assert config["name"] == "dsml-kit-test"
    assert app["container_name"] == "dsml-kit-test-app"
    assert app["image"] == "example/dsml-kit:test-tag"
    assert app["pull_policy"] == "never"
    assert app["restart"] == "no"
    assert app["security_opt"] == ["no-new-privileges:true"]
    assert app["user"] == "root"
    assert app["working_dir"] == "/home/jovyan/custom-work"

    assert app["ports"] == [
        {
            "mode": "ingress",
            "host_ip": "127.0.0.2",
            "target": 8888,
            "published": "8899",
            "protocol": "tcp",
        }
    ]
    assert app["volumes"][0]["target"] == "/home/jovyan/custom-work"
    assert app["environment"]["JUPYTER_BASE_URL"] == "/lab/"
    assert app["environment"]["JUPYTER_ROOT_DIR"] == "/home/jovyan/custom-work"
    assert app["environment"]["JUPYTER_TOKEN"] == "test-token"
    assert app["environment"]["NB_UID"] == "1234"
    assert app["environment"]["NB_GID"] == "4567"
    assert app["environment"]["CHOWN_EXTRA"] == "/home/jovyan/custom-work"


def test_gpu_compose_config_adds_gpu_runtime_settings(tmp_path):
    env_file, env = write_env_file(
        tmp_path, GPU_DEVICES="0", NVIDIA_DRIVER_CAPABILITIES="compute,utility,video"
    )
    config = compose_config_json("compose.yaml", "compose.gpu.yaml", env_file=env_file, env=env)
    app = config["services"]["app"]

    assert app["gpus"] == [{"count": -1}]
    assert app["environment"]["NVIDIA_VISIBLE_DEVICES"] == "0"
    assert app["environment"]["NVIDIA_DRIVER_CAPABILITIES"] == "compute,utility,video"
