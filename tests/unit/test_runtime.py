import pytest

from dsml import config, runtime


def test_up_reports_missing_dev_image_before_docker_run(tmp_path, monkeypatch):
    data = config.default_config(profile="dev", image="dsml-kit:dev")
    data["workspace"]["gpu"] = False
    config.write_config(tmp_path / "dsml.toml", data)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runtime.docker, "image_exists", lambda image: False)

    with pytest.raises(runtime.RuntimeError, match="dsml image build --dev"):
        runtime.up()
