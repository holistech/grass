"""Test that t.snap refuses a dataset name that carries a semantic label

The name "<dataset>.S2_1" reads the maps of the dataset that have the label
S2_1, but snapping it acts on the whole dataset, so the call is refused before
anything is written.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

REFUSAL = "selects maps by the semantic label <S2_1>"


def test_snap_refuses_a_label(tools, labelled):
    before = labelled.snapshot()

    with pytest.raises(ToolError) as error:
        tools.t_snap(input=f"{labelled.name}.S2_1")

    assert REFUSAL in message(error.value)
    assert labelled.snapshot() == before


def test_snap_without_label_unchanged(tools, labelled):
    tools.t_snap(input=labelled.name)

    info = tools.t_info(type="strds", input=labelled.name, flags="g").keyval
    # The last map is a day long, so snapping leaves the end where it was.
    assert info["end_time"] == "'2001-01-05 00:00:00'"
