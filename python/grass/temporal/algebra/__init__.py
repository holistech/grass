"""A small core for the spatio-temporal algebra

A series is an immutable, time ordered sequence of planned or existing maps.
Each map is a slot with a time stamp and a content tree that says what the
map contains; building a series computes no maps.
"""

from .content import NULL, Call, Const, MapRef, SeriesReduce
from .operations import (
    apply,
    cell_offset,
    choose,
    gather,
    lift,
    merge,
    pairs,
    select,
    where,
)
from .reducers import fold
from .relations import (
    Relation,
    contains,
    during,
    equal,
    finished,
    finishes,
    follows,
    inverse,
    overlapped,
    overlaps,
    precedes,
    relation,
    started,
    starts,
)
from .series import Extent, Series, Slot, Space

__all__ = [
    "NULL",
    "Call",
    "Const",
    "Extent",
    "MapRef",
    "Relation",
    "Series",
    "SeriesReduce",
    "Slot",
    "Space",
    "apply",
    "cell_offset",
    "choose",
    "contains",
    "during",
    "equal",
    "finished",
    "finishes",
    "fold",
    "follows",
    "gather",
    "inverse",
    "lift",
    "merge",
    "overlapped",
    "overlaps",
    "pairs",
    "precedes",
    "relation",
    "select",
    "started",
    "starts",
    "where",
]
