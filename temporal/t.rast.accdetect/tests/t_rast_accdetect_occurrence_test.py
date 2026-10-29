"""Test the occurrence dataset of t.rast.accdetect

A map of the occurrence holds, for each cell whose input value lies strictly
between the minimum and the maximum, the number of days from the start of the
cycle to the start of the map, and is null elsewhere. The data are described
in conftest.py; N below is null.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
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


def assert_nothing_found(tools, cells, name, **options):
    """Run t.rast.accdetect and check that it made no occurrence dataset

    Every occurrence map is empty then, so without -n none is registered and
    no dataset is created.
    """
    options = {"start": "2001-01-01", "cycle": "6 days", **options}
    result = tools.t_rast_accdetect(
        input=cells, occurrence=name, basename=name, **options
    )
    assert f"No space time dataset <{name}> was created." in message(result)
    assert f"{name}@" not in tools.t_list(type="strds").text
    assert not tools.g_list(type="raster", pattern=f"{name}_*").stdout.split()


def test_a_range_with_the_bounds_the_wrong_way_finds_nothing(tools, cells):
    assert_nothing_found(tools, cells, "swapped", range="45,15")


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


@pytest.fixture(scope="module")
def sparse(tools):
    """Two inputs with windows that hold no start of a map

    det_gap has daily maps on the 1st, 2nd, 6th and 7th of January 2001,
    det_rel relative maps from 0 to 1 and from 1 to 2 days, all of the value
    20 in the range 10 to 50.
    """
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "det_gap",
        [MapSpec(f"det_g{k}", 20, day(k), day(k + 1)) for k in (0, 1, 5, 6)],
    )
    create_stds(
        tools,
        "strds",
        "det_rel",
        [MapSpec(f"det_r{k}", 20, k, k + 1) for k in (0, 1)],
        temporaltype="relative",
        unit="days",
    )


# Each window holds no start of a map: the cycles start after the data,
# end before them, lie in the gap from the 3rd to the 6th, or end at once
# at the relative stop 0, which is not after the start.
EMPTY_WINDOWS = {
    "start_after_the_data": {"start": "2002-01-01"},
    "window_before_the_data": {"start": "2000-12-01", "stop": "2000-12-20"},
    "window_in_a_gap": {"start": "2001-01-03", "stop": "2001-01-06", "cycle": "3 days"},
    "relative_stop_0": {"input": "det_rel", "start": "0", "stop": "0", "cycle": "1"},
}


@pytest.mark.parametrize("window", EMPTY_WINDOWS.values(), ids=EMPTY_WINDOWS.keys())
def test_an_empty_result_warns_and_creates_no_dataset(tools, sparse, prefix, window):
    options = {"input": "det_gap", "cycle": "6 days", "range": "10,50", **window}

    result = tools.t_rast_accdetect(
        occurrence=f"{prefix}_occ",
        indicator=f"{prefix}_ind",
        basename=prefix,
        **options,
    )

    for name in (f"{prefix}_occ", f"{prefix}_ind"):
        assert (
            f"No map with values was computed in any cycle. No space time "
            f"dataset <{name}> was created." in message(result)
        )
        assert f"{name}@" not in tools.t_list(type="strds").text
    assert not tools.g_list(type="raster", pattern=f"{prefix}*").stdout.split()


def test_an_empty_result_keeps_existing_datasets_with_overwrite(tools, sparse):
    # As t.rast.aggregate (measured 29.10.2026 in grass --tmp-project XY: an
    # empty result with --overwrite warns and leaves the existing output
    # dataset and its maps as they were).
    options = {
        "input": "det_gap",
        "occurrence": "kept_occ",
        "indicator": "kept_ind",
        "basename": "kept",
        "cycle": "6 days",
        "range": "10,50",
    }
    tools.t_rast_accdetect(**options, start="2001-01-01")
    before = {
        name: list_maps(tools, "strds", name) for name in ("kept_occ", "kept_ind")
    }

    result = tools.t_rast_accdetect(**options, start="2002-01-01", overwrite=True)

    for name, rows in before.items():
        assert len(rows) == 4
        assert list_maps(tools, "strds", name) == rows
    assert sorted(tools.g_list(type="raster", pattern="kept_*").stdout.split()) == (
        sorted(row.name for rows in before.values() for row in rows)
    )
    for name in before:
        assert f"No space time dataset <{name}> was created." in message(result)


def test_an_empty_result_of_null_maps_warns_and_creates_no_dataset(tools, cells):
    # No value lies in the range 100 to 200, so every occurrence map and with
    # it every indicator map is null. Without -n none is registered.
    result = tools.t_rast_accdetect(
        input=cells,
        occurrence="nulls_occ",
        indicator="nulls_ind",
        basename="nulls",
        start="2001-01-01",
        cycle="6 days",
        range="100,200",
    )

    for name in ("nulls_occ", "nulls_ind"):
        assert f"No space time dataset <{name}> was created." in message(result)
        assert f"{name}@" not in tools.t_list(type="strds").text
    assert not tools.g_list(type="raster", pattern="nulls_*").stdout.split()


def test_an_empty_result_of_null_maps_keeps_existing_datasets(tools, cells):
    # The existing outputs hold maps named by their time; the null maps of
    # the second run are numbered, have other names and leave them as they
    # were.
    options = {
        "input": cells,
        "occurrence": "nkept_occ",
        "indicator": "nkept_ind",
        "basename": "nkept",
        "start": "2001-01-01",
        "cycle": "6 days",
    }
    tools.t_rast_accdetect(**options, range="10,50")
    before = {
        name: list_maps(tools, "strds", name) for name in ("nkept_occ", "nkept_ind")
    }

    result = tools.t_rast_accdetect(
        **options, range="100,200", suffix="num", overwrite=True
    )

    for name, rows in before.items():
        assert len(rows) == 5
        assert list_maps(tools, "strds", name) == rows
    assert sorted(tools.g_list(type="raster", pattern="nkept_*").stdout.split()) == (
        sorted(row.name for rows in before.values() for row in rows)
    )
    for name in before:
        assert f"No space time dataset <{name}> was created." in message(result)


def test_the_reverse_flag_keeps_the_days_since_the_start(tools, cells, detect):
    # The occurrence does not depend on the direction.
    assert detect("rev", flags="r") == detect("fwd")


# Five daily maps around the ends of the months, by the day of their start
# (day 0 is 2001-01-01): 2001-02-27 (57), 2001-02-28 (58), 2001-03-29 (87),
# 2001-03-31 (89) and 2001-04-29 (118). The data end on 2001-04-30.
MONTH_ENDS = [57, 58, 87, 89, 118]


@pytest.fixture(scope="module")
def month_ends(tools):
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "det_month_ends",
        [MapSpec(f"det_me{n}", 20, day(n), day(n + 1)) for n in MONTH_ENDS],
    )


@pytest.fixture
def detect_month_ends(tools, month_ends, by_day):
    """Function that detects monthly cycles from 2001-01-31 (day 30)"""

    def run(name, **options):
        tools.t_rast_accdetect(
            input="det_month_ends",
            occurrence=name,
            basename=name,
            start="2001-01-31",
            cycle="1 months",
            range="10,50",
            **options,
        )
        return by_day(name)

    return run


def test_monthly_cycles_from_day_31_count_from_the_start(detect_month_ends):
    # Cycle k runs from k to k + 1 months after January 31, counted from it:
    # [01-31, 02-28), [02-28, 03-31) and [03-31, 04-30), the days [30, 58),
    # [58, 89) and [89, 119). Chained from the end of the cycle before, the
    # later cycles would start on 03-28 and 04-28. The days since the start
    # of the cycle: 57 - 30, 58 - 58, 87 - 58, 89 - 89, 118 - 89.
    assert detect_month_ends("me_cycle") == {
        57: [27, 27],
        58: [0, 0],
        87: [29, 29],
        89: [0, 0],
        118: [29, 29],
    }


def test_monthly_cycles_and_offsets_from_day_31_count_from_the_start(
    detect_month_ends,
):
    # Cycle k runs from 2k to 2k + 1 months after January 31: [01-31, 02-28)
    # and [03-31, 04-30), the days [30, 58) and [89, 119). The maps of the
    # days 58 and 87 lie between the cycles. Chained, the second cycle would
    # be [03-28, 04-28).
    assert detect_month_ends("me_offset", offset="1 months") == {
        57: [27, 27],
        89: [0, 0],
        118: [29, 29],
    }


def test_a_monthly_cycle_with_an_offset_in_days_is_chained(detect_month_ends):
    # A month and a day do not add up to one step, so each cycle starts a
    # day after the end of the one before and lasts one month from its own
    # start: [01-31, 02-28), [03-01, 04-01) and [04-02, 05-02), the days
    # [30, 58), [59, 90) and [91, 121). The map of the day 58 lies between
    # the first two cycles.
    assert detect_month_ends("me_days", offset="1 days") == {
        57: [27, 27],
        87: [28, 28],
        89: [30, 30],
        118: [27, 27],
    }


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
        ("num%03", ["001", "002", "003", "004", "005"]),
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


def test_a_threshold_map_of_the_same_time_is_used(tools, cells, thresholds):
    # Minimum 100 on each day: nothing lies above it.
    assert_nothing_found(tools, cells, "eq", minimum="det_equal_min", range="10,50")


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


def test_minimum_and_maximum_datasets_work_without_a_range(
    tools, cells, thresholds, detect
):
    result = detect(
        "norange_ok", minimum="det_min_all", maximum="det_max_all", range=None
    )

    assert result == {1: [N, 1], 2: [2, N], 3: [3, N], 4: [N, 4]}


def test_a_granule_without_a_threshold_map_needs_a_range(
    tools, cells, thresholds, detect
):
    # The minimum covers the days 0 to 2 only, so the granule of day 3 has no
    # minimum map and, without a range, no value to fall back on.
    create_stds(
        tools,
        "strds",
        "det_min_part",
        [MapSpec("det_mp0", 15, day(0), day(3))],
    )

    with pytest.raises(ToolError) as error:
        detect("part", minimum="det_min_part", maximum="det_max_all", range=None)

    assert "No minimum map found for <det_c3@PERMANENT> and no range given" in message(
        error.value
    )
    assert "Traceback" not in message(error.value)


def test_the_occurrence_dataset_copies_the_description_of_the_input(
    tools, cells, detect
):
    detect("attrs")

    info = stds_info(tools, "strds", "attrs")
    assert info["semantic_type"] == "mean"
    assert info["granularity"] == "'1 day'"
    assert info["number_of_maps"] == 5


def test_the_threshold_lookup_does_not_depend_on_the_time_zone(
    zone_tools, zone_by_day, request
):
    # Without this the module would test one zone twice.
    zone = request.node.callspec.params["zone_tools"]
    offset = zone_tools.run_cmd(["date", "-d", "2001-01-01 12:00", "+%z"])
    assert offset.stdout.strip() == {"UTC": "+0000", "Asia/Kathmandu": "+0545"}[zone]

    # The result of the test of the minimum that changes over time.
    zone_tools.t_rast_accdetect(
        input="det_cells",
        occurrence="zone_occ",
        basename="zone_occ",
        start="2001-01-01",
        cycle="6 days",
        minimum="det_min_step",
        range="0,1000",
    )

    assert zone_by_day("zone_occ") == {
        0: [N, 0],
        1: [1, 1],
        2: [2, N],
        3: [3, N],
    }
