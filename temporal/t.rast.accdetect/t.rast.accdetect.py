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


############################################################################

# The keys of the relations as the topology builder files them.
range_relations = ["EQUAL", "DURING", "OVERLAPS", "OVERLAPPED", "CONTAINS"]


def _to_datetime(text, option, dbif):
    """Convert the value of an option to a datetime or end with a message"""
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

    id = input if input.find("@") >= 0 else input + "@" + mapset
    input_strds = tgis.SpaceTimeRasterDataset(id)

    if not input_strds.is_in_db():
        dbif.close()
        gs.fatal(
            _("Space time %s dataset <%s> not found")
            % (input_strds.get_new_map_instance(None).get_type(), id)
        )

    input_strds.select(dbif)
    dummy = input_strds.get_new_map_instance(None)

    # The occurrence space time raster dataset
    if occurrence:
        if not minimum or not maximum:
            if not range_:
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
        if occurrence_strds.is_in_db(dbif):
            if not gs.overwrite():
                dbif.close()
                gs.fatal(
                    _(
                        "Space time raster dataset <%s> is already in the "
                        "database, use overwrite flag to overwrite"
                    )
                    % occurrence_id
                )

    # The indicator space time raster dataset
    if indicator:
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
        if indicator.find("@") >= 0:
            indicator_id = indicator
        else:
            indicator_id = indicator + "@" + mapset

        indicator_strds = tgis.SpaceTimeRasterDataset(indicator_id)
        if indicator_strds.is_in_db(dbif):
            if not gs.overwrite():
                dbif.close()
                gs.fatal(
                    _(
                        "Space time raster dataset <%s> is already in the "
                        "database, use overwrite flag to overwrite"
                    )
                    % indicator_id
                )
        staend = staend.split(",")
        indicator_start = int(staend[0])
        indicator_mid = int(staend[1])
        indicator_end = int(staend[2])

    # The minimum threshold space time raster dataset
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

    # The maximum threshold space time raster dataset
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

    if not tgis.check_granularity_string(cycle, input_strds.get_temporal_type()):
        dbif.close()
        gs.fatal(_("Invalid cycle"))

    if offset and not tgis.check_granularity_string(
        offset, input_strds.get_temporal_type()
    ):
        dbif.close()
        gs.fatal(_("Invalid offset"))

    if input_strds.is_time_absolute():
        start = _to_datetime(start, "start", dbif)
        stop = _to_datetime(stop, "stop", dbif) if stop else input_strds_end
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
        # Added to the start as text the cycle and the offset would fail.
        cycle = int(cycle)
        offset = int(offset) if offset else 0
        end = start + cycle

    # A cycle or an offset that does not move time forward would make the
    # loop run forever.
    if end <= start:
        dbif.close()
        gs.fatal(_("The cycle must be longer than zero"))
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

    count = 1
    indi_count = 1
    number = 0
    occurrence_maps = {}
    indicator_maps = {}

    while input_strds_end > start and stop > start:
        # Make sure that the cyclic computation will stop at the correct time
        if stop and end > stop:
            end = stop

        where = "start_time >= '%s' AND start_time < '%s'" % (str(start), str(end))
        input_maps = input_strds.get_registered_maps_as_objects(where=where, dbif=dbif)

        gs.debug(len(input_maps))

        input_topo = tgis.SpatioTemporalTopologyBuilder()
        input_topo.build(input_maps, input_maps)

        if len(input_maps) == 0:
            number += 1
            start, end = tgis.next_cycle(
                origin, number, end, cycle, offset, input_strds.is_time_absolute()
            )
            continue

        gs.message(_("Processing cycle %s - %s") % (str(start), str(end)))

        count = compute_occurrence(
            occurrence_maps,
            input_strds,
            input_maps,
            start,
            base,
            count,
            time_suffix,
            mapset,
            where,
            reverse,
            range_,
            minimum_strds,
            maximum_strds,
            dbif,
        )

        # Indicator computation is based on the occurrence so we need to start it after
        # the occurrence cycle
        if indicator:
            num_maps = len(input_maps)
            for i in range(num_maps):
                map = input_maps[num_maps - i - 1] if reverse else input_maps[i]

                suffix = tgis.map_name_suffix(
                    map, time_suffix, input_strds.get_granularity(), indi_count
                )
                indicator_map_name = f"{base}_indicator_{suffix}"
                indicator_map_id = dummy.build_id(indicator_map_name, mapset)
                indicator_map = input_strds.get_new_map_instance(indicator_map_id)

                # Check if new map is in the temporal database
                if indicator_map.is_in_db(dbif):
                    if gs.overwrite():
                        # Remove the existing temporal database entry
                        indicator_map.delete(dbif)
                        indicator_map = input_strds.get_new_map_instance(
                            indicator_map_id
                        )
                    else:
                        gs.fatal(
                            _(
                                "Map <%s> is already registered in the temporal"
                                " database, use overwrite flag to overwrite."
                            )
                            % (indicator_map.get_map_id())
                        )

                curr_map = occurrence_maps[map.get_id()].get_name()

                # Reverse time
                if reverse:
                    if i == 0:
                        prev_map = curr_map
                        subexpr1 = "null()"
                        subexpr3 = "%i" % (indicator_start)
                    elif 0 < i < num_maps - 1:
                        prev_map = occurrence_maps[map.next().get_id()].get_name()
                        next_map = occurrence_maps[map.prev().get_id()].get_name()
                        # In case the previous map is null() set null() or the start
                        # indicator
                        subexpr1 = "if(isnull(%s), null(), %i)" % (
                            curr_map,
                            indicator_start,
                        )
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
                        expression = "%s = if(isnull(%s), %s, %s)" % (
                            indicator_map_name,
                            prev_map,
                            subexpr1,
                            subexpr3,
                        )
                    else:
                        prev_map = occurrence_maps[map.next().get_id()].get_name()
                        subexpr1 = "if(isnull(%s), null(), %i)" % (
                            curr_map,
                            indicator_start,
                        )
                        # The cycle ends here, so a run that goes on ends too.
                        subexpr3 = "if(isnull(%s), null(), %i)" % (
                            curr_map,
                            indicator_end,
                        )
                else:  # noqa: PLR5501
                    if i == 0:
                        prev_map = curr_map
                        subexpr1 = "null()"
                        subexpr3 = "%i" % (indicator_start)
                    elif 0 < i < num_maps - 1:
                        prev_map = occurrence_maps[map.prev().get_id()].get_name()
                        next_map = occurrence_maps[map.next().get_id()].get_name()
                        # In case the previous map is null() set null() or the start
                        # indicator
                        subexpr1 = "if(isnull(%s), null(), %i)" % (
                            curr_map,
                            indicator_start,
                        )
                        # In case the previous map was not null() if the current map
                        #   is null() set null()
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
                        expression = "%s = if(isnull(%s), %s, %s)" % (
                            indicator_map_name,
                            prev_map,
                            subexpr1,
                            subexpr3,
                        )
                    else:
                        prev_map = occurrence_maps[map.prev().get_id()].get_name()
                        subexpr1 = "if(isnull(%s), null(), %i)" % (
                            curr_map,
                            indicator_start,
                        )
                        # The cycle ends here, so a run that goes on ends too.
                        subexpr3 = "if(isnull(%s), null(), %i)" % (
                            curr_map,
                            indicator_end,
                        )

                expression = "%s = if(isnull(%s), %s, %s)" % (
                    indicator_map_name,
                    prev_map,
                    subexpr1,
                    subexpr3,
                )
                gs.debug(expression)
                gs.mapcalc(expression, overwrite=True)

                map_start, map_end = map.get_temporal_extent_as_tuple()

                if map.is_time_absolute():
                    indicator_map.set_absolute_time(map_start, map_end)
                else:
                    indicator_map.set_relative_time(
                        map_start, map_end, map.get_relative_time_unit()
                    )

                indicator_maps[map.get_id()] = indicator_map
                indi_count += 1

        number += 1
        start, end = tgis.next_cycle(
            origin, number, end, cycle, offset, input_strds.is_time_absolute()
        )

    empty_maps = []

    create_strds_register_maps(
        input_strds, occurrence_strds, occurrence_maps, register_null, empty_maps, dbif
    )

    if indicator:
        create_strds_register_maps(
            input_strds,
            indicator_strds,
            indicator_maps,
            register_null,
            empty_maps,
            dbif,
        )

    dbif.close()

    # Remove empty maps
    if len(empty_maps) > 0:
        for map in empty_maps:
            gs.run_command(
                "g.remove", flags="f", type="raster", name=map.get_name(), quiet=True
            )


