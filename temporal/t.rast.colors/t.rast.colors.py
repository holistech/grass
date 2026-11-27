#!/usr/bin/env python3

############################################################################
#
# MODULE:	t.rast.colors
# AUTHOR(S):	Soeren Gebbert
#
# PURPOSE:  Creates/modifies the color table associated with each raster map of the space time raster dataset.
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Creates/modifies the color table associated with each raster map of the space time raster dataset.
# % keyword: temporal
# % keyword: color table
# % keyword: raster
# % keyword: time
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option G_OPT_M_COLR
# % key: color
# % type: string
# % description: Name of color table (see r.color help)
# % required: no
# % multiple: no
# % guisection: Define
# %end

# %option G_OPT_R_INPUT
# % key: raster
# % description: Raster map from which to copy color table
# % required: no
# % guisection: Define
# %end

# %option G_OPT_R3_INPUT
# % key: raster_3d
# % description: 3D raster map from which to copy color table
# % required: no
# % guisection: Define
# %end

# %option G_OPT_F_INPUT
# % key: rules
# % description: Path to rules file
# % required: no
# % guisection: Define
# %end

# %flag
# % key: r
# % description: Remove existing color table
# % guisection: Remove
# %end

# %flag
# % key: w
# % description: Only write new color table if it does not already exist
# %end

# %flag
# % key: l
# % description: List available rules then exit
# % guisection: Print
# %end

# %flag
# % key: n
# % description: Invert colors
# % guisection: Define
# %end

# %flag
# % key: g
# % description: Logarithmic scaling
# % guisection: Define
# %end

# %flag
# % key: a
# % description: Logarithmic-absolute scaling
# % guisection: Define
# %end

# %flag
# % key: e
# % description: Histogram equalization
# % guisection: Define
# %end

from pathlib import Path

import grass.script as gs
from grass.exceptions import CalledModuleError

############################################################################


def has_color_table(map_id, env):
    """Whether r.colors -w would find a color table of the raster map map_id

    Like Rast_read_colors(), this is the secondary table of the current
    mapset (colr2/<mapset>, which r.colors writes for a map of another
    mapset) or the table in the mapset of the map (colr). env is the result
    of gs.gisenv().
    """
    location = Path(env["GISDBASE"], env["LOCATION_NAME"])
    name, mapset = map_id.split("@")
    return (location / env["MAPSET"] / "colr2" / mapset / name).is_file() or (
        location / mapset / "colr" / name
    ).is_file()


def none_if_empty(value):
    """Return None for an option that was not given, else its value"""
    return None if value == "" else value


def list_rules():
    """Print the color rules of r.colors"""
    # r.colors -l lists the rules and refuses any map, so the maps of the
    # dataset are not passed.
    try:
        gs.run_command("r.colors", flags="l")
    except CalledModuleError:
        gs.fatal(_("Error in r.colors call"))


def maps_to_color(sp, write):
    """Return the rows with the ids of the maps of sp that r.colors gets"""
    rows = sp.get_registered_maps("id", None, None, None)

    if rows and write:
        # r.colors with -w stops at the first map that has a table and then
        # writes none, so the maps that have one are left out of its list.
        # The files are looked up directly, as g.findfile would be one
        # process per map.
        env = gs.gisenv()
        rows = [row for row in rows if not has_color_table(row["id"], env)]
    return rows


def run_r_colors(rows, flags_, color, raster, volume, rules):
    """Give the maps in rows their colors with one call of r.colors"""
    # Create the r.colors input file
    filename = gs.tempfile(True)
    Path(filename).write_text("\n".join(str(row["id"]) for row in rows))

    try:
        gs.run_command(
            "r.colors",
            flags=flags_,
            file=filename,
            color=color,
            raster=raster,
            volume=volume,
            rules=rules,
            overwrite=gs.overwrite(),
        )
    except CalledModuleError:
        gs.fatal(_("Error in r.colors call"))


def main():
    # lazy imports
    import grass.temporal as tgis

    # Get the options
    input = options["input"]
    color = none_if_empty(options["color"])
    raster = none_if_empty(options["raster"])
    volume = none_if_empty(options["raster_3d"])
    rules = none_if_empty(options["rules"])
    write = flags["w"]

    # Make sure the temporal database exists
    tgis.init()

    sp = tgis.open_old_stds(input, "strds")

    if flags["l"]:
        list_rules()
        return

    rows = maps_to_color(sp, write)

    if rows:
        # The flags of r.colors in the order of this tool's flags
        flags_ = "".join(key for key in "rwngae" if flags[key])
        run_r_colors(rows, flags_, color, raster, volume, rules)


if __name__ == "__main__":
    options, flags = gs.parser()
    main()
