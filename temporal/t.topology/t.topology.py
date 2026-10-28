#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.topology
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      List temporal topology of a space time dataset
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Lists temporal topology of a space time dataset.
# % keyword: temporal
# % keyword: topology
# % keyword: time
# %end

# %option G_OPT_STDS_INPUT
# %end

# %option G_OPT_STDS_TYPE
# % guidependency: input
# % guisection: Required
# %end

# %option G_OPT_T_WHERE
# %end

# %flag
# % key: m
# % description: Print temporal topological relationships and exit
# %end

# %flag
# % key: s
# % description: Print spatio-temporal topological relationships and exit
# %end
import grass.script as gs

# lazy imports at the end of the file

#: The summary line of each count of count_temporal_types(), by its key
TYPE_LINES = {
    "interval": " | Number of intervals: ....... %s",
    "point": " | Number of points: .......... %s",
    "invalid": " | Invalid time stamps: ....... %s",
}

#: The summary line of each count of count_temporal_relations(), by its key;
#: a key without a line, such as that of a spatial relation, is not printed.
RELATION_LINES = {
    "equal": " | Equal:...................... %s",
    "during": " | During: .................... %s",
    "contains": " | Contains: .................. %s",
    "overlaps": " | Overlaps: .................. %s",
    "overlapped": " | Overlapped: ................ %s",
    "starts": " | Starts: .................... %s",
    "finishes": " | Finishes: .................. %s",
    "started": " | Started: ................... %s",
    "finished": " | Finished: .................. %s",
    "follows": " | Follows: ................... %s",
    "precedes": " | Precedes: .................. %s",
}


def ordered_maps(sp, where):
    """Return the maps of sp that where selects, ordered by start time"""
    try:
        return sp.get_registered_maps_as_objects(
            where=where, order="start_time", dbif=None
        )
    except tgis.SQLStatementError as error:
        gs.fatal(_("Invalid where condition <{}>: {}").format(where, error))


def print_counts(counts, lines):
    """Print the line of each count in the order of counts, if it has one"""
    for key, value in counts.items():
        if key in lines:
            print(lines[key] % value)


def print_temporal_topology(sp, maps, where):
    """Print the validity, the counts of the time types, gaps and granularity"""
    print(
        " +-------------------- Temporal topology -------------------------------------+"  # noqa: E501
    )
    if where:
        print(" | Is subset of dataset: ...... True")
    else:
        print(" | Is subset of dataset: ...... False")

    if sp.check_temporal_topology(maps):
        print(" | Temporal topology is: ...... valid")
    else:
        print(" | Temporal topology is: ...... invalid")

    print_counts(sp.count_temporal_types(maps), TYPE_LINES)

    print(" | Number of gaps: ............ %i" % sp.count_gaps(maps))

    # No maps have no granularity. The function of relative time returns None
    # for them, the one of absolute time fails on the empty list.
    if not maps:
        gran = None
    elif sp.is_time_absolute():
        gran = tgis.compute_absolute_time_granularity(maps)
    else:
        gran = tgis.compute_relative_time_granularity(maps)
    print(" | Granularity: ............... %s" % str(gran))


def print_relations(sp, maps):
    """Print the number of each temporal relation between the maps"""
    print(
        " +-------------------- Topological relations ---------------------------------+"  # noqa: E501
    )
    relations = sp.count_temporal_relations(maps)
    # Without maps there are no counts at all, and no line.
    if relations:
        print_counts(relations, RELATION_LINES)
    print(
        "+----------------------------------------------------------------------------+"  # noqa: E501
    )


def main():
    # Get the options
    name = options["input"]
    type = options["type"]
    where = options["where"]
    temporal_relations = flags["m"]
    spatio_temporal_relations = flags["s"]

    # Make sure the temporal database exists
    tgis.init()

    sp = tgis.open_old_stds(name, type)
    maps = ordered_maps(sp, where)

    if temporal_relations or spatio_temporal_relations:
        spatial = None
        if spatio_temporal_relations:
            spatial = "2D" if sp.get_type() == "strds" else "3D"
        sp.print_spatio_temporal_relationships(maps=maps, spatial=spatial)
        return

    sp.base.print_info()
    print_temporal_topology(sp, maps, where)
    print_relations(sp, maps)


if __name__ == "__main__":
    options, flags = gs.parser()
    # lazy imports
    import grass.temporal as tgis

    main()
