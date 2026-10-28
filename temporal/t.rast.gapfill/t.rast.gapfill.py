#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.rast.gapfill
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Replace gaps in a space time raster dataset with interpolated raster maps.
# SPDX-FileCopyrightText: 2012-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Replaces gaps in a space time raster dataset with interpolated raster maps.
# % keyword: temporal
# % keyword: interpolation
# % keyword: raster
# % keyword: time
# % keyword: no-data filling
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option G_OPT_T_WHERE
# %end

# %option
# % key: basename
# % type: string
# % label: Basename of the new generated output maps
# % description: A numerical suffix separated by an underscore will be attached to create a unique identifier
# % required: yes
# % multiple: no
# %end

# %option G_OPT_T_SUFFIX
# %end

# %option
# % key: nprocs
# % type: integer
# % description: Number of interpolation processes to run in parallel
# % required: no
# % multiple: no
# % answer: 1
# %end

import copy
import sys

import grass.script as gs
from grass.exceptions import CalledModuleError

# lazy imports at the end of the file


def maps_with_gaps(sp, where, dbif):
    """Return the maps of sp that where selects, with a map without id per gap"""
    try:
        return sp.get_registered_maps_as_objects_with_gaps(where, dbif)
    except tgis.SQLStatementError as error:
        dbif.close()
        gs.fatal(_("Invalid where condition <{}>: {}").format(where, error))


def check_instants(sp, maps, dbif):
    """Refuse time instants alone and a gap after a time instant"""
    # Time instants alone leave nothing that a gap could be filled from; a
    # single instant is refused as well, although it has no gap.
    selected = [map_ for map_ in maps if map_.get_id() is not None]
    if selected and all(
        map_.get_temporal_extent_as_tuple()[1] is None for map_ in selected
    ):
        dbif.close()
        gs.fatal(
            _(
                "Space time raster dataset <{}> holds only time instants, "
                "only intervals can be filled"
            ).format(sp.get_id())
        )

    # The predecessor of a gap is a map that ends where the gap starts. A gap
    # after a time instant starts at the instant, and unless an interval ends
    # there too, it has none: check_neighbours() would not name the cause,
    # or, after an earlier gap, the topology takes that gap as the
    # predecessor and r.series.interp fails on its placeholder name after the
    # earlier gap was written (probe 23.10.2026 with the tool of 8d102f4f15:
    # interval days 0-1, point day 2, interval days 5-6). A gap before an
    # instant has the instant as its successor and is filled.
    ends = {map_.get_temporal_extent_as_tuple()[1] for map_ in selected}
    # A map without time can stand between the instant and the gap; the
    # message names the last real map with a start time, which is the cause.
    previous = None
    for map_ in maps:
        start = map_.get_temporal_extent_as_tuple()[0]
        if map_.get_id() is not None:
            if start is not None:
                previous = map_
            continue
        if start not in ends:
            dbif.close()
            gs.fatal(
                _(
                    "The gap after the time instant <{}> cannot be filled, "
                    "only gaps after an interval can be filled"
                ).format(previous.get_id())
            )


def name_gaps(sp, maps, base, tsuffix, mapset):
    """Give each gap of maps the id of a map in the current mapset

    Returns the gaps in the order of maps.
    """
    num = len(maps)
    gap_list = []
    count = 0
    for map_ in maps:
        if map_.get_id() is None:
            count += 1
            if sp.get_temporal_type() == "absolute" and tsuffix in {"gran", "time"}:
                id_ = f"{base}@{mapset}"
            else:
                map_name = tgis.create_numeric_suffix(base, num + count, tsuffix)
                id_ = f"{map_name}@{mapset}"
            map_.set_id(id_)

            gap_list.append(map_)
    return gap_list


def check_neighbours(gap_list):
    """Refuse a gap without predecessor or successor, warn of more than one

    The temporal topology of the maps must be built.
    """
    for map_ in gap_list:
        if not map_.get_precedes() or not map_.get_follows():
            gs.fatal(_("Unable to determine successor and predecessor of a gap."))

        if len(map_.get_precedes()) > 1:
            gs.warning(
                _("More than one successor of the gap found. Using the first found.")
            )

        if len(map_.get_follows()) > 1:
            gs.warning(
                _("More than one predecessor of the gap found. Using the first found.")
            )


