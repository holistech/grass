"""Test that t.register refuses a dataset name that carries a semantic label

The name "<dataset>.S2_1" reads the maps of the dataset that have the label
S2_1, but registering maps acts on the whole dataset, so the call is refused
before anything is written.
"""

import pytest

from grass.temporal.testing.data import insert_old_stds, make_map
from grass.temporal.testing.readback import message
from grass.temporal.testing.session import temporal_session
from grass.tools import ToolError, Tools

REFUSAL = "selects maps by the semantic label <S2_1>"


def test_register_refuses_a_label(tools, labelled, prefix):
    extra = f"{prefix}_5"
    make_map(tools, "raster", extra, 5)
    before = labelled.snapshot()

    with pytest.raises(ToolError) as error:
        tools.t_register(
            type="raster",
            input=f"{labelled.name}.S2_1",
            maps=extra,
            start="2001-01-10",
        )

    assert REFUSAL in message(error.value)
    assert labelled.snapshot() == before
    # The map is not in the temporal database, so it has no timestamp either.
    assert extra not in tools.t_rast_list(input=labelled.name, columns="name").stdout
    with pytest.raises(ToolError, match="not found in temporal database"):
        tools.t_info(type="raster", input=extra, flags="g")


def test_register_without_label_unchanged(tools, labelled, prefix):
    extra = f"{prefix}_5"
    make_map(tools, "raster", extra, 5)

    tools.t_register(type="raster", input=labelled.name, maps=extra, start="2001-01-10")

    info = tools.t_info(type="strds", input=labelled.name, flags="g").keyval
    assert int(info["number_of_maps"]) == 5


def test_register_takes_a_dataset_with_a_dot_in_its_name(tmp_path):
    """A dataset of an older release is named whole, not by a label"""
    with temporal_session(tmp_path / "project") as session:
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        tools.r_mapcalc(expression="one = 1")
        insert_old_stds("a.b")

        tools.t_register(type="raster", input="a.b", maps="one", start="2001-01-01")

        info = tools.t_info(type="strds", input="a.b", flags="g").keyval
        assert int(info["number_of_maps"]) == 1
