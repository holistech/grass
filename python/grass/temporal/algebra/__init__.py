"""The algebra core: an algebra of time series of maps

grass.temporal.algebra computes the expressions of t.rast.algebra,
t.rast3d.algebra, t.vect.algebra and t.select and the aggregations of
t.rast.aggregate and t.rast.aggregate.ds.

A series is an immutable, time ordered sequence of planned or existing maps.
Each map is a slot with a time stamp and a content tree that says what the
map contains; building a series computes no maps. The operations are pure
functions on series; only materialize() computes maps and registers them,
and plan() shows what it would do. source(), source_map() and materialize()
need a GRASS session with an initialised temporal database (tgis.init()).
plan() needs a session only when a result map has the name of a map that
the series reads, to look up the current mapset; the other functions need
none.

Example: the monthly sum of precipitation on days warmer than 5 degrees:

.. code-block:: python

    import grass.temporal.algebra as ta

    precip = ta.source("precipitation_daily")
    temp = ta.source("temperature_daily")
    months = ta.granules("2020-01-01", "2021-01-01", "1 month")

    warm = ta.where(temp > 5, precip, 0)
    monthly = ta.gather(months, ta.contains, warm, reduce="sum", nulls="skip")
    ta.materialize(monthly, "precip_warm_monthly", basename="pwm")

test_the_package_example_runs in
python/grass/temporal/tests/temporal_algebra_core_package_example_test.py
runs this code block on two small datasets.

Relations read "l R x" for the slots l of the first and x of the second
series, as the selection L {:,R} X of t.rast.algebra does. Series are
related only by select(), pairs() and gather(); apply() and where() need
equal time stamps and never align series silently, and choose() judges each
slot by the condition of its own time stamp.

Vector maps are combined with the overlays of v.overlay and v.patch, written
a & b, a | b, a ^ b, a - b and a + b, and buffered with buffer().

Terms
-----

The docstrings and comments of this package use one term for each thing:

the core
    grass.temporal.algebra, this package.
the classic algebra
    The language of the temporal algebra as the releases before GRASS 8.6
    and the publications define it: what an expression may say and what it
    means.
the public parser classes
    TemporalRasterAlgebraParser, TemporalRaster3DAlgebraParser and
    TemporalVectorAlgebraParser (parser/facade.py), which the tools and
    addons call.
the temporal reference
    One of l, r, u, i and d in a temporal operator such as {+,during,l}: it
    says which time stamp a result map takes.

Layers
------

From the bottom up:

1. Values: series.py has Extent (a time stamp), Space (a box), Slot and
   Series; content.py has the content trees MapRef, Const, Call,
   SeriesReduce and SeriesAggregate and the builders call() and chain(),
   which fold constants as r.mapcalc would compute them.
2. Link to grass.temporal: adapters.py builds throw-away map objects, so
   that the relations, the time arithmetic and the granularity of
   grass.temporal are used and not written a second time; maptypes.py names
   each map type for the temporal database and the tools; sources.py reads
   datasets and maps as series.
3. Relations: relations.py, Relation and related(), which ask the topology
   builder of grass.temporal.
4. Operations: operations.py (select, pairs, gather, apply, where, choose,
   merge, cell_offset, buffer, lift); reducers.py, how gather() combines
   related slots; time_functions.py (timevar, retime, neighbour, granules);
   _checks.py, the type checks at the entry of the operations.
5. Computing: backends.py turns a content tree into module calls
   (r.mapcalc, r3.mapcalc, r.series, g.copy, v.overlay, v.patch, v.buffer);
   in materialize.py, plan() returns these calls with the map names and the
   registration as a ProcessChain, and materialize() runs them and
   registers the maps.
6. Syntax, in parser/: lexer.py, grammar.py, ast.py and operators.py read
   the syntax of the core with PLY; translate.py turns the syntax tree into
   operations (Translator); granularity.py finds the datasets of the
   granularity mode (-g) and their common granularity and samples them;
   shared.py has checks of the translator. __init__.py has evaluate(), and
   facade.py the public parser classes.

A run of t.rast.algebra
-----------------------

The tool creates a TemporalRasterAlgebraParser. With -g,
setup_common_granularity() finds the datasets in the syntax tree and their
common granularity. parse() calls parser.evaluate().
The grammar (grammar.py) reads the expression into an ast.Statement; the
translator reads each dataset with source(), with -g sampled by
sample_by_granularity(), and builds the result series with the operations.
plan() gives the process chain that a dry run prints, and materialize()
computes and registers the maps.

Entry points
------------

What code outside the package uses, by caller:

- t.rast.algebra, t.rast3d.algebra, t.vect.algebra and addons: the public
  parser classes;
- t.select: parser.evaluate() and maptypes.KINDS_OF_STDS;
- grass.temporal.aggregation_core (t.rast.aggregate, t.rast.aggregate.ds):
  gather(), relation(), series_method(), materialize(),
  materialize.reject_input_names() and adapters.as_map(), with Series, Slot,
  Extent, NULL and SeriesAggregate; the two tools themselves call source()
  and granules();
- grass.temporal.mapcalc: sources.source() and time_functions.timevar(),
  with Series, Slot and Const;
- grass.temporal.sampling and t.sample: sources.source();
- grass.temporal.related_maps: relations.relation() and related(), with
  Series, Slot, Extent, Space and NULL.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

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
from .reducers import compare, fold, series_method
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
    "SeriesAggregate",
    "SeriesReduce",
    "Slot",
    "Space",
    "apply",
    "buffer",
    "cell_offset",
    "choose",
    "compare",
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
