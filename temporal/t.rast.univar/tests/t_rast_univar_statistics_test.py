"""Test the statistics of t.rast.univar on maps of six cells

The cells of the maps are listed in conftest.py. The statistics are those of
the population (variance with the divisor n). The quartiles and percentiles
follow r.univar (raster/r.univar/stats.c): the n values are sorted and the
value at index trunc(n * p / 100 - 0.5) is taken; the median of an even number
of values is the mean of the two middle ones.
"""

import math

import pytest

HEADER = [
    "id", "semantic_label", "start", "end", "non_null_cells", "null_cells", "min", "max",
    "range", "mean", "mean_of_abs", "stddev", "variance", "coeff_var", "sum", "sum_abs",
]  # fmt: skip


def _table(result):
    """The header and the rows (as dicts) of the plain output"""
    lines = result.stdout.splitlines()
    header = lines[0].split("|")
    return header, [
        dict(zip(header, line.split("|"), strict=True)) for line in lines[1:]
    ]


def _rows(result):
    return _table(result)[1]


def _numbers(row, *keys):
    return [float(row[key]) for key in keys]


def test_the_header_and_the_times_of_the_maps(tools, values):
    result = tools.t_rast_univar(input=values)

    assert result.stdout.splitlines()[0].split("|") == HEADER
    rows = _rows(result)
    assert [(row["id"], row["start"], row["end"]) for row in rows] == [
        ("uv_1@PERMANENT", "2001-01-01 00:00:00", "2001-01-02 00:00:00"),
        ("uv_2@PERMANENT", "2001-01-02 00:00:00", "2001-01-03 00:00:00"),
        ("uv_3@PERMANENT", "2001-01-03 00:00:00", "2001-01-04 00:00:00"),
    ]


def test_the_cells_and_the_sums(tools, values):
    rows = _rows(tools.t_rast_univar(input=values))

    # 1..6; 1, 3, 4, 6 with two null cells; 0.5 to 3
    assert [
        _numbers(row, "non_null_cells", "null_cells", "sum", "sum_abs") for row in rows
    ] == [
        [6, 0, 21, 21],
        [4, 2, 14, 14],
        [6, 0, 10.5, 10.5],
    ]


def test_min_max_range_and_mean(tools, values):
    rows = _rows(tools.t_rast_univar(input=values))

    assert [
        _numbers(row, "min", "max", "range", "mean", "mean_of_abs") for row in rows
    ] == [
        [1, 6, 5, 3.5, 3.5],
        [1, 6, 5, 3.5, 3.5],
        [0.5, 3, 2.5, 1.75, 1.75],
    ]


def test_variance_standard_deviation_and_coefficient(tools, values):
    rows = _rows(tools.t_rast_univar(input=values))

    # 1..6: squares of the deviations from 3.5 sum to 17.5, so 17.5 / 6;
    # 1, 3, 4, 6: 6.25 + 0.25 + 0.25 + 6.25 = 13, so 13 / 4; the third map
    # holds half of the first, so a quarter of its variance
    variances = [35 / 12, 3.25, 35 / 48]
    for row, variance in zip(rows, variances, strict=True):
        stddev = math.sqrt(variance)
        assert _numbers(row, "variance", "stddev", "coeff_var") == pytest.approx(
            [variance, stddev, 100 * stddev / float(row["mean"])], rel=1e-12
        )


def _extended(tools, values, **options):
    return _table(tools.t_rast_univar(input=values, flags="e", **options))


def test_extended_statistics_add_quartiles_and_a_percentile(tools, values):
    header, rows = _extended(tools, values)

    assert header[len(HEADER) :] == [
        "first_quartile",
        "median",
        "third_quartile",
        "percentile_90",
    ]
    # 6 values: indexes 1 and 4 for the quartiles and 4 for the 90th percentile,
    # the median is the mean of the indexes 2 and 3. 4 values: indexes 0, 2 and 3
    # and the median (3 + 4) / 2.
    assert [
        _numbers(row, "first_quartile", "median", "third_quartile", "percentile_90")
        for row in rows
    ] == [[2, 3.5, 5, 5], [1, 3.5, 4, 6], [1, 1.75, 2.5, 2.5]]


