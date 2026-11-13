"""Translation of the syntax tree onto the core operations

Each node type has a method named after it that computes the value of the
node from the values of its children with the core operations; the grammar
only builds nodes, so the meaning of the syntax is all in this module. A
value is a series, a content node (numbers, null() and expressions of
numbers) or a text; a text stands only in comparisons with time functions
and as the increment of tshift() and buff_t().

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import dataclasses
import datetime
import functools

from grass.temporal.algebra import operations, time_functions
from grass.temporal.algebra.backends import BUFFER_TYPES, PATCH, VECTOR_FUNCTIONS
from grass.temporal.algebra.content import (
    COMPARISONS,
    NULL,
    Const,
    call,
    check_condition,
    value_kind,
)
from grass.temporal.algebra.maptypes import OFFSET_COUNTS, STDS_TYPES
from grass.temporal.algebra.reducers import compare, fold
from grass.temporal.algebra.relations import TEMPORAL_RELATIONS, Relation, inverse
from grass.temporal.algebra.series import Series, Slot
from grass.temporal.algebra.sources import source, source_map
from grass.temporal.datetime_math import check_datetime_string

from . import ast
from .operators import TemporalOperator
from .shared import (
    ABSENT,
    EXTENTS,
    check_time_variable,
    timed,
    vector_field,
    whole,
)

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
    "buff_a",
    "buff_l",
    "buff_p",
    "buff_t",
    "exist",
    "if",
    "isntnull",
    "merge",
    "null",
    "tshift",
    "tsnap",
)
_AGGREGATES = {"&": "all", "|": "any"}
# The overlays of vector maps; + is the v.patch of vector maps.
_OVERLAYS = {"&": "and", "|": "or", "^": "xor", "~": "not"}
# The functions of t.select that name the type of a dataset, in lower case and
# in the capitals of the published paper
_DATASET_FUNCTIONS = ("strds", "str3ds", "stvds", "STRDS", "STR3DS", "STVDS")
# The forms of an index per number of cell offsets of a map type: A[t] is a
# temporal neighbour, the others read cells at an offset, with a temporal
# neighbour as last number.
_INDEX_FORMS = {
    0: "one offset",
    2: "one, two or three offsets",
    3: "one, three or four offsets",
}


class Translator:
    """Translate statements of the algebra into series

    resolve(name) gives the series of a space time dataset and
    resolve_map(name, timestamp=...) the series of a single map; tests pass
    functions that build series in memory. With spatial, every relation also
    asks for spatially related maps. kind is the map type of the datasets; it
    decides what + means and which indexes and functions exist. selection says
    that the expression selects registered maps (t.select) and computes none:
    strds(), str3ds() and stvds() then name datasets of other map types, which
    are related by time and box only, and the result may not be a time
    function.
    """

    def __init__(
        self,
        *,
        kind="raster",
        spatial=False,
        resolve=None,
        resolve_map=None,
        selection=False,
    ):
        self._kind = kind
        self._spatial = spatial
        self._selection = selection
        self._resolve = resolve or functools.partial(source, stds_type=STDS_TYPES[kind])
        self._resolve_map = resolve_map or functools.partial(source_map, kind=kind)
        self._datasets = {}

    def statement(self, node):
        """Return the name of the result and its series

        :raises ValueError: if the expression gives no series
        :raises SyntaxError: if a vector expression gives numbers
        """
        result = self.value(node.expression)
        if not isinstance(result, Series):
            msg = f"The expression of {node.target} gives no space time dataset"
            raise ValueError(msg)
        # Checked on the sort rather than on the contents: a count whose
        # relation finds no pair has no slot to look at, and would otherwise
        # pass as an empty dataset.
        if self._kind == "vector" and result.sort != "field":
            msg = (
                f"The expression of {node.target} gives numbers, not vector maps; "
                "numbers such as td() or the hash operator belong in a condition"
            )
            raise SyntaxError(msg)
        return node.target, result

    def value(self, node):
        """Return the series, content node or text of a syntax tree node

        The method is chosen by the class name of the node: _number for
        ast.Number, _negative for ast.Negative, and so on for _text, _name,
        _index, _binary and _function. Apart from _name, which _index also
        calls, none of them is called by name, so a search for a caller finds
        only this method.
        """
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
        # The count is checked before the dataset is read, so that a wrong
        # count is reported even for a missing dataset.
        offsets = node.offsets
        axes = OFFSET_COUNTS[self._kind]
        if len(offsets) != 1 and (not axes or len(offsets) not in (axes, axes + 1)):
            msg = f"{node.name}[...] takes {_INDEX_FORMS[axes]} for {self._kind} maps"
            raise SyntaxError(msg)
        series = self._name(ast.Name(node.name))
        if len(offsets) == 1:
            return time_functions.neighbour(series, offsets[0])
        if len(offsets) == axes + 1:
            series = time_functions.neighbour(series, offsets[-1])
        return operations.cell_offset(series, *offsets[:axes])

    def _operands(self, node):
        """Return the values of the left and right operand of a binary node"""
        return self.value(node.left), self.value(node.right)

    def _binary(self, node):
        left, right = self._operands(node)
        return self._binary_values(node, left, right)

    def _binary_values(self, node, left, right):
        """Return the value of a binary node from the values of its operands"""
        symbol = node.symbol
        operator = node.operator or TemporalOperator(symbol)
        if symbol in (":", "!:"):
            return self._select(left, right, operator)
        if symbol == "#":
            return self._count(left, right, operator)
        if symbol in _OVERLAYS or (symbol == "+" and vector_field(left, right)):
            return self._overlay(symbol, left, right, node.operator)
        if vector_field(left, right):
            msg = (
                f"The operator {symbol} is not defined for vector maps; they are "
                "combined with &, |, ^, ~ and +"
            )
            raise SyntaxError(msg)
        if symbol in ("&&", "||"):
            return self._logical(symbol, left, right, node.operator)
        if symbol in COMPARISONS:
            if node.operator is not None:
                return self._compare_related(symbol, left, right, node.operator)
            return self._compare(symbol, left, right)
        return self._arithmetic(symbol, left, right, node.operator)

    def _relation(self, operator):
        names = frozenset(operator.relations)
        temporal = names & frozenset(TEMPORAL_RELATIONS)
        spatial = names - temporal
        if spatial or self._spatial:
            # A spatial name asks for spatially related maps also without the
            # flag, as in the classic algebra; the paper prints such an
            # expression without it. With the flag alone, an empty set asks
            # for maps that are related in space at all.
            return Relation(temporal, spatial)
        return Relation(temporal)

    def _aligned(self, left, right):
        """right as a series of the map type of left in a selection

        t.select relates maps of different dataset types (strds(A) :
        stvds(B)), which the operations refuse where the maps of both meet in
        one result, as in A {+,during} stvds(B). Only time and box matter for
        the relation, and plan() refuses a selection that computes maps.
        Elsewhere the types are fixed by the tool and stay as they are.
        """
        if not self._selection or right.kind == left.kind:
            return right
        return dataclasses.replace(right, kind=left.kind)

    @staticmethod
    def _pair(symbol, left, right):
        if not (timed(left) and timed(right)):
            msg = f"The operator {symbol} relates two space time datasets"
            raise SyntaxError(msg)

    def _select(self, left, right, operator):
        self._pair(operator.symbol, left, right)
        right = self._aligned(left, right)
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
            left, relation, right, reduce=None, extent=EXTENTS[operator.temporal]
        )

    def _count(self, left, right, operator):
        self._pair("#", left, right)
        right = self._aligned(left, right)
        if operator.temporal != "l":
            msg = (
                "The hash operator keeps the time stamps of the left maps, so "
                "it takes no temporal reference other than l"
            )
            raise SyntaxError(msg)
        return operations.gather(left, self._relation(operator), right, reduce="count")

    def _overlay(self, symbol, left, right, operator):
        timed_vectors = all(
            timed(value) and vector_field(value) for value in (left, right)
        )
        if not timed_vectors:
            msg = f"The overlay {symbol} combines two space time vector datasets"
            raise SyntaxError(msg)
        function = _OVERLAYS.get(symbol, PATCH)
        # An overlay with and lies within its inputs, the others within the
        # box around them, as in the classic algebra.
        space = "intersection" if function == "and" else "union"
        return self._combine(
            function,
            left,
            right,
            operator or TemporalOperator(symbol),
            fold(function),
            space=space,
        )

    def _arithmetic(self, symbol, left, right, operator):
        if timed(left) and timed(right):
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

    def _combine(self, symbol, left, right, operator, reduce, *, space="keep"):
        right = self._aligned(left, right)
        relation = self._relation(operator)
        if operator.temporal == "r":
            return operations.pairs(
                left,
                relation,
                right,
                extent="right",
                content=lambda mine, theirs: call(symbol, mine, theirs),
                space=space,
            )
        return operations.gather(
            left,
            relation,
            right,
            reduce=reduce,
            extent=EXTENTS[operator.temporal],
            space=space,
        )

    def _apply(self, function, *operands):
        if vector_field(*operands) and function not in VECTOR_FUNCTIONS:
            msg = (
                f"{function}() is not defined for vector maps; they are "
                "combined with &, |, ^, ~ and +"
            )
            raise SyntaxError(msg)
        for operand in operands:
            if isinstance(operand, str):
                msg = (
                    f"A text such as '{operand}' stands only in comparisons with "
                    "time functions and as the increment of tshift() and buff_t()"
                )
                raise TypeError(msg)
        if any(timed(operand) for operand in operands):
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
        _refuse_number_with_moments(left, right)
        _refuse_number_with_moments(right, left)
        _refuse_values_of_different_kinds(left, right)
        return self._apply(symbol, left, right)

    def _compare_related(self, symbol, left, right, operator):
        """Return a comparison with a temporal relation

        Each left map is compared with every related map, and the comparisons
        are joined by the aggregation of the operator, (a1 >= f1 && a1 >= f2).
        With the temporal reference r every pair is compared on its own and
        takes the time stamp of the right map, as in _logical().
        """
        if not (timed(left) and timed(right)):
            msg = (
                f"The temporal operator {{{symbol},...}} relates two space "
                "time datasets"
            )
            raise SyntaxError(msg)
        _refuse_values_of_different_kinds(left, right)
        return self._combine(
            symbol, left, right, operator, compare(symbol, operator.aggregate)
        )

    def _logical(self, symbol, left, right, operator):
        if not (timed(left) and timed(right)):
            if operator is not None:
                msg = (
                    f"The temporal operator {{{symbol},...}} relates two space "
                    "time datasets"
                )
                raise SyntaxError(msg)
            return self._apply(symbol, left, right)
        right = self._aligned(left, right)
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
        extent = EXTENTS[operator.temporal]
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
        otherwise = arguments[2] if len(arguments) == 3 else ABSENT
        if self._kind == "vector" and not all(
            vector_field(branch) for branch in arguments[1:]
        ):
            # A number in one branch would become the content of a map,
            # which no vector module can compute.
            msg = "if() on vector datasets chooses between vector maps, not numbers"
            raise SyntaxError(msg)
        if not isinstance(condition, Series):
            msg = "The condition of if() needs a space time dataset"
            raise SyntaxError(msg)
        if vector_field(condition):
            msg = (
                "Conditions on vector maps take temporal variables such as td() "
                "or start_doy(), or the hash operator"
            )
            raise SyntaxError(msg)
        if condition.timeless:
            if relation is not None:
                msg = "The relation of if() needs a condition with time stamps"
                raise SyntaxError(msg)
            return _where(condition, then, otherwise)
        first = next((branch for branch in (then, otherwise) if timed(branch)), None)
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
                _constant_like(condition, then),
                None if otherwise is ABSENT else _constant_like(condition, otherwise),
            )
        return self._temporal_if(condition, then, otherwise, relation, first)

    def _temporal_if(self, condition, then, otherwise, relation, first):
        """Choose between then and else by a condition with time stamps

        first is the first of then and else that has time stamps. Without
        else, otherwise is the marker ABSENT. A condition per cell chooses in
        each cell, so where() takes the joined conditions and both branches
        with the same time stamps.
        """
        # The conditions are joined with != 0 below, so a date would be
        # refused there in the name of an operator the expression lacks.
        for value in _values(condition):
            check_condition("if", value)
        operator = relation or TemporalOperator(None)
        conditions = self._conditions(first, condition, operator)
        if conditions.sort == "field":
            return _where(conditions, then, otherwise)
        then_maps = then if timed(then) else _constant_like(first, then)
        if otherwise is ABSENT:
            return operations.choose(conditions, then_maps)
        settled = _settled(conditions, relation)
        if not timed(otherwise):
            return operations.choose(
                settled, then_maps, _constant_like(first, otherwise)
            )
        if not timed(then):
            return operations.choose(settled, then_maps, otherwise)
        # Then and else have time stamps of their own; each map is judged by
        # the conditions related to it.
        if self._selection and "scalar" in {then.sort, otherwise.sort}:
            # merge() would refuse the numbers beside maps with a message
            # about sorts of series, which says nothing to a user of t.select.
            self._refuse_time_function()
        others = self._conditions(otherwise, condition, operator)
        return operations.merge(
            operations.choose(conditions, then),
            operations.choose(
                operations.apply("!", _settled(others, relation)), otherwise
            ),
        )

    @staticmethod
    def _refuse_time_function():
        """Stop a selection whose result would be a time function"""
        msg = (
            "A time function such as start_doy() cannot be the result of a "
            "selection: t.select selects maps, and a time function belongs "
            "in the condition of if()"
        )
        raise ValueError(msg)

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
        if self._selection and name in _DATASET_FUNCTIONS:
            return self._dataset_of_type(node)
        # The name is checked before the arguments are read, so that an
        # unknown function is reported as such and reads no dataset.
        if name not in (*_CELL_FUNCTIONS, *_OTHER_FUNCTIONS, *time_functions.TIMEVARS):
            msg = f"Unknown function {name}()"
            raise SyntaxError(msg)
        if node.relation is not None and name != "if":
            msg = f"{name}() takes no relation"
            raise SyntaxError(msg)
        arguments = [self.value(argument) for argument in node.arguments]
        return self._call(name, arguments, node.relation)

    def _dataset_of_type(self, node):
        """strds(A), str3ds(A) and stvds(A): the dataset A as one of this type

        A selection may relate datasets of different types; the type of the
        left function need not be the one of the tool, as in the classic
        algebra. The capitals are the spelling of the published paper.
        """
        if len(node.arguments) != 1 or not isinstance(node.arguments[0], ast.Name):
            msg = f"{node.name}() takes the name of a space time dataset"
            raise SyntaxError(msg)
        ident = node.arguments[0].ident
        stds_type = node.name.lower()
        if (ident, stds_type) not in self._datasets:
            self._datasets[ident, stds_type] = self._resolve(ident, stds_type=stds_type)
        return self._datasets[ident, stds_type]

    def _call(self, name, arguments, relation):
        """Return the value of a known function from the values of its arguments

        tmap() and map() are not among them; _function() reads those.
        """
        if name == "if":
            return self._if(arguments, relation)
        if name in _CELL_FUNCTIONS:
            return self._apply(name, *_exactly(name, arguments, 1))
        if name == "isntnull":
            return self._apply(
                "!", self._apply("isnull", *_exactly(name, arguments, 1))
            )
        if name == "exist":
            return _exactly(name, arguments, 1)[0]
        if name in BUFFER_TYPES:
            series, distance = _exactly(name, arguments, 2)
            if not (
                isinstance(series, Series)
                and series.kind == "vector"
                and isinstance(distance, Const)
                and isinstance(distance.value, (int, float))
            ):
                msg = f"{name}() takes a space time vector dataset and a distance"
                raise SyntaxError(msg)
            return operations.buffer(
                series, distance.value, features=BUFFER_TYPES[name]
            )
        if name == "null":
            _exactly(name, arguments, 0)
            return NULL
        if name in time_functions.TIMEVARS:
            return self._time_variable(name, arguments)
        if name == "tsnap":
            return self._tsnap(*_exactly(name, arguments, 1))
        if name == "tshift":
            return self._tshift(*_exactly(name, arguments, 2))
        if name == "buff_t":
            return self._buff_t(*_exactly(name, arguments, 2))
        # merge is the only known name left.
        return self._merge(*_exactly(name, arguments, 2))

    def _tsnap(self, series):
        """Snap the time stamps of series to its granularity"""
        return time_functions.retime(series, snap=True)

    def _tshift(self, series, increment):
        """Shift the time stamps of series by an increment

        increment is the value of the argument, a text or a Const; the
        conversion to a text or a whole number is done by _increment().
        """
        return time_functions.retime(series, shift=_increment(increment))

    def _buff_t(self, series, increment):
        """Buffer the time stamps of series by an increment

        increment is the value of the argument, a text or a Const; the
        conversion to a text or a whole number is done by _increment().
        """
        return time_functions.retime(series, buffer=_increment(increment))

    def _merge(self, first, second):
        """Keep the maps of both series"""
        return operations.merge(first, second)

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

    def _time_variable(self, name, arguments):
        if len(arguments) not in (1, 2):
            msg = f"{name}() takes a dataset and an optional offset"
            raise SyntaxError(msg)
        variable = time_functions.timevar(arguments[0], name)
        check_time_variable(name, arguments[0])
        if len(arguments) == 1:
            return variable
        # start_doy(A, -1) is the value of the map before, at the time stamp
        # of each map: neighbour() takes the content and keeps the extent.
        return time_functions.neighbour(variable, whole(arguments[1], name))


def _exactly(name, arguments, count):
    if len(arguments) != count:
        msg = f"{name}() takes {count} argument{'' if count == 1 else 's'}"
        raise SyntaxError(msg)
    return arguments


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
    if otherwise is ABSENT:
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


def _constant_like(series, value):
    """A series with the time stamps of series and value as each content

    value is a content node or a map without time stamp. The slots take no
    rank (Slot.rank), so that the result does not depend on the list order
    of series.
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


