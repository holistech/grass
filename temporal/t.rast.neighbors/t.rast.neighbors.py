#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.rast.neighbors
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Performs a neighborhood analysis for each map in a space time
#               raster dataset.
# SPDX-FileCopyrightText: 2013 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Performs a neighborhood analysis for each map in a space time raster dataset.
# % keyword: temporal
# % keyword: aggregation
# % keyword: raster
# % keyword: time
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option G_OPT_STRDS_OUTPUT
# %end

# %option G_OPT_T_WHERE
# %end

# %option
# % key: region_relation
# % type: string
# % description: Process only maps with this spatial relation to the current computational region
# % guisection: Selection
# % options: overlaps,contains,is_contained
# % required: no
# % multiple: no
# %end

# %option G_OPT_R_INPUT
# % key: selection
# % required: no
# % description: Name of an input raster map to select the cells which should be processed
# %end

# %option
# % key: size
# % type: integer
# % description: Neighborhood size
# % required: no
# % multiple: no
# % answer: 3
# %end

# %option
# % key: method
# % type: string
# % description: Aggregate operation to be performed on the raster maps
# % required: yes
# % multiple: no
# % options: average,median,mode,minimum,maximum,range,stddev,sum,count,variance,diversity,interspersion,quart1,quart3,perc90,quantile
# % answer: average
# %end

# %option
# % key: weighting_function
# % type: string
# % required: no
# % multiple: no
# % options: none,gaussian,exponential,file
# % description: Weighting function
# % descriptions: none;No weighting; gaussian;Gaussian weighting function; exponential;Exponential weighting function; file;File with a custom weighting matrix
# % answer: none
# %end

# %option
# % key: weighting_factor
# % type: double
# % required: no
# % multiple: no
# % description: Factor used in the selected weighting function (ignored for weighting_function=none and file)
# %end

# %option G_OPT_F_INPUT
# % key: weight
# % type: string
# % required: no
# % multiple: no
# % description: Text file containing weights
# %end

# %option
# % key: quantile
# % type: double
# % required: no
# % multiple: no
# % options: 0.0-1.0
# % description: Quantile to calculate for method=quantile
# % guisection: Neighborhood
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
# % key: semantic_labels
# % type: string
# % options: input,method
# % description: Set semantic labels
# % descriptions: input;copy semantic labels from input to output;method;append method name to input label if existing, otherwise use method name
# % answer: input
# % required: no
# % multiple: no
# %end

# %option
# % key: nprocs
# % type: integer
# % description: Number of r.neighbor processes to run in parallel
# % required: no
# % multiple: no
# % answer: 1
# %end

# %flag
# % key: c
# % description: Use circular neighborhood
# %end

# %flag
# % key: e
# % description: Extend existing space time raster dataset
# %end

# %flag
# % key: n
# % description: Register Null maps
# %end

# %flag
# % key: r
# % description: Ignore the current region settings and use the raster map regions
# %end

import copy

import grass.script as gs
from grass.exceptions import CalledModuleError


def selected_maps(sp, where, region_relation, dbif):
    """Return the registered maps of sp that where and the region select

    With a region_relation the maps are selected by their relation to the
    current 3D region.
    """
    spatial_extent = None
    if region_relation:
        spatial_extent = gs.parse_command("g.region", flags="3gu")

    try:
        return sp.get_registered_maps_as_objects(
            where=where,
            spatial_extent=spatial_extent,
            spatial_relation=region_relation,
            dbif=dbif,
        )
    except tgis.SQLStatementError as error:
        dbif.close()
        gs.fatal(_("Invalid where condition <{}>: {}").format(where, error))


def neighbor_module(options, quantile, flag_c, overwrite):
    """Return r.neighbors with the options of the tool, without input and output"""
    return pymod.Module(
        "r.neighbors",
        flags="c" if flag_c else "",
        input="dummy",
        output="dummy",
        run_=False,
        finish_=False,
        selection=options["selection"],
        size=int(options["size"]),
        method=options["method"],
        quantile=quantile,
        weighting_function=options["weighting_function"],
        weighting_factor=(
            float(options["weighting_factor"]) if options["weighting_factor"] else None
        ),
        weight=options["weight"],
        overwrite=overwrite,
        quiet=True,
    )


def set_semantic_label(new_map, map, new_labels, method):
    """Give new_map the semantic label that the option semantic_labels asks for

    input takes the label of map, if it has one; method appends the method to
    the label of map or, without one, is the label.
    """
    semantic_label = map.metadata.get_semantic_label()
    if new_labels == "input":
        if semantic_label is not None:
            new_map.set_semantic_label(semantic_label)
    elif new_labels == "method":
        if semantic_label is not None:
            semantic_label = f"{semantic_label}_{method}"
        else:
            semantic_label = method
        new_map.set_semantic_label(semantic_label)


