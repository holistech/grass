"""Test t.rast.algebra with relative time

Dataset RT holds x1..x3 (values 1..3) with the relative intervals [0, 1],
[1, 2] and [2, 3] days. The datasets are described in the algebra fixture in
conftest.py. The result dataset has the temporal type of its inputs (review
finding M5).
"""

import pytest

from grass.temporal.testing.reference import run_reference


def relative_maps(algebra, expression, **kwargs):
    """Return (start, end, value) of the result maps"""
    return [(row.start, row.end, row.min) for row in algebra.run(expression, **kwargs)]


@pytest.mark.parametrize(
    ("expression", "classic", "expected"),
    [
        ("RT * 2", None, [(0, 1, 2), (1, 2, 4), (2, 3, 6)]),
        ("RT + RT", None, [(0, 1, 2), (1, 2, 4), (2, 3, 6)]),
        ("RT : RT", None, [(0, 1, 1), (1, 2, 2), (2, 3, 3)]),
        ("RT[1]", None, [(0, 1, 2), (1, 2, 3)]),
        # without else x1 is null and left out, 0 in the classic algebra
        pytest.param(
            "if(RT > 1, RT)",
            False,
            [(1, 2, 2), (2, 3, 3)],
            marks=pytest.mark.fixed_algebra,
        ),
        pytest.param(
            "if(RT > 1, RT)",
            True,
            [(0, 1, 0), (1, 2, 2), (2, 3, 3)],
            marks=pytest.mark.fixed_algebra,
        ),
    ],
)
def test_relative_time_is_kept(algebra, expression, classic, expected):
    """The maps keep their relative time stamps; classic None follows
    GRASS_TEMPORAL_ALGEBRA where both algebras agree"""
    assert relative_maps(algebra, expression, classic=classic) == expected


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


@pytest.mark.fixed_algebra
@pytest.mark.parametrize(
    "expression",
    [
        'buff_t(RT, "3 hours")',
        'buff_t(RT, "1 day")',
        'buff_t(RT, "1 month")',
        'RT + buff_t(RT, "1 day")',
        # A refused buffer leaves no result, also for absolute time.
        "buff_t(A, 3)",
    ],
)
def test_buffer_of_the_wrong_kind_is_a_syntax_error(algebra, expression):
    """A buffer with a time unit is refused for relative time like a number
    without unit is for absolute time. It was a TypeError of the subtraction
    of the buffer from the start time. The error leaves no result dataset.

    Checked on the earlier implementation only: the core raises a ValueError
    with its own message for the same expressions.
    """
    algebra.remove("R")
    with pytest.raises(SyntaxError, match=r"buff_t\(\) needs a"):
        run_reference(
            "raster", f"R = {expression}", basename="r", overwrite=True, run=True
        )
    assert not algebra.exists()


@pytest.mark.fixed_algebra
@pytest.mark.parametrize(
    ("increment", "expected"),
    [
        # A fraction is cut to a whole number of units, towards zero.
        ("1.5", [(-1, 2, 1), (0, 3, 2), (1, 4, 3)]),
        ("2", [(-2, 3, 1), (-1, 4, 2), (0, 5, 3)]),
        ("0.5", [(0, 1, 1), (1, 2, 2), (2, 3, 3)]),
        ("-1.5", [(0, 1, 1), (1, 2, 2), (2, 3, 3)]),
    ],
)
def test_relative_buffer_with_a_fractional_number(algebra, increment, expected):
    """Numbers other than whole ones stay valid for relative time. Targets
    measured 2026-10-15 on the library before the buff_t() checks changed,
    with the earlier implementation."""
    algebra.remove("R")
    run_reference(
        "raster",
        f"R = buff_t(RT, {increment})",
        basename="r",
        overwrite=True,
        run=True,
    )
    assert [(row.start, row.end, row.min) for row in algebra.maps("R")] == expected


def test_relative_time_difference(algebra):
    """td() is one for intervals of one day"""
    assert relative_maps(algebra, "if(td(RT) == 1, RT)") == [
        (0, 1, 1),
        (1, 2, 2),
        (2, 3, 3),
    ]
