"""Series of planned or existing maps, the values of the algebra core"""

import datetime
from dataclasses import dataclass

from .content import Content

KINDS = ("raster", "raster3d", "vector")
SORTS = ("field", "scalar")


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
        return "absolute" if self.unit is None else "relative"

    def sort_key(self):
        """Order by start, then by end; an instant sorts as an empty interval"""
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
    every slot of another series. origin is the identifier of the registered
    map whose content and time stamp the slot has unchanged, None for a
    computed slot.
    """

    extent: Extent | None
    content: Content
    space: Space | None = None
    origin: str | None = None


def _slot_key(slot):
    return () if slot.extent is None else slot.extent.sort_key()


@dataclass(frozen=True, eq=False)
class Series:
    """An immutable, time ordered sequence of slots

    kind is the map type, sort is "field" (one value per cell) or "scalar"
    (one value per slot). spatial is True once a spatial relation related
    its slots, meaning that the regions of the maps matter and not only
    their time, as with the spatial flag of t.rast.algebra.

    Equality is by identity, so comparing two series by mistake cannot pass
    for a comparison of contents; compare their slots to compare contents.
    """

    slots: tuple[Slot, ...] = ()
    kind: str = "raster"
    sort: str = "field"
    spatial: bool = False

    def __post_init__(self):
        if self.kind not in KINDS:
            msg = f"Unknown map type {self.kind!r}, use one of {', '.join(KINDS)}"
            raise ValueError(msg)
        if self.sort not in SORTS:
            msg = f"Unknown sort {self.sort!r}, use one of {', '.join(SORTS)}"
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
        object.__setattr__(self, "slots", tuple(sorted(slots, key=_slot_key)))

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
