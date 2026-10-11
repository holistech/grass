"""A small core for the spatio-temporal algebra

A series is an immutable, time ordered sequence of planned or existing maps.
Each map is a slot with a time stamp and a content tree that says what the
map contains; building a series computes no maps.
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
