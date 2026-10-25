# SPDX-License-Identifier: GPL-2.0-or-later

"""Characterize every call a client can make to the C library server

The server runs in a subprocess; each test sends the call through the client
methods of CLibrariesInterface and checks the answer for a raster, a 3D
raster and a vector map, and for a map that does not exist. The expected
values follow from the data: the region is 80 by 120 map units at a
resolution of 10, so the maps have 8 rows and 12 columns, and the vector
map holds 10 random points.
"""

import datetime
from pathlib import Path

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal import c_libraries_interface
from grass.pygrass.messages import FatalError
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools

pytestmark = pytest.mark.real_io

KINDS = {"raster": "rast", "raster3d": "rast3", "vector": "vect"}
TIMESTRING = "13 Jan 1999 14:30:05"
TIMESTAMP = datetime.datetime(1999, 1, 13, 14, 30, 5)


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    """A session that grass.temporal can use, in one module-wide project"""
    with temporal_session(tmp_path_factory.mktemp("ciface") / "project") as session:
        tgis.init(raise_fatal_error=True)
        yield session


@pytest.fixture(scope="module")
def ciface(session):
    """The client, with its server, shared by the tests of the module"""
    client = tgis.CLibrariesInterface()
    yield client
    client.stop()


@pytest.fixture
def maps(session):
    """Create the maps anew, so that no test sees a timestamp of another

    Overwriting a raster keeps its timestamp, so the maps are removed first.
    """
    tools = Tools(session=session, overwrite=True)
    for kind, name in KINDS.items():
        tools.g_remove(type=kind.replace("raster3d", "raster_3d"), name=name, flags="f")
    tools.g_region(n=80, s=0, e=120, w=0, t=1, b=0, res=10, res3=10)
    tools.r_mapcalc(expression="rast = 1")
    tools.r3_mapcalc(expression="rast3 = 1")
    tools.v_random(output="vect", npoints=10, seed=1)


def method(ciface, pattern, kind):
    """Return the client method of kind, such as has_raster3d_timestamp"""
    return getattr(ciface, pattern.format(kind=kind))


@pytest.mark.parametrize("kind", KINDS)
def test_map_exists(ciface, maps, kind):
    exists = method(ciface, "{kind}_map_exists", kind)
    mapset = tgis.get_current_mapset()

    assert exists(KINDS[kind], mapset) is True
    assert exists("no_such_map", mapset) is False


def test_raster_info(ciface, maps):
    mapset = tgis.get_current_mapset()

    assert ciface.read_raster_info("rast", mapset) == {
        "north": 80.0,
        "south": 0.0,
        "east": 120.0,
        "west": 0.0,
        "nsres": 10.0,
        "ewres": 10.0,
        "rows": 8,
        "cols": 12,
        "datatype": "CELL",
        "min": 1,
        "max": 1,
    }


def test_raster3d_info(ciface, maps):
    mapset = tgis.get_current_mapset()

    assert ciface.read_raster3d_info("rast3", mapset) == {
        "north": 80.0,
        "south": 0.0,
        "east": 120.0,
        "west": 0.0,
        "nsres": 10.0,
        "ewres": 10.0,
        "tbres": 1.0,
        "rows": 8,
        "cols": 12,
        "depths": 1,
        "top": 1.0,
        "bottom": 0.0,
        "datatype": "DCELL",
        "min": 1.0,
        "max": 1.0,
    }


def test_vector_info(ciface, maps):
    info = ciface.read_vector_info("vect", tgis.get_current_mapset())

    assert info["points"] == 10
    assert info["primitives"] == 10
    assert info["map3d"] is False
    assert (info["lines"], info["boundaries"], info["areas"]) == (0, 0, 0)
    assert 0 < info["south"] < info["north"] < 80
    assert 0 < info["west"] < info["east"] < 120
    assert sorted(info) == sorted(
        [
            "areas",
            "boundaries",
            "bottom",
            "centroids",
            "east",
            "faces",
            "holes",
            "islands",
            "kernels",
            "lines",
            "map3d",
            "nodes",
            "north",
            "points",
            "primitives",
            "south",
            "top",
            "volumes",
            "west",
        ]
    )


@pytest.mark.parametrize("kind", KINDS)
def test_info_of_a_missing_map_is_none(ciface, maps, kind):
    read = method(ciface, "read_{kind}_info", kind)

    assert read("no_such_map", tgis.get_current_mapset()) is None


@pytest.mark.parametrize("kind", KINDS)
def test_history(ciface, maps, kind):
    read = method(ciface, "read_{kind}_history", kind)
    mapset = tgis.get_current_mapset()

    history = read(KINDS[kind], mapset)

    assert sorted(history) == ["creation_time", "creator"]
    assert history["creator"]
    assert history["creation_time"]
    assert read("no_such_map", mapset) is None


@pytest.mark.parametrize("kind", KINDS)
def test_timestamp_cycle(ciface, maps, kind):
    name = KINDS[kind]
    mapset = tgis.get_current_mapset()
    has = method(ciface, "has_{kind}_timestamp", kind)
    read = method(ciface, "read_{kind}_timestamp", kind)
    write = method(ciface, "write_{kind}_timestamp", kind)
    remove = method(ciface, "remove_{kind}_timestamp", kind)

    assert has(name, mapset) is False
    assert write(name, mapset, TIMESTRING) == 1
    assert has(name, mapset) is True
    assert read(name, mapset) == (1, (TIMESTAMP, None))
    assert remove(name, mapset) == 1
    assert has(name, mapset) is False
    assert read(name, mapset) == (0, (None, None, None))


