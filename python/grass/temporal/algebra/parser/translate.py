"""Translation of the syntax tree onto the core operations

Each node becomes the core call that the translation table of the algebra
names. A value is a series, a content node (numbers, null() and expressions
of numbers) or a text; a text stands only in comparisons with time functions
and as the increment of tshift() and buff_t().
"""

from __future__ import annotations

import datetime

from grass.temporal.algebra import operations, time_functions
from grass.temporal.algebra.content import NULL, Const, call
from grass.temporal.algebra.reducers import fold
from grass.temporal.algebra.relations import TEMPORAL_RELATIONS, Relation, inverse
from grass.temporal.algebra.series import Series, Slot
from grass.temporal.algebra.sources import source, source_map
from grass.temporal.datetime_math import check_datetime_string

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
_OTHER_FUNCTIONS = (
    "buff_t",
    "exist",
    "if",
    "isntnull",
    "merge",
    "null",
    "tshift",
    "tsnap",
)
_COMPARISONS = ("==", "!=", "<", "<=", ">", ">=")
_AGGREGATES = {"&": "all", "|": "any"}
# Marks an if() without else, which differs from an else of null().
_ABSENT = object()


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
        if isinstance(left, str):
            left = _moment(left, right)
        if isinstance(right, str):
            right = _moment(right, left)
        return self._apply(symbol, left, right)

    def _logical(self, symbol, left, right, operator):
        if not (_timed(left) and _timed(right)):
            if operator is not None:
                msg = (
                    f"The temporal operator {{{symbol},...}} relates two space "
                    "time datasets"
                )
                raise SyntaxError(msg)
            return self._apply(symbol, left, right)
        if operator is None:
            operator = TemporalOperator(symbol, aggregate=symbol[0])
        relation = self._relation(operator)
        if operator.temporal == "r":
            return operations.pairs(
                left,
                relation,
                right,
                extent="right",
                content=lambda mine, theirs: call(symbol, mine, theirs),
            )
        extent = _EXTENTS[operator.temporal]
        # The left maps that have related maps, and the joined conditions of
        # those related maps; both have the same time stamps.
        targets = operations.gather(left, relation, right, reduce=None, extent=extent)
        others = operations.gather(
            left,
            relation,
            right,
            reduce=_AGGREGATES[operator.aggregate],
            extent=extent,
        )
        return operations.apply(symbol, targets, others)

    def _if(self, arguments, relation):
        if len(arguments) not in (2, 3):
            msg = "if() takes a condition, then and an optional else"
            raise SyntaxError(msg)
        condition, then = arguments[:2]
        otherwise = arguments[2] if len(arguments) == 3 else _ABSENT
        if not isinstance(condition, Series):
            msg = "The condition of if() needs a space time dataset"
            raise SyntaxError(msg)
        if condition.timeless:
            if relation is not None:
                msg = "The relation of if() needs a condition with time stamps"
                raise SyntaxError(msg)
            return _where(condition, then, otherwise)
        first = next((branch for branch in (then, otherwise) if _timed(branch)), None)
        if first is None:
            # Only numbers or maps without time stamp: the maps of the
            # condition are the result.
            if relation is not None:
                msg = "The relation of if() needs a space time dataset as then or else"
                raise SyntaxError(msg)
            if condition.sort == "field":
                return _where(condition, then, otherwise)
            return operations.choose(
                condition,
                _like(condition, then),
                None if otherwise is _ABSENT else _like(condition, otherwise),
            )
        operator = relation or TemporalOperator(None)
        conditions = self._conditions(first, condition, operator)
        if conditions.sort == "field":
            # A condition per cell chooses between then and else in each
            # cell, so where() needs both with the same time stamps.
            return _where(conditions, then, otherwise)
        then_maps = then if _timed(then) else _like(first, then)
        if otherwise is _ABSENT:
            return operations.choose(conditions, then_maps)
        settled = _settled(conditions, relation)
        if not _timed(otherwise):
            return operations.choose(settled, then_maps, _like(first, otherwise))
        if not _timed(then):
            return operations.choose(settled, then_maps, otherwise)
        # Then and else have time stamps of their own; each map is judged by
        # the conditions related to it.
        others = self._conditions(otherwise, condition, operator)
        return operations.merge(
            operations.choose(conditions, then),
            operations.choose(
                operations.apply("!", _settled(others, relation)), otherwise
            ),
        )

    def _conditions(self, target, condition, operator):
        """The joined condition of each map of target

        if({R}, c, X) reads "c R x", so the maps of X are related to the
        conditions by the inverse of R.
        """
        return operations.gather(
            target,
            inverse(self._relation(operator)),
            condition,
            reduce=_AGGREGATES[operator.aggregate],
            missing="null",
            equal_times="pairwise",
        )

    def _function(self, node):
        name = node.name
        if name in ("tmap", "map"):
            return self._single_map(node)
        # The name is checked before the arguments are read, so that an
        # unknown function is reported as such and reads no dataset.
        if name not in (*_CELL_FUNCTIONS, *_OTHER_FUNCTIONS, *time_functions.TIMEVARS):
            msg = f"Unknown function {name}()"
            raise SyntaxError(msg)
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
        # merge is the only known name left.
        return operations.merge(*_exactly(name, arguments, 2))

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


