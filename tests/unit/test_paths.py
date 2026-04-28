from dsml import paths


def test_default_names_are_stable_and_prefixed(tmp_path):
    project = tmp_path / "My Project"
    project.mkdir()

    container = paths.default_container_name(project)
    volume = paths.default_home_volume(project)

    assert container.startswith("dsml-my-project-")
    assert volume.startswith("dsml-home-my-project-")
    assert container == paths.default_container_name(project)


def test_resolve_mount_path_handles_relative_paths(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    assert paths.resolve_mount_path(project, ".") == project
    assert paths.resolve_mount_path(project, "workspace") == project / "workspace"
