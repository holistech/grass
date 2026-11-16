"""The week start of adjust_datetime_to_granularity() and the datetime delta

A week granule starts on the Monday on or before the date, also when that
Monday lies in the month or the year before. compute_datetime_delta() counts
the months between two firsts of a month over more than a year in full, and
an hour, a minute or a second only where the two times of the day differ in
that unit or a finer one. Pure datetime arithmetic: no GRASS session and no
temporal database needed.
"""

from datetime import datetime, timedelta, timezone

import pytest

from grass.temporal.datetime_math import (
    adjust_datetime_to_granularity,
    compute_datetime_delta,
)


@pytest.mark.parametrize(
    ("date", "monday"),
    [
        # The day of the month is not greater than the weekday (Monday is 0):
        # Thursday, Sunday, Saturday, Sunday and Tuesday.
        (datetime(2026, 1, 1), datetime(2025, 12, 29)),
        (datetime(2026, 2, 1), datetime(2026, 1, 26)),
        (datetime(2026, 4, 4), datetime(2026, 3, 30)),
        (datetime(2026, 4, 5), datetime(2026, 3, 30)),
        (datetime(2026, 9, 1), datetime(2026, 8, 31)),
        # A Monday, and dates later in the month
        (datetime(2026, 1, 5), datetime(2026, 1, 5)),
        (datetime(2026, 1, 11, 18, 30), datetime(2026, 1, 5)),
        (datetime(2026, 7, 8), datetime(2026, 7, 6)),
    ],
)
@pytest.mark.parametrize("granularity", ["1 weeks", "2 weeks", "1 week"])
def test_week_granule_starts_on_or_before_first_map(date, monday, granularity):
    adjusted = adjust_datetime_to_granularity(date, granularity)
    assert adjusted == monday
    assert adjusted.weekday() == 0
    assert date - timedelta(days=7) < adjusted <= date


def test_week_start_keeps_the_time_zone():
    zone = timezone(timedelta(hours=2))
    assert adjust_datetime_to_granularity(
        datetime(2026, 1, 3, 12, tzinfo=zone), "1 weeks"
    ) == datetime(2025, 12, 29, tzinfo=zone)


def delta(*, year=0, month=0, day=0, hour=0, minute=0, second=0, max_days=0):
    return {
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "minute": minute,
        "second": second,
        "max_days": max_days,
    }


# Pairs of times whose delta changed with the counting of months over a year
# and of the time of the day, and pairs next to them that keep their delta
DELTAS = [
    # 12 months of the year and 2 months after it, before only the 2
    (datetime(2024, 1, 1), datetime(2025, 3, 1), delta(year=1, month=14, max_days=425)),
    (datetime(2024, 11, 1), datetime(2025, 2, 1), delta(year=1, month=3, max_days=92)),
    (datetime(2024, 3, 1), datetime(2026, 3, 1), delta(year=2, month=24, max_days=730)),
    # From January to January the step counts in years only.
    (datetime(2024, 1, 1), datetime(2026, 1, 1), delta(year=2, max_days=731)),
    # The same time of the day: 10 days, before also 240 hours and 14400
    # minutes
    (
        datetime(2026, 6, 1, 10, 30),
        datetime(2026, 6, 11, 10, 30),
        delta(day=10, max_days=10),
    ),
    # The hours differ, the minutes do not: 241 hours, before also 14460
    # minutes
    (
        datetime(2026, 6, 1, 10, 30),
        datetime(2026, 6, 11, 11, 30),
        delta(day=10, hour=241, max_days=10),
    ),
    (datetime(2026, 6, 1, 10), datetime(2026, 6, 1, 10, 0, 30), delta(second=30)),
    # An hour that is 0 at both ends does not count, although the minutes
    # differ; the minutes hold the whole delta.
    (
        datetime(2026, 6, 1, 0, 30),
        datetime(2026, 6, 11, 0, 45),
        delta(day=10, minute=14415, max_days=10),
    ),
    (datetime(2026, 6, 1), datetime(2026, 6, 11), delta(day=10, max_days=10)),
]


@pytest.mark.parametrize(("start", "end", "expected"), DELTAS)
def test_datetime_delta(start, end, expected):
    assert compute_datetime_delta(start, end) == expected
