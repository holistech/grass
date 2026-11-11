"""Comparison of the algebra core with the classic algebra for 3D rasters

The outcome of the classic algebra is that of the reference implementation
(grass.temporal.classic), which runs in each test. The registered maps
(start, end, minimum and maximum, rounded to 6 significant digits) must agree,
except for the differences that the manual lists between the core and the
releases before GRASS 8.6.
"""

import pytest

from grass.temporal.testing import differential

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


def without_names(result):
    """The outcome without the names of the maps

    The reference counts the maps in another order and with gaps, so the
    names differ, as in ``merge(A, D)`` (N_0, N_4, N_6 in the reference,
    N_0, N_1, N_5 in the core, seen 11.11.2026). The comparison of the core
    with the classic profile, which this test made before, did not read the
    names either.
    """
    if "maps" in result:
        result = {**result, "maps": [[None, *row[1:]] for row in result["maps"]]}
    return result


def outcomes(expression, **options):
    """The outcomes of the reference and of the core, without map names"""
    options = {"register_null": True, **options}
    return tuple(
        without_names(
            differential.outcome(
                "raster3d",
                expression,
                differential.RUNNERS[runner],
                basename=basename,
                **options,
            )
        )
        for runner, basename in (("reference", "fa"), ("core", "fb"))
    )


def kind(core):
    """The class of the error of the core, or "maps" without an error"""
    return core.get("error", "maps")


@pytest.mark.parametrize("expression", SAME)
def test_same_result(series_3d, expression):
    reference, core = outcomes(expression)
    assert differential.compare("raster3d", expression, reference, core) is None


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_still_differ(series_3d, expression):
    """A listed difference that no longer differs must leave the list"""
    reference, core = outcomes(expression)
    assert differential.compare("raster3d", expression, reference, core) is not None
    assert kind(core) == DIFFERENT[expression][0]


@pytest.mark.parametrize("expression", GRANULARITY_SAME)
def test_granularity_same_result(series_3d, expression):
    reference, core = outcomes(expression, granularity=True)
    assert differential.compare("raster3d", expression, reference, core) is None


@pytest.mark.parametrize("expression", sorted(GRANULARITY_DIFFERENT))
def test_granularity_listed_differences_still_differ(series_3d, expression):
    """A listed difference that no longer differs must leave the list"""
    reference, core = outcomes(expression, granularity=True)
    assert differential.compare("raster3d", expression, reference, core) is not None
    assert kind(core) == GRANULARITY_DIFFERENT[expression][0]
