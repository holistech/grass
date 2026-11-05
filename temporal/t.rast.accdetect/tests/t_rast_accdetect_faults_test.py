"""Test the indicator of t.rast.accdetect for a stretch of a single map

The indicator marks the first map of a stretch with the start value and the
last with the end value. A stretch of one map has only that one map, and it
gets the start value, never the end value; so does a map that is alone in its
cycle.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import cell_values, list_maps

N = None
# Six daily maps from 2001-01-01 on a region of one row and four cells; 60 is
# outside the range 10 to 50. The cells, by column, are in the range on the
# days: 1 (inside the cycle), 0 (the first map of the cycle), 5 (the last
# map of the cycle), and 0 and 1 (a stretch of two maps).
IN_RANGE = ([1], [0], [5], [0, 1])


def column_values(days):
    return [20 if number in days else 60 for number in range(6)]


@pytest.fixture
def stretches(tools, prefix):
    small_region(tools, 1, 4)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_c{number}",
                "if(col() == 1, {}, if(col() == 2, {}, if(col() == 3, {}, {})))".format(
                    *(column_values(days)[number] for days in IN_RANGE)
                ),
                day(number),
                day(number + 1),
            )
            for number in range(6)
        ],
    )
    return f"{prefix}_in"


def indicator_by_day(tools, name):
    """The cells of every map by the day of its start; empty maps are removed"""
    return {
        (datetime.fromisoformat(row.start) - day(0)).days: cell_values(tools, row.name)
        for row in list_maps(tools, "strds", name)
    }


def test_single_map_stretch_indicator(tools, prefix, stretches):
    tools.t_rast_accdetect(
        input=stretches,
        occurrence=f"{prefix}_occ",
        indicator=f"{prefix}_ind",
        basename=prefix,
        start="2001-01-01",
        cycle="6 days",
        range="10,50",
    )

    # A stretch of one map is marked 1, wherever it lies in the cycle; the
    # stretch of two maps in the fourth cell is 1 and 3.
    assert indicator_by_day(tools, f"{prefix}_ind") == {
        0: [N, 1, N, 1],
        1: [1, N, N, 3],
        5: [N, N, 1, N],
    }


def test_map_alone_in_its_cycle_gets_start_value(tools, prefix, stretches):
    tools.t_rast_accdetect(
        input=stretches,
        occurrence=f"{prefix}_occ",
        indicator=f"{prefix}_ind",
        basename=prefix,
        start="2001-01-01",
        cycle="1 day",
        range="10,50",
    )

    # Every cycle holds one map, so the stretch of two maps is cut into two
    # stretches of one, each 1.
    assert indicator_by_day(tools, f"{prefix}_ind") == {
        0: [N, 1, N, 1],
        1: [1, N, N, 1],
        5: [N, N, 1, N],
    }
