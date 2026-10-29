"""
Functions to create space time dataset lists

Usage:

.. code-block:: python

    import grass.temporal as tgis

    tgis.register_maps_in_space_time_dataset(type, name, maps)


SPDX-FileCopyrightText: 2012-2022 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
:authors: Vaclav Petras
"""

import os
import sys
from contextlib import contextmanager

import grass.script as gs

from .datetime_math import time_delta_to_relative_time
from .db import (
    SQLStatementError,
    connection,
    sql_identifier,
    sql_literal,
    sql_statement,
)
from .kinds import find_kind
from .open_stds import open_old_stds
from .state import get_tgis_message_interface
from .topology import _has_start

#: Columns that only the methods delta, deltagaps and gran can list: they
#: compute the values from the times of the maps, the temporal database has
#: no such columns.
_DELTA_ONLY_COLUMNS = ("interval_length", "distance_from_begin")


def message_option_value_excludes_option_value(
    option_name, option_value, excluded_option_name, excluded_option_value, reason
):
    """Return the message for a combination of two option values that is refused"""
    return _(
        "Combining {option_name}={option_value} and "
        "{excluded_option_name}={excluded_option_value} is not allowed. {reason}"
    ).format(
        option_name=option_name,
        option_value=option_value,
        excluded_option_name=excluded_option_name,
        excluded_option_value=excluded_option_value,
        reason=reason,
    )


def message_option_value_excludes_option(
    option_name, option_value, excluded_option_name, reason
):
    """Return the message for an option that is refused with a value of another"""
    return _(
        "The option {excluded_option_name} is not allowed with "
        "{option_name}={option_value}. {reason}"
    ).format(
        excluded_option_name=excluded_option_name,
        option_name=option_name,
        option_value=option_value,
        reason=reason,
    )


def message_option_value_excludes_flag(option_name, option_value, flag_name, reason):
    """Return the message for a flag that is refused with a value of an option"""
    return _(
        "The flag -{flag_name} is not allowed with {option_name}={option_value}."
        " {reason}"
    ).format(
        flag_name=flag_name,
        option_name=option_name,
        option_value=option_value,
        reason=reason,
    )


def checked_separator(output_format, separator, *, column_names):
    """Check the separator of a tool that prints a table as plain, csv or json

    :param output_format: The value of the option format
    :param separator: The separator, already converted by gs.separator(), an
                      empty string if the user gave none
    :param column_names: True if the user set the flag that changes whether
                         the column names are printed
    :return: The separator, the comma for csv and the bar for the other
             formats if the user gave none
    :raises ValueError: for a csv separator of more than one character, and
                        for a separator or the flag with json, whose output
                        has its own structure and always names the columns
    """
    if output_format == "csv":
        if not separator:
            return ","
        if len(separator) > 1:
            msg = _("A standard CSV separator (delimiter) is only one character long")
            raise ValueError(msg)
    elif output_format == "json":
        if column_names:
            msg = _("Column names are always included in JSON output")
            raise ValueError(msg)
        if separator:
            msg = _("Separator option is not allowed with JSON format")
            raise ValueError(msg)
    elif not separator:
        return "|"
    return separator


