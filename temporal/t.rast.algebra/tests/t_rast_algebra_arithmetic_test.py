"""Test the raster arithmetic of t.rast.algebra

The datasets are described in the algebra fixture in conftest.py. All
expectations are derived by hand from the map values: map a<i> of dataset A
has the value i and the interval [i, i + 1] of January 2001.
"""

import pytest


def a_intervals(values):
    """Return the expected maps of dataset A with the given values"""
    return [(number, number + 1, value) for number, value in enumerate(values, 1)]


@pytest.mark.parametrize(
    ("expression", "values"),
    [
        ("A + 1", [2, 3, 4, 5]),
        ("A - 1", [0, 1, 2, 3]),
        ("A * 3", [3, 6, 9, 12]),
        ("float(A) / 2", [0.5, 1, 1.5, 2]),
        ("A % 3", [1, 2, 0, 1]),
        ("A + 1.5", [2.5, 3.5, 4.5, 5.5]),
        ("2 * A", [2, 4, 6, 8]),
        ("10 - A", [9, 8, 7, 6]),
        # r.mapcalc divides two integers as integers.
        ("12 / A", [12, 6, 4, 3]),
        ("20 % A", [0, 0, 2, 0]),
    ],
)
def test_strds_and_number(algebra, expression, values):
    """Operators combine every map of a STRDS with a number, in both orders"""
    assert algebra.triples(expression) == a_intervals(values)


@pytest.mark.parametrize(
    ("expression", "values"),
    [
        ("A + A", [2, 4, 6, 8]),
        ("A - A", [0, 0, 0, 0]),
        ("A * A", [1, 4, 9, 16]),
        ("A / A", [1, 1, 1, 1]),
        ("A % A", [0, 0, 0, 0]),
        ("A + N", [12, 14, 16, 18]),
        ("N - A", [10, 10, 10, 10]),
        ("A * N", [11, 24, 39, 56]),
    ],
)
def test_strds_and_strds(algebra, expression, values):
    """Two STRDS with equal time stamps are combined map by map"""
    assert algebra.triples(expression) == a_intervals(values)


@pytest.mark.parametrize(
    ("expression", "values"),
    [
        # % / * bind stronger than + -
        ("A + 1 * 2", [3, 4, 5, 6]),
        ("A + 6 % 4", [3, 4, 5, 6]),
        ("A + A * A", [2, 6, 12, 20]),
        ("(A + 1) * 2", [4, 6, 8, 10]),
        ("A * 2 + 1", [3, 5, 7, 9]),
        ("(A + A) * (A - 1)", [0, 4, 12, 24]),
        # operators of the same precedence are evaluated from left to right
        ("A - 1 - 1", [-1, 0, 1, 2]),
        ("A / 2 * 2", [0, 2, 2, 4]),
        ("A * 2 % 3", [2, 1, 0, 2]),
        ("A / A + A*A/A", [2, 3, 4, 5]),
    ],
)
def test_precedence_and_parentheses(algebra, expression, values):
    """Operator precedence and parentheses follow the manual"""
    assert algebra.triples(expression) == a_intervals(values)


@pytest.mark.parametrize(
    ("expression", "values"),
    [
        ("sqrt(A * A)", [1, 2, 3, 4]),
        ("abs(0 - A)", [1, 2, 3, 4]),
        ("float(A)", [1, 2, 3, 4]),
        ("int(float(A) / 2)", [0, 1, 1, 2]),
        ("float(A) / 4", [0.25, 0.5, 0.75, 1]),
        ("exp(A * 0)", [1, 1, 1, 1]),
        ("log(exp(A * 0 + 1))", [1, 1, 1, 1]),
        ("sin(A * 0)", [0, 0, 0, 0]),
        ("cos(A * 0)", [1, 1, 1, 1]),
        ("tan(A * 0 + 45)", [1, 1, 1, 1]),
        ("sqrt(A + 0.0) * sqrt(A + 0.0)", [1, 2, 3, 4]),
    ],
)
def test_mapcalc_functions(algebra, expression, values):
    """r.mapcalc functions are applied to every map, also nested"""
    result = algebra.triples(expression)
    assert [(start, end) for start, end, _ in result] == [
        (start, end) for start, end, _ in a_intervals(values)
    ]
    assert [value for _, _, value in result] == pytest.approx(values)


@pytest.mark.xfail(
    strict=True, reason="doc: round() is in the manual but not in the lexer"
)
def test_round_function(algebra):
    """round(x) rounds to the nearest integer as documented"""
    assert algebra.values("round(float(A) + 0.2)") == [1, 2, 3, 4]


def test_result_time_stamps_follow_the_input(algebra):
    """The result maps carry the time stamps of the input maps"""
    rows = algebra.run("B * 2")
    assert [(row.start, row.end, row.min) for row in rows] == [
        (algebra.day(1), algebra.day(3), 10),
        (algebra.day(3), algebra.day(5), 12),
    ]


def test_single_map_without_time(algebra):
    """map() adds a raster without time stamp to every map of a STRDS"""
    assert algebra.values("A * map(singlemap)") == [100, 200, 300, 400]
    assert algebra.values("map(singlemap) + A") == [101, 102, 103, 104]
    assert algebra.values("map(singlemap) - A") == [99, 98, 97, 96]


def test_chained_strds_without_relation(algebra):
    """Three STRDS with equal time stamps can be added in one expression"""
    assert algebra.values("A + N + A") == [13, 16, 19, 22]


def test_instants_are_computed(algebra):
    """Datasets of time instants (no end time) are handled like intervals"""
    rows = algebra.run("I * 10")
    assert [(row.start, row.end, row.min) for row in rows] == [
        (algebra.day(1), None, 10),
        (algebra.day(2), None, 20),
        (algebra.day(3), None, 30),
    ]


def test_cell_values_are_computed_per_cell(algebra):
    """The expression is evaluated per cell, not only per map"""
    rows = algebra.run("G * 2")
    assert [(row.min, row.max) for row in rows] == [(2, 6), (20, 60)]
