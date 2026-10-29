#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.vect.observe.strds
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Observe specific locations in a space time raster dataset over a period of time using vector points
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Observes specific locations in a space time raster dataset over a period of time using vector points.
# % keyword: temporal
# % keyword: sampling
# % keyword: vector
# % keyword: time
# %end

# %option G_OPT_V_INPUT
# %end

# %option G_OPT_STRDS_INPUTS
# % key: strds
# %end

# %option G_OPT_STVDS_OUTPUT
# %end

# %option G_OPT_V_OUTPUT
# % key: vector_output
# % description: Name of the new created vector map that stores the sampled values in different layers
# %end

# %option
# % key: columns
# % type: string
# % description: Names of the vector columns to be created and to store sampled raster values, one name for each STRDS
# % required: yes
# % multiple: yes
# %end

# %option G_OPT_DB_WHERE
# %end

import atexit
import os

import grass.script as gs
from grass.exceptions import CalledModuleError

# lazy imports at the end of the file


class Sample:
    def __init__(self, start, end, raster_names):
        self.start = start
        self.end = end
        self.raster_names = raster_names


def check_input(input, where):
    """Check the input map and whether where can select its points

    Nothing is written. Returns the database connections of the input.
    """
    if not gs.find_file(input, element="vector")["file"]:
        gs.fatal(_("Vector map <%s> not found") % input)

    input_db = gs.vector.vector_db(input)
    if where:
        # v.extract copies layer 1 only: the other layers of the input would
        # be missing in the output without a word. A layer may have
        # categories without a table or a table without categories, so both
        # are asked.
        with_categories = gs.read_command(
            "v.category", input=input, option="layers"
        ).split()
        other_layers = sorted(
            {int(layer) for layer in with_categories}.union(input_db) - {1}
        )
        if other_layers:
            gs.fatal(
                _(
                    "The where option cannot be used with vector map <{vector}>: "
                    "it has the layers {layers} besides layer 1 and the selection "
                    "would drop them"
                ).format(
                    vector=input, layers=", ".join(str(layer) for layer in other_layers)
                )
            )
    return input_db


def single_samples(first_strds, dbif):
    """Return a sample for each map of one space time raster dataset"""
    rows = first_strds.get_registered_maps(
        columns="name,mapset,start_time,end_time", order="start_time", dbif=dbif
    )

    if not rows:
        dbif.close()
        gs.fatal(_("Space time raster dataset <%s> is empty") % first_strds.get_id())

    samples = []
    for row in rows:
        start = row["start_time"]
        end = row["end_time"]
        raster_maps = [
            row["name"] + "@" + row["mapset"],
        ]

        s = Sample(start, end, raster_maps)
        samples.append(s)
    return samples


def granule_samples(strds_names, first_strds, dbif):
    """Return a sample for each granule of the first dataset that all datasets have

    The granules are the maps of the first dataset; one in which a dataset
    has no map is left out. All datasets must have the temporal type of the
    first one.
    """
    for name in strds_names[1:]:
        dataset = tgis.open_old_stds(name, "strds", dbif)
        if dataset.get_temporal_type() != first_strds.get_temporal_type():
            gs.fatal(
                _(
                    "Temporal type of space time raster datasets must be equal\n"
                    "<%(a)s> of type %(type_a)s do not match <%(b)s> of type "
                    "%(type_b)s"
                )
                % {
                    "a": first_strds.get_id(),
                    "type_a": first_strds.get_temporal_type(),
                    "b": dataset.get_id(),
                    "type_b": dataset.get_temporal_type(),
                }
            )

    mapmatrizes = tgis.sample_stds_by_stds_topology(
        "strds",
        "strds",
        strds_names,
        strds_names[0],
        False,
        None,
        "equal",
        False,
        False,
    )

    samples = []
    for i in range(len(mapmatrizes[0])):
        isvalid = True
        mapname_list = []
        for mapmatrix in mapmatrizes:
            entry = mapmatrix[i]

            if entry["samples"]:
                sample = entry["samples"][0]
                name = sample.get_id()
                if name is None:
                    isvalid = False
                    break
                mapname_list.append(name)

        if isvalid:
            entry = mapmatrizes[0][i]
            map = entry["granule"]

            start, end = map.get_temporal_extent_as_tuple()
            s = Sample(start, end, mapname_list)
            samples.append(s)
    return samples


def select_points(input, where, dbif):
    """Return the map whose points are observed: input, or those where selects

    With where the selected points are copied into a helper map, which is
    removed at the end of the run.
    """
    if not where:
        return input
    # where selects points of the input: the other points are not in the
    # output at all. Applying it in the new layers would fail, as they have
    # no column of the input table.
    selected = "tmp_t_vect_observe_strds_%d" % os.getpid()
    try:
        gs.run_command(
            "v.extract", input=input, where=where, output=selected, quiet=True
        )
    except CalledModuleError:
        dbif.close()
        gs.fatal(_("Unable to select the points of <%s> with where") % input)
    atexit.register(
        gs.run_command,
        "g.remove",
        flags="f",
        type="vector",
        name=selected,
        quiet=True,
    )
    return selected


