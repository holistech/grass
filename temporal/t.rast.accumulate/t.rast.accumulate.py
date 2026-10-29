#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.rast.accumulate
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Compute cyclic accumulations of a space time raster dataset
# SPDX-FileCopyrightText: 2013-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Computes cyclic accumulations of a space time raster dataset.
# % keyword: temporal
# % keyword: accumulation
# % keyword: raster
# % keyword: time
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option G_OPT_STRDS_OUTPUT
# %end


# %option G_OPT_STRDS_INPUT
# % key: lower
# % description: Input space time raster dataset that defines the lower threshold, values lower than this threshold are excluded from accumulation
# % required: no
# %end

# %option G_OPT_STRDS_INPUT
# % key: upper
# % description: Input space time raster dataset that defines the upper threshold, values higher than this threshold are excluded from accumulation
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
# % description: The temporal offset to the beginning of the next cycle, eg '6 months'
# % required: no
# % multiple: no
# %end

# %option
# % key: granularity
# % type: string
# % description: The granularity for accumulation '1 day'
# % answer: 1 day
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
# % key: limits
# % type: double
# % key_desc: lower,upper
# % description: Use these limits in case lower and/or upper input space time raster datasets are not defined or contain NULL values
# % required: yes
# % multiple: no
# %end

# %option
# % key: scale
# % type: double
# % description: Scale factor for input space time raster dataset
# % required: no
# % multiple: no
# %end

# %option
# % key: shift
# % type: double
# % description: Shift factor for input space time raster dataset
# % required: no
# % multiple: no
# %end

# %option
# % key: method
# % type: string
# % label: This method will be applied to compute the accumulative values from the input maps in a single granule
# % description: Growing Degree Days or Winkler indices; Mean: sum(input maps)/(number of input maps); Biologically Effective Degree Days; Huglin Heliothermal index
# % options: mean,gdd,bedd,huglin
# % answer: mean
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
from copy import copy

import grass.script as gs
from grass.exceptions import CalledModuleError

# lazy imports at the end of the file


def check_options(limits, time_suffix):
    """Check the options that need no database, return the limits as numbers"""
    # r.series.accumulate refuses limits that do not rise, so refuse them
    # before any map is made.
    limits_lower, limits_upper = (float(value) for value in limits.split(","))
    if limits_upper <= limits_lower:
        gs.fatal(_("The upper limit must be above the lower limit"))

    try:
        tgis.check_suffix(time_suffix)
    except ValueError as error:
        gs.fatal(str(error))
    return limits_lower, limits_upper


def open_datasets(input_name, output_name, mapset, dbif):
    """Open the input dataset and the output dataset

    Returns the input dataset read from the database and the output dataset.
    Nothing is written; an output that exists ends the run unless overwrite
    is set.
    """
    id = input_name if input_name.find("@") >= 0 else input_name + "@" + mapset
    input_strds = tgis.SpaceTimeRasterDataset(id)

    if not input_strds.is_in_db():
        dbif.close()
        gs.fatal(_("Space time raster dataset <%s> not found") % (id))

    input_strds.select(dbif)

    out_id = output_name if output_name.find("@") >= 0 else output_name + "@" + mapset

    output_strds = tgis.SpaceTimeRasterDataset(out_id)
    if output_strds.is_in_db(dbif) and not gs.overwrite():
        dbif.close()
        gs.fatal(
            _(
                "Space time raster dataset <%s> is already in the "
                "database, use overwrite flag to overwrite"
            )
            % out_id
        )
    return input_strds, output_strds


def check_lengths(input_strds, granularity, cycle, offset, dbif):
    """Refuse a granularity, cycle or offset that the temporal type cannot read"""
    if (
        tgis.check_granularity_string(granularity, input_strds.get_temporal_type())
        is False
    ):
        dbif.close()
        gs.fatal(_("Invalid granularity"))

    if tgis.check_granularity_string(cycle, input_strds.get_temporal_type()) is False:
        dbif.close()
        gs.fatal(_("Invalid cycle"))

    if offset and (
        tgis.check_granularity_string(offset, input_strds.get_temporal_type()) is False
    ):
        dbif.close()
        gs.fatal(_("Invalid offset"))


