"""Datasets for the tests of t.rast.to.vect

The region has three rows and three columns of size 1, so the cell centres lie
at 0.5, 1.5 and 2.5 in both directions. A point of the output sits on the
centre of its cell and an area follows the cell borders (0 to 3).
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region


def quarter(index):
    """The first day of quarter index, counted from 2001-01-01"""
    month = 1 + 3 * index
    return datetime(2001 + (month - 1) // 12, (month - 1) % 12 + 1, 1)


@pytest.fixture(scope="module")
def quarterly(tools):
    """Four maps of three months with the constant values 100 to 400 and a
    fifth map without values; returns the name of the dataset"""
    small_region(tools, 3, 3)
    specs = [
        MapSpec(
            f"tv_q{index + 1}",
            str(100 * (index + 1)),
            quarter(index),
            quarter(index + 1),
        )
        for index in range(4)
    ]
    specs.append(MapSpec("tv_q5", "null()", quarter(4), quarter(5)))
    create_stds(tools, "strds", "tv_quarterly", specs)
    return "tv_quarterly"


@pytest.fixture(scope="module")
def shapes(tools):
    """Three daily maps: the first column holding 10 and the rest 20, a plus
    sign of five cells holding 1 on null, and the middle row holding 1 on null;
    returns the name of the dataset"""
    small_region(tools, 3, 3)
    create_stds(
        tools,
        "strds",
        "tv_shapes",
        [
            MapSpec("tv_halves", "if(col() == 1, 10, 20)", day(0), day(1)),
            MapSpec(
                "tv_plus", "if(row() == 2 || col() == 2, 1, null())", day(1), day(2)
            ),
            MapSpec("tv_row", "if(row() == 2, 1, null())", day(2), day(3)),
        ],
    )
    return "tv_shapes"


@pytest.fixture(scope="module")
def thin(tools):
    """Two daily maps of lines, the plus sign and the middle row; the lines
    are one cell wide, which r.to.vect needs for type=line; returns the name
    of the dataset"""
    small_region(tools, 3, 3)
    create_stds(
        tools,
        "strds",
        "tv_thin",
        [
            MapSpec(
                "tv_thin_plus",
                "if(row() == 2 || col() == 2, 1, null())",
                day(0),
                day(1),
            ),
            MapSpec("tv_thin_row", "if(row() == 2, 1, null())", day(1), day(2)),
        ],
    )
    return "tv_thin"
