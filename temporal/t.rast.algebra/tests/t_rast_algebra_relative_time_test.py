"""Test t.rast.algebra with relative time

Dataset RT holds x1..x3 (values 1..3) with the relative intervals [0, 1],
[1, 2] and [2, 3] days. The datasets are described in the algebra fixture in
conftest.py. The result dataset has the temporal type of its inputs (review
finding M5).
"""

import pytest


def relative_maps(algebra, expression, **kwargs):
    """Return (start, end, value) of the result maps"""
    return [(row.start, row.end, row.min) for row in algebra.run(expression, **kwargs)]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("RT * 2", [(0, 1, 2), (1, 2, 4), (2, 3, 6)]),
        ("RT + RT", [(0, 1, 2), (1, 2, 4), (2, 3, 6)]),
        ("RT : RT", [(0, 1, 1), (1, 2, 2), (2, 3, 3)]),
        ("RT[1]", [(0, 1, 2), (1, 2, 3)]),
        # without else x1 is 0
        ("if(RT > 1, RT)", [(0, 1, 0), (1, 2, 2), (2, 3, 3)]),
    ],
)
def test_relative_time_is_kept(algebra, expression, expected):
    """The maps keep their relative time stamps"""
    assert relative_maps(algebra, expression) == expected


def test_relative_buffer_and_shift(algebra):
    """buff_t(A, 1) and tshift(A, 5) take a number of the time unit"""
    assert relative_maps(algebra, "buff_t(RT, 1)") == [
        (-1, 2, 1),
        (0, 3, 2),
        (1, 4, 3),
    ]
    assert relative_maps(algebra, "tshift(RT, 5)") == [
        (5, 6, 1),
        (6, 7, 2),
        (7, 8, 3),
    ]


@pytest.mark.parametrize(
    ("increment", "expected"),
    [("2", [(-2, 3, 1), (-1, 4, 2), (0, 5, 3)])],
)
def test_relative_buffer_with_a_whole_number(algebra, increment, expected):
    """A whole number is a buffer in the time unit. Target recorded from the
    reference implementation on 2026-10-15."""
    assert relative_maps(algebra, f"buff_t(RT, {increment})") == expected


@pytest.mark.parametrize("increment", ["1.5", "0.5", "-1.5"])
def test_relative_buffer_with_a_fractional_number_is_refused(algebra, increment):
    """A number with a fraction is a syntax error on relative time. The classic
    algebra cut it to a whole number of units, towards zero."""
    with pytest.raises(SyntaxError, match="whole number"):
        algebra.parse(f"buff_t(RT, {increment})")


def test_relative_time_difference(algebra):
    """td() is one for intervals of one day"""
    assert relative_maps(algebra, "if(td(RT) == 1, RT)") == [
        (0, 1, 1),
        (1, 2, 2),
        (2, 3, 3),
    ]
