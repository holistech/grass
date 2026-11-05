"""Test the granularity of t.rast.aggregate: one unit, weeks from a Monday

The granularity is one number and one unit; a mixed form is refused, as the
description of the option says. A week granule starts on the Monday on or
before the first map, also when that Monday lies in the month before.
"""

import xml.etree.ElementTree as ET
from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.tools import ToolError

D = datetime


def test_mixed_granularity_is_refused(tools, prefix):
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_m1", 1, D(2026, 1, 5), D(2026, 1, 6))],
    )
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate(
            input=f"{prefix}_in",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            granularity="1 months, 5 days",
        )
    assert "Invalid granularity <1 months, 5 days>" in message(error.value)
    assert inventory(tools) == before


@pytest.mark.parametrize(
    ("first", "monday"),
    [
        # Saturday; the Monday lies in the year before
        (D(2026, 1, 3), "2025-12-29 00:00:00"),
        # Thursday, the first of the year
        (D(2026, 1, 1), "2025-12-29 00:00:00"),
        # Monday: the granule starts with the map
        (D(2026, 1, 5), "2026-01-05 00:00:00"),
    ],
)
def test_week_granule_starts_on_or_before_first_map(tools, prefix, first, monday):
    """One map of one day gives one week granule that holds it"""
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_m1", 7, first, first.replace(day=first.day + 1))],
    )
    result = tools.t_rast_aggregate(
        input=f"{prefix}_in",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        granularity="1 weeks",
    )
    assert "No map is related" not in message(result)
    rows = list_maps(tools, "strds", f"{prefix}_out")
    assert [(row.start, row.min) for row in rows] == [(monday, 7.0)]


def test_option_descriptions_match_behaviour(tools, prefix):
    """The description of granularity names one number and one unit, which the
    tool takes; the mixed form is refused in the test above"""
    root = ET.fromstring(
        tools.call_cmd(["t.rast.aggregate", "--interface-description"]).stdout
    )
    text = root.findtext("parameter[@name='granularity']/description").strip()
    assert "one number and one unit" in text
    assert "x years, x months" not in text
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_m{k}", k, D(2026, 1, k), D(2026, 1, k + 1))
            for k in (1, 2)
        ],
    )
    tools.t_rast_aggregate(
        input=f"{prefix}_in",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        granularity="2 days",
        method="sum",
    )
    assert [row.min for row in list_maps(tools, "strds", f"{prefix}_out")] == [3.0]
