"""The operations of the algebra core: pure functions on series

No operation changes a series; each returns a new one. Series are related
only through select(), pairs() and gather(); apply() and where() need
series of equal time stamps and never align them silently. choose() judges
each slot by the condition of its own time stamp.
"""

import math
from collections import Counter, defaultdict
from dataclasses import replace

from . import reducers
from ._adapters import as_map, extent_from
from ._checks import (
    check_callable,
    check_int,
    check_operands,
    check_option,
    check_relation,
    check_series,
    require,
)
from .backends import BUFFERS, VECTOR_FUNCTIONS
from .content import (
    NULL,
    Const,
    MapRef,
    ScalarFunctionError,
    call,
)
from .maptypes import DIMENSIONS
from .relations import ORDERS
from .relations import related as related_indices
from .series import Series, Slot, Space
from .variants import (
    check_comparable,
    combine_boxes,
    content_at,
    describe_extent,
    pair_equal_times,
    warn,
)

PAIR_EXTENTS = ("left", "right", "union", "intersection", "disjoint")
SPACES = ("keep", "union", "intersection")

_COMBINE = {
    "union": "temporal_union",
    "intersection": "temporal_intersection",
    "disjoint": "temporal_disjoint_union",
}


def _joined_sort(*series):
    """A field if any operand is a field, else a scalar"""
    return "field" if any(part.sort == "field" for part in series) else "scalar"


def _in_time_order(slot):
    """The slot without a list order: a selection lists its maps in time order"""
    return slot if slot.rank is None else replace(slot, rank=None)


def _origin(content, extent, *slots):
    """The registered map that a result slot equals, if any"""
    for slot in slots:
        if slot.origin is not None and (content, extent) == (slot.content, slot.extent):
            return slot.origin
    return None


FAILURES = ("empty", "stop", "skip")
BOXES = ("intersection", "union")


def _combine(target, others, mode):
    """The time stamp of a target combined with related slots, None if empty

    A convenience for the callers that need the time stamp only; see
    _combine_steps().
    """
    found = _combine_steps(target, others, mode)
    return None if found is None else found[0]


def _combine_steps(target, others, mode, *, box=None, failure="empty", three_d=False):
    """The time stamp and the box of a target combined with related slots

    "left" and "target" keep the time stamp of the target, "right" takes that
    of each related slot in turn, so that of the last one. The other modes
    fold the target with each related slot in turn using the methods of
    grass.temporal. With box the box of the target is combined with the box
    of each related slot in the same step (see combine_boxes()).

    A step fails if the time stamps do not combine or the boxes do not. The
    failing step still applies the half that did combine, as the classic
    algebra does (overlay_map_extent() evaluates the spatial and the temporal
    overlay one after the other and without short circuit, and both change
    the same map). failure says what a failing step means:

    - "empty": the whole combination is empty
    - "stop": the slots after it are left out, and what the steps before and
      the half step itself set stays; the combination is empty only if no step
      before succeeded
    - "skip": the slot is passed over, and the combination is that of the
      other slots, at worst the target as it is

    :return: (time stamp, box), or None if the combination is empty
    """
    extent, space = target.extent, target.space
    succeeded = 0
    for partner in others:
        ok = True
        if mode == "right":
            extent = partner.extent
        elif mode not in {"left", "target"}:
            combined = getattr(as_map(extent), _COMBINE[mode])(as_map(partner.extent))
            found = extent_from(combined, target.extent.unit)
            if found is None:
                ok = False
            else:
                extent = found
        if box is not None and space is not None and partner.space is not None:
            found = combine_boxes(space, partner.space, box, three_d)
            if found is None:
                ok = False
            else:
                space = found
        if ok:
            succeeded += 1
        elif failure == "empty":
            return None
        elif failure == "stop":
            return (extent, space) if succeeded else None
    return extent, space


def _check_box(box, space):
    if box is None:
        return
    check_option("box", box, BOXES)
    if space != "keep":
        msg = "box replaces space, so space must stay keep"
        raise ValueError(msg)


def _box_of(slot, partner, operation, three_d):
    """The box of the pair (slot, partner), False if the boxes do not combine"""
    if slot.space is None or partner.space is None:
        return slot.space
    found = combine_boxes(slot.space, partner.space, operation, three_d)
    return False if found is None else found


