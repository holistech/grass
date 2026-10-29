"""Test the options and refusals of t.list that the format tests do not reach

The tests share the project of the module and filter by the unique prefix of
the test, because other tests list the same tables.
"""

import json

import pytest

from grass.temporal.testing.data import create_daily_stds
from grass.temporal.testing.readback import message
from grass.tools import ToolError

# Most tests make maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

HEADER = "----------------------------------------------"


def test_plain_output_groups_the_datasets_by_type(tools, prefix, make_stds):
    _, names = make_stds(2)
    create_daily_stds(tools, "stvds", [f"{prefix}_v"], 2, map_prefix=f"{prefix}v")
    where = f"name LIKE '{prefix}%'"

    result = tools.t_list(type="strds,stvds", columns="name,type", where=where)

    # The types are listed in the order of the option, and every group has its
    # own report of the mapset.
    assert result.stdout.splitlines() == [f"{names[0]}|strds", f"{prefix}_v|stvds"]
    assert result.stderr.count(HEADER) == 2
    assert "Space time raster datasets with absolute time available in mapset" in (
        result.stderr
    )
    assert "Space time vector datasets with absolute time available in mapset" in (
        result.stderr
    )


def test_the_type_column_with_one_type(tools, prefix, make_stds):
    maps, _ = make_stds(2)

    result = tools.t_list(
        type="raster", columns="name,type", where=f"name LIKE '{prefix}%'"
    )

    assert result.stdout.splitlines() == [f"{maps[0]}|raster", f"{maps[1]}|raster"]


def test_the_type_column_cannot_be_requested_alone(tools):
    with pytest.raises(ToolError) as error:
        tools.t_list(type="strds", columns="type")

    assert "Column 'type' cannot be requested alone" in message(error.value)


def test_a_separator_of_a_plain_listing(tools, prefix, make_stds):
    maps, _ = make_stds(2)

    result = tools.t_list(
        type="raster",
        columns="name,semantic_label",
        where=f"name LIKE '{prefix}%'",
        separator=";",
    )

    # The maps have no semantic label, which the plain format prints as None.
    assert result.stdout.splitlines() == [f"{maps[0]};None", f"{maps[1]};None"]


def test_the_column_flag_prints_the_names_once_and_adds_the_type(
    tools, prefix, make_stds
):
    _, names = make_stds(2)
    create_daily_stds(tools, "stvds", [f"{prefix}_v"], 2, map_prefix=f"{prefix}v")

    result = tools.t_list(
        type="strds,stvds",
        columns="name,number_of_maps",
        where=f"name LIKE '{prefix}%'",
        flags="c",
        separator=" ",
    )

    assert result.stdout.splitlines() == [
        "name number_of_maps type",
        f"{names[0]} 2 strds",
        f"{prefix}_v 2 stvds",
    ]


def test_csv_with_the_column_flag_and_a_separator(tools, prefix, make_stds):
    maps, _ = make_stds(2)

    result = tools.t_list(
        type="raster",
        columns="name,start_time",
        where=f"name LIKE '{prefix}%'",
        format="csv",
        separator=";",
        flags="c",
    )

    # Day n-1 to day n from 2001-01-01, see make_stds.
    assert result.stdout.splitlines() == [
        "name;start_time",
        f"{maps[0]};2001-01-01 00:00:00",
        f"{maps[1]};2001-01-02 00:00:00",
    ]
    assert result.stderr == ""


def test_csv_always_prints_the_column_names(tools, prefix, make_stds):
    maps, _ = make_stds(1)

    result = tools.t_list(
        type="raster",
        columns="name,semantic_label",
        where=f"name LIKE '{prefix}%'",
        format="csv",
    )

    # A missing value is left empty, and the flag -c is not needed for the
    # header.
    assert result.stdout.splitlines() == ["name,semantic_label", f"{maps[0]},"]


def test_a_csv_separator_is_one_character(tools):
    with pytest.raises(ToolError) as error:
        tools.t_list(type="strds", format="csv", separator="ab")

    assert "A standard CSV separator (delimiter) is only one character long" in (
        message(error.value)
    )


def test_json_refuses_a_separator(tools):
    with pytest.raises(ToolError) as error:
        tools.t_list(type="strds", format="json", separator=",")

    assert "Separator option is not allowed with JSON format" in message(error.value)


def test_json_refuses_the_column_flag(tools):
    with pytest.raises(ToolError) as error:
        tools.t_list(type="strds", format="json", flags="c")

    assert "Column names are always included in JSON output" in message(error.value)


def test_line_refuses_the_column_flag(tools):
    with pytest.raises(ToolError) as error:
        tools.t_list(type="strds", format="line", flags="c")

    assert "Column names are not allowed with line format" in message(error.value)


