"""Test the statistics of t.rast3d.univar on maps of twelve voxels

The voxels of the maps are listed in conftest.py. The statistics are those of
the population (variance with the divisor n). The quartiles and percentiles
follow r.univar (raster/r.univar/stats.c, shared with r3.univar): the n values
are sorted and the value at index trunc(n * p / 100 - 0.5) is taken; the
median of an even number of values is the mean of the two middle ones.
"""

import math

import pytest

HEADER = [
    "id", "start", "end", "non_null_cells", "null_cells", "min", "max", "range",
    "mean", "mean_of_abs", "stddev", "variance", "coeff_var", "sum", "sum_abs",
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
    result = tools.t_rast3d_univar(input=values)

    assert result.stdout.splitlines()[0].split("|") == HEADER
    rows = _rows(result)
    assert [(row["id"], row["start"], row["end"]) for row in rows] == [
        ("uv3_1@PERMANENT", "2001-01-01 00:00:00", "2001-01-02 00:00:00"),
        ("uv3_2@PERMANENT", "2001-01-02 00:00:00", "2001-01-03 00:00:00"),
        ("uv3_3@PERMANENT", "2001-01-03 00:00:00", "2001-01-04 00:00:00"),
    ]


def test_the_cells_and_the_sums(tools, values):
    rows = _rows(tools.t_rast3d_univar(input=values))

    # 1..12; 1, 3, 4, 6, 7, 9, 10, 12 with four null voxels; 0.5 to 6
    assert [
        _numbers(row, "non_null_cells", "null_cells", "sum", "sum_abs") for row in rows
    ] == [
        [12, 0, 78, 78],
        [8, 4, 52, 52],
        [12, 0, 39, 39],
    ]


def test_min_max_range_and_mean(tools, values):
    rows = _rows(tools.t_rast3d_univar(input=values))

    assert [
        _numbers(row, "min", "max", "range", "mean", "mean_of_abs") for row in rows
    ] == [
        [1, 12, 11, 6.5, 6.5],
        [1, 12, 11, 6.5, 6.5],
        [0.5, 6, 5.5, 3.25, 3.25],
    ]


def test_variance_standard_deviation_and_coefficient(tools, values):
    rows = _rows(tools.t_rast3d_univar(input=values))

    # 1..12: the variance of n consecutive numbers is (n^2 - 1) / 12 = 143 / 12;
    # 1, 3, 4, 6, 7, 9, 10, 12: the squares of the deviations from 6.5 sum to
    # 2 * (30.25 + 12.25 + 6.25 + 0.25) = 98, so 98 / 8; the third map holds
    # half of the first, so a quarter of its variance
    variances = [143 / 12, 12.25, 143 / 48]
    for row, variance in zip(rows, variances, strict=True):
        stddev = math.sqrt(variance)
        assert _numbers(row, "variance", "stddev", "coeff_var") == pytest.approx(
            [variance, stddev, 100 * stddev / float(row["mean"])], rel=1e-12
        )


def _extended(tools, values, **options):
    return _table(tools.t_rast3d_univar(input=values, flags="e", **options))


def test_extended_statistics_add_quartiles_and_a_percentile(tools, values):
    header, rows = _extended(tools, values)

    assert header[len(HEADER) :] == [
        "first_quartile",
        "median",
        "third_quartile",
        "percentile_90",
    ]
    # 12 values: indexes 2 and 8 for the quartiles and 10 for the 90th
    # percentile, the median is the mean of the indexes 5 and 6 (6, 7). 8
    # values: indexes 1, 5 and 6 and the median (6 + 7) / 2. The third map has
    # half of the values of the first.
    assert [
        _numbers(row, "first_quartile", "median", "third_quartile", "percentile_90")
        for row in rows
    ] == [[3, 6.5, 9, 11], [3, 6.5, 9, 10], [1.5, 3.25, 4.5, 5.5]]


def test_percentiles_are_named_and_found_by_the_index_rule(tools, values):
    header, rows = _extended(tools, values, percentile="10,97.5")

    assert header[-2:] == ["percentile_10", "percentile_97_5"]
    # 12 values: indexes 0 and 11; 8 values: indexes 0 and 7
    assert [_numbers(row, "percentile_10", "percentile_97_5") for row in rows] == [
        [1, 12],
        [1, 12],
        [0.5, 6],
    ]


def test_percentile_zero_and_one_hundred_are_the_minimum_and_the_maximum(tools, values):
    _, rows = _extended(tools, values, percentile="0,100")

    assert [_numbers(row, "percentile_0", "percentile_100") for row in rows] == [
        [1, 12],
        [1, 12],
        [0.5, 6],
    ]


def test_zones_give_statistics_per_zone(tools, values):
    result = tools.t_rast3d_univar(
        input=values, zones="uv3_zones", where="start_time < '2001-01-02'"
    )

    header, rows = _table(result)
    assert header[3:5] == ["zone", "label"]
    # Zone c holds the voxels of column c: (c, c + 3, c + 6, c + 9); the
    # variance is that of two pairs 3 apart and two 6 apart: (2 * 4.5^2 +
    # 2 * 1.5^2) / 4 = 11.25 in every zone
    assert [
        _numbers(row, "zone", "non_null_cells", "min", "max", "mean", "variance", "sum")
        for row in rows
    ] == [
        [1, 4, 1, 10, 5.5, 11.25, 22],
        [2, 4, 2, 11, 6.5, 11.25, 26],
        [3, 4, 3, 12, 7.5, 11.25, 30],
    ]


def test_zones_with_extended_statistics(tools, values):
    result = tools.t_rast3d_univar(
        input=values, zones="uv3_zones", flags="e", where="start_time < '2001-01-02'"
    )

    rows = _rows(result)
    # Four values per zone: indexes 0 (first quartile), 2 (third quartile)
    # and 3 (90th percentile); the median is the mean of the indexes 1 and 2
    assert [
        _numbers(row, "first_quartile", "median", "third_quartile", "percentile_90")
        for row in rows
    ] == [[1, 5.5, 7, 10], [2, 6.5, 8, 11], [3, 7.5, 9, 12]]


@pytest.mark.parametrize("nprocs", [1, 2, 4])
def test_zones_with_nprocs_give_the_same_rows_in_the_same_order(tools, values, nprocs):
    # r3.univar has no parallel mode; the option is accepted and changes
    # nothing in the output
    rows = _rows(tools.t_rast3d_univar(input=values, zones="uv3_zones", nprocs=nprocs))

    assert [(row["id"], row["zone"]) for row in rows] == [
        (f"uv3_{number}@PERMANENT", str(zone))
        for number in (1, 2, 3)
        for zone in (1, 2, 3)
    ]
    assert [row["sum"] for row in rows[:3]] == ["22", "26", "30"]


def test_where_selects_the_maps(tools, values):
    rows = _rows(
        tools.t_rast3d_univar(input=values, where="start_time >= '2001-01-03'")
    )

    assert [row["id"] for row in rows] == ["uv3_3@PERMANENT"]


def test_a_selection_without_maps_prints_nothing(tools, values):
    result = tools.t_rast3d_univar(input=values, where="start_time > '2010-01-01'")

    assert result.stdout == ""


@pytest.mark.parametrize("nprocs", [1, 2, 4])
def test_nprocs_gives_the_same_rows_in_the_same_order(tools, values, nprocs):
    rows = _rows(tools.t_rast3d_univar(input=values, nprocs=nprocs))

    assert [row["id"] for row in rows] == [
        "uv3_1@PERMANENT",
        "uv3_2@PERMANENT",
        "uv3_3@PERMANENT",
    ]
    assert [row["sum"] for row in rows] == ["78", "52", "39"]
