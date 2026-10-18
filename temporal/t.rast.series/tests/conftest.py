"""Datasets and helpers for the tests of t.rast.series

Every dataset lives in a region of one row and two cells, so the value of each
cell of a result can be derived by hand. No dataset uses the current date.
"""

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    day,
    intervals,
    small_region,
)
from grass.temporal.testing.readback import cell_values

# The values of the two cells in time order. The first series is 1, 2, 3, 4,
# 10 and the second 3, 2, 4, 5, 2: both have five distinct positions, the
# first has no repeated value (mode, diversity) and the second repeats the 2.
CELL1 = [1, 2, 3, 4, 10]
CELL2 = [3, 2, 4, 5, 2]

# Map names in time order. Their alphabetical order (a, b, c, d, e) is the
# time order 3, 1, 5, 4, 2, which lets order=name tell itself apart from the
# default order=start_time.
STAT_NAMES = ["ser_b", "ser_e", "ser_a", "ser_d", "ser_c"]


@pytest.fixture(scope="module")
def stats(tools):
    """Five daily maps with CELL1 and CELL2 as the two cells; returns the name"""
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "ser_stats",
        [
            MapSpec(
                STAT_NAMES[k],
                f"if(col() == 1, {CELL1[k]}, {CELL2[k]})",
                day(k),
                day(k + 1),
            )
            for k in range(5)
        ],
    )
    return "ser_stats"


@pytest.fixture(scope="module")
def monthly(tools):
    """Six monthly maps holding 100 to 600 in both cells; returns the name"""
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "ser_monthly",
        [
            MapSpec(f"ser_m{k + 1}", 100 * (k + 1), start, end)
            for k, (start, end) in enumerate(intervals(6))
        ],
    )
    return "ser_monthly"


@pytest.fixture
def series(tools, prefix):
    """Function that runs t.rast.series and reads the first cell values back

    run(input, **options) names the output after the test (<prefix>_o); with
    several outputs each is <prefix>_o<n>. Returns the cell values of each
    output map as a list of lists, in the order of the outputs.
    """

    def run(input, outputs=1, **options):
        names = (
            [f"{prefix}_o"]
            if outputs == 1
            else [f"{prefix}_o{n}" for n in range(outputs)]
        )
        tools.t_rast_series(input=input, output=",".join(names), **options)
        return [cell_values(tools, name) for name in names]

    return run
