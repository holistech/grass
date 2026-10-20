"""Test the occurrence dataset of t.rast.accdetect

A map of the occurrence holds, for each cell whose input value lies strictly
between the minimum and the maximum, the number of days from the start of the
cycle to the start of the map, and is null elsewhere. The data are described
in conftest.py; N below is null.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.tools import ToolError

# Most tests make maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

N = None


def test_the_occurrence_in_the_range(tools, cells, detect):
    # Day 5 holds no value in the range (5 and 5), so its map is empty and
    # not registered.
    assert detect("occ") == {
        0: [N, 0],
        1: [1, 1],
        2: [2, N],
        3: [3, 3],
        4: [N, 4],
    }


def test_the_n_flag_registers_the_empty_map(tools, cells, detect):
    result = detect("occn", flags="n")

    assert result[5] == [N, N]
    assert sorted(result) == [0, 1, 2, 3, 4, 5]


def test_the_bounds_of_the_range_are_not_part_of_it(tools, cells, detect):
    # From 20 to 40 only the 30 are inside: the first cell on the day 2 and
    # the second cell on the days 1 and 4.
    assert detect("bounds", range="20,40") == {
        1: [N, 1],
        2: [2, N],
        4: [N, 4],
    }


def test_a_range_with_the_bounds_the_wrong_way_finds_nothing(tools, cells, detect):
    assert detect("swapped", range="45,15") == {}


def test_a_cycle_restarts_the_count_of_days(tools, cells, detect):
    # Cycles of three days: [0,3) and [3,6). On the day 3 a new count starts.
    assert detect("cyc", cycle="3 days") == {
        0: [N, 0],
        1: [1, 1],
        2: [2, N],
        3: [0, 0],
        4: [N, 1],
    }


def test_an_offset_leaves_out_the_days_between_the_cycles(tools, cells, detect):
    # Cycles [0,2) and [3,5): the days 2 and 5 are in no cycle.
    assert detect("off", cycle="2 days", offset="1 day") == {
        0: [N, 0],
        1: [1, 1],
        3: [0, 0],
        4: [N, 1],
    }


def test_stop_ends_the_last_cycle(tools, cells, detect):
    # Maps that start before the 4th of January: the days 0, 1 and 2.
    assert detect("stop", stop="2001-01-04") == {
        0: [N, 0],
        1: [1, 1],
        2: [2, N],
    }


def test_the_start_moves_the_first_cycle(tools, cells, detect):
    # From the 3rd of January the days count from 2.
    assert detect("later", start="2001-01-03") == {
        2: [0, N],
        3: [1, 1],
        4: [N, 2],
    }


def test_the_reverse_flag_keeps_the_days_since_the_start(tools, cells, detect):
    # The occurrence does not depend on the direction.
    assert detect("rev", flags="r") == detect("fwd")


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        (
            "gran",
            ["2001_01_01", "2001_01_02", "2001_01_03", "2001_01_04", "2001_01_05"],
        ),
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
        ("count%03", ["001", "002", "003", "004", "005"]),
        ("num", ["00001", "00002", "00003", "00004", "00005"]),
    ],
)
def test_the_suffix_of_the_names(tools, cells, detect, suffix, names):
    output = "suf_" + suffix.replace("%", "")

    detect(output, suffix=suffix)

    listed = [row.name for row in list_maps(tools, "strds", output)]
    assert listed == [f"{output}_{name}" for name in names]


def test_the_numeric_suffix_counts_in_the_order_of_the_computation(
    tools, cells, detect
):
    # With -r the map of the last day gets the number 1.
    detect("revnum", suffix="num%02", flags="r")

    names = {row.start[:10]: row.name for row in list_maps(tools, "strds", "revnum")}
    assert names["2001-01-05"] == "revnum_02"
    assert names["2001-01-01"] == "revnum_06"


@pytest.fixture(scope="module")
def thresholds(tools, cells):
    """Minimum and maximum datasets

    - det_min_all: one map 25 over the six days, det_max_all: one map 45.
    - det_min_step: 15 for the days 0 to 2, 35 for the days 3 to 5.
    - det_equal_min: a map of 100 on each day (equal in time to the input).
    """
    create_stds(
        tools, "strds", "det_min_all", [MapSpec("det_min_a", 25, day(0), day(6))]
    )
    create_stds(
        tools, "strds", "det_max_all", [MapSpec("det_max_a", 45, day(0), day(6))]
    )
    create_stds(
        tools,
        "strds",
        "det_min_step",
        [
            MapSpec("det_ms0", 15, day(0), day(3)),
            MapSpec("det_ms1", 35, day(3), day(6)),
        ],
    )
    create_stds(
        tools,
        "strds",
        "det_equal_min",
        [MapSpec(f"det_em{k}", 100, day(k), day(k + 1)) for k in range(6)],
    )


def test_the_minimum_and_maximum_datasets_replace_the_range(
    tools, cells, thresholds, detect
):
    # Between 25 and 45: the first cell holds 30 and 40 (days 2 and 3), the
    # second 30 (days 1 and 4).
    result = detect(
        "both", minimum="det_min_all", maximum="det_max_all", range="0,1000"
    )

    assert result == {1: [N, 1], 2: [2, N], 3: [3, N], 4: [N, 4]}


def test_a_minimum_dataset_that_changes_over_time(tools, cells, thresholds, detect):
    # Minimum 15 on the days 0 to 2, 35 from the day 3, no maximum: day 0 only
    # the second cell (20), day 1 both (20, 30), day 2 the first (30), day 3
    # the first (40); on the days 4 and 5 nothing exceeds 35.
    result = detect("minstep", minimum="det_min_step", range="0,1000")

    assert result == {0: [N, 0], 1: [1, 1], 2: [2, N], 3: [3, N]}


def test_a_maximum_dataset_alone(tools, cells, thresholds, detect):
    # Maximum 45 for all days with the range minimum 25: as the case above.
    result = detect("maxall", maximum="det_max_all", range="25,0")

    assert result == {1: [N, 1], 2: [2, N], 3: [3, N], 4: [N, 4]}


def test_a_threshold_map_of_the_same_time_is_used(tools, cells, thresholds, detect):
    # Minimum 100 on each day: nothing lies above it.
    assert detect("eq", minimum="det_equal_min", range="10,50") == {}


@pytest.fixture(scope="module")
def half_day_minimum(tools, cells):
    """A minimum of 100 from the noon of day 2 to the noon of day 3

    The granule of day 2 overlaps the map, the map overlaps the granule of
    day 3; the manual names both relations, overlaps and overlapped.
    """
    create_stds(
        tools,
        "strds",
        "det_half_min",
        [MapSpec("det_half_min_map", 100, day(2, hours=12), day(3, hours=12))],
    )
    return "det_half_min"


def test_a_threshold_map_that_the_granule_overlaps_last_is_used(
    tools, cells, half_day_minimum, detect
):
    # Day 3 (40, 20) also lies below the minimum 100.
    result = detect("ov", minimum=half_day_minimum, range="10,50")

    assert result == {0: [N, 0], 1: [1, 1], 4: [N, 4]}


def test_the_reverse_flag_takes_the_threshold_of_the_day(
    tools, cells, thresholds, detect
):
    result = detect("rev_ok", minimum="det_min_step", range="0,1000", flags="r")

    assert result == detect("fwd_ok", minimum="det_min_step", range="0,1000")


@pytest.fixture(scope="module")
def maximum_step(tools, cells):
    """A maximum of 25 for the days 0 to 2 and 45 for the days 3 to 5"""
    create_stds(
        tools,
        "strds",
        "det_max_step",
        [
            MapSpec("det_xs0", 25, day(0), day(3)),
            MapSpec("det_xs1", 45, day(3), day(6)),
        ],
    )


def test_the_reverse_flag_takes_the_maximum_of_the_day(
    tools, cells, maximum_step, detect
):
    # Above 10 and below the maximum of the day: day 0 (cells 5, 20) only the
    # second cell, day 1 (20, 30) the first, day 2 (30, 5) none, day 3 (40,
    # 20) both, day 4 (5, 30) the second, day 5 none. A maximum read from the
    # mirrored day would also let the second cell of day 1 (30) pass.
    result = detect("rev_max", maximum="det_max_step", range="10,0", flags="r")

    assert result == {0: [N, 0], 1: [1, N], 3: [3, 3], 4: [N, 4]}


def test_today_minimum_and_maximum_datasets_without_a_range_end_with_a_traceback(
    tools, cells, thresholds, detect
):
    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(
            input="det_cells",
            occurrence="norange",
            basename="norange",
            start="2001-01-01",
            cycle="6 days",
            minimum="det_min_all",
            maximum="det_max_all",
        )

    assert "IndexError: list index out of range" in message(error.value)


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.accdetect with minimum and maximum datasets but no range ends in an IndexError",
)
def test_minimum_and_maximum_datasets_work_without_a_range(
    tools, cells, thresholds, detect
):
    result = detect(
        "norange_ok", minimum="det_min_all", maximum="det_max_all", range=None
    )

    assert result == {1: [N, 1], 2: [2, N], 3: [3, N], 4: [N, 4]}


def test_the_occurrence_dataset_copies_the_description_of_the_input(
    tools, cells, detect
):
    detect("attrs")

    info = stds_info(tools, "strds", "attrs")
    assert info["semantic_type"] == "mean"
    assert info["granularity"] == "'1 day'"
    assert info["number_of_maps"] == 5
