from dsml import paths


def test_default_names_are_stable_and_prefixed(tmp_path):
    project = tmp_path / "My Project"
    project.mkdir()

    container = paths.default_container_name(project)
    volume = paths.default_home_volume(project)

    assert container.startswith("dsml-my-project-")
    assert volume.startswith("dsml-home-my-project-")
    assert container == paths.default_container_name(project)


def test_default_container_name_does_not_duplicate_dsml_prefix(tmp_path):
    project = tmp_path / "dsml-kit"
    project.mkdir()

    container = paths.default_container_name(project)

    assert container.startswith("dsml-kit-")
    assert not container.startswith("dsml-dsml-kit-")


def test_resolve_mount_path_handles_relative_paths(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    assert paths.resolve_mount_path(project, ".") == project
    assert paths.resolve_mount_path(project, "workspace") == project / "workspace"


def test_compose_path_lives_under_project_state_dir(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    assert paths.state_dir(project) == project / ".dsml"
    assert paths.compose_path(project) == project / ".dsml" / "compose.yaml"
