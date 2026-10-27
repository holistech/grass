"""Tests for the granularity computation and the granularity strings

The granularity of a map list is the largest unit in which the start and end
times of every map can be expressed. Maps are built in memory only, so no
GRASS session and no temporal database are needed here.
"""

from datetime import datetime

import pytest

from grass.temporal.datetime_math import increment_datetime_by_string
from grass.temporal.space_time_datasets import RasterDataset
from grass.temporal.temporal_granularity import (
    _is_after,
    check_granularity_string,
    compute_absolute_time_granularity,
    compute_common_absolute_time_granularity,
    compute_common_relative_time_granularity,
    compute_relative_time_granularity,
    get_time_tuple_function,
    gran_singular_unit,
    gran_to_gran,
)


def interval_maps(start, increment, count):
    """Return count maps covering consecutive intervals of the given increment"""
    maps = []
    for i in range(count):
        map_ = RasterDataset(None)
        map_.set_absolute_time(
            increment_datetime_by_string(start, increment, i),
            increment_datetime_by_string(start, increment, i + 1),
        )
        maps.append(map_)
    return maps


def point_maps(start, increment, count):
    """Return count maps which are time points spaced by the given increment"""
    maps = []
    for i in range(count):
        map_ = RasterDataset(None)
        map_.set_absolute_time(increment_datetime_by_string(start, increment, i), None)
        maps.append(map_)
    return maps


@pytest.mark.parametrize(
    ("start", "increment", "count", "expected"),
    [
        (datetime(2001, 1, 1), "1 year", 10, "1 year"),
        (datetime(2001, 1, 1), "3 years", 10, "3 years"),
        (datetime(2001, 5, 1), "1 month", 20, "1 month"),
        (datetime(2001, 1, 1), "3 months", 20, "3 months"),
        (datetime(2001, 1, 1), "1 day", 6, "1 day"),
        (datetime(2001, 1, 14), "14 days", 6, "14 days"),
        (datetime(2001, 6, 12), "6 hours", 20, "6 hours"),
        (datetime(2001, 1, 1), "20 minutes", 20, "20 minutes"),
        (datetime(2001, 12, 31, 12, 30, 30), "3600 seconds", 24, "3600 seconds"),
        # Mixed units collapse to the finest unit that can express every
        # boundary. Months and days cannot be combined, so days remain.
        (datetime(2001, 3, 1), "1 month, 4 days", 20, "1 day"),
        (datetime(2001, 2, 11), "1 days, 1 hours", 20, "25 hours"),
        (datetime(2001, 1, 1), "5 hours, 25 minutes", 20, "325 minutes"),
        (datetime(2001, 1, 1), "5 minutes, 30 seconds", 20, "330 seconds"),
        (datetime(2001, 12, 31), "60 minutes, 30 seconds", 24, "3630 seconds"),
    ],
)
def test_granularity_of_intervals(start, increment, count, expected) -> None:
    assert (
        compute_absolute_time_granularity(interval_maps(start, increment, count))
        == expected
    )


@pytest.mark.parametrize(
    ("start", "increment", "count", "expected"),
    [
        (datetime(2001, 12, 31, 12, 30, 30), "3600 seconds", 24, "3600 seconds"),
        (datetime(2001, 12, 31), "20 days", 24, "20 days"),
        (datetime(2001, 12, 1), "5 months", 24, "5 months"),
    ],
)
def test_granularity_of_time_points(start, increment, count, expected) -> None:
    assert (
        compute_absolute_time_granularity(point_maps(start, increment, count))
        == expected
    )


@pytest.mark.parametrize(
    ("interval_start", "point_start", "increment", "count", "expected"),
    [
        (
            datetime(2001, 12, 31, 12, 30, 30),
            datetime(2002, 2, 1, 12, 30, 30),
            "3600 seconds",
            24,
            "3600 seconds",
        ),
        (datetime(2001, 1, 1), datetime(2001, 2, 2), "2 days", 8, "2 days"),
    ],
)
def test_granularity_of_intervals_and_time_points(
    interval_start, point_start, increment, count, expected
) -> None:
    """A list may mix intervals and time points and still have a granularity"""
    maps = interval_maps(interval_start, increment, count) + point_maps(
        point_start, increment, count
    )
    assert compute_absolute_time_granularity(maps) == expected


