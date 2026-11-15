"""The algebra core on vector expressions that the classic algebra read the same way

Each expression of SAME gives the outcome that the reference implementation
gave (recorded in data/reference_outcomes.json on
2026-11-12; the reference implementation already included the corrections
listed in the changes page, so the values are not those of GRASS 8.5),
each of REFUSED is a syntax error in both. DIFFERENT lists the changed rules
with a short form of the item in the list of differences in the manual and what
the core gives. The registered maps are compared as identifier, start, end and
the numbers of points, lines and areas.
"""

import json
from pathlib import Path

import pytest

from grass.temporal.testing import outcomes

# An expression whose recorded maps are input maps, or whose outcome
# t_vect_algebra_test.py checks in more detail, is tested there only.
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
    "buff_p(pa, 1)",
    "buff_l(la, 1)",
    "buff_a(aa, 1) & ab",
    "if(td(aa) == 1, aa)",
    "if(start_day(aa) > 1, aa, ab)",
    'tshift(aa, "1 day")',
    # Shrinks the two-day maps of wide to one day, so each keeps an interval.
    'buff_t(wide, "-12 hours")',
    "merge(aa, ac)",
]

# A count is no vector map; the core rejects it as a syntax error
# (test_hash_operator_is_not_a_map_expression in t_vect_algebra_test.py), also
# when the relation finds no pair, as for aa and ab. A number as else is no vector map
# either, also where no map takes the else branch. The classic algebra
# rejected the same expressions.
REFUSED = [
    "aa {#,during} ab",
    "if(td(aa) == 1, aa, null())",
]

# Each changed rule with a short form of its item in the list of differences
# in the manual, and what the core gives: "maps" for registered maps, which
# may be none, or the class of the error as outcomes.outcome() names it.
# A crash of the core then does not pass for a difference.
DIFFERENT = {
    # Where a negative buffer leaves a map no time, the core stops with an
    # error. The classic algebra stored an instant when the end equals the
    # start, and kept the old time stamp with an error message when the end
    # would precede it (measured 2026-10-14 with t.vect.algebra -c, -1 and -6 days).
    'buff_t(wide, "-1 day")': (
        "Other:ValueError",
        "a negative buffer must leave every map some time (end == start)",
    ),
    'buff_t(aa, "-1 day")': (
        "Other:ValueError",
        "a negative buffer must leave every map some time (end < start)",
    ),
    # The classic vector grammar had no neighbour rule and reported a syntax
    # error.
    "aa[1]": ("maps", "the core reads A[1] and A[-1] also for vector datasets"),
    "aa[-1]": ("maps", "the core reads A[1] and A[-1] also for vector datasets"),
    # The classic vector grammar read the hash operator only directly before
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
    # algebra did. Both give no map, which the core registers as an empty
    # dataset and the classic algebra did not create at all.
    "aa {&,equal|overlap} ab": (
        "maps",
        "an empty result creates an empty dataset only in the core",
    ),
}


# The outcome that the classic algebra gave for each expression, recorded from
# the reference implementation on 2026-11-12 (grass.temporal.classic as it was
# before its removal, run on the data of the fixture below). Keys are
# "<mode>|<expression>" with the mode same. One file per tool instead
# of a table in the test, because an outcome lists every map with its times
# and values.
RECORDED = json.loads(
    Path(__file__).with_name("data").joinpath("reference_outcomes.json").read_text()
)


def run(expression):
    """The outcome of the core"""
    return outcomes.outcome("vector", expression, basename="fb")


@pytest.mark.parametrize("expression", SAME)
def test_gives_the_recorded_outcome(vector_series, expression):
    core = run(expression)
    assert (
        outcomes.compare("vector", expression, RECORDED[f"same|{expression}"], core)
        is None
    )


@pytest.mark.parametrize("expression", REFUSED)
def test_the_core_refuses_a_number_as_a_vector_map(vector_series, expression):
    core = run(expression)
    assert core["error"] == "SyntaxError"
    assert (
        outcomes.compare("vector", expression, RECORDED[f"same|{expression}"], core)
        is None
    )


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_give_the_listed_outcome(vector_series, expression):
    kind = run(expression).get("error", "maps")
    assert kind == DIFFERENT[expression][0]
