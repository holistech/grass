"""Checks at the entry of the public operations

A wrong kind of argument, such as the string "during" for a relation, would
otherwise fail with an AttributeError from the inside of an operation, or
only when the series is planned. Every type check raises a TypeError that
names the argument; check_option() raises a ValueError that names the
allowed values.
"""

from collections.abc import Callable

from .content import Call, Const, MapRef, SeriesAggregate, SeriesReduce
from .relations import Relation
from .series import Series

_OPERANDS = (
    Series,
    int,
    float,
    bool,
    type(None),
    Const,
    MapRef,
    Call,
    SeriesReduce,
    SeriesAggregate,
)


def require(value, expected, name, what, hint=""):
    """Raise a TypeError unless value is an instance of expected

    :param what: the expected kind with its article, e.g. "a Series"
    :param hint: what to do instead, appended to the message
    """
    if isinstance(value, expected):
        return
    msg = f"{name} must be {what}, got {type(value).__name__}"
    raise TypeError(f"{msg}; {hint}" if hint else msg)


def check_series(value, name="series"):
    """Stop unless value is a Series"""
    require(value, Series, name, "a Series")


def check_relation(value, name="relation"):
    """Stop unless value is a Relation, which a string is not"""
    hint = ""
    if isinstance(value, str):
        hint = f'use relation("{value}") or the constant {value}'
    require(value, Relation, name, "a Relation", hint)


def check_operands(function, operands):
    """Stop unless function is a name and the operands can be applied

    An operand is a Series, a number, a bool, None (null) or a content node.
    """
    require(function, str, "function", "a str")
    for number, operand in enumerate(operands, start=1):
        require(
            operand,
            _OPERANDS,
            f"operand {number} of {function}",
            "a Series, number, bool, None or content node",
        )


def check_option(name, value, allowed):
    """Stop unless value is one of the allowed values of the option name"""
    if value not in allowed:
        msg = f"{name} must be one of {', '.join(allowed)}, got {value!r}"
        raise ValueError(msg)


def check_int(value, name):
    """Stop unless value is an int"""
    require(value, int, name, "an int")


def check_callable(value, name):
    """Stop unless value is callable"""
    require(value, Callable, name, "callable")
