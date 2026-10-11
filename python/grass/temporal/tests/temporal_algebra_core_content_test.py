"""Tests for the content trees of the algebra core

Scalars are folded while a tree is built; the expected values follow
r.mapcalc, which divides integers like C and gives null for a null operand.
"""

import pytest

from grass.temporal.algebra.content import (
    NULL,
    Call,
    Const,
    MapRef,
    SeriesReduce,
    call,
    chain,
    evaluate,
    series_reduce,
)

A = MapRef("a1@PERMANENT")
B = MapRef("b1@PERMANENT")


@pytest.mark.parametrize(
    ("function", "args", "expected"),
    [
        ("+", (1, 2), 3),
        ("/", (7, 2), 3),
        ("/", (-7, 2), -3),
        ("/", (7.0, 2), 3.5),
        ("/", (1, 0), None),
        ("%", (-7, 2), -1),
        (">", (2, 1), 1),
        ("==", (2, 1), 0),
        ("&&", (1, 0), 0),
        ("||", (1, 0), 1),
        ("!", (0,), 1),
        ("+", (None, 1), None),
        ("isnull", (None,), 1),
        ("nmin", (None, 3, 2), 2),
        ("nmax", (None, None), None),
    ],
)
def test_constants_are_folded(function, args, expected):
    assert call(function, *(Const(arg) for arg in args)) == Const(expected)


def test_field_stays_a_tree():
    assert call("+", A, Const(1)) == Call("+", (A, Const(1)))


def test_null_operand_of_an_operator_is_null():
    assert call("+", A, NULL) == NULL
    assert call("isnull", A) == Call("isnull", (A,))


def test_function_without_scalar_implementation_stays_a_call():
    """r.mapcalc computes sin() in degrees; the core does not imitate it"""
    assert call("sin", Const(0)) == Call("sin", (Const(0),))


def test_function_without_arguments_stays_a_call():
    assert call("rand") == Call("rand", ())


def test_if_without_else_is_null_where_false():
    assert call("if", Const(0), A) == NULL
    assert call("if", Const(1), A) == A
    assert call("if", NULL, A, B) == NULL
    assert call("if", MapRef("c@PERMANENT"), A) == Call(
        "if", (MapRef("c@PERMANENT"), A, NULL)
    )


def test_if_with_three_branches_decides_by_the_sign_of_the_condition():
    """r.mapcalc.md: if(x, a, b, c) is a where x > 0, b where x is zero and c
    where x < 0, null where x is null"""
    c = MapRef("c1@PERMANENT")
    assert call("if", Const(3), A, B, c) == A
    assert call("if", Const(0), A, B, c) == B
    assert call("if", Const(-2), A, B, c) == c
    assert call("if", NULL, A, B, c) == NULL
    assert call("if", Const(-0.5), Const(1), Const(2), Const(3)) == Const(3)
    unknown = MapRef("k@PERMANENT")
    assert call("if", unknown, A, B, c) == Call("if", (unknown, A, B, c))


def test_if_with_more_than_four_arguments_is_rejected():
    with pytest.raises(ValueError, match="if"):
        call("if", A, A, A, A, A)


def test_chain_joins_from_left_to_right():
    c = MapRef("c1@PERMANENT")
    assert chain("-", [A, B, c]) == Call("-", (A, B, c))
    assert chain("+", [A]) == A


def test_chain_of_a_right_associative_operator_keeps_its_nesting():
    """r.mapcalc reads a ^ b ^ c as a ^ (b ^ c), so a flat call would change
    the meaning of the chain ((a ^ b) ^ c)"""
    c = MapRef("c1@PERMANENT")
    assert chain("^", [A, B, c]) == Call("^", (Call("^", (A, B)), c))


@pytest.mark.parametrize("function", ["min", "max", "nmin", "nmax"])
def test_chain_of_a_variadic_function_is_one_call(function):
    c = MapRef("c1@PERMANENT")
    assert chain(function, [A, B, c]) == Call(function, (A, B, c))


def test_chain_of_a_function_that_is_not_associative_nests():
    c = MapRef("c1@PERMANENT")
    assert chain("median", [A, B, c]) == Call("median", (Call("median", (A, B)), c))


def test_chain_folds_leading_constants_and_null():
    assert chain("+", [Const(1), Const(2), A]) == Call("+", (Const(3), A))
    assert chain("+", [A, NULL, B]) == NULL


def test_chain_of_many_contents_is_not_deep():
    """A left-deep tree of 1000 maps would exhaust the stack of repr(), hash()
    and ==, and of every walk over the tree"""
    maps = [MapRef(f"m{i}@PERMANENT") for i in range(1000)]
    result = chain("+", maps)
    assert result.args == tuple(maps)
    assert result == chain("+", maps)
    assert hash(result) == hash(chain("+", maps))
    assert "m999@PERMANENT" in repr(result)


@pytest.mark.parametrize(
    ("function", "values", "expected"),
    [
        ("-", [10, 3, 2], 5),
        ("/", [100, 5, 2], 10),
        ("/", [100, 0, 2], None),
        ("-", [10, None, 2], None),
        ("<", [1, 2, 3], 1),
        ("&&", [1, 1, 0], 0),
        ("min", [3, 1, 2], 1),
    ],
)
def test_evaluate_n_ary_operators_left_to_right(function, values, expected):
    assert evaluate(function, values) == expected
    assert call(function, *(Const(v) for v in values)) == Const(expected)


def test_series_reduce_folds_constants_and_skips_null():
    assert series_reduce("sum", [Const(1), NULL, Const(3)]) == Const(4)
    assert series_reduce("average", [Const(1), NULL, Const(3)]) == Const(2.0)
    assert series_reduce("sum", [NULL, NULL]) == NULL
    assert series_reduce("sum", [A, B]) == SeriesReduce("sum", (A, B))


def test_if_needs_a_condition_and_a_value():
    with pytest.raises(ValueError, match="if"):
        call("if")
    with pytest.raises(ValueError, match="if"):
        call("if", A)


def test_chain_needs_contents():
    with pytest.raises(ValueError, match="at least one"):
        chain("+", [])


def test_evaluate_rejects_function_without_scalar_implementation():
    with pytest.raises(ValueError, match="sin"):
        evaluate("sin", [0])