def test_percentiles_are_named_and_found_by_the_index_rule(tools, values):
    header, rows = _extended(tools, values, percentile="10,97.5")

    assert header[-2:] == ["percentile_10", "percentile_97_5"]
    # 6 values: indexes 0 and 5; 4 values: indexes 0 and 3
    assert [_numbers(row, "percentile_10", "percentile_97_5") for row in rows] == [
        [1, 6],
        [1, 6],
        [0.5, 3],
    ]


def test_percentile_zero_and_one_hundred_are_the_minimum_and_the_maximum(tools, values):
    _, rows = _extended(tools, values, percentile="0,100")

    assert [_numbers(row, "percentile_0", "percentile_100") for row in rows] == [
        [1, 6],
        [1, 6],
        [0.5, 3],
    ]


def test_zones_give_statistics_per_zone(tools, values):
    result = tools.t_rast_univar(
        input=values, zones="uv_zones", where="start_time < '2001-01-02'"
    )

    header, rows = _table(result)
    assert header[4:6] == ["zone", "label"]
    # Zone c holds the cells of column c: (c, c + 3)
    assert [
        _numbers(row, "zone", "non_null_cells", "min", "max", "mean", "variance", "sum")
        for row in rows
    ] == [
        [1, 2, 1, 4, 2.5, 2.25, 5],
        [2, 2, 2, 5, 3.5, 2.25, 7],
        [3, 2, 3, 6, 4.5, 2.25, 9],
    ]


def test_zones_with_extended_statistics(tools, values):
    result = tools.t_rast_univar(
        input=values, zones="uv_zones", flags="e", where="start_time < '2001-01-02'"
    )

    rows = _rows(result)
    # Two values per zone: indexes 0 (first quartile), 1 (third quartile and
    # 90th percentile); the median is their mean
    assert [
        _numbers(row, "first_quartile", "median", "third_quartile", "percentile_90")
        for row in rows
    ] == [[1, 2.5, 4, 4], [2, 3.5, 5, 5], [3, 4.5, 6, 6]]


def test_where_selects_the_maps(tools, values):
    rows = _rows(tools.t_rast_univar(input=values, where="start_time >= '2001-01-03'"))

    assert [row["id"] for row in rows] == ["uv_3@PERMANENT"]


def test_a_selection_without_maps_prints_nothing(tools, values):
    result = tools.t_rast_univar(input=values, where="start_time > '2010-01-01'")

    assert result.stdout == ""


def test_the_semantic_label_in_the_name_selects_the_maps(tools, labeled):
    rows = _rows(tools.t_rast_univar(input=f"{labeled}.S2_B1"))

    assert [(row["id"], row["semantic_label"], row["mean"]) for row in rows] == [
        ("uv_b1@PERMANENT", "S2_B1", "10"),
        ("uv_b2@PERMANENT", "S2_B1", "30"),
    ]


def test_without_a_label_all_the_maps_are_used(tools, labeled):
    rows = _rows(tools.t_rast_univar(input=labeled))

    assert sorted((row["id"], row["semantic_label"]) for row in rows) == [
        ("uv_b1@PERMANENT", "S2_B1"),
        ("uv_b2@PERMANENT", "S2_B1"),
        ("uv_c1@PERMANENT", "S2_C1"),
        ("uv_c2@PERMANENT", "S2_C1"),
    ]


@pytest.mark.parametrize("nprocs", [1, 2, 4])
def test_nprocs_gives_the_same_rows_in_the_same_order(tools, values, nprocs):
    rows = _rows(tools.t_rast_univar(input=values, nprocs=nprocs))

    assert [row["id"] for row in rows] == [
        "uv_1@PERMANENT",
        "uv_2@PERMANENT",
        "uv_3@PERMANENT",
    ]
    assert [row["sum"] for row in rows] == ["21", "14", "10.5"]