def test_line_with_a_separator(tools, prefix, make_stds):
    maps, _ = make_stds(2)

    result = tools.t_list(
        type="raster",
        where=f"name LIKE '{prefix}%'",
        format="line",
        separator=";",
    )

    assert result.stdout == f"{maps[0]}@PERMANENT;{maps[1]}@PERMANENT\n"


def test_a_relative_listing_leaves_out_the_absolute_datasets(tools, prefix, make_stds):
    make_stds(2)

    result = tools.t_list(
        type="raster", where=f"name LIKE '{prefix}%'", temporaltype="relative"
    )

    assert result.stdout == ""


def test_both_temporal_types_are_listed_one_after_the_other(tools, prefix, make_stds):
    maps, _ = make_stds(2)
    where = f"name LIKE '{prefix}%'"

    result = tools.t_list(
        type="raster", columns="name", where=where, temporaltype="relative,absolute"
    )

    assert result.stdout.splitlines() == maps
    assert "with absolute time available" in result.stderr
    assert "with relative time" not in result.stderr


def test_a_column_that_the_type_lacks(tools, make_stds):
    # The columns are read from the tables of the temporal database, which
    # exists once a dataset has been made.
    make_stds(1)
    with pytest.raises(ToolError) as error:
        tools.t_list(type="strds", columns="name,semantic_label")

    assert (
        "Column 'semantic_label' is not available for the requested dataset type"
        in (message(error.value))
    )


def test_order_descending_is_refused(tools):
    # The parser takes only the names of columns, so a sort direction cannot be
    # given.
    with pytest.raises(ToolError) as error:
        tools.t_list(type="strds", order="name DESC")

    assert "Value <name DESC> out of range for parameter <order>" in message(
        error.value
    )


def test_the_report_is_left_out_when_quiet(tools, prefix, make_stds):
    _, names = make_stds(1)

    result = tools.t_list(
        type="strds", columns="name", where=f"name LIKE '{prefix}%'", quiet=True
    )

    assert result.stdout == f"{names[0]}\n"
    assert result.stderr == ""


def test_output_to_a_file(tools, prefix, make_stds, tmp_path):
    _, names = make_stds(1)
    path = tmp_path / "list.txt"

    result = tools.t_list(
        type="strds",
        columns="name",
        where=f"name LIKE '{prefix}%'",
        output=str(path),
    )

    assert path.read_text() == f"{names[0]}\n"
    assert result.stdout == ""
    # The report of the mapset belongs to the screen only.
    assert HEADER not in result.stderr


def test_output_dash_is_the_screen(tools, prefix, make_stds):
    _, names = make_stds(1)

    result = tools.t_list(
        type="strds", columns="name", where=f"name LIKE '{prefix}%'", output="-"
    )

    assert result.stdout == f"{names[0]}\n"


def test_json_to_a_file(tools, prefix, make_stds, tmp_path):
    maps, _ = make_stds(2)
    path = tmp_path / "list.json"

    tools.t_list(
        type="raster",
        columns="name",
        where=f"name LIKE '{prefix}%'",
        format="json",
        output=str(path),
    )

    assert [row["name"] for row in json.loads(path.read_text())] == maps


@pytest.fixture(scope="module")
def raster_3d_maps(tools):
    """A 3D raster map in a dataset, made once for the pinned defect"""
    return create_daily_stds(
        tools, "str3ds", ["list_raster_3d_ds"], 2, map_prefix="list_raster_3d"
    )


def test_t_list_lists_raster_3d_maps(tools, raster_3d_maps):
    result = tools.t_list(
        type="raster_3d", columns="name", where="name LIKE 'list_raster_3d%'"
    )

    assert result.stdout.splitlines() == raster_3d_maps


def _listing_refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_list(type="strds", **options)
    return message(error.value)


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, make_stds):
    make_stds(1)
    text = _listing_refused(tools, where="nonsense =")

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    # The library leaves the report to the tool: one error, not also the SQL.
    assert text.count("ERROR:") == 1


@pytest.mark.parametrize(
    ("output_format", "expected"),
    [("plain", ""), ("csv", "name\n"), ("line", ""), ("json", "[]\n")],
)
def test_a_where_that_selects_nothing(
    tools, prefix, make_stds, output_format, expected
):
    # A dataset makes sure that the temporal database exists.
    make_stds(1)

    result = tools.t_list(
        type="strds",
        columns="name",
        where=f"name = '{prefix}_none'",
        format=output_format,
    )

    assert result.stdout == expected


