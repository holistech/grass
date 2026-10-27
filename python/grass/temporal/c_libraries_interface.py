"""
Fast and exit-safe interface to GRASS C-library functions
using ctypes and multiprocessing

The C-library functions run in a subprocess, so that a G_fatal_error() ends
the subprocess and not the caller. A request is a tuple of the name of a
function, the kind of the map, its name, mapset and layer, and a dictionary
of further arguments. Every function the server offers is registered under
its name with the decorator :func:`_handler`.

SPDX-FileCopyrightText: 2013-2024 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import logging
import math
import sys
from ctypes import CFUNCTYPE, POINTER, byref, c_int, c_void_p, cast
from datetime import datetime
from typing import TYPE_CHECKING

import grass.lib.date as libdate
import grass.lib.gis as libgis
import grass.lib.raster as libraster
import grass.lib.raster3d as libraster3d
import grass.lib.temporal as libtgis
import grass.lib.vector as libvector
from grass.exceptions import FatalError
from grass.pygrass.rpc.base import RPCServerBase
from grass.pygrass.utils import decode
from grass.script.utils import _get_multiprocessing_context, encode
import grass.script as gs

if TYPE_CHECKING:
    from collections.abc import Callable
    from multiprocessing.connection import Connection
    from multiprocessing.synchronize import _LockLike


logger = logging.getLogger(__name__)

# The kinds of maps the server knows. The names are the prefixes of the
# methods of the client for the existence of a map, such as raster3d_map_exists.
_KINDS = ("raster", "raster3d", "vector")

# What a handler sends when it raises. A handler without an answer on error
# is one whose client would otherwise wait for ever; None would be an answer.
_NO_ANSWER = object()

# Name of a function -> (handler, answer sent when the handler raises)
_HANDLERS: dict[str, tuple[Callable[..., object], object]] = {}


def _handler(
    name: str, on_error: object = None
) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """Register a function of the server under name

    The handler is called with the keyword arguments kind, name, mapset and
    layer, and with the entries of the dictionary of the request; it returns
    the answer. The client always waits for one. When the handler raises, the
    answer on_error is sent before the exception ends the server, so that the
    client does not block, and the client starts a new server with its next
    call. The registration also fixes the name, so that the table of the
    names and the code that serves them cannot differ.
    """

    def register(function: Callable[..., object]) -> Callable[..., object]:
        if name in _HANDLERS:
            msg = f"The C-library function {name} is registered twice"
            raise ValueError(msg)
        _HANDLERS[name] = (function, on_error)
        return function

    return register


def _read_raster_info(name, mapset):
    """Read the raster map info from the file system and store the content
    into a dictionary

    This method uses the ctypes interface to the gis and raster libraries
    to read the map metadata information

    :param name: The name of the map
    :param mapset: The mapset of the map
    :returns: The key value pairs of the map specific metadata, or None in
              case of an error
    """

    kvp = {}

    if not libgis.G_find_raster(name, mapset):
        return None

    # Read the region information
    region = libraster.struct_Cell_head()
    libraster.Rast_get_cellhd(name, mapset, byref(region))

    kvp["north"] = region.north
    kvp["south"] = region.south
    kvp["east"] = region.east
    kvp["west"] = region.west
    kvp["nsres"] = region.ns_res
    kvp["ewres"] = region.ew_res
    kvp["rows"] = region.rows
    kvp["cols"] = region.cols

    maptype = libraster.Rast_map_type(name, mapset)

    if maptype == libraster.DCELL_TYPE:
        kvp["datatype"] = "DCELL"
    elif maptype == libraster.FCELL_TYPE:
        kvp["datatype"] = "FCELL"
    elif maptype == libraster.CELL_TYPE:
        kvp["datatype"] = "CELL"

    # Read range
    if libraster.Rast_map_is_fp(name, mapset):
        range_ = libraster.FPRange()
        libraster.Rast_init_fp_range(byref(range_))
        ret = libraster.Rast_read_fp_range(name, mapset, byref(range_))
        if ret < 0:
            logger.warning(_("Unable to read range file"))
            kvp["min"] = None
            kvp["max"] = None
        elif ret == 2:
            logger.info(_("Raster range file is empty"))
            kvp["min"] = None
            kvp["max"] = None
        else:
            min_ = libgis.DCELL()
            max_ = libgis.DCELL()
            libraster.Rast_get_fp_range_min_max(byref(range_), byref(min_), byref(max_))
            kvp["min"] = min_.value
            kvp["max"] = max_.value
    else:
        range_ = libraster.Range()
        libraster.Rast_init_range(byref(range_))
        ret = libraster.Rast_read_range(name, mapset, byref(range_))
        if ret < 0:
            logger.warning(_("Unable to read range file"))
            kvp["min"] = None
            kvp["max"] = None
        elif ret == 2:
            logger.info(_("Raster range file is empty"))
            kvp["min"] = None
            kvp["max"] = None
        else:
            min_ = libgis.CELL()
            max_ = libgis.CELL()
            libraster.Rast_get_range_min_max(byref(range_), byref(min_), byref(max_))
            kvp["min"] = min_.value
            kvp["max"] = max_.value

    return kvp


def _read_raster3d_info(name, mapset):
    """Read the 3D raster map info from the file system and store the content
    into a dictionary

    This method uses the ctypes interface to the gis and raster3d libraries
    to read the map metadata information

    :param name: The name of the map
    :param mapset: The mapset of the map
    :returns: The key value pairs of the map specific metadata, or None in
              case of an error
    """

    kvp = {}

    if not libgis.G_find_raster3d(name, mapset):
        return None

    # Read the region information
    region = libraster3d.RASTER3D_Region()
    libraster3d.Rast3d_read_region_map(name, mapset, byref(region))

    kvp["north"] = region.north
    kvp["south"] = region.south
    kvp["east"] = region.east
    kvp["west"] = region.west
    kvp["nsres"] = region.ns_res
    kvp["ewres"] = region.ew_res
    kvp["tbres"] = region.tb_res
    kvp["rows"] = region.rows
    kvp["cols"] = region.cols
    kvp["depths"] = region.depths
    kvp["top"] = region.top
    kvp["bottom"] = region.bottom

    # We need to open the map, this function returns a void pointer
    # but we may need the correct type which is RASTER3D_Map, hence
    # the casting
    g3map = cast(
        libraster3d.Rast3d_open_cell_old(
            name,
            mapset,
            libraster3d.RASTER3D_DEFAULT_WINDOW,
            libraster3d.RASTER3D_TILE_SAME_AS_FILE,
            libraster3d.RASTER3D_NO_CACHE,
        ),
        POINTER(libraster3d.RASTER3D_Map),
    )

    if not g3map:
        logger.error(_("Unable to open 3D raster map <%s>"), name)
        return None

    maptype = libraster3d.Rast3d_file_type_map(g3map)

    if maptype == libraster.DCELL_TYPE:
        kvp["datatype"] = "DCELL"
    elif maptype == libraster.FCELL_TYPE:
        kvp["datatype"] = "FCELL"

    # Read range
    min_ = libgis.DCELL()
    max_ = libgis.DCELL()
    ret = libraster3d.Rast3d_range_load(g3map)
    if not ret:
        logger.error(_("Unable to load range of 3D raster map <%s>"), name)
        return None
    libraster3d.Rast3d_range_min_max(g3map, byref(min_), byref(max_))

    if math.isnan(min_.value):
        kvp["min"] = None
    else:
        kvp["min"] = float(min_.value)
    if math.isnan(max_.value):
        kvp["max"] = None
    else:
        kvp["max"] = float(max_.value)

    if not libraster3d.Rast3d_close(g3map):
        logger.error(_("Unable to close 3D raster map <%s>"), name)
        return None

    return kvp


def _read_vector_info(name, mapset):
    """Read the vector map info from the file system and store the content
    into a dictionary

    This method uses the ctypes interface to the vector libraries
    to read the map metadata information

    :param name: The name of the map
    :param mapset: The mapset of the map
    :returns: The key value pairs of the map specific metadata, or None in
              case of an error
    """

    kvp = {}

    if not libgis.G_find_vector(name, mapset):
        return None

    # The vector map structure
    Map = libvector.Map_info()

    # We open the maps always in topology mode first
    libvector.Vect_set_open_level(2)
    with_topo = True

    # Code lend from v.info main.c
    if libvector.Vect_open_old_head2(byref(Map), name, mapset, "1") < 2:
        # force level 1, open fully
        # NOTE: number of points, lines, boundaries, centroids,
        # faces, kernels is still available
        libvector.Vect_set_open_level(1)  # no topology
        with_topo = False
        if libvector.Vect_open_old2(byref(Map), name, mapset, "1") < 1:
            logger.error(
                _("Unable to open vector map <%s>"),
                libvector.Vect_get_full_name(byref(Map)),
            )
            return None

    # Release the vector spatial index memory when closed
    libvector.Vect_set_release_support(byref(Map))

    # Read the extent information
    bbox = libvector.bound_box()
    libvector.Vect_get_map_box(byref(Map), byref(bbox))

    kvp["north"] = bbox.N
    kvp["south"] = bbox.S
    kvp["east"] = bbox.E
    kvp["west"] = bbox.W
    kvp["top"] = bbox.T
    kvp["bottom"] = bbox.B

    kvp["map3d"] = bool(libvector.Vect_is_3d(byref(Map)))

    # Read number of features
    if with_topo:
        kvp["points"] = libvector.Vect_get_num_primitives(
            byref(Map), libvector.GV_POINT
        )
        kvp["lines"] = libvector.Vect_get_num_primitives(byref(Map), libvector.GV_LINE)
        kvp["boundaries"] = libvector.Vect_get_num_primitives(
            byref(Map), libvector.GV_BOUNDARY
        )
        kvp["centroids"] = libvector.Vect_get_num_primitives(
            byref(Map), libvector.GV_CENTROID
        )
        kvp["faces"] = libvector.Vect_get_num_primitives(byref(Map), libvector.GV_FACE)
        kvp["kernels"] = libvector.Vect_get_num_primitives(
            byref(Map), libvector.GV_KERNEL
        )

        # Summarize the primitives
        kvp["primitives"] = (
            kvp["points"] + kvp["lines"] + kvp["boundaries"] + kvp["centroids"]
        )
        if kvp["map3d"]:
            kvp["primitives"] += kvp["faces"] + kvp["kernels"]

        # Read topology information
        kvp["nodes"] = libvector.Vect_get_num_nodes(byref(Map))
        kvp["areas"] = libvector.Vect_get_num_areas(byref(Map))
        kvp["islands"] = libvector.Vect_get_num_islands(byref(Map))
        kvp["holes"] = libvector.Vect_get_num_holes(byref(Map))
        kvp["volumes"] = libvector.Vect_get_num_primitives(
            byref(Map), libvector.GV_VOLUME
        )
    else:
        kvp["points"] = None
        kvp["lines"] = None
        kvp["boundaries"] = None
        kvp["centroids"] = None
        kvp["faces"] = None
        kvp["kernels"] = None
        kvp["primitives"] = None
        kvp["nodes"] = None
        kvp["areas"] = None
        kvp["islands"] = None
        kvp["holes"] = None
        kvp["volumes"] = None

    libvector.Vect_close(byref(Map))

    return kvp


def _read_raster_history(name, mapset):
    """Read the raster history from the file system and store the content
    into a dictionary

    This method uses the ctypes interface to the gis and raster libraries
    to read the map history

    :param name: The name of the map
    :param mapset: The mapset of the map
    :returns: The key value pairs of the map specific metadata, or None in
              case of an error
    """

    kvp = {}

    if not libgis.G_find_raster(name, mapset):
        return None

    # Read the raster history
    hist = libraster.History()
    ret = libraster.Rast_read_history(name, mapset, byref(hist))
    if ret < 0:
        logger.warning(_("Unable to read history file"))
        return None
    kvp["creation_time"] = decode(
        libraster.Rast_get_history(byref(hist), libraster.HIST_MAPID)
    )
    kvp["creator"] = decode(
        libraster.Rast_get_history(byref(hist), libraster.HIST_CREATOR)
    )

    return kvp


def _read_raster3d_history(name, mapset):
    """Read the 3D raster map info from the file system and store the content
    into a dictionary

    This method uses the ctypes interface to the gis and raster3d libraries
    to read the map metadata information

    :param name: The name of the map
    :param mapset: The mapset of the map
    :returns: The key value pairs of the map specific metadata, or None in
              case of an error
    """

    kvp = {}

    if not libgis.G_find_raster3d(name, mapset):
        return None

    # Read the region information
    hist = libraster.History()
    ret = libraster3d.Rast3d_read_history(name, mapset, byref(hist))
    if ret < 0:
        logger.warning(_("Unable to read history file"))
        return None
    kvp["creation_time"] = decode(
        libraster.Rast_get_history(byref(hist), libraster3d.HIST_MAPID)
    )
    kvp["creator"] = decode(
        libraster.Rast_get_history(byref(hist), libraster3d.HIST_CREATOR)
    )

    return kvp


def _read_vector_history(name, mapset):
    """Read the vector history from the file system and store the content
    into a dictionary

    This method uses the ctypes interface to the gis and raster libraries
    to read the map history

    :param name: The name of the map
    :param mapset: The mapset of the map
    :returns: The key value pairs of the map specific metadata, or None in
              case of an error
    """

    kvp = {}

    if not libgis.G_find_vector(name, mapset):
        return None

    # Read the vector history
    Map = libvector.Map_info()
    if libvector.Vect_open_old(byref(Map), name, mapset, "1") > 0:
        kvp["creation_time"] = decode(libvector.Vect_get_map_date(byref(Map)))
        kvp["creator"] = decode(libvector.Vect_get_person(byref(Map)))
    else:
        kvp = None
    libvector.Vect_close(byref(Map))

    return kvp


# The units a relative GRASS datetime can be written in, from the largest to the
# smallest, as the name and the field that holds the value.
_RELATIVE_UNITS = (
    (libdate.DATETIME_YEAR, "years", "year"),
    (libdate.DATETIME_MONTH, "months", "month"),
    (libdate.DATETIME_DAY, "days", "day"),
    (libdate.DATETIME_HOUR, "hours", "hour"),
    (libdate.DATETIME_MINUTE, "minutes", "minute"),
    (libdate.DATETIME_SECOND, "seconds", "second"),
)


def _relative_value(datetime_):
    """Return the signed value and the unit of a relative GRASS datetime

    A single value is read in the unit it was written in, so "0 days" is zero
    and not a missing value. A compound value such as "1 year 6 months" is
    read in its leading unit, or in the first unit that is not zero when the
    leading one is zero ("0 years 6 months" is six months, as it always was).
    The sign is the one of the C structure.
    """
    leading = getattr(datetime_, "from")
    # The constants grow from DATETIME_YEAR to DATETIME_SECOND
    units = [unit for unit in _RELATIVE_UNITS if unit[0] >= leading]
    if not units:
        return None, None
    _, name, field = next(
        (unit for unit in units if getattr(datetime_, unit[2]) != 0), units[0]
    )
    value = getattr(datetime_, field)
    return (value if datetime_.positive else -value), name


def _convert_timestamp_from_grass(ts):
    """Convert a GRASS file based timestamp into the temporal framework
    format datetime or integer.

    A tuple of two datetime objects (start, end) is returned in case of
    absolute time.
    In case of relative time a tuple with start time, end time and the
    relative unit (start, end, unit) will be returned.

    .. note::
        The end time will be set to None in case of a time instance.

    :param ts grass.lib.gis.TimeStamp object created by G_read_*_timestamp
    """

    dt1 = libgis.DateTime()
    dt2 = libgis.DateTime()
    count = c_int()

    libgis.G_get_timestamps(byref(ts), byref(dt1), byref(dt2), byref(count))

    if dt1.mode == libdate.DATETIME_ABSOLUTE:
        pdt1 = None
        pdt2 = None
        if count.value >= 1:
            pdt1 = datetime(
                int(dt1.year),
                int(dt1.month),
                int(dt1.day),
                int(dt1.hour),
                int(dt1.minute),
                int(dt1.second),
            )
        if count.value == 2:
            pdt2 = datetime(
                int(dt2.year),
                int(dt2.month),
                int(dt2.day),
                int(dt2.hour),
                int(dt2.minute),
                int(dt2.second),
            )

        # ATTENTION: We ignore the time zone
        # TODO: Write time zone support
        return (pdt1, pdt2)
    start = None
    end = None
    unit = None
    if count.value >= 1:
        start, unit = _relative_value(dt1)
    if count.value == 2:
        end, _end_unit = _relative_value(dt2)
    return (start, end, unit)


def _located(kind: str, name: str, layer, mapset) -> tuple:
    """Arguments that find a map in the G_*_timestamp functions

    Only the functions of the vector maps take a layer, between name and
    mapset.
    """
    return (name, layer, mapset) if kind == "vector" else (name, mapset)


@_handler("has_timestamp", on_error=False)
def _has_timestamp(*, kind, name, mapset, layer, **_):
    """Tell whether the file based GRASS timestamp of a map is present"""
    has = getattr(libgis, f"G_has_{kind}_timestamp")
    return has(*_located(kind, name, layer, mapset)) == 1


@_handler("read_timestamp", on_error=(False, None))
def _read_timestamp(*, kind, name, mapset, layer, **_):
    """Read the file based GRASS timestamp of a map

    The answer is a tuple (return value of G_read_*_timestamp, timestamps).
    Please have a look at the documentation of G_read_raster_timestamp,
    G_read_vector_timestamp and G_read_raster3d_timestamp for the return
    values.

    The timestamps are a tuple of values:

    - relative time (start, end, unit), start and end are of type integer,
      unit is of type string.
    - absolute time (start, end), start and end are of type datetime

    The end time may be None in case of a time instance.
    """
    ts = libgis.TimeStamp()
    read = getattr(libgis, f"G_read_{kind}_timestamp")
    check = read(*_located(kind, name, layer, mapset), byref(ts))
    return check, _convert_timestamp_from_grass(ts)


@_handler("write_timestamp", on_error=-3)
def _write_timestamp(*, kind, name, layer, timestring, **_):
    """Write the file based GRASS timestamp of a map

    The answer is the return value of G_write_*_timestamp, or -2 when
    timestring is not a datetime the C library reads.
    """
    ts = libgis.TimeStamp()
    if libgis.G_scan_timestamp(byref(ts), timestring) != 1:
        logger.error(
            "Unable to convert the timestamp: %(timestring)s",
            {"timestring": timestring},
        )
        return -2
    write = getattr(libgis, f"G_write_{kind}_timestamp")
    # Written maps are always of the current mapset, so there is no mapset.
    if kind == "vector":
        return write(name, layer, byref(ts))
    return write(name, byref(ts))


@_handler("remove_timestamp", on_error=False)
def _remove_timestamp(*, kind, name, mapset, layer, **_):
    """Remove the file based GRASS timestamp of a map

    The answer is the return value of G_remove_*_timestamp.
    """
    remove = getattr(libgis, f"G_remove_{kind}_timestamp")
    return remove(*_located(kind, name, layer, mapset))


@_handler("read_semantic_label")
def _read_semantic_label(*, kind, name, mapset, **_):
    """Read the file based GRASS band identifier of a raster map

    The answer is the semantic label, or None.
    """
    if kind != "raster":
        logger.error(
            "Unable to read semantic label. Unsupported map type %(maptype)s",
            {"maptype": kind},
        )
        return None
    # Must use temporary variable to work around
    # ValueError: ctypes objects containing pointers cannot be pickled
    ret = libraster.Rast_read_semantic_label(name, mapset)
    return decode(ret) if ret else None


@_handler("write_semantic_label", on_error=True)
def _write_semantic_label(*, kind, name, semantic_label, **_):
    """Write the file based GRASS band identifier of a raster map

    Raises ValueError on an invalid semantic label. The answer is always True.
    """
    if kind != "raster":
        logger.error(
            "Unable to write semantic label. Unsupported map type %(maptype)s",
            {"maptype": kind},
        )
        return True
    if libraster.Rast_legal_semantic_label(semantic_label) is False:
        raise ValueError(_("Invalid semantic label"))
    libraster.Rast_write_semantic_label(name, semantic_label)
    return True


@_handler("map_exists", on_error=False)
def _map_exists(*, kind, name, mapset, **_):
    """Tell whether a map exists in the spatial database

    A map object that was deleted has no name any more. The G_find functions
    take no NULL name, and a call with one ended the server.
    """
    if name is None:
        return False
    return bool(getattr(libgis, f"G_find_{kind}")(name, mapset))


@_handler("read_info")
def _read_map_info(*, kind, name, mapset, **_):
    """Read the metadata of a map with the C library

    The answer is a dictionary, or None in case of an error.
    """
    return _INFO_READERS[kind](name, mapset)


@_handler("read_history")
def _read_map_history(*, kind, name, mapset, **_):
    """Read the history of a map with the C library

    The answer is a dictionary with creation_time and creator, or None in
    case of an error.
    """
    return _HISTORY_READERS[kind](name, mapset)


@_handler("available_mapsets", on_error=[])
def _available_mapsets(**_):
    """Return all mapsets the user can access, the current one first"""
    mapset_list = gs.parse_command("g.mapsets", flags="p", format="json")["mapsets"]
    # We need to sort the mapset list, but the first one should be
    # the current mapset
    current_mapset = decode(libgis.G_mapset())
    if current_mapset in mapset_list:
        mapset_list.remove(current_mapset)
    mapset_list.sort()
    mapset_list.reverse()
    mapset_list.append(current_mapset)
    mapset_list.reverse()
    return mapset_list


@_handler("get_mapset", on_error=_NO_ANSWER)
def _get_mapset(**_):
    """Return the current mapset"""
    return decode(libgis.G_mapset())


@_handler("get_driver_name", on_error=_NO_ANSWER)
def _get_driver_name(*, mapset, **_):
    """Return the temporal database driver of a mapset

    The answer is None if no temporal database is present.
    """
    mapset = libgis.G_mapset() if not mapset else encode(mapset)
    return decode(libtgis.tgis_get_mapset_driver_name(mapset).data)


@_handler("get_database_name")
def _get_database_name(*, mapset, **_):
    """Return the temporal database name of a mapset

    The answer is None if no temporal database is present.
    """
    mapset = libgis.G_mapset() if not mapset else encode(mapset)
    dbstring = libtgis.tgis_get_mapset_database_name(mapset).data

    if dbstring:
        # We substitute GRASS variables if they are located in the database string
        # This behavior is in conjunction with db.connect
        dbstring = dbstring.replace(encode("$GISDBASE"), libgis.G_gisdbase())
        dbstring = dbstring.replace(encode("$LOCATION_NAME"), libgis.G_location())
        dbstring = dbstring.replace(encode("$MAPSET"), mapset)
    return decode(dbstring)


_INFO_READERS = {
    "raster": _read_raster_info,
    "raster3d": _read_raster3d_info,
    "vector": _read_vector_info,
}
_HISTORY_READERS = {
    "raster": _read_raster_history,
    "raster3d": _read_raster3d_history,
    "vector": _read_vector_history,
}


def c_library_server(lock: _LockLike, conn: Connection) -> None:
    """The GRASS C-libraries server function designed to be a target for
    multiprocessing.Process

    The server answers every request with exactly one message: the result of
    the handler registered under the name in the request, or a FatalError
    for a request that no handler serves. The message [0] ends the server, as
    for every RPCServerBase.

    :param lock: A multiprocessing.Lock
    :param conn: A multiprocessing.connection.Connection object obtained from
                 multiprocessing.Pipe
    """

    def error_handler(data) -> None:
        """This function will be called in case of a fatal error in libgis"""
        # We send an exception that will be handled in
        # the parent process, then close the pipe.
        conn.send(FatalError())
        conn.close()

    CALLBACK = CFUNCTYPE(c_void_p, c_void_p)
    CALLBACK.restype = c_void_p
    CALLBACK.argtypes = c_void_p

    cerror_handler = CALLBACK(error_handler)

    libgis.G_add_error_handler(cerror_handler, None)

    libgis.G_gisinit("c_library_server")
    libgis.G_debug(1, "Start C-interface server")

    while True:
        # Avoid busy waiting
        conn.poll(None)
        message = conn.recv()
        if message == [0]:
            libgis.G_debug(1, "Stop C-interface server")
            conn.close()
            sys.exit()
        well_formed = isinstance(message, (list, tuple)) and len(message) == 6
        function = message[0] if well_formed else None
        # The client waits for an answer, so a request that no function serves
        # gets an error instead of killing the server.
        if not isinstance(function, str) or function not in _HANDLERS:
            conn.send(FatalError(f"The C-library server has no function {function}"))
            continue
        handler, on_error = _HANDLERS[function]
        _, kind, name, mapset, layer, extra = message
        with lock:
            if kind is not None and kind not in _KINDS:
                logger.error(
                    "Unknown map type %(maptype)s in %(function)s",
                    {"maptype": kind, "function": function},
                )
                # A function without an answer on error would leave the
                # client waiting for ever.
                answer = (
                    FatalError(f"Unknown map type {kind} in {function}")
                    if on_error is _NO_ANSWER
                    else on_error
                )
            else:
                try:
                    answer = handler(
                        kind=kind, name=name, mapset=mapset, layer=layer, **extra
                    )
                except BaseException:
                    if on_error is not _NO_ANSWER:
                        conn.send(on_error)
                    raise
            if answer is not _NO_ANSWER:
                conn.send(answer)


class CLibrariesInterface(RPCServerBase):
    """Fast and exit-safe interface to GRASS C-libraries functions

    This class implements a fast and exit-safe interface to the GRASS
    gis, raster, 3D raster and vector  C-libraries functions.

    The C-libraries functions are called via ctypes in a subprocess
    using a pipe (multiprocessing.Pipe) to transfer the text messages.
    Hence, the process that uses the CLibrariesInterface will not be
    exited, if a G_fatal_error() was invoked in the subprocess.
    In this case the CLibrariesInterface object will simply start a
    new subprocess and restarts the pipeline.


    Usage:

    .. code-block:: pycon

        >>> import grass.script as gscript
        >>> import grass.temporal as tgis
        >>> gscript.use_temp_region()
        >>> gscript.run_command(
        ...     "g.region",
        ...     n=80.0,
        ...     s=0.0,
        ...     e=120.0,
        ...     w=0.0,
        ...     t=1.0,
        ...     b=0.0,
        ...     res=10.0,
        ...     res3=10.0,
        ... )
        >>> tgis.init()
        >>> gscript.run_command(
        ...     "r.mapcalc", expression="test = 1", overwrite=True, quiet=True
        ... )
        >>> gscript.run_command(
        ...     "r3.mapcalc", expression="test = 1", overwrite=True, quiet=True
        ... )
        >>> gscript.run_command(
        ...     "v.random", output="test", n=10, overwrite=True, quiet=True
        ... )
        >>> gscript.run_command(
        ...     "r.timestamp",
        ...     map="test",
        ...     date="12 Mar 1995 10:34:40",
        ...     overwrite=True,
        ...     quiet=True,
        ... )
        >>> gscript.run_command(
        ...     "r3.timestamp",
        ...     map="test",
        ...     date="12 Mar 1995 10:34:40",
        ...     overwrite=True,
        ...     quiet=True,
        ... )
        >>> gscript.run_command(
        ...     "v.timestamp",
        ...     map="test",
        ...     date="12 Mar 1995 10:34:40",
        ...     overwrite=True,
        ...     quiet=True,
        ... )

        # Check mapsets
        >>> ciface = tgis.c_libraries_interface.CLibrariesInterface()
        >>> mapsets = ciface.available_mapsets()
        >>> mapsets[0] == tgis.get_current_mapset()
        True

        # Raster map
        >>> ciface = tgis.c_libraries_interface.CLibrariesInterface()
        >>> check = ciface.raster_map_exists("test", tgis.get_current_mapset())
        >>> print(check)
        True
        >>> ciface.call("read_info", "raster", "test", tgis.get_current_mapset())
        {'north': 80.0, 'south': 0.0, 'east': 120.0, 'west': 0.0, 'nsres': 10.0, 'ewres': 10.0, 'rows': 8, 'cols': 12, 'datatype': 'CELL', 'min': 1, 'max': 1}

        >>> check = ciface.call(
        ...     "has_timestamp", "raster", "test", tgis.get_current_mapset()
        ... )
        >>> print(check)
        True
        >>> if check:
        ...     res = ciface.call(
        ...         "read_timestamp", "raster", "test", tgis.get_current_mapset()
        ...     )
        ...     if res[0]:
        ...         print(str(res[1][0]), str(res[1][0]))
        ...         ciface.call(
        ...             "remove_timestamp", "raster", "test", tgis.get_current_mapset()
        ...         )
        1995-03-12 10:34:40 1995-03-12 10:34:40
        1
        >>> ciface.call("has_timestamp", "raster", "test", tgis.get_current_mapset())
        False
        >>> ciface.call(
        ...     "write_timestamp",
        ...     "raster",
        ...     "test",
        ...     tgis.get_current_mapset(),
        ...     timestring="13 Jan 1999 14:30:05",
        ... )
        1
        >>> ciface.call("has_timestamp", "raster", "test", tgis.get_current_mapset())
        True


        # 3D raster map
        >>> check = ciface.raster3d_map_exists("test", tgis.get_current_mapset())
        >>> print(check)
        True
        >>> ciface.call("read_info", "raster3d", "test", tgis.get_current_mapset())
        {'north': 80.0, 'south': 0.0, 'east': 120.0, 'west': 0.0, 'nsres': 10.0, 'ewres': 10.0, 'tbres': 1.0, 'rows': 8, 'cols': 12, 'depths': 1, 'top': 1.0, 'bottom': 0.0, 'datatype': 'DCELL', 'min': 1.0, 'max': 1.0}
        >>> check = ciface.call(
        ...     "has_timestamp", "raster3d", "test", tgis.get_current_mapset()
        ... )
        >>> print(check)
        True
        >>> if check:
        ...     res = ciface.call(
        ...         "read_timestamp", "raster3d", "test", tgis.get_current_mapset()
        ...     )
        ...     if res[0]:
        ...         print(str(res[1][0]), str(res[1][0]))
        ...         ciface.call(
        ...             "remove_timestamp",
        ...             "raster3d",
        ...             "test",
        ...             tgis.get_current_mapset(),
        ...         )
        1995-03-12 10:34:40 1995-03-12 10:34:40
        1
        >>> ciface.call("has_timestamp", "raster3d", "test", tgis.get_current_mapset())
        False
        >>> ciface.call(
        ...     "write_timestamp",
        ...     "raster3d",
        ...     "test",
        ...     tgis.get_current_mapset(),
        ...     timestring="13 Jan 1999 14:30:05",
        ... )
        1
        >>> ciface.call("has_timestamp", "raster3d", "test", tgis.get_current_mapset())
        True


        # Vector map
        >>> check = ciface.vector_map_exists("test", tgis.get_current_mapset())
        >>> print(check)
        True
        >>> kvp = ciface.call("read_info", "vector", "test", tgis.get_current_mapset())
        >>> kvp["points"]
        10

        >>> check = ciface.call(
        ...     "has_timestamp", "vector", "test", tgis.get_current_mapset()
        ... )
        >>> print(check)
        True
        >>> if check:
        ...     res = ciface.call(
        ...         "read_timestamp", "vector", "test", tgis.get_current_mapset()
        ...     )
        ...     if res[0]:
        ...         print(str(res[1][0]), str(res[1][0]))
        ...         ciface.call(
        ...             "remove_timestamp", "vector", "test", tgis.get_current_mapset()
        ...         )
        1995-03-12 10:34:40 1995-03-12 10:34:40
        1
        >>> ciface.call("has_timestamp", "vector", "test", tgis.get_current_mapset())
        False
        >>> ciface.call(
        ...     "write_timestamp",
        ...     "vector",
        ...     "test",
        ...     tgis.get_current_mapset(),
        ...     timestring="13 Jan 1999 14:30:05",
        ... )
        1
        >>> ciface.call("has_timestamp", "vector", "test", tgis.get_current_mapset())
        True

        >>> ciface.get_driver_name()
        'sqlite'
        >>> ciface.get_database_name().split("/")[-1]
        'sqlite.db'

        >>> ciface.get_mapset() == tgis.get_current_mapset()
        True

        >>> ciface.stop()

        >>> gscript.del_temp_region()



    """  # noqa: E501

    def start_server(self) -> None:
        """Start the server process that calls the C libraries

        The client sends its requests through a pipe.
        """
        ctx = _get_multiprocessing_context()
        self.client_conn, self.server_conn = ctx.Pipe(True)
        self.lock = ctx.Lock()
        self.server = ctx.Process(
            target=c_library_server, args=(self.lock, self.server_conn)
        )
        self.server.daemon = True
        self.server.start()

    def call(
        self,
        function: str,
        kind: str | None = None,
        name: str | None = None,
        mapset: str | None = None,
        layer: str | None = None,
        **extra,
    ) -> object:
        """Call a function of the C-library server and return its answer

        The functions are the ones registered with the decorator _handler,
        such as ``has_timestamp``. Some of them have a method of this class, such
        as the one for the existence of a map; the timestamp, info and history
        functions are only called through this method.

        :param function: The name of the function of the server
        :param kind: The kind of the map: raster, raster3d or vector
        :param name: The name of the map
        :param mapset: The mapset of the map
        :param layer: The layer of a vector map
        :param extra: Further arguments of the function
        :returns: The answer of the function
        :raises FatalError: If the server has no such function or was
                            terminated by a fatal error
        """
        self.check_server()
        self.client_conn.send((function, kind, name, mapset, layer, extra))
        return self.safe_receive(function if kind is None else f"{function} {kind}")

    def raster_map_exists(self, name, mapset):
        """Check if a raster map exists in the spatial database

        :param name: The name of the map
        :param mapset: The mapset of the map
        :returns: True if exists, False if not
        """
        return self.call("map_exists", "raster", name, mapset)

    def read_raster_semantic_label(self, name, mapset):
        """Read a file based raster semantic label

        :param name: The name of the map
        :param mapset: The mapset of the map
        :returns: The return value of Rast_read_semantic_label, a string or None
        """
        return self.call("read_semantic_label", "raster", name, mapset)

    def write_raster_semantic_label(self, name, mapset, semantic_label):
        """Write a file based raster semantic label

        .. note::
            Only semantic labels of maps from the current mapset can be written.

        :param name: The name of the map
        :param mapset: The mapset of the map
        :param semantic_label: semantic label
        :returns: always True
        """
        return self.call(
            "write_semantic_label",
            "raster",
            name,
            mapset,
            semantic_label=semantic_label,
        )

    def raster3d_map_exists(self, name, mapset):
        """Check if a 3D raster map exists in the spatial database

        :param name: The name of the map
        :param mapset: The mapset of the map
        :returns: True if exists, False if not
        """
        return self.call("map_exists", "raster3d", name, mapset)

    def vector_map_exists(self, name, mapset):
        """Check if a vector map exists in the spatial database

        :param name: The name of the map
        :param mapset: The mapset of the map
        :returns: True if exists, False if not
        """
        return self.call("map_exists", "vector", name, mapset)

    def available_mapsets(self):
        """Return all available mapsets the user can access as a list of strings

        :returns: Names of available mapsets as list of strings
        """
        return self.call("available_mapsets")

    def get_driver_name(self, mapset=None):
        """Return the temporal database driver of a specific mapset

        :param mapset: Name of the mapset

        :returns: Name of the driver or None if no temporal database present
        """
        return self.call("get_driver_name", mapset=mapset)

    def get_database_name(self, mapset=None):
        """Return the temporal database name of a specific mapset

        :param mapset: Name of the mapset

        :returns: Name of the database or None if no temporal database present
        """
        return self.call("get_database_name", mapset=mapset)

    def get_mapset(self):
        """Return the current mapset

        :returns: Name of the current mapset
        """
        return self.call("get_mapset")
