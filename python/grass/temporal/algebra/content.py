"""Content of the slots of a series: immutable expression trees

A tree says what a map contains, not how it is computed; the backend of the
map type turns it into module calls when a series is materialized. Scalar
values, one value per slot such as the length of an interval, are folded
into constants while a tree is built, so a tree without map references can
be decided in Python.
"""

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

    r.mapcalc has no sum or mean that skips null cells, so the backend
    computes this node with r.series.
    """

    method: str
    args: tuple


Content = MapRef | Const | Call | SeriesReduce

NULL = Const(None)


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


def _if(condition, then, otherwise=None):
    if condition is None:
        return None
    return then if condition else otherwise


def _skipping(function):
    def reduce(*values):
        present = [value for value in values if value is not None]
        return function(present) if present else None

    return reduce


# Scalar implementations of r.mapcalc operators. As in r.mapcalc,
# comparisons give 1 or 0 and a null operand gives null.
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


def evaluate(function, values):
    """Compute an operator or a function of r.mapcalc on scalar values

    :raises ValueError: if the function has no scalar implementation
    """
    if function in _NULL_AWARE:
        return _NULL_AWARE[function](*values)
    if function not in _SCALAR:
        msg = f"{function}() cannot be computed for scalar values"
        raise ValueError(msg)
    if any(value is None for value in values):
        return None
    return _SCALAR[function](*values)


def call(function, *args):
    """Return the content of a function applied to contents

    An if without else gets null as else: a cell or map for which the
    condition is false is null, not the 0 of r.mapcalc. An if with a
    constant condition is replaced by the chosen branch. An operator with a
    null operand is null, as in r.mapcalc. Other calls whose arguments are
    all constants are folded into a constant where Python can compute them.
    """
    if function == "if" and len(args) == 2:
        args = (*args, NULL)
    if function == "if" and isinstance(args[0], Const):
        condition = args[0].value
        if condition is None:
            return NULL
        return args[1] if condition else args[2]
    if function in _SCALAR and NULL in args:
        return NULL
    foldable = function in _SCALAR or function in _NULL_AWARE
    if foldable and args and all(isinstance(arg, Const) for arg in args):
        return Const(evaluate(function, [arg.value for arg in args]))
    return Call(function, tuple(args))


def chain(function, contents):
    """Join contents from left to right: ((c1 f c2) f c3) ..."""
    result = contents[0]
    for content in contents[1:]:
        result = call(function, result, content)
    return result


def series_reduce(method, contents):
    """Return the reduction of contents that skips null, folded if constant

    :param method: "sum" or "average", the method names of r.series
    """
    if not all(isinstance(content, Const) for content in contents):
        return SeriesReduce(method, tuple(contents))
    present = [content.value for content in contents if content.value is not None]
    if not present:
        return NULL
    total = sum(present)
    return Const(total if method == "sum" else total / len(present))
