"""
The abstract_space_time_dataset module provides the AbstractSpaceTimeDataset
class that is the base class for all space time datasets.

SPDX-FileCopyrightText: 2011-2024 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import copy
import os
import sys
from abc import ABCMeta, abstractmethod
from datetime import datetime


from .abstract_dataset import AbstractDataset
from .db import connection, sql_literal
from .topology import (
    count_gaps,
    count_temporal_topology_relationships,
    count_temporal_types,
    has_correct_temporal_topology,
    print_spatio_temporal_topology_relationships,
    reversed_map_ids,
)
from .state import get_current_mapset
from . import granule_sampling, stds_time_edit
from .stds_map_register import StdsMapRegister
from .temporal_granularity import check_granularity_string


class AbstractSpaceTimeDataset(AbstractDataset, metaclass=ABCMeta):
    """Abstract space time dataset class

    Base class for all space time datasets.

    This class represents an abstract space time dataset. Convenient functions
    to select, update, insert or delete objects of this type in the SQL
    temporal database exists as well as functions to register or unregister
    raster maps.

    Parts of the temporal logic are implemented in the SQL temporal
    database, like the computation of the temporal and spatial extent as
    well as the collecting of metadata.
    """

    def __init__(self, ident) -> None:
        super().__init__()
        self.reset(ident)
        self.map_counter = 0

        # SpaceTimeRasterDataset related only
        self.semantic_label = None

    def get_name(self, semantic_label: bool = True):
        """Get dataset name including semantic label filter if enabled.

        :param bool semantic_label: True to return dataset name
          including semantic label filter if defined
          (eg. "landsat.L8_1") otherwise dataset name is returned only
          (eg. "landsat").

        :return str: dataset name

        """
        dataset_name = super().get_name()

        if semantic_label and self.semantic_label:
            return f"{dataset_name}.{self.semantic_label}"

        return dataset_name

    @property
    def map_register(self) -> StdsMapRegister:
        """The map register table of this dataset

        A new object for each access: it holds nothing but the dataset, so a
        copy of the dataset never points to the register of the original.
        """
        return StdsMapRegister(self)

    @abstractmethod
    def get_new_map_instance(self, ident=None):
        """Return a new instance of a map which is associated
        with the type of this object

        :param ident: The unique identifier of the new object
        """

    @abstractmethod
    def get_map_register(self):
        """Return the name of the map register table

        :return: The map register table name
        """

    @abstractmethod
    def set_map_register(self, name):
        """Set the name of the map register table

        This table stores all map names which are registered
        in this space time dataset.

        This method only modifies this object and does not commit
        the modifications to the temporal database.

        :param name: The name of the register table
        """

    def print_self(self) -> None:
        """Print the content of the internal structure to stdout"""
        self.base.print_self()
        self.temporal_extent.print_self()
        self.spatial_extent.print_self()
        self.metadata.print_self()

    def print_info(self) -> None:
        """Print information about this class in human readable style"""

        if self.get_type() == "strds":
            #                1         2         3         4         5         6         7  # noqa: E501
            #      0123456789012345678901234567890123456789012345678901234567890123456789012345678  # noqa: E501
            print(
                " +-------------------- Space Time Raster Dataset -----------------------------+"  # noqa: E501
            )
        if self.get_type() == "str3ds":
            #                1         2         3         4         5         6         7  # noqa: E501
            #      0123456789012345678901234567890123456789012345678901234567890123456789012345678  # noqa: E501
            print(
                " +-------------------- Space Time 3D Raster Dataset --------------------------+"  # noqa: E501
            )
        if self.get_type() == "stvds":
            #                1         2         3         4         5         6         7  # noqa: E501
            #      0123456789012345678901234567890123456789012345678901234567890123456789012345678  # noqa: E501
            print(
                " +-------------------- Space Time Vector Dataset -----------------------------+"  # noqa: E501
            )
        print(
            " |                                                                            |"  # noqa: E501
        )
        self.base.print_info()
        self.temporal_extent.print_info()
        self.spatial_extent.print_info()
        self.metadata.print_info()
        print(
            " +----------------------------------------------------------------------------+"  # noqa: E501
        )

    def print_shell_info(self) -> None:
        """Print information about this class in shell style"""
        self.base.print_shell_info()
        self.temporal_extent.print_shell_info()
        self.spatial_extent.print_shell_info()
        self.metadata.print_shell_info()

    def print_history(self) -> None:
        """Print history information about this class in human readable
        shell style
        """
        self.metadata.print_history()

    def set_initial_values(
        self,
        temporal_type,
        semantic_type=None,
        title=None,
        description: str | None = None,
    ) -> None:
        """Set the initial values of the space time dataset

        In addition the command creation string is generated
        an inserted into the metadata object.

        This method only modifies this object and does not commit
        the modifications to the temporal database.

        The insert() function must be called to commit
        this content into the temporal database.

        :param temporal_type: The temporal type of this space
                             time dataset (absolute or relative)
        :param semantic_type: The semantic type of this dataset
        :param title: The title
        :param description: The description of this dataset
        """

        if temporal_type == "absolute":
            self.base.set_ttype("absolute")
        elif temporal_type == "relative":
            self.base.set_ttype("relative")
        else:
            self.msgr.fatal(_('Unknown temporal type "%s"') % (temporal_type))

        self.base.set_semantic_type(semantic_type)
        self.metadata.set_title(title)
        self.metadata.set_description(description)
        self.metadata.set_command(self.create_command_string())

    def set_aggregation_type(self, aggregation_type) -> None:
        """Set the aggregation type of the space time dataset

        :param aggregation_type: The aggregation type of the space time
                                 dataset
        """
        self.metadata.set_aggregation_type(aggregation_type)

    def update_command_string(self, dbif=None) -> None:
        """Append the current command string to any existing command string
        in the metadata class and calls metadata update

        :param dbif: The database interface to be used
        """

        self.metadata.select(dbif=dbif)
        command = self.metadata.get_command()
        if command is None:
            command = ""
        command += self.create_command_string()
        self.metadata.set_command(command)
        self.metadata.update(dbif=dbif)

    def create_command_string(self):
        """Create the command string that was used to create this
        space time dataset.

        The command string should be set with self.metadata.set_command()

        :return: The command string
        """
        # The grass module

        command = "# {} \n".format(str(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
        command += os.path.basename(sys.argv[0])

        # We will wrap the command line to fit into 80 character
        length = len(command)
        for token in sys.argv[1:]:
            # We need to remove specific characters
            token = token.replace("'", " ")
            token = token.replace('"', " ")

            # Check for sub strings
            if token.find("=") > 0:
                first = token.split("=")[0]
                second = ""

                flag = 0
                for t in token.split("=")[1:]:
                    if flag == 0:
                        second += t
                        flag = 1
                    else:
                        second += "=" + t

                token = f'{first}="{second}"'

            if length + len(token) >= 76:
                command += f"\n    {token}"
                length = len(token) + 4
            else:
                command += f" {token}"
                length += len(token) + 1

        command += "\n"
        return str(command)

    def get_semantic_type(self):
        """Return the semantic type of this dataset

        :return: The semantic type
        """
        return self.base.get_semantic_type()

    def get_initial_values(self):
        """Return the initial values: temporal_type,
        semantic_type, title, description"""

        temporal_type = self.get_temporal_type()
        semantic_type = self.base.get_semantic_type()
        title = self.metadata.get_title()
        description = self.metadata.get_description()

        return temporal_type, semantic_type, title, description

    def get_granularity(self):
        """Return the granularity of the space time dataset

        Granularity can be of absolute time or relative time.
        In case of absolute time a string containing an integer
        value and the time unit (years, months, days, hours, minutes,
        seconds). In case of relative time an integer value is expected.

        :return: The granularity
        """

        return self.temporal_extent.get_granularity()

    def set_granularity(self, granularity) -> None:
        """Set the granularity

        The granularity is usually computed by the space time dataset at
        runtime.

        Granularity can be of absolute time or relative time.
        In case of absolute time a string containing an integer
        value and the time unit (years, months, days, hours, minutes,
        seconds). In case of relative time an integer value is expected.

        This method only modifies this object and does not commit
        the modifications to the temporal database.

        :param granularity: The granularity of the dataset
        """

        temporal_type = self.get_temporal_type()

        check = check_granularity_string(granularity, temporal_type)
        if not check:
            self.msgr.fatal(_('Wrong granularity: "%s"') % str(granularity))

        if temporal_type == "absolute":
            self.base.set_ttype("absolute")
        elif temporal_type == "relative":
            self.base.set_ttype("relative")
        else:
            self.msgr.fatal(_('Unknown temporal type "%s"') % (temporal_type))

        self.temporal_extent.set_granularity(granularity)

    def set_relative_time_unit(self, unit) -> None:
        """Set the relative time unit which may be of type:
        years, months, days, hours, minutes or seconds

        All maps registered in a (relative time)
        space time dataset must have the same unit

        This method only modifies this object and does not commit
        the modifications to the temporal database.

        :param unit: The relative time unit
        """

        temporal_type = self.get_temporal_type()

        if temporal_type == "relative":
            if not self.check_relative_time_unit(unit):
                self.msgr.fatal(_("Unsupported temporal unit: %s") % (unit))
            self.relative_time.set_unit(unit)

    def insert(self, dbif=None, execute: bool = True):
        """Insert the space time dataset content into the database from the internal
        structure

        The map register table will be created, so that maps
        can be registered.

        :param dbif: The database interface to be used
        :param execute: If True the SQL statements will be executed.
                        If False the prepared SQL statements are
                        returned and must be executed by the caller.
        :return: The SQL insert statement in case execute=False, or an
                 empty string otherwise
        """

        with connection(dbif) as dbif:
            statement = ""

            # The register table is created with the first insert
            if self.map_register.table_name() is None:
                statement += self.map_register.create_statement(dbif)

            statement += AbstractDataset.insert(self, dbif=dbif, execute=False)

            if execute:
                dbif.execute_transaction(statement)
                statement = ""

            return statement

    def get_map_time(self):
        """Return the type of the map time, interval, point, mixed or invalid"""

        return self.temporal_extent.get_map_time()

    def count_temporal_types(self, maps=None, dbif=None):
        """Return the temporal type of the registered maps as dictionary

        The map list can be a list of AbstractDataset or database rows.
        It must be ordered by start time

        The temporal type can be:

        - point    -> only the start time is present
        - interval -> start and end time
        - invalid  -> No valid time point or interval found

        :param maps: A sorted (start_time) list of AbstractDataset objects or database
                     rows
        :param dbif: The database interface to be used
        """

        if maps is None:
            maps = self.get_registered_maps(where=None, order="start_time", dbif=dbif)

        return count_temporal_types(maps)

    def count_gaps(self, maps=None, dbif=None):
        """Count the number of gaps between temporal neighbors

        :param maps: A sorted (start_time) list of AbstractDataset objects
        :param dbif: The database interface to be used
        :return: The numbers of gaps between temporal neighbors
        """

        if maps is None:
            maps = self.get_registered_maps_as_objects(
                where=None, order="start_time", dbif=dbif
            )

        return count_gaps(maps)

    def print_spatio_temporal_relationships(
        self, maps=None, spatial=None, dbif=None
    ) -> None:
        """Print the spatio-temporal relationships for each map of the space
        time dataset or for each map of the optional list of maps

        :param maps: a ordered by start_time list of map objects, if None
                     the registered maps of the space time dataset are used
        :param spatial: This indicates if the spatial topology is created as
                        well: spatial can be None (no spatial topology),
                        "2D" using west, east, south, north or "3D" using
                        west, east, south, north, bottom, top
        :param dbif: The database interface to be used
        """

        if maps is None:
            maps = self.get_registered_maps_as_objects(
                where=None, order="start_time", dbif=dbif
            )

        print_spatio_temporal_topology_relationships(
            maps1=maps, maps2=maps, spatial=spatial, dbif=dbif
        )

    def count_temporal_relations(self, maps=None, dbif=None):
        """Count the temporal relations between the registered maps.

        The map list must be ordered by start time.
        Temporal relations are counted by analysing the sparse upper right
        side temporal relationships matrix.

        :param maps: A sorted (start_time) list of AbstractDataset objects
        :param dbif: The database interface to be used
        :return: A dictionary with counted temporal relationships
        """

        if maps is None:
            maps = self.get_registered_maps_as_objects(
                where=None, order="start_time", dbif=dbif
            )

        return count_temporal_topology_relationships(maps1=maps, dbif=dbif)

    def check_temporal_topology(self, maps=None, dbif=None) -> bool:
        """Check the temporal topology of all maps of the current space time
        dataset or of an optional list of maps

        Correct topology means, that time intervals are not overlap or
        that intervals does not contain other intervals.
        Equal time intervals  are not allowed.

        The optional map list must be ordered by start time

        Allowed and not allowed temporal relationships for correct topology:

        - after      -> allowed
        - precedes   -> allowed
        - follows    -> allowed
        - precedes   -> allowed

        - equal      -> not allowed
        - during     -> not allowed
        - contains   -> not allowed
        - overlaps   -> not allowed
        - overlapped -> not allowed
        - starts     -> not allowed
        - finishes   -> not allowed
        - started    -> not allowed
        - finished   -> not allowed


        :param maps: An optional list of AbstractDataset objects, in case of
                    None all maps of the space time dataset are checked
        :param dbif: The database interface to be used
        :return: True if topology is correct
        """
        if maps is None:
            maps = self.get_registered_maps_as_objects(
                where=None, order="start_time", dbif=dbif
            )

        relations = count_temporal_topology_relationships(maps1=maps, dbif=dbif)

        return has_correct_temporal_topology(relations, self.get_map_time())

    def get_registered_maps_as_objects_by_granularity(
        self, gran: str | None = None, where: str | None = None, dbif=None
    ):
        """Return all registered maps as ordered (by start_time) object list
        with "gap" map objects (id==None) for spatio-temporal topological
        operations that require the temporal extent only.

        Each list entry is a list of AbstractMapDatasets objects
        which are potentially equal the actual granule, contain the
        actual granule or are located in the actual granule.
        Hence for each granule a list of AbstractMapDatasets can be
        expected.

        Maps that overlap the granule are ignored.

        The granularity of the space time dataset is used as increment in
        case the granule is not user defined.

        A valid temporal topology (no overlapping or inclusion allowed)
        is needed to get correct results.

        Space time datasets with interval time, time instances and mixed
        time are supported.

        Gaps between maps are identified as unregistered maps with id==None.

        The objects are initialized with their id's' and the spatio-temporal
        extent (temporal type, start time, end time, west, east, south,
        north, bottom and top).
        In case more map information are needed, use the select()
        method for each listed object.

        :param gran: The granularity string to be used, if None the
                    granularity of the space time dataset is used.
                    Absolute time has the format "number unit", relative
                    time has the format "number".
                    The unit in case of absolute time can be one of "second,
                    seconds, minute, minutes, hour, hours, day, days, week,
                    weeks, month, months, year, years". The unit of the
                    relative time granule is always the space time dataset
                    unit and can not be changed.
        :param where: The SQL where statement to select a subset of
                      the registered maps without "WHERE"
        :param dbif: The database interface to be used

        :return: ordered list of map lists. Each list represents a single
                granule, or None in case nothing found
        """

        return granule_sampling.registered_maps_by_granularity(self, gran, where, dbif)

    @staticmethod
    def resample_maplist_by_granularity(maps, start, end, gran):
        """Resample a list of AbstractMapDatasets by a given granularity

        The provided map list must be sorted by start time.
        A valid temporal topology (no overlapping or inclusion allowed)
        is needed to receive correct results. See
        :func:`grass.temporal.granule_sampling.resample_maplist_by_granularity`.

        :param maps: An ordered list (by start time) of AbstractMapDatasets
                objects. All maps must have the same temporal type
                and the same unit in case of relative time.
        :param start: The start time of the provided map list
        :param end:   The end time of the provided map list
        :param gran: The granularity string
        :return: ordered list of map lists. Each list represents a single
            granule, or None in case nothing found
        """
        return granule_sampling.resample_maplist_by_granularity(maps, start, end, gran)

    def get_registered_maps_as_objects_with_gaps(
        self, where=None, dbif=None, spatial_extent=None, spatial_relation=None
    ):
        """Return all or a subset of the registered maps as
        ordered (by start_time) object list with
        "gap" map objects (id==None) for spatio-temporal topological
        operations that require the spatio-temporal extent only.

        Gaps between maps are identified as maps with id==None

        The objects are initialized with their id's' and the spatio-temporal
        extent (temporal type, start time, end time, west, east, south,
        north, bottom and top).
        In case more map information are needed, use the select()
        method for each listed object.

        The combination of the spatial_extent and spatial_relation parameters
        can be used to return only map objects with the given spatial relation
        to the provided spatial extent.

        :param where: The SQL where statement to select a
                     subset of the registered maps without "WHERE"
        :param dbif: The database interface to be used
        :param spatial_extent: Spatial extent dict and projection information
            e.g. from g.region -ug3 with GRASS region keys
            "n", "s", "e", "w", "b", "t", and "projection".
        :param spatial_relation: Spatial relation to the provided
            spatial extent as a string with one of the following values:

            - "overlaps": maps that spatially overlap ("intersect")
              within the provided spatial extent
            - "is_contained": maps that are fully within the provided spatial extent
            - "contains": maps that contain (fully cover) the provided spatial extent

        :return: Ordered object list, in case nothing found None is returned
        """

        with connection(dbif) as dbif:
            obj_list = []

            maps = self.get_registered_maps_as_objects(
                where, "start_time", dbif, spatial_extent, spatial_relation
            )

            if maps is not None and len(maps) > 0:
                # No gap is inserted next to a map that ends before it starts.
                # This matters for a reader that keeps the stored times (a
                # subclass or an add-on); the own reader already drops such
                # times, so the map arrives without time.
                reversed_ids = reversed_map_ids(maps)
                for i in range(len(maps)):
                    obj_list.append(maps[i])
                    # Detect and insert gaps
                    if i < len(maps) - 1 and reversed_ids.isdisjoint(
                        (maps[i].get_id(), maps[i + 1].get_id())
                    ):
                        relation = maps[i + 1].temporal_relation(maps[i])
                        if relation == "after":
                            start1, end1 = maps[i].get_temporal_extent_as_tuple()
                            start2, end2 = maps[i + 1].get_temporal_extent_as_tuple()
                            end = start2
                            start = end1 if end1 is not None else start1

                            map_ = self.get_new_map_instance(None)

                            if self.is_time_absolute():
                                map_.set_absolute_time(start, end)
                            elif self.is_time_relative():
                                map_.set_relative_time(
                                    start, end, self.get_relative_time_unit()
                                )
                            map_.set_spatial_extent_from_values(0, 0, 0, 0, 0, 0)
                            obj_list.append(copy.copy(map_))

            return obj_list

    def get_registered_maps_as_objects(
        self,
        where=None,
        order="start_time",
        dbif=None,
        spatial_extent=None,
        spatial_relation=None,
    ):
        """Return all or a subset of the registered maps as ordered object
        list for spatio-temporal topological operations that require the
        spatio-temporal extent only

        The objects are initialized with their id's' and the spatio-temporal
        extent (temporal type, start time, end time, west, east, south,
        north, bottom and top).
        In case more map information are needed, use the select()
        method for each listed object.

        The combination of the spatial_extent and spatial_relation parameters
        can be used to return only maps with the given spatial relation to
        the provided spatial extent

        :param where: The SQL where statement to select a subset of
                      the registered maps without "WHERE"
        :param order: The SQL order statement to be used to order the
                      objects in the list without "ORDER BY"
        :param dbif: The database interface to be used
        :param spatial_extent: Spatial extent dict and projection information
            e.g. from g.region -ug3 with GRASS region keys
            "n", "s", "e", "w", "b", "t", and "projection".
        :param spatial_relation: Spatial relation to the provided
            spatial extent as a string with one of the following values:

            - "overlaps": maps that spatially overlap ("intersect")
              within the provided spatial extent
            - "is_contained": maps that are fully within the provided spatial extent
            - "contains": maps that contain (fully cover) the provided spatial extent

        :return: The ordered map object list.
                In case nothing is found, an empty list is returned
        """

        with connection(dbif) as dbif:
            obj_list = []

            # use all columns
            rows = self.get_registered_maps(
                columns=None,
                where=where,
                order=order,
                dbif=dbif,
                spatial_extent=spatial_extent,
                spatial_relation=spatial_relation,
            )

            if rows:
                # Older temporal databases have no bottom and top columns
                # in their views so we need a work around to set the full
                # spatial extent as well

                # check keys in first row
                # note that 'if "bottom" in row' does not work
                # because row is not a dict but some db backend object
                has_bt_columns = "bottom" in rows[0].keys()  # noqa: SIM118
                has_semantic_label = "semantic_label" in rows[0].keys()  # noqa: SIM118
            else:
                return obj_list

            for row in rows:
                map_ = self.get_new_map_instance(row["id"])
                # time
                if self.is_time_absolute():
                    map_.set_absolute_time(row["start_time"], row["end_time"])
                elif self.is_time_relative():
                    map_.set_relative_time(
                        row["start_time"],
                        row["end_time"],
                        self.get_relative_time_unit(),
                    )
                # space
                # The fast way
                if has_bt_columns:
                    map_.set_spatial_extent_from_values(
                        west=row["west"],
                        east=row["east"],
                        south=row["south"],
                        top=row["top"],
                        north=row["north"],
                        bottom=row["bottom"],
                    )
                # The slow work around
                else:
                    map_.spatial_extent.select(dbif)

                # labels
                if (
                    has_semantic_label
                    and row["semantic_label"] is not None
                    and row["semantic_label"] != "None"
                ):
                    map_.metadata.set_semantic_label(row["semantic_label"])

                obj_list.append(copy.copy(map_))

            return obj_list

    def _update_where_statement_by_semantic_label(self, where):
        """Update given SQL WHERE statement by semantic label.

        Call this method only when self.semantic_label is defined.

        :param str where: SQL WHERE statement to be updated

        :return: updated SQL WHERE statement
        """

        def leading_zero(value):
            try:
                if value.startswith("0"):
                    return value.lstrip("0")
                return f"{int(value):02d}"
            except ValueError:
                return None

            return None

        # The label narrows the condition of the user, which may hold an OR
        # of its own, and the alternatives of a shortcut are an OR as well;
        # each side is bracketed, so that AND binds the two as wholes.
        label_where = ""

        # be case-insensitive
        if "_" in self.semantic_label:
            # fully-qualified semantic label, do not modify
            label_where += f"semantic_label IN ({sql_literal(self.semantic_label)}"

            # be zero-padding less sensitive
            try:
                shortcut, identifier = self.semantic_label.split("_", -1)
                identifier_zp = leading_zero(identifier)
                if identifier_zp:
                    zero_padded = f"{shortcut.upper()}_{identifier_zp.upper()}"
                    label_where += f", {sql_literal(zero_padded)}"
            except ValueError:
                # any number of "_" is allowed in semantic labels
                pass

            label_where += ")"
        else:
            # shortcut or band identifier given
            shortcut_identifier = leading_zero(self.semantic_label)
            if shortcut_identifier:
                label = self.semantic_label.upper()
                patterns = (
                    sql_literal(f"{shortcut_identifier}\\_%"),
                    sql_literal(f"%\\_{shortcut_identifier}"),
                    sql_literal(f"{label}\\_%"),
                    sql_literal(f"%\\_{label}"),
                )
                alternatives = " OR ".join(
                    f"semantic_label LIKE {pattern} ESCAPE '\\'" for pattern in patterns
                )
                label_where += f"({alternatives})"
            else:
                label_where += f"semantic_label = {sql_literal(self.semantic_label)}"

        return f"({where}) AND {label_where}" if where else label_where

    def _update_where_statement_by_spatial_extent(
        self, where, spatial_extent, spatial_relation
    ):
        """Update given SQL WHERE statement by spatial extent where clause

        Code is lend from wind_overlap.c in lib/gis and
        temporal.SpatialExtent

        Call this method only when spatial extent is given as a dict
        with GRASS region keys "n", "s", "e", "w", "b", "t", and
        "projection", where projection value "3" refers to latlong.
        It can be created with gs.parse_command("g.region", flags="ug3")
        {n: '80', "s": '20', "e": '60', "w": '10', "b": '-50', "t": '50',
        "projection": '1'}

        :param str where: SQL WHERE statement to be updated
        :param dict spatial_extent: Spatial extent dict and projection information
            e.g. from g.region -ug3
        :param str spatial_relation: Spatial relation to the provided
            spatial extent as a string with one of the following values:

            - "overlaps": maps that spatially overlap ("intersect")
              within the provided spatial extent
            - "is_contained": maps that are fully within the provided spatial extent
            - "contains": maps that contain (fully cover) the provided spatial extent

        :return: updated SQL WHERE statement

        .. code-block:: pycon

            >>> import grass.script as gs
            >>> import grass.temporal as tgis
            >>> where = None
            >>> spatial_extent = gs.parse_command("g.region", flags="ug3")
            >>> strds = tgis.SpaceTimeRasterDataset("a@PERMANENT")
            >>> strds._update_where_statement_by_spatial_extent(
            ...     where, spatial_extent, "overlaps"
            ... )
            '((north > 0 AND south < 1 AND east > 0 AND west < 1))'
        """

        # The condition of the user may hold an OR of its own, and the shifted
        # extents below are joined with OR as well; each side is bracketed,
        # so that AND binds the two as wholes.
        where = f"({where}) AND (" if where else "("

        if not spatial_relation:
            spatial_relation = "overlaps"
        elif spatial_relation not in {"overlaps", "is_contained", "contains"}:
            msg = _(
                "Invalid spatial relation <{}> requested. "
                "Only values 'overlaps', 'is_contained', and 'contains' are allowed."
            ).format(spatial_relation)
            self.msgr.error(msg)
            raise ValueError(msg)
        # SQL implementation of overlap, is_contained, and contains
        where += ""

        if spatial_relation == "overlaps":
            spatial_where_template = (
                "(north > {s} AND south < {n} AND east > {w} AND west < {e}"
            )
        elif spatial_relation == "is_contained":
            spatial_where_template = (
                "(north <= {n} AND south >= {s} AND east <= {e} AND west >= {w}"
            )
        elif spatial_relation == "contains":
            spatial_where_template = (
                "(north >= {n} AND south <= {s} AND east >= {e} AND west <= {w}"
            )

        if self.get_type() == "str3ds":
            if spatial_relation == "overlaps":
                spatial_where_template += " AND top > {b} AND bottom < {t}"
            elif spatial_relation == "is_contained":
                spatial_where_template += " AND top <= {t} AND bottom >= {b}"
            elif spatial_relation == "contains":
                spatial_where_template += " AND top >= {t} AND bottom <= {b}"
        spatial_where_template += ")"

        spatial_where_list = [spatial_where_template.format(**spatial_extent)]

        # Adjust the east and west in case of LL projection
        if spatial_extent["projection"] == "3":
            for coord_shift in [-360, 360]:
                spatial_extent_shift = spatial_extent.copy()
                spatial_extent_shift["e"] = str(
                    float(spatial_extent_shift["e"]) + coord_shift
                )
                spatial_extent_shift["w"] = str(
                    float(spatial_extent_shift["w"]) + coord_shift
                )
                spatial_where_list.append(
                    spatial_where_template.format(**spatial_extent_shift)
                )
        where += " OR ".join(spatial_where_list)

        # close WHERE statement
        where += ")"

        return where

    def get_registered_maps(
        self,
        columns=None,
        where=None,
        order=None,
        dbif=None,
        group=None,
        spatial_extent=None,
        spatial_relation=None,
    ):
        """Return SQL rows of the selected registered maps.

        In case neither columns nor columns for grouping (group)
        are specified, each returned row represents a dataset and
        includes all columns specified in the datatype specific view.

        If group is not None, the rows in the register tables are
        grouped_by the list of columns in the group option. This
        function is useful to retrieve e.g. granules from an STRDS
        with satellite imagery where scene consists of different bands
        that have different semantic_labels but equal an temporal extend
        (group=["start_time", "end_time"]).
        The returned SQL rows of grouped output contain the selected
        columns plus the columns in the group option. If no columns
        are selected only the "id" column is returned. Content of the
        selected columns is concatenated to a comma separated string.

        The combination of the spatial_extent and spatial_relation parameters
        can be used to return only SQL rows of maps with the given spatial
        relation to the provided spatial extent

        :param columns: Columns to be selected as SQL compliant string,
                        default is "*" or "id" if group is given.
        :param where: The SQL where statement to select a subset
                      of the registered maps without "WHERE"
        :param group: The columns to be used in the SQL GROUP BY statement
                      as SQL compliant string without "GROUP BY"
        :param spatial_extent: Spatial extent dict and projection information
            e.g. from g.region -ug3 with GRASS region keys
            "n", "s", "e", "w", "b", "t", and  "projection".
        :param spatial_relation: Spatial relation to the provided
            spatial extent as a string with one of the following values:

            - "overlaps": maps that spatially overlap ("intersect")
              within the provided spatial extent
            - "is_contained": maps that are fully within the provided spatial extent
            - "contains": maps that contain (fully cover) the provided spatial extent
        :param dbif: The database interface to be used

        :return: SQL rows of all registered maps grouped by the columns given in
                the group option, in case no maps are found, None is returned
        """

        return self.map_register.rows(
            columns,
            where,
            order,
            dbif,
            group,
            spatial_extent,
            spatial_relation,
        )

    @staticmethod
    def shift_map_list(maps, gran):
        """Temporally shift each map in the list with the provided granularity

        This method does not perform any temporal database operations. See
        :func:`grass.temporal.stds_time_edit.shift_map_list`.

        :param maps: A list of maps  with initialized temporal extent
        :param gran: The granularity to be used for shifting
        :return: The modified map list, None if nothing to shift or wrong
                granularity
        """
        return stds_time_edit.shift_map_list(maps, gran)

    def shift(self, gran, dbif=None) -> bool:
        """Temporally shift each registered map with the provided granularity

        :param gran: The granularity to be used for shifting
        :param dbif: The database interface to be used
        :return: True something to shift, False if nothing to shift or wrong
                granularity

        """
        return stds_time_edit.shift(self, gran, dbif)

    @staticmethod
    def snap_map_list(maps):
        """For each map in the list snap the end time to the start time of its
        temporal nearest neighbor in the future.

        Maps with equal time stamps are not snapped. This method does not
        perform any temporal database operations. See
        :func:`grass.temporal.stds_time_edit.snap_map_list`.

        :param maps: A list of maps with initialized temporal extent
        :return: The modified map list, None nothing to shift or wrong
                granularity
        """
        return stds_time_edit.snap_map_list(maps)

    def snap(self, dbif=None) -> None:
        """For each registered map snap the end time to the start time of
        its temporal nearest neighbor in the future

        Maps with equal time stamps are not snapped

        :param dbif: The database interface to be used

        """
        stds_time_edit.snap(self, dbif)

    def update_map_timestamps(self, maps, date_list, dbif) -> None:
        """Update the timestamps of maps with the start and end time
        stored in the date_list.

        The number of dates in the list must be equal to the number
        of maps. The datasets the maps are registered in are updated too.

        :param maps: A list of map objects
        :param date_list: A list with date tuples (start_time, end_time)
        :param dbif: The database interface to be used
        """
        stds_time_edit.update_map_timestamps(self, maps, date_list, dbif)

    def rename(self, ident, dbif=None) -> None:
        """Rename the space time dataset

        This method renames the space time dataset, the map register table
        and updates the entries in registered maps stds register.

        Renaming does not work with Postgresql yet.

        :param ident: The new identifier "name@mapset"
        :param dbif: The database interface to be used
        """

        if self.get_mapset() != get_current_mapset():
            self.msgr.fatal(
                _(
                    "Unable to rename dataset <%(ds)s> of type "
                    "%(type)s in the temporal database. The mapset "
                    "of the database does not match the current "
                    "mapset"
                )
                % {"ds": self.get_id(), "type": self.get_type()}
            )

        with connection(dbif) as dbif:
            if dbif.get_dbmi().__name__ != "sqlite3":
                self.msgr.fatal(
                    _(
                        "Renaming of space time datasets is not supported for PostgreSQL."
                    )
                )

            # SELECT all needed information from the database
            self.select(dbif)

            # We need to select the registered maps here
            maps = self.get_registered_maps_as_objects(None, "start_time", dbif)

            # Safe old identifier
            old_ident = self.get_id()
            # Set new identifier
            self.set_id(ident)

            # The new register table name must be set before update() writes
            # the row of the dataset
            register_statement = self.map_register.rename_statement(dbif)

            # Get the update statement, we update the table entry of the old
            # identifier
            statement = self.update(dbif, execute=False, ident=old_ident)
            statement += register_statement

            # We need to rename the space time dataset in the maps register table
            if maps:
                for map_ in maps:
                    map_.remove_stds_from_register(stds_id=old_ident, dbif=dbif)
                    map_.add_stds_to_register(stds_id=ident, dbif=dbif)

            # Execute the accumulated statements
            dbif.execute_transaction(statement)

    def delete(self, dbif=None, execute: bool = True):
        """Delete a space time dataset from the temporal database

        This method removes the space time dataset from the temporal
        database and drops its map register table

        :param dbif: The database interface to be used
        :param execute: If True the SQL DELETE and DROP table
                       statements will be executed.
                       If False the prepared SQL statements are returned
                       and must be executed by the caller.

        :return: The SQL statements if execute == False, else an empty
                 string
        """
        # First we need to check if maps are registered in this dataset and
        # unregister them

        self.msgr.verbose(
            _("Delete space time %s  dataset <%s> from temporal database")
            % (self.get_new_map_instance(ident=None).get_type(), self.get_id())
        )

        if self.get_mapset() != get_current_mapset():
            self.msgr.fatal(
                _(
                    "Unable to delete dataset <%(ds)s> of type "
                    "%(type)s from the temporal database. The mapset"
                    " of the database does not match the current "
                    "mapset"
                )
                % {"ds": self.get_id(), "type": self.get_type()}
            )

        statement = ""
        with connection(dbif) as dbif:
            # SELECT all needed information from the database
            self.metadata.select(dbif)

            if self.map_register.table_name() is not None:
                self.msgr.debug(
                    1, _("Drop map register table: %s") % (self.get_map_register())
                )
                rows = self.get_registered_maps(
                    columns="id", where=None, order=None, dbif=dbif
                )
                # Unregister each registered map in the table
                if rows is not None:
                    for row in rows:
                        # Unregister map
                        map_ = self.get_new_map_instance(row["id"])
                        statement += self.unregister_map(
                            map=map_, dbif=dbif, execute=False
                        )

                # Safe the DROP table statement
                statement += self.map_register.drop_statement()

            # Remove the primary key, the foreign keys will be removed by trigger
            statement += self.base.get_delete_statement()

            if execute:
                dbif.execute_transaction(statement)

            self.reset(None)

            if execute:
                return ""

            return statement

    def register_map(self, map, dbif=None) -> bool:
        """Register a map in the space time dataset.

        This method takes care of the registration of a map
        in a space time dataset.

        In case the map is already registered this function
        will break with a warning and return False.

        :param map: The AbstractMapDataset object that should be registered
        :param dbif: The database interface to be used
        :return: True if success, False otherwise

        :raises ~grass.exceptions.FatalError:
            This method raises a :exc:`~grass.exceptions.FatalError` exception
            in case of a fatal error
        """

        return self.map_register.register(map, dbif)

    def unregister_map(self, map, dbif=None, execute: bool = True):
        """Unregister a map from the space time dataset.

        This method takes care of the un-registration of a map
        from a space time dataset.

        :param map: The map object to unregister
        :param dbif: The database interface to be used
        :param execute: If True the SQL DELETE and DROP table
                        statements will be executed.
                        If False the prepared SQL statements are
                        returned and must be executed by the caller.

        :return: The SQL statements if execute == False, else an empty
                string, None in case of a failure
        """

        return self.map_register.unregister(map, dbif, execute)

    def update_from_registered_maps(self, dbif=None) -> None:
        """This methods updates the modification time, the spatial and
        temporal extent as well as type specific metadata. It should always
        been called after maps are registered or unregistered/deleted from
        the space time dataset.

        The update of the temporal extent checks if the end time is set
        correctly.
        In case the registered maps have no valid end time (None) the
        maximum start time
        will be used. If the end time is earlier than the maximum start
        time, it will be replaced by the maximum start time.

        :param dbif: The database interface to be used
        """

        self.map_register.update_extent(dbif)
