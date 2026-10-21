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

############################################################################


class Sample:
    def __init__(self, start=None, end=None, raster_names=None):
        self.start = start
        self.end = end
        if raster_names is not None:
            self.raster_names = raster_names
        else:
            self.raster_names = []

    def __str__(self):
        return "Start: %s\nEnd: %s\nNames: %s\n" % (
            str(self.start),
            str(self.end),
            str(self.raster_names),
        )


############################################################################


def main():
    # lazy imports
    import grass.temporal as tgis

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

    if not gs.find_file(input, element="vector")["file"]:
        gs.fatal(_("Vector map <%s> not found") % input)

    # Make sure the temporal database exists
    tgis.init()
    # We need a database interface
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    mapset = gs.gisenv()["MAPSET"]

    out_sp = tgis.check_new_stds(output, "stvds", dbif, overwrite)

    samples = []

    first_strds = tgis.open_old_stds(strds_names[0], "strds", dbif)

    # Single space time raster dataset
    if len(strds_names) == 1:
        rows = first_strds.get_registered_maps(
            columns="name,mapset,start_time,end_time", order="start_time", dbif=dbif
        )

        if not rows:
            dbif.close()
            gs.fatal(_("Space time raster dataset <%s> is empty") % out_sp.get_id())

        for row in rows:
            start = row["start_time"]
            end = row["end_time"]
            raster_maps = [
                row["name"] + "@" + row["mapset"],
            ]

            s = Sample(start, end, raster_maps)
            samples.append(s)
    else:
        # Multiple space time raster datasets
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

    num_samples = len(samples)

    input_name = input
    if where:
        # where selects points of the input: the other points are not in the
        # output at all. Applying it in the new layers would fail, as they
        # have no column of the input table.
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
        input = selected

    # Get the layer and database connections of the input vector
    vector_db = gs.vector.vector_db(input)

    # We copy the vector table and create the new layers
    # If vector_db, use the first layer to copy the categories from
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

    vectmap = vector_output

    # We create a new vector map using the categories of the original map
    try:
        gs.run_command(
            "v.category",
            input=input,
            layer=layers,
            output=vectmap,
            option="transfer",
            overwrite=overwrite,
        )
    except CalledModuleError:
        gs.fatal(_("Unable to create new layers for vector map <%s>") % (vectmap))

    title = _("Observation of space time raster dataset(s) <%s>") % (strds)
    description = _(
        "Observation of space time raster dataset(s) <%s> with vector map <%s>"
    ) % (strds, input_name)

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

    dummy = out_sp.get_new_map_instance(None)

    # The dataset and its maps are removed if a step fails; the vector map
    # with the layers stays
    registered = []
    try:
        # Sample the space time raster dataset with the vector
        # map at specific layer with v.what.rast
        count = 1
        for sample in samples:
            raster_names = sample.raster_names

            if len(raster_names) != len(column_names):
                gs.fatal(
                    _(
                        "The number of raster maps in a granule must "
                        "be equal to the number of column names"
                    )
                )

            # Create the column definitions
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

            # Try to add the columns
            if vector_db and count in vector_db and vector_db[count]["table"]:
                # v.db.addcolumn only prints an error for a column that the
                # table has and the run would go on and replace its values
                present = {
                    column.lower() for column in gs.vector_columns(vectmap, layer=count)
                }
                for column in column_defs.copy():
                    if column.lower() not in present:
                        continue
                    if not overwrite:
                        dbif.close()
                        gs.fatal(
                            _(
                                "Unable to add column {column} to vector map "
                                "<{vector}> with layer {layer}: the column exists, "
                                "use the overwrite flag to replace its values"
                            ).format(column=column, vector=vectmap, layer=count)
                        )
                    del column_defs[column]
                columns_string = ",".join(column_defs.values())
                if columns_string:
                    try:
                        gs.run_command(
                            "v.db.addcolumn",
                            map=vectmap,
                            layer=count,
                            column=columns_string,
                            overwrite=overwrite,
                        )
                    except CalledModuleError:
                        dbif.close()
                        gs.fatal(
                            _(
                                "Unable to add column %s to vector map <%s> with layer %i"
                            )
                            % (columns_string, vectmap, count)
                        )
            else:
                columns_string = ",".join(column_defs.values())
                # Try to add a new table
                gs.message("Add table to layer %i" % (count))
                try:
                    gs.run_command(
                        "v.db.addtable",
                        map=vectmap,
                        layer=count,
                        columns=columns_string,
                        overwrite=overwrite,
                    )
                except CalledModuleError:
                    dbif.close()
                    gs.fatal(
                        _("Unable to add table to vector map <%s> with layer %i")
                        % (vectmap, count)
                    )

            # Call v.what.rast for each raster map
            for name, column in zip(raster_names, column_names, strict=False):
                try:
                    gs.run_command(
                        "v.what.rast",
                        map=vectmap,
                        layer=count,
                        raster=name,
                        column=column,
                    )
                except CalledModuleError:
                    dbif.close()
                    gs.fatal(
                        _(
                            "Unable to run v.what.rast for vector map <%s> "
                            "with layer %i and raster map <%s>"
                        )
                        % (vectmap, count, str(raster_names))
                    )

            vect = out_sp.get_new_map_instance(
                dummy.build_id(vectmap, mapset, str(count))
            )
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
            registered.append(vect)
            count += 1

    except BaseException:
        for vect in registered:
            vect.delete(dbif)
        out_sp.delete(dbif)
        dbif.close()
        raise

    out_sp.update_from_registered_maps(dbif)
    dbif.close()


if __name__ == "__main__":
    options, flags = gs.parser()
    main()
