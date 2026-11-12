"""Sampling of space time datasets with a common granularity

In the granularity mode of t.rast.algebra and t.rast3d.algebra (-g), every
dataset of an expression is replaced by its maps on a regular grid of
granules before the expression is computed. This module finds the datasets
of an expression and their common granularity, and rebuilds the sampling
from the core operations, so that both algebras sample a dataset alike; the
rest of the expression is translated as without the mode.

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
from grass.temporal.db import connection
from grass.temporal.open_stds import open_old_stds
from grass.temporal.temporal_granularity import (
    compute_common_absolute_time_granularity,
    compute_common_relative_time_granularity,
)

from . import ast
from .grammar import parse

# A granule takes its map from the first of these relations that relates
# any map, read as "granule R map". This is the order of
# AbstractSpaceTimeDataset.resample_maplist_by_granularity(), whose docstring
# names the relations from the side of the map. A map that overlaps the
# granule therefore wins over a map that lies within it.
GRANULE_RELATIONS = (equal, during, overlaps, overlapped, contains)

# The functions whose arguments name single maps; the mode samples only
# space time datasets.
_SINGLE_MAP_FUNCTIONS = ("map", "tmap")


def dataset_names(expression):
    """Return the names of the space time datasets that an expression reads

    The names come from the syntax tree of the core, so a text such as the
    "1 day" of tshift() and the result name left of "=" are no datasets. The
    arguments of map() and tmap() name single maps and are left out too. An
    index such as A[1] names the dataset A, and a call such as STRDS(A) or
    td(A) the dataset of its argument, also for a function that the
    translator does not know: the translation reports that one later.

    :param expression: the whole statement, such as "R = A + B"
    :return: the names as written, in the order of their first occurrence,
        each once
    :raises SyntaxError: for a statement that the parser of the core refuses
    """
    names = _names_in(parse(expression).expression)
    return list(dict.fromkeys(names))


def _names_in(node):
    """Yield the dataset names of a node of the syntax tree from left to right"""
    if isinstance(node, ast.Name):
        yield node.ident
    elif isinstance(node, ast.Index):
        yield node.name
    elif isinstance(node, ast.Negative):
        yield from _names_in(node.operand)
    elif isinstance(node, ast.Binary):
        yield from _names_in(node.left)
        yield from _names_in(node.right)
    elif isinstance(node, ast.Function) and node.name not in _SINGLE_MAP_FUNCTIONS:
        for argument in node.arguments:
            yield from _names_in(argument)


class GranularityModeError(Exception):
    """A refusal of the granularity mode; the text is the message for the user"""


def common_granularity(names, stds_type):
    """Return the common granularity of the datasets of the granularity mode

    Each dataset gives the granularity stored with its maps and its start
    time; the library computes the common granularity from them, and its
    result is returned as it is.

    :param names: the names of the datasets, see dataset_names(); not empty
    :param stds_type: the type of the datasets, such as "strds"
    :return: a text such as "1 day" for absolute time, a whole number of the
        unit for relative time
    :raises GranularityModeError: for a dataset without a valid temporal
        topology and for datasets of different temporal types
    :raises grass.exceptions.FatalError: for a dataset that does not exist
    """
    granularities = []
    start_times = []
    temporal_types = set()
    with connection() as dbif:
        for name in names:
            stds = open_old_stds(name, stds_type, dbif)
            if stds.check_temporal_topology() is False:
                raise GranularityModeError(
                    _(
                        "All input space time datasets must have a valid temporal "
                        "topology."
                    )
                )
            granularities.append(stds.get_granularity())
            start_times.append(stds.get_temporal_extent_as_tuple()[0])
            temporal_types.add(stds.get_temporal_type())
    if len(temporal_types) > 1:
        raise GranularityModeError(
            _("All input space time datasets must have the same temporal type.")
        )
    if "absolute" in temporal_types:
        return compute_common_absolute_time_granularity(granularities, start_times)
    return compute_common_relative_time_granularity(granularities)


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

    :param series: the Series of one dataset, in time order, whose maps are
        sampled
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
    # Granules have no spatial extent. The classic sampling gave each
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
