#!/usr/bin/env python3

############################################################################
#
# MODULE:    t.rast.univar
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:    Calculates univariate statistics from the non-null cells for each registered raster map of a space time raster dataset
# SPDX-FileCopyrightText: 2011-2017 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Calculates univariate statistics from the non-null cells for each registered raster map of a space time raster dataset.
# % keyword: temporal
# % keyword: statistics
# % keyword: raster
# % keyword: time
# % keyword: parallel
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option G_OPT_R_INPUT
# % key: zones
# % description: Raster map used for zoning, must be of type CELL
# % required: no
# %end

# %option G_OPT_M_NPROCS
# % required: no
# %end

# %option G_OPT_F_OUTPUT
# % required: no
# %end

# %option
# % key: percentile
# % type: double
# % required: no
# % multiple: yes
# % options: 0-100
# % description: Percentile to calculate (requires extended statistics flag)
# %end

# %option G_OPT_T_WHERE
# % guisection: Selection
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

# %option
# % key: granularity
# % type: string
# % description: Compute the statistics of the maps of each granule together instead of each map: for absolute time one number and one unit, such as "3 months" (years, months, weeks, days, hours, minutes, seconds); for relative time an integer in the unit of the dataset
# % required: no
# % multiple: no
# % guisection: Granularity
# %end

# The standard option answers "start", which is no relation of a granule and
# would reach the library in every run. The empty answer leaves sampling unset
# unless it is given; without it the library takes contains.
# %option G_OPT_T_SAMPLE
# % options: equal,overlaps,overlapped,starts,started,finishes,finished,during,contains,related
# % answer:
# % description: Relation of a granule to the maps it takes, contains if not given; related takes all maps that share time with the granule
# % guisection: Granularity
# %end

# %option G_OPT_F_SEP
# % label: Field separator character between the output columns
# % answer:
# % guisection: Formatting
# %end

# %option G_OPT_F_FORMAT
# % options: plain,json,csv
# % descriptions: plain;Plain text output;json;JSON (JavaScript Object Notation);csv;CSV (Comma Separated Values)
# % guisection: Formatting
# %end

# %flag
# % key: e
# % description: Calculate extended statistics
# %end

# %flag
# % key: r
# % description: Use the raster map regions for univar statistical calculation instead of the current region
# %end

# %flag
# % key: u
# % description: Suppress printing of column names
# % guisection: Formatting
# %end

# %rules
# % requires: percentile,-e
# % requires: sampling,granularity
# %end

import grass.script as gs

############################################################################


def main():
    # Get the options and flags
    options, flags = gs.parser()

    # Define variables
    input = options["input"]
    zones = options["zones"]
    output = options["output"]
    nprocs = gs.resolve_nprocs(options["nprocs"])
    where = options["where"]
    region_relation = options["region_relation"]
    granularity = options["granularity"] or None
    sampling = options["sampling"].split(",") if options["sampling"] else None
    extended = flags["e"]
    no_header = flags["u"]
    rast_region = bool(flags["r"])
    separator = gs.separator(options["separator"])
    output_format = options.get("format", "plain")

    # lazy imports
    import grass.temporal as tgis
    from grass.temporal.list_stds import checked_separator

    try:
        separator = checked_separator(output_format, separator, column_names=no_header)
    except ValueError as error:
        gs.fatal(str(error))

    percentile = None
    if options["percentile"]:
        # The parser has checked that every value is a number from 0 to 100.
        percentile = list(map(float, options["percentile"].split(",")))
    # Make sure the temporal database exists
    tgis.init()

    if not output or output == "-":
        output = None

    # Check if zones map exists and is of type CELL
    if zones and gs.raster.raster_info(zones)["datatype"] != "CELL":
        gs.fatal(_("Zoning raster must be of type CELL"))

    tgis.print_gridded_dataset_univar_statistics(
        "strds",
        input,
        output,
        where,
        extended,
        percentile=percentile,
        no_header=no_header,
        fs=separator,
        zones=zones,
        rast_region=rast_region,
        region_relation=region_relation,
        nprocs=nprocs,
        format=output_format,
        granularity=granularity,
        sampling=sampling,
    )


if __name__ == "__main__":
    main()
