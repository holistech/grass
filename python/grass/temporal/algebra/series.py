"""Series of planned or existing maps, the values of the algebra core"""

import datetime
from dataclasses import dataclass

from .content import Content

KINDS = ("raster", "raster3d", "vector")
SORTS = ("field", "scalar")


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
    every slot of another series. origin is the identifier of the map that
    came into the series with its content and time stamp, registered or only
    stamped with r.timestamp (see source_map()), and that the slot still has
    unchanged; None for a computed slot.
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
