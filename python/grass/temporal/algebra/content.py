"""Content of the slots of a series: immutable expression trees

A tree says what a map contains, not how it is computed, so it is independent
of the module that could compute it. Scalar values, one value per slot such
as the length of an interval, are folded into constants while a tree is
built, so a tree without map references can be decided in Python.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import datetime
import math
import operator
from dataclasses import dataclass


@dataclass(frozen=True)
class MapRef:
    """A registered map, optionally read at a cell offset (row, column)"""

    ident: str
    offset: tuple[int, ...] = ()


@dataclass(frozen=True)
class Const:
    """A constant value; None is null"""

    value: object = None


@dataclass(frozen=True)
class Call:
    """An operator or a function of the raster algebra applied to contents"""

    function: str
    args: tuple


@dataclass(frozen=True)
class SeriesReduce:
    """A reduction over maps that passes over null cells

    r.mapcalc has no sum or mean that skips null cells, so this node is kept
    apart from Call; r.series is the module that computes it.
    """

    method: str
    args: tuple


@dataclass(frozen=True)
class SeriesAggregate:
    """An r.series aggregation of related maps, or a verbatim copy of one

    Kept apart from SeriesReduce for two things that belong to
    t.rast.aggregate and must not leak into the skip-sum and skip-mean of the
    algebra: a single related map is copied with g.copy so that its data type
    and color table survive and the method does not touch its values (measured
    2026-10-14 with t.rast.aggregate method=count on a one map granule: the
    result was the source value, not 1, and kept the CELL type and the grey
    color table), and the open file limit that switches r.series to its -z
    mode travels with the node.

    weights is None for an aggregation without weights, else one weight per
    map in args, which r.series reads from its file as name|weight. A lone
    map is copied with weights as well, except for the method sum with a
    weight other than 1, which r.series must scale.
    """

    method: str
    args: tuple
    file_limit: int = 1000
    weights: tuple | None = None


Content = MapRef | Const | Call | SeriesReduce | SeriesAggregate

NULL = Const(None)


# The null rules and the integer arithmetic below follow r.mapcalc. Checked
# 2026-10-11 with r.mapcalc expression="out = <expression>" in grass
# --tmp-project XY and r.stats -n: 5/2 gave 2, -7/2 gave -3, 5.0/2 gave 2.5,
# -7 % 2 gave -1, 5/0 and 5 % 0 gave null, and 5 + null() and 1 && null()
# gave null.
def _divide(left, right):
    if right == 0:
        return None
    if isinstance(left, int) and isinstance(right, int):
        # r.mapcalc divides integers like C, truncating towards zero
        return int(left / right)
    return left / right


def _modulo(left, right):
    if right == 0:
        return None
    result = math.fmod(left, right)
    if isinstance(left, int) and isinstance(right, int):
        return int(result)
    return result


def _compare(function):
    return lambda left, right: int(function(left, right))


def _if(condition, then, otherwise=None, *negative):
    if condition is None:
        return None
    if negative:
        # if(x, a, b, c) is a where x > 0, b where x == 0, c where x < 0
        # (r.mapcalc.md; checked 2026-10-11 with r.mapcalc expression=
        # "out = if(x, 10, 20, 30)": x = 3 gave 10, x = 0 gave 20 and
        # x = -2 gave 30).
        if condition > 0:
            return then
        return otherwise if condition == 0 else negative[0]
    return then if condition else otherwise


def _skipping(function):
    def reduce(*values):
        present = [value for value in values if value is not None]
        return function(present) if present else None

    return reduce


# The comparison operators of r.mapcalc. They are named here rather than in
# the parser, so that the backends need not import the parser.
COMPARISONS = ("==", "!=", ">", ">=", "<", "<=")

# Scalar implementations of r.mapcalc operators. As in r.mapcalc (see the
# check above), comparisons give 1 or 0 and a null operand gives null.
_SCALAR = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": _divide,
    "%": _modulo,
    "neg": operator.neg,
    "==": _compare(operator.eq),
    "!=": _compare(operator.ne),
    ">": _compare(operator.gt),
    ">=": _compare(operator.ge),
    "<": _compare(operator.lt),
    "<=": _compare(operator.le),
    "&&": lambda left, right: int(bool(left) and bool(right)),
    "||": lambda left, right: int(bool(left) or bool(right)),
    "!": lambda value: int(not value),
    "abs": abs,
    "min": min,
    "max": max,
}

# Functions that decide about null themselves instead of propagating it
_NULL_AWARE = {
    "isnull": lambda value: int(value is None),
    "if": _if,
    "nmin": _skipping(min),
    "nmax": _skipping(max),
}


# The operators that r.mapcalc parses from left to right (mapcalc.y), so that
# "a - b - c" is "(a - b) - c". A chain of one of them is one call with all
# operands: a left-deep tree of binary calls is as deep as the chain is long,
# and reducing many maps overflowed the stack of repr(), hash(), == and of
# every walk over the tree (measured 2026-10-11 with gather(reduce="sum") of
# n related maps followed by plan(), repr() and hash(): n=400 ran, n=500
# raised RecursionError).
# ^ is missing on purpose: r.mapcalc reads "a ^ b ^ c" as "a ^ (b ^ c)".
LEFT_ASSOCIATIVE = frozenset(
    {"+", "-", "*", "/", "%", "==", "!=", ">", ">=", "<", "<=", "&&", "||"}
    | {"&&&", "|||", "&", "|", "<<", ">>", ">>>"}
)

# Functions of r.mapcalc that take any number of operands and give the same
# result for min(min(a, b), c) as for min(a, b, c).
_VARIADIC = frozenset({"min", "max", "nmin", "nmax"})


class ScalarFunctionError(ValueError):
    """A function that has no implementation for scalar values

    apply() raises it for a series of numbers, such as sin(td(A)), whose
    function has no Python implementation here.
    """


# The kinds of value_kind() that are moments in time
MOMENT_KINDS = frozenset({"date", "time", "datetime"})

_KIND_NAMES = {
    "number": "a number",
    "date": "a date",
    "time": "a time of day",
    "datetime": "a date with a time of day",
    "other": "a value",
}


def value_kind(value):
    """Return the kind of a scalar value: what the time functions can give

    :returns: None for null, "datetime", "date" or "time" for the values of
        start_datetime(), start_date() and start_time(), "number" for int,
        float and bool, and "other" for anything else
    """
    if value is None:
        return None
    # datetime is a subclass of date, so it is checked first.
    if isinstance(value, datetime.datetime):
        return "datetime"
    if isinstance(value, datetime.date):
        return "date"
    if isinstance(value, datetime.time):
        return "time"
    # bool is a subclass of int, and r.mapcalc has no truth values apart
    # from numbers.
    if isinstance(value, (int, float)):
        return "number"
    return "other"


def describe_value(value):
    """Return the kind and the value as the messages of the core name them

    For example "a date (2001-01-01)" or "a number (5)"; not for null.
    """
    return f"{_KIND_NAMES[value_kind(value)]} ({value})"


# Python refuses < between a date and a number with a TypeError that names no
# function, gives False for == between them, and computes date - date into a
# duration that r.mapcalc has no number for; the checks below report each of
# these slips with the function and a way out. Null is no kind.


def check_condition(function, value):
    """Raise TypeError if the condition value of function is a date or a time

    :raises TypeError: for a date or a time, whose truth Python decides
        without a word: every date and time of day is true
    """
    if value_kind(value) in MOMENT_KINDS:
        msg = f"{function}() needs a number as condition, not {describe_value(value)}"
        raise TypeError(msg)


def _check_compared(function, values):
    """Raise TypeError for the first value of another kind than the first"""
    present = [value for value in values if value is not None]
    if not present:
        return
    for value in present[1:]:
        if value_kind(value) != value_kind(present[0]):
            msg = (
                f"{function}() compares values of one kind, but got "
                f"{describe_value(present[0])} and {describe_value(value)}"
            )
            raise TypeError(msg)


def _refuse_computing(function, value):
    msg = (
        f"{function}() computes with numbers, not with {describe_value(value)}; "
        "use the numbers of time functions such as start_doy() or td()"
    )
    raise TypeError(msg)


def _check_kinds(function, values):
    """Raise TypeError if function cannot take the kinds of values

    The branches of if() and the argument of isnull() may be of any kind.
    """
    if function == "isnull":
        return
    if function == "if":
        check_condition(function, values[0])
    elif function in COMPARISONS:
        _check_compared(function, values)
    else:
        for value in values:
            if value_kind(value) not in (None, "number"):
                _refuse_computing(function, value)


def evaluate(function, values):
    """Compute an operator or a function of r.mapcalc on scalar values

    An operator with more than two operands is applied from left to right.
    Dates and times, see value_kind(), are only compared with values of
    their own kind; null is no kind.

    :raises ScalarFunctionError: if the function has no scalar implementation
    :raises TypeError: for a comparison of values of two kinds, for any other
        operator or function with a value that is not a number, and for an
        if() whose condition is a date or a time
    """
    if function in _NULL_AWARE:
        _check_kinds(function, values)
        return _NULL_AWARE[function](*values)
    if function not in _SCALAR:
        msg = f"{function}() cannot be computed for scalar values"
        raise ScalarFunctionError(msg)
    _check_kinds(function, values)
    if function in LEFT_ASSOCIATIVE and len(values) > 2:
        result = values[0]
        for value in values[1:]:
            result = evaluate(function, [result, value])
        return result
    if any(value is None for value in values):
        return None
    return _SCALAR[function](*values)


def _check_maps_with_moments(function, args):
    """Raise TypeError if a map meets a constant date or time

    r.mapcalc has no dates, so plan() would refuse the tree later with a
    message that names neither the function nor a way out.
    """
    for arg in args:
        if isinstance(arg, Const) and value_kind(arg.value) in MOMENT_KINDS:
            msg = (
                f"{function}() cannot combine maps with "
                f"{describe_value(arg.value)}: maps hold numbers; compare time "
                "functions with each other or with a date in quotes, or use the "
                "numbers of time functions such as start_doy() or td()"
            )
            raise TypeError(msg)


def call(function, *args):
    """Return the content of a function applied to contents

    An if without else gets 0 as else, as in r.mapcalc: a cell or map for
    which the condition is false is 0, not null. An if with a
    constant condition is replaced by the chosen branch; with four arguments
    the branches are for a condition above zero, zero and below zero. An
    operator with a null operand is null, as in r.mapcalc. Other calls whose
    arguments are all constants are folded into a constant where Python can
    compute them, with the checks of evaluate().

    :raises ValueError: for an if with fewer than two or more than four
        arguments
    :raises TypeError: for an if whose constant condition is a date or a
        time, for a call of a map with a constant date or time, also as a
        branch of if(), and for the constants that evaluate() refuses
    """
    if function == "if" and not 2 <= len(args) <= 4:
        msg = f"if() takes two to four arguments, got {len(args)}"
        raise ValueError(msg)
    if function == "if" and len(args) == 2:
        # r.mapcalc gives 0 where if(c, t) is false (measured 2026-10-17 with
        # r.mapcalc "z = if(col() > 1, 5)": 0 in the first column), and so did
        # the classic algebra, which handed if() to r.mapcalc.
        args = (*args, Const(0))
    if function == "if" and isinstance(args[0], Const):
        # The branch is chosen here without evaluate(), which would check
        # the condition.
        check_condition("if", args[0].value)
        if args[0].value is None:
            return NULL
        return _if(args[0].value, *args[1:])
    constant = bool(args) and all(isinstance(arg, Const) for arg in args)
    if not constant:
        _check_maps_with_moments(function, args)
        if function in _SCALAR and NULL in args:
            return NULL
    if constant and (function in _SCALAR or function in _NULL_AWARE):
        # evaluate() gives null for a null operand as well, but only after it
        # has checked the kinds, so that a date minus null is refused as a
        # date minus a date is.
        return Const(evaluate(function, [arg.value for arg in args]))
    return Call(function, tuple(args))


def chain(function, contents):
    """Join contents from left to right: ((c1 f c2) f c3) ...

    An operator that r.mapcalc applies from left to right, and min, max, nmin
    and nmax, give one call with all contents, so that the tree stays flat;
    leading constants are folded. Any other function nests to the left.

    :raises ValueError: if contents is empty
    """
    if not contents:
        msg = f"chain({function!r}) needs at least one content"
        raise ValueError(msg)
    if function not in LEFT_ASSOCIATIVE and function not in _VARIADIC:
        result = contents[0]
        for content in contents[1:]:
            result = call(function, result, content)
        return result
    contents = list(contents)
    constants = 0
    while constants < len(contents) and isinstance(contents[constants], Const):
        constants += 1
    if constants > 1:
        contents[:constants] = [call(function, *contents[:constants])]
    if len(contents) == 1:
        return contents[0]
    return call(function, *contents)


def series_reduce(method, contents):
    """Return the reduction of contents that skips null, folded if constant

    :param method: "sum" or "average", the method names of r.series
    :param contents: the Content objects to reduce, one for each map; if all
        are constants the result is folded into one constant, otherwise a
        SeriesReduce node is returned
    :raises TypeError: if a constant is a date or a time
    """
    if not all(isinstance(content, Const) for content in contents):
        return SeriesReduce(method, tuple(contents))
    present = [content.value for content in contents if content.value is not None]
    for value in present:
        if value_kind(value) in MOMENT_KINDS:
            _refuse_computing(method, value)
    if not present:
        return NULL
    total = sum(present)
    return Const(total if method == "sum" else total / len(present))


def series_aggregate(method, contents, file_limit=1000, weights=None):
    """Return the r.series aggregation of contents

    :param weights: None, or one weight for each content
    :raises ValueError: if weights is not of the length of contents
    """
    contents = tuple(contents)
    if weights is not None:
        weights = tuple(weights)
        if len(weights) != len(contents):
            msg = f"{len(contents)} contents need as many weights, got {len(weights)}"
            raise ValueError(msg)
    return SeriesAggregate(method, contents, file_limit, weights)
