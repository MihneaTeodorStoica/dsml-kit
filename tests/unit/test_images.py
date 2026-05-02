from dsml import images


def test_build_image_uses_base_requirements_by_default(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(images.paths, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(images.docker, "run", lambda args: calls.append(args))

    images.build_image(tag="example:test")

    assert calls == [
        [
            "docker",
            "build",
            "-f",
            str(tmp_path / "images" / "base" / "Dockerfile"),
            "-t",
            "example:test",
            "--build-arg",
            "DSML_REQUIREMENTS=requirements-base.txt",
            str(tmp_path),
        ]
    ]


def test_build_image_allows_custom_requirements_variant(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(images.paths, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(images.docker, "run", lambda args: calls.append(args))

    images.build_image(
        tag="example:full",
        target="runtime",
        build_args={"DSML_REQUIREMENTS": "requirements-full.txt"},
    )

    assert "--target" in calls[0]
    assert "runtime" in calls[0]
    assert "DSML_REQUIREMENTS=requirements-full.txt" in calls[0]
