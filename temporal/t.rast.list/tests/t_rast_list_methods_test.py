"""Test the listing methods of t.rast.list on datasets of different time layouts

Six datasets of six maps each (the maps adj_1 to adj_6 and so on, hold the
value of their number) cover what a series of maps can look like in time: adjacent months (adjacent),
instants (points), intervals with gaps (gaps), intervals that contain and
overlap each other (nested) and a mix of intervals and instants (mixed).

The expected rows are written down from the times of the maps. The lengths
and distances are numbers of days: delta and deltagaps print the length of
the interval of a map and the distance of its start from the start of the
first row. The method gran prints one row per granule, with the extent of the
granule, not of the map that covers it, so a map longer than the granule
appears once per granule. A granule without a map is a row whose id, name
and mapset are None.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    intervals,
    register_stds,
    small_region,
)
from grass.temporal.testing.readback import message, stds_info
from grass.tools import ToolError

# Short names for the dates of the datasets.
D = datetime

DELTA_HEADER = "id|name|mapset|start_time|end_time|interval_length|distance_from_begin"
LIST_HEADER = "name|mapset|start_time|end_time"

ADJACENT = intervals(6)
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
# The fourth and fifth map are registered with the same start and end, which makes
# them time instants.
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
    "adjacent": ADJACENT,
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


def _days(value):
    return "None" if value is None else f"{float(value)}"


def _row(name, start, end, first):
    """The row of delta, deltagaps and gran for a map or a gap

    name is None for a gap. first is the start of the first row.
    """
    length = None if end is None else (end - start).days
    return [
        "None" if name is None else f"{name}@PERMANENT",
        "None" if name is None else name,
        "None" if name is None else "PERMANENT",
        _time(start),
        _time(end),
        _days(length),
        _days((start - first).days),
    ]


def _table(entries, separator="|", header=DELTA_HEADER):
    """Lines of the table for entries, tuples (name, start, end)"""
    first = entries[0][1]
    lines = [header.replace("|", separator)]
    lines.extend(separator.join(_row(*entry, first)) for entry in entries)
    return lines


def _names(scenario):
    return [f"{PREFIX[scenario]}_{number}" for number in range(1, 7)]


def _maps(scenario):
    return [
        (name, start, end)
        for name, (start, end) in zip(_names(scenario), TIMES[scenario], strict=True)
    ]


@pytest.fixture(scope="module")
def stds(tools):
    """Name of the dataset for each of the scenarios, here the scenario's name"""
    small_region(tools, 1, 1)
    for scenario in PREFIX:
        for number, name in enumerate(_names(scenario), start=1):
            tools.r_mapcalc(expression=f"{name} = {number}")
    for scenario, times in {**TIMES, "mixed": MIXED_REGISTERED}.items():
        register_stds(
            tools,
            "strds",
            scenario,
            [
                MapSpec(name, None, *time)
                for name, time in zip(_names(scenario), times, strict=True)
            ],
        )
    # The same maps in the opposite order of time, to tell the order of the
    # rows from the order of the names.
    register_stds(
        tools,
        "strds",
        "reversed",
        [
            MapSpec(name, None, *time)
            for name, time in zip(
                _names("reversed"), reversed(intervals(6)), strict=True
            )
        ],
    )
    tools.t_create(
        type="strds",
        output="empty",
        temporaltype="absolute",
        title="empty",
        description="no maps",
    )
    return {name: name for name in [*TIMES, "reversed", "empty"]}


def _lines(tools, **options):
    return tools.t_rast_list(**options).stdout.splitlines()


@pytest.mark.slow
def test_the_setup_matches_the_layouts(tools, stds):
    # The expectations of gran rely on the granularity the library derives for
    # the series: months for the series of whole months, otherwise days.
    assert stds_info(tools, "strds", "adjacent")["granularity"] == "'1 month'"
    assert stds_info(tools, "strds", "points")["granularity"] == "'1 month'"
    assert stds_info(tools, "strds", "gaps")["granularity"] == "'1 month'"
    assert stds_info(tools, "strds", "mixed")["map_time"] == "mixed"


