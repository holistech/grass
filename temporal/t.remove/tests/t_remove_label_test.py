"""Test that t.remove refuses a dataset name that carries a semantic label

The name "<dataset>.S2_1" reads the maps of the dataset that have the label
S2_1, but removing it acts on the whole dataset, so the call is refused before
anything is written.
"""

import pytest

from grass.temporal.testing.data import insert_old_stds
from grass.temporal.testing.readback import message
from grass.temporal.testing.session import temporal_session
from grass.tools import ToolError, Tools

REFUSAL = "selects maps by the semantic label <S2_1>"


@pytest.mark.parametrize("flags", ["f", "rf", "df"])
def test_remove_refuses_a_label(tools, labelled, flags):
    before = labelled.snapshot()

    with pytest.raises(ToolError) as error:
        tools.t_remove(type="strds", inputs=f"{labelled.name}.S2_1", flags=flags)

    assert REFUSAL in message(error.value)
    assert labelled.snapshot() == before
    # The maps of the dataset exist in the mapset as before.
    assert set(labelled.maps) <= set(tools.g_list(type="raster").text_split())


def test_remove_refuses_a_label_next_to_the_plain_name(tools, labelled):
    """One name with a label refuses the call, though another names the dataset"""
    before = labelled.snapshot()

    with pytest.raises(ToolError) as error:
        tools.t_remove(
            type="strds",
            inputs=f"{labelled.name},{labelled.name}.S2_1",
            flags="f",
        )

    assert REFUSAL in message(error.value)
    assert labelled.snapshot() == before


def test_remove_without_label_unchanged(tools, labelled):
    tools.t_remove(type="strds", inputs=labelled.name, flags="f")

    assert labelled.name not in tools.t_list(type="strds", columns="name").text_split()
    assert set(labelled.maps) <= set(tools.g_list(type="raster").text_split())


def test_remove_takes_a_dataset_with_a_dot_in_its_name(tmp_path):
    """A dataset of an older release is named whole, not by a label"""
    with temporal_session(tmp_path / "project") as session:
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        insert_old_stds("a.b")

        tools.t_remove(type="strds", inputs="a.b", flags="f")

        assert tools.t_list(type="strds", columns="name").text_split() == []
