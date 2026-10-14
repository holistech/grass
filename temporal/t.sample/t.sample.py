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


def _open_stds(stds_type, name, msgr):
    """The dataset object of a space time dataset, selected from the database"""
    import grass.temporal as tgis
    from grass.temporal.factory import dataset_factory

    ident = name if "@" in name else f"{name}@{tgis.get_current_mapset()}"
    stds = dataset_factory(stds_type, ident)
    if stds.is_in_db() is False:
        msgr.fatal(
            _("Dataset <{name}> not found in temporal database").format(name=ident)
        )
    stds.select()
    return stds


def main():
    import grass.temporal as tgis
    from grass.temporal.algebra.sources import source
    from grass.temporal.datetime_math import time_delta_to_relative_time
    from grass.temporal.related_maps import (
        method_relations,
        related_per_granule,
        sampler_refused,
        with_gaps,
    )

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

    names = method_relations(methods)
    granules = None
    columns = []
    for stds in input_stds:
        # An input that cannot be sampled is reported and left out of the
        # rows, but it stays in the header, as in the classic function.
        if sampler_refused(sampler_stds, stds, msgr):
            continue
        # Only an interval sampler can be given gaps, so this waits for the
        # guards above.
        if granules is None:
            granules = with_gaps(source(sampler_stds.get_id(), stds_type=samtype))
        if granules.slots:
            columns.append(
                related_per_granule(
                    granules,
                    names,
                    source(stds.get_id(), stds_type=intype),
                    spatial=spatial,
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
