"""Test t.rast.series on monthly maps, as the old suites and scripts did

The maps hold 100, 200, ... 600 and cover one calendar month each from
2001-01-01. The where clauses compare the start time as text: the database
stores "2001-02-01 00:00:00", which sorts after the text "2001-02-01", so
start_time > '2001-02-01' still selects the map that starts on February 1
(and start_time >= '2001-02-01' selects it as well).
"""

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    intervals,
    register_stds,
    small_region,
)
from grass.temporal.testing.readback import map_info, message
from grass.tools import ToolError


@pytest.fixture(scope="module")
def four(tools, monthly):
    """The first four monthly maps (100 to 400) in a dataset of their own"""
    register_stds(
        tools,
        "strds",
        "ser_four",
        [
            MapSpec(f"ser_m{k + 1}", None, start, end)
            for k, (start, end) in enumerate(intervals(4))
        ],
    )
    return "ser_four"


def _times(tools, name):
    info = map_info(tools, "raster", name)
    return info["start_time"], info["end_time"]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_time_of_the_output_of_the_old_suite(tools, four, prefix):
    # Maps 2 to 4 start on February 1, March 1 and April 1; the text
    # comparison keeps the map of February 1. They end on May 1.
    tools.t_rast_series(
        input=four,
        method="average",
        output=f"{prefix}_o",
        where="start_time > '2001-02-01'",
    )

    assert _times(tools, f"{prefix}_o") == (
        "'2001-02-01 00:00:00'",
        "'2001-05-01 00:00:00'",
    )
    assert map_info(tools, "raster", f"{prefix}_o")["min"] == 300.0


@pytest.mark.parametrize(
    ("method", "value"), [("average", 250.0), ("maximum", 400.0), ("minimum", 100.0)]
)
def test_the_methods_of_the_old_suite(series, four, method, value):
    assert series(four, method=method) == [[value, value]]


def test_several_methods_of_the_old_suite(series, four):
    assert series(four, outputs=3, method="average,maximum,minimum") == [
        [250.0, 250.0],
        [400.0, 400.0],
        [100.0, 100.0],
    ]


def test_minimum_where_of_the_old_suite(series, four):
    # Maps 3 and 4: the minimum is 300.
    assert series(four, method="minimum", where="start_time >= '2001-03-01'") == [
        [300.0, 300.0]
    ]


@pytest.fixture(scope="module")
def relative_four(tools):
    """Four time instants 0, 14, 28 and 42 days, holding 100 to 400"""
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "ser_rel_four",
        [MapSpec(f"ser_q{k}", 100 * (k + 1), 14 * k) for k in range(4)],
        temporaltype="relative",
        unit="days",
    )
    return "ser_rel_four"


@pytest.mark.parametrize(
    ("method", "value"), [("average", 250.0), ("maximum", 400.0), ("minimum", 100.0)]
)
def test_relative_time_methods_of_the_old_suite(series, relative_four, method, value):
    assert series(relative_four, method=method) == [[value, value]]


def test_relative_time_where_of_the_old_suite(series, relative_four):
    # The instants 28 and 42 hold 300 and 400.
    assert series(relative_four, method="minimum", where="start_time >= 28") == [
        [300.0, 300.0]
    ]


def test_the_shell_script_with_two_methods_and_no_time(tools, monthly, prefix):
    # test.t.rast.series.sh: average and range of the maps after March 1.
    # The text comparison keeps the map of March 1: 300 to 600, so the
    # average is 450 and the range 300.
    tools.t_rast_series(
        input=monthly,
        method="average,range",
        output=f"{prefix}_avg,{prefix}_range",
        where="start_time > '2001-03-01'",
        flags="t",
    )

    assert map_info(tools, "raster", f"{prefix}_avg") is None
    stats = {
        name: tools.r_univar(map=f"{prefix}_{name}", flags="g").keyval
        for name in ("avg", "range")
    }
    assert (stats["avg"]["min"], stats["avg"]["max"]) == (450.0, 450.0)
    assert (stats["range"]["min"], stats["range"]["max"]) == (300.0, 300.0)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_shell_script_with_maximum_and_sum(tools, monthly, prefix):
    tools.t_rast_series(
        input=monthly, method="maximum", output=f"{prefix}_max", order="start_time"
    )
    tools.t_rast_series(input=monthly, method="sum", output=f"{prefix}_sum")

    assert tools.r_univar(map=f"{prefix}_max", flags="g").keyval["max"] == 600.0
    # 100 + 200 + 300 + 400 + 500 + 600, in both cells.
    assert tools.r_univar(map=f"{prefix}_sum", flags="g").keyval["sum"] == 4200.0

    # The script ran the sum again without overwrite and expected an error.
    with pytest.raises(ToolError) as error:
        tools.t_rast_series(input=monthly, method="sum", output=f"{prefix}_sum")
    assert f"<{prefix}_sum> exists" in message(error.value)
    tools.t_rast_series(
        input=monthly, method="sum", output=f"{prefix}_sum", overwrite=True
    )


def test_bug_3223_average_of_all_maps(series, monthly):
    # The script of the bug report gave no method: the default is average.
    # (100 + 200 + 300 + 400 + 500 + 600) / 6 = 350.
    assert series(monthly) == [[350.0, 350.0]]


def test_bug_3223_average_of_the_last_three_months(tools, series, monthly, prefix):
    # Maps 4 to 6: (400 + 500 + 600) / 3 = 500, from April 1 to July 1.
    assert series(monthly, where="start_time >= '2001-04-01'") == [[500.0, 500.0]]
    assert _times(tools, f"{prefix}_o") == (
        "'2001-04-01 00:00:00'",
        "'2001-07-01 00:00:00'",
    )
