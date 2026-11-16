"""Datasets for the tests of t.vect.export

The absolute dataset vx_abs has three point maps of one month each from
2001-01-01. Map vx_k has two points at (k, 1) and (k, 2) with the columns
value = 10 k + i (i = 1, 2) and name = "k_i" for point i.

The relative dataset vx_rel has the maps vx_r1 and vx_r2 in the years 1 to 2
and 2 to 3, each with one point at (1, 1) and (2, 2) and value 5 and 6.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, register_stds, vector_points


@pytest.fixture(autouse=True)
def _work_in_tmp_path(tmp_path, monkeypatch):
    # The default of directory is /tmp, the archive of a relative output goes
    # to the current directory.
    monkeypatch.chdir(tmp_path)


@pytest.fixture(scope="module")
def absolute(tools):
    """Three monthly maps (see above); returns the name of the dataset"""
    for k in (1, 2, 3):
        vector_points(
            tools,
            f"vx_{k}",
            [(k, 1), (k, 2)],
            attributes={
                "value": [10 * k + 1, 10 * k + 2],
                "name": [f"{k}_1", f"{k}_2"],
            },
        )
    register_stds(
        tools,
        "stvds",
        "vx_abs",
        [
            MapSpec(f"vx_{k}", None, datetime(2001, k, 1), datetime(2001, k + 1, 1))
            for k in (1, 2, 3)
        ],
    )
    return "vx_abs"


@pytest.fixture(scope="module")
def relative(tools):
    """Two maps of one year in relative time; returns the name of the dataset"""
    for k, value in ((1, 5), (2, 6)):
        vector_points(
            tools, f"vx_r{k}", [(1, 1), (2, 2)], attributes={"value": [value, value]}
        )
    register_stds(
        tools,
        "stvds",
        "vx_rel",
        [MapSpec("vx_r1", None, 1, 2), MapSpec("vx_r2", None, 2, 3)],
        temporaltype="relative",
        unit="years",
    )
    return "vx_rel"
