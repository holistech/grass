"""Comparison of the algebra core with the classic algebra

Both algebras compute each expression; the registered maps (start, end,
minimum, maximum) must agree, except for the differences that the manual
lists between the core and the classic algebra. Values are compared rather
than r.mapcalc expressions, because the two parsers parenthesize and quote
differently.
"""

import random

import pytest

from grass.temporal.temporal_raster_algebra import ALGEBRA_VARIABLE


def unreadable_for_classic(expression):
    """An expression that only the core reads

    The classic grammar has no rule for it, and no listed difference covers
    that; it stays expected to fail until it is decided how such expressions
    are compared.
    """
    return pytest.param(
        expression,
        marks=pytest.mark.xfail(
            strict=True,
            reason="undecided: the classic algebra cannot read this syntax",
        ),
    )


SAME = [
    unreadable_for_classic("A"),
    "A + N",
    "A - N - 1",
    "A * 2",
    "2 * A - 1",
    "A / N",
    "A % 3",
    unreadable_for_classic("-A + 10"),
    "float(A) / 2",
    "abs(A - 3)",
    "sqrt(A * A)",
    unreadable_for_classic("isnull(A)"),
    unreadable_for_classic("isntnull(A)"),
    unreadable_for_classic("exist(A)"),
    "A {+,during} B",
    "A {+,during,r} B",
    "B {+,contains} A",
    "B {+,contains,u} A",
    "B {*,contains,i} A",
    "HB {+,follows|precedes} HA",
    "A : B",
    "A {:,during} B",
    "A {:,during,u} B",
    "A !: C",
    "A {!:,during} B",
    "B {:,contains} A",
    "A + td(A)",
    "A {#,during} B",
    "if(A > 2, A, N)",
    "if(A > 2 && A < 4, A, 0)",
    "if(td(A) == 1, A)",
    "if(start_day(A) > 2, A, N)",
    'if(start_date(A) < "2001-01-03", A)',
    "if(td(A) == 1 && A > 2, A, N)",
    "if(A # B == 2, A)",
    'tshift(A, "1 day")',
    'buff_t(A, "1 day")',
    "tsnap(I)",
    "merge(A, D)",
    "A[1]",
    "A[-1]",
    "tmap(singletmap) + 1",
    "A + map(singlemap)",
    "A + 1.5e1",
]

# Each changed rule with the manual section that describes it.
DIFFERENT = {
    "B {:,contains,r} A": "a selection with r gives one map per related pair",
    "if(A > 2, A)": "an if without else is null where a map condition is false",
    "if({during}, A > 1, B)": "one result per conclusion map",
    "if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)": "&& binds stronger than ||",
    "if(A > 2, A, D)": "then and else of a map condition need equal time stamps",
    "if(td(I) > 0, I)": "td() of a time instance is null",
}


def outcome(algebra, monkeypatch, expression, parser):
    """The registered maps, or the name of the error"""
    monkeypatch.setenv(ALGEBRA_VARIABLE, parser)
    try:
        rows = algebra.run(expression, f"d{parser}", register_null=True)
    except (*algebra.errors, SyntaxError, ValueError, TypeError) as error:
        return type(error).__name__
    return [(row.start, row.end, row.min, row.max) for row in rows]


@pytest.mark.parametrize("expression", SAME)
def test_same_result(algebra, monkeypatch, expression):
    assert outcome(algebra, monkeypatch, expression, "core") == outcome(
        algebra, monkeypatch, expression, "classic"
    )


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_still_differ(algebra, monkeypatch, expression):
    """A listed difference that no longer differs must leave the list"""
    assert outcome(algebra, monkeypatch, expression, "core") != outcome(
        algebra, monkeypatch, expression, "classic"
    )


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
    """The core computes each result map with one r.mapcalc call"""

    def calls(parser):
        monkeypatch.setenv(ALGEBRA_VARIABLE, parser)
        chain = algebra.parse(expression, dry_run=True)
        return sum(process["name"] == "r.mapcalc" for process in chain["processes"])

    assert calls("core") <= calls("classic")