def open_thresholds(input_strds, lower, upper, mapset, dbif):
    """Open the threshold datasets of the options lower and upper

    Returns both, None for an option that is not given. A dataset that does
    not exist or has another temporal type than the input ends the run, and so
    does upper without lower.
    """
    lower_strds = None
    if lower:
        lower_id = lower if lower.find("@") >= 0 else lower + "@" + mapset

        lower_strds = tgis.SpaceTimeRasterDataset(lower_id)
        if not lower_strds.is_in_db():
            dbif.close()
            gs.fatal(
                _("Space time raster dataset <%s> not found") % (lower_strds.get_id())
            )

        # The type is read from the dataset, which select() loads.
        lower_strds.select(dbif)
        if lower_strds.get_temporal_type() != input_strds.get_temporal_type():
            dbif.close()
            gs.fatal(_("Temporal type of input strds and lower strds must be equal"))

    upper_strds = None
    if upper:
        if not lower:
            dbif.close()
            gs.fatal(
                _("The upper option works only in conjunction with the lower option")
            )

        upper_id = upper if upper.find("@") >= 0 else upper + "@" + mapset
        upper_strds = tgis.SpaceTimeRasterDataset(upper_id)
        if not upper_strds.is_in_db():
            dbif.close()
            gs.fatal(
                _("Space time raster dataset <%s> not found") % (upper_strds.get_id())
            )

        # The type is read from the dataset, which select() loads.
        upper_strds.select(dbif)
        if upper_strds.get_temporal_type() != input_strds.get_temporal_type():
            dbif.close()
            gs.fatal(_("Temporal type of input strds and upper strds must be equal"))
    return lower_strds, upper_strds


def read_start_and_stop(input_strds, start, stop, granularity, dbif):
    """Convert the options start and stop to the time of the input dataset

    An absolute start moves to the beginning of its granule, with a warning.
    Without stop, stop is None: the cycles run to the end of the data.
    """
    if input_strds.is_time_absolute():
        try:
            start = tgis.option_to_datetime(start, "start")
            stop = tgis.option_to_datetime(stop, "stop") if stop else None
        except ValueError as error:
            dbif.close()
            gs.fatal(str(error))
        given_start = start
        start = tgis.adjust_datetime_to_granularity(start, granularity)
        if start != given_start:
            # The cycles count from the start, so a start in the middle of a
            # month or week would give other cycles than t.rast.accdetect,
            # which does not move it, gives for the same start.
            gs.warning(
                _(
                    "The start <{given}> is moved to <{used}>, the beginning "
                    "of the granularity <{granularity}>."
                ).format(given=given_start, used=start, granularity=granularity)
            )
    else:
        try:
            start = int(start)
            stop = int(stop) if stop else None
        except ValueError:
            dbif.close()
            gs.fatal(_("The options start and stop must be integers"))
    return start, stop


def first_cycle(input_strds, start, cycle, granularity, offset, dbif):
    """The end of the first cycle and the lengths of time as the cycles use them

    Returns end, cycle, granularity and offset; in relative time the three
    lengths become integers. A cycle or granule that does not move time
    forward ends the run, and so does an offset that moves the next cycle back
    to or before the start of the first.
    """
    if input_strds.is_time_absolute():
        end = tgis.increment_datetime_by_string(start, cycle)
    else:
        # The lengths of time were checked as integers of the unit of the
        # dataset; added to the start as text they would fail.
        cycle = int(cycle)
        granularity = int(granularity)
        offset = int(offset) if offset else 0
        end = start + cycle

    # A cycle, a granule or an offset that does not move time forward would
    # make the loops of the cycles and the granules run forever.
    if input_strds.is_time_absolute():
        granule_end = tgis.increment_datetime_by_string(start, granularity)
    else:
        granule_end = start + granularity
    if end <= start:
        dbif.close()
        gs.fatal(_("The cycle must be longer than zero"))
    if granule_end <= start:
        dbif.close()
        gs.fatal(_("The granularity must be longer than zero"))
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
    return end, cycle, granularity, offset


