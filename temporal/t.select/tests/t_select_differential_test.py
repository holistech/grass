"""Comparison of the algebra core with the classic algebra for t.select

Both algebras select from the same datasets (conftest.py); the registered
maps (identifier, start day, end day) must agree, except for the differences
listed in the manual between the core and the classic algebra.
"""

import itertools
from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.temporal.algebra.parser import evaluate
from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE
from grass.tools import Tools

DAY0 = datetime(2001, 1, 1)
counter = itertools.count()

SAME = [
    "A : B",
    "A !: B",
    "A {:, during} B",
    "A {:, contains} B",
    "A {:, over} B",
    "A {:,during,l} D",
    "A {:,during,r} D",
    "A {:,overlaps,i} B",
    "A {:,overlaps,u} B",
    "A {:,overlaps,d} B",
    "A : B : D",
    "A {:,equal} B {:,equal} B",
    "if(start_doy(A) > 20, A)",
    "if(start_doy(A) > 20, A, B)",
    "if(A {#, contains} B > 1, A)",
    "if(td(A) == 10, A) : B",
    "if({equal}, A {#, contains} B > 1, A {:, contains} B)",
    "tsnap(A)",
    'A : tshift(B, "5 days")',
    'buff_t(A, "1 days") : B',
    "A : X@other",
    "X@other {:, precedes} A",
]

# Each changed rule with the item of the manual's difference list, and what
# the core gives: "maps" for the registered maps (possibly none) or the name
# of the error, so that a crash does not pass for a difference. The marker is
# the core's outcome, which the test asserts. The mixed-result case, where
# both algebras register maps and only the copy numbers differ, is checked
# separately below, because this comparison cannot see the numbers.
DIFFERENT = {
    # The core reads the neighbourhood modifier A[1] and copies the shifted
    # map; the classic base grammar reports a syntax error.
    "A[1]": ("maps", "the core reads A[1] and A[-1]"),
    # Dataset-type mixing is a core syntax error; the classic base algebra
    # mixes types.
    "strds(A) : stvds(B)": ("SyntaxError", "mixing dataset types needs -c"),
    # A computed result is no selection on the core.
    "A + B": ("ValueError", "t.select selects maps, it computes none"),
}


def selected(session, expression, algebra):
    """The registered maps of a tool run as (identifier without the result
    name, start day, end day), through the subprocess the session chooses"""
    name = f"diff_{algebra}_{next(counter)}"
    env = dict(session.env, **{ALGEBRA_VARIABLE: algebra})
    tools = Tools(session=session, overwrite=True, env=env)
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


@pytest.mark.parametrize("expression", SAME)
def test_same_result(series, expression):
    assert selected(series.session, expression, "core") == selected(
        series.session, expression, "classic"
    )


def outcome(monkeypatch, expression, algebra):
    """The registered maps, None for no dataset, or the name of the error

    The parsers run in this process, so that the error class is visible; the
    core takes evaluate(..., selection=True), the classic algebra the base
    parser, each into its own result dataset.
    """
    monkeypatch.setenv(ALGEBRA_VARIABLE, algebra)
    name = f"diff_{algebra}_{next(counter)}"
    try:
        if algebra == "classic":
            tgis.TemporalAlgebraParser(run=True, debug=False).parse(
                f"{name} = {expression}", "strds", basename=name, overwrite=True
            )
        else:
            evaluate(
                f"{name} = {expression}",
                kind="raster",
                basename=name,
                overwrite=True,
                run=True,
                selection=True,
            )
    except (SyntaxError, ValueError, TypeError, tgis.FatalError) as error:
        return type(error).__name__
    dataset = tgis.dataset_factory("strds", f"{name}@{tgis.get_current_mapset()}")
    return "maps" if dataset.is_in_db() else None


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_still_differ(series, monkeypatch, expression):
    """A listed difference that no longer differs must leave the list"""
    core = outcome(monkeypatch, expression, "core")
    classic = outcome(monkeypatch, expression, "classic")
    assert core != classic
    kind = "maps" if core == "maps" else core
    assert kind == DIFFERENT[expression][0]


def test_mixed_result_copies_are_numbered_differently(series):
    """A result that mixes maps registered unchanged with retimed copies:
    both algebras register the same unchanged maps with the same times, but
    the classic algebra numbers the copies among all result maps, so the copy
    suffixes differ while the maps and their times stay the same"""
    expression = "merge(A {:,during,l} D, A {:,during,r} D)"
    core = selected(series.session, expression, "core")
    classic = selected(series.session, expression, "classic")
    assert sorted((start, end) for _, start, end in core) == sorted(
        (start, end) for _, start, end in classic
    )
    kept_core = [i for i, _, _ in core if not i.startswith("C_")]
    kept_classic = [i for i, _, _ in classic if not i.startswith("C_")]
    assert kept_core == kept_classic == ["a2@PERMANENT", "a3@PERMANENT", "a4@PERMANENT"]
    assert [i for i, _, _ in core if i.startswith("C_")] == [
        "C_1@PERMANENT",
        "C_2@PERMANENT",
        "C_3@PERMANENT",
    ]
    assert [i for i, _, _ in classic if i.startswith("C_")] == [
        "C_4@PERMANENT",
        "C_5@PERMANENT",
        "C_6@PERMANENT",
    ]
