"""The two generic dataset classes of the temporal framework

A map (raster, 3D raster, vector) and a space time dataset (strds, str3ds,
stvds) differ between the types only in the kind they have: the names of
their tables, the prefix of the C interface and the register of the maps.
MapDataset and StdsDataset read all of that from the class attribute kind,
so the six public classes in space_time_datasets.py state their kind and what
is really their own.

SPDX-FileCopyrightText: 2012-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import getpass
from abc import abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

from .abstract_map_dataset import AbstractMapDataset
from .abstract_space_time_dataset import AbstractSpaceTimeDataset
from .base import BaseRow, RegisterRow
from .c_libraries_interface import INVALID_TIMESTAMP
from .metadata import MetadataRow
from .spatial_extent import SpatialExtentRow
from .temporal_extent import AbsoluteTimeRow, RelativeTimeRow

if TYPE_CHECKING:
    from .kinds import Kind

_C_MONTHS = {
    name: number
    for number, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov")
        + ("Dec",),
        start=1,
    )
}


# Each kind has the whole sentence of each message rather than one sentence
# with the name of the kind inserted, so that translators can inflect it.
def _cannot_read_timestamp(kind: str) -> str:
    return {
        "raster": _("Unable to read timestamp file for raster map <%s>"),
        "raster3d": _("Unable to read timestamp file for 3D raster map <%s>"),
        "vector": _("Unable to read timestamp file for vector map <%s>"),
    }[kind]


def _stored_timestamp_is_not_a_time(kind: str) -> str:
    """Return the message for a stored text that is no valid date or time.

    The message is a str.format() template with the fields map and text.
    """
    return {
        "raster": _(
            "The timestamp of raster map <{map}> is not a valid date or time: <{text}>"
        ),
        "raster3d": _(
            "The timestamp of 3D raster map <{map}> is not a valid date or time: <{text}>"
        ),
        "vector": _(
            "The timestamp of vector map <{map}> is not a valid date or time: <{text}>"
        ),
    }[kind]


def _cannot_create_timestamp(kind: str) -> str:
    return {
        "raster": _("Unable to create timestamp file for raster map <%s>"),
        "raster3d": _("Unable to create timestamp file for 3D raster map <%s>"),
        "vector": _("Unable to create timestamp file for vector map <%s>"),
    }[kind]


def _invalid_timestamp(kind: str) -> str:
    return {
        "raster": _("Invalid datetime in timestamp for raster map <%s>"),
        "raster3d": _("Invalid datetime in timestamp for 3D raster map <%s>"),
        "vector": _("Invalid datetime in timestamp for vector map <%s>"),
    }[kind]


def _cannot_remove_timestamp(kind: str) -> str:
    return {
        "raster": _("Unable to remove timestamp for raster map <%s>"),
        "raster3d": _("Unable to remove timestamp for 3D raster map <%s>"),
        "vector": _("Unable to remove timestamp for vector map <%s>"),
    }[kind]


# The public class of each kind. get_new_instance() and its relatives return
# exactly this class, also when they are called on a subclass of it.
_CLASSES: dict[str, type] = {}


def class_of_kind(name: str) -> type:
    """Return the public class of the kind with the canonical name

    The classes enter the table when space_time_datasets is imported. That
    module imports this one, so it is imported here, when the table is read,
    and not at the top.
    """
    from . import space_time_datasets  # noqa: F401, PLC0415

    return _CLASSES[name]


def _register(cls: type) -> None:
    """Enter a class that states its own kind as the class of that kind"""
    if "kind" in cls.__dict__:
        _CLASSES[cls.kind.name] = cls


def parse_c_creation_time(text: str) -> datetime:
    """Read the creation time of the GRASS C library

    The format is "Mon Jan  1 12:00:00 2001".

    The names of the month and the weekday are always English there.
    datetime.strptime() with %a and %b would read them in the language of the
    locale of the process, so a German session could not read its own maps.
    The weekday is not needed for the date and is not checked.

    :raises ValueError: if the text is not such a time
    """
    parts = text.split()
    if len(parts) != 5 or parts[1] not in _C_MONTHS:
        msg = f"Not a creation time of the C library: {text!r}"
        raise ValueError(msg)
    _weekday, month, day, clock, year = parts
    return datetime.strptime(
        f"{year}-{_C_MONTHS[month]}-{day} {clock}", "%Y-%m-%d %H:%M:%S"
    )


class MapDataset(AbstractMapDataset):
    """A raster, 3D raster or vector map of the temporal database

    A subclass sets kind and implements _fill_from_info(), which copies what
    the C library knows about a map of its type into the metadata.
    """

    kind: Kind

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        _register(cls)

    def __init__(self, ident) -> None:
        super().__init__()
        self.reset(ident)

    def is_stds(self) -> bool:
        """Return True if this class is a space time dataset

        :return: True if this class is a space time dataset, False otherwise
        """
        return False

    def get_type(self) -> str:
        """Return the type of the map: raster, raster3d or vector"""
        return self.kind.name

    def get_new_instance(self, ident):
        """Return a new instance with the type of this class"""
        return _CLASSES[self.kind.name](ident)

    def get_new_stds_instance(self, ident):
        """Return a new space time dataset instance for maps of this class type."""
        return _CLASSES[self.kind.stds_kind](ident)

    def reset(self, ident) -> None:
        """Reset the internal structure and set the identifier"""
        self.base = BaseRow(self.kind, ident=ident)
        self.absolute_time = AbsoluteTimeRow(self.kind, ident=ident)
        self.relative_time = RelativeTimeRow(self.kind, ident=ident)
        self.spatial_extent = SpatialExtentRow(self.kind, ident=ident)
        self.metadata = MetadataRow(self.kind, ident=ident)
        self.stds_register = RegisterRow(self.kind, ident=ident)

    def _call(self, function: str, layer=None, **extra):
        """Call a function of the C interface for this map"""
        return self.ciface.call(
            function,
            self.kind.ciface_prefix,
            self.get_name(),
            self.get_mapset(),
            layer,
            **extra,
        )

    def _layer(self):
        """Return the layer of a vector map, None for any other map"""
        return self.base.get_layer() if self.kind.has_layer else None

    def has_grass_timestamp(self):
        """Check if a grass file based time stamp exists for this map.

        :return: True if success, False on error
        """
        return self._call("has_timestamp", self._layer())

    def read_timestamp_from_grass(self) -> bool:
        """Read the timestamp of this map from the map metadata.

        The metadata live in the GRASS file system based spatial database. The internal
        time stamp that is inserted or updated in the temporal database is set from it.

        A stored timestamp that is no valid absolute or relative time ends
        with a fatal message that names the map and the stored text.

        :return: True if success, False on error
        """
        if not self.has_grass_timestamp():
            return False

        check, dates = self._call("read_timestamp", self._layer())

        if check == INVALID_TIMESTAMP:
            # The C library read a text it cannot turn into a time (such as
            # "5"); dates is that text. Stopping here keeps register and the
            # other readers from going on with a map that has no usable time.
            self.msgr.fatal(
                _stored_timestamp_is_not_a_time(self.kind.name).format(
                    map=self.get_map_id(), text=dates
                )
            )

        if check == -2:
            # The C library cannot parse the file at all. The stored text is
            # not at hand here (the file name is known to libgis only), so the
            # message names the map and says the file cannot be read; it is
            # fatal for the same reason as above.
            self.msgr.fatal(_cannot_read_timestamp(self.kind.name) % self.get_map_id())

        if check < 1:
            self.msgr.error(_cannot_read_timestamp(self.kind.name) % self.get_map_id())
            return False

        if len(dates) == 2:
            self.set_absolute_time(dates[0], dates[1])
        else:
            self.set_relative_time(dates[0], dates[1], dates[2])

        return True

    def write_timestamp_to_grass(self) -> bool:
        """Write the timestamp of this map into the map metadata.

        The metadata live in the GRASS file system based spatial database.

        Internally the libgis API functions are used for writing

        :return: True if success, False on error
        """
        check = self._call(
            "write_timestamp", self._layer(), timestring=self._convert_timestamp()
        )

        if check == -1:
            self.msgr.error(
                _cannot_create_timestamp(self.kind.name) % self.get_map_id()
            )
            return False

        if check == -2:
            self.msgr.error(_invalid_timestamp(self.kind.name) % self.get_map_id())
            return False

        if check == -3:
            self.msgr.error(_("Internal error"))
            return False

        return True

    def remove_timestamp_from_grass(self) -> bool:
        """Remove the timestamp from the grass file system based spatial database

        Internally the libgis API functions are used for removal

        :return: True if success, False on error
        """
        check = self._call("remove_timestamp", self._layer())

        if check == -1:
            self.msgr.error(_cannot_remove_timestamp(self.kind.name) % self.get_name())
            return False

        return True

    def map_exists(self):
        """Return True in case the map exists in the grass spatial database

        :return: True if map exists, False otherwise
        """
        return self._call("map_exists")

    @abstractmethod
    def _fill_from_info(self, kvp) -> None:
        """Copy the extent and the metadata of the map info into this map

        :param kvp: The key value pairs of the C library for a map of this type
        """

    def load(self) -> bool:
        """Load all info from an existing map into the internal structure

        This method checks first if the map exists, in case it exists
        the metadata of the map is put into this object and True is returned

        :return: True is the map exists and the metadata was filled
                 successfully and getting the data was successful,
                 False otherwise
        """
        if self.map_exists() is not True:
            return False

        # Fill base information
        kvp = self._call("read_history")

        if kvp:
            self.base.set_creator(kvp["creator"])
            self.base.set_ctime(parse_c_creation_time(kvp["creation_time"]))
        else:
            self.base.set_creator(str(getpass.getuser()))
            self.base.set_ctime()

        kvp = self._call("read_info")

        if not kvp:
            return False

        self._fill_from_info(kvp)
        return True


class StdsDataset(AbstractSpaceTimeDataset):
    """A space time dataset of raster, 3D raster or vector maps

    A subclass sets kind, which is the kind of the dataset and tells
    through map_kind the kind of the maps it holds.
    """

    kind: Kind

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        _register(cls)

    def is_stds(self) -> bool:
        """Return True if this class is a space time dataset

        :return: True if this class is a space time dataset, False otherwise
        """
        return True

    def get_type(self) -> str:
        """Return the type of the dataset: strds, str3ds or stvds"""
        return self.kind.name

    def get_new_instance(self, ident):
        """Return a new instance with the type of this class"""
        return _CLASSES[self.kind.name](ident)

    def get_new_map_instance(self, ident):
        """Return a new map dataset instance associated with the type of this class"""
        return _CLASSES[self.kind.map_kind](ident)

    def get_map_register(self):
        """Return the name of the map register table"""
        return getattr(self.metadata, f"get_{self.kind.map_kind}_register")()

    def set_map_register(self, name) -> None:
        """Set the name of the map register table"""
        getattr(self.metadata, f"set_{self.kind.map_kind}_register")(name)

    def reset(self, ident) -> None:
        """Reset the internal structure and set the identifier"""
        self.base = BaseRow(self.kind, ident=ident)
        self.base.set_creator(str(getpass.getuser()))
        self.absolute_time = AbsoluteTimeRow(self.kind, ident=ident)
        self.relative_time = RelativeTimeRow(self.kind, ident=ident)
        self.spatial_extent = SpatialExtentRow(self.kind, ident=ident)
        self.metadata = MetadataRow(self.kind, ident=ident)
