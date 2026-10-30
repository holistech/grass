"""Content of the slots of a series: immutable expression trees

A tree says what a map contains, not how it is computed, so it is independent
of the module that could compute it. Scalar values, one value per slot such
as the length of an interval, are folded into constants while a tree is
built, so a tree without map references can be decided in Python.

Every class has a field mark that the core neither sets nor reads. A variant
of the algebra attaches an identity to a content with it, for the maps that
it tells apart although their trees are equal. The mark takes no part in
equality, hash or repr, so two contents that differ only in their mark are
equal and the core cannot tell them apart.
"""

import math
import operator
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MapRef:
    """A registered map, optionally read at a cell offset (row, column)"""

    ident: str
    offset: tuple[int, ...] = ()
    mark: object = field(default=None, compare=False, repr=False, kw_only=True)


@dataclass(frozen=True)
class Const:
    """A constant value; None is null"""

    value: object = None
    mark: object = field(default=None, compare=False, repr=False, kw_only=True)


@dataclass(frozen=True)
class Call:
    """An operator or a function of the raster algebra applied to contents"""

    function: str
    args: tuple
    mark: object = field(default=None, compare=False, repr=False, kw_only=True)


@dataclass(frozen=True)
class SeriesReduce:
    """A reduction over maps that passes over null cells

    r.mapcalc has no sum or mean that skips null cells, so this node is kept
    apart from Call; r.series is the module that computes it.
    """

    method: str
    args: tuple
    mark: object = field(default=None, compare=False, repr=False, kw_only=True)


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
    """

    method: str
    args: tuple
    file_limit: int = 1000
    mark: object = field(default=None, compare=False, repr=False, kw_only=True)


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

    A profile that lets r.mapcalc compute such a function on the maps of a
    scalar series (the classic algebra does) catches this class.
    """


def evaluate(function, values):
    """Compute an operator or a function of r.mapcalc on scalar values

    An operator with more than two operands is applied from left to right.

    :raises ScalarFunctionError: if the function has no scalar implementation
    """
    if function in _NULL_AWARE:
        return _NULL_AWARE[function](*values)
    if function not in _SCALAR:
        msg = f"{function}() cannot be computed for scalar values"
        raise ScalarFunctionError(msg)
    if function in LEFT_ASSOCIATIVE and len(values) > 2:
        result = values[0]
        for value in values[1:]:
            result = evaluate(function, [result, value])
        return result
    if any(value is None for value in values):
        return None
    return _SCALAR[function](*values)


def call(function, *args):
    """Return the content of a function applied to contents

    An if without else gets 0 as else, as in r.mapcalc: a cell or map for
    which the condition is false is 0, not null. An if with a
    constant condition is replaced by the chosen branch; with four arguments
    the branches are for a condition above zero, zero and below zero. An
    operator with a null operand is null, as in r.mapcalc. Other calls whose
    arguments are all constants are folded into a constant where Python can
    compute them.

    :raises ValueError: for an if with fewer than two or more than four
        arguments
    """
    if function == "if" and not 2 <= len(args) <= 4:
        msg = f"if() takes two to four arguments, got {len(args)}"
        raise ValueError(msg)
    if function == "if" and len(args) == 2:
        # r.mapcalc gives 0 where if(c, t) is false (measured 2026-10-17 with
        # r.mapcalc "z = if(col() > 1, 5)": 0 in the first column), and so did
        # the earlier implementation of the algebra.
        args = (*args, Const(0))
    if function == "if" and isinstance(args[0], Const):
        condition = args[0].value
        if condition is None:
            return NULL
        if len(args) == 4:
            if condition > 0:
                return args[1]
            return args[2] if condition == 0 else args[3]
        return args[1] if condition else args[2]
    if function in _SCALAR and NULL in args:
        return NULL
    foldable = function in _SCALAR or function in _NULL_AWARE
    if foldable and args and all(isinstance(arg, Const) for arg in args):
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
    """
    if not all(isinstance(content, Const) for content in contents):
        return SeriesReduce(method, tuple(contents))
    present = [content.value for content in contents if content.value is not None]
    if not present:
        return NULL
    total = sum(present)
    return Const(total if method == "sum" else total / len(present))


def series_aggregate(method, contents, file_limit=1000):
    """Return the r.series aggregation of contents"""
    return SeriesAggregate(method, tuple(contents), file_limit)
