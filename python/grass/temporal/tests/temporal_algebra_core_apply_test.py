"""Tests for apply() and the operators of series in the algebra core"""

import pytest

from grass.temporal.algebra.content import NULL, Call, Const, MapRef
from grass.temporal.algebra.operations import apply, cell_offset, lift
from grass.temporal.algebra.series import Series, Slot


def ref(name):
    return MapRef(f"{name}@PERMANENT")


@pytest.fixture
def a(make_series):
    return make_series("a", (1, 2), (2, 3))


@pytest.fixture
def n(make_series):
    return make_series("n", (1, 2), (2, 3))


@pytest.fixture
def s(make_series):
    return make_series("s", (1, 2), (2, 3), values=[1, None])


def contents(series):
    return [slot.content for slot in series]


def test_apply_slot_by_slot(a, n):
    result = apply("+", a, n)
    assert result.times() == a.times()
    assert contents(result) == [
        Call("+", (ref("a1"), ref("n1"))),
        Call("+", (ref("a2"), ref("n2"))),
    ]
    assert result.sort == "field"
    assert all(slot.origin is None for slot in result)


def test_operators_build_the_same_trees(a, n):
    assert contents(a + n) == contents(apply("+", a, n))
    assert contents(1 - a) == [
        Call("-", (Const(1), ref("a1"))),
        Call("-", (Const(1), ref("a2"))),
    ]
    assert contents(-a) == [Call("neg", (ref("a1"),)), Call("neg", (ref("a2"),))]
    assert contents(a > 2) == contents(apply(">", a, 2))
    assert contents((a > 1) & (a < 3)) == contents(apply("&&", a > 1, a < 3))
    assert contents((a > 1) | (a < 3)) == contents(apply("||", a > 1, a < 3))
    assert contents(~(a > 1)) == contents(apply("!", a > 1))
    assert contents(a == n) == contents(apply("==", a, n))
    assert contents(a != n) == contents(apply("!=", a, n))


@pytest.mark.parametrize("function", ["+", "-", "*", "/", "%"])
def test_arithmetic_operators_and_their_reflections(a, function):
    operators = {
        "+": lambda x, y: x + y,
        "-": lambda x, y: x - y,
        "*": lambda x, y: x * y,
        "/": lambda x, y: x / y,
        "%": lambda x, y: x % y,
    }
    assert contents(operators[function](a, 2)) == contents(apply(function, a, 2))
    assert contents(operators[function](2, a)) == contents(apply(function, 2, a))


@pytest.mark.parametrize("function", ["<", "<=", ">", ">="])
def test_ordering_operators(a, function):
    operators = {
        "<": lambda x, y: x < y,
        "<=": lambda x, y: x <= y,
        ">": lambda x, y: x > y,
        ">=": lambda x, y: x >= y,
    }
    assert contents(operators[function](a, 2)) == contents(apply(function, a, 2))


def test_reflected_logic_operators(a):
    assert contents(True & (a > 1)) == contents(apply("&&", True, a > 1))
    assert contents(False | (a > 1)) == contents(apply("||", False, a > 1))


def test_comparison_of_series_is_not_a_truth_value(a, n):
    with pytest.raises(TypeError, match="truth value"):
        assert a == n


def test_series_are_not_hashable(a):
    with pytest.raises(TypeError, match="unhashable"):
        hash(a)


def test_scalars_are_computed_in_python(s):
    doubled = s * 2
    assert doubled.sort == "scalar"
    assert contents(doubled) == [Const(2), NULL]


def test_scalar_and_field_give_a_field(a, s):
    result = a + s
    assert result.sort == "field"
    assert contents(result) == [Call("+", (ref("a1"), Const(1))), NULL]


def test_scalar_function_without_python_implementation_is_rejected(s):
    with pytest.raises(ValueError, match="cannot be computed for scalar"):
        apply("sin", s)


def test_series_of_different_time_stamps_are_rejected(a, make_series):
    b = make_series("b", (1, 3))
    with pytest.raises(ValueError, match="slot 0"):
        apply("+", a, b)


def test_message_names_the_first_slot_that_differs(a, make_series):
    b = make_series("b", (1, 2), (2, 4))
    with pytest.raises(ValueError, match=r"slot 1: .*2001-01-03.* and .*2001-01-04"):
        apply("+", a, b)


def test_series_of_different_length_are_rejected(a, make_series):
    b = make_series("b", (1, 2))
    with pytest.raises(ValueError, match=r"slot 1: .*2001-01-03.* and no slot"):
        apply("+", a, b)
    with pytest.raises(ValueError, match=r"slot 1: no slot and .*2001-01-03"):
        apply("+", b, a)


def test_message_shows_an_instant_without_end(a, make_series):
    b = make_series("b", 1, (2, 3))
    with pytest.raises(ValueError, match=r"and 2001-01-01 00:00:00\. Relate") as info:
        apply("+", a, b)
    assert "None" not in str(info.value)


def test_message_shows_the_unit_of_relative_time(make_series):
    days = make_series("d", (1, 2), unit="days")
    hours = make_series("h", (1, 2), unit="hours")
    with pytest.raises(ValueError, match=r"1 \.\. 2 days and 1 \.\. 2 hours\. Relate"):
        apply("+", days, hours)
    instant = make_series("i", 1, unit="days")
    with pytest.raises(ValueError, match=r"slot 0: 1 \.\. 2 days and 1 days\. Relate"):
        apply("+", days, instant)


def test_series_of_different_map_types_are_rejected(a):
    vector = Series((Slot(a.slots[0].extent, ref("v")),), kind="vector")
    with pytest.raises(ValueError, match="different map types"):
        apply("+", Series(a.slots[:1]), vector)


def test_map_without_time_stamp_is_used_in_every_slot(a):
    m = Series((Slot(None, ref("m")),))
    assert contents(a + m) == [
        Call("+", (ref("a1"), ref("m"))),
        Call("+", (ref("a2"), ref("m"))),
    ]


def test_content_of_another_tree_is_not_taken_for_a_constant(a):
    tree = Call("abs", (ref("m"),))
    assert contents(apply("+", a, tree))[0] == Call("+", (ref("a1"), tree))


def test_apply_needs_a_series_with_time_stamps():
    m = Series((Slot(None, ref("m")),))
    with pytest.raises(ValueError, match="time stamps"):
        apply("+", m, 1)


def test_apply_of_empty_series():
    assert apply("+", Series(), 1).slots == ()


def test_lift_makes_a_constant_field(s):
    lifted = lift(s)
    assert lifted.sort == "field"
    assert lifted.slots == s.slots


def test_cell_offset(a):
    assert contents(cell_offset(a, 1, 0)) == [
        MapRef("a1@PERMANENT", (1, 0)),
        MapRef("a2@PERMANENT", (1, 0)),
    ]
    with pytest.raises(ValueError, match="cell offset"):
        cell_offset(a + 1, 1, 0)
