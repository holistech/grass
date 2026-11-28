"""Datasets for the tests of t.rast.out.vtk

The region has two rows and three columns of size 1. The dataset has three
maps: vt_a holds 10 in every cell (January), vt_b holds 1.5 in the first
column and nothing in the others (February) and vt_c holds 3 in every cell
(April, so March is a gap). The map vt_e holds row * 100 + column and serves as
the elevation: 101, 102, 103 in the northern row and 201, 202, 203 in the
southern one.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region


@pytest.fixture(autouse=True)
def _work_in_tmp_path(tmp_path, monkeypatch):
    # The tool changes into the export directory; files of a failing run
    # should not end up in the repository.
    monkeypatch.chdir(tmp_path)


@pytest.fixture(scope="module")
def vtk_input(tools):
    """The dataset and the elevation map described above; returns its name"""
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "vt_in",
        [
            MapSpec("vt_a", "10", datetime(2001, 1, 1), datetime(2001, 2, 1)),
            MapSpec(
                "vt_b",
                "if(col() == 1, 1.5, null())",
                datetime(2001, 2, 1),
                datetime(2001, 3, 1),
            ),
            MapSpec("vt_c", "3", datetime(2001, 4, 1), datetime(2001, 5, 1)),
        ],
    )
    tools.r_mapcalc(expression="vt_e = row() * 100 + col()", overwrite=True)
    return "vt_in"
