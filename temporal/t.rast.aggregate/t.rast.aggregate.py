#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.rast.aggregate
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Temporally aggregates the maps of a space time raster dataset by a user defined granularity.
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Aggregates temporally the maps of a space time raster dataset by a user defined granularity.
# % keyword: temporal
# % keyword: aggregation
# % keyword: raster
# % keyword: time
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option G_OPT_STRDS_OUTPUT
# %end

# %option
# % key: basename
# % type: string
# % label: Basename of the new generated output maps
# % description: Either a numerical suffix or the start time (s-flag) separated by an underscore will be attached to create a unique identifier
# % required: yes
# % multiple: no
# %end

# %option G_OPT_T_SUFFIX
# %end

# %option
# % key: granularity
# % type: string
# % description: Aggregation granularity: for absolute time one number and one unit, such as "1 months" or "2 weeks" (years, months, weeks, days, hours, minutes, seconds); for relative time an integer in the unit of the dataset
# % required: yes
# % multiple: no
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
# % description: Number of r.series processes to run in parallel
# % required: no
# % multiple: no
# % answer: 1
# %end

# %option
# % key: file_limit
# % type: integer
# % description: Number of maps of a granule above which r.series reopens the maps for each row (flag z); fewer maps also do when they exceed the open files of the process
# % required: no
# % multiple: no
# % answer: 1000
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
        aggregation_granules,
        sampling_relation,
        set_output_metadata,
    )

    input = options["input"]
    output = options["output"]
    where = options["where"]
    gran = options["granularity"]
    base = options["basename"]
    register_null = flags["n"]
    method = options["method"]
    sampling = options["sampling"].split(",")
    offset = options["offset"]
    nprocs = options["nprocs"]
    file_limit = options["file_limit"]
    time_suffix = options["suffix"]

    try:
        tgis.check_suffix(time_suffix)
    except ValueError as error:
        gs.fatal(str(error))

    tgis.init()
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        sp = tgis.open_old_stds(input, "strds", dbif)
        absolute = sp.is_time_absolute()
        tgis.check_new_stds(output, "strds", dbif, gs.overwrite())

        try:
            input_series = ta.source(input, where=where)
        except tgis.SQLStatementError as error:
            gs.fatal(_("Invalid where condition <{}>: {}").format(where, error))
        if not input_series.slots:
            gs.fatal(_("Space time raster dataset <{}> is empty").format(input))

        target = aggregation_granules(
            input_series,
            gran,
            absolute=absolute,
            unit=sp.get_relative_time_unit(),
        )
        if not absolute:
            # aggregation_granules() has checked the text, so this cannot fail.
            gran = int(gran)

        dataset = aggregate_series(
            input_series,
            target,
            sampling_relation(sampling),
            method,
            sampling=sampling,
            output=output,
            basename=base,
            granularity=gran,
            time_suffix=time_suffix,
            offset=offset,
            nprocs=nprocs,
            file_limit=file_limit,
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
