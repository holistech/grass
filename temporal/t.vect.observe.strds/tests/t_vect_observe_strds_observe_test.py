"""Test what t.vect.observe.strds writes for one and for several raster datasets

The data are described in conftest.py. The tool copies the input map with one
layer per granule of the raster dataset, adds the columns to the tables of the
layers (the table of the input for layer 1) and registers the layers as the
maps vector_output:<layer> with the times of the granules.
"""

from datetime import datetime, timedelta

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    small_region,
    vector_points,
)
from grass.temporal.testing.readback import list_maps, stds_info


def _observe(tools, points, prefix, strds="ob_a", columns="obs", **options):
    tools.t_vect_observe_strds(
        input=points,
        strds=strds,
        output=prefix,
        vector_output=f"{prefix}_v",
        columns=columns,
        **options,
    )
    return f"{prefix}_v"


def _rows(tools, vector, layer, columns):
    """The rows of the table of a layer as tuples of texts"""
    text = tools.v_db_select(map=vector, layer=layer, columns=columns, flags="c").stdout
    return [tuple(line.split("|")) for line in text.splitlines()]


def test_each_granule_becomes_a_layer_with_the_registered_time(
    tools, rasters, points, prefix
):
    vector = _observe(tools, points, prefix)

    rows = list_maps(tools, "stvds", prefix)

    assert [(row.start, row.end) for row in rows] == [
        ("2001-03-01 00:00:00", "2001-04-01 00:00:00"),
        ("2001-04-01 00:00:00", "2001-05-01 00:00:00"),
        ("2001-05-01 00:00:00", "2001-06-01 00:00:00"),
    ]
    layers = tools.t_vect_list(input=prefix, columns="id,layer", flags="u").stdout
    assert layers.splitlines() == [f"{vector}:{k}@PERMANENT|{k}" for k in (1, 2, 3)]


@pytest.mark.parametrize("layer", [1, 2, 3])
def test_the_layer_holds_the_value_of_each_point_from_its_raster(
    tools, rasters, points, prefix, layer
):
    vector = _observe(tools, points, prefix)

    # Map k holds 100 k + 10 row + col: p1 is in (1, 1), p2 in (1, 2), p3 in
    # (2, 1) and p4 in (2, 2).
    assert _rows(tools, vector, layer, "cat,obs") == [
        (str(cat), str(100 * layer + value))
        for cat, value in ((1, 11), (2, 12), (3, 21), (4, 22))
    ]


def test_layer_one_is_the_table_of_the_input(tools, rasters, points, prefix):
    vector = _observe(tools, points, prefix)

    # The column h of the input stays in layer 1 beside the new column; the
    # new layers have the category and the new column only.
    assert _rows(tools, vector, 1, "cat,h,obs")[0] == ("1", "1", "111")
    assert tools.db_columns(table=vector).stdout.split() == [
        "x",
        "y",
        "cat",
        "h",
        "obs",
    ]
    assert tools.db_columns(table=f"{vector}_2").stdout.split() == ["cat", "obs"]


def test_the_output_dataset_takes_type_and_semantics_from_the_raster_dataset(
    tools, rasters, points, prefix
):
    _observe(tools, points, prefix)

    info = stds_info(tools, "stvds", prefix)

    assert info["temporal_type"] == "absolute"
    assert info["semantic_type"] == "mean"
    assert info["number_of_maps"] == 3
    # 4 points in every one of the three layers
    assert info["points"] == 12


def test_the_title_is_spelled_correctly(tools, rasters, points, prefix):
    _observe(tools, points, prefix)

    assert "Observaion" not in tools.t_info(type="stvds", input=prefix).stdout


def test_the_description_names_the_dataset_and_the_vector_map(
    tools, rasters, points, prefix
):
    _observe(tools, points, prefix)

    text = tools.t_info(type="stvds", input=prefix).stdout

    assert (
        f"Observation of space time raster dataset(s) <ob_a> with vector map <{points}>"
        in text
    )


def test_the_column_type_follows_the_raster_type(tools, rasters, points, prefix):
    vector = _observe(tools, points, prefix, strds="ob_b")

    # ob_b has float maps: DOUBLE PRECISION; ob_a has integer maps: INTEGER
    integer = _observe(tools, points, f"{prefix}_i")
    float_type = tools.db_describe(table=f"{vector}_2", flags="c").stdout
    integer_type = tools.db_describe(table=f"{integer}_2", flags="c").stdout
    assert "Column 2: obs:DOUBLE PRECISION" in float_type
    assert "Column 2: obs:INTEGER" in integer_type


def test_float_values_are_stored_as_they_are(tools, rasters, points, prefix):
    vector = _observe(tools, points, prefix, strds="ob_b")

    # rb_1 holds 0.5 + 1 and rb_2 0.5 + 2 in every cell
    assert _rows(tools, vector, 1, "obs") == [("1.5",)] * 4
    assert _rows(tools, vector, 2, "obs") == [("2.5",)] * 4


