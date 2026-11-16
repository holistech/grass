"""Tests for the check and the name builder of the suffix option

The temporal tools that create maps from a basename take the standard option
suffix: gran, time, num or num%NN. Both functions only read the time stamp of
a map object, so no GRASS session and no temporal database are needed here.
"""

from datetime import datetime

import pytest

from grass.temporal.datetime_math import check_suffix, map_name_suffix
from grass.temporal.space_time_datasets import RasterDataset


def _absolute_map(start, end=None):
    map_ = RasterDataset("a@PERMANENT")
    map_.set_absolute_time(start, end)
    return map_


def _relative_map(start, end=None):
    map_ = RasterDataset("a@PERMANENT")
    map_.set_relative_time(start, end, "days")
    return map_


@pytest.mark.parametrize("suffix", ["gran", "time", "num", "num%03", "num%3"])
def test_valid_suffixes_pass(suffix):
    check_suffix(suffix)


@pytest.mark.parametrize(
    "suffix",
    # A typing error, digits that are not digits, a missing number of digits,
    # another word before the digits, the digits alone and nothing at all.
    ["gram", "num%x", "num%", "count%03", "%03", ""],
)
def test_unknown_suffixes_are_refused(suffix):
    with pytest.raises(ValueError, match=rf"Invalid suffix <{suffix}>, use gran"):
        check_suffix(suffix)


@pytest.mark.parametrize(
    ("suffix", "granularity", "expected"),
    [
        # The largest unit of the granularity cuts the start time.
        ("gran", "1 month", "2001_01"),
        ("gran", "6 seconds", "2001_01_01_10_04_12"),
        # A single time instant has no granularity, so gran names it like time.
        ("gran", None, "2001_01_01T10_04_12"),
        # time takes the full start time and ignores the granularity.
        ("time", "1 month", "2001_01_01T10_04_12"),
        ("time", None, "2001_01_01T10_04_12"),
        # num has five digits unless the number of digits is given; the number
        # 7 decides, not the time.
        ("num", "1 month", "00007"),
        ("num%03", None, "007"),
        ("num%3", None, "007"),
    ],
)
def test_suffix_of_a_map_in_absolute_time(suffix, granularity, expected):
    map_ = _absolute_map(datetime(2001, 1, 1, 10, 4, 12))

    assert map_name_suffix(map_, suffix, granularity, 7) == expected


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [
        # Relative time has no calendar date, so every suffix gives the number;
        # gran and time have no number of digits and get five.
        ("gran", "00012"),
        ("time", "00012"),
        ("num", "00012"),
        ("num%02", "12"),
    ],
)
def test_suffix_of_a_map_in_relative_time(suffix, expected):
    map_ = _relative_map(3, 5)

    assert map_name_suffix(map_, suffix, "2", 12) == expected


def test_the_name_builder_refuses_an_unknown_suffix():
    map_ = _absolute_map(datetime(2001, 1, 1))

    with pytest.raises(ValueError, match=r"Invalid suffix <gram>"):
        map_name_suffix(map_, "gram", "1 day", 1)
