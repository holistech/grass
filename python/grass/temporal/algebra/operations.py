"""The operations of the algebra core: pure functions on series

No operation changes a series; each returns a new one. Series are related
only through select(), pairs() and gather(); apply() and where() need
series of equal time stamps and never align them silently. choose() judges
each slot by the condition of its own time stamp.
"""

import warnings
from collections import Counter, defaultdict
from dataclasses import replace

from grass.temporal.core import get_tgis_message_interface

from . import reducers
from ._adapters import as_map, extent_from
from ._checks import (
    check_callable,
    check_int,
    check_operands,
    check_relation,
    check_series,
)
from .content import NULL, Call, Const, MapRef, SeriesReduce, call
from .relations import related as related_indices
from .series import Series, Slot

PAIR_EXTENTS = ("left", "right", "union", "intersection", "disjoint")

_COMBINE = {
    "union": "temporal_union",
    "intersection": "temporal_intersection",
    "disjoint": "temporal_disjoint_union",
}


def _check_option(name, value, allowed):
    if value not in allowed:
        msg = f"{name} must be one of {', '.join(allowed)}, got {value!r}"
        raise ValueError(msg)


def _check_comparable(first, second):
    """Relations exist only between series of one map and temporal type

    related() does not check this itself: on mixed absolute and relative
    time, or on different units, it finds no relation instead of failing.
    """
    if first.kind != second.kind:
        msg = f"A {first.kind} series cannot be related to a {second.kind} series"
        raise ValueError(msg)
    units = {
        slot.extent.unit
        for slot in (*first.slots, *second.slots)
        if slot.extent is not None
    }
    if len(units) > 1:
        msg = "Series of different temporal types or units cannot be related"
        raise ValueError(msg)


def _joined_sort(*series):
    """A field if any operand is a field, else a scalar"""
    return "field" if any(part.sort == "field" for part in series) else "scalar"


def _origin(content, extent, *slots):
    """The registered map that a result slot equals, if any"""
    for slot in slots:
        if slot.origin is not None and (content, extent) == (slot.content, slot.extent):
            return slot.origin
    return None


def _combine(target, others, mode):
    """The time stamp of a target combined with related slots

    "left" and "target" keep the time stamp of the target. The other modes
    fold the target with each related slot in turn using the methods of
    grass.temporal. None means that the combination is empty.
    """
    if mode in {"left", "target"}:
        return target.extent
    unit = target.extent.unit
    current = target.extent
    for slot in others:
        combined = getattr(as_map(current), _COMBINE[mode])(as_map(slot.extent))
        current = extent_from(combined, unit)
        if current is None:
            return None
    return current


def select(left, relation, other, *, related=True):
    """Keep the slots l of left for which a slot x of other with "l R x"
    exists (related=True) or none exists (related=False)

    Content and time stamps stay as they are. select(L, R, X) and
    select(L, R, X, related=False) are disjoint and together are L.
    """
    check_series(left, "left")
    check_relation(relation)
    check_series(other, "other")
    _check_comparable(left, other)
    matches = related_indices(left.slots, relation, other.slots)
    slots = tuple(
        slot
        for slot, found in zip(left.slots, matches, strict=True)
        if bool(found) == related
    )
    return replace(
        left, slots=slots, spatial=left.spatial or relation.spatial is not None
    )


def pairs(left, relation, other, *, extent="left", content=None):
    """One slot per pair (l, x) with "l R x"

    :param extent: the time stamp of a slot: that of l ("left"), of x
        ("right"), or the union, intersection or disjoint union of both; a
        pair without intersection is left out
    :param content: function of the contents of l and x that returns the
        content of the slot; the default keeps the content of l
    """
    check_series(left, "left")
    check_relation(relation)
    check_series(other, "other")
    if content is not None:
        check_callable(content, "content")
    _check_option("extent", extent, PAIR_EXTENTS)
    _check_comparable(left, other)
    matches = related_indices(left.slots, relation, other.slots)
    slots = []
    for slot, found in zip(left.slots, matches, strict=True):
        for index in found:
            partner = other.slots[index]
            if extent == "right":
                time, space = partner.extent, partner.space
            else:
                time, space = _combine(slot, [partner], extent), slot.space
            if time is None:
                continue
            value = (
                slot.content
                if content is None
                else content(slot.content, partner.content)
            )
            slots.append(Slot(time, value, space, _origin(value, time, slot, partner)))
    sort = left.sort if content is None else _joined_sort(left, other)
    spatial = left.spatial or other.spatial or relation.spatial is not None
    return Series(tuple(slots), left.kind, sort, spatial)


