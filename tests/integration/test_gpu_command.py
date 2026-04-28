from dsml import compose, docker


def test_gpu_compose_model_requests_all_gpus(tmp_path):
    service = compose.build_compose_model(
        docker.DockerRunOptions(
            image="dsml-kit:gpu",
            container_name="dsml-gpu-test",
            project_root=tmp_path,
            mount_path=tmp_path,
            home_volume="dsml-home-gpu-test",
            port=8888,
            gpu=True,
        )
    )["services"]["app"]

    assert service["environment"]["NVIDIA_VISIBLE_DEVICES"] == "all"
    assert service["environment"]["NVIDIA_DRIVER_CAPABILITIES"] == "all"
    assert service["deploy"]["resources"]["reservations"]["devices"][0]["count"] == "all"
    assert service["deploy"]["resources"]["reservations"]["devices"][0]["capabilities"] == ["gpu"]
