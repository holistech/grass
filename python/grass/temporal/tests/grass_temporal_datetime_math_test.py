"""Tests for datetime arithmetic, parsing, formatting and granularity adjustment

The functions are pure datetime arithmetic, so no GRASS session and no
temporal database are needed here.
"""

import re
from datetime import datetime

import pytest
from dateutil import parser

from grass.temporal import datetime_math
from grass.temporal.datetime_math import (
    adjust_datetime_to_granularity,
    check_datetime_string,
    create_suffix_from_datetime,
    datetime_to_grass_datetime_string,
    decrement_datetime_by_string,
    increment_datetime_by_string,
    modify_datetime,
)


@pytest.mark.parametrize(
    ("start", "increment", "expected"),
    [
        # A single increment string may combine every supported unit. Seconds
        # carry into minutes and weeks are added on top of the days.
        (
            datetime(2001, 9, 1),
            "60 seconds, 4 minutes, 12 hours, 10 days, 1 weeks, 5 months, 1 years",
            datetime(2003, 2, 18, 12, 5),
        ),
        # A month increment lands on the same day of the following month.
        (datetime(2001, 11, 1), "1 months", datetime(2001, 12, 1)),
        # More than twelve months has to roll the year over.
        (datetime(2001, 11, 1), "13 months", datetime(2002, 12, 1)),
        (datetime(2001, 1, 1), "72 months", datetime(2007, 1, 1)),
        # Units below a month are added as a time span and carry over.
        (datetime(2001, 1, 1), "5 minutes", datetime(2001, 1, 1, 0, 5)),
        (datetime(2001, 1, 1), "49 hours", datetime(2001, 1, 3, 1, 0)),
        (datetime(2001, 1, 1), "3600 seconds", datetime(2001, 1, 1, 1, 0)),
        (datetime(2001, 1, 1), "30 days", datetime(2001, 1, 31, 0, 0)),
    ],
)
def test_increment_datetime_by_string(start, increment, expected) -> None:
    assert increment_datetime_by_string(start, increment) == expected


@pytest.mark.parametrize(
    ("start", "decrement", "expected"),
    [
        # 31 days and one month back from 1 January both end on 1 December.
        (datetime(2001, 1, 1), "31 days", datetime(2000, 12, 1, 0, 0)),
        (datetime(2001, 1, 1), "1 month", datetime(2000, 12, 1, 0, 0)),
        (datetime(2001, 1, 1), "2 month", datetime(2000, 11, 1, 0, 0)),
        # Months back over one or more year boundaries
        (datetime(2001, 1, 1), "24 months", datetime(1999, 1, 1, 0, 0)),
        (datetime(2001, 1, 1), "48 months", datetime(1997, 1, 1, 0, 0)),
        (datetime(2001, 6, 1), "5 months", datetime(2001, 1, 1, 0, 0)),
        (datetime(2001, 6, 1), "7 months", datetime(2000, 11, 1, 0, 0)),
        (datetime(2001, 1, 1), "1 year", datetime(2000, 1, 1, 0, 0)),
    ],
)
def test_decrement_datetime_by_string(start, decrement, expected) -> None:
    assert decrement_datetime_by_string(start, decrement) == expected


@pytest.mark.parametrize(
    ("start", "step", "expected"),
    [
        # 23 months from 31 March end on the last day of February.
        (datetime(2003, 3, 31), {"months": 23}, datetime(2005, 2, 28, 0, 0)),
        # A negative month step goes back by whole years here.
        (datetime(2003, 12, 1), {"months": -24}, datetime(2001, 12, 1, 0, 0)),
    ],
)
def test_modify_datetime(start, step, expected) -> None:
    assert modify_datetime(start, **step) == expected


@pytest.mark.parametrize("use_dateutil", [True, False])
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Every ISO form that the parser of the library reads without dateutil
        ("2000-01-01", datetime(2000, 1, 1, 0, 0)),
        ("2000-01-01T10:00:00", datetime(2000, 1, 1, 10, 0)),
        ("2000-01-01 10:00:00", datetime(2000, 1, 1, 10, 0)),
        ("2000-01-01T10:00:00.000001", datetime(2000, 1, 1, 10, 0, 0, 1)),
        ("2000-01-01 10:00:00.000001", datetime(2000, 1, 1, 10, 0, 0, 1)),
    ],
)
def test_check_datetime_string(text, use_dateutil, expected) -> None:
    assert check_datetime_string(text, use_dateutil) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # GRASS reads the offset as hours and minutes, also when negative.
        ("2011-01-01 10:00:00 +01:30", "01 jan 2011 10:00:00 +0130"),
        ("2011-01-01 10:00:00 +02:30", "01 jan 2011 10:00:00 +0230"),
        ("2011-01-01 10:00:00 +12:00", "01 jan 2011 10:00:00 +1200"),
        ("2011-01-01 10:00:00 -01:30", "01 jan 2011 10:00:00 -0130"),
    ],
)
def test_datetime_to_grass_datetime_string_with_time_zone(text, expected) -> None:
    assert datetime_to_grass_datetime_string(parser.parse(text)) == expected


@pytest.mark.parametrize(
    ("granularity", "expected"),
    [
        ("1 month", "2001_01"),
        # Only the unit after the first number decides the suffix.
        ("1 year 1 month", "2001"),
        ("6 seconds", "2001_01_01_10_04_12"),
    ],
)
def test_create_suffix_from_datetime(granularity, expected) -> None:
    start = datetime(2001, 1, 1, 10, 4, 12)
    assert create_suffix_from_datetime(start, granularity) == expected


