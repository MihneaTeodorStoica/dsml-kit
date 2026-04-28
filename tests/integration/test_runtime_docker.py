import os
import uuid

from conftest import assert_run, free_port, run, wait_for_container_health, wait_for_http
from dsml import docker


UID_GID_AND_WORKSPACE_CHECK = """
from pathlib import Path
import os
import pwd

jovyan = pwd.getpwnam("jovyan")
expected_uid = int(os.environ["NB_UID"])
expected_gid = int(os.environ["NB_GID"])
if jovyan.pw_uid != expected_uid:
    raise SystemExit(f"jovyan uid {jovyan.pw_uid} != NB_UID {expected_uid}")
if jovyan.pw_gid != expected_gid:
    raise SystemExit(f"jovyan gid {jovyan.pw_gid} != NB_GID {expected_gid}")

path = Path(os.environ["JUPYTER_ROOT_DIR"]) / "uid-test.txt"
path.write_text("ok\\n")
"""


IMPORT_CONTRACT = """
import IPython
import duckdb
import ipykernel
import jupyterlab
import matplotlib
import notebook
import numpy
import pandas
import polars
import pyarrow
import scipy
import seaborn
import sklearn
import statsmodels
"""


def test_docker_runtime_serves_jupyter_and_writes_workspace_as_host_user(request, tmp_path, image):
    container_name = f"dsml-kit-runtime-{uuid.uuid4().hex[:8]}"
    home_volume = f"dsml-home-test-{uuid.uuid4().hex[:8]}"
    port = free_port()
    token = "validate-token"
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    def cleanup():
        run(["docker", "rm", "-f", container_name], check=False)
        run(["docker", "volume", "rm", home_volume], check=False)

    request.addfinalizer(cleanup)
    cleanup()

    options = docker.DockerRunOptions(
        image=image,
        container_name=container_name,
        project_root=tmp_path,
        mount_path=workspace,
        home_volume=home_volume,
        port=port,
        token=token,
        host_uid=os.getuid(),
        host_gid=os.getgid(),
        restart_policy="no",
    )
    assert_run(docker.build_run_args(options))

    wait_for_container_health(container_name)
    wait_for_http(f"http://127.0.0.1:{port}/api/status?token={token}")

    uid_result = assert_run(
        [
            "docker",
            "exec",
            "--user",
            "jovyan",
            container_name,
            "python",
            "-c",
            UID_GID_AND_WORKSPACE_CHECK,
        ]
    )
    assert uid_result.returncode == 0
    workspace_file = workspace / "uid-test.txt"
    assert workspace_file.exists()
    assert workspace_file.stat().st_uid == os.getuid()

    import_result = assert_run(
        [
            "docker",
            "exec",
            "--user",
            "jovyan",
            container_name,
            "python",
            "-c",
            IMPORT_CONTRACT,
        ]
    )
    assert import_result.returncode == 0
