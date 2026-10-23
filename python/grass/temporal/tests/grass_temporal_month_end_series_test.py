"""Tests for series of granules that start behind the end of a shorter month

A series of month granules from 31 January counts every start from the first
one, so a cut to the end of February does not carry over into March: 31.01.,
28.02., 31.03., 30.04. Covered are the granules of the algebra core and the
gap list of the classic library, which the classic algebra (-g), t.rast.list
(method=gran) and other tools sample with. Maps are built in memory only, so
no GRASS session and no temporal database are needed here.
"""

from datetime import datetime

from grass.temporal.abstract_space_time_dataset import AbstractSpaceTimeDataset
from grass.temporal.algebra.time_functions import granules
from grass.temporal.space_time_datasets import RasterDataset


def day(number, month, year=2001):
    return datetime(year, month, number)


def test_monthly_granules_from_day_31_count_from_the_start():
    # Each start is 31.01. plus n months, cut to the last day of a shorter
    # month: 28.02. (2001 is no leap year), 31.03., 30.04. Each granule ends
    # where the next starts; the last one ends at 31.01. + 4 months = 31.05.
    months = granules(day(31, 1), day(31, 5), "1 months")
    assert months.times() == [
        (day(31, 1), day(28, 2)),
        (day(28, 2), day(31, 3)),
        (day(31, 3), day(30, 4)),
        (day(30, 4), day(31, 5)),
    ]


def test_relative_granules_are_unchanged():
    # Starts 0, 3, 6, 9 are below the end 10; the last granule covers it.
    steps = granules(0, 10, 3, temporal_type="relative", unit="days")
    assert steps.times() == [(0, 3), (3, 6), (6, 9), (9, 12)]


def interval_map(name, start, end):
    map_ = RasterDataset(f"{name}@PERMANENT")
    map_.set_absolute_time(start, end)
    return map_


def test_the_classic_gap_list_from_day_31_counts_from_the_start():
    # Granules from 31.01. to 30.04.: [31.01., 28.02.], [28.02., 31.03.],
    # [31.03., 30.04.]. The first and the last are equal to a map, the
    # middle one relates to none and is the only gap.
    maps = [
        interval_map("first", day(31, 1), day(28, 2)),
        interval_map("last", day(31, 3), day(30, 4)),
    ]
    rows = AbstractSpaceTimeDataset.resample_maplist_by_granularity(
        maps, day(31, 1), day(30, 4), "1 months"
    )
    assert [
        (row[0].get_id(), *row[0].get_temporal_extent_as_tuple()) for row in rows
    ] == [
        ("first@PERMANENT", day(31, 1), day(28, 2)),
        (None, day(28, 2), day(31, 3)),
        ("last@PERMANENT", day(31, 3), day(30, 4)),
    ]