def check_column_cases(points, vector_db, num_samples, column_names, input, dbif):
    """Refuse a column that differs only in case from a column of a table

    Only the layers that are observed and have a table in vector_db count,
    the others get a new table. This is checked before vectmap is made: the
    column check of add_columns() takes K for k, as SQLite does, and lets it
    pass with overwrite, but v.what.rast looks for K as written and then
    fails to add it. points is the map vector_db was read from; input names
    the map in the message.
    """
    for layer in range(1, num_samples + 1):
        if not (layer in vector_db and vector_db[layer]["table"]):
            continue
        stored = list(gs.vector_columns(points, layer=layer))
        stored_by_lower = {name.lower(): name for name in stored}
        for column in column_names:
            if column.lower() in stored_by_lower and column not in stored:
                dbif.close()
                gs.fatal(
                    _(
                        "Column <{column}> differs only in case from the column "
                        "<{stored}> of the table of vector map <{vector}> "
                        "layer {layer}"
                    ).format(
                        column=column,
                        stored=stored_by_lower[column.lower()],
                        vector=input,
                        layer=layer,
                    )
                )


def copy_with_layers(points, vector_db, num_samples, vectmap, overwrite):
    """Create vectmap from points with a layer for each sample

    v.category copies the categories of the first listed layer to the
    others. vector_db holds the connections of points: if there are any,
    layer 1 is listed first, and the layers that have a connection are left
    out of the rest of the list.
    """
    layers = "1," if vector_db else ""
    first = True
    for layer in range(num_samples):
        layer += 1
        # Skip existing layer
        if vector_db and layer in vector_db and vector_db[layer]["layer"] == layer:
            continue
        if first:
            layers += "%i" % (layer)
            first = False
        else:
            layers += ",%i" % (layer)

    # We create a new vector map using the categories of the original map
    try:
        gs.run_command(
            "v.category",
            input=points,
            layer=layers,
            output=vectmap,
            option="transfer",
            overwrite=overwrite,
        )
    except CalledModuleError:
        gs.fatal(_("Unable to create new layers for vector map <%s>") % (vectmap))


def name_layer_one(vectmap, layer_one):
    """Connect layer 1 of vectmap again under the layer name of the input

    layer_one is the connection of layer 1 of the input. If that fails,
    vectmap is removed.
    """
    # v.extract names layer 1 after the helper map, which is removed at the
    # end of the run. Without where the output has the layer name of the
    # input, so the layer is connected again under that name.
    copied = gs.vector.vector_db(vectmap)[1]
    try:
        gs.run_command(
            "v.db.connect",
            map=vectmap,
            layer="1/%s" % layer_one["name"] if layer_one["name"] else "1",
            table=copied["table"],
            key=copied["key"],
            database=copied["database"],
            driver=copied["driver"],
            overwrite=True,
            quiet=True,
        )
    except CalledModuleError:
        gs.run_command("g.remove", flags="f", type="vector", name=vectmap, quiet=True)
        gs.fatal(_("Unable to name layer 1 of vector map <%s>") % (vectmap))


def column_definitions(raster_names, column_names):
    """Return the definition of each column, INT for a CELL raster map

    The other raster maps give DOUBLE PRECISION columns.
    """
    column_defs = {}
    for name, column in zip(raster_names, column_names, strict=False):
        # The column is by default double precision
        coltype = "DOUBLE PRECISION"
        # Get raster map type
        raster_map = tgis.RasterDataset(name)
        raster_map.load()
        if raster_map.metadata.get_datatype() == "CELL":
            coltype = "INT"

        column_defs[column] = "%s %s" % (column, coltype)
    return column_defs


def add_columns(vectmap, layer, column_defs, vector_db, overwrite):
    """Add the columns to the table of layer, or add a table with them

    vector_db holds the connections of the map vectmap was copied from: a
    layer that has a table there has it in vectmap too. A column that the
    table has is refused without overwrite and written again with it.
    """
    if vector_db and layer in vector_db and vector_db[layer]["table"]:
        # v.db.addcolumn only prints an error for a column that the
        # table has and the run would go on and replace its values
        present = {column.lower() for column in gs.vector_columns(vectmap, layer=layer)}
        for column in column_defs.copy():
            if column.lower() not in present:
                continue
            if not overwrite:
                gs.fatal(
                    _(
                        "Unable to add column {column} to vector map "
                        "<{vector}> with layer {layer}: the column exists, "
                        "use the overwrite flag to replace its values"
                    ).format(column=column, vector=vectmap, layer=layer)
                )
            del column_defs[column]
        columns_string = ",".join(column_defs.values())
        if columns_string:
            try:
                gs.run_command(
                    "v.db.addcolumn",
                    map=vectmap,
                    layer=layer,
                    column=columns_string,
                    overwrite=overwrite,
                )
            except CalledModuleError:
                gs.fatal(
                    _("Unable to add column %s to vector map <%s> with layer %i")
                    % (columns_string, vectmap, layer)
                )
    else:
        columns_string = ",".join(column_defs.values())
        # Try to add a new table
        gs.message("Add table to layer %i" % (layer))
        try:
            gs.run_command(
                "v.db.addtable",
                map=vectmap,
                layer=layer,
                columns=columns_string,
                overwrite=overwrite,
            )
        except CalledModuleError:
            gs.fatal(
                _("Unable to add table to vector map <%s> with layer %i")
                % (vectmap, layer)
            )


