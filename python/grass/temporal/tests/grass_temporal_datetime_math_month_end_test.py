"""Tests for month and year steps that start behind the end of a shorter month

Pure datetime arithmetic: no GRASS session and no temporal database needed.
"""

from datetime import datetime

import pytest

from grass.temporal import datetime_math
from grass.temporal.datetime_math import (
    datetime_after_steps,
    decrement_datetime_by_string,
    increment_datetime_by_string,
)


@pytest.mark.parametrize(
    ("start", "step", "expected"),
    [
        (datetime(2001, 1, 31), "1 months", datetime(2001, 2, 28)),
        (datetime(2004, 1, 31), "1 months", datetime(2004, 2, 29)),
        (datetime(2001, 1, 30), "1 months", datetime(2001, 2, 28)),
        (datetime(2001, 3, 31), "1 months", datetime(2001, 4, 30)),
        (datetime(2004, 2, 29), "1 years", datetime(2005, 2, 28)),
        (datetime(2001, 8, 31, 6, 30), "6 months", datetime(2002, 2, 28, 6, 30)),
    ],
)
def test_a_month_or_year_step_ends_on_the_last_day_of_a_shorter_month(
    start, step, expected
):
    assert increment_datetime_by_string(start, step) == expected


def test_a_month_step_back_ends_on_the_last_day_of_a_shorter_month():
    assert decrement_datetime_by_string(datetime(2001, 3, 31), "1 months") == datetime(
        2001, 2, 28
    )


def test_a_year_step_back_ends_on_the_last_day_of_a_shorter_month():
    # 2004 is a leap year, 2003 is not.
    assert decrement_datetime_by_string(datetime(2004, 2, 29), "1 years") == datetime(
        2003, 2, 28
    )


@pytest.mark.parametrize(
    ("start", "step", "expected"),
    [
        # January - 2 months crosses into the previous year: November has 30 days.
        (datetime(2001, 1, 31), "2 months", datetime(2000, 11, 30)),
        # March - 13 months is February of the leap year 2000.
        (datetime(2001, 3, 31), "13 months", datetime(2000, 2, 29)),
    ],
)
def test_a_month_step_back_across_a_year_ends_on_the_last_day(start, step, expected):
    assert decrement_datetime_by_string(start, step) == expected


def test_steps_up_to_day_28_are_unchanged():
    assert increment_datetime_by_string(datetime(2001, 1, 28), "1 months") == datetime(
        2001, 2, 28
    )
    assert increment_datetime_by_string(datetime(2001, 12, 15), "1 months") == datetime(
        2002, 1, 15
    )


def test_a_month_series_counts_from_its_anchor():
    anchor = datetime(2001, 1, 31)
    assert [datetime_after_steps(anchor, "1 months", n) for n in range(5)] == [
        datetime(2001, 1, 31),
        datetime(2001, 2, 28),
        datetime(2001, 3, 31),
        datetime(2001, 4, 30),
        datetime(2001, 5, 31),
    ]


def test_a_year_series_from_a_leap_day_meets_the_next_leap_day():
    anchor = datetime(2004, 2, 29)
    assert datetime_after_steps(anchor, "1 years", 1) == datetime(2005, 2, 28)
    assert datetime_after_steps(anchor, "1 years", 4) == datetime(2008, 2, 29)


def test_a_composite_step_is_chained_as_before():
    # 28.01. + 1 month + 1 day = 01.03.; + 1 month + 1 day = 02.04.
    assert datetime_after_steps(
        datetime(2001, 1, 28), "1 months, 1 days", 2
    ) == datetime(2001, 4, 2)


def test_a_day_step_series_equals_the_chained_one():
    # 31.01. + 3 * 10 days = 02.03. (February has 28 days in 2001).
    assert datetime_after_steps(datetime(2001, 1, 31), "10 days", 3) == datetime(
        2001, 3, 2
    )


def test_zero_steps_return_the_anchor():
    anchor = datetime(2001, 1, 31, 5)
    assert datetime_after_steps(anchor, "1 months", 0) == anchor
    assert datetime_after_steps(anchor, "1 months, 1 days", 0) == anchor


@pytest.mark.parametrize(
    ("anchor", "step", "count", "expected"),
    [
        # Chained, the cut to 28.02. would carry over: 28.03. instead of 31.03.
        (datetime(2001, 1, 31), "1 month", 2, datetime(2001, 3, 31)),
        # Chained: 31.12. + 2 months = 28.02., + 2 months = 28.04.
        (datetime(2000, 12, 31), "2 months", 2, datetime(2001, 4, 30)),
        # Chained: 29.02.2004 + 1 year = 28.02.2005, then 28.02. for good.
        (datetime(2004, 2, 29), "1 year", 4, datetime(2008, 2, 29)),
    ],
)
def test_singular_and_multiple_month_steps_count_from_the_anchor(
    anchor, step, count, expected
):
    assert datetime_after_steps(anchor, step, count) == expected


@pytest.mark.parametrize("step", ["1 months", "10 days", "1 months, 1 days"])
def test_a_negative_number_of_steps_is_an_error(step):
    with pytest.raises(ValueError, match="0 or more"):
        datetime_after_steps(datetime(2001, 3, 31), step, -1)


@pytest.mark.parametrize("step", ["1 days", "6 hours, 30 minutes", "1 months"])
def test_a_long_series_takes_one_step_per_time_stamp(monkeypatch, step):
    # A loop that asks for each time stamp of a series from its anchor
    # would add up count steps per time stamp if every step were chained,
    # which makes a series of days or hours quadratic in its length.
    calls = []

    def counted(mydate, increment, mult=1):
        calls.append(mult)
        return increment_datetime_by_string(mydate, increment, mult)

    monkeypatch.setattr(datetime_math, "increment_datetime_by_string", counted)
    anchor = datetime(2001, 1, 31)
    assert datetime_math.datetime_after_steps(anchor, step, 1000) == (
        increment_datetime_by_string(anchor, step, 1000)
    )
    assert calls == [1000]
