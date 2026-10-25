"""Regression tests for faults in queries, registration and topology"""

from datetime import datetime
from pathlib import Path

import pytest

import grass.temporal as tgis
from grass.temporal import spatio_temporal_relationships
from grass.temporal.testing.data import MapSpec, day, make_map, register_stds
from grass.temporal.testing.session import mapset_session, temporal_session
from grass.tools import Tools

pytestmark = pytest.mark.real_io


def _open_handles(path):
    """Count the file descriptors of this process that point to the file"""
    target = Path(path).resolve()
    count = 0
    for descriptor in Path("/proc/self/fd").iterdir():
        try:
            if descriptor.readlink().resolve() == target:
                count += 1
        except OSError:
            continue
    return count


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


@pytest.fixture
def small_strds(two_mapsets):
    work, _other = two_mapsets
    make_map(work, "raster", "b15_map", 1, overwrite=True)
    register_stds(
        work,
        "strds",
        "b15_ds",
        [MapSpec("b15_map", None, day(0), day(1))],
        via="library",
        overwrite=True,
    )
    return tgis.open_old_stds("b15_ds", "strds")


def test_where_with_a_semicolon_in_a_value_is_kept(small_strds):
    rows = small_strds.get_registered_maps(
        "name", where="name = 'a;b' OR name = 'b15_map'", order="name"
    )

    assert [row["name"] for row in rows] == ["b15_map"]


def test_where_with_a_semicolon_is_not_cut_into_a_valid_statement(small_strds):
    # Cutting at the semicolon used to turn this into "name = 'b15_map'" and
    # hide that the condition is not valid SQL.
    with pytest.raises(tgis.SQLStatementError):
        small_strds.get_registered_maps("name", where="name = 'b15_map'; --")


def _unregistered_map():
    return tgis.RasterDataset("b16_not_in_db@" + tgis.get_current_mapset())


def test_register_map_leaves_a_given_connection_open_on_abort(small_strds):
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    with pytest.raises(tgis.FatalError, match="inserted in the temporal"):
        small_strds.register_map(_unregistered_map(), dbif)

    assert dbif.is_connected()
    dbif.close()


def test_register_map_closes_its_own_connection_on_abort(small_strds):
    path = tgis.get_tgis_database_string()
    before = _open_handles(path)

    with pytest.raises(tgis.FatalError) as error:
        small_strds.register_map(_unregistered_map())

    assert error.tb is not None
    assert _open_handles(path) == before


def test_register_map_leaves_a_given_connection_open_when_done(small_strds):
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    # The map is registered already: the call ends with a warning and False
    done = tgis.RasterDataset("b15_map@" + tgis.get_current_mapset())

    assert small_strds.register_map(done, dbif) is False

    assert dbif.is_connected()
    dbif.close()


@pytest.mark.parametrize("dates", [None, [], [datetime(2001, 1, 1)]])
def test_common_granularity_of_no_granules_is_none(dates):
    assert tgis.compute_common_absolute_time_granularity([], dates) is None


def test_common_granularity_of_an_invalid_granule_is_false_with_dates():
    result = tgis.compute_common_absolute_time_granularity(
        ["nonsense"], [datetime(2001, 1, 1)]
    )

    assert result is False


@pytest.mark.parametrize(
    "label", ["x' OR '1'='1", "x' OR '1'='1_1", "it's", "it's_01", "0' OR '1'='1"]
)
def test_semantic_label_with_a_quote_is_text(small_strds, label):
    # The map has no semantic label, so no label can select it. A label that
    # leaves its quotes opens the statement: the first one selects every map.
    small_strds.semantic_label = label

    rows = small_strds.get_registered_maps("name")

    assert not rows


@pytest.fixture
def freed(monkeypatch):
    """Record the calls that free the R-tree and the list of the builder"""
    calls = []
    for module, name in (
        (spatio_temporal_relationships.rtree, "RTreeDestroyTree"),
        (spatio_temporal_relationships.gis, "G_free_ilist"),
    ):
        original = getattr(module, name)

        def record(*args, _original=original, _name=name):
            calls.append(_name)
            return _original(*args)

        monkeypatch.setattr(module, name, record)
    return calls


def _maps(count):
    maps = []
    for number in range(count):
        item = tgis.RasterDataset(f"b21_{number}@" + tgis.get_current_mapset())
        item.set_absolute_time(day(number), day(number + 1))
        maps.append(item)
    return maps


def test_build_frees_the_tree_and_the_list(two_mapsets, freed):
    tgis.SpatioTemporalTopologyBuilder().build(_maps(3))

    assert sorted(freed) == ["G_free_ilist", "RTreeDestroyTree"]


def test_build_frees_the_tree_and_the_list_when_it_fails(
    two_mapsets, freed, monkeypatch
):
    def refuse(*args):
        msg = "stop"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        spatio_temporal_relationships, "set_temporal_relationship", refuse
    )

    with pytest.raises(RuntimeError, match="stop"):
        tgis.SpatioTemporalTopologyBuilder().build(_maps(3))

    assert sorted(freed) == ["G_free_ilist", "RTreeDestroyTree"]
