"""Test t.remove with a dataset of the current mapset that holds maps of another one

The maps belong to the mapset "other" and are not registered there, only in the
datasets of the mapset "work". GRASS writes to the current mapset only, so -d
cannot remove the maps; it says so for each map and still removes the dataset.
"""

import pytest

from grass.temporal.testing.readback import message

pytestmark = pytest.mark.slow


@pytest.fixture
def foreign(two_mapsets, prefix):
    """The dataset <prefix>_ds of mapset work and its maps of mapset other"""
    work, other = two_mapsets
    maps = [f"{prefix}_{i}" for i in range(2)]
    for name in maps:
        other.r_mapcalc(expression=f"{name} = 1")
    work.t_create(output=f"{prefix}_ds", title="t", description="t")
    work.t_register(
        input=f"{prefix}_ds",
        maps=[f"{name}@other" for name in maps],
        start="2001-01-01",
        increment="1 days",
    )
    return f"{prefix}_ds", maps


def _datasets(tools):
    return tools.t_list(type="strds", columns="name").stdout


def test_rf_removes_the_dataset_of_maps_that_are_registered_here_only(
    two_mapsets, foreign
):
    work, other = two_mapsets
    name, maps = foreign

    work.t_remove(inputs=name, flags="rf")

    assert name not in _datasets(work)
    assert set(maps) <= set(other.g_list(type="raster", mapset="other").stdout.split())


def test_df_warns_for_each_map_of_another_mapset(two_mapsets, foreign):
    work, other = two_mapsets
    name, maps = foreign

    result = work.t_remove(inputs=name, flags="df")

    for item in maps:
        assert f"Map <{item}> is in mapset <other> and is not removed" in " ".join(
            message(result).split()
        )
    assert name not in _datasets(work)
    assert set(maps) <= set(other.g_list(type="raster", mapset="other").stdout.split())


def test_df_does_not_remove_a_map_of_the_current_mapset_with_the_same_name(
    two_mapsets, foreign
):
    work, other = two_mapsets
    name, maps = foreign
    work.r_mapcalc(expression=f"{maps[0]} = 5")

    work.t_remove(inputs=name, flags="df")

    assert maps[0] in work.g_list(type="raster", mapset="work").stdout.split()
