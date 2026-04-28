from pathlib import Path

from dsml import docker


def options(tmp_path, **overrides):
    values = {
        "image": "example/dsml-kit:test",
        "container_name": "dsml-test",
        "project_root": tmp_path,
        "mount_path": tmp_path,
        "home_volume": "dsml-home-test",
        "port": 8899,
        "bind_address": "127.0.0.2",
        "root_dir": "/home/jovyan/work",
        "base_url": "/lab/",
        "token": "test-token",
        "host_uid": 1234,
        "host_gid": 4567,
    }
    values.update(overrides)
    return docker.DockerRunOptions(**values)


def test_run_args_capture_runtime_contract(tmp_path):
    args = docker.build_run_args(options(tmp_path))

    assert args[:3] == ["docker", "run", "-d"]
    assert "compose" not in args
    assert args[args.index("--name") + 1] == "dsml-test"
    assert "no-new-privileges:true" in args
    assert f"{Path(tmp_path)}:/home/jovyan/work" in args
    assert "dsml-home-test:/home/jovyan" in args
    assert "127.0.0.2:8899:8888" in args
    assert "JUPYTER_ROOT_DIR=/home/jovyan/work" in args
    assert "JUPYTER_BASE_URL=/lab/" in args
    assert "JUPYTER_TOKEN=test-token" in args
    assert "NB_UID=1234" in args
    assert "NB_GID=4567" in args
    assert args[-1] == "example/dsml-kit:test"


def test_gpu_run_args_add_nvidia_settings(tmp_path):
    args = docker.build_run_args(options(tmp_path, gpu=True))

    assert "--gpus" in args
    assert "all" == args[args.index("--gpus") + 1]
    assert "NVIDIA_VISIBLE_DEVICES=all" in args
    assert "NVIDIA_DRIVER_CAPABILITIES=all" in args


def test_attached_run_args_are_interactive(tmp_path):
    args = docker.build_run_args(options(tmp_path, detach=False))

    assert "-it" in args
    assert "-d" not in args
