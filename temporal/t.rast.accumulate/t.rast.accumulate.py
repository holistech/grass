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

############################################################################


def _to_datetime(text, option, dbif):
    """Convert the value of an option to a datetime or end with a message"""
    import grass.temporal as tgis

    # string_to_datetime ends in an AttributeError for text it cannot read
    # (checked 20.10.2026 with "garbage"), the annotation says None.
    try:
        converted = tgis.string_to_datetime(text)
    except (AttributeError, ValueError):
        converted = None
    if converted is None:
        dbif.close()
        gs.fatal(_("Invalid date <{}> of the option <{}>").format(text, option))
    return converted


def main():
    # lazy imports
    import grass.temporal as tgis
    from grass.pygrass.modules import Module

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

    # r.series.accumulate refuses limits that do not rise, so refuse them
    # before any map is made.
    limits_lower, limits_upper = (float(value) for value in limits.split(","))
    if limits_upper <= limits_lower:
        gs.fatal(_("The upper limit must be above the lower limit"))

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

    id = input if input.find("@") >= 0 else input + "@" + mapset
    input_strds = tgis.SpaceTimeRasterDataset(id)

    if not input_strds.is_in_db():
        dbif.close()
        gs.fatal(_("Space time raster dataset <%s> not found") % (id))

    input_strds.select(dbif)

    out_id = output if output.find("@") >= 0 else output + "@" + mapset

    # The output space time raster dataset
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

    # The lower threshold space time raster dataset
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

    # The upper threshold space time raster dataset
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

    _input_strds_start, input_strds_end = input_strds.get_temporal_extent_as_tuple()
    # The loop below ends before input_strds_end and before stop, so an
    # instant at the end of the dataset would be left out. One unit behind it
    # keeps it in, as in t.rast.aggregate.
    if input_strds.get_registered_maps_as_objects(
        where="start_time = '%s' AND end_time IS NULL" % str(input_strds_end),
        dbif=dbif,
    ):
        if input_strds.is_time_absolute():
            input_strds_end = tgis.increment_datetime_by_string(
                input_strds_end, "1 second"
            )
        else:
            input_strds_end += 1

    if input_strds.is_time_absolute():
        start = _to_datetime(start, "start", dbif)
        stop = _to_datetime(stop, "stop", dbif) if stop else input_strds_end
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
            stop = int(stop) if stop else input_strds_end
        except ValueError:
            dbif.close()
            gs.fatal(_("The options start and stop must be integers"))

    if input_strds.is_time_absolute():
        end = tgis.increment_datetime_by_string(start, cycle)
    else:
        # The lengths of time were checked above as integers of the unit of
        # the dataset; added to the start as text they would fail.
        cycle = int(cycle)
        granularity = int(granularity)
        offset = int(offset) if offset else 0
        end = start + cycle

    # A cycle, a granule or an offset that does not move time forward would
    # make the loops below run forever.
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
    origin = start
    next_start, _next_end = tgis.next_cycle(
        origin, 1, end, cycle, offset, input_strds.is_time_absolute()
    )
    if next_start <= start:
        dbif.close()
        gs.fatal(
            _(
                "The offset must not move the next cycle back to or before the start of this one"
            )
        )

    # The keys of the relations as the topology builder files them.
    limit_relations = ["EQUAL", "DURING", "OVERLAPS", "OVERLAPPED", "CONTAINS"]

    count = 1
    output_maps = []
    number = 0

    while input_strds_end > start and stop > start:
        # Make sure that the cyclic computation will stop at the correct time
        if stop and end > stop:
            end = stop

        where = "start_time >= '%s' AND start_time < '%s'" % (str(start), str(end))
        input_maps = input_strds.get_registered_maps_as_objects(where=where, dbif=dbif)

        gs.message(_("Processing cycle %s - %s") % (str(start), str(end)))

        if len(input_maps) == 0:
            number += 1
            start, end = tgis.next_cycle(
                origin, number, end, cycle, offset, input_strds.is_time_absolute()
            )
            continue

        # Lets create a dummy list of maps with granularity conform intervals
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
        # Lists to compute the topology with upper and lower datasets

        # Create the topology between the granularity conform list and all maps
        # of the current cycle
        gran_topo = tgis.SpatioTemporalTopologyBuilder()
        gran_topo.build(gran_list, input_maps)

        if lower:
            lower_maps = lower_strds.get_registered_maps_as_objects(dbif=dbif)
            gran_lower_topo = tgis.SpatioTemporalTopologyBuilder()
            gran_lower_topo.build(gran_list_low, lower_maps)

        if upper:
            upper_maps = upper_strds.get_registered_maps_as_objects(dbif=dbif)
            gran_upper_topo = tgis.SpatioTemporalTopologyBuilder()
            gran_upper_topo.build(gran_list_up, upper_maps)

        old_map_name = None

        # Aggregate
        num_maps = len(gran_list)

        for i in range(num_maps):
            # The threshold lists are in time order like gran_list, so they
            # take the same index as the granule.
            index = num_maps - i - 1 if reverse else i
            map = gran_list[index]
            # Select input maps based on temporal topology relations
            input_maps = []
            if map.get_equal():
                input_maps += map.get_equal()
            elif map.get_contains():
                input_maps += map.get_contains()
            elif map.get_overlaps():
                input_maps += map.get_overlaps()
            elif map.get_overlapped():
                input_maps += map.get_overlapped()
            elif map.get_during():
                input_maps += map.get_during()

            # Check input maps
            if len(input_maps) == 0:
                continue

            # New output map
            suffix = tgis.map_name_suffix(
                map, time_suffix, input_strds.get_granularity(), count
            )
            output_map_name = f"{base}_{suffix}"

            output_map_id = map.build_id(output_map_name, mapset)
            output_map = input_strds.get_new_map_instance(output_map_id)

            # Check if new map is in the temporal database
            if output_map.is_in_db(dbif):
                if gs.overwrite():
                    # Remove the existing temporal database entry
                    output_map.delete(dbif)
                    output_map = input_strds.get_new_map_instance(output_map_id)
                else:
                    gs.fatal(
                        _(
                            "Map <%s> is already registered in the temporal"
                            " database, use overwrite flag to overwrite."
                        )
                        % (output_map.get_map_id())
                    )

            map_start, map_end = map.get_temporal_extent_as_tuple()

            if map.is_time_absolute():
                output_map.set_absolute_time(map_start, map_end)
            else:
                output_map.set_relative_time(
                    map_start, map_end, map.get_relative_time_unit()
                )

            lower_map_name = None
            if lower:
                relations = gran_list_low[index].get_temporal_relations()
                for relation in limit_relations:
                    if relation in relations:
                        lower_map_name = str(relations[relation][0].get_id())
                        break

            upper_map_name = None
            if upper:
                relations = gran_list_up[index].get_temporal_relations()
                for relation in limit_relations:
                    if relation in relations:
                        upper_map_name = str(relations[relation][0].get_id())
                        break

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

            accmod.inputs["limits"].value = (limits_lower, limits_upper)

            if shift:
                accmod.inputs["shift"].value = float(shift)

            if scale:
                accmod.inputs["scale"].value = float(scale)

            if method:
                accmod.inputs["method"].value = method

            try:
                accmod.run()
            except CalledModuleError:
                dbif.close()
                gs.fatal(_("Error running r.series.accumulate"))

            output_maps.append(output_map)
            old_map_name = output_map_name
            count += 1

        number += 1
        start, end = tgis.next_cycle(
            origin, number, end, cycle, offset, input_strds.is_time_absolute()
        )

    # Insert the maps into the output space time dataset
    if output_strds.is_in_db(dbif) and gs.overwrite():
        output_strds.delete(dbif)
        output_strds = input_strds.get_new_instance(out_id)

    temporal_type, semantic_type, title, description = input_strds.get_initial_values()
    output_strds.set_initial_values(temporal_type, semantic_type, title, description)
    output_strds.insert(dbif)

    empty_maps = tgis.register_new_maps(output_maps, output_strds, register_null, dbif)

    dbif.close()

    # Remove empty maps
    if len(empty_maps) > 0:
        for map in empty_maps:
            gs.run_command(
                "g.remove", flags="f", type="raster", name=map.get_name(), quiet=True
            )


if __name__ == "__main__":
    options, flags = gs.parser()
    main()