def check_list_format(
    output_format,
    separator,
    method,
    columns,
    header,
    header_flag,
    separator_reason=None,
):
    """Check format, separator, columns and header flag of a list tool

    The method comma is the old name of the format line and is treated as
    such unless the format names another one.

    :param output_format: The value of the option format
    :param separator: The separator, already converted by gs.separator(), an
                      empty string if the user gave none
    :param method: The value of the option method
    :param columns: The value of the option columns
    :param header: True if the flag that suppresses the column names is set
    :param header_flag: The letter of that flag, for the message
    :param separator_reason: The reason given when a separator is refused with
                             json or yaml, a default text if None
    :return: The tuple (output_format, separator) with the format line for the
             method comma and the default separator filled in
    :raises ValueError: with the message for the combination that is refused
    """
    if separator_reason is None:
        separator_reason = _("Separator is part of the format")
    if output_format == "csv":
        if not separator:
            separator = ","
        elif len(separator) > 1:
            raise ValueError(
                message_option_value_excludes_option_value(
                    option_name="format",
                    option_value=output_format,
                    excluded_option_name="separator",
                    excluded_option_value=separator,
                    reason=_(
                        "A standard CSV separator (delimiter) is only one character "
                        "long"
                    ),
                )
            )
    elif output_format in {"json", "yaml"}:
        if header:
            raise ValueError(
                message_option_value_excludes_flag(
                    option_name="format",
                    option_value=output_format,
                    flag_name=header_flag,
                    reason=_("Column names are always included"),
                )
            )
        if separator:
            raise ValueError(
                message_option_value_excludes_option_value(
                    option_name="format",
                    option_value=output_format,
                    excluded_option_name="separator",
                    excluded_option_value=separator,
                    reason=separator_reason,
                )
            )
    elif output_format == "line" or method == "comma":
        output_format = "line"
        if not separator:
            separator = ","
        columns_list = columns.split(",")
        if len(columns_list) > 1:
            raise ValueError(
                message_option_value_excludes_option_value(
                    option_name="format",
                    option_value=output_format,
                    excluded_option_name="columns",
                    excluded_option_value=columns,
                    reason=_("Only one column is allowed (not {num_columns})").format(
                        num_columns=len(columns_list)
                    ),
                )
            )
    elif not separator:  # output_format = "plain"
        separator = "|"
    return output_format, separator


def check_list_method(method, order, columns, delta_excluded_columns):
    """Check the columns and the order of a list tool against its method

    :param method: The value of the option method
    :param order: The value of the option order
    :param columns: The value of the option columns
    :param delta_excluded_columns: The columns that the methods delta,
                                   deltagaps and gran cannot list
    :raises ValueError: with the message for the combination that is refused
    """
    columns_list = columns.split(",") if columns else []
    if method in {"delta", "deltagaps", "gran"}:
        if order:
            raise ValueError(
                message_option_value_excludes_option(
                    option_name="method",
                    option_value=method,
                    excluded_option_name="order",
                    reason=_("Values are always ordered by start_time"),
                )
            )
        excluded = delta_excluded_columns
    else:
        excluded = _DELTA_ONLY_COLUMNS
    for column in excluded:
        if column in columns_list:
            raise ValueError(
                message_option_value_excludes_option_value(
                    option_name="method",
                    option_value=method,
                    excluded_option_name="columns",
                    excluded_option_value=columns,
                    reason=_(
                        "Column '{name}' is not available with the method '{method}'"
                    ).format(name=column, method=method),
                )
            )


def check_list_options(
    options, flags, *, header_flag, delta_excluded_columns, separator_reason=None
):
    """Check the options of a list tool against each other

    Format and separator are checked before method, order and columns, so
    that a call with several refused combinations reports the same one as
    t.rast.list and t.rast3d.list did when each carried its own checks.

    :param options: The options of the tool as returned by gs.parser()
    :param flags: The flags of the tool as returned by gs.parser()
    :param header_flag: The letter of the flag that suppresses the column names
    :param delta_excluded_columns: The columns that the methods delta,
                                   deltagaps and gran cannot list
    :param separator_reason: See check_list_format()
    :return: The tuple (output_format, separator) to list with
    :raises ValueError: with the message for the combination that is refused
    """
    output_format, separator = check_list_format(
        options["format"],
        gs.separator(options["separator"]),
        options["method"],
        options["columns"],
        flags[header_flag],
        header_flag,
        separator_reason,
    )
    check_list_method(
        options["method"], options["order"], options["columns"], delta_excluded_columns
    )
    return output_format, separator


class _ListingError(ValueError):
    """A combination of columns, method and format that cannot be listed

    list_maps_of_stds() reports it as a message; any other ValueError is a
    bug and keeps its traceback.
    """


