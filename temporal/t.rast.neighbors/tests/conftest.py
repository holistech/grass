"""Maps and datasets for the tests of t.rast.neighbors

The region has three rows and three columns of size 1, so a 3 x 3 window
around the centre cell sees the whole map and the value of the centre cell
can be derived by hand. Cells are counted row by row from the upper left, so
the list of cell values has the centre at index 4 and the upper left corner at
index 0.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region

# The values of the ramp: 1 to 9 row by row.
RAMP = "double((row() - 1) * 3 + col())"
# The spike: 10 in the centre, 20 right of it, 40 in the upper left corner and
# 0 elsewhere. The weights of a window then act on three values only.
SPIKE = (
    "double(if(row() == 2 && col() == 2, 10, if(row() == 2 && col() == 3, 20, "
    "if(row() == 1 && col() == 1, 40, 0))))"
)


@pytest.fixture(scope="module")
def ramp(tools):
    """A dataset of one map, the ramp, with a semantic label; returns the name"""
    small_region(tools, 3, 3)
    create_stds(
        tools,
        "strds",
        "nbr_ramp",
        [MapSpec("nbr_ramp_map", RAMP, day(0), day(1), semantic_label="LBL_1")],
    )
    return "nbr_ramp"


@pytest.fixture(scope="module")
def spike(tools):
    """A dataset of one map, the spike; returns the name"""
    small_region(tools, 3, 3)
    create_stds(
        tools,
        "strds",
        "nbr_spike",
        [MapSpec("nbr_spike_map", SPIKE, day(0), day(1))],
    )
    return "nbr_spike"


@pytest.fixture(scope="module")
def daily(tools):
    """Four maps of one day: the ramp plus 0, 10, 20 and 30; returns the name"""
    small_region(tools, 3, 3)
    create_stds(
        tools,
        "strds",
        "nbr_daily",
        [
            MapSpec(f"nbr_d{k}", f"{RAMP} + {10 * k}", day(k), day(k + 1))
            for k in range(4)
        ],
    )
    return "nbr_daily"
