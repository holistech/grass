"""Test that t.shift refuses a dataset name that carries a semantic label

The name "<dataset>.S2_1" reads the maps of the dataset that have the label
S2_1, but shifting it acts on the whole dataset, so the call is refused before
anything is written.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

REFUSAL = "selects maps by the semantic label <S2_1>"


def test_shift_refuses_a_label(tools, labelled):
    before = labelled.snapshot()

    with pytest.raises(ToolError) as error:
        tools.t_shift(input=f"{labelled.name}.S2_1", granularity="1 day")

    assert REFUSAL in message(error.value)
    assert labelled.snapshot() == before


def test_shift_without_label_unchanged(tools, labelled):
    tools.t_shift(input=labelled.name, granularity="1 day")

    info = tools.t_info(type="strds", input=labelled.name, flags="g").keyval
    assert info["start_time"] == "'2001-01-02 00:00:00'"
