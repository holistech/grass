"""Steps that several temporal tools share when they compute map by map

t.rast.contour, t.rast.to.vect and t.rast.neighbors run a module for each map
of a space time raster dataset and write a new map with the time of the input
map; they open the new maps with open_new_map_for(). t.rast.neighbors,
t.rast.to.vect, t.rast.accumulate and t.rast.accdetect register the computed
maps with register_new_maps(). Each tool keeps the steps in which it differs
from the others: opening the output dataset, running the modules, and
removing the empty maps (t.rast.accumulate and t.rast.accdetect remove them
one by one after closing the database connection, the others with one g.remove
before).

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import grass.script as gs

from .datetime_math import map_name_suffix
from .open_stds import open_new_map_dataset

if TYPE_CHECKING:
    from collections.abc import Collection


def open_new_map_for(
    input_map, basename, suffix, granularity, number, *, map_type, overwrite, dbif
):
    """Open the new map that a tool computes from input_map, with its time

    The new map is named {basename}_{map_name_suffix(...)} in the current
    mapset and gets the temporal extent of input_map; it is not inserted
    into the temporal database. Whether a map of that name exists in the
    GRASS database is not checked; that is up to the tool.

    :param input_map: The map whose start time or number names the new map;
                      its temporal type must be set
    :param basename: The value of the basename option
    :param suffix: The value of the suffix option, see map_name_suffix()
    :param granularity: The granularity of the input dataset for gran
    :param number: The number for num, counted from 1 by the caller
    :param map_type: The type of the new map as dataset_factory() takes it,
                     for example raster or vector
    :param overwrite: Whether a registered map of that name may be replaced;
                      its entry in the temporal database is then removed
    :param dbif: The database interface or None
    :raises FatalError: when a map of that name is registered and overwrite
                        is False
    """
    suffix = map_name_suffix(input_map, suffix, granularity, number)
    return open_new_map_dataset(
        f"{basename}_{suffix}",
        None,
        type=map_type,
        temporal_extent=input_map.get_temporal_extent(),
        overwrite=overwrite,
        dbif=dbif,
    )


def register_new_maps(new_maps: Collection, dataset, register_null: bool, dbif) -> list:
    """Register the computed maps in dataset, except empty ones, and update it

    Each map is loaded from the GRASS database, inserted into the temporal
    database and registered in dataset, in the order of new_maps. An empty
    map, a raster or 3D raster map of only null cells or a vector map
    without primitives, is left out unless register_null is True. Then the
    extent and the metadata of dataset are computed from its registered
    maps, so a dataset that held maps before keeps them.

    The progress is shown with gs.percent() every ten maps and at the end,
    as the tools did before. The message interface of the library would give
    other output: measured 2026-10-28 in grass --tmp-project XY --exec with
    a script that shows the progress of 25 maps the way of this loop, once
    with gs.percent() and once with the percent() of the message interface,
    GRASS_MESSAGE_FORMAT=gui gives a blank line before each percent line
    with gs.percent() and none with the message interface; standard and
    plain give the same bytes.

    :param new_maps: The computed maps, opened with open_new_map_for() or
                     otherwise with their time set
    :param dataset: The output dataset, inserted into the temporal database
    :param register_null: The value of the flag that keeps empty maps
    :param dbif: The database interface or None
    :return: The empty maps that were left out, in the order of new_maps;
             the caller removes them
    """
    empty_maps = []
    for count, new_map in enumerate(new_maps, start=1):
        if count % 10 == 0:
            gs.percent(count, len(new_maps), 1)
        new_map.load()
        if _is_empty(new_map) and not register_null:
            empty_maps.append(new_map)
            continue
        new_map.insert(dbif)
        dataset.register_map(new_map, dbif)
    dataset.update_from_registered_maps(dbif)
    gs.percent(1, 1, 1)
    return empty_maps


def _is_empty(new_map) -> bool:
    """Tell whether a loaded map has no cell values or no primitives"""
    if new_map.get_type() != "vector":
        return new_map.metadata.get_min() is None and new_map.metadata.get_max() is None
    primitives = new_map.metadata.get_number_of_primitives()
    if primitives is None:
        # Without topology (-b of v.in.ascii, r.to.vect) the temporal library
        # cannot count the primitives and stores None; v.info -t counts them
        # from the coor file without writing a topology.
        primitives = gs.vector_info_topo(new_map.get_id())["primitives"]
    return primitives == 0
