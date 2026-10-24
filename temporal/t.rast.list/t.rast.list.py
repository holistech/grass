#!/usr/bin/env python3

############################################################################
#
# MODULE:	t.rast.list
# AUTHOR(S):	Soeren Gebbert
#
# PURPOSE:	List registered maps of a space time raster dataset
# SPDX-FileCopyrightText: 2011-2017 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Lists registered maps of a space time raster dataset.
# % keyword: temporal
# % keyword: map management
# % keyword: raster
# % keyword: list
# % keyword: time
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option
# % key: order
# % type: string
# % description: Sort the space time dataset by category
# % guisection: Formatting
# % required: no
# % multiple: yes
# % options: id,name,semantic_label,creator,mapset,temporal_type,creation_time,start_time,end_time,north,south,west,east,nsres,ewres,cols,rows,number_of_cells,min,max
# %end

# %option
# % key: columns
# % type: string
# % description: Columns to be printed to stdout
# % guisection: Selection
# % required: no
# % multiple: yes
# % options: id,name,semantic_label,creator,mapset,temporal_type,creation_time,start_time,end_time,north,south,west,east,nsres,ewres,cols,rows,number_of_cells,min,max,interval_length,distance_from_begin
# %end

# %option G_OPT_T_WHERE
# % guisection: Selection
# %end

# %option
# % key: method
# % type: string
# % description: Method used for data listing
# % required: no
# % multiple: no
# % options: list,cols,comma,delta,deltagaps,gran
# % answer: list
# %end

# %option
# % key: granule
# % type: string
# % description: The granule to be used for listing. The granule must be specified as string eg.: absolute time "1 months" or relative time "1"
# % required: no
# % multiple: no
# %end

# %option G_OPT_F_FORMAT
# % options: plain,line,json,yaml,csv
# % descriptions: plain;Plain text output;line;Comma separated list of map names;json;JSON (JavaScript Object Notation);yaml;YAML (YAML Ain't Markup Language);csv;CSV (Comma Separated Values);
# % guisection: Formatting
# %end

# %option G_OPT_F_SEP
# % label: Field separator character between the output columns
# % answer: {NULL}
# % guisection: Formatting
# %end

# %option G_OPT_F_OUTPUT
# % required: no
# %end

# %flag
# % key: u
# % description: Suppress printing of column names
# % guisection: Formatting
# %end

import grass.script as gs


def main():
    options, flags = gs.parser()

    # lazy imports
    import grass.temporal as tgis
    from grass.temporal.list_stds import check_list_options

    # Get the options
    # Parser does not ensure that the input exists.
    input = options["input"]
    columns = options["columns"]
    order = options["order"]
    where = options["where"]
    method = options["method"]
    granule = options["granule"]
    header = flags["u"]
    output = options["output"]

    delta_excluded_columns = [
        "semantic_label",
        "creator",
        "temporal_type",
        "creation_time",
        "north",
        "south",
        "west",
        "east",
        "nsres",
        "ewres",
        "cols",
        "rows",
        "number_of_cells",
        "min",
        "max",
    ]
    try:
        output_format, separator = check_list_options(
            options,
            flags,
            header_flag="u",
            delta_excluded_columns=delta_excluded_columns,
        )
    except ValueError as error:
        gs.fatal(str(error))

    # Make sure the temporal database exists
    tgis.init()

    tgis.list_maps_of_stds(
        "strds",
        input,
        columns,
        order,
        where,
        separator,
        method,
        header,
        granule,
        outpath=output,
        output_format=output_format,
    )


if __name__ == "__main__":
    main()
