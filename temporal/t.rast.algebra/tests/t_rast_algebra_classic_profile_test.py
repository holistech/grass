"""The classic profile of the algebra core against the classic algebra

Each expression runs on the classic profile (``CLASSIC``, what ``-c`` runs)
and is compared with the outcome of the classic algebra of the parser
classes, the reference, that grass.temporal.testing.corpus holds. The
registered maps (name, start, end, minimum, maximum) or the
class of the error must be equal. The expressions are the hard cases of the
classic algebra: the rules in which it differs from the core, and the
borders of its grammar.
"""

import pytest

import grass.temporal as tgis
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.differential import RUNNERS, compare, outcome

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

EXPRESSIONS = [
    "if({during}, A > 1, B, 0)",
    "if({contains}, B > 5, A)",
    "if({during}, A > 1, B)",
    "if({equal|during}, A > 1, B, D)",
    "B {:,contains,r} A",
    "B {:,contains,u} A",
    "B {:,contains,i} A",
    "C {+,contains,r} A",
    "C {+,contains,i} A",
    "B {-,contains} A",
    "B {%,contains} A",
    "HB {:,follows|precedes,i} HA",
    "HB {:,precedes|follows,i} HA",
    "HB {+,follows|precedes,i} HA",
    "HB {+,precedes|follows,i} HA",
    "HB {+,follows|precedes,u} HA",
    "HB {+,follows|precedes,d} HA",
    "if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)",
    "if(start_day(A) == 1 || start_day(A) == 2 && start_day(A) == 2, A)",
    "if(A > 1 || A < 3 && A > 2, A)",
    "if(A > 2 || td(A) == 1 && A < 2, A, 0)",
    "if(A > 2, A)",
    "if(A > 2, A, D)",
    "if(A > 2, A, B)",
    "if(A > 2, 7)",
    "if(A > 2, null())",
    "if(A > 2, 1, 0)",
    "if(A > 2, A, A * 10)",
    "A {+,equal|overlap} N",
    'buff_t(A, "-1 day")',
    'buff_t(B, "-1 day")',
    'buff_t(I, "-1 day")',
    "buff_t(RT, -1)",
    'buff_t(B, "-12 hours")',
    "if(td(I) > 0, I)",
    "E + td(E)",
    "B {#,contains} A",
    "B {#,contains,r} A",
    "merge(A, A)",
    "merge(A {:,during} B, A {:,during} C)",
    "merge(D, A)",
    "if(E > 2, E, null())",
    "if(tmap(sinst) > 50, E, null())",
    "E + E",
    "E {+,equal} I",
    "if({contains}, td(B) == 2, A)",
    "if({contains}, td(B) == 2, A, N)",
    "if({during}, td(A) == 1, B, C)",
    "if({equal|during}, start_day(A) < 3, B, D)",
    "if(A {#,during} B + A > 2, A, N)",
    "A[1] + A[-1]",
    "if(A[-1] > 1, A)",
    "if(A > 0.0 && A[-1] > 0.0, start_doy(A, -1), 0)",
    'tshift(A, "1 day") + A',
    "tsnap(I) + 1",
    "A {*,during,u} B",
    "A {/,during,l} B",
    "(A + N) {*,during,r} B",
    "A : B {+,contains} A",
    "A {!:,during,r} B",
    "D !: A",
    "if(A > 1 && A < 4, A + N, A - N)",
    'if(start_date(A) < "2001-01-03", A, N)',
    'if(start_date(A) < "2001-01-03", A, 0)',
    "if(start_doy(A) > 2, A, 5)",
    "if(td(A) == 1, 3, 4)",
    "abs(A - 3) + A {+,during} B",
    "1 + 2 + A",
    "A - 1",
    "A-1",
    "if(isnull(A), 1, 0)",
    "if(exist(A), A)",
    "if(A {&&,during} B > 5, A)",
    "if(A > 1 {||,during} B > 5, A)",
    "if(A > 1 {&&,during,|} B > 5, A, 0)",
    "A {+,equal|equal} N",
    "A {+,during|starts} B",
    "B {-,contains|started|finished} A",
    "SA {+,equal} SB",
    "SA + SB",
    "if(SA > 0, SB)",
    "RT !: RT",
    "if(A > 2 && B > 2, A)",
    "merge(A, D)",
    "rel + 1",
    "rel[1]",
    "tsnap(rel)",
    "A + 3000000000",
    'tshift(A, "1days")',
]

