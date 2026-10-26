"""
Functions to register map layer in space time datasets and the temporal database

Usage:

.. code-block:: python

    import grass.temporal as tgis

    tgis.register_maps_in_space_time_dataset(type, name, maps)

SPDX-FileCopyrightText: 2012-2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime

import grass.script as gs

from .abstract_map_dataset import (
    AbstractMapDataset,
    other_temporal_type_message,
    other_time_unit_message,
)
from .datetime_math import (
    check_datetime_string,
    increment_datetime_by_string,
    string_to_datetime,
)
from .db import SQLDatabaseInterfaceConnection, connection
from .factory import dataset_factory
from .kinds import MAP_ALIASES, find_kind, stds_kind_of
from .open_stds import open_old_stds
from .state import get_current_mapset, get_tgis_message_interface

# The names of the map types that dataset_factory() knows
MAP_TYPES = MAP_ALIASES

###############################################################################


def _refuse_other_time(sp, map_object, dbif, run_unit=None):
    """Stop if the dataset would not take the map for its time

    Tests the temporal type and the relative unit, as register_map() of the
    dataset does. A relative dataset that holds maps sets the unit. An empty
    one takes the unit of the first map it registers, so run_unit carries
    the unit of the first map checked in this run.

    Returns the unit the next map must have, None for an absolute dataset.
    """
    msgr = get_tgis_message_interface()
    if sp.get_temporal_type() != map_object.get_temporal_type():
        msgr.fatal(other_temporal_type_message(sp.get_id(), map_object))
    if not sp.is_time_relative():
        return None
    if sp.metadata.get_number_of_maps():
        expected = sp.get_relative_time_unit()
    else:
        expected = run_unit or map_object.get_relative_time_unit()
    if expected != map_object.get_relative_time_unit():
        msgr.fatal(other_time_unit_message(sp.get_id(), map_object))
    return expected


@dataclass
class _FileRow:
    """A map of the input file or of the maps option, with the columns it has

    A column the line does not have is None; an empty column is "".
    """

    id: str
    start: str | None = None
    end: str | None = None
    semantic_label: str | None = None


@dataclass
class _Run:
    """What the registration of one call shares between its steps"""

    type: str
    name: str | None
    sp: object
    dbif: SQLDatabaseInterfaceConnection
    mapset: str
    overwrite: bool
    unit: str | None
    increment: str | None
    interval: bool
    option_start: str | None
    option_end: str | None
    # The unit of the first map checked, for a dataset that holds no map yet
    run_unit: str | None = None
    # Whether the times of the dataset have a time zone; unknown for an
    # empty dataset until the first new map is seen
    zone_aware: bool | None = None
    # The maps to enter into the temporal database, with whether they are
    # there already and the semantic label of the input file
    to_write: list = field(default_factory=list)
    # The maps to register in the dataset
    stds_maps: list = field(default_factory=list)
    # The ids of datasets that must be updated
    other_datasets: dict = field(default_factory=dict)


def _as_text(value):
    """The value as a string; None and an empty string stay as they are"""
    return value if value is None or value == "" else str(value)


def _check_arguments(type, maps, file, start, end, increment, interval):
    """Refuse arguments that do not go together, before anything is read

    :return: start, end and increment as strings (None stays None)
    """
    start, end, increment = _as_text(start), _as_text(end), _as_text(increment)

    # The first refusal in this order is the one that is reported
    refusals = (
        (maps and file, _("maps and file are mutually exclusive")),
        (end and increment, _("end and increment are mutually exclusive")),
        (end and interval, _("end and the interval flag are mutually exclusive")),
        (increment and not start, _("The increment option requires the start option")),
        (interval and not start, _("The interval flag requires the start option")),
        (end and not start, _("Please specify start_time and end_time")),
        (not maps and not file, _("Please specify maps or file")),
        # dataset_factory() would return None for any other name and the loop
        # over the maps would stop with an AttributeError.
        (
            type not in MAP_TYPES,
            _("Unknown map type <{type}>, use one of: {types}").format(
                type=type, types=", ".join(sorted(MAP_TYPES))
            ),
        ),
    )
    msgr = get_tgis_message_interface()
    for refused, message in refusals:
        if refused:
            msgr.fatal(message)
    return start, end, increment


def _open_dataset(name, type, mapset, start, end, unit, dbif):
    """Open the dataset to register in; None without a name

    The dataset is written only at the very end, after the maps were entered
    and their time stamps set, so a dataset of another mapset is refused here,
    before those writes.
    """
    if not name:
        return None
    msgr = get_tgis_message_interface()
    sp = open_old_stds(name, type, dbif)

    if sp.get_mapset() != mapset:
        msgr.fatal(
            _(
                "Unable to register maps in the space time dataset <{name}>. "
                "The mapset of the dataset does not match the current "
                "mapset"
            ).format(name=sp.get_id())
        )

    if sp.is_time_relative() and (start or end) and not unit:
        msgr.fatal(
            _(
                "Space time {sp} dataset <{name}> with relative"
                " time found, but no relative unit set for {sp} "
                "maps"
            ).format(name=name, sp=sp.get_new_map_instance(None).get_type())
        )
    return sp


def _columns_of_line(line_list, sp):
    """Tell which of start, end and semantic label a line of the file has

    :return: a tuple of three booleans
    """
    if len(line_list) == 2:
        return True, False, False
    if len(line_list) == 4:
        return True, True, True
    if len(line_list) != 3:
        return False, False, False
    # The last column is an end time or a semantic label. Relative timestamps
    # are integers, absolute timestamps are datetime strings; anything else
    # is a semantic label.
    if sp is not None and sp.is_time_relative():
        try:
            int(line_list[2])
        except ValueError:
            has_end = False
        else:
            has_end = True
    else:
        has_end = isinstance(check_datetime_string(line_list[2]), datetime)
    return True, has_end, not has_end


def _read_rows(stream, fs, sp, type):
    """Read one row for each line of the stream that is not empty"""
    rows = []
    while True:
        line = stream.readline()
        # The end of the file is the only empty string; an empty line
        # still has its newline.
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        line_list = line.split(fs)
        has_start, has_end, has_label = _columns_of_line(line_list, sp)

        row = _FileRow(
            AbstractMapDataset.build_id_from_search_path(line_list[0].strip(), type)
        )
        if has_start:
            row.start = line_list[1].strip()
        if has_end:
            row.end = line_list[2].strip()
        if has_label:
            # case-sensitive, the user decides on the band name
            row.semantic_label = line_list[3 if has_end else 2].strip()
        rows.append(row)
    return rows


def _read_map_file(file, fs, sp, type):
    """Read the rows of the input file, a path or a stream with readline()

    A stream belongs to the caller and stays open; a path is opened here.

    :param file: A path, or an object with readline()
    :param fs: The field separator
    :param sp: The dataset, or None; its temporal type decides which last
               column of three is an end time
    :param type: The map type
    :return: A list of _FileRow, one for each line
    """
    if hasattr(file, "readline"):
        return _read_rows(file, fs, sp, type)
    with open(file) as stream:
        return _read_rows(stream, fs, sp, type)


def _map_rows(maps, file, fs, sp, type, increment, interval):
    """The rows of the maps option or of the file, with the warnings for a file"""
    if maps:
        return [
            _FileRow(AbstractMapDataset.build_id_from_search_path(item, type))
            for item in maps.split(",")
        ]

    rows = _read_map_file(file, fs, sp, type)
    msgr = get_tgis_message_interface()
    times_in_file = any(row.start is not None for row in rows)
    if times_in_file and increment:
        msgr.warning(
            _(
                "The increment option will be ignored because of time stamps in "
                "input file"
            )
        )
    if times_in_file and interval:
        msgr.warning(
            _("The interval flag will be ignored because of time stamps in input file")
        )
    return rows


def _dataset_zone(sp, dbif):
    """Whether the times of the maps in an absolute dataset have a time zone

    The start time of the dataset itself loses its time zone, so the first
    registered map is looked at instead. None for a dataset without maps.
    """
    rows = sp.get_registered_maps("start_time", None, "start_time", dbif)
    if not rows:
        return None
    dataset_start = rows[0]["start_time"]
    if isinstance(dataset_start, str):
        dataset_start = check_datetime_string(dataset_start)
    if isinstance(dataset_start, datetime):
        return dataset_start.tzinfo is not None
    return None


def _check_exists(run, map_object):
    """Refuse a map that is not in the GRASS database"""
    if not map_object.map_exists():
        get_tgis_message_interface().fatal(
            _("Unable to update {t} map <{mid}>. The map does not exist.").format(
                t=map_object.get_type(), mid=map_object.get_map_id()
            )
        )


def _check_vector_layer(run, map_object):
    """Refuse a layer that a vector map does not have

    A vector map with a database link lists its layers. A layer can also have
    categories without a link (v.category option=add), so those are asked
    before a layer outside the links is refused. A map without any link is
    not checked, so any layer of it can still be registered.
    """
    layer = map_object.get_layer()
    if not layer or map_object.get_type() != "vector":
        return
    map_id = map_object.get_map_id()
    if not layer.isdecimal():
        get_tgis_message_interface().fatal(
            _(
                "Unable to register vector map <{mid}>. The layer <{l}> is no integer."
            ).format(mid=map_id, l=layer)
        )
    layers = set(gs.vector_db(map_id))
    if layers and int(layer) not in layers:
        layers.update(
            int(item)
            for item in gs.read_command(
                "v.category", input=map_id, option="layers"
            ).split()
        )
    if layers and int(layer) not in layers:
        get_tgis_message_interface().fatal(
            _(
                "Unable to register vector map <{mid}>. The map has no layer {l}."
            ).format(mid=map_id, l=layer)
        )


def _row_times(run, row):
    """The start, end and increment that apply to the row

    A row with a start time sets both times. Without an end time it takes the
    end of the command line, not the end of the row before it. A row without a
    start time takes the options of the command line, not what the row before
    it set. The increment applies to these rows only: a row with its own time
    is not moved.
    """
    if row.start is not None:
        return row.start, row.end if row.end is not None else run.option_end, None
    return run.option_start, run.option_end, run.increment


def _check_new_map_time(run, map_object, start):
    """Refuse a new map without a usable start time and set its time type"""
    if (start == "" or start is None) and not map_object.has_grass_timestamp():
        msgr = get_tgis_message_interface()
        if map_object.get_layer():
            msgr.fatal(
                _(
                    "Unable to register {t} map <{mid}> with "
                    "layer {l}. The map has no timestamp and "
                    "the start time is not set."
                ).format(
                    t=map_object.get_type(),
                    mid=map_object.get_map_id(),
                    l=map_object.get_layer(),
                )
            )
        else:
            msgr.fatal(
                _(
                    "Unable to register {t} map <{mid}>. The"
                    " map has no timestamp and the start time "
                    "is not set."
                ).format(t=map_object.get_type(), mid=map_object.get_map_id())
            )
    if start == "" or start is None:
        return
    # We need to check if the time is absolute and the unit was specified
    is_date = isinstance(check_datetime_string(start), datetime)
    if is_date and run.unit:
        get_tgis_message_interface().fatal(_("unit can only be set for relative time"))
    if not is_date and not run.unit:
        get_tgis_message_interface().fatal(
            _("unit must be set in case of relative time stamps")
        )

    if run.unit:
        map_object.set_time_to_relative()
    else:
        map_object.set_time_to_absolute()


def _warn_known_map(run, map_object):
    """Warn that a known map is not updated without the overwrite flag"""
    msgr = get_tgis_message_interface()
    if map_object.get_layer():
        msgr.warning(
            _(
                "Map is already registered in temporal "
                "database. Unable to update {t} map "
                "<{mid}> with layer {l}. Overwrite flag"
                " is not set."
            ).format(
                t=map_object.get_type(),
                mid=map_object.get_map_id(),
                l=str(map_object.get_layer()),
            )
        )
    else:
        msgr.warning(
            _(
                "Map is already registered in temporal "
                "database. Unable to update {t} map "
                "<{mid}>. Overwrite flag is not set."
            ).format(t=map_object.get_type(), mid=map_object.get_map_id())
        )


def _reload_known_map(run, map_object):
    """Load a known map that is updated and note the datasets it is in"""
    mapset = run.mapset
    map_object.select(run.dbif, mapset)

    # Save the datasets that must be updated
    datasets = map_object.get_registered_stds(run.dbif, mapset)
    if datasets is None:
        return
    for dataset in datasets:
        if dataset != "":
            run.other_datasets[dataset] = dataset

    if run.name and map_object.get_temporal_type() != run.sp.get_temporal_type():
        msgr = get_tgis_message_interface()
        if map_object.get_layer():
            msgr.fatal(
                _(
                    "Unable to update {t} map <{mid}> "
                    "with layer {l}. The temporal types "
                    "are different."
                ).format(
                    t=map_object.get_type(),
                    mid=map_object.get_map_id(),
                    l=map_object.get_layer(),
                )
            )
        else:
            msgr.fatal(
                _(
                    "Unable to update {t} map <{mid}>. "
                    "The temporal types are different."
                ).format(t=map_object.get_type(), mid=map_object.get_map_id())
            )


def _check_zone_consistency(run, map_object):
    """Refuse a time with a time zone in a dataset without one, and back

    A dataset cannot hold times with and without a time zone, because their
    extent cannot be computed. Refuse before any map is written, as the
    refusal would otherwise come after the maps were registered.
    """
    if not (run.name and run.sp.is_time_absolute()):
        return
    start_time = map_object.temporal_extent.get_start_time()
    if not isinstance(start_time, datetime):
        return
    aware = start_time.tzinfo is not None
    if run.zone_aware is None:
        run.zone_aware = aware
    elif run.zone_aware != aware:
        get_tgis_message_interface().fatal(
            _(
                "Unable to register {t} map <{mid}>. Its time "
                "{with_or_without} a time zone, the time of the "
                "maps in the space time dataset <{name}> "
                "{other}."
            ).format(
                t=map_object.get_type(),
                mid=map_object.get_map_id(),
                name=run.name,
                with_or_without=_("has") if aware else _("has no"),
                other=_("has none") if aware else _("has one"),
            )
        )


def _validate_map(run, count, row):
    """Check one map and set its time; queue it for writing and registering

    Nothing is written to the temporal database here.
    """
    map_object = dataset_factory(run.type, row.id)
    _check_exists(run, map_object)
    _check_vector_layer(run, map_object)

    start, end, row_increment = _row_times(run, row)
    is_in_db = map_object.is_in_db(run.dbif, run.mapset)

    if not is_in_db:
        _check_new_map_time(run, map_object, start)
    else:
        if not run.overwrite:
            _warn_known_map(run, map_object)
            # Simple registration is allowed. The map keeps the time of its
            # entry, so that time is checked against the dataset before any
            # other map of the run is written.
            if run.name:
                map_object.select(run.dbif, run.mapset)
                run.run_unit = _refuse_other_time(
                    run.sp, map_object, run.dbif, run.run_unit
                )
                run.stds_maps.append(map_object)
            return
        _reload_known_map(run, map_object)

    # Load the data from the grass file database
    map_object.load()

    # Try to read an existing time stamp from the grass spatial database in
    # case this map wasn't already registered in the temporal database. This
    # is done only if no time stamp was provided for this map as method
    # argument or in the input file.
    if not is_in_db and not start:
        map_object.read_timestamp_from_grass()

    if start:
        assign_valid_time_to_map(
            ttype=map_object.get_temporal_type(),
            map_object=map_object,
            start=start,
            end=end,
            unit=run.unit,
            increment=row_increment,
            mult=count,
            interval=run.interval,
        )

    # A semantic label of the input file is set after all maps were checked,
    # because it is written to the GRASS database at once. Without one, the
    # label is read from the GRASS database (only raster type supported).
    if not row.semantic_label:
        map_object.read_semantic_label_from_grass()

    _check_zone_consistency(run, map_object)

    # The dataset refuses a map of another temporal type or relative unit
    # when it registers it, which is after the map was written. The same
    # tests come first, with the messages of the dataset.
    if run.name:
        run.run_unit = _refuse_other_time(run.sp, map_object, run.dbif, run.run_unit)

    run.to_write.append((map_object, is_in_db, row.semantic_label))
    if run.name:
        run.stds_maps.append(map_object)


def _write_maps(run):
    """Enter the checked maps into the temporal database

    Writing starts after all maps were checked: insert() and update_all()
    write the time stamp of the map at once, even with execute=False, so a
    refusal later in the list would leave the maps before it changed.
    """
    dbif = run.dbif
    statement = ""
    for count, (map_object, is_in_db, semantic_label) in enumerate(
        run.to_write, start=1
    ):
        if semantic_label:
            # semantic label defined in input file
            # -> update raster metadata
            # -> write band identifier to GRASS data base
            map_object.set_semantic_label(semantic_label)

        if is_in_db:
            statement += map_object.update_all(dbif=dbif, execute=False)
        else:
            statement += map_object.insert(dbif=dbif, execute=False)

        # Sqlite3 performance is better for huge datasets when committing in
        # small chunks
        if dbif.get_dbmi().__name__ == "sqlite3" and count % 100 == 0 and statement:
            dbif.execute_transaction(statement)
            statement = ""

    if statement:
        dbif.execute_transaction(statement)


def _register_in_stds(run, msgr, update_cmd_list):
    """Register the maps in the dataset and update the dataset"""
    if not (run.name and run.stds_maps):
        return
    num_maps = len(run.stds_maps)
    for count, map_object in enumerate(run.stds_maps):
        if count % 50 == 0:
            msgr.percent(count, num_maps, 1)
        run.sp.register_map(map=map_object, dbif=run.dbif)

    run.sp.update_from_registered_maps(run.dbif)
    if update_cmd_list is True:
        run.sp.update_command_string(dbif=run.dbif)


def _update_other_stds(run):
    """Update the datasets that held maps which were updated"""
    for dataset in run.other_datasets:
        ds = dataset_factory(stds_kind_of(run.type).name, dataset)
        ds.select(run.dbif)
        ds.update_from_registered_maps(run.dbif)


def register_maps_in_space_time_dataset(
    type: str,
    name: str | None = None,
    maps=None,
    file=None,
    start=None,
    end=None,
    unit=None,
    increment=None,
    *,
    dbif: SQLDatabaseInterfaceConnection | None = None,
    interval: bool = False,
    fs: str = "|",
    update_cmd_list: bool = True,
) -> None:
    """Use this method to register maps in space time datasets.

    Additionally a start time string and an increment string can be
    specified to assign a time interval automatically to the maps.

    It takes care of the correct update of the space time datasets from all
    registered maps.

    :param type: The type of the maps raster, raster_3d or vector
    :param name: The name of the space time dataset. Maps will be
                 registered in the temporal database if the name was set
                 to None
    :param maps: A comma separated list of map names
    :param file: Input file, one map per line map with start and optional
                end time, or the same as io object (with readline capability)
    :param start: The start date and time of the first map
                 (format absolute: "yyyy-mm-dd HH:MM:SS" or "yyyy-mm-dd",
                 format relative is integer 5)
    :param end: The end date and time of the first map
               (format absolute: "yyyy-mm-dd HH:MM:SS" or "yyyy-mm-dd",
               format relative is integer 5)
    :param unit: The unit of the relative time: years, months, days,
                hours, minutes, seconds
    :param increment: Time increment between maps for time stamp creation
                     (format absolute: NNN seconds, minutes, hours, days,
                     weeks, months, years; format relative: 1.0)
    :param dbif: The database interface to be used (deprecated,
                will be removed in future versions)
    :param interval: If True, time intervals are created in case the start
                    time and an increment is provided
    :param fs: Field separator used in input file
    :param update_cmd_list: If is True, the command that was invoking this
                            process will be written to the process history
    """
    overwrite = gs.overwrite()

    msgr = get_tgis_message_interface()

    msgr.debug(1, "register_maps_in_space_time_dataset()")

    start, end, increment = _check_arguments(
        type, maps, file, start, end, increment, interval
    )

    if dbif is not None:
        msgr.warning(
            _(
                "The dbif argument is deprecated and will be removed in a future release."
            )
        )
    # Create a new DB connection only for the current mapset
    mapset = get_current_mapset()
    dbif = SQLDatabaseInterfaceConnection(mapsets=mapset)
    dbif.connect()

    try:
        # The name of the space time dataset is optional
        sp = _open_dataset(name, type, mapset, start, end, unit, dbif)

        rows = _map_rows(maps, file, fs, sp, type, increment, interval)
        num_maps = len(rows)

        run = _Run(
            type=type,
            name=name,
            sp=sp,
            dbif=dbif,
            mapset=mapset,
            overwrite=overwrite,
            unit=unit,
            increment=increment,
            interval=interval,
            option_start=start,
            option_end=end,
        )
        if name and sp.is_time_absolute():
            run.zone_aware = _dataset_zone(sp, dbif)

        msgr.debug(2, "Gathering map information...")

        for count, row in enumerate(rows):
            if count % 50 == 0:
                msgr.percent(count, num_maps, 1)
            _validate_map(run, count, row)

        _write_maps(run)

        msgr.percent(num_maps, num_maps, 1)

        _register_in_stds(run, msgr, update_cmd_list)
        _update_other_stds(run)
    finally:
        dbif.close()

    total = len(run.stds_maps) if name and run.stds_maps else num_maps
    msgr.percent(total, total, 1)


###############################################################################


def _absolute_times(start, end, increment, mult, interval):
    """The start and end time of an absolute map; the end may be None"""
    msgr = get_tgis_message_interface()
    start_time = string_to_datetime(start)
    if start_time is None:
        msgr.fatal(
            _('Unable to convert string "{}" into a datetime object').format(start)
        )
    end_time = None

    if end:
        end_time = string_to_datetime(end)
        if end_time is None:
            msgr.fatal(
                _('Unable to convert string "{}" into a datetime object').format(end)
            )

    # Add the increment
    if increment:
        anchor = start_time
        start_time = increment_datetime_by_string(anchor, increment, mult)
        if start_time is None:
            msgr.fatal(_("Error occurred in increment computation"))
        if interval:
            # The end of a map is the start of the next one, counted from
            # the anchor like that start. One increment added to the start
            # would end a map of a series from January 31 on March 28 where
            # the next map starts on March 31, and would not meet the next
            # start of a list increment either, because the calendar step
            # is cut to the month end once per start.
            end_time = increment_datetime_by_string(anchor, increment, mult + 1)
            if end_time is None:
                msgr.fatal(_("Error occurred in increment computation"))
    return start_time, end_time


def _relative_times(start, end, increment, mult, interval):
    """The start and end time of a relative map; the end may be None"""
    start_time = int(start)
    end_time = int(end) if end else None

    if increment:
        start_time += mult * int(increment)
        if interval:
            end_time = start_time + int(increment)
    return start_time, end_time


def assign_valid_time_to_map(
    ttype, map_object, start, end, unit, increment=None, mult=1, interval: bool = False
) -> None:
    """Assign the valid time to a map dataset

    :param ttype: The temporal type which should be assigned
                  and which the time format is of
    :param map_object: A map dataset object derived from abstract_map_dataset
    :param start: The start date and time of the first map
                  (format absolute: "yyyy-mm-dd HH:MM:SS" or "yyyy-mm-dd",
                  format relative is integer 5)
    :param end: The end date and time of the first map
                (format absolute: "yyyy-mm-dd HH:MM:SS" or "yyyy-mm-dd",
                format relative is integer 5)
    :param unit: The unit of the relative time: years, months,
                 days, hours, minutes, seconds
    :param increment: Time increment between maps for time stamp creation
                     (format absolute: NNN seconds, minutes, hours, days,
                     weeks, months, years; format relative is integer 1)
    :param mult: A multiplier for the increment
    :param interval: If True, time intervals are created in case the start
                     time and an increment is provided. With an increment of
                     one unit, such as "1 months", the interval ends at the
                     start of the next map, mult + 1 increments after the
                     anchor, also for a composite increment such as
                     "1 months, 1 days".
    """

    msgr = get_tgis_message_interface()

    if ttype == "absolute":
        start_time, end_time = _absolute_times(start, end, increment, mult, interval)
        if map_object.get_layer():
            msgr.debug(
                1,
                _(
                    "Set absolute valid time for map <{id}> with layer {layer} "
                    "to {start} - {end}"
                ).format(
                    id=map_object.get_map_id(),
                    layer=map_object.get_layer(),
                    start=str(start_time),
                    end=str(end_time),
                ),
            )
        else:
            msgr.debug(
                1,
                _(
                    "Set absolute valid time for map <{mid}> to {start_time} - {end_time}"
                ).format(
                    mid=map_object.get_map_id(),
                    start_time=str(start_time),
                    end_time=str(end_time),
                ),
            )
        map_object.set_absolute_time(start_time, end_time)
    else:
        start_time, end_time = _relative_times(start, end, increment, mult, interval)
        if map_object.get_layer():
            msgr.debug(
                1,
                _(
                    "Set relative valid time for map <{mid}> with layer"
                    " {layer} to {start} - {end} with unit {unit}"
                ).format(
                    mid=map_object.get_map_id(),
                    layer=map_object.get_layer(),
                    start=start_time,
                    end=str(end_time),
                    unit=unit,
                ),
            )
        else:
            msgr.debug(
                1,
                _(
                    "Set relative valid time for map <{mid}> to {start} - {end} "
                    "with unit {unit}"
                ).format(
                    mid=map_object.get_map_id(),
                    start=start_time,
                    end=str(end_time),
                    unit=unit,
                ),
            )
        map_object.set_relative_time(start_time, end_time, unit)


##############################################################################


def _is_empty(map_layer, map_kind):
    """True for a raster map without values or a vector map without primitives"""
    if map_kind in {"raster", "raster3d"}:
        return (
            map_layer.metadata.get_min() is None
            and map_layer.metadata.get_max() is None
        )
    if map_kind == "vector":
        return map_layer.metadata.get_number_of_primitives() == 0
    return False


def _write_register_file(path, type, map_list, delete_empty):
    """Write the maps with their times to a file for the registration

    :return: The empty maps, which are left out of the file if delete_empty
    """
    empty_maps = []
    kind = find_kind(type)
    map_kind = kind.name if kind else None
    with open(path, "w") as register_file:
        for map_layer in map_list:
            # Read the map data
            map_layer.load()
            # In case of a empty map continue, do not register empty maps
            if delete_empty and _is_empty(map_layer, map_kind):
                empty_maps.append(map_layer)
                continue

            start, end = map_layer.get_temporal_extent_as_tuple()
            if not end:
                end = start
            register_file.write(f"{map_layer.get_id()}|{start}|{end}\n")
    return empty_maps


def _remove_empty_maps(empty_maps, dbif):
    """Remove empty maps from the GRASS database and the temporal database"""
    import grass.pygrass.modules as pymod

    g_remove_types = {"raster": "raster", "raster3d": "raster_3d", "vector": "vector"}
    g_remove = pymod.Module("g.remove", flags="f", quiet=True, run_=False, finish_=True)
    for map_object in empty_maps:
        mod = copy.deepcopy(g_remove)
        if map_object.get_name():
            g_remove_type = g_remove_types.get(map_object.get_type())
            if g_remove_type:
                mod(type=g_remove_type, name=map_object.get_name())
            mod.run()
        if map_object.is_in_db(dbif):
            map_object.delete(dbif)


def register_map_object_list(
    type, map_list, output_stds, delete_empty: bool = False, unit=None, dbif=None
) -> None:
    """Register a list of AbstractMapDataset objects in the temporal database
    and optional in a space time dataset.

    :param type: The type of the map layer (raster, raster_3d, vector)
    :param map_list: List of AbstractMapDataset objects
    :param output_stds: The output stds
    :param delete_empty: Set True to delete empty map layer found in the map_list
    :param unit: The temporal unit of the space time dataset
    :param dbif: The database interface to be used

    """
    with connection(None) as dbif:
        filename = gs.tempfile(True)
        empty_maps = _write_register_file(filename, type, map_list, delete_empty)

        output_stds_id = output_stds.get_id() if output_stds else None

        register_maps_in_space_time_dataset(
            type,
            output_stds_id,
            unit=unit,
            file=filename,
        )

        # Remove empty maps and unregister them from the temporal database
        _remove_empty_maps(empty_maps, dbif)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
