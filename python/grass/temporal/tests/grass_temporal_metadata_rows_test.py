# SPDX-License-Identifier: GPL-2.0-or-later

"""Characterize the metadata rows of the six dataset types

The metadata of a map or a space time dataset differs by type in its
columns, in the order in which they are printed, and in the labels of
print_info(). The tests pin, for every type, the order of the columns, the
accessors the other modules call, the conversion of the values, the printed
text in both styles with every column empty and filled, and the round trip
through the temporal database.

The golden file metadata_print.json holds the printed text as the classes
wrote it before the columns were described in tables. It is not adapted to a
result: where a line there is wrong, the code is repaired and the line with it
in a commit of its own.
"""

import json
from pathlib import Path

import pytest

import grass.temporal as tgis
from grass.temporal.kinds import KINDS

pytestmark = pytest.mark.real_io

GOLDEN = json.loads(
    Path(__file__).with_name("data").joinpath("metadata_print.json").read_text()
)

KIND_NAMES = ("raster", "raster3d", "vector", "strds", "str3ds", "stvds")

# kind -> constructor. This is the only place that names the classes.
_CLASSES = {
    "raster": tgis.RasterMetadata,
    "raster3d": tgis.Raster3DMetadata,
    "vector": tgis.VectorMetadata,
    "strds": tgis.STRDSMetadata,
    "str3ds": tgis.STR3DSMetadata,
    "stvds": tgis.STVDSMetadata,
}

# The values the database computes for a space time dataset; they have a
# setter nowhere, a read of the row fills them.
_COMPUTED = {
    "strds": {
        "number_of_maps": 12,
        "min_min": 0.1234567890123456,
        "min_max": 1e-07,
        "max_min": 123456789.123456789,
        "max_max": 3,
        "nsres_min": 0.30000000000000004,
        "nsres_max": 10.0,
        "ewres_min": 0.5,
        "ewres_max": 25.25,
        "number_of_semantic_labels": 2,
    },
    "str3ds": {
        "number_of_maps": 3,
        "min_min": -1.5,
        "min_max": 2.0,
        "max_min": 3.25,
        "max_max": 4.125,
        "nsres_min": 1.1,
        "nsres_max": 2.2,
        "ewres_min": 3.3,
        "ewres_max": 4.4,
        "tbres_min": 5.5,
        "tbres_max": 6.6,
    },
    "stvds": {
        "number_of_maps": 5,
        "points": 11,
        "lines": 12,
        "boundaries": 13,
        "centroids": 14,
        "faces": 15,
        "kernels": 16,
        "primitives": 17,
        "nodes": 18,
        "areas": 19,
        "islands": 20,
        "holes": 21,
        "volumes": 22,
    },
}

# kind -> the arguments of the constructor and the setters that fill the
# columns that have a setter, with values of a type that converts.
_FILLED = {
    "raster": {
        "datatype": "FCELL",
        "cols": "7",
        "rows": 8.0,
        "number_of_cells": "56",
        "nsres": "0.1",
        "ewres": 2,
        "min": 1,
        "max": "2.5",
    },
    "raster3d": {
        "datatype": "DCELL",
        "cols": 7,
        "rows": 8,
        "depths": "9",
        "number_of_cells": 504,
        "nsres": 0.1,
        "ewres": 0.2,
        "tbres": "0.3",
        "min": -1,
        "max": 12345678.123456789,
    },
    "vector": {
        "is_3d": True,
        "number_of_points": 1,
        "number_of_lines": 2,
        "number_of_boundaries": 3,
        "number_of_centroids": 4,
        "number_of_faces": 5,
        "number_of_kernels": 6,
        "number_of_primitives": 7,
        "number_of_nodes": 8,
        "number_of_areas": 9,
        "number_of_islands": 10,
        "number_of_holes": 11,
        "number_of_volumes": 12,
    },
    "strds": {
        "raster_register": "strds_map_register_abc",
        "title": "A title",
        "description": "A description",
    },
    "str3ds": {
        "raster3d_register": "str3ds_map_register_abc",
        "title": "A title",
        "description": "A description",
    },
    "stvds": {
        "vector_register": "stvds_map_register_abc",
        "title": "A title",
        "description": "A description",
    },
}

COMMAND = "t.create output=a\nt.register input=a"


