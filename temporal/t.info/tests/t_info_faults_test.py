"""Test the granularity that t.info shows for a month series from a month end

A month step that is cut to the end of a shorter month counts as a month: the
series from 31 January (28 February, 31 March) has the granularity "1 month".
"""

from datetime import datetime
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import stds_info

D = datetime


@pytest.mark.parametrize(
    ("starts", "expected"),
    [
        ([D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)], "1 month"),
        ([D(2026, 1, 15), D(2026, 2, 15), D(2026, 3, 15)], "1 month"),
        ([D(2026, 1, 31), D(2026, 2, 27), D(2026, 3, 31)], "1 day"),
    ],
    ids=["month ends", "15th", "one day short"],
)
def test_month_end_series_has_one_month(tools, prefix, starts, expected):
    create_stds(
        tools,
        "strds",
        prefix,
        [
            MapSpec(f"{prefix}_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(starts), start=1)
        ],
    )
    assert stds_info(tools, "strds", prefix)["granularity"] == f"'{expected}'"
