"""Tests for month and year steps that start behind the end of a shorter month

Pure datetime arithmetic: no GRASS session and no temporal database needed.
"""

from datetime import datetime

import pytest

from grass.temporal.datetime_math import (
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


def test_steps_up_to_day_28_are_unchanged():
    assert increment_datetime_by_string(datetime(2001, 1, 28), "1 months") == datetime(
        2001, 2, 28
    )
    assert increment_datetime_by_string(datetime(2001, 12, 15), "1 months") == datetime(
        2002, 1, 15
    )
