"""The week start of adjust_datetime_to_granularity()

A week granule starts on the Monday on or before the date, also when that
Monday lies in the month or the year before. Pure datetime arithmetic: no
GRASS session and no temporal database needed.
"""

from datetime import datetime, timedelta, timezone

import pytest

from grass.temporal.datetime_math import adjust_datetime_to_granularity


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
