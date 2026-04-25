from conftest import assert_run


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


def test_key_packages_import_in_image(image):
    assert_run(["docker", "run", "--rm", "--entrypoint", "python", image, "-c", IMPORT_CONTRACT])