def interpolation_maps(
    gap, predecessor, successor, sp, *, tsuffix, mapset, overwrite_flags, dbif
):
    """Return the maps that fill gap, one per granule of sp

    Each map gets its name and is checked against the maps of the mapset and
    of the temporal database; overwrite_flags gets for its id whether its
    entry in the temporal database is to be replaced.
    """
    gran = sp.get_granularity()
    _predecessor_end, start = predecessor.get_temporal_extent_as_tuple()
    end, _successor_end = successor.get_temporal_extent_as_tuple()

    # Now resample the gap
    map_matrix = tgis.AbstractSpaceTimeDataset.resample_maplist_by_granularity(
        (gap,), start, end, gran
    )

    new_maps = []
    for count, intp_list in enumerate(map_matrix, start=1):
        new_map = intp_list[0]
        suffix = tgis.map_name_suffix(new_map, tsuffix, sp.get_granularity(), count)
        new_id = f"{new_map.get_name()}_{suffix}@{mapset}"

        new_map.set_id(new_id)

        overwrite_flags[new_id] = False
        if new_map.map_exists() or new_map.is_in_db(dbif):
            if not gs.overwrite():
                gs.fatal(
                    _(
                        "Map with name <%s> already exists. "
                        "Please use another base name."
                    )
                    % (new_id)
                )
            elif new_map.is_in_db(dbif):
                overwrite_flags[new_id] = True

        new_maps.append(new_map)
    return new_maps


def queue_interpolation(
    gapfill_module, process_queue, predecessor, successor, new_maps, dbif
):
    """Hand r.series.interp for the maps of a gap to the queue

    The maps lie at equal distances between the predecessor and the
    successor of the gap.
    """
    map_names = []
    map_positions = []
    increment = 1.0 / (len(new_maps) + 1.0)
    position = increment
    for new_map in new_maps:
        map_names.append(new_map.get_name())
        map_positions.append(position)
        position += increment

    mod = copy.deepcopy(gapfill_module)
    mod(
        input=(predecessor.get_map_id(), successor.get_map_id()),
        datapos=(0, 1),
        output=map_names,
        samplingpos=map_positions,
    )
    sys.stderr.write(mod.get_bash() + "\n")
    try:
        process_queue.put(mod)
    except CalledModuleError as error:
        dbif.close()
        gs.fatal(_("Error running r.series.interp: {}").format(error))


def register_gap_maps(result_list, overwrite_flags, sp, dbif):
    """Insert the interpolated maps into the temporal database and into sp

    A map whose entry overwrite_flags marks is entered anew, with its time.
    """
    for map_ in result_list:
        id = map_.get_id()
        if overwrite_flags[id]:
            if map_.is_time_absolute():
                start, end = map_.get_absolute_time()
                if map_.is_in_db():
                    map_.delete(dbif)
                map_ = sp.get_new_map_instance(id)
                map_.set_absolute_time(start, end)
            else:
                start, end, unit = map_.get_relative_time()
                if map_.is_in_db():
                    map_.delete(dbif)
                map_ = sp.get_new_map_instance(id)
                map_.set_relative_time(start, end, unit)
        map_.load()
        map_.insert(dbif)
        sp.register_map(map_, dbif)


def main():
    # Get the options
    input = options["input"]
    base = options["basename"]
    where = options["where"]
    nprocs = options["nprocs"]
    tsuffix = options["suffix"]

    mapset = gs.gisenv()["MAPSET"]

    try:
        tgis.check_suffix(tsuffix)
    except ValueError as error:
        gs.fatal(str(error))

    # Make sure the temporal database exists
    tgis.init()

    # We need a database interface
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    sp = tgis.open_old_stds(input, "strds")

    maps = maps_with_gaps(sp, where, dbif)
    check_instants(sp, maps, dbif)

    # Configure the r.series.interp module
    gapfill_module = pymod.Module(
        "r.series.interp",
        overwrite=gs.overwrite(),
        quiet=True,
        run_=False,
        finish_=False,
    )

    process_queue = pymod.ParallelModuleQueue(int(nprocs))

    gap_list = name_gaps(sp, maps, base, tsuffix, mapset)
    if not gap_list:
        gs.message(_("No gaps found"))
        return

    # Build the temporal topology
    tb = tgis.SpatioTemporalTopologyBuilder()
    tb.build(maps)

    check_neighbours(gap_list)

    # Interpolate the maps using parallel processing; each gap is named and
    # checked right before its module is queued.
    result_list = []
    overwrite_flags = {}
    for gap in gap_list:
        # The neighbours are read before the gap is resampled: the resampling
        # builds a new topology for the gap, without them.
        predecessor = gap.get_follows()[0]
        successor = gap.get_precedes()[0]
        new_maps = interpolation_maps(
            gap,
            predecessor,
            successor,
            sp,
            tsuffix=tsuffix,
            mapset=mapset,
            overwrite_flags=overwrite_flags,
            dbif=dbif,
        )
        queue_interpolation(
            gapfill_module, process_queue, predecessor, successor, new_maps, dbif
        )
        result_list.extend(new_maps)

    # Wait for unfinished processes
    try:
        process_queue.wait()
    except CalledModuleError as error:
        dbif.close()
        gs.fatal(_("Error running r.series.interp: {}").format(error))

    register_gap_maps(result_list, overwrite_flags, sp, dbif)

    sp.update_from_registered_maps(dbif)
    sp.update_command_string(dbif=dbif)
    dbif.close()


if __name__ == "__main__":
    options, flags = gs.parser()
    # lazy imports
    import grass.pygrass.modules as pymod
    import grass.temporal as tgis

    main()
