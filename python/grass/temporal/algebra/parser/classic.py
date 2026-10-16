"""The classic temporal algebra as a profile of the algebra core

The classic algebra of the parser classes (``temporal_algebra`` and its
subclasses) is one variant of the algebra: it reads another syntax, relates and
combines maps by other rules, and computes the result maps with other texts.
The profile ``CLASSIC`` carries those rules: the classic grammar
(``classic_grammar``) builds the syntax tree, ``ClassicTranslator`` gives it the
classic meaning with the operations of the core, and the options of the profile
set the rules of ``plan()`` and ``materialize()``.

The translator overrides the protected extension points of ``Translator``
only. Where the classic rule is a parameter of a core operation (the order and
repetition of relation names, the stepwise time and box combination, the
failure policy), the translator passes it; the pieces that have no such
parameter (the conditions of ``if()``, which judge maps, and ``buff_t()``,
which keeps the quirks of the library) are written out here.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import dataclasses

from grass.exceptions import FatalError
from grass.temporal.algebra import operations, time_functions
from grass.temporal.algebra._adapters import as_map, extent_from
from grass.temporal.algebra.backends import MapcalcStyle
from grass.temporal.algebra.content import (
    NULL,
    Call,
    Const,
    MapRef,
    ScalarFunctionError,
    call,
)
from grass.temporal.algebra.maptypes import DIMENSIONS
from grass.temporal.algebra.profile import Profile
from grass.temporal.algebra.relations import (
    TEMPORAL_RELATIONS,
    Relation,
    inverse,
    related,
)
from grass.temporal.algebra.series import Series, Slot

from . import ast
from .classic_grammar import classic_grammar
from .operators import TemporalOperator
from .translate import (
    _ABSENT,
    _EXTENTS,
    Translator,
    _check_time_variable,
    _timed,
    _whole,
)

# strds(), str3ds() and stvds() of t.select read a dataset of another type
# than the result.
_DATASET_FUNCTIONS = ("strds", "str3ds", "stvds")
_CONDITION_FUNCTIONS = ("exist", "isnull", "isntnull")
_EQUAL = TemporalOperator(None)


class ClassicSyntax:
    """The classic grammars as one grammar of a profile

    The classic syntax depends on the map type and on t.select, so the profile
    holds this object, and evaluate() asks it for the grammar of the
    expression.
    """

    @staticmethod
    def for_kind(kind, selection=False):
        """Return the classic grammar object for a map type or for t.select"""
        return classic_grammar("select" if selection else kind)


def _pairing_error(message):
    """The classic error for maps of equal time that cannot be paired"""
    return FatalError(
        _("Unable to pair maps with maps of equal time stamps: {error}").format(
            error=message
        )
    )


def _like(series, slots, sort=None):
    """A series of slots with the map type, order and flags of series"""
    return Series(
        tuple(slots),
        series.kind,
        series.sort if sort is None else sort,
        series.spatial,
        series.order,
    )


def _joined(symbol, first, second):
    """The content of two conditions joined by && or ||, as r.mapcalc reads
    the text of the classic algebra

    The classic algebra writes "a||(b)&&(c)" and r.mapcalc binds && stronger,
    so the condition is a || (b && c) whatever grouped the operands before.
    """
    if (
        symbol == "&&"
        and isinstance(first, Call)
        and first.function == "||"
        and len(first.args) == 2
    ):
        return Call("||", (first.args[0], _joined(symbol, first.args[1], second)))
    return call(symbol, first, second)


def _constant(value):
    """The content of a number, null() or a missing else (0, as r.mapcalc)"""
    if value is _ABSENT:
        return Const(0)
    if value is NULL or isinstance(value, Const):
        return value
    if isinstance(value, Series) and value.timeless:
        return value.slots[0].content
    return value


def _written_increment(increment):
    """The increment of tshift() and buff_t() as the parser classes read it

    :return: the text of a quoted number and unit, or the number, and whether
        a unit was given
    :raises SyntaxError: for another value
    """
    if isinstance(increment, str):
        return increment, True
    if isinstance(increment, Const) and isinstance(increment.value, (int, float)):
        return increment.value, False
    msg = (
        'The increment of tshift() and buff_t() is a text such as "1 month" or a number'
    )
    raise SyntaxError(msg)


def _check_increment(function, series, increment, with_unit):
    """Refuse an increment of the wrong kind for the time type of the maps

    Absolute time takes a number and a unit, relative time a number of its
    unit. A fractional number is no refusal for relative time: it is truncated
    to a whole one, as the parser classes do.

    :raises SyntaxError: for a number without unit on absolute time, and a
        unit on relative time
    """
    absolute = any(slot.extent.unit is None for slot in series.slots)
    relative = any(slot.extent.unit is not None for slot in series.slots)
    if str(increment).strip().lstrip("-").isdigit() and absolute:
        msg = (
            "Function {function}() needs a time unit for absolute time, "
            'e.g. "{increment} days", but got {increment}'
        ).format(function=function, increment=increment)
        raise SyntaxError(msg)
    if with_unit and relative:
        msg = (
            "Function {function}() needs a number without a time unit for "
            'relative time, e.g. 3, but got "{increment}"'
        ).format(function=function, increment=increment)
        raise SyntaxError(msg)


class ClassicTranslator(Translator):
    """Translate statements with the meaning of the classic algebra"""

    def __init__(self, **keywords):
        super().__init__(**keywords)
        # The conditions on time functions whose argument is a computed
        # expression, by id(), with the series itself so that the id stays
        # taken; see _remember_commands().
        self._commands = {}
        # The results of the hash operator, by id() (and the series itself, so
        # that the id stays taken); see _field_if().
        self._counts = {}
        # The conditions isnull(), isntnull() and exist() of a count, by id()
        # with the series and the count; see _if().
        self._count_conditions = {}
        # The time stamp of every registered map the expression reads, by
        # identifier; see statement().
        self._stored = {}
        self._resolve = self._noting(self._resolve)
        self._resolve_map = self._noting(self._by_start(self._resolve_map))

    @staticmethod
    def _by_start(resolve):
        """resolve, with the series ordered by start alone as the datasets are
        (see resolve in evaluate()): a single map joins lists of datasets, and
        the order of its list decides the ties in the lists it joins"""

        def read(*arguments, **keywords):
            series = resolve(*arguments, **keywords)
            return dataclasses.replace(series, order="start")

        return read

    def _noting(self, resolve):
        """resolve, noting the time stamps of the registered maps it reads"""

        def read(*arguments, **keywords):
            series = resolve(*arguments, **keywords)
            for slot in series.slots:
                if slot.origin is not None and slot.extent is not None:
                    self._stored[slot.origin] = slot.extent
            return series

        return read

    def statement(self, node):
        """A selection registers a map unchanged if its time stamp is the
        stored one, also after tshift(), tsnap() and buff_t() moved it away
        and back; the classic algebra compares the time stamps only"""
        name, series = super().statement(node)
        if not self._selection:
            return name, series
        slots = [
            dataclasses.replace(slot, origin=slot.content.ident)
            if slot.origin is None
            and isinstance(slot.content, MapRef)
            and not slot.content.offset
            and self._stored.get(slot.content.ident) == slot.extent
            else slot
            for slot in series.slots
        ]
        return name, _like(series, slots)

    def _operands(self, node):
        """The classic production for a bare name reads the dataset only when
        it reduces, after the other operand: that operand's errors and
        temporal type come first"""
        if isinstance(node.left, ast.Name) and not isinstance(node.right, ast.Name):
            right = self.value(node.right)
            return self.value(node.left), right
        return super()._operands(node)

    def _binary(self, node):
        """The classic hash production refuses a temporal reference other
        than l before it reads its datasets; operands that are expressions
        were evaluated before"""
        operator = node.operator
        if node.symbol == "#" and operator is not None and operator.temporal != "l":
            for operand in (node.left, node.right):
                if not isinstance(operand, ast.Name):
                    self.value(operand)
            return self._count(None, None, operator)
        return super()._binary(node)

    def _apply(self, function, *operands):
        """Functions of time constants such as sqrt(start_doy(A, 0)) are
        computed by r.mapcalc per map in the classic algebra, while the core
        computes scalars in Python and lacks most of the functions"""
        try:
            return super()._apply(function, *operands)
        except ScalarFunctionError:
            pass
        fields = tuple(
            dataclasses.replace(operand, sort="field")
            if isinstance(operand, Series)
            and operand.sort == "scalar"
            and not operand.timeless
            else operand
            for operand in operands
        )
        return super()._apply(function, *fields)

    def _relation(self, operator):
        """The relation in the written order of its names; a spatial name
        relates in space also without the spatial flag"""
        names = tuple(operator.relations)
        temporal = tuple(name for name in names if name in TEMPORAL_RELATIONS)
        spatial = frozenset(names) - frozenset(temporal)
        if spatial or self._spatial:
            return Relation(frozenset(temporal), spatial, temporal)
        return Relation(frozenset(temporal), None, temporal)

    def _related(self, left, relation, other, *, pairwise=False):
        """Per slot of left the indices of the related slots of other

        They are in the written order of the relation names and repeated per
        name, as the classic algebra visits them. With pairwise maps of equal
        time are paired one to one, also in space.
        """
        matches = related(
            left.slots,
            relation,
            other.slots,
            dimension=DIMENSIONS[left.kind],
            order="written",
            unique=False,
        )
        if pairwise:
            matches = operations.pair_equal_times(
                left.slots, matches, other.slots, order="written", error=_pairing_error
            )
        return matches

    @staticmethod
    def _aligned(left, right):
        """right as a series of the map type of left

        t.select relates maps of different types (strds(A) : stvds(B)), which
        the operations of the core refuse. Only time and box matter for the
        relation.
        """
        if right.kind == left.kind:
            return right
        return dataclasses.replace(right, kind=left.kind)

    def _meeting(self, slot, other, found):
        """The partners of slot up to the first whose box does not meet the
        box combined so far, as the classic result map stops there"""
        space = slot.space
        three_d = DIMENSIONS[other.kind] == "3D"
        for index in found:
            partner = other.slots[index].space
            if space is not None and partner is not None:
                space = operations.combine_boxes(
                    space, partner, "intersection", three_d
                )
                if space is None:
                    return
            yield index

    def _select(self, left, right, operator):
        """Selections keep one map per selected left map; with a temporal
        reference other than l its time stamp is combined with the partners
        one after the other, skipping those that do not combine"""
        self._pair(operator.symbol, left, right)
        for name in operator.relations:
            # The classic selection with a temporal operator refuses spatial
            # names, also with the temporal reference l.
            if name not in TEMPORAL_RELATIONS:
                msg = f"Unpermitted temporal relation name '{name}'"
                raise SyntaxError(msg)

        relation = self._relation(operator)
        right = self._aligned(left, right)
        if operator.symbol == "!:":
            return operations.select(
                left,
                relation,
                right,
                related=False,
                order="written",
                unique=False,
                mixed_times=self.profile.mixed_times,
            )
        return operations.select(
            left,
            relation,
            right,
            extent=_SELECT_EXTENTS[operator.temporal],
            failure="skip",
            order="written",
            unique=False,
            mixed_times=self.profile.mixed_times,
        )

    def _count(self, left, right, operator):
        if operator.temporal != "l":
            msg = (
                f"The hash operator {{#,{'|'.join(operator.relations)},"
                f"{operator.temporal}}} counts the related maps of each left map "
                "and keeps its time stamp, a temporal operator "
                f"'{operator.temporal}' is not supported"
            )
            raise SyntaxError(msg)
        self._pair("#", left, right)
        counts = operations.gather(
            left,
            self._relation(operator),
            self._aligned(left, right),
            reduce="count",
            order="written",
            unique=False,
            mixed_times=self.profile.mixed_times,
        )
        self._counts[id(counts)] = counts
        return counts

    def _combine(self, symbol, left, right, operator, reduce, *, space="keep"):
        """Fold each left map with all its partners in the written order of
        the relation names

        l keeps the left time stamp; r gives a map per partner with the time
        stamp of the partner and the whole fold as content, and for vector
        maps only the map of the last partner, as the result maps of one left
        map share their id; u, i and d combine the time stamp with the
        partners one after the other and stop at the first that does not
        combine, keeping what was combined before. The boxes combine in the
        same steps, also without the spatial flag: an intersection for
        everything but the overlays of vector maps that are not "and".
        """
        relation = self._relation(operator)
        right = self._aligned(left, right)
        box = space if self._kind == "vector" and space != "keep" else "intersection"
        if operator.temporal == "r":
            return operations.pairs(
                left,
                relation,
                right,
                extent="right",
                content=lambda mine, theirs: call(symbol, mine, theirs),
                order="written",
                unique=False,
                box=box,
                fold_all=True,
                last_only=self._kind == "vector",
                mixed_times=self.profile.mixed_times,
            )
        return operations.gather(
            left,
            relation,
            right,
            reduce=reduce,
            extent=_EXTENTS[operator.temporal],
            order="written",
            unique=False,
            failure="stop",
            box=box,
            mixed_times=self.profile.mixed_times,
        )

    def _remember_commands(self, result, argument):
        """Note the commands of the argument of a time function

        The classic algebra gives a map of the argument that carries a
        command (a computed expression, not a registered map) a condition
        on its time as the command of the argument; see _logical().
        """
        slots = argument.slots
        if (
            isinstance(result, Series)
            and result.sort == "scalar"
            and len(result.slots) == len(slots)
            and any(not isinstance(slot.content, MapRef) for slot in slots)
        ):
            self._commands[id(result)] = (result, argument)

    def _carry_commands(self, result, source):
        """Note for result the commands of source, a condition on a time
        function: result keeps the maps of the left operand, so what the
        classic algebra found at their argument is still there"""
        known = self._commands.get(id(source))
        if known is None:
            return
        argument = known[1]
        taken = set()
        slots = []
        for slot in result.slots:
            index = next(
                (
                    number
                    for number, candidate in enumerate(source.slots)
                    if number not in taken and candidate.extent == slot.extent
                ),
                None,
            )
            if index is None:
                return
            taken.add(index)
            slots.append(argument.slots[index])
        self._remember_commands(result, _like(argument, slots))

    def _compare(self, symbol, left, right):
        result = super()._compare(symbol, left, right)
        for operand, other in ((left, right), (right, left)):
            known = self._commands.get(id(operand))
            if known is not None and not isinstance(other, Series):
                self._remember_commands(result, known[1])
        return result

    def _as_command(self, series):
        """series, with the command of the argument of its time function in
        place of the truth value of each map that has one

        A condition that joins a condition on a time function with one on
        cells (A > 1 && start_month(A * 0) == 1) takes the command of the
        argument, so the cells of the expression decide and not the time,
        where the classic algebra finds a command at the argument. A
        registered map has none, and its time decides.
        """
        known = self._commands.get(id(series))
        if known is None:
            return series
        slots = [
            slot
            if isinstance(argument.content, MapRef)
            else dataclasses.replace(slot, content=argument.content)
            for slot, argument in zip(series.slots, known[1].slots, strict=True)
        ]
        return _like(series, slots, "field")

    def _logical(self, symbol, left, right, operator):
        """&& and || of two condition series combine the boxes in the same
        steps as the time stamps, as every classic combination of maps does"""
        if operator is None and (left.sort == "field") != (right.sort == "field"):
            left, right = self._as_command(left), self._as_command(right)
        if not (_timed(left) and _timed(right)):
            return super()._logical(symbol, left, right, operator)
        if operator is None:
            operator = TemporalOperator(symbol, aggregate=symbol[0])
        relation = self._relation(operator)
        right = self._aligned(left, right)
        options = {
            "order": "written",
            "unique": False,
            "box": "intersection",
            "mixed_times": self.profile.mixed_times,
        }
        if operator.temporal == "r":
            return operations.pairs(
                left,
                relation,
                right,
                extent="right",
                content=lambda mine, theirs: _joined(symbol, mine, theirs),
                **options,
            )
        extent = _EXTENTS[operator.temporal]
        targets = operations.gather(
            left, relation, right, reduce=None, extent=extent, failure="stop", **options
        )
        others = operations.gather(
            left,
            relation,
            right,
            reduce="and" if operator.aggregate == "&" else "or",
            extent=extent,
            failure="stop",
            **options,
        )
        joined = operations.apply(symbol, targets, others)
        if symbol == "&&":
            # apply() wrote call(symbol, target, other) for every slot, unless
            # it computed a constant.
            joined = _like(
                joined,
                (
                    dataclasses.replace(
                        slot, content=_joined(symbol, *slot.content.args)
                    )
                    if isinstance(slot.content, Call)
                    else slot
                    for slot in joined.slots
                ),
            )
        if left.sort == "scalar" and right.sort == "scalar":
            self._carry_commands(joined, left)
        return joined

    def _time_variable(self, name, arguments):
        """td() needs intervals; in a selection start_doy(A, 1) and the like
        keep the neighbour map itself under the time stamp of each map, as no
        value is computed there. With an offset only the maps whose value is
        read are asked for the variable: start_hour(RT, 5) of three maps of
        relative time is empty, not an error."""
        series = arguments[0] if arguments else None
        used = series
        offset = None
        if len(arguments) == 2 and isinstance(series, Series):
            offset = _whole(arguments[1], name)
            if not self._selection:
                count = len(series.slots)
                used = dataclasses.replace(
                    series, slots=series.slots[max(offset, 0) : count + min(offset, 0)]
                )
        if name == "td" and isinstance(used, Series):
            for slot in used.slots:
                if slot.extent is not None and slot.extent.end is None:
                    raise FatalError(
                        _(
                            "Function td() requires a time interval, but map "
                            "<{map}> is a time instance."
                        ).format(map=slot.origin or slot.extent.start)
                    )
        if self._selection and offset is not None:
            return time_functions.neighbour(series, offset)
        if offset is not None:
            _check_time_variable(name, used)
            variable = time_functions.timevar(series, name)
            # The value of a neighbour is a number in the map, so a condition
            # on it judges cells, not time.
            return dataclasses.replace(
                time_functions.neighbour(variable, offset), sort="field"
            )
        result = super()._time_variable(name, arguments)
        self._remember_commands(result, series)
        return result

    def _function(self, node):
        if node.name in _DATASET_FUNCTIONS:
            (argument,) = node.arguments
            stds_type = node.name
            key = (argument.ident, stds_type)
            if key not in self._datasets:
                self._datasets[key] = self._resolve(argument.ident, stds_type=stds_type)
            return self._datasets[key]
        result = super()._function(node)
        if (
            node.name in _CONDITION_FUNCTIONS
            and isinstance(result, Series)
            and result.sort == "scalar"
            and not result.timeless
        ):
            # These are conditions on cells in the classic grammar, also of a
            # count or a time value, so the if() of a field condition applies.
            result = dataclasses.replace(result, sort="field")
            argument = node.arguments[0]
            if isinstance(argument, ast.Binary) and argument.symbol == "#":
                self._count_conditions[id(result)] = (result, self.value(argument))
        return result

    def _merge(self, first, second):
        """The classic map lists mix maps and numbers freely: a number in a
        list is a constant map, so merging a count with maps is a list of
        maps. A map that the second list shares with the first is kept once;
        what repeats in the first list stays, as the lists of the classic
        algebra tell two computed maps apart by the map they came from."""
        if first.sort != second.sort:
            first, second = (
                dataclasses.replace(series, sort="field") for series in (first, second)
            )
        self._check_merged_times(first, second)
        return operations.merge(first, second, keep_first_repeats=True)

    @staticmethod
    def _check_merged_times(first, second):
        """The classic result list may hold maps of different temporal types
        and units, which relate to nothing; registering them in one dataset
        is what fails there, so merge() is where this surfaces

        :raises FatalError: for absolute and relative time, and for relative
            time of different units
        """
        units = {
            slot.extent.unit
            for slot in (*first.slots, *second.slots)
            if slot.extent is not None
        }
        if len(units) < 2:
            return
        if None in units:
            msg = _("Temporal type of the merged maps are different")
        else:
            msg = _("Relative time units of the merged maps are different")
        raise FatalError(msg)

    def _tshift(self, series, increment):
        """Shift by an increment; a number needs relative and a text with a
        unit absolute time"""
        value, with_unit = _written_increment(increment)
        _check_increment("tshift", series, value, with_unit)
        return time_functions.retime(series, shift=str(value))

    def _buff_t(self, series, increment):
        """Buffer by temporal_buffer() of the map objects, as the classic
        algebra does: a negative buffer gives an instant where the end meets
        the start and keeps the time stamp where the end would fall before
        the start, and instants stay"""
        value, with_unit = _written_increment(increment)
        _check_increment("buff_t", series, value, with_unit)
        slots = []
        for slot in series.slots:
            map_ = as_map(slot.extent)
            # Relative time is buffered by a whole number of its unit.
            map_.temporal_buffer(str(value) if slot.extent.unit is None else int(value))
            extent = extent_from(map_.get_temporal_extent(), slot.extent.unit)
            # A map that keeps its time stamp is still the registered map.
            origin = slot.origin if extent == slot.extent else None
            slots.append(Slot(extent, slot.content, slot.space, origin, slot.rank))
        return _like(series, slots)

    def _if(self, arguments, relation):
        """The classic if(): conditions on map values choose per cell, one map
        per pair of condition and conclusion; conditions on temporal
        variables judge each conclusion map by the conditions related to it.
        The maps of then and else are listed together in time order, where
        the core lists those of then first."""
        known = self._count_conditions.get(id(arguments[0]))
        if known is not None:
            # The classic algebra reads such a condition as the count itself,
            # whatever the function made of it.
            arguments = [dataclasses.replace(known[1], sort="field"), *arguments[1:]]
        if self._kind == "vector" or len(arguments) not in (2, 3):
            return self._in_time_order(super()._if(arguments, relation))
        condition = arguments[0]
        if (
            isinstance(condition, Series)
            and condition.sort == "scalar"
            and not condition.timeless
            and all(_timed(branch) for branch in arguments[1:])
        ):
            return self._in_time_order(
                self._judged_if(condition, *arguments[1:], relation=relation)
            )
        if not (_timed(condition) and condition.sort == "field"):
            return self._in_time_order(super()._if(arguments, relation))
        then = arguments[1]
        otherwise = arguments[2] if len(arguments) == 3 else _ABSENT
        return self._in_time_order(self._field_if(condition, then, otherwise, relation))

    @staticmethod
    def _in_time_order(series):
        """series with its slots listed in time order"""
        if not isinstance(series, Series):
            return series
        return _like(series, (dataclasses.replace(s, rank=None) for s in series.slots))

    def _judged_if(self, condition, then, otherwise=None, *, relation):
        """if() on temporal variables: each conclusion map is judged by all
        condition maps related to it, over all of them and without pairing
        maps of equal time; a map without related condition is left out,
        except in else with a relation beyond equal

        The relation reads "condition R conclusion", so the conclusion maps
        are related to the conditions by its inverse. Maps of other types than
        the result relate as well (t.select with stvds() and the like).
        """
        operator = relation or _EQUAL
        names = operator.relations
        backwards = inverse(self._relation(operator))
        takes_unrelated = relation is not None and any(
            name in TEMPORAL_RELATIONS and name != "equal" for name in names
        )

        def judged(target):
            matches = self._related(target, backwards, self._aligned(target, condition))
            true, false, unrelated = [], [], []
            for slot, found in zip(target.slots, matches, strict=True):
                if not found:
                    unrelated.append(slot)
                    continue
                # The core folds comparisons into 1 and 0, as r.mapcalc; the
                # classic algebra passes over values that are no booleans.
                values = [condition.slots[index].content.value for index in found]
                values = [bool(value) for value in values if value is not None]
                (true if all(values) else false).append(slot)
            return true, false, unrelated

        slots, _false, _unrelated = judged(then)
        sorts = {then.sort}
        if otherwise is not None:
            _true, false, unrelated = judged(otherwise)
            slots += false + (unrelated if takes_unrelated else [])
            sorts.add(otherwise.sort)
        # The classic map lists mix maps and numbers freely; a number in a
        # map list is a constant map.
        return _like(then, slots, "field" if "field" in sorts else "scalar")

    def _field_if(self, condition, then, otherwise, relation):
        """if() on map values as r.mapcalc text, one map per pair

        The then and else maps are paired first (equal time, one to one); each
        condition map is then paired with each related conclusion and gives a
        map with the time stamp of the conclusion. Numbers stand in every map.
        Without else r.mapcalc's if(c, x) gives 0 where c is false.
        """
        # The classic algebra reads the operand of a count as the count itself
        # whatever command was built for it, so a number next to a count is
        # lost and the count stands alone as the then part.
        if id(otherwise) in self._counts and not _timed(then):
            then, otherwise = otherwise, _ABSENT
        elif id(then) in self._counts and not _timed(otherwise):
            otherwise = _ABSENT
        timed_then, timed_else = _timed(then), _timed(otherwise)
        if timed_then and timed_else:
            matches = self._related(
                then, self._relation(_EQUAL), otherwise, pairwise=True
            )
            conclusion = [
                (other_slot, (slot.content, other_slot.content))
                for slot, found in zip(then.slots, matches, strict=True)
                for other_slot in (
                    otherwise.slots[i] for i in self._meeting(slot, otherwise, found)
                )
            ]
        elif timed_then:
            constant = _constant(otherwise)
            conclusion = [(slot, (slot.content, constant)) for slot in then.slots]
        elif timed_else:
            constant = _constant(then)
            conclusion = [(slot, (constant, slot.content)) for slot in otherwise.slots]
        else:
            contents = (_constant(then), _constant(otherwise))
            return _like(
                condition,
                (
                    Slot(slot.extent, call("if", slot.content, *contents), slot.space)
                    for slot in condition.slots
                ),
                "field",
            )
        # Series sorts its slots by time, stably; the conclusion list is in
        # time order already, so its contents stay aligned.
        targets = Series(
            tuple(slot for slot, _ in conclusion),
            condition.kind,
            "field",
            order=condition.order,
        )
        contents = [pair for _, pair in conclusion]
        matches = self._related(
            condition, self._relation(relation or _EQUAL), targets, pairwise=True
        )
        slots = []
        for slot, found in zip(condition.slots, matches, strict=True):
            for index in self._meeting(slot, targets, found):
                target = targets.slots[index]
                slots.append(
                    Slot(
                        target.extent,
                        call("if", slot.content, *contents[index]),
                        target.space,
                    )
                )
        return _like(condition, slots, "field")


_SELECT_EXTENTS = {
    "l": "left",
    "r": "right",
    "u": "union",
    "i": "intersection",
    "d": "disjoint",
}

CLASSIC = Profile(
    grammar=ClassicSyntax(),
    translator=ClassicTranslator,
    mapcalc=MapcalcStyle(
        quote_names=False, written_integers=True, bare_comparisons=True
    ),
    classic_absence_check=True,
    keep_empty_vector_maps=True,
    vector_dataset_if_empty=False,
    copies_by_position=True,
    empty_result_type_from_input=True,
    one_temporal_type=True,
    union_region_when_spatial=True,
    list_order=True,
    database_order=True,
    last_of_equal_names=True,
    neighbour_space="neighbour",
    mixed_times="unrelated",
    classic_errors=True,
)
