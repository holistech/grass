"""The messages of register_maps_in_space_time_dataset() for maps with a layer

Every refusal and warning of the registration has one text for a map and one
for a map with a layer (vector map "name:layer"). The tests make each of them
happen and compare the whole text, so that the texts stay as they are when the
code that writes them changes.
"""

import importlib
import io
import itertools
from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")

COUNTER = itertools.count(1)
MAPSET = "PERMANENT"


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=80, s=0, e=120, w=0, res=10)
    return tools


@pytest.fixture
def ids(tools):
    """A vector map, a second one, a raster map and unique dataset names

    The datasets and the maps are removed from the temporal database and from
    the mapset after the test.
    """
    number = next(COUNTER)
    names = {
        "vec": f"msg{number}_vec",
        "vec2": f"msg{number}_vec2",
        "ras": f"msg{number}_ras",
        "abs": f"msg{number}_abs",
        "rel": f"msg{number}_rel",
        "rel2": f"msg{number}_rel2",
    }
    tools.v_random(output=names["vec"], npoints=3, seed=1)
    tools.v_random(output=names["vec2"], npoints=3, seed=1)
    tools.r_mapcalc(expression=f"{names['ras']} = 1")
    for key, temporaltype in (
        ("abs", "absolute"),
        ("rel", "relative"),
        ("rel2", "relative"),
    ):
        tgis.open_new_stds(
            name=names[key],
            type="stvds",
            temporaltype=temporaltype,
            title="t",
            descr="t",
            semantic="field",
            overwrite=True,
        )
    yield names
    for key in ("abs", "rel", "rel2"):
        tgis.open_old_stds(names[key], "stvds").delete()
    tools.t_unregister(type="vector", maps=f"{names['vec']},{names['vec2']}")
    tools.t_unregister(type="raster", maps=names["ras"])
    tools.g_remove(flags="f", type="vector", name=f"{names['vec']},{names['vec2']}")
    tools.g_remove(flags="f", type="raster", name=names["ras"])


class Recorder:
    """The message interface of the library, which also keeps the warnings"""

    def __init__(self, messenger):
        self.messenger = messenger
        self.warnings = []

    def warning(self, message):
        self.warnings.append(message)
        self.messenger.warning(message)

    def __getattr__(self, name):
        return getattr(self.messenger, name)


@pytest.fixture
def warnings(monkeypatch):
    """The warnings that the registration gives, as a list of texts"""
    module = importlib.import_module("grass.temporal.register")
    recorder = Recorder(module.get_tgis_message_interface())
    monkeypatch.setattr(module, "get_tgis_message_interface", lambda: recorder)
    return recorder.warnings


def register(kind="vector", **arguments):
    tgis.register_maps_in_space_time_dataset(type=kind, **arguments)


def test_no_time_stamp_of_a_map_with_a_layer(ids):
    with pytest.raises(tgis.FatalError) as error:
        register(maps=f"{ids['vec']}:2")

    assert str(error.value) == (
        f"Unable to register vector map <{ids['vec']}@{MAPSET}> with layer 2. "
        "The map has no timestamp and the start time is not set."
    )


def test_no_time_stamp_of_a_map_without_layer(ids):
    with pytest.raises(tgis.FatalError) as error:
        register(maps=ids["vec"])

    assert str(error.value) == (
        f"Unable to register vector map <{ids['vec']}@{MAPSET}>. "
        "The map has no timestamp and the start time is not set."
    )


def test_a_registered_map_with_a_layer_gets_a_warning_and_a_time_check(ids, warnings):
    register(name=ids["abs"], maps=f"{ids['vec']}:2", start="2001-01-01")

    with pytest.raises(tgis.FatalError) as error:
        register(name=ids["rel"], maps=f"{ids['vec']}:2")

    assert str(error.value) == (
        f"Temporal type of space time dataset <{ids['rel']}@{MAPSET}> and map "
        f"<{ids['vec']}@{MAPSET}> with layer 2 are different"
    )
    assert warnings == [
        "Map is already registered in temporal database. Unable to update "
        f"vector map <{ids['vec']}@{MAPSET}> with layer 2. Overwrite flag is "
        "not set."
    ]


def test_a_registered_map_without_layer_gets_a_warning_and_a_time_check(ids, warnings):
    register(name=ids["abs"], maps=ids["vec"], start="2001-01-01")

    with pytest.raises(tgis.FatalError) as error:
        register(name=ids["rel"], maps=ids["vec"])

    assert str(error.value) == (
        f"Temporal type of space time dataset <{ids['rel']}@{MAPSET}> and map "
        f"<{ids['vec']}@{MAPSET}> are different"
    )
    assert warnings == [
        "Map is already registered in temporal database. Unable to update "
        f"vector map <{ids['vec']}@{MAPSET}>. Overwrite flag is not set."
    ]


def test_relative_units_of_a_map_with_a_layer_and_a_dataset_differ(ids):
    register(name=ids["rel"], maps=f"{ids['vec']}:2", start="0", unit="days")
    register(name=ids["rel2"], maps=ids["vec2"], start="0", unit="years")

    with pytest.raises(tgis.FatalError) as error:
        register(name=ids["rel2"], maps=f"{ids['vec']}:2")

    assert str(error.value) == (
        f"Relative time units of space time dataset <{ids['rel2']}@{MAPSET}> "
        f"and map <{ids['vec']}@{MAPSET}> with layer 2 are different"
    )