def sample_rasters(vectmap, layer, raster_names, column_names):
    """Write the values of the raster maps at the points into the columns"""
    for name, column in zip(raster_names, column_names, strict=False):
        try:
            gs.run_command(
                "v.what.rast",
                map=vectmap,
                layer=layer,
                raster=name,
                column=column,
            )
        except CalledModuleError:
            gs.fatal(
                _(
                    "Unable to run v.what.rast for vector map <%s> "
                    "with layer %i and raster map <%s>"
                )
                % (vectmap, layer, str(raster_names))
            )


def register_layer(out_sp, vect, sample, first_strds, dbif):
    """Give vect the time of sample and register it in out_sp"""
    vect.load()

    start = sample.start
    end = sample.end

    if out_sp.is_time_absolute():
        vect.set_absolute_time(start, end)
    else:
        vect.set_relative_time(start, end, first_strds.get_relative_time_unit())

    if vect.is_in_db(dbif):
        vect.update_all(dbif)
    else:
        vect.insert(dbif)

    out_sp.register_map(vect, dbif)


def observe_samples(
    samples,
    column_names,
    vectmap,
    vector_db,
    out_sp,
    first_strds,
    mapset,
    overwrite,
    dbif,
):
    """Sample the raster maps in a layer of vectmap per sample and register it

    The layers are counted from 1 in the order of samples. If a step fails,
    the registered maps, out_sp and vectmap are removed and the connection
    is closed.
    """
    dummy = out_sp.get_new_map_instance(None)

    # The dataset, its map entries and the vector map that this run made are
    # removed if a step fails
    # The cleanup below needs the open connection, so the refusals inside the
    # try do not close it; the cleanup closes it.
    registered = []
    try:
        # Sample the space time raster dataset with the vector
        # map at specific layer with v.what.rast
        for count, sample in enumerate(samples, 1):
            raster_names = sample.raster_names

            column_defs = column_definitions(raster_names, column_names)
            add_columns(vectmap, count, column_defs, vector_db, overwrite)
            sample_rasters(vectmap, count, raster_names, column_names)

            vect = out_sp.get_new_map_instance(
                dummy.build_id(vectmap, mapset, str(count))
            )
            register_layer(out_sp, vect, sample, first_strds, dbif)
            registered.append(vect)

    except BaseException:
        for vect in registered:
            vect.delete(dbif)
        out_sp.delete(dbif)
        dbif.close()
        gs.run_command(
            "g.remove",
            flags="f",
            type="vector",
            name=vectmap,
            quiet=True,
            errors="ignore",
        )
        raise


def main():
    # Get the options
    input = options["input"]
    output = options["output"]
    vector_output = options["vector_output"]
    strds = options["strds"]
    where = options["where"]
    columns = options["columns"]

    if where in {"", " ", "\n"}:
        where = None

    overwrite = gs.overwrite()

    # Check the number of sample strds and the number of columns
    strds_names = strds.split(",")
    column_names = columns.split(",")

    if len(strds_names) != len(column_names):
        gs.fatal(
            _(
                "The number of columns must be equal to the number of space time "
                "raster datasets"
            )
        )

    input_db = check_input(input, where)

    # Make sure the temporal database exists
    tgis.init()
    # We need a database interface
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    mapset = gs.gisenv()["MAPSET"]

    out_sp = tgis.check_new_stds(output, "stvds", dbif, overwrite)

    first_strds = tgis.open_old_stds(strds_names[0], "strds", dbif)

    if len(strds_names) == 1:
        samples = single_samples(first_strds, dbif)
    else:
        samples = granule_samples(strds_names, first_strds, dbif)

    points = select_points(input, where, dbif)

    # Get the layer and database connections of the observed points
    vector_db = gs.vector.vector_db(points)
    if overwrite:
        check_column_cases(points, vector_db, len(samples), column_names, input, dbif)
    copy_with_layers(points, vector_db, len(samples), vector_output, overwrite)

    layer_one = input_db.get(1)
    if where and layer_one:
        name_layer_one(vector_output, layer_one)

    title = _("Observation of space time raster dataset(s) <%s>") % (strds)
    description = _(
        "Observation of space time raster dataset(s) <%s> with vector map <%s>"
    ) % (strds, input)

    # Create the output space time vector dataset
    out_sp = tgis.open_new_stds(
        output,
        "stvds",
        first_strds.get_temporal_type(),
        title,
        description,
        first_strds.get_semantic_type(),
        dbif,
        overwrite,
    )

    observe_samples(
        samples,
        column_names,
        vector_output,
        vector_db,
        out_sp,
        first_strds,
        mapset,
        overwrite,
        dbif,
    )

    out_sp.update_from_registered_maps(dbif)
    dbif.close()


if __name__ == "__main__":
    options, flags = gs.parser()
    # lazy imports
    import grass.temporal as tgis

    main()
