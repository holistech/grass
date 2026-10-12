"""Translation of the syntax tree onto the core operations

Each node becomes the core call that the translation table of the algebra
names. A value is a series, a content node (numbers, null() and expressions
of numbers) or a text; a text stands only in comparisons with time functions
and as the increment of tshift() and buff_t().
"""

from __future__ import annotations

from grass.temporal.algebra import operations, time_functions
from grass.temporal.algebra.content import NULL, Const, call
from grass.temporal.algebra.reducers import fold
from grass.temporal.algebra.relations import TEMPORAL_RELATIONS, Relation
from grass.temporal.algebra.series import Series, Slot
from grass.temporal.algebra.sources import source, source_map

from . import ast
from .operators import TemporalOperator

_EXTENTS = {"l": "target", "u": "union", "i": "intersection", "d": "disjoint"}
_CELL_FUNCTIONS = (
    "abs",
    "acos",
    "asin",
    "cos",
    "double",
    "exp",
    "float",
    "int",
    "isnull",
    "log",
    "sin",
    "sqrt",
    "tan",
)
_COMPARISONS = ("==", "!=", "<", "<=", ">", ">=")


def _timed(value):
    return isinstance(value, Series) and not value.timeless


class Translator:
    """Translate statements of the algebra into series

    resolve(name) gives the series of a space time dataset and
    resolve_map(name, timestamp=...) the series of a single map; tests pass
    functions that build series in memory. With spatial, every relation also
    asks for spatially related maps.
    """

    def __init__(self, *, spatial=False, resolve=None, resolve_map=None):
        self._spatial = spatial
        self._resolve = resolve or source
        self._resolve_map = resolve_map or source_map
        self._datasets = {}

    def statement(self, node):
        """Return the name of the result and its series

        :raises ValueError: if the expression gives no series
        """
        result = self.value(node.expression)
        if not isinstance(result, Series):
            msg = f"The expression of {node.target} gives no space time dataset"
            raise ValueError(msg)
        return node.target, result

    def value(self, node):
        """Return the series, content node or text of a syntax tree node"""
        return getattr(self, f"_{type(node).__name__.lower()}")(node)

    @staticmethod
    def _number(node):
        return Const(node.value)

    @staticmethod
    def _text(node):
        return node.value

    def _name(self, node):
        # A dataset that occurs several times is read once, so that all its
        # occurrences are the same series.
        if node.ident not in self._datasets:
            self._datasets[node.ident] = self._resolve(node.ident)
        return self._datasets[node.ident]

    def _negative(self, node):
        return self._apply("neg", self.value(node.operand))

    def _index(self, node):
        series = self._name(ast.Name(node.name))
        offsets = node.offsets
        if len(offsets) == 1:
            return time_functions.neighbour(series, offsets[0])
        if len(offsets) == 3:
            series = time_functions.neighbour(series, offsets[2])
        if len(offsets) in (2, 3):
            return operations.cell_offset(series, *offsets[:2])
        msg = f"{node.name}[...] takes one, two or three offsets"
        raise SyntaxError(msg)

    def _binary(self, node):
        left, right = self.value(node.left), self.value(node.right)
        symbol = node.symbol
        operator = node.operator or TemporalOperator(symbol)
        if symbol in (":", "!:"):
            return self._select(left, right, operator)
        if symbol == "#":
            return self._count(left, right, operator)
        if symbol in ("&&", "||"):
            return self._logical(symbol, left, right, node.operator)
        if symbol in _COMPARISONS:
            return self._compare(symbol, left, right)
        return self._arithmetic(symbol, left, right, node.operator)

    def _relation(self, operator):
        names = frozenset(operator.relations)
        temporal = names & frozenset(TEMPORAL_RELATIONS)
        spatial = names - temporal
        if spatial and not self._spatial:
            msg = (
                f"The spatial relations {', '.join(sorted(spatial))} need the "
                "spatial flag"
            )
            raise ValueError(msg)
        if self._spatial:
            # An empty set asks for maps that are related in space at all.
            return Relation(temporal, spatial)
        return Relation(temporal)

    @staticmethod
    def _pair(symbol, left, right):
        if not (_timed(left) and _timed(right)):
            msg = f"The operator {symbol} relates two space time datasets"
            raise SyntaxError(msg)

    def _select(self, left, right, operator):
        self._pair(operator.symbol, left, right)
        relation = self._relation(operator)
        if operator.symbol == "!:":
            if operator.temporal != "l":
                msg = (
                    "An inverse selection keeps the maps without related map, "
                    "so it takes no temporal reference other than l"
                )
                raise SyntaxError(msg)
            return operations.select(left, relation, right, related=False)
        if operator.temporal == "l":
            return operations.select(left, relation, right)
        if operator.temporal == "r":
            return operations.pairs(left, relation, right, extent="right")
        return operations.gather(
            left, relation, right, reduce=None, extent=_EXTENTS[operator.temporal]
        )

    def _count(self, left, right, operator):
        self._pair("#", left, right)
        if operator.temporal != "l":
            msg = (
                "The hash operator keeps the time stamps of the left maps, so "
                "it takes no temporal reference other than l"
            )
            raise SyntaxError(msg)
        return operations.gather(left, self._relation(operator), right, reduce="count")

    def _arithmetic(self, symbol, left, right, operator):
        if _timed(left) and _timed(right):
            return self._combine(
                symbol, left, right, operator or TemporalOperator(symbol), fold(symbol)
            )
        if operator is not None:
            msg = (
                f"The temporal operator {{{symbol},...}} relates two space time "
                "datasets"
            )
            raise SyntaxError(msg)
        return self._apply(symbol, left, right)

    def _combine(self, symbol, left, right, operator, reduce):
        relation = self._relation(operator)
        if operator.temporal == "r":
            return operations.pairs(
                left,
                relation,
                right,
                extent="right",
                content=lambda mine, theirs: call(symbol, mine, theirs),
            )
        return operations.gather(
            left, relation, right, reduce=reduce, extent=_EXTENTS[operator.temporal]
        )

    @staticmethod
    def _apply(function, *operands):
        for operand in operands:
            if isinstance(operand, str):
                msg = (
                    f"A text such as '{operand}' stands only in comparisons with "
                    "time functions and as the increment of tshift() and buff_t()"
                )
                raise TypeError(msg)
        if any(_timed(operand) for operand in operands):
            return operations.apply(function, *operands)
        maps = [operand for operand in operands if isinstance(operand, Series)]
        if not maps:
            return call(function, *operands)
        # apply() takes its time stamps from a timed operand, so maps
        # without time stamp, as in map(L) + 1, are combined here and stay
        # a map without time stamp.
        contents = (
            operand.slots[0].content if isinstance(operand, Series) else operand
            for operand in operands
        )
        return Series(
            (Slot(None, call(function, *contents), maps[0].slots[0].space),),
            kind=maps[0].kind,
        )

    def _compare(self, symbol, left, right):
        msg = "conditions follow"
        raise NotImplementedError(msg)

    def _logical(self, symbol, left, right, operator):
        msg = "conditions follow"
        raise NotImplementedError(msg)

    def _if(self, arguments, relation):
        msg = "conditions follow"
        raise NotImplementedError(msg)

    def _function(self, node):
        name = node.name
        if name in ("tmap", "map"):
            return self._single_map(node)
        if node.relation is not None and name != "if":
            msg = f"{name}() takes no relation"
            raise SyntaxError(msg)
        arguments = [self.value(argument) for argument in node.arguments]
        if name == "if":
            return self._if(arguments, node.relation)
        if name in _CELL_FUNCTIONS:
            return self._apply(name, *_exactly(name, arguments, 1))
        if name == "isntnull":
            return self._apply(
                "!", self._apply("isnull", *_exactly(name, arguments, 1))
            )
        if name == "exist":
            return _exactly(name, arguments, 1)[0]
        if name == "null":
            _exactly(name, arguments, 0)
            return NULL
        if name in time_functions.TIMEVARS:
            return self._time_variable(name, arguments)
        if name == "tsnap":
            return time_functions.retime(*_exactly(name, arguments, 1), snap=True)
        if name in ("tshift", "buff_t"):
            series, increment = _exactly(name, arguments, 2)
            keyword = "shift" if name == "tshift" else "buffer"
            return time_functions.retime(series, **{keyword: _increment(increment)})
        if name == "merge":
            return operations.merge(*_exactly(name, arguments, 2))
        msg = f"Unknown function {name}()"
        raise SyntaxError(msg)

    def _single_map(self, node):
        arguments = node.arguments
        if (
            node.relation is not None
            or len(arguments) != 1
            or not isinstance(arguments[0], ast.Name)
        ):
            msg = f"{node.name}() takes the name of one map"
            raise SyntaxError(msg)
        return self._resolve_map(arguments[0].ident, timestamp=node.name == "tmap")

    @staticmethod
    def _time_variable(name, arguments):
        if len(arguments) not in (1, 2):
            msg = f"{name}() takes a dataset and an optional offset"
            raise SyntaxError(msg)
        variable = time_functions.timevar(arguments[0], name)
        if len(arguments) == 1:
            return variable
        # start_doy(A, -1) is the value of the map before, at the time stamp
        # of each map: neighbour() takes the content and keeps the extent.
        return time_functions.neighbour(variable, _whole(arguments[1], name))


def _exactly(name, arguments, count):
    if len(arguments) != count:
        msg = f"{name}() takes {count} argument{'' if count == 1 else 's'}"
        raise SyntaxError(msg)
    return arguments


def _whole(value, name):
    if not (isinstance(value, Const) and isinstance(value.value, int)):
        msg = f"The offset of {name}() is a whole number"
        raise SyntaxError(msg)
    return value.value


def _increment(value):
    if isinstance(value, str):
        return value
    if isinstance(value, Const) and isinstance(value.value, int):
        return value.value
    msg = (
        "The increment of tshift() and buff_t() is a text such as "
        '"1 month" or a whole number'
    )
    raise SyntaxError(msg)
