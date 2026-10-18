"""Test t.unregister with 3D raster maps and vector maps, also in layers

A vector layer is named map:layer and is a map of its own for the temporal
database; the name of the map alone is another one.
"""

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    day,
    register_stds,
    vector_points,
)
from grass.temporal.testing.readback import map_info, stds_info

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def test_raster_3d_maps(tools, make_stds):
    maps, (name,) = make_stds(3, stds_type="str3ds")

    tools.t_unregister(type="raster_3d", input=name, maps=maps[0])

    assert stds_info(tools, "str3ds", name)["number_of_maps"] == 2
    assert map_info(tools, "raster_3d", maps[0]) is not None

    tools.t_unregister(type="raster_3d", maps=f"{maps[0]},{maps[1]}")

    assert [map_info(tools, "raster_3d", m) is None for m in maps] == [
        True,
        True,
        False,
    ]
    assert stds_info(tools, "str3ds", name)["number_of_maps"] == 1


def test_a_raster_3d_map_is_not_found_as_a_raster(tools, make_stds):
    maps, _ = make_stds(1, stds_type="str3ds")

    result = tools.t_unregister(maps=maps[0])

    assert f"Unable to find raster map <{maps[0]}@PERMANENT>" in " ".join(
        result.stderr.split()
    )
    assert map_info(tools, "raster_3d", maps[0]) is not None


def test_vector_maps(tools, make_stds):
    maps, (name,) = make_stds(3, stds_type="stvds")

    tools.t_unregister(type="vector", input=name, maps=maps[2])
    assert stds_info(tools, "stvds", name)["number_of_maps"] == 2
    assert map_info(tools, "vector", maps[2]) is not None

    tools.t_unregister(type="vector", maps=",".join(maps))
    assert [map_info(tools, "vector", m) for m in maps] == [None] * 3
    assert stds_info(tools, "stvds", name)["number_of_maps"] == 0


def test_vector_layers_are_unregistered_one_by_one(tools, prefix):
    vector_points(tools, prefix, [(1, 1), (2, 2)], layers=(1, 2, 3))
    layers = [f"{prefix}:{layer}" for layer in (1, 2, 3)]
    name = f"{prefix}_ds"
    register_stds(
        tools,
        "stvds",
        name,
        [MapSpec(layer, None, day(n), day(n + 1)) for n, layer in enumerate(layers)],
    )
    assert stds_info(tools, "stvds", name)["number_of_maps"] == 3

    tools.t_unregister(type="vector", input=name, maps=layers[0])

    assert stds_info(tools, "stvds", name)["number_of_maps"] == 2
    assert [map_info(tools, "vector", layer) is None for layer in layers] == [False] * 3

    tools.t_unregister(type="vector", maps=layers[1])

    assert [map_info(tools, "vector", layer) is None for layer in layers] == [
        False,
        True,
        False,
    ]
    assert stds_info(tools, "stvds", name)["number_of_maps"] == 1


def test_the_name_of_a_vector_map_without_its_layer_is_another_map(tools, prefix):
    vector_points(tools, prefix, [(1, 1)], layers=(1, 2))
    layers = [f"{prefix}:{layer}" for layer in (1, 2)]
    register_stds(
        tools,
        "stvds",
        f"{prefix}_ds",
        [MapSpec(layer, None, day(n), day(n + 1)) for n, layer in enumerate(layers)],
    )

    result = tools.t_unregister(type="vector", maps=prefix)

    assert f"Unable to find vector map <{prefix}@PERMANENT>" in " ".join(
        result.stderr.split()
    )
    assert [map_info(tools, "vector", layer) is not None for layer in layers] == [
        True
    ] * 2
