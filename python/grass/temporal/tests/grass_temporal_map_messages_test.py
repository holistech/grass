"""The messages of the register of a dataset and of the time check of a map

Registering and unregistering a map, and the check of the time of a map, give
one message for a map and one for a map with a layer. The tests make each of
them happen with a vector map and the same map with a layer and compare the
whole text.
"""

import importlib
import itertools
from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")

COUNTER = itertools.count(1)
MAPSET = "PERMANENT"


class Recorder:
    """A message interface that keeps the warnings and errors and forwards"""

    def __init__(self, messenger):
        self.messenger = messenger
        self.texts = []

    def warning(self, message):
        self.texts.append(message)
        self.messenger.warning(message)

    def error(self, message):
        self.texts.append(message)
        self.messenger.error(message)

    def __getattr__(self, name):
        return getattr(self.messenger, name)


@pytest.fixture
def messages(monkeypatch):
    """The warnings and errors that datasets and maps give, as a list of texts"""
    module = importlib.import_module("grass.temporal.abstract_dataset")
    recorder = Recorder(module.get_tgis_message_interface())
    monkeypatch.setattr(module, "get_tgis_message_interface", lambda: recorder)
    return recorder.texts


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=80, s=0, e=120, w=0, res=10)
    return tools


@pytest.fixture
def ids(tools):
    """A vector map and unique names of an absolute and a relative dataset"""
    number = next(COUNTER)
    names = {
        "vec": f"mm{number}_vec",
        "abs": f"mm{number}_abs",
        "rel": f"mm{number}_rel",
    }
    tools.v_random(output=names["vec"], npoints=3, seed=1)
    for key, temporaltype in (("abs", "absolute"), ("rel", "relative")):
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
    for key in ("abs", "rel"):
        tgis.open_old_stds(names[key], "stvds").delete()
    tools.t_unregister(type="vector", maps=names["vec"])
    tools.g_remove(flags="f", type="vector", name=names["vec"])


def vector(names, layer):
    name = f"{names['vec']}:{layer}" if layer else names["vec"]
    return tgis.VectorDataset(f"{name}@{MAPSET}")


def stds_of(names, key):
    stds = tgis.open_old_stds(names[key], "stvds")
    stds.select()
    return stds


def described(names, layer):
    """The map as the messages name it"""
    suffix = f" with layer {layer}" if layer else ""
    return f"<{names['vec']}@{MAPSET}>{suffix}"


LAYERS = [None, "2"]


@pytest.mark.parametrize("layer", LAYERS)
def test_unregistering_a_map_that_is_not_registered(ids, layer, messages):
    stds = stds_of(ids, "abs")

    assert stds.unregister_map(vector(ids, layer)) == ""

    assert messages == [
        f"Map {described(ids, layer)} is not registered in space time dataset "
        f"<{ids['abs']}@{MAPSET}>"
    ]


@pytest.mark.parametrize("layer", LAYERS)
def test_registering_a_map_again(ids, layer, messages):
    tgis.register_maps_in_space_time_dataset(
        "vector",
        ids["abs"],
        maps=f"{ids['vec']}:{layer}" if layer else ids["vec"],
        start="2001-01-01",
    )
    stds = stds_of(ids, "abs")
    item = vector(ids, layer)
    item.select()

    assert stds.register_map(item) is False

    assert messages == [f"Map {described(ids, layer)} is already registered."]


@pytest.mark.parametrize("layer", LAYERS)
def test_a_map_with_an_invalid_time_is_refused(ids, layer):
    tgis.register_maps_in_space_time_dataset(
        "vector",
        ids["rel"],
        maps=f"{ids['vec']}:{layer}" if layer else ids["vec"],
        start="0",
        unit="days",
    )
    stds = stds_of(ids, "abs")
    item = vector(ids, layer)
    item.check_for_correct_time = lambda: False

    with pytest.raises(tgis.FatalError) as error:
        stds.register_map(item)

    assert str(error.value) == f"Map {described(ids, layer)} has invalid time"


@pytest.mark.parametrize("layer", LAYERS)
def test_another_temporal_type_is_refused_by_the_dataset(ids, layer):
    tgis.register_maps_in_space_time_dataset(
        "vector",
        ids["rel"],
        maps=f"{ids['vec']}:{layer}" if layer else ids["vec"],
        start="0",
        unit="days",
    )
    stds = stds_of(ids, "abs")
    item = vector(ids, layer)

    with pytest.raises(tgis.FatalError) as error:
        stds.register_map(item)

    assert str(error.value) == (
        f"Temporal type of space time dataset <{ids['abs']}@{MAPSET}> and map "
        f"{described(ids, layer)} are different"
    )


@pytest.mark.parametrize("layer", LAYERS)
def test_another_relative_unit_is_refused_by_the_dataset(ids, layer):
    tgis.register_maps_in_space_time_dataset(
        "vector",
        ids["rel"],
        maps=f"{ids['vec']}:{layer}" if layer else ids["vec"],
        start="0",
        unit="days",
    )
    stds = stds_of(ids, "rel")
    stds.set_relative_time_unit("years")
    item = vector(ids, layer)

    with pytest.raises(tgis.FatalError) as error:
        stds.register_map(item)

    assert str(error.value) == (
        f"Relative time units of space time dataset <{ids['rel']}@{MAPSET}> and "
        f"map {described(ids, layer)} are different"
    )


@pytest.mark.parametrize("layer", LAYERS)
def test_a_map_whose_interval_ends_before_it_starts(layer, messages):
    name = f"x:{layer}@{MAPSET}" if layer else f"x@{MAPSET}"
    item = tgis.VectorDataset(name)
    item.temporal_extent.set_start_time(datetime(2001, 1, 3))
    item.temporal_extent.set_end_time(datetime(2001, 1, 2))

    assert item.check_for_correct_time() is False

    suffix = f" with layer {layer}" if layer else ""
    assert messages == [
        f"Map <x@{MAPSET}>{suffix} has incorrect time interval, start time is "
        "greater than end time"
    ]


@pytest.mark.parametrize(
    ("layer", "text"),
    [
        (None, "map <x@PERMANENT> are"),
        ("", "map <x@PERMANENT> are"),
        ("2", "map <x@PERMANENT> with layer 2 are"),
    ],
)
def test_a_map_with_an_empty_layer_has_the_message_without_a_layer(layer, text):
    item = tgis.VectorDataset("x:2@PERMANENT" if layer else "x@PERMANENT")

    message = tgis.abstract_map_dataset.other_temporal_type_message("s@PERMANENT", item)

    assert (
        message
        == f"Temporal type of space time dataset <s@PERMANENT> and {text} different"
    )
