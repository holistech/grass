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
# % label: Field separator between output columns
# % description: A comma lists several map ids in a granule, so a separator with a comma is replaced by " | "
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


def labelled_id(stds):
    """The id of an opened dataset with the semantic label it was opened with

    get_id() drops the label, so source() would read all maps of the dataset.
    A dataset of an older release with a dot in its name was opened whole and
    has no label, so its name stays whole.
    """
    return f"{stds.get_name()}@{stds.get_mapset()}"


def main():
    global tgis
    # Imported here, not at module level: gs.parser() answers --help and
    # --interface-description before main() runs, and these need no temporal code.
    import grass.temporal as tgis
    from grass.temporal.algebra.sources import source
    from grass.temporal.datetime_math import time_delta_to_relative_time
    from grass.temporal.related_maps import (
        method_relations,
        related_per_granule,
        sampler_refusal,
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

    # All datasets are checked before anything is read, the inputs first, as
    # the classic function did.
    input_stds = [tgis.open_old_stds(name, intype) for name in inputs]
    sampler_stds = tgis.open_old_stds(sampler, samtype)

    # The comma joins several map ids in one cell, so it cannot separate
    # columns; the classic function fell back to " | ".
    if separator is None or separator == "" or separator.find(",") >= 0:
        separator = " | "

    names = method_relations(methods)
    granules = None
    columns = []
    for stds in input_stds:
        # A refusal ends the run with an error, so that a script sees that
        # the input was not sampled. A sampler without maps has no map time
        # to check; it has no granules and the run prints nothing.
        refusal = sampler_refusal(
            sampler_stds, stds, check_map_time=sampler_stds.get_map_time() is not None
        )
        if refusal is not None:
            gs.fatal(refusal)
        # Only an interval sampler can be given gaps, so this waits for the
        # guards above.
        if granules is None:
            granules = with_gaps(source(labelled_id(sampler_stds), stds_type=samtype))
        if granules.slots:
            columns.append(
                related_per_granule(
                    granules,
                    names,
                    source(labelled_id(stds), stds_type=intype),
                    spatial=spatial,
                )
            )

    if not columns:
        return

    if header:
        head = [labelled_id(sampler_stds)]
        head += [labelled_id(stds) for stds in input_stds]
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
