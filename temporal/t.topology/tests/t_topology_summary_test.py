"""Test the summary that t.topology prints: validity, counts, gaps, relations

Each scenario registers six maps with the times of the former shell tests and
compares the printed summary with values derived from the intervals. The
relations are counted over the pairs of maps, sorted by start time, as the
tool does it: a pair counts once, as the relation of the later map to the
earlier one. GRASS counts the relations "starts" and "finishes" also as
"during" (and their inverses as "contains"), which is how the totals below are
derived; "follows" and "precedes" are counted for maps that touch only, a
map that lies before another one without touching it is not counted.

Months are counted from 2001-01 (0) and days from 2001-01-01.
"""

import re
from io import StringIO

import pytest

from grass.temporal.testing.data import register_file

# Every test makes maps and a dataset with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

ZERO = {
    "Equal": "0",
    "Follows": "0",
    "Precedes": "0",
    "Overlaps": "0",
    "Overlapped": "0",
    "During": "0",
    "Contains": "0",
    "Starts": "0",
    "Started": "0",
    "Finishes": "0",
    "Finished": "0",
}


def _counts(**counts):
    return {**ZERO, **{key: str(value) for key, value in counts.items()}}


def _summary(text):
    """The lines "| Label: .... value" of t.topology as a dict of label to value"""
    values = {}
    for line in text.splitlines():
        match = re.match(r"\s*\|\s*([^:|]+?):[ .]*(.*?)\s*$", line)
        if match and match.group(2):
            values[match.group(1)] = match.group(2)
    return values


def _make_maps(tools, prefix, count=6):
    names = [f"{prefix}_{n}" for n in range(1, count + 1)]
    tools.r_mapcalc(file=StringIO("\n".join(f"{n} = 1" for n in names)))
    return names


# Scenario: id, kind, register options, expected summary.
# Monthly intervals p1 to p6 as registered by start and increment.
ABSOLUTE = [
    pytest.param(
        # [0,1) [1,2) ... [5,6): every map follows the one before.
        {"start": "2001-01-01", "increment": "1 months", "flags": "i"},
        None,
        {
            "Temporal topology is": "valid",
            "Number of points": "0",
            "Number of intervals": "6",
            "Number of gaps": "0",
            "Granularity": "1 month",
            **_counts(Follows=5, Precedes=5),
        },
        id="adjacent_intervals",
    ),
    pytest.param(
        # Six points, one per month, 2001-01-01 to 2001-06-01: no relation,
        # five gaps between the six.
        {},
        [(n, f"2001-{n:02d}-01") for n in range(1, 7)],
        {
            "Temporal topology is": "valid",
            "Number of points": "6",
            "Number of intervals": "0",
            "Number of gaps": "5",
            "Granularity": "1 month",
            **_counts(),
        },
        id="points",
    ),
    pytest.param(
        # Months [0,3) [4,9) [7,9) [10,12) [10,15) [16,18). Map 3 lies in
        # map 2 and ends with it (finishes, also during), map 4 lies in map 5
        # and starts with it (starts, also during). Gaps: 3-4, 9-10, 15-16.
        {},
        [
            (1, "2001-01-01", "2001-04-01"),
            (2, "2001-05-01", "2001-10-01"),
            (3, "2001-08-01", "2001-10-01"),
            (4, "2001-11-01", "2002-01-01"),
            (5, "2001-11-01", "2002-04-01"),
            (6, "2002-05-01", "2002-07-01"),
        ],
        {
            "Temporal topology is": "invalid",
            "Number of points": "0",
            "Number of intervals": "6",
            "Number of gaps": "3",
            "Granularity": "1 month",
            **_counts(
                During=2, Contains=2, Starts=1, Started=1, Finishes=1, Finished=1
            ),
        },
        id="contained_intervals_with_gaps",
    ),
    pytest.param(
        # Months [0,6) [1,3) [2,3) [3,5) [4,5) [5,6). Map 1 contains the maps
        # 2 to 5 strictly and map 6 with a common end; 2/3 and 4/5 end
        # together: three "finishes" (1/6, 2/3, 4/5), seven "during" (the
        # four strict ones and the three that finish). Follows: 2/4, 3/4, 4/6,
        # 5/6.
        {},
        [
            (1, "2001-01-01", "2001-07-01"),
            (2, "2001-02-01", "2001-04-01"),
            (3, "2001-03-01", "2001-04-01"),
            (4, "2001-04-01", "2001-06-01"),
            (5, "2001-05-01", "2001-06-01"),
            (6, "2001-06-01", "2001-07-01"),
        ],
        {
            "Temporal topology is": "invalid",
            "Number of points": "0",
            "Number of intervals": "6",
            "Number of gaps": "0",
            "Granularity": "1 month",
            **_counts(
                Follows=4, Precedes=4, During=7, Contains=7, Finishes=3, Finished=3
            ),
        },
        id="nested_intervals",
    ),
    pytest.param(
        # Days: map 1 [0,69), 2 [31,90), 3 [59,152), points 4 at 90 and 5 at
        # 120, map 6 [151,181). Overlaps: 1/2, 1/3, 2/3, 3/6. Point 4 touches
        # the end of map 2 (follows) and lies in map 3, as does point 5
        # (during). Gaps: 4 to 5 and 5 to 6.
        {},
        [
            (1, "2001-01-01", "2001-03-11"),
            (2, "2001-02-01", "2001-04-01"),
            (3, "2001-03-01", "2001-06-02"),
            (4, "2001-04-01"),
            (5, "2001-05-01"),
            (6, "2001-06-01", "2001-07-01"),
        ],
        {
            "Temporal topology is": "invalid",
            "Number of points": "2",
            "Number of intervals": "4",
            "Number of gaps": "2",
            "Granularity": "1 day",
            **_counts(
                Follows=1, Precedes=1, Overlaps=4, Overlapped=4, During=2, Contains=2
            ),
        },
        id="overlapping_intervals_and_points",
    ),
]