def _describe(extent):
    if extent is None:
        return "no slot"
    # The unit tells apart relative times that read alike, e.g. series in
    # days and in hours.
    unit = "" if extent.unit is None else f" {extent.unit}"
    if extent.end is None:
        return f"{extent.start}{unit}"
    return f"{extent.start} .. {extent.end}{unit}"


def _check_aligned(first, second, name):
    """Stop unless both series have the same time stamps in the same order"""
    times = [slot.extent for slot in first.slots]
    others = [slot.extent for slot in second.slots]
    if times == others:
        return
    # Series of different length differ at the first slot one of them lacks.
    index = next(
        (
            i
            for i, (one, two) in enumerate(zip(times, others, strict=False))
            if one != two
        ),
        min(len(times), len(others)),
    )
    msg = (
        f"{name}() needs series with equal time stamps; they differ at slot "
        f"{index}: {_describe(times[index] if index < len(times) else None)} and "
        f"{_describe(others[index] if index < len(others) else None)}. Relate "
        "the series with gather() or pairs() first."
    )
    raise ValueError(msg)


def _content_at(operand, index):
    if isinstance(operand, Series):
        return operand.slots[0 if operand.timeless else index].content
    if operand is None:
        return NULL
    if isinstance(operand, (Const, MapRef, Call, SeriesReduce)):
        return operand
    return Const(operand)


def _apply(function, operands, name):
    check_operands(function, operands)
    timed = [
        operand
        for operand in operands
        if isinstance(operand, Series) and not operand.timeless
    ]
    if not timed:
        msg = f"{name}() needs a series with time stamps"
        raise ValueError(msg)
    first = timed[0]
    for operand in timed[1:]:
        _check_aligned(first, operand, name)
    series = [operand for operand in operands if isinstance(operand, Series)]
    if len({part.kind for part in series}) > 1:
        msg = f"{name}() cannot combine series of different map types"
        raise ValueError(msg)
    sort = _joined_sort(*series)
    slots = []
    for index, slot in enumerate(first.slots):
        value = call(function, *(_content_at(operand, index) for operand in operands))
        if sort == "scalar" and not isinstance(value, Const):
            msg = f"{function}() cannot be computed for scalar values"
            raise ValueError(msg)
        partners = (operand.slots[index] for operand in timed)
        slots.append(
            Slot(slot.extent, value, slot.space, _origin(value, slot.extent, *partners))
        )
    spatial = any(part.spatial for part in series)
    return Series(tuple(slots), first.kind, sort, spatial)


def apply(function, *operands):
    """Apply an operator or a function of the raster algebra slot by slot

    All series operands need the same time stamps in the same order. Numbers
    and maps without time stamp are used in every slot, None is null. There
    is no implicit alignment: relate series with gather() or pairs() first.
    The result is a field if any operand is a field; a scalar result is
    computed in Python.

    :raises TypeError: for an operand that is not a Series, a number, a bool,
        None or a content node
    :raises ValueError: if the time stamps differ, naming the first slot that
        differs, or if a scalar result cannot be computed in Python
    """
    return _apply(function, operands, function)


def lift(series):
    """Turn a scalar series into a field that is constant in each map"""
    check_series(series)
    return replace(series, sort="field")


def cell_offset(series, *offset):
    """Read each map at a cell offset (row, column), as A[1,0] does

    r.mapcalc knows offsets of maps only, so the slots must hold maps, not
    expressions.
    """
    check_series(series)
    for step in offset:
        check_int(step, "offset")
    slots = []
    for slot in series.slots:
        if not isinstance(slot.content, MapRef):
            msg = "Only a map can be read at a cell offset, not an expression"
            raise ValueError(msg)
        content = MapRef(slot.content.ident, tuple(offset))
        slots.append(Slot(slot.extent, content, slot.space))
    return replace(series, slots=tuple(slots))


