"""Test that t.vect.import gives back what t.vect.export wrote

The data come from conftest.py: the maps vi_1 and vi_2 with the points (k, 1)
and (k, 2) of map k, each with the columns value (10 k + i) and name ("k_i").
The maps, their times, the geometry and the attributes of the imported maps
must be those of the exported ones.
"""

import pytest

from grass.temporal.testing.readback import list_maps, stds_info

# Every test imports at least once (measured 18.10.2026 with a serial
# pytest --durations=0: 0.5 s to more than 2 s).
pytestmark = pytest.mark.slow

FORMATS = [
    ("GML", "bzip2"),
    ("GML", "gzip"),
    ("GML", "no"),
    ("pack", "no"),
    ("pack", "gzip"),
    ("pack", "bzip2"),
]
TIMES = [
    ("2001-01-01 00:00:00", "2001-02-01 00:00:00"),
    ("2001-02-01 00:00:00", "2001-03-01 00:00:00"),
]


def _points(tools, name):
    """The (x, y, category) of the points of a map, in the order of the map"""
    lines = tools.v_out_ascii(input=name, format="point", separator="comma").stdout
    return [tuple(float(word) for word in line.split(",")) for line in lines.split()]


def _table(tools, name, columns):
    """The rows of the given columns of the table of layer 1"""
    text = tools.v_db_select(map=name, columns=columns, flags="c").stdout
    return [tuple(line.split("|")) for line in text.splitlines()]


def _import(tools, archive, prefix, tmp_path, **options):
    tools.t_vect_import(
        input=str(archive),
        output=prefix,
        basename=prefix,
        directory=str(tmp_path),
        flags="o",
        **options,
    )
    return list_maps(tools, "stvds", prefix)


def _exported(tools, tmp_path, fmt, compression):
    archive = tmp_path / "out"
    tools.t_vect_export(
        input="vi_pair",
        output=str(archive),
        format=fmt,
        compression=compression,
    )
    return archive


@pytest.fixture(autouse=True)
def _pair(archives):
    """The datasets of conftest.py"""


@pytest.mark.parametrize(("fmt", "compression"), FORMATS)
def test_the_maps_come_back_with_their_times_and_points(
    tools, tmp_path, prefix, fmt, compression
):
    archive = _exported(tools, tmp_path, fmt, compression)

    rows = _import(tools, archive, prefix, tmp_path)

    assert [(row.start, row.end) for row in rows] == TIMES
    # Map k has the points (k, 1) and (k, 2) with the categories 1 and 2
    assert [_points(tools, row.name) for row in rows] == [
        [(1.0, 1.0, 1.0), (1.0, 2.0, 2.0)],
        [(2.0, 1.0, 1.0), (2.0, 2.0, 2.0)],
    ]


@pytest.mark.parametrize(("fmt", "compression"), FORMATS)
def test_the_attributes_come_back(tools, tmp_path, prefix, fmt, compression):
    archive = _exported(tools, tmp_path, fmt, compression)

    rows = _import(tools, archive, prefix, tmp_path)

    # value = 10 k + i and name = "k_i" for point i of map k
    assert [_table(tools, row.name, "value,name") for row in rows] == [
        [("11", "1_1"), ("12", "1_2")],
        [("21", "2_1"), ("22", "2_2")],
    ]


def test_a_pack_archive_keeps_the_columns_of_the_table(tools, tmp_path, prefix):
    archive = _exported(tools, tmp_path, "pack", "no")

    rows = _import(tools, archive, prefix, tmp_path)

    # The columns of vector_points(): x, y, cat and the two attributes
    columns = tools.db_columns(table=rows[0].name).stdout.split()
    assert columns == ["x", "y", "cat", "value", "name"]


def test_a_gml_archive_adds_the_columns_of_the_gml_file(tools, tmp_path, prefix):
    archive = _exported(tools, tmp_path, "GML", "no")

    rows = _import(tools, archive, prefix, tmp_path)

    # Not a defect of the tool: the GML driver of GDAL reads the feature id
    # as the field gml_id, and v.in.ogr makes a new key column cat ("If not
    # specified, categories numbers are generated ... stored in the column
    # named cat", its manual) and renames a field of that name to cat_. The
    # manual of t.vect.import promises no unchanged table. The other columns
    # stay.
    columns = tools.db_columns(table=rows[0].name).stdout.split()
    assert columns == ["cat", "gml_id", "x", "y", "cat_", "value", "name"]
    assert _table(tools, rows[0].name, "gml_id,cat_") == [
        ("vi_1.0", "1"),
        ("vi_1.1", "2"),
    ]


