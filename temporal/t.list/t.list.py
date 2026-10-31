#!/usr/bin/env python3

############################################################################
#
# MODULE: t.list
# AUTHOR(S): Soeren Gebbert
#
# PURPOSE: List space time datasets and maps registered in the temporal database
# SPDX-FileCopyrightText: 2011-2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Lists space time datasets and maps registered in the temporal database.
# % keyword: temporal
# % keyword: map management
# % keyword: list
# % keyword: time
# %end

# %option
# % key: type
# % type: string
# % description: Type of the space time dataset or map, default is strds
# % guisection: Selection
# % required: no
# % multiple: yes
# % options: strds, str3ds, stvds, raster, raster_3d, vector
# % answer: strds
# %end

# %option G_OPT_T_TYPE
# % multiple: yes
# % answer: absolute,relative
# % guisection: Selection
# %end

# %option
# % key: order
# % type: string
# % description: Columns number_of_maps and granularity only available for space time datasets
# % label: Sort the space time dataset by category
# % guisection: Formatting
# % required: no
# % multiple: yes
# % options: id,name,semantic_label,creator,mapset,number_of_maps,creation_time,start_time,end_time,interval,north,south,west,east,granularity
# % answer: id
# %end

# %option
# % key: columns
# % type: string
# % description: Columns number_of_maps and granularity only available for space time datasets, number_of_semantic_labels only for space time raster datasets
# % label: Columns to be printed to stdout
# % guisection: Selection
# % required: no
# % multiple: yes
# % options: id,name,type,semantic_type,semantic_label,creator,mapset,number_of_maps,number_of_semantic_labels,creation_time,start_time,end_time,north,south,west,east,granularity,all
# % answer:
# %end

# %option G_OPT_T_WHERE
# % guisection: Selection
# %end

# %option G_OPT_F_FORMAT
# % options: plain,line,json,csv
# % descriptions: plain;Plain text output;line;Comma separated list of dataset names;json;JSON (JavaScript Object Notation);csv;CSV (Comma Separated Values)
# % guisection: Formatting
# %end

# %option G_OPT_M_MAPSET
# % multiple: yes
# % description: Name of mapsets to list ('.' for current, '*' for all mapsets)
# % guisection: Selection
# %end

# %option G_OPT_F_SEP
# % answer:
# % label: Field separator character between the output columns
# % guisection: Formatting
# %end

# %option G_OPT_F_OUTPUT
# % required: no
# %end

# %flag
# % key: c
# % description: Print the column names as first row (format=csv always prints them)
# % guisection: Formatting
# %end

import json
import sys
from contextlib import nullcontext

import grass.script as gs


def output_file(outpath):
    """Return the file to write the listing to, stdout without outpath or for -"""
    return (
        open(outpath, "w") if (outpath and outpath != "-") else nullcontext(sys.stdout)
    )


def checked_format_separator(output_format, separator, colhead, stds_type, columns):
    """Check the options against the format and return the separator to use"""
    if output_format != "line":
        try:
            return checked_separator(output_format, separator, column_names=colhead)
        except ValueError as error:
            gs.fatal(str(error))

    if colhead:
        gs.fatal(_("Column names are not allowed with line format"))
    if len(stds_type) > 1:
        gs.fatal(_("Only one type is allowed for line format"))
    if not separator:
        separator = ","
    columns_list = columns.split(",") if columns else []
    if columns == "all" or len(columns_list) > 1:
        gs.fatal(_("Only one column is allowed for line format"))
    return separator


def query_types(stds_type, columns):
    """Check the types and return them and the columns to read from the database"""
    if set(stds_type) & {"raster", "raster_3d", "vector"} and set(stds_type) & {
        "strds",
        "str3ds",
        "stvds",
    }:
        gs.fatal(
            _(
                "Combinations across space time datasets and time stamped maps "
                "(e.g., raster and strds) are not allowed"
            )
        )
    if columns and "type" in columns.split(","):
        cols_list = [c.strip() for c in columns.split(",") if c.strip() != "type"]
        if not cols_list:
            gs.fatal(_("Column 'type' cannot be requested alone"))
        columns_for_db = ",".join(cols_list)
    else:
        columns_for_db = columns

    # If only one type is requested and 'type' is not in columns, pass it as a string
    # so get_dataset_list doesn't implicitly inject the 'type' column.
    if len(stds_type) == 1 and not (columns and "type" in columns.split(",")):
        stds_type = stds_type[0]
    return stds_type, columns_for_db


def list_nothing(output_format, outpath):
    """Say that no mapset has a temporal database; json lists nothing"""
    if output_format == "plain":
        gs.message(
            _(
                "No temporal database found in the requested mapset(s). No datasets to list."
            )
        )
    with output_file(outpath) as out_file:
        if output_format == "json":
            out_file.write(json.dumps([], indent=4) + "\n")


def query_datasets(dbif, stds_type, temporal_type, columns_for_db, where, order):
    """Query the datasets of each temporal type

    Returns the pairs ("absolute time" or "relative time", datasets by
    mapset). All queries run before the output file is opened, so that a
    refused where condition leaves the file as it was.
    """
    queried = []
    for ttype in temporal_type.split(","):
        time = "absolute time" if ttype == "absolute" else "relative time"
        try:
            stds_list = tgis.get_dataset_list(
                stds_type, ttype, columns_for_db, where, order, dbif=dbif
            )
        except tgis.SQLStatementError as error:
            dbif.close()
            gs.fatal(_("Invalid where condition <{}>: {}").format(where, error))
        queried.append((time, stds_list))
    return queried


