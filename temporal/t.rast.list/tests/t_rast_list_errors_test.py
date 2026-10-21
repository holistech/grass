"""Test the checks of t.rast.list on the combination of its options

Combinations that cannot work are refused before the temporal database is
opened; the messages say which option and value are in the way. Values the
parser does not know are refused by the parser.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import message
from grass.tools import ToolError

try:
    import yaml
except ImportError:
    yaml = None

DELTA_COLUMNS = [
    "semantic_label",
    "creator",
    "temporal_type",
    "creation_time",
    "north",
    "south",
    "west",
    "east",
    "nsres",
    "ewres",
    "cols",
    "rows",
    "number_of_cells",
    "min",
    "max",
]
STRUCTURED = [
    "json",
    pytest.param(
        "yaml",
        marks=pytest.mark.skipif(yaml is None, reason="PyYAML package not available"),
    ),
]


@pytest.fixture(scope="module")
def series(tools):
    """Three monthly maps in the dataset err and an empty dataset"""
    create_stds(
        tools,
        "strds",
        "err",
        [
            MapSpec(f"e_{n}", n, datetime(2001, n, 1), datetime(2001, n + 1, 1))
            for n in (1, 2, 3)
        ],
    )
    tools.t_create(
        type="strds",
        output="void",
        temporaltype="absolute",
        title="void",
        description="no maps",
    )


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_list(**options)
    return message(error.value)


@pytest.mark.parametrize("method", ["delta", "deltagaps", "gran"])
def test_order_is_refused_with_the_delta_methods(tools, series, method):
    text = _refused(tools, input="err", method=method, order="name")

    assert (
        f"The option order is not allowed with method={method}. "
        "Values are always ordered by start_time"
    ) in text


@pytest.mark.parametrize("column", DELTA_COLUMNS)
def test_columns_of_the_database_are_refused_with_delta(tools, series, column):
    text = _refused(tools, input="err", method="delta", columns=f"id,{column}")

    assert (
        f"Combining method=delta and columns=id,{column} is not allowed. "
        f"Column '{column}' is not available with the method 'delta'"
    ) in text


@pytest.mark.parametrize("method", ["deltagaps", "gran"])
def test_columns_of_the_database_are_refused_with_deltagaps_and_gran(
    tools, series, method
):
    text = _refused(tools, input="err", method=method, columns="north")

    assert (
        f"Combining method={method} and columns=north is not allowed. "
        f"Column 'north' is not available with the method '{method}'"
    ) in text


@pytest.mark.parametrize("column", ["interval_length", "distance_from_begin"])
@pytest.mark.parametrize("method", ["list", "cols", "comma"])
def test_columns_of_the_delta_methods_are_refused_with_list(
    tools, series, method, column
):
    text = _refused(tools, input="err", method=method, columns=column)

    assert (
        f"Combining method={method} and columns={column} is not allowed. "
        f"Column '{column}' is not available with the method '{method}'"
    ) in text


def test_a_long_csv_separator_is_refused(tools, series):
    text = _refused(tools, input="err", format="csv", separator="ab")

    assert (
        "Combining format=csv and separator=ab is not allowed. "
        "A standard CSV separator (delimiter) is only one character long"
    ) in text


@pytest.mark.parametrize("output_format", STRUCTURED)
def test_the_flag_u_is_refused_with_json_and_yaml(tools, series, output_format):
    text = _refused(tools, input="err", format=output_format, flags="u")

    assert (
        f"The flag -u is not allowed with format={output_format}. "
        "Column names are always included"
    ) in text


@pytest.mark.parametrize("output_format", STRUCTURED)
def test_a_separator_is_refused_with_json_and_yaml(tools, series, output_format):
    text = _refused(tools, input="err", format=output_format, separator="comma")

    assert (
        f"Combining format={output_format} and separator=, is not allowed. "
        "Separator is part of the format"
    ) in text


def test_the_line_format_takes_one_column(tools, series):
    text = _refused(tools, input="err", format="line", columns="name,mapset")

    assert (
        "Combining format=line and columns=name,mapset is not allowed. "
        "Only one column is allowed (not 2)"
    ) in text


@pytest.mark.parametrize(
    "options",
    [
        {"method": "sum"},
        {"format": "xml"},
        {"order": "colour"},
        {"columns": "colour"},
    ],
)
def test_the_parser_refuses_unknown_values(tools, series, options):
    ((name, value),) = options.items()

    text = _refused(tools, input="err", **options)

    assert f"<{value}>" in text
    assert f"<{name}>" in text


def test_a_missing_dataset_is_named(tools, series):
    assert "Space time dataset <nothere> of type <strds> not found" in _refused(
        tools, input="nothere"
    )


def test_the_input_is_required(tools, series):
    assert "Required parameter <input> not set" in _refused(tools)


def test_an_empty_dataset_is_refused_by_list_and_line(tools, series):
    for options in ({}, {"format": "line"}):
        text = _refused(tools, input="void", **options)

        assert (
            "Nothing found in the database for space time dataset "
            "<void@PERMANENT> (type: strds): Dataset is empty"
        ) in text


def test_a_where_that_selects_nothing_is_named(tools, series):
    text = _refused(tools, input="err", where="start_time > '2030-01-01'")

    assert (
        "Nothing found in the database for space time dataset <err@PERMANENT> "
        "(type: strds): Dataset is empty or where clause is too constrained or "
        "incorrect"
    ) in text


def test_a_granule_of_the_wrong_kind_is_refused(tools, series):
    assert 'Wrong granularity: "3 foo"' in _refused(
        tools, input="err", method="gran", granule="3 foo"
    )
    # A relative granule does not fit absolute time.
    assert 'Wrong granularity: "2"' in _refused(
        tools, input="err", method="gran", granule="2"
    )


def test_the_gran_method_of_an_empty_dataset_says_it_is_empty(tools, series):
    assert "Dataset is empty" in _refused(tools, input="void", method="gran")


def test_the_gran_method_with_a_granule_says_an_empty_dataset_is_empty(tools, series):
    # The manual says that gran refuses an empty dataset, with or without a
    # granule of its own.
    assert "Dataset is empty" in _refused(
        tools, input="void", method="gran", granule="1 month"
    )


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, series):
    text = _refused(tools, input="err", where="nonsense =")

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    # The statement is not printed as an error of its own.
    assert "Unable to execute" not in text


def test_the_delta_method_with_the_line_format_is_reported_as_a_message(tools, series):
    text = _refused(tools, input="err", method="delta", format="line")

    assert "Traceback" not in text
    assert "'line' output_format can have only 1 column, not 7" in text


def test_the_delta_method_with_the_line_format_works_for_one_column(tools, series):
    result = tools.t_rast_list(
        input="err", method="delta", format="line", columns="name"
    )

    assert result.stdout == "e_1,e_2,e_3\n"
