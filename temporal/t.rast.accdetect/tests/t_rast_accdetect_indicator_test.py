"""Test the indicator dataset of t.rast.accdetect

For every cell the indicator marks a run of occurrences: the start value where
the previous map has no occurrence, the end value where the next map has none
or the cycle ends, the intermediate value between, and null where the cell has
no occurrence. The data are in conftest.py (range 10 to 50): the occurrence is, by day,
    0: N 0    1: 1 1    2: 2 N    3: 3 3    4: N 4    5: N N (empty)
so the first cell has one run (days 1 to 3) and the second two (days 0 to 1
and 3 to 4). N is null; the values below are start 1, intermediate 2, end 3.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
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
    # of a run, the end value on its first day. Day 0 is the last map computed
    # and the end of the cycle: the run of the second cell goes on there and
    # ends (see the test of the last map below).
    assert indicate("rev", flags="r") == {
        0: [N, 3],
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


def test_an_empty_staend_takes_the_defaults(indicate):
    # The parser gives an empty staend its default, so the tool needs no
    # check of its own for it.
    assert indicate("blank", staend="") == indicate("blank_default")


def test_a_cycle_restarts_the_runs(indicate):
    # Cycles of three days. The occurrence of the cycle [0,3) is
    # 0: N 0   1: 1 1   2: 2 N, so the indicator is 0: N 1   1: 1 3   2: 3 N
    # (the first cell goes on at the end of the cycle and ends there, see the
    # test of the last map below). The cycle [3,6) has 3: 0 0   4: N 1   5:
    # empty, so 3: 1 1   4: N 3.
    assert indicate("cyc", cycle="3 days") == {
        0: [N, 1],
        1: [1, 3],
        2: [3, N],
        3: [1, 1],
        4: [N, 3],
    }


def test_a_run_that_goes_on_at_the_last_map_of_a_cycle_ends(indicate):
    # Cycles of three days, occurrence by day (N is null):
    #   cycle [0,3)   0: N 0   1: 1 1   2: 2 N
    #   cycle [3,6)   3: 0 0   4: N 1   5: empty
    # The first cell is in the range on the days 1 and 2 and the cycle ends
    # with the day 2: the run ends there, with the end value 3 (the day 3
    # starts a run of its own in the next cycle). The second cell has the
    # runs 0 to 1 (start 1 on the day 0, end 3 on the day 1) and 3 to 4.
    assert indicate("lastmap", cycle="3 days") == {
        0: [N, 1],
        1: [1, 3],
        2: [3, N],
        3: [1, 1],
        4: [N, 3],
    }


def test_a_run_that_goes_on_at_the_first_map_of_a_cycle_ends_with_the_flag_r(
    indicate,
):
    # The same cycles, computed from the last day of each cycle back. Cycle
    # [0,3), computed 2, 1, 0: the first cell has the start 1 on the day 2 and
    # the end 3 on the day 1 (day 0 is null). The second cell is null on the
    # day 2, starts on the day 1 (1) and goes on at the day 0, the last map
    # computed in the cycle: the end value 3. Cycle [3,6), computed 5, 4, 3:
    # the first cell is in the range only on the day 3, the last map computed,
    # where the previous map (day 4) has none: start 1. The second cell is
    # null on the day 5, starts on the day 4 (1) and ends on the day 3 (3).
    assert indicate("lastmaprev", cycle="3 days", flags="r") == {
        0: [N, 3],
        1: [3, 1],
        2: [1, N],
        3: [1, 3],
        4: [N, 1],
    }


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


def test_the_indicator_maps_of_relative_time(tools, cells):
    # Three maps of 20, one per day: every cell is in the range on the days
    # 0, 1 and 2, one run from the start value to the end value. The
    # indicator maps take the time and the unit of their input maps.
    create_stds(
        tools,
        "strds",
        "ind_relative",
        [MapSpec(f"ind_r{k}", 20, k, k + 1) for k in range(3)],
        temporaltype="relative",
        unit="days",
    )

    tools.t_rast_accdetect(
        input="ind_relative",
        occurrence="ind_rel_occ",
        indicator="ind_rel_ind",
        basename="ind_rel",
        start="0",
        cycle="3",
        range="10,50",
    )

    rows = list_maps(tools, "strds", "ind_rel_ind")
    assert [(row.start, row.end, row.min, row.max) for row in rows] == [
        (0, 1, 1, 1),
        (1, 2, 2, 2),
        (2, 3, 3, 3),
    ]
    info = tools.t_info(type="raster", input=rows[0].name, flags="g").keyval
    assert info["unit"] == "days"