@pytest.mark.parametrize(
    ("granularity", "expected"),
    [
        # The date is truncated to the granularity unit, so a granularity
        # finer than or equal to the seconds of the date leaves it unchanged.
        ("5 seconds", datetime(2001, 8, 8, 12, 30, 30)),
        ("20 minutes", datetime(2001, 8, 8, 12, 30)),
        ("3 hours", datetime(2001, 8, 8, 12, 0)),
        ("5 days", datetime(2001, 8, 8, 0, 0)),
        # Weeks snap back to the Monday of the week, 2001-08-08 is a Wednesday.
        ("2 weeks", datetime(2001, 8, 6, 0, 0)),
        ("6 months", datetime(2001, 8, 1, 0, 0)),
        ("2 years", datetime(2001, 1, 1, 0, 0)),
        # With several units the finest one present wins, because truncating to
        # it already satisfies all the coarser ones.
        (
            "2 years, 3 months, 5 days, 3 hours, 3 minutes, 2 seconds",
            datetime(2001, 8, 8, 12, 30, 30),
        ),
        ("3 months, 5 days, 3 minutes", datetime(2001, 8, 8, 12, 30)),
        ("3 weeks, 5 days", datetime(2001, 8, 8, 0, 0)),
    ],
)
def test_adjust_datetime_to_granularity(granularity, expected) -> None:
    assert (
        adjust_datetime_to_granularity(datetime(2001, 8, 8, 12, 30, 30), granularity)
        == expected
    )


class _Messages:
    """Collect the errors that the date functions report"""

    def __init__(self):
        self.errors = []

    def error(self, message):
        self.errors.append(message)


@pytest.fixture
def messages(monkeypatch):
    recorder = _Messages()
    monkeypatch.setattr(
        "grass.temporal.datetime_math.get_tgis_message_interface", lambda: recorder
    )
    return recorder


# A word names the first unit in the order second, minute, hour, day, week,
# month, year that it contains, so plurals and longer words count. A unit that
# appears twice takes its last number.
@pytest.mark.parametrize(
    ("increment", "mult", "sign", "expected"),
    [
        ("2 seconds", 1, 1, datetime(2001, 1, 31, 0, 0, 2)),
        ("2 second", 1, 1, datetime(2001, 1, 31, 0, 0, 2)),
        ("2 secondsx", 1, 1, datetime(2001, 1, 31, 0, 0, 2)),
        ("3 minutesecond", 1, 1, datetime(2001, 1, 31, 0, 0, 3)),
        ("2 hourday", 1, 1, datetime(2001, 1, 31, 2)),
        ("2 weekday", 1, 1, datetime(2001, 2, 2)),
        ("1 yearmonth", 1, 1, datetime(2001, 2, 28)),
        ("1 weeks", 1, 1, datetime(2001, 2, 7)),
        ("1 week", 2, -1, datetime(2001, 1, 17)),
        ("1 years, 1 month", 1, 1, datetime(2002, 2, 28)),
        ("1 day, 2 days", 1, 1, datetime(2001, 2, 2)),
        ("2 days, 1 day", 1, 1, datetime(2001, 2, 1)),
        ("1 day, 1 hour, 3 days", 2, 1, datetime(2001, 2, 6, 2)),
        ("1 days extra", 1, 1, datetime(2001, 2, 1)),
        (" 1 day ,  2 hours ", 1, 1, datetime(2001, 2, 1, 2)),
        ("1 day", 1, "-1", datetime(2001, 1, 30)),
    ],
)
def test_the_unit_of_an_increment_word(increment, mult, sign, expected, messages):
    result = datetime_math.modify_datetime_by_string(
        datetime(2001, 1, 31), increment, mult, sign
    )

    assert result == expected
    assert messages.errors == []


@pytest.mark.parametrize(
    "increment",
    [
        "1 fortnight",
        "1 Days",
        "1",
        "day",
        "1  day",
        "x fortnight",
        "1 day, 1",
        "1 fortnight, x days",
    ],
)
def test_an_increment_without_a_unit_is_reported(increment, messages):
    result = datetime_math.modify_datetime_by_string(datetime(2001, 1, 31), increment)

    assert result is None
    assert messages.errors == [f"Wrong increment format: {increment}"]


@pytest.mark.parametrize(
    ("increment", "error"),
    [
        ("x days", "invalid literal for int() with base 10: 'x'"),
        ("1.5 days", "invalid literal for int() with base 10: '1.5'"),
        ("1 day, y hours", "invalid literal for int() with base 10: 'y'"),
        ("x days, 1 fortnight", "invalid literal for int() with base 10: 'x'"),
    ],
)
def test_an_increment_with_a_number_that_is_no_integer_raises(
    increment, error, messages
):
    with pytest.raises(ValueError, match=re.escape(error)):
        datetime_math.modify_datetime_by_string(datetime(2001, 1, 31), increment)
    assert messages.errors == []


@pytest.mark.parametrize("increment", ["", None])
def test_an_empty_increment_returns_the_date_itself(increment, messages):
    date = datetime(2001, 1, 31)

    assert datetime_math.modify_datetime_by_string(date, increment) is date
    assert messages.errors == []


@pytest.mark.parametrize("sign", [0, 2, -2])
def test_a_sign_other_than_one_gives_none(sign, messages):
    assert (
        datetime_math.modify_datetime_by_string(datetime(2001, 1, 31), "1 day", 1, sign)
        is None
    )
    assert messages.errors == []
