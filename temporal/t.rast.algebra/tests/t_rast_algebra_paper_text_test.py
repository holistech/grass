"""Statements of the text of the paper that introduced the algebra

Gebbert, Leppelt and Pebesma (2019): A Topology Based Spatio-Temporal Map
Algebra for Big Data Analysis. Data 4(2), 86. t_rast_algebra_published_test.py
and t_rast_algebra_paper_test.py check the printed expressions and figures;
the tests here check the rules the text states without a figure, and the
functions of the tables of Appendix B that no other test shows doing what the
table says. Each docstring names the place in the paper; the expected values
are derived by hand in the docstring or a comment.

The datasets are those of the fixture algebra (daily maps of January 2001)
in conftest.py.
"""

import datetime

import pytest

from grass.temporal.algebra.parser import evaluate
from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE

# Every test runs on the algebra core, whatever GRASS_TEMPORAL_ALGEBRA says,
# see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra


@pytest.fixture(autouse=True)
def core(monkeypatch):
    """Run the public parser of the fixtures on the algebra core"""
    monkeypatch.setenv(ALGEBRA_VARIABLE, "core")


def days(first, *values):
    """Daily maps of January 2001 from day first on, as (start, end, value)"""
    return [(day, day + 1, value) for day, value in enumerate(values, first)]


def test_sum_of_equal_timestamps(algebra):
    """Section 3.1.1: C = A + B sums the maps of A and B with equal time stamps

    A has a1..a4 = 1..4 and N n1..n4 = 11..14 on the days 1 to 4: 1 + 11,
    2 + 12, 3 + 13, 4 + 14. D has d1..d3 = 8..10 on the days 3 to 5; only d1
    and d2 have the time of a map of A: 3 + 8 and 4 + 9 on the days 3 and 4.
    """
    assert algebra.triples("A + N") == days(1, 12, 14, 16, 18)
    assert algebra.triples("A + D") == days(3, 11, 13)


@pytest.mark.parametrize(
    ("long", "short", "expected"),
    [
        # n >= 4a: 11 >= 4, 12 >= 8, 13 >= 12 hold, 14 >= 16 does not, so
        # the then part n on the days 1 to 3 and the else part a on day 4.
        ("if(N {>=,equals,l} A * 4, N, A)", "if(N >= A * 4, N, A)", [11, 12, 13, 4]),
        # a > 1 is false on day 1, n < 14 is false on day 4: the then part a
        # on the days 2 and 3, the else part n on the days 1 and 4.
        (
            "if(A > 1 {&&,equals,&,l} N < 14, A, N)",
            "if(A > 1 && N < 14, A, N)",
            [11, 2, 3, 14],
        ),
    ],
    ids=[">=", "&&"],
)
def test_short_comparison_form(algebra, long, short, expected):
    """Section 3.2.1: {>=, equals, l} -> >= and {&&, equals, &, l} -> &&

    The short form of the comparison and of the logical operator gives the
    maps of the printed long form, values and time stamps.
    """
    assert algebra.triples(long) == days(1, *expected)
    assert algebra.triples(short) == days(1, *expected)


def test_left_to_right_without_parentheses(algebra):
    """Section 3.1: without parentheses the operators apply from left to right

    On the days 1 to 4 a = k, n = 10 + k and ha = k, all with equal time.
    (n - ha) - a = 10 - k: 9, 8, 7, 6; n - (ha - a) = n: 11, 12, 13, 14.
    The printed Z = A {STTOP} ((B {STTOP} C {STTOP} D) {STTOP} E) with
    subtraction: B* = n - ha = 10, B** = 10 - a = 10 - k,
    B*** = 10 - k - n = -2k, Z = a - B*** = 3k: 3, 6, 9, 12.
    """
    unbracketed = algebra.triples("N {-,equal,l} HA {-,equal,l} A")
    assert unbracketed == days(1, 9, 8, 7, 6)
    assert algebra.triples("(N {-,equal,l} HA) {-,equal,l} A") == unbracketed
    assert algebra.triples("N {-,equal,l} (HA {-,equal,l} A)") == days(
        1, 11, 12, 13, 14
    )
    printed = "A {-,equal,l} ((N {-,equal,l} HA {-,equal,l} A) {-,equal,l} N)"
    assert algebra.triples(printed) == days(1, 3, 6, 9, 12)


def test_appendix_b_td(algebra):
    """Table A1: td(A) is the interval size in days and fraction of days

    The maps of T last one hour, 1 / 24 day; pt0..pt7 have the values 0..7,
    so T + td(T) is k + 1 / 24.
    """
    rows = algebra.run("T + td(T)")
    assert [row.min for row in rows] == pytest.approx([k + 1 / 24 for k in range(8)])
    assert all(row.end - row.start == datetime.timedelta(hours=1) for row in rows)


def test_appendix_b_sin(algebra):
    """Table A2: sin(A) is the sine in degrees

    sin(30 degrees) = 0.5; in radians sin(30) would be about -0.988.
    """
    assert [value for *_, value in algebra.triples("sin(A * 0 + 30)")] == (
        pytest.approx([0.5] * 4)
    )


def test_appendix_b_isnull(algebra):
    """Table A2: isnull(A) is 1 where a cell is null and 0 elsewhere

    if(A > 2, A, null()) is null in a1 and a2 (1 and 2), so isnull gives 1,
    1, 0, 0.
    """
    assert algebra.triples("isnull(if(A > 2, A, null()))") == days(1, 1, 1, 0, 0)


def test_appendix_b_isntnull(algebra):
    """Table A2: isntnull(A) is 1 where a cell is not null and 0 elsewhere

    The maps of test_appendix_b_isnull, the other way round: 0, 0, 1, 1.
    """
    assert algebra.triples("isntnull(if(A > 2, A, null()))") == days(1, 0, 0, 1, 1)


def test_appendix_b_strds(algebra):
    """Table A3: STRDS(A) names A as a space time raster dataset

    The function identifies the type of a dataset in the mixed selections of
    t.select, which computes like this; t.rast.algebra takes no such
    function. c1 covers the days 2 and 3: a2 starts it and a3 finishes it,
    which count as during; a1 and a4 lie outside. a2 and a3 are selected
    with their values 2 and 3.
    """
    algebra.remove("R")
    evaluate(
        "R = STRDS(A) {:,during,l} C",
        kind="raster",
        basename="r",
        overwrite=True,
        selection=True,
    )
    rows = algebra.maps("R")
    assert [(row.start.day, row.end.day, row.min) for row in rows] == days(2, 2, 3)
