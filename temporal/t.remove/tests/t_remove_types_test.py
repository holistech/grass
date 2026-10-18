"""Test t.remove with space time 3D raster and vector datasets, also in layers

Map n holds the value n and lasts one day. Vector layers are named map:layer;
-d deletes the vector map once, however many of its layers the dataset holds.
"""

import pytest

from grass.temporal.testing.data import MapSpec, day, register_stds, vector_points
from grass.tools import ToolError

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def test_str3ds_rf(tools, make_stds, has_dataset, registered, existing):
    maps, (name,) = make_stds(3, stds_type="str3ds")

    tools.t_remove(inputs=name, type="str3ds", flags="rf")

    assert not has_dataset(name, "str3ds")
    assert registered(maps, "raster_3d") == [False] * 3
    assert existing(maps, "raster_3d") == [True] * 3


def test_str3ds_df(tools, make_stds, has_dataset, registered, existing):
    maps, (name,) = make_stds(3, stds_type="str3ds")

    tools.t_remove(inputs=name, type="str3ds", flags="df")

    assert not has_dataset(name, "str3ds")
    assert registered(maps, "raster_3d") == [False] * 3
    assert existing(maps, "raster_3d") == [False] * 3


def test_str3ds_f_keeps_the_maps(tools, make_stds, has_dataset, registered):
    maps, (name,) = make_stds(2, stds_type="str3ds")

    tools.t_remove(inputs=name, type="str3ds", flags="f")

    assert not has_dataset(name, "str3ds")
    assert registered(maps, "raster_3d") == [True] * 2


def test_stvds_rf(tools, make_stds, has_dataset, registered, existing):
    maps, (name,) = make_stds(3, stds_type="stvds")

    tools.t_remove(inputs=name, type="stvds", flags="rf")

    assert not has_dataset(name, "stvds")
    assert registered(maps, "vector") == [False] * 3
    assert existing(maps, "vector") == [True] * 3


def test_stvds_df(tools, make_stds, has_dataset, registered, existing):
    maps, (name,) = make_stds(3, stds_type="stvds")

    tools.t_remove(inputs=name, type="stvds", flags="df")

    assert not has_dataset(name, "stvds")
    assert registered(maps, "vector") == [False] * 3
    assert existing(maps, "vector") == [False] * 3


def test_a_dataset_is_found_by_its_type_only(tools, make_stds, has_dataset):
    _, (name,) = make_stds(1, stds_type="stvds")

    with pytest.raises(ToolError, match=r"not\s+found"):
        tools.t_remove(inputs=name, flags="f")

    assert has_dataset(name, "stvds")


@pytest.fixture
def layered(tools, prefix):
    """A vector map of three layers, registered as three maps of a dataset"""
    vector_points(tools, prefix, [(1, 1), (2, 2)], layers=(1, 2, 3))
    layers = [f"{prefix}:{layer}" for layer in (1, 2, 3)]
    name = f"{prefix}_ds"
    register_stds(
        tools,
        "stvds",
        name,
        [MapSpec(layer, None, day(n), day(n + 1)) for n, layer in enumerate(layers)],
    )
    return prefix, layers, name


def test_vector_layers_rf(tools, layered, registered, existing):
    vector, layers, name = layered

    tools.t_remove(inputs=name, type="stvds", flags="rf")

    assert registered(layers, "vector") == [False] * 3
    assert existing([vector], "vector") == [True]


def test_vector_layers_df_delete_the_map_once(tools, layered, registered, existing):
    vector, layers, name = layered

    tools.t_remove(inputs=name, type="stvds", flags="df")

    assert registered(layers, "vector") == [False] * 3
    assert existing([vector], "vector") == [False]
