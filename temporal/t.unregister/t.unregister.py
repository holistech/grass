#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.unregister
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Unregister raster, vector and raster3d maps from the temporal database or a specific space time dataset
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Unregisters raster, vector and raster3d maps from the temporal database or a specific space time dataset.
# % keyword: temporal
# % keyword: map management
# % keyword: unregister
# % keyword: time
# %end

# %option G_OPT_STDS_INPUT
# % required: no
# %end

# %option G_OPT_F_INPUT
# % key: file
# % description: Input file with map names, one per line
# % required: no
# %end

# %option G_OPT_MAP_TYPE
# % guidependency: input,maps
# %end


# %option G_OPT_MAP_INPUTS
# % description: Name(s) of existing raster, vector or raster3d map(s) to unregister
# % required: no
# %end

import grass.script as gs


def check_options(maps, file):
    """Refuse a call with both or neither of maps and file"""
    if maps and file:
        gs.fatal(_("%s= and %s= are mutually exclusive") % ("maps", "file"))

    if not maps and not file:
        gs.fatal(_("%s= or %s= must be specified") % ("maps", "file"))


def map_ids(maps, file, mapset):
    """Return the ids of the maps of the option maps or of the file

    A name without mapset gets the current mapset.
    """
    dummy = tgis.RasterDataset(None)

    if maps:
        return [dummy.build_id(mapname, mapset) for mapname in maps.split(",")]

    try:
        names = tgis.names_from_file(file)
    except ValueError as error:
        gs.fatal(str(error))
    return [dummy.build_id(mapname, mapset) for mapname in names]


def unregister_maps(maplist, type, sp, mapset, dbif):
    """Unregister the maps from sp, or without sp from the temporal database

    Returns the ids of the datasets that held a map unregistered from the
    temporal database, in the order they were found.
    """
    num_maps = len(maplist)
    update_dict = {}
    statement = ""

    gs.message(_("Unregister maps"))
    for count, mapid in enumerate(maplist):
        if count % 10 == 0:
            gs.percent(count, num_maps, 1)

        map_item = tgis.dataset_factory(type, mapid)

        # Unregister map if in database
        if map_item.is_in_db(dbif, mapset=mapset):
            # Unregister from a single dataset
            if sp is not None:
                # Collect SQL statements
                statement += sp.unregister_map(map=map_item, dbif=dbif, execute=False)

            # Unregister from temporal database
            else:
                # We need to update all datasets after the removement of maps
                map_item.metadata.select(dbif, mapset=mapset)
                datasets = map_item.get_registered_stds(dbif)
                # Store all unique dataset ids in a dictionary
                if datasets:
                    for dataset in datasets:
                        update_dict[dataset] = dataset
                # Collect SQL statements
                statement += map_item.delete(dbif=dbif, update=False, execute=False)
        else:
            gs.warning(
                _("Unable to find %s map <%s> in temporal database")
                % (map_item.get_type(), map_item.get_id())
            )

    # Execute the collected SQL statements
    if statement:
        dbif.execute_transaction(statement, mapset=mapset)

    gs.percent(num_maps, num_maps, 1)
    return list(update_dict.values())


def update_datasets(input, sp, dataset_ids, type, dbif):
    """Update the extent and metadata of the datasets that held the maps

    With input the dataset sp also gets the command of this call.
    """
    if input:
        gs.message(_("Unregister maps from space time dataset <%s>") % (input))
    else:
        gs.message(_("Unregister maps from the temporal database"))

    if sp is not None:
        sp.update_from_registered_maps(dbif)
        sp.update_command_string(dbif=dbif)
    elif dataset_ids:
        for count, id in enumerate(dataset_ids):
            sp = tgis.open_old_stds(id, type, dbif)
            sp.update_from_registered_maps(dbif)
            gs.percent(count, len(dataset_ids), 1)
        gs.percent(len(dataset_ids), len(dataset_ids), 1)


def main():
    # Get the options
    file = options["file"]
    input = options["input"]
    maps = options["maps"]
    type = options["type"]

    # Make sure the temporal database exists
    tgis.init()

    check_options(maps, file)

    mapset = tgis.get_current_mapset()

    dbif = tgis.SQLDatabaseInterfaceConnection(mapsets=mapset)
    dbif.connect()

    # In case a space time dataset is specified
    sp = None
    if input:
        sp = tgis.open_old_stds(input, type, dbif)

    maplist = map_ids(maps, file, mapset)
    dataset_ids = unregister_maps(maplist, type, sp, mapset, dbif)
    update_datasets(input, sp, dataset_ids, type, dbif)

    dbif.close()


if __name__ == "__main__":
    options, flags = gs.parser()

    # Not in main(): profile_function() needs the library before main() runs.
    # gs.parser() has already answered --help and --interface-description.
    import grass.temporal as tgis

    tgis.profile_function(main)