GATHER_EXTENTS = ("target", "union", "intersection", "disjoint")
MISSING = ("drop", "null", "keep")
EQUAL_TIMES = ("all", "pairwise")
NULLS = ("propagate", "skip")


def _pair_equal_times(targets, matches, others):
    """Pair maps of equal time stamps like numpy broadcasting

    A single map on one side goes with all maps of its time on the other
    side, n maps go with n maps one to one in the order of the series, and
    other counts are an error.
    """
    positions = {}
    counts = defaultdict(int)
    for index, slot in enumerate(targets):
        positions[index] = counts[slot.extent]
        counts[slot.extent] += 1
    paired = []
    for index, found in enumerate(matches):
        size = counts[targets[index].extent]
        groups = defaultdict(list)
        for other_index in found:
            groups[others[other_index].extent].append(other_index)
        chosen = []
        for time, members in groups.items():
            if size == 1 or len(members) == 1:
                chosen.extend(members)
            elif len(members) == size:
                chosen.append(members[positions[index]])
            else:
                msg = (
                    f"{size} maps of the time stamp {_describe(targets[index].extent)} "
                    f"cannot be paired with {len(members)} maps of the time stamp "
                    f"{_describe(time)}"
                )
                raise ValueError(msg)
        paired.append(sorted(chosen))
    return paired


def gather(
    target,
    relation,
    other,
    *,
    reduce,
    missing="drop",
    extent="target",
    equal_times="all",
    nulls="propagate",
):
    """For each slot t of target, reduce the slots x of other with "t R x"

    The result has at most one slot per target slot.

    :param reduce: how the related slots are combined: "sum", "prod", "min",
        "max", "mean", "count", "all", "any", "first", "last", fold(op), or
        None to keep the content of the target. The other reducers leave the
        content of the target out, except fold(), which starts with it.
    :param missing: a target without related slot is dropped ("drop"),
        gets a null content ("null") or stays as it is ("keep")
    :param extent: the time stamp of a result slot: that of the target, or
        its union, intersection or disjoint union with the related slots; a
        target whose combined time stamp is empty (an intersection without
        overlap) is left out whatever missing says
    :param equal_times: "all" relates every map of a time to a target,
        "pairwise" pairs maps of equal time stamps one to one; without effect
        if space takes part in the relation
    :param nulls: "propagate" makes a cell null if a related cell is null,
        "skip" passes over null cells
    :raises ValueError: for missing="keep" with a reducer whose result has
        another sort than the target
    """
    check_series(target, "target")
    check_relation(relation)
    check_series(other, "other")
    _check_option("missing", missing, MISSING)
    _check_option("extent", extent, GATHER_EXTENTS)
    _check_option("equal_times", equal_times, EQUAL_TIMES)
    _check_option("nulls", nulls, NULLS)
    reducers.check(reduce, nulls)
    _check_comparable(target, other)
    sort = reducers.sort_of(reduce, target.sort, other.sort)
    if missing == "keep" and sort != target.sort:
        msg = (
            f'missing="keep" with reduce={reduce!r} would mix kept {target.sort} '
            f"maps with {sort} values"
        )
        raise ValueError(msg)
    matches = related_indices(target.slots, relation, other.slots)
    if equal_times == "pairwise" and relation.spatial is None:
        matches = _pair_equal_times(target.slots, matches, other.slots)
    slots = []
    for slot, found in zip(target.slots, matches, strict=True):
        partners = [other.slots[index] for index in found]
        if not partners:
            if missing == "null":
                slots.append(Slot(slot.extent, NULL, slot.space))
            elif missing == "keep":
                slots.append(slot)
            continue
        time = _combine(slot, partners, extent)
        if time is None:
            continue
        value = reducers.reduce(
            reduce, slot.content, [partner.content for partner in partners], nulls
        )
        slots.append(Slot(time, value, slot.space, _origin(value, time, slot)))
    spatial = target.spatial or other.spatial or relation.spatial is not None
    return Series(tuple(slots), target.kind, sort, spatial)


def _warn(message):
    """Warn through grass.temporal, or through Python before tgis.init()"""
    # The messenger of grass.temporal exists only after init(), but the
    # operations on series need no session.
    messenger = get_tgis_message_interface()
    if messenger is None:
        warnings.warn(message, stacklevel=3)
    else:
        messenger.warning(message)


