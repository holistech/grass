#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.vect.db.select
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Prints attributes of vector maps registered in a space time vector dataset.
# SPDX-FileCopyrightText: 2011-2017 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Prints attributes of vector maps registered in a space time vector dataset.
# % keyword: temporal
# % keyword: attribute table
# % keyword: vector
# % keyword: database
# % keyword: select
# % keyword: time
# %end

# %option G_OPT_STVDS_INPUT
# %end

# %option G_OPT_DB_COLUMNS
# %end

# %option G_OPT_F_FORMAT
# % options: plain,csv,json
# % descriptions: plain;Plain text output;csv;CSV (Comma Separated Values);json;JSON (JavaScript Object Notation)
# % answer: plain
# % guisection: Formatting
# %end

# %option G_OPT_F_SEP
# % label: Field separator character between the output columns
# % answer:
# %end

# %option G_OPT_V_FIELD
# %end

# %option G_OPT_DB_WHERE
# %end

# %option G_OPT_T_WHERE
# % key: t_where
# %end

import json
import re

import grass.script as gs
from grass.tools import ToolError, Tools

############################################################################


def _check_columns(tools, rows, layer, columns):
    """Refuse the run before the first output line if a map cannot deliver

    The maps are printed one after the other, so a map that fails in the
    middle would leave the output of the earlier maps behind. A map fails
    if it has no table in its layer or lacks one of the requested columns.
    Only plain column names are checked; "*" and SQL expressions are left
    to v.db.select, which evaluates them in the table of each map.
    The layer of each map is chosen as in the main loop: the layer of a
    registered map replaces the layer option, and keeps doing so for the
    maps after it.
    """
    wanted = []
    if columns:
        wanted = [
            name.strip()
            for name in columns.split(",")
            if re.fullmatch(r"\s*\w+\s*", name)
        ]

    without_table = []
    missing = {}
    for row in rows:
        vector_name = "%s@%s" % (row["name"], row["mapset"])
        if row["layer"]:
            layer = row["layer"]
        label = "%s (layer %s)" % (vector_name, layer)
        try:
            listing = tools.v_info(map=vector_name, layer=layer, flags="c").text
        except ToolError:
            without_table.append(label)
            continue
        # One line per column: TYPE|name. SQLite compares names without case.
        present = {
            line.split("|", 1)[-1].strip().lower() for line in listing.split("\n")
        }
        for name in wanted:
            if name.lower() not in present:
                missing.setdefault(name, []).append(label)

    if without_table:
        gs.fatal(
            _("No attribute table found for the maps: {}").format(
                ", ".join(without_table)
            )
        )
    if missing:
        # One message for all columns, so that a second run is not needed to
        # learn about the next missing one.
        gs.fatal(
            "\n".join(
                _("Column <{}> not found in the maps: {}").format(
                    name, ", ".join(labels)
                )
                for name, labels in missing.items()
            )
        )


def none_if_blank(value):
    """Return None for an option that is empty or only a blank"""
    return None if value in {"", " ", "\n"} else value


def registered_maps(input, tempwhere):
    """Return the rows of the maps of the dataset that t_where selects"""
    # Make sure the temporal database exists
    tgis.init()

    sp = tgis.open_old_stds(input, "stvds")

    try:
        return sp.get_registered_maps(
            "name,layer,mapset,start_time,end_time", tempwhere, "start_time", None
        )
    except tgis.SQLStatementError as error:
        gs.fatal(_("Invalid t_where condition <{}>: {}").format(tempwhere, error))


def append_json_records(json_output, row, res):
    """Add the records of the result res of the map in row, with its times"""
    for record in res["records"]:
        new_record = {
            "start_time": row["start_time"],
            "end_time": row["end_time"],
        }
        new_record.update(record)
        json_output.append(new_record)


def print_plain_entries(row, res, separator, col_names):
    """Print the lines of the result res of the map in row, with its times

    The first line holds the column names; they are printed again when they
    differ from those printed last, col_names. Return the names printed last.
    """
    select = res.text
    # The first line are the column names
    list = select.split("\n")
    count = 0
    for entry in list:
        if entry.strip() != "":
            # print the column names in case they change
            if count == 0:
                col_names_new = "start_time%send_time%s%s" % (
                    separator,
                    separator,
                    entry,
                )
                if col_names != col_names_new:
                    col_names = col_names_new
                    print(col_names)
            elif row["end_time"]:
                print(
                    "%s%s%s%s%s"
                    % (
                        row["start_time"],
                        separator,
                        row["end_time"],
                        separator,
                        entry,
                    )
                )
            else:
                print("%s%s%s%s" % (row["start_time"], separator, separator, entry))
            count += 1
    return col_names


def select_from_maps(tools, rows, layer, columns, separator, where, output_format):
    """Run v.db.select on the map of each row and print what it selects

    Return the records of all maps for the format json, which main prints in
    one list at the end.
    """
    json_output = []
    col_names = ""

    for row in rows:
        vector_name = "%s@%s" % (row["name"], row["mapset"])
        # In case a layer is defined in the vector dataset,
        # we override the option layer
        if row["layer"]:
            layer = row["layer"]

        try:
            res = tools.v_db_select(
                map=vector_name,
                layer=layer,
                columns=columns,
                separator=separator,
                where=where,
                format=output_format,
            )
        except ToolError as error:
            gs.fatal(
                _("Error running v.db.select on <{}>: {}").format(vector_name, error)
            )

        if output_format == "json":
            append_json_records(json_output, row, res)
        else:
            col_names = print_plain_entries(row, res, separator, col_names)
    return json_output


def main():
    global checked_separator, tgis
    # Imported here, not at module level: gs.parser() answers --help and
    # --interface-description before main() runs, and these need no temporal code.
    import grass.temporal as tgis
    from grass.temporal.list_stds import checked_separator

    # Get the options
    input = options["input"]
    where = none_if_blank(options["where"])
    columns = none_if_blank(options["columns"])
    tempwhere = options["t_where"]
    layer = options["layer"]
    separator = gs.separator(options["separator"])
    output_format = options.get("format", "plain")

    # The format json has no flag for the column names here.
    try:
        separator = checked_separator(output_format, separator, column_names=False)
    except ValueError as error:
        gs.fatal(str(error))

    rows = registered_maps(input, tempwhere)

    tools = Tools()
    json_output = []

    if not rows:
        gs.warning(
            _("No map of the space time vector dataset <{}> matches t_where.").format(
                input
            )
        )

    if rows:
        _check_columns(tools, rows, layer, columns)
        json_output = select_from_maps(
            tools, rows, layer, columns, separator, where, output_format
        )

    if output_format == "json":
        print(json.dumps(json_output, indent=4, default=str))


if __name__ == "__main__":
    options, flags = gs.parser()
    main()
