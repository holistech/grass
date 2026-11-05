"""Test the gaps and the granularity that t.topology reports

A gap is time that no map covers: a map that ends inside a longer one leaves
no gap behind it. A month step that is cut to the end of a shorter month
counts as a month in the granularity. A step between two firsts of a month
counts all its months, and a time of the day that is the same at both ends of
a step does not count.
"""

import re
from datetime import datetime
from itertools import pairwise

from grass.temporal.testing.data import MapSpec, create_stds

D = datetime


def summary(tools, name):
    """The lines " | key: ..... value" of the summary as a dictionary"""
    text = tools.t_topology(input=name).stdout
    return dict(re.findall(r"^ \| ([^:.]+?):? ?\.+:? *(.*)$", text, re.MULTILINE))


def test_gap_inside_longer_map_is_not_a_gap(tools):
    """m_1 1 to 11 January covers 5 to 8 January; only 13 to 15 January is a
    gap"""
    create_stds(
        tools,
        "strds",
        "cover",
        [
            MapSpec("cover_1", 1, D(2026, 1, 1), D(2026, 1, 11)),
            MapSpec("cover_2", 2, D(2026, 1, 3), D(2026, 1, 5)),
            MapSpec("cover_3", 3, D(2026, 1, 8), D(2026, 1, 13)),
            MapSpec("cover_4", 4, D(2026, 1, 15), D(2026, 1, 16)),
        ],
    )
    assert summary(tools, "cover")["Number of gaps"] == "1"


def test_month_end_series_has_one_month(tools):
    ends = [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)]
    create_stds(
        tools,
        "strds",
        "month_ends",
        [
            MapSpec(f"month_end_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ends), start=1)
        ],
    )
    assert summary(tools, "month_ends")["Granularity"] == "1 month"


def test_granularity_of_month_firsts_over_a_year_and_of_a_time_of_day(tools, prefix):
    """Before 05.11.2026 the granularities were 2 months and 14400 minutes"""
    create_stds(
        tools,
        "strds",
        f"{prefix}_months",
        [
            MapSpec(f"{prefix}_m1", 1, D(2024, 1, 1)),
            MapSpec(f"{prefix}_m2", 2, D(2025, 3, 1)),
        ],
    )
    create_stds(
        tools,
        "strds",
        f"{prefix}_days",
        [
            MapSpec(f"{prefix}_d1", 1, D(2026, 6, 1, 10, 30), D(2026, 6, 11, 10, 30)),
            MapSpec(f"{prefix}_d2", 2, D(2026, 6, 21, 10, 30), D(2026, 7, 1, 10, 30)),
        ],
    )
    assert summary(tools, f"{prefix}_months")["Granularity"] == "14 months"
    assert summary(tools, f"{prefix}_days")["Granularity"] == "10 days"
