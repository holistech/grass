"""Tests for the series of the algebra core"""

import dataclasses
import datetime

import pytest

from grass.temporal.algebra.content import MapRef
from grass.temporal.algebra.series import Extent, Series, Slot


def day(number):
    return datetime.datetime(2001, 1, number)


def test_slots_are_ordered_by_time_and_stable_for_equal_times():
    second = Slot(Extent(day(1), day(2)), MapRef("x2@PERMANENT"))
    first = Slot(Extent(day(1), day(2)), MapRef("x1@PERMANENT"))
    late = Slot(Extent(day(3), day(4)), MapRef("y@PERMANENT"))
    series = Series((late, second, first))
    assert series.slots == (second, first, late)


def test_instant_sorts_before_interval_of_same_start():
    instant = Slot(Extent(day(1)), MapRef("i@PERMANENT"))
    interval = Slot(Extent(day(1), day(3)), MapRef("j@PERMANENT"))
    assert Series((interval, instant)).slots == (instant, interval)


def test_temporal_types_cannot_be_mixed():
    absolute = Slot(Extent(day(1), day(2)), MapRef("a@PERMANENT"))
    relative = Slot(Extent(1, 2, "days"), MapRef("r@PERMANENT"))
    with pytest.raises(ValueError, match="temporal type"):
        Series((absolute, relative))


def test_units_cannot_be_mixed():
    days = Slot(Extent(1, 2, "days"), MapRef("d@PERMANENT"))
    years = Slot(Extent(1, 2, "years"), MapRef("y@PERMANENT"))
    with pytest.raises(ValueError, match="temporal type"):
        Series((days, years))


def test_map_without_time_stamp_forms_a_series_of_its_own():
    timeless = Slot(None, MapRef("m@PERMANENT"))
    assert Series((timeless,)).timeless
    with pytest.raises(ValueError, match="without time stamp"):
        Series((timeless, Slot(Extent(day(1), day(2)), MapRef("a@PERMANENT"))))


def test_series_is_immutable(make_series):
    series = make_series("a", (1, 2))
    with pytest.raises(dataclasses.FrozenInstanceError):
        series.slots = ()


def test_series_has_no_truth_value(make_series):
    with pytest.raises(TypeError, match="truth value"):
        bool(make_series("a", (1, 2)))


def test_unknown_kind_and_sort_are_rejected():
    with pytest.raises(ValueError, match="map type"):
        Series((), kind="image")
    with pytest.raises(ValueError, match="sort"):
        Series((), sort="vector")


def test_times_and_temporal_type(make_series):
    series = make_series("a", (1, 2), 3)
    assert series.times() == [(day(1), day(2)), (day(3), None)]
    assert series.temporal_type == "absolute"
    assert make_series("r", (0, 1), unit="days").temporal_type == "relative"
    assert Series().temporal_type is None


def test_fixture_builds_maps_and_scalars(make_series):
    maps = make_series("a", (1, 2))
    assert maps.slots[0].content == MapRef("a1@PERMANENT")
    assert maps.slots[0].origin == "a1@PERMANENT"
    scalars = make_series("s", (1, 2), values=[5])
    assert scalars.sort == "scalar"
    assert scalars.slots[0].origin is None


def test_times_of_a_timeless_series_is_an_error():
    with pytest.raises(ValueError, match="without time stamps"):
        Series((Slot(None, MapRef("m@PERMANENT")),)).times()
