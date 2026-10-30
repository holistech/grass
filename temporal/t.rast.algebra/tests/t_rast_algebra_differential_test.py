"""Comparison of the algebra core with the classic algebra

The core and the classic profile compute each expression; the registered maps
(start, end, minimum, maximum) must agree, except for the differences that the
manual lists between the core and the classic algebra. Values are compared
rather than r.mapcalc expressions, because the two write them differently.

The classic profile in turn must give what the earlier implementation of the
classic algebra gives, for every expression of the lists, the differences
included.
"""

import random

import pytest

from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE
from grass.temporal.testing import differential
from grass.temporal.testing.corpus import reference_outcome

# Every test sets the algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

SAME = [
    "A + N",
    "A - N - 1",
    "A * 2",
    "2 * A - 1",
    "A / N",
    "A % 3",
    "float(A) / 2",
    "abs(A - 3)",
    "sqrt(A * A)",
    "A {+,during} B",
    # Each map of A lies in one map of B, so the classic sum over all
    # partners of a map and the sum of the pair agree.
    "A {+,during,r} B",
    "B {+,contains} A",
    "B {+,contains,u} A",
    "B {*,contains,i} A",
    "HB {+,follows|precedes} HA",
    "D : A",
    "A {:,during} B",
    "A {:,during,u} B",
    "A !: C",
    "A {!:,starts} C",
    "B {:,contains} A",
    "A + td(A)",
    "A {#,during} B",
    "A # D",
    "if(A > 2, A, N)",
    "if(A > 2 && A < 4, A, 0)",
    "if(td(A) == 1, A)",
    "if(start_day(A) > 2, A, N)",
    'if(start_date(A) < "2001-01-03", A)',
    "if(td(A) == 1 && A > 2, A, N)",
    "if(A > 2, A)",
    "A {+,equal|overlap} N",
    "if(A {#,during} B + A > 2, A, N)",
    'tshift(A, "1 day")',
    'buff_t(A, "1 day")',
    # Shrinks the two-day maps of B to one day, so each keeps an interval.
    'buff_t(B, "-12 hours")',
    "tsnap(I)",
    # a2 [2,3] and c1 [2,4] start together
    "tsnap(merge(A, C))",
    "merge(A, D)",
    "A[1]",
    "A[-1]",
    "tmap(singletmap) + 1",
    "A + map(singlemap)",
    "A + 1.5e1",
]

# Each changed rule with a short form of its item in the list of differences
# in the manual, and what the core gives: "maps" for registered maps, which
# may be none, or the name of the error. A crash of the core then does not
# pass for a difference.
DIFFERENT = {
    "B {:,contains,r} A": (
        "maps",
        "a selection with r gives one map per related pair",
    ),
    "if({during}, A > 1, B, 0)": ("maps", "one result per conclusion map"),
    "if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)": (
        "maps",
        "&& binds stronger than ||",
    ),
    "if(A > 2, A, D)": (
        "ValueError",
        "then and else of a map condition need equal time stamps",
    ),
    "if(td(I) > 0, I)": ("maps", "td() of a time instance is null"),
    "C {+,contains,r} A": (
        "maps",
        "an operator with r gives each pair its own value",
    ),
    # Where a negative buffer leaves a map no time, the core stops with an
    # error. The classic algebra stores an instant when the end equals the
    # start without a message, and keeps the old time stamp when the end
    # would precede it, printing one ERROR line per map ("End time must be
    # greater than start time ...", exit code 0; measured 2026-10-14).
    'buff_t(B, "-1 day")': (
        "ValueError",
        "a negative buffer must leave every map some time (end == start)",
    ),
    'buff_t(A, "-1 day")': (
        "ValueError",
        "a negative buffer must leave every map some time (end < start)",
    ),
    'buff_t(I, "-1 day")': (
        "ValueError",
        "a negative buffer cannot shrink a time instance",
    ),
    "buff_t(RT, -1)": (
        "ValueError",
        "a negative buffer must leave every map some time (relative time)",
    ),
    # Both maps of HB are such maps, so the core registers none.
    "HB {:,follows|precedes,i} HA": (
        "maps",
        "with i, a map whose partners have no common intersection is left out",
    ),
    # c1 [2,4] is listed before a2 [2,3]; tsnap(merge(A, C)) agrees.
    "tsnap(merge(C, A))": (
        "maps",
        "tsnap() orders maps that start together by their end, not by the list",
    ),
}

