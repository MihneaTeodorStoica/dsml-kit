from conftest import assert_run, free_port, wait_for_container_health, wait_for_http


def test_image_starts_and_serves_jupyter_api(image, image_container):
    port = free_port()
    token = "validate-token"

    assert_run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            image_container,
            "-e",
            f"JUPYTER_TOKEN={token}",
            "-p",
            f"127.0.0.1:{port}:8888",
            image,
        ]
    )

    wait_for_container_health(image_container)
    wait_for_http(f"http://127.0.0.1:{port}/api/status?token={token}")
