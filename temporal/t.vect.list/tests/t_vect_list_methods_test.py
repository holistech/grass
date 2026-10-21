"""Test the listing methods of t.vect.list on datasets of different time layouts

Five datasets of six point maps each (adj_1 to adj_6 and so on; map n has one
point at (n, n)) cover what a series of maps can look like in time: adjacent
months (adjacent), instants (points), intervals with gaps (gaps), intervals
that contain and overlap each other (nested) and a mix of intervals and
instants (mixed). A sixth dataset holds the maps in the opposite order of
time (reversed).

The expected rows are written down from the times of the maps. The maps have
no layer, so the column layer reads None.

The default columns of cols are name, layer, mapset, start_time and end_time;
the methods delta, deltagaps and gran list id, name, layer, mapset, start_time,
end_time, interval_length and distance_from_begin, as the manual shows. Most
tests of these methods name the five columns of cols so that they check the
maps, the gaps and the granules; the lengths have their own tests.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, intervals, make_map, register_stds
from grass.temporal.testing.readback import message
from grass.tools import ToolError

D = datetime

HEADER = "name|layer|mapset|start_time|end_time"
COLUMNS = "name,layer,mapset,start_time,end_time"

POINTS = [D(2001, 1, 1), D(2001, 3, 1), D(2001, 4, 1), D(2001, 5, 1)] + [
    D(2001, 8, 1),
    D(2001, 9, 1),
]
GAPS = [
    (D(2001, 1, 1), D(2001, 4, 1)),
    (D(2001, 5, 1), D(2001, 7, 1)),
    (D(2001, 8, 1), D(2001, 10, 1)),
    (D(2001, 11, 1), D(2002, 1, 1)),
    (D(2002, 2, 1), D(2002, 4, 1)),
    (D(2002, 5, 1), D(2002, 7, 1)),
]
NESTED = [
    (D(2001, 1, 1), D(2001, 7, 1)),
    (D(2001, 2, 1), D(2001, 4, 1)),
    (D(2001, 3, 1), D(2001, 4, 1)),
    (D(2001, 4, 1), D(2001, 6, 1)),
    (D(2001, 5, 1), D(2001, 6, 1)),
    (D(2001, 6, 1), D(2001, 7, 1)),
]
# The fourth and fifth map are registered with the same start and end, which
# makes them instants.
MIXED_REGISTERED = [
    (D(2001, 1, 1), D(2001, 3, 11)),
    (D(2001, 2, 1), D(2001, 4, 1)),
    (D(2001, 3, 1), D(2001, 6, 2)),
    (D(2001, 4, 1), D(2001, 4, 1)),
    (D(2001, 5, 1), D(2001, 5, 1)),
    (D(2001, 6, 1), D(2001, 7, 1)),
]
MIXED = [(start, None if start == end else end) for start, end in MIXED_REGISTERED]
TIMES = {
    "adjacent": intervals(6),
    "points": [(start, None) for start in POINTS],
    "gaps": GAPS,
    "nested": NESTED,
    "mixed": MIXED,
}
PREFIX = {
    "adjacent": "adj",
    "points": "pts",
    "gaps": "gap",
    "nested": "nes",
    "mixed": "mix",
    "reversed": "rev",
}


def _time(moment):
    return "None" if moment is None else moment.strftime("%Y-%m-%d %H:%M:%S")


def _names(scenario):
    return [f"{PREFIX[scenario]}_{number}" for number in range(1, 7)]


def _rows(scenario, separator="|"):
    return [
        separator.join([name, "None", "PERMANENT", _time(start), _time(end)])
        for name, (start, end) in zip(_names(scenario), TIMES[scenario], strict=True)
    ]


@pytest.fixture(scope="module")
def stds(tools):
    """Register the maps of each scenario; the dataset has the scenario's name"""
    registered = {**TIMES, "mixed": MIXED_REGISTERED}
    for scenario, times in registered.items():
        register_stds_of_points(tools, scenario, _names(scenario), times)
    # The same maps in the opposite order of time, to tell the order of the
    # rows from the order of the names.
    register_stds_of_points(
        tools, "reversed", _names("reversed"), list(reversed(intervals(6)))
    )
    tools.t_create(
        type="stvds",
        output="empty",
        temporaltype="absolute",
        title="empty",
        description="no maps",
    )


def register_stds_of_points(tools, dataset, names, times):
    """A dataset of the maps names, the map n has a point at (n, n)"""
    for number, name in enumerate(names, start=1):
        make_map(tools, "vector", name, number)
    register_stds(
        tools,
        "stvds",
        dataset,
        [MapSpec(name, None, *time) for name, time in zip(names, times, strict=True)],
    )


def _lines(tools, **options):
    return tools.t_vect_list(**options).stdout.splitlines()


