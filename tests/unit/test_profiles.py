import pytest

from dsml import profiles


def test_loads_expected_profiles():
    loaded = profiles.load_profiles()

    assert {"dev", "minimal", "base", "extended", "gpu", "full"} <= set(loaded)
    assert loaded["dev"].image == "dsml-kit:dev"
    assert loaded["minimal"].gpu is False
    assert loaded["base"].image.endswith(":base")
    assert loaded["extended"].image.endswith(":extended")
    assert loaded["gpu"].gpu is True
    assert loaded["gpu"].image.endswith(":full")
    assert loaded["full"].gpu == "auto"


def test_unknown_profile_reports_available_names():
    with pytest.raises(profiles.ProfileError, match="Available profiles"):
        profiles.resolve_profile("unknown")
