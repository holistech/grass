#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.shift
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Temporally shift the maps of a space time dataset
# SPDX-FileCopyrightText: 2013-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Shifts temporally the maps of a space time dataset.
# % keyword: temporal
# % keyword: time management
# % keyword: shift
# % keyword: time
# %end

# %option G_OPT_STDS_INPUT
# % description: Name of an existing space time dataset
# %end

# %option G_OPT_STDS_TYPE
# % guidependency: input
# % guisection: Required
# %end

# %option
# % key: granularity
# % type: string
# % label: Shift granularity
# % description: Format absolute time: "x years, x months, x weeks, x days, x hours, x minutes, x seconds", relative time is of type integer
# % required: yes
# % multiple: no
# %end

import grass.script as gs

############################################################################


def shift_by_list(stds, gran, dbif):
    """Shift the maps of an absolute time dataset by a list of granularities

    This does what the shift() method of the dataset does for one
    granularity, which refuses a list, with the same dry run before any map
    is changed. The parts of the list are checked one by one, so that only
    this tool accepts a list. Each unit may appear once: the function that
    adds the shift keeps only the last number of a unit.

    :return: True if the maps were shifted, False if a part is invalid or
             there is nothing to shift
    """
    from grass.temporal.core import get_current_mapset
    from grass.temporal.datetime_math import increment_datetime_by_string
    from grass.temporal.temporal_granularity import check_granularity_string

    if stds.get_mapset() != get_current_mapset():
        gs.fatal(
            _(
                "Unable to shift dataset <{ds}> of type {type} in the temporal "
                "database. The mapset of the database does not match the current "
                "mapset"
            ).format(ds=stds.get_id(), type=stds.get_type())
        )

    parts = [part.strip() for part in gran.split(",")]
    if not all(check_granularity_string(part, "absolute") for part in parts):
        gs.error(_("Wrong granularity format: {}").format(gran))
        return False
    units = [part.split(" ")[1].removesuffix("s") for part in parts]
    if len(set(units)) != len(units):
        gs.error(
            _("Each unit may appear only once in the granularity: {}").format(gran)
        )
        return False

    maps = stds.get_registered_maps_as_objects(dbif=dbif)
    if maps is None:
        return False

    # All new times are computed before the first map changes, as in shift(),
    # so that a date behind the year 9999 leaves the dataset as it was.
    # Shifting by one part after the other with shift() would not: a later
    # part could fail after the earlier ones were written.
    date_list = []
    for map in maps:
        start, end = map.get_temporal_extent_as_tuple()
        try:
            start = increment_datetime_by_string(start, gran)
            if end is not None:
                end = increment_datetime_by_string(end, gran)
        except ValueError as error:
            # A shift behind the year 9999, which datetime cannot represent;
            # the caller names the dataset and the shift.
            raise ValueError(
                _("map <{map}>: {error}").format(map=map.get_id(), error=error)
            ) from error
        date_list.append((start, end))

    # The dataset offers no public method that writes a list of new times and
    # updates the datasets of the maps; shift() uses this one.
    stds._update_map_timestamps(maps, date_list, dbif)
    return True


def main():
    # lazy imports
    import grass.temporal as tgis

    name = options["input"]
    type = options["type"]
    gran = options["granularity"]

    # Make sure the temporal database exists
    tgis.init()

    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    stds = tgis.open_old_stds(name, type, dbif)
    # As in t.snap: a dataset without maps is reported and left as it is,
    # also in the history.
    if not stds.get_registered_maps_as_objects(dbif=dbif):
        dbif.close()
        gs.message(
            _("Space time dataset <{}> has no maps, nothing to shift").format(
                stds.get_id()
            )
        )
        return
    try:
        if stds.is_time_absolute() and "," in gran:
            check = shift_by_list(stds, gran, dbif)
        else:
            check = stds.shift(gran=gran, dbif=dbif)
    except ValueError as error:
        # shift() computes all new times before it changes a map, so the
        # dataset is as it was.
        dbif.close()
        gs.fatal(
            _("Unable to shift dataset <{ds}> by <{gran}>: {error}").format(
                ds=stds.get_id(), gran=gran, error=error
            )
        )

    if check is False:
        dbif.close()
        gs.fatal(
            _("Unable to temporally shift the space time %s dataset <%s>")
            % (stds.get_new_map_instance(None).get_type(), stds.get_id())
        )

    stds.update_command_string(dbif=dbif)
    dbif.close()


if __name__ == "__main__":
    options, flags = gs.parser()
    main()
