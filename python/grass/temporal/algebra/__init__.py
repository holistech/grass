"""A small core for the spatio-temporal algebra

A series is an immutable, time ordered sequence of planned or existing maps.
The operations are pure functions on series; only materialize() computes
maps and registers them.
"""

from .content import NULL, Call, Const, MapRef, SeriesReduce
from .series import Extent, Series, Slot, Space

__all__ = [
    "NULL",
    "Call",
    "Const",
    "Extent",
    "MapRef",
    "Series",
    "SeriesReduce",
    "Slot",
    "Space",
]
