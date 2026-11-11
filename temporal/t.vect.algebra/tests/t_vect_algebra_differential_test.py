"""Comparison of the algebra core with the classic algebra for vector maps

The outcome of the classic algebra is that of the reference implementation
(grass.temporal.classic), which runs in each test. The registered maps
(identifier, start, end and the numbers of points, lines and areas) must
agree, except for the differences that the manual lists between the core and
the releases before GRASS 8.6.
"""

import pytest

from grass.temporal.testing import differential

SAME = [
    "aa & ab",
    "aa | ab",
    "aa ^ ab",
    "aa ~ ab",
    "aa + ab",
    "aa & ab | ac",
    "aa {&,equal} ab",
    "aa {|,during} wide",
    "wide {|,contains} aa",
    "aa : ab",
    "aa {:,during} wide",
    "aa !: wide",
    "buff_p(pa, 1)",
    "buff_l(la, 1)",
    "buff_a(aa, 1) & ab",
    "if(td(aa) == 1, aa)",
    "if(start_day(aa) > 1, aa, ab)",
    'tshift(aa, "1 day")',
    # Shrinks the two-day maps of wide to one day, so each keeps an interval.
    'buff_t(wide, "-12 hours")',
    "merge(aa, ac)",
    # A count is no vector map; both algebras reject it as a syntax error,
    # also when the relation finds no pair, as for aa and ab.
    "aa {#,during} wide",
    "aa {#,during} ab",
    # A number as else is no vector map either, also where no map takes the
    # else branch.
    "if(td(aa) == 1, aa, null())",
]

# Each changed rule with a short form of its item in the list of differences
# in the manual, and what the core gives: "maps" for registered maps, which
# may be none, or the class of the error as differential.outcome() names it.
# A crash of the core then does not pass for a difference.
DIFFERENT = {
    # Where a negative buffer leaves a map no time, the core stops with an
    # error. The classic algebra stores an instant when the end equals the
    # start, and keeps the old time stamp with an error message when the end
    # would precede it (measured 2026-10-14 with t.vect.algebra -c, -1 and -6 days).
    'buff_t(wide, "-1 day")': (
        "Other:ValueError",
        "a negative buffer must leave every map some time (end == start)",
    ),
    'buff_t(aa, "-1 day")': (
        "Other:ValueError",
        "a negative buffer must leave every map some time (end < start)",
    ),
    "aa {:,contains} wide": ("maps", "an empty result creates an empty dataset"),
    # wide1 contains aa1 and aa2, which do not overlap, so that the
    # intersection with both has no primitives. The classic algebra
    # registers that map empty.
    "wide {&,contains} aa": (
        "maps",
        "a vector map without primitives is not registered",
    ),
    # The classic vector grammar has no neighbour rule and reports a syntax
    # error.
    "aa[1]": ("maps", "the core reads A[1] and A[-1] also for vector datasets"),
    "aa[-1]": ("maps", "the core reads A[1] and A[-1] also for vector datasets"),
    # The classic vector grammar reads the hash operator only directly before
    # a comparison.
    "if(aa {#,during} wide + 1 > 1, aa)": (
        "maps",
        "the hash operator may stand in arithmetic within a condition",
    ),
    "wide {:,contains,r} aa": (
        "maps",
        "a selection with r gives one map per related pair",
    ),
    "wide {&,contains,r} aa": (
        "maps",
        "an overlay with r gives each pair its own overlay",
    ),
    # The core reads the name of a spatial relation without -s, as the classic
    # algebra does. Both give no map, which the core registers as an empty
    # dataset and the classic algebra does not create at all.
    "aa {&,equal|overlap} ab": (
        "maps",
        "an empty result creates an empty dataset only in the core",
    ),
}


def outcomes(expression):
    """The outcomes of the reference and of the core"""
    reference = differential.outcome(
        "vector", expression, differential.RUNNERS["reference"], basename="fa"
    )
    core = differential.outcome(
        "vector", expression, differential.RUNNERS["core"], basename="fb"
    )
    return reference, core


@pytest.mark.parametrize("expression", SAME)
def test_same_result(vector_series, expression):
    reference, core = outcomes(expression)
    assert differential.compare("vector", expression, reference, core) is None


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_still_differ(vector_series, expression):
    """A listed difference that no longer differs must leave the list"""
    reference, core = outcomes(expression)
    assert differential.compare("vector", expression, reference, core) is not None
    kind = core.get("error", "maps")
    assert kind == DIFFERENT[expression][0]