# The cases below were the examples in the docstrings of temporal_granularity,
# which now keep one example each.


@pytest.mark.parametrize(
    ("granularity", "temporal_type", "expected"),
    [
        ("5 days", "absolute", True),
        ("5 minutes", "absolute", True),
        ("5 years", "absolute", True),
        ("5 hours", "absolute", True),
        ("2 seconds", "absolute", True),
        ("1 secondo", "absolute", False),
        ("bla second", "absolute", False),
        ("bla", "absolute", False),
        ("bla", "relative", False),
    ],
)
def test_check_granularity_string(granularity, temporal_type, expected) -> None:
    assert check_granularity_string(granularity, temporal_type) is expected


@pytest.mark.parametrize(
    ("start", "start1", "end1", "expected"),
    [
        (datetime(2024, 1, 1), datetime(2023, 12, 12), None, True),
        (datetime(2023, 12, 14), datetime(2023, 12, 12), datetime(2023, 12, 24), False),
    ],
)
def test_is_after(start, start1, end1, expected) -> None:
    assert _is_after(start, start1, end1) is expected


@pytest.mark.parametrize(
    ("maps", "expected"),
    [
        ([RasterDataset("a@PERMANENT")], "_get_map_time_tuple"),
        ([{"start_time": 1, "end_time": 2}], "_get_row_time_tuple"),
    ],
)
def test_get_time_tuple_function(maps, expected) -> None:
    assert get_time_tuple_function(maps).__name__ == expected


@pytest.mark.parametrize(
    ("unit", "intervals", "expected"),
    [
        ("seconds", [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)], 1),
        ("years", [(0, 3), (3, 6), (6, 9)], 3),
        ("years", [(0, 3), (4, 6), (8, 11)], 1),
        ("months", [(0, 8), (2, 6), (5, 9)], 4),
        ("days", [(0, 8), (8, 12), (12, 18)], 2),
        ("minutes", [(0, None), (8, None), (12, None), (24, None)], 4),
        ("hours", [(0, None), (8, 14), (18, None), (24, None)], 2),
        ("hours", [(0, 21)], 21),
    ],
)
def test_relative_granularity_of_maps(unit, intervals, expected) -> None:
    maps = []
    for number, (start, end) in enumerate(intervals):
        map_ = RasterDataset(f"a{number}@P")
        assert map_.set_relative_time(start, end, unit)
        maps.append(map_)
    # The docstring printed an int; repr tells it from a float of equal value.
    assert repr(compute_relative_time_granularity(maps)) == repr(expected)


# Database rows instead of maps, with the edge cases of the two loops over
# intervals and gaps: an interval in relative time counts only if its end is
# not 0, a gap starts at the previous end only if that end is not 0, and the
# deltas of relative times are cut to integers. The cut is why the start of a
# gap after a fractional end matters: from 2.5 to 5 counts 2, from 0 counts 5.
@pytest.mark.parametrize(
    ("times", "expected"),
    [
        ([(-6, 0)], 0),
        ([(-6, 0), (4, 8)], 2),
        ([(0, 3), (5, 9)], 1),
        ([(0.5, 2.9), (5.0, None)], 2),
        ([(0, 2.5), (5, 7.5)], 2),
        ([(0, None), (3, None), (9, None)], 3),
        ([(2, 3), (0, 1), (1, 2)], 1),
    ],
)
def test_relative_granularity_of_rows(times, expected) -> None:
    rows = [{"start_time": start, "end_time": end} for start, end in times]

    result = compute_relative_time_granularity(rows)

    assert result == expected
    assert type(result) is int


