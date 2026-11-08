"""Test that t.unregister refuses a dataset name that carries a semantic label

The name "<dataset>.S2_1" reads the maps of the dataset that have the label
S2_1, but unregistering maps acts on the whole dataset, so the call is refused before
anything is written.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

REFUSAL = "selects maps by the semantic label <S2_1>"


def test_unregister_refuses_a_label(tools, labelled):
    before = labelled.snapshot()

    with pytest.raises(ToolError) as error:
        tools.t_unregister(input=f"{labelled.name}.S2_1", maps=labelled.maps[0])

    assert REFUSAL in message(error.value)
    assert labelled.snapshot() == before


def test_unregister_without_label_unchanged(tools, labelled):
    tools.t_unregister(input=labelled.name, maps=labelled.maps[0])

    info = tools.t_info(type="strds", input=labelled.name, flags="g").keyval
    assert int(info["number_of_maps"]) == 3