def _values(series):
    """The values of a scalar series that are not null, in time order"""
    return (
        slot.content.value
        for slot in series
        if isinstance(slot.content, Const) and slot.content.value is not None
    )


def _sample(series):
    """The first value of a scalar series that is not null"""
    return next(_values(series), None)


def _refuse_number_with_moments(number, other):
    """Raise if number is a number and other a series of dates or times

    Python refuses < between a date and a number with a TypeError that names
    neither the function nor a way out, and == gives false for every map
    without a word, so both would hide the slip. Every value counts, as
    if() can join a date function and a number in one series. A series whose
    values are all null passes, as no value is compared.

    :raises TypeError: for a comparison of a number with dates or times
    """
    if isinstance(number, Const):
        number = number.value
    if isinstance(number, bool) or not isinstance(number, (int, float)):
        return
    if not (isinstance(other, Series) and other.sort == "scalar"):
        return
    if any(
        isinstance(value, (datetime.date, datetime.time)) for value in _values(other)
    ):
        msg = (
            "Dates and times, such as those of start_date() or start_time(), "
            f"cannot be compared with the number {number}; compare them with a "
            'date or time in quotes, such as "2001-01-03" or "12:00:00"'
        )
        raise TypeError(msg)


# What a time function gives, by the kinds of value_kind(), for the message
# that refuses to compare two kinds
_VALUE_KINDS = {
    "datetime": "dates with a time of day, such as those of start_datetime()",
    "date": "dates, such as those of start_date()",
    "time": "times of day, such as those of start_time()",
    "number": "numbers, such as those of start_doy() or td()",
}


