"""Test layer= and type= of t.vect.extract, and maps registered with a layer

A map registered as name:layer is extracted from that layer; the option layer
applies to the maps registered without a layer. In the maps of conftest.py the
layer 1 holds the values 1 and 2 and the layer 2 the values 101 and 102.
"""

import pytest

from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.tools import ToolError

# Most tests take more than a second (measured 18.10.2026 with a serial
# pytest --durations=0).
pytestmark = pytest.mark.slow


def _primitives(tools, name):
    return [
        (row.name, int(tools.v_info(map=row.name, flags="t").keyval["points"]))
        for row in list_maps(tools, "stvds", name)
    ]


def test_the_registered_layer_decides_which_table_the_expression_reads(
    tools, layered, prefix
):
    # The layers are registered one after the other: vl_1:1, vl_1:2, vl_2:1,
    # vl_2:2. value > 100 finds nothing in the layers 1 (1, 2) and both points
    # in the layers 2 (101, 102).
    tools.t_vect_extract(
        input=layered,
        output=prefix,
        expression="value > 100",
        basename=f"{prefix}_x",
        flags="n",
    )

    assert _primitives(tools, prefix) == [
        (f"{prefix}_x_2001_01", 0),
        (f"{prefix}_x_2001_04", 2),
        (f"{prefix}_x_2001_07", 0),
        (f"{prefix}_x_2001_10", 2),
    ]
    listed = tools.t_vect_list(input=prefix, columns="id,layer").stdout.splitlines()
    assert [line.split("|")[1] for line in listed[1:]] == ["1", "2", "1", "2"]


def test_the_option_layer_applies_to_maps_without_a_layer(tools, plain_layers, prefix):
    tools.t_vect_extract(
        input=plain_layers,
        output=prefix,
        expression="value > 100",
        basename=f"{prefix}_x",
        layer="2",
    )

    assert _primitives(tools, prefix) == [
        (f"{prefix}_x_2001_01", 2),
        (f"{prefix}_x_2001_04", 2),
    ]


def test_the_layer_one_is_the_default(tools, plain_layers, prefix):
    tools.t_vect_extract(
        input=plain_layers,
        output=prefix,
        expression="value > 100",
        basename=f"{prefix}_x",
        flags="n",
    )

    assert [count for _, count in _primitives(tools, prefix)] == [0, 0]


def test_type_selects_the_kind_of_primitives(tools, plain_layers, prefix):
    # The maps hold points only, so type=line finds nothing and type=point
    # everything the condition lets through.
    options = {"input": plain_layers, "expression": "value > 0", "flags": "n"}
    tools.t_vect_extract(
        output=f"{prefix}_line", basename=f"{prefix}_l", type="line", **options
    )
    tools.t_vect_extract(
        output=f"{prefix}_point", basename=f"{prefix}_p", type="point", **options
    )

    assert [c for _, c in _primitives(tools, f"{prefix}_line")] == [0, 0]
    assert [c for _, c in _primitives(tools, f"{prefix}_point")] == [2, 2]
    assert stds_info(tools, "stvds", f"{prefix}_point")["points"] == 4


def test_two_layers_of_one_time_get_the_layer_in_the_name(
    tools, same_time_layers, prefix
):
    tools.t_vect_extract(
        input=same_time_layers,
        output=prefix,
        expression="value > 0",
        basename=f"{prefix}_x",
    )

    # Both layers of vs_1 are registered for the first quarter: the time
    # suffix is the same, so the layer follows it.
    assert _primitives(tools, prefix) == [
        (f"{prefix}_x_2001_01_1", 2),
        (f"{prefix}_x_2001_01_2", 2),
    ]


def test_a_failed_extraction_leaves_no_new_map(tools, layered, prefix):
    # The second new map exists already, v.extract refuses to replace it and
    # the call ends after the first map was made.
    tools.v_extract(input="vl_1", layer=1, output=f"{prefix}_x_2001_04", where="1")

    with pytest.raises(ToolError) as error:
        tools.t_vect_extract(
            input=layered,
            output=prefix,
            expression="value > 0",
            basename=f"{prefix}_x",
            nprocs=1,
        )

    assert "Error in computation process" in message(error.value)
    # The map that the run made is gone, the one that was there stays.
    assert tools.g_list(type="vector", pattern=f"{prefix}_x_*").stdout.split() == [
        f"{prefix}_x_2001_04"
    ]


def test_a_numbered_suffix_keeps_the_layers_apart(tools, same_time_layers, prefix):
    tools.t_vect_extract(
        input=same_time_layers,
        output=prefix,
        expression="value > 0",
        basename=f"{prefix}_x",
        suffix="num",
    )

    assert _primitives(tools, prefix) == [
        (f"{prefix}_x_00001", 2),
        (f"{prefix}_x_00002", 2),
    ]