def _view_name(dataset_type, temporal_type):
    """Return the name of the database view of a dataset type

    The views of 3D raster maps are named raster3d_view_*, the type is
    raster_3d.
    """
    kind = find_kind(dataset_type)
    # An unknown type stays in the name, so that the query reports the missing
    # view as it always did.
    prefix = kind.table_prefix if kind else dataset_type
    suffix = "abs_time" if temporal_type == "absolute" else "rel_time"
    return f"{prefix}_view_{suffix}"


def _common_columns(dbif, stds_type, ttype, mapset):
    """Return the columns that the views of all the dataset types have

    The schema is read from the view of each type in the database of the mapset.
    """
    type_schemas = []
    for dtype in stds_type:
        sql = sql_statement(
            "SELECT * FROM {view} WHERE 0=1", view=_view_name(dtype, ttype)
        )
        dbif.execute(sql, mapset=mapset)
        type_schemas.append([d[0] for d in dbif.connections[mapset].cursor.description])
    return [
        col
        for col in type_schemas[0]
        if all(col in schema for schema in type_schemas[1:])
    ]


def _requested_columns(columns, common_columns, stds_type):
    """Return the columns to read: the requested ones or all the common ones

    Stops with a message for a requested column that the types do not share.
    """
    if not columns or columns.find("all") != -1:
        return common_columns
    msgr = get_tgis_message_interface()
    requested_columns = [col.strip() for col in columns.split(",") if col != "type"]
    valid = set(common_columns)
    for col in requested_columns:
        if col not in valid:
            if len(stds_type) == 1:
                msgr.fatal(
                    _("Column '%s' is not available for the requested dataset type")
                    % col
                )
            else:
                msgr.fatal(
                    _(
                        "Column '%s' is not available for the requested combination"
                        " of dataset types"
                    )
                    % col
                )
    return requested_columns


def listed_columns(dbif, type, temporal_type, columns, mapset):
    """Return the database columns that get_dataset_list() reads for columns

    The requested columns without blanks and in their order, or all the
    columns the views of the types share when columns is empty or contains
    "all". The type column is not a database column and is left out.

    :param dbif: The database interface to be used
    :param type: The dataset type as a string or a list of strings
    :param temporal_type: A single temporal type (absolute or relative)
    :param columns: A comma separated list of columns or None
    :param mapset: The mapset whose database holds the views
    :return: The list of the column names
    """
    stds_type = [type] if isinstance(type, str) else type
    common_columns = _common_columns(dbif, stds_type, temporal_type, mapset)
    return _requested_columns(columns, common_columns, stds_type)


