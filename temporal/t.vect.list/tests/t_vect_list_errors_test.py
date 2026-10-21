"""Test the checks of t.vect.list on the combination of its options

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
        "stvds",
        "err",
        [
            MapSpec(f"e_{n}", n, datetime(2001, n, 1), datetime(2001, n + 1, 1))
            for n in (1, 2, 3)
        ],
    )
    tools.t_create(
        type="stvds",
        output="void",
        temporaltype="absolute",
        title="void",
        description="no maps",
    )


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_vect_list(**options)
    return message(error.value)


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


@pytest.mark.parametrize("method", ["delta", "deltagaps", "gran"])
def test_the_line_format_with_a_delta_method_and_the_default_columns_is_refused(
    tools, series, method
):
    text = _refused(tools, input="err", format="line", method=method)

    assert "Only one column is allowed (not 5)" in text


@pytest.mark.parametrize(
    "options",
    [
        {"method": "sum"},
        {"format": "xml"},
        {"order": "colour"},
        {"columns": "colour"},
        {"columns": "semantic_label"},
    ],
)
def test_the_parser_refuses_unknown_values(tools, series, options):
    ((name, value),) = options.items()

    text = _refused(tools, input="err", **options)

    assert f"Value <{value}> out of range for parameter <{name}>" in text


def test_a_missing_dataset_is_named(tools, series):
    assert "Space time dataset <nothere> of type <stvds> not found" in _refused(
        tools, input="nothere"
    )


def test_the_input_is_required(tools, series):
    assert "Required parameter <input> not set" in _refused(tools)


def test_an_empty_dataset_is_refused_by_cols(tools, series):
    text = _refused(tools, input="void")

    assert (
        "Nothing found in the database for space time dataset "
        "<void@PERMANENT> (type: stvds): Dataset is empty"
    ) in text


def test_an_empty_dataset_is_refused_by_the_line_format(tools, series):
    text = _refused(tools, input="void", format="line", columns="id")

    assert "Nothing found in the database for space time dataset" in text


def test_a_where_that_selects_nothing_is_named(tools, series):
    text = _refused(tools, input="err", where="start_time > '2030-01-01'")

    assert (
        "Nothing found in the database for space time dataset <err@PERMANENT> "
        "(type: stvds): Dataset is empty or where clause is too constrained or "
        "incorrect"
    ) in text


def test_the_gran_method_of_an_empty_dataset_says_it_is_empty(tools, series):
    assert "Dataset is empty" in _refused(tools, input="void", method="gran")


@pytest.mark.parametrize("method", ["delta", "deltagaps"])
def test_the_delta_methods_of_an_empty_dataset_print_the_header_only(
    tools, series, method
):
    result = tools.t_vect_list(input="void", method=method)

    assert result.stdout.splitlines() == ["name|layer|mapset|start_time|end_time"]


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, series):
    text = _refused(tools, input="err", where="nonsense =")

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text


def test_the_delta_method_with_a_database_column_today_ends_with_a_traceback(
    tools, series
):
    text = _refused(tools, input="err", method="delta", columns="north")

    assert "ValueError: Unsupported column 'north'" in text


@pytest.mark.xfail(
    strict=True,
    reason="t.vect.list method=delta with a database column ends in a ValueError traceback instead of a message",
)
def test_the_delta_method_with_a_database_column_is_reported_as_a_message(
    tools, series
):
    assert "Traceback" not in _refused(
        tools, input="err", method="delta", columns="north"
    )