def test_csv_prints_the_column_names_once_over_both_temporal_types(
    tools, prefix, make_stds
):
    _, names = make_stds(1)
    relative = f"{prefix}_rel"
    tools.t_create(
        output=relative,
        type="strds",
        temporaltype="relative",
        title="relative",
        description="relative",
    )

    result = tools.t_list(
        type="strds",
        columns="name",
        where=f"name LIKE '{prefix}%'",
        temporaltype="absolute,relative",
        format="csv",
    )

    assert result.stdout.splitlines() == ["name", names[0], relative]


def test_an_invalid_where_leaves_the_output_file(tools, make_stds, tmp_path):
    make_stds(1)
    path = tmp_path / "list.txt"
    path.write_text("earlier listing\n")

    with pytest.raises(ToolError) as error:
        tools.t_list(type="strds", where="nonsense =", output=str(path), overwrite=True)

    assert "Invalid where condition <nonsense =>" in message(error.value)
    assert path.read_text() == "earlier listing\n"


def test_an_invalid_where_creates_no_output_file(tools, make_stds, tmp_path):
    make_stds(1)
    path = tmp_path / "list.txt"

    text = _listing_refused(tools, where="nonsense =", output=str(path))

    assert "Invalid where condition <nonsense =>" in text
    assert not path.exists()


@pytest.mark.parametrize(
    ("output_format", "expected"),
    [("plain", ""), ("csv", "name\n"), ("line", ""), ("json", "[]\n")],
)
def test_a_where_that_selects_nothing_still_writes_the_output_file(
    tools, prefix, make_stds, tmp_path, output_format, expected
):
    make_stds(1)
    path = tmp_path / "list.txt"
    path.write_text("earlier listing\n")

    tools.t_list(
        type="strds",
        columns="name",
        where=f"name = '{prefix}_none'",
        format=output_format,
        output=str(path),
        overwrite=True,
    )

    assert path.read_text() == expected


def test_csv_without_matches_prints_the_header(tools, prefix, make_stds):
    make_stds(1)

    result = tools.t_list(
        type="strds",
        columns="name,id,creator",
        where=f"name = '{prefix}_none'",
        format="csv",
        separator=";",
    )

    # The column names come in the requested order and with the separator,
    # without a data line.
    assert result.stdout == "name;id;creator\n"


def test_csv_without_matches_prints_the_header_once_with_the_flag(
    tools, prefix, make_stds
):
    make_stds(1)

    result = tools.t_list(
        type="strds",
        columns="name,id",
        where=f"name = '{prefix}_none'",
        temporaltype="absolute,relative",
        format="csv",
        flags="c",
    )

    assert result.stdout == "name,id\n"


def test_csv_without_matches_names_the_type_after_the_other_columns(
    tools, prefix, make_stds
):
    make_stds(1)

    result = tools.t_list(
        type="strds,stvds",
        columns="type,name",
        where=f"name = '{prefix}_none'",
        format="csv",
    )

    # As with rows, where the type is added to the database columns.
    assert result.stdout == "name,type\n"


def test_csv_without_matches_names_all_the_columns_like_a_listing_with_rows(
    tools, prefix, make_stds
):
    make_stds(1)
    with_rows = tools.t_list(
        type="strds", columns="all", where=f"name LIKE '{prefix}%'", format="csv"
    )

    without_rows = tools.t_list(
        type="strds", columns="all", where=f"name = '{prefix}_none'", format="csv"
    )

    assert without_rows.stdout == with_rows.stdout.splitlines()[0] + "\n"
    assert without_rows.stdout.startswith("id,")


def test_csv_without_matches_writes_the_header_to_the_output_file(
    tools, prefix, make_stds, tmp_path
):
    make_stds(1)
    path = tmp_path / "list.csv"
    path.write_text("earlier listing\n")

    result = tools.t_list(
        type="strds",
        columns="name,id",
        where=f"name = '{prefix}_none'",
        format="csv",
        output=str(path),
        overwrite=True,
    )

    assert path.read_text() == "name,id\n"
    assert result.stdout == ""


@pytest.mark.parametrize("columns", ["name,all", "all", "id,name,type"])
def test_the_header_without_matches_is_that_of_a_listing_with_rows(
    tools, prefix, make_stds, columns
):
    make_stds(1)
    options = {"type": "strds,stvds", "columns": columns, "format": "csv"}

    with_rows = tools.t_list(where=f"name LIKE '{prefix}%'", **options)
    without_rows = tools.t_list(where=f"name = '{prefix}_none'", **options)

    # The library takes all columns when "all" occurs in the list, so the
    # header does the same. A blank after a comma never reaches it, because
    # the parser refuses it.
    assert without_rows.stdout == with_rows.stdout.splitlines()[0] + "\n"
