#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.rast.to.rast3
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Convert a space time raster dataset into a 3D raster map
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Converts a space time raster dataset into a 3D raster map.
# % keyword: temporal
# % keyword: conversion
# % keyword: raster
# % keyword: raster3d
# % keyword: voxel
# % keyword: time
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option G_OPT_R3_OUTPUT
# %end
import os
from datetime import datetime

import grass.script as gs
from grass.exceptions import CalledModuleError

############################################################################


def cube_geometry(sp):
    """Return the unit, the bottom and the resolution of the cube of sp

    The bottom is the start of sp in relation to 1900-01-01: years and months
    count from 1900 (the year number, the month number); for days, hours,
    minutes and seconds the bottom is the number of days since 1900-01-01 as a
    decimal number and the resolution is the granularity converted to days.
    The returned unit is always that of the granularity of sp, also for hours,
    minutes and seconds, whose bottom and resolution are counted in days. A
    cube of monthly or yearly granularity cannot be mixed with the other
    units. In relative time the start, the granularity and the unit of sp are
    taken as they are.
    """
    granularity = sp.get_granularity()
    start, _end = sp.get_temporal_extent_as_tuple()

    if not sp.is_time_absolute():
        return sp.get_relative_time_unit(), start, granularity

    unit = granularity.split(" ")[1]
    granularity = float(granularity.split(" ")[0])

    gs.verbose(_("Gran from stds %0.15f") % (granularity))

    if unit in {"years", "year"}:
        return unit, float(start.year - 1900), granularity
    if unit in {"months", "month"}:
        return unit, float((start.year - 1900) * 12 + start.month), granularity

    bottom = float(tgis.time_delta_to_relative_time(start - datetime(1900, 1, 1)))
    days = 0.0
    hours = 0.0
    minutes = 0.0
    seconds = 0.0
    if unit in {"days", "day"}:
        days = float(granularity)
    if unit in {"hours", "hour"}:
        hours = float(granularity)
    if unit in {"minutes", "minute"}:
        minutes = float(granularity)
    if unit in {"seconds", "second"}:
        seconds = float(granularity)

    granularity = float(days + hours / 24.0 + minutes / 1440.0 + seconds / 86400.0)
    return unit, bottom, granularity


def set_cube_region(bottom, top, granularity):
    """Set the temporary 3D region to the extent and resolution of the cube"""
    try:
        gs.run_command("g.region", t=top, b=bottom, tbres=granularity)
    except CalledModuleError:
        gs.fatal(_("Unable to set 3D region"))


def make_null_map(datatype):
    """Make the map of null cells that fills the gaps; return its name

    The map has the data type of the first map of the dataset.
    """
    null_map = "temporary_null_map_%i" % os.getpid()
    if datatype == "DCELL":
        gs.mapcalc("%s = double(null())" % (null_map))
    elif datatype == "FCELL":
        gs.mapcalc("%s = float(null())" % (null_map))
    else:
        gs.mapcalc("%s = null()" % (null_map))
    return null_map


def make_cube(maps, null_map, output):
    """Put the first map of each step on top of each other in the 3D map output

    A step without a map gets null_map.
    """
    ids = []
    for map in maps:
        # Use the first map
        id = map[0].get_id()
        # None ids will be replaced by NULL maps
        if id is None:
            id = null_map
        ids.append(id)

    try:
        gs.run_command(
            "r.to.rast3",
            input=",".join(ids),
            output=output,
            overwrite=gs.overwrite(),
        )
    except CalledModuleError:
        gs.fatal(_("Unable to create 3D raster map <%s>") % output)


def set_cube_unit(output, unit):
    """Give the 3D map its vertical unit, a title and a description"""
    title = _("Space time voxel cube")
    descr = _("This space time voxel cube was created with t.rast.to.rast3")

    try:
        gs.run_command(
            "r3.support",
            map=output,
            vunit=unit,
            title=title,
            description=descr,
            overwrite=gs.overwrite(),
        )
    except CalledModuleError:
        gs.warning(_("%s failed to set units.") % "r3.support")


def register_cube(sp, output, mapset):
    """Register the 3D map in the temporal database with the extent of sp

    An entry of the same name is replaced.
    """
    id = output if output.find("@") >= 0 else output + "@" + mapset

    start, end = sp.get_temporal_extent_as_tuple()
    r3ds = tgis.Raster3DDataset(id)

    if r3ds.is_in_db():
        r3ds.select()
        r3ds.delete()
        r3ds = tgis.Raster3DDataset(id)

    r3ds.load()

    if sp.is_time_absolute():
        r3ds.set_absolute_time(start, end)
    else:
        r3ds.set_relative_time(start, end, sp.get_relative_time_unit())

    r3ds.insert()


def main():
    # Get the options
    input = options["input"]
    output = options["output"]

    # Make sure the temporal database exists
    tgis.init()

    mapset = gs.gisenv()["MAPSET"]

    sp = tgis.open_old_stds(input, "strds")

    # Checked before the granularity is used, which an empty dataset lacks.
    if not sp.metadata.get_number_of_maps():
        gs.fatal(_("Space time raster dataset <{}> is empty").format(sp.get_id()))

    gs.use_temp_region()

    maps = sp.get_registered_maps_as_objects_by_granularity()

    num_maps = len(maps)
    # get datatype of the first map
    maps[0][0].select()
    datatype = maps[0][0].metadata.get_datatype()

    unit, bottom, granularity = cube_geometry(sp)
    top = float(bottom + granularity * float(num_maps))
    set_cube_region(bottom, top, granularity)

    null_map = make_null_map(datatype)
    try:
        make_cube(maps, null_map, output)
    finally:
        gs.run_command("g.remove", flags="f", type="raster", name=null_map)

    set_cube_unit(output, unit)
    register_cube(sp, output, mapset)


if __name__ == "__main__":
    options, flags = gs.parser()
    # lazy import
    import grass.temporal as tgis

    main()