def make(kind, filled=False):
    """Build the metadata row of a kind, empty or with every column filled"""
    row = _CLASSES[kind](ident="a@PERMANENT")
    if not filled:
        return row
    values = _FILLED[kind]
    if kind in {"raster", "raster3d"}:
        for name, value in values.items():
            getattr(row, f"set_{name}")(value)
        if kind == "raster":
            row.set_semantic_label("S2_1")
    elif kind == "vector":
        row.set_3d_info(values["is_3d"])
        for name, value in values.items():
            if name != "is_3d":
                getattr(row, f"set_{name}")(value)
    else:
        row.set_title(values["title"])
        row.set_description(values["description"])
        row.set_command(COMMAND)
        register = next(name for name in values if name.endswith("_register"))
        getattr(row, f"set_{register}")(values[register])
        if kind != "stvds":
            row.set_aggregation_type("mean")
        row.D.update(_COMPUTED[kind])
    return row


@pytest.fixture(scope="module", autouse=True)
def session(temporal_module_session):
    tgis.init(raise_fatal_error=True)
    return temporal_module_session


@pytest.fixture(autouse=True)
def no_semantic_labels_query(monkeypatch):
    """Let semantic_labels answer without a register table to read"""
    monkeypatch.setattr(
        tgis.STRDSMetadata, "get_semantic_labels", lambda self, dbif=None: "S2_1,S2_2"
    )


def printed(row, capsys):
    row.print_info()
    info = capsys.readouterr().out
    row.print_shell_info()
    return info, capsys.readouterr().out


@pytest.mark.parametrize("filled", [False, True], ids=["empty", "filled"])
@pytest.mark.parametrize("kind", KIND_NAMES)
def test_the_printed_text(kind, filled, capsys):
    info, shell = printed(make(kind, filled), capsys)

    expected = GOLDEN[f"{kind}_{'filled' if filled else 'empty'}"]
    assert info == expected["info"]
    assert shell == expected["shell"]


@pytest.mark.parametrize("filled", [False, True], ids=["empty", "filled"])
@pytest.mark.parametrize("kind", KIND_NAMES)
def test_the_order_of_the_columns(kind, filled):
    # The order of D is the order of the columns in the INSERT statement.
    row = make(kind, filled)

    assert list(row.D) == GOLDEN[f"{kind}_{'filled' if filled else 'empty'}"]["columns"]
    assert row.get_table_name() == KINDS[kind].table("metadata")


@pytest.mark.parametrize("kind", ["raster", "raster3d"])
def test_the_values_of_a_map_are_converted(kind):
    row = make(kind, filled=True)

    assert row.get_cols() == 7
    assert row.get_rows() == 8
    assert row.get_number_of_cells() in {56, 504}
    assert isinstance(row.get_nsres(), float)
    assert isinstance(row.get_min(), float)
    assert isinstance(row.get_max(), float)
    row.set_cols(None)
    row.set_min(None)
    assert (row.get_cols(), row.get_min()) == (None, None)
    assert (row.cols, row.min) == (None, None)


def test_the_3d_raster_converts_its_own_columns():
    row = make("raster3d", filled=True)

    assert row.get_depths() == 9
    assert row.get_tbres() == 0.3
    assert (row.depths, row.tbres) == (9, 0.3)
    row.set_depths(None)
    row.set_tbres(None)
    assert (row.depths, row.tbres) == (None, None)


def test_the_semantic_label_of_a_raster():
    row = make("raster")
    assert row.get_semantic_label() is None

    row.semantic_label = "S2_2"

    assert row.get_semantic_label() == "S2_2"
    assert row.D["semantic_label"] == "S2_2"


def test_only_a_raster_has_a_semantic_label():
    for kind in KIND_NAMES:
        assert hasattr(make(kind), "get_semantic_label") is (kind == "raster")


def test_the_vector_columns_are_stored_under_their_column_names():
    row = make("vector", filled=True)

    assert row.D["points"] == 1
    assert row.D["is_3d"] is True
    assert row.get_3d_info() is True
    assert row.is_3d is True
    assert row.number_of_volumes == 12
    row.number_of_areas = 99
    assert row.D["areas"] == 99


@pytest.mark.parametrize("kind", ["strds", "str3ds", "stvds"])
def test_the_accessors_of_a_space_time_dataset(kind):
    row = make(kind, filled=True)

    assert (row.title, row.description) == ("A title", "A description")
    assert row.get_command() == COMMAND
    assert row.number_of_maps == _COMPUTED[kind]["number_of_maps"]
    assert not hasattr(row, "set_number_of_maps")
    row.title = "Other"
    assert row.get_title() == "Other"
    assert row.print_history is not None


