# SPDX-License-Identifier: GPL-2.0-or-later

"""Characterize the row classes that map a dataset to the tables of its type

Every map and every space time dataset has a base, a spatial extent, an
absolute and a relative time row, and a map has a register row, each in a
table of its own. The rows are checked here for all six types through the one
table CASES, so that the classes can be generated from column lists without
changing what is stored: the order of the columns in the statements, the
accessors that code outside the library reaches, the text of print_info()
and print_shell_info(), and insert, select, update, update_all, is_in_db and
delete against the temporal database.

The golden file rows_print.json holds the column order and the printed
text of each row as the classes wrote them before they were generated.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

import grass.temporal as tgis
from grass.temporal.kinds import KINDS

pytestmark = pytest.mark.real_io

GOLDEN = json.loads(
    Path(__file__).with_name("data").joinpath("rows_print.json").read_text()
)

START = datetime(2001, 1, 1)
END = datetime(2002, 1, 1)
LATER = datetime(2003, 1, 1)

MAPS = ("raster", "raster3d", "vector")
DATASETS = ("strds", "str3ds", "stvds")

# part -> constructor of the row of a kind. This is the only place that
# names the classes.
_ROWS = {
    "base": tgis.BaseRow,
    "absolute_time": tgis.AbsoluteTimeRow,
    "relative_time": tgis.RelativeTimeRow,
    "spatial_extent": tgis.SpatialExtentRow,
    "register": tgis.RegisterRow,
}
_PARTS = {
    "base": MAPS + DATASETS,
    "absolute_time": MAPS + DATASETS,
    "relative_time": MAPS + DATASETS,
    "spatial_extent": MAPS + DATASETS,
    "register": MAPS,
}

# Arguments that fill every column of a part, by the name of the part and
# whether the type is a space time dataset.
_ARGUMENTS = {
    ("base", False): {"creator": "u", "ctime": START},
    ("base", True): {"semantic_type": "mean", "creator": "u", "ctime": START},
    ("absolute_time", False): {"start_time": START, "end_time": END},
    ("absolute_time", True): {
        "start_time": START,
        "end_time": END,
        "granularity": "1 day",
    },
    ("relative_time", False): {"start_time": 1, "end_time": 2, "unit": "days"},
    ("relative_time", True): {
        "start_time": 1,
        "end_time": 2,
        "unit": "days",
        "granularity": 1,
        "map_time": "interval",
    },
    ("spatial_extent", False): {
        "north": 4,
        "south": 1,
        "east": 3,
        "west": 2,
        "top": 6,
        "bottom": 5,
    },
    ("register", False): {"registered_stds": "x@PERMANENT,y@PERMANENT"},
}
_ARGUMENTS[("spatial_extent", True)] = _ARGUMENTS[("spatial_extent", False)]

# part -> (property to change, new value, property that is set to None)
_CHANGES = {
    "base": ("name", "other", "creator"),
    "absolute_time": ("start_time", LATER, "end_time"),
    "relative_time": ("start_time", 7, "end_time"),
    "spatial_extent": ("north", 9.0, "top"),
    "register": ("registered_stds", "z@PERMANENT", "registered_stds"),
}


def build(kind, part, ident, **override):
    """Build the row of a part for a type, filled with the arguments above"""
    arguments = dict(_ARGUMENTS[part, KINDS[kind].is_stds])
    arguments.update(override)
    row = _ROWS[part](KINDS[kind], ident=ident, **arguments)
    if part == "base" and KINDS[kind].is_stds:
        # The constructors of the datasets take the time of the call.
        row.set_mtime(START)
    return row


CASES = [(kind, part) for part, kinds in _PARTS.items() for kind in kinds]


def case_id(case):
    return f"{case[0]}_{case[1]}"


def golden_key(kind, part):
    return f"{kind}_{part}"


def table_of(kind, part):
    return KINDS[kind].table(part)


@pytest.fixture(scope="module", autouse=True)
def session(temporal_module_session):
    tgis.init(raise_fatal_error=True)
    return temporal_module_session


@pytest.mark.parametrize(("kind", "part"), CASES, ids=case_id)
def test_the_table_of_the_row(kind, part):
    row = build(kind, part, "a@PERMANENT")

    assert row.get_table_name() == table_of(kind, part)


@pytest.mark.parametrize(("kind", "part"), CASES, ids=case_id)
def test_the_order_of_the_columns(kind, part):
    # The order of D is the order of the columns in INSERT and UPDATE.
    row = build(kind, part, "a@PERMANENT")

    assert list(row.D) == GOLDEN[golden_key(kind, part)]["columns"]


def test_the_order_of_the_columns_of_a_vector_layer():
    layered = build("vector", "base", "a:1@PERMANENT")
    plain = build("vector", "base", None)

    assert list(layered.D) == GOLDEN["vector_base_layer"]["columns"]
    assert list(plain.D) == GOLDEN["vector_base_no_id"]["columns"]
    assert layered.get_layer() == "1"
    assert layered.get_name() == "a"


@pytest.mark.parametrize(
    ("kind", "part"),
    [case for case in CASES if case[1] != "register"],
    ids=case_id,
)
def test_the_printed_text(kind, part, capsys):
    row = build(kind, part, "a@PERMANENT")

    row.print_info()
    info = capsys.readouterr().out
    row.print_shell_info()
    shell = capsys.readouterr().out

    assert info == GOLDEN[golden_key(kind, part)]["info"]
    assert shell == GOLDEN[golden_key(kind, part)]["shell"]


@pytest.mark.parametrize(("kind", "part"), CASES, ids=case_id)
def test_the_statements_bind_the_columns_in_order(kind, part):
    row = build(kind, part, "a@PERMANENT")
    columns = list(row.D)

    sql, args = row.get_insert_statement()

    assert sql.startswith(f"INSERT INTO {table_of(kind, part)} (")
    assert [name.strip() for name in sql.split("(")[1].split(")")[0].split(",")] == (
        columns
    )
    assert args == tuple(row.D[name] for name in columns)
    sql, args = row.get_select_statement()
    assert sql.startswith(f"SELECT  {'  , '.join(columns)}  FROM")
    assert args == ("a@PERMANENT",)


# The accessors the other modules and the tools call, by family. Each entry
# is the name of the accessor with a value that survives a round trip.
_BASE_ACCESSORS = {
    "id": "b@PERMANENT",
    "name": "b",
    "mapset": "PERMANENT",
    "layer": "2",
    "creator": "v",
    "ctime": datetime(2010, 1, 1),
    "ttype": "relative",
}
_STDS_ACCESSORS = {"semantic_type": "sum", "mtime": datetime(2011, 1, 1)}
_TIME_ACCESSORS = {"id": "b@PERMANENT", "start_time": START, "end_time": END}
_SPATIAL_ACCESSORS = {
    "id": "b@PERMANENT",
    "north": 5.0,
    "south": 6.0,
    "east": 7.0,
    "west": 8.0,
    "top": 9.0,
    "bottom": 10.0,
}
_REGISTER_ACCESSORS = {"id": "b@PERMANENT", "registered_stds": "q@PERMANENT"}
# Accessors that exist without a property of the same name.
_NO_PROPERTY = {"layer", "mtime", "projection"}


def accessors_of(kind, part):
    if part == "base":
        accessors = dict(_BASE_ACCESSORS)
        if KINDS[kind].is_stds:
            accessors.update(_STDS_ACCESSORS)
        return accessors
    if part == "spatial_extent":
        return dict(_SPATIAL_ACCESSORS)
    if part == "register":
        return dict(_REGISTER_ACCESSORS)
    accessors = dict(_TIME_ACCESSORS)
    if part == "relative_time":
        accessors["unit"] = "years"
    if KINDS[kind].is_stds:
        accessors.update({"granularity": "2 days", "map_time": "point"})
    return accessors


@pytest.mark.parametrize(("kind", "part"), CASES, ids=case_id)
def test_the_accessors_round_trip(kind, part):
    row = build(kind, part, "a@PERMANENT")

    for name, value in accessors_of(kind, part).items():
        getattr(row, f"set_{name}")(value)
        assert getattr(row, f"get_{name}")() == value, name
        if name not in _NO_PROPERTY:
            assert getattr(row, name) == value, name
            setattr(row, name, value)
            assert getattr(row, f"get_{name}")() == value, name


def test_the_projection_of_a_spatial_extent():
    extent = build("raster", "spatial_extent", "a@PERMANENT")

    assert extent.get_projection() == "XY"
    extent.set_projection("LL")
    assert extent.get_projection() == "LL"
    extent.set_projection("nonsense")
    assert extent.get_projection() == "XY"


def test_the_map_identifier_drops_the_layer():
    row = build("vector", "base", "a:1@PERMANENT")

    assert row.get_map_id() == "a@PERMANENT"
    assert row.map_id == "a@PERMANENT"


@pytest.mark.parametrize(("kind", "part"), CASES, ids=case_id)
def test_insert_select_update_delete(kind, part):
    ident = f"rows_{kind}_{part}@PERMANENT"
    changed, value, emptied = _CHANGES[part]
    row = build(kind, part, ident)
    assert row.is_in_db() is False

    row.insert()
    assert row.is_in_db() is True
    stored = build(kind, part, ident)
    assert stored.select() is True
    assert dict(stored.D) == dict(row.D)

    setattr(row, changed, value)
    row.update()
    stored = build(kind, part, ident)
    stored.select()
    assert getattr(stored, changed) == value

    # update() writes only the columns that are not None, update_all() the
    # None, too. The columns of a base and a spatial extent are NOT NULL, so
    # that the database refuses the second statement and the check stays with
    # the statements.
    setattr(row, emptied, None)
    column = emptied
    assert f"{column} =" not in row.get_update_statement()[0]
    assert f"{column} =" in row.get_update_all_statement()[0]
    if part in {"absolute_time", "relative_time", "register"}:
        row.update()
        stored = build(kind, part, ident)
        stored.select()
        assert getattr(stored, emptied) is not None
        row.update_all()
        stored = build(kind, part, ident)
        stored.select()
        assert getattr(stored, emptied) is None

    row.delete()
    assert row.is_in_db() is False
    assert build(kind, part, ident).select() is False


@pytest.mark.parametrize(("kind", "part"), CASES, ids=case_id)
def test_the_connection_of_the_caller_stays_open(kind, part):
    ident = f"rows_open_{kind}_{part}@PERMANENT"
    row = build(kind, part, ident)
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        row.insert(dbif=dbif)
        assert row.is_in_db(dbif=dbif) is True
        row.delete(dbif=dbif)
        assert dbif.is_connected()
    finally:
        dbif.close()


def test_the_area_and_the_volume_of_a_spatial_extent():
    extent = build("raster", "spatial_extent", "a@PERMANENT")

    assert extent.get_spatial_extent_as_tuple() == (4.0, 1.0, 3.0, 2.0, 6.0, 5.0)
    assert extent.get_spatial_extent_as_tuple_2d() == (4.0, 1.0, 3.0, 2.0)
    assert extent.get_area() == 3.0
    assert extent.get_volume() == 3.0
    extent.set_bottom(2)
    assert extent.get_volume() == 12.0


def test_a_flat_extent_has_the_volume_of_its_area():
    extent = build("raster", "spatial_extent", "a@PERMANENT", top=5, bottom=5)

    assert extent.get_volume() == extent.get_area()


def test_the_spatial_extent_is_copied_from_another():
    source = build("raster", "spatial_extent", "a@PERMANENT")
    target = build("vector", "spatial_extent", "b@PERMANENT", north=0, top=0)

    target.set_spatial_extent(source)
    assert target.get_spatial_extent_as_tuple() == source.get_spatial_extent_as_tuple()

    flat = build("vector", "spatial_extent", "c@PERMANENT", top=100, bottom=100)
    flat.set_spatial_extent_2d(source)
    assert (
        flat.get_spatial_extent_as_tuple_2d() == source.get_spatial_extent_as_tuple_2d()
    )
    assert (flat.get_top(), flat.get_bottom()) == (100.0, 100.0)
    flat.set_spatial_extent_from_values_2d(8, 7, 6, 5)
    assert flat.get_spatial_extent_as_tuple_2d() == (8.0, 7.0, 6.0, 5.0)


def test_an_empty_edge_stays_empty():
    extent = build("raster", "spatial_extent", "a@PERMANENT", north=None)

    assert extent.get_north() is None
    assert extent.get_south() == 1.0


class Sample(tgis.Row):
    columns = (
        tgis.Column("size", alias="extent", convert=int, doc="the size"),
        tgis.Column("label"),
    )

    def set_label(self, value) -> None:
        self.D["label"] = value.upper()


def test_a_column_gets_getter_setter_and_property_under_its_alias():
    row = Sample("sample", "a@PERMANENT")

    row.set_extent("7")
    assert row.get_extent() == 7
    assert row.D["size"] == 7
    row.extent = 8
    assert row.extent == 8
    assert row.get_label() is None
    assert "the size" in Sample.get_extent.__doc__
    assert not hasattr(row, "size")


def test_a_setter_written_by_hand_is_kept_and_reached_by_the_property():
    row = Sample("sample", "a@PERMANENT")

    row.label = "abc"

    assert row.D["label"] == "ABC"


def test_the_property_of_a_base_class_calls_the_setter_of_the_subclass():
    class Other(Sample):
        def set_id(self, ident) -> None:
            super().set_id(ident + "!")

    row = Other("sample", "a@PERMANENT")
    row.id = "b@PERMANENT"

    assert row.D["id"] == "b@PERMANENT!"
    assert row.ident == "b@PERMANENT!"
