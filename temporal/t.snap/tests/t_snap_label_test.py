"""Test that t.snap refuses a dataset name that carries a semantic label

The name "<dataset>.S2_1" reads the maps of the dataset that have the label
S2_1, but snapping it acts on the whole dataset, so the call is refused before
anything is written.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, message, time_text
from grass.tools import ToolError

REFUSAL = "selects maps by the semantic label <S2_1>"


def test_snap_refuses_a_label(tools, labelled):
    before = labelled.snapshot()

    with pytest.raises(ToolError) as error:
        tools.t_snap(input=f"{labelled.name}.S2_1")

    assert REFUSAL in message(error.value)
    assert labelled.snapshot() == before


def test_snap_without_label_unchanged(tools, prefix):
    """Without a label the call acts: the gap between two maps is closed"""
    name = f"{prefix}_gap"
    create_stds(
        tools,
        "strds",
        name,
        [
            MapSpec(f"{prefix}_a", 1, day(0), day(1)),
            MapSpec(f"{prefix}_b", 2, day(2), day(3)),
        ],
    )

    tools.t_snap(input=name)

    # The end of each map becomes the start of the next; the last map is an
    # interval and keeps its end.
    maps = list_maps(tools, "strds", name)
    assert [(row.start, row.end) for row in maps] == [
        (time_text(day(0)), time_text(day(2))),
        (time_text(day(2)), time_text(day(3))),
    ]
