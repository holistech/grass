#!/usr/bin/env python3

############################################################################
#
# MODULE:	t.rast.aggregate.ds
# AUTHOR(S):	Soeren Gebbert
#
# PURPOSE:	Aggregates data of an existing space time raster dataset using the time intervals of a second space time dataset
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Aggregates data of an existing space time raster dataset using the time intervals of a second space time dataset.
# % keyword: temporal
# % keyword: aggregation
# % keyword: raster
# % keyword: time
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option G_OPT_STDS_INPUT
# % key: sample
# % description: Time intervals from this space time dataset (raster, vector or raster3d) are used for aggregation computation
# %end

# %option G_OPT_STDS_TYPE
# % description: Type of the space time dataset from which aggregation will be copied
# %end

# %option G_OPT_STRDS_OUTPUT
# %end

# %option
# % key: basename
# % type: string
# % label: Basename of the new generated output maps
# % description: A numerical suffix separated by an underscore will be attached to create a unique identifier
# % required: yes
# % multiple: no
# %end

# %option G_OPT_T_SUFFIX
# %end

# %option
# % key: method
# % type: string
# % description: Aggregate operation to be performed on the raster maps
# % required: yes
# % multiple: no
# % options: average,count,median,mode,minimum,min_raster,maximum,max_raster,stddev,range,sum,variance,diversity,slope,offset,detcoeff,quart1,quart3,perc90,quantile,skewness,kurtosis
# % answer: average
# %end

# %option
# % key: offset
# % type: integer
# % description: Offset that is used to create the output map ids, output map id is generated as: basename_ (count + offset)
# % required: no
# % multiple: no
# % answer: 0
# %end

# %option
# % key: nprocs
# % type: integer
# % description: Number of r.mapcalc processes to run in parallel
# % required: no
# % multiple: no
# % answer: 1
# %end

# %option G_OPT_T_SAMPLE
# % options: equal,overlaps,overlapped,starts,started,finishes,finished,during,contains
# % answer: contains
# %end

# %option G_OPT_T_WHERE
# %end

# %flag
# % key: n
# % description: Register Null maps
# %end

import grass.script as gs

############################################################################


def main():
    # lazy imports
    import grass.temporal as tgis
    import grass.temporal.algebra as ta
    from grass.exceptions import FatalError
    from grass.temporal.aggregation_core import (
        aggregate_series,
        sampler_target,
        set_output_metadata,
    )

    input = options["input"]
    output = options["output"]
    sampler = options["sample"]
    where = options["where"]
    base = options["basename"]
    register_null = flags["n"]
    method = options["method"]
    sampling = options["sampling"].split(",")
    offset = options["offset"]
    nprocs = options["nprocs"]
    time_suffix = options["suffix"]
    stds_type = options["type"]

    tgis.init()
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        sp = tgis.open_old_stds(input, "strds", dbif)
        sampler_sp = tgis.open_old_stds(sampler, stds_type, dbif)
        if sampler_sp.get_temporal_type() != sp.get_temporal_type():
            gs.fatal(
                _("Input and aggregation dataset must have the same temporal type")
            )
        if sampler_sp.temporal_extent.get_map_time() != "interval":
            gs.fatal(
                _(
                    "All registered maps of the aggregation dataset must have time intervals"
                )
            )
        tgis.check_new_stds(output, "strds", dbif, gs.overwrite())

        input_series = ta.source(input, where=where)
        if not input_series.slots:
            gs.fatal(_("Space time raster dataset <{}> is empty").format(input))
        # where filters the sampler too, as the classic tool does.
        sampler_maps = sampler_sp.get_registered_maps_as_objects(
            where=where, order="start_time", dbif=dbif
        )
        if not sampler_maps:
            gs.fatal(_("Space time dataset <{}> is empty").format(sampler))

        gran = sampler_sp.get_granularity()
        unit = None if sp.is_time_absolute() else sp.get_relative_time_unit()
        target = sampler_target(sampler_maps, unit)

        dataset = aggregate_series(
            input_series,
            target,
            sampling,
            method,
            output=output,
            basename=base,
            granularity=gran,
            time_suffix=time_suffix,
            offset=offset,
            nprocs=nprocs,
            # t.rast.aggregate.ds has no file_limit option, so the classic
            # default stays.
            file_limit=1000,
            # register_null straight (not negated): -n keeps null maps,
            # matching t.rast.aggregate and the help text. The tool used to
            # pass it as delete_empty, so -n deleted them (measured
            # 2026-10-14 with the characterization tests).
            register_null=register_null,
            overwrite=gs.overwrite(),
        )
        if dataset is not None:
            set_output_metadata(dataset, sp, method, dbif)
    # The core reports wrong user input as ValueError or TypeError; the tool
    # turns it into a fatal error with the message only.
    except (FatalError, ValueError, TypeError) as error:
        gs.fatal(str(error))
    finally:
        dbif.close()


if __name__ == "__main__":
    options, flags = gs.parser()
    main()
