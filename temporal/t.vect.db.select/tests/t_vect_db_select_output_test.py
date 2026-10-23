"""Test what t.vect.db.select prints for the maps of a dataset

The datasets are described in conftest.py. The tool runs v.db.select for each
map in the order of the start times and puts the start and end time of the map
in front of every row; the end time of an instant is empty. The header of a map
is printed again whenever it differs from the header printed before.
"""

import json

import pytest

# x = k and y = 1, 2, 3 for map k, observation = 100 k, label = a, b, c
INTERVAL_ROWS = [
    f"{start}|{end}|{k}|{y}|{y}|{100 * k}|{label}"
    for k, (start, end) in enumerate(
        [
            ("2001-03-01 00:00:00", "2001-04-01 00:00:00"),
            ("2001-04-01 00:00:00", "2001-05-01 00:00:00"),
            ("2001-05-01 00:00:00", "2001-06-01 00:00:00"),
        ],
        start=1,
    )
    for y, label in ((1, "a"), (2, "b"), (3, "c"))
]
INTERVAL_HEADER = "start_time|end_time|x|y|cat|observation|label"


def _lines(tools, **options):
    return tools.t_vect_db_select(**options).stdout.splitlines()


def test_the_default_prints_the_times_and_the_whole_table(tools, intervals):
    assert _lines(tools, input=intervals) == [INTERVAL_HEADER, *INTERVAL_ROWS]


def test_an_instant_has_an_empty_end_time(tools, instants):
    lines = _lines(tools, input=instants)

    assert lines[0] == "start_time|end_time|x|y|cat|observation"
    assert lines[1:] == [
        f"{start}||{k}|{y}|{y}|{100 * k}"
        for k, start in enumerate(
            ["2004-01-01 00:00:00", "2004-04-01 00:00:00", "2004-07-01 00:00:00"],
            start=1,
        )
        for y in (1, 2, 3)
    ]


def test_columns_choose_and_order_the_attributes(tools, intervals):
    lines = _lines(tools, input=intervals, columns="label,observation", where="cat = 3")

    assert lines == [
        "start_time|end_time|label|observation",
        "2001-03-01 00:00:00|2001-04-01 00:00:00|c|100",
        "2001-04-01 00:00:00|2001-05-01 00:00:00|c|200",
        "2001-05-01 00:00:00|2001-06-01 00:00:00|c|300",
    ]


def test_where_selects_rows_of_every_map(tools, intervals):
    lines = _lines(tools, input=intervals, where="cat = 1", separator="  |  ")

    assert lines == [
        "start_time  |  end_time  |  x  |  y  |  cat  |  observation  |  label",
        "2001-03-01 00:00:00  |  2001-04-01 00:00:00  |  1  |  1  |  1  |  100  |  a",
        "2001-04-01 00:00:00  |  2001-05-01 00:00:00  |  2  |  1  |  1  |  200  |  a",
        "2001-05-01 00:00:00  |  2001-06-01 00:00:00  |  3  |  1  |  1  |  300  |  a",
    ]


def test_the_separator_of_an_instant_sits_between_the_empty_fields(tools, instants):
    lines = _lines(tools, input=instants, where="cat = 1", separator="  |  ")

    assert lines == [
        "start_time  |  end_time  |  x  |  y  |  cat  |  observation",
        "2004-01-01 00:00:00  |    |  1  |  1  |  1  |  100",
        "2004-04-01 00:00:00  |    |  2  |  1  |  1  |  200",
        "2004-07-01 00:00:00  |    |  3  |  1  |  1  |  300",
    ]


@pytest.mark.parametrize(
    ("separator", "delimiter"),
    [("comma", ","), ("tab", "\t"), ("space", " "), (";", ";"), ("pipe", "|")],
)
def test_the_separator_can_be_a_name_or_a_character(
    tools, intervals, separator, delimiter
):
    lines = _lines(
        tools, input=intervals, where="cat = 1", columns="label", separator=separator
    )

    assert lines[0] == delimiter.join(["start_time", "end_time", "label"])
    assert lines[1] == delimiter.join(
        ["2001-03-01 00:00:00", "2001-04-01 00:00:00", "a"]
    )


def test_t_where_selects_the_maps(tools, intervals):
    lines = _lines(
        tools,
        input=intervals,
        columns="observation",
        where="cat = 1",
        t_where="start_time >= '2001-04-01 00:00:00'",
    )

    assert lines == [
        "start_time|end_time|observation",
        "2001-04-01 00:00:00|2001-05-01 00:00:00|200",
        "2001-05-01 00:00:00|2001-06-01 00:00:00|300",
    ]


@pytest.mark.parametrize(("output_format", "stdout"), [("plain", ""), ("json", "[]")])
def test_a_t_where_without_a_map_warns_and_prints_nothing_else(
    tools, intervals, output_format, stdout
):
    # t.vect.list and t.vect.univar refuse an empty selection; this tool ends
    # successfully, but says on stderr why there is no output.
    result = tools.t_vect_db_select(
        input=intervals, t_where="start_time > '2030-01-01'", format=output_format
    )

    assert result.stdout.strip() == stdout
    assert result.returncode == 0
    assert "No map of the space time vector dataset <dbs_int" in result.stderr


def test_a_where_without_a_row_prints_the_headers_only(tools, changing):
    # Both maps are read; the tables differ, so both headers are printed.
    assert _lines(tools, input=changing, where="a > 100") == [
        "start_time|end_time|x|y|cat|a|b",
        "start_time|end_time|x|y|cat|a|c",
    ]