# The new grammar reads forms that the classic grammar has no rule for. Each
# must give what an expression of the classic grammar gives.
EXTENDED = {
    "A": "A * 1",
    "-A + 10": "10 - A",
    # A / (A - 2) is null for a2, so that the maps differ.
    "isnull(A / (A - 2))": "if(isnull(A / (A - 2)), 1, 0)",
    "isntnull(A / (A - 2))": "if(isntnull(A / (A - 2)), 1, 0)",
}

# The granularity mode (-g) samples each dataset with the common granularity
# of the expression before both algebras compute it.
GRANULARITY_SAME = [
    # B has maps of two days, so that each counts for two days of A.
    "A + B",
    # A dataset alone keeps its own granularity.
    "B * 2",
    "A : B",
    "B : A",
    # The granules of C start a day after those of A.
    "A + C",
    "HA + HB",
    "A + (A # B)",
    "A + td(B)",
    'if(start_date(B) >= "2001-01-03", A, N)',
    "if(B > 5, A, N)",
    "if(B > 5, A)",
    "A[1] + B",
    # Time instances get one more granule at the end.
    "A + I",
    "A + map(singletmap)",
    "tmap(singletmap) + B",
    # The single map lies on no granule of B, but on one of A.
    "tmap(singletmap) + A",
    "RT * 2",
]

GRANULARITY_DIFFERENT = {
    "if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)": (
        "maps",
        "&& binds stronger than ||",
    ),
}


def outcome(algebra, monkeypatch, expression, parser, **keywords):
    """The registered maps, or the name of the error

    parser is "core" or "classic" (the profile).
    """
    monkeypatch.setenv(ALGEBRA_VARIABLE, parser)
    try:
        rows = algebra.run(expression, f"d{parser}", register_null=True, **keywords)
    except (*algebra.errors, SyntaxError, ValueError, TypeError) as error:
        return type(error).__name__
    return [(row.start, row.end, row.min, row.max) for row in rows]


# The result of the earlier implementation comes from the recorded corpus,
# which stores the form of differential.outcome(), so the profile is read in
# that form as well.
# That form rounds minimum and maximum to 6 significant digits, so this
# comparison is coarser than the one of the core with the profile, which
# outcome() above reads in full.
def profile_difference(expression, **options):
    """What compare() finds between the earlier implementation and -c"""
    options = {"register_null": True, **options}
    reference = reference_outcome("raster", expression, **options)
    profile = differential.outcome(
        "raster", expression, differential.RUNNERS["classic"], basename="fb", **options
    )
    return differential.compare("raster", expression, reference, profile)


@pytest.mark.parametrize("expression", SAME)
def test_same_result(algebra, monkeypatch, expression):
    assert outcome(algebra, monkeypatch, expression, "core") == outcome(
        algebra, monkeypatch, expression, "classic"
    )


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_still_differ(algebra, monkeypatch, expression):
    """A listed difference that no longer differs must leave the list"""
    core = outcome(algebra, monkeypatch, expression, "core")
    assert core != outcome(algebra, monkeypatch, expression, "classic")
    assert ("maps" if isinstance(core, list) else core) == DIFFERENT[expression][0]


@pytest.mark.parametrize(("expression", "equivalent"), EXTENDED.items())
def test_extended_syntax(algebra, monkeypatch, expression, equivalent):
    assert outcome(algebra, monkeypatch, expression, "classic") == "SyntaxError"
    expected = outcome(algebra, monkeypatch, equivalent, "classic")
    assert isinstance(expected, list)
    assert outcome(algebra, monkeypatch, expression, "core") == expected


@pytest.mark.parametrize(
    "expression", [*SAME, *sorted(DIFFERENT), *EXTENDED, *EXTENDED.values()]
)
def test_profile_equals_reference(algebra, expression):
    """-c computes what the earlier implementation of the classic algebra
    computed, also where the core differs and where the classic grammar has no
    rule"""
    assert profile_difference(expression) is None


