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


def message_option_value_excludes_option_value(
    option_name, option_value, excluded_option_name, excluded_option_value, reason
):
    return _(
        "Combining {option_name}={option_value} and "
        "{excluded_option_name}={excluded_option_value} is not allowed. {reason}"
    ).format(
        option_name=option_name,
        option_value=option_value,
        excluded_option_name=excluded_option_name,
        excluded_option_value=excluded_option_value,
        reason=reason,
    )


def message_option_value_excludes_option(
    option_name, option_value, excluded_option_name, reason
):
    return _(
        "The option {excluded_option_name} is not allowed with "
        "{option_name}={option_value}. {reason}"
    ).format(
        excluded_option_name=excluded_option_name,
        option_name=option_name,
        option_value=option_value,
        reason=reason,
    )


def message_option_value_excludes_flag(option_name, option_value, flag_name, reason):
    return _(
        "The flag -{flag_name} is not allowed with {option_name}={option_value}."
        " {reason}"
    ).format(
        flag_name=flag_name,
        option_name=option_name,
        option_value=option_value,
        reason=reason,
    )


############################################################################


def main():
    options, flags = gs.parser()
    # lazy imports
    import grass.temporal as tgis

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

    if method in {"delta", "deltagaps", "gran"}:
        if order:
            gs.fatal(
                message_option_value_excludes_option(
                    option_name="method",
                    option_value=method,
                    excluded_option_name="order",
                    reason=_("Values are always ordered by start_time"),
                )
            )
        # Columns that come from the database and not from the map objects
        # the method works on
        for column in [
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
        ]:
            if column in columns.split(","):
                gs.fatal(
                    message_option_value_excludes_option_value(
                        option_name="method",
                        option_value=method,
                        excluded_option_name="columns",
                        excluded_option_value=columns,
                        reason=_(
                            "Column '{name}' is not available with the method "
                            "'{method}'"
                        ).format(name=column, method=method),
                    )
                )
    else:
        for column in ["interval_length", "distance_from_begin"]:
            if column in columns.split(","):
                gs.fatal(
                    message_option_value_excludes_option_value(
                        option_name="method",
                        option_value=method,
                        excluded_option_name="columns",
                        excluded_option_value=columns,
                        reason=_(
                            "Column '{name}' is not available with the method "
                            "'{method}'"
                        ).format(name=column, method=method),
                    )
                )

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

    if output_format == "csv":
        if not separator:
            separator = ","
        elif len(separator) > 1:
            gs.fatal(
                message_option_value_excludes_option_value(
                    option_name="format",
                    option_value=output_format,
                    excluded_option_name="separator",
                    excluded_option_value=separator,
                    reason=_(
                        "A standard CSV separator (delimiter) is only one character "
                        "long"
                    ),
                )
            )

    elif output_format in {"json", "yaml"}:
        if header:
            gs.fatal(
                message_option_value_excludes_flag(
                    option_name="format",
                    option_value=output_format,
                    flag_name="u",
                    reason=_("Column names are always included"),
                )
            )
        if separator:
            gs.fatal(
                message_option_value_excludes_option_value(
                    option_name="format",
                    option_value=output_format,
                    excluded_option_name="separator",
                    excluded_option_value=separator,
                    reason=_("Separator is part of the format"),
                )
            )

    elif output_format == "line":
        if not separator:
            separator = ","
        columns_list = columns.split(",")
        if len(columns_list) > 1:
            gs.fatal(
                message_option_value_excludes_option_value(
                    option_name="format",
                    option_value=output_format,
                    excluded_option_name="columns",
                    excluded_option_value=columns,
                    reason=_("Only one column is allowed (not {num_columns})").format(
                        num_columns=len(columns_list)
                    ),
                )
            )
    elif not separator:  # output_format = "plain"
        separator = "|"

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
