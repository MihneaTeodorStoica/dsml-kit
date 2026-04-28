import pytest

from dsml import backends, config


def test_resolve_backend_defaults_to_compose():
    backend = backends.resolve_backend(config.default_config())

    assert backend.name == "compose"


def test_resolve_backend_rejects_unknown_backend():
    data = config.default_config()
    data["runtime"]["backend"] = "docker"

    with pytest.raises(backends.BackendError, match="Unsupported runtime backend"):
        backends.resolve_backend(data)