def test_several_datasets_give_a_column_each_in_the_granules_they_share(
    tools, rasters, points, prefix
):
    vector = _observe(tools, points, prefix, strds="ob_a,ob_a,ob_b", columns="c1,c2,c3")

    # The granules are those of the first dataset where every dataset has a
    # map: April (ra_2 and rb_1) and May (ra_3 and rb_2). March has no map
    # in ob_b and is left out, so two layers remain.
    rows = list_maps(tools, "stvds", prefix)
    assert [(row.start, row.end) for row in rows] == [
        ("2001-04-01 00:00:00", "2001-05-01 00:00:00"),
        ("2001-05-01 00:00:00", "2001-06-01 00:00:00"),
    ]
    assert _rows(tools, vector, 1, "cat,c1,c2,c3") == [
        ("1", "211", "211", "1.5"),
        ("2", "212", "212", "1.5"),
        ("3", "221", "221", "1.5"),
        ("4", "222", "222", "1.5"),
    ]
    assert _rows(tools, vector, 2, "cat,c1,c3")[0] == ("1", "311", "2.5")


def test_the_relative_time_is_kept_with_its_unit(tools, rasters, points, prefix):
    _observe(tools, points, prefix, strds="ob_rel")

    info = stds_info(tools, "stvds", prefix)
    rows = list_maps(tools, "stvds", prefix)

    assert info["temporal_type"] == "relative"
    assert info["unit"] == "months"
    assert [(row.start, row.end) for row in rows] == [(0, 1), (1, 2), (2, 3)]


def test_relative_values_come_from_the_map_of_each_month(
    tools, rasters, points, prefix
):
    vector = _observe(tools, points, prefix, strds="ob_rel")

    assert [_rows(tools, vector, layer, "obs")[3] for layer in (1, 2, 3)] == [
        ("122",),
        ("222",),
        ("322",),
    ]


def test_where_selects_the_points_of_the_input(tools, rasters, points, prefix):
    vector = _observe(tools, points, prefix, where="h > 2")

    # h = 3 and 4 for p3 and p4: only these two are in the output, in every
    # layer. Map k gives them 100 k + 21 and 100 k + 22.
    for layer in (1, 2, 3):
        assert _rows(tools, vector, layer, "cat,obs") == [
            ("3", str(100 * layer + 21)),
            ("4", str(100 * layer + 22)),
        ]
    assert stds_info(tools, "stvds", prefix)["points"] == 6


def test_an_input_with_layers_gets_the_columns_in_its_own_tables(
    tools, rasters, prefix
):
    name = f"{prefix}_two"
    vector_points(
        tools, name, [(0.5, 1.5), (1.5, 0.5)], attributes={"h": [1, 2]}, layers=(1, 2)
    )

    vector = _observe(tools, name, prefix)

    # The layers 1 and 2 exist, so the first two granules add the column to
    # their tables (with the column h of the input); only layer 3 is new.
    assert _rows(tools, vector, 1, "cat,h,obs") == [
        ("1", "1", "111"),
        ("2", "2", "122"),
    ]
    assert _rows(tools, vector, 2, "cat,h,obs") == [
        ("1", "1", "211"),
        ("2", "2", "222"),
    ]
    assert _rows(tools, vector, 3, "cat,obs") == [("1", "311"), ("2", "322")]
    assert len(list_maps(tools, "stvds", prefix)) == 3


def test_overwrite_replaces_the_dataset_and_the_vector(tools, rasters, points, prefix):
    _observe(tools, points, prefix)

    vector = _observe(tools, points, prefix, strds="ob_b", overwrite=True)

    assert [(row.start) for row in list_maps(tools, "stvds", prefix)] == [
        "2001-04-01 00:00:00",
        "2001-05-01 00:00:00",
    ]
    assert _rows(tools, vector, 1, "obs") == [("1.5",)] * 4


# About 90 seconds (measured 19.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_more_than_256_layers_keep_their_values(tools, points, prefix):
    # The case of the old script test.t.vect.observe.strds.layer_bug.sh ("the
    # limit of the number of layers"), which an exit statement had disabled
    # for its run time: maps of one hour each from 2001-01-01, observed by
    # four points. The script used 269 maps and checked nothing. Its commit
    # does not name the limit, and the vector library has none today
    # (GV_FIELD_MAX is PORT_INT_MAX); 257 maps cross the one of a byte, the
    # likely candidate, with the fewest maps.
    previous = small_region(tools, 1, 1)
    try:
        start = datetime(2001, 1, 1)
        create_stds(
            tools,
            "strds",
            f"{prefix}_big",
            [
                MapSpec(
                    f"{prefix}_b{k}",
                    k,
                    start + timedelta(hours=k - 1),
                    start + timedelta(hours=k),
                )
                for k in range(1, 258)
            ],
        )

        vector = _observe(
            tools, points, prefix, strds=f"{prefix}_big", columns="test_val"
        )
    finally:
        tools.g_region(**previous)

    rows = list_maps(tools, "stvds", prefix)
    assert len(rows) == 257
    assert rows[0].start == "2001-01-01 00:00:00"
    # 257 hours are 10 days and 17 hours.
    assert rows[-1].end == "2001-01-11 17:00:00"
    # Layer k holds the value k. Only the third point, (0.5, 0.5), lies in
    # the region of one cell; the others read nothing.
    for layer in (1, 2, 255, 256, 257):
        assert _rows(tools, vector, layer, "cat,test_val")[2] == ("3", str(layer)), (
            layer
        )
