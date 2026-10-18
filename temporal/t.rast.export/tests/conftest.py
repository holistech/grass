"""Datasets for the tests of t.rast.export

The region has two rows and three columns of size 1. The absolute dataset has
three maps of one month each:

- ex_a holds 10 in every cell (an integer map),
- ex_b holds 1.5 in the first column and 2.5 in the other two (a float map),
- ex_c holds 7 in the third column and nothing in the others.

The relative dataset has the two maps ex_r1 (all 3) and ex_r2 (all 4) in the
years 1 to 2 and 2 to 3.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region


@pytest.fixture(autouse=True)
def _work_in_tmp_path(tmp_path, monkeypatch):
    # The default of directory is the current directory, where the tool leaves
    # its working files when it fails.
    monkeypatch.chdir(tmp_path)


@pytest.fixture(scope="module")
def absolute(tools):
    """Three monthly maps (see above); returns the name of the dataset"""
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "ex_abs",
        [
            MapSpec("ex_a", "10", datetime(2001, 1, 1), datetime(2001, 2, 1)),
            MapSpec(
                "ex_b",
                "if(col() == 1, 1.5, 2.5)",
                datetime(2001, 2, 1),
                datetime(2001, 3, 1),
            ),
            MapSpec(
                "ex_c",
                "if(col() == 3, 7, null())",
                datetime(2001, 3, 1),
                datetime(2001, 4, 1),
            ),
        ],
    )
    return "ex_abs"


@pytest.fixture(scope="module")
def relative(tools):
    """Two maps of one year in relative time; returns the name of the dataset"""
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "ex_rel",
        [MapSpec("ex_r1", "3", 1, 2), MapSpec("ex_r2", "4", 2, 3)],
        temporaltype="relative",
        unit="years",
    )
    return "ex_rel"