@pytest.mark.parametrize("scenario", list(TIMES))
def test_cols_is_the_default_and_prints_name_layer_mapset_and_times(
    tools, stds, scenario
):
    expected = [HEADER, *_rows(scenario)]

    assert _lines(tools, input=scenario) == expected
    assert _lines(tools, input=scenario, method="cols") == expected


def _entry(name, start, end):
    """The row of a map, or of a gap if name is None"""
    return "|".join(
        [
            "None" if name is None else name,
            "None",
            "None" if name is None else "PERMANENT",
            _time(start),
            _time(end),
        ]
    )


def _table(entries):
    return [HEADER, *(_entry(*entry) for entry in entries)]


def _maps(scenario):
    return [
        (name, start, end)
        for name, (start, end) in zip(_names(scenario), TIMES[scenario], strict=True)
    ]


@pytest.mark.parametrize("method", ["delta", "deltagaps", "gran"])
def test_the_delta_methods_of_adjacent_intervals_list_the_maps(tools, stds, method):
    assert _lines(tools, input="adjacent", method=method, columns=COLUMNS) == _table(
        _maps("adjacent")
    )


def test_delta_lists_the_maps_of_instants_without_an_end(tools, stds):
    assert _lines(tools, input="points", method="delta", columns=COLUMNS) == _table(
        _maps("points")
    )


def test_deltagaps_of_instants_lists_the_distance_between_two_as_a_gap(tools, stds):
    # Between two instants lies a gap from the first instant to the next one.
    entries = []
    for number, (start, following) in enumerate(
        zip(POINTS, [*POINTS[1:], None], strict=True), 1
    ):
        entries.append((f"pts_{number}", start, None))
        if following is not None:
            entries.append((None, start, following))

    assert _lines(tools, input="points", method="deltagaps", columns=COLUMNS) == _table(
        entries
    )


def test_delta_of_intervals_with_gaps_skips_the_gaps(tools, stds):
    assert _lines(tools, input="gaps", method="delta", columns=COLUMNS) == _table(
        _maps("gaps")
    )


def test_deltagaps_of_intervals_with_gaps_adds_the_gaps(tools, stds):
    maps = _maps("gaps")
    entries = []
    for index, entry in enumerate(maps):
        entries.append(entry)
        if index < 5:
            entries.append((None, entry[2], maps[index + 1][1]))

    assert _lines(tools, input="gaps", method="deltagaps", columns=COLUMNS) == _table(
        entries
    )


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_deltagaps_of_nested_intervals_finds_no_gap(tools, stds):
    # Every map starts before the previous one ends or when it ends.
    assert _lines(tools, input="nested", method="deltagaps", columns=COLUMNS) == _lines(
        tools, input="nested", method="delta", columns=COLUMNS
    )
    assert _lines(tools, input="nested", method="delta", columns=COLUMNS) == _table(
        _maps("nested")
    )


def test_deltagaps_of_mixed_times_puts_gaps_after_instants(tools, stds):
    # mix_4 (an instant on 2001-04-01) lies inside mix_3, so no gap comes
    # before it; the next map starts a month later and a gap follows. mix_5
    # (an instant on 2001-05-01) is followed by a gap of a month.
    maps = _maps("mixed")
    entries = [
        *maps[:4],
        (None, D(2001, 4, 1), D(2001, 5, 1)),
        maps[4],
        (None, D(2001, 5, 1), D(2001, 6, 1)),
        maps[5],
    ]

    assert _lines(tools, input="mixed", method="deltagaps", columns=COLUMNS) == _table(
        entries
    )


def test_gran_of_instants_has_a_row_per_month(tools, stds):
    # The series ends with the instant 2001-09-01, so the last granule starts
    # there.
    entries = [
        ("pts_1", D(2001, 1, 1), D(2001, 2, 1)),
        (None, D(2001, 2, 1), D(2001, 3, 1)),
        ("pts_2", D(2001, 3, 1), D(2001, 4, 1)),
        ("pts_3", D(2001, 4, 1), D(2001, 5, 1)),
        ("pts_4", D(2001, 5, 1), D(2001, 6, 1)),
        (None, D(2001, 6, 1), D(2001, 7, 1)),
        (None, D(2001, 7, 1), D(2001, 8, 1)),
        ("pts_5", D(2001, 8, 1), D(2001, 9, 1)),
        ("pts_6", D(2001, 9, 1), D(2001, 10, 1)),
    ]

    assert _lines(tools, input="points", method="gran", columns=COLUMNS) == _table(
        entries
    )


