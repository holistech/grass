"""Test t.copy -c with --overwrite on maps that the current mapset has already

The source dataset <prefix>_src belongs to the mapset "other" and holds three
maps; the tests run in the mapset "work". A second copy with --overwrite
replaces the maps of the first, unless another dataset holds one of them.
"""

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_daily_stds,
    create_stds,
    intervals,
)
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.tools import ToolError

pytestmark = pytest.mark.slow


@pytest.fixture
def source(two_mapsets, prefix):
    """The dataset <prefix>_src of mapset other and the names of its maps"""
    maps = create_daily_stds(
        two_mapsets.other, "strds", [f"{prefix}_src"], 3, map_prefix=prefix
    )
    return f"{prefix}_src@other", maps


def _values(tools, name):
    return [(row.min, row.max) for row in list_maps(tools, "strds", name)]


def test_copy_maps_overwrite_replaces_maps(two_mapsets, prefix, source):
    work, other = two_mapsets
    name, maps = source
    work.t_copy(input=name, output=f"{prefix}_copy", flags="c")
    # The copies in the current mapset are changed, to see them replaced.
    work.r_mapcalc(expression=f"{maps[0]} = 99", overwrite=True)

    result = work.t_copy(input=name, output=f"{prefix}_copy", flags="c", overwrite=True)

    assert result.returncode == 0
    assert _values(work, f"{prefix}_copy") == [(1, 1), (2, 2), (3, 3)]
    assert [row.name for row in list_maps(work, "strds", f"{prefix}_copy")] == maps
    assert set(maps) <= set(work.g_list(type="raster", mapset="work").stdout.split())


def test_copy_maps_overwrite_replaces_maps_without_dataset(two_mapsets, prefix, source):
    work, _ = two_mapsets
    name, maps = source
    work.r_mapcalc(expression=f"{maps[1]} = 9")

    work.t_copy(input=name, output=f"{prefix}_copy", flags="c", overwrite=True)

    assert _values(work, f"{prefix}_copy") == [(1, 1), (2, 2), (3, 3)]


def test_copy_maps_overwrite_refuses_map_of_other_dataset(two_mapsets, prefix, source):
    work, other = two_mapsets
    name, maps = source
    # A map of the current mapset that another dataset holds.
    create_stds(
        work,
        "strds",
        f"{prefix}_held",
        [MapSpec(maps[1], 9, *intervals(2, granularity="day")[1])],
    )
    before = inventory(work)

    with pytest.raises(ToolError) as error:
        work.t_copy(input=name, output=f"{prefix}_copy", flags="c", overwrite=True)

    text = message(error.value)
    assert f"<{maps[1]}>" in text
    assert f"<{prefix}_held@work>" in text
    assert "cannot be replaced" in text
    # Nothing was copied before the refusal, and the map is as it was.
    assert inventory(work) == before
    assert _values(work, f"{prefix}_held") == [(9, 9)]
