from dsml import docker


class FakeContainer:
    def __init__(self):
        self.removed = False
        self.attrs = {
            "Config": {
                "Labels": {"dsml.project": "example"},
                "Env": ["JUPYTER_TOKEN=token"],
            }
        }

    def remove(self, *, force=False):
        self.removed = force


class FakeContainers:
    def __init__(self, container):
        self.container = container

    def get(self, name):
        return self.container


class FakeImage:
    id = "sha256:test"


class FakeImages:
    def __init__(self):
        self.pulled = []
        self.removed = []

    def get(self, image):
        return FakeImage()

    def pull(self, image):
        self.pulled.append(image)

    def remove(self, image):
        self.removed.append(image)


class FakeVolume:
    def __init__(self):
        self.removed = False

    def remove(self):
        self.removed = True


class FakeVolumes:
    def __init__(self, volume):
        self.volume = volume

    def get(self, name):
        return self.volume


class FakeClient:
    def __init__(self):
        self.container = FakeContainer()
        self.images = FakeImages()
        self.volume = FakeVolume()
        self.containers = FakeContainers(self.container)
        self.volumes = FakeVolumes(self.volume)

    def ping(self):
        return True


def test_sdk_backed_docker_helpers(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(docker, "sdk_client", lambda: client)

    assert docker.daemon_reachable() is True
    assert docker.image_exists("example:test") is True
    assert docker.image_id("example:test") == "sha256:test"
    assert docker.container_exists("dsml-test") is True
    assert docker.container_label("dsml-test", "dsml.project") == "example"
    assert docker.container_env_value("dsml-test", "JUPYTER_TOKEN") == "token"

    assert docker.pull_image("example:test").returncode == 0
    assert client.images.pulled == ["example:test"]

    assert docker.remove_image("example:test").returncode == 0
    assert client.images.removed == ["example:test"]

    assert docker.remove_container("dsml-test", force=True).returncode == 0
    assert client.container.removed is True

    assert docker.remove_volume("dsml-home").returncode == 0
    assert client.volume.removed is True