def _kinds_of_values(series):
    """The kinds of the values of a scalar series, in the order they appear

    Empty if the series is not scalar or all its values are null. A value of
    the kind "other" adds no kind; the core refuses to compare it.
    """
    if not (isinstance(series, Series) and series.sort == "scalar"):
        return []
    kinds = []
    for value in _values(series):
        kind = _VALUE_KINDS.get(value_kind(value))
        if kind is not None and kind not in kinds:
            kinds.append(kind)
    return kinds


def _refuse_values_of_different_kinds(left, right):
    """Raise if two time functions give different kinds of values

    Python refuses < between any two of a number, a date, a time of day and
    a date with time with a TypeError that names neither function, and ==
    gives false for every map without a word; _refuse_number_with_moments()
    refuses a number and a date for the same reason. Every value counts, as
    if() can join two time functions in one series.

    :raises TypeError: for a comparison of two different kinds
    """
    left_kinds, right_kinds = _kinds_of_values(left), _kinds_of_values(right)
    if not (left_kinds and right_kinds):
        return
    first = left_kinds[0]
    second = next((kind for kind in right_kinds + left_kinds if kind != first), None)
    if second is None:
        return
    msg = (
        f"{first[0].upper()}{first[1:]}, cannot be compared with {second}; "
        "compare time functions that give the same kind of value, such as "
        "start_date() with end_date()"
    )
    raise TypeError(msg)


def _moment(text, other):
    """Read a date, a time or both for a comparison with a time function

    The text is read as the time stamps of grass.temporal are, so with
    dateutil installed also in formats other than ISO and as a time of day
    alone. It then takes the kind of the values it is compared with, as the
    classic algebra did: the date for start_date(), the time of day for
    start_time() and both for start_datetime().

    :raises TypeError: if other is not a series of dates or times
    :raises ValueError: if the text is no date or time, or a date alone is
        compared with a time of day
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
        # A text without a colon has no time of day. Reading it as midnight
        # made "start_time(A) >= '2001-03-01'" hold for every map that starts
        # at midnight, whatever the date.
        if ":" not in text:
            msg = (
                f"'{text}' is a date without a time of day, but start_time() "
                "and end_time() give only the time of day; compare dates with "
                "start_date() or end_date(), or a date and time with "
                "start_datetime() or end_datetime()"
            )
            raise ValueError(msg)
        return Const(moment.time())
    # datetime is a subclass of date, so it is checked first.
    if sample is None or isinstance(sample, datetime.datetime):
        return Const(moment)
    return Const(moment.date())
