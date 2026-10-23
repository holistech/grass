#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.vect.what.strds
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Store raster map values at spatial and temporal positions of vector points as vector attributes.
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Stores raster map values at spatial and temporal positions of vector points as vector attributes.
# % keyword: temporal
# % keyword: sampling
# % keyword: vector
# % keyword: time
# %end

# %option G_OPT_STVDS_INPUT
# %end

# %option G_OPT_STRDS_INPUT
# % key: strds
# %end

# %option
# % key: column
# % type: string
# % label: Name of the vector column to be created and to store sampled raster values
# % description: The use of a column name forces t.vect.what.rast to sample only values from the first map found in an interval. Without it, the raster map names are used as column names, and the aggregate of an interval is stored in a column named <strds>_<method>
# % required: no
# % multiple: no
# %end

# %option
# % key: method
# % type: string
# % description: Aggregate operation to be performed on the raster maps
# % required: yes
# % multiple: no
# % options: disabled,average,count,median,mode,minimum,min_raster,maximum,max_raster,stddev,range,sum,variance,diversity,slope,offset,detcoeff,quart1,quart3,perc90,quantile,skewness,kurtosis
# % answer: disabled
# %end

# %option G_OPT_DB_WHERE
# %end

# %option G_OPT_T_WHERE
# % key: t_where
# %end

# %option G_OPT_T_SAMPLE
# %end

import os
import re

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.script import raster

############################################################################


def aggregate_column_name(strds_name, method):
    """Return the column that stores the aggregate of a dataset

    Characters outside [A-Za-z0-9_] become underscores. v.db.addcolumn quotes
    a name that starts with a digit, but v.what.rast does not and then fails
    with "unrecognized token" (probe 23.10.2026 with SQLite), so such a name
    gets the prefix c_.
    """
    name = re.sub(r"[^A-Za-z0-9_]", "_", f"{strds_name}_{method}")
    return f"c_{name}" if name[0].isdigit() else name


def sampled_column_names(raster_maps, column, aggregated, method, strds_name):
    """Return the columns the tool writes for the raster maps of one interval

    The check before the first write and the write loop both take the names
    from here, so that the check sees the columns that are written.
    """
    if column:
        return [column]
    if aggregated:
        return [aggregate_column_name(strds_name, method)]
    return [name.split("@")[0].replace(".", "_") for name in raster_maps]


def check_target_columns(targets, overwrite, dbif):
    """Refuse missing tables and existing columns before anything is written

    targets maps (vector map, layer) to the column names to write. A map of
    another mapset and a layer without a table are always an error: the
    column can be added and written in the current mapset only, and only to
    a table.
    Names are compared in lower case, as SQLite does, so that "M" is taken to
    be "m". Without overwrite an existing column is an error; with it the
    column is written again and keeps its type. Returns the existing columns
    of each (map, layer).
    """
    existing = {}
    errors = []
    clashes = []
    mapset = gs.gisenv()["MAPSET"]
    for (vectmap, layer), names in targets.items():
        if vectmap.split("@")[1] != mapset:
            errors.append(
                _(
                    "Vector map <{vector}> is not in the current mapset, so its "
                    "table cannot be written"
                ).format(vector=vectmap)
            )
            continue
        if not gs.vector_db(vectmap).get(layer):
            errors.append(
                _(
                    "Vector map <{vector}> has no attribute table in layer {layer}"
                ).format(vector=vectmap, layer=layer)
            )
            continue
        present = {name.lower() for name in gs.vector_columns(vectmap, layer)}
        existing[vectmap, layer] = present
        clashes.extend(
            _(
                "Column <{column}> exists in the table of vector map "
                "<{vector}> layer {layer}"
            ).format(column=name, vector=vectmap, layer=layer)
            for name in sorted(names)
            if name.lower() in present
        )
    if clashes and not overwrite:
        errors.extend(clashes)
        errors.append(_("Use the overwrite flag to write the values again."))
    if errors:
        dbif.close()
        gs.fatal("\n".join(errors))
    return existing


