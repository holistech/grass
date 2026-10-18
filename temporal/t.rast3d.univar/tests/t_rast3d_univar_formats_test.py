"""Test the output options of t.rast3d.univar: format, separator, -s and output"""

import csv
import io
import json
import math

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

ONE_MAP = "start_time < '2001-01-02'"
# The row of the first map: 12 voxels holding 1 to 12. The statistics that
# are no whole numbers are compared as numbers (stddev = sqrt(143 / 12)).
IDENTITY = ["uv3_1@PERMANENT", "2001-01-01 00:00:00", "2001-01-02 00:00:00"]
STATISTICS = [
    12, 0, 1, 12, 11, 6.5, 6.5, math.sqrt(143 / 12), 143 / 12,
    100 * math.sqrt(143 / 12) / 6.5, 78, 78,
]  # fmt: skip


def _check_row(fields):
    assert fields[:3] == IDENTITY
    assert [float(field) for field in fields[3:]] == pytest.approx(
        STATISTICS, rel=1e-12
    )


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast3d_univar(**options)
    return message(error.value)


def test_a_separator_replaces_the_bar(tools, values):
    result = tools.t_rast3d_univar(input=values, where=ONE_MAP, separator=";")

    lines = result.stdout.splitlines()
    assert len(lines) == 2
    _check_row(lines[1].split(";"))


def test_a_separator_can_be_a_name(tools, values):
    result = tools.t_rast3d_univar(input=values, where=ONE_MAP, separator="tab")

    _check_row(result.stdout.splitlines()[1].split("\t"))


def test_the_s_flag_leaves_out_the_header(tools, values):
    result = tools.t_rast3d_univar(input=values, where=ONE_MAP, flags="s")

    lines = result.stdout.splitlines()
    assert len(lines) == 1
    _check_row(lines[0].split("|"))


def test_csv_uses_a_comma(tools, values):
    result = tools.t_rast3d_univar(input=values, where=ONE_MAP, format="csv")

    rows = list(csv.reader(io.StringIO(result.stdout)))
    assert rows[0][:4] == ["id", "start", "end", "non_null_cells"]
    _check_row(rows[1])


def test_csv_takes_another_one_character_separator(tools, values):
    result = tools.t_rast3d_univar(
        input=values, where=ONE_MAP, format="csv", separator=";"
    )

    _check_row(result.stdout.splitlines()[1].split(";"))


def test_csv_with_the_s_flag_has_no_header(tools, values):
    result = tools.t_rast3d_univar(input=values, where=ONE_MAP, format="csv", flags="s")

    assert len(result.stdout.splitlines()) == 1


def test_json_has_numbers_and_one_object_per_map(tools, values):
    result = tools.t_rast3d_univar(input=values, format="json")

    data = json.loads(result.stdout)
    assert [entry["id"] for entry in data] == [
        "uv3_1@PERMANENT",
        "uv3_2@PERMANENT",
        "uv3_3@PERMANENT",
    ]
    # The second map: 8 of 12 voxels, variance 98 / 8
    entry = data[1]
    assert entry == {
        "id": "uv3_2@PERMANENT",
        # The key is there although 3D raster maps have no semantic label.
        "semantic_label": None,
        "start": "2001-01-02 00:00:00",
        "end": "2001-01-03 00:00:00",
        "n": 8,
        "null_cells": 4,
        "cells": 12,
        "min": 1,
        "max": 12,
        "range": 11,
        "mean": 6.5,
        "mean_of_abs": 6.5,
        "stddev": pytest.approx(3.5, rel=1e-12),
        "variance": 12.25,
        "coeff_var": pytest.approx(100 * 3.5 / 6.5, rel=1e-12),
        "sum": 52,
    }


def test_json_with_extended_statistics_lists_the_percentiles(tools, values):
    result = tools.t_rast3d_univar(
        input=values, format="json", flags="e", percentile=[10, 97.5], where=ONE_MAP
    )

    (entry,) = json.loads(result.stdout)
    assert (entry["first_quartile"], entry["median"], entry["third_quartile"]) == (
        3,
        6.5,
        9,
    )
    assert entry["percentiles"] == [
        {"percentile": 10, "value": 1},
        {"percentile": 97.5, "value": 12},
    ]


@pytest.mark.parametrize("output_format", ["plain", "csv", "json"])
def test_a_selection_without_maps_prints_nothing_in_any_format(
    tools, values, output_format
):
    # Not even "[]" for json, so the output is no valid JSON then.
    result = tools.t_rast3d_univar(
        input=values, format=output_format, where="start_time > '2010-01-01'"
    )

    assert result.stdout == ""


def test_json_refuses_a_separator(tools, values):
    text = _refused(tools, input=values, format="json", separator=";")

    assert "Separator option is not allowed with JSON format" in text


def test_json_refuses_the_s_flag(tools, values):
    text = _refused(tools, input=values, format="json", flags="s")

    assert "Column names are always included in JSON output" in text


def test_csv_refuses_a_separator_of_two_characters(tools, values):
    text = _refused(tools, input=values, format="csv", separator="::")

    assert "A standard CSV separator (delimiter) is only one character long" in text


def test_output_writes_the_same_text_to_a_file(tools, values, tmp_path):
    path = tmp_path / "univar.txt"

    result = tools.t_rast3d_univar(input=values, where=ONE_MAP, output=str(path))

    assert result.stdout == ""
    lines = path.read_text().splitlines()
    assert lines[0].startswith("id|start|end|")
    _check_row(lines[1].split("|"))


def test_output_without_the_header_for_a_subset(tools, values, tmp_path):
    path = tmp_path / "univar.txt"

    tools.t_rast3d_univar(
        input=values, where="start_time >= '2001-01-02'", output=str(path), flags="s"
    )

    lines = path.read_text().splitlines()
    assert [line.split("|")[0] for line in lines] == [
        "uv3_2@PERMANENT",
        "uv3_3@PERMANENT",
    ]


def test_an_existing_output_file_is_refused_without_overwrite(tools, values, tmp_path):
    path = tmp_path / "univar.txt"
    path.write_text("keep")

    text = _refused(tools, input=values, output=str(path))

    assert "exists. To overwrite, use the --overwrite flag" in text
    assert path.read_text() == "keep"


def test_overwrite_replaces_the_output_file(tools, values, tmp_path):
    path = tmp_path / "univar.txt"
    path.write_text("old")

    tools.t_rast3d_univar(input=values, output=str(path), overwrite=True)

    assert path.read_text().startswith("id|start|")


def test_a_dash_as_output_means_the_standard_output(
    tools, values, tmp_path, monkeypatch
):
    # In tmp_path, so that a tool that writes a file named "-" leaves it there.
    monkeypatch.chdir(tmp_path)
    result = tools.t_rast3d_univar(input=values, where=ONE_MAP, output="-")

    _check_row(result.stdout.splitlines()[1].split("|"))