def row_groups(dbif, queried, stds_type, plain):
    """Yield the rows to list, per temporal type, mapset and group

    Yields the tuple (type, "absolute time" or "relative time", mapset,
    rows). With plain the rows of a mapset are grouped by type, otherwise
    they form one group.
    """
    for time, stds_list in queried:
        for mapset in dbif.tgis_mapsets:
            rows = stds_list.get(mapset)
            if rows:
                for dtype, current_rows in type_groups(rows, stds_type, plain):
                    yield dtype, time, mapset, current_rows


def header_names(dbif, stds_type, temporal_type, columns_for_db):
    """Return the column names a listing without rows prints as header

    The names are those of the first row of a listing with rows: the
    database columns of get_dataset_list() and type last when it is listed
    per row.
    """
    # Like get_dataset_list(), which takes the columns from the views of all
    # mapsets and uses the same columns for every temporal type.
    names = tgis.list_stds.listed_columns(
        dbif,
        stds_type,
        temporal_type.split(",")[0],
        columns_for_db,
        list(dbif.tgis_mapsets),
    )
    return names if isinstance(stds_type, str) else [*names, "type"]


def type_groups(rows, stds_type, plain):
    """Return the rows of a mapset as (type, rows) pairs

    With plain one pair for each type, in the order the types first occur,
    otherwise one pair with all rows.
    """
    if plain:
        if isinstance(stds_type, str):
            return [(stds_type, rows)]
        rows_by_type = {}
        for r in rows:
            rows_by_type.setdefault(r["type"], []).append(r)
        return rows_by_type.items()
    # Process all rows together
    return [
        (
            rows[0]["type"] if not isinstance(stds_type, str) else stds_type,
            rows,
        )
    ]


def report_group(dtype, time, mapset):
    """Write the heading of a group of rows to stderr"""
    sys.stderr.write("----------------------------------------------\n")
    if dtype in {"raster", "raster_3d", "vector"}:
        sys.stderr.write(
            _("Time stamped %s maps with %s available in mapset <%s>:\n")
            % (dtype, time, mapset)
        )
    else:
        type_desc = {
            "strds": "raster",
            "stvds": "vector",
            "str3ds": "3D raster",
        }.get(dtype, dtype)
        sys.stderr.write(
            _("Space time %s datasets with %s available in mapset <%s>:\n")
            % (type_desc, time, mapset)
        )


def write_rows(out_file, rows, output_format, separator, header):
    """Write rows as plain or csv text, after the column names if header"""
    if header:
        # A database row iterates its values, not its keys, so keys() cannot
        # be dropped.
        output = separator.join(str(k) for k in rows[0].keys())  # noqa: SIM118
        out_file.write(f"{output}\n")

    for row in rows:
        output = separator.join(
            ("" if output_format == "csv" else "None") if v is None else str(v)
            for v in dict(row).values()
        )
        out_file.write(f"{output}\n")


def main():
    global tgis, checked_separator
    # Imported here, not at module level: gs.parser() answers --help and
    # --interface-description before main() runs, and these need no temporal code.
    import grass.temporal as tgis
    from grass.temporal.list_stds import checked_separator

    # Get the options
    stds_type = options["type"].split(",")
    temporal_type = options["temporaltype"]
    columns = options["columns"]
    order = options["order"]
    where = options["where"]
    separator = gs.separator(options["separator"])
    outpath = options["output"]
    colhead = flags["c"]
    output_format = options.get("format", "plain")
    mapsets = options["mapset"]

    if not columns:
        columns = "all" if output_format == "json" else "id"

    separator = checked_format_separator(
        output_format, separator, colhead, stds_type, columns
    )
    stds_type, columns_for_db = query_types(stds_type, columns)

    tgis.init(skip_db_init=True)

    dbif = tgis.SQLDatabaseInterfaceConnection(mapsets=mapsets)

    # if no connection is found
    if not dbif.tgis_mapsets:
        list_nothing(output_format, outpath)
        return

    dbif.connect()

    json_output = []
    line_output = []
    # Plain text gets the column names with -c, csv always; both only once,
    # before the first rows.
    header = colhead or output_format == "csv"
    report = (
        gs.verbosity() > 0
        and (not outpath or outpath == "-")
        and output_format == "plain"
    )

    queried = query_datasets(
        dbif, stds_type, temporal_type, columns_for_db, where, order
    )

    with output_file(outpath) as out_file:
        for dtype, time, mapset, rows in row_groups(
            dbif, queried, stds_type, output_format == "plain"
        ):
            if report:
                report_group(dtype, time, mapset)

            if output_format == "json":
                json_output.extend([dict(row) for row in rows])
            elif output_format == "line":
                line_output.extend(str(v) for row in rows for v in dict(row).values())
            else:
                write_rows(out_file, rows, output_format, separator, header)
                header = False

        # Without rows the formats with a header still print the column names.
        if header and output_format in {"plain", "csv"}:
            names = header_names(dbif, stds_type, temporal_type, columns_for_db)
            out_file.write(f"{separator.join(names)}\n")

        # Dump the collected output
        if output_format == "json":
            out_file.write(json.dumps(json_output, indent=4, default=str) + "\n")
        elif output_format == "line" and line_output:
            out_file.write(separator.join(line_output) + "\n")

    dbif.close()


if __name__ == "__main__":
    options, flags = gs.parser()

    main()
