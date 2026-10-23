"""modify_datetime() counts years and months as one calendar step

Before, years and months were each measured from the original date and the two
differences were added, so a step of both could end in another month than a
step of 12 * years + months, and a month step back to December of the year
before last or earlier raised "bad month number 0".
"""

import calendar
import copy
from datetime import datetime, timedelta

import pytest

from grass.temporal.datetime_math import _replace_year_month, modify_datetime


@pytest.mark.parametrize(
    ("start", "years", "months", "expected"),
    [
        # 31.03.2003 + 23 months = 28.02.2005 (2005 is no leap year).
        (datetime(2003, 3, 31), 1, 11, datetime(2005, 2, 28)),
        # 01.02.2003 + 13 months = 01.03.2004.
        (datetime(2003, 2, 1), 1, 1, datetime(2004, 3, 1)),
        # 15.02.2004 + 13 months = 15.03.2005.
        (datetime(2004, 2, 15), 1, 1, datetime(2005, 3, 15)),
        # 29.02.2004 + 13 months = 29.03.2005 (March has 31 days).
        (datetime(2004, 2, 29), 1, 1, datetime(2005, 3, 29)),
    ],
)
def test_years_and_months_are_one_calendar_step(start, years, months, expected):
    assert modify_datetime(start, years=years, months=months) == expected


@pytest.mark.parametrize(
    ("start", "years", "months", "expected"),
    [
        # 01.12.2003 - 24 months = 01.12.2001.
        (datetime(2003, 12, 1), 0, -24, datetime(2001, 12, 1)),
        # 15.01.2003 - 13 months = 15.12.2001.
        (datetime(2003, 1, 15), 0, -13, datetime(2001, 12, 15)),
        # 31.03.2005 - 13 months = 29.02.2004 (2004 is a leap year).
        (datetime(2005, 3, 31), -1, -1, datetime(2004, 2, 29)),
    ],
)
def test_steps_back_by_a_multiple_of_twelve(start, years, months, expected):
    assert modify_datetime(start, years=years, months=months) == expected


def _old_month_year_step(mydate, years, months):
    """The computation before the correction, kept to show that pure steps are
    unchanged

    Copy of the month and year branches. Returns None where it raised.
    """
    tdelta_months = timedelta(0)
    tdelta_years = timedelta(0)
    try:
        if months > 0:
            all_months = int(months) + mydate.month
            years_to_add = int(all_months / 12.001)
            residual_months = all_months - (years_to_add * 12)
            if residual_months == 0:
                residual_months = 1
            dt1 = _replace_year_month(
                copy.copy(mydate), mydate.year + years_to_add, residual_months
            )
            tdelta_months = dt1 - mydate
        elif months < 0:
            years_to_remove = 0
            all_months = int(months) + mydate.month
            if all_months <= 0:
                years_to_remove = abs(int(all_months / 12.001))
                residual_months = all_months + (years_to_remove * 12)
                years_to_remove += 1
            else:
                residual_months = all_months
            if residual_months <= 0:
                residual_months += 12
            dt1 = _replace_year_month(
                copy.copy(mydate), mydate.year - years_to_remove, residual_months
            )
            tdelta_months = dt1 - mydate
        if years != 0:
            dt1 = _replace_year_month(
                copy.copy(mydate), mydate.year + int(years), mydate.month
            )
            tdelta_years = dt1 - mydate
    except ValueError:
        return None
    return mydate + tdelta_months + tdelta_years


def test_pure_steps_are_unchanged():
    days = (1, 15, 28, 29, 30, 31)
    compared = 0
    broken = []
    for year in (2003, 2004):
        for month in range(1, 13):
            for day in days:
                if day > calendar.monthrange(year, month)[1]:
                    continue
                start = datetime(year, month, day)
                steps = [(0, m) for m in range(-40, 41)]
                steps += [(y, 0) for y in range(-5, 6)]
                for years, months in steps:
                    old = _old_month_year_step(start, years, months)
                    new = modify_datetime(start, years=years, months=months)
                    if old is None:
                        broken.append((start, months))
                    else:
                        assert new == old, (start, years, months)
                        compared += 1
    assert compared > 0
    # The old computation breaks exactly where start month + months is a
    # multiple of 12 that is -12 or less: the target month is then December
    # of the year before last or earlier (-24 from December, -13 from
    # January, -25 from January, ...). Nothing else breaks: for -12 from
    # December start month + months is 0 and the old computation lands on
    # December of the previous year; -24 from March has a result as well.
    expected = {
        (datetime(year, month, day), steps)
        for year in (2003, 2004)
        for month in range(1, 13)
        for day in days
        if day <= calendar.monthrange(year, month)[1]
        for steps in range(-40, 0)
        if month + steps <= -12 and (month + steps) % 12 == 0
    }
    assert set(broken) == expected
