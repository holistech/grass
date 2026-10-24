"""Tests for the start and end of the cycles of t.rast.accumulate and t.rast.accdetect

Pure datetime arithmetic: no GRASS session and no temporal database needed.
"""

from datetime import datetime

import pytest

from grass.temporal.datetime_math import next_cycle

JAN_31 = datetime(2001, 1, 31)
FEB_28 = datetime(2001, 2, 28)
MAR_31 = datetime(2001, 3, 31)
APR_30 = datetime(2001, 4, 30)

# Each case gives the end of the previous cycle as the tool does, so that a
# count from that end would give another value than the count from the origin.
CASES = {
    # Month steps count from the origin: 31 Jan + 1 month is cut to 28 Feb and
    # 31 Jan + 2 months is 31 Mar. Counting from the end 28 Feb of cycle 0
    # would give 28 Mar. The cycle is one month long.
    "month-from-origin-1": (
        (JAN_31, 1, FEB_28, "1 months", None),
        (FEB_28, MAR_31),
    ),
    # 31 Jan + 2 months = 31 Mar, one month later is 30 Apr (cut).
    "month-from-origin-2": (
        (JAN_31, 2, MAR_31, "1 months", None),
        (MAR_31, APR_30),
    ),
    # A one month cycle and a one month offset make a step of 2 months: cycle 1
    # starts 31 Jan + 2 months = 31 Mar and ends one month later, on 30 Apr.
    "month-with-month-offset-1": (
        (JAN_31, 1, FEB_28, "1 months", "1 months"),
        (MAR_31, APR_30),
    ),
    # Cycle 2 starts 31 Jan + 4 months = 31 May and ends on 30 Jun.
    "month-with-month-offset-2": (
        (JAN_31, 2, APR_30, "1 months", "1 months"),
        (datetime(2001, 5, 31), datetime(2001, 6, 30)),
    ),
    # Months and days do not add up to one step, so the count starts at the
    # end of the previous cycle: 28 Feb + 2 days = 2 Mar, one month later is
    # 2 Apr.
    "month-with-day-offset": (
        (JAN_31, 1, FEB_28, "1 months", "2 days"),
        (datetime(2001, 3, 2), datetime(2001, 4, 2)),
    ),
    # 29 Feb 2000 + 12 months = 28 Feb 2001, + 24 months = 28 Feb 2002.
    "year-from-leap-day": (
        (datetime(2000, 2, 29), 1, FEB_28, "1 years", None),
        (FEB_28, datetime(2002, 2, 28)),
    ),
    # Days are no month steps: the cycle starts at the end of the previous
    # one, 31 Jan, and 10 days later is 10 Feb.
    "days-without-offset": (
        (JAN_31, 1, JAN_31, "10 days", None),
        (JAN_31, datetime(2001, 2, 10)),
    ),
}


@pytest.mark.parametrize(
    ("arguments", "expected"), CASES.values(), ids=list(CASES.keys())
)
def test_the_cycle_is_counted_as_documented(arguments, expected):
    origin, number, end, cycle, offset = arguments

    assert next_cycle(origin, number, end, cycle, offset, absolute=True) == expected


def test_a_relative_cycle_starts_at_the_end_plus_the_offset():
    # start = end + offset = 5 + 2, end = start + cycle = 7 + 5.
    assert next_cycle(0, 1, 5, 5, 2, absolute=False) == (7, 12)
