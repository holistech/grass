"""The operations of the algebra core: pure functions on series

No operation changes a series; each returns a new one. Series are related
only through select(), pairs() and gather(); apply() and the conditions
need series of equal time stamps and never align them silently.
"""

from dataclasses import replace

from ._adapters import as_map, extent_from
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
    if extent.end is None:
        return f"{extent.start}"
    return f"{extent.start} .. {extent.end}"


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

    :raises ValueError: if the time stamps differ, naming the first slot that
        differs, or if a scalar result cannot be computed in Python
    """
    return _apply(function, operands, function)


def lift(series):
    """Turn a scalar series into a field that is constant in each map"""
    return replace(series, sort="field")


def cell_offset(series, *offset):
    """Read each map at a cell offset (row, column), as A[1,0] does

    r.mapcalc knows offsets of maps only, so the slots must hold maps, not
    expressions.
    """
    slots = []
    for slot in series.slots:
        if not isinstance(slot.content, MapRef):
            msg = "Only a map can be read at a cell offset, not an expression"
            raise ValueError(msg)
        content = MapRef(slot.content.ident, tuple(offset))
        slots.append(Slot(slot.extent, content, slot.space))
    return replace(series, slots=tuple(slots))
