"""Regression tests for faults in queries, registration and topology"""

import pytest

import grass.temporal as tgis
from grass.temporal.testing.data import MapSpec, day, make_map, register_stds
from grass.temporal.testing.session import mapset_session, temporal_session
from grass.tools import Tools

pytestmark = pytest.mark.real_io


@pytest.fixture(scope="module")
def two_mapsets(tmp_path_factory):
    """Tools in the mapsets "work" and "other" of one project

    grass.temporal is bound to "work", which has "other" in its search path.
    """
    project = tmp_path_factory.mktemp("query") / "project"
    with (
        temporal_session(project, mapset="work") as work,
        mapset_session(work, "other") as other,
    ):
        tools = [
            Tools(session=session, consistent_return_value=True)
            for session in (work, other)
        ]
        for item in tools:
            item.g_region(n=1, s=0, e=1, w=0, res=1)
        tools[0].g_mapsets(operation="add", mapset="other")
        tgis.stop_subprocesses()
        tgis.init(raise_fatal_error=True)
        yield tools


def test_where_with_or_does_not_return_rows_of_another_mapset(two_mapsets):
    work, other = two_mapsets
    make_map(work, "raster", "b14_work", 1)
    make_map(other, "raster", "b14_other", 2)
    register_stds(
        work,
        "strds",
        "b14_ds",
        [
            MapSpec("b14_work", None, day(0), day(1)),
            MapSpec("b14_other@other", None, day(1), day(2)),
        ],
        via="library",
    )

    result = tgis.get_dataset_list(
        "raster",
        "absolute",
        columns="name,mapset",
        where="name = 'b14_other' OR name = 'b14_work'",
    )

    rows = {
        (mapset, row["name"], row["mapset"])
        for mapset, rows in result.items()
        for row in rows
    }
    # A row is listed under the mapset whose database was asked for the maps
    # of that mapset; the map of "other" is registered in the database of
    # "work" but belongs to "other".
    assert rows == {("work", "b14_work", "work")}
