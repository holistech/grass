#!/usr/bin/env python3

############################################################################
#
# MODULE:   t.remove
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:  Remove space time datasets from the temporal database
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Removes space time datasets from temporal database.
# % keyword: temporal
# % keyword: map management
# % keyword: remove
# % keyword: time
# %end

# %option G_OPT_STDS_INPUTS
# % guisection: Input
# % required: no
# %end

# %option
# % key: type
# % type: string
# % description: Type of the space time dataset, default is strds
# % guidependency: inputs
# % guisection: Input
# % required: no
# % options: strds, str3ds, stvds
# % answer: strds
# %end

# %option G_OPT_F_INPUT
# % key: file
# % description: Input file with dataset names, one per line
# % guisection: Input
# % required: no
# %end

# %flag
# % key: r
# % description: Remove stds and unregister maps from temporal database
# %end

# %flag
# % key: f
# % description: Force removal (required for actual deletion of files)
# %end

# %flag
# % key: d
# % description: Remove stds, unregister maps from temporal database and delete them from mapset
# %end

import grass.script as gs

# lazy imports at the end of the file

#: The type of g.remove for the maps of each type of dataset
MAP_TYPES = {"strds": "raster", "str3ds": "raster_3d", "stvds": "vector"}


def check_options(datasets, file):
    """Refuse a call with both or neither of inputs and file"""
    if datasets and file:
        gs.fatal(_("%s= and %s= are mutually exclusive") % ("inputs", "file"))

    # Without a target the call would end silently, which hides an empty
    # variable in the calling script.
    if not datasets and not file:
        gs.fatal(_("%s= or %s= must be specified") % ("inputs", "file"))


def dataset_names(datasets, file):
    """Return the dataset names of the option inputs or of the file"""
    if datasets:
        return datasets.split(",")
    try:
        return tgis.names_from_file(file)
    except ValueError as error:
        gs.fatal(str(error))


def selected_maps(sp, current_mapset, dbif):
    """Yield the registered maps of sp, each selected from the database"""
    for map in sp.get_registered_maps_as_objects(dbif=dbif):
        # A map of another mapset is registered in the database of the
        # current mapset only, when no dataset there holds it.
        map.select(dbif, mapset=current_mapset)
        yield map


def list_datasets(stds_list, recursive, clean, current_mapset, dbif):
    """Show what a call with -f would remove, and that nothing was removed"""
    for sp in stds_list:
        gs.message(
            _("{stds}: {gid}").format(stds=sp.get_type().upper(), gid=sp.get_id())
        )
        if recursive or clean:
            list_maps(sp, recursive, current_mapset, dbif)

    gs.message(
        _(
            "Nothing removed. You must use the force flag (-{flag}) to actually "
            "remove them."
        ).format(flag="f")
    )


def list_maps(sp, recursive, current_mapset, dbif):
    """Show the maps of sp that -f would unregister, and with -d delete"""
    if recursive:
        msg = _(
            "The following maps of {stds} {gid} will be "
            "unregistered from temporal database:"
        )
    else:
        msg = _(
            "The following maps of {stds} {gid} will be "
            "unregistered from temporal database and removed "
            "from spatial database:"
        )
    gs.message(msg.format(stds=sp.get_type(), gid=sp.get_id()))
    for map in selected_maps(sp, current_mapset, dbif):
        gs.message(_("- %s") % map.get_name())


def remove_datasets(stds_list, type, recursive, clean, remove, current_mapset, dbif):
    """Remove the datasets, with -r or -d their maps, and update the others

    The datasets that held a removed map and are not removed themselves get
    their extent and metadata computed from the maps that are left.
    """
    statement = ""
    # Datasets that held a deleted map. The maps are deleted without
    # execution, so delete() cannot update them.
    affected = set()
    removed = set()
    for sp in stds_list:
        if recursive or clean:
            affected |= unregister_maps(sp, type, clean, remove, current_mapset, dbif)
        removed.add(sp.get_id())
        statement += sp.delete(dbif=dbif, execute=False)

    # Execute the collected SQL statements
    dbif.execute_transaction(statement)
    # The datasets that are removed need no update.
    for dataset_id in sorted(affected - removed):
        stds = tgis.open_old_stds(dataset_id, type, dbif)
        stds.update_from_registered_maps(dbif)
    dbif.close()


def unregister_maps(sp, type, clean, remove, current_mapset, dbif):
    """Unregister the maps of sp, and with clean delete them from the mapset

    Returns the ids of the datasets that held the maps.
    """
    affected = set()
    map_statement = ""
    count = 1
    name_list = []
    for map in selected_maps(sp, current_mapset, dbif):
        if clean:
            # g.remove works in the current mapset only
            if map.get_mapset() != current_mapset:
                gs.warning(
                    _("Map <{name}> is in mapset <{mapset}> and is not removed").format(
                        name=map.get_name(), mapset=map.get_mapset()
                    )
                )
            # We may have multiple layer for a single map, hence we need
            # to avoid multiple deletions of the same map,
            # but the database entries are still present and must be removed
            elif map.get_name() not in name_list:
                name_list.append(str(map.get_name()))
        # The register of the current mapset, which delete() also
        # uses: the map may belong to another mapset, whose temporal
        # database knows nothing of the datasets here.
        affected.update(map.get_registered_stds(dbif, mapset=current_mapset) or ())
        map_statement += map.delete(dbif=dbif, execute=False)

        count += 1
        # Execute and delete in batches, the first of 99 maps because count
        # starts at 1, then of 100 maps each.
        if count % 100 == 0:
            dbif.execute_transaction(map_statement)
            if clean:
                remove(type=MAP_TYPES[type], name=name_list, run_=True)
            map_statement = ""
            name_list = []

    if map_statement:
        dbif.execute_transaction(map_statement)
    if clean and name_list:
        remove(type=MAP_TYPES[type], name=name_list, run_=True)
    return affected


def main():
    # Get the options
    datasets = options["inputs"]
    file = options["file"]
    type = options["type"]
    recursive = flags["r"]
    force = flags["f"]
    clean = flags["d"]

    check_options(datasets, file)

    # Make sure the temporal database exists
    tgis.init()

    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    dataset_list = dataset_names(datasets, file)
    current_mapset = tgis.get_current_mapset()

    # Create the pygrass Module object for g.remove
    remove = pyg.Module("g.remove", quiet=True, flags="f", run_=False)

    if not force:
        gs.message(_("The following data base element files will be deleted:"))

    # All datasets are opened before the first one is removed, so that an
    # unknown name stops the run before anything has changed.
    stds_list = [tgis.open_old_stds(name.strip(), type, dbif) for name in dataset_list]

    if force:
        remove_datasets(stds_list, type, recursive, clean, remove, current_mapset, dbif)
    else:
        list_datasets(stds_list, recursive, clean, current_mapset, dbif)


if __name__ == "__main__":
    options, flags = gs.parser()

    # lazy imports
    import grass.pygrass.modules as pyg
    import grass.temporal as tgis

    tgis.profile_function(main)