def get_dataset_list(
    type,
    temporal_type,
    columns=None,
    where=None,
    order=None,
    dbif=None,
):
    """Return a list of time stamped maps or space time datasets of a specific
    temporal type that are registered in the temporal database

    This method returns a dictionary, the keys are the available mapsets,
    the values are the rows from the SQL database query.

    :param type: The dataset type(s) (strds, str3ds, stvds, raster,
                 raster_3d, vector) as a string with a single dataset type
                 (e.g. "strds") or a list of strings with dataset types (e.g.
                 ["strds", "stvds"])
    :param temporal_type: The temporal type of the datasets (absolute,
                          relative) as a string or a list of strings
    :param columns: A comma separated list of columns that will be selected
    :param where: A where statement for selected listing without "WHERE"
    :param order: A comma separated list of columns to order the
                  datasets by category
    :param dbif: The database interface to be used

    :return: A dictionary with mapsets as keys. When *type* is a string,
             values are raw database row objects (preserving backward
             compatibility). When *type* is a list, values are plain
             dicts with an additional ``"type"`` key identifying the
             dataset type of each record.

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.core.init()
        >>> name = "list_stds_test"
        >>> sp = tgis.open_stds.open_new_stds(
        ...     name=name,
        ...     type="strds",
        ...     temporaltype="absolute",
        ...     title="title",
        ...     descr="descr",
        ...     semantic="mean",
        ...     dbif=None,
        ...     overwrite=True,
        ... )
        >>> mapset = tgis.get_current_mapset()
        >>> stds_list = tgis.list_stds.get_dataset_list(
        ...     "strds", "absolute", columns="name"
        ... )
        >>> rows = stds_list[mapset]
        >>> for row in rows:
        ...     if row["name"] == name:
        ...         print(True)
        True
        >>> stds_list = tgis.list_stds.get_dataset_list(
        ...     "strds",
        ...     "absolute",
        ...     columns="name,mapset",
        ...     where="mapset = '%s'" % (mapset),
        ... )
        >>> rows = stds_list[mapset]
        >>> for row in rows:
        ...     if row["name"] == name and row["mapset"] == mapset:
        ...         print(True)
        True
        >>> check = sp.delete()

    """
    msgr = get_tgis_message_interface()

    with connection(dbif) as dbif:
        is_list_input = isinstance(type, list)
        stds_type = [type] if isinstance(type, str) else type
        if isinstance(temporal_type, str):
            temporal_type = [temporal_type]

        result = {}

        for ttype in temporal_type:
            mapset_for_schema = (
                list(dbif.tgis_mapsets.keys())[0] if dbif.tgis_mapsets else None
            )
            if not mapset_for_schema:
                continue

            final_columns = listed_columns(
                dbif, stds_type, ttype, columns, mapset_for_schema
            )

            if not final_columns:
                msgr.fatal(_("No valid database columns were requested"))

            selected = ",".join(sql_identifier(column) for column in final_columns)

            for dtype in stds_type:
                for mapset in dbif.tgis_mapsets:
                    view = sql_identifier(_view_name(dtype, ttype))
                    in_mapset = f"mapset = {sql_literal(mapset)}"
                    # In brackets: an OR in the condition would otherwise
                    # take the rows of every mapset
                    condition = f"({where}) AND {in_mapset}" if where else in_mapset
                    ordering = f" ORDER BY {order}" if order else ""
                    # The where and order options are SQL of the caller by design.
                    sql = f"SELECT {selected} FROM {view} WHERE {condition}{ordering}"  # noqa: S608

                    dbif.execute(sql, mapset=mapset)
                    rows = dbif.fetchall(mapset=mapset)

                    if rows:
                        if mapset not in result:
                            result[mapset] = []
                        if is_list_input:
                            for row in rows:
                                result[mapset].append({**dict(row), "type": dtype})
                        else:
                            result[mapset].extend(rows)

        return result


@contextmanager
def _open_output_file(file, encoding="utf-8", **kwargs):
    if not file:
        yield sys.stdout
    elif not isinstance(file, (str, os.PathLike)):
        yield file
    else:
        with open(file, "w", encoding=encoding, **kwargs) as stream:
            yield stream


def _write_line(items, separator, file) -> None:
    if not separator:
        separator = ","
    output = separator.join([f"{item}" for item in items])
    with _open_output_file(file) as stream:
        print(f"{output}", file=stream)


def _write_plain(rows, header, separator, file) -> None:
    def write_plain_row(items, separator, file) -> None:
        output = separator.join([f"{item}" for item in items])
        print(f"{output}", file=file)

    with _open_output_file(file) as stream:
        # Print the column names if requested
        if header:
            write_plain_row(items=header, separator=separator, file=stream)
        for row in rows:
            write_plain_row(items=row, separator=separator, file=stream)


