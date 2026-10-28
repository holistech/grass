"""Steps that several temporal tools share

A tool that runs a module for each map of a space time dataset opens the new
map of each input map with open_new_map_for() and registers the computed maps
with register_new_maps() and removes the empty ones with remove_maps(). Opening
the output dataset and running the modules stay with the caller: the tools
differ there, and their error messages are translated per tool.

The tools that compute in cycles (t.rast.accumulate, t.rast.accdetect) walk
their cycles with dataset_cycles(), find the threshold map of a map with
first_related_map_id(), open each result map with open_result_map() and
write each output dataset with register_in_new_stds().

A tool whose file option lists names, one per line, reads them with
names_from_file().

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from pathlib import Path

import grass.script as gs

from .datetime_math import increment_datetime_by_string, map_name_suffix, next_cycle
from .open_stds import open_new_map_dataset
from .state import get_current_mapset


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

    A registered map of that name without overwrite ends the run through the
    message interface (msgr.fatal), which raises FatalError only when the
    interface is set to raise. This function keeps that fatal, unlike the
    later helpers that raise ValueError, because it passes straight through
    to open_new_map_dataset(), whose message and exit are fixed.
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


def register_new_maps(new_maps, dataset, *, register_null, dbif):
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
                     otherwise with their time set; a sequence or another
                     collection with len(), such as the values of a dict
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


def remove_maps(maps, map_type):
    """Remove the maps from the GRASS database with one call of g.remove

    Used for maps a tool has computed but does not keep, such as the empty
    maps that register_new_maps() returns or those that t.rast.contour finds
    in its own registration step. The caller decides when this happens
    relative to closing the database connection.

    :param maps: The maps to remove, objects with get_name(); nothing is
                 called for an empty sequence
    :param map_type: The type of the maps as g.remove takes it: raster,
                     raster_3d or vector
    """
    if not maps:
        return
    gs.run_command(
        "g.remove",
        flags="f",
        type=map_type,
        name=",".join(map_.get_name() for map_ in maps),
        quiet=True,
    )


def register_in_new_stds(
    new_maps, dataset, input_dataset, *, register_null, overwrite, dbif
):
    """Insert dataset anew and register the computed maps in it

    With overwrite an entry of dataset in the temporal database is removed
    first, so that the dataset holds only the new maps; without overwrite
    the caller has refused an existing dataset before. The new entry takes
    the temporal and semantic type, the title and the description of
    input_dataset. The maps are registered with register_new_maps().

    :param new_maps: The computed maps, see register_new_maps()
    :param dataset: The output dataset, not yet inserted or to be replaced
    :param input_dataset: The input dataset of the tool, selected from the
                          database
    :param register_null: The value of the flag that keeps empty maps
    :param overwrite: Whether an existing entry of dataset is replaced
    :param dbif: The database interface or None
    :return: The empty maps that were left out; the caller removes them
    """
    dataset_id = dataset.get_id()
    if dataset.is_in_db(dbif) and overwrite:
        dataset.delete(dbif)
        dataset = input_dataset.get_new_instance(dataset_id)

    temporal_type, semantic_type, title, description = (
        input_dataset.get_initial_values()
    )
    dataset.set_initial_values(temporal_type, semantic_type, title, description)
    dataset.insert(dbif)

    return register_new_maps(new_maps, dataset, register_null=register_null, dbif=dbif)


def names_from_file(path):
    """Return the names that a file lists, one per line

    Whitespace around a name, such as spaces and tabs, is removed, and a line
    that is empty or holds only whitespace is left out: an editor often
    leaves an empty line at the end of a file. The file is read with the
    default encoding of open().

    :param path: The value of the file option
    :return: The names in the order of the file
    :raises ValueError: when path is not a file
    """
    if not Path(path).is_file():
        raise ValueError(_("File <{}> not found").format(path))
    with open(path) as stream:
        return [line.strip() for line in stream if line.strip()]


def _is_empty(new_map):
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


def open_result_map(input_map, name, *, overwrite, dbif):
    """Open the new map name in the current mapset with the time of input_map

    The new map has the type of input_map and is not inserted into the
    temporal database. Unlike open_new_map_for(), the caller gives the whole
    name and decides how a registered map of that name ends the run.

    :param input_map: The map whose type and time the new map takes
    :param name: The name of the new map
    :param overwrite: Whether a registered map of that name may be replaced;
                      its entry in the temporal database is then removed
    :param dbif: The database interface or None
    :return: The new map
    :raises ValueError: "Map <id> is already registered in the temporal
                        database, use overwrite flag to overwrite." when a
                        map of that name is registered and overwrite is False
    """
    map_id = input_map.build_id(name, get_current_mapset())
    result_map = input_map.get_new_instance(map_id)

    if result_map.is_in_db(dbif):
        if overwrite:
            result_map.delete(dbif)
            result_map = input_map.get_new_instance(map_id)
        else:
            raise ValueError(
                _(
                    "Map <%s> is already registered in the temporal"
                    " database, use overwrite flag to overwrite."
                )
                % (result_map.get_map_id())
            )

    start, end = input_map.get_temporal_extent_as_tuple()
    if input_map.is_time_absolute():
        result_map.set_absolute_time(start, end)
    else:
        result_map.set_relative_time(start, end, input_map.get_relative_time_unit())
    return result_map


# The relations by which a map selects a map of another dataset, in the order
# in which they are tried, as the topology builder files them.
_SELECTING_RELATIONS = ("EQUAL", "DURING", "OVERLAPS", "OVERLAPPED", "CONTAINS")


def first_related_map_id(map_):
    """The id of the map of another dataset that map_ selects, or None

    The relations EQUAL, DURING, OVERLAPS, OVERLAPPED and CONTAINS are tried
    in this order; of the first that holds maps, the first map counts. The
    topology of map_ with the other maps must be built
    (SpatioTemporalTopologyBuilder.build(maps, other_maps)).

    :param map_: A map with its temporal relations built
    :return: The id of the selected map, None when no relation holds a map
    """
    relations = map_.get_temporal_relations()
    for relation in _SELECTING_RELATIONS:
        if relation in relations:
            return str(relations[relation][0].get_id())
    return None


def dataset_cycles(dataset, start, end, *, stop, cycle, offset, dbif):
    """Yield the start and the end of each cycle over the maps of dataset

    The first cycle runs from start to end, next_cycle() gives the later
    ones, counted from start. A cycle is yielded while it starts before stop
    and before the end of the data. A cycle that reaches beyond stop ends at
    stop, except for the relative stop 0: it is falsy and therefore cuts no
    cycle. The end of the data is the end of dataset, or one unit behind it
    (one second in absolute time) when a map is an instant there, so that
    this map lies in a cycle. It is read from the database when the first
    cycle is asked for.

    The dataset must have registered maps: an empty dataset has no end, and
    the comparison with it raises TypeError. The tools check this before.

    :param dataset: The input dataset with registered maps, selected from
                    the database
    :param start: The start of the first cycle, a datetime in absolute time,
                  a number of the unit of dataset in relative time
    :param end: The end of the first cycle, after start
    :param stop: The time at which the cycles end, None for the end of the
                 data
    :param cycle: The length of a cycle as next_cycle() takes it
    :param offset: The gap between two cycles as next_cycle() takes it; the
                   caller makes sure that the cycles move forward
    :param dbif: The database interface or None
    """
    data_end = _data_end(dataset, dbif)
    if stop is None:
        stop = data_end
    absolute = dataset.is_time_absolute()
    origin = start
    number = 0
    while data_end > start and stop > start:
        if stop and end > stop:
            end = stop
        yield start, end
        number += 1
        start, end = next_cycle(origin, number, end, cycle, offset, absolute)


def _data_end(dataset, dbif):
    """The end of dataset, one unit behind an instant at the end"""
    _start, end = dataset.get_temporal_extent_as_tuple()
    # The cycles end before the end of the data, so an instant at the end of
    # the dataset would be left out. One unit behind it keeps it in, as in
    # t.rast.aggregate.
    if dataset.get_registered_maps_as_objects(
        where=f"start_time = '{end}' AND end_time IS NULL", dbif=dbif
    ):
        if dataset.is_time_absolute():
            return increment_datetime_by_string(end, "1 second")
        return end + 1
    return end
