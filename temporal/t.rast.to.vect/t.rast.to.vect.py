#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.rast.to.vect
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Converts a space time raster dataset into a space time vector dataset.
#
# SPDX-FileCopyrightText: 2015-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Converts a space time raster dataset into a space time vector dataset
# % keyword: temporal
# % keyword: conversion
# % keyword: raster
# % keyword: vector
# % keyword: time
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option G_OPT_STVDS_OUTPUT
# %end

# %option G_OPT_T_WHERE
# %end

# %option
# % key: type
# % type: string
# % description: Output feature type
# % required: yes
# % multiple: no
# % options: point,line,area
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
# % key: column
# % type: string
# % description: Name of attribute column to store value
# % required: no
# % multiple: no
# % answer: value
# %end

# %option
# % key: nprocs
# % type: integer
# % description: Number of r.to.vect processes to run in parallel, more than 1 process works only in conjunction with flag -t
# % required: no
# % multiple: no
# % answer: 1
# %end

# %flag
# % key: n
# % description: Register empty vector maps
# %end

# %flag
# % key: t
# % description: Do not create attribute tables
# %end

# %flag
# % key: s
# % description: Smooth corners of area features
# %end

# %flag
# % key: z
# % label: Write raster values as z coordinate
# % description: Table is not created. Currently supported only for points.
# %end

# %flag
# % key: b
# % label: Do not build vector topology
# % description: Name must be SQL compliant
# %end

# %flag
# % key: v
# % description: Use raster values as categories instead of unique sequence (CELL only)
# %end

import copy
import sys

import grass.script as gs
from grass.exceptions import CalledModuleError

############################################################################


def selected_maps(sp, where, dbif):
    """Return the registered maps of sp that where selects"""
    try:
        return sp.get_registered_maps_as_objects(where=where, dbif=dbif)
    except tgis.SQLStatementError as error:
        dbif.close()
        gs.fatal(_("Invalid where condition <{}>: {}").format(where, error))


def conversion_flags(flags):
    """Return the flags of r.to.vect that the flags of the tool name"""
    return "".join(letter for letter in "tsvbz" if flags[letter])


def process_count(nprocs, t_flag):
    """Return the number of parallel processes, one without -t

    Warn when it is reduced.
    """
    if t_flag is False and nprocs > 1:
        gs.warning(
            _(
                "The number of parallel r.to.vect processes was "
                "reduced to 1 because of the table attribute "
                "creation"
            )
        )
        return 1
    return nprocs


def queue_conversions(
    maps, to_vector_module, process_queue, *, sp, base, time_suffix, overwrite, dbif
):
    """Open the new map of each map of maps and queue r.to.vect for it

    Return the new maps in the order of maps.
    """
    num_maps = len(maps)
    new_maps = []

    # run r.to.vect all selected maps
    for count, map in enumerate(maps, start=1):
        new_map = tgis.open_new_map_for(
            map,
            base,
            time_suffix,
            sp.get_granularity(),
            count,
            map_type="vector",
            overwrite=overwrite,
            dbif=dbif,
        )
        new_maps.append(new_map)

        mod = copy.deepcopy(to_vector_module)
        mod(input=map.get_id(), output=new_map.get_id())
        sys.stderr.write(mod.get_bash() + "\n")
        try:
            process_queue.put(mod)
        except CalledModuleError as error:
            dbif.close()
            gs.fatal(_("Error running r.to.vect: {}").format(error))

        if count % 10 == 0:
            gs.percent(count, num_maps, 1)
    return new_maps


def wait_for_conversions(process_queue, dbif):
    """Wait for the queued processes, end with a message if one failed"""
    try:
        process_queue.wait()
    except CalledModuleError as error:
        dbif.close()
        gs.fatal(_("Error running r.to.vect: {}").format(error))


def main(options, flags):
    global pymod, tgis
    # Imported here, not at module level: gs.parser() answers --help and
    # --interface-description before main() runs, and these need no temporal code.
    import grass.pygrass.modules as pymod
    import grass.temporal as tgis

    # Get the options
    input = options["input"]
    output = options["output"]
    where = options["where"]
    base = options["basename"]
    method = options["type"]
    nprocs = int(options["nprocs"])
    column = options["column"]
    time_suffix = options["suffix"]

    register_null = flags["n"]

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
    maps = selected_maps(sp, where, dbif)

    if not maps:
        dbif.close()
        gs.warning(_("Space time raster dataset <%s> is empty") % sp.get_id())
        return

    # Check the new stvds
    tgis.check_new_stds(output, "stvds", dbif=dbif, overwrite=overwrite)

    # Configure the r.to.vect module
    to_vector_module = pymod.Module(
        "r.to.vect",
        input="dummy",
        output="dummy",
        run_=False,
        finish_=False,
        flags=conversion_flags(flags),
        type=method,
        overwrite=overwrite,
        quiet=True,
        column=column,
    )

    # The module queue for parallel execution, except if attribute tables should
    # be created. Then force single process use
    process_queue = pymod.ParallelModuleQueue(process_count(nprocs, flags["t"]))

    new_maps = queue_conversions(
        maps,
        to_vector_module,
        process_queue,
        sp=sp,
        base=base,
        time_suffix=time_suffix,
        overwrite=overwrite,
        dbif=dbif,
    )

    # Wait for unfinished processes
    wait_for_conversions(process_queue, dbif)

    # Open the new space time vector dataset
    ttype, stype, title, descr = sp.get_initial_values()
    new_sp = tgis.open_new_stds(
        output, "stvds", ttype, title, descr, stype, dbif, overwrite
    )
    empty_maps = tgis.register_new_maps(
        new_maps, new_sp, register_null=register_null, dbif=dbif
    )

    # Remove empty maps
    tgis.remove_maps(empty_maps, "vector")

    dbif.close()


############################################################################

if __name__ == "__main__":
    options, flags = gs.parser()

    main(options, flags)
