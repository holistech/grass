"""Test t.shift: the maps of a dataset move in time

The dataset of most tests has an interval from 2001-01-01 to 2001-01-15 and a
time point on 2001-01-20. A shift moves the start and the end of every map by
the same amount; the expected times are calculated by hand in the cases.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.tools import ToolError


def _text(offset, *, hours=0):
    """day(offset, hours) in the form that t.rast.list prints"""
    return day(offset, hours=hours).strftime("%Y-%m-%d %H:%M:%S")


def _dataset(tools, prefix, times, *, stds_type="strds", **options):
    """Make a dataset <prefix>_ds of constant maps with the times (start, end)"""
    maps = [
        MapSpec(f"{prefix}_{number}", number, start, end)
        for number, (start, end) in enumerate(times, 1)
    ]
    create_stds(tools, stds_type, f"{prefix}_ds", maps, **options)
    return f"{prefix}_ds"


def _times(tools, name, stds_type="strds"):
    return [(row.start, row.end) for row in list_maps(tools, stds_type, name)]


@pytest.fixture
def mixed(tools, prefix):
    """An interval from day 0 to day 14 and a time point on day 19"""
    return _dataset(tools, prefix, [(day(0), day(14)), (day(19), None)])


# Day 0 is 2001-01-01, so day 14 is 2001-01-15 and day 19 is 2001-01-20. The
# units are taken in the singular and in the plural.
@pytest.mark.parametrize(
    ("granularity", "interval", "point"),
    [
        ("1 day", ("2001-01-02", "2001-01-16"), "2001-01-21"),
        ("-1 day", ("2000-12-31", "2001-01-14"), "2001-01-19"),
        ("2 weeks", ("2001-01-15", "2001-01-29"), "2001-02-03"),
        ("6 month", ("2001-07-01", "2001-07-15"), "2001-07-20"),
        ("-1 month", ("2000-12-01", "2000-12-15"), "2000-12-20"),
        ("1 year", ("2002-01-01", "2002-01-15"), "2002-01-20"),
        ("-1 year", ("2000-01-01", "2000-01-15"), "2000-01-20"),
        ("0 days", ("2001-01-01", "2001-01-15"), "2001-01-20"),
    ],
)
def test_shifts_by_days_weeks_months_and_years(
    tools, mixed, granularity, interval, point
):
    tools.t_shift(input=mixed, granularity=granularity)

    # A date without a time is midnight.
    assert _times(tools, mixed) == [
        (f"{interval[0]} 00:00:00", f"{interval[1]} 00:00:00"),
        (f"{point} 00:00:00", None),
    ]


@pytest.mark.parametrize(
    ("granularity", "interval", "point"),
    [
        # 1 hour is 01:00:00 on the same day.
        (
            "1 hour",
            ("2001-01-01 01:00:00", "2001-01-15 01:00:00"),
            "2001-01-20 01:00:00",
        ),
        (
            "1 second",
            ("2001-01-01 00:00:01", "2001-01-15 00:00:01"),
            "2001-01-20 00:00:01",
        ),
        (
            "30 minutes",
            ("2001-01-01 00:30:00", "2001-01-15 00:30:00"),
            "2001-01-20 00:30:00",
        ),
        # 25 hours are one day and one hour.
        (
            "25 hours",
            ("2001-01-02 01:00:00", "2001-01-16 01:00:00"),
            "2001-01-21 01:00:00",
        ),
        # 3630 seconds are 1 hour and 30 seconds: 00:00:00 - 01:00:30 is
        # 22:59:30 of the day before.
        (
            "-3630 seconds",
            ("2000-12-31 22:59:30", "2001-01-14 22:59:30"),
            "2001-01-19 22:59:30",
        ),
    ],
)
def test_shifts_by_hours_minutes_and_seconds(
    tools, mixed, granularity, interval, point
):
    tools.t_shift(input=mixed, granularity=granularity)

    assert _times(tools, mixed) == [(interval[0], interval[1]), (point, None)]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_two_shifts_in_a_row_add_up(tools, mixed):
    tools.t_shift(input=mixed, granularity="1 day")
    tools.t_shift(input=mixed, granularity="-1 day")
    tools.t_shift(input=mixed, granularity="6 months")

    assert _times(tools, mixed) == [
        ("2001-07-01 00:00:00", "2001-07-15 00:00:00"),
        ("2001-07-20 00:00:00", None),
    ]


def test_the_extent_of_the_dataset_follows_its_maps(tools, mixed):
    tools.t_shift(input=mixed, granularity="1 month")

    info = stds_info(tools, "strds", mixed)
    # The point on 2001-01-20 becomes 2001-02-20, the interval ends on
    # 2001-02-15; the dataset ends where its last map ends.
    assert info["start_time"] == "'2001-02-01 00:00:00'"
    assert info["end_time"] == "'2001-02-20 00:00:00'"
    assert info["map_time"] == "mixed"


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_granularity_is_calculated_again(tools, make_stds):
    maps, (name,) = make_stds(3)
    assert stds_info(tools, "strds", name)["granularity"] == "'1 day'"

    tools.t_shift(input=name, granularity="1 hour")

    # The maps now start at 01:00:00, so the smallest unit is the hour.
    assert stds_info(tools, "strds", name)["granularity"] == "'24 hours'"


def test_the_command_is_added_to_the_history(tools, mixed):
    tools.t_shift(input=mixed, granularity="2 days")

    # The history wraps long commands with a backslash at the end of the line.
    history = tools.t_info(type="strds", input=mixed, flags="h").stdout
    history = history.replace("\\\n", "")
    assert f't.shift input="{mixed}" granularity="2 days"' in history


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_map_in_two_datasets_moves_in_both(tools, make_stds):
    _, (first, second) = make_stds(2, datasets=2)

    tools.t_shift(input=first, granularity="1 day")

    # The time belongs to the map: map n lasted from day n-1 to day n.
    for name in (first, second):
        assert _times(tools, name) == [
            (_text(1), _text(2)),
            (_text(2), _text(3)),
        ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_each_dataset_type_with_absolute_time(tools, prefix, stds_type):
    name = _dataset(
        tools, prefix, [(day(0), day(1)), (day(1), day(2))], stds_type=stds_type
    )

    tools.t_shift(type=stds_type, input=name, granularity="1 day")

    assert _times(tools, name, stds_type) == [
        (_text(1), _text(2)),
        (_text(2), _text(3)),
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_each_dataset_type_with_relative_time(tools, prefix, stds_type):
    name = _dataset(
        tools,
        prefix,
        [(0, 14), (14, 28)],
        stds_type=stds_type,
        temporaltype="relative",
        unit="days",
    )

    tools.t_shift(type=stds_type, input=name, granularity="1")

    assert _times(tools, name, stds_type) == [(1, 15), (15, 29)]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize(
    ("granularity", "expected"),
    [
        # An interval and a point: both move by the number.
        ("5", [(5, 7), (7, None)]),
        ("-3", [(-3, -1), (-1, None)]),
        ("0", [(0, 2), (2, None)]),
    ],
)
def test_relative_time_adds_the_number(tools, prefix, granularity, expected):
    name = _dataset(
        tools,
        prefix,
        [(0, 2), (2, None)],
        temporaltype="relative",
        unit="days",
    )

    tools.t_shift(input=name, granularity=granularity)

    assert _times(tools, name) == expected


@pytest.mark.parametrize(
    "granularity", ["1.5 days", "abc", "1 fortnight", "5", "1 days, 2 fortnights"]
)
def test_a_granularity_in_the_wrong_form_is_refused(tools, mixed, granularity):
    # "5" lacks the unit that absolute time needs; a list is accepted since
    # 18.10.2026, but each of its parts must be a number and a unit.
    with pytest.raises(ToolError) as error:
        tools.t_shift(input=mixed, granularity=granularity)

    assert f"Wrong granularity format: {granularity}" in message(error.value)
    assert _times(tools, mixed) == [
        ("2001-01-01 00:00:00", "2001-01-15 00:00:00"),
        ("2001-01-20 00:00:00", None),
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("granularity", ["1 day", "1.5", "invalid"])
def test_a_granularity_in_the_wrong_form_for_relative_time_is_refused(
    tools, prefix, granularity
):
    name = _dataset(
        tools, prefix, [(0, 14), (14, 28)], temporaltype="relative", unit="days"
    )

    with pytest.raises(ToolError) as error:
        tools.t_shift(input=name, granularity=granularity)

    assert f"Wrong granularity format: {granularity}" in message(error.value)
    assert _times(tools, name) == [(0, 14), (14, 28)]


@pytest.mark.parametrize(
    ("granularity", "interval", "point"),
    [
        # Changed on 18.10.2026: a list of units is shifted as a whole.
        (
            "1 days, 2 hours",
            ("2001-01-02 02:00:00", "2001-01-16 02:00:00"),
            "2001-01-21 02:00:00",
        ),
        (
            "1 years, 2 months, 3 days, 4 hours, 5 minutes, 6 seconds",
            ("2002-03-04 04:05:06", "2002-03-18 04:05:06"),
            "2002-03-23 04:05:06",
        ),
        (
            "-1 days, -2 hours",
            ("2000-12-30 22:00:00", "2001-01-13 22:00:00"),
            "2001-01-18 22:00:00",
        ),
        (
            "1 weeks,1 days",
            ("2001-01-09 00:00:00", "2001-01-23 00:00:00"),
            "2001-01-28 00:00:00",
        ),
    ],
)
def test_a_list_of_units_is_added_as_a_whole(
    tools, mixed, granularity, interval, point
):
    # Derived from the dates 2001-01-01, 2001-01-15 and 2001-01-20.
    tools.t_shift(input=mixed, granularity=granularity)

    assert _times(tools, mixed) == [(interval[0], interval[1]), (point, None)]


def test_a_list_with_a_wrong_part_changes_nothing(tools, mixed):
    with pytest.raises(ToolError) as error:
        tools.t_shift(input=mixed, granularity="1 days, abc")

    assert "Wrong granularity format: 1 days, abc" in message(error.value)
    assert _times(tools, mixed) == [
        ("2001-01-01 00:00:00", "2001-01-15 00:00:00"),
        ("2001-01-20 00:00:00", None),
    ]


@pytest.mark.parametrize("granularity", ["1 days, 2 days", "1 day, 1 days"])
def test_a_list_that_names_a_unit_twice_is_refused(tools, mixed, granularity):
    # The function that adds the shift keeps only the last number of a unit,
    # so "1 days, 2 days" would move the maps by 2 days, not 3.
    with pytest.raises(ToolError) as error:
        tools.t_shift(input=mixed, granularity=granularity)

    assert (
        f"Each unit may appear only once in the granularity: {granularity}"
        in message(error.value)
    )
    assert _times(tools, mixed) == [
        ("2001-01-01 00:00:00", "2001-01-15 00:00:00"),
        ("2001-01-20 00:00:00", None),
    ]


@pytest.mark.parametrize(
    ("granularity", "expected"),
    [
        ("1 years, 1 months", "2004-03-14 00:00:00"),
        ("13 months", "2004-03-15 00:00:00"),
    ],
)
def test_the_parts_of_a_list_are_measured_from_the_old_time(
    tools, prefix, granularity, expected
):
    # Every part is counted from 2003-02-15 and the lengths are added: one
    # month is 28 days (to 2003-03-15), one year 365 days (to 2004-02-15).
    # 2004-02-15 plus 28 days is 2004-03-14, as February 2004 has 29 days.
    # 13 months in one part land on 2004-03-15.
    name = _dataset(tools, prefix, [(datetime(2003, 2, 15), None)])

    tools.t_shift(input=name, granularity=granularity)

    assert _times(tools, name) == [(expected, None)]


def test_a_list_updates_the_granularity_and_the_history(tools, prefix):
    name = _dataset(tools, prefix, [(day(0), day(1)), (day(1), day(2))])

    tools.t_shift(input=name, granularity="1 days, 2 hours")

    # As after a shift by hours (test_the_granularity_is_calculated_again).
    assert stds_info(tools, "strds", name)["granularity"] == "'24 hours'"
    history = tools.t_info(type="strds", input=name, flags="h").stdout
    history = history.replace("\\\n", "")
    assert f't.shift input="{name}" granularity="1 days, 2 hours"' in history


def test_a_list_is_not_possible_for_relative_time(tools, prefix):
    name = _dataset(
        tools, prefix, [(0, 14), (14, 28)], temporaltype="relative", unit="days"
    )

    with pytest.raises(ToolError) as error:
        tools.t_shift(input=name, granularity="1, 2")

    assert "Wrong granularity format: 1, 2" in message(error.value)
    assert _times(tools, name) == [(0, 14), (14, 28)]


def test_the_message_of_a_refused_shift_names_the_dataset(tools, mixed):
    with pytest.raises(ToolError) as error:
        tools.t_shift(input=mixed, granularity="abc")

    assert f"<{mixed}@PERMANENT>" in message(error.value)


@pytest.fixture
def end_of_month(tools, prefix):
    """A map from 2001-01-31 to 2001-02-28: one month later has no day 31"""
    return _dataset(tools, prefix, [(day(30), day(58))])


def test_a_month_shift_from_day_31_ends_on_the_last_day_of_february(
    tools, end_of_month
):
    # January 31 plus one month is February 28, the last day of February
    # 2001; February 28 plus one month is March 28.
    tools.t_shift(input=end_of_month, granularity="1 month")

    assert _times(tools, end_of_month) == [
        ("2001-02-28 00:00:00", "2001-03-28 00:00:00")
    ]


def test_a_list_shift_from_day_31_cuts_the_month_before_adding_the_day(
    tools, end_of_month
):
    # Each part is counted from the old time: January 31 plus one month is
    # February 28, plus one day March 1; February 28 plus one month is
    # March 28, plus one day March 29.
    tools.t_shift(input=end_of_month, granularity="1 months, 1 days")

    assert _times(tools, end_of_month) == [
        ("2001-03-01 00:00:00", "2001-03-29 00:00:00")
    ]


def test_a_month_shift_back_from_day_31_ends_on_the_last_day_of_february(tools, prefix):
    # March 31 minus one month is February 28, the last day of February 2001.
    name = _dataset(tools, prefix, [(datetime(2001, 3, 31), None)])

    tools.t_shift(input=name, granularity="-1 months")

    assert _times(tools, name) == [("2001-02-28 00:00:00", None)]


@pytest.fixture
def end_of_time(tools, prefix):
    """A map from 9999-06-01 to 9999-12-01: one year later is no date"""
    return _dataset(tools, prefix, [(datetime(9999, 6, 1), datetime(9999, 12, 1))])


def test_a_shift_behind_the_year_9999_ends_with_a_message(tools, end_of_time):
    # The manual: the shifting is not performed for the whole dataset. Tools
    # end with a message, not with a traceback.
    with pytest.raises(ToolError) as error:
        tools.t_shift(input=end_of_time, granularity="1 year")

    text = message(error.value)
    assert "Traceback" not in text
    assert f"Unable to shift dataset <{end_of_time}@PERMANENT> by <1 year>" in text
    assert "year 10000 is out of range" in text
    assert _times(tools, end_of_time) == [
        ("9999-06-01 00:00:00", "9999-12-01 00:00:00")
    ]


def test_a_list_shift_behind_the_year_9999_names_the_map(tools, end_of_time):
    with pytest.raises(ToolError) as error:
        tools.t_shift(input=end_of_time, granularity="1 years, 1 days")

    assert f"map <{end_of_time.removesuffix('_ds')}_1@PERMANENT>" in message(
        error.value
    )


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_dataset_without_maps_is_shifted_silently(tools, prefix):
    name = _dataset(tools, prefix, [])

    result = tools.t_shift(input=name, granularity="1 day")

    assert result.returncode == 0
    assert _times(tools, name) == []


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("granularity", ["1 day", "1 days, 2 hours"])
def test_a_dataset_of_another_mapset_is_refused(two_mapsets, prefix, granularity):
    work, other = two_mapsets
    name = _dataset(other, prefix, [(day(0), day(1))])

    with pytest.raises(ToolError) as error:
        work.t_shift(input=f"{name}@other", granularity=granularity)

    text = message(error.value)
    assert f"Unable to shift dataset <{name}@other> of type strds" in text
    assert "The mapset of the database does not match the current mapset" in text
    assert _times(other, name) == [(_text(0), _text(1))]


def test_an_unknown_dataset_is_refused(tools):
    with pytest.raises(ToolError) as error:
        tools.t_shift(input="no_such_dataset", granularity="1 day")

    assert "Space time dataset <no_such_dataset> of type <strds> not found" in message(
        error.value
    )


def test_the_type_selects_the_dataset(tools, mixed):
    with pytest.raises(ToolError) as error:
        tools.t_shift(type="stvds", input=mixed, granularity="1 day")

    assert f"Space time dataset <{mixed}> of type <stvds> not found" in message(
        error.value
    )


@pytest.mark.parametrize("missing", ["input", "granularity"])
def test_input_and_granularity_are_required(tools, mixed, missing):
    options = {"input": mixed, "granularity": "1 day"}
    del options[missing]

    with pytest.raises(ToolError) as error:
        tools.t_shift(**options)

    assert f"Required parameter <{missing}> not set" in message(error.value)


def test_a_list_for_a_dataset_without_maps_ends_like_one_unit(tools, prefix):
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output=f"{prefix}_empty",
        title="empty",
        description="empty",
    )

    # Both end without an error and without a map to move.
    tools.t_shift(input=f"{prefix}_empty", granularity="1 days")
    tools.t_shift(input=f"{prefix}_empty", granularity="1 days, 2 hours")

    assert stds_info(tools, "strds", f"{prefix}_empty")["number_of_maps"] == 0
