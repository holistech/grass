#!/usr/bin/env python3

############################################################################
#
# MODULE:	t.sample
# AUTHOR(S):	Soeren Gebbert
#
# PURPOSE:	Sample the input space time dataset(s) with a sample space time dataset and print the result to stdout
# SPDX-FileCopyrightText: 2011-2017 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Samples the input space time dataset(s) with a sample space time dataset and print the result to stdout.
# % keyword: temporal
# % keyword: sampling
# % keyword: time
# %end

# %option G_OPT_STDS_INPUTS
# %end

# %option G_OPT_STDS_INPUT
# % key: sample
# % description: Name of the sample space time dataset
# %end

# %option G_OPT_STDS_TYPE
# % key: intype
# % guisection: Required
# %end

# %option G_OPT_STDS_TYPE
# % key: samtype
# % guisection: Required
# % description: Type of the sample space time dataset
# %end

# %option G_OPT_T_SAMPLE
# % key: method
# % answer: during,overlap,contain,equal
# %end

# %option G_OPT_F_SEP
# % description: Field separator between output columns, default is tabular " | "
# % label: Do not use "," as this char is reserved to list several map ids in a sample granule
# %end

# %flag
# % key: c
# % description: Print the column names as first row
# %end

# %flag
# % key: s
# % description: Check for spatial topological overlap
# %end

import grass.script as gs

############################################################################


def _method_relations(methods):
    """The sampling method names expanded into core relation names

    Each name is read as "granule R input". The names come in the order in
    which AbstractSpaceTimeDataset.sample_by_dataset() tries its topology
    keys: the given names first, then the expansions of "start", "overlap"
    and "contain", each as far as not yet listed. The groups themselves are
    not relations and are dropped.

    sample_by_dataset() also appends "equals" for "start". It is left out
    here: the topology files equal maps under "EQUAL", so the "EQUALS" key
    of the classic tool never matches (measured 2026-10-14 in a temporary
    project: method=equal lists an equal map, method=start prints None for
    it). Dropping the name keeps that output byte for byte, and the core
    would reject it as an unknown relation.
    """
    names = list(methods)
    if "start" in names:
        for name in ("overlapped", "starts", "started", "finishes", "contains"):
            if name not in names:
                names.append(name)
    if "overlap" in names or "over" in names:
        for name in ("overlapped", "overlaps"):
            if name not in names:
                names.append(name)
    if "contain" in names and "contains" not in names:
        names.append("contains")
    ordered = []
    for name in names:
        if name in {"start", "overlap", "over", "contain"}:
            continue
        if name not in ordered:
            ordered.append(name)
    return ordered


def _with_gaps(series):
    """The sampler slots with a gap slot (origin None) between granules that
    have a hole between them

    get_registered_maps_as_objects_with_gaps() puts a map with id None between
    two consecutive maps if the later one is strictly after the earlier one.
    The sampler is an interval dataset (the tool refuses any other), so a gap
    runs from the end of the earlier granule to the start of the later one;
    touching granules give no gap. A gap has the spatial extent (0, 0, 0, 0)
    as in the classic function, which matters under -s: the gap then relates
    only to maps whose box touches the origin.
    """
    from grass.temporal.algebra.content import NULL
    from grass.temporal.algebra.series import Extent, Series, Slot, Space

    slots = list(series.slots)
    out = []
    for i, slot in enumerate(slots):
        out.append(slot)
        if i < len(slots) - 1:
            extent = slot.extent
            following = slots[i + 1].extent
            if extent.end < following.start:
                out.append(
                    Slot(
                        Extent(extent.end, following.start, extent.unit),
                        NULL,
                        Space(0, 0, 0, 0, 0, 0),
                        None,
                    )
                )
    return Series(tuple(out), series.kind, series.sort, series.spatial)


def _relation(name):
    """A temporal relation of one name, read as "granule R input"

    Without a spatial part: the core drops maps that share only a corner
    with the granule, which the classic -s keeps (see _boxes_intersect).
    """
    from grass.temporal.algebra.relations import Relation

    return Relation(frozenset({name}))


def _boxes_intersect(left, right):
    """True if the 2D extents touch or overlap, edges and corners included

    The classic -s searches an R-tree over west/east/south/north, which counts
    contact as intersection, whatever the bottom and top of 3D maps.
    """
    return (
        left.west <= right.east
        and right.west <= left.east
        and left.south <= right.north
        and right.south <= left.north
    )


