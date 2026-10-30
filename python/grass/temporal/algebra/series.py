"""Series of planned or existing maps, the values of the algebra core

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import datetime
from dataclasses import dataclass, field

from .content import Content

KINDS = ("raster", "raster3d", "vector")
SORTS = ("field", "scalar")
TIME_ORDERS = ("time", "start")


# The operators of vector maps are overlays (v.overlay, v.patch); scalar
# values of vector maps, such as td(), keep the arithmetic of numbers.
_VECTOR_OPERATORS = {"&&": "and", "||": "or", "xor": "xor", "+": "disor", "-": "not"}


@dataclass(frozen=True)
class Extent:
    """A time stamp: an interval, or an instant if end is None

    unit is the unit of relative time and None for absolute time.
    """

    start: datetime.datetime | int | float
    end: datetime.datetime | int | float | None = None
    unit: str | None = None

    @property
    def temporal_type(self):
        """Return "absolute" or "relative" by the unit"""
        return "absolute" if self.unit is None else "relative"

    def sort_key(self, order="time"):
        """Order by start, then by end; an instant sorts as an empty interval

        With order "start" the key is the start only, see Series.
        """
        if order == "start":
            return (self.start,)
        return (self.start, self.start if self.end is None else self.end)


@dataclass(frozen=True)
class Space:
    """A spatial extent"""

    north: float
    south: float
    east: float
    west: float
    top: float = 0.0
    bottom: float = 0.0


@dataclass(frozen=True)
class Slot:
    """A planned or existing map of a series

    extent is None for a map without time stamp, which can be combined with
    every slot of another series. origin is the identifier of the map that
    came into the series with its content and time stamp, registered or only
    stamped with r.timestamp (see source_map()), and that the slot still has
    unchanged; None for a computed slot.

    rank is the position of the slot in the list order of its series (see
    Series.listed()), None where the list follows the time order. It is
    not part of the identity of a slot: two slots that agree in everything
    else are the same map, wherever they stand in a list.
    """

    extent: Extent | None
    content: Content
    space: Space | None = None
    origin: str | None = None
    rank: int | None = field(default=None, compare=False)


def _slot_key(slot, order):
    return () if slot.extent is None else slot.extent.sort_key(order)


@dataclass(frozen=True, eq=False)
class Series:
    """An immutable, time ordered sequence of slots

    kind is the map type, sort is "field" (one value per cell) or "scalar"
    (one value per slot). spatial is True once a spatial relation related
    its slots, meaning that the regions of the maps matter and not only
    their time, as with the spatial flag of t.rast.algebra.

    The slots are sorted by time: by start, then by end for order "time",
    by start alone for order "start". Slots that tie keep the order in
    which they were given, which is the only tie-breaker they have. The
    classic algebra sorts by start alone and keeps the order of the
    database for equal starts, so a profile that follows it builds its
    series with order "start" (an operation keeps the order of its first
    operand).

    The list order is a second order beside the time order, for variants of
    the algebra whose lists are not sorted: merge() lists the maps of its
    first series, then those of the second, and so on, and the operations
    that give one map for each map of one series (numbers and functions of
    cells, buffers, time shifts) keep that list. listed() returns the slots
    in this order. Operations that relate or combine two series give a new
    list in time order. The list order is kept in the slots (Slot.rank)
    and not beside them, so it follows a slot through every operation that
    sorts or filters the slots again, and nested calls of merge() need no
    extra bookkeeping.

    The operators build new series (see apply()), and that includes ==, !=
    and the ordering operators: a == b is a series of comparisons, not a
    bool. Therefore bool(series) raises, so that "assert a == b" cannot pass
    for a comparison of contents, and a series is not hashable because it has
    no value-based equality to hash; compare the slots to compare contents.

    For vector maps, &, |, ^, + and - are the overlays and, or, xor, disor
    and not; ^ is xor() of r.mapcalc for raster maps.
    """

    slots: tuple[Slot, ...] = ()
    kind: str = "raster"
    sort: str = "field"
    spatial: bool = False
    order: str = "time"

    def __post_init__(self):
        if self.kind not in KINDS:
            msg = f"Unknown map type {self.kind!r}, use one of {', '.join(KINDS)}"
            raise ValueError(msg)
        if self.sort not in SORTS:
            msg = f"Unknown sort {self.sort!r}, use one of {', '.join(SORTS)}"
            raise ValueError(msg)
        if self.order not in TIME_ORDERS:
            msg = f"Unknown order {self.order!r}, use one of {', '.join(TIME_ORDERS)}"
            raise ValueError(msg)
        slots = tuple(self.slots)
        if len(slots) > 1 and any(slot.extent is None for slot in slots):
            msg = "A map without time stamp forms a series of its own"
            raise ValueError(msg)
        units = {slot.extent.unit for slot in slots if slot.extent is not None}
        if len(units) > 1:
            msg = "The slots of a series need one temporal type and unit"
            raise ValueError(msg)
        # sorted() is stable: slots of equal time keep their input order,
        # which is the only tie-breaker slots of equal time have.
        object.__setattr__(
            self, "slots", tuple(sorted(slots, key=lambda x: _slot_key(x, self.order)))
        )

    @property
    def temporal_type(self):
        """Return "absolute", "relative", or None for an empty or timeless series"""
        if not self.slots or self.slots[0].extent is None:
            return None
        return self.slots[0].extent.temporal_type

    @property
    def timeless(self):
        """True for a single map without time stamp"""
        return len(self.slots) == 1 and self.slots[0].extent is None

    def listed(self):
        """The slots in list order, as a tuple

        The list order is that of the ranks if every slot has one, else the
        time order of the slots.
        """
        if self.slots and all(slot.rank is not None for slot in self.slots):
            return tuple(sorted(self.slots, key=lambda slot: slot.rank))
        return self.slots

    def times(self):
        """The (start, end) of each slot

        :raises ValueError: for a series without time stamps
        """
        if self.timeless:
            msg = "A series without time stamps has no times"
            raise ValueError(msg)
        return [(slot.extent.start, slot.extent.end) for slot in self.slots]

    def __len__(self):
        return len(self.slots)

    def __iter__(self):
        return iter(self.slots)

    def __bool__(self):
        msg = "The truth value of a series is ambiguous; use len()"
        raise TypeError(msg)

    def _apply(self, function, *operands):
        # Imported here: operations imports this module.
        from .operations import apply

        if self.kind == "vector" and self.sort == "field":
            function = _VECTOR_OPERATORS.get(function, function)
        return apply(function, *operands)

    def __add__(self, other):
        return self._apply("+", self, other)

    def __radd__(self, other):
        return self._apply("+", other, self)

    def __sub__(self, other):
        return self._apply("-", self, other)

    def __rsub__(self, other):
        return self._apply("-", other, self)

    def __mul__(self, other):
        return self._apply("*", self, other)

    def __rmul__(self, other):
        return self._apply("*", other, self)

    def __truediv__(self, other):
        return self._apply("/", self, other)

    def __rtruediv__(self, other):
        return self._apply("/", other, self)

    def __mod__(self, other):
        return self._apply("%", self, other)

    def __rmod__(self, other):
        return self._apply("%", other, self)

    def __neg__(self):
        return self._apply("neg", self)

    def __eq__(self, other):
        return self._apply("==", self, other)

    def __ne__(self, other):
        return self._apply("!=", self, other)

    def __lt__(self, other):
        return self._apply("<", self, other)

    def __le__(self, other):
        return self._apply("<=", self, other)

    def __gt__(self, other):
        return self._apply(">", self, other)

    def __ge__(self, other):
        return self._apply(">=", self, other)

    def __and__(self, other):
        return self._apply("&&", self, other)

    def __rand__(self, other):
        return self._apply("&&", other, self)

    def __or__(self, other):
        return self._apply("||", self, other)

    def __ror__(self, other):
        return self._apply("||", other, self)

    def __xor__(self, other):
        return self._apply("xor", self, other)

    def __rxor__(self, other):
        return self._apply("xor", other, self)

    def __invert__(self):
        return self._apply("!", self)

    # Defining __eq__ would set this implicitly; stated because it is a decision.
    __hash__ = None
