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


def main():
    # lazy imports
    import grass.temporal as tgis

    # Get the options
    input = options["input"]
    output = options["output"]
    stdstype = options["type"]
    copy_maps = flags["c"]

    maptype = "raster"
    element = "cell"
    if stdstype == "str3ds":
        maptype = "raster_3d"
        element = "grid3"
    elif stdstype == "stvds":
        maptype = "vector"
        element = "vector"

    # Make sure the temporal database exists
    tgis.init()

    # Get the current mapset to create the id of the space time dataset
    mapset = gs.gisenv()["MAPSET"]

    inname = input
    inmapset = mapset
    if "@" in input:
        inname, inmapset = input.split("@")

    outname = output
    outmapset = mapset
    if "@" in output:
        outname, outmapset = output.split("@")
        if outmapset != mapset:
            gs.fatal(
                _("The output dataset <%s> must be in the current mapset<%s>.")
                % (output, mapset)
            )

    msgr = tgis.get_tgis_message_interface()

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
    new_sp = tgis.check_new_stds(output, stdstype, dbif, overwrite)

    new_maps = None
    if copy_maps:
        gs.message(_("Copying %s maps to the current mapset...") % maptype)
        new_maps = []
        num_maps = len(old_maps)
        count = 0

        # Everything that can refuse the copy is checked before the first map
        # is copied, so that a refusal does not leave copied maps behind.
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
    else:
        # don't copy maps, use old maps
        new_maps = old_maps

    temporal_type, semantic_type, title, description = old_sp.get_initial_values()
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
    num_maps = len(new_maps)
    count = 0
    for map in new_maps:
        count += 1

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

    # Update the spatio-temporal extent and the metadata table entries
    new_sp.update_from_registered_maps(dbif)

    dbif.close()


###############################################################################

if __name__ == "__main__":
    options, flags = gs.parser()
    main()
