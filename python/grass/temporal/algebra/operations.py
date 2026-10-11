"""The operations of the algebra core: pure functions on series

No operation changes a series; each returns a new one. Series are related
only through select(), pairs() and gather(); apply() and the conditions
need series of equal time stamps and never align them silently.
"""

from dataclasses import replace

from ._adapters import as_map, extent_from
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
