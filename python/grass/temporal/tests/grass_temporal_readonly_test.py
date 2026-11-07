"""Maps and datasets of another mapset are read-only for the file metadata

The time stamp and the semantic label of a map are files in the mapset that
is current in the session, whatever mapset the map is named after. A map of
another mapset in the temporal database must therefore never write them,
otherwise a file appears in the current mapset for a map that does not live
there. The check follows the current mapset at the time of the call, because
a process can switch to a second session.
"""

from datetime import datetime
from pathlib import Path

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal.state import STATE
from grass.temporal.testing.session import mapset_session, temporal_session
from grass.tools import Tools

pytestmark = pytest.mark.real_io

CURRENT = "second"
OWNER = "source"


@pytest.fixture(scope="module")
def cross_mapset(tmp_path_factory):
    """Yield the session of "second" after registering a map of "source"

    "source" holds the map foreign_map; "second" holds local_map in the
    dataset test_strds, and foreign_map@source is registered there with a
    time and the label S2_1 from a file.
    """
    root = tmp_path_factory.mktemp("readonly")
    with temporal_session(root / "project", mapset=CURRENT) as session:
        with mapset_session(session, OWNER) as owner:
            owner_tools = Tools(session=owner)
            owner_tools.g_region(s=0, n=1, w=0, e=1, res=1)
            owner_tools.r_mapcalc(expression="foreign_map = 1")
        tools = Tools(session=session)
        tools.g_region(s=0, n=1, w=0, e=1, res=1)
        tools.r_mapcalc(expression="local_map = 1")
        tools.t_create(output="test_strds", type="strds", title="T", description="T")
        tools.t_register(input="test_strds", maps="local_map", start="2001-01-01")
        map_file = root / "maps.txt"
        map_file.write_text("foreign_map@source|2010-06-01|S2_1\n")
        tools.t_register(input="test_strds", file=map_file)
        yield session


def _misc_file(session, name, item):
    """Return the path of the file item of the map name in the current mapset"""
    env = gs.gisenv(env=session.env)
    return (
        Path(env["GISDBASE"])
        / env["LOCATION_NAME"]
        / env["MAPSET"]
        / "cell_misc"
        / name
        / item
    )


def test_no_ghost_semantic_label_in_current_mapset(cross_mapset):
    """The label of a map of another mapset leaves no file in the current mapset"""
    assert not _misc_file(cross_mapset, "foreign_map", "semantic_label").exists()


def test_no_ghost_timestamp_in_current_mapset(cross_mapset):
    """The time of a map of another mapset leaves no file in the current mapset"""
    assert not _misc_file(cross_mapset, "foreign_map", "timestamp").exists()


def test_own_map_still_gets_label_and_timestamp(cross_mapset):
    """A map of the current mapset has its time stamp and label as files"""
    rmap = tgis.RasterDataset(f"local_map@{CURRENT}")
    rmap.set_absolute_time(datetime(2001, 1, 1))
    rmap.set_semantic_label("S2_2")
    assert _misc_file(cross_mapset, "local_map", "timestamp").exists()
    assert _misc_file(cross_mapset, "local_map", "semantic_label").exists()
    assert rmap.read_semantic_label_from_grass()
    assert rmap.metadata.get_semantic_label() == "S2_2"


def test_foreign_map_keeps_its_time_in_the_database(cross_mapset):
    """The guard skips the file of the map, not its registration"""
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        rmap = tgis.RasterDataset(f"foreign_map@{OWNER}")
        rmap.select(dbif=dbif, mapset=CURRENT)
        start, _end = rmap.get_absolute_time()
    finally:
        dbif.close()
    assert rmap.get_readonly()
    assert start == datetime(2010, 6, 1)


def test_foreign_map_direct_writes_are_skipped(cross_mapset, monkeypatch):
    """The write and remove methods of a map of another mapset do nothing"""
    rmap = tgis.RasterDataset(f"foreign_map@{OWNER}")
    rmap.set_absolute_time(datetime(2010, 6, 1))
    rmap.metadata.set_semantic_label("S2_1")

    def unexpected(*args, **kwargs):
        pytest.fail("a file of the current mapset was written")

    monkeypatch.setattr(rmap.ciface, "call", unexpected)
    monkeypatch.setattr(rmap, "_call", unexpected)
    assert not rmap.write_timestamp_to_grass()
    assert not rmap.write_semantic_label_to_grass()
    assert not rmap.remove_timestamp_from_grass()


def test_foreign_timestamp_removal_keeps_the_file_of_the_current_mapset(cross_mapset):
    """Removing the time of foreign_map@source does not remove a local file"""
    rmap = tgis.RasterDataset(f"foreign_map@{OWNER}")
    stamp = _misc_file(cross_mapset, "foreign_map", "timestamp")
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text("local timestamp")
    try:
        assert not rmap.remove_timestamp_from_grass()
        assert stamp.read_text() == "local timestamp"
    finally:
        stamp.unlink(missing_ok=True)


def test_readonly_follows_the_current_mapset(cross_mapset, monkeypatch):
    """readonly is computed at the call from the mapset of the row"""
    rmap = tgis.RasterDataset(f"local_map@{CURRENT}")
    assert rmap.get_readonly() is False
    assert rmap.base.get_readonly() is False
    assert rmap.base.readonly is False

    monkeypatch.setattr(STATE, "current_mapset", OWNER)
    assert rmap.get_readonly() is True
    assert rmap.base.readonly is True

    monkeypatch.setattr(STATE, "current_mapset", CURRENT)
    assert rmap.get_readonly() is False
    rmap.base.set_mapset(OWNER)
    assert rmap.get_readonly() is True
    assert rmap.base.readonly is True
    rmap.base.set_mapset(CURRENT)
    assert rmap.get_readonly() is False


def test_dataset_of_another_mapset_is_readonly(cross_mapset):
    """A space time dataset of another mapset is read-only, its own is not"""
    own = tgis.SpaceTimeRasterDataset(f"test_strds@{CURRENT}")
    other = tgis.SpaceTimeRasterDataset(f"test_strds@{OWNER}")
    assert own.base.readonly is False
    assert other.base.readonly is True