def _combined_space(own, others, mode):
    """The spatial extent of a result slot

    "keep" leaves own. "union" is the box around all extents. An overlay
    with and lies within all its inputs, so "intersection" is their common
    box; if they have none, the result is empty and own stays, since no
    box describes an empty map better.
    """
    if mode == "keep" or own is None or any(other is None for other in others):
        return own
    boxes = (own, *others)
    if mode == "union":
        return Space(
            max(box.north for box in boxes),
            min(box.south for box in boxes),
            max(box.east for box in boxes),
            min(box.west for box in boxes),
            max(box.top for box in boxes),
            min(box.bottom for box in boxes),
        )
    common = Space(
        min(box.north for box in boxes),
        max(box.south for box in boxes),
        min(box.east for box in boxes),
        max(box.west for box in boxes),
        min(box.top for box in boxes),
        max(box.bottom for box in boxes),
    )
    if (
        common.north < common.south
        or common.east < common.west
        or common.top < common.bottom
    ):
        return own
    return common


SELECT_EXTENTS = ("left", "right", "union", "intersection", "disjoint")


def select(
    left,
    relation,
    other,
    *,
    related=True,
    extent="left",
    failure="skip",
    order="sorted",
    unique=True,
    mixed_times="error",
):
    """Keep the slots l of left for which a slot x of other with "l R x"
    exists (related=True) or none exists (related=False)

    Content stays as it is. select(L, R, X) and select(L, R, X, related=False)
    are disjoint and together are L.

    :param extent: the time stamp of a kept slot: its own ("left"), or its own
        combined with the time stamps of its partners one after the other:
        the union, intersection or disjoint union, or "right", the time stamp
        of the last partner. Only for related=True
    :param failure: what a partner whose time stamp does not combine means
        for extent other than "left" and "right", see gather(); the default
        "skip" passes over such a partner, so the slot is always kept
    :param order: the order of the partners, which fixes the last one and the
        result of "stop", see related()
    :param unique: see related()
    :param mixed_times: "error" refuses series of absolute and relative time
        or of different units; "unrelated" relates nothing across them
    :raises ValueError: for an extent other than "left" with related=False
    """
    check_series(left, "left")
    check_relation(relation)
    check_series(other, "other")
    check_option("extent", extent, SELECT_EXTENTS)
    check_option("failure", failure, FAILURES)
    check_option("order", order, ORDERS)
    if extent != "left" and not related:
        msg = "A slot without partner has no time stamp to combine, so extent must be left"
        raise ValueError(msg)
    check_comparable(left, other, mixed_times, times_only=True)
    matches = related_indices(
        left.slots,
        relation,
        other.slots,
        dimension=DIMENSIONS[left.kind],
        order=order,
        unique=unique,
    )
    slots = []
    for slot, found in zip(left.slots, matches, strict=True):
        if bool(found) != related:
            continue
        if extent != "left":
            combined = _combine_steps(
                slot, [other.slots[index] for index in found], extent, failure=failure
            )
            if combined is None:
                continue
            if combined[0] != slot.extent:
                # The slot is no longer the registered map it was.
                slot = Slot(combined[0], slot.content, slot.space)
        slots.append(_in_time_order(slot))
    return replace(
        left, slots=tuple(slots), spatial=left.spatial or relation.spatial is not None
    )


