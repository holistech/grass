#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.rast.accdetect
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Detect accumulation pattern in temporally accumulated space time raster datasets created by t.rast.accumulate.
# SPDX-FileCopyrightText: 2013-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Detects accumulation patterns in temporally accumulated space time raster datasets created by t.rast.accumulate.
# % keyword: temporal
# % keyword: accumulation
# % keyword: raster
# % keyword: time
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option G_OPT_STRDS_INPUT
# % key: minimum
# % description: Input space time raster dataset that specifies the minimum values to detect the accumulation pattern
# % required: no
# %end

# %option G_OPT_STRDS_INPUT
# % key: maximum
# % description: Input space time raster dataset that specifies the maximum values to detect the accumulation pattern
# % required: no
# %end

# %option G_OPT_STRDS_OUTPUT
# % key: occurrence
# % description: The output space time raster dataset that stores the occurrence of the accumulation pattern using the provided data range
# % required: yes
# %end

# %option G_OPT_STRDS_OUTPUT
# % key: indicator
# % description: The output space time raster dataset that stores the indication of the start, intermediate and end of the specified data range
# % required: no
# %end

# %option
# % key: start
# % type: string
# % description: The temporal starting point to begin the accumulation, eg '2001-01-01'
# % required: yes
# % multiple: no
# %end

# %option
# % key: stop
# % type: string
# % description: The temporal date to stop the accumulation, eg '2009-01-01'
# % required: no
# % multiple: no
# %end

# %option
# % key: cycle
# % type: string
# % description: The temporal cycle to restart the accumulation, eg '12 months'
# % required: yes
# % multiple: no
# %end

# %option
# % key: offset
# % type: string
# % description: The temporal offset to the begin of the next cycle, eg '6 months'
# % required: no
# % multiple: no
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
# % key: range
# % type: double
# % key_desc: min,max
# % description: The minimum and maximum value of the occurrence of accumulated values, these values will be used if the min/max space time raster datasets are not specified
# % required: no
# % multiple: no
# %end

# %option
# % key: staend
# % type: integer
# % key_desc: start,intermediate,end
# % description: The user defined values that indicate start, intermediate and end status in the indicator output space time raster dataset
# % answer: 1,2,3
# % required: no
# % multiple: no
# %end

# %flag
# % key: n
# % description: Register empty maps in the output space time raster dataset, otherwise they will be deleted
# %end

# %flag
# % key: r
# % description: Reverse time direction in cyclic accumulation
# %end

import grass.script as gs

# lazy imports at the end of the file


def open_input(input_name, mapset, dbif):
    """Open the input dataset and read it from the database"""
    id = input_name if input_name.find("@") >= 0 else input_name + "@" + mapset
    input_strds = tgis.SpaceTimeRasterDataset(id)

    if not input_strds.is_in_db():
        dbif.close()
        gs.fatal(
            _("Space time %s dataset <%s> not found")
            % (input_strds.get_new_map_instance(None).get_type(), id)
        )

    input_strds.select(dbif)
    return input_strds


def open_occurrence(occurrence, minimum, maximum, range_, mapset, dbif):
    """Open the occurrence dataset, None without the option

    Without a range both threshold datasets are needed. Nothing is written;
    an occurrence dataset that exists ends the run unless overwrite is set.
    """
    occurrence_strds = None
    if occurrence:
        if (not minimum or not maximum) and not range_:
            dbif.close()
            gs.fatal(
                _(
                    "You need to set the range to compute the occurrence"
                    " space time raster dataset"
                )
            )

        if occurrence.find("@") >= 0:
            occurrence_id = occurrence
        else:
            occurrence_id = occurrence + "@" + mapset

        occurrence_strds = tgis.SpaceTimeRasterDataset(occurrence_id)
        if occurrence_strds.is_in_db(dbif) and not gs.overwrite():
            dbif.close()
            gs.fatal(
                _(
                    "Space time raster dataset <%s> is already in the "
                    "database, use overwrite flag to overwrite"
                )
                % occurrence_id
            )
    return occurrence_strds


def open_indicator(indicator, occurrence, staend, mapset, dbif):
    """Open the indicator dataset and read staend, both None without the option

    The indicator needs the occurrence and staend. Nothing is written; an
    indicator dataset that exists ends the run unless overwrite is set.
    Returns the dataset and the start, intermediate and end values.
    """
    if not indicator:
        return None, None

    if not occurrence:
        dbif.close()
        gs.fatal(
            _(
                "You need to set the occurrence to compute the indicator"
                " space time raster dataset"
            )
        )
    if not staend:
        dbif.close()
        gs.fatal(
            _(
                "You need to set the staend options to compute the indicator"
                " space time raster dataset"
            )
        )
    indicator_id = indicator if indicator.find("@") >= 0 else indicator + "@" + mapset

    indicator_strds = tgis.SpaceTimeRasterDataset(indicator_id)
    if indicator_strds.is_in_db(dbif) and not gs.overwrite():
        dbif.close()
        gs.fatal(
            _(
                "Space time raster dataset <%s> is already in the "
                "database, use overwrite flag to overwrite"
            )
            % indicator_id
        )
    staend = staend.split(",")
    return indicator_strds, (int(staend[0]), int(staend[1]), int(staend[2]))


