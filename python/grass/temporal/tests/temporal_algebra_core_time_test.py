"""Tests for the time functions of the algebra core

The expected time stamps of retime() were measured on 2026-10-11 with the
functions of grass.temporal that retime() uses (scratch script, map objects
in memory): one day of buffer around [1, 2] gives [31.12.2000, 3.1.2001],
and snapping the instants of January 1 and 4 gives [1, 4] and [4, 7].
"""

import datetime

import pytest

from grass.temporal.algebra.content import NULL, Const, MapRef
from grass.temporal.algebra.operations import apply
from grass.temporal.algebra.series import Series, Slot
from grass.temporal.algebra.time_functions import (
    TIMEVARS,
    granules,
    neighbour,
    retime,
    timevar,
)


def day(number, month=1, year=2001):
    return datetime.datetime(year, month, number)


def values(series):
    return [slot.content.value for slot in series]


@pytest.fixture
def a(make_series):
    return make_series("a", (1, 2), (2, 3), (3, 4), (4, 5))


def test_td_in_days_and_null_for_an_instant(make_series):
    series = make_series("x", (1, 3), 5)
    result = timevar(series, "td")
    assert result.sort == "scalar"
    assert values(result) == [2.0, None]


def test_td_of_relative_time_in_its_unit(make_series):
    assert values(timevar(make_series("r", (2, 5), unit="days"), "td")) == [3]


def test_td_of_a_relative_instant_is_null(make_series):
    assert values(timevar(make_series("r", 2, unit="days"), "td")) == [None]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("start_day", [1, 2, 3, 4]),
        ("end_day", [2, 3, 4, 5]),
        ("start_doy", [1, 2, 3, 4]),
        ("start_dow", [1, 2, 3, 4]),
        ("start_month", [1, 1, 1, 1]),
        ("start_date", [day(n).date() for n in range(1, 5)]),
    ],
)
def test_calendar_variables(a, name, expected):
    """2001-01-01 was a Monday, ISO day of week 1"""
    assert values(timevar(a, name)) == expected


def test_end_variables_are_null_for_an_instant(make_series):
    series = make_series("x", 2)
    assert values(timevar(series, "end_day")) == [None]
    assert values(timevar(series, "start_day")) == [2]


def test_every_variable_has_a_value_for_an_absolute_interval(a):
    for name in TIMEVARS:
        assert all(value is not None for value in values(timevar(a, name)))


def test_calendar_variables_are_null_for_relative_time(make_series):
    assert values(timevar(make_series("r", (2, 5), unit="days"), "start_day")) == [None]


def test_variables_keep_the_time_stamps(a):
    assert timevar(a, "td").times() == a.times()


def test_unknown_variable(a):
    with pytest.raises(ValueError, match="Unknown temporal variable"):
        timevar(a, "start_fortnight")


def test_variables_of_a_map_without_time_stamp():
    timeless = Series((Slot(None, MapRef("m@PERMANENT")),))
    with pytest.raises(ValueError, match="no temporal variables"):
        timevar(timeless, "td")


def test_scalars_take_part_in_apply(a):
    assert values(apply("==", timevar(a, "start_day"), 2)) == [0, 1, 0, 0]


def test_shift_keeps_the_content(a):
    shifted = retime(a, shift="1 day")
    assert shifted.times()[0] == (day(2), day(3))
    assert [slot.content for slot in shifted] == [slot.content for slot in a]
    assert all(slot.origin is None for slot in shifted)


def test_shift_keeps_the_input(a):
    before = a.times()
    retime(a, shift="1 day")
    assert a.times() == before


def test_buffer(make_series):
    assert retime(make_series("x", (1, 2)), buffer="1 day").times() == [
        (day(31, 12, 2000), day(3))
    ]


def test_snap(make_series):
    assert retime(make_series("i", 1, 4), snap=True).times() == [
        (day(1), day(4)),
        (day(4), day(7)),
    ]


def test_relative_shift_by_a_number(make_series):
    shifted = retime(make_series("r", (2, 5), unit="days"), shift=1)
    assert shifted.times() == [(3, 6)]


def test_relative_time_keeps_its_unit(make_series):
    shifted = retime(make_series("r", (2, 5), unit="years"), shift=1)
    assert shifted.slots[0].extent.unit == "years"
    assert shifted.temporal_type == "relative"


def test_relative_time_is_not_changed_by_a_time_string(make_series):
    with pytest.raises(ValueError, match="number of its unit"):
        retime(make_series("r", (2, 5), unit="days"), shift="1 day")


def test_retime_needs_one_change(a):
    with pytest.raises(ValueError, match="exactly one"):
        retime(a, shift="1 day", snap=True)
    with pytest.raises(ValueError, match="exactly one"):
        retime(a)


def test_absolute_time_needs_a_unit(a):
    with pytest.raises(ValueError, match="time unit"):
        retime(a, shift=1)


@pytest.mark.parametrize("option", ["shift", "buffer"])
def test_unreadable_increment(a, option):
    with pytest.raises(ValueError, match="Cannot read"):
        retime(a, **{option: "a while"})


def test_relative_time_is_changed_by_whole_units(make_series):
    with pytest.raises(ValueError, match="whole units"):
        retime(make_series("r", (2, 5), unit="days"), shift=0.5)


def test_relative_buffer(make_series):
    buffered = retime(make_series("r", (2, 5), unit="days"), buffer=1)
    assert buffered.times() == [(1, 6)]


