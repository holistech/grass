"""The algebra core on 3D raster expressions that the classic algebra read the same way

Each expression of SAME is computed and must give maps. DIFFERENT lists the
changed rules with a short form of the item in the list of differences in the
manual and the class of the outcome of the core, which is the class of the
error or "maps". The registered maps are compared as start, end, minimum and
maximum, rounded to 6 significant digits.
"""

import pytest

from grass.temporal.testing import outcomes

SAME = [
    "A + B",
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
# may be none, or the class of the error as differential.outcome() names it.
# A crash of the core then does not pass for a difference.
DIFFERENT = {
    # Where a negative buffer leaves a map no time, the core stops with an
    # error. The classic algebra stores an instant when the end equals the
    # start, and keeps the old time stamp with an error message when the end
    # would precede it. Measured 2026-10-14 with t.rast.algebra -c only; the
    # 3D algebra takes the same classic code path, buff_t() calling
    # temporal_buffer() of the map dataset.
    'buff_t(W, "-1 day")': (
        "Other:ValueError",
        "a negative buffer must leave every map some time (end == start)",
    ),
    'buff_t(A, "-1 day")': (
        "Other:ValueError",
        "a negative buffer must leave every map some time (end < start)",
    ),
    "W {:,contains,r} A": (
        "maps",
        "a selection with r gives one map per related pair",
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


def run(expression, **options):
    """The outcome of the core, with the options of the tool"""
    options = {"register_null": True, **options}
    return outcomes.outcome("raster3d", expression, basename="fb", **options)


def kind(core):
    """The class of the error of the core, or "maps" without an error"""
    return core.get("error", "maps")


@pytest.mark.parametrize("expression", SAME)
def test_the_core_computes_the_expression(series_3d, expression):
    assert kind(run(expression)) == "maps"


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_give_the_listed_outcome(series_3d, expression):
    assert kind(run(expression)) == DIFFERENT[expression][0]


@pytest.mark.parametrize("expression", GRANULARITY_SAME)
def test_granularity_computes_the_expression(series_3d, expression):
    assert kind(run(expression, granularity=True)) == "maps"


@pytest.mark.parametrize("expression", sorted(GRANULARITY_DIFFERENT))
def test_granularity_listed_differences_give_the_listed_outcome(series_3d, expression):
    core = run(expression, granularity=True)
    assert kind(core) == GRANULARITY_DIFFERENT[expression][0]