def _related_per_granule(granules, names, inp, spatial=False):
    """Per granule, the input slots related through names

    The classic function collects the maps relation by relation in the order
    of names and drops duplicates. One merged relation would return a single
    start-time order, which differs whenever a granule relates maps through
    more than one relation, so the relations are kept apart.

    Within a relation the maps come in the order of the classic function,
    which lists them as the database returns them: by start time, and for an
    equal start time by map id (pinned by the characterization tests; the
    core orders such ties by end time, so the input is put in the classic
    order before related() numbers it).

    With spatial, a map must also touch the granule in 2D.
    """
    from grass.temporal.algebra.relations import related

    partners = sorted(inp.slots, key=lambda slot: (slot.extent.start, slot.origin))
    per_relation = [
        related(granules.slots, _relation(name), partners) for name in names
    ]
    rows = []
    for number, granule in enumerate(granules.slots):
        found = []
        for indices in per_relation:
            for index in indices[number]:
                if index in found:
                    continue
                if spatial and not _boxes_intersect(
                    granule.space, partners[index].space
                ):
                    continue
                found.append(index)
        rows.append([partners[index] for index in found])
    return rows


def _open_stds(stds_type, name, msgr):
    """The dataset object of a space time dataset, selected from the database"""
    import grass.temporal as tgis
    from grass.temporal.factory import dataset_factory

    ident = name if "@" in name else f"{name}@{tgis.get_current_mapset()}"
    stds = dataset_factory(stds_type, ident)
    if stds.is_in_db() is False:
        msgr.fatal(_("Dataset <%s> not found in temporal database") % ident)
    stds.select()
    return stds


def main():
    import grass.temporal as tgis
    from grass.temporal.algebra.sources import source
    from grass.temporal.datetime_math import time_delta_to_relative_time

    inputs = options["inputs"].split(",")
    sampler = options["sample"]
    samtype = options["samtype"]
    intype = options["intype"]
    separator = gs.separator(options["separator"])
    methods = options["method"].split(",")
    header = flags["c"]
    spatial = flags["s"]

    tgis.init()
    msgr = tgis.get_tgis_message_interface()

    # All datasets are checked before anything is read, the inputs first, as
    # the classic function did.
    input_stds = [_open_stds(intype, name, msgr) for name in inputs]
    sampler_stds = _open_stds(samtype, sampler, msgr)

    # The comma joins several map ids in one cell, so it cannot separate
    # columns; the classic function fell back to " | ".
    if separator is None or separator == "" or separator.find(",") >= 0:
        separator = " | "

    names = _method_relations(methods)
    granules = None
    columns = []
    for stds in input_stds:
        # An input that cannot be sampled is reported and left out of the
        # rows, but it stays in the header, as in the classic function.
        if stds.get_temporal_type() != sampler_stds.get_temporal_type():
            msgr.error(_("The space time datasets must be of the same temporal type"))
            continue
        if sampler_stds.get_map_time() != "interval":
            msgr.error(
                _("The temporal map type of the sample dataset must be interval")
            )
            continue
        # Only an interval sampler can be given gaps, so this waits for the
        # guards above.
        if granules is None:
            granules = _with_gaps(source(sampler_stds.get_id(), stds_type=samtype))
        if granules.slots:
            columns.append(
                _related_per_granule(
                    granules,
                    names,
                    source(stds.get_id(), stds_type=intype),
                    spatial,
                )
            )

    if not columns:
        return

    if header:
        head = [sampler_stds.get_id()]
        head += [stds.get_id() for stds in input_stds]
        head += ["start_time", "end_time", "interval_length", "distance_from_begin"]
        print(separator.join(head))

    first = granules.slots[0].extent.start
    for number, slot in enumerate(granules.slots):
        row = [str(slot.origin)]  # None -> "None" for a gap
        for column in columns:
            maps = column[number]
            row.append(",".join(m.content.ident for m in maps) if maps else "None")
        start, end = slot.extent.start, slot.extent.end
        length, distance = end - start, start - first
        if slot.extent.unit is None:
            length = time_delta_to_relative_time(length)
            distance = time_delta_to_relative_time(distance)
        row += [str(start), str(end), str(length), str(distance)]
        print(separator.join(row))


if __name__ == "__main__":
    options, flags = gs.parser()
    main()