def test_relative_units_of_a_map_and_a_dataset_differ(ids):
    register(name=ids["rel"], maps=ids["vec"], start="0", unit="days")
    register(name=ids["rel2"], maps=ids["vec2"], start="0", unit="years")

    with pytest.raises(tgis.FatalError) as error:
        register(name=ids["rel2"], maps=ids["vec"])

    assert str(error.value) == (
        f"Relative time units of space time dataset <{ids['rel2']}@{MAPSET}> "
        f"and map <{ids['vec']}@{MAPSET}> are different"
    )


def test_overwrite_with_another_temporal_type_of_a_map_with_a_layer(ids, monkeypatch):
    register(name=ids["abs"], maps=f"{ids['vec']}:2", start="2001-01-01")
    monkeypatch.setenv("GRASS_OVERWRITE", "1")

    with pytest.raises(tgis.FatalError) as error:
        register(name=ids["rel"], maps=f"{ids['vec']}:2", start="0", unit="days")

    assert str(error.value) == (
        f"Unable to update vector map <{ids['vec']}@{MAPSET}> with layer 2. "
        "The temporal types are different."
    )


def test_overwrite_with_another_temporal_type_of_a_map(ids, monkeypatch):
    register(name=ids["abs"], maps=ids["vec"], start="2001-01-01")
    monkeypatch.setenv("GRASS_OVERWRITE", "1")

    with pytest.raises(tgis.FatalError) as error:
        register(name=ids["rel"], maps=ids["vec"], start="0", unit="days")

    assert str(error.value) == (
        f"Unable to update vector map <{ids['vec']}@{MAPSET}>. "
        "The temporal types are different."
    )


def test_a_relative_dataset_needs_a_unit_for_a_start_time(ids):
    with pytest.raises(tgis.FatalError) as error:
        register(name=ids["rel"], maps=ids["vec"], start="0")

    assert str(error.value) == (
        f"Space time vector dataset <{ids['rel']}> with relative time found, "
        "but no relative unit set for vector maps"
    )


def test_the_dbif_argument_is_deprecated(ids, warnings):
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        register(maps=ids["vec"], start="2001-01-01", dbif=dbif)
    finally:
        dbif.close()

    assert warnings == [
        "The dbif argument is deprecated and will be removed in a future release."
    ]


@pytest.mark.parametrize(
    ("start", "end", "text"),
    [
        ("garbage", None, 'Unable to convert string "garbage" into a datetime object'),
        (
            "2001-01-01",
            "garbage",
            'Unable to convert string "garbage" into a datetime object',
        ),
    ],
)
def test_a_time_string_that_is_no_date_is_refused(start, end, text):
    item = tgis.VectorDataset(f"x@{MAPSET}")

    with pytest.raises(tgis.FatalError) as error:
        tgis.assign_valid_time_to_map("absolute", item, start, end, None)

    assert str(error.value) == text


def test_an_increment_that_gives_no_time_is_refused():
    item = tgis.VectorDataset(f"x@{MAPSET}")

    with pytest.raises(tgis.FatalError) as error:
        tgis.assign_valid_time_to_map(
            "absolute", item, "2001-01-01", None, None, increment="garbage"
        )

    assert str(error.value) == "Error occurred in increment computation"


@pytest.mark.parametrize("layer", [None, "2"])
def test_valid_time_of_a_relative_map_with_and_without_layer(layer):
    name = f"x:{layer}@{MAPSET}" if layer else f"x@{MAPSET}"
    item = tgis.VectorDataset(name)

    tgis.assign_valid_time_to_map(
        "relative", item, "3", "7", "days", increment=None, interval=False
    )

    assert item.get_relative_time() == (3, 7, "days")
    assert item.get_layer() == layer


def test_empty_3d_raster_maps_are_deleted_on_request(tools, ids):
    name = ids["ras"] + "_3d"
    tools.g_region(n=80, s=0, e=120, w=0, t=1, b=0, res=10, res3=1)
    tools.r3_mapcalc(expression=f"{name} = null()")
    item = tgis.Raster3DDataset(f"{name}@{MAPSET}")
    item.set_absolute_time(datetime(2001, 1, 1), datetime(2001, 1, 2))
    tgis.register_maps_in_space_time_dataset(
        type="raster3d", maps=name, start="2001-01-01", increment="1 day", interval=True
    )
    item.select()
    assert tools.g_list(type="raster_3d", pattern=name, format="json")

    tgis.register_map_object_list("raster3d", [item], None, delete_empty=True)

    assert not tools.g_list(type="raster_3d", pattern=name, format="json")
    assert item.map_exists() is False


def test_a_passed_stream_stays_open(ids):
    stream = io.StringIO(f"{ids['vec']}|2001-01-01|2001-01-02\n")

    register(file=stream)

    assert not stream.closed
    assert absolute_time(ids["vec"]) == (datetime(2001, 1, 1), datetime(2001, 1, 2))


def absolute_time(name):
    item = tgis.VectorDataset(f"{name}@{MAPSET}")
    item.select()
    return item.get_absolute_time()
