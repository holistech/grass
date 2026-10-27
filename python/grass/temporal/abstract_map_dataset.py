"""
The abstract_map_dataset module provides the AbstractMapDataset class
that is the base class for all map layer.

SPDX-FileCopyrightText: 2011-2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from abc import ABCMeta, abstractmethod
from datetime import datetime
from fractions import Fraction

import grass.script as gs

from .abstract_dataset import AbstractDataset
from .base import check_identifier
from .datetime_math import (
    datetime_to_grass_datetime_string,
    decrement_datetime_by_string,
    increment_datetime_by_string,
)
from .db import connection, db_datetime
from .state import (
    get_current_mapset,
    get_enable_mapset_check,
    get_enable_timestamp_write,
    get_tgis_c_library_interface,
    get_tgis_message_interface,
)
from .temporal_extent import AbsoluteTemporalExtent, RelativeTemporalExtent


def layer_form(has_layer, with_layer, without_layer):
    """Pick the message of a map with a layer or the one of a map without

    A map with a layer has a sentence of its own rather than the plain one with
    words inserted, so that a translator can inflect it. Each caller passes
    both ``_()`` literals, so that the message ids are found in the source,
    and the condition that tells a layer: some callers test ``is not None``,
    some the truth value, and an empty layer counts as a layer in the first
    form only.
    """
    return with_layer if has_layer else without_layer


def other_temporal_type_message(stds_id: str, map_) -> str:
    """Return the message that a dataset and a map differ in the temporal type"""
    values = {"id": stds_id, "map": map_.get_map_id(), "l": map_.get_layer()}
    return (
        layer_form(
            values["l"],
            _(
                "Temporal type of space time dataset "
                "<%(id)s> and map <%(map)s> with layer %(l)s"
                " are different"
            ),
            _(
                "Temporal type of space time dataset <%(id)s> and map <%(map)s> are different"
            ),
        )
        % values
    )


def other_time_unit_message(stds_id: str, map_) -> str:
    """Return the message that a dataset and a map differ in the time unit"""
    values = {"id": stds_id, "map": map_.get_map_id(), "l": map_.get_layer()}
    return (
        layer_form(
            values["l"],
            _(
                "Relative time units of space time dataset "
                "<%(id)s> and map <%(map)s> with layer %(l)s"
                " are different"
            ),
            _(
                "Relative time units of space time dataset <%(id)s> and map <%(map)s> are different"
            ),
        )
        % values
    )


class AbstractMapDataset(AbstractDataset, metaclass=ABCMeta):
    """This is the base class for all maps (raster, vector, raster3d).

    The temporal extent, the spatial extent and the metadata of maps
    are stored in the temporal database. Maps can be registered in the
    temporal database, updated and deleted.

    This class provides all functionalities that are needed to manage maps
    in the temporal database. That are:

    - insert() to register the map and therefore its spatio-temporal extent
      and metadata in the temporal database
    - update() to update the map spatio-temporal extent and metadata in the
      temporal database
    - unregister() to unregister the map from each space time dataset in
      which this map is registered
    - delete() to remove the map from the temporal database
    - Methods to set relative and absolute time stamps
    - Abstract methods that must be implemented in the map specific
      subclasses

    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def ciface(self):
        """The C-library interface of the current session

        Fetched at each use: a session change replaces the C-library
        interface, and an object that kept the one of its construction would
        talk to the stopped server.
        """
        return get_tgis_c_library_interface()

    @abstractmethod
    def get_new_stds_instance(self, ident):
        """Return a new space time dataset instance that store maps with the
        type of this map object (raster, raster_3d or vector)

        :param ident: The identifier of the space time dataset
        :return: The new space time dataset instance
        """

    @abstractmethod
    def has_grass_timestamp(self):
        """Check if a grass file based time stamp exists for this map.

        :return: True is the grass file based time stamped exists for this map

        """

    @abstractmethod
    def write_timestamp_to_grass(self):
        """Write the timestamp of this map into the map metadata
        in the grass file system based spatial database.
        """

    @abstractmethod
    def read_timestamp_from_grass(self):
        """Read the timestamp of this map from the map metadata
        in the grass file system based spatial database and
        set the internal time stamp that should be insert/updated
        in the temporal database.
        """

    @abstractmethod
    def remove_timestamp_from_grass(self):
        """Remove the timestamp from the grass file
        system based spatial database
        """

    @abstractmethod
    def map_exists(self):
        """Return True in case the map exists in the grass spatial database

        :return: True if map exists, False otherwise
        """

    @abstractmethod
    def load(self):
        """Load the content of this object from the grass
        file system based database"""

    def _convert_timestamp(self):
        """Convert the valid time into a grass datetime library
        compatible timestamp string

        This methods works for relative and absolute time

        :return: the grass timestamp string
        """
        start = ""

        if self.is_time_absolute():
            start_time, end_time = self.get_absolute_time()
            start = datetime_to_grass_datetime_string(start_time)
            if end_time is not None:
                end = datetime_to_grass_datetime_string(end_time)
                start += f" / {end}"
        else:
            start_time, end_time, unit = self.get_relative_time()
            start = f"{int(start_time)} {unit}"
            if end_time is not None:
                end = f"{int(end_time)} {unit}"
                start += f" / {end}"

        return start

    def get_map_id(self):
        """Return the map id. The map id is the unique identifier
        in grass and must not be equal to the
        primary key identifier (id) of the map in the database.
        Since vector maps may have layer information,
        the unique id is a combination of name, layer and mapset.

        Use get_map_id() every time your need to access the grass map
        in the file system but not to identify
        map information in the temporal database.

        :return: The map id "name@mapset"
        """
        return self.base.get_map_id()

    @staticmethod
    def split_name(name: str, layer=None, mapset=None):
        """Convenient method to split a map name into three potentially
        contained parts: map name, map layer and mapset. For the layer and
        mapset, default keyword arguments can be given if not present in
        the name. Layer and mapset present in the name will overwrite
        the keyword arguments.

        :param name: The name of the map
        :param layer: The layer of the vector map, use None in case no layer exists
        :param mapset: The mapset in which the map is located

        :return: tuple of three elements name, layer, mapset e(:layer)@mapset" while
                 layer is optional
        """

        check_identifier(name)

        # Check if the name includes any mapset
        if name.find("@") >= 0:
            name, mapset = name.split("@")

        # Check for layer number in map name
        if name.find(":") >= 0:
            name, layer = name.split(":")

        return name, layer, mapset

    @staticmethod
    def build_id_from_search_path(name: str, element) -> str:
        """Convenient method to build the unique identifier while
        checking the current search path for the correct mapset.

        Existing mapset definitions in the name string will be reused.

        If an element type is given and the mapset is not specified in
        the name, the function will try to get the correct mapset by
        searching for a map with the given name and of the given element
        type on the current search path. If the combination is not found
        on the current search path, it will fail and throw an error.

        :param name: The name of the map
        :param element: A mapset element type to be passed to g.findfile,
                        e.g. "cell", "vector", "raster3d"

        :return: the id of the map as "name(:layer)@mapset" where layer is
                 optional
        """

        # Split given name into relevant parts
        name, layer, mapset = AbstractMapDataset.split_name(name)

        # Identify mapset of map with the given name of given element type
        if element and not mapset:
            result = gs.find_file(element=element, name=name)
            if result["mapset"]:
                mapset = result["mapset"]
            else:
                get_tgis_message_interface().fatal(
                    _(
                        "Map <{map_name}> of element type '{element}' not found "
                        "on search path"
                    ).format(element=element, map_name=name)
                )

        if layer is not None:
            return f"{name}:{layer}@{mapset}"
        return f"{name}@{mapset}"

    @staticmethod
    def build_id(name: str, mapset, layer=None) -> str:
        """Convenient method to build the unique identifier

        Existing layer and mapset definitions in the name
        string will be reused

        :param name: The name of the map
        :param mapset: The mapset in which the map is located
        :param layer: The layer of the vector map, use None in case no layer exists

        :return: the id of the map as "name(:layer)@mapset" where layer is optional
        """

        # Split given name into relevant parts
        name, layer, mapset = AbstractMapDataset.split_name(
            name, layer=layer, mapset=mapset
        )

        if layer is not None:
            return f"{name}:{layer}@{mapset}"
        return f"{name}@{mapset}"

    def get_layer(self):
        """Return the layer of the map

        :return: the layer of the map or None in case no layer is defined
        """
        return self.base.get_layer()

    def print_self(self) -> None:
        """Print the content of the internal structure to stdout"""
        self.base.print_self()
        self.temporal_extent.print_self()
        self.spatial_extent.print_self()
        self.metadata.print_self()
        self.stds_register.print_self()

    def print_info(self) -> None:
        """Print information about this object in human readable style"""

        if self.get_type() == "raster":
            #                1         2         3         4         5         6         7  # noqa: E501
            #      0123456789012345678901234567890123456789012345678901234567890123456789012345678  # noqa: E501
            print(
                " +-------------------- Raster Dataset ----------------------------------------+"  # noqa: E501
            )
        if self.get_type() == "raster3d":
            #                1         2         3         4         5         6         7  # noqa: E501
            #      0123456789012345678901234567890123456789012345678901234567890123456789012345678  # noqa: E501
            print(
                " +-------------------- 3D Raster Dataset -------------------------------------+"  # noqa: E501
            )
        if self.get_type() == "vector":
            #                1         2         3         4         5         6         7  # noqa: E501
            #      0123456789012345678901234567890123456789012345678901234567890123456789012345678  # noqa: E501
            print(
                " +-------------------- Vector Dataset ----------------------------------------+"  # noqa: E501
            )
        print(
            " |                                                                            |"  # noqa: E501
        )
        self.base.print_info()
        self.temporal_extent.print_info()
        if self.is_topology_build():
            self.print_topology_info()
        self.spatial_extent.print_info()
        self.metadata.print_info()
        datasets = self.get_registered_stds()
        count = 0
        string = ""
        if datasets is not None:
            for ds in datasets:
                if count > 0 and count % 3 == 0:
                    string += "\n | ............................ "
                    count = 0
                if count == 0:
                    string += ds
                else:
                    string += f",{ds}"
                count += 1
        print(" | Registered datasets ........ " + string)
        print(
            " +----------------------------------------------------------------------------+"  # noqa: E501
        )

    def print_shell_info(self) -> None:
        """Print information about this object in shell style"""
        self.base.print_shell_info()
        self.temporal_extent.print_shell_info()
        self.spatial_extent.print_shell_info()
        self.metadata.print_shell_info()
        datasets = self.get_registered_stds()
        count = 0
        string = ""
        if datasets is not None:
            for ds in datasets:
                if count == 0:
                    string += ds
                else:
                    string += f",{ds}"
                count += 1
            print("registered_datasets=" + string)

        if self.is_topology_build():
            self.print_topology_shell_info()

    def insert(self, dbif=None, execute: bool = True):
        """Insert the map content into the database from the internal
        structure

        This functions assures that the timestamp is written to the
        grass file system based database in addition to the temporal
        database entry. The stds register table will be created as well.
        Hence maps can only be registered in a space time dataset, when
        they were inserted in the temporal database beforehand.

        :param dbif: The database interface to be used
        :param execute: If True the SQL statements will be executed.
                        If False the prepared SQL statements are
                        returned and must be executed by the caller.
        :return: The SQL insert statement in case execute=False, or an
                 empty string otherwise
        """
        if get_enable_timestamp_write():
            self.write_timestamp_to_grass()
        return AbstractDataset.insert(self, dbif=dbif, execute=execute)

    def update(self, dbif=None, execute: bool = True):
        """Update the map content in the database from the internal structure
        excluding None variables

        This functions assures that the timestamp is written to the
        grass file system based database in addition to the temporal
        database entry.

        :param dbif: The database interface to be used
        :param execute: If True the SQL statements will be executed.
                        If False the prepared SQL statements are
                        returned and must be executed by the caller.
        :return: The SQL insert statement in case execute=False, or an
                 empty string otherwise
        """
        if get_enable_timestamp_write():
            self.write_timestamp_to_grass()
        return AbstractDataset.update(self, dbif, execute)

    def update_all(self, dbif=None, execute: bool = True):
        """Update the map content in the database from the internal structure
        including None variables

        This functions assures that the timestamp is written to the
        grass file system based database in addition to the temporal
        database entry.

        :param dbif: The database interface to be used
        :param execute: If True the SQL statements will be executed.
                        If False the prepared SQL statements are
                        returned and must be executed by the caller.
        :return: The SQL insert statement in case execute=False, or an
                 empty string otherwise

        """
        if get_enable_timestamp_write():
            self.write_timestamp_to_grass()
        return AbstractDataset.update_all(self, dbif, execute)

    def set_time_to_absolute(self) -> None:
        """Set the temporal type to absolute"""
        self.base.set_ttype("absolute")

    def set_time_to_relative(self) -> None:
        """Set the temporal type to relative"""
        self.base.set_ttype("relative")

    def set_absolute_time(self, start_time, end_time=None) -> bool:
        """Set the absolute time with start time and end time

         The end time is optional and must be set to None in case of time
         instance.

         This method only modifies this object and does not commit
         the modifications to the temporal database.

        :param start_time: A datetime object specifying the start time of the map
        :param end_time: A datetime object specifying the end time of the
                         map, None in case of a time instance

        :return: True for success and False otherwise
        """
        values = {
            "type": self.get_type(),
            "id": self.get_map_id(),
            "l": self.get_layer(),
        }
        if start_time and not isinstance(start_time, datetime):
            self.msgr.error(
                layer_form(
                    self.get_layer() is not None,
                    _(
                        "Start time must be of type datetime for "
                        "%(type)s map <%(id)s> with layer: %(l)s"
                    ),
                    _("Start time must be of type datetime for %(type)s map <%(id)s>"),
                )
                % values
            )
            return False

        if end_time and not isinstance(end_time, datetime):
            self.msgr.error(
                layer_form(
                    self.get_layer(),
                    _(
                        "End time must be of type datetime for "
                        "%(type)s map <%(id)s> with layer: %(l)s"
                    ),
                    _("End time must be of type datetime for %(type)s map <%(id)s>"),
                )
                % values
            )
            return False

        if start_time is not None and end_time is not None:
            if start_time > end_time:
                self.msgr.error(
                    layer_form(
                        self.get_layer(),
                        _(
                            "End time must be greater than start "
                            "time for %(type)s map <%(id)s> with "
                            "layer: %(l)s"
                        ),
                        _(
                            "End time must be greater than start "
                            "time for %(type)s map <%(id)s>"
                        ),
                    )
                    % values
                )
                return False
            # Do not create an interval in case start and end time are equal.
            # They are compared as the database stores them, in whole
            # seconds: an interval inside one second would otherwise be
            # written with equal times and refused when it is read back.
            if db_datetime(start_time) == db_datetime(end_time):
                end_time = None

        self.base.set_ttype("absolute")
        self.absolute_time.set_start_time(start_time)
        self.absolute_time.set_end_time(end_time)

        return True

    def _refuse_foreign_mapset(self) -> None:
        """Refuse to update a map of another mapset, if the mapset check is on"""
        if (
            get_enable_mapset_check() is True
            and self.get_mapset() != get_current_mapset()
        ):
            self.msgr.fatal(
                _(
                    "Unable to update dataset <%(ds)s> of type "
                    "%(type)s in the temporal database. The mapset "
                    "of the dataset does not match the current "
                    "mapset"
                )
                % {"ds": self.get_id(), "type": self.get_type()}
            )

    def _store_time(self, time_table, dbif) -> None:
        """Write the time just set to the database and the GRASS file system"""
        with connection(dbif) as dbif:
            time_table.update_all(dbif)
            self.base.update(dbif)

        if get_enable_timestamp_write():
            self.write_timestamp_to_grass()

    def update_absolute_time(self, start_time, end_time=None, dbif=None) -> None:
        """Update the absolute time

        The end time is optional and must be set to None in case of time
        instance.

        This functions assures that the timestamp is written to the
        grass file system based database in addition to the temporal
        database entry.

        :param start_time: A datetime object specifying the start time of the map
        :param end_time: A datetime object specifying the end time of the
                                     map, None in case of a time instance
        :param dbif: The database interface to be used
        """

        self._refuse_foreign_mapset()

        if self.set_absolute_time(start_time, end_time):
            self._store_time(self.absolute_time, dbif)

    def set_relative_time(self, start_time, end_time, unit) -> bool:
        """Set the relative time interval

         The end time is optional and must be set to None in case of time
         instance.

         This method only modifies this object and does not commit
         the modifications to the temporal database.

        :param start_time: A number; it is compared with the end time as
                           given and stored truncated toward zero
        :param end_time: A number, None in case of a time instance. An end
                         before the start is refused; an end that equals
                         the start after truncation makes a time instance.
        :param unit: The unit of the relative time. Supported units:
                     year(s), month(s), day(s), hour(s), minute(s), second(s)

        :return: True for success and False otherwise

        """
        # The layer form of the message about the end before the start names
        # the type "typ"; its message id stays as it is.
        values = {
            "type": self.get_type(),
            "typ": self.get_type(),
            "id": self.get_id(),
            "l": self.get_layer(),
            "u": unit,
        }
        if not self.check_relative_time_unit(unit):
            self.msgr.error(
                layer_form(
                    self.get_layer() is not None,
                    _(
                        "Unsupported relative time unit type for "
                        "%(type)s map <%(id)s> with layer %(l)s: "
                        "%(u)s"
                    ),
                    _(
                        "Unsupported relative time unit type for "
                        "%(type)s map <%(id)s>: %(u)s"
                    ),
                )
                % values
            )
            return False

        if start_time is not None and end_time is not None:
            # Compare before int() truncates: 1.7 to 1.2 would otherwise
            # both become 1 and pass as an instance. Fraction compares
            # exactly (float() rounds above 2**53) and takes numeric text as
            # a number ("10" before "9" as text).
            if Fraction(start_time) > Fraction(end_time):
                self.msgr.error(
                    layer_form(
                        self.get_layer() is not None,
                        _(
                            "End time must be greater than start "
                            "time for %(typ)s map <%(id)s> with "
                            "layer %(l)s"
                        ),
                        _(
                            "End time must be greater than start "
                            "time for %(type)s map <%(id)s>"
                        ),
                    )
                    % values
                )
                return False
            # Compare what is stored: both values go through int(), so an
            # interval inside one unit would otherwise be saved as an
            # interval whose start equals its end.
            if int(start_time) == int(end_time):
                end_time = None

        self.base.set_ttype("relative")

        self.relative_time.set_unit(unit)
        self.relative_time.set_start_time(int(start_time))
        if end_time is not None:
            self.relative_time.set_end_time(int(end_time))
        else:
            self.relative_time.set_end_time(None)

        return True

    def update_relative_time(self, start_time, end_time, unit, dbif=None) -> None:
        """Update the relative time interval

        The end time is optional and must be set to None in case of time
        instance.

        This functions assures that the timestamp is written to the
        grass file system based database in addition to the temporal
        database entry.

        :param start_time: A number; it is compared with the end time as
                           given and stored truncated toward zero
        :param end_time: A number, None in case of a time instance. An end
                         before the start is refused; an end that equals
                         the start after truncation makes a time instance.
        :param unit: The relative time unit
        :param dbif: The database interface to be used
        """
        self._refuse_foreign_mapset()

        if self.set_relative_time(start_time, end_time, unit):
            self._store_time(self.relative_time, dbif)

    def set_temporal_extent(self, extent) -> None:
        """Convenient method to set the temporal extent from a temporal extent
        object

        :param extent: The temporal extent that should be set for this object

        .. code-block:: pycon

            >>> import datetime
            >>> import grass.temporal as tgis
            >>> map = tgis.RasterDataset(None)
            >>> from grass.temporal.kinds import KINDS
            >>> temp_ext = tgis.temporal_extent.RelativeTimeRow(
            ...     KINDS["raster"], start_time=1, end_time=2, unit="years"
            ... )
            >>> map.set_temporal_extent(temp_ext)
            >>> print(map.get_temporal_extent_as_tuple())
            (1, 2)
            >>> map = tgis.VectorDataset(None)
            >>> temp_ext = tgis.temporal_extent.AbsoluteTimeRow(
            ...     KINDS["vector"],
            ...     start_time=datetime.datetime(2000, 1, 1),
            ...     end_time=datetime.datetime(2001, 1, 1),
            ... )
            >>> map.set_temporal_extent(temp_ext)
            >>> print(map.get_temporal_extent_as_tuple())
            (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2001, 1, 1, 0, 0))

            >>> map1 = tgis.VectorDataset("A@P")
            >>> check = map1.set_absolute_time(
            ...     datetime.datetime(2000, 5, 5), datetime.datetime(2005, 6, 6)
            ... )
            >>> print(map1.get_temporal_extent_as_tuple())
            (datetime.datetime(2000, 5, 5, 0, 0), datetime.datetime(2005, 6, 6, 0, 0))
            >>> map2 = tgis.RasterDataset("B@P")
            >>> check = map2.set_absolute_time(
            ...     datetime.datetime(1990, 1, 1), datetime.datetime(1999, 8, 1)
            ... )
            >>> print(map2.get_temporal_extent_as_tuple())
            (datetime.datetime(1990, 1, 1, 0, 0), datetime.datetime(1999, 8, 1, 0, 0))
            >>> map2.set_temporal_extent(map1.get_temporal_extent())
            >>> print(map2.get_temporal_extent_as_tuple())
            (datetime.datetime(2000, 5, 5, 0, 0), datetime.datetime(2005, 6, 6, 0, 0))

        """
        if issubclass(type(extent), RelativeTemporalExtent):
            start = extent.get_start_time()
            end = extent.get_end_time()
            unit = extent.get_unit()

            self.set_relative_time(start, end, unit)

        elif issubclass(type(extent), AbsoluteTemporalExtent):
            start = extent.get_start_time()
            end = extent.get_end_time()

            self.set_absolute_time(start, end)

    def temporal_buffer(self, increment, update: bool = False, dbif=None) -> None:
        """Create a temporal buffer based on an increment

        For absolute time the increment must be a string of type "integer
        unit"
        Unit can be year, years, month, months, day, days, hour, hours,
        minute, minutes, day or days.

        :param increment: This is the increment, a string in case of
                          absolute time or an integer in case of relative
                          time
        :param update: Perform an immediate database update to store the
                       modified temporal extent, otherwise only this object
                       will be modified

        Usage:

        .. code-block:: pycon

            >>> import grass.temporal as tgis
            >>> maps = []
            >>> for i in range(5):
            ...     map = tgis.RasterDataset(None)
            ...     if i % 2 == 0:
            ...         check = map.set_relative_time(i, i + 1, "years")
            ...     else:
            ...         check = map.set_relative_time(i, None, "years")
            ...     map.temporal_buffer(3)
            ...     maps.append(map)
            >>> for map in maps:
            ...     map.temporal_extent.print_info()
             +-------------------- Relative time -----------------------------------------+
             | Start time:................. -3
             | End time:................... 4
             | Relative time unit:......... years
             +-------------------- Relative time -----------------------------------------+
             | Start time:................. -2
             | End time:................... 4
             | Relative time unit:......... years
             +-------------------- Relative time -----------------------------------------+
             | Start time:................. -1
             | End time:................... 6
             | Relative time unit:......... years
             +-------------------- Relative time -----------------------------------------+
             | Start time:................. 0
             | End time:................... 6
             | Relative time unit:......... years
             +-------------------- Relative time -----------------------------------------+
             | Start time:................. 1
             | End time:................... 8
             | Relative time unit:......... years
            >>> maps = []
            >>> for i in range(1, 5):
            ...     map = tgis.RasterDataset(None)
            ...     if i % 2 == 0:
            ...         check = map.set_absolute_time(
            ...             datetime(2001, i, 1), datetime(2001, i + 1, 1)
            ...         )
            ...     else:
            ...         check = map.set_absolute_time(datetime(2001, i, 1), None)
            ...     map.temporal_buffer("7 days")
            ...     maps.append(map)
            >>> for map in maps:
            ...     map.temporal_extent.print_info()
             +-------------------- Absolute time -----------------------------------------+
             | Start time:................. 2000-12-25 00:00:00
             | End time:................... 2001-01-08 00:00:00
             +-------------------- Absolute time -----------------------------------------+
             | Start time:................. 2001-01-25 00:00:00
             | End time:................... 2001-03-08 00:00:00
             +-------------------- Absolute time -----------------------------------------+
             | Start time:................. 2001-02-22 00:00:00
             | End time:................... 2001-03-08 00:00:00
             +-------------------- Absolute time -----------------------------------------+
             | Start time:................. 2001-03-25 00:00:00
             | End time:................... 2001-05-08 00:00:00

        """  # noqa: E501

        if self.is_time_absolute():
            start, end = self.get_absolute_time()

            new_start = decrement_datetime_by_string(start, increment)
            if end is None:
                new_end = increment_datetime_by_string(start, increment)
            else:
                new_end = increment_datetime_by_string(end, increment)

            if update:
                self.update_absolute_time(new_start, new_end, dbif=dbif)
            else:
                self.set_absolute_time(new_start, new_end)
        else:
            start, end, unit = self.get_relative_time()
            new_start = start - increment
            new_end = start + increment if end is None else end + increment

            if update:
                self.update_relative_time(new_start, new_end, unit, dbif=dbif)
            else:
                self.set_relative_time(new_start, new_end, unit)

    def set_spatial_extent_from_values(
        self, north, south, east, west, top=0, bottom=0
    ) -> None:
        """Set the spatial extent of the map from values

         This method only modifies this object and does not commit
         the modifications to the temporal database.

        :param north: The northern edge
        :param south: The southern edge
        :param east: The eastern edge
        :param west: The western edge
        :param top: The top edge
        :param bottom: The bottom edge
        """
        self.spatial_extent.set_spatial_extent_from_values(
            north, south, east, west, top, bottom
        )

    def set_spatial_extent(self, spatial_extent) -> None:
        """Set the spatial extent of the map

         This method only modifies this object and does not commit
         the modifications to the temporal database.

         :param spatial_extent: An object of type SpatialExtent or its subclasses

        .. code-block:: pycon

            >>> import datetime
            >>> import grass.temporal as tgis
            >>> map = tgis.RasterDataset(None)
            >>> spat_ext = tgis.spatial_extent.SpatialExtent(
            ...     north=10, south=-10, east=20, west=-20, top=5, bottom=-5
            ... )
            >>> map.set_spatial_extent(spat_ext)
            >>> print(map.get_spatial_extent_as_tuple())
            (10.0, -10.0, 20.0, -20.0, 5.0, -5.0)

        """
        self.spatial_extent.set_spatial_extent(spatial_extent)

    def spatial_buffer(self, size, update: bool = False, dbif=None) -> None:
        """Buffer the spatial extent by a given size in all
        spatial directions.

        :param size: The buffer size, using the unit of the grass region
        :param update: If True perform an immediate database update, otherwise only the
                       internal variables are set
        :param dbif: The database interface to be used

        .. code-block:: pycon

            >>> import grass.temporal as tgis
            >>> map = tgis.RasterDataset(None)
            >>> spat_ext = tgis.spatial_extent.SpatialExtent(
            ...     north=10, south=-10, east=20, west=-20, top=5, bottom=-5
            ... )
            >>> map.set_spatial_extent(spat_ext)
            >>> map.spatial_buffer(10)
            >>> print(map.get_spatial_extent_as_tuple())
            (20.0, -20.0, 30.0, -30.0, 15.0, -15.0)

        """
        self.spatial_extent.north += size
        self.spatial_extent.south -= size
        self.spatial_extent.east += size
        self.spatial_extent.west -= size
        self.spatial_extent.top += size
        self.spatial_extent.bottom -= size

        if update:
            self.spatial_extent.update(dbif)

    def spatial_buffer_2d(self, size, update: bool = False, dbif=None) -> None:
        """Buffer the spatial extent by a given size in 2d
        spatial directions.

        :param size: The buffer size, using the unit of the grass region
        :param update: If True perform an immediate database update, otherwise only the
                       internal variables are set
        :param dbif: The database interface to be used

        .. code-block:: pycon

            >>> import grass.temporal as tgis
            >>> map = tgis.RasterDataset(None)
            >>> spat_ext = tgis.spatial_extent.SpatialExtent(
            ...     north=10, south=-10, east=20, west=-20, top=5, bottom=-5
            ... )
            >>> map.set_spatial_extent(spat_ext)
            >>> map.spatial_buffer_2d(10)
            >>> print(map.get_spatial_extent_as_tuple())
            (20.0, -20.0, 30.0, -30.0, 5.0, -5.0)

        """
        self.spatial_extent.north += size
        self.spatial_extent.south -= size
        self.spatial_extent.east += size
        self.spatial_extent.west -= size

        if update:
            self.spatial_extent.update(dbif)

    def check_for_correct_time(self) -> bool:
        """Check for correct time

        :return: True in case of success, False otherwise
        """
        if self.is_time_absolute():
            start, end = self.get_absolute_time()
        else:
            start, end, unit = self.get_relative_time()

        if start is None:
            self.msgr.error(_("Map <%s> has incorrect start time") % self.get_map_id())
            return False
        if end is not None and start >= end:
            # A map with a layer has a sentence of its own rather than one
            # with words inserted, so that a translator can inflect each.
            if self.get_layer():
                self.msgr.error(
                    _(
                        "Map <%(id)s> with layer %(layer)s has incorrect time "
                        "interval, start time is greater than end time"
                    )
                    % {"id": self.get_map_id(), "layer": self.get_layer()}
                )
            else:
                self.msgr.error(
                    _(
                        "Map <%s> has incorrect time interval, start time is "
                        "greater than end time"
                    )
                    % self.get_map_id()
                )
            return False

        return True

    def delete(self, dbif=None, update: bool = True, execute: bool = True):
        """Delete a map entry from database if it exists

         Remove dependent entries:

         - Remove the map entry in each space time dataset in which this map
           is registered
         - Remove the space time dataset register table

        :param dbif: The database interface to be used
        :param update: Update each space time dataset that held the map from
                       its registered maps once the map is deleted. This can
                       slow down the deletion significantly. It has no effect
                       with execute=False: the caller then updates the
                       datasets, which it can list with get_registered_stds()
                       before the call.
        :param execute: If True the SQL DELETE and DROP table statements
                        will be executed.
                        If False the prepared SQL statements are
                        returned and must be executed by the caller.

        :return: The SQL statements if execute=False, else an empty string,
                 None in case of a failure
        """

        # TODO: it must be possible to delete a map from a temporal
        # database even if the map is in a different mapset,
        # as long as the temporal database of the current mapset is used

        mapset = get_current_mapset()

        with connection(dbif) as dbif:
            statement = ""
            datasets = None

            if self.is_in_db(dbif, mapset=mapset):
                # SELECT all needed information from the database
                self.metadata.select(dbif, mapset=mapset)

                # Remember the datasets that hold the map: after the delete the
                # database no longer says which they were.
                if execute and update:
                    datasets = self.get_registered_stds(dbif, mapset=mapset)

                # First we unregister from all dependent space time datasets
                statement += self.unregister(dbif=dbif, update=update, execute=False)

                self.msgr.verbose(
                    _("Delete %s dataset <%s> from temporal database")
                    % (self.get_type(), self.get_id())
                )

                # Delete yourself from the database, trigger functions will
                # take care of dependencies
                statement += self.base.get_delete_statement()

            if execute:
                dbif.execute_transaction(statement, mapset=mapset)
                statement = ""
                # unregister() was asked for its statements only, so it could not
                # update the datasets; do it now that the rows are gone.
                if update and datasets:
                    for dataset_id in datasets:
                        stds = self.get_new_stds_instance(dataset_id)
                        stds.select(dbif)
                        stds.update_from_registered_maps(dbif)

            # Remove the timestamp from the file system. GRASS removes it by name in
            # the current mapset, so for a map of another mapset it would remove
            # the time stamp of a map of the same name here.
            if self.get_mapset() == mapset:
                self.remove_timestamp_from_grass()

            self.reset(None)

            return statement

    def unregister(self, dbif=None, update: bool = True, execute: bool = True):
        """Remove the map entry in each space time dataset in which this map
        is registered

        :param dbif: The database interface to be used
        :param update: Call for each unregister statement the update from
                       registered maps of the space time dataset. This can
                       slow down the un-registration process significantly.
        :param execute: If True the SQL DELETE and DROP table statements
                        will be executed.
                        If False the prepared SQL statements are
                        returned and must be executed by the caller.

        :return: The SQL statements if execute=False, else an empty string
        """

        if self.get_layer() is not None:
            self.msgr.debug(
                1,
                f"Unregister {self.get_type()} map <{self.get_map_id()}> with "
                f"layer {self.get_layer()} from space time datasets",
            )
        else:
            self.msgr.debug(
                1,
                f"Unregister {self.get_type()} map <{self.get_map_id()}> "
                "from space time datasets",
            )

        mapset = get_current_mapset()

        statement = ""
        with connection(dbif) as dbif:
            # Get all datasets in which this map is registered
            datasets = self.get_registered_stds(dbif, mapset=mapset)

            # For each stds in which the map is registered
            if datasets is not None:
                for dataset in datasets:
                    # Create a space time dataset object to remove the map
                    # from its register
                    stds = self.get_new_stds_instance(dataset)
                    stds.metadata.select(dbif)
                    statement += stds.unregister_map(self, dbif, False)
                    # Take care to update the space time dataset after
                    # the map has been unregistered
                    if update is True and execute is True:
                        stds.update_from_registered_maps(dbif)

            if execute:
                dbif.execute_transaction(statement, mapset=mapset)
                statement = ""

            return statement

    def get_registered_stds(self, dbif=None, mapset=None):
        """Return all space time dataset ids in which this map is registered
        as as a list of strings, or None if this map is not
        registered in any space time dataset.

        :param dbif: The database interface to be used
        :return: A list of ids of all space time datasets in
                     which this map is registered
        """
        with connection(dbif) as dbif:
            self.stds_register.select(dbif, mapset)
            datasets = self.stds_register.get_registered_stds()

            if datasets is not None and datasets != "" and datasets.find("@") >= 0:
                datasets = datasets.split(",")
            else:
                datasets = None

            return datasets

    # this fn should not be in a class for maps,
    # but instead in a class for stds: AbstractSpaceTimeDataset ?
    def add_stds_to_register(self, stds_id, dbif=None, execute: bool = True):
        """Add a new space time dataset to the register

        :param stds_id: The id of the space time dataset to be registered
        :param dbif: The database interface to be used
        :param execute: If True the SQL INSERT table statements
                        will be executed.
                        If False the prepared SQL statements are
                        returned and must be executed by the caller.

        :return: The SQL statements if execute=False, else an empty string
        """
        self.msgr.debug(2, "AbstractMapDataset.add_stds_to_register")

        with connection(dbif) as dbif:
            # only modify database in current mapset
            mapset = get_current_mapset()
            datasets = self.get_registered_stds(dbif=dbif, mapset=mapset)

            if stds_id is None or stds_id == "":
                return ""

            # Check if no datasets are present
            if datasets is None:
                datasets = []

            # Check if the dataset is already present
            if stds_id in datasets:
                return ""

            datasets.append(stds_id)

            self.stds_register.set_registered_stds(",".join(datasets))

            statement = ""

            if execute is True:
                self.stds_register.update(dbif=dbif)
            else:
                statement = self.stds_register.get_update_statement_mogrified(dbif=dbif)

            return statement

    def remove_stds_from_register(self, stds_id, dbif=None, execute: bool = True):
        """Remove a space time dataset from the register

        :param stds_id: The id of the space time dataset to removed from
                        the registered
        :param dbif: The database interface to be used
        :param execute: If True the SQL INSERT table statements
                        will be executed.
                        If False the prepared SQL statements are
                        returned and must be executed by the caller.

        :return: The SQL statements if execute=False, else an empty string
        """
        self.msgr.debug(2, "AbstractMapDataset.remove_stds_from_register")
        with connection(dbif) as dbif:
            # only modify database in current mapset
            mapset = get_current_mapset()
            datasets = self.get_registered_stds(dbif=dbif, mapset=mapset)

            # Check if no datasets are present
            if datasets is None:
                return ""

            # Check if the dataset is already present
            if stds_id not in datasets:
                return ""

            datasets.remove(stds_id)

            self.stds_register.set_registered_stds(",".join(datasets))

            statement = ""

            if execute is True:
                self.stds_register.update(dbif=dbif)
            else:
                statement = self.stds_register.get_update_statement_mogrified(dbif=dbif)

            return statement

    def read_semantic_label_from_grass(self) -> None:
        """Read the band identifier of this map from the map metadata
        in the GRASS file system based spatial database and
        set the internal band identifier that should be insert/updated
        in the temporal database.

        Currently only implemented in RasterDataset. Otherwise
        silently pass.
        """

    def set_semantic_label(self, semantic_label) -> None:
        """Set semantic label identifier

        Currently only implemented in RasterDataset. Otherwise
        report a warning.
        """
        self.msgr.warning(_("semantic labels can only be assigned to raster maps"))