def granules(input_strds, start, end, granularity, count):
    """Maps without data, one for each granule of the cycle, in time order

    Returns three lists of copies of the same maps: one to relate the granules
    to the input maps, one each to relate them to the lower and the upper
    thresholds.
    """
    gran_list = []
    gran_list_low = []
    gran_list_up = []
    gran_start = start
    granule = 0
    while gran_start < end:
        map = input_strds.get_new_map_instance("%i@%i" % (count, count))
        granule += 1
        if input_strds.is_time_absolute():
            # Counted from the start of the cycle, as the cycles are from
            # the origin, so that a cut at the end of a short month does
            # not carry over into the later granules.
            gran_end = tgis.datetime_after_steps(start, granularity, granule)
            map.set_absolute_time(gran_start, gran_end)
        else:
            gran_end = gran_start + granularity
            map.set_relative_time(
                gran_start, gran_end, input_strds.get_relative_time_unit()
            )
        gran_start = gran_end
        gran_list.append(copy(map))
        gran_list_low.append(copy(map))
        gran_list_up.append(copy(map))
    return gran_list, gran_list_low, gran_list_up


def relate_granules(gran_lists, input_maps, lower_strds, upper_strds, dbif):
    """Build the topology of the granules with the input and threshold maps"""
    gran_list, gran_list_low, gran_list_up = gran_lists
    gran_topo = tgis.SpatioTemporalTopologyBuilder()
    gran_topo.build(gran_list, input_maps)

    if lower_strds is not None:
        lower_maps = lower_strds.get_registered_maps_as_objects(dbif=dbif)
        gran_lower_topo = tgis.SpatioTemporalTopologyBuilder()
        gran_lower_topo.build(gran_list_low, lower_maps)

    if upper_strds is not None:
        upper_maps = upper_strds.get_registered_maps_as_objects(dbif=dbif)
        gran_upper_topo = tgis.SpatioTemporalTopologyBuilder()
        gran_upper_topo.build(gran_list_up, upper_maps)


def granule_input_maps(granule):
    """The input maps of the granule, by the first relation that has any"""
    input_maps = []
    if granule.get_equal():
        input_maps += granule.get_equal()
    elif granule.get_contains():
        input_maps += granule.get_contains()
    elif granule.get_overlaps():
        input_maps += granule.get_overlaps()
    elif granule.get_overlapped():
        input_maps += granule.get_overlapped()
    elif granule.get_during():
        input_maps += granule.get_during()
    return input_maps


def run_accumulation(
    input_maps,
    output_map_name,
    old_map_name,
    lower_map_name,
    upper_map_name,
    settings,
    dbif,
):
    """Run r.series.accumulate for one granule

    settings holds the options that are the same for every granule: limits,
    shift, scale and method. A failing run ends the tool.
    """
    input_map_names = [input_map.get_id() for input_map in input_maps]

    # Set up the module
    accmod = Module(
        "r.series.accumulate",
        input=input_map_names,
        output=output_map_name,
        run_=False,
    )

    if old_map_name:
        accmod.inputs["basemap"].value = old_map_name
    if lower_map_name:
        accmod.inputs["lower"].value = lower_map_name
    if upper_map_name:
        accmod.inputs["upper"].value = upper_map_name

    accmod.inputs["limits"].value = settings["limits"]

    if settings["shift"]:
        accmod.inputs["shift"].value = float(settings["shift"])

    if settings["scale"]:
        accmod.inputs["scale"].value = float(settings["scale"])

    if settings["method"]:
        accmod.inputs["method"].value = settings["method"]

    try:
        accmod.run()
    except CalledModuleError:
        dbif.close()
        gs.fatal(_("Error running r.series.accumulate"))


def accumulate_granules(
    input_strds,
    gran_lists,
    count,
    *,
    reverse,
    base,
    time_suffix,
    lower_strds,
    upper_strds,
    settings,
    dbif,
):
    """Accumulate the granules of one cycle, each on the result of the one before

    gran_lists are the lists of granules() after relate_granules(). Returns
    the new maps in the order of the computation, the first numbered count. A
    granule without input maps gets no map.
    """
    gran_list, gran_list_low, gran_list_up = gran_lists
    new_maps = []
    old_map_name = None
    num_maps = len(gran_list)
    for i in range(num_maps):
        # The threshold lists are in time order like gran_list, so they
        # take the same index as the granule.
        index = num_maps - i - 1 if reverse else i
        granule = gran_list[index]
        input_maps = granule_input_maps(granule)
        if len(input_maps) == 0:
            continue

        suffix = tgis.map_name_suffix(
            granule, time_suffix, input_strds.get_granularity(), count
        )
        output_map_name = f"{base}_{suffix}"
        try:
            output_map = tgis.open_result_map(
                granule, output_map_name, overwrite=gs.overwrite(), dbif=dbif
            )
        except ValueError as error:
            gs.fatal(str(error))
        lower_map_name = (
            tgis.first_related_map_id(gran_list_low[index])
            if lower_strds is not None
            else None
        )
        upper_map_name = (
            tgis.first_related_map_id(gran_list_up[index])
            if upper_strds is not None
            else None
        )
        run_accumulation(
            input_maps,
            output_map_name,
            old_map_name,
            lower_map_name,
            upper_map_name,
            settings,
            dbif,
        )

        new_maps.append(output_map)
        old_map_name = output_map_name
        count += 1
    return new_maps


