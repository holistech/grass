# SPDX-FileCopyrightText: 2026 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Test which limit map t.rast.accdetect takes for a map

The input holds a map of the value 20 on 2001-01-01, with the last test a
second one on 2001-01-02. The range 0 to 100 holds 20; a minimum map of 30 or
a maximum map of 10 leaves no occurrence, so a run that takes the limit map
computes only empty maps.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, message

# The tests make maps and datasets with tools, which takes more than a second
# (measured 14.11.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

DAY_1 = (day(0), day(1))
DAY_2 = (day(1), day(2))
LIMIT_VALUE = {"minimum": 30, "maximum": 10}


def detect_occurrence(tools, prefix, inputs, option, limit, **options):
    """Detect occurrences with one limit map, return the result of the tool

    inputs are the (start, end) of the input maps of the value 20, limit the
    (start, end) of the map of the option minimum or maximum. The datasets
    and maps are named after prefix, the occurrence dataset <prefix>_output.
    """
    create_stds(
        tools,
        "strds",
        f"{prefix}_input",
        [
            MapSpec(f"{prefix}_input_{number}", 20, start, end)
            for number, (start, end) in enumerate(inputs)
        ],
    )
    create_stds(
        tools,
        "strds",
        f"{prefix}_limit",
        [MapSpec(f"{prefix}_limit_map", LIMIT_VALUE[option], *limit)],
    )
    return tools.t_rast_accdetect(
        input=f"{prefix}_input",
        occurrence=f"{prefix}_output",
        basename=f"{prefix}_result",
        range="0,100",
        start="2001-01-01",
        cycle="2 days",
        **{option: f"{prefix}_limit"},
        **options,
    )


def maxima(tools, prefix):
    """The maximum of each map of the occurrence dataset of prefix"""
    return [row.max for row in list_maps(tools, "strds", f"{prefix}_output")]


@pytest.mark.parametrize("option", ["minimum", "maximum"])
@pytest.mark.parametrize(
    ("relation", "limit"),
    [
        pytest.param("equal", DAY_1, id="equal"),
        pytest.param("overlapped", (day(-1), day(0, hours=12)), id="overlapped"),
    ],
)
def test_limit_map_by_relation(tools, option, relation, limit):
    """A limit map with a documented relation replaces the range option"""
    # Only empty maps: without -n none is registered and no dataset is made.
    prefix = f"{relation}_{option}"
    result = detect_occurrence(tools, prefix, [DAY_1], option, limit)
    assert f"No space time dataset <{prefix}_output> was created." in message(result)
    assert f"{prefix}_output@" not in tools.t_list(type="strds").text


def test_unrelated_limit_map_uses_range(tools):
    """A limit map without a documented relation leaves the range option in use"""
    # The occurrence on the first day of the cycle is 0 days.
    detect_occurrence(tools, "unrel", [DAY_1], "maximum", (day(365), day(366)))
    assert maxima(tools, "unrel") == [0]


@pytest.mark.parametrize("option", ["minimum", "maximum"])
def test_reverse_uses_limit_map_of_each_map(tools, option):
    """With the reverse flag each input map uses the limit map of its own time"""
    # Day 2 takes the limit map and is empty, day 1 the range: occurrence 0.
    prefix = f"rev_{option}"
    detect_occurrence(tools, prefix, [DAY_1, DAY_2], option, DAY_2, flags="r")
    assert maxima(tools, prefix) == [0]
