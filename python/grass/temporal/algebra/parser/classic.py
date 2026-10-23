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

The module also uses private helpers of ``translate`` (the constants and
checks imported from there) and of ``operations`` (``_check_comparable()``,
``_warn()``). The profile must judge operands and refuse map types exactly as
the core does, and these helpers are that judgement; making them public would
make them API of the core for this one caller. A change of these helpers
must therefore be checked against this module.

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
    _COMPARISONS,
    _EXTENTS,
    Translator,
    _check_time_variable,
    _timed,
    _vector_field,
    _whole,
)

# strds(), str3ds() and stvds() of t.select read a dataset of another type
# than the result.
_DATASET_FUNCTIONS = ("strds", "str3ds", "stvds")
_BUFFERS = ("buff_p", "buff_l", "buff_a")
_CONDITION_FUNCTIONS = ("exist", "isnull", "isntnull")
_EQUAL = TemporalOperator(None)
_INT32_MAX = 2**31 - 1


def _beyond_int32(content):
    """Whether content is an integer constant that r.mapcalc reads with an
    overflow"""
    return (
        isinstance(content, Const)
        and isinstance(content.value, int)
        and abs(content.value) > _INT32_MAX
    )


def _unit(series):
    """The temporal type and unit of a series: the unit of relative time,
    None for absolute time, _ABSENT for a map without time stamp"""
    extent = series.slots[0].extent
    return _ABSENT if extent is None else extent.unit


@dataclasses.dataclass(frozen=True)
class _Mixed:
    """A classic list of maps of more than one temporal type or unit

    The classic lists take any maps; maps of different types or units relate
    to nothing, and registering them in one dataset fails. A series of the
    core has one type and unit, so the list is held as one series per type
    and unit, in the order in which the list first shows each. Only merge()
    makes such a list; ClassicTranslator._each_unit() evaluates what takes
    it once per series.
    """

    parts: tuple[Series, ...]

    def part(self, unit):
        """The series of maps of a unit; for a unit the list lacks, a series
        that relates to nothing of that unit"""
        return next((part for part in self.parts if _unit(part) == unit), self.parts[0])


def _listed(parts):
    """The slots of the parts of a list in its order"""
    slots = [slot for part in parts for slot in part.listed()]
    if all(slot.rank is not None for slot in slots):
        slots.sort(key=lambda slot: slot.rank)
    return slots


def _gathered(parts):
    """One series, or a _Mixed if the non-empty parts differ in unit"""
    groups = {}
    for part in parts:
        if part.slots:
            unit = _unit(part)
            groups[unit] = (
                dataclasses.replace(groups[unit], slots=groups[unit].slots + part.slots)
                if unit in groups
                else part
            )
    if not groups:
        return parts[0]
    if len(groups) == 1:
        return next(iter(groups.values()))
    return _Mixed(tuple(groups.values()))


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


# The map that a content stands for is its own, a new map object of the
# classic algebra, as long as the map of its mark is this value.
_OWN = object()


@dataclasses.dataclass(eq=False)
class _MapObject:
    """The map object of the classic algebra that a content stands for

    The classic algebra tells maps apart by the id of their map object, their
    time stamp and the command written on them (_merge_key() of the classic
    algebra). The profile attaches this object to the content as its mark,
    which the core never reads. A new map object is its own id; the classic
    algebra makes one for each result of an operation of two map lists, each
    map read at an offset, each buffer and each value of a time function at
    an offset. A number or a function keeps the object, and the hash operator
    counts on the object of the left map.

    It compares and hashes by identity, because a mark that is its own map
    object is the identity.

    map: _OWN for a new map object, whose id is this mark; else the id it
        keeps, the identifier of a registered map or the mark of a new one,
        or None for a map that has no id
    first: the first count of a counted map (see _first_counts()), which is
        the content itself for the first count; None for a map that is not
        counted. Set after the content is made, because the content that
        carries the mark is the first count.
    text: the command as the classic algebra writes it, unfolded, where the
        content was folded to a number (a count changed by numbers, a value
        of a time function at an offset); None for the content itself. The
        classic algebra compares this text in merge(), and the profile folds
        a count plus 0 to the number of the count.
    bare: True for a neighbour map, a new map object whose command is its own
        reference; see _has_command().
    """

    map: object = _OWN
    first: Content | None = None
    text: Content | None = None
    bare: bool = False


