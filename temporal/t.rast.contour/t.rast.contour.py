#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.rast.contour
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Produces a space time vector dataset of specified contours from a space time raster dataset.
# SPDX-FileCopyrightText: 2015-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Produces a space time vector dataset of specified contours from a space time raster dataset.
# % keyword: temporal
# % keyword: contour
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
# % key: step
# % type: double
# % description: Increment between contour levels
# % required: no
# % multiple: no
# %end

# %option
# % key: levels
# % type: double
# % description: List of contour levels
# % required: no
# % multiple: yes
# %end

# %option
# % key: minlevel
# % type:  double
# % description: Minimum contour level
# % required: no
# % multiple: no
# %end

# %option
# % key: maxlevel
# % type: double
# % description: Maximum contour level
# % required: no
# % multiple: no
# %end

# %option
# % key: cut
# % type: integer
# % description: Minimum number of points for a contour line (0 -> no limit)
# % required: no
# % multiple: no
# % answer: 0
# %end

# %option
# % key: nprocs
# % type: integer
# % description: Number of r.contour processes to run in parallel, more than 1 process works only in conjunction with flag -t
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

import copy
import sys

import grass.script as gs
from grass.exceptions import CalledModuleError, FatalError

############################################################################


def selected_maps(sp, where, dbif):
    """Return the registered maps of sp that where selects"""
    try:
        return sp.get_registered_maps_as_objects(where=where, dbif=dbif)
    except tgis.SQLStatementError as error:
        dbif.close()
        gs.fatal(_("Invalid where condition <{}>: {}").format(where, error))


def contour_module(options, t_flag, overwrite):
    """Return r.contour with the options of the tool, without input and output"""
    module = pymod.Module(
        "r.contour",
        input="dummy",
        output="dummy",
        run_=False,
        finish_=False,
        flags="t" if t_flag is True else "",
        overwrite=overwrite,
        quiet=True,
    )

    if options["step"]:
        module.inputs.step = float(options["step"])
    if options["minlevel"]:
        module.inputs.minlevel = float(options["minlevel"])
    if options["maxlevel"]:
        module.inputs.maxlevel = float(options["maxlevel"])
    if options["levels"]:
        module.inputs.levels = options["levels"].split(",")
    if options["cut"]:
        module.inputs.cut = int(options["cut"])
    return module


def process_count(nprocs, t_flag):
    """Return the number of parallel processes, one without -t

    Warn when it is reduced.
    """
    if t_flag is False and nprocs > 1:
        gs.warning(
            _(
                "The number of parallel r.contour processes was "
                "reduced to 1 because of the table attribute "
                "creation"
            )
        )
        return 1
    return nprocs


def queue_contours(
    maps, r_contour, process_queue, *, sp, base, time_suffix, overwrite, dbif
):
    """Open the new map of each map of maps and queue r.contour for it

    Return the new maps in the order of maps.
    """
    num_maps = len(maps)
    new_maps = []

    # run r.contour on all selected maps
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

        mod = copy.deepcopy(r_contour)
        mod(input=map.get_id(), output=new_map.get_id())
        sys.stderr.write(mod.get_bash() + "\n")
        try:
            process_queue.put(mod)
        except CalledModuleError as error:
            dbif.close()
            gs.fatal(_("Error running r.contour: {}").format(error))

        if count % 10 == 0:
            gs.percent(count, num_maps, 1)
    return new_maps


def wait_for_contours(process_queue, dbif):
    """Wait for the queued processes, end with a message if one failed"""
    try:
        process_queue.wait()
    except CalledModuleError as error:
        dbif.close()
        gs.fatal(_("Error running r.contour: {}").format(error))


def register_contours(new_maps, new_sp, register_null, dbif):
    """Register the new maps in the temporal database and in new_sp

    A map that cannot be loaded is passed over, neither registered nor
    returned. A map without primitives is not registered unless register_null
    is set. Return the empty maps that were left out; the caller removes them.
    """
    num_maps = len(new_maps)
    empty_maps = []

    for count, map in enumerate(new_maps, start=1):
        if count % 10 == 0:
            gs.percent(count, num_maps, 1)

        # Do not register empty maps
        try:
            if map.load() is not True:
                continue
        except FatalError:
            continue
        if map.metadata.get_number_of_primitives() == 0 and not register_null:
            empty_maps.append(map)
            continue

        # Insert map in temporal database
        map.insert(dbif)
        new_sp.register_map(map, dbif)

    # Update the spatio-temporal extent and the metadata table entries
    new_sp.update_from_registered_maps(dbif)
    gs.percent(1, 1, 1)
    return empty_maps


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
    nprocs = int(options["nprocs"])
    time_suffix = options["suffix"]

    register_null = flags["n"]
    t_flag = flags["t"]

    # r.contour refuses this too, but only from inside the queue, where its
    # error would surface as an exception after the output maps were opened.
    if not options["step"] and not options["levels"]:
        gs.fatal(_("Either <levels> or <step> option must be specified"))

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

    # Configure the r.contour module
    r_contour = contour_module(options, t_flag, overwrite)

    # The module queue for parallel execution, except if attribute tables should
    # be created. Then force single process use
    process_queue = pymod.ParallelModuleQueue(process_count(nprocs, t_flag))

    new_maps = queue_contours(
        maps,
        r_contour,
        process_queue,
        sp=sp,
        base=base,
        time_suffix=time_suffix,
        overwrite=overwrite,
        dbif=dbif,
    )

    # Wait for unfinished processes
    wait_for_contours(process_queue, dbif)

    # Open the new space time vector dataset
    ttype, stype, title, descr = sp.get_initial_values()
    new_sp = tgis.open_new_stds(
        output, "stvds", ttype, title, descr, stype, dbif, overwrite
    )

    empty_maps = register_contours(new_maps, new_sp, register_null, dbif)

    # Remove empty maps
    tgis.remove_maps(empty_maps, "vector")

    dbif.close()


############################################################################

if __name__ == "__main__":
    options, flags = gs.parser()

    main(options, flags)
