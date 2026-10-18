"""Test t.remove with more maps than it deletes in one step

t.remove collects the statements for the maps of a dataset and executes them
(and deletes the maps with g.remove, for -d) after every 99 maps, then the
rest. A dataset of 120 maps takes the second path as well. -d is the flag
that deletes maps in these steps, and each dataset type has its own call of
g.remove there, so it is the one tested, once per type.
"""

from io import StringIO

import pytest

from grass.temporal.testing.data import MapSpec, day, register_stds, vector_points

COUNT = 120

# Each test makes and removes 120 maps (about 50 s, measured 18.10.2026 with a
# serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _raster_maps(tools, prefix, mapcalc):
    """COUNT maps <prefix>_1 ... made by one call of the map calculator"""
    names = [f"{prefix}_{number}" for number in range(1, COUNT + 1)]
    expressions = [f"{name} = {number}" for number, name in enumerate(names, 1)]
    getattr(tools, mapcalc)(file=StringIO("\n".join(expressions)))
    return names


def _vector_layers(tools, prefix):
    """Two vector maps with 99 and COUNT - 99 layers, and the names of the layers

    The first step of t.remove ends after the 99th map, so the first vector
    map is deleted in it and the second one only in the last step. With one
    map for all layers the last step would delete it again and hide a first
    step that does nothing.
    """
    names = []
    vectors = (f"{prefix}_a", f"{prefix}_b")
    for vector, layers in zip(
        vectors, (range(1, 100), range(1, COUNT - 98)), strict=True
    ):
        vector_points(tools, vector, [(1, 1)], layers=layers)
        names += [f"{vector}:{layer}" for layer in layers]
    return names, list(vectors)


@pytest.mark.parametrize(
    ("stds_type", "map_type"),
    [("strds", "raster"), ("str3ds", "raster_3d"), ("stvds", "vector")],
)
def test_df_deletes_every_map(
    tools, prefix, stds_type, map_type, has_dataset, registered, existing
):
    if stds_type == "stvds":
        names, spatial = _vector_layers(tools, prefix)
    else:
        mapcalc = "r_mapcalc" if stds_type == "strds" else "r3_mapcalc"
        names = spatial = _raster_maps(tools, prefix, mapcalc)
    tools.r_mapcalc(expression=f"{prefix}_bystander = 0")
    dataset = f"{prefix}_ds"
    register_stds(
        tools,
        stds_type,
        dataset,
        [MapSpec(name, None, day(n), day(n + 1)) for n, name in enumerate(names)],
    )

    tools.t_remove(inputs=dataset, type=stds_type, flags="df")

    assert not has_dataset(dataset, stds_type)
    assert registered(names, map_type) == [False] * COUNT
    assert existing(spatial, map_type) == [False] * len(spatial)
    assert existing([f"{prefix}_bystander"]) == [True]
