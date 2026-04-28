from dsml import docker


def test_gpu_command_requests_all_gpus(tmp_path):
    args = docker.build_run_args(
        docker.DockerRunOptions(
            image="dsml-kit:gpu",
            container_name="dsml-gpu-test",
            project_root=tmp_path,
            mount_path=tmp_path,
            home_volume="dsml-home-gpu-test",
            port=8888,
            gpu=True,
        )
    )

    assert "--gpus" in args
    assert args[args.index("--gpus") + 1] == "all"