SPATIAL = [
    "A * 2",
    "SA * 2",
    "SA {+,equal} SB",
    "SA : SB",
]


def both(expression, **options):
    """The outcomes of the reference and of the profile"""
    options = {"register_null": True, **options}
    reference = reference_outcome("raster", expression, **options)
    profile = outcome(
        "raster", expression, RUNNERS["classic"], basename="fb", **options
    )
    return reference, profile


@pytest.mark.parametrize("expression", EXPRESSIONS)
def test_profile_equals_reference(algebra, expression):
    reference, profile = both(expression)
    assert compare("raster", expression, reference, profile) is None


@pytest.mark.parametrize("expression", SPATIAL)
def test_profile_equals_reference_spatial(algebra, large_region, expression):
    reference, profile = both(expression, spatial=True)
    assert compare("raster", expression, reference, profile) is None


def test_comparison_sees_a_different_result(algebra):
    """Negative test: compare() reports two expressions that differ"""
    reference, _ = both("A + N")
    _, profile = both("A - N")
    assert compare("raster", "A + N", reference, profile) is not None


# The increment of a time shift or buffer is truncated to whole units on
# relative time and refused on others, and an empty list passes any increment.
INCREMENTS = [
    "buff_t(RT, 1.5)",
    "tshift(RT, 1.5)",
    "tshift(RT, 2)",
    "buff_t(A, 1.5)",
    "tshift(A, 1.5)",
    'buff_t(RT, "1 day")',
    'tshift(RT, "1 day")',
    'tshift(A, "1 DAY")',
    'tshift(A, "1 d")',
    'tshift(A, "3 onth")',
    'buff_t(A, "1 d")',
    "buff_t(A, 5)",
    "tshift(A, 2)",
    "tshift(D !: D, 2)",
    'tshift(D !: D, "1 DAY")',
    "buff_t(D !: D, 2)",
    'buff_t(D !: D, "1 d")',
    'buff_t(RT !: RT, "1 day")',
    "tshift(RT !: RT, 1.5)",
    "tsnap(D !: D)",
]

# In the granularity mode every dataset is sampled with the common
# granularity first; maps without partner of a relation stay in the list.
GRANULARITY = [
    "A + B",
    "A + N",
    "A {+,during} B",
    "B {+,contains} A",
    "A : B",
    "A : D",
    "A !: C",
    "A {:,during,u} B",
    "D {:,equal|follows} A",
    "A # D",
    "if(A > 2, A, N)",
    "if({during}, A > 1, B)",
    "if(td(A) == 1, A)",
    'tshift(A, "1 day") + N',
    "tsnap(I)",
    "merge(A, D)",
]


@pytest.mark.parametrize("expression", INCREMENTS)
def test_increments_equal_reference(algebra, expression):
    reference, profile = both(expression)
    assert compare("raster", expression, reference, profile) is None


@pytest.mark.parametrize("expression", GRANULARITY)
def test_granularity_mode_equals_reference(algebra, expression):
    reference, profile = both(expression, granularity=True)
    assert compare("raster", expression, reference, profile) is None


def test_the_increment_tests_see_results_and_errors(algebra):
    """The expressions above cover both: maps and a refused increment"""
    refused = both('tshift(A, "1 DAY")')[0]
    kept = both("buff_t(RT, 1.5)")[0]
    assert refused["error"] == "SyntaxError"
    assert len(kept["maps"]) == 3


@pytest.mark.parametrize(
    "expression", ['buff_t(RT, "1 day")', "buff_t(A, 5)", 'tshift(A, "1 DAY")']
)
def test_a_refused_increment_leaves_no_dataset(algebra, expression):
    """The reference and the profile both stop before a dataset exists"""
    exists = {}
    for name in ("reference", "classic"):
        result = f"Rx{name}"
        dataset = tgis.dataset_factory("strds", f"{result}@PERMANENT")
        if dataset.is_in_db():
            dataset.delete()
        with pytest.raises(SyntaxError):
            RUNNERS[name](
                "raster",
                f"{result} = {expression}",
                basename=f"x{name}",
                overwrite=True,
                run=True,
                debug=False,
            )
        exists[name] = dataset.is_in_db()
    assert exists == {"reference": False, "classic": False}
