"""Sampling of space time datasets with a common granularity

In the granularity mode of t.rast.algebra and t.rast3d.algebra (-g), every
dataset of an expression is replaced by its maps on a regular grid of
granules before the expression is computed. This module rebuilds that
sampling from the core operations, so that both algebras sample a dataset
alike; the rest of the expression is translated as without the mode.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import dataclasses

from grass.temporal.algebra.operations import gather, select
from grass.temporal.algebra.relations import (
    contains,
    during,
    equal,
    overlapped,
    overlaps,
)
from grass.temporal.algebra.series import Series
from grass.temporal.algebra.time_functions import granules
from grass.temporal.datetime_math import increment_datetime_by_string

# A granule takes its map from the first of these relations that relates
# any map, read as "granule R map". This is the order of
# AbstractSpaceTimeDataset.resample_maplist_by_granularity(), whose docstring
# names the relations from the side of the map. A map that overlaps the
# granule therefore wins over a map that lies within it.
GRANULE_RELATIONS = (equal, during, overlaps, overlapped, contains)


def sample_by_granularity(series, granularity):
    """Return the maps of series on granules of the given granularity

    The granules start with the first map and follow each other while they
    start before the end of the last map; if the series has time instances,
    one more granule follows, so that an instance at the end is covered, as
    get_registered_maps_as_objects_by_granularity() does. Each granule takes
    the first map of the first relation of GRANULE_RELATIONS that relates a
    map, with the time stamp of the granule and the spatial extent of the
    map. A granule without such a map is left out.

    The series needs a valid temporal topology (no overlapping maps);
    setup_common_granularity() of the public parser classes checks it.

    :param granularity: a text such as "1 day" for absolute time, a whole
        number of the unit for relative time
    """
    if not series.slots:
        return series
    first, last = series.slots[0].extent, series.slots[-1].extent
    end = last.start if last.end is None else last.end
    if any(slot.extent.end is None for slot in series.slots):
        if first.unit is None:
            end = increment_datetime_by_string(end, granularity)
        else:
            end += granularity
    grid = granules(
        first.start,
        end,
        granularity,
        temporal_type=first.temporal_type,
        unit=first.unit,
        kind=series.kind,
    )
    # Granules have no spatial extent. The classic sampling gives each
    # sampled map the extent of its map, without which a spatial relation
    # (-s) would find nothing.
    spaces = {slot.content: slot.space for slot in series.slots}
    slots = []
    remaining = grid
    for relation in GRANULE_RELATIONS:
        slots.extend(gather(remaining, relation, series, reduce="first").slots)
        remaining = select(remaining, relation, series, related=False)
    return Series(
        tuple(dataclasses.replace(slot, space=spaces[slot.content]) for slot in slots),
        series.kind,
        series.sort,
        series.spatial,
    )
