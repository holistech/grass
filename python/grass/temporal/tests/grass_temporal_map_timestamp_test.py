"""Tests for the file based timestamp of a map dataset

The C interface and the messenger are replaced by recorders, so no GRASS
session is needed and the test sees exactly which call each kind of map makes
and what it says about a failure.
"""

from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.temporal.c_libraries_interface import CLibrariesInterface


class RecordingInterface(CLibrariesInterface):
    """The C interface without a server: every call is recorded and answered"""

    def __init__(self):
        self.calls = []
        self.answers = {}

    def call(self, function, kind=None, name=None, mapset=None, layer=None, **extra):
        self.calls.append((function, kind, name, mapset, layer, extra))
        return self.answers.get(function)


class Messages:
    def __init__(self):
        self.errors = []

    def error(self, text):
        self.errors.append(text)


@pytest.fixture
def ciface(monkeypatch):
    interface = RecordingInterface()
    monkeypatch.setattr(
        "grass.temporal.abstract_map_dataset.get_tgis_c_library_interface",
        lambda: interface,
    )
    return interface


@pytest.fixture
def messages(monkeypatch):
    recorder = Messages()
    monkeypatch.setattr(
        "grass.temporal.abstract_dataset.get_tgis_message_interface", lambda: recorder
    )
    return recorder


# class, map identifier, kind of the C interface, name in the messages
MAPS = [
    (tgis.RasterDataset, "m@PERMANENT", "raster", "raster map"),
    (tgis.Raster3DDataset, "m@PERMANENT", "raster3d", "3D raster map"),
    (tgis.VectorDataset, "m:2@PERMANENT", "vector", "vector map"),
]
IDS = [kind for _, _, kind, _ in MAPS]


def layer_of(kind):
    return "2" if kind == "vector" else None


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS, ids=IDS)
def test_has_asks_for_the_map_and_for_the_layer(cls, ident, kind, label, ciface):
    ciface.answers["has_timestamp"] = True

    assert cls(ident).has_grass_timestamp() is True
    assert ciface.calls == [
        ("has_timestamp", kind, "m", "PERMANENT", layer_of(kind), {})
    ]


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS, ids=IDS)
def test_nothing_is_read_without_a_timestamp(cls, ident, kind, label, ciface):
    ciface.answers["has_timestamp"] = False

    assert cls(ident).read_timestamp_from_grass() is False
    assert [call[0] for call in ciface.calls] == ["has_timestamp"]


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS, ids=IDS)
def test_an_absolute_timestamp_is_read(cls, ident, kind, label, ciface):
    ciface.answers["has_timestamp"] = True
    start, end = datetime(2001, 1, 1), datetime(2002, 1, 1)
    ciface.answers["read_timestamp"] = (1, (start, end))
    dataset = cls(ident)

    assert dataset.read_timestamp_from_grass() is True
    assert dataset.get_absolute_time() == (start, end)
    # The layer is not passed when the timestamp is read.
    assert ciface.calls[1] == ("read_timestamp", kind, "m", "PERMANENT", None, {})


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS, ids=IDS)
def test_a_relative_timestamp_is_read(cls, ident, kind, label, ciface):
    ciface.answers["has_timestamp"] = True
    ciface.answers["read_timestamp"] = (1, (3, 5, "days"))
    dataset = cls(ident)

    assert dataset.read_timestamp_from_grass() is True
    assert dataset.get_relative_time() == (3, 5, "days")


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS, ids=IDS)
def test_an_unreadable_timestamp_is_reported(cls, ident, kind, label, ciface, messages):
    ciface.answers["has_timestamp"] = True
    ciface.answers["read_timestamp"] = (0, None)
    dataset = cls(ident)

    assert dataset.read_timestamp_from_grass() is False
    assert messages.errors == [
        f"Unable to read timestamp file for {label} <{dataset.get_map_id()}>"
    ]


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS, ids=IDS)
def test_the_timestamp_is_written_with_the_layer(cls, ident, kind, label, ciface):
    ciface.answers["write_timestamp"] = 1
    dataset = cls(ident)
    dataset.set_absolute_time(datetime(2001, 1, 1), datetime(2002, 1, 1))

    assert dataset.write_timestamp_to_grass() is True
    assert ciface.calls == [
        (
            "write_timestamp",
            kind,
            "m",
            "PERMANENT",
            layer_of(kind),
            {"timestring": "01 jan 2001 00:00:00 / 01 jan 2002 00:00:00"},
        )
    ]


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS, ids=IDS)
def test_a_relative_timestamp_is_written_as_text(cls, ident, kind, label, ciface):
    ciface.answers["write_timestamp"] = 0
    dataset = cls(ident)
    dataset.set_relative_time(3, 5, "days")

    assert dataset.write_timestamp_to_grass() is True
    assert ciface.calls[0][5] == {"timestring": "3 days / 5 days"}


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS, ids=IDS)
@pytest.mark.parametrize(
    ("check", "text"),
    [
        (-1, "Unable to create timestamp file for {label} <{map_id}>"),
        (-2, "Invalid datetime in timestamp for {label} <{map_id}>"),
    ],
)
def test_a_failed_write_is_reported(
    cls, ident, kind, label, check, text, ciface, messages
):
    ciface.answers["write_timestamp"] = check
    dataset = cls(ident)
    dataset.set_absolute_time(datetime(2001, 1, 1))

    assert dataset.write_timestamp_to_grass() is False
    assert messages.errors == [text.format(label=label, map_id=dataset.get_map_id())]


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS[:2], ids=IDS[:2])
def test_an_internal_error_of_the_write_is_reported(
    cls, ident, kind, label, ciface, messages
):
    ciface.answers["write_timestamp"] = -3
    dataset = cls(ident)
    dataset.set_absolute_time(datetime(2001, 1, 1))

    assert dataset.write_timestamp_to_grass() is False
    assert messages.errors == ["Internal error"]


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS, ids=IDS)
def test_the_timestamp_is_removed_without_the_layer(cls, ident, kind, label, ciface):
    ciface.answers["remove_timestamp"] = 1

    assert cls(ident).remove_timestamp_from_grass() is True
    assert ciface.calls == [("remove_timestamp", kind, "m", "PERMANENT", None, {})]


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS, ids=IDS)
def test_a_failed_removal_is_reported(cls, ident, kind, label, ciface, messages):
    ciface.answers["remove_timestamp"] = -1

    assert cls(ident).remove_timestamp_from_grass() is False
    assert messages.errors == [f"Unable to remove timestamp for {label} <m>"]


@pytest.mark.parametrize(("cls", "ident", "kind", "label"), MAPS, ids=IDS)
def test_the_map_is_looked_up_by_its_kind(cls, ident, kind, label, ciface):
    ciface.answers["map_exists"] = True

    assert cls(ident).map_exists() is True
    assert ciface.calls == [("map_exists", kind, "m", "PERMANENT", None, {})]