def pairs(
    left,
    relation,
    other,
    *,
    extent="left",
    content=None,
    space="keep",
    order="sorted",
    unique=True,
    box=None,
    fold_all=False,
    last_only=False,
    mixed_times="error",
):
    """One slot per pair (l, x) with "l R x"

    :param extent: the time stamp of a slot: that of l ("left"), of x
        ("right"), or the union, intersection or disjoint union of both; a
        pair without intersection is left out
    :param content: function of the contents of l and x that returns the
        content of the slot; the default keeps the content of l
    :param space: the spatial extent of a slot: that of the slot that the
        time stamp comes from, x for extent="right" and l otherwise
        ("keep"), the box around l and x ("union"), or their common box
        ("intersection"), which keeps the extent of "keep" if there is none
    :param order: the order of the partners of l, see related(); it is the
        order of the slots of one l, and the order in which fold_all folds
    :param unique: False makes a pair for every written relation name that
        relates x to l, see related()
    :param box: "intersection" or "union" combines the box of l with the box
        of x for the slot of each pair, as an overlay of the classic algebra
        does (see combine_boxes()), also if space takes no part in the relation; it
        replaces space. The pairs end at the first partner of l without
        common box (only "intersection" has none); fold_all still folds all
        partners. Slots without box combine
    :param fold_all: every pair of l gets the content that folds all partners
        of l, content(content(l, x1), x2) and so on, instead of
        content(l, x); needs content
    :param last_only: keep only the last pair of each l, as the classic
        algebra does when the partners of a map share one result map
    :param mixed_times: "error" refuses series of absolute and relative time
        or of different units; "unrelated" relates nothing across them
    :raises ValueError: for fold_all without content
    """
    check_series(left, "left")
    check_relation(relation)
    check_series(other, "other")
    if content is not None:
        check_callable(content, "content")
    check_option("extent", extent, PAIR_EXTENTS)
    check_option("space", space, SPACES)
    check_option("order", order, ORDERS)
    _check_box(box, space)
    if fold_all and content is None:
        msg = "fold_all needs a content function to fold with"
        raise ValueError(msg)
    check_comparable(
        left, other, mixed_times, times_only=content is None or other.sort == "scalar"
    )
    matches = related_indices(
        left.slots,
        relation,
        other.slots,
        dimension=DIMENSIONS[left.kind],
        order=order,
        unique=unique,
    )
    slots = []
    for slot, found in zip(left.slots, matches, strict=True):
        partners = [other.slots[index] for index in found]
        folded = slot.content
        if fold_all:
            for partner in partners:
                folded = content(folded, partner.content)
        made = []
        for partner in partners:
            pair_space = None
            if box is not None:
                pair_space = _box_of(slot, partner, box, DIMENSIONS[left.kind] == "3D")
                if pair_space is False:
                    break
            if extent == "right":
                time, own, others = partner.extent, partner.space, [slot.space]
            else:
                time, own, others = (
                    _combine(slot, [partner], extent),
                    slot.space,
                    [partner.space],
                )
            if time is None:
                continue
            if fold_all:
                value = folded
            elif content is None:
                value = slot.content
            else:
                value = content(slot.content, partner.content)
            if box is None:
                pair_space = _combined_space(own, others, space)
            made.append(
                Slot(time, value, pair_space, _origin(value, time, slot, partner))
            )
        slots.extend(made[-1:] if last_only else made)
    sort = left.sort if content is None else _joined_sort(left, other)
    spatial = left.spatial or other.spatial or relation.spatial is not None
    return Series(tuple(slots), left.kind, sort, spatial, left.order)


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
        f"{index}: {describe_extent(times[index] if index < len(times) else None)} and "
        f"{describe_extent(others[index] if index < len(others) else None)}. Relate "
        "the series with gather() or pairs() first."
    )
    raise ValueError(msg)


def _describe_operand(operand):
    if isinstance(operand, Series):
        return f"{operand.kind} {operand.sort} values"
    if operand is None:
        return "null"
    if isinstance(operand, (int, float, bool)):
        return "a number"
    return "an expression"


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
    if first.kind == "vector" and sort == "field":
        # An overlay of a number has no meaning in v.overlay or v.patch, and
        # a scalar series is not a vector map, so none of them is an operand.
        for operand in operands:
            if not (
                isinstance(operand, Series)
                and operand.kind == "vector"
                and operand.sort == "field"
            ):
                msg = (
                    f"{name}() combines vector maps only, got "
                    f"{_describe_operand(operand)}"
                )
                raise ValueError(msg)
        if function not in VECTOR_FUNCTIONS:
            msg = (
                f"{function}() is not an operation on vector maps; they are "
                f"combined with {', '.join(sorted(VECTOR_FUNCTIONS))} and buffered "
                "with buffer()"
            )
            raise ValueError(msg)
    # With one series of maps the result is one map for each of its maps and
    # keeps its list order; with several the classic algebra builds a new
    # list in time order (probe 2026-10-16 with the classic algebra:
    # merge(N, A) + 1 numbers the maps of N first, merge(N, A) + merge(A, N)
    # numbers the results in time order).
    keep_rank = len(timed) == 1
    slots = []
    for index, slot in enumerate(first.slots):
        value = call(function, *(content_at(operand, index) for operand in operands))
        if sort == "scalar" and not isinstance(value, Const):
            msg = f"{function}() cannot be computed for scalar values"
            raise ScalarFunctionError(msg)
        partners = (operand.slots[index] for operand in timed)
        slots.append(
            Slot(
                slot.extent,
                value,
                slot.space,
                _origin(value, slot.extent, *partners),
                slot.rank if keep_rank else None,
            )
        )
    spatial = any(part.spatial for part in series)
    return Series(tuple(slots), first.kind, sort, spatial, first.order)


