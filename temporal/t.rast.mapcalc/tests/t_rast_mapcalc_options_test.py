"""Test the documented example and the checks of the options of t.rast.mapcalc

The characterization tests of this directory cover the expression, the
sampling methods, -n, -s and where. This file adds a series with a different
time layout (the example of the manual page) and the options that are
required, wrong or in the way of existing data.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import list_maps, message
from grass.tools import ToolError


def _month(number):
    """First day of month number, counted from 2001-01 (2001-13 is 2002-01)"""
    return datetime(2001 + (number - 1) // 12, (number - 1) % 12 + 1, 1)


@pytest.fixture(scope="module")
def series(tools):
    """Datasets A (March to August) and B (January to December), monthly

    The value of the map of month m in B is m except for September, which is
    8 (as in the manual page); A holds m for months 3 to 8.
    """
    create_stds(
        tools,
        "strds",
        "A",
        [MapSpec(f"a{m}", m, _month(m), _month(m + 1)) for m in range(3, 9)],
    )
    values = {9: 8}
    create_stds(
        tools,
        "strds",
        "B",
        [
            MapSpec(f"b{m}", values.get(m, m), _month(m), _month(m + 1))
            for m in range(1, 13)
        ],
    )
    create_stds(
        tools,
        "strds",
        "S",
        [MapSpec(f"s{m}", m, _month(m), _month(m + 1)) for m in (1, 2, 3)],
    )


def _call(tools, **options):
    return tools.t_rast_mapcalc(**{"overwrite": True, **options})


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_mapcalc(**options)
    return message(error.value)


def test_the_manual_example_with_a_condition_on_the_month(tools, series):
    # Sampled by the equal method the series meet in March to August: A holds
    # 3 to 8 and B the same numbers. In May and June the result is A + B,
    # otherwise A * B: 9, 16, 10, 12, 49 and 64.
    _call(
        tools,
        inputs="A,B",
        output="C",
        basename="c",
        method="equal",
        expression="if(start_month() == 5 || start_month() == 6, (A + B), (A * B))",
    )

    rows = list_maps(tools, "strds", "C")

    assert [row.name for row in rows] == [f"c_{number}" for number in range(1, 7)]
    assert [row.start for row in rows] == [
        _month(month).strftime("%Y-%m-%d %H:%M:%S") for month in range(3, 9)
    ]
    assert [(row.min, row.max) for row in rows] == [
        (value, value) for value in (9, 16, 10, 12, 49, 64)
    ]


@pytest.mark.parametrize("missing", ["inputs", "output", "expression", "basename"])
def test_required_options_are_named(tools, series, missing):
    options = {
        "inputs": "S",
        "output": "S_out",
        "expression": "S + 1",
        "basename": "s_out",
    }
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_unknown_sampling_method_is_refused(tools, series):
    text = _refused(
        tools,
        inputs="S",
        output="S_out",
        expression="S + 1",
        basename="s_out",
        method="bogus",
    )

    assert "Value <bogus> out of range for parameter <method>" in text


def test_a_missing_input_dataset_is_named(tools, series):
    assert "Space time dataset <nothere> of type <strds> not found" in _refused(
        tools, inputs="nothere", output="S_out", expression="nothere + 1", basename="x"
    )


def test_an_invalid_expression_stops_the_computation(tools, series):
    text = _refused(
        tools, inputs="S", output="S_out", expression="S +", basename="s_out"
    )

    assert "Error while mapcalc computation" in text


@pytest.mark.slow
def test_an_existing_output_needs_overwrite(tools, series):
    _call(tools, inputs="S", output="S_keep", expression="S + 1", basename="sk")

    text = _refused(
        tools, inputs="S", output="S_keep", expression="S + 2", basename="sk"
    )

    assert "Space time raster dataset <S_keep> is already in the database" in text
    assert [row.min for row in list_maps(tools, "strds", "S_keep")] == [2, 3, 4]


@pytest.mark.parametrize("nprocs", [0, -1])
def test_nprocs_without_a_positive_number_is_accepted(tools, series, nprocs):
    # A value below 1 runs all statements at once (_run_in_batches in
    # mapcalc.py); the result is that of a single process, so the batch size
    # itself is not visible in the output.
    _call(
        tools,
        inputs="S",
        output="S_np",
        expression="S * 10",
        basename="snp",
        nprocs=nprocs,
    )

    assert [row.min for row in list_maps(tools, "strds", "S_np")] == [10, 20, 30]


def test_nprocs_must_be_an_integer(tools, series):
    text = _refused(
        tools,
        inputs="S",
        output="S_out",
        expression="S + 1",
        basename="s_out",
        nprocs="x",
    )

    assert "Invalid value <x> for parameter <nprocs>" in text


def test_a_decimal_nprocs_today_ends_with_a_traceback(tools, series):
    # Observed 18.10.2026: the parser accepts 2.5 for the integer option and
    # int() in the script then fails.
    text = _refused(
        tools,
        inputs="S",
        output="S_out",
        expression="S + 1",
        basename="s_out",
        nprocs="2.5",
    )

    assert "ValueError: invalid literal for int() with base 10: '2.5'" in text


@pytest.mark.xfail(strict=True, reason="a decimal nprocs ends with a traceback")
def test_a_decimal_nprocs_is_reported_as_a_message(tools, series):
    text = _refused(
        tools,
        inputs="S",
        output="S_out",
        expression="S + 1",
        basename="s_out",
        nprocs="2.5",
    )

    assert "Traceback" not in text


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, series):
    text = _refused(
        tools,
        inputs="S",
        output="S_out",
        expression="S + 1",
        basename="s_out",
        where="nonsense =",
    )

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    # Nothing was made before the refusal.
    assert "S_out" not in tools.t_list(type="strds", columns="name").stdout
    assert not tools.g_list(type="raster", pattern="s_out*").stdout.strip()


def test_basename_maps_that_exist_end_with_an_error_status(tools, series):
    _call(tools, inputs="S", output="S_base3", expression="S + 1", basename="sc")

    with pytest.raises(ToolError) as error:
        tools.t_rast_mapcalc(
            inputs="S", output="S_base4", expression="S + 5", basename="sc"
        )

    assert (
        "Map <sc_1@PERMANENT> is already in temporal database, "
        "use overwrite flag to overwrite"
    ) in message(error.value)
    # The tool stops before it computes or makes anything: the maps of the
    # first run keep the values of S + 1, not S + 5.
    assert "S_base4" not in tools.t_list(type="strds", columns="name").stdout
    assert [row.min for row in list_maps(tools, "strds", "S_base3")] == [2, 3, 4]


@pytest.fixture(scope="module")
def partners(tools):
    """Sampler G with two granules and the input X with one partner for each

    The granules are 2001-01-01 to 2001-02-01 and 2001-03-01 to 2001-04-01.
    Map x1 (value 1) has the extent of the first granule (equal). Map x2
    (value 2) runs from 2001-02-15 to 2001-04-15 and covers the second
    granule (during).
    """
    create_stds(
        tools,
        "strds",
        "G",
        [
            MapSpec("g1", 100, datetime(2001, 1, 1), datetime(2001, 2, 1)),
            MapSpec("g2", 200, datetime(2001, 3, 1), datetime(2001, 4, 1)),
        ],
    )
    create_stds(
        tools,
        "strds",
        "X",
        [
            MapSpec("x1", 1, datetime(2001, 1, 1), datetime(2001, 2, 1)),
            MapSpec("x2", 2, datetime(2001, 2, 15), datetime(2001, 4, 15)),
        ],
    )


@pytest.mark.parametrize(
    ("method", "values"),
    [("equal", [1]), ("during", [2]), ("equal,during", [1, 2])],
)
def test_several_methods_collect_the_granules_of_each(tools, partners, method, values):
    _call(
        tools,
        inputs="G,X",
        output="M",
        basename="m",
        expression="X",
        method=method,
    )

    assert [row.min for row in list_maps(tools, "strds", "M")] == values


@pytest.mark.parametrize(
    ("flags", "announced", "not_announced"),
    [
        ("", "Starting temporal sampling...", "spatio-temporal"),
        ("s", "Starting spatio-temporal sampling...", "Starting temporal sampling"),
    ],
)
def test_the_flag_s_is_announced(tools, series, flags, announced, not_announced):
    result = _call(
        tools,
        inputs="S",
        output="S_flag",
        expression="S + 1",
        basename="sf",
        flags=flags,
    )

    text = message(result)
    assert announced in text
    assert not_announced not in text