@pytest.mark.parametrize(
    ("times", "expected"),
    [
        (
            [
                (datetime(2001, 1, 1), datetime(2001, 1, 3)),
                (datetime(2001, 1, 7), None),
                (datetime(2001, 1, 13), None),
            ],
            "2 days",
        ),
        (
            [
                (datetime(2001, 1, 1), datetime(2001, 3, 1)),
                (datetime(2001, 3, 1), datetime(2001, 4, 1)),
                (datetime(2001, 7, 1), None),
            ],
            "1 month",
        ),
        ([(datetime(2001, 1, 1, 6), None)], None),
    ],
)
def test_absolute_granularity_of_rows(times, expected) -> None:
    rows = [{"start_time": start, "end_time": end} for start, end in times]

    assert compute_absolute_time_granularity(rows) == expected


def test_common_relative_granularity() -> None:
    assert repr(compute_common_relative_time_granularity([10, 20, 30])) == "10"


@pytest.mark.parametrize(
    ("granularities", "start_dates", "expected"),
    [
        (
            ["20 second", "10 minutes", "2 hours"],
            [datetime(2001, 1, 1), datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "20 seconds",
        ),
        (
            ["20 second", "10 minutes", "2 hours"],
            [
                datetime(2001, 1, 1, 0, 0, 20),
                datetime(2001, 1, 1),
                datetime(2001, 1, 1),
            ],
            "1 second",
        ),
        (
            ["7200 second", "240 minutes", "1 year"],
            [
                datetime(2001, 1, 1, 0, 0, 10),
                datetime(2001, 1, 1),
                datetime(2001, 1, 1),
            ],
            "1 second",
        ),
        (
            ["7200 second", "89 minutes", "1 year"],
            [datetime(2001, 1, 1), datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "60 seconds",
        ),
        (
            ["120 minutes", "2 hours"],
            [datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "60 minutes",
        ),
        (
            ["120 minutes", "2 hours"],
            [datetime(2001, 1, 1, 0, 30), datetime(2001, 1, 1)],
            "1 minute",
        ),
        (
            ["360 minutes", "3 hours"],
            [datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "60 minutes",
        ),
        (
            ["2 hours", "4 hours", "8 hours"],
            [datetime(2001, 1, 1), datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "2 hours",
        ),
        (
            ["2 hours", "4 hours", "8 hours"],
            [
                datetime(2001, 1, 1, 2, 0),
                datetime(2001, 1, 1, 4, 0),
                datetime(2001, 1, 1, 8, 0),
            ],
            "1 hour",
        ),
        (
            ["8 hours", "2 days"],
            [datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "8 hours",
        ),
        (
            ["8 hours", "2 days"],
            [datetime(2001, 1, 1, 10, 0), datetime(2001, 1, 1)],
            "1 hour",
        ),
        (
            ["120 months", "360 months", "4 years"],
            [datetime(2001, 1, 1), datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "12 months",
        ),
        (
            ["30 days", "10 days", "5 days"],
            [datetime(2001, 2, 1), datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "5 days",
        ),
        (
            ["30 days", "10 days", "5 days"],
            [datetime(2001, 2, 2), datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "1 day",
        ),
        (
            ["2 days", "360 months", "4 years"],
            [datetime(2001, 1, 1), datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "2 days",
        ),
        (
            ["2 days", "360 months", "4 years"],
            [datetime(2001, 1, 2), datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "1 day",
        ),
        (
            ["120 months", "360 months", "4 years"],
            [datetime(2001, 2, 1), datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "1 month",
        ),
        (
            ["120 months", "361 months", "4 years"],
            [datetime(2001, 1, 1), datetime(2001, 1, 1), datetime(2001, 1, 1)],
            "1 month",
        ),
        (["1 second", "2 seconds", "30 seconds"], None, "1 second"),
        (["3 second", "6 seconds", "30 seconds"], None, "3 seconds"),
        (["12 second", "18 seconds", "30 seconds", "10 minutes"], None, "6 seconds"),
        (["20 second", "10 minutes", "2 hours"], None, "20 seconds"),
        (["7200 second", "240 minutes", "1 year"], None, "7200 seconds"),
        (["7200 second", "89 minutes", "1 year"], None, "60 seconds"),
        (
            ["10 minutes", "20 minutes", "30 minutes", "40 minutes", "2 hours"],
            None,
            "10 minutes",
        ),
        (["120 minutes", "2 hours"], None, "120 minutes"),
        (["360 minutes", "3 hours"], None, "180 minutes"),
        (["2 hours", "4 hours", "8 hours"], None, "2 hours"),
        (["8 hours", "2 days"], None, "8 hours"),
        (["48 hours", "1 month"], None, "24 hours"),
        (["48 hours", "1 year"], None, "24 hours"),
        (["2 months", "4 months", "1 year"], None, "2 months"),
        (["120 months", "360 months", "4 years"], None, "24 months"),
        (["120 months", "361 months", "4 years"], None, "1 month"),
        (["2 years", "3 years", "4 years"], None, "1 year"),
    ],
)
def test_common_absolute_granularity(granularities, start_dates, expected) -> None:
    """With start dates, a granule longer than the next coarser unit is cut
    to it, and start dates that differ in the field of the unit cut it to one
    unit"""
    assert (
        compute_common_absolute_time_granularity(granularities, start_dates) == expected
    )


@pytest.mark.parametrize(
    ("granularity", "expected"),
    [
        ("2 months", "month"),
        ("6 seconds", "second"),
    ],
)
def test_gran_singular_unit(granularity, expected) -> None:
    assert gran_singular_unit(granularity) == expected


@pytest.mark.parametrize(
    ("source", "target", "shell", "expected"),
    [
        ("10 year", "1 hour", False, "87658.20000000001 hours"),
        ("10 year", "1 minute", False, "5259492.000000001 minutes"),
        ("6 months", "1 day", False, "182.62125 days"),
        ("1 months", "1 second", False, "2629746.0 seconds"),
        ("30 month", "1 month", True, 30),
    ],
)
def test_gran_to_gran(source, target, shell, expected) -> None:
    # With shell the number is returned as it was read, int or float.
    assert repr(gran_to_gran(source, target, shell)) == repr(expected)


# The reading of a dataset leaves a map without time when it refuses the
# stored times, for example an end before the start. The granularity leaves
# such a map out; the expected value is that of the list without it.
ABSOLUTE_TIMES = [
    (datetime(2001, 1, 1), datetime(2001, 1, 5)),
    (datetime(2001, 1, 11), None),
    (datetime(2001, 1, 17), datetime(2001, 1, 21)),
]
RELATIVE_TIMES = [(0, 4), (8, 12), (12, 16)]


def timeless_maps(times, position, temporal_type):
    """Maps of the times with a map without time inserted at position"""
    maps = []
    for number, (start, end) in enumerate(times):
        map_ = RasterDataset(f"a{number}@P")
        if temporal_type == "absolute":
            assert map_.set_absolute_time(start, end)
        else:
            assert map_.set_relative_time(start, end, "days")
        maps.append(map_)
    timeless = RasterDataset("timeless@P")
    timeless.base.set_ttype(temporal_type)
    maps.insert(position, timeless)
    return maps


def timeless_rows(times, position):
    """Rows of the times with a row without time inserted at position"""
    rows = [{"start_time": start, "end_time": end} for start, end in times]
    rows.insert(position, {"start_time": None, "end_time": None})
    return rows


@pytest.mark.parametrize("position", [0, 1, 3])
@pytest.mark.parametrize("kind", ["maps", "rows"])
@pytest.mark.parametrize(
    ("compute", "times", "temporal_type"),
    [
        (compute_absolute_time_granularity, ABSOLUTE_TIMES, "absolute"),
        (compute_relative_time_granularity, RELATIVE_TIMES, "relative"),
    ],
)
def test_a_map_without_time_is_left_out_of_the_granularity(
    compute, times, temporal_type, kind, position
) -> None:
    if kind == "maps":
        with_timeless = timeless_maps(times, position, temporal_type)
        without = [map_ for map_ in with_timeless if map_.get_id() != "timeless@P"]
    else:
        with_timeless = timeless_rows(times, position)
        without = [row for row in with_timeless if row["start_time"] is not None]

    expected = compute(without)

    assert expected not in {None, 0}
    assert compute(with_timeless) == expected
