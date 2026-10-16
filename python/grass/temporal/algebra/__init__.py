"""A small core for the spatio-temporal algebra

A series is an immutable, time ordered sequence of planned or existing maps.
Each map is a slot with a time stamp and a content tree that says what the
map contains; building a series computes no maps. The operations are pure
functions on series; only materialize() computes maps and registers them,
and plan() shows what it would do. source(), source_map() and materialize()
need a GRASS session with an initialised temporal database (tgis.init()); the
other functions need none.

Example: the monthly sum of precipitation on days warmer than 5 degrees:

.. code-block:: python

    import grass.temporal.algebra as ta

    precip = ta.source("precipitation_daily")
    temp = ta.source("temperature_daily")
    months = ta.granules("2020-01-01", "2021-01-01", "1 month")

    warm = ta.where(temp > 5, precip, 0)
    monthly = ta.gather(months, ta.contains, warm, reduce="sum", nulls="skip")
    ta.materialize(monthly, "precip_warm_monthly", basename="pwm")

Relations read "l R x" for the slots l of the first and x of the second
series, as the selection L {:,R} X of t.rast.algebra does. Series are
related only by select(), pairs() and gather(); apply() and where() need
equal time stamps and never align series silently, and choose() judges each
slot by the condition of its own time stamp.

Vector maps are combined with the overlays of v.overlay and v.patch, written
a & b, a | b, a ^ b, a - b and a + b, and buffered with buffer().
"""

from .backends import MapcalcStyle
from .content import NULL, Call, Const, MapRef, SeriesAggregate, SeriesReduce
from .operations import (
    apply,
    buffer,
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
from .profile import CORE, Profile
from .reducers import fold, series_method
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
    "CORE",
    "NULL",
    "Call",
    "Const",
    "Extent",
    "MapRef",
    "MapcalcStyle",
    "ProcessChain",
    "Profile",
    "Relation",
    "Series",
    "SeriesAggregate",
    "SeriesReduce",
    "Slot",
    "Space",
    "apply",
    "buffer",
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
    "series_method",
    "source",
    "source_map",
    "started",
    "starts",
    "timevar",
    "where",
]