def choose(condition, then, otherwise=None):
    """Select whole slots by a scalar condition

    A slot of then is kept where the condition of its time stamp is true, a
    slot of otherwise where it is false, so then and otherwise may have
    different time stamps. A slot without a condition of its time stamp, or
    with a null one, is left out, as gather() with missing="drop" leaves it
    out. Several conditions of one time stamp are paired one to one, in
    order, with the slots of that time stamp, as equal_times="pairwise"
    builds them. A condition without time stamp decides for every slot of
    every branch, as a map without time stamp does in apply().

    :raises TypeError: if the condition is not a scalar series
    :raises ValueError: if a time stamp has several conditions and another
        number of slots in a branch, if a timed condition meets a branch map
        without time stamp, or if the series cannot be related
    """
    check_series(condition, "condition")
    check_series(then, "then")
    if otherwise is not None:
        check_series(otherwise, "otherwise")
    if condition.sort != "scalar":
        msg = "choose() needs a scalar condition; use where() for one per cell"
        raise TypeError(msg)
    values = defaultdict(list)
    for slot in condition.slots:
        values[slot.extent].append(slot.content.value)
    branches = [then] if otherwise is None else [then, otherwise]
    slots = []
    for branch, wanted in zip(branches, (True, False), strict=False):
        _check_comparable(condition, branch)
        slots.extend(_chosen(branch, values, wanted))
    spatial = any(part.spatial for part in (condition, *branches))
    return Series(tuple(slots), then.kind, _joined_sort(*branches), spatial)


def _chosen(branch, values, wanted):
    """The slots of branch whose condition has the truth value wanted"""
    counts = Counter(slot.extent for slot in branch.slots)
    seen = Counter()
    chosen = []
    for slot in branch.slots:
        if slot.extent is None and values and None not in values:
            msg = "choose() cannot select a map without time stamp by a timed condition"
            raise ValueError(msg)
        # A timeless condition is the only one and decides for every slot.
        conditions = values.get(slot.extent) or values.get(None, [])
        if len(conditions) > 1 and len(conditions) != counts[slot.extent]:
            msg = (
                f"choose() cannot pair {len(conditions)} conditions with "
                f"{counts[slot.extent]} maps of {_describe(slot.extent)}"
            )
            raise ValueError(msg)
        if not conditions:
            continue
        value = conditions[seen[slot.extent] if len(conditions) > 1 else 0]
        seen[slot.extent] += 1
        if value is not None and bool(value) is wanted:
            chosen.append(slot)
    return chosen


def where(condition, then, otherwise=None):
    """Choose per cell: if(condition, then, otherwise)

    Without otherwise a cell is null where the condition is false. A scalar
    condition is lifted to a constant field. condition, then and otherwise
    need equal time stamps; numbers are used in every slot.
    """
    check_series(condition, "condition")
    if condition.sort == "scalar":
        condition = lift(condition)
    return _apply("if", (condition, then, otherwise), "where")


def merge(*series):
    """The union of series

    Identical slots are kept once with a warning, so that a later reduction
    does not count a map twice. Slots are identical if they agree in time
    stamp, content, space and origin. Different maps of equal time are all
    kept.

    :raises ValueError: if no series is given, or the series differ in sort,
        map type, temporal type or unit
    """
    if not series:
        msg = "merge() needs at least one series"
        raise ValueError(msg)
    for number, part in enumerate(series, start=1):
        check_series(part, f"series {number}")
    first = series[0]
    for part in series[1:]:
        if part.sort != first.sort:
            msg = "merge() needs series of one sort, fields or scalars"
            raise ValueError(msg)
        _check_comparable(first, part)
    seen = set()
    slots = []
    duplicates = 0
    for part in series:
        for slot in part.slots:
            if slot in seen:
                duplicates += 1
                continue
            seen.add(slot)
            slots.append(slot)
    if duplicates:
        _warn(_("merge() dropped {count} duplicate slot(s)").format(count=duplicates))
    spatial = any(part.spatial for part in series)
    return Series(tuple(slots), first.kind, first.sort, spatial)