@pytest.mark.parametrize("fmt", ["GML", "pack"])
def test_the_dataset_has_the_extent_and_the_time_of_the_maps(
    tools, tmp_path, prefix, fmt
):
    archive = _exported(tools, tmp_path, fmt, "no")
    _import(tools, archive, prefix, tmp_path)

    info = stds_info(tools, "stvds", prefix)

    # The points lie at x = 1 and 2 and y = 1 and 2
    assert (info["west"], info["east"]) == (1.0, 2.0)
    assert (info["south"], info["north"]) == (1.0, 2.0)
    assert info["number_of_maps"] == 2
    assert info["points"] == 4
    # t.info -g puts the times in single quotes
    assert (info["start_time"], info["end_time"]) == (
        "'2001-01-01 00:00:00'",
        "'2001-03-01 00:00:00'",
    )


@pytest.mark.parametrize("fmt", ["GML", "pack"])
def test_the_relative_time_comes_back(tools, archives, tmp_path, prefix, fmt):
    rows = _import(tools, archives[f"relative {fmt}"], prefix, tmp_path)

    info = stds_info(tools, "stvds", prefix)
    assert info["temporal_type"] == "relative"
    assert info["unit"] == "years"
    assert info["granularity"] == 1
    assert [(row.start, row.end) for row in rows] == [(1, 2), (2, 3)]
    assert [_table(tools, row.name, "value") for row in rows] == [
        [("41",), ("42",)],
        [("51",), ("52",)],
    ]


def test_without_a_basename_the_maps_keep_their_names(
    other, archives, prefix, tmp_path
):
    other.t_vect_import(
        input=str(archives["GML"]),
        output=prefix,
        directory=str(tmp_path),
        flags="o",
    )

    rows = list_maps(other, "stvds", prefix)
    assert [(row.name, row.start) for row in rows] == [
        ("vi_1", TIMES[0][0]),
        ("vi_2", TIMES[1][0]),
    ]


def test_without_a_basename_the_maps_of_a_pack_archive_keep_their_names(
    other, archives, prefix, tmp_path
):
    other.t_vect_import(
        input=str(archives["pack"]),
        output=prefix,
        directory=str(tmp_path),
        flags="o",
    )

    rows = list_maps(other, "stvds", prefix)
    assert [(row.name, row.start) for row in rows] == [
        ("vi_1", TIMES[0][0]),
        ("vi_2", TIMES[1][0]),
    ]
    assert _table(other, "vi_2", "value") == [("21",), ("22",)]


def test_a_layer_of_a_pack_archive_is_imported_with_the_map(
    tools, archives, tmp_path, prefix
):
    # vi_3 has the layers 1 and 2; pack holds the whole map
    rows = _import(tools, archives["layer pack"], prefix, tmp_path)

    layers = tools.v_category(input=rows[0].name, option="layers").stdout.split()
    assert layers == ["1", "2"]
    assert _table(tools, rows[0].name, "value") == [("31",), ("32",)]


def _layer_of_the_registered_map(tools, prefix):
    text = tools.t_vect_list(input=prefix, columns="name,layer").stdout
    return text.splitlines()[1:]


def test_today_a_pack_archive_registers_the_map_without_its_layer(
    tools, archives, tmp_path, prefix
):
    # list.txt of the archive says vi_3:2, but the dataset registers the map
    # under its name alone (stds_import.py writes mapname, not the layer).
    _import(tools, archives["layer pack"], prefix, tmp_path)

    assert _layer_of_the_registered_map(tools, prefix) == [f"{prefix}_2|None"]


@pytest.mark.xfail(
    strict=True,
    reason="t.vect.import registers a pack archive map without the layer that list.txt names, stds_import.py writes the map name alone",
)
def test_a_pack_archive_registers_the_layer_of_the_exported_map(
    tools, archives, tmp_path, prefix
):
    _import(tools, archives["layer pack"], prefix, tmp_path)

    assert _layer_of_the_registered_map(tools, prefix) == [f"{prefix}_2|2"]


def test_today_a_gml_archive_holds_the_registered_layer_as_layer_1(
    tools, archives, tmp_path, prefix
):
    rows = _import(tools, archives["layer GML"], prefix, tmp_path)

    # The export took the table of layer 2 (value 131 and 132); the new map
    # has the rows as layer 1.
    assert _table(tools, rows[0].name, "value") == [("131",), ("132",)]
    assert _layer_of_the_registered_map(tools, prefix) == [f"{prefix}_2|None"]
