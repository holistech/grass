"""Tests for the type checks at the entry of the public operations

A wrong kind of argument is a TypeError that names the argument, not an
AttributeError from the inside of an operation or an error at plan().
"""

import pytest

from grass.temporal.algebra import (
    Const,
    MapRef,
    apply,
    cell_offset,
    choose,
    contains,
    during,
    gather,
    lift,
    merge,
    neighbour,
    pairs,
    retime,
    select,
    timevar,
    where,
)


@pytest.fixture
def a(make_series):
    return make_series("a", (1, 2), (2, 3))


def test_a_string_is_not_a_relation(a):
    for operation in (
        lambda: select(a, "during", a),
        lambda: pairs(a, "during", a),
        lambda: gather(a, "during", a, reduce="sum"),
    ):
        with pytest.raises(TypeError, match=r"relation\(\"during\"\).*constant"):
            operation()


@pytest.mark.parametrize(
    "wrong", [[1], None, 5, "a1@PERMANENT", MapRef("a1@PERMANENT")]
)
def test_series_arguments_must_be_series(a, wrong):
    with pytest.raises(TypeError, match="left must be a Series"):
        select(wrong, during, a)
    with pytest.raises(TypeError, match="other must be a Series"):
        select(a, during, wrong)
    with pytest.raises(TypeError, match="left must be a Series"):
        pairs(wrong, during, a)
    with pytest.raises(TypeError, match="other must be a Series"):
        pairs(a, during, wrong)
    with pytest.raises(TypeError, match="target must be a Series"):
        gather(wrong, during, a, reduce="sum")
    with pytest.raises(TypeError, match="other must be a Series"):
        gather(a, during, wrong, reduce="sum")
    with pytest.raises(TypeError, match="condition must be a Series"):
        choose(wrong, a)
    with pytest.raises(TypeError, match="then must be a Series"):
        choose(timevar(a, "td"), wrong)
    if wrong is not None:  # no otherwise is allowed
        with pytest.raises(TypeError, match="otherwise must be a Series"):
            choose(timevar(a, "td"), a, wrong)
    with pytest.raises(TypeError, match="condition must be a Series"):
        where(wrong, a)
    with pytest.raises(TypeError, match="must be a Series"):
        merge(a, wrong)
    with pytest.raises(TypeError, match="series must be a Series"):
        retime(wrong, shift="1 day")
    with pytest.raises(TypeError, match="series must be a Series"):
        timevar(wrong, "td")
    with pytest.raises(TypeError, match="series must be a Series"):
        neighbour(wrong, 1)
    with pytest.raises(TypeError, match="series must be a Series"):
        cell_offset(wrong, 1, 0)
    with pytest.raises(TypeError, match="series must be a Series"):
        lift(wrong)


def test_choose_with_a_bool_as_condition(a):
    with pytest.raises(TypeError, match="condition must be a Series, got bool"):
        choose(True, a)


def test_a_relation_must_be_a_relation(a):
    with pytest.raises(TypeError, match="relation must be a Relation"):
        select(a, 5, a)


def test_pairs_content_must_be_callable(a):
    with pytest.raises(TypeError, match="content must be callable"):
        pairs(a, during, a, content="+")


def test_offsets_must_be_integers(a):
    with pytest.raises(TypeError, match="offset must be an int"):
        neighbour(a, 1.5)
    with pytest.raises(TypeError, match="offset must be an int"):
        cell_offset(a, 1, "0")


@pytest.mark.parametrize("wrong", [[1, 2, 3], "text", (1, 2), {"a": 1}, object()])
def test_operands_of_apply_must_be_numbers_series_or_contents(a, wrong):
    with pytest.raises(TypeError, match="operand"):
        apply("+", a, wrong)
    with pytest.raises(TypeError, match="operand"):
        a + wrong
    with pytest.raises(TypeError, match="operand"):
        wrong + a
    with pytest.raises(TypeError, match="operand"):
        a == wrong
    with pytest.raises(TypeError, match="operand"):
        where(a > 1, a, wrong)


def test_the_function_of_apply_is_a_string(a):
    with pytest.raises(TypeError, match="function must be a str"):
        apply(5, a)


def test_valid_operands_are_still_accepted(a):
    for operand in (1, 2.5, True, None, Const(3), MapRef("m@PERMANENT"), a):
        assert len(apply("+", a, operand)) == 2
    assert len(choose(timevar(a, "td") > 0, a)) == 2
    assert len(merge(a)) == 2
    assert len(select(a, contains, a, related=False)) == 2
