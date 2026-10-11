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
from .materialize import ProcessChain, materialize, plan
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
from .sources import source, source_map
from .time_functions import granules, neighbour, retime, timevar

__all__ = [
    "NULL",
    "Call",
    "Const",
    "Extent",
    "MapRef",
    "ProcessChain",
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
    "granules",
    "inverse",
    "lift",
    "materialize",
    "merge",
    "neighbour",
    "overlapped",
    "overlaps",
    "pairs",
    "plan",
    "precedes",
    "relation",
    "retime",
    "select",
    "source",
    "source_map",
    "started",
    "starts",
    "timevar",
    "where",
]
