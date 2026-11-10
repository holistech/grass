"""
Univariate statistic function for space time datasets

Usage:

.. code-block:: python

    import grass.temporal as tgis

    tgis.print_gridded_dataset_univar_statistics(
        type, input, output, where, extended, no_header, fs, rast_region
    )

    # One line per quarter instead of per map
    tgis.print_gridded_dataset_univar_statistics(
        "strds", input, output, where, extended, granularity="3 months"
    )

..

SPDX-FileCopyrightText: 2012-2024 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from contextlib import ExitStack
from multiprocessing import Pool
from subprocess import PIPE
import csv
import io
import json
import os

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.pygrass.modules import Module

from .aggregation_core import aggregation_granules, sampling_relation
from .algebra.content import MapRef
from .algebra.relations import related
from .algebra.series import Extent, Series, Slot
from .db import SQLStatementError, connection
from .state import get_tgis_message_interface
from .factory import dataset_factory
from .open_stds import find_stds_id, open_old_stds


def compute_univar_stats(
    registered_map_info,
    stats_module,
    fs,
    rast_region: bool = False,
    output_format: str | None = None,
):
    """Compute univariate statistics for a map of a space time raster dataset

    The dataset may also be a raster3d dataset.

    :param registered_map_info: dict or db row with tgis info for a registered map
    :param stats_module: Pre-configured PyGRASS Module to compute univariate statistics
                        with
    :param fs: Field separator
    :param rast_region: If set True ignore the current region settings
           and use the raster map regions for univar statistical calculation.
    :param output_format: Output format specification
    """
    id_ = registered_map_info["id"]
    start = registered_map_info["start_time"]
    end = registered_map_info["end_time"]
    semantic_label = (
        ""
        if stats_module.name == "r3.univar" or not registered_map_info["semantic_label"]
        else registered_map_info["semantic_label"]
    )
    # Only r.univar, not r3.univar has nprocs parameter
    if stats_module.name == "r.univar":
        stats_module.inputs.nprocs = 1

    stats_module.inputs.map = id_
    if rast_region and (stats_module.inputs.zones or stats_module.name == "r3.univar"):
        # r.univar refuses -r together with zones and r3.univar has no -r, so
        # the region of the map goes into the environment of the module.
        # pygrass reads that from env_ (a dictionary of the whole environment)
        # and ignores an attribute env.
        if stats_module.name == "r3.univar":
            region = gs.region_env(region3d=True, raster_3d=id_)
        else:
            region = gs.region_env(raster=id_)
        stats_module.env_ = {**os.environ, "GRASS_REGION": region}
    stats_module.run()

    univar_stats = stats_module.outputs.stdout

    if not univar_stats:
        gs.warning(
            _("Unable to get statistics for raster map <%s>") % id_
            if stats_module.name == "r.univar"
            else _("Unable to get statistics for 3d raster map <%s>") % id_
        )
        return None

    if output_format == "json":
        leading = {
            "id": id_,
            "semantic_label": semantic_label
            if stats_module.name == "r.univar" and semantic_label
            else None,
            "start": str(start) if start else None,
            "end": str(end) if end else None,
        }
        return _json_stats(univar_stats, id_, leading)
    return _text_stats(univar_stats, id_, semantic_label, start, end, fs, stats_module)


def _granule_stats(granule, stats_module, fs, output_format):
    """Compute univariate statistics over all maps of a granule with r.univar

    :param granule: Tuple of the start and the end of the granule and the list
                    of the identifiers of its maps
    :param stats_module: Pre-configured PyGRASS Module r.univar
    :param fs: Field separator
    :param output_format: Output format specification
    """
    start, end, ids = granule
    names = ",".join(ids)
    stats_module.inputs.nprocs = 1
    stats_module.inputs.map = ids
    stats_module.run()

    univar_stats = stats_module.outputs.stdout
    if not univar_stats:
        gs.warning(_("Unable to get statistics for the raster maps <{}>").format(names))
        return None

    if output_format == "json":
        leading = {"maps": ids, "start": str(start), "end": str(end)}
        return _json_stats(univar_stats, names, leading)
    if output_format == "csv":
        # The identifiers are separated by commas, so the field is quoted
        # if the separator is a comma as well.
        line = io.StringIO()
        csv.writer(line, delimiter=fs, lineterminator="").writerow([names])
        names = line.getvalue()
    return _text_stats(univar_stats, names, "", start, end, fs, stats_module)


def _json_stats(univar_stats, name, leading):
    """Return the statistics of a map or a granule as a list of dictionaries

    Each dictionary has the entries of leading in front of the entries of the
    module. None if the output is not JSON.

    :param name: The map or the maps, for the warning
    :param leading: The entries that name the map or the granule
    """
    try:
        stats = json.loads(univar_stats)
    except ValueError:
        gs.warning(_("Unable to parse JSON output for map <%s>") % name)
        return None

    if isinstance(stats, dict):
        stats = [stats]

    processed_stats = []
    for s in stats:
        new_s = dict(leading)

        new_s.update(s)

        processed_stats.append(new_s)

    return processed_stats


def _text_stats(univar_stats, id_, semantic_label, start, end, fs, stats_module):
    """Return the statistics of a map as lines, each led by the map's columns

    The module prints a header line, which is dropped. The result is an empty
    string if there is nothing but the header.
    """
    lines = univar_stats.strip().split("\n")
    if len(lines) < 2:
        return ""

    prefix = (
        f"{id_}{fs}{semantic_label}{fs}{start}{fs}{end}"
        if stats_module.name == "r.univar"
        else f"{id_}{fs}{start}{fs}{end}"
    )

    output_rows = []
    for line in lines[1:]:
        if line.strip():
            formatted_line = line.replace(",", fs)
            output_rows.append(f"{prefix}{fs}{formatted_line}")

    return "\n".join(output_rows)


def _selected_rows(sp, columns, where, option, dbif, **kwargs):
    """Return the registered maps of the dataset that the condition selects

    Stops with a message if the database refuses the condition.

    :param sp: The space time dataset
    :param columns: The columns of the map register to read
    :param where: The condition on the registered maps
    :param option: The option that holds the condition, "where" or "twhere",
                   which selects the message
    :param dbif: The connected database interface
    :param kwargs: The spatial selection that get_registered_maps() takes
    """
    try:
        return sp.get_registered_maps(columns, where, "start_time", dbif, **kwargs)
    except SQLStatementError as error:
        get_tgis_message_interface().fatal(
            {
                "where": _("Invalid where condition <{}>: {}"),
                "twhere": _("Invalid twhere condition <{}>: {}"),
            }[option].format(where, error)
        )


def _gridded_columns(type, zones, extended, percentile):
    """Return the names of the columns of the statistics of gridded maps"""
    cols = (
        ["id", "semantic_label", "start", "end"]
        if type == "strds"
        else ["id", "start", "end"]
    )
    if zones:
        cols.extend(["zone", "label"])
    cols.extend(
        [
            "non_null_cells",
            "null_cells",
            "min",
            "max",
            "range",
            "mean",
            "mean_of_abs",
            "stddev",
            "variance",
            "coeff_var",
            "sum",
            "sum_abs",
        ]
    )
    if extended is True:
        cols.extend(["first_quartile", "median", "third_quartile"])
        if percentile:
            cols.extend(
                [
                    f"percentile_{str(perc).rstrip('0').rstrip('.').replace('.', '_')}"
                    for perc in percentile
                ]
            )
        else:
            cols.extend(["percentile_90"])
    return cols


def _starmap(function, arguments, nprocs):
    """Call function with each tuple of arguments, in nprocs processes if more"""
    if nprocs == 1:
        return [function(*item) for item in arguments]
    with Pool(min(nprocs, len(arguments))) as pool:
        return pool.starmap(function, arguments)


def _check_granule_options(type, granularity, sampling, rast_region, format, fs):
    """Stop with a message if the options do not go together with granularity"""
    msgr = get_tgis_message_interface()
    if granularity is None:
        if sampling:
            msgr.fatal(
                _("The sampling relates maps to granules and needs a granularity")
            )
        return
    if type != "strds":
        # r3.univar takes one map only.
        msgr.fatal(_("A granularity needs a space time raster dataset"))
    if rast_region:
        msgr.fatal(
            _(
                "The region of each map (-r) cannot be used with a granularity: "
                "the maps of a granule are computed together in one region"
            )
        )
    if format == "plain" and fs == ",":
        msgr.fatal(
            _(
                "The format plain with the separator ',' cannot be used with a "
                "granularity: the identifiers of the maps of a granule are "
                "separated by commas. Use format=csv, which quotes them, or "
                "another separator"
            )
        )


def _granules_with_maps(sp, rows, granularity, sampling):
    """Return the granules that have a related map, with the maps

    The granules are those of t.rast.aggregate for the selected registered
    maps (rows); sampling is the list of relation names from a granule to a
    map. Each item is a tuple of the start and the end of a granule and the
    identifiers of its maps, both in time order. Stops with a message for an
    invalid granularity or sampling.
    """
    absolute = sp.is_time_absolute()
    unit = None if absolute else sp.get_relative_time_unit()
    maps = Series(
        tuple(
            Slot(
                Extent(row["start_time"], row["end_time"], unit),
                MapRef(row["id"]),
                origin=row["id"],
            )
            for row in rows
        ),
        "raster",
    )
    try:
        granules = aggregation_granules(maps, granularity, absolute=absolute, unit=unit)
        partners = related(granules.slots, sampling_relation(sampling), maps.slots)
    except ValueError as error:
        get_tgis_message_interface().fatal(str(error))
    return [
        (
            granule.extent.start,
            granule.extent.end,
            [maps.slots[index].origin for index in indices],
        )
        for granule, indices in zip(granules.slots, partners, strict=True)
        if indices
    ]


def _print_nothing(format, output):
    """Print what stands for no statistics: nothing, or [] for JSON

    An empty list keeps the output valid JSON for a reader.
    """
    if format == "json":
        if output is None:
            print("[]")
        else:
            with open(output, "w") as out_file:
                out_file.write("[]\n")


def print_gridded_dataset_univar_statistics(
    type,
    input,
    output,
    where,
    extended,
    no_header: bool = False,
    fs: str = "|",
    rast_region: bool = False,
    region_relation=None,
    zones=None,
    percentile=None,
    nprocs: int = 1,
    format: str = "plain",
    granularity: str | None = None,
    sampling: list[str] | None = None,
) -> None:
    """Print univariate statistics for a space time raster or raster3d dataset.

    Returns None if the space time raster dataset is empty or if applied
    filters (where, region_relation) do not return any maps to process.

    With granularity, the statistics are those of the maps of each granule
    together, one line per granule that has a map, instead of one per map.

    :param type: Type of Space-Time-Dataset, must be either strds or str3ds
    :param input: The name of the space time dataset
    :param output: Name of the optional output file, if None stdout is used
    :param where: A temporal database where statement
    :param extended: If True compute extended statistics
    :param percentile: List of percentiles to compute
    :param no_header: Suppress the printing of column names
    :param fs: Field separator
    :param nprocs: Number of cores to use for processing
    :param format: Output format ("plain", "csv", or "json"). Default is "plain".
    :param rast_region: If set True ignore the current region settings
           and use the raster map regions for univar statistical calculation.
    :param region_relation: Process only maps with the given spatial relation
           to the computational region. A string with one of the following values:

           - "overlaps": maps that spatially overlap ("intersect")
             within the provided spatial extent
           - "is_contained": maps that are fully within the provided spatial extent
           - "contains": maps that contain (fully cover) the provided spatial extent
    :param zones: raster map with zones to calculate statistics for
    :param granularity: Size of the granules, as for t.rast.aggregate: for
           absolute time a text such as "3 months", for relative time a whole
           number of the unit of the dataset. The granules start at the start
           of the first selected map, rounded down to the granularity, and
           follow each other without gaps. Only for "strds" and not with
           rast_region; with format "plain", fs must not be a comma.
    :param sampling: List of the relations from a granule to the maps that it
           takes, the values of the option sampling of t.rast.aggregate,
           ["contains"] if None. Needs granularity.
    """
    _check_granule_options(type, granularity, sampling, rast_region, format, fs)
    # We need a database interface
    # The stack closes the output file also when the run ends in gs.fatal().
    with connection() as dbif, ExitStack() as stack:
        sp = open_old_stds(input, type, dbif)

        spatial_extent = None
        if region_relation:
            spatial_extent = gs.parse_command("g.region", flags="3gu")

        strds_cols = (
            "id,start_time,end_time,semantic_label"
            if type == "strds"
            else "id,start_time,end_time"
        )
        rows = _selected_rows(
            sp,
            strds_cols,
            where,
            "where",
            dbif,
            spatial_extent=spatial_extent,
            spatial_relation=region_relation,
        )

        if not rows and rows != [""]:
            gs.verbose(
                _(
                    "No maps found to process. "
                    "Space time {type} dataset <{id}> is either empty "
                    "or the where condition (if used) does not return any maps "
                    "or no maps with the requested spatial relation to the "
                    "computational region exist in the dataset."
                ).format(type=sp.get_new_map_instance(None).get_type(), id=sp.get_id())
            )
            _print_nothing(format, output)
            return

        granules = None
        if granularity is not None:
            sampling = sampling or ["contains"]
            granules = _granules_with_maps(sp, rows, granularity, sampling)
            if not granules:
                gs.warning(
                    _(
                        "No map is related to any granule of the granularity "
                        "<{gran}> with the sampling <{sampling}>"
                    ).format(gran=granularity, sampling=",".join(sampling))
                )
                _print_nothing(format, output)
                return

        if output is not None:
            out_file = stack.enter_context(open(output, "w"))

        if no_header is False and format != "json":
            string = fs.join(_gridded_columns(type, zones, extended, percentile))
            if output is None:
                print(string)
            else:
                out_file.write(string + "\n")

        # Define flags
        flag = ""
        if extended is True:
            flag += "e"
        if type == "strds" and rast_region is True and not zones:
            flag += "r"

        # Setup pygrass module to use for computation
        univar_module = Module(
            "r.univar" if type == "strds" else "r3.univar",
            flags=flag,
            zones=zones,
            percentile=percentile,
            stdout_=PIPE,
            format="json" if format == "json" else "csv",
            quiet=True,
            run_=False,
        )

        if granules is None:
            strings = _starmap(
                compute_univar_stats,
                [(dict(row), univar_module, fs, rast_region, format) for row in rows],
                max(nprocs, 1),
            )
        else:
            strings = _starmap(
                _granule_stats,
                [(granule, univar_module, fs, format) for granule in granules],
                max(nprocs, 1),
            )

        if format == "json":
            json_out = []

            for block in filter(None, strings):
                json_out.extend(block)

            output_str = json.dumps(json_out, indent=4)
        else:
            output_str = "\n".join(filter(None, strings))

        if output is None:
            print(output_str)
        else:
            out_file.write(output_str + "\n")


_VECTOR_MOMENTS = (
    "mean",
    "mean_abs",
    "population_stddev",
    "population_variance",
    "population_coeff_variation",
    "sample_stddev",
    "sample_variance",
    "kurtosis",
    "skewness",
)
_VECTOR_QUARTILES = ("first_quartile", "median", "third_quartile", "percentile_90")


def _vector_columns(type, extended):
    """Return the names of the columns of the statistics of vector maps"""
    cols = ["id", "start", "end", "n", "nmissing", "nnull", "min", "max", "range"]
    if type in {"point", "centroid"}:
        cols.extend(_VECTOR_MOMENTS)
        if extended is True:
            cols.extend(_VECTOR_QUARTILES)
    return cols


def _vector_fields(id_, start, end, stats, type, extended):
    """Return the values of one line, in the order of ``_vector_columns``

    A statistic that v.univar did not print (no value in the column, too few
    values for a quartile) leaves its fields empty.
    """
    fields = [str(id_), str(start), str(end)]
    fields.extend(str(stats[key]) for key in ("n", "nmissing", "nnull"))
    fields.extend(_vector_values(stats, ("min", "max", "range"), "min"))
    if type in {"point", "centroid"}:
        fields.extend(_vector_values(stats, _VECTOR_MOMENTS, "mean"))
        if extended is True:
            fields.extend(_vector_values(stats, _VECTOR_QUARTILES, "first_quartile"))
    return fields


def _vector_values(stats, keys, probe):
    """Return the values of the keys as text, empty ones if probe is missing"""
    if probe in stats:
        return [str(stats[key]) for key in keys]
    return [""] * len(keys)


def print_vector_dataset_univar_statistics(
    input,
    output,
    twhere,
    layer,
    type,
    column,
    where,
    extended,
    no_header: bool = False,
    fs: str = "|",
) -> None:
    """Print univariate statistics for a space time vector dataset

    :param input: The name of the space time dataset
    :param output: Name of the optional output file, if None stdout is used
    :param twhere: A temporal database where statement
    :param layer: The layer number used in case no layer is present
           in the temporal dataset
    :param type: options: point,line,boundary,centroid,area
    :param column: The name of the attribute column
    :param where: A temporal database where statement
    :param extended: If True compute extended statistics
    :param no_header: Suppress the printing of column names
    :param fs: Field separator
    """

    msgr = get_tgis_message_interface()
    # We need a database interface
    # The stack closes the output file also when the run ends in msgr.fatal().
    with connection() as dbif, ExitStack() as stack:
        if output is not None:
            out_file = stack.enter_context(open(output, "w"))

        id_ = find_stds_id(input, "stvds", dbif)

        sp = dataset_factory("stvds", id_)

        if sp.is_in_db(dbif) is False:
            msgr.fatal(
                _("Space time %(sp)s dataset <%(i)s> not found")
                % {"sp": sp.get_new_map_instance(None).get_type(), "i": id_}
            )

        sp.select(dbif)

        rows = _selected_rows(
            sp, "id,name,mapset,start_time,end_time,layer", twhere, "twhere", dbif
        )

        if not rows:
            msgr.fatal(
                _("Space time %(sp)s dataset <%(i)s> is empty")
                % {"sp": sp.get_new_map_instance(None).get_type(), "i": id_}
            )

        if no_header is False:
            string = fs.join(_vector_columns(type, extended))
            if output is None:
                print(string)
            else:
                out_file.write(string + "\n")

        for row in rows:
            id_ = row["name"] + "@" + row["mapset"]
            start = row["start_time"]
            end = row["end_time"]
            mylayer = row["layer"]

            flags = "g"

            if extended is True:
                flags += "e"

            if not mylayer:
                mylayer = layer

            try:
                stats = gs.parse_command(
                    "v.univar",
                    map=id_,
                    where=where,
                    column=column,
                    layer=mylayer,
                    type=type,
                    flags=flags,
                )
            except CalledModuleError as error:
                msgr.fatal(_("Error running v.univar on <{}>: {}").format(id_, error))

            if not stats:
                gs.warning(_("Unable to get statistics for vector map <%s>") % id_)
                continue

            string = fs.join(_vector_fields(id_, start, end, stats, type, extended))

            if output is None:
                print(string)
            else:
                out_file.write(string + "\n")