@pytest.mark.parametrize(("options", "rows", "expected"), ABSOLUTE)
def test_absolute_time(tools, prefix, options, rows, expected, tmp_path):
    maps = _make_maps(tools, prefix)
    name = f"{prefix}_ds"
    tools.t_create(output=name, title="t", description="d")
    if rows is None:
        tools.t_register(input=name, maps=",".join(maps), **options)
    else:
        file = register_file(
            tmp_path / "maps.txt", [(maps[n - 1], *rest) for n, *rest in rows]
        )
        tools.t_register(input=name, file=file, **options)

    result = tools.t_topology(input=name)

    summary = _summary(result.stdout)
    assert {key: summary[key] for key in expected} == expected
    assert summary["Is subset of dataset"] == "False"


# Relative time: the same shapes in days and in years (a unit per dataset).
RELATIVE = [
    pytest.param(
        "days",
        {"start": 0, "increment": 1, "flags": "i"},
        None,
        {
            "Temporal topology is": "valid",
            "Number of points": "0",
            "Number of intervals": "6",
            "Number of gaps": "0",
            "Granularity": "1",
            **_counts(Follows=5, Precedes=5),
        },
        id="days_adjacent",
    ),
    pytest.param(
        "days",
        {},
        [
            (1, 1, 4),
            (2, 5, 7),
            (3, 8, 10),
            (4, 11, 12),
            (5, 13, 14),
            (6, 15, 25),
        ],
        {
            # Lengths 3, 2, 2, 1, 1, 10 and gaps of 1 between all: five gaps,
            # nothing touches or overlaps.
            "Temporal topology is": "valid",
            "Number of points": "0",
            "Number of intervals": "6",
            "Number of gaps": "5",
            "Granularity": "1",
            **_counts(),
        },
        id="days_gaps",
    ),
    pytest.param(
        "years",
        {},
        [
            (1, 2001, 2007),
            (2, 2002, 2004),
            (3, 2003, 2004),
            (4, 2004, 2006),
            (5, 2005, 2006),
            (6, 2006, 2007),
        ],
        {
            # As the months of the nested intervals above, one year each.
            "Temporal topology is": "invalid",
            "Number of points": "0",
            "Number of intervals": "6",
            "Number of gaps": "0",
            "Granularity": "1",
            **_counts(
                Follows=4, Precedes=4, During=7, Contains=7, Finishes=3, Finished=3
            ),
        },
        id="years_nested",
    ),
    pytest.param(
        "years",
        {},
        [
            (1, 2001, 2003),
            (2, 2002, 2004),
            (3, 2003, 2006),
            (4, 2004, 2004),
            (5, 2005, 2005),
            (6, 2006, 2007),
        ],
        {
            # Maps 4 and 5 have the same start and end: they are points (the
            # list shows no end). Overlaps 1/2 and 2/3. Follows: 1/3 (2003),
            # 2/4 (point at the end 2004), 3/6 (2006). During: points 4 and 5
            # lie in map 3. Gaps: 4 to 5 and 5 to 6.
            "Temporal topology is": "invalid",
            "Number of points": "2",
            "Number of intervals": "4",
            "Number of gaps": "2",
            "Granularity": "1",
            **_counts(
                Follows=3, Precedes=3, Overlaps=2, Overlapped=2, During=2, Contains=2
            ),
        },
        id="years_overlapping_and_points",
    ),
]


