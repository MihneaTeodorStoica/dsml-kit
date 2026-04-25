from conftest import wait_for_container_health, wait_for_http


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


def assert_compose_ok(result, diagnostics):
    if result.returncode != 0:
        raise AssertionError(
            f"compose command failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}\n{diagnostics()}"
        )


def test_compose_runtime_serves_jupyter_and_writes_workspace_as_host_user(compose_runtime):
    compose_runtime["run"]("config")
    compose_runtime["run"]("up", "-d", "--no-build")

    wait_for_container_health(compose_runtime["container_name"])
    wait_for_http(
        f"http://127.0.0.1:{compose_runtime['port']}/api/status?token={compose_runtime['token']}"
    )

    uid_result = compose_runtime["run"](
        "exec",
        "-T",
        "--user",
        "jovyan",
        "app",
        "python",
        "-c",
        UID_GID_AND_WORKSPACE_CHECK,
        check=False,
    )
    assert_compose_ok(uid_result, compose_runtime["diagnostics"])

    workspace_file = compose_runtime["workspace"] / "uid-test.txt"
    assert workspace_file.exists()
    assert workspace_file.stat().st_uid == compose_runtime["host_uid"]

    import_result = compose_runtime["run"](
        "exec",
        "-T",
        "--user",
        "jovyan",
        "app",
        "python",
        "-c",
        IMPORT_CONTRACT,
        check=False,
    )
    assert_compose_ok(import_result, compose_runtime["diagnostics"])
