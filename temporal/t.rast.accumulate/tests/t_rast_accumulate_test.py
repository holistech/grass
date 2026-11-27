# SPDX-FileCopyrightText: 2026 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Test which limit map t.rast.accumulate takes for a granule

The input holds a map of the value 20 on 2001-01-01, with the second test a
second one on 2001-01-02. The method bedd with the limits 0 and 100 adds
min(value, upper) - lower for each granule.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps

# The tests make maps and datasets with tools, which takes more than a second
# (measured 14.11.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

DAY_1 = (day(0), day(1))
DAY_2 = (day(1), day(2))


def accumulate(tools, prefix, inputs, lower, upper, **options):
    """Accumulate inputs with the lower and upper limit maps, return the maxima

    inputs, lower and upper are lists of (value, start, end); each makes a map
    of the dataset <prefix>_input, <prefix>_lower or <prefix>_upper.
    """
    for kind, maps in (("input", inputs), ("lower", lower), ("upper", upper)):
        create_stds(
            tools,
            "strds",
            f"{prefix}_{kind}",
            [
                MapSpec(f"{prefix}_{kind}_{number}", value, start, end)
                for number, (value, start, end) in enumerate(maps)
            ],
        )
    tools.t_rast_accumulate(
        input=f"{prefix}_input",
        output=f"{prefix}_output",
        basename=f"{prefix}_result",
        lower=f"{prefix}_lower",
        upper=f"{prefix}_upper",
        limits="0,100",
        method="bedd",
        start="2001-01-01",
        **options,
    )
    return [row.max for row in list_maps(tools, "strds", f"{prefix}_output")]


@pytest.mark.parametrize(
    ("prefix", "preferred", "other"),
    [
        pytest.param("equal", DAY_1, (day(-31), day(31)), id="equal-over-during"),
        pytest.param(
            "overlapped",
            (day(-1), day(0, hours=12)),
            (day(0, hours=6), day(0, hours=18)),
            id="overlapped-over-contains",
        ),
    ],
)
def test_limit_maps_by_relation(tools, prefix, preferred, other):
    """Limit maps with the relation documented first replace the limits option"""
    # The lower map 5 of the preferred relation and the upper map 10 give
    # 10 - 5 = 5; the lower map 8 of the other relation would give 2.
    maxima = accumulate(
        tools,
        prefix,
        inputs=[(20, *DAY_1)],
        lower=[(5, *preferred), (8, *other)],
        upper=[(10, *preferred)],
        cycle="1 day",
    )
    assert maxima == [5]


def test_reverse_uses_limit_maps_of_each_granule(tools):
    """With the reverse flag each granule uses the limit maps of its own time"""
    # Back in time: day 2 adds 10 - 8 = 2 with its own limit maps, day 1 adds
    # 20 - 5 = 15 with the lower map 5 and the upper limit 100: 17 and 2.
    maxima = accumulate(
        tools,
        "rev",
        inputs=[(20, *DAY_1), (20, *DAY_2)],
        lower=[(5, *DAY_1), (8, *DAY_2)],
        upper=[(10, *DAY_2)],
        cycle="2 days",
        flags="r",
    )
    assert maxima == [17, 2]