def open_thresholds(input_strds, minimum, maximum, mapset, dbif):
    """Open the threshold datasets of the options minimum and maximum

    Returns both, None for an option that is not given. A dataset that does
    not exist or has another temporal type than the input ends the run.
    """
    minimum_strds = None
    if minimum:
        minimum_id = minimum if minimum.find("@") >= 0 else minimum + "@" + mapset

        minimum_strds = tgis.SpaceTimeRasterDataset(minimum_id)
        if not minimum_strds.is_in_db():
            dbif.close()
            gs.fatal(
                _("Space time raster dataset <%s> not found") % (minimum_strds.get_id())
            )

        # The type is read from the dataset, which select() loads.
        minimum_strds.select(dbif)
        if minimum_strds.get_temporal_type() != input_strds.get_temporal_type():
            dbif.close()
            gs.fatal(_("Temporal type of input strds and minimum strds must be equal"))

    maximum_strds = None
    if maximum:
        maximum_id = maximum if maximum.find("@") >= 0 else maximum + "@" + mapset

        maximum_strds = tgis.SpaceTimeRasterDataset(maximum_id)
        if not maximum_strds.is_in_db():
            dbif.close()
            gs.fatal(
                _("Space time raster dataset <%s> not found") % (maximum_strds.get_id())
            )

        # The type is read from the dataset, which select() loads.
        maximum_strds.select(dbif)
        if maximum_strds.get_temporal_type() != input_strds.get_temporal_type():
            dbif.close()
            gs.fatal(_("Temporal type of input strds and maximum strds must be equal"))
    return minimum_strds, maximum_strds


def check_lengths(input_strds, cycle, offset, dbif):
    """Refuse a cycle or offset that the temporal type cannot read"""
    if not tgis.check_granularity_string(cycle, input_strds.get_temporal_type()):
        dbif.close()
        gs.fatal(_("Invalid cycle"))

    if offset and not tgis.check_granularity_string(
        offset, input_strds.get_temporal_type()
    ):
        dbif.close()
        gs.fatal(_("Invalid offset"))


def read_start_and_stop(input_strds, start, stop, dbif):
    """Convert the options start and stop to the time of the input dataset

    Without stop, stop is None: the cycles run to the end of the data.
    """
    if input_strds.is_time_absolute():
        try:
            start = tgis.option_to_datetime(start, "start")
            stop = tgis.option_to_datetime(stop, "stop") if stop else None
        except ValueError as error:
            dbif.close()
            gs.fatal(str(error))
    else:
        try:
            start = int(start)
            stop = int(stop) if stop else None
        except ValueError:
            dbif.close()
            gs.fatal(_("The options start and stop must be integers"))
    return start, stop


def first_cycle(input_strds, start, cycle, offset, dbif):
    """The end of the first cycle and the lengths of time as the cycles use them

    Returns end, cycle and offset; in relative time the two lengths become
    integers. A cycle that does not move time forward ends the run, and so
    does an offset that moves the next cycle back to or before the start of
    the first.
    """
    if input_strds.is_time_absolute():
        end = tgis.increment_datetime_by_string(start, cycle)
    else:
        # Added to the start as text the cycle and the offset would fail.
        cycle = int(cycle)
        offset = int(offset) if offset else 0
        end = start + cycle

    # A cycle or an offset that does not move time forward would make the
    # loop of the cycles run forever.
    if end <= start:
        dbif.close()
        gs.fatal(_("The cycle must be longer than zero"))
    next_start, _next_end = tgis.next_cycle(
        start, 1, end, cycle, offset, input_strds.is_time_absolute()
    )
    if next_start <= start:
        dbif.close()
        gs.fatal(
            _(
                "The offset must not move the next cycle back to or before the start of this one"
            )
        )
    return end, cycle, offset


