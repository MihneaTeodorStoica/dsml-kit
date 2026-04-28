from dsml import doctor


def test_doctor_checks_docker_compose_v2(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor.docker, "docker_cli_exists", lambda: True)
    monkeypatch.setattr(doctor.docker, "daemon_reachable", lambda: True)
    monkeypatch.setattr(doctor.docker, "compose_cli_exists", lambda: False)

    checks = doctor.run_checks(tmp_path)

    compose_check = next(check for check in checks if check.name == "Docker Compose v2")
    assert not compose_check.ok
    assert "docker compose version" in compose_check.message