def main():
    # Get the options
    input = options["input"]
    output = options["output"]
    start = options["start"]
    stop = options["stop"]
    base = options["basename"]
    cycle = options["cycle"]
    lower = options["lower"]
    upper = options["upper"]
    offset = options["offset"]
    limits = options["limits"]
    shift = options["shift"]
    scale = options["scale"]
    method = options["method"]
    granularity = options["granularity"]
    register_null = flags["n"]
    reverse = flags["r"]
    time_suffix = options["suffix"]

    limits = check_options(limits, time_suffix)

    # Make sure the temporal database exists
    tgis.init()

    # We need a database interface
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    mapset = tgis.get_current_mapset()

    input_strds, output_strds = open_datasets(input, output, mapset, dbif)
    check_lengths(input_strds, granularity, cycle, offset, dbif)
    lower_strds, upper_strds = open_thresholds(input_strds, lower, upper, mapset, dbif)
    start, stop = read_start_and_stop(input_strds, start, stop, granularity, dbif)
    end, cycle, granularity, offset = first_cycle(
        input_strds, start, cycle, granularity, offset, dbif
    )

    # An empty dataset has no end for the cycles to run up to. The warning
    # and the stop without output are those of t.rast.contour, t.rast.to.vect
    # and t.rast.neighbors.
    if not input_strds.metadata.get_number_of_maps():
        dbif.close()
        gs.warning(_("Space time raster dataset <%s> is empty") % input_strds.get_id())
        return

    settings = {"limits": limits, "shift": shift, "scale": scale, "method": method}
    count = 1
    output_maps = []
    for cycle_start, cycle_end in tgis.dataset_cycles(
        input_strds, start, end, stop=stop, cycle=cycle, offset=offset, dbif=dbif
    ):
        where = "start_time >= '%s' AND start_time < '%s'" % (
            str(cycle_start),
            str(cycle_end),
        )
        input_maps = input_strds.get_registered_maps_as_objects(where=where, dbif=dbif)

        gs.message(_("Processing cycle %s - %s") % (str(cycle_start), str(cycle_end)))

        if len(input_maps) == 0:
            continue

        gran_lists = granules(input_strds, cycle_start, cycle_end, granularity, count)
        relate_granules(gran_lists, input_maps, lower_strds, upper_strds, dbif)
        cycle_maps = accumulate_granules(
            input_strds,
            gran_lists,
            count,
            reverse=reverse,
            base=base,
            time_suffix=time_suffix,
            lower_strds=lower_strds,
            upper_strds=upper_strds,
            settings=settings,
            dbif=dbif,
        )
        output_maps += cycle_maps
        count += len(cycle_maps)

    # When no map is to be registered, a warning and no output dataset; an
    # output dataset that exists is not replaced, also with overwrite, and
    # the computed maps are removed as empty maps. t.rast.aggregate does so
    # when no granule has a map, as here when no cycle computes one. A result
    # of only empty maps without -n is treated the same by the decision of
    # 29.10.2026; t.rast.aggregate makes a dataset without maps there.
    if tgis.maps_to_register(output_maps, register_null=register_null):
        empty_maps = tgis.register_in_new_stds(
            output_maps,
            output_strds,
            input_strds,
            register_null=register_null,
            overwrite=gs.overwrite(),
            dbif=dbif,
        )
    else:
        gs.warning(
            _(
                "No map with values was computed in any cycle. No space time "
                "dataset <{out}> was created."
            ).format(out=output)
        )
        empty_maps = output_maps

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
    from grass.pygrass.modules import Module

    main()