def compute_occurrence(
    occurrence_maps,
    input_strds,
    input_maps,
    start,
    base,
    count,
    *,
    tsuffix,
    where,
    reverse,
    range_,
    minimum_strds,
    maximum_strds,
    dbif,
):
    """Compute the occurrence maps of one cycle

    Stores the new maps in occurrence_maps by the id of their input map and
    returns the count for the next occurrence map.
    """
    if minimum_strds:
        input_maps_minimum = input_strds.get_registered_maps_as_objects(
            where=where, dbif=dbif
        )
        minimum_maps = minimum_strds.get_registered_maps_as_objects(dbif=dbif)
        minimum_topo = tgis.SpatioTemporalTopologyBuilder()
        minimum_topo.build(input_maps_minimum, minimum_maps)

    if maximum_strds:
        input_maps_maximum = input_strds.get_registered_maps_as_objects(
            where=where, dbif=dbif
        )
        maximum_maps = maximum_strds.get_registered_maps_as_objects(dbif=dbif)
        maximum_topo = tgis.SpatioTemporalTopologyBuilder()
        maximum_topo.build(input_maps_maximum, maximum_maps)

    # Aggregate
    num_maps = len(input_maps)
    for i in range(num_maps):
        # The lists of the threshold maps are in time order like input_maps,
        # so they take the same index as the map.
        index = num_maps - i - 1 if reverse else i
        map = input_maps[index]

        # Compute the days since start
        input_start, _input_end = map.get_temporal_extent_as_tuple()

        td = input_start - start
        days = tgis.time_delta_to_relative_time(td) if map.is_time_absolute() else td

        suffix = tgis.map_name_suffix(
            map, tsuffix, input_strds.get_granularity(), count
        )
        occurrence_map_name = f"{base}_{suffix}"

        try:
            occurrence_map = tgis.open_result_map(
                map, occurrence_map_name, overwrite=gs.overwrite(), dbif=dbif
            )
        except ValueError as error:
            gs.fatal(str(error))

        # Without a range every granule needs a map of the datasets.
        range_vals = range_.split(",") if range_ else [None, None]
        min = range_vals[0]
        max = range_vals[1]

        if minimum_strds:
            min = tgis.first_related_map_id(input_maps_minimum[index]) or min

        if maximum_strds:
            max = tgis.first_related_map_id(input_maps_maximum[index]) or max

        for bound, name in ((min, "minimum"), (max, "maximum")):
            if bound is None:
                gs.fatal(
                    _("No {} map found for <{}> and no range given").format(
                        name, map.get_id()
                    )
                )

        expression = "%s = if(%s > %s && %s < %s, %s, null())" % (
            occurrence_map_name,
            map.get_name(),
            min,
            map.get_name(),
            max,
            days,
        )
        gs.debug(expression)
        gs.mapcalc(expression, overwrite=True)

        # Store the new maps
        occurrence_maps[map.get_id()] = occurrence_map

        count += 1

    return count


def compute_indicator(
    indicator_maps,
    occurrence_maps,
    input_strds,
    input_maps,
    base,
    indi_count,
    tsuffix,
    reverse,
    staend,
    dbif,
):
    """Compute the indicator maps of one cycle from its occurrence maps

    staend holds the start, intermediate and end values. Stores the new maps
    in indicator_maps by the id of their input map and returns the count for
    the next indicator map.
    """
    indicator_start, indicator_mid, indicator_end = staend
    num_maps = len(input_maps)
    for i in range(num_maps):
        map = input_maps[num_maps - i - 1] if reverse else input_maps[i]

        suffix = tgis.map_name_suffix(
            map, tsuffix, input_strds.get_granularity(), indi_count
        )
        indicator_map_name = f"{base}_indicator_{suffix}"
        try:
            indicator_map = tgis.open_result_map(
                map, indicator_map_name, overwrite=gs.overwrite(), dbif=dbif
            )
        except ValueError as error:
            gs.fatal(str(error))

        curr_map = occurrence_maps[map.get_id()].get_name()

        # The maps computed before and after this one; with the flag r the
        # computation runs back in time.
        before, after = (map.next, map.prev) if reverse else (map.prev, map.next)
        if i == 0:
            prev_map = curr_map
            subexpr1 = "null()"
            subexpr3 = "%i" % (indicator_start)
        elif 0 < i < num_maps - 1:
            prev_map = occurrence_maps[before().get_id()].get_name()
            next_map = occurrence_maps[after().get_id()].get_name()
            # In case the previous map is null() set null() or the start
            # indicator
            subexpr1 = "if(isnull(%s), null(), %i)" % (curr_map, indicator_start)
            # In case the previous map was not null() if the current map is
            #   null() set null()
            # if the current map is not null() and the next map is not
            #   null() set
            # intermediate indicator, if the next map is null set the end
            #   indicator
            subexpr2 = "if(isnull(%s), %i, %i)" % (
                next_map,
                indicator_end,
                indicator_mid,
            )
            subexpr3 = "if(isnull(%s), null(), %s)" % (curr_map, subexpr2)
        else:
            prev_map = occurrence_maps[before().get_id()].get_name()
            subexpr1 = "if(isnull(%s), null(), %i)" % (curr_map, indicator_start)
            # The cycle ends here, so a run that goes on ends too.
            subexpr3 = "if(isnull(%s), null(), %i)" % (curr_map, indicator_end)

        expression = "%s = if(isnull(%s), %s, %s)" % (
            indicator_map_name,
            prev_map,
            subexpr1,
            subexpr3,
        )
        gs.debug(expression)
        gs.mapcalc(expression, overwrite=True)

        indicator_maps[map.get_id()] = indicator_map
        indi_count += 1

    return indi_count


