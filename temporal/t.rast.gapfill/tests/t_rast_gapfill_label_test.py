"""Test that t.rast.gapfill refuses a dataset name that carries a semantic label

The name "<dataset>.S2_1" reads the maps of the dataset that have the label
S2_1, but filling its gaps acts on the whole dataset, so the call is refused before
anything is written.
"""

import pytest

from grass.temporal.testing.readback import message
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


def test_gapfill_without_label_unchanged(tools, labelled, prefix):
    """The dataset has no gap, so the tool succeeds and leaves it as it is"""
    before = labelled.snapshot()

    tools.t_rast_gapfill(input=labelled.name, basename=f"{prefix}_gf")

    assert labelled.snapshot() == before