@pytest.mark.parametrize("method", [None, "list", "cols"])
@pytest.mark.parametrize("scenario", list(TIMES))
def test_list_prints_name_mapset_and_times_by_start(tools, stds, scenario, method):
    # list is the default (None: no method given). The method cols is
    # accepted and does the same as list: the script has no branch of its own
    # for it.
    expected = [LIST_HEADER] + [
        "|".join([name, "PERMANENT", _time(start), _time(end)])
        for name, start, end in _maps(scenario)
    ]

    options = {"method": method} if method else {}
    assert _lines(tools, input=stds[scenario], **options) == expected


@pytest.mark.parametrize("scenario", list(TIMES))
def test_comma_prints_the_ids_in_one_line(tools, stds, scenario):
    ids = [f"{name}@PERMANENT" for name, _, _ in _maps(scenario)]

    assert _lines(tools, input=stds[scenario], method="comma") == [",".join(ids)]


def test_comma_uses_the_separator_between_the_ids(tools, stds):
    ids = [f"{name}@PERMANENT" for name in _names("adjacent")]

    assert _lines(tools, input="adjacent", method="comma", separator=" | ") == [
        " | ".join(ids)
    ]


def test_the_line_format_prints_the_ids_in_one_line(tools, stds):
    ids = [f"{name}@PERMANENT" for name in _names("adjacent")]

    assert _lines(tools, input="adjacent", format="line", separator=" | ") == [
        " | ".join(ids)
    ]


def test_list_with_separator(tools, stds):
    lines = _lines(tools, input="adjacent", separator=" | ")

    assert lines[0] == "name | mapset | start_time | end_time"
    assert lines[1] == "adj_1 | PERMANENT | 2001-01-01 00:00:00 | 2001-02-01 00:00:00"


def test_separator_name(tools, stds):
    lines = _lines(tools, input="adjacent", separator="tab")

    assert lines[0] == "name\tmapset\tstart_time\tend_time"


def test_a_list_without_header(tools, stds):
    lines = _lines(tools, input="adjacent", flags="u")

    assert lines[0] == "adj_1|PERMANENT|2001-01-01 00:00:00|2001-02-01 00:00:00"
    assert len(lines) == 6


def test_a_csv_without_header(tools, stds):
    lines = _lines(tools, input="adjacent", format="csv", flags="u", columns="name")

    assert lines == [f'"adj_{number}"' for number in range(1, 7)]


# The distances of the rows below are counted from the start of the first map:
# 2001-01-01 to 2001-02-01 is 31 days, to 2001-03-01 59, to 2001-04-01 90, to
# 2001-05-01 120, to 2001-06-01 151.
@pytest.mark.parametrize("method", ["delta", "deltagaps"])
def test_delta_of_adjacent_intervals(tools, stds, method):
    assert _lines(tools, input="adjacent", method=method, separator=" | ") == _table(
        _maps("adjacent"), " | "
    )
    # Written out for the first two and the last row:
    lines = _lines(tools, input="adjacent", method=method)
    assert lines[1] == (
        "adj_1@PERMANENT|adj_1|PERMANENT|2001-01-01 00:00:00|"
        "2001-02-01 00:00:00|31.0|0.0"
    )
    assert lines[2].endswith("|2001-02-01 00:00:00|2001-03-01 00:00:00|28.0|31.0")
    assert lines[6].endswith("|2001-06-01 00:00:00|2001-07-01 00:00:00|30.0|151.0")


def test_delta_of_instants_has_no_length_and_no_gaps(tools, stds):
    # Distances: 2001-01-01 to 03-01 is 59 days, to 04-01 90, to 05-01 120,
    # to 08-01 212 (120 + 31 + 30 + 31), to 09-01 243.
    lines = _lines(tools, input="points", method="delta")

    assert [line.split("|")[-2:] for line in lines[1:]] == [
        ["None", "0.0"],
        ["None", "59.0"],
        ["None", "90.0"],
        ["None", "120.0"],
        ["None", "212.0"],
        ["None", "243.0"],
    ]
    assert lines[1].split("|")[3:5] == ["2001-01-01 00:00:00", "None"]