def test_gran_of_intervals_with_gaps_repeats_a_long_map(tools, stds):
    # The granule is a month; a map names every granule it covers, a month
    # between the maps is a row without a name.
    month = [D(2001 + (index // 12), index % 12 + 1, 1) for index in range(19)]
    covering = {
        "gap_1": range(3),
        "gap_2": range(4, 6),
        "gap_3": range(7, 9),
        "gap_4": range(10, 12),
        "gap_5": range(13, 15),
        "gap_6": range(16, 18),
    }
    owner = {index: name for name, months in covering.items() for index in months}
    entries = [
        (owner.get(index), month[index], month[index + 1]) for index in range(18)
    ]

    assert _lines(tools, input="gaps", method="gran", columns=COLUMNS) == _table(
        entries
    )


@pytest.mark.parametrize("method", ["delta", "deltagaps", "gran"])
def test_the_delta_methods_print_the_lengths_of_the_intervals(tools, stds, method):
    lines = _lines(tools, input="gaps", method=method)

    assert lines[0].split("|")[-2:] == ["interval_length", "distance_from_begin"]


@pytest.mark.parametrize("column", ["interval_length", "distance_from_begin"])
def test_the_columns_of_the_delta_methods_are_refused_by_the_other_methods(
    tools, stds, column
):
    with pytest.raises(ToolError) as error:
        tools.t_vect_list(input="adjacent", method="cols", columns=column)
    assert f"Column '{column}' is not available with the method 'cols'" in message(
        error.value
    )


@pytest.mark.parametrize("method", ["delta", "deltagaps", "gran"])
def test_a_database_column_is_refused_by_the_delta_methods(tools, stds, method):
    with pytest.raises(ToolError) as error:
        tools.t_vect_list(input="adjacent", method=method, columns="north")
    assert f"Column 'north' is not available with the method '{method}'" in message(
        error.value
    )


@pytest.mark.parametrize("method", ["delta", "deltagaps", "gran"])
def test_order_is_refused_by_the_delta_methods(tools, stds, method):
    # The rows are always ordered by the start time, as in t.rast.list.
    with pytest.raises(ToolError) as error:
        tools.t_vect_list(input="reversed", method=method, columns="name", order="name")
    assert (
        f"The option order is not allowed with method={method}. "
        "Values are always ordered by start_time"
    ) in message(error.value)


def test_comma_prints_the_ids_in_one_line(tools, stds):
    ids = [f"{name}@PERMANENT" for name in _names("adjacent")]

    assert _lines(tools, input="adjacent", method="comma") == [",".join(ids)]


def test_the_line_format_prints_the_ids_in_one_line(tools, stds):
    ids = [f"{name}@PERMANENT" for name in _names("adjacent")]

    lines = _lines(tools, input="adjacent", format="line", columns="id", separator="|")

    assert lines == ["|".join(ids)]


def test_the_line_format_uses_a_comma_by_default(tools, stds):
    assert _lines(tools, input="adjacent", format="line", columns="name") == [
        ",".join(_names("adjacent"))
    ]


def test_the_line_format_lists_the_ids_without_columns(tools, stds):
    ids = [f"{name}@PERMANENT" for name in _names("adjacent")]

    assert _lines(tools, input="adjacent", format="line") == [",".join(ids)]


def test_list_with_separator(tools, stds):
    lines = _lines(tools, input="adjacent", separator=" | ")

    assert lines[0] == "name | layer | mapset | start_time | end_time"
    assert lines[1] == (
        "adj_1 | None | PERMANENT | 2001-01-01 00:00:00 | 2001-02-01 00:00:00"
    )


def test_separator_name(tools, stds):
    assert _lines(tools, input="adjacent", separator="tab")[0] == (
        "name\tlayer\tmapset\tstart_time\tend_time"
    )


def test_a_list_without_header(tools, stds):
    lines = _lines(tools, input="adjacent", flags="u")

    assert lines == _rows("adjacent")


def test_a_csv_without_header(tools, stds):
    lines = _lines(tools, input="adjacent", format="csv", flags="u", columns="name")

    assert lines == [f'"adj_{number}"' for number in range(1, 7)]


def test_a_csv_with_another_separator(tools, stds):
    lines = _lines(
        tools, input="adjacent", format="csv", separator=";", columns="id,name"
    )

    assert lines[:2] == ['"id";"name"', '"adj_1@PERMANENT";"adj_1"']


def test_a_csv_of_an_instant_writes_nothing_for_none(tools, stds):
    # csv.writer writes None as an empty string; a text is quoted.
    lines = _lines(tools, input="points", format="csv", columns="name,end_time")

    assert lines[1] == '"pts_1",""'


def test_json_of_an_instant_has_null(tools, stds):
    result = tools.t_vect_list(input="points", format="json").json

    first = result["data"][0]
    assert first["end_time"] is None
    assert first["layer"] is None
    assert result["metadata"]["column_names"] == [
        "name",
        "layer",
        "mapset",
        "start_time",
        "end_time",
    ]


def test_json_ignores_the_comma_method(tools, stds):
    # The format wins: the output is the table of the cols method.
    result = tools.t_vect_list(input="adjacent", method="comma", format="json").json

    assert len(result["data"]) == 6
    assert result["data"][0]["name"] == "adj_1"


def test_where_selects_the_maps_of_the_listing(tools, stds):
    lines = _lines(
        tools, input="adjacent", where="start_time >= '2001-03-01' and name != 'adj_5'"
    )

    assert [line.split("|")[0] for line in lines[1:]] == ["adj_3", "adj_4", "adj_6"]


@pytest.mark.parametrize("method", ["delta", "deltagaps", "gran"])
def test_where_applies_to_the_delta_methods(tools, stds, method):
    lines = _lines(
        tools,
        input="adjacent",
        method=method,
        columns="name",
        where="start_time >= '2001-04-01'",
    )

    assert [line.split("|")[0] for line in lines[1:]] == ["adj_4", "adj_5", "adj_6"]


def test_order_by_name_differs_from_the_order_of_time(tools, stds):
    by_time = _lines(tools, input="reversed", columns="name", flags="u")
    by_name = _lines(tools, input="reversed", columns="name", order="name", flags="u")

    assert by_time == [f"rev_{number}" for number in range(6, 0, -1)]
    assert by_name == [f"rev_{number}" for number in range(1, 7)]


def test_order_by_two_columns(tools, stds):
    # End times: nes_2 and nes_3 end 2001-04-01, nes_4 and nes_5 end
    # 2001-06-01, nes_1 and nes_6 end 2001-07-01; the start time breaks the
    # tie.
    lines = _lines(
        tools, input="nested", columns="name", order="end_time,start_time", flags="u"
    )

    assert lines == [f"nes_{number}" for number in (2, 3, 4, 5, 1, 6)]


ORDER_COLUMNS = [
    "id",
    "name",
    "layer",
    "creator",
    "mapset",
    "temporal_type",
    "creation_time",
    "start_time",
    "end_time",
    "north",
    "south",
    "west",
    "east",
    "points",
    "lines",
    "boundaries",
    "centroids",
    "faces",
    "kernels",
    "primitives",
    "nodes",
    "areas",
    "islands",
    "holes",
    "volumes",
]


@pytest.mark.slow
def test_every_order_column_is_accepted(tools, stds):
    for column in ORDER_COLUMNS:
        lines = _lines(tools, input="adjacent", columns="name", order=column, flags="u")
        assert sorted(lines) == [f"adj_{number}" for number in range(1, 7)], column


@pytest.mark.parametrize("column", ["id", "name", "north", "east"])
def test_order_by_columns_that_differ_between_maps(tools, stds, column):
    # Map n has its point at (n, n), so north and east follow the names; the
    # maps were registered in the opposite order of time.
    lines = _lines(tools, input="reversed", columns="name", order=column, flags="u")

    assert lines == [f"rev_{number}" for number in range(1, 7)]


def test_the_output_goes_to_a_file(tools, stds, tmp_path):
    path = tmp_path / "list.txt"

    result = tools.t_vect_list(input="adjacent", output=str(path), columns="name")

    assert result.stdout == ""
    assert path.read_text().splitlines() == ["name"] + [f"adj_{n}" for n in range(1, 7)]


def test_the_ids_go_to_a_file_as_one_line(tools, stds, tmp_path):
    path = tmp_path / "ids.txt"

    tools.t_vect_list(input="adjacent", format="line", columns="id", output=str(path))

    assert path.read_text() == (
        ",".join(f"adj_{n}@PERMANENT" for n in range(1, 7)) + "\n"
    )


def test_an_empty_dataset_gives_an_empty_json_table(tools, stds):
    result = tools.t_vect_list(input="empty", format="json").json

    assert result["data"] == []


def test_gran_names_the_map_by_the_order_of_the_relations(tools, stds):
    # The granule is a month. A granule takes the maps of the first relation
    # that has one, in the order equal, during, overlaps, overlapped,
    # contains, and the first of them names it. January, February and April
    # lie during nes_1 (January to July); March equals nes_3, May nes_5 and
    # June nes_6. The maps nes_2 and nes_4 are never named: February lies
    # during nes_2 as well, but nes_1 starts first.
    lines = _lines(tools, input="nested", method="gran", columns="name,start_time")

    assert lines == [
        "name|start_time",
        "nes_1|2001-01-01 00:00:00",
        "nes_1|2001-02-01 00:00:00",
        "nes_3|2001-03-01 00:00:00",
        "nes_1|2001-04-01 00:00:00",
        "nes_5|2001-05-01 00:00:00",
        "nes_6|2001-06-01 00:00:00",
    ]
