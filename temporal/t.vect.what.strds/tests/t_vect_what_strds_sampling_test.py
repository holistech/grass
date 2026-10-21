"""Test which raster maps t.vect.what.strds reads and what it writes

The data are described in conftest.py. For each vector map the tool collects
the raster maps that stand in the chosen temporal relations to its interval
(sampling), optionally aggregates them to one map (method), adds a column per
raster map (or one column, named by column, for the first map) to the table of
the layer and stores the value at every point with v.what.rast.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds

# Most tests take more than a second (measured 19.10.2026 with a serial
# pytest --durations=0): every test makes its own vector maps.
pytestmark = pytest.mark.slow

# The cells of the points in the raster maps: 10 row + col (conftest.py)
CELLS = [11, 12, 21, 22]


def _values(k):
    """The values of the points p1 to p4 in the raster map k (conftest.py)"""
    return [str(100 * k + cell) for cell in CELLS]


def _columns(tools, vector, layer=1):
    """The names of the columns of a table without x, y, cat and h"""
    table = vector if layer == 1 else f"{vector}_{layer}"
    names = tools.db_columns(table=table).stdout.split()
    return [name for name in names if name not in {"x", "y", "cat", "h"}]


def _column(tools, vector, column, layer=1):
    text = tools.v_db_select(map=vector, layer=layer, columns=column, flags="c").stdout
    return text.splitlines()


def _what(tools, vectors, **options):
    options.setdefault("strds", "wh_a")
    return tools.t_vect_what_strds(input=vectors.dataset, **options)


def test_the_default_sampling_takes_the_maps_that_start_in_the_interval(
    tools, rasters, vectors
):
    data = vectors()

    _what(tools, data)

    # Interval 1 (January to April): wr_1 starts on 03-01. Interval 2 (May
    # and June): wr_3 starts on 05-01 and wr_4 on 06-01. Interval 3 (August
    # to November): wr_6 starts on 08-01.
    v1, v2, v3 = data.maps
    assert _columns(tools, v1) == ["wr_1"]
    assert _columns(tools, v2) == ["wr_3", "wr_4"]
    assert _columns(tools, v3) == ["wr_6"]
    assert _column(tools, v1, "wr_1") == _values(1)
    assert _column(tools, v2, "wr_3") == _values(3)
    assert _column(tools, v2, "wr_4") == _values(4)
    assert _column(tools, v3, "wr_6") == _values(6)


def test_a_column_name_stores_the_first_map_of_the_interval(tools, rasters, vectors):
    data = vectors()

    _what(tools, data, sampling="start,during", column="map_vals")

    # wr_3 comes before wr_4; the other intervals have one map.
    v1, v2, v3 = data.maps
    assert _column(tools, v1, "map_vals") == _values(1)
    assert _column(tools, v2, "map_vals") == _values(3)
    assert _column(tools, v3, "map_vals") == _values(6)
    assert _columns(tools, v2) == ["map_vals"]


def test_the_values_are_those_of_the_point_in_its_cell(tools, rasters, vectors):
    data = vectors()

    _what(tools, data, sampling="start", column="map_vals")

    # wr_1 reads 100 + 10 row + col: p1 111, p2 112, p3 121, p4 122.
    assert _column(tools, data.maps[0], "map_vals") == ["111", "112", "121", "122"]


@pytest.mark.parametrize(
    ("sampling", "interval", "names"),
    [
        # The raster maps wr_k last from 2001-(k+2)-01 to 2001-(k+3)-01.
        ("start", ("2001-03-15", "2001-04-15"), ["wr_2"]),
        ("during", ("2001-02-01", "2001-05-15"), ["wr_1", "wr_2"]),
        ("overlap", ("2001-03-15", "2001-04-15"), ["wr_1", "wr_2"]),
        ("contain", ("2001-03-10", "2001-03-20"), ["wr_1"]),
        ("equal", ("2001-04-01", "2001-05-01"), ["wr_2"]),
        ("follows", ("2001-02-01", "2001-03-01"), ["wr_1"]),
        ("precedes", ("2001-04-01", "2001-06-01"), ["wr_1"]),
    ],
)
def test_each_sampling_method_selects_its_relation(
    tools, rasters, vectors, sampling, interval, names
):
    start, end = (datetime.fromisoformat(day) for day in interval)
    data = vectors([(start, end)])

    _what(tools, data, sampling=sampling)

    assert _columns(tools, data.maps[0]) == names


def test_sampling_methods_can_be_combined(tools, rasters, vectors):
    data = vectors([(datetime(2001, 3, 15), datetime(2001, 4, 15))])

    _what(tools, data, sampling="overlap,contain,follows")

    # overlap: wr_1 and wr_2; follows: the map that starts at 04-15: none
    assert _columns(tools, data.maps[0]) == ["wr_1", "wr_2"]


def test_an_interval_without_a_raster_map_is_left_alone(tools, rasters, vectors):
    data = vectors([(datetime(2005, 1, 1), datetime(2005, 2, 1))])

    _what(tools, data)

    assert _columns(tools, data.maps[0]) == []


# Two maps lie during the second interval: wr_3 (a = 300 + cell) and wr_4
# (b = 400 + cell); n = 2, the mean is 350 + cell, the deviations are -50 and
# 50 (lib/stats and r.series). The expressions are those of the cells.
METHODS = {
    "average": lambda cell: 350 + cell,
    "count": lambda cell: 2,
    "median": lambda cell: 350 + cell,
    "minimum": lambda cell: 300 + cell,
    "maximum": lambda cell: 400 + cell,
    "range": lambda cell: 100,
    "sum": lambda cell: 700 + 2 * cell,
    # The population variance (sum of squares / n) is 2500, the deviation 50.
    "variance": lambda cell: 2500,
    "stddev": lambda cell: 50,
    # The index of the smaller and the larger map in the list (0 and 1)
    "min_raster": lambda cell: 0,
    "max_raster": lambda cell: 1,
    # The first value of the sorted list with the highest count (all have 1)
    "mode": lambda cell: 300 + cell,
    # The number of distinct values
    "diversity": lambda cell: 2,
    # The regression of the values over their index 0 and 1: slope 100, offset
    # 300 + cell, determination 1.
    "slope": lambda cell: 100,
    "offset": lambda cell: 300 + cell,
    "detcoeff": lambda cell: 1,
    # Quantiles by the rule of Hyndman and Fan, type 7: k = q (n - 1), the
    # value is a (1 - k) + b k with a = 300 + cell and b = 400 + cell.
    "quart1": lambda cell: 325 + cell,
    "quart3": lambda cell: 375 + cell,
    "perc90": lambda cell: 390 + cell,
    # The tool has no quantile option, so r.series uses the quantile 0
    # (raster/r.series/main.c) and c_quant gives the smaller value, as in
    # t.rast.aggregate.
    "quantile": lambda cell: 300 + cell,
    # Two symmetric values: no skew; the fourth moment equals the squared
    # variance, so the excess kurtosis is 1 - 3.
    "skewness": lambda cell: 0,
    "kurtosis": lambda cell: -2,
}


@pytest.mark.parametrize("method", list(METHODS))
def test_a_method_aggregates_the_maps_of_the_interval(tools, rasters, vectors, method):
    data = vectors()

    _what(tools, data, sampling="during", column="m", method=method)

    expected = [str(METHODS[method](cell)) for cell in CELLS]
    assert [
        float(value) for value in _column(tools, data.maps[1], "m")
    ] == pytest.approx([float(value) for value in expected], abs=1e-5)


def test_a_single_map_is_not_aggregated(tools, rasters, vectors):
    data = vectors()

    _what(tools, data, sampling="during", column="m", method="sum")

    # The first and third interval hold one map: the raster values themselves
    assert _column(tools, data.maps[0], "m") == _values(1)
    assert _column(tools, data.maps[2], "m") == _values(6)


def test_the_disabled_method_is_the_default(tools, rasters, vectors):
    data = vectors()

    _what(tools, data, sampling="during")

    assert _columns(tools, data.maps[1]) == ["wr_3", "wr_4"]


def test_the_aggregate_is_stored_in_a_column_named_after_a_temporary_map(
    tools, rasters, vectors
):
    data = vectors()

    _what(tools, data, sampling="during", method="average")

    # Without column= the name is that of the aggregate, which is deleted.
    (name,) = _columns(tools, data.maps[1])
    assert name.startswith("aggreagated_map_name_")
    assert tools.g_list(type="raster", pattern="aggreagated_map_name_*").stdout == ""


def test_the_column_type_follows_the_raster_type(tools, rasters, vectors):
    data = vectors()

    _what(tools, data, sampling="during", column="m", method="sum")

    # Interval 1 and 3 read one integer map; interval 2 reads the sum, a
    # float map.
    types = [tools.db_describe(table=name, flags="c").stdout for name in data.maps]
    assert "m:INTEGER" in types[0]
    assert "m:DOUBLE PRECISION" in types[1]
    assert "m:INTEGER" in types[2]


def test_where_selects_the_points_that_get_a_value(tools, rasters, vectors):
    data = vectors()

    _what(tools, data, column="m", where="h > 2")

    # Only p3 and p4 (h = 3 and 4) are read; the others stay NULL.
    assert _column(tools, data.maps[0], "m") == ["", "", "121", "122"]


def test_where_works_with_a_table_whose_key_is_not_cat(tools, rasters, vectors):
    data = vectors()
    first = data.maps[0]
    tools.db_execute(sql=f"CREATE TABLE {first}_k AS SELECT cat AS id, h FROM {first}")
    tools.v_db_connect(map=first, table=f"{first}_k", key="id", layer=1, flags="o")

    _what(tools, data, column="m", where="h > 2")

    assert _column(tools, first, "m") == ["", "", "121", "122"]


def test_t_where_selects_the_vector_maps(tools, rasters, vectors):
    data = vectors()

    _what(tools, data, t_where="start_time >= '2001-05-01 00:00:00'", column="m")

    v1, v2, v3 = data.maps
    assert _columns(tools, v1) == []
    assert _columns(tools, v2) == ["m"]
    assert _columns(tools, v3) == ["m"]


def test_a_dot_in_the_raster_name_becomes_an_underscore_in_the_column(
    tools, rasters, vectors, prefix
):
    create_stds(
        tools,
        "strds",
        f"{prefix}_dots",
        [MapSpec(f"{prefix}d.1", "7", datetime(2001, 3, 1), datetime(2001, 4, 1))],
    )
    data = vectors()

    _what(tools, data, strds=f"{prefix}_dots")

    assert _columns(tools, data.maps[0]) == [f"{prefix}d_1"]
    assert _column(tools, data.maps[0], f"{prefix}d_1") == ["7"] * 4


def test_an_aggregate_without_a_value_adds_no_column(tools, rasters, vectors, prefix):
    # Both maps of January and February hold no value, so their average has
    # none either; the aggregation removes such a map and the tool goes on
    # with the next vector map without a column.
    create_stds(
        tools,
        "strds",
        f"{prefix}_null",
        [
            MapSpec(
                f"{prefix}_n{k}",
                "null()",
                datetime(2001, k, 1),
                datetime(2001, k + 1, 1),
            )
            for k in (1, 2)
        ],
    )
    data = vectors([(datetime(2001, 1, 1), datetime(2001, 3, 1))])

    _what(tools, data, strds=f"{prefix}_null", sampling="during", method="average")

    assert _columns(tools, data.maps[0]) == []
    assert tools.g_list(type="raster", pattern="aggreagated_map_name_*").stdout == ""