@pytest.mark.parametrize("kind", KINDS)
def test_an_interval_has_a_start_and_an_end(ciface, maps, kind):
    name = KINDS[kind]
    mapset = tgis.get_current_mapset()

    method(ciface, "write_{kind}_timestamp", kind)(
        name, mapset, "13 Jan 1999 14:30:05 / 14 Jan 1999 14:30:05"
    )

    assert method(ciface, "read_{kind}_timestamp", kind)(name, mapset) == (
        1,
        (TIMESTAMP, TIMESTAMP + datetime.timedelta(days=1)),
    )


@pytest.mark.parametrize("kind", KINDS)
def test_a_relative_timestamp_is_read_with_its_unit(ciface, maps, kind):
    name = KINDS[kind]
    mapset = tgis.get_current_mapset()

    method(ciface, "write_{kind}_timestamp", kind)(name, mapset, "5 days")

    assert method(ciface, "read_{kind}_timestamp", kind)(name, mapset) == (
        1,
        (5, None, "days"),
    )


@pytest.mark.parametrize("kind", KINDS)
def test_an_unreadable_timestamp_is_not_written(ciface, maps, kind):
    name = KINDS[kind]
    mapset = tgis.get_current_mapset()
    write = method(ciface, "write_{kind}_timestamp", kind)

    assert write(name, mapset, "not a time") == -2
    assert method(ciface, "has_{kind}_timestamp", kind)(name, mapset) is False
    # The server answered and went on.
    assert write(name, mapset, TIMESTRING) == 1


def test_vector_timestamps_are_kept_per_layer(ciface, maps):
    mapset = tgis.get_current_mapset()

    assert ciface.write_vector_timestamp("vect", mapset, TIMESTRING, layer="1") == 1

    assert ciface.has_vector_timestamp("vect", mapset, layer="1") is True
    assert ciface.read_vector_timestamp("vect", mapset, layer="1") == (
        1,
        (TIMESTAMP, None),
    )
    assert ciface.has_vector_timestamp("vect", mapset, layer="2") is False
    # No layer means the first one.
    assert ciface.has_vector_timestamp("vect", mapset) is True
    assert ciface.remove_vector_timestamp("vect", mapset, layer="1") == 1
    assert ciface.has_vector_timestamp("vect", mapset, layer="1") is False


def test_semantic_label_cycle(ciface, maps):
    mapset = tgis.get_current_mapset()

    assert ciface.read_raster_semantic_label("rast", mapset) is None
    assert ciface.write_raster_semantic_label("rast", mapset, "S2_1") is True
    assert ciface.read_raster_semantic_label("rast", mapset) == "S2_1"


def test_the_server_names(ciface, session):
    mapset = tgis.get_current_mapset()

    assert ciface.get_mapset() == mapset
    assert ciface.available_mapsets() == [mapset]
    assert ciface.get_driver_name() == "sqlite"
    assert ciface.get_driver_name(mapset) == "sqlite"
    database = Path(gs.gisenv(env=session.env)["GISDBASE"])
    assert Path(ciface.get_database_name()).name == "sqlite.db"
    assert Path(ciface.get_database_name()).parent.name == "tgis"
    assert Path(ciface.get_database_name()).is_relative_to(database)
    assert ciface.get_database_name(mapset) == ciface.get_database_name()


def test_a_killed_server_is_restarted(ciface, maps):
    mapset = tgis.get_current_mapset()
    old = ciface.server.pid

    ciface.server.kill()
    ciface.server.join(10)

    assert ciface.raster_map_exists("rast", mapset) is True
    assert ciface.server.pid != old


def test_a_second_client_has_its_own_server(ciface, maps):
    mapset = tgis.get_current_mapset()
    other = tgis.CLibrariesInterface()
    try:
        assert other.server.pid != ciface.server.pid
        assert other.raster_map_exists("rast", mapset) is True
        assert ciface.raster_map_exists("rast", mapset) is True
    finally:
        other.stop()


@pytest.mark.parametrize("number", [5, 40, 99, -1])
def test_an_unknown_request_is_answered_with_an_error(ciface, number):
    pid = ciface.server.pid

    ciface.client_conn.send([number])
    with pytest.raises(FatalError, match="function"):
        ciface.safe_receive("unknown function")

    assert ciface.get_mapset()
    assert ciface.server.pid == pid


def test_a_call_by_an_unknown_name_is_answered_with_an_error(ciface):
    pid = ciface.server.pid

    with pytest.raises(FatalError, match="no function no_such_function"):
        ciface.call("no_such_function")

    assert ciface.get_mapset()
    assert ciface.server.pid == pid


def test_a_function_is_registered_once():
    # A second registration under the same name would replace the first
    # silently, so the decorator refuses it.
    with pytest.raises(ValueError, match="registered twice"):

        @c_libraries_interface._handler("get_mapset")
        def other(**_):
            return None


def test_an_unknown_map_type_is_answered_also_by_a_function_without_answer_on_error(
    ciface,
):
    # get_mapset sends nothing when it fails; with a map type it does not
    # read, the call used to leave the client waiting for ever.
    pid = ciface.server.pid

    with pytest.raises(FatalError, match="Unknown map type bogus"):
        ciface.call("get_mapset", "bogus")

    assert ciface.get_mapset()
    assert ciface.server.pid == pid


def test_a_request_of_the_wrong_length_is_answered_with_an_error(ciface):
    pid = ciface.server.pid

    ciface.client_conn.send(("get_mapset", None))
    with pytest.raises(FatalError, match="no function"):
        ciface.safe_receive("short request")

    assert ciface.get_mapset()
    assert ciface.server.pid == pid
