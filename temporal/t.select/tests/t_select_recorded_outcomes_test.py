"""The algebra core on t.select expressions that the classic algebra read the same way

Each expression of SAME selects the maps that the reference implementation
selected (recorded in data/reference_outcomes.json on
2026-11-12; the reference implementation already included the corrections
listed in the changes page, so the values are not those of GRASS 8.5),
from the datasets of conftest.py. DIFFERENT lists the changed rules with the
item of the manual's list of differences from the releases before GRASS 8.6 and
the outcome of the core.
"""

import itertools
import json
from datetime import datetime
from pathlib import Path

import pytest

import grass.temporal as tgis
from grass.temporal.algebra.parser import evaluate
from grass.temporal.testing import outcomes
from grass.tools import Tools

DAY0 = datetime(2001, 1, 1)
counter = itertools.count()

# An expression whose recorded maps are input maps that t_select_test.py
# already expects by name (and so by time and value) is tested there only.
SAME = [
    "A {:,during,r} D",
    "A {:,overlaps,i} B",
    "A {:,overlaps,u} B",
    "A {:,overlaps,d} B",
    "A : B !: D",
    "A {:,during} B {:,during} D",
    'buff_t(A, "1 days") {:,contains} B',
    'buff_t(A, "1 days") {:,overlaps} B',
    # b2 [22,27) and b9 [28,29) lie inside the shrunk a3 [21,29)
    'buff_t(A, "-1 days") {:,contains} B',
    'buff_t(A, "-1 days") {:,during} D',
]

# Each changed rule with the item of the manual's difference list, and what
# the core gives: "maps" for the registered maps (possibly none) or the name
# of the error, so that a crash does not pass for a difference. The marker is
# the core's outcome, which the test asserts. The mixed-result case, where
# the core and the reference register maps and only the copy numbers differ,
# is checked separately below, because this comparison cannot see the numbers.
DIFFERENT = {
    # The core reads the neighbourhood modifier A[1] and copies the shifted
    # map; the reference reported a syntax error.
    "A[1]": ("maps", "the core reads A[1] and A[-1]"),
    # The core reads the name of a spatial relation, with and without -s; the
    # reference did not know it (see also the test with the flag below).
    "A {:,equal|overlap} B": ("maps", "the core reads spatial relations"),
    # The core reads an expression that is only a dataset, the reference
    # reported a syntax error.
    "A": ("maps", "the core reads a bare dataset"),
    # A computed result is no selection on the core.
    "A + B": ("ValueError", "t.select selects maps, it computes none"),
    # A negative buffer that leaves a map no time is an error on the core;
    # the reference made instants (end == start) without a message or
    # kept the old time (end < start) and printed one ERROR line per map
    # ("End time must be greater than start time ...", exit code 0).
    'buff_t(A, "-5 days") {:,during} D': (
        "ValueError",
        "a negative buffer must leave every map some time",
    ),
    'buff_t(A, "-6 days") {:,during} D': (
        "ValueError",
        "a negative buffer must leave every map some time",
    ),
    # The core refuses a time function as the conclusion of if(); the
    # reference only where its value would be selected. a1, the only map that
    # meets the condition, has no predecessor, so else gives a2 to a4.
    "if(start_doy(A) < 3, start_doy(A, -1), A)": (
        "ValueError",
        "the core refuses a time function as the conclusion of if()",
    ),
}


def selected(session, expression):
    """The registered maps of a tool run as (identifier without the result
    name, start day, end day), through the subprocess the session chooses"""
    name = f"diff_core_{next(counter)}"
    tools = Tools(session=session, overwrite=True)
    tools.t_select(expression=f"{name} = {expression}")
    listing = tools.t_rast_list(
        input=name, columns="id,start_time,end_time", format="json"
    )
    rows = []
    for row in listing["data"]:
        start = (datetime.strptime(row["start_time"], "%Y-%m-%d %H:%M:%S") - DAY0).days
        end = (datetime.strptime(row["end_time"], "%Y-%m-%d %H:%M:%S") - DAY0).days
        rows.append((row["id"].replace(name, "C", 1), start, end))
    return sorted(rows)


def selection_outcome(basename, expression, stdstype="strds", **options):
    """outcomes.outcome() of a selection"""
    return outcomes.outcome(
        "select",
        expression,
        basename=basename,
        stdstype=stdstype,
        **options,
    )


# The outcome that the classic algebra gave for each expression, recorded from
# the reference implementation on 2026-11-12 (grass.temporal.classic as it was
# before its removal, run on the data of the fixture). Keys are "same|<expression>".
RECORDED = json.loads(
    Path(__file__).with_name("data").joinpath("reference_outcomes.json").read_text()
)


@pytest.mark.parametrize("expression", SAME)
def test_the_core_selects_what_the_reference_selected(series, expression):
    core = selection_outcome("fb", expression)
    assert core.get("maps"), "the expression selects no map"
    expected = RECORDED[f"same|{expression}"]
    assert outcomes.compare("select", expression, expected, core) is None


def outcome(expression, spatial=False):
    """The word "maps" for a result dataset, None for none, or the error name

    The parser runs in this process, so that the error class is visible.
    """
    name = f"diff_core_{next(counter)}"
    try:
        evaluate(
            f"{name} = {expression}",
            kind="raster",
            basename=name,
            overwrite=True,
            run=True,
            spatial=spatial,
            selection=True,
        )
    except (SyntaxError, ValueError, TypeError, tgis.FatalError) as error:
        return type(error).__name__
    dataset = tgis.dataset_factory("strds", f"{name}@{tgis.get_current_mapset()}")
    if not dataset.is_in_db():
        return None
    return "maps"


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_give_the_listed_outcome(series, expression):
    assert outcome(expression) == DIFFERENT[expression][0], DIFFERENT[expression][1]


def test_spatial_relation_is_read_by_the_core(series):
    """The core reads the spatial relation and selects maps, with and without
    -s; the classic grammar reported a syntax error for the name"""
    expression = "A {:,equal|overlap} B"
    assert outcome(expression) == "maps"
    assert outcome(expression, spatial=True) == "maps"


def test_right_reference_gives_one_map_per_pair(series):
    """a3 contains b2 and b9: the core registers a map for each pair, the
    classic algebra only the last pair of each map of A (measured 2026-10-14
    on this fixture: 4 maps against 3, the map of b2 missing)"""
    expression = "A {:,contains,r} B"
    core = selected(series.session, expression)
    assert [(start, end) for _, start, end in core] == [
        (0, 4),
        (22, 27),
        (28, 29),
        (35, 40),
    ]


def test_mixed_result_numbers_the_copies_in_time_order(series):
    """A result that mixes maps registered unchanged with retimed copies: the
    unchanged maps keep their names, and the copies are numbered from 1 in the
    time order of the result (the releases before GRASS 8.6 numbered them
    among all result maps, C_4 to C_6 here)"""
    expression = "merge(A {:,during,l} D, A {:,during,r} D)"
    core = selected(series.session, expression)
    assert [i for i, _, _ in core if not i.startswith("C_")] == [
        "a2@PERMANENT",
        "a3@PERMANENT",
        "a4@PERMANENT",
    ]
    assert [i for i, _, _ in core if i.startswith("C_")] == [
        "C_1@PERMANENT",
        "C_2@PERMANENT",
        "C_3@PERMANENT",
    ]
