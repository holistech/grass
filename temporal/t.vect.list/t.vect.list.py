#!/usr/bin/env python3

############################################################################
#
# MODULE:	t.vect.list
# AUTHOR(S):	Soeren Gebbert
#
# PURPOSE:	List registered maps of a space time vector dataset
# SPDX-FileCopyrightText: 2011-2017 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Lists registered maps of a space time vector dataset.
# % keyword: temporal
# % keyword: map management
# % keyword: vector
# % keyword: list
# % keyword: time
# %end

# %option G_OPT_STVDS_INPUT
# %end

# %option
# % key: order
# % type: string
# % description: Sort the space time dataset by category
# % guisection: Formatting
# % required: no
# % multiple: yes
# % options: id,name,layer,creator,mapset,temporal_type,creation_time,start_time,end_time,north,south,west,east,points,lines,boundaries,centroids,faces,kernels,primitives,nodes,areas,islands,holes,volumes
# %end

# %option
# % key: columns
# % type: string
# % description: Columns to be printed to stdout
# % guisection: Selection
# % required: no
# % multiple: yes
# % options: id,name,layer,creator,mapset,temporal_type,creation_time,start_time,end_time,north,south,west,east,points,lines,boundaries,centroids,faces,kernels,primitives,nodes,areas,islands,holes,volumes,interval_length,distance_from_begin
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
# % options: cols,comma,delta,deltagaps,gran
# % answer: cols
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
    from grass.temporal.list_stds import check_list_format, check_list_method

    # Get the options
    input = options["input"]
    columns = options["columns"]
    order = options["order"]
    where = options["where"]
    separator = gs.separator(options["separator"])
    method = options["method"]
    header = flags["u"]
    output = options["output"]
    output_format = options["format"]

    # Columns that come from the database and not from the map objects the
    # methods delta, deltagaps and gran work on
    delta_excluded_columns = [
        "creator",
        "temporal_type",
        "creation_time",
        "north",
        "south",
        "west",
        "east",
        "points",
        "lines",
        "boundaries",
        "centroids",
        "faces",
        "kernels",
        "primitives",
        "nodes",
        "areas",
        "islands",
        "holes",
        "volumes",
    ]
    try:
        check_list_method(method, order, columns, delta_excluded_columns)
    except ValueError as error:
        gs.fatal(str(error))

    # The method comma is the old name of the format line
    if method == "comma" and output_format == "plain":
        output_format = "line"

    # Without columns the library chooses them: the ids for the line format and
    # the table of the manual for the delta methods. The other methods and
    # formats list the columns below.
    if (
        not columns
        and output_format != "line"
        and method
        not in {
            "delta",
            "deltagaps",
            "gran",
        }
    ):
        columns = "name,layer,mapset,start_time,end_time"

    try:
        output_format, separator = check_list_format(
            output_format, separator, method, columns, header, header_flag="u"
        )
    except ValueError as error:
        gs.fatal(str(error))

    # Make sure the temporal database exists
    tgis.init()

    tgis.list_maps_of_stds(
        "stvds",
        input,
        columns,
        order,
        where,
        separator,
        method,
        header,
        outpath=output,
        output_format=output_format,
    )


if __name__ == "__main__":
    main()
