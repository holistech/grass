"""Test the output options of t.rast.univar: format, separator, -u and output"""

import csv
import io
import json

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

ONE_MAP = "start_time < '2001-01-02'"
FIRST_ROW = [
    "uv_1@PERMANENT", "", "2001-01-01 00:00:00", "2001-01-02 00:00:00", "6", "0", "1", "6",
    "5", "3.5", "3.5", "1.70782512765993", "2.91666666666667", "48.7950036474267", "21", "21",
]  # fmt: skip


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_univar(**options)
    return message(error.value)


def test_a_separator_replaces_the_bar(tools, values):
    result = tools.t_rast_univar(input=values, where=ONE_MAP, separator=";")

    lines = result.stdout.splitlines()
    assert len(lines) == 2
    assert lines[1].split(";") == FIRST_ROW


def test_a_separator_can_be_a_name(tools, values):
    result = tools.t_rast_univar(input=values, where=ONE_MAP, separator="tab")

    assert result.stdout.splitlines()[1].split("\t") == FIRST_ROW


def test_the_u_flag_leaves_out_the_header(tools, values):
    result = tools.t_rast_univar(input=values, where=ONE_MAP, flags="u")

    lines = result.stdout.splitlines()
    assert len(lines) == 1
    assert lines[0].split("|") == FIRST_ROW


def test_csv_uses_a_comma(tools, values):
    result = tools.t_rast_univar(input=values, where=ONE_MAP, format="csv")

    rows = list(csv.reader(io.StringIO(result.stdout)))
    assert rows[0][:5] == ["id", "semantic_label", "start", "end", "non_null_cells"]
    assert rows[1] == FIRST_ROW


def test_csv_takes_another_one_character_separator(tools, values):
    result = tools.t_rast_univar(
        input=values, where=ONE_MAP, format="csv", separator=";"
    )

    assert result.stdout.splitlines()[1].split(";") == FIRST_ROW


def test_csv_with_the_u_flag_has_no_header(tools, values):
    result = tools.t_rast_univar(input=values, where=ONE_MAP, format="csv", flags="u")

    assert len(result.stdout.splitlines()) == 1


def test_json_has_numbers_and_one_object_per_map(tools, values):
    result = tools.t_rast_univar(input=values, format="json")

    data = json.loads(result.stdout)
    assert [entry["id"] for entry in data] == [
        "uv_1@PERMANENT",
        "uv_2@PERMANENT",
        "uv_3@PERMANENT",
    ]
    assert (
        data[1]
        == {
            "id": "uv_2@PERMANENT",
            "semantic_label": None,
            "start": "2001-01-02 00:00:00",
            "end": "2001-01-03 00:00:00",
            "n": 4,
            "null_cells": 2,
            "cells": 6,
            "min": 1,
            "max": 6,
            "range": 5,
            "mean": 3.5,
            "mean_of_abs": 3.5,
            "stddev": pytest.approx(13**0.5 / 2, rel=1e-12),
            "variance": 3.25,
            "coeff_var": pytest.approx(100 * 13**0.5 / 2 / 3.5, rel=1e-12),
            "sum": 14,
        }
        or data[1].keys()
    )


def test_json_with_extended_statistics_lists_the_percentiles(tools, values):
    result = tools.t_rast_univar(
        input=values, format="json", flags="e", percentile=[10, 97.5], where=ONE_MAP
    )

    (entry,) = json.loads(result.stdout)
    assert (entry["first_quartile"], entry["median"], entry["third_quartile"]) == (
        2,
        3.5,
        5,
    )
    assert entry["percentiles"] == [
        {"percentile": 10, "value": 1},
        {"percentile": 97.5, "value": 6},
    ]


@pytest.mark.parametrize("output_format", ["plain", "csv", "json"])
def test_a_selection_without_maps_prints_nothing_in_any_format(
    tools, values, output_format
):
    # Not even "[]" for json, so the output is no valid JSON then.
    result = tools.t_rast_univar(
        input=values, format=output_format, where="start_time > '2010-01-01'"
    )

    assert result.stdout == ""


def test_json_refuses_a_separator(tools, values):
    text = _refused(tools, input=values, format="json", separator=";")

    assert "Separator option is not allowed with JSON format" in text


def test_json_refuses_the_u_flag(tools, values):
    text = _refused(tools, input=values, format="json", flags="u")

    assert "Column names are always included in JSON output" in text


def test_csv_refuses_a_separator_of_two_characters(tools, values):
    text = _refused(tools, input=values, format="csv", separator="ab")

    assert "A standard CSV separator (delimiter) is only one character long" in text


def test_output_writes_the_same_text_to_a_file(tools, values, tmp_path):
    path = tmp_path / "univar.txt"

    result = tools.t_rast_univar(input=values, where=ONE_MAP, output=str(path))

    assert result.stdout == ""
    lines = path.read_text().splitlines()
    assert lines[1].split("|") == FIRST_ROW


def test_an_existing_output_file_is_refused_without_overwrite(tools, values, tmp_path):
    path = tmp_path / "univar.txt"
    path.write_text("keep")

    text = _refused(tools, input=values, output=str(path))

    assert "exists. To overwrite, use the --overwrite flag" in text
    assert path.read_text() == "keep"


def test_overwrite_replaces_the_output_file(tools, values, tmp_path):
    path = tmp_path / "univar.txt"
    path.write_text("old")

    tools.t_rast_univar(input=values, output=str(path), overwrite=True)

    assert path.read_text().startswith("id|semantic_label|")


def test_a_dash_as_output_means_the_standard_output(tools, values):
    result = tools.t_rast_univar(input=values, where=ONE_MAP, output="-")

    assert result.stdout.splitlines()[1].split("|") == FIRST_ROW
