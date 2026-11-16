"""Test the options and flags of t.rast.series

order, where, -n, -t, nprocs, memory, file_limit, several outputs and an
output named with its mapset. The data are the series of conftest.py.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import map_info, message
from grass.tools import ToolError

AVERAGE = [4.0, pytest.approx(3.2)]


def test_several_methods_give_one_output_each(series, stats):
    result = series(stats, outputs=3, method="minimum,maximum,average")

    assert result == [[1.0, 2.0], [10.0, 5.0], AVERAGE]


def test_an_output_may_name_its_mapset(tools, stats, prefix):
    tools.t_rast_series(input=stats, method="sum", output=f"{prefix}_o@PERMANENT")

    assert map_info(tools, "raster", f"{prefix}_o@PERMANENT")["name"] == f"{prefix}_o"


# order sorts the maps before r.series numbers them, which matters for the
# methods that use the position: slope, offset, detcoeff, min_raster,
# max_raster. The maps in time order, with their names and values (first
# cell / second cell), are
#   ser_b 1 / 3, ser_e 2 / 2, ser_a 3 / 4, ser_d 4 / 5, ser_c 10 / 2.
# By name the order is ser_a ser_b ser_c ser_d ser_e: first cell 3, 1, 10, 4,
# 2 and second cell 4, 3, 2, 5, 2. Slope of the first cell: sum(i v) = 0 + 1 +
# 20 + 12 + 8 = 41, numerator 41 - 5 2 4 = 1, slope 1 / 10 = 0.1; second cell:
# sum(i v) = 0 + 3 + 4 + 15 + 8 = 30, mean 3.2, numerator 30 - 32 = -2, slope
# -0.2.
# By maximum (the largest cell of the map: 3, 2, 4, 5, 10) the order is
# ser_e ser_b ser_a ser_d ser_c: first cell 2, 1, 3, 4, 10 and second cell
# 2, 3, 4, 5, 2. Slope of the first cell: sum(i v) = 0 + 1 + 6 + 12 + 40 = 59,
# numerator 59 - 40 = 19, slope 1.9; second cell: sum(i v) = 0 + 3 + 8 + 15
# + 8 = 34, numerator 34 - 32 = 2, slope 0.2.
ORDERS = [
    ("start_time", [2.0, pytest.approx(0.1)]),
    ("end_time", [2.0, pytest.approx(0.1)]),
    ("name", [pytest.approx(0.1), pytest.approx(-0.2)]),
    ("id", [pytest.approx(0.1), pytest.approx(-0.2)]),
    ("max", [pytest.approx(1.9), pytest.approx(0.2)]),
]


@pytest.mark.parametrize(("order", "slope"), ORDERS)
def test_order_numbers_the_maps(series, stats, order, slope):
    assert series(stats, method="slope", order=order) == [slope]


def test_the_default_order_is_the_start_time(series, stats):
    assert series(stats, method="slope") == [[2.0, pytest.approx(0.1)]]


def test_several_orders(series, stats):
    # The second key only breaks ties of the first, and start times differ.
    assert series(stats, method="slope", order="start_time,name") == [
        [2.0, pytest.approx(0.1)]
    ]


@pytest.mark.parametrize(
    "order",
    [
        "creator",
        "mapset",
        "creation_time",
        "north",
        "south",
        "west",
        "east",
        "min",
    ],
)
def test_the_other_orders_are_accepted(series, stats, order):
    # These keys tie or depend on the clock, so the order is not tested; the
    # average does not depend on it.
    assert series(stats, method="average", order=order) == [AVERAGE]


def test_the_modification_time_is_no_order(tools, stats, prefix):
    # The view of the maps has no such column, so the parser does not offer it.
    with pytest.raises(ToolError) as error:
        tools.t_rast_series(
            input=stats,
            method="average",
            order="modification_time",
            output=f"{prefix}_o",
        )

    assert "Value <modification_time> out of range for parameter <order>" in message(
        error.value
    )


def test_where_selects_the_maps(series, stats):
    # Maps 2, 3, 4 (ser_a, ser_d, ser_c) start on 2001-01-03, -04 and -05:
    # the first cell averages (3 + 4 + 10) / 3, the second (4 + 5 + 2) / 3.
    result = series(stats, method="average", where="start_time >= '2001-01-03'")

    assert result == [[pytest.approx(17 / 3), pytest.approx(11 / 3)]]


def test_where_and_order_work_together(series, stats):
    # The same three maps, numbered by name: ser_a 3, ser_c 10, ser_d 4 and
    # 4, 2, 5. Slope of the first cell: sum(i v) = 0 + 10 + 8 = 18, mean 17 / 3,
    # numerator 18 - 3 1 17 / 3 = 1, denominator 5 - 3 = 2: 0.5. Second cell:
    # sum(i v) = 0 + 2 + 10 = 12, mean 11 / 3, numerator 12 - 11 = 1: 0.5.
    result = series(
        stats, method="slope", order="name", where="start_time >= '2001-01-03'"
    )

    assert result == [[pytest.approx(0.5), pytest.approx(0.5)]]


@pytest.fixture(scope="module")
def with_a_null(tools):
    """Three maps; the first cell of the middle one is null"""
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "ser_nulls",
        [
            MapSpec("ser_n1", "if(col() == 1, 4, 1)", day(0), day(1)),
            MapSpec("ser_n2", "if(col() == 1, null(), 2)", day(1), day(2)),
            MapSpec("ser_n3", "if(col() == 1, 8, 3)", day(2), day(3)),
        ],
    )
    return "ser_nulls"


def test_a_null_is_left_out_by_default(series, with_a_null):
    # (4 + 8) / 2 = 6 for the first cell, (1 + 2 + 3) / 3 = 2 for the second.
    assert series(with_a_null, method="average") == [[6.0, 2.0]]
    assert series(with_a_null, method="count", overwrite=True) == [[2.0, 3.0]]


def test_the_n_flag_propagates_a_null(series, with_a_null):
    assert series(with_a_null, method="average", flags="n") == [[None, 2.0]]


def test_the_n_flag_changes_nothing_without_a_null(series, stats):
    assert series(stats, method="average", flags="n") == [AVERAGE]


@pytest.mark.parametrize("nprocs", [2, 4])
def test_nprocs_gives_the_same_result(series, stats, nprocs):
    assert series(stats, method="kurtosis", nprocs=nprocs) == series(
        stats, method="kurtosis", nprocs=1, overwrite=True
    )


def test_memory_gives_the_same_result(series, stats):
    assert series(stats, method="median", memory=10) == [[3.0, 3.0]]


def test_file_limit_below_the_number_of_maps_warns_and_keeps_the_result(
    tools, stats, prefix
):
    result = tools.t_rast_series(
        input=stats, method="sum", output=f"{prefix}_o", file_limit=4
    )

    assert "Processing over 4 maps: activating -z flag of r.series" in message(result)
    assert tools.r_univar(map=f"{prefix}_o", flags="g").keyval["sum"] == 36.0


def test_file_limit_at_the_number_of_maps_is_silent(tools, stats, prefix):
    result = tools.t_rast_series(
        input=stats, method="sum", output=f"{prefix}_o", file_limit=5
    )

    assert "activating -z flag" not in message(result)


def test_an_existing_output_is_refused_without_overwrite(tools, stats, prefix):
    tools.t_rast_series(input=stats, method="sum", output=f"{prefix}_o")

    with pytest.raises(ToolError) as error:
        tools.t_rast_series(input=stats, method="sum", output=f"{prefix}_o")

    assert f"<{prefix}_o> exists" in message(error.value)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_overwrite_replaces_the_output_and_its_time(tools, stats, prefix):
    tools.t_rast_series(input=stats, method="sum", output=f"{prefix}_o")
    assert map_info(tools, "raster", f"{prefix}_o")["end_time"] == (
        "'2001-01-06 00:00:00'"
    )

    tools.t_rast_series(
        input=stats,
        method="maximum",
        output=f"{prefix}_o",
        where="start_time < '2001-01-03'",
        overwrite=True,
    )

    info = map_info(tools, "raster", f"{prefix}_o")
    assert info["end_time"] == "'2001-01-03 00:00:00'"
    assert info["max"] == 3.0
