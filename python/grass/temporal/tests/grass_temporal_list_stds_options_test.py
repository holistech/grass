"""Tests for the option checks shared by t.rast.list, t.rast3d.list and t.vect.list

The messages are the ones the tools print, so each is pinned word for word.
"""

import pytest

from grass.temporal.list_stds import (
    check_list_format,
    check_list_method,
    check_list_options,
    checked_separator,
    message_option_value_excludes_flag,
    message_option_value_excludes_option,
    message_option_value_excludes_option_value,
)

DELTA_COLUMNS = ["creator", "north"]


def _refusal(function, *args, **kwargs):
    """Return the message of the ValueError that function raises"""
    try:
        function(*args, **kwargs)
    except ValueError as error:
        return str(error)
    return pytest.fail("The combination was not refused")


def test_the_message_for_two_option_values():
    assert message_option_value_excludes_option_value(
        option_name="format",
        option_value="csv",
        excluded_option_name="separator",
        excluded_option_value="ab",
        reason="Too long",
    ) == ("Combining format=csv and separator=ab is not allowed. Too long")


def test_the_message_for_an_option_after_an_option_value():
    assert message_option_value_excludes_option(
        option_name="method",
        option_value="delta",
        excluded_option_name="order",
        reason="Always ordered",
    ) == ("The option order is not allowed with method=delta. Always ordered")


def test_the_message_for_a_flag_after_an_option_value():
    assert message_option_value_excludes_flag(
        option_name="format", option_value="json", flag_name="u", reason="Included"
    ) == ("The flag -u is not allowed with format=json. Included")


@pytest.mark.parametrize(
    ("output_format", "method", "separator", "expected"),
    [
        ("plain", "cols", "", ("plain", "|")),
        ("plain", "cols", ";", ("plain", ";")),
        ("csv", "cols", "", ("csv", ",")),
        ("csv", "cols", ";", ("csv", ";")),
        ("line", "cols", "", ("line", ",")),
        ("plain", "comma", "", ("line", ",")),
        # The format wins over the old name of the line format.
        ("csv", "comma", "", ("csv", ",")),
        ("json", "comma", "", ("json", "")),
        ("yaml", "cols", "", ("yaml", "")),
    ],
)
def test_the_format_and_the_separator_are_completed(
    output_format, method, separator, expected
):
    assert (
        check_list_format(output_format, separator, method, "name", False, "u")
        == expected
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"output_format": "csv", "separator": ";;"},
            "Combining format=csv and separator=;; is not allowed. "
            "A standard CSV separator (delimiter) is only one character long",
        ),
        (
            {"output_format": "json", "header": True},
            "The flag -u is not allowed with format=json. "
            "Column names are always included",
        ),
        (
            {"output_format": "yaml", "separator": ","},
            "Combining format=yaml and separator=, is not allowed. "
            "Separator is part of the format",
        ),
        (
            {"output_format": "line", "columns": "name,mapset"},
            "Combining format=line and columns=name,mapset is not allowed. "
            "Only one column is allowed (not 2)",
        ),
        (
            {"output_format": "plain", "method": "comma", "columns": "a,b,c"},
            "Combining format=line and columns=a,b,c is not allowed. "
            "Only one column is allowed (not 3)",
        ),
    ],
)
def test_a_refused_combination_of_format_options_gives_its_message(kwargs, message):
    arguments = {
        "output_format": "plain",
        "separator": "",
        "method": "cols",
        "columns": "name",
        "header": False,
        "header_flag": "u",
    }
    arguments.update(kwargs)

    text = _refusal(check_list_format, **arguments)

    assert text == message


def test_the_reason_for_a_separator_with_json_can_be_replaced():
    text = _refusal(
        check_list_format, "json", ",", "cols", "", False, "s", "Not with this"
    )

    assert text == (
        "Combining format=json and separator=, is not allowed. Not with this"
    )


@pytest.mark.parametrize("method", ["delta", "deltagaps", "gran"])
def test_an_order_is_refused_with_the_delta_methods(method):
    text = _refusal(check_list_method, method, "name", "", DELTA_COLUMNS)

    assert text == (
        f"The option order is not allowed with method={method}. "
        "Values are always ordered by start_time"
    )


def test_a_column_of_the_database_is_refused_with_a_delta_method():
    text = _refusal(check_list_method, "delta", "", "name,north", DELTA_COLUMNS)

    assert text == (
        "Combining method=delta and columns=name,north is not allowed. "
        "Column 'north' is not available with the method 'delta'"
    )


@pytest.mark.parametrize("method", ["cols", "comma"])
def test_a_column_of_the_delta_methods_is_refused_with_the_other_methods(method):
    text = _refusal(check_list_method, method, "", "interval_length", DELTA_COLUMNS)

    assert text == (
        f"Combining method={method} and columns=interval_length is not allowed. "
        f"Column 'interval_length' is not available with the method '{method}'"
    )


@pytest.mark.parametrize(
    ("method", "order", "columns"),
    [
        ("cols", "name", "north"),
        ("delta", "", "interval_length"),
        ("delta", "", ""),
        ("gran", "", "name"),
    ],
)
def test_allowed_combinations_of_method_order_and_columns_pass(method, order, columns):
    assert check_list_method(method, order, columns, DELTA_COLUMNS) is None


def test_the_options_are_checked_as_the_tools_did():
    options = {
        "format": "plain",
        "separator": "comma",
        "method": "cols",
        "columns": "name",
        "order": "",
    }

    assert check_list_options(
        options, {"u": False}, header_flag="u", delta_excluded_columns=DELTA_COLUMNS
    ) == ("plain", ",")


def test_the_format_is_checked_before_the_method():
    options = {
        "format": "csv",
        "separator": ";;",
        "method": "delta",
        "columns": "north",
        "order": "name",
    }

    with pytest.raises(ValueError, match="format=csv"):
        check_list_options(
            options,
            {"u": False},
            header_flag="u",
            delta_excluded_columns=DELTA_COLUMNS,
        )


@pytest.mark.parametrize(
    ("output_format", "separator", "expected"),
    [
        ("csv", "", ","),
        ("csv", ";", ";"),
        ("plain", "", "|"),
        ("plain", "\t", "\t"),
        ("json", "", ""),
    ],
)
def test_the_separator_gets_its_default_per_format(output_format, separator, expected):
    assert checked_separator(output_format, separator, column_names=False) == expected


@pytest.mark.parametrize(
    ("output_format", "separator", "column_names", "message"),
    [
        (
            "csv",
            ";;",
            False,
            "A standard CSV separator (delimiter) is only one character long",
        ),
        (
            "json",
            "",
            True,
            "Column names are always included in JSON output",
        ),
        (
            "json",
            ",",
            False,
            "Separator option is not allowed with JSON format",
        ),
        # The flag is checked before the separator.
        (
            "json",
            ",",
            True,
            "Column names are always included in JSON output",
        ),
    ],
)
def test_a_refused_separator_gives_its_message(
    output_format, separator, column_names, message
):
    text = _refusal(
        checked_separator, output_format, separator, column_names=column_names
    )

    assert text == message


@pytest.mark.parametrize("output_format", ["plain", "csv"])
def test_the_flag_for_the_column_names_is_free_outside_json(output_format):
    assert checked_separator(output_format, "", column_names=True) in {",", "|"}