def main():
    # Get the options
    input = options["input"]
    start = options["start"]
    stop = options["stop"]
    base = options["basename"]
    cycle = options["cycle"]
    offset = options["offset"]
    minimum = options["minimum"]
    maximum = options["maximum"]
    occurrence = options["occurrence"]
    range_ = options["range"]
    indicator = options["indicator"]
    staend = options["staend"]
    register_null = flags["n"]
    reverse = flags["r"]
    time_suffix = options["suffix"]

    try:
        tgis.check_suffix(time_suffix)
    except ValueError as error:
        gs.fatal(str(error))

    # Make sure the temporal database exists
    tgis.init()
    # We need a database interface
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    mapset = tgis.get_current_mapset()

    input_strds = open_input(input, mapset, dbif)
    occurrence_strds = open_occurrence(
        occurrence, minimum, maximum, range_, mapset, dbif
    )
    indicator_strds, staend = open_indicator(
        indicator, occurrence, staend, mapset, dbif
    )
    minimum_strds, maximum_strds = open_thresholds(
        input_strds, minimum, maximum, mapset, dbif
    )
    check_lengths(input_strds, cycle, offset, dbif)
    start, stop = read_start_and_stop(input_strds, start, stop, dbif)
    end, cycle, offset = first_cycle(input_strds, start, cycle, offset, dbif)

    # An empty dataset has no end for the cycles to run up to. The warning
    # and the stop without output are those of t.rast.contour, t.rast.to.vect
    # and t.rast.neighbors.
    if not input_strds.metadata.get_number_of_maps():
        dbif.close()
        gs.warning(_("Space time raster dataset <%s> is empty") % input_strds.get_id())
        return

    count = 1
    indi_count = 1
    occurrence_maps = {}
    indicator_maps = {}

    for cycle_start, cycle_end in tgis.dataset_cycles(
        input_strds, start, end, stop=stop, cycle=cycle, offset=offset, dbif=dbif
    ):
        where = "start_time >= '%s' AND start_time < '%s'" % (
            str(cycle_start),
            str(cycle_end),
        )
        input_maps = input_strds.get_registered_maps_as_objects(where=where, dbif=dbif)

        gs.debug(len(input_maps))

        input_topo = tgis.SpatioTemporalTopologyBuilder()
        input_topo.build(input_maps, input_maps)

        if len(input_maps) == 0:
            continue

        gs.message(_("Processing cycle %s - %s") % (str(cycle_start), str(cycle_end)))

        count = compute_occurrence(
            occurrence_maps,
            input_strds,
            input_maps,
            cycle_start,
            base,
            count,
            tsuffix=time_suffix,
            where=where,
            reverse=reverse,
            range_=range_,
            minimum_strds=minimum_strds,
            maximum_strds=maximum_strds,
            dbif=dbif,
        )

        # Indicator computation is based on the occurrence so we need to start it after
        # the occurrence cycle
        if indicator:
            indi_count = compute_indicator(
                indicator_maps,
                occurrence_maps,
                input_strds,
                input_maps,
                base,
                indi_count,
                time_suffix,
                reverse,
                staend,
                dbif,
            )

    empty_maps = tgis.register_in_new_stds(
        occurrence_maps.values(),
        occurrence_strds,
        input_strds,
        register_null=register_null,
        overwrite=gs.overwrite(),
        dbif=dbif,
    )

    if indicator:
        empty_maps += tgis.register_in_new_stds(
            indicator_maps.values(),
            indicator_strds,
            input_strds,
            register_null=register_null,
            overwrite=gs.overwrite(),
            dbif=dbif,
        )

    dbif.close()

    # Remove empty maps
    for map in empty_maps:
        gs.run_command(
            "g.remove", flags="f", type="raster", name=map.get_name(), quiet=True
        )


if __name__ == "__main__":
    options, flags = gs.parser()
    # lazy imports
    import grass.temporal as tgis

    main()
