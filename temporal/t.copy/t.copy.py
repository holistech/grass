#!/usr/bin/env python3

############################################################################
#
# MODULE:	    t.copy
# AUTHOR(S):	Markus Metz
#
# PURPOSE:	    Create a copy of a space time dataset
# SPDX-FileCopyrightText: 2021 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Creates a copy of a space time raster dataset.
# % keyword: temporal
# % keyword: copy
# % keyword: time
# %end

# %option G_OPT_STDS_INPUT
# %end

# %option G_OPT_STDS_TYPE
# % guidependency: input
# % guisection: Required
# % options: strds, str3ds, stvds
# %end

# %option G_OPT_STDS_OUTPUT
# %end

# %flag
# % key: c
# % label: Also copy maps of the space-time dataset
# % description: By default the old maps are only registered in the new dataset.
# %end


import grass.script as gs

############################################################################


def _layer(map, maptype):
    """Return the layer of a vector map and None for all other maps"""
    return map.get_layer() if maptype == "vector" else None


def map_type_and_element(stdstype):
    """Return the map type of a dataset type and the element of that map type"""
    if stdstype == "str3ds":
        return "raster_3d", "grid3"
    if stdstype == "stvds":
        return "vector", "vector"
    return "raster", "cell"


def check_output_mapset(output, mapset):
    """Refuse an output name that is in another mapset than the current one"""
    if "@" in output:
        check_identifier(output)
        _outname, outmapset = output.split("@")
        if outmapset != mapset:
            gs.fatal(
                _("The output dataset <%s> must be in the current mapset<%s>.")
                % (output, mapset)
            )


def check_maps_can_be_copied(old_maps, mapset, maptype, element, overwrite, dbif):
    """Stop if a map of another mapset cannot be copied into the current one

    Everything that can refuse the copy is checked before the first map is
    copied, so that a refusal does not leave copied maps behind.
    """
    for map in old_maps:
        map_name, map_mapset = map.get_name(), map.get_mapset()
        if map_mapset != mapset:
            found = gs.find_file(name=map_name, element=element, mapset=mapset)
            if found["name"] is not None and len(found["name"]) > 0:
                gs.fatal(
                    _("A %s map <%s> exists already in the current mapset <%s>.")
                    % (maptype, map_name, mapset)
                )
        tgis.check_new_map_dataset(
            map_name, _layer(map, maptype), maptype, overwrite, dbif
        )


def copy_maps_to_mapset(old_maps, mapset, maptype, overwrite, dbif):
    """Copy the maps of other mapsets into the current one; return all maps

    A map that is in the current mapset already is not copied: it keeps its
    entry in the temporal database.
    """
    msgr = tgis.get_tgis_message_interface()

    new_maps = []
    num_maps = len(old_maps)
    count = 0

    for map in old_maps:
        count += 1
        map_name, map_mapset = map.get_name(), map.get_mapset()

        if map_mapset != mapset:
            # The id of a vector map carries its layer, which g.copy refuses.
            kwargs = {maptype: f"{map_name}@{map_mapset},{map_name}"}
            gs.run_command("g.copy", **kwargs)
            new_map = tgis.open_new_map_dataset(
                map_name,
                _layer(map, maptype),
                type=maptype,
                temporal_extent=map.get_temporal_extent(),
                overwrite=overwrite,
                dbif=dbif,
            )
            # Semantic labels exist for raster maps only
            if maptype == "raster":
                semantic_label = map.metadata.get_semantic_label()
                if semantic_label is not None and semantic_label != "None":
                    new_map.metadata.set_semantic_label(semantic_label)
        else:
            # The map is already in the current mapset. It keeps its entry
            # in the temporal database, and so its registration in the
            # source dataset, and joins the new dataset in addition.
            gs.message(
                _("The %s map <%s> is already in the current mapset, not copying")
                % (maptype, map_name)
            )
            new_map = map

        if count % 10 == 0:
            msgr.percent(count, num_maps, 1)

        new_maps.append(new_map)
    return new_maps


def register_maps(new_sp, new_maps, mapset, maptype, dbif):
    """Insert the maps that the temporal database lacks and register them"""
    for map in new_maps:
        # Insert map in temporal database
        if not map.is_in_db(dbif, mapset):
            # Only the metadata of raster maps has a semantic label.
            semantic_label = (
                map.metadata.get_semantic_label() if maptype == "raster" else None
            )
            map.load()
            if semantic_label is not None and semantic_label != "None":
                map.metadata.set_semantic_label(semantic_label)
            map.insert(dbif)
        new_sp.register_map(map, dbif)


def main():
    global check_identifier, tgis
    # Imported here, not at module level: gs.parser() answers --help and
    # --interface-description before main() runs, and these need no temporal code.
    import grass.temporal as tgis
    from grass.temporal.base import check_identifier

    # Get the options
    input = options["input"]
    output = options["output"]
    stdstype = options["type"]
    copy_maps = flags["c"]

    maptype, element = map_type_and_element(stdstype)

    # Make sure the temporal database exists
    tgis.init()

    # Get the current mapset to create the id of the space time dataset
    mapset = gs.gisenv()["MAPSET"]

    check_output_mapset(output, mapset)

    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    old_sp = tgis.open_old_stds(input, stdstype, dbif)
    old_maps = old_sp.get_registered_maps_as_objects(dbif=dbif)

    if not old_maps:
        dbif.close()
        gs.warning(
            _("Empty space-time %s dataset <%s>, nothing to copy") % (maptype, input)
        )
        return

    overwrite = gs.overwrite()

    # Check the new stds
    tgis.check_new_stds(output, stdstype, dbif, overwrite)

    if copy_maps:
        gs.message(_("Copying %s maps to the current mapset...") % maptype)
        check_maps_can_be_copied(old_maps, mapset, maptype, element, overwrite, dbif)
        new_maps = copy_maps_to_mapset(old_maps, mapset, maptype, overwrite, dbif)
    else:
        # don't copy maps, use old maps
        new_maps = old_maps

    _temporal_type, semantic_type, title, description = old_sp.get_initial_values()
    new_sp = tgis.open_new_stds(
        output,
        stdstype,
        old_sp.get_temporal_type(),
        title,
        description,
        semantic_type,
        dbif,
        gs.overwrite(),
    )

    # Register the maps in the database
    register_maps(new_sp, new_maps, mapset, maptype, dbif)

    # Update the spatio-temporal extent and the metadata table entries
    new_sp.update_from_registered_maps(dbif)

    dbif.close()


###############################################################################

if __name__ == "__main__":
    options, flags = gs.parser()
    main()