def test_deltagaps_of_instants_lists_every_distance_as_a_gap(tools, stds):
    # Between two instants lies a gap from the first instant to the next one:
    # 59, 31, 30, 92 and 31 days.
    a, b, c, d, e, f = POINTS
    expected = _table(
        [
            ("pts_1", a, None),
            (None, a, b),
            ("pts_2", b, None),
            (None, b, c),
            ("pts_3", c, None),
            (None, c, d),
            ("pts_4", d, None),
            (None, d, e),
            ("pts_5", e, None),
            (None, e, f),
            ("pts_6", f, None),
        ]
    )

    assert _lines(tools, input="points", method="deltagaps") == expected
    assert expected[2].endswith("|2001-01-01 00:00:00|2001-03-01 00:00:00|59.0|0.0")
    assert expected[8].endswith("|2001-05-01 00:00:00|2001-08-01 00:00:00|92.0|120.0")


def test_delta_of_intervals_with_gaps_skips_the_gaps(tools, stds):
    # Lengths 90, 61, 61, 61, 59, 61 days. Distances: 2001-01-01 to 05-01 is
    # 120 days, to 08-01 212, to 11-01 304, to 2002-02-01 396, to 2002-05-01 485.
    lines = _lines(tools, input="gaps", method="delta")

    assert [line.split("|")[-2:] for line in lines[1:]] == [
        ["90.0", "0.0"],
        ["61.0", "120.0"],
        ["61.0", "212.0"],
        ["61.0", "304.0"],
        ["59.0", "396.0"],
        ["61.0", "485.0"],
    ]


def test_deltagaps_of_intervals_with_gaps_adds_the_gaps(tools, stds):
    # Gaps: 30 days from 2001-04-01, 31 from 2001-07-01, 31 from 2001-10-01,
    # 31 from 2002-01-01 and 30 from 2002-04-01.
    maps = _maps("gaps")
    gaps = [(None, maps[i][2], maps[i + 1][1]) for i in range(5)]
    entries = []
    for index, entry in enumerate(maps):
        entries.append(entry)
        if index < 5:
            entries.append(gaps[index])
    expected = _table(entries)

    assert _lines(tools, input="gaps", method="deltagaps") == expected
    assert [line.split("|")[-2:] for line in expected[1:]][1::2] == [
        ["30.0", "90.0"],
        ["31.0", "181.0"],
        ["31.0", "273.0"],
        ["31.0", "365.0"],
        ["30.0", "455.0"],
    ]


def test_delta_of_nested_intervals_follows_the_start_times(tools, stds):
    # Lengths 181, 59, 31, 61, 31 and 30 days, distances 0, 31, 59, 90, 120
    # and 151 days.
    lines = _lines(tools, input="nested", method="delta")

    assert [line.split("|")[-2:] for line in lines[1:]] == [
        ["181.0", "0.0"],
        ["59.0", "31.0"],
        ["31.0", "59.0"],
        ["61.0", "90.0"],
        ["31.0", "120.0"],
        ["30.0", "151.0"],
    ]


def test_deltagaps_of_nested_intervals_finds_no_gap(tools, stds):
    # Every map starts before the previous one ends or when it ends.
    assert _lines(tools, input="nested", method="deltagaps") == _lines(
        tools, input="nested", method="delta"
    )


def test_deltagaps_of_mixed_times_puts_gaps_after_instants(tools, stds):
    # mix_4 (an instant on 2001-04-01) lies inside mix_3, so no gap comes
    # before it; the next map starts a month later and a gap of 30 days
    # follows. mix_5 (instant on 2001-05-01) is followed by a gap of 31 days.
    maps = _maps("mixed")
    entries = [
        maps[0],
        maps[1],
        maps[2],
        maps[3],
        (None, D(2001, 4, 1), D(2001, 5, 1)),
        maps[4],
        (None, D(2001, 5, 1), D(2001, 6, 1)),
        maps[5],
    ]

    assert _lines(tools, input="mixed", method="deltagaps") == _table(entries)
    # Lengths 69 (to 03-11), 59, 93 (to 06-02), instants, 30 days.
    lines = _lines(tools, input="mixed", method="delta")
    assert [line.split("|")[-2:] for line in lines[1:]] == [
        ["69.0", "0.0"],
        ["59.0", "31.0"],
        ["93.0", "59.0"],
        ["None", "90.0"],
        ["None", "120.0"],
        ["30.0", "151.0"],
    ]


def test_gran_of_adjacent_months_is_the_delta_table(tools, stds):
    assert _lines(tools, input="adjacent", method="gran") == _table(_maps("adjacent"))