def _write_json(rows, column_names, file) -> None:
    # Lazy import output format-specific dependencies.
    # pylint: disable=import-outside-toplevel
    import datetime
    import json

    class ResultsEncoder(json.JSONEncoder):
        """Results encoder for JSON which handles SimpleNamespace objects"""

        def default(self, o):
            """Handle additional types"""
            if isinstance(o, datetime.datetime):
                return f"{o}"
            return super().default(o)

    dict_rows = []
    for row in rows:
        new_row = dict(zip(column_names, row, strict=True))
        dict_rows.append(new_row)
    meta = {"column_names": column_names}
    with _open_output_file(file) as stream:
        json.dump({"data": dict_rows, "metadata": meta}, stream, cls=ResultsEncoder)


def _write_yaml(rows, column_names, file=sys.stdout) -> None:
    # Lazy import output format-specific dependencies.
    # pylint: disable=import-outside-toplevel
    import yaml

    class NoAliasIndentListSafeDumper(yaml.SafeDumper):
        """YAML dumper class which does not create aliases and indents lists

        This avoid dates being labeled with &id001 and referenced with *id001.
        Instead, same dates are simply repeated.

        Lists have their dash-space (- ) indented instead of considering the
        dash and space to be a part of indentation. This might be better handled
        when https://github.com/yaml/pyyaml/issues/234 is resolved.
        """

        def ignore_aliases(self, data) -> bool:
            return True

        def increase_indent(self, flow: bool = False, indentless: bool = False):
            return super().increase_indent(flow=flow, indentless=False)

    dict_rows = []
    for row in rows:
        new_row = dict(zip(column_names, row, strict=True))
        dict_rows.append(new_row)
    meta = {"column_names": column_names}
    with _open_output_file(file) as stream:
        print(
            yaml.dump(
                {"data": dict_rows, "metadata": meta},
                Dumper=NoAliasIndentListSafeDumper,
                default_flow_style=False,
            ),
            end="",
            file=stream,
        )


def _write_csv(rows, column_names, separator, file=sys.stdout) -> None:
    # Lazy import output format-specific dependencies.
    # pylint: disable=import-outside-toplevel
    import csv

    # Newlines handled by the CSV writer. Set according to the package doc.
    with _open_output_file(file, newline="") as stream:
        spamwriter = csv.writer(
            stream,
            delimiter=separator,
            quotechar='"',
            doublequote=True,
            quoting=csv.QUOTE_NONNUMERIC,
            lineterminator="\n",
        )
        if column_names:
            spamwriter.writerow(column_names)
        for row in rows:
            spamwriter.writerow(row)


def _write_table(rows, column_names, output_format, separator, file):
    if output_format == "json":
        _write_json(rows=rows, column_names=column_names, file=file)
    elif output_format == "yaml":
        _write_yaml(rows=rows, column_names=column_names, file=file)
    elif output_format == "plain":
        # No particular reason for this separator except that this is the original
        # behavior.
        if not separator:
            separator = "\t"
        _write_plain(rows=rows, header=column_names, separator=separator, file=file)
    elif output_format == "csv":
        if not separator:
            separator = ","
        _write_csv(rows=rows, column_names=column_names, separator=separator, file=file)
    else:
        msg = f"Unknown value '{output_format}' for output_format"
        raise ValueError(msg)


def _get_get_registered_maps_as_objects_with_method(dataset, where, method, gran, dbif):
    if method == "deltagaps":
        return dataset.get_registered_maps_as_objects_with_gaps(where=where, dbif=dbif)
    if method == "delta":
        return dataset.get_registered_maps_as_objects(
            where=where, order="start_time", dbif=dbif
        )
    if method == "gran":
        return dataset.get_registered_maps_as_objects_by_granularity(
            gran=gran, where=where, dbif=dbif
        )
    msg = f"Invalid method '{method}'"
    raise _ListingError(msg)