def test_the_header_is_printed_again_when_the_table_changes(tools, changing):
    assert _lines(tools, input=changing) == [
        "start_time|end_time|x|y|cat|a|b",
        "2001-01-01 00:00:00|2001-02-01 00:00:00|1|1|1|1|x",
        "2001-01-01 00:00:00|2001-02-01 00:00:00|2|2|2|2|y",
        "start_time|end_time|x|y|cat|a|c",
        "2001-02-01 00:00:00|2001-03-01 00:00:00|1|1|1|5|2.5",
    ]


def test_the_header_is_printed_once_for_equal_tables(tools, changing):
    assert _lines(tools, input=changing, columns="a") == [
        "start_time|end_time|a",
        "2001-01-01 00:00:00|2001-02-01 00:00:00|1",
        "2001-01-01 00:00:00|2001-02-01 00:00:00|2",
        "2001-02-01 00:00:00|2001-03-01 00:00:00|5",
    ]


def test_a_registered_layer_decides_the_table(tools, layers):
    lines = _lines(
        tools, input=layers, columns="a", t_where="start_time < '2001-02-01'"
    )

    assert lines[1:] == [
        "2001-01-01 00:00:00|2001-02-01 00:00:00|101",
        "2001-01-01 00:00:00|2001-02-01 00:00:00|102",
    ]


@pytest.mark.parametrize(
    ("layer", "values"), [(None, [1, 2]), (1, [1, 2]), (2, [101, 102])]
)
def test_the_layer_option_applies_to_a_map_without_a_registered_layer(
    tools, layers, layer, values
):
    options = {} if layer is None else {"layer": layer}

    lines = _lines(
        tools,
        input=layers,
        columns="a",
        t_where="start_time >= '2001-02-01'",
        **options,
    )

    assert lines[1:] == [f"2001-02-01 00:00:00|2001-03-01 00:00:00|{v}" for v in values]


def test_a_registered_layer_wins_over_the_layer_option(tools, layers):
    lines = _lines(
        tools, input=layers, columns="a", t_where="start_time < '2001-02-01'", layer=1
    )

    assert lines[1] == "2001-01-01 00:00:00|2001-02-01 00:00:00|101"


def test_csv_uses_a_comma_by_default(tools, intervals):
    # v.db.select puts text values in double quotes in the csv format.
    lines = _lines(tools, input=intervals, format="csv", where="cat = 1")

    assert lines == [
        "start_time,end_time,x,y,cat,observation,label",
        '2001-03-01 00:00:00,2001-04-01 00:00:00,1,1,1,100,"a"',
        '2001-04-01 00:00:00,2001-05-01 00:00:00,2,1,1,200,"a"',
        '2001-05-01 00:00:00,2001-06-01 00:00:00,3,1,1,300,"a"',
    ]


def test_csv_takes_another_one_character_separator(tools, intervals):
    lines = _lines(
        tools,
        input=intervals,
        format="csv",
        separator=";",
        where="cat = 1",
        columns="label",
    )

    assert lines[:2] == [
        "start_time;end_time;label",
        '2001-03-01 00:00:00;2001-04-01 00:00:00;"a"',
    ]


def test_json_has_one_object_per_row_with_the_times_first(tools, intervals):
    data = json.loads(
        tools.t_vect_db_select(
            input=intervals, format="json", where="cat = 2", columns="observation,label"
        ).stdout
    )

    assert data == [
        {
            "start_time": "2001-03-01 00:00:00",
            "end_time": "2001-04-01 00:00:00",
            "observation": 100,
            "label": "b",
        },
        {
            "start_time": "2001-04-01 00:00:00",
            "end_time": "2001-05-01 00:00:00",
            "observation": 200,
            "label": "b",
        },
        {
            "start_time": "2001-05-01 00:00:00",
            "end_time": "2001-06-01 00:00:00",
            "observation": 300,
            "label": "b",
        },
    ]
    assert list(data[0]) == ["start_time", "end_time", "observation", "label"]


def test_json_of_an_instant_has_a_null_end_time(tools, instants):
    data = json.loads(
        tools.t_vect_db_select(input=instants, format="json", where="cat = 1").stdout
    )

    assert data[0]["end_time"] is None
    assert [row["observation"] for row in data] == [100, 200, 300]


def test_json_keeps_the_columns_of_each_map(tools, changing):
    data = json.loads(tools.t_vect_db_select(input=changing, format="json").stdout)

    assert [sorted(set(row) - {"start_time", "end_time"}) for row in data] == [
        ["a", "b", "cat", "x", "y"],
        ["a", "b", "cat", "x", "y"],
        ["a", "c", "cat", "x", "y"],
    ]
    assert data[2]["c"] == 2.5


def test_json_of_no_map_is_an_empty_list(tools, intervals):
    result = tools.t_vect_db_select(
        input=intervals, format="json", t_where="start_time > '2030-01-01'"
    )

    assert json.loads(result.stdout) == []


def test_the_maps_come_in_the_order_of_their_start_times(tools, nested):
    # dx_2 ends first but starts second.
    assert _lines(tools, input=nested, columns="a") == [
        "start_time|end_time|a",
        "2001-01-01 00:00:00|2001-07-01 00:00:00|1",
        "2001-02-01 00:00:00|2001-03-01 00:00:00|2",
    ]


def test_json_is_indented_by_four_spaces(tools, instants):
    text = tools.t_vect_db_select(
        input=instants, format="json", where="cat = 1", columns="observation"
    ).stdout

    assert text.startswith(
        '[\n    {\n        "start_time": "2004-01-01 00:00:00",\n        "end_time": null,\n'
    )