############################################################################


def create_strds_register_maps(
    in_strds, out_strds, out_maps, register_null, empty_maps, dbif
):
    out_id = out_strds.get_id()

    if out_strds.is_in_db(dbif):
        if gs.overwrite():
            out_strds.delete(dbif)
            out_strds = in_strds.get_new_instance(out_id)

    temporal_type, semantic_type, title, description = in_strds.get_initial_values()
    out_strds.set_initial_values(temporal_type, semantic_type, title, description)
    out_strds.insert(dbif)

    # Register the maps in the database
    count = 0
    for map in out_maps.values():
        count += 1
        if count % 10 == 0:
            gs.percent(count, len(out_maps), 1)
        # Read the raster map data
        map.load()
        # In case of a empty map continue, do not register empty maps
        if not register_null:
            if map.metadata.get_min() is None and map.metadata.get_max() is None:
                empty_maps.append(map)
                continue

        # Insert map in temporal database
        map.insert(dbif)
        out_strds.register_map(map, dbif)

    out_strds.update_from_registered_maps(dbif)
    gs.percent(1, 1, 1)


############################################################################


def compute_occurrence(
    occurrence_maps,
    input_strds,
    input_maps,
    start,
    base,
    count,
    tsuffix,
    mapset,
    where,
    reverse,
    range_,
    minimum_strds,
    maximum_strds,
    dbif,
):
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

        occurrence_map_id = map.build_id(occurrence_map_name, mapset)
        occurrence_map = input_strds.get_new_map_instance(occurrence_map_id)

        # Check if new map is in the temporal database
        if occurrence_map.is_in_db(dbif):
            if gs.overwrite():
                # Remove the existing temporal database entry
                occurrence_map.delete(dbif)
                occurrence_map = input_strds.get_new_map_instance(occurrence_map_id)
            else:
                gs.fatal(
                    _(
                        "Map <%s> is already registered in the temporal"
                        " database, use overwrite flag to overwrite."
                    )
                    % (occurrence_map.get_map_id())
                )

        # Without a range every granule needs a map of the datasets.
        range_vals = range_.split(",") if range_ else [None, None]
        min = range_vals[0]
        max = range_vals[1]

        if minimum_strds:
            relations = input_maps_minimum[index].get_temporal_relations()
            for relation in range_relations:
                if relation in relations:
                    min = str(relations[relation][0].get_id())
                    break

        if maximum_strds:
            relations = input_maps_maximum[index].get_temporal_relations()
            for relation in range_relations:
                if relation in relations:
                    max = str(relations[relation][0].get_id())
                    break

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

        map_start, map_end = map.get_temporal_extent_as_tuple()

        if map.is_time_absolute():
            occurrence_map.set_absolute_time(map_start, map_end)
        else:
            occurrence_map.set_relative_time(
                map_start, map_end, map.get_relative_time_unit()
            )

        # Store the new maps
        occurrence_maps[map.get_id()] = occurrence_map

        count += 1

    return count


############################################################################

if __name__ == "__main__":
    options, flags = gs.parser()
    # lazy imports
    import grass.temporal as tgis

    main()
