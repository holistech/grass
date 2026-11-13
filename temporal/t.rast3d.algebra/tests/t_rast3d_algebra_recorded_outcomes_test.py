"""The algebra core on 3D raster expressions the classic algebra read the same way

Each expression of SAME gives the outcome that the reference implementation
gave (recorded in data/reference_outcomes.json on
2026-11-12; the reference implementation already included the corrections
listed in the changes page, so the values are not those of GRASS 8.5).
DIFFERENT lists the changed rules with a short form of the item in the list of
differences in the manual and the class of the outcome of the core, which is
the class of the error or "maps". The registered maps are compared as start,
end, minimum and maximum, rounded to 6 significant digits.
"""

import json
from pathlib import Path

import pytest

from grass.temporal.testing import outcomes

# "A + B" is tested in t_rast3d_algebra_test.py with the same values and times.
SAME = [
    "A - B - 1",
    "A * 2",
    "A / B",
    "A % 3",
    "abs(A - 3)",
    "A {+,during} W",
    "W {+,contains} A",
    "W {+,contains,u} A",
    "A {:,during} W",
    "A !: Q",
    "A {#,during} W",
    "if(A > 2, A, B)",
    "if(A > 2, A)",
    "A {+,equal|overlap} B",
    "if(td(A) == 1, A)",
    "if(start_day(A) > 2, A, B)",
    'tshift(A, "1 day")',
    # Shrinks the two-day maps of W to one day, so each keeps an interval.
    'buff_t(W, "-12 hours")',
    "merge(A, D)",
    "A[1]",
    "A[-1]",
    "D[0,0,1]",
    "A + map(single)",
]

# Each changed rule with a short form of its item in the list of differences
# in the manual, and what the core gives: "maps" for registered maps, which
# may be none, or the class of the error as outcomes.outcome() names it.
# A crash of the core then does not pass for a difference.
DIFFERENT = {
    # Where a negative buffer leaves a map no time, the core stops with an
    # error. The classic algebra stored an instant when the end equals the
    # start, and kept the old time stamp with an error message when the end
    # would precede it. Measured 2026-10-14 with t.rast.algebra -c only; the
    # 3D algebra took the same classic code path, buff_t() calling
    # temporal_buffer() of the map dataset.
    'buff_t(W, "-1 day")': (
        "Other:ValueError",
        "a negative buffer must leave every map some time (end == start)",
    ),
    'buff_t(A, "-1 day")': (
        "Other:ValueError",
        "a negative buffer must leave every map some time (end < start)",
    ),
    "W {+,contains,r} A": (
        "maps",
        "an operator with r gives each pair its own value",
    ),
    "if({during}, A > 1, W, 0)": ("maps", "one result per conclusion map"),
    "if(A > 2, A, W)": (
        "Other:ValueError",
        "then and else of a map condition need equal time stamps",
    ),
}

# The granularity mode (-g) samples each dataset with the common granularity
# of the expression before the reference and the core compute it.
GRANULARITY_SAME = [
    # W has maps of two days, so that each counts for two days of A.
    "A + W",
    "W * 2",
    "A : W",
    "if(W > 150, A, B)",
    "if(W > 150, A)",
    "A[1] + W",
    # Q starts at noon, so that the common granularity is shorter than a day.
    "A + Q",
    "A + map(single)",
]

GRANULARITY_DIFFERENT = {
    "if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)": (
        "maps",
        "&& binds stronger than ||",
    ),
}


# The outcome that the classic algebra gave for each expression, recorded from
# the reference implementation on 2026-11-12 (grass.temporal.classic as it was
# before its removal, run on the data of the fixture below). Keys are
# "<mode>|<expression>" with the modes same and gran. One file per tool instead
# of a table in the test, because an outcome lists every map with its times
# and values.
RECORDED = json.loads(
    Path(__file__).with_name("data").joinpath("reference_outcomes.json").read_text()
)


def without_names(result):
    """The outcome without the names of the maps

    The reference counted the maps in another order and with gaps, so the
    names differ, as in ``merge(A, D)``.
    """
    if "maps" in result:
        result = {**result, "maps": [[None, *row[1:]] for row in result["maps"]]}
    return result


def run(expression, **options):
    """The outcome of the core, with the options of the tool"""
    options = {"register_null": True, **options}
    return without_names(
        outcomes.outcome("raster3d", expression, basename="fb", **options)
    )


def kind(core):
    """The class of the error of the core, or "maps" without an error"""
    return core.get("error", "maps")


@pytest.mark.parametrize("expression", SAME)
def test_gives_the_recorded_outcome(series_3d, expression):
    core = run(expression)
    assert (
        outcomes.compare("raster3d", expression, RECORDED[f"same|{expression}"], core)
        is None
    )


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_give_the_listed_outcome(series_3d, expression):
    assert kind(run(expression)) == DIFFERENT[expression][0]


@pytest.mark.parametrize("expression", GRANULARITY_SAME)
def test_granularity_gives_the_recorded_outcome(series_3d, expression):
    core = run(expression, granularity=True)
    assert (
        outcomes.compare("raster3d", expression, RECORDED[f"gran|{expression}"], core)
        is None
    )


@pytest.mark.parametrize("expression", sorted(GRANULARITY_DIFFERENT))
def test_granularity_listed_differences_give_the_listed_outcome(series_3d, expression):
    core = run(expression, granularity=True)
    assert kind(core) == GRANULARITY_DIFFERENT[expression][0]
