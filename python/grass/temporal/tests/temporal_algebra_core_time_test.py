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
from grass.temporal.algebra.series import Extent, Series, Slot, Space
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


def test_snap_keeps_the_origin_of_gapless_maps(a):
    """tsnap leaves gapless intervals unchanged, so each slot stays the
    registered map; a selection registers it instead of copying it"""
    snapped = retime(a, snap=True)
    assert snapped.times() == a.times()
    assert [slot.origin for slot in snapped] == [slot.origin for slot in a]


def test_snap_drops_the_origin_where_it_closes_a_gap(make_series):
    """A gap moves the end of the earlier map, so that slot is no longer the
    registered map and loses its origin; the unchanged slot keeps it"""
    series = make_series("m", (1, 2), (4, 5))
    snapped = retime(series, snap=True)
    assert snapped.times() == [(day(1), day(4)), (day(4), day(5))]
    assert [slot.origin for slot in snapped] == [None, "m2@PERMANENT"]


def test_shift_drops_the_origin(a):
    """A shift changes every extent, so no slot is the registered map"""
    assert all(slot.origin is None for slot in retime(a, shift="1 day"))


def test_zero_buffer_keeps_the_origin(a):
    """A zero buffer changes nothing, so each slot stays the registered map"""
    assert [slot.origin for slot in retime(a, buffer="0 days")] == [
        slot.origin for slot in a
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


def test_negative_buffer_shrinks_the_maps(make_series):
    x = make_series("x", (1, 11), (11, 21))
    assert retime(x, buffer="-1 days").times() == [
        (day(2), day(10)),
        (day(12), day(20)),
    ]


def test_negative_buffer_drops_the_origin(make_series):
    assert retime(make_series("x", (1, 11)), buffer="-1 days").slots[0].origin is None


def test_negative_relative_buffer(make_series):
    x = make_series("r", (0, 4), (4, 8), unit="years")
    shrunk = retime(x, buffer=-1)
    assert shrunk.times() == [(1, 3), (5, 7)]
    assert shrunk.slots[0].extent.unit == "years"
    assert retime(x, buffer="-1").times() == [(1, 3), (5, 7)]


@pytest.mark.parametrize(
    ("buffer", "unit", "length"),
    [("-5 days", None, 10), ("-6 days", None, 10), (-2, "days", 4), (-3, "days", 4)],
    ids=["absolute-equal", "absolute-before", "relative-equal", "relative-before"],
)
def test_negative_buffer_that_leaves_no_time_is_an_error(
    make_series, buffer, unit, length
):
    """end == start counts as no time: grass.temporal stores such a map as an
    instant, which is not the interval the map had (see set_absolute_time()
    and set_relative_time(): "Do not create an interval in case start and end
    time are equal"), and end < start it refuses and leaves the old stamp"""
    x = make_series("x", (1, 1 + length), unit=unit)
    with pytest.raises(ValueError, match=r"x1@PERMANENT.*leaves no time"):
        retime(x, buffer=buffer)


def test_the_error_names_the_extent_and_the_buffer(make_series):
    with pytest.raises(ValueError, match=r"2001-01-01.*2001-01-11.*-6 days"):
        retime(make_series("x", (1, 11)), buffer="-6 days")


def test_one_map_too_short_stops_the_whole_dataset(make_series):
    """Classic keeps the short maps unchanged or makes instants of them; the
    core does not register a result in which some maps have another meaning"""
    x = make_series("x", (1, 11), (12, 16), (17, 29))
    with pytest.raises(ValueError, match=r"x2@PERMANENT"):
        retime(x, buffer="-3 days")


def test_slot_without_origin_is_named_by_its_position():
    x = Series((Slot(Extent(day(1), day(3)), Const(1)),))
    with pytest.raises(ValueError, match=r"slot 1 "):
        retime(x, buffer="-1 days")


def test_negative_buffer_of_an_instant_is_an_error(make_series):
    """An instant has no duration to shrink"""
    with pytest.raises(ValueError, match=r"i1@PERMANENT.*instant"):
        retime(make_series("i", 3), buffer="-1 days")


def test_positive_buffer_of_an_instant_still_works(make_series):
    assert retime(make_series("i", 3), buffer="1 days").times() == [(day(2), day(4))]


def test_relative_instant_with_negative_buffer_is_an_error(make_series):
    with pytest.raises(ValueError, match="instant"):
        retime(make_series("r", 3, unit="days"), buffer=-1)


def month_series(*spans):
    return Series(
        tuple(
            Slot(Extent(day(*start), day(*end)), Const(i))
            for i, (start, end) in enumerate(spans, 1)
        )
    )


def test_negative_month_buffer_is_calendar_arithmetic():
    """Quarters of different length shrink by a calendar month on each side"""
    quarters = month_series(((1, 1), (1, 4)), ((1, 4), (1, 7)))
    assert retime(quarters, buffer="-1 months").times() == [
        (day(1, 2), day(1, 3)),
        (day(1, 5), day(1, 6)),
    ]


def test_months_are_compared_after_the_calendar_arithmetic():
    """A buffer of a month is no fixed number of days: February [1.2, 1.3) is
    28 days, so -1 months moves its end before its start"""
    february = month_series(((1, 2), (1, 3)))
    with pytest.raises(ValueError, match="leaves no time"):
        retime(february, buffer="-1 months")


def test_month_buffer_from_day_31_ends_on_the_last_day_of_the_month():
    """A month step that ends behind the last day of a shorter month ends on
    that day"""
    # 31.01. + 1 month = 28.02. (2001 is no leap year); 31.05. - 1 month = 30.04.
    x = month_series(((31, 1), (31, 5)))
    assert retime(x, buffer="-1 months").times() == [(day(28, 2), day(30, 4))]


def test_a_month_buffer_past_the_year_9999_is_an_error():
    # 01.12.9999 + 1 month would be in the year 10000, which datetime lacks.
    x = Series((Slot(Extent(day(1, 12, 9999), day(31, 12, 9999)), Const(1)),))
    with pytest.raises(ValueError, match=r"slot 1 .*failed: year 10000"):
        retime(x, buffer="-1 months")


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


def test_neighbour_has_its_own_space_by_default(make_series):
    boxes = [Space(10, 0, 10, 0), Space(20, 10, 20, 10), Space(30, 20, 30, 20)]
    series = make_series("a", (1, 2), (2, 3), (3, 4))
    series = Series(
        tuple(
            Slot(slot.extent, slot.content, box, slot.origin)
            for slot, box in zip(series.slots, boxes, strict=True)
        )
    )
    assert [slot.space for slot in neighbour(series, 1)] == boxes[:2]


def test_neighbour_can_take_the_space_of_the_map_it_reads(make_series):
    """A[1] of the classic algebra is a new map of the neighbour A2, with the
    time stamp of A1 (generate_new_map(), then set_temporal_extent())"""
    boxes = [Space(10, 0, 10, 0), Space(20, 10, 20, 10), Space(30, 20, 30, 20)]
    series = make_series("a", (1, 2), (2, 3), (3, 4))
    series = Series(
        tuple(
            Slot(slot.extent, slot.content, box, slot.origin)
            for slot, box in zip(series.slots, boxes, strict=True)
        )
    )
    following = neighbour(series, 1, space="neighbour")
    assert [slot.space for slot in following] == boxes[1:]
    assert following.times() == series.times()[:2]
    preceding = neighbour(series, -1, space="neighbour")
    assert [slot.space for slot in preceding] == boxes[:2]


def test_neighbour_refuses_another_space(a):
    with pytest.raises(ValueError, match="space must be one of"):
        neighbour(a, 1, space="union")
