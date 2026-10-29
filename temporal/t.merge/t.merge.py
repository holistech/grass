#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.merge
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Merge several space time datasets into a single one
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Merges several space time datasets into a single space time dataset.
# % keyword: temporal
# % keyword: time management
# % keyword: merge
# % keyword: time
# %end

# %option G_OPT_STDS_INPUTS
# %end

# %option G_OPT_STDS_OUTPUT
# %end

# %option G_OPT_STDS_TYPE
# % guidependency: inputs
# % guisection: Required
# %end

import grass.script as gs

# lazy imports at the end of the file


def dataset_ids(inputs, output, mapset):
    """Return the ids of the input datasets and of the output dataset

    A name without mapset gets the current mapset; the output must be in it.
    """
    input_ids = []
    for input in inputs.split(","):
        if input.find("@") >= 0:
            input_ids.append(input)
        else:
            input_ids.append(input + "@" + mapset)

    if output.find("@") >= 0:
        output_id = output
        out_mapset = output.split("@")[1]
        if out_mapset != mapset:
            gs.fatal(
                _("Output space time dataset <%s> must be located in this mapset")
                % (output)
            )
    else:
        output_id = output + "@" + mapset
    return input_ids, output_id


def open_inputs(input_ids, type, dbif):
    """Open the input datasets, which must have the same temporal type"""
    stds_list = []
    first = None
    for id in input_ids:
        stds = tgis.open_old_stds(id, type, dbif)
        if first is None:
            first = stds

        if first.get_temporal_type() != stds.get_temporal_type():
            dbif.close()
            gs.fatal(_("Space time datasets to merge must have the same temporal type"))

        stds_list.append(stds)
    return stds_list


def open_output(output, output_id, type, first, dbif):
    """Open the output dataset: a new one, or an existing one with --overwrite

    The temporal type of a new one is that of the first input. Returns the
    dataset and whether it existed.
    """
    output_stds = tgis.dataset_factory(type, output_id)
    output_exists = output_stds.is_in_db(dbif=dbif)

    if output_exists and not gs.overwrite():
        dbif.close()
        gs.fatal(
            _(
                "Unable to merge maps into space time %s dataset <%s> "
                "please use the overwrite flag."
            )
            % (first.get_new_map_instance(None).get_type(), output_id)
        )

    if not output_exists:
        output_stds = tgis.open_new_stds(
            output,
            type,
            first.get_temporal_type(),
            "Merged space time dataset",
            "Merged space time dataset",
            "mean",
            dbif=dbif,
            overwrite=False,
        )
    else:
        output_stds.select(dbif=dbif)
    return output_stds, output_exists


def registered_map_ids(output_stds, dbif):
    """Return the ids of the maps that output_stds holds"""
    rows = output_stds.get_registered_maps(columns="id", dbif=dbif)
    return {row["id"] for row in rows or ()}


def register_maps(stds_list, output_stds, registered, mapset, dbif):
    """Register the maps of the inputs in output_stds, each map once

    registered holds the ids of the maps that output_stds holds already; the
    maps registered here are added to it.
    """
    for stds in stds_list:
        # The output as one of the inputs adds no map.
        if stds.get_id() == output_stds.get_id():
            continue

        for map in stds.get_registered_maps_as_objects(dbif=dbif) or ():
            if map.get_id() in registered:
                continue

            map.select(dbif=dbif)
            # A map of another mapset is registered in the temporal database
            # of its own mapset only; the output needs an entry for it in the
            # current one.
            if not map.is_in_db(dbif, mapset):
                map.insert(dbif)
            output_stds.register_map(map=map, dbif=dbif)
            registered.add(map.get_id())


def main():
    # Get the options
    inputs = options["inputs"]
    output = options["output"]
    type = options["type"]

    # Make sure the temporal database exists
    tgis.init()

    # Get the current mapset to create the id of the space time dataset
    mapset = gs.gisenv()["MAPSET"]

    input_ids, output_id = dataset_ids(inputs, output, mapset)

    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    stds_list = open_inputs(input_ids, type, dbif)

    output_stds, output_exists = open_output(
        output, output_id, type, stds_list[0], dbif
    )

    # Maps that are already registered in an existing dataset are not
    # registered again.
    registered = set()
    if output_exists:
        registered = registered_map_ids(output_stds, dbif)

    filled = False
    try:
        register_maps(stds_list, output_stds, registered, mapset, dbif)
        filled = True
    finally:
        # A refusal of the library ends the process through sys.exit(); a new
        # output that could not be filled would stay behind empty.
        if not filled:
            if not output_exists:
                output_stds.delete(dbif=dbif)
            dbif.close()

    output_stds.update_from_registered_maps(dbif=dbif)

    if output_exists:
        output_stds.update_command_string(dbif=dbif)


if __name__ == "__main__":
    options, flags = gs.parser()
    # lazy imports
    import grass.temporal as tgis

    main()