def open_new_maps(maps, *, sp, base, time_suffix, new_labels, method, overwrite, dbif):
    """Open the new map of each map of maps; return them in the order of maps

    All output maps are checked before the first r.neighbors starts, so that
    an existing map stops the run before anything is written. The temporal
    database knows only registered maps; a raster of the same name outside
    it would otherwise stop only its own r.neighbors run while the others
    write their maps.
    """
    new_maps = []
    for count, map in enumerate(maps, start=1):
        new_map = tgis.open_new_map_for(
            map,
            base,
            time_suffix,
            sp.get_granularity(),
            count,
            map_type="raster",
            overwrite=overwrite,
            dbif=dbif,
        )
        if not overwrite and new_map.map_exists():
            dbif.close()
            gs.fatal(
                _(
                    "Raster map <{}> exists. To overwrite, use the --overwrite flag."
                ).format(new_map.get_id())
            )
        set_semantic_label(new_map, map, new_labels, method)
        new_maps.append(new_map)
    return new_maps


def queue_neighbors(
    maps,
    new_maps,
    r_neighbors,
    gregion_module,
    process_queue,
    *,
    use_raster_region,
    dbif,
):
    """Queue r.neighbors for each map, with g.region on its raster for -r"""
    for map, new_map in zip(maps, new_maps, strict=True):
        mod = copy.deepcopy(r_neighbors)
        mod(input=map.get_id(), output=new_map.get_id())

        try:
            if use_raster_region is True:
                reg = copy.deepcopy(gregion_module)
                reg(raster=map.get_id())
                gs.verbose(reg.get_bash())
                mm = pymod.MultiModule([reg, mod], sync=False, set_temp_region=True)
                process_queue.put(mm)
            else:
                process_queue.put(mod)
        except CalledModuleError as error:
            dbif.close()
            gs.fatal(_("Error running r.neighbors: {}").format(error))
        gs.verbose(mod.get_bash())


def wait_for_neighbors(process_queue, dbif):
    """Wait for the queued processes, end with a message if one failed"""
    try:
        process_queue.wait()
    except CalledModuleError as error:
        dbif.close()
        gs.fatal(_("Error running r.neighbors: {}").format(error))


def open_output(output, sp, *, output_exists, extend, overwrite, dbif):
    """Return the output dataset: a new one, or the existing one for -e

    An existing dataset reaches the second return only with -e, because
    check_new_stds() refuses it otherwise unless overwrite is set.
    """
    if not output_exists or (overwrite and not extend):
        # Get basic metadata
        temporal_type, semantic_type, title, description = sp.get_initial_values()

        # Create new STRDS
        return tgis.open_new_stds(
            output,
            "strds",
            temporal_type,
            title,
            description,
            semantic_type,
            dbif,
            overwrite,
        )

    # Append to existing
    return tgis.open_old_stds(output, "strds", dbif)


def main():
    # Get the options
    input = options["input"]
    output = options["output"]
    where = options["where"]
    region_relation = options["region_relation"]
    base = options["basename"]
    register_null = flags["n"]
    method = options["method"]
    nprocs = options["nprocs"]
    time_suffix = options["suffix"]
    quantile = float(options["quantile"]) if options["quantile"] else None

    if method == "quantile" and not options["quantile"]:
        gs.fatal(_("The method <quantile> requires input in the 'quantile' option."))

    try:
        tgis.check_suffix(time_suffix)
    except ValueError as error:
        gs.fatal(str(error))

    # Make sure the temporal database exists
    tgis.init()
    # We need a database interface
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    overwrite = gs.overwrite()

    sp = tgis.open_old_stds(input, "strds", dbif)
    maps = selected_maps(sp, where, region_relation, dbif)

    if not maps:
        dbif.close()
        gs.warning(_("Space time raster dataset <{}> is empty").format(sp.get_id()))
        return

    # -e appends to an existing dataset, so only the maps can clash.
    output_strds = tgis.check_new_stds(
        output, "strds", dbif=dbif, overwrite=overwrite or flags["e"]
    )
    output_exists = output_strds.is_in_db(dbif)
    # Configure the r.neighbor module
    r_neighbors = neighbor_module(options, quantile, flags["c"], overwrite)

    gregion_module = pymod.Module(
        "g.region",
        raster="dummy",
        run_=False,
        finish_=False,
    )

    # The module queue for parallel execution
    process_queue = pymod.ParallelModuleQueue(int(nprocs))

    new_maps = open_new_maps(
        maps,
        sp=sp,
        base=base,
        time_suffix=time_suffix,
        new_labels=options["semantic_labels"],
        method=method,
        overwrite=overwrite,
        dbif=dbif,
    )
    queue_neighbors(
        maps,
        new_maps,
        r_neighbors,
        gregion_module,
        process_queue,
        use_raster_region=flags["r"],
        dbif=dbif,
    )

    # Wait for unfinished processes
    wait_for_neighbors(process_queue, dbif)

    # Open the output dataset
    output_strds = open_output(
        output,
        sp,
        output_exists=output_exists,
        extend=flags["e"],
        overwrite=overwrite,
        dbif=dbif,
    )

    empty_maps = tgis.register_new_maps(new_maps, output_strds, register_null, dbif)

    if output_exists:
        output_strds.update_command_string(dbif=dbif)

    # Remove empty maps
    tgis.remove_maps(empty_maps, "raster")

    dbif.close()


############################################################################

if __name__ == "__main__":
    options, flags = gs.parser()
    # lazy imports
    import grass.pygrass.modules as pymod
    import grass.temporal as tgis

    main()