class _SeriesNotes:
    """Notes about series, found by identity

    A series is not hashable, so the notes are keyed by id(). Each entry holds
    its series: once a series is gone, a later one can take its id and would
    read the note of another.
    """

    def __init__(self):
        self._notes = {}

    def note(self, series, value=None):
        """Remember value for series"""
        self._notes[id(series)] = (series, value)

    def get(self, series):
        """Return the value noted for series, or None"""
        entry = self._notes.get(id(series))
        return None if entry is None else entry[1]

    def __contains__(self, series):
        return id(series) in self._notes


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
        # expression, with the argument; see _remember_commands().
        self._commands = _SeriesNotes()
        # The results of the hash operator itself; see _compare().
        self._hashes = _SeriesNotes()
        # The time stamp of every registered map the expression reads, by
        # identifier; see statement().
        self._stored = {}
        self._sampled = False
        # The contents of the time functions with an offset in a selection, by
        # id, held here so that no other content takes their id; see
        # statement().
        self._time_values = {}
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
            idents = [
                slot.content.ident
                for slot in series.slots
                if isinstance(slot.content, MapRef)
            ]
            # Sampled by a granularity, a dataset reads a map once per granule
            self._sampled = self._sampled or len(set(idents)) < len(idents)
            for slot in series.slots:
                if slot.origin is not None and slot.extent is not None:
                    self._stored[slot.origin] = slot.extent
            return series

        return read

    def statement(self, node):
        """A selection and the vector algebra register a map unchanged if its
        time stamp is the stored one, also after tshift(), tsnap() and buff_t()
        moved it away and back; the classic algebra compares the time stamps
        only. Raster maps are computed, so they are always new. A selection
        that would register the value of a time function is refused."""
        name, series = super().statement(node)
        if self._selection and any(
            id(slot.content) in self._time_values for slot in series.slots
        ):
            # In a selection the value of a time function stands for the map
            # it is read from. The earlier implementation never computes it
            # and fails when it copies it into the result, so the profile
            # refuses that result before it writes anything. Where the value
            # is not selected, as in if(start_doy(A) < 3, start_doy(A, -1), A)
            # whose first map has no predecessor, the earlier implementation
            # selects maps, and so does the profile; the core refuses every
            # time function as the conclusion of if().
            self._refuse_time_function()
        if not (self._selection or self._kind == "vector"):
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

    def _binary_values(self, node, left, right):
        return self._each_unit(self._binary_unit, node, left, right)

    def _binary_unit(self, node, left, right):
        if (
            node.symbol in _COMPARISONS
            and isinstance(left, Series)
            and isinstance(right, Series)
        ):
            # The grammar reads the comparison of two datasets in if() only.
            return self._compare_related(
                node.symbol, left, right, node.operator or TemporalOperator(node.symbol)
            )
        if node.symbol in (":", "!:") and node.operator is None:
            return self._select(
                left, right, TemporalOperator(node.symbol), one_per_map=False
            )
        return super()._binary_values(node, left, right)

    def _each_unit(self, function, *arguments):
        """function of arguments, once for each temporal type and unit of
        the maps of a _Mixed among them

        The unit is that of the first argument with time stamps: its maps
        meet only the maps of their unit in the other arguments, as maps of
        different units relate to nothing. An argument may be a list of
        values, as the arguments of a function are.
        """
        values = [
            value
            for argument in arguments
            for value in (argument if isinstance(argument, list) else [argument])
        ]
        if not any(isinstance(value, _Mixed) for value in values):
            return function(*arguments)
        lead = next(
            value for value in values if isinstance(value, _Mixed) or _timed(value)
        )
        units = (
            [_unit(part) for part in lead.parts]
            if isinstance(lead, _Mixed)
            else [_unit(lead)]
        )

        def part(value, unit):
            if isinstance(value, list):
                return [part(item, unit) for item in value]
            return value.part(unit) if isinstance(value, _Mixed) else value

        return _gathered(
            [
                function(*(part(argument, unit) for argument in arguments))
                for unit in units
            ]
        )

    def _result(self, target, result):
        """The classic dataset takes the temporal type and unit of its first
        map; registering a map of another fails"""
        if not isinstance(result, _Mixed):
            return result
        first, second = result.parts[:2]
        if (_unit(first) is None) != (_unit(second) is None):
            msg = _(
                "Temporal type of space time dataset <{name}> and its maps "
                "are different"
            )
        else:
            msg = _(
                "Relative time units of space time dataset <{name}> and its "
                "maps are different"
            )
        raise FatalError(msg.format(name=target))

    def _apply(self, function, *operands):
        """The classic result of function; a count that meets numbers stays a
        count of the same map, as the map changed by a number keeps its id
        and its first count"""
        result = self._applied(function, *operands)
        series = [operand for operand in operands if isinstance(operand, Series)]
        if not (
            len(series) == 1
            and isinstance(result, Series)
            and len(result.slots) == len(series[0].slots)
            and any(
                self._counted(slot.content) or self._new_map(slot.content)
                for slot in series[0].slots
            )
        ):
            return result
        slots = []
        for index, (slot, operand) in enumerate(
            zip(result.slots, series[0].slots, strict=True)
        ):
            if self._counted(operand.content):
                # Equal contents are copied, so that each has an identity.
                content = self._counting(slot.content, operand.content)
                content.mark.text = self._text_of(function, operands, index)
                slot = dataclasses.replace(slot, content=content)
            elif self._new_map(operand.content) and isinstance(slot.content, Const):
                # A new map changed by a number is the same map, but the
                # profile has folded it: it keeps the map and the command.
                content = dataclasses.replace(
                    slot.content,
                    mark=_MapObject(
                        self._source(operand.content),
                        text=self._text_of(function, operands, index),
                    ),
                )
                slot = dataclasses.replace(slot, content=content)
            slots.append(slot)
        return dataclasses.replace(result, slots=tuple(slots))

    def _text_of(self, function, operands, index):
        """The command of function on the operands in the slot at index,
        written with the commands of the operands and not folded"""
        return Call(
            function,
            tuple(
                self._written(operations._content_at(operand, index))  # noqa: SLF001
                for operand in operands
            ),
        )

    @staticmethod
    def _new_map(content):
        """True if content is a new map object of the classic algebra"""
        return content.mark is not None and content.mark.map is _OWN

    @staticmethod
    def _counted(content):
        """True if the map of content has a count"""
        return content.mark is not None and content.mark.first is not None

    @staticmethod
    def _counting(content, like):
        """A copy of content that is the map and the count that like is

        The copy has the mark of a new map object, so that each content has an
        identity of its own, and keeps the map, the first count and the text
        of like.
        """
        return dataclasses.replace(
            content, mark=_MapObject(like.mark.map, like.mark.first, like.mark.text)
        )

    @staticmethod
    def _written(content):
        """The content as the classic algebra writes its command: unfolded
        where the profile folded it to a number"""
        mark = content.mark
        return content if mark is None or mark.text is None else mark.text

    @staticmethod
    def _new_maps(series, *, bare=False):
        """series with a new map object for each content; bare if the command
        of the map is its own reference, as for a neighbour map"""
        return dataclasses.replace(
            series,
            slots=tuple(
                dataclasses.replace(
                    slot,
                    content=dataclasses.replace(
                        slot.content, mark=_MapObject(bare=bare)
                    ),
                )
                for slot in series.slots
            ),
        )

    @staticmethod
    def _has_command(content):
        """True if the map of content has a command of its own in the classic
        algebra: it is computed or a new map object whose command is more than
        its reference. A neighbour map (read at an offset in time or in cells)
        has only its reference, so the truth value of its time function is the
        operand of && and || and not the map itself."""
        return not isinstance(content, MapRef) or (
            content.mark is not None
            and content.mark.map is _OWN
            and not content.mark.bare
        )

    def _first_counts(self, series):
        """series with the first count in place of each content made of a
        count, or series itself if it has none

        The classic algebra keeps the count on the map object of the left
        map, and the map stays that object through numbers, functions,
        selections, merge() and if() on time with a number as else; if() on
        time with maps only as then and else clears the count, see
        _uncounted(). Where it is an operand of an operation with
        another map or of a cell condition of if(), the classic text takes
        the first count kept on it, not the expression built so far:
        exp(A # A) + N computes 1 + N.
        """
        if not isinstance(series, Series) or not any(
            self._counted(slot.content) for slot in series.slots
        ):
            return series
        return _like(
            series,
            (
                dataclasses.replace(slot, content=slot.content.mark.first)
                if self._counted(slot.content)
                else slot
                for slot in series.slots
            ),
        )

    def _arithmetic(self, symbol, left, right, operator):
        """An operation of two map lists writes the first count of a counted
        map (see _first_counts()) and gives new maps"""
        if not (isinstance(left, Series) and isinstance(right, Series)):
            return super()._arithmetic(symbol, left, right, operator)
        left, right = self._first_counts(left), self._first_counts(right)
        result = super()._arithmetic(symbol, left, right, operator)
        if not isinstance(result, Series):
            return result
        # Each result map is a new map with an id of its own, also where one
        # list holds no map, as td(N) in A * td(N).
        slots = []
        for slot in result.slots:
            content = dataclasses.replace(slot.content, mark=_MapObject())
            slots.append(dataclasses.replace(slot, content=content))
        return dataclasses.replace(result, slots=tuple(slots))

    def _applied(self, function, *operands):
        """Functions of time constants such as sqrt(start_doy(A, 0)) are
        computed by r.mapcalc per map in the classic algebra, while the core
        computes scalars in Python and lacks most of the functions"""
        # A condition on time (start_month(A) > 3000000000) is decided in
        # Python by the classic algebra, so it is folded here as well.
        on_time = function in _COMPARISONS and any(
            _timed(operand) and operand.sort == "scalar" for operand in operands
        )
        if not on_time and any(
            _beyond_int32(constant)
            for operand in operands
            for constant in (
                (slot.content for slot in operand.slots)
                if isinstance(operand, Series)
                else (operand,)
            )
        ):
            # r.mapcalc reads such an integer with an overflow, so folding the
            # constants here would give another number than the classic text.
            # This holds for a number in the slots of a series as well
            # (abs(if(td(A) <= 0.5, A, 3000000000))): abs() of the folded
            # number would skip the overflow the classic text runs into.
            unfolded = self._unfolded(function, operands)
            if unfolded is not None:
                return unfolded
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

    @staticmethod
    def _unfolded(function, operands):
        """The call of function for each slot of the series among operands,
        or for numbers alone, without computing it; None where the series do
        not agree, which apply() reports"""
        series = [operand for operand in operands if isinstance(operand, Series)]
        if not series:
            return Call(function, operands)
        first = series[0]
        if any(
            len(other.slots) != len(first.slots)
            or any(
                a.extent != b.extent
                for a, b in zip(other.slots, first.slots, strict=True)
            )
            for other in series
        ):
            return None
        slots = [
            dataclasses.replace(
                slot,
                content=Call(
                    function,
                    tuple(
                        operand.slots[number].content
                        if isinstance(operand, Series)
                        else operand
                        for operand in operands
                    ),
                ),
                origin=None,
            )
            for number, slot in enumerate(first.slots)
        ]
        return dataclasses.replace(first, slots=tuple(slots), sort="field")

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

    def _select(self, left, right, operator, *, one_per_map=True):
        """Selections keep one map per selected left map; with a temporal
        reference other than l its time stamp is combined with the partners
        one after the other, skipping those that do not combine

        Only the selection in braces ({:,equal}) keeps one map per map id
        (set_granularity() of the classic algebra collects the maps by id);
        A : B and A !: B keep every selected map, also two of one id.
        """
        self._pair(operator.symbol, left, right)
        # Spatial names alone fail in the reference before the selection, with
        # the error that every operator gives them; building the relation
        # raises it.
        self._relation(operator)
        for name in operator.relations:
            # The classic selection with a temporal operator refuses spatial
            # names, also with the temporal reference l.
            if name not in TEMPORAL_RELATIONS:
                msg = f"Unpermitted temporal relation name '{name}'"
                raise SyntaxError(msg)
        selected = self._selected(left, right, operator)
        if one_per_map and not self._sampled:
            selected = self._one_per_map(selected)
        return selected

    def _source(self, content):
        """The id of the map that the map of content is, or None: a computed
        map keeps the id of the first map it was made of, and so does a count
        of the left map"""
        if content.mark is not None:
            return content.mark if content.mark.map is _OWN else content.mark.map
        if isinstance(content, MapRef):
            return None if content.offset else content.ident
        if isinstance(content, Call):
            found = [ident for ident in map(self._source, content.args) if ident]
            # An operation of two maps is a new map, one with a number is the
            # map itself changed.
            return id(content) if len(found) > 1 else next(iter(found), None)
        return None

    def _one_per_map(self, series):
        """series with one slot per registered map: a map that came twice
        with different time stamps, as in merge(tshift(A, "1 hours"), A),
        stays with the latest start once it is selected, as the reference
        keeps its selected maps in a dictionary by map id, the last of the
        start-sorted list winning. Not where a dataset reads one map for
        several granules (granularity mode): there the reference holds
        separate map objects of the same id and keeps them all"""

        def map_id(slot):
            return None if slot.extent is None else self._source(slot.content)

        latest = {}
        for slot in series.slots:
            ident = map_id(slot)
            if ident is not None and (
                ident not in latest or slot.extent.start >= latest[ident].extent.start
            ):
                latest[ident] = slot
        slots = [
            slot
            for slot in series.slots
            if map_id(slot) is None or latest[map_id(slot)] is slot
        ]
        return _like(series, slots)

    def _selected(self, left, right, operator):
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
        slots = []
        targets = list(left.slots)
        for slot in counts.slots:
            # A left map without partner has no count, so the counts are
            # matched to the left maps by time stamp, in order.
            target = targets.pop(
                next(
                    i for i, found in enumerate(targets) if found.extent == slot.extent
                )
            )
            # Equal counts are copied, so that each has an identity.
            mark = _MapObject(self._source(target.content))
            content = dataclasses.replace(slot.content, mark=mark)
            # Counted again, the map keeps its first count.
            mark.first = (
                target.content.mark.first if self._counted(target.content) else content
            )
            slots.append(dataclasses.replace(slot, content=content))
        counts = dataclasses.replace(counts, slots=tuple(slots))
        self._hashes.note(counts)
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
            result = operations.pairs(
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
            if self._kind != "vector":
                # Each partner gives a new map with an id of its own; the
                # maps of vector maps share the id of the left one.
                # Equal contents are copied, so that each has an identity.
                slots = []
                for slot in result.slots:
                    content = dataclasses.replace(slot.content, mark=_MapObject())
                    slots.append(dataclasses.replace(slot, content=content))
                return dataclasses.replace(result, slots=tuple(slots))
            return result
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

    def _index(self, node):
        """A map read at an offset, in time or in cells, is a new map object
        in the classic algebra with an id of its own, whose command is only
        its reference (bare, see _has_command())"""
        result = super()._index(node)
        return (
            self._new_maps(result, bare=True) if isinstance(result, Series) else result
        )

    def _remember_commands(self, result, argument):
        """Note the commands of the argument of a time function

        The classic algebra gives a map of the argument that carries a
        command (a computed expression, not a registered map or a map read
        at an offset) a condition on its time as the command of the
        argument; see _logical().
        """
        slots = argument.slots
        if (
            isinstance(result, Series)
            and result.sort == "scalar"
            and len(result.slots) == len(slots)
            and any(self._has_command(slot.content) for slot in slots)
        ):
            self._commands.note(result, argument)

    def _carry_commands(self, result, source):
        """Note for result the commands of source, a condition on a time
        function: result keeps the maps of the left operand, so what the
        classic algebra found at their argument is still there"""
        argument = self._commands.get(source)
        if argument is None:
            return
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
        """A comparison of the hash operator itself (A # B == 2) is a condition
        on time on the first count; any other comparison of a count, as
        (A # B) + 1 > 2, is a cell condition in the r.mapcalc text"""
        if left in self._hashes:
            left = self._first_counts(left)
        else:
            left, right = (
                dataclasses.replace(operand, sort="field")
                if self._first_counts(operand) is not operand
                and operand.sort == "scalar"
                else operand
                for operand in (left, right)
            )
        result = super()._compare(symbol, left, right)
        for operand, other in ((left, right), (right, left)):
            known = self._commands.get(operand)
            if known is not None and not isinstance(other, Series):
                self._remember_commands(result, known)
        return result

    def _as_command(self, series):
        """series, with the command of the argument of its time function in
        place of the truth value of each map that has one

        A condition that joins a condition on a time function with one on
        cells (A > 1 && start_month(A * 0) == 1) takes the command of the
        argument, so the cells of the expression decide and not the time,
        where the classic algebra finds a command at the argument. A
        registered map and a map read at an offset have none, and their
        time decides.
        """
        known = self._commands.get(series)
        if known is None:
            return series
        slots = [
            slot
            if not self._has_command(argument.content)
            else dataclasses.replace(slot, content=argument.content)
            for slot, argument in zip(series.slots, known.slots, strict=True)
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
            return self._logical_per_partner(symbol, left, relation, right, operator)
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

    def _logical_per_partner(self, symbol, left, relation, right, operator):
        """&& and || with the temporal reference r: a map per partner, with
        the time stamp of the partner and the whole condition as content

        The classic algebra joins all partners of a left map with the
        aggregate (a1 > 1 && (b1 > 1 && b2 > 1)) and gives every partner a
        copy of that map, as it does for arithmetic with r.
        """
        aggregate = "&&" if operator.aggregate == "&" else "||"
        joined = []
        for slot, found in zip(
            left.slots, self._related(left, relation, right), strict=True
        ):
            others = [right.slots[index].content for index in found]
            if not others:
                joined.append(None)
                continue
            other = others[0]
            for content in others[1:]:
                other = call(aggregate, other, content)
            joined.append(_joined(symbol, slot.content, other))
        return self._place(left, relation, right, joined, "r")

    def _place(self, left, relation, right, conditions, temporal, sort=None):
        """The conditions of the left maps, with the time stamps that the
        temporal reference gives the pairs of a map and its related maps

        :param conditions: One content for each slot of left, in its order
        :param temporal: l, r, u, i or d; r gives a map per partner that
            carries the whole condition of its left map, the others one map
            per left map.
        :param sort: The sort of the result, that of left if omitted
        """
        # The left maps are marked by their position, so that each pair
        # finds the condition of its left map.
        marked = _like(
            left,
            (
                dataclasses.replace(slot, content=Const(number))
                for number, slot in enumerate(left.slots)
            ),
        )
        options = {
            "order": "written",
            "unique": False,
            "box": "intersection",
            "mixed_times": self.profile.mixed_times,
        }
        if temporal == "r":
            placed = operations.pairs(
                marked, relation, right, extent="right", **options
            )
        else:
            placed = operations.gather(
                marked,
                relation,
                right,
                reduce=None,
                extent=_EXTENTS[temporal],
                failure="stop",
                **options,
            )
        return _like(
            placed,
            (
                dataclasses.replace(slot, content=conditions[slot.content.value])
                for slot in placed.slots
            ),
            sort,
        )

    def _compare_related(self, symbol, left, right, operator):
        """A comparison of two datasets: each left map is compared with every
        related map, and the comparisons are joined by the aggregation, as
        (a1 >= f1 && a1 >= f2)

        A count is a cell value here, as in other cell conditions. A left map
        without related map gives no map.
        """
        left, right = self._cells(left), self._cells(self._aligned(left, right))
        relation = self._relation(operator)
        join = "&&" if operator.aggregate == "&" else "||"
        conditions = []
        for slot, found in zip(
            left.slots, self._related(left, relation, right), strict=True
        ):
            condition = None
            for index in found:
                part = call(symbol, slot.content, right.slots[index].content)
                condition = part if condition is None else call(join, condition, part)
            conditions.append(condition)
        return self._place(
            left, relation, right, conditions, operator.temporal, "field"
        )

    def _cells(self, series):
        """The series with its counts as cell values"""
        series = self._first_counts(series)
        if series.sort == "scalar" and _timed(series):
            return dataclasses.replace(series, sort="field")
        return series

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
            # Copies of the neighbour contents, equal to them but with an
            # identity of their own, which tshift(), merge() and the other
            # operations of a selection keep: statement() finds them so in
            # the result, also after they were moved in time.
            values = time_functions.neighbour(series, offset)
            slots = []
            for slot in values.slots:
                content = dataclasses.replace(slot.content)
                self._time_values[id(content)] = content
                slots.append(dataclasses.replace(slot, content=content))
            return _like(values, slots)
        if offset is not None:
            _check_time_variable(name, used)
            variable = time_functions.timevar(series, name)
            # The value of a neighbour is a number in the map, so a condition
            # on it judges cells, not time.
            return self._new_maps(
                dataclasses.replace(
                    time_functions.neighbour(variable, offset), sort="field"
                )
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
        return super()._function(node)

    def _call(self, name, arguments, relation):
        # merge() takes a _Mixed whole, as it lists the maps of all units.
        if name == "merge":
            return super()._call(name, arguments, relation)
        return self._each_unit(self._call_unit, name, arguments, relation)

    def _call_unit(self, name, arguments, relation):
        result = super()._call(name, arguments, relation)
        if name in _BUFFERS and isinstance(result, Series):
            # Each buffer is a new map object (v.buffer of its own), also
            # where the buffer of the same map is made twice.
            result = self._new_maps(result)
        if (
            name in _CONDITION_FUNCTIONS
            and isinstance(result, Series)
            and result.sort == "scalar"
            and not result.timeless
        ):
            # These are conditions on cells in the classic grammar, also of a
            # count or a time value, so the if() of a field condition applies.
            result = dataclasses.replace(result, sort="field")
        return result

    def _merge(self, first, second):
        """The classic map lists mix maps and numbers freely: a number in a
        list is a constant map, so merging a count with maps is a list of
        maps. A map that the second list shares with the first is kept once;
        what repeats in the first list stays, as the lists of the classic
        algebra tell two computed maps apart by the map they came from.

        Shared means the same map id, time stamp and text, as in the classic
        algebra; the core compares the contents only, which would take the
        counts of two datasets (merge(A # N, N # A)) for one map.
        """
        firsts, seconds = (
            value.parts if isinstance(value, _Mixed) else (value,)
            for value in (first, second)
        )
        if len({part.sort for part in (*firsts, *seconds)}) > 1:
            firsts, seconds = (
                tuple(dataclasses.replace(part, sort="field") for part in parts)
                for parts in (firsts, seconds)
            )
        first, second = firsts[0], seconds[0]
        # The check of the map types that operations.merge() makes
        operations._check_comparable(  # noqa: SLF001
            first, second, mixed_times="unrelated"
        )
        first_listed = _listed(firsts)
        known = {self._merge_key(slot) for slot in first_listed}
        kept = []
        second_listed = _listed(seconds)
        for slot in second_listed:
            key = self._merge_key(slot)
            if key not in known:
                known.add(key)
                kept.append(slot)
        dropped = len(second_listed) - len(kept)
        if dropped:
            # The warning of the core, with its fallback before tgis.init()
            operations._warn(  # noqa: SLF001
                _("merge() dropped {count} duplicate map(s)").format(count=dropped)
            )
        # One series per unit, so that the core keeps all its slots and only
        # ranks them; the ranks are those of the whole list. A map without
        # time stamp goes with absolute time, where the series refuses it
        # beside other maps.
        units = {}
        for n, slot in enumerate((*first_listed, *kept)):
            unit = None if slot.extent is None else slot.extent.unit
            units.setdefault(unit, []).append(dataclasses.replace(slot, rank=n))
        spatial = any(part.spatial for part in (*firsts, *seconds))
        return _gathered(
            [
                operations.merge(
                    Series(tuple(slots), first.kind, first.sort, spatial, first.order),
                    keep_first_repeats=True,
                )
                for slots in list(units.values()) or [[]]
            ]
        )

    def _merge_key(self, slot):
        """The identity of a map in merge(): time stamp, text and the id of
        the map, as the classic key (map id, time stamp, command)

        Box and origin, which the slots of the core also compare, follow from
        the map id and the text: a map of one id and text has one box, and
        the origin is the id of a registered map.
        """
        return (slot.extent, self._written(slot.content), self._source(slot.content))

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
        for position, slot in enumerate(series.listed()):
            map_ = as_map(slot.extent)
            # Relative time is buffered by a whole number of its unit.
            map_.temporal_buffer(str(value) if slot.extent.unit is None else int(value))
            extent = extent_from(map_.get_temporal_extent(), slot.extent.unit)
            # A map that keeps its time stamp is still the registered map.
            origin = slot.origin if extent == slot.extent else None
            # The classic list keeps its order when the buffer moves a start
            # past the next one, and the result maps are numbered by it.
            rank = position if slot.rank is None else slot.rank
            slots.append(Slot(extent, slot.content, slot.space, origin, rank))
        return _like(series, slots)

    def _if(self, arguments, relation):
        """The classic if(): conditions on map values choose per cell, one map
        per pair of condition and conclusion; conditions on temporal
        variables judge each conclusion map by the conditions related to it.
        The maps of then and else are listed together in time order, where
        the core lists those of then first."""
        # Without maps in then and else, the result is the list of the
        # condition as it stands, also if that list is not in time order.
        listed = not any(_timed(branch) for branch in arguments[1:])
        order = (lambda series: series) if listed else self._in_time_order
        if len(arguments) not in (2, 3):
            return order(super()._if(arguments, relation))
        condition = arguments[0]
        if (
            isinstance(condition, Series)
            and condition.sort == "scalar"
            and not condition.timeless
            and all(_timed(branch) for branch in arguments[1:])
            # The core checks the branches of the vector algebra itself.
            and (
                self._kind != "vector"
                or all(_vector_field(branch) for branch in arguments[1:])
            )
        ):
            return self._uncounted(
                self._in_time_order(
                    self._judged_if(condition, *arguments[1:], relation=relation)
                )
            )
        if self._kind == "vector":
            return order(super()._if(arguments, relation))
        if not (_timed(condition) and condition.sort == "field"):
            return order(super()._if(arguments, relation))
        then = arguments[1]
        otherwise = arguments[2] if len(arguments) == 3 else _ABSENT
        return order(self._field_if(condition, then, otherwise, relation))

    def _uncounted(self, series):
        """series with the counted maps no longer counted, but still the maps
        they were

        if() on time with maps as then and else ends by clearing the values
        of the selected map objects (check_stds(..., clear=True)), the count
        among them, and keeps their text; the form with a number as else
        does not, see _temporal_if().
        """
        slots = []
        for slot in series.slots:
            if self._counted(slot.content):
                # A copy, so that the count stays with the original content
                content = dataclasses.replace(
                    slot.content, mark=_MapObject(slot.content.mark.map)
                )
                slot = dataclasses.replace(slot, content=content)
            slots.append(slot)
        return dataclasses.replace(series, slots=tuple(slots))

    def _temporal_if(self, condition, then, otherwise, relation, first):
        """if() on time with maps as then and a number as else: the classic
        algebra writes the number on the map objects of then that the
        condition rejects, so a counted map there stays counted"""
        result = super()._temporal_if(condition, then, otherwise, relation, first)
        if not (
            _timed(then)
            and otherwise is not _ABSENT
            and not _timed(otherwise)
            and any(self._counted(slot.content) for slot in then.slots)
        ):
            return result
        mine = {id(slot.content) for slot in then.slots}
        chosen = {id(slot.content) for slot in result.slots}
        rejected = {}
        for slot in then.slots:
            if id(slot.content) not in chosen:
                rejected.setdefault(slot.extent, []).append(slot)
        slots = []
        for slot in result.slots:
            waiting = rejected.get(slot.extent)
            if waiting and id(slot.content) not in mine:
                rejected_content = waiting.pop(0).content
                if self._counted(rejected_content):
                    content = self._counting(slot.content, rejected_content)
                    slot = dataclasses.replace(slot, content=content)
            slots.append(slot)
        return _like(result, slots)

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
        # The condition and the conclusion maps are operands of the classic
        # text, so a counted map is its first count there; see _first_counts().
        condition, then, otherwise = map(
            self._first_counts, (condition, then, otherwise)
        )
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
        elif timed_then or timed_else:
            timed = then if timed_then else otherwise
            constant = _constant(otherwise if timed_then else then)
            conclusion = []
            for slot in timed.slots:
                if self._counted(slot.content):
                    # The classic algebra writes "map, number" or "number,
                    # map" as the command of the map, which a counted map
                    # loses to its first count: the number is dropped and
                    # the count stands alone as the then part.
                    pair = (slot.content, Const(0))
                elif timed_then:
                    pair = (slot.content, constant)
                else:
                    pair = (constant, slot.content)
                conclusion.append((slot, pair))
        else:
            return self._numbers_if(condition, then, otherwise)
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
                # Each is a new map with an id of its own, also where the text
                # folds to a map: if(1, a1) is not a1.
                content = dataclasses.replace(
                    call("if", slot.content, *contents[index]), mark=_MapObject()
                )
                slots.append(Slot(target.extent, content, target.space))
        return _like(condition, slots, "field")

    def _numbers_if(self, condition, then, otherwise):
        """if() of a cell condition with numbers as then and else: the list of
        the condition, each map with its if() text

        The classic algebra writes the text on the map objects of the
        condition, so a counted condition map stays the same counted map.
        """
        contents = (_constant(then), _constant(otherwise))
        slots = []
        for slot in condition.slots:
            content = call("if", slot.content, *contents)
            if self._counted(slot.content):
                # Copied, so that each has an identity
                content = self._counting(content, slot.content)
                content.mark.text = Call("if", (self._written(slot.content), *contents))
            slots.append(Slot(slot.extent, content, slot.space, rank=slot.rank))
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
