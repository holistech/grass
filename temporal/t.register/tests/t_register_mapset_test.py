"""Test t.register with maps of another mapset

The dataset and the temporal database entries belong to the current mapset,
the maps to the mapset they were made in. The project has the mapsets "other"
(where the maps are made) and "work" (where the tests run, with "other" in the
search path). Each test registers maps of its own, because registering sets
the time of the map.
"""

import pytest

from grass.temporal.testing.data import make_map
from grass.temporal.testing.readback import list_maps
from grass.tools import ToolError

# Almost every test of the module runs longer than one second (measured
# 18.10.2026 with pytest --durations).
pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def work(two_mapsets):
    """Tools in mapset work; the maps foreign_1 to foreign_4 are in mapset other"""
    for number in (1, 2, 3, 4):
        make_map(two_mapsets.other, "raster", f"foreign_{number}", number)
    return two_mapsets.work


def test_maps_of_another_mapset_in_a_dataset_of_the_current_one(work):
    tools = work
    tools.t_create(output="mixed", title="t", description="d")

    tools.t_register(
        type="raster",
        input="mixed",
        maps="foreign_1@other,foreign_2@other",
        start="2001-01-01",
        increment="1 days",
        flags="i",
    )

    result = tools.t_rast_list(
        input="mixed", columns="name,mapset,start_time,end_time", format="json"
    )
    assert [(r["name"], r["mapset"], r["start_time"]) for r in result.json["data"]] == [
        ("foreign_1", "other", "2001-01-01 00:00:00"),
        ("foreign_2", "other", "2001-01-02 00:00:00"),
    ]


def test_name_without_mapset_is_found_in_the_search_path(work):
    tools = work
    tools.t_create(output="searched", title="t", description="d")

    tools.t_register(
        type="raster", input="searched", maps="foreign_3", start="2002-02-02"
    )

    rows = list_maps(tools, "strds", "searched")
    assert [(row.name, row.start) for row in rows] == [
        ("foreign_3", "2002-02-02 00:00:00")
    ]


def test_dataset_in_another_mapset_is_refused(work):
    tools = work

    with pytest.raises(ToolError, match="not found"):
        tools.t_register(
            type="raster", input="nothing@other", maps="foreign_4", start="2001-01-01"
        )