def apply(function, *operands):
    """Apply an operator or a function of the raster algebra slot by slot

    All series operands need the same time stamps in the same order. Numbers
    and maps without time stamp are used in every slot, None is null. There
    is no implicit alignment: relate series with gather() or pairs() first.
    The result is a field if any operand is a field; a scalar result is
    computed in Python. Vector maps take the overlays and, or, xor, not and
    disor only.

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


# r.mapcalc reads a map at a row and column offset, r3.mapcalc at a row,
# column and depth offset; vector maps have no cells.
_OFFSET_COUNTS = {"raster": 2, "raster3d": 3}


def cell_offset(series, *offset):
    """Read each map at a cell offset, as A[1,0] and A[1,0,-1] do

    The offset is (row, column) for raster maps and (row, column, depth) for
    3D raster maps. r.mapcalc and r3.mapcalc know offsets of maps only, so
    the slots must hold maps, not expressions.
    """
    check_series(series)
    for step in offset:
        check_int(step, "offset")
    expected = _OFFSET_COUNTS.get(series.kind)
    if expected is None:
        msg = f"{series.kind} maps have no cells to read at an offset"
        raise ValueError(msg)
    if len(offset) != expected:
        msg = f"A {series.kind} map takes {expected} cell offsets, got {len(offset)}"
        raise ValueError(msg)
    slots = []
    for slot in series.slots:
        if not isinstance(slot.content, MapRef):
            msg = "Only a map can be read at a cell offset, not an expression"
            raise ValueError(msg)
        content = MapRef(slot.content.ident, tuple(offset))
        slots.append(replace(slot, content=content, origin=None))
    return replace(series, slots=tuple(slots))


GATHER_EXTENTS = ("target", "union", "intersection", "disjoint")
MISSING = ("drop", "null", "keep")
EQUAL_TIMES = ("all", "pairwise")
NULLS = ("propagate", "skip")


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
    space="keep",
    order="sorted",
    unique=True,
    failure="empty",
    box=None,
    mixed_times="error",
):
    """For each slot t of target, reduce the slots x of other with "t R x"

    The result has at most one slot per target slot.

    :param reduce: how the related slots are combined: "sum", "prod", "min",
        "max", "mean", "count", "all", "any", "and", "or", "first", "last",
        fold(op), compare(symbol, join), series_method(method), or None to
        keep the content of the target. "all" and "any" give 0 or 1; "and" and
        "or" join the related contents with && and || as they are, so one
        related content stays unchanged. The other reducers leave the content
        of the target out, except fold(), which starts with it, and
        compare(), which compares it with each related content.
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
    :param space: the spatial extent of a result slot: that of the target
        ("keep"), the box around the target and its related slots
        ("union"), or their common box ("intersection"), which keeps the
        extent of the target if there is none
    :param order: the order of the related slots, see related(); a reducer
        sees them in this order, which counts for fold(), "first", "last"
        and the left-to-right nesting of the other reducers
    :param unique: False lets a slot count once for every written relation
        name that relates it, see related()
    :param failure: what a related slot whose time stamp (or box, see box)
        does not combine with that of the target means: "empty" leaves the
        target out, "stop" ends the combination there and keeps what the
        slots before it and the failing step itself set (the target is left
        out only if no step before succeeded), "skip" passes over the slot.
        The reducer sees all related slots whatever failure says
    :param box: "intersection" or "union" combines the box of the target with
        the box of each related slot in the same step as the time stamp, as an
        overlay of the classic algebra does (see _combine_steps() and combine_boxes()),
        also if space takes no part in the relation; the result box is the one
        so far, and it replaces space. Only "intersection" can fail. Slots
        without box combine
    :param mixed_times: "error" refuses series of absolute and relative time
        or of different units; "unrelated" relates nothing across them
    :raises ValueError: for missing="keep" with a reducer whose result has
        another sort than the target
    :raises ValueError: if equal_times="pairwise" cannot pair the maps of
        a time stamp
    """
    check_series(target, "target")
    check_relation(relation)
    check_series(other, "other")
    check_option("missing", missing, MISSING)
    check_option("extent", extent, GATHER_EXTENTS)
    check_option("equal_times", equal_times, EQUAL_TIMES)
    check_option("nulls", nulls, NULLS)
    check_option("space", space, SPACES)
    check_option("order", order, ORDERS)
    check_option("failure", failure, FAILURES)
    _check_box(box, space)
    reducers.check(reduce, nulls)
    check_comparable(
        target,
        other,
        mixed_times,
        times_only=reduce in (None, "count") or other.sort == "scalar",
    )
    sort = reducers.sort_of(reduce, target.sort, other.sort)
    if missing == "keep" and sort != target.sort:
        msg = (
            f'missing="keep" with reduce={reduce!r} would mix kept {target.sort} '
            f"maps with {sort} values"
        )
        raise ValueError(msg)
    matches = related_indices(
        target.slots,
        relation,
        other.slots,
        dimension=DIMENSIONS[target.kind],
        order=order,
        unique=unique,
    )
    if equal_times == "pairwise" and relation.spatial is None:
        matches = pair_equal_times(target.slots, matches, other.slots, order=order)
    slots = []
    for slot, found in zip(target.slots, matches, strict=True):
        partners = [other.slots[index] for index in found]
        if not partners:
            if missing == "null":
                slots.append(Slot(slot.extent, NULL, slot.space))
            elif missing == "keep":
                slots.append(_in_time_order(slot))
            continue
        combined = _combine_steps(
            slot,
            partners,
            extent,
            box=box,
            failure=failure,
            three_d=DIMENSIONS[target.kind] == "3D",
        )
        if combined is None:
            continue
        time, box_space = combined
        value = reducers.reduce(
            reduce, slot.content, [partner.content for partner in partners], nulls
        )
        extent_space = (
            box_space
            if box is not None
            else _combined_space(
                slot.space, [partner.space for partner in partners], space
            )
        )
        slots.append(Slot(time, value, extent_space, _origin(value, time, slot)))
    spatial = target.spatial or other.spatial or relation.spatial is not None
    return Series(tuple(slots), target.kind, sort, spatial, target.order)


def _grown(space, distance):
    """The box of space grown by distance on all six sides, as
    AbstractMapDataset.spatial_buffer() does

    A negative distance shrinks areas in v.buffer; the box stays, since it
    still contains the result.
    """
    if space is None or distance <= 0:
        return space
    return Space(
        space.north + distance,
        space.south - distance,
        space.east + distance,
        space.west - distance,
        space.top + distance,
        space.bottom - distance,
    )


def buffer(series, distance, *, features="area"):
    """Buffer the features of each vector map, as v.buffer does

    :param distance: the buffer distance in map units; v.buffer shrinks
        areas for a negative distance
    :param features: the feature type to buffer: "point", "line" or "area"
    :raises TypeError: for a distance that is no number
    :raises ValueError: for a series of other maps than vector maps, of
        scalar values, for a distance that is not finite, or for an unknown
        feature type
    """
    check_series(series)
    require(distance, (int, float), "distance", "a number")
    # isinstance() takes a bool for an int, but True is no distance.
    if isinstance(distance, bool):
        msg = "distance must be a number, got bool"
        raise TypeError(msg)
    # A distance that is not finite would give the maps extents that are not
    # finite either, such as nan for nan.
    if not math.isfinite(distance):
        msg = f"distance must be finite, got {distance}"
        raise ValueError(msg)
    check_option("features", features, tuple(BUFFERS))
    if series.kind != "vector" or series.sort != "field":
        msg = f"buffer() buffers vector maps, not {series.kind} {series.sort}s"
        raise ValueError(msg)
    function = BUFFERS[features]
    slots = tuple(
        Slot(
            slot.extent,
            call(function, slot.content, Const(float(distance))),
            _grown(slot.space, distance),
            rank=slot.rank,
        )
        for slot in series.slots
    )
    return replace(series, slots=slots)


def choose(condition, then, otherwise=None, *, mixed_times="error"):
    """Select whole slots by a scalar condition

    A slot of then is kept where the condition of its time stamp is true, a
    slot of otherwise where it is false, so then and otherwise may have
    different time stamps. A slot without a condition of its time stamp, or
    with a null one, is left out, as gather() with missing="drop" leaves it
    out. Several conditions of one time stamp are paired one to one, in
    order, with the slots of that time stamp, as equal_times="pairwise"
    builds them. A condition without time stamp decides for every slot of
    every branch, as a map without time stamp does in apply().

    :param mixed_times: "error" refuses a branch of another temporal type or
        unit than the condition; "unrelated" leaves out its slots, which no
        condition belongs to
    :raises TypeError: if the condition is not a scalar series
    :raises ValueError: if a time stamp has several conditions and another
        number of slots in a branch, if a timed condition meets a branch map
        without time stamp, if then and otherwise hold maps of different
        types, or if the series cannot be related
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
    if otherwise is not None and otherwise.kind != then.kind:
        msg = f"choose() cannot list {then.kind} and {otherwise.kind} maps together"
        raise ValueError(msg)
    for branch, wanted in zip(branches, (True, False), strict=False):
        # The condition gives numbers only, so its map type does not matter.
        check_comparable(condition, branch, mixed_times, times_only=True)
        slots.extend(_chosen(branch, values, wanted))
    spatial = any(part.spatial for part in (condition, *branches))
    if not condition.timeless:
        # Two series meet, as in apply(): the list is in time order.
        slots = [_in_time_order(slot) for slot in slots]
    return Series(tuple(slots), then.kind, _joined_sort(*branches), spatial, then.order)


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
                f"{counts[slot.extent]} maps of {describe_extent(slot.extent)}"
            )
            raise ValueError(msg)
        if not conditions:
            continue
        value = conditions[seen[slot.extent] if len(conditions) > 1 else 0]
        seen[slot.extent] += 1
        if value is not None and bool(value) is wanted:
            chosen.append(slot)
    return chosen