def main():
    # lazy imports
    import grass.temporal as tgis

    # Get the options
    input = options["input"]
    strds = options["strds"]
    where = options["where"]
    column = options["column"]
    method = options["method"]
    tempwhere = options["t_where"]
    sampling = options["sampling"]

    if where in {"", " ", "\n"}:
        where = None

    # Make sure the temporal database exists
    tgis.init()
    # We need a database interface
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    sp = tgis.open_old_stds(input, "stvds", dbif)
    strds_sp = tgis.open_old_stds(strds, "strds", dbif)

    if strds_sp.get_temporal_type() != sp.get_temporal_type():
        dbif.close()
        gs.fatal(_("Input and aggregation dataset must have the same temporal type"))

    # An empty dataset has no map time either; say that it is empty
    if not sp.get_registered_maps("id", None, None, dbif):
        dbif.close()
        gs.fatal(_("Space time vector dataset <%s> is empty") % sp.get_id())

    # Check if intervals are present in the sample dataset
    if sp.get_temporal_type() == "absolute":
        map_time = sp.absolute_time.get_map_time()
    else:
        map_time = sp.relative_time.get_map_time()

    if map_time != "interval":
        dbif.close()
        gs.fatal(
            _(
                "All registered maps of the space time vector "
                "dataset must have time intervals"
            )
        )

    try:
        rows = sp.get_registered_maps(
            "name,layer,mapset,start_time,end_time", tempwhere, "start_time", dbif
        )
    except tgis.SQLStatementError as error:
        dbif.close()
        gs.fatal(_("Invalid t_where condition <{}>: {}").format(tempwhere, error))

    if not rows:
        dbif.close()
        gs.fatal(_("Space time vector dataset <%s> is empty") % sp.get_id())

    # v.what.rast only reports an error in the where condition and the run
    # ends with status 0 and empty values, so the condition is tried on the
    # table of each layer first. The layers are taken in the order of the
    # dataset: a set would name any of several failing tables, differing from
    # run to run with the hash seed of the interpreter.
    if where:
        for vectmap, layer in dict.fromkeys(
            (f"{row['name']}@{row['mapset']}", int(row["layer"] or 1)) for row in rows
        ):
            connection = gs.vector_db(vectmap).get(layer)
            if not connection:
                continue
            try:
                gs.read_command(
                    "db.select",
                    # The key column, as the table need not have one named cat
                    sql="SELECT {} FROM {} WHERE {}".format(
                        connection["key"], connection["table"], where
                    ),
                    driver=connection["driver"],
                    database=connection["database"],
                )
            except CalledModuleError:
                dbif.close()
                gs.fatal(
                    _("Invalid where condition <{}> for vector map <{}>").format(
                        where, vectmap
                    )
                )

    # All target columns are checked before the first one is written: a
    # refusal found at the second map would leave the first one changed. An
    # aggregate column is checked too, although an aggregate without any
    # value is skipped later: whether it is empty is known only after
    # r.series has run, which is after the first write.
    targets = {}
    # Which id wrote a column first. The ids c and c:1 name the same layer,
    # so they share a key in targets and only this tells them apart.
    column_owners = {}
    interval_maps = []
    for row in rows:
        raster_maps = tgis.collect_map_names(
            strds_sp, dbif, row["start_time"], row["end_time"], sampling
        )
        interval_maps.append(raster_maps)
        if raster_maps:
            key = (f"{row['name']}@{row['mapset']}", int(row["layer"] or 1))
            names = sampled_column_names(
                raster_maps,
                column,
                method != "disabled" and len(raster_maps) > 1,
                method,
                strds_sp.get_name(),
            )
            targets.setdefault(key, set()).update(names)
            # The second write would replace the first one without a word.
            map_id = row["name"] + (f":{row['layer']}" if row["layer"] else "")
            map_id += "@" + row["mapset"]
            for name in names:
                owner = column_owners.setdefault((key, name.lower()), map_id)
                if owner != map_id:
                    dbif.close()
                    gs.fatal(
                        _(
                            "Vector maps <{first}> and <{second}> are the same "
                            "layer of one map and would both write column "
                            "<{column}>"
                        ).format(first=owner, second=map_id, column=name)
                    )
    existing = check_target_columns(targets, gs.overwrite(), dbif)

    # Sample the raster dataset with the vector dataset and run v.what.rast
    for row, raster_maps in zip(rows, interval_maps, strict=True):
        start = row["start_time"]
        end = row["end_time"]
        vectmap = row["name"] + "@" + row["mapset"]
        layer = int(row["layer"] or 1)

        aggreagated_map_name = None

        if raster_maps:
            # Aggregation
            if method != "disabled" and len(raster_maps) > 1:
                # Generate the temporary map name
                aggreagated_map_name = "aggreagated_map_name_" + str(os.getpid())
                new_map = tgis.aggregate_raster_maps(
                    raster_maps,
                    aggreagated_map_name,
                    start,
                    end,
                    0,
                    method,
                    False,
                    dbif,
                )
                aggreagated_map_name += "_0"
                if new_map is None:
                    continue
                # We overwrite the raster_maps list
                raster_maps = (new_map.get_id(),)

            for rastermap in raster_maps:
                # Create a new column with the SQL compliant
                # name of the sampled raster map if not column
                (col_name,) = sampled_column_names(
                    [rastermap],
                    column,
                    aggreagated_map_name is not None,
                    method,
                    strds_sp.get_name(),
                )

                coltype = "DOUBLE PRECISION"
                # Get raster type
                rasterinfo = raster.raster_info(rastermap)
                if rasterinfo["datatype"] == "CELL":
                    coltype = "INT"

                # A column that exists was accepted by the check above and
                # is written again; adding it would only report an error.
                if col_name.lower() not in existing[vectmap, layer]:
                    try:
                        gs.run_command(
                            "v.db.addcolumn",
                            map=vectmap,
                            layer=layer,
                            column="%s %s" % (col_name, coltype),
                        )
                    except CalledModuleError:
                        dbif.close()
                        gs.fatal(
                            _(
                                "Unable to add column {column} to vector map <{vector}>"
                            ).format(column=col_name, vector=vectmap)
                        )
                    existing[vectmap, layer].add(col_name.lower())

                # Call v.what.rast
                try:
                    gs.run_command(
                        "v.what.rast",
                        map=vectmap,
                        layer=layer,
                        raster=rastermap,
                        column=col_name,
                        where=where,
                    )
                except CalledModuleError:
                    dbif.close()
                    gs.fatal(
                        _(
                            "Unable to run v.what.rast for vector map "
                            "<%s> and raster map <%s>"
                        )
                        % (vectmap, rastermap)
                    )

                if aggreagated_map_name:
                    try:
                        gs.run_command(
                            "g.remove",
                            flags="f",
                            type="raster",
                            name=aggreagated_map_name,
                        )
                    except CalledModuleError:
                        dbif.close()
                        gs.fatal(
                            _("Unable to remove raster map <%s>")
                            % (aggreagated_map_name)
                        )

                # Use the first map in case a column names was provided
                if column:
                    break

    dbif.close()


if __name__ == "__main__":
    options, flags = gs.parser()
    main()
