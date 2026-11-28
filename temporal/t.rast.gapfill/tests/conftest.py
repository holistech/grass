"""Datasets with gaps for the tests of t.rast.gapfill

The tool fills the gaps of its input in place, so each test builds the dataset
it fills, with names of its own (the prefix fixture).
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region


def month(number):
    """The first day of month number, counted from 2001-01 as month 1"""
    return datetime(2001 + (number - 1) // 12, (number - 1) % 12 + 1, 1)


@pytest.fixture
def gappy(tools, prefix):
    """Function that makes a dataset of monthly maps with gaps; returns its name

    make(months) takes a dict {month number: (first cell, second cell)} and
    makes a map of one month for each entry, in a region of one row and two
    cells. The maps are <prefix>_m<number>, the dataset <prefix>_in.
    """

    def make(months, *, name=None):
        small_region(tools, 1, 2)
        name = name or f"{prefix}_in"
        create_stds(
            tools,
            "strds",
            name,
            [
                MapSpec(
                    f"{name}_m{number}",
                    f"if(col() == 1, {first}, {second})",
                    month(number),
                    month(number + 1),
                )
                for number, (first, second) in months.items()
            ],
        )
        return name

    return make


@pytest.fixture(scope="session")
def month_start():
    """The function month(number): the first day of month number from 2001-01"""
    return month


@pytest.fixture(scope="session")
def old_suite():
    """The maps of the old suite: January (100), April (400), December (1200)

    The second cell rises by 10 per month in the first gap and by 8 in the
    second: 0, 30 and 94 in the three maps, so every interpolated value of
    both cells is a whole number.
    """
    return {1: (100, 0), 4: (400, 30), 12: (1200, 94)}
