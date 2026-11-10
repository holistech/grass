"""Aggregate a raster series onto a target series with the algebra core

The target is a regular grid of granules (t.rast.aggregate) or the time
stamps of a sampler dataset (t.rast.aggregate.ds). Both read the relation
from the target side, as the topology builder does, so neither inverts it.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import grass.temporal.algebra as ta
from grass.temporal.algebra.adapters import as_map
from grass.temporal.algebra.materialize import reject_input_names
from grass.temporal.datetime_math import (
    adjust_datetime_to_granularity,
    increment_datetime_by_string,
    map_name_suffix,
)
from grass.temporal.state import get_tgis_message_interface


def sampling_relation(names):
    """The relation from a granule to a map that the sampling names select

    names is the list of relation names of the sampling option. The relation
    reads from the granule's side, so "contains" selects the maps that a
    granule contains.
    """
    return ta.relation("|".join(names))


def aggregation_granules(input_series, granularity, *, absolute, unit):
    """A regular grid of granules that covers the maps of input_series

    The first granule starts at the start of the first map, rounded down to
    the granularity (absolute time only; a relative start is kept as it is).
    The grid ends behind the last map, so that the last granule is the one
    that holds it. The granules follow each other without gaps and count from
    that anchor.

    granularity is a text such as "1 month" for absolute time and a whole
    number, as text or integer, for relative time. unit is the relative time
    unit of the dataset, or None for absolute time. Raises ValueError for a
    granularity that is no valid one of the time type.
    """
    first = input_series.slots[0].extent
    last = input_series.slots[-1].extent
    start = first.start
    if absolute:
        # check_granularity_string() would also refuse "1 fortnight" and
        # "1.5 days" with a text of its own, and the messages of
        # adjust_datetime_to_granularity() for them stay as they were.
        # Only a granularity without a unit, which it fails on with an
        # IndexError, is refused here.
        if len(granularity.split()) != 2:
            msg = _("Invalid granularity <{}>").format(granularity)
            raise ValueError(msg)
        start = adjust_datetime_to_granularity(start, granularity)
    end = last.end
    if end is None:
        # The last map is an instant. granules() adds a granule while its
        # start is before end, so one time unit past the instant makes
        # the last granule the one that holds it and no later one. A
        # whole granularity would add a trailing granule that a longer
        # earlier map can still relate to.
        if absolute:
            end = increment_datetime_by_string(last.start, "1 second")
        else:
            end = last.start + 1

    if not absolute:
        # int() accepts neither "1 day" nor "1.5"; the caller's handler would
        # report its ValueError, whose text does not name the option.
        try:
            granularity = int(granularity)
        except ValueError:
            msg = _("Invalid granularity <{}>").format(granularity)
            raise ValueError(msg) from None

    return ta.granules(
        start,
        end,
        granularity,
        temporal_type="absolute" if absolute else "relative",
        unit=unit,
    )


def sampler_target(maps, unit):
    """A raster target series that carries only the sampler maps' time stamps

    gather() relates two series of one map type and returns a series of the
    target's type, so a vector or 3D raster sampler is reduced to raster
    slots with its time stamps. Only the times form the aggregation grid; the
    aggregated maps are always the raster input (checked 2026-10-14 with an
    stvds sampler).

    unit is None for absolute time, otherwise the relative time unit of the
    input dataset.
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
    # the maps of a sampler dataset may. Two target slots with the same extent
    # have the same related maps, so gather() keeps or drops both, and the
    # in-order match assigns them to the right numbers.
    position = []
    following = 0
    for slot in surviving.slots:
        while target.slots[following].extent != slot.extent:
            following += 1
        position.append(following + 1)
        following += 1
    names = []
    for slot, number in zip(surviving.slots, position, strict=True):
        suffix = map_name_suffix(
            as_map(slot.extent), time_suffix, granularity, number + int(offset)
        )
        names.append(f"{basename}_{suffix}")
    return names


def _report_granules(reduced):
    """Tell for each granule with a related map that it is aggregated

    The classic aggregation reported this per granule at verbose level. A
    lone related map counts as well: it is a one-argument aggregate.
    """
    msgr = get_tgis_message_interface()
    for slot in reduced.slots:
        content = slot.content
        if isinstance(content, ta.SeriesAggregate) and content.args:
            msgr.verbose(
                _("Aggregating {num} raster maps from {start} to {end}").format(
                    num=len(content.args), start=slot.extent.start, end=slot.extent.end
                )
            )


def aggregate_series(
    input_series,
    target,
    relation,
    method,
    *,
    sampling,
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

    relation is the relation from a granule to a map, see sampling_relation().
    sampling is the list of names it was built from; it only names the
    sampling in the warning. Returns the new space time dataset, or None,
    with a warning, if no granule has a related map. The caller sets title,
    description, semantic type and aggregation type with
    set_output_metadata().
    """
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
        # A warning, not an error: the tools end with code 0 and no dataset
        # (the behaviour before the warning existed), so a script that
        # aggregates possibly empty periods keeps running. The text names
        # what to look at: monthly granules and maps that start late in the
        # month never meet under the default sampling "contains".
        get_tgis_message_interface().warning(
            _(
                "No map is related to any granule of the granularity <{gran}> "
                "with the sampling <{sampling}>. No space time dataset <{out}> "
                "was created."
            ).format(gran=granularity, sampling=",".join(sampling), out=output)
        )
        return None
    _report_granules(reduced)
    names = _names(target, reduced, basename, granularity, time_suffix, offset)
    # materialize() sees only the maps of the reduced series; a granule that
    # was dropped or reduced away may still read a map with a result's name.
    reject_input_names(input_series, names)
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
    """Copy title, description and semantic type from the input and record the method.

    materialize() does not set the aggregation method."""
    temporal_type, semantic_type, title, description = source_stds.get_initial_values()
    dataset.set_initial_values(temporal_type, semantic_type, title, description)
    dataset.set_aggregation_type(method)
    dataset.metadata.update(dbif)
    dataset.base.update(dbif)
