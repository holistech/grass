"""Tests for the content trees of the algebra core

Scalars are folded while a tree is built; the expected values follow
r.mapcalc, which divides integers like C and gives null for a null operand.
"""

import re
from datetime import date, datetime, time, timedelta, timezone

import pytest

from grass.temporal.algebra import content
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
DAY = date(2001, 1, 1)
NOON = time(12)


@pytest.mark.parametrize(
    ("function", "args", "expected"),
    [
        ("+", (1, 2), 3),
        ("/", (7, 2), 3),
        ("/", (-7, 2), -3),
        ("/", (7.0, 2), 3.5),
        ("/", (1, 0), None),
        ("%", (-7, 2), -1),
        # r.mapcalc takes the remainder of a float like C fmod() (measured
        # 2026-11-12 with r.mapcalc "m = 7.5 % 2" in a one-cell region of a
        # temporary project: r.univar -g mean 1.5; -7.5 % 2 gave -1.5 and
        # 7 % 2.5 gave 2).
        ("%", (7.5, 2), 1.5),
        ("%", (-7.5, 2), -1.5),
        ("%", (7, 2.5), 2.0),
        # r.mapcalc gives null for a modulo by zero (measured 2026-11-11 with
        # r.mapcalc "m = 7 % 0" in a one-cell region: r.univar null_cells=1).
        ("%", (7, 0), None),
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


def test_if_without_else_is_zero_where_false():
    """As in r.mapcalc, if(x, a) is a where x is not zero and 0 otherwise;
    a null condition gives null"""
    assert call("if", Const(0), A) == Const(0)
    assert call("if", Const(1), A) == A
    assert call("if", NULL, A) == NULL
    assert call("if", NULL, A, B) == NULL
    assert call("if", MapRef("c@PERMANENT"), A) == Call(
        "if", (MapRef("c@PERMANENT"), A, Const(0))
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


def test_a_null_condition_of_the_scalar_if_gives_null():
    """if() is null aware, so evaluate() hands it the null condition itself"""
    assert evaluate("if", [None, 1, 2]) is None
    assert evaluate("if", [None, 1]) is None


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        (None, None),
        (datetime(2001, 1, 1, 6), "datetime"),
        (DAY, "date"),
        (NOON, "time"),
        (1, "number"),
        (1.5, "number"),
        (True, "number"),
        (timedelta(days=1), "other"),
        ("2001-01-01", "other"),
    ],
)
def test_value_kind(value, kind):
    """bool is a subclass of int and datetime one of date"""
    assert content.value_kind(value) == kind


def test_moment_kinds():
    assert {"date", "time", "datetime"} == content.MOMENT_KINDS


@pytest.mark.parametrize(
    ("function", "values", "first", "second"),
    [
        (">", [date(2001, 1, 3), 5], "a date (2001-01-03)", "a number (5)"),
        # Python gives False for == of a time and a number, so this was 0
        # without a word.
        ("==", [NOON, 3], "a time of day (12:00:00)", "a number (3)"),
        (
            "<",
            [DAY, datetime(2001, 1, 1)],
            "a date (2001-01-01)",
            "a date with a time of day (2001-01-01 00:00:00)",
        ),
        # Null is no kind; in a chain the first value of another kind than
        # the first value is named.
        ("<", [None, 5, 6, date(2001, 1, 3)], "a number (5)", "a date (2001-01-03)"),
        ("!=", [timedelta(days=1), 1], "a value (1 day, 0:00:00)", "a number (1)"),
    ],
)
def test_evaluate_refuses_a_comparison_of_two_kinds(function, values, first, second):
    message = f"{function}() compares values of one kind, but got {first} and {second}"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        evaluate(function, values)


@pytest.mark.parametrize(
    ("function", "values", "described"),
    [
        ("+", [DAY, 1], "a date (2001-01-01)"),
        ("-", [DAY, date(2001, 1, 2)], "a date (2001-01-01)"),
        ("*", [2, NOON], "a time of day (12:00:00)"),
        (
            "/",
            [datetime(2001, 1, 1, 6), 2],
            "a date with a time of day (2001-01-01 06:00:00)",
        ),
        ("%", [DAY, 2], "a date (2001-01-01)"),
        ("neg", [DAY], "a date (2001-01-01)"),
        ("abs", [NOON], "a time of day (12:00:00)"),
        ("min", [1, DAY], "a date (2001-01-01)"),
        ("max", [NOON, NOON], "a time of day (12:00:00)"),
        ("nmin", [None, DAY], "a date (2001-01-01)"),
        ("nmax", [DAY, None], "a date (2001-01-01)"),
        ("&&", [DAY, 1], "a date (2001-01-01)"),
        ("||", [0, NOON], "a time of day (12:00:00)"),
        ("!", [DAY], "a date (2001-01-01)"),
        # The null operand does not hide the date.
        ("-", [DAY, None], "a date (2001-01-01)"),
        ("+", [timedelta(days=1), 1], "a value (1 day, 0:00:00)"),
    ],
)
def test_evaluate_refuses_arithmetic_on_dates_and_times(function, values, described):
    message = (
        f"{function}() computes with numbers, not with {described}; use the "
        "numbers of time functions such as start_doy() or td()"
    )
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        evaluate(function, values)


@pytest.mark.parametrize(
    "arguments",
    [[DAY, 1, 2], [NOON, 1], [datetime(2001, 1, 1), 1, 2, 3]],
)
def test_evaluate_refuses_a_date_as_condition_of_if(arguments):
    """call() decides an if with a constant condition without evaluate()"""
    condition = arguments[0]
    kind = {
        date: "a date",
        time: "a time of day",
        datetime: "a date with a time of day",
    }
    message = (
        f"if() needs a number as condition, not {kind[type(condition)]} ({condition})"
    )
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        evaluate("if", arguments)
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        call("if", *(Const(argument) for argument in arguments))
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        call("if", Const(condition), A, B)


def test_null_and_one_kind_still_compute():
    """Null is no kind, and int, float and bool are one kind; the branches of
    if() and the argument of isnull() may be of any kind"""
    assert evaluate("==", [None, DAY]) is None
    assert evaluate("<", [DAY, None, date(2001, 1, 2)]) is None
    assert evaluate("<", [DAY, date(2001, 1, 2)]) == 1
    assert evaluate("==", [NOON, time(12)]) == 1
    assert evaluate(">=", [datetime(2001, 1, 2), datetime(2001, 1, 1, 6)]) == 1
    assert evaluate("==", [1, 1.0]) == 1
    assert evaluate("+", [True, 1]) == 2
    assert evaluate(">", [1.5, True]) == 1
    assert evaluate("-", [None, 1]) is None
    assert evaluate("if", [1, DAY, 0]) == DAY
    assert evaluate("if", [0, 0, NOON]) == NOON
    assert evaluate("if", [None, DAY]) is None
    assert evaluate("isnull", [DAY]) == 0
    assert call("if", Const(1), Const(DAY), Const(0)) == Const(DAY)
    assert call("if", Const(0), Const(DAY)) == Const(0)
    assert call("==", Const(DAY), NULL) == NULL


MAPS_HOLD_NUMBERS = (
    "maps hold numbers; compare time functions with each other or with a date "
    "in quotes, or use the numbers of time functions such as start_doy() or td()"
)


@pytest.mark.parametrize(
    ("function", "args", "described"),
    [
        (">", (A, Const(DAY)), "a date (2001-01-01)"),
        ("+", (Const(NOON), A), "a time of day (12:00:00)"),
        ("if", (A, Const(DAY), Const(0)), "a date (2001-01-01)"),
        ("if", (A, Const(DAY)), "a date (2001-01-01)"),
        ("if", (A, B, Const(NOON)), "a time of day (12:00:00)"),
    ],
)
def test_call_refuses_a_map_with_a_date(function, args, described):
    """Before, the tree was built and plan() refused it later"""
    message = f"{function}() cannot combine maps with {described}: {MAPS_HOLD_NUMBERS}"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        call(function, *args)


@pytest.mark.parametrize("method", ["sum", "average"])
def test_series_reduce_refuses_dates(method):
    message = (
        f"{method}() computes with numbers, not with a date (2001-01-01); use the "
        "numbers of time functions such as start_doy() or td()"
    )
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        series_reduce(method, [NULL, Const(DAY), Const(date(2001, 1, 2))])


def test_dates_with_and_without_offset_are_not_compared():
    aware = datetime(2001, 1, 1, tzinfo=timezone(timedelta(hours=1)))
    naive = datetime(2001, 1, 1)
    for values in ([aware, naive], [naive, aware]):
        with pytest.raises(TypeError) as error:
            evaluate("==", values)
        assert str(error.value) == (
            "==() cannot compare a date and time with a time zone offset "
            "(2001-01-01 00:00:00+01:00) with one without (2001-01-01 00:00:00)"
        )
