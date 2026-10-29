"""Test the accumulated values of t.rast.accumulate

The dataset has seven daily maps from 2001-01-01 with the values
5, 10, 20, 35, 20, 10, 5 on a region of two cells that hold the same value.
Each step adds the increment of one granule to the map of the step before, so
the expected values are running sums that the comments derive.

r.series.accumulate computes the increment from the mean of the maps of a
granule: gdd is mean - lower (not below 0), bedd the same with the mean cut at
the upper limit, huglin (mean + maximum) / 2 - lower and mean the mean itself.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import cell_values, list_maps, message, stds_info

# Most tests make maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

VALUES = [5, 10, 20, 35, 20, 10, 5]


def _text(offset):
    return day(offset).strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture(scope="module")
def daily(tools):
    """The dataset acc_daily and the thresholds acc_lower (10) and acc_upper (30)"""
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "acc_daily",
        [MapSpec(f"acc_d{k}", v, day(k), day(k + 1)) for k, v in enumerate(VALUES)],
    )
    # One map each over the first ten days, so every granule lies during it.
    for name, value in (("acc_lower", 10), ("acc_upper", 30)):
        create_stds(
            tools, "strds", name, [MapSpec(f"{name}_map", value, day(0), day(10))]
        )
    return "acc_daily"


def _accumulate(tools, output, **options):
    options = {
        "input": "acc_daily",
        "start": "2001-01-01",
        "cycle": "7 days",
        "limits": "0,40",
        **options,
    }
    tools.t_rast_accumulate(output=output, basename=output, **options)
    return [
        (row.name.removeprefix(f"{output}_"), row.start, row.end, row.min)
        for row in list_maps(tools, "strds", output)
    ]


def _values(rows):
    return [row[3] for row in rows]


# Increments of a day, from the values 5, 10, 20, 35, 20, 10, 5:
#   gdd, lower 0:  5 10 20 35 20 10 5       sums 5 15 35 70 90 100 105
#   gdd, lower 10: 0 0 10 25 10 0 0         sums 0 0 10 35 45 45 45
#   bedd, 10 to 30: 35 is cut to 30, so 0 0 10 20 10 0 0 and the sums
#                   0 0 10 30 40 40 40
# Two days: the granules [1,3), [3,5), [5,7), [7,9) hold the maps 5 10,
# 20 35, 20 10 and 5 with the means 7.5, 27.5, 15 and 5, so bedd (10 to 30)
# gives 0, 17.5, 5 and 0, and the sums 0, 17.5, 22.5, 22.5.
@pytest.mark.parametrize(
    ("options", "expected", "end", "granularity"),
    [
        (
            {"method": "gdd", "limits": "0,40"},
            [5, 15, 35, 70, 90, 100, 105],
            8,
            "'1 day'",
        ),
        (
            {"method": "gdd", "limits": "10,40"},
            [0, 0, 10, 35, 45, 45, 45],
            8,
            "'1 day'",
        ),
        (
            {"method": "bedd", "limits": "10,30"},
            [0, 0, 10, 30, 40, 40, 40],
            8,
            "'1 day'",
        ),
        # The thresholds of the datasets replace the limits.
        (
            {
                "method": "bedd",
                "limits": "0,40",
                "lower": "acc_lower",
                "upper": "acc_upper",
            },
            [0, 0, 10, 30, 40, 40, 40],
            8,
            "'1 day'",
        ),
        (
            {"method": "bedd", "limits": "10,30", "granularity": "2 days"},
            [0, 17.5, 22.5, 22.5],
            9,
            "'2 days'",
        ),
        (
            {
                "method": "bedd",
                "limits": "0,40",
                "lower": "acc_lower",
                "upper": "acc_upper",
                "granularity": "2 days",
            },
            [0, 17.5, 22.5, 22.5],
            9,
            "'2 days'",
        ),
        (
            {"method": "gdd", "limits": "0,40", "stop": "2001-01-05"},
            [5, 15, 35, 70],
            5,
            "'1 day'",
        ),
    ],
    ids=[
        "gdd",
        "gdd_lower_10",
        "bedd",
        "bedd_datasets",
        "bedd_2d",
        "bedd_2d_datasets",
        "stop",
    ],
)
def test_the_accumulation_of_the_old_suite(
    request, tools, daily, options, expected, end, granularity
):
    output = f"old_{request.node.callspec.id}"

    rows = _accumulate(tools, output, **options)

    assert _values(rows) == expected
    info = stds_info(tools, "strds", output)
    assert info["number_of_maps"] == len(expected)
    assert info["min_min"] == min(expected)
    assert info["max_max"] == max(expected)
    assert info["start_time"] == f"'{_text(0)}'"
    assert info["end_time"] == f"'{_text(end - 1)}'"
    assert info["granularity"] == granularity
    # The granules follow each other, so the topology of the result is valid.
    assert [row[2] for row in rows[:-1]] == [row[1] for row in rows[1:]]


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        ("gran", ["2001_01_01", "2001_01_02", "2001_01_03", "2001_01_04"]),
        ("num", ["00001", "00002", "00003", "00004"]),
        ("num%03", ["001", "002", "003", "004"]),
        (
            "time",
            [
                "2001_01_01T00_00_00",
                "2001_01_02T00_00_00",
                "2001_01_03T00_00_00",
                "2001_01_04T00_00_00",
            ],
        ),
    ],
)
def test_the_suffix_of_the_names(tools, daily, suffix, names):
    rows = _accumulate(
        tools, f"suf_{suffix.replace('%', '')}", suffix=suffix, stop="2001-01-05"
    )

    assert [row[0] for row in rows] == names
    # The day 7 map of the old suite was never made: the run stops on day 5.
    assert not tools.g_list(type="raster", pattern="suf_*_2001_01_07").stdout.split()


# One map per granule: the mean of 5, 10, 20, 35, 20, 10, 5 added up gives the
# same sums as gdd with the lower limit 0.
# Granules of two days hold 5 10, 20 35, 20 10 and 5: the means are 7.5, 27.5,
# 15 and 5 and the maxima 10, 35, 20 and 5.
#   mean:   7.5, 27.5, 15, 5          sums 7.5 35 50 55
#   huglin: (7.5 + 10) / 2 = 8.75, (27.5 + 35) / 2 = 31.25, (15 + 20) / 2 =
#           17.5, (5 + 5) / 2 = 5     sums 8.75 40 57.5 62.5
@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({"method": "mean"}, [5, 15, 35, 70, 90, 100, 105]),
        ({}, [5, 15, 35, 70, 90, 100, 105]),
        ({"method": "mean", "granularity": "2 days"}, [7.5, 35, 50, 55]),
        ({"method": "huglin", "granularity": "2 days"}, [8.75, 40, 57.5, 62.5]),
        ({"method": "huglin"}, [5, 15, 35, 70, 90, 100, 105]),
    ],
    ids=["mean", "default_is_mean", "mean_2d", "huglin_2d", "huglin_1d"],
)
def test_the_methods(tools, daily, options, expected):
    output = "meth_" + "_".join(str(v) for v in options.values()).replace(" ", "")

    assert _values(_accumulate(tools, output or "meth_default", **options)) == expected


# new = old * scale + shift, then gdd with lower 0:
#   scale 2, shift -10: 0 10 30 60 30 10 0      sums 0 10 40 100 130 140 140
#   scale 2:            10 20 40 70 40 20 10    sums 10 30 70 140 180 200 210
#   shift -5:           0 5 15 30 15 5 0        sums 0 5 20 50 65 70 70
@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({"scale": 2, "shift": -10}, [0, 10, 40, 100, 130, 140, 140]),
        ({"scale": 2}, [10, 30, 70, 140, 180, 200, 210]),
        ({"shift": -5}, [0, 5, 20, 50, 65, 70, 70]),
    ],
    ids=["scale_and_shift", "scale", "shift"],
)
def test_scale_and_shift(tools, daily, options, expected):
    output = "ss_" + "_".join(f"{k}{v}" for k, v in options.items()).replace("-", "m")

    assert _values(_accumulate(tools, output, method="gdd", **options)) == expected


def test_a_cycle_restarts_the_accumulation(tools, daily):
    # Cycles of three days: [1,4) sums 5 15 35, [4,7) 35 55 65, [7,10) 5.
    rows = _accumulate(tools, "cyc", method="gdd", cycle="3 days")

    assert _values(rows) == [5, 15, 35, 35, 55, 65, 5]


def test_an_offset_leaves_out_the_days_between_the_cycles(tools, daily):
    # The cycles [1,4) and [5,8): the map of the 4th has no cycle.
    rows = _accumulate(tools, "off", method="gdd", cycle="3 days", offset="1 day")

    assert [(row[1], row[3]) for row in rows] == [
        (_text(0), 5),
        (_text(1), 15),
        (_text(2), 35),
        (_text(4), 20),
        (_text(5), 30),
        (_text(6), 35),
    ]


def test_the_start_moves_the_first_cycle(tools, daily):
    # From the 3rd on: 20, 20 + 35, 55 + 20, 75 + 10, 85 + 5.
    rows = _accumulate(tools, "later", method="gdd", start="2001-01-03")

    assert [(row[1], row[3]) for row in rows] == [
        (_text(2), 20),
        (_text(3), 55),
        (_text(4), 75),
        (_text(5), 85),
        (_text(6), 90),
    ]


def test_a_start_before_the_data_gives_cycles_that_cut_the_data(tools, daily):
    # Cycles of seven days from 2000-12-30: the first holds the days 1 to 5
    # (5 15 35 70 90), the second the days 6 and 7 (10, 15).
    rows = _accumulate(tools, "early", method="gdd", start="2000-12-30", cycle="7 days")

    assert _values(rows) == [5, 15, 35, 70, 90, 10, 15]


@pytest.fixture(scope="module")
def sparse(tools):
    """acc_gap with daily maps on the 1st, 2nd, 6th and 7th of January 2001

    and acc_rel with maps from 0 to 1 and from 1 to 2 days.
    """
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "acc_gap",
        [MapSpec(f"acc_g{k}", 10, day(k), day(k + 1)) for k in (0, 1, 5, 6)],
    )
    create_stds(
        tools,
        "strds",
        "acc_rel",
        [MapSpec(f"acc_r{k}", 10, k, k + 1) for k in (0, 1)],
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
    "relative_stop_0": {
        "input": "acc_rel",
        "start": "0",
        "stop": "0",
        "cycle": "1",
        "granularity": "1",
    },
}


@pytest.mark.parametrize("window", EMPTY_WINDOWS.values(), ids=EMPTY_WINDOWS.keys())
def test_an_empty_result_warns_and_creates_no_dataset(tools, sparse, prefix, window):
    options = {"input": "acc_gap", "cycle": "7 days", "limits": "0,40", **window}

    result = tools.t_rast_accumulate(output=prefix, basename=prefix, **options)

    assert (
        f"No map was computed in any cycle. No space time dataset <{prefix}> "
        "was created." in message(result)
    )
    assert f"{prefix}@" not in tools.t_list(type="strds").text
    assert not tools.g_list(type="raster", pattern=f"{prefix}*").stdout.split()


def test_an_empty_result_keeps_an_existing_dataset_with_overwrite(tools, sparse):
    # As t.rast.aggregate (measured 29.10.2026 in grass --tmp-project XY: an
    # empty result with --overwrite warns and leaves the existing output
    # dataset and its maps as they were).
    options = {"input": "acc_gap", "cycle": "7 days", "limits": "0,40"}
    tools.t_rast_accumulate(
        output="kept", basename="kept", **options, start="2001-01-01"
    )
    before = list_maps(tools, "strds", "kept")

    result = tools.t_rast_accumulate(
        output="kept", basename="kept", **options, start="2002-01-01", overwrite=True
    )

    assert len(before) == 4
    assert list_maps(tools, "strds", "kept") == before
    assert sorted(tools.g_list(type="raster", pattern="kept_*").stdout.split()) == [
        row.name for row in before
    ]
    assert "No space time dataset <kept> was created." in message(result)


def test_the_reverse_flag_accumulates_from_the_end(tools, daily):
    # The sums run from the 7th to the 1st day: 5, 15, 35, 70, 90, 100, 105.
    rows = _accumulate(tools, "rev", method="gdd", flags="r")

    assert [(row[1], row[3]) for row in rows] == [
        (_text(0), 105),
        (_text(1), 100),
        (_text(2), 90),
        (_text(3), 70),
        (_text(4), 35),
        (_text(5), 15),
        (_text(6), 5),
    ]


def test_the_numeric_suffix_counts_in_the_order_of_the_computation(tools, daily):
    # With -r the first map computed is the one of the last day.
    rows = _accumulate(tools, "revnum", method="gdd", flags="r", suffix="num%03")

    by_name = {row[0]: row[1] for row in rows}
    assert by_name["001"] == _text(6)
    assert by_name["007"] == _text(0)


@pytest.fixture(scope="module")
def with_nulls(tools):
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "acc_nulls",
        [
            MapSpec(f"acc_n{k}", v, day(k), day(k + 1))
            for k, v in enumerate(["null()", "null()", 5])
        ],
    )
    create_stds(
        tools,
        "strds",
        "acc_hole",
        [
            MapSpec(f"acc_h{k}", v, day(k), day(k + 1))
            for k, v in enumerate([5, "null()", 10])
        ],
    )


def test_a_null_in_the_middle_keeps_the_sum(tools, with_nulls):
    # The second step has no value, so it keeps the 5 of the first: 5, 5, 15.
    rows = _accumulate(tools, "hole", input="acc_hole", method="gdd", cycle="3 days")

    assert _values(rows) == [5, 5, 15]


def test_a_null_at_the_start_makes_every_step_null(tools, with_nulls):
    # The first step has no value and no map to keep; the later steps add to
    # that null and stay null (measured 18.10.2026 with
    # t.rast.accumulate in a temporary project). Without -n the empty maps
    # are not registered and not kept.
    output = "lead"
    tools.t_rast_accumulate(
        input="acc_nulls",
        output=output,
        basename=output,
        start="2001-01-01",
        cycle="3 days",
        limits="0,40",
        method="gdd",
    )

    assert list_maps(tools, "strds", output) == []
    assert not tools.g_list(type="raster", pattern=f"{output}_*").stdout.split()


def test_the_n_flag_registers_the_empty_maps(tools, with_nulls):
    output = "leadn"
    tools.t_rast_accumulate(
        input="acc_nulls",
        output=output,
        basename=output,
        start="2001-01-01",
        cycle="3 days",
        limits="0,40",
        method="gdd",
        flags="n",
    )

    rows = list_maps(tools, "strds", output)
    assert [(row.start, row.min) for row in rows] == [
        (_text(0), None),
        (_text(1), None),
        (_text(2), None),
    ]
    assert cell_values(tools, rows[2].name) == [None, None]


@pytest.fixture(scope="module")
def cells(tools):
    """Two cells with their own inputs and thresholds

    The first cell holds 5 10 20 35 20 10 5 as acc_daily, the second
    10 20 30 40 30 20 10. The lower map is 10 and 0, the upper map 30 and 40.
    """
    small_region(tools, 1, 2)
    second = [10, 20, 30, 40, 30, 20, 10]
    create_stds(
        tools,
        "strds",
        "acc_cells",
        [
            MapSpec(f"acc_c{k}", f"if(col() == 1, {a}, {b})", day(k), day(k + 1))
            for k, (a, b) in enumerate(zip(VALUES, second, strict=True))
        ],
    )
    for name, expression in (
        ("acc_clower", "if(col() == 1, 10, 0)"),
        ("acc_cupper", "if(col() == 1, 30, 40)"),
    ):
        create_stds(
            tools,
            "strds",
            name,
            [MapSpec(f"{name}_map", expression, day(0), day(10))],
        )


def test_every_cell_has_its_own_thresholds(tools, cells):
    # First cell: lower 10 and upper 30 as in the bedd case above, sums
    # 0 0 10 30 40 40 40. Second cell: lower 0 and upper 40 cut nothing
    # (the values do not pass 40), so the increments are the values and the
    # sums 10 30 60 100 130 150 160.
    output = "percell"
    tools.t_rast_accumulate(
        input="acc_cells",
        output=output,
        basename=output,
        start="2001-01-01",
        cycle="7 days",
        limits="0,40",
        method="bedd",
        lower="acc_clower",
        upper="acc_cupper",
    )

    assert [
        cell_values(tools, row.name) for row in list_maps(tools, "strds", output)
    ] == [
        [0, 10],
        [0, 30],
        [10, 60],
        [30, 100],
        [40, 130],
        [40, 150],
        [40, 160],
    ]


# Five daily maps around the ends of the months, from the start of each day
# (day 0 is 2001-01-01) and with the value: 2001-02-27 (57) 1, 2001-02-28
# (58) 2, 2001-03-29 (87) 4, 2001-03-31 (89) 8 and 2001-04-29 (118) 16. The
# data end on 2001-04-30.
MONTH_ENDS = [(57, 1), (58, 2), (87, 4), (89, 8), (118, 16)]


@pytest.fixture(scope="module")
def month_ends(tools):
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "acc_month_ends",
        [MapSpec(f"acc_me{n}", v, day(n), day(n + 1)) for n, v in MONTH_ENDS],
    )


def _month_end_sums(tools, output, **options):
    """The (date, sum) of the result maps of monthly cycles from 2001-01-31"""
    tools.t_rast_accumulate(
        input="acc_month_ends",
        output=output,
        basename=output,
        start="2001-01-31",
        cycle="1 months",
        limits="0,100",
        method="gdd",
        **options,
    )
    return [(row.start[:10], row.min) for row in list_maps(tools, "strds", output)]


def test_monthly_cycles_from_day_31_count_from_the_start(tools, month_ends):
    # Cycle k runs from k to k + 1 months after January 31, counted from it:
    # [01-31, 02-28), [02-28, 03-31) and [03-31, 04-30). Chained from the end
    # of the cycle before, the later cycles would start on 03-28 and 04-28.
    # The sums are 1 | 2, 2 + 4 | 8, 8 + 16.
    assert _month_end_sums(tools, "me_cycle") == [
        ("2001-02-27", 1),
        ("2001-02-28", 2),
        ("2001-03-29", 6),
        ("2001-03-31", 8),
        ("2001-04-29", 24),
    ]


def test_monthly_cycles_and_offsets_from_day_31_count_from_the_start(tools, month_ends):
    # Cycle k runs from 2k to 2k + 1 months after January 31: [01-31, 02-28)
    # and [03-31, 04-30). The maps of 02-28 and 03-29 lie between the
    # cycles. Chained, the second cycle would be [03-28, 04-28). The sums are
    # 1 | 8, 8 + 16.
    assert _month_end_sums(tools, "me_offset", offset="1 months") == [
        ("2001-02-27", 1),
        ("2001-03-31", 8),
        ("2001-04-29", 24),
    ]


def test_a_monthly_cycle_with_an_offset_in_days_is_chained(tools, month_ends):
    # A month and a day do not add up to one step, so each cycle starts a
    # day after the end of the one before and lasts one month from its own
    # start: [01-31, 02-28), [03-01, 04-01) and [04-02, 05-02), cut to 04-30
    # at the end of the data. The map of 02-28 lies between the first two
    # cycles. The sums are 1 | 4, 4 + 8 | 16.
    assert _month_end_sums(tools, "me_days", offset="1 days") == [
        ("2001-02-27", 1),
        ("2001-03-29", 4),
        ("2001-03-31", 12),
        ("2001-04-29", 16),
    ]


@pytest.fixture(scope="module")
def month_granules(tools):
    """Daily maps on 2001-04-30 (day 119) 1, 2001-05-30 (149) 2, 2001-05-31 (150) 4"""
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "acc_month_granules",
        [
            MapSpec(f"acc_mg{n}", v, day(n), day(n + 1))
            for n, v in [(119, 1), (149, 2), (150, 4)]
        ],
    )


def test_monthly_granules_count_from_the_start_of_the_cycle(tools, month_granules):
    # Cycles of 89 days from January 1: [01-01, 03-31) holds no map, the
    # second cycle starts on 03-31 and is cut at the end of the data
    # (06-01). Its granules of one month count from 03-31: [03-31, 04-30),
    # [04-30, 05-31) and [05-31, 06-30). Chained, the third granule would
    # start on 05-30. The second granule holds the maps of 04-30 and 05-30
    # with the mean 1.5, the third the map of 05-31: sums 1.5 and 5.5.
    output = "me_granules"
    tools.t_rast_accumulate(
        input="acc_month_granules",
        output=output,
        basename=output,
        start="2001-01-01",
        cycle="89 days",
        granularity="1 months",
        limits="0,100",
        method="gdd",
    )

    rows = list_maps(tools, "strds", output)
    assert [(row.start[:10], row.min) for row in rows] == [
        ("2001-04-30", 1.5),
        ("2001-05-31", 5.5),
    ]
