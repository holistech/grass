"""Registration across mapsets and a change of the mapset

The tests of the earlier gunittest files test_register_function.py (history
of a map from another mapset, registration of maps of another mapset) and
test_mapset_change.py. The mapsets are made in the project of the session,
which lives in tmp_path.

Every test ends in PERMANENT again: the session is shared by the tests of
the module, and grass.temporal binds to the mapset at tgis.init().
"""

import datetime
from pathlib import Path

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.tools import Tools

# What the history of a map says; the tests write it into the files of the
# map, so the creator is not the user who runs the tests.
CREATOR = "helena"
RASTER_CTIME = "Tue Nov  7 01:09:51 2006"
VECTOR_CTIME = "Tue Nov  7 19:48:08 2006"


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=80, s=0, e=120, w=0, res=10)
    return tools


def reinit():
    """Bind grass.temporal to the mapset that is current now"""
    tgis.stop_subprocesses()
    tgis.init()


@pytest.fixture
def permanent(tools):
    """The test starts and ends in PERMANENT"""
    tools.g_mapset(mapset="PERMANENT")
    reinit()
    yield tools
    tools.g_mapset(mapset="PERMANENT")
    reinit()


def mapset_path(name):
    gisenv = gs.gisenv()
    return Path(gisenv["GISDBASE"]) / gisenv["LOCATION_NAME"] / name


def test_a_registered_raster_map_has_the_history_of_the_map(permanent):
    tools = permanent
    tools.g_mapset(mapset="history_raster", flags="c")
    tools.r_mapcalc(expression="hist_raster = 1")
    hist = mapset_path("history_raster") / "hist" / "hist_raster"
    lines = hist.read_text().split("\n")
    # The first line is the creation time, the fourth the creator.
    assert lines[3] != CREATOR
    lines[0], lines[3] = RASTER_CTIME, CREATOR
    hist.write_text("\n".join(lines))
    tools.g_mapset(mapset="PERMANENT")
    tools.g_mapsets(operation="add", mapset="history_raster")
    reinit()

    tgis.register_maps_in_space_time_dataset(
        type="raster",
        name=None,
        maps="hist_raster@history_raster",
        start="2001-01-01 10:30:01",
        increment="1 year",
        interval=True,
    )

    registered = tgis.RasterDataset("hist_raster@history_raster")
    registered.select(None, tgis.get_current_mapset())
    assert registered.base.get_ctime() == datetime.datetime(2006, 11, 7, 1, 9, 51)
    assert registered.base.get_creator() == CREATOR


def test_a_registered_vector_map_has_the_history_of_the_map(permanent):
    tools = permanent
    tools.g_mapset(mapset="history_vector", flags="c")
    tools.v_random(output="hist_vector", npoints=3, seed=1)
    # grass.temporal reads the creator and the date of a vector map from its
    # header, the lines "DIGIT NAME:" and "MAP DATE:" (checked 19.10.2026 by
    # reading the header of a map that v.random made).
    head = mapset_path("history_vector") / "vector" / "hist_vector" / "head"
    lines = head.read_text().split("\n")
    assert CREATOR not in lines[2]
    lines[2] = f"DIGIT NAME:   {CREATOR}"
    lines[4] = f"MAP DATE:     {VECTOR_CTIME}"
    head.write_text("\n".join(lines))
    tools.g_mapset(mapset="PERMANENT")
    tools.g_mapsets(operation="add", mapset="history_vector")
    reinit()

    tgis.register_maps_in_space_time_dataset(
        type="vector",
        name=None,
        maps="hist_vector@history_vector",
        start="2001-01-01 10:30:01",
        increment="1 year",
        interval=True,
    )

    registered = tgis.VectorDataset("hist_vector@history_vector")
    registered.select(None, tgis.get_current_mapset())
    assert registered.base.get_ctime() == datetime.datetime(2006, 11, 7, 19, 48, 8)
    assert registered.base.get_creator() == CREATOR


def make_dataset(name):
    return tgis.open_new_stds(
        name=name,
        type="strds",
        temporaltype="absolute",
        title="Test strds",
        descr="Test strds",
        semantic="field",
        overwrite=True,
    )


def test_maps_of_another_mapset_go_into_a_dataset_of_the_current_mapset(
    permanent, temporal_module_session
):
    tools = permanent
    tools.r_mapcalc(expression="access_1 = 1")
    tools.r_mapcalc(expression="access_2 = 2")
    make_dataset("access_abs")
    tgis.register_maps_in_space_time_dataset(
        type="raster",
        name="access_abs",
        maps="access_1,access_2",
        start="2001-01-01",
        increment="1 day",
        interval=True,
    )
    tools.g_mapset(mapset="access_work", flags="c")
    tools.g_mapsets(operation="add", mapset="PERMANENT")
    reinit()
    assert tgis.get_current_mapset() == "access_work"
    make_dataset("access_abs")

    # The names are not fully qualified, the maps are in another mapset.
    tgis.register_maps_in_space_time_dataset(
        type="raster",
        name="access_abs@access_work",
        maps="access_1,access_2",
        start="2001-01-01",
        increment="1 day",
        interval=True,
    )

    stds = tgis.open_old_stds("access_abs@access_work", "strds")
    stds.select()
    registered = stds.get_registered_maps_as_objects()
    assert [item.get_id() for item in registered] == [
        "access_1@PERMANENT",
        "access_2@PERMANENT",
    ]
    assert stds.get_absolute_time() == (
        datetime.datetime(2001, 1, 1),
        datetime.datetime(2001, 1, 3),
    )

    result = Tools(
        session=temporal_module_session,
        overwrite=True,
        consistent_return_value=True,
        capture_stderr=True,
    ).t_remove(type="strds", inputs="access_abs@access_work", flags="df")

    def in_db(name):
        return tgis.dataset_factory("strds", name).is_in_db()

    assert in_db("access_abs@access_work") is False
    # The dataset of the same name in PERMANENT is another one and stays.
    assert in_db("access_abs@PERMANENT") is True
    # GRASS writes to the current mapset only: -d leaves the maps of another
    # mapset where they are and says so for each of them.
    text = " ".join(result.stderr.split())
    for name in ("access_1", "access_2"):
        assert f"Map <{name}> is in mapset <PERMANENT> and is not removed" in text
    listed = tools.g_list(type="raster", mapset="PERMANENT").stdout.split()
    assert {"access_1", "access_2"} <= set(listed)


def test_a_change_of_the_mapset_is_taken_into_account(permanent):
    tools = permanent
    tools.g_mapset(mapset="mapset_test1", flags="c")
    assert tools.g_mapsets(flags="p", format="json")["mapsets"] == [
        "mapset_test1",
        "PERMANENT",
    ]
    tgis.init()
    assert tgis.get_current_mapset() == "mapset_test1"

    tools.g_mapset(mapset="mapset_test2", flags="c")
    # The old test failed here if the change was not noticed.
    tgis.init()

    assert tools.g_mapsets(flags="p", format="json")["mapsets"] == [
        "mapset_test2",
        "PERMANENT",
    ]
    assert tgis.get_current_mapset() == "mapset_test2"
