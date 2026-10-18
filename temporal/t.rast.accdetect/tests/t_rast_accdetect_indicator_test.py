"""Test the indicator dataset of t.rast.accdetect

For every cell the indicator marks a run of occurrences: the start value where
the previous map has no occurrence, the end value where the next map has none,
the intermediate value between, and null where the cell has no occurrence. The
data are in conftest.py (range 10 to 50): the occurrence is, by day,
    0: N 0    1: 1 1    2: 2 N    3: 3 3    4: N 4    5: N N (empty)
so the first cell has one run (days 1 to 3) and the second two (days 0 to 1
and 3 to 4). N is null; the values below are start 1, intermediate 2, end 3.
"""

import pytest

from grass.temporal.testing.readback import list_maps, message
from grass.tools import ToolError

# Most tests make maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

N = None


@pytest.fixture
def indicate(tools, cells, by_day):
    """Function that runs t.rast.accdetect with an indicator and reads it"""

    def run(name, **options):
        options = {
            "input": cells,
            "start": "2001-01-01",
            "cycle": "6 days",
            "range": "10,50",
            **options,
        }
        tools.t_rast_accdetect(
            occurrence=f"{name}_occ",
            indicator=f"{name}_ind",
            basename=name,
            **options,
        )
        return by_day(f"{name}_ind")

    return run


def test_the_start_intermediate_and_end_values(indicate):
    # First cell: day 1 starts, day 2 continues, day 3 ends (day 4 has none).
    # Second cell: day 0 starts and day 1 ends; day 3 starts and day 4 ends.
    assert indicate("fwd") == {
        0: [N, 1],
        1: [1, 3],
        2: [2, N],
        3: [3, 1],
        4: [N, 3],
    }


def test_the_reverse_flag_marks_the_runs_from_the_end(indicate):
    # The runs are read from the last day: the start value is on the last day
    # of a run, the end value on its first day. The first day of the second
    # run of the second cell (day 0) is the last map computed: a run that goes
    # on there is marked as intermediate and not as end (see the test of the
    # last map below).
    assert indicate("rev", flags="r") == {
        0: [N, 2],
        1: [3, 1],
        2: [2, N],
        3: [1, 3],
        4: [N, 1],
    }


def test_the_n_flag_registers_the_empty_map(indicate):
    result = indicate("withn", flags="n")

    assert result[5] == [N, N]
    assert sorted(result) == [0, 1, 2, 3, 4, 5]


def test_the_values_of_staend_replace_the_defaults(indicate):
    # 1 becomes 7, 2 becomes 8 and 3 becomes 9.
    assert indicate("custom", staend="7,8,9") == {
        0: [N, 7],
        1: [7, 9],
        2: [8, N],
        3: [9, 7],
        4: [N, 9],
    }


def test_a_cycle_restarts_the_runs(indicate):
    # Cycles of three days. The occurrence of the cycle [0,3) is
    # 0: N 0   1: 1 1   2: 2 N, so the indicator is 0: N 1   1: 1 3   2: 2 N
    # (the first cell goes on at the end of the cycle). The cycle [3,6) has
    # 3: 0 0   4: N 1   5: empty, so 3: 1 1   4: N 3.
    assert indicate("cyc", cycle="3 days") == {
        0: [N, 1],
        1: [1, 3],
        2: [2, N],
        3: [1, 1],
        4: [N, 3],
    }


def test_today_a_run_that_goes_on_at_the_last_map_is_intermediate(indicate):
    # The first cell is in the range on the days 1 and 2 of the first cycle
    # and the cycle ends with the day 2: the last map has the value
    # intermediate, never the end value, because no later map shows that the
    # run ended. The manual does not say; this is the behavior of the tool.
    assert indicate("lastmap", cycle="3 days")[2][0] == 2


def test_the_names_of_the_indicator_maps(indicate, tools):
    indicate("named")

    names = [row.name for row in list_maps(tools, "strds", "named_ind")]
    assert names == [f"named_indicator_2001_01_0{day}" for day in range(1, 6)]


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        ("num%02", ["01", "02", "03", "04", "05"]),
        (
            "time",
            [
                "2001_01_01T00_00_00",
                "2001_01_02T00_00_00",
                "2001_01_03T00_00_00",
                "2001_01_04T00_00_00",
                "2001_01_05T00_00_00",
            ],
        ),
    ],
)
def test_the_suffix_of_the_indicator_maps(indicate, tools, suffix, names):
    output = "isuf_" + suffix[:3]

    indicate(output, suffix=suffix)

    listed = [row.name for row in list_maps(tools, "strds", f"{output}_ind")]
    assert listed == [f"{output}_indicator_{name}" for name in names]


def test_an_existing_indicator_is_not_overwritten(indicate, tools, cells):
    indicate("again")

    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(
            input=cells,
            occurrence="again_occ_new",
            indicator="again_ind",
            basename="again_new",
            start="2001-01-01",
            cycle="6 days",
            range="10,50",
        )

    assert "again_ind@PERMANENT> is already in the database" in message(error.value)