@pytest.mark.parametrize(
    ("series", "buffer"),
    [
        ("absolute", "-1 day"),
        ("absolute", "-2 hours"),
        ("relative", -1),
        ("relative", "-1"),
    ],
)
def test_negative_buffer_is_rejected(make_series, series, buffer):
    """grass.temporal would make the interval end before it starts, which
    fails with an AttributeError outside a session and prints an error and
    returns inconsistent times inside one"""
    unit = "days" if series == "relative" else None
    x = make_series("x", (1, 2), (3, 6), unit=unit)
    with pytest.raises(ValueError, match="must not be negative"):
        retime(x, buffer=buffer)


def test_zero_buffer_changes_nothing(make_series):
    x = make_series("x", (1, 2), (3, 6), unit="days")
    assert retime(x, buffer=0).times() == x.times()
    y = make_series("y", (1, 2))
    assert retime(y, buffer="0 days").times() == y.times()


def test_a_map_without_time_stamp_cannot_be_moved():
    timeless = Series((Slot(None, MapRef("m@PERMANENT")),))
    with pytest.raises(ValueError, match="without time stamp"):
        retime(timeless, shift="1 day")


@pytest.mark.parametrize(
    "option",
    [{"shift": "1 day"}, {"buffer": "1 day"}, {"snap": True}],
    ids=["shift", "buffer", "snap"],
)
def test_empty_series_stay_empty(option):
    result = retime(Series(), **option)
    assert len(result) == 0


@pytest.mark.parametrize("name", ["td", "start_day"])
def test_timevar_of_an_empty_series(name):
    result = timevar(Series(), name)
    assert len(result) == 0
    assert result.sort == "scalar"


def test_neighbour_of_an_empty_series():
    assert len(neighbour(Series(), 1)) == 0


def test_neighbour(a):
    following = neighbour(a, 1)
    assert following.times() == a.times()[:3]
    assert [slot.content for slot in following] == [
        MapRef(f"a{i}@PERMANENT") for i in (2, 3, 4)
    ]
    preceding = neighbour(a, -1)
    assert preceding.times() == a.times()[1:]


def test_neighbour_beyond_the_series_is_empty(a):
    assert len(neighbour(a, 4)) == 0


def test_monthly_granules():
    months = granules("2001-01-01", "2001-04-01", "1 month")
    assert months.times() == [
        (day(1, 1), day(1, 2)),
        (day(1, 2), day(1, 3)),
        (day(1, 3), day(1, 4)),
    ]
    assert all(slot.content == NULL for slot in months)


def test_relative_granules():
    steps = granules(0, 6, 2, temporal_type="relative", unit="days")
    assert steps.times() == [(0, 2), (2, 4), (4, 6)]
    assert steps.temporal_type == "relative"
    assert steps.slots[0].extent.unit == "days"


def test_granules_of_an_empty_period():
    assert len(granules("2001-01-01", "2001-01-01", "1 month")) == 0
    assert len(granules(6, 0, 2, temporal_type="relative", unit="days")) == 0


def test_granules_need_a_positive_step():
    with pytest.raises(ValueError, match="positive"):
        granules(0, 6, 0, temporal_type="relative", unit="days")


@pytest.mark.parametrize(
    ("start", "end", "granularity", "message"),
    [
        ("xx", "2001-01-04", "1 day", "Cannot read 'xx'"),
        ("2001-01-01", "xx", "1 day", "Cannot read 'xx'"),
        (5, "2001-01-04", "1 day", "Cannot read 5"),
        ("2001-01-01", "2001-01-04", "a while", "Cannot read 'a while'"),
        ("2001-01-01", "2001-01-04", "1 fortnight", "Cannot read '1 fortnight'"),
        ("2001-01-01", "2001-01-04", 5, "Cannot read 5"),
        ("2001-01-01", "2001-01-04", "0 days", "positive"),
        ("2001-01-01", "2001-01-01", "-1 day", "positive"),
    ],
)
def test_unreadable_absolute_granules(start, end, granularity, message):
    with pytest.raises(ValueError, match=message):
        granules(start, end, granularity)


@pytest.mark.parametrize(
    ("start", "end", "granularity", "message"),
    [
        (0, 6, "2", "whole number"),
        (0, 6, 1.5, "whole number"),
        (0.5, 6, 2, "whole number"),
        (0, 6.5, 2, "whole number"),
        ("0", 6, 2, "whole number"),
        (0, 6, -2, "positive"),
    ],
)
def test_unreadable_relative_granules(start, end, granularity, message):
    with pytest.raises(ValueError, match=message):
        granules(start, end, granularity, temporal_type="relative", unit="days")


def test_whole_floats_are_fine_for_relative_granules():
    steps = granules(0.0, 4.0, 2.0, temporal_type="relative", unit="days")
    assert steps.times() == [(0, 2), (2, 4)]


def test_relative_granules_need_a_unit():
    with pytest.raises(ValueError, match="unit"):
        granules(0, 6, 2, temporal_type="relative")


def test_granules_need_a_known_temporal_type():
    with pytest.raises(ValueError, match="temporal_type"):
        granules(0, 6, 2, temporal_type="cyclic")


def test_constant_content_is_unaffected(make_series):
    s = make_series("s", (1, 2), values=[3])
    assert retime(s, shift="1 day").slots[0].content == Const(3)
