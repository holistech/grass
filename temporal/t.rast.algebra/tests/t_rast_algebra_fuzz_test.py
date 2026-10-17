"""Differential fuzzing of the algebras for raster maps

Random expressions of the classic grammar (grass.temporal.testing.expressions)
run on two implementations of the algebra, and the registered maps must agree.
Which two is set in one place, DIFFERENTIAL in that module: the earlier
implementation and the classic profile of the core. That must give 0
differences. The test of the listed differences shows that the fuzzer sees one
where there is one: the expressions of the differential test of this directory,
run on the reference and on the core.

The seeds 0 to 199 run in the normal run. GRASS_TEMPORAL_FUZZ_COUNT and
GRASS_TEMPORAL_FUZZ_SEED widen that, see the module docstring of
grass.temporal.testing.expressions. The tests carry slow, because the seeds
cost seconds, and fixed_algebra, because they choose their runners themselves.

Normal run: 48.9 s for 329 tests, measured 2026-10-16 with
`python3 -m pytest -p no:cacheprovider -q <this file>`, including the creation of the
datasets.
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.expressions import (
    RUNNERS,
    accepted_error_pair,
    boundary_forms,
    check_agreement,
    check_difference_seen,
    check_seed,
    compare_runs,
    generate,
    outcome,
    prepare,
    seed_range,
)

KIND = "raster"

pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# Expressions of the differential test of this directory that the reference
# and the core answer differently on the datasets of the fuzzer.
LISTED = [
    "B {:,contains,r} A",
    "if({during}, A > 1, B, 0)",
    "if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)",
    "if(A > 2, A, D)",
    "if(td(I) > 0, I)",
    "C {+,contains,r} A",
    'buff_t(B, "-1 day")',
    'buff_t(A, "-1 day")',
    'buff_t(I, "-1 day")',
    "buff_t(RT, -1)",
    "HB {:,follows|precedes,i} HA",
]


# The same for the granularity mode (-g).
LISTED_GRANULARITY = ["if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)"]
GRANULARITY_SEEDS = range(50)


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    """Create the datasets of the fuzzer, then switch on the test-only caches

    The caches of grass.temporal.testing.fakes serve both runners alike. They
    start after the creation of the datasets, which runs with real IO.
    """
    prepare(KIND, temporal_module_session, tmp_path_factory.mktemp("fuzz"))
    with fakes.cached_io(fakes.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(datasets):
    """Replace the fixture of conftest.py: the caches run through datasets"""


@pytest.mark.parametrize("seed", seed_range())
def test_runners_agree(datasets, seed):
    check_seed(KIND, seed)


@pytest.mark.parametrize("expression", boundary_forms(KIND))
def test_runners_agree_on_boundary_forms(datasets, expression):
    check_agreement(
        KIND,
        expression,
        **({"register_null": True} if KIND in {"raster", "raster3d"} else {}),
    )


@pytest.mark.parametrize("expression", LISTED)
def test_compare_sees_a_listed_difference(datasets, expression):
    check_difference_seen(
        KIND,
        expression,
        **({"register_null": True} if KIND in {"raster", "raster3d"} else {}),
    )


@pytest.mark.parametrize("seed", GRANULARITY_SEEDS)
def test_runners_agree_in_granularity_mode(datasets, seed):
    check_seed(KIND, seed, granularity_share=1.0)


@pytest.mark.parametrize("expression", LISTED_GRANULARITY)
def test_compare_sees_a_listed_difference_in_granularity_mode(datasets, expression):
    check_difference_seen(KIND, expression, register_null=True, granularity=True)


def test_granularity_mode_reaches_the_runner(datasets):
    """The option must not end as an error of the parser, equal on both sides"""
    result = outcome(
        KIND, "A + B", RUNNERS["reference"], basename="fa", granularity=True
    )
    assert result["stds"]
    assert result["maps"]


def test_same_seed_gives_the_same_expression():
    assert generate(KIND, 17) == generate(KIND, 17)
    assert generate(KIND, 17) != generate(KIND, 18)
    assert generate(KIND, 17, granularity_share=1.0)[1]["granularity"]


def test_a_run_error_before_a_syntax_error_is_accepted(datasets):
    """The earlier implementation computes while it parses: end_date() of a
    time instance stops it before it reads the syntax error after it. The
    profile reports the syntax error."""
    expression = 'if(end_date(I) <= "2001-01-01", 3)'
    first = outcome(KIND, expression, RUNNERS["reference"], basename="fa")
    second = outcome(KIND, expression, RUNNERS["classic"], basename="fb")
    assert first["error"] == "FatalError"
    assert second["error"] == "SyntaxError"
    assert accepted_error_pair(KIND, expression, first, second) == (
        "FatalError/SyntaxError"
    )
    assert compare_runs(KIND, expression, first, second) is None


def test_other_pairs_of_errors_are_differences(datasets):
    """Only the pairs of accepted_error_pair() are accepted: a valid
    expression that fails in a module, or exits the process, is a difference
    from another class of error, and so is a syntax error of the profile that
    the earlier implementation does not report without computing"""
    expression = "A + N"
    valid = outcome(KIND, expression, RUNNERS["reference"], basename="fa")
    rejected = {"error": "SyntaxError", "msg": "syntax error"}
    assert "error" not in valid
    assert compare_runs(KIND, expression, valid, rejected) is not None
    fatal = {"error": "FatalError", "msg": "run error"}
    for first, second in (
        ({"error": "Other:CalledModuleError", "msg": ""}, fatal),
        ({"error": "Exit", "msg": ""}, fatal),
        (fatal, {"error": "Other:ValueError", "msg": ""}),
        (fatal, rejected),
    ):
        assert accepted_error_pair(KIND, expression, first, second) is None
        assert compare_runs(KIND, expression, first, second) is not None


def test_a_syntax_error_against_another_fatal_error_is_a_difference(datasets):
    """The profile's FatalError is accepted against a SyntaxError of the
    earlier implementation only if it refuses a dataset of another temporal
    type, not if it refuses to register maps of different types"""
    expression = "A + N"
    syntax = {"error": "SyntaxError", "msg": "syntax error"}
    refusal = {
        "error": "FatalError",
        "msg": "Wrong temporal type of space time dataset <RT@PERMANENT> "
        "<absolute> time is required",
    }
    registration = {
        "error": "FatalError",
        "msg": "Temporal type of space time dataset <Rfa> and its maps are different",
    }
    other = {"error": "FatalError", "msg": "Dataset <A> not found"}
    assert accepted_error_pair(KIND, expression, syntax, refusal) is not None
    for fatal in (registration, other):
        assert accepted_error_pair(KIND, expression, syntax, fatal) is None
        assert compare_runs(KIND, expression, syntax, fatal) is not None


def test_the_crash_on_mixed_time_against_its_refusal_is_accepted(datasets):
    """The earlier implementation crashes while tsnap() orders the maps of
    absolute and relative time that merge() put into one list; the profile
    refuses to register that list, as the earlier implementation does
    without tsnap()"""
    expression = "tsnap(merge(tmap(sinst), RT))"
    first = outcome(KIND, expression, RUNNERS["reference"], basename="fa")
    second = outcome(KIND, expression, RUNNERS["classic"], basename="fb")
    plain = outcome(KIND, "merge(tmap(sinst), RT)", RUNNERS["reference"], basename="fc")
    assert first["error"] == "Other:TypeError"
    assert second["error"] == "FatalError"
    assert plain["error"] == "FatalError"
    assert accepted_error_pair(KIND, expression, first, second) == (
        "Other:TypeError/FatalError"
    )
    assert compare_runs(KIND, expression, first, second) is None


def test_a_type_error_against_another_fatal_error_is_a_difference(datasets):
    """A TypeError of the earlier implementation is accepted only against the
    refusal to register maps of different temporal types, and only if it is
    the crash of an ordering"""
    expression = "A + N"
    crash = {
        "error": "Other:TypeError",
        "msg": "# not supported between instances of # and #",
    }
    registration = {
        "error": "FatalError",
        "msg": "Temporal type of space time dataset # and its maps are different",
    }
    other_crash = {"error": "Other:TypeError", "msg": "unsupported operand type(s)"}
    other_fatal = {"error": "FatalError", "msg": "Dataset <A> not found"}
    assert accepted_error_pair(KIND, expression, crash, registration) is not None
    for first, second in ((crash, other_fatal), (other_crash, registration)):
        assert accepted_error_pair(KIND, expression, first, second) is None
        assert compare_runs(KIND, expression, first, second) is not None