@pytest.mark.parametrize(
    "expression", [*GRANULARITY_SAME, *sorted(GRANULARITY_DIFFERENT)]
)
def test_granularity_profile_equals_reference(algebra, expression):
    assert profile_difference(expression, granularity=True) is None


RANDOM_DATASETS = ("A", "N", "D", "HA")


def random_expression(generator, depth=0):
    """Arithmetic and selections on datasets of equal intervals, where both
    parsers must agree

    The classic grammar has no rule for a dataset or a number alone, for a
    dataset in parentheses or for abs() of a number (checked 12 October 2026
    by parsing with run=False). The core reads all of them, so such
    expressions would compare a result with a syntax error.
    """
    if depth == 3 or (depth > 0 and generator.random() < 0.3):
        return generator.choice([*RANDOM_DATASETS, str(generator.randint(1, 5))])
    form = generator.choice(
        ["{} + {}", "{} - {}", "{} * {}", "({}) : {}", "abs({}) + {}"]
    )
    left = random_expression(generator, depth + 1)
    right = random_expression(generator, depth + 1)
    if not any(name in left + right for name in RANDOM_DATASETS) or (
        form in {"({}) : {}", "abs({}) + {}"}
        and not any(name in left for name in RANDOM_DATASETS)
    ):
        left = "A"
    if form == "({}) : {}":
        if not any(name in right for name in RANDOM_DATASETS):
            right = "N"
        if left in RANDOM_DATASETS:
            form = "{} : {}"
    return form.format(left, right)


RANDOM = [random_expression(random.Random(seed)) for seed in range(30)]


@pytest.mark.parametrize("expression", RANDOM)
def test_random_expressions(algebra, monkeypatch, expression):
    assert outcome(algebra, monkeypatch, expression, "core") == outcome(
        algebra, monkeypatch, expression, "classic"
    )


@pytest.mark.parametrize("expression", SAME)
def test_no_more_mapcalc_calls(algebra, monkeypatch, expression):
    """The core computes each result map with one r.mapcalc call, and needs
    no more calls than the classic algebra"""

    def chain(parser):
        monkeypatch.setenv(ALGEBRA_VARIABLE, parser)
        return algebra.parse(expression, dry_run=True)

    def calls(processes):
        return sum(process["name"] == "r.mapcalc" for process in processes)

    core = chain("core")
    assert calls(core["processes"]) == len(core["register"])
    assert calls(core["processes"]) <= calls(chain("classic")["processes"])


@pytest.mark.parametrize("expression", GRANULARITY_SAME)
def test_granularity_same_result(algebra, monkeypatch, expression):
    assert outcome(
        algebra, monkeypatch, expression, "core", granularity=True
    ) == outcome(algebra, monkeypatch, expression, "classic", granularity=True)


@pytest.mark.parametrize("expression", sorted(GRANULARITY_DIFFERENT))
def test_granularity_listed_differences_still_differ(algebra, monkeypatch, expression):
    """A listed difference that no longer differs must leave the list"""
    core = outcome(algebra, monkeypatch, expression, "core", granularity=True)
    assert core != outcome(
        algebra, monkeypatch, expression, "classic", granularity=True
    )
    assert ("maps" if isinstance(core, list) else core) == GRANULARITY_DIFFERENT[
        expression
    ][0]


def test_granularity_with_the_spatial_flag(algebra, monkeypatch):
    """The sampled maps keep their spatial extent, so that the spatial
    relation of -s finds them"""
    core = outcome(
        algebra, monkeypatch, "A + B", "core", granularity=True, spatial=True
    )
    assert len(core) == 4
    assert core == outcome(
        algebra, monkeypatch, "A + B", "classic", granularity=True, spatial=True
    )


@pytest.mark.parametrize("expression", GRANULARITY_SAME)
def test_granularity_no_more_mapcalc_calls(algebra, monkeypatch, expression):
    """In the granularity mode, too, the core needs no more r.mapcalc calls
    than the classic algebra"""

    def chain(parser):
        monkeypatch.setenv(ALGEBRA_VARIABLE, parser)
        return algebra.parse(expression, dry_run=True, granularity=True)

    def calls(processes):
        return sum(process["name"] == "r.mapcalc" for process in processes)

    core = chain("core")
    assert calls(core["processes"]) == len(core["register"])
    assert calls(core["processes"]) <= calls(chain("classic")["processes"])
