"""Comparison of the algebra core with the classic algebra

The outcome of the classic algebra is that of the reference implementation
(grass.temporal.classic), which runs in each test. The registered maps (start,
end, minimum and maximum, rounded to 6 significant digits) must agree, except
for the differences that the manual lists between the core and the releases
before GRASS 8.6. Values are compared rather than r.mapcalc expressions,
because the two write them differently.
"""

import random

import pytest

from grass.temporal.testing import differential

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
# may be none, or the class of the error as differential.outcome() names it.
# A crash of the core then does not pass for a difference.
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
        "Other:ValueError",
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
        "Other:ValueError",
        "a negative buffer must leave every map some time (end == start)",
    ),
    'buff_t(A, "-1 day")': (
        "Other:ValueError",
        "a negative buffer must leave every map some time (end < start)",
    ),
    'buff_t(I, "-1 day")': (
        "Other:ValueError",
        "a negative buffer cannot shrink a time instance",
    ),
    "buff_t(RT, -1)": (
        "Other:ValueError",
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

# The core reads forms that the grammar of the reference has no rule for. Each
# must give what an expression of that grammar gives.
EXTENDED = {
    "A": "A * 1",
    "-A + 10": "10 - A",
    # A / (A - 2) is null for a2, so that the maps differ.
    "isnull(A / (A - 2))": "if(isnull(A / (A - 2)), 1, 0)",
    "isntnull(A / (A - 2))": "if(isntnull(A / (A - 2)), 1, 0)",
}

# The granularity mode (-g) samples each dataset with the common granularity
# of the expression before the reference and the core compute it.
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


def without_names(result):
    """The outcome without the names of the maps

    The reference and the core count the maps in another order, so the names
    differ; the comparison of the core with the classic profile, which this
    test made before, did not read them either.
    """
    if "maps" in result:
        result = {**result, "maps": [[None, *row[1:]] for row in result["maps"]]}
    return result


def run(runner, expression, **options):
    """The outcome of a runner of differential.RUNNERS, without map names"""
    basename = {"reference": "fa", "core": "fb"}[runner]
    options = {"register_null": True, **options}
    return without_names(
        differential.outcome(
            "raster",
            expression,
            differential.RUNNERS[runner],
            basename=basename,
            **options,
        )
    )


def difference(expression, **options):
    """What compare() finds between the reference and the core"""
    reference = run("reference", expression, **options)
    return differential.compare(
        "raster", expression, reference, run("core", expression, **options)
    )


def kind(result):
    """The class of the error of an outcome, or "maps" without an error"""
    return result.get("error", "maps")


@pytest.mark.parametrize("expression", SAME)
def test_same_result(algebra, expression):
    assert difference(expression) is None


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_still_differ(algebra, expression):
    """A listed difference that no longer differs must leave the list"""
    assert difference(expression) is not None
    assert kind(run("core", expression)) == DIFFERENT[expression][0]


@pytest.mark.parametrize(("expression", "equivalent"), EXTENDED.items())
def test_extended_syntax(algebra, expression, equivalent):
    assert kind(run("reference", expression)) == "SyntaxError"
    expected = run("reference", equivalent)
    assert kind(expected) == "maps"
    core = run("core", expression)
    assert differential.compare("raster", expression, expected, core) is None


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
def test_random_expressions(algebra, expression):
    assert difference(expression) is None


def mapcalc_calls(chain):
    return sum(process["name"] == "r.mapcalc" for process in chain["processes"])


@pytest.mark.parametrize("expression", SAME)
def test_one_mapcalc_call_per_map(algebra, expression):
    """The core computes each result map with one r.mapcalc call"""
    chain = algebra.parse(expression, dry_run=True)
    assert mapcalc_calls(chain) == len(chain["register"])


@pytest.mark.parametrize("expression", GRANULARITY_SAME)
def test_granularity_same_result(algebra, expression):
    assert difference(expression, granularity=True) is None


@pytest.mark.parametrize("expression", sorted(GRANULARITY_DIFFERENT))
def test_granularity_listed_differences_still_differ(algebra, expression):
    """A listed difference that no longer differs must leave the list"""
    assert difference(expression, granularity=True) is not None
    core = run("core", expression, granularity=True)
    assert kind(core) == GRANULARITY_DIFFERENT[expression][0]


def test_granularity_with_the_spatial_flag(algebra):
    """The sampled maps keep their spatial extent, so that the spatial
    relation of -s finds them"""
    assert len(run("core", "A + B", granularity=True, spatial=True)["maps"]) == 4
    assert difference("A + B", granularity=True, spatial=True) is None


@pytest.mark.parametrize("expression", GRANULARITY_SAME)
def test_granularity_one_mapcalc_call_per_map(algebra, expression):
    """In the granularity mode, too, the core computes each result map with
    one r.mapcalc call"""
    chain = algebra.parse(expression, dry_run=True, granularity=True)
    assert mapcalc_calls(chain) == len(chain["register"])