def _get_get_registered_maps_as_objects_delta_gran(
    dataset, where, method, gran, dbif, msgr
):
    if method == "gran" and not dataset.metadata.get_number_of_maps():
        # Without maps the dataset has no granularity to list by; the method
        # would end in a message about a wrong granularity "None". With a
        # granule of the user it would print the header only, so both are
        # refused alike.
        msgr.fatal(
            _(
                "Nothing found in the database for space time dataset <{name}> "
                "(type: {element_type}): {detail}"
            ).format(
                name=dataset.get_id(),
                element_type=dataset.get_type(),
                detail=_("Dataset is empty"),
            )
        )
    maps = _get_get_registered_maps_as_objects_with_method(
        dataset=dataset, where=where, method=method, gran=gran, dbif=dbif
    )
    if not maps:
        return []

    if isinstance(maps[0], list):
        if len(maps[0]) <= 0:
            msgr.warning(_("Empty map list"))
            return []
        first_maps = [map_[0] for map_ in maps if map_]
    else:
        first_maps = maps
    # A map without start time (the reading leaves one when the stored end
    # lies before the start) cannot give the distance of the others, so the
    # distances count from the first map that has one.
    first_time = next(
        (
            map_.get_temporal_extent_as_tuple()[0]
            for map_ in first_maps
            if _has_start(map_)
        ),
        None,
    )

    records = []
    for map_object in maps:
        if isinstance(map_object, list):
            if len(map_object) > 0:
                map_object = map_object[0]
            else:
                msgr.fatal(_("Empty entry in map list, this should not happen"))

        if not _has_start(map_object):
            msgr.warning(
                _("Map <{}> has no start time; it is listed without times").format(
                    map_object.get_id()
                )
            )
            records.append((map_object, None, None, None, None))
            continue
        start, end = map_object.get_temporal_extent_as_tuple()
        delta = end - start if end else None
        delta_first = start - first_time

        if map_object.is_time_absolute():
            if end:
                delta = time_delta_to_relative_time(delta)
            delta_first = time_delta_to_relative_time(delta_first)
        records.append((map_object, start, end, delta, delta_first))
    return records


def _get_list_of_maps_delta_gran(dataset, columns, where, method, gran, dbif, msgr):
    maps = _get_get_registered_maps_as_objects_delta_gran(
        dataset=dataset, where=where, method=method, gran=gran, dbif=dbif, msgr=msgr
    )
    rows = []
    for map_object, start, end, delta, delta_first in maps:
        # Here the names must be the same as in the database
        # to make the interface consistent.
        values = {
            "id": map_object.get_id(),
            "name": map_object.get_name(),
            "layer": map_object.get_layer(),
            "mapset": map_object.get_mapset(),
            "start_time": start,
            "end_time": end,
            "interval_length": delta,
            "distance_from_begin": delta_first,
        }
        for column in columns:
            if column not in values:
                msg = f"Unsupported column '{column}'"
                raise _ListingError(msg)
        rows.append([values[column] for column in columns])
    return rows