def _where(condition, then, otherwise):
    if otherwise is _ABSENT:
        return operations.where(condition, then)
    return operations.where(condition, then, otherwise)


def _settled(conditions, relation):
    """The scalar conditions by which else chooses its maps

    With a temporal relation beyond equal, else also takes the maps without
    related condition, whose condition is null, as the paper that
    introduced the algebra defines it (Gebbert, Leppelt and Pebesma 2019,
    section 3.2.1); then leaves them out. Without such a relation the
    condition speaks of maps of equal time only, so a map of other time
    stays out of both branches, and if({equal}, ...) means the same as
    if(...).
    """
    beyond_equal = set(TEMPORAL_RELATIONS) - {"equal"}
    if relation is None or not set(relation.relations) & beyond_equal:
        return conditions
    return operations.apply("if", operations.apply("isnull", conditions), 0, conditions)


def _like(series, value):
    """A series with the time stamps of series and value as each content

    value is a content node or a map without time stamp.
    """
    if isinstance(value, str):
        msg = f"A text such as '{value}' cannot be a branch of if()"
        raise TypeError(msg)
    content = value.slots[0].content if isinstance(value, Series) else value
    return Series(
        tuple(Slot(slot.extent, content, slot.space) for slot in series),
        kind=series.kind,
        spatial=series.spatial,
    )


def _sample(series):
    """The first value of a scalar series that is not null"""
    return next(
        (
            slot.content.value
            for slot in series
            if isinstance(slot.content, Const) and slot.content.value is not None
        ),
        None,
    )


def _moment(text, other):
    """Read a date, a time or both for a comparison with a time function

    The text is read as the time stamps of grass.temporal are, so with
    dateutil installed also in formats other than ISO and as a time of day
    alone. It then takes the kind of the values it is compared with, as the
    classic algebra does: the date for start_date(), the time of day for
    start_time() and both for start_datetime().

    :raises TypeError: if other is not a series of dates or times
    :raises ValueError: if the text is no date or time
    """
    if not (isinstance(other, Series) and other.sort == "scalar"):
        msg = (
            f"A text such as '{text}' can only be compared with the time "
            "functions, such as start_date()"
        )
        raise TypeError(msg)
    sample = _sample(other)
    # start_day() and td() are scalar too, but give numbers; a time of day
    # would compare unequal to them without an error.
    if sample is not None and not isinstance(sample, (datetime.date, datetime.time)):
        msg = (
            f"'{text}' cannot be compared with numbers such as those of "
            "start_day() or td(); start_date(), start_time() and "
            "start_datetime() give dates and times"
        )
        raise TypeError(msg)
    # string_to_datetime() would report the error through the messenger of
    # grass.temporal, which exists only after tgis.init().
    moment = check_datetime_string(text)
    if not isinstance(moment, datetime.datetime):
        msg = f"'{text}' is not a date or time: {moment}"
        raise ValueError(msg)
    if isinstance(sample, datetime.time):
        return Const(moment.time())
    # datetime is a subclass of date, so it is checked first.
    if sample is None or isinstance(sample, datetime.datetime):
        return Const(moment)
    return Const(moment.date())
