"""
Metadata of the maps and space time datasets in the temporal database

Every type has a row in a metadata table of its own. The columns of a type are
listed once, in the order in which the row stores them, together with the text
that print_info() and print_shell_info() show for them; the accessors, the
printing and the constructor are generated from that list. A map has its
resolution, its range and the like, a vector map the number of its features,
and a space time dataset a title, a description, the command history and the
values the database computes from the registered maps.

Usage:

.. code-block:: pycon

    >>> import grass.temporal as tgis
    >>> from grass.temporal.kinds import KINDS
    >>> tgis.init()
    >>> meta = tgis.MetadataRow(KINDS["raster"])
    >>> meta = tgis.MetadataRow(KINDS["raster3d"])
    >>> meta = tgis.MetadataRow(KINDS["vector"])
    >>> meta = tgis.MetadataRow(KINDS["strds"])
    >>> meta = tgis.MetadataRow(KINDS["str3ds"])
    >>> meta = tgis.MetadataRow(KINDS["stvds"])

SPDX-FileCopyrightText: 2012-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .db import connection
from .kinds import KINDS
from .rows import Column, Row, SQLDatabaseInterface, accessor_property
from .schema import get_tgis_db_version_from_metadata, get_tgis_metadata
from .state import get_tgis_database_string, get_tgis_db_version

if TYPE_CHECKING:
    from .kinds import Kind

__all__ = ["MetadataRow"]

_HEAD = (
    " +-------------------- Metadata information ----------------------------------+"  # noqa: E501
)


@dataclass(frozen=True)
class Line:
    """A line of print_info() and print_shell_info()

    :param accessor: The name that get_<accessor> reads the value with
    :param label: The text before the value in print_info(), with the dots
                  that align the values and a space behind them
    :param shell: The key before the value in print_shell_info()
    """

    accessor: str
    label: str
    shell: str


def _int(value) -> int | None:
    return None if value is None else int(value)


def _float(value) -> float | None:
    return None if value is None else float(value)


def _has_semantic_label_counts() -> bool:
    """Tell whether the temporal database counts the semantic labels

    TGIS metadata is only available with an accessible temporal database
    initialized with tgis.init(). Initialization with tgis.init(skip_db_init=True)
    leaves the database string empty, and the global version of the database
    is used if tgis is not fully initialized.
    """
    if get_tgis_database_string() is not None:
        version = get_tgis_db_version_from_metadata()
    else:
        version = get_tgis_db_version()
    return version > 2


# The columns of a raster and of a 3D raster map, in the order the row stores
# them. The semantic label is left out of the row until one is given.
_RASTER_COLUMNS = (
    Column("datatype", doc="the datatype"),
    Column("cols", convert=_int, doc="the number of cols"),
    Column("rows", convert=_int, doc="the number of rows"),
    Column("number_of_cells", convert=_int, doc="the number of cells"),
    Column("nsres", convert=_float, doc="the north-south resolution"),
    Column("ewres", convert=_float, doc="the east-west resolution"),
    Column("min", convert=_float, doc="the minimum cell value"),
    Column("max", convert=_float, doc="the maximum cell value"),
)
_RASTER_LINES = (
    Line("datatype", "Datatype:................... ", "datatype"),
    Line("cols", "Number of columns:.......... ", "cols"),
    Line("rows", "Number of rows:............. ", "rows"),
    Line("number_of_cells", "Number of cells:............ ", "number_of_cells"),
    Line("nsres", "North-South resolution:..... ", "nsres"),
    Line("ewres", "East-west resolution:....... ", "ewres"),
    Line("min", "Minimum value:.............. ", "min"),
    Line("max", "Maximum value:.............. ", "max"),
)

_VECTOR_FEATURES = (
    ("points", "Number of points ........... "),
    ("lines", "Number of lines ............ "),
    ("boundaries", "Number of boundaries ....... "),
    ("centroids", "Number of centroids ........ "),
    ("faces", "Number of faces ............ "),
    ("kernels", "Number of kernels .......... "),
    ("primitives", "Number of primitives ....... "),
    ("nodes", "Number of nodes ............ "),
    ("areas", "Number of areas ............ "),
    ("islands", "Number of islands .......... "),
    ("holes", "Number of holes ............ "),
    ("volumes", "Number of volumes .......... "),
)


def _feature_columns(writable: bool) -> tuple[Column, ...]:
    """The columns that count the features of a vector map or dataset"""
    return tuple(
        Column(
            key,
            alias=f"number_of_{key}",
            writable=writable,
            doc=f"the number of {key}",
        )
        for key, _ in _VECTOR_FEATURES
    )


def _feature_lines() -> tuple[Line, ...]:
    return tuple(
        Line(f"number_of_{key}", label, key) for key, label in _VECTOR_FEATURES
    )


_STDS_COLUMNS = (
    Column("title", doc="the title"),
    Column("description", doc="the description"),
    Column("command", doc="the command history"),
    Column(
        "number_of_maps",
        writable=False,
        doc=(
            "the number of registered maps, a value the database sets "
            "automatically via SQL, so no setter exists"
        ),
    ),
)

# The order in which a space time raster dataset stores its computed columns.
_RASTER_STDS_RESOLUTIONS = (
    ("min_max", "the minimal maximum"),
    ("max_max", "the maximal maximum"),
    ("min_min", "the minimal minimum"),
    ("max_min", "the maximal minimum"),
    ("nsres_min", "the minimal north-south resolution"),
    ("nsres_max", "the maximal north-south resolution"),
    ("ewres_min", "the minimal east-west resolution"),
    ("ewres_max", "the maximal east-west resolution"),
)

# The columns of a space time raster and 3D raster dataset. Their values are
# computed from the registered maps by the database.
_RASTER_STDS_COLUMNS = (
    *(
        Column(key, writable=False, doc=f"{what} of all registered maps")
        for key, what in _RASTER_STDS_RESOLUTIONS
    ),
    Column(
        "aggregation_type",
        doc="the aggregation type of the dataset (mean, min, max, ...)",
    ),
)
# The order in which the lines are printed differs from the order of the columns.
_RASTER_STDS_LINES = tuple(
    Line(key, label, key)
    for key, label in (
        ("nsres_min", "North-South resolution min:. "),
        ("nsres_max", "North-South resolution max:. "),
        ("ewres_min", "East-west resolution min:... "),
        ("ewres_max", "East-west resolution max:... "),
        ("min_min", "Minimum value min:.......... "),
        ("min_max", "Minimum value max:.......... "),
        ("max_min", "Maximum value min:.......... "),
        ("max_max", "Maximum value max:.......... "),
        ("aggregation_type", "Aggregation type:........... "),
    )
)


class MetadataRow(Row):
    """The metadata of a map or a space time dataset

    The kind selects the class that is made: MetadataRow(kind) returns an
    instance of the class that has the columns of the type, so that a raster
    map has no number of points and a vector map no semantic label. The
    constructor takes the columns that have a setter by the name of their
    accessor, such as ``cols`` or ``number_of_points``.

    Usage:

    .. code-block:: pycon

        >>> init()
        >>> from grass.temporal.kinds import KINDS
        >>> meta = MetadataRow(
        ...     KINDS["raster3d"],
        ...     ident="soil@PERMANENT",
        ...     datatype="FCELL",
        ...     cols=100,
        ...     rows=100,
        ...     depths=100,
        ...     number_of_cells=1000000,
        ...     nsres=0.1,
        ...     ewres=0.1,
        ...     tbres=0.1,
        ...     min=0,
        ...     max=100,
        ... )
        >>> meta.datatype
        'FCELL'
        >>> meta.cols
        100
        >>> meta.depths
        100
        >>> meta.nsres
        0.1
        >>> meta.min
        0.0
        >>> meta.max
        100.0
        >>> meta.print_info()
         +-------------------- Metadata information ----------------------------------+
         | Datatype:................... FCELL
         | Number of columns:.......... 100
         | Number of rows:............. 100
         | Number of cells:............ 1000000
         | North-South resolution:..... 0.1
         | East-west resolution:....... 0.1
         | Minimum value:.............. 0.0
         | Maximum value:.............. 100.0
         | Number of depths:........... 100
         | Top-Bottom resolution:...... 0.1
        >>> meta.print_shell_info()
        datatype=FCELL
        cols=100
        rows=100
        number_of_cells=1000000
        nsres=0.1
        ewres=0.1
        min=0.0
        max=100.0
        depths=100
        tbres=0.1

    A space time dataset has the values that the database computes from its
    maps, and a title, a description and the command history:

    .. code-block:: pycon

        >>> meta = MetadataRow(
        ...     KINDS["stvds"],
        ...     ident="lidars@PERMANENT",
        ...     title="LIDARS",
        ...     description="LIDARS 2008 - 2010",
        ... )
        >>> meta.id
        'lidars@PERMANENT'
        >>> meta.title
        'LIDARS'
        >>> meta.number_of_maps
        >>> meta.number_of_points
        >>> meta.print_info()
         +-------------------- Metadata information ----------------------------------+
         | Vector register table:...... None
         | Number of points ........... None
         | Number of lines ............ None
         | Number of boundaries ....... None
         | Number of centroids ........ None
         | Number of faces ............ None
         | Number of kernels .......... None
         | Number of primitives ....... None
         | Number of nodes ............ None
         | Number of areas ............ None
         | Number of islands .......... None
         | Number of holes ............ None
         | Number of volumes .......... None
         | Number of registered maps:.. None
         |
         | Title:
         | LIDARS
         | Description:
         | LIDARS 2008 - 2010
         | Command history:
        >>> meta.print_shell_info()
        vector_register=None
        points=None
        lines=None
        boundaries=None
        centroids=None
        faces=None
        kernels=None
        primitives=None
        nodes=None
        areas=None
        islands=None
        holes=None
        volumes=None
        number_of_maps=None

    """

    # Set for each class that is made for a kind
    lines: tuple[Line, ...] = ()

    def __new__(cls, kind: Kind | None = None, *_args, **_values):
        # copy and pickle call cls.__new__(cls) of the class that was made, so
        # the kind is only needed to choose that class
        target = _CLASSES[kind.name] if cls is MetadataRow else cls
        return super().__new__(target)

    def __init__(self, kind: Kind, ident=None, **values) -> None:
        """Constructor

        :param kind: The kind of the map or space time dataset
        :param ident: The unique identifier, name@mapset or name:layer@mapset
        :param values: The columns that have a setter, by the name of their
                       accessor. A column that is not given is None, except
                       where the column has another default, or is left out of
                       the row until it is given (the semantic label).
        :raises TypeError: For a name that is no column of the type, or the
                           name of a column the database computes
        """
        self.kind = kind
        SQLDatabaseInterface.__init__(self, kind.table("metadata"), ident)

        self.set_id(ident)
        for column in self.columns:
            names = {column.accessor, column.name} & values.keys()
            if names:
                if not column.writable:
                    msg = f"The column {column.name} is computed by the database"
                    raise TypeError(msg)
                value = values.pop(names.pop())
            elif column.init() if callable(column.init) else column.init:
                value = column.default
            else:
                continue
            if column.writable:
                getattr(self, f"set_{column.accessor}")(value)
            else:
                self.D[column.name] = value
        if values:
            msg = f"{self.kind.name} metadata has no column {', '.join(values)}"
            raise TypeError(msg)

    def print_info(self) -> None:
        """Print information about this class in human readable style"""
        self._print(shell=False)

    def print_shell_info(self) -> None:
        """Print information about this class in shell style"""
        self._print(shell=True)

    def _print(self, shell: bool) -> None:
        """Print the lines of the type, without the header in shell style"""
        if not shell:
            print(_HEAD)
        for line in self.lines:
            value = str(getattr(self, f"get_{line.accessor}")())
            print(f"{line.shell}={value}" if shell else f" | {line.label}{value}")
        self._print_tail(shell)

    def _print_tail(self, shell: bool) -> None:
        """Print what follows the lines of the type"""


class _SpaceTimeMetadata:
    """What only the metadata of a space time dataset has"""

    def _print_tail(self, shell: bool) -> None:
        """Print the number of registered maps, the title and the history

        :param bool shell: True for shell style, otherwise human readable
        """
        if shell:
            print("number_of_maps=" + str(self.get_number_of_maps()))
        else:
            print(" | Number of registered maps:.. " + str(self.get_number_of_maps()))
            print(" |")
            print(" | Title:")
            print(" | " + str(self.get_title()))
            print(" | Description:")
            print(" | " + str(self.get_description()))
            print(" | Command history:")
            command = self.get_command()
            if command:
                for token in command.split("\n"):
                    print(" | " + str(token))

    def print_history(self) -> None:
        """Print history information about this class in human readable
        shell style
        """
        #      0123456789012345678901234567890
        print("# Title:")
        print("# " + str(self.get_title()))
        print("# Description:")
        print("# " + str(self.get_description()))
        print("# Command history:")
        command = self.get_command()

        if command:
            tokens = command.split("\n")
            print_list = []
            for token in tokens:
                token = str(token).rstrip().lstrip()
                if len(token) > 1:
                    print_list.append(token)

            count = 0
            for token in print_list:
                count += 1
                if len(token) > 1:
                    if token[0] == "#":
                        print(token)
                    elif count < len(print_list):
                        print(token + " \\")
                    else:
                        print(token)


class _SemanticLabelsMetadata:
    """What only the metadata of a space time raster dataset has"""

    def get_semantic_labels(self, dbif=None):
        """Get the distinct semantic labels of registered maps
           The distinct semantic labels are not stored in the metadata table
           and fetched on-the-fly

        :param dbif: The database interface to be used, if None a
                     connection is opened for this call and closed again
        :return: None if not found
        """
        # A metadata object that is not read from the temporal database has
        # no register table; the query would name the table None.
        if self.get_raster_register() is None:
            return None

        sql = "SELECT distinct semantic_label FROM %s WHERE %s.id " % (
            "raster_metadata",
            "raster_metadata",
        )

        sql += "IN (SELECT id FROM %s)" % (str(self.get_raster_register()))

        # One connection serves the version check and the query. Every
        # SQLDatabaseInterfaceConnection runs t.connect for each mapset.
        with connection(dbif) as dbif:
            if get_tgis_db_version_from_metadata(get_tgis_metadata(dbif)) <= 2:
                # band names supported from TGIS DB version 3
                return None
            dbif.execute(sql, mapset=self.mapset)
            rows = dbif.fetchall(mapset=self.mapset)

            if not rows:
                return None
            string = ""
            count = 0
            for row in rows:
                if row["semantic_label"]:
                    if count == 0:
                        string += row["semantic_label"]
                    else:
                        string += ",%s" % row["semantic_label"]
                    count += 1

            if count > 0:
                return string
            return None

    semantic_labels = property(fget=get_semantic_labels)


def _register_column(name: str, what: str) -> Column:
    return Column(name, doc=f"the name of the table that registers the {what}")


def _make_class(
    kind: Kind, columns: tuple[Column, ...], lines: tuple[Line, ...], *bases: type
) -> type[MetadataRow]:
    """Make the class that has the columns and the lines of a kind"""
    name = {
        "raster": "RasterMetadata",
        "raster3d": "Raster3DMetadata",
        "vector": "VectorMetadata",
        "strds": "STRDSMetadata",
        "str3ds": "STR3DSMetadata",
        "stvds": "STVDSMetadata",
    }[kind.name]
    attributes = {
        "columns": columns,
        "lines": lines,
        "__doc__": f"The metadata of a {kind.name} in the table {kind.table('metadata')}",
        "__module__": __name__,
    }
    if kind.name == "vector":
        attributes["is_3d"] = accessor_property("3d_info")
    return type(name, (*bases, MetadataRow), attributes)


_RASTER_3D = (
    Column("tbres", convert=_float, doc="the top-bottom resolution"),
    Column("depths", convert=_int, doc="the number of depths"),
)

_CLASSES: dict[str, type[MetadataRow]] = {
    "raster": _make_class(
        KINDS["raster"],
        (
            *_RASTER_COLUMNS,
            Column("semantic_label", init=False, doc="the semantic label identifier"),
        ),
        (
            *_RASTER_LINES,
            Line("semantic_label", "Semantic label:............. ", "semantic_label"),
        ),
    ),
    "raster3d": _make_class(
        KINDS["raster3d"],
        (*_RASTER_COLUMNS, *_RASTER_3D),
        (
            *_RASTER_LINES,
            Line("depths", "Number of depths:........... ", "depths"),
            Line("tbres", "Top-Bottom resolution:...... ", "tbres"),
        ),
    ),
    "vector": _make_class(
        KINDS["vector"],
        (
            Column(
                "is_3d",
                alias="3d_info",
                default=False,
                doc="whether the vector map is three dimensional",
            ),
            *_feature_columns(writable=True),
        ),
        (Line("3d_info", "Is map 3d .................. ", "is_3d"), *_feature_lines()),
    ),
    "strds": _make_class(
        KINDS["strds"],
        (
            *_STDS_COLUMNS,
            *_RASTER_STDS_COLUMNS,
            Column(
                "number_of_semantic_labels",
                writable=False,
                init=_has_semantic_label_counts,
                doc="the number of registered semantic labels",
            ),
            _register_column("raster_register", "raster maps"),
        ),
        (
            Line("raster_register", "Raster register table:...... ", "raster_register"),
            *_RASTER_STDS_LINES,
            Line(
                "number_of_semantic_labels",
                "Number of semantic labels:.. ",
                "number_of_semantic_labels",
            ),
            Line("semantic_labels", "Semantic labels:............ ", "semantic_labels"),
        ),
        _SpaceTimeMetadata,
        _SemanticLabelsMetadata,
    ),
    "str3ds": _make_class(
        KINDS["str3ds"],
        (
            *_STDS_COLUMNS,
            *_RASTER_STDS_COLUMNS,
            _register_column("raster3d_register", "3D raster maps"),
            Column(
                "tbres_min",
                writable=False,
                doc="the minimal top-bottom resolution of all registered maps",
            ),
            Column(
                "tbres_max",
                writable=False,
                doc="the maximal top-bottom resolution of all registered maps",
            ),
        ),
        (
            Line(
                "raster3d_register",
                "3D raster register table:... ",
                "raster3d_register",
            ),
            Line("tbres_min", "Top-bottom resolution min:.. ", "tbres_min"),
            Line("tbres_max", "Top-bottom resolution max:.. ", "tbres_max"),
            *_RASTER_STDS_LINES,
        ),
        _SpaceTimeMetadata,
    ),
    "stvds": _make_class(
        KINDS["stvds"],
        (
            *_STDS_COLUMNS,
            _register_column("vector_register", "vector maps"),
            *_feature_columns(writable=False),
        ),
        (
            Line("vector_register", "Vector register table:...... ", "vector_register"),
            *_feature_lines(),
        ),
        _SpaceTimeMetadata,
    ),
}

# Pickle finds a class by its name in the module, so the made classes are
# named there, as the hand-written classes were.
globals().update({cls.__name__: cls for cls in _CLASSES.values()})


if __name__ == "__main__":
    import doctest

    doctest.testmod()