def _get_list_of_maps_stds(
    element_type,
    name,
    columns,
    order,
    where,
    method,
    output_format,
    gran=None,
    dbif=None,
):
    with connection(dbif) as dbif:
        msgr = get_tgis_message_interface()

        dataset = open_old_stds(name, element_type, dbif)

        def check_columns(column_names, output_format, element_type):
            if element_type != "stvds" and "layer" in columns:
                msg = (
                    f"Column 'layer' is not allowed with temporal type '{element_type}'"
                )
                raise _ListingError(msg)
            if output_format == "line" and len(column_names) > 1:
                msg = (
                    f"'{output_format}' output_format can have only 1 column, "
                    f"not {len(column_names)}"
                )
                raise _ListingError(msg)

        # This method expects a list of objects for gap detection
        if method in {"delta", "deltagaps", "gran"}:
            if not columns:
                if output_format == "line":
                    # Only one column is needed.
                    columns = ["id"]
                else:
                    columns = ["id", "name"]
                    if element_type == "stvds":
                        columns.append("layer")
                    columns.extend(
                        [
                            "mapset",
                            "start_time",
                            "end_time",
                            "interval_length",
                            "distance_from_begin",
                        ]
                    )
            check_columns(
                column_names=columns,
                output_format=output_format,
                element_type=element_type,
            )
            rows = _get_list_of_maps_delta_gran(
                dataset=dataset,
                columns=columns,
                where=where,
                method=method,
                gran=gran,
                dbif=dbif,
                msgr=msgr,
            )
        else:
            if columns:
                check_columns(
                    column_names=columns,
                    output_format=output_format,
                    element_type=element_type,
                )
            elif output_format == "line":
                # For list of values, only one column is needed.
                columns = ["id"]
            else:
                columns = ["name", "mapset", "start_time", "end_time"]
            if not order:
                order = "start_time"

            try:
                rows = dataset.get_registered_maps(
                    ",".join(columns), where, order, dbif
                )
            except SQLStatementError as error:
                msgr.fatal(_("Invalid where condition <{}>: {}").format(where, error))

            # End with error for the old, custom formats. Proper formats simply return
            # empty result whatever empty is for each format (e.g., empty list for JSON).
            if not rows and (output_format in {"plain", "line"}):
                msgr.fatal(
                    _(
                        "Nothing found in the database for space time dataset <{name}> "
                        "(type: {element_type}): {detail}"
                    ).format(
                        name=dataset.get_id(),
                        element_type=element_type,
                        detail=(
                            _(
                                "Dataset is empty or where clause is too constrained or "
                                "incorrect"
                            )
                            if where
                            else _("Dataset is empty")
                        ),
                    )
                )
        return rows, columns


# The code is compatible with pre-v8.2 versions, but for v9, it needs to be reviewed
# to remove the backwards compatibility which will clean it up.
def list_maps_of_stds(
    type,  # pylint: disable=redefined-builtin
    input,  # pylint: disable=redefined-builtin
    columns,
    order,
    where,
    separator,
    method,
    no_header: bool = False,
    gran=None,
    dbif=None,
    outpath=None,
    output_format=None,
) -> None:
    """List the maps of a space time dataset using different methods

    :param type: The type of the maps raster, raster3d or vector
    :param input: Name of a space time raster dataset
    :param columns: A comma separated list of columns to be printed to stdout
    :param order: A comma separated list of columns to order the
                  maps by category
    :param where: A where statement for selected listing without "WHERE"
                  e.g: start_time < "2001-01-01" and end_time > "2001-01-01"
    :param separator: The field separator character between the columns
    :param method: String identifier to select a method out of cols,
                   comma, delta or deltagaps
    :param dbif: The database interface to be used

        - "cols" Print preselected columns specified by columns
        - "comma" Print the map ids ("name@mapset") as comma separated string
        - "delta" Print the map ids ("name@mapset") with start time,
           end time, relative length of intervals and the relative
           distance to the begin
        - "deltagaps" Same as "delta" with additional listing of gaps.
           Gaps can be easily identified as the id is "None"
        - "gran" List map using the granularity of the space time dataset,
           columns are identical to deltagaps

    :param no_header: Suppress the printing of column names
    :param gran: The user defined granule to be used if method=gran is
                 set, in case gran=None the granule of the space time
                 dataset is used
    :param outpath: The path to file where to save output
    """
    if gran == "":
        gran = None
    if not output_format:
        if method == "comma":
            output_format = "line"
            if not separator:
                separator = ","
        else:
            output_format = "plain"

    if columns and isinstance(columns, str):
        columns = columns.split(",")

    try:
        rows, columns = _get_list_of_maps_stds(
            element_type=type,
            name=input,
            columns=columns,
            order=order,
            where=where,
            method=method,
            output_format=output_format,
            gran=gran,
            dbif=dbif,
        )
    except _ListingError as error:
        get_tgis_message_interface().fatal(str(error))

    if output_format == "line":
        _write_line(
            items=[row[0] for row in rows],
            separator=separator,
            file=outpath,
        )
    else:
        _write_table(
            rows=rows,
            column_names=None if no_header else columns,
            separator=separator,
            output_format=output_format,
            file=outpath,
        )
