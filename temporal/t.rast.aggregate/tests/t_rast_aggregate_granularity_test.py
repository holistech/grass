"""Test t.rast.aggregate with the granularities of the old gunittest suites

The dataset has seven maps of 14 days (absolute time) or 3 days (relative
time) that follow each other: ag1 to ag6 hold 100 to 600, ag7 is null. The
expected values are those of the old suites, derived again in the comments.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, stds_info

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _rows(tools, name):
    return [
        (row.name, row.start, row.end, row.min)
        for row in list_maps(tools, "strds", name)
    ]


@pytest.fixture(scope="module")
def absolute(tools):
    """ag1..ag7 from 2001-01-15 12:05:45, 14 days each, in <ag_abs>"""
    # ag_k lasts from start + 14 (k - 1) days to start + 14 k days, so ag1 is
    # 15 to 29 January, ag2 29 January to 12 February, ag3 12 to 26 February,
    # ag4 26 February to 12 March, ag5 12 to 26 March, ag6 26 March to 9
    # April and ag7 9 to 23 April (2001 is no leap year).
    start = day(14, hours=12)
    start = start.replace(minute=5, second=45)
    maps = [
        MapSpec(
            f"ag{k}",
            "null()" if k == 7 else 100.0 * k,
            start + (k - 1) * (day(14) - day(0)),
            start + k * (day(14) - day(0)),
        )
        for k in range(1, 8)
    ]
    create_stds(tools, "strds", "ag_abs", maps)
    return "ag_abs"


@pytest.fixture(scope="module")
def relative(tools):
    """ag_r1..ag_r7 as 3 day intervals from 0: [0,3), [3,6), ... [18,21)"""
    maps = [
        MapSpec(f"agr{k}", "null()" if k == 7 else 100 * k, 3 * (k - 1), 3 * k)
        for k in range(1, 8)
    ]
    create_stds(tools, "strds", "ag_rel", maps, temporaltype="relative", unit="days")
    return "ag_rel"


def _check(tools, name, expected):
    info = stds_info(tools, "strds", name)
    for key, value in expected.items():
        assert info[key] == value, key


def test_disaggregation_with_overlaps_and_empty_maps(tools, absolute):
    # Granules of 2 days from 2001-01-15 00:00:00. The grid runs until the
    # end of ag7, 2001-04-23 12:05:45, so 98.5 days or 50 granules reach
    # 2001-04-25. Every granule lies inside one 14 day map or straddles the
    # border of two, so each average is one of 100 to 600 or the mean of two
    # neighbours; the granules inside ag7 are null and -n registers them.
    tools.t_rast_aggregate(
        input=absolute,
        output="ag_dis",
        basename="ag_dis",
        granularity="2 days",
        method="average",
        sampling="overlaps,overlapped,during",
        nprocs=2,
        flags="n",
    )

    _check(
        tools,
        "ag_dis",
        {
            "start_time": "'2001-01-15 00:00:00'",
            "end_time": "'2001-04-25 00:00:00'",
            "granularity": "'2 days'",
            "aggregation_type": "average",
            "number_of_maps": 50,
            "map_time": "interval",
            "min_min": 100.0,
            "min_max": 600.0,
            "max_min": 100.0,
            "max_max": 600.0,
        },
    )
    rows = _rows(tools, "ag_dis")
    assert rows[0][3] == 100.0
    assert rows[-1][3] is None


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        ("gran", ["2001_01", "2001_02", "2001_03"]),
        (
            "time",
            ["2001_01_01T00_00_00", "2001_02_01T00_00_00", "2001_03_01T00_00_00"],
        ),
    ],
)
def test_one_month_maximum(tools, absolute, suffix, names):
    # A month holds the maps that lie wholly inside it: January ag1 (ag2 runs
    # into February), February ag3, March ag5 (ag4 and ag6 cross the
    # borders); April holds only the null ag7 and is dropped.
    tools.t_rast_aggregate(
        input=absolute,
        output=f"ag_month_{suffix}",
        basename=f"ag_month_{suffix}",
        granularity="1 months",
        method="maximum",
        sampling="contains",
        file_limit=0,
        nprocs=3,
        suffix=suffix,
    )

    rows = _rows(tools, f"ag_month_{suffix}")
    prefix = f"ag_month_{suffix}"
    assert [(row[0], row[3]) for row in rows] == [
        (f"{prefix}_{name}", value)
        for name, value in zip(names, [100.0, 300.0, 500.0], strict=True)
    ]
    _check(
        tools,
        f"ag_month_{suffix}",
        {
            "start_time": "'2001-01-01 00:00:00'",
            "end_time": "'2001-04-01 00:00:00'",
            "granularity": "'1 month'",
            "aggregation_type": "maximum",
            "number_of_maps": 3,
        },
    )


def test_two_months_minimum_with_offset(tools, absolute):
    # January and February hold ag1, ag2 and ag3 (minimum 100), March and
    # April hold ag5 and ag6 (minimum 500) and the null ag7.
    tools.t_rast_aggregate(
        input=absolute,
        output="ag_two",
        basename="ag_two",
        granularity="2 months",
        method="minimum",
        sampling="contains",
        nprocs=4,
        offset=10,
        suffix="num%02",
    )

    assert [(row[0], row[3]) for row in _rows(tools, "ag_two")] == [
        ("ag_two_11", 100.0),
        ("ag_two_12", 500.0),
    ]
    _check(
        tools,
        "ag_two",
        {
            "start_time": "'2001-01-01 00:00:00'",
            "end_time": "'2001-05-01 00:00:00'",
            "granularity": "'2 months'",
            "aggregation_type": "minimum",
        },
    )


def test_three_months_sum_with_offset(tools, absolute):
    # January to March hold ag1 to ag5 (ag6 ends in April): 100 + 200 + 300 +
    # 400 + 500 = 1500. April to June hold only the null ag7.
    tools.t_rast_aggregate(
        input=absolute,
        output="ag_three",
        basename="ag_three",
        granularity="3 months",
        method="sum",
        sampling="contains",
        file_limit=0,
        nprocs=9,
        offset=100,
        suffix="num%03",
    )

    assert [(row[0], row[3]) for row in _rows(tools, "ag_three")] == [
        ("ag_three_101", 1500.0)
    ]
    _check(
        tools,
        "ag_three",
        {"end_time": "'2001-04-01 00:00:00'", "number_of_maps": 1},
    )


def test_relative_granularity_6_average(tools, relative):
    # [0,6) holds ag1, ag2 (150), [6,12) ag3, ag4 (350), [12,18) ag5, ag6
    # (550); [18,24) holds only the null ag7 and is dropped.
    tools.t_rast_aggregate(
        input=relative,
        output="agr_6",
        basename="agr_6",
        granularity=6,
        method="average",
        file_limit=0,
        sampling="overlaps,overlapped,contains",
        nprocs=2,
    )

    assert [(row[1], row[2], row[3]) for row in _rows(tools, "agr_6")] == [
        (0, 6, 150.0),
        (6, 12, 350.0),
        (12, 18, 550.0),
    ]
    _check(tools, "agr_6", {"unit": "days", "granularity": 6, "map_time": "interval"})


def test_relative_granularity_9_maximum_with_null_maps(tools, relative):
    # [0,9) holds ag1 to ag3 (300), [9,18) ag4 to ag6 (600), [18,27) only
    # the null ag7, which -n keeps.
    tools.t_rast_aggregate(
        input=relative,
        output="agr_9n",
        basename="agr_9n",
        granularity=9,
        method="maximum",
        sampling="contains",
        nprocs=4,
        flags="n",
    )

    assert [(row[1], row[2], row[3]) for row in _rows(tools, "agr_9n")] == [
        (0, 9, 300.0),
        (9, 18, 600.0),
        (18, 27, None),
    ]


def test_relative_granularity_9_maximum_drops_the_null_granule(tools, relative):
    tools.t_rast_aggregate(
        input=relative,
        output="agr_9",
        basename="agr_9",
        granularity=9,
        method="maximum",
        sampling="contains",
        nprocs=4,
    )

    assert [(row[1], row[2], row[3]) for row in _rows(tools, "agr_9")] == [
        (0, 9, 300.0),
        (9, 18, 600.0),
    ]
    _check(tools, "agr_9", {"end_time": "'18'", "number_of_maps": 2})


def test_relative_granularity_21_average(tools, relative):
    # [0,21) holds ag1 to ag7: the average of 100 to 600 is 350, the null
    # ag7 is left out.
    tools.t_rast_aggregate(
        input=relative,
        output="agr_21",
        basename="agr_21",
        granularity=21,
        method="average",
        sampling="contains",
        nprocs=4,
    )

    # The old suite expected two maps, but compared with a tolerance of 2.
    assert _rows(tools, "agr_21") == [("agr_21_00001", 0, 21, 350.0)]
