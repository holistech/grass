"""Test that t.support refuses a dataset name that carries a semantic label

The name "<dataset>.S2_1" reads the maps of the dataset that have the label
S2_1, but changing its metadata acts on the whole dataset, so the call is refused before
anything is written.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

REFUSAL = "selects maps by the semantic label <S2_1>"


@pytest.mark.parametrize(
    ("options", "flags"),
    [({"title": "New title"}, ""), ({}, "m"), ({}, "u")],
    ids=["title", "-m", "-u"],
)
def test_support_refuses_a_label(tools, labelled, options, flags):
    before = labelled.snapshot()

    with pytest.raises(ToolError) as error:
        tools.t_support(
            type="strds", input=f"{labelled.name}.S2_1", flags=flags, **options
        )

    assert REFUSAL in message(error.value)
    assert labelled.snapshot() == before


def test_support_without_label_unchanged(tools, labelled):
    tools.t_support(input=labelled.name, title="New title")

    text = tools.t_info(type="strds", input=labelled.name).stdout
    assert "New title" in text.split("Title:")[1].split("Description:")[0]
