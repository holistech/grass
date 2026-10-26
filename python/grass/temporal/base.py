"""
Basic information of the maps and space time datasets of the temporal database

A map or space time dataset has a row in a table of its kind with its
identifier, name, mapset, creator and time of creation, and a map has a row
that lists the space time datasets it is registered in. One class serves all
six kinds; the kind fixes the table and the columns that only a space time
dataset or a vector map has. The classes of the SQL serialization are in
rows.py.

Usage:

.. code-block:: pycon

    >>> import grass.temporal as tgis
    >>> from grass.temporal.kinds import KINDS
    >>> tgis.init()
    >>> rbase = tgis.base.BaseRow(KINDS["raster"], ident="soil@PERMANENT")
    >>> vbase = tgis.base.BaseRow(KINDS["vector"], ident="soil:1@PERMANENT")
    >>> strdsbase = tgis.base.BaseRow(KINDS["strds"], ident="soil@PERMANENT")
    >>> rbase.get_table_name(), strdsbase.get_table_name()
    ('raster_base', 'strds_base')


SPDX-FileCopyrightText: 2011-2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:author: Soeren Gebbert
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from .rows import Column, DictSQLSerializer, Row, SQLDatabaseInterface

if TYPE_CHECKING:
    from .kinds import Kind

__all__ = [
    "BaseRow",
    "DictSQLSerializer",
    "RegisterRow",
    "SQLDatabaseInterface",
]


class BaseRow(Row):
    """The basic information of a map or a space time dataset

    The kind selects the table. A space time dataset has the semantic type
    and the time of the last modification in addition, a vector map the layer.

    Usage:

    .. code-block:: pycon

        >>> init()
        >>> from grass.temporal.kinds import KINDS
        >>> t = BaseRow(
        ...     KINDS["raster"],
        ...     "soil@PERMANENT",
        ...     creator="soeren",
        ...     ctime=datetime(2001, 1, 1),
        ...     ttype="absolute",
        ... )
        >>> t.id
        'soil@PERMANENT'
        >>> t.name
        'soil'
        >>> t.mapset
        'PERMANENT'
        >>> t.creator
        'soeren'
        >>> t.ctime
        datetime.datetime(2001, 1, 1, 0, 0)
        >>> t.ttype
        'absolute'
        >>> t.print_info()
         +-------------------- Basic information -------------------------------------+
         | Id: ........................ soil@PERMANENT
         | Name: ...................... soil
         | Mapset: .................... PERMANENT
         | Creator: ................... soeren
         | Temporal type: ............. absolute
         | Creation time: ............. 2001-01-01 00:00:00
        >>> t.print_shell_info()
        id=soil@PERMANENT
        name=soil
        mapset=PERMANENT
        creator=soeren
        temporal_type=absolute
        creation_time='2001-01-01 00:00:00'

        A space time dataset adds the semantic type and the modification time.

        >>> t = BaseRow(
        ...     KINDS["strds"],
        ...     "soil@PERMANENT",
        ...     semantic_type="average",
        ...     creator="soeren",
        ...     ctime=datetime(2001, 1, 1),
        ...     ttype="absolute",
        ...     mtime=datetime(2001, 1, 1),
        ... )
        >>> t.semantic_type
        'average'
        >>> t.print_info()
         +-------------------- Basic information -------------------------------------+
         | Id: ........................ soil@PERMANENT
         | Name: ...................... soil
         | Mapset: .................... PERMANENT
         | Creator: ................... soeren
         | Temporal type: ............. absolute
         | Creation time: ............. 2001-01-01 00:00:00
         | Modification time:.......... 2001-01-01 00:00:00
         | Semantic type:.............. average
        >>> t.print_shell_info()
        id=soil@PERMANENT
        name=soil
        mapset=PERMANENT
        creator=soeren
        temporal_type=absolute
        creation_time='2001-01-01 00:00:00'
        modification_time='2001-01-01 00:00:00'
        semantic_type=average

    """

    columns = (
        Column("id"),
        Column("name"),
        Column("mapset"),
        Column("layer"),
        Column("creator"),
        Column("creation_time", alias="ctime"),
        Column("temporal_type", alias="ttype"),
        Column("semantic_type"),
        Column("modification_time", alias="mtime"),
    )

    def __init__(
        self,
        kind: Kind,
        ident=None,
        name: str | None = None,
        mapset=None,
        layer=None,
        creator=None,
        ctime=None,
        ttype=None,
        semantic_type=None,
        mtime=None,
    ) -> None:
        """Constructor

        :param kind: The kind of the map or space time dataset
        :param ident: The unique identifier must be a combination of
                      the dataset name, layer name and the mapset
                      "name@mapset" or "name:layer@mapset"
                      used as as primary key in the temporal database
        :param name: The name of the map or dataset
        :param mapset: The name of the mapset
        :param layer: The layer of a vector map
        :param creator: The name of the creator
        :param ctime: The creation datetime object
        :param ttype: The temporal type

                          - "absolute" Identifier for absolute time
                          - "relative" Identifier for relative time
        :param semantic_type: The semantic type of a space time dataset
        :param mtime: The modification datetime object of a space time dataset
        """
        self.kind = kind
        SQLDatabaseInterface.__init__(self, kind.table("base"), ident)

        self.set_id(ident)
        # set_id() has derived name and mapset from the identifier
        if ident is None or name is not None or mapset is not None:
            self.set_name(name)
            self.set_mapset(mapset)
        self.set_creator(creator)
        self.set_ctime(ctime)
        self.set_ttype(ttype)

        if kind.is_stds:
            self.set_semantic_type(semantic_type)
            self.set_mtime(mtime)

        if kind.has_layer:
            self.set_id(ident)
            if ident is not None and name is None and mapset is None:
                if ident.find("@") >= 0:
                    name, mapset = ident.split("@")
                if layer is None and name.find(":") >= 0:
                    name, layer = name.split(":")
            self.set_name(name)
            self.set_mapset(mapset)
            # Layer currently only in use by vector maps
            self.set_layer(layer)

    def set_id(self, ident) -> None:
        """Convenient method to set the unique identifier (primary key)

        :param ident: The unique identifier must be a combination
                      of the dataset name, layer name and the mapset
                      "name@mapset" or "name:layer@mapset"
        """
        self.ident = ident
        self.D["id"] = ident

        if ident is not None:
            if ident.find("@") < 0:
                self.msgr.fatal(_("Wrong identifier, the mapset is missing"))
            parts = ident.split("@")
            name = parts[0]
            if len(parts) != 2 or name.count(":") > 1:
                self.msgr.fatal(
                    _(
                        "Wrong identifier <{ident}>, it must be name@mapset "
                        "or name:layer@mapset"
                    ).format(ident=ident)
                )
            self.set_mapset(parts[1])
            if name.find(":") >= 0:
                name, layer = name.split(":")
                self.set_layer(layer)
            self.set_name(name)

    def set_ctime(self, ctime=None) -> None:
        """Set the creation time of the dataset,
        if nothing set the current time is used

        :param ctime: The current time of type datetime
        """
        if ctime is None:
            self.D["creation_time"] = datetime.today()
        else:
            self.D["creation_time"] = ctime

    def set_ttype(self, ttype) -> None:
        """Set the temporal type of the dataset: absolute or relative,
        if nothing set absolute time will assumed

        :param ttype: The temporal type of the dataset "absolute or relative"
        """
        if ttype is None or (ttype not in {"absolute", "relative"}):
            self.D["temporal_type"] = "absolute"
        else:
            self.D["temporal_type"] = ttype

    def set_mtime(self, mtime=None) -> None:
        """Set the modification time of the space time dataset, if nothing set
        the current time is used
        """
        if mtime is None:
            self.D["modification_time"] = datetime.now()
        else:
            self.D["modification_time"] = mtime

    def get_map_id(self):
        """Convenient method to get the unique map identifier
        without layer information

        :return: The name of the vector map as "name@mapset"
               or None in case the id was not set
        """
        if self.id:
            if self.id.find(":") >= 0:
                # Remove the layer identifier from the id
                return self.id.split("@")[0].split(":")[0] + "@" + self.id.split("@")[1]
            return self.id
        return None

    map_id = property(fget=get_map_id, fset=None)

    def print_info(self) -> None:
        """Print information about this class in human readable style"""
        #      0123456789012345678901234567890
        print(
            " +-------------------- Basic information -------------------------------------+"  # noqa: E501
        )
        print(" | Id: ........................ " + str(self.get_id()))
        print(" | Name: ...................... " + str(self.get_name()))
        print(" | Mapset: .................... " + str(self.get_mapset()))
        if self.get_layer():
            print(" | Layer:...................... " + str(self.get_layer()))
        print(" | Creator: ................... " + str(self.get_creator()))
        print(" | Temporal type: ............. " + str(self.get_ttype()))
        print(" | Creation time: ............. " + str(self.get_ctime()))
        if self.kind.is_stds:
            print(" | Modification time:.......... " + str(self.get_mtime()))
            print(" | Semantic type:.............. " + str(self.get_semantic_type()))

    def print_shell_info(self) -> None:
        """Print information about this class in shell style"""
        print("id=" + str(self.get_id()))
        print("name=" + str(self.get_name()))
        print("mapset=" + str(self.get_mapset()))
        if self.get_layer():
            print("layer=" + str(self.get_layer()))
        print("creator=" + str(self.get_creator()))
        print("temporal_type=" + str(self.get_ttype()))
        print("creation_time='{}'".format(str(self.get_ctime())))
        if self.kind.is_stds:
            print("modification_time='{}'".format(str(self.get_mtime())))
            print("semantic_type=" + str(self.get_semantic_type()))


class RegisterRow(Row):
    """The space time datasets a map is registered in, as a comma separated string

    Usage:

    .. code-block:: pycon

        >>> init()
        >>> from grass.temporal.kinds import KINDS
        >>> t = RegisterRow(KINDS["raster"], "soil@PERMANENT", "A@P,B@P,C@P")
        >>> t.id
        'soil@PERMANENT'
        >>> t.registered_stds
        'A@P,B@P,C@P'

    """

    columns = (Column("registered_stds"),)

    def __init__(self, kind: Kind, ident=None, registered_stds=None) -> None:
        """Constructor

        :param kind: The kind of the map
        :param ident: The unique identifier must be a combination of
                      the dataset name, layer name and the mapset
                      "name@mapset" or "name:layer@mapset"
                      used as as primary key in the temporal database
        :param registered_stds: A comma separated list of space time dataset ids
        :raises ValueError: If the kind is a space time dataset, which keeps
                            its maps in a register table of its own
        """
        if kind.is_stds:
            msg = f"A {kind.name} has no register row, it has a register table"
            raise ValueError(msg)
        self.kind = kind
        SQLDatabaseInterface.__init__(self, kind.table("register"), ident)

        self.set_id(ident)
        self.set_registered_stds(registered_stds)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