def test_gran_with_a_longer_granule_names_the_first_map_of_each(tools, stds):
    # Granules [01-01, 03-01), [03-01, 05-01) and [05-01, 07-01) hold two
    # monthly maps each; the row names the first of them.
    entries = [
        ("adj_1", D(2001, 1, 1), D(2001, 3, 1)),
        ("adj_3", D(2001, 3, 1), D(2001, 5, 1)),
        ("adj_5", D(2001, 5, 1), D(2001, 7, 1)),
    ]

    assert _lines(tools, input="adjacent", method="gran", granule="2 months") == (
        _table(entries)
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

    assert _lines(tools, input="points", method="gran") == _table(entries)


def test_gran_of_instants_with_a_longer_granule(tools, stds):
    entries = [
        ("pts_1", D(2001, 1, 1), D(2001, 3, 1)),
        ("pts_2", D(2001, 3, 1), D(2001, 5, 1)),
        ("pts_4", D(2001, 5, 1), D(2001, 7, 1)),
        ("pts_5", D(2001, 7, 1), D(2001, 9, 1)),
        ("pts_6", D(2001, 9, 1), D(2001, 11, 1)),
    ]

    assert _lines(tools, input="points", method="gran", granule="2 months") == _table(
        entries
    )


def test_gran_of_intervals_with_gaps_repeats_a_long_map(tools, stds):
    month = [D(2001 + (index // 12), index % 12 + 1, 1) for index in range(19)]
    # Month index 0 is 2001-01. A map covers its months; gaps are the months
    # between the maps.
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

    assert len(entries) == 18
    assert _lines(tools, input="gaps", method="gran") == _table(entries)


def test_gran_with_a_granule_of_the_length_of_the_maps(tools, stds):
    # Three months: [2001-01-01, 04-01) is gap_1, [04-01, 07-01) holds
    # gap_2, and so on up to 2002-07-01.
    starts = [D(2001, 1, 1), D(2001, 4, 1), D(2001, 7, 1), D(2001, 10, 1)]
    starts += [D(2002, 1, 1), D(2002, 4, 1), D(2002, 7, 1)]
    entries = [
        (name, starts[index], starts[index + 1])
        for index, name in enumerate(_names("gaps"))
    ]

    assert _lines(tools, input="gaps", method="gran", granule="3 months") == _table(
        entries
    )


def test_gran_of_months_from_day_31_counts_from_the_first_map(tools, stds):
    # Granules from 31.01.: each start is 31.01. plus n months, cut to the
    # last day of a shorter month, so [31.01., 28.02.], [28.02., 31.03.] and
    # [31.03., 30.04.]. The maps are equal to the first and the last; the
    # middle one is a gap.
    create_stds(
        tools,
        "strds",
        "month_end",
        [
            MapSpec("eom_1", 1, D(2001, 1, 31), D(2001, 2, 28)),
            MapSpec("eom_3", 3, D(2001, 3, 31), D(2001, 4, 30)),
        ],
    )
    entries = [
        ("eom_1", D(2001, 1, 31), D(2001, 2, 28)),
        (None, D(2001, 2, 28), D(2001, 3, 31)),
        ("eom_3", D(2001, 3, 31), D(2001, 4, 30)),
    ]

    assert _lines(tools, input="month_end", method="gran", granule="1 months") == (
        _table(entries)
    )


@pytest.mark.parametrize(
    ("scenario", "granule", "extents"),
    [
        # nested: granules of three months from 2001-01-01 to 2001-07-01.
        (
            "nested",
            "3 months",
            [("2001-01-01", "2001-04-01", 90, 0), ("2001-04-01", "2001-07-01", 91, 90)],
        ),
        # mixed (intervals and instants): the end of the series is extended by
        # a granule, so the series 2001-01-01 to 2001-07-01 gets a third
        # granule, 2001-07-01 to 2001-10-01.
        (
            "mixed",
            "3 months",
            [
                ("2001-01-01", "2001-04-01", 90, 0),
                ("2001-04-01", "2001-07-01", 91, 90),
                ("2001-07-01", "2001-10-01", 92, 181),
            ],
        ),
    ],
)
def test_gran_extents_for_overlapping_maps(tools, stds, scenario, granule, extents):
    # The extents are those of the granules; which map a granule names is
    # derived in the test below.
    lines = _lines(
        tools,
        input=stds[scenario],
        method="gran",
        granule=granule,
        columns="start_time,end_time,interval_length,distance_from_begin",
    )

    expected = ["start_time|end_time|interval_length|distance_from_begin"] + [
        f"{start} 00:00:00|{end} 00:00:00|{length}.0|{distance}.0"
        for start, end, length, distance in extents
    ]
    assert lines == expected


@pytest.mark.parametrize(
    ("scenario", "names"),
    [
        # nested, granules [Jan, Apr) and [Apr, Jul): nes_1 (Jan to Jul)
        # starts with the first granule and ends with the second, so each
        # granule lies during nes_1; the other maps lie in a granule
        # (contains), which comes later in the search order.
        ("nested", ["nes_1", "nes_1"]),
        # mixed: the first granule overlaps mix_3 (Mar 1 to Jun 2); mix_1 and
        # mix_2 lie in it (contains). The second granule is overlapped by
        # mix_3; the instants and mix_6 lie in it. The third is a gap.
        ("mixed", ["mix_3", "mix_3", "None"]),
    ],
)
def test_gran_names_the_map_by_the_order_of_the_relations(tools, stds, scenario, names):
    # resample_maplist_by_granularity() takes the maps of the first relation
    # of a granule in the order equal, during, overlaps, overlapped,
    # contains, and the first of them names the granule. That holds without
    # a valid topology, too.
    lines = _lines(
        tools, input=stds[scenario], method="gran", granule="3 months", columns="name"
    )

    assert lines == ["name", *names]


def test_the_last_granule_of_mixed_times_is_a_gap(tools, stds):
    lines = _lines(tools, input="mixed", method="gran", granule="3 months")

    assert lines[-1] == (
        "None|None|None|2001-07-01 00:00:00|2001-10-01 00:00:00|92.0|181.0"
    )


def test_a_granule_does_not_change_the_list_method(tools, stds):
    assert _lines(tools, input="adjacent", granule="2 months") == _lines(
        tools, input="adjacent"
    )


@pytest.mark.parametrize("method", ["delta", "deltagaps", "gran"])
def test_where_selects_before_the_delta_is_counted(tools, stds, method):
    # Three maps remain: their distances start at 0 for adj_4.
    lines = _lines(
        tools,
        input="adjacent",
        method=method,
        where="start_time >= '2001-04-01'",
        columns="name,distance_from_begin",
    )

    assert lines == [
        "name|distance_from_begin",
        "adj_4|0.0",
        "adj_5|30.0",
        "adj_6|61.0",
    ]


def test_where_on_the_list_method(tools, stds):
    lines = _lines(
        tools, input="adjacent", where="start_time >= '2001-03-01' and name != 'adj_5'"
    )

    assert [line.split("|")[0] for line in lines[1:]] == ["adj_3", "adj_4", "adj_6"]


def test_where_that_selects_nothing_in_delta_prints_the_header(tools, stds):
    # The list method fails in the same case (see the error tests).
    assert _lines(
        tools, input="adjacent", method="delta", where="start_time > '2030-01-01'"
    ) == [DELTA_HEADER]


def test_order_by_name_differs_from_the_order_of_time(tools, stds):
    by_time = _lines(tools, input="reversed", columns="name", flags="u")
    by_name = _lines(tools, input="reversed", columns="name", order="name", flags="u")

    assert by_time == [f"rev_{number}" for number in range(6, 0, -1)]
    assert by_name == [f"rev_{number}" for number in range(1, 7)]


@pytest.mark.parametrize("column", ["id", "name", "min", "max"])
def test_order_by_columns_that_differ_between_maps(tools, stds, column):
    # rev_i holds i in every cell, so min and max follow the names.
    lines = _lines(tools, input="reversed", columns="name", order=column, flags="u")

    assert lines == [f"rev_{number}" for number in range(1, 7)]


def test_order_by_two_columns(tools, stds):
    # End times: nes_2 and nes_3 end 2001-04-01, nes_4 and nes_5 end
    # 2001-06-01, nes_1 and nes_6 end 2001-07-01; the start time breaks the
    # tie.
    lines = _lines(
        tools, input="nested", columns="name", order="end_time,start_time", flags="u"
    )

    assert lines == [f"nes_{number}" for number in (2, 3, 4, 5, 1, 6)]


@pytest.mark.slow
def test_every_order_column_is_accepted(tools, stds):
    columns = [
        "id",
        "name",
        "semantic_label",
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
        "nsres",
        "ewres",
        "cols",
        "rows",
        "number_of_cells",
        "min",
        "max",
    ]
    for column in columns:
        lines = _lines(tools, input="adjacent", columns="name", order=column, flags="u")
        assert sorted(lines) == [f"adj_{number}" for number in range(1, 7)], column


def test_the_values_of_the_columns(tools, stds):
    # The region is one cell of size 1 at (0, 0): north 1, south 0, west 0,
    # east 1. adj_1 holds 1, so min and max are 1.
    columns = (
        "id,temporal_type,semantic_label,north,south,west,east,nsres,ewres,cols,"
        "rows,number_of_cells,min,max"
    )
    lines = _lines(
        tools,
        input="adjacent",
        columns=columns,
        where="name = 'adj_1'",
    )

    assert lines == [
        columns.replace(",", "|"),
        "adj_1@PERMANENT|absolute|None|1.0|0.0|0.0|1.0|1.0|1.0|1|1|1|1.0|1.0",
    ]


def test_creator_and_creation_time_are_set(tools, stds):
    lines = _lines(
        tools,
        input="adjacent",
        columns="creator,creation_time",
        where="name = 'adj_1'",
    )

    creator, creation_time = lines[1].split("|")
    assert creator
    assert datetime.strptime(creation_time[:19], "%Y-%m-%d %H:%M:%S")


def test_the_output_goes_to_a_file(tools, stds, tmp_path):
    path = tmp_path / "list.txt"

    result = tools.t_rast_list(input="adjacent", output=str(path), columns="name")

    assert result.stdout == ""
    assert path.read_text().splitlines() == ["name"] + [f"adj_{n}" for n in range(1, 7)]


def test_the_ids_go_to_a_file_as_one_line(tools, stds, tmp_path):
    path = tmp_path / "ids.txt"

    tools.t_rast_list(input="adjacent", format="line", output=str(path))

    assert path.read_text() == (
        ",".join(f"adj_{n}@PERMANENT" for n in range(1, 7)) + "\n"
    )


def test_a_csv_of_a_table_with_gaps_writes_nothing_for_none(tools, stds):
    # csv.writer writes None as an empty string; a text is quoted, a number
    # is not (quoting of all non-numeric fields).
    lines = _lines(tools, input="points", method="deltagaps", format="csv")

    assert lines[1] == (
        '"pts_1@PERMANENT","pts_1","PERMANENT","2001-01-01 00:00:00","","",0.0'
    )
    assert lines[2] == '"","","","2001-01-01 00:00:00","2001-03-01 00:00:00",59.0,0.0'


def test_a_csv_with_another_separator(tools, stds):
    lines = _lines(
        tools, input="adjacent", format="csv", separator=";", columns="id,name"
    )

    assert lines[:2] == ['"id";"name"', '"adj_1@PERMANENT";"adj_1"']


def test_json_of_a_table_with_instants_has_null(tools, stds):
    result = tools.t_rast_list(input="points", method="delta", format="json").json

    first = result["data"][0]
    assert first["end_time"] is None
    assert first["interval_length"] is None
    assert first["distance_from_begin"] == 0.0
    assert result["metadata"]["column_names"][0] == "id"


def test_json_ignores_the_comma_method(tools, stds):
    # The format wins: the output is the table of the list method.
    result = tools.t_rast_list(input="adjacent", method="comma", format="json").json

    assert result["metadata"]["column_names"] == [
        "name",
        "mapset",
        "start_time",
        "end_time",
    ]
    assert len(result["data"]) == 6


@pytest.mark.slow
def test_delta_of_an_empty_dataset_prints_the_header_only(tools, stds):
    for method in ("delta", "deltagaps"):
        assert _lines(tools, input="empty", method=method) == [DELTA_HEADER], method
    result = tools.t_rast_list(input="empty", method="delta", format="json").json
    assert result["data"] == []


def test_the_list_of_an_empty_dataset_is_refused(tools, stds):
    with pytest.raises(ToolError) as error:
        tools.t_rast_list(input="empty")

    assert "Nothing found in the database for space time dataset <empty@PERMANENT>" in (
        message(error.value)
    )
    assert "Dataset is empty" in message(error.value)
