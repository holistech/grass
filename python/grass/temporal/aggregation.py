"""
Aggregation methods for space time raster datasets

Usage:

.. code-block:: python

    import grass.temporal as tgis

    tgis.aggregate_raster_maps(
        dataset, mapset, inputs, base, start, end, count, method, register_null, dbif
    )

SPDX-FileCopyrightText: 2012-2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:author: Soeren Gebbert
"""

import grass.script as gs
from grass.exceptions import CalledModuleError

from .space_time_datasets import RasterDataset
from .topology import (
    create_temporal_relation_sql_where_statement,
)
from .state import get_current_mapset, get_tgis_message_interface

###############################################################################


def collect_map_names(sp, dbif, start, end, sampling):
    """Gather all maps from dataset using a specific sample method

    :param sp: The space time raster dataset to select aps from
    :param dbif: The temporal database interface to use
    :param start: The start time of the sample interval, may be relative or
           absolute
    :param end: The end time of the sample interval, may be relative or
           absolute
    :param sampling: The sampling methods to use
    """

    use_start = False
    use_during = False
    use_overlap = False
    use_contain = False
    use_equal = False
    use_follows = False
    use_precedes = False

    # Initialize the methods
    if sampling:
        for name in sampling.split(","):
            if name == "start":
                use_start = True
            if name == "during":
                use_during = True
            if name == "overlap":
                use_overlap = True
            if name == "contain":
                use_contain = True
            if name == "equal":
                use_equal = True
            if name == "follows":
                use_follows = True
            if name == "precedes":
                use_precedes = True

    else:
        use_start = True

    if sp.get_map_time() != "interval":
        use_start = True
        use_during = False
        use_overlap = False
        use_contain = False
        use_equal = False
        use_follows = False
        use_precedes = False

    where = create_temporal_relation_sql_where_statement(
        start,
        end,
        use_start,
        use_during,
        use_overlap,
        use_contain,
        use_equal,
        use_follows,
        use_precedes,
    )

    rows = sp.get_registered_maps("id", where, "start_time", dbif)

    if not rows:
        return None

    return [row["id"] for row in rows]


###############################################################################


def aggregate_raster_maps(
    inputs,
    base,
    start,
    end,
    count: int,
    method,
    register_null,
    dbif,
    offset: int = 0,
    *,
    nprocs: int = 0,
):
    """Aggregate a list of raster input maps with r.series

    :param inputs: The names of the raster maps to be aggregated
    :param base: The basename of the new created raster maps
    :param start: The start time of the sample interval, may be relative or
                 absolute
    :param end: The end time of the sample interval, may be relative or
               absolute
    :param count: The number to be attached to the basename of the new
                 created raster map
    :param method: The aggregation method to be used by r.series
    :param register_null: If true null maps will be registered in the space
                         time raster dataset, if false not
    :param dbif: The temporal database interface to use
    :param offset: Offset to be added to the map counter to create the map ids
    :param nprocs: Number of cores to use for processing (0 means use all available cores)
    """

    msgr = get_tgis_message_interface()

    msgr.verbose(_("Aggregating {} raster maps").format(len(inputs)))
    output = f"{base}_{int(offset) + count}"

    mapset = get_current_mapset()
    map_id = output + "@" + mapset
    new_map = RasterDataset(map_id)

    # Check if new map is in the temporal database
    if new_map.is_in_db(dbif):
        if gs.overwrite() is True:
            # Remove the existing temporal database entry
            new_map.delete(dbif)
            new_map = RasterDataset(map_id)
        else:
            msgr.error(
                _(
                    "Raster map <%(name)s> is already in temporal "
                    "database, use overwrite flag to overwrite"
                )
                % ({"name": new_map.get_name()})
            )
            return None

    msgr.verbose(
        _("Computing aggregation of maps between %(st)s - %(end)s")
        % {"st": str(start), "end": str(end)}
    )

    # Create the r.series input file
    filename = gs.tempfile(True)
    with open(filename, "w") as out_file:
        for name in inputs:
            string = f"{name}\n"
            out_file.write(string)

    # Run r.series
    try:
        if len(inputs) > 1000:
            gs.run_command(
                "r.series",
                nprocs=nprocs,
                flags="z",
                file=filename,
                output=output,
                overwrite=gs.overwrite(),
                method=method,
            )
        else:
            gs.run_command(
                "r.series",
                nprocs=nprocs,
                file=filename,
                output=output,
                overwrite=gs.overwrite(),
                method=method,
            )

    except CalledModuleError:
        msgr.fatal(_("Error occurred in r.series computation"))

    # Read the raster map data
    new_map.load()

    # In case of a null map continue, do not register null maps
    if (
        new_map.metadata.get_min() is None
        and new_map.metadata.get_max() is None
        and not register_null
    ):
        gs.run_command("g.remove", flags="f", type="raster", name=output)
        return None

    return new_map