def where(condition, then, otherwise=0):
    """Choose per cell: if(condition, then, otherwise)

    Without otherwise a cell is 0 where the condition is false, as in
    r.mapcalc; pass None for null. A scalar
    condition is lifted to a constant field. condition, then and otherwise
    need equal time stamps; numbers are used in every slot.
    """
    check_series(condition, "condition")
    if condition.sort == "scalar":
        condition = lift(condition)
    return _apply("if", (condition, then, otherwise), "where")


def merge(*series, keep_first_repeats=False):
    """The union of series

    Identical slots are kept once with a warning, so that a later reduction
    does not count a map twice. Slots are identical if they agree in time
    stamp, content, space and origin. Different maps of equal time are all
    kept. The slots of the result are ranked in the order of the call, first
    the maps of the first series, see Series.listed().

    :param keep_first_repeats: keep identical slots of the first series, and
        drop only those of the later series that an earlier slot has already.
        Computed slots lose the map they came from, so two of them can look
        identical although they are different maps.
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
        check_comparable(first, part)
    seen = set()
    slots = []
    duplicates = 0
    for number, part in enumerate(series):
        # The list order of a part, so that a merge of merges lists the maps
        # of the inner one in the order it was written.
        for slot in part.listed():
            if slot in seen and not (number == 0 and keep_first_repeats):
                duplicates += 1
                continue
            seen.add(slot)
            slots.append(replace(slot, rank=len(slots)))
    if duplicates:
        warn(_("merge() dropped {count} duplicate map(s)").format(count=duplicates))
    spatial = any(part.spatial for part in series)
    return Series(tuple(slots), first.kind, first.sort, spatial, first.order)
