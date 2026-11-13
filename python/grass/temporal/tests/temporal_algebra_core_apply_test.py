"""Tests for apply() and the operators of series in the algebra core"""

import re
from datetime import date

import pytest

from grass.temporal.algebra.content import NULL, Call, Const, MapRef
from grass.temporal.algebra.operations import apply, cell_offset, choose, lift
from grass.temporal.algebra.series import Series, Slot
from grass.temporal.algebra.time_functions import timevar


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
    with pytest.raises(ValueError, match="map 1"):
        apply("+", a, b)


def test_message_names_the_first_slot_that_differs(a, make_series):
    b = make_series("b", (1, 2), (2, 4))
    with pytest.raises(ValueError, match=r"map 2: .*2001-01-03.* and .*2001-01-04"):
        apply("+", a, b)


def test_series_of_different_length_are_rejected(a, make_series):
    b = make_series("b", (1, 2))
    with pytest.raises(ValueError, match=r"map 2: .*2001-01-03.* and no map"):
        apply("+", a, b)
    with pytest.raises(ValueError, match=r"map 2: no map and .*2001-01-03"):
        apply("+", b, a)


def test_message_shows_an_instant_without_end(a, make_series):
    b = make_series("b", 1, (2, 3))
    with pytest.raises(ValueError, match=r"and 2001-01-01 00:00:00\. Select") as info:
        apply("+", a, b)
    assert "None" not in str(info.value)


def test_message_shows_the_unit_of_relative_time(make_series):
    days = make_series("d", (1, 2), unit="days")
    hours = make_series("h", (1, 2), unit="hours")
    with pytest.raises(ValueError, match=r"1 \.\. 2 days and 1 \.\. 2 hours\. Select"):
        apply("+", days, hours)
    instant = make_series("i", 1, unit="days")
    with pytest.raises(ValueError, match=r"map 1: 1 \.\. 2 days and 1 days\. Select"):
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


@pytest.mark.parametrize("function", [">", "=="])
def test_python_api_refuses_a_comparison_of_two_kinds(a, function):
    """The parser refuses this with its own message; the Python API gets the
    message of the core instead of a raw TypeError for > and a silent 0 for
    ==. The first map of a starts on 1 January 2001 at midnight."""
    message = (
        f"{function}() compares values of one kind, but got a number (1) and a "
        "time of day (00:00:00)"
    )
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        apply(function, timevar(a, "start_doy"), timevar(a, "start_time"))


def test_null_is_no_kind_in_the_python_api(make_series):
    """Instances have no end, so end_date() is null and the comparison is
    null; a series of a date and a null compares with dates"""
    instants = make_series("i", 1, 2)
    compared = apply(
        "==", timevar(instants, "end_date"), timevar(instants, "start_date")
    )
    assert contents(compared) == [NULL, NULL]
    some = make_series("s", 1, 2, values=[date(2001, 1, 1), None])
    later = apply("<", some, timevar(instants, "start_date"))
    # 1 January is not before itself; the second slot is null.
    assert contents(later) == [Const(0), NULL]


def test_choose_refuses_a_date_condition(a, make_series):
    """A date is no truth value; before, every date chose its slot"""
    condition = make_series("c", (1, 2), (2, 3), values=[None, date(2001, 1, 2)])
    message = "choose() needs numbers as condition, not a date (2001-01-02)"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        choose(condition, a)