def test_the_computed_columns_of_a_raster_dataset_have_no_setter():
    for kind, names in (
        ("strds", ["min_min", "max_max", "nsres_min", "ewres_max"]),
        ("str3ds", ["tbres_min", "tbres_max", "min_max"]),
    ):
        row = make(kind, filled=True)
        for name in names:
            assert getattr(row, f"get_{name}")() == _COMPUTED[kind][name]
            assert getattr(row, name) == _COMPUTED[kind][name]
            assert not hasattr(row, f"set_{name}")


def test_the_aggregation_type_of_the_raster_datasets():
    for kind in ("strds", "str3ds"):
        row = make(kind)
        assert row.get_aggregation_type() is None
        row.aggregation_type = "max"
        assert row.get_aggregation_type() == "max"
    assert not hasattr(make("stvds"), "set_aggregation_type")


def test_the_register_of_a_space_time_dataset():
    assert make("strds", True).raster_register == "strds_map_register_abc"
    assert make("str3ds", True).raster3d_register == "str3ds_map_register_abc"
    assert make("stvds", True).vector_register == "stvds_map_register_abc"


def test_the_number_of_vector_features_of_a_space_time_dataset():
    row = make("stvds", filled=True)

    assert row.number_of_points == 11
    assert row.get_number_of_volumes() == 22
    assert not hasattr(row, "set_number_of_points")


def test_the_command_history_is_printed_line_by_line(capsys):
    make("strds", filled=True).print_info()

    lines = capsys.readouterr().out.splitlines()
    assert lines[-3:] == [
        " | Command history:",
        " | t.create output=a",
        " | t.register input=a",
    ]


def test_the_history_in_shell_style(capsys):
    make("strds", filled=True).print_history()

    assert capsys.readouterr().out == GOLDEN["strds_history"]


@pytest.mark.parametrize("kind", KIND_NAMES)
def test_insert_select_update_delete(kind):
    ident = f"meta_{kind}@PERMANENT"
    row = _CLASSES[kind](ident=ident)
    if kind in {"raster", "raster3d"}:
        row.set_datatype("CELL")
        row.set_cols(3)
        row.set_rows(4)
        row.set_number_of_cells(12)
        row.set_nsres(1)
        row.set_ewres(1)
        row.set_min(1)
        row.set_max(2)
        if kind == "raster3d":
            row.set_depths(2)
            row.set_tbres(1)
        changed = ("set_cols", "cols", 9)
    elif kind == "vector":
        changed = ("set_number_of_points", "number_of_points", 9)
    else:
        row.set_title("t")
        row.set_description("d")
        changed = ("set_title", "title", "other")
        register = {"strds": "raster", "str3ds": "raster3d", "stvds": "vector"}[kind]
        getattr(row, f"set_{register}_register")(f"{kind}_map_register_{'0' * 32}")
    assert row.is_in_db() is False

    row.insert()
    stored = _CLASSES[kind](ident=ident)
    assert stored.select() is True
    assert stored.get_id() == ident
    for name, value in row.D.items():
        if value is not None and name != "number_of_maps":
            assert stored.D[name] == value, name

    getattr(row, changed[0])(changed[2])
    row.update()
    stored = _CLASSES[kind](ident=ident)
    stored.select()
    assert getattr(stored, changed[1]) == changed[2]

    row.delete()
    assert row.is_in_db() is False


def test_a_3d_raster_dataset_prints_its_own_top_bottom_resolution(capsys):
    # The human readable text used to show the east-west resolution on these
    # two lines.
    make("str3ds", filled=True).print_info()

    lines = capsys.readouterr().out.splitlines()
    assert " | Top-bottom resolution min:.. 5.5" in lines
    assert " | Top-bottom resolution max:.. 6.6" in lines


def test_a_raster_keeps_the_semantic_label_it_is_given():
    row = tgis.RasterMetadata(ident="a@PERMANENT", semantic_label="S2_1")

    assert row.get_semantic_label() == "S2_1"


def test_a_raster_without_a_semantic_label_has_no_such_column():
    # The column is left out of INSERT and UPDATE until a label is set.
    assert "semantic_label" not in tgis.RasterMetadata(ident="a@PERMANENT").D
