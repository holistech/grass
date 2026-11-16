"""Test that t.rast.gapfill refuses a dataset name that carries a semantic label

The name "<dataset>.S2_1" reads the maps of the dataset that have the label
S2_1, but filling its gaps acts on the whole dataset, so the call is refused
before anything is written.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, message, time_text
from grass.tools import ToolError

REFUSAL = "selects maps by the semantic label <S2_1>"


def test_gapfill_refuses_a_label(tools, labelled, prefix):
    before = labelled.snapshot()
    maps_before = tools.g_list(type="raster").text_split()

    with pytest.raises(ToolError) as error:
        tools.t_rast_gapfill(input=f"{labelled.name}.S2_1", basename=f"{prefix}_gf")

    assert REFUSAL in message(error.value)
    assert labelled.snapshot() == before
    assert tools.g_list(type="raster").text_split() == maps_before


def test_gapfill_without_label_unchanged(tools, prefix):
    """Without a label the call acts: the gap of two days gets two maps"""
    name = f"{prefix}_gap"
    create_stds(
        tools,
        "strds",
        name,
        [
            MapSpec(f"{prefix}_a", 10, day(0), day(1)),
            MapSpec(f"{prefix}_b", 50, day(3), day(4)),
        ],
    )

    tools.t_rast_gapfill(input=name, basename=f"{prefix}_gf")

    # The granularity is one day, so the gap from day 1 to day 3 gets one map
    # for each of its two steps.
    maps = list_maps(tools, "strds", name)
    assert [(row.start, row.end) for row in maps] == [
        (time_text(day(0)), time_text(day(1))),
        (time_text(day(1)), time_text(day(2))),
        (time_text(day(2)), time_text(day(3))),
        (time_text(day(3)), time_text(day(4))),
    ]
