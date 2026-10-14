"""Aggregate a raster series onto a target series with the algebra core

The target is a regular grid of granules (t.rast.aggregate) or the time
stamps of a sampler dataset (t.rast.aggregate.ds). Both read the relation
from the target side, as the topology builder does, so neither inverts it.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import grass.temporal.algebra as ta
from grass.temporal.algebra._adapters import as_map
from grass.temporal.core import get_tgis_message_interface
from grass.temporal.datetime_math import (
    create_numeric_suffix,
    create_suffix_from_datetime,
    create_time_suffix,
)


def sampler_target(maps, unit):
    """A raster target series that carries only the sampler maps' time stamps

    gather() relates two series of one map type and returns a series of the
    target's type, so a vector or 3D raster sampler is reduced to raster
    slots with its time stamps. Only the times form the aggregation grid; the
    aggregated maps are always the raster input (checked 2026-10-14 with an
    stvds sampler).
    """
    slots = []
    for map_ in maps:
        start, end = map_.get_temporal_extent_as_tuple()
        slots.append(ta.Slot(ta.Extent(start, end, unit), ta.NULL))
    return ta.Series(tuple(slots), "raster")


def _names(target, surviving, basename, granularity, time_suffix, offset):
    """The output names, reproducing the suffix rules of t.rast.aggregate

    surviving is the series that gather() returned, target the full grid of
    granules. The numeric suffix counts the granules from one, so that a
    dropped empty granule leaves a gap, as the classic count does: the number
    of a surviving slot is its position in target.
    """
    # gather() keeps the order of target and the extent of each target slot,
    # so the surviving slots are a subsequence of the target slots. Matching
    # them in order also tells apart target slots that share a start time, as
    # the maps of a sampler dataset may.
    position = []
    following = 0
    for slot in surviving.slots:
        while target.slots[following].extent != slot.extent:
            following += 1
        position.append(following + 1)
        following += 1
    absolute = target.temporal_type == "absolute"
    names = []
    for slot, number in zip(surviving.slots, position, strict=True):
        if absolute and time_suffix == "gran":
            suffix = create_suffix_from_datetime(slot.extent.start, granularity)
            names.append(f"{basename}_{suffix}")
        elif absolute and time_suffix == "time":
            names.append(f"{basename}_{create_time_suffix(as_map(slot.extent))}")
        else:
            count = number + int(offset)
            names.append(create_numeric_suffix(basename, count, time_suffix))
    return names


def _warn_file_limit(reduced, file_limit):
    """Warn for each granule that r.series reads with flag z

    The backend sets the flag silently; the classic tool told the user, and
    a user who set file_limit wants to know that the run is slower.
    """
    msgr = get_tgis_message_interface()
    for slot in reduced.slots:
        content = slot.content
        # A lone related map is copied with g.copy, and r.series never runs.
        if (
            isinstance(content, ta.SeriesAggregate)
            and len(content.args) > 1
            and len(content.args) > file_limit
        ):
            msgr.warning(
                _(
                    "The limit of open files (%i) was reached (%i). The module "
                    "r.series will be run with flag z, to avoid open files "
                    "limit exceeding."
                )
                % (file_limit, len(content.args))
            )


def aggregate_series(
    input_series,
    target,
    sampling,
    method,
    *,
    output,
    basename,
    granularity,
    time_suffix,
    offset,
    nprocs,
    file_limit,
    register_null,
    overwrite,
):
    """Aggregate input_series onto target and materialize the result

    Returns the new space time dataset, or None if no granule has a related
    map. The caller sets title, description, semantic type and aggregation
    type with set_output_metadata().
    """
    relation = ta.relation("|".join(sampling))
    # missing="drop": a granule without a related map produces no map, as the
    # classic tool skips it. nulls="skip": r.series passes over null cells.
    reduced = ta.gather(
        target,
        relation,
        input_series,
        reduce=ta.series_method(method, file_limit=int(file_limit)),
        missing="drop",
        nulls="skip",
    )
    if not reduced.slots:
        return None
    _warn_file_limit(reduced, int(file_limit))
    names = _names(target, reduced, basename, granularity, time_suffix, offset)
    return ta.materialize(
        reduced,
        output,
        basename=basename,
        names=names,
        register_null=register_null,
        nprocs=int(nprocs),
        overwrite=overwrite,
    )


def set_output_metadata(dataset, source_stds, method, dbif):
    """Copy title, description and semantic type from the input and record
    the aggregation method, which materialize() does not set"""
    temporal_type, semantic_type, title, description = source_stds.get_initial_values()
    dataset.set_initial_values(temporal_type, semantic_type, title, description)
    dataset.set_aggregation_type(method)
    dataset.metadata.update(dbif)
    dataset.base.update(dbif)
