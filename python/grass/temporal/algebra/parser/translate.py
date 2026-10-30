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
from grass.temporal.algebra.content import COMPARISONS, NULL, Const, call
from grass.temporal.algebra.maptypes import OFFSET_COUNTS, STDS_TYPES
from grass.temporal.algebra.profile import CORE
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
    that the expression selects registered maps (t.select) and computes none;
    the core translates it like any other expression, a variant of the algebra
    may need to know.

    The profile says which variant of the algebra is translated. Its fields
    are read through self.profile.

    The protected extension points of the class are statement(), value() and
    the methods _result, _name, _index, _single_map, _operands, _binary,
    _binary_values, _relation, _select, _count, _overlay, _arithmetic,
    _combine, _apply, _compare, _logical, _if, _temporal_if, _field_if,
    _conditions, _function, _call, _time_variable, _tsnap, _tshift, _buff_t
    and _merge. A subclass for another variant of the algebra overrides them
    and relies on their signatures; the translation calls every one of them
    as a method of self, so an override is always reached. The other private
    names are details of this class.
    """

    def __init__(
        self,
        *,
        kind="raster",
        spatial=False,
        resolve=None,
        resolve_map=None,
        profile=CORE,
        selection=False,
    ):
        self.profile = profile
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
        result = self._result(node.target, self.value(node.expression))
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

    def _result(self, target, result):
        """Return the value of the expression that target is registered as;
        a profile refuses here what it cannot register"""
        return result

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
        # The count is checked before the dataset is read, so that a wrong
        # count is reported even for a missing dataset.
        offsets = node.offsets
        axes = OFFSET_COUNTS[self._kind]
        if len(offsets) != 1 and (not axes or len(offsets) not in (axes, axes + 1)):
            msg = f"{node.name}[...] takes {_INDEX_FORMS[axes]} for {self._kind} maps"
            raise SyntaxError(msg)
        series = self._name(ast.Name(node.name))
        space = self.profile.neighbour_space
        if len(offsets) == 1:
            return time_functions.neighbour(series, offsets[0], space=space)
        if len(offsets) == axes + 1:
            series = time_functions.neighbour(series, offsets[-1], space=space)
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

    def _relating_options(self):
        """Return the options that every select(), pairs() and gather() of
        the translation passes; an option that a call names itself takes
        precedence"""
        return {"mixed_times": self.profile.mixed_times}

    def _select_op(self, left, relation, other, **options):
        return operations.select(
            left, relation, other, **(self._relating_options() | options)
        )

    def _pairs_op(self, left, relation, other, **options):
        return operations.pairs(
            left, relation, other, **(self._relating_options() | options)
        )

    def _gather_op(self, target, relation, other, **options):
        return operations.gather(
            target, relation, other, **(self._relating_options() | options)
        )

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
            return self._select_op(left, relation, right, related=False)
        if operator.temporal == "l":
            return self._select_op(left, relation, right)
        if operator.temporal == "r":
            return self._pairs_op(left, relation, right, extent="right")
        return self._gather_op(
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
        return self._gather_op(left, self._relation(operator), right, reduce="count")

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
            return self._pairs_op(
                left,
                relation,
                right,
                extent="right",
                content=lambda mine, theirs: call(symbol, mine, theirs),
                space=space,
            )
        return self._gather_op(
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
        return self._apply(symbol, left, right)

    def _compare_related(self, symbol, left, right, operator):
        """A comparison with a temporal relation: each left map is compared
        with every related map, and the comparisons are joined by the
        aggregation of the operator, (a1 >= f1 && a1 >= f2)

        With the temporal reference r every pair is compared on its own and
        takes the time stamp of the right map, as in _logical().
        """
        if not (timed(left) and timed(right)):
            msg = (
                f"The temporal operator {{{symbol},...}} relates two space "
                "time datasets"
            )
            raise SyntaxError(msg)
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
            return self._pairs_op(
                left,
                relation,
                right,
                extent="right",
                content=lambda mine, theirs: call(symbol, mine, theirs),
            )
        extent = EXTENTS[operator.temporal]
        # The left maps that have related maps, and the joined conditions of
        # those related maps; both have the same time stamps.
        targets = self._gather_op(left, relation, right, reduce=None, extent=extent)
        others = self._gather_op(
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
                _constant_like(condition, then, listed=self.profile.list_order),
                None
                if otherwise is ABSENT
                else _constant_like(
                    condition, otherwise, listed=self.profile.list_order
                ),
                mixed_times=self.profile.mixed_times,
            )
        return self._temporal_if(condition, then, otherwise, relation, first)

    def _temporal_if(self, condition, then, otherwise, relation, first):
        """Choose between then and else by a condition with time stamps

        first is the first of then and else that has time stamps. Without
        else, otherwise is the marker ABSENT. A condition per cell goes to
        _field_if().
        """
        operator = relation or TemporalOperator(None)
        conditions = self._conditions(first, condition, operator)
        if conditions.sort == "field":
            return self._field_if(condition, then, otherwise, relation)
        then_maps = (
            then
            if timed(then)
            else _constant_like(first, then, listed=self.profile.list_order)
        )
        if otherwise is ABSENT:
            return operations.choose(
                conditions, then_maps, mixed_times=self.profile.mixed_times
            )
        settled = _settled(conditions, relation)
        if not timed(otherwise):
            return operations.choose(
                settled,
                then_maps,
                _constant_like(first, otherwise, listed=self.profile.list_order),
                mixed_times=self.profile.mixed_times,
            )
        if not timed(then):
            return operations.choose(
                settled, then_maps, otherwise, mixed_times=self.profile.mixed_times
            )
        # Then and else have time stamps of their own; each map is judged by
        # the conditions related to it.
        if self._selection and "scalar" in {then.sort, otherwise.sort}:
            # merge() would refuse the numbers beside maps with a message
            # about sorts of series, which says nothing to a user of t.select.
            self._refuse_time_function()
        others = self._conditions(otherwise, condition, operator)
        return operations.merge(
            operations.choose(conditions, then, mixed_times=self.profile.mixed_times),
            operations.choose(
                operations.apply("!", _settled(others, relation)),
                otherwise,
                mixed_times=self.profile.mixed_times,
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

    def _field_if(self, condition, then, otherwise, relation):
        """Choose by a condition per cell between then and else

        condition, then and otherwise are as _if() got them, relation is the
        relation of if() or None. The choice is made in each cell, so
        where() needs the joined conditions and both branches with the same
        time stamps.
        """
        # The join that _temporal_if() made is made again here: the hook takes
        # the condition as _if() got it, because an override (the classic
        # profile) pairs that raw condition with the branches itself. The cost
        # is a second join for a condition per cell.
        first = next((branch for branch in (then, otherwise) if timed(branch)), None)
        operator = relation or TemporalOperator(None)
        conditions = self._conditions(first, condition, operator)
        return _where(conditions, then, otherwise)

    def _conditions(self, target, condition, operator):
        """The joined condition of each map of target

        if({R}, c, X) reads "c R x", so the maps of X are related to the
        conditions by the inverse of R.
        """
        # Every variant relates the conditions of if() in time order and once
        # per map, so order and unique are named here and the relating options
        # of a profile do not reach them. The classic profile comes here
        # through _temporal_if() and has always related the conditions so;
        # its results must not change.
        return self._gather_op(
            target,
            inverse(self._relation(operator)),
            condition,
            reduce=_AGGREGATES[operator.aggregate],
            missing="null",
            equal_times="pairwise",
            order="sorted",
            unique=True,
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
        """Return the value of a known function other than tmap() and map()
        from the values of its arguments"""
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


def _constant_like(series, value, *, listed=False):
    """A series with the time stamps of series and value as each content

    value is a content node or a map without time stamp. With listed the
    slots keep their rank and the series its order, as a profile that lists
    results in the order of the lists needs; the core leaves them out so that
    its results do not depend on them.
    """
    if isinstance(value, str):
        msg = f"A text such as '{value}' cannot be a branch of if()"
        raise TypeError(msg)
    content = value.slots[0].content if isinstance(value, Series) else value
    return Series(
        tuple(
            Slot(slot.extent, content, slot.space, rank=slot.rank if listed else None)
            for slot in series
        ),
        kind=series.kind,
        spatial=series.spatial,
        **({"order": series.order} if listed else {}),
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