@pytest.mark.parametrize(("unit", "options", "rows", "expected"), RELATIVE)
def test_relative_time(tools, prefix, unit, options, rows, expected, tmp_path):
    maps = _make_maps(tools, prefix)
    name = f"{prefix}_ds"
    tools.t_create(output=name, temporaltype="relative", title="t", description="d")
    if rows is None:
        tools.t_register(input=name, maps=",".join(maps), unit=unit, **options)
    else:
        file = register_file(
            tmp_path / "maps.txt", [(maps[n - 1], *rest) for n, *rest in rows]
        )
        tools.t_register(input=name, file=file, unit=unit, **options)

    result = tools.t_topology(input=name)

    summary = _summary(result.stdout)
    assert {key: summary[key] for key in expected} == expected


def _report(text):
    """The lines of the summary from its first frame line to the last one"""
    lines = text.splitlines()
    return lines[lines.index(SUMMARY_LINES[0]) :]


# The summary of six adjacent monthly intervals, line by line. The counts of
# the time types and of the relations come in the order of the dictionaries of
# the library, the relations in the order of their table in topology.py.
SUMMARY_LINES = [
    " +-------------------- Temporal topology -------------------------------------+",
    " | Is subset of dataset: ...... False",
    " | Temporal topology is: ...... valid",
    " | Number of points: .......... 0",
    " | Number of intervals: ....... 6",
    " | Invalid time stamps: ....... 0",
    " | Number of gaps: ............ 0",
    " | Granularity: ............... 1 month",
    " +-------------------- Topological relations ---------------------------------+",
    " | Equal:...................... 0",
    " | Follows: ................... 5",
    " | Precedes: .................. 5",
    " | Overlaps: .................. 0",
    " | Overlapped: ................ 0",
    " | During: .................... 0",
    " | Contains: .................. 0",
    " | Starts: .................... 0",
    " | Started: ................... 0",
    " | Finishes: .................. 0",
    " | Finished: .................. 0",
    "+----------------------------------------------------------------------------+",
]


def test_the_lines_of_the_summary_and_their_order(tools, prefix):
    maps = _make_maps(tools, prefix)
    name = f"{prefix}_ds"
    tools.t_create(output=name, title="t", description="d")
    tools.t_register(
        input=name,
        maps=",".join(maps),
        start="2001-01-01",
        increment="1 months",
        flags="i",
    )

    result = tools.t_topology(input=name)

    assert _report(result.stdout) == SUMMARY_LINES


def test_an_empty_dataset_in_relative_time_has_no_granularity(tools, prefix):
    name = f"{prefix}_ds"
    tools.t_create(output=name, temporaltype="relative", title="t", description="d")

    result = tools.t_topology(input=name)

    # Without maps the library counts no relation at all (None, not zeros), so
    # the lines of the relations are missing, and its check of the topology
    # takes no counts as invalid.
    assert _report(result.stdout) == [
        *SUMMARY_LINES[:2],
        " | Temporal topology is: ...... invalid",
        " | Number of points: .......... 0",
        " | Number of intervals: ....... 0",
        " | Invalid time stamps: ....... 0",
        " | Number of gaps: ............ 0",
        " | Granularity: ............... None",
        SUMMARY_LINES[8],
        SUMMARY_LINES[-1],
    ]
