"""
Export functions for space time datasets

Usage:

.. code-block:: python

    import grass.temporal as tgis

    input = "temp_1950_2012@PERMANENT"
    output = "/tmp/temp_1950_2012.tar.gz"
    compression = "gzip"
    directory = "/tmp"
    where = None
    format_ = "GTiff"
    type_ = "strds"
    tgis.export_stds(input, output, compression, directory, where, format_, type_)


SPDX-FileCopyrightText: 2012-2021 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import contextlib
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import grass.script as gs
from grass.exceptions import CalledModuleError

from .db import SQLStatementError
from .kinds import KINDS, find_kind, stds_kind_of
from .open_stds import open_old_stds
from .state import get_tgis_message_interface

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .kinds import Kind

proj_file_name = "proj.txt"
init_file_name = "init.txt"
metadata_file_name = "metadata.txt"
read_file_name = "readme.txt"
list_file_name = "list.txt"
tmp_tar_file_name = "archive"

# The suffix of the file that an archive holds for each map, by export format;
# the import reads the files by the same table.
FORMAT_SUFFIX = {
    "GTiff": ".tif",
    "AAIGrid": ".asc",
    "GML": ".xml",
    "GPKG": ".gpkg",
    "pack": ".pack",
}


def _gdal_type_for_cell_map(minimum, maximum, nodata):
    """Return the smallest GDAL integer type that holds a CELL map and nodata

    The candidates are Byte, UInt16, Int16, UInt32 and Int32, in the order of
    their size, the unsigned type first where both of a size fit. Returns None
    if nodata is not a whole number or no candidate holds all three values;
    the caller then leaves the choice to r.out.gdal.
    """
    # is_integer() is False for nan and inf, which int() would refuse.
    if nodata is None or not float(nodata).is_integer():
        return None
    nodata = int(nodata)
    lowest = min(minimum, maximum, nodata)
    highest = max(minimum, maximum, nodata)
    for name, low, high in (
        ("Byte", 0, 2**8 - 1),
        ("UInt16", 0, 2**16 - 1),
        ("Int16", -(2**15), 2**15 - 1),
        ("UInt32", 0, 2**32 - 1),
        ("Int32", -(2**31), 2**31 - 1),
    ):
        if low <= lowest and highest <= high:
            return name
    return None


def _list_line(fs: str, name: str, start: str, end: str | None, *more: object) -> str:
    """Return the line of the list file for a map

    A map in a time instant has no end, and its line repeats the start. The
    values after the end are written as they are, so a missing one is "None".
    """
    return fs.join(str(value) for value in (name, start, end or start, *more)) + "\n"


def _gdal_tif_options(
    datatype: str, type_: str | None, min_val, max_val, kwargs: dict
) -> dict:
    """Return the flags and options of r.out.gdal besides the files and format

    :param datatype: The data type of the map
    :param type_: The data type that was forced, None to choose one
    :param min_val: The minimum of the map, None for a map without a valid cell
    :param max_val: The maximum of the map
    :param kwargs: The options of the caller, without those that are None
    """
    cell = datatype == "CELL" and not type_
    if cell and "nodata" in kwargs:
        # A map without a valid cell has no minimum and maximum.
        gdal_type = _gdal_type_for_cell_map(
            min_val or 0, max_val or 0, float(kwargs["nodata"])
        )
        if gdal_type:
            # r.out.gdal refuses a nodata value its type cannot hold, so the
            # type is chosen to hold it. nodata comes from kwargs, passing it
            # twice is a TypeError.
            return {"flags": "c", "type": gdal_type, **kwargs}
    elif cell:
        # A map without a valid cell has no minimum and maximum; it is
        # exported as the smallest type with the nodata value 1, as a map
        # whose only value is 0 would be.
        if max_val is None:
            min_val = max_val = 0
        nodata = max_val + 1
        if nodata < 256 and min_val >= 0:
            gdal_type = "Byte"
        elif nodata < 65536 and min_val >= 0:
            gdal_type = "UInt16"
        elif min_val >= 0:
            gdal_type = "UInt32"
        else:
            gdal_type = "Int32"
        return {"flags": "c", "nodata": nodata, "type": gdal_type, **kwargs}
    if type_:
        return {"flags": "cf", "type": type_, **kwargs}
    return {"flags": "c", **kwargs}


def _gdal_aaigrid_options(datatype: str, min_val, max_val, kwargs: dict) -> dict:
    """Return the flags and options of r.out.gdal for an Arc/Info ASCII Grid"""
    options = {"flags": "c"}
    if datatype == "CELL" and "nodata" in kwargs:
        # The same reason as for GTiff: a nodata value the default
        # type cannot hold aborts r.out.gdal.
        chosen = _gdal_type_for_cell_map(
            min_val or 0, max_val or 0, float(kwargs["nodata"])
        )
        if chosen:
            options["type"] = chosen
    return {**options, **kwargs}


def _export_raster_maps_as_gdal(
    rows, tar, list_file, fs, format_, type_, **kwargs
) -> None:
    kwargs = {key: value for key, value in kwargs.items() if value is not None}
    for row in rows:
        name = row["name"]
        list_file.write(
            _list_line(
                fs, name, row["start_time"], row["end_time"], row["semantic_label"]
            )
        )

        out_name = name + FORMAT_SUFFIX[format_]
        if format_ == "GTiff":
            options = _gdal_tif_options(
                row["datatype"], type_, row["min"], row["max"], kwargs
            )
        else:
            options = _gdal_aaigrid_options(
                row["datatype"], row["min"], row["max"], kwargs
            )
        try:
            gs.run_command(
                "r.out.gdal", input=name, output=out_name, format=format_, **options
            )
        except CalledModuleError:
            gs.fatal(_("Unable to export raster map <%s>") % name)

        tar.add(out_name)

        # Export the color rules
        out_name = name + ".color"
        try:
            gs.run_command("r.colors.out", map=name, rules=out_name)
        except CalledModuleError:
            gs.fatal(
                _("Unable to export color rules for raster map <%s> r.out.gdal") % name
            )

        tar.add(out_name)


def _export_raster_maps(rows, tar, list_file, fs) -> None:
    for row in rows:
        name = row["name"]
        list_file.write(
            _list_line(
                fs, name, row["start_time"], row["end_time"], row["semantic_label"]
            )
        )
        # Export the raster map with r.pack
        try:
            gs.run_command("r.pack", input=name, flags="c")
        except CalledModuleError:
            gs.fatal(_("Unable to export raster map <%s> with r.pack") % name)

        tar.add(name + ".pack")


def _export_vector_maps_with_ogr(rows, tar, list_file, fs, format_) -> None:
    """Export the vector maps as GML or GPKG files with v.out.ogr"""
    messages = {
        "GML": _("Unable to export vector map <%s> as GML with v.out.ogr"),
        "GPKG": _("Unable to export vector map <%s> as GPKG with v.out.ogr"),
    }
    for row in rows:
        name = row["name"]
        list_file.write(_list_line(fs, name, row["start_time"], row["end_time"]))
        out_name = name + FORMAT_SUFFIX[format_]
        try:
            gs.run_command(
                "v.out.ogr",
                input=name,
                output=out_name,
                layer=row["layer"] or 1,
                format=format_,
            )
        except CalledModuleError:
            gs.fatal(messages[format_] % name)

        tar.add(out_name)
        if format_ == "GML":
            # The schema of the GML file
            tar.add(name + ".xsd")


def _export_vector_maps(rows, tar, list_file, fs) -> None:
    # A vector map with several layers is listed once per layer but packed
    # once. The set is per call: a set of the module would skip the maps of
    # every later export in the same process.
    exported = set()
    for row in rows:
        name = row["name"]
        if name in exported:
            continue

        list_file.write(
            _list_line(
                fs, f"{name}:{row['layer'] or 1}", row["start_time"], row["end_time"]
            )
        )
        # Export the vector map with v.pack
        try:
            gs.run_command("v.pack", input=name, flags="c")
        except CalledModuleError:
            gs.fatal(_("Unable to export vector map <%s> with v.pack") % name)

        tar.add(name + ".pack")

        exported.add(name)


def _export_maps(rows, tar, list_file, fs, kind, format_, datatype, kwargs) -> None:
    """Write the list file and add the files of every map to the archive

    The format selects the module for raster and vector maps; a format a kind
    does not know is exported in the pack format.
    """
    if kind == "strds":
        if format_ in {"GTiff", "AAIGrid"}:
            _export_raster_maps_as_gdal(
                rows, tar, list_file, fs, format_, datatype, **kwargs
            )
        else:
            _export_raster_maps(rows, tar, list_file, fs)
    elif kind == "stvds":
        if format_ in {"GML", "GPKG"}:
            _export_vector_maps_with_ogr(rows, tar, list_file, fs, format_)
        else:
            _export_vector_maps(rows, tar, list_file, fs)


def _extent_of_maps(rows):
    """Return (north, south, east, west, top, bottom) of the rows' maps

    None for no row. A map without an extent in the temporal database is
    left out; None also if no map has one.
    """
    boxes = [
        tuple(row[key] for key in ("north", "south", "east", "west", "top", "bottom"))
        for row in rows
        if row["north"] is not None
    ]
    if not boxes:
        return None
    return (
        max(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        min(box[3] for box in boxes),
        max(box[4] for box in boxes),
        min(box[5] for box in boxes),
    )


def _check_directory(directory) -> None:
    """Stop with a message unless the work directory exists and is writable"""
    if not directory or not Path(directory).exists():
        gs.fatal(_("Directory {} not found").format(directory))
    if not Path(directory).is_dir():
        gs.fatal(_("Directory {} is not a directory").format(directory))
    if not os.access(directory, os.W_OK):
        gs.fatal(_("Directory {} is not writable").format(directory))


def _check_output_directory(output) -> None:
    """Stop with a message unless the archive can be written to its place"""
    parent = Path(output).absolute().parent
    if not parent.is_dir():
        gs.fatal(_("Output directory {} not found").format(parent))
    if not os.access(parent, os.W_OK):
        gs.fatal(_("Output directory {} is not writable").format(parent))


# The sentences of the readme file, by the kind of the dataset
_README_HEADS = {
    "strds": "This space time raster dataset was exported with t.rast.export of GRASS 8",
    "stvds": "This space time vector dataset was exported with t.vect.export of GRASS 8",
}

# The lines of the readme file that name the files of each export format. A
# format that a kind does not list is described as the one with the key None.
_README_FILES = {
    "strds": {
        "GTiff": (
            "       *.tif  -- GeoTIFF raster files",
            "     *.color  -- GRASS raster color rules",
        ),
        "AAIGrid": (
            "       *.asc  -- Arc/Info ASCII Grid raster files",
            "     *.color  -- GRASS raster color rules",
        ),
        "pack": ("      *.pack  -- GRASS raster files packed with r.pack",),
    },
    "stvds": {
        "GML": ("       *.xml  -- Vector GML files",),
        "GPKG": ("      *.gpkg  -- Vector GeoPackage files",),
        None: ("      *.pack  -- GRASS vector files packed with v.pack",),
    },
}


def _map_columns(kind: Kind | None) -> str:
    """Return the columns of the map register that the exporters read

    A raster map is described by its range and data type, which the choice of
    the GDAL type needs, and by its semantic label; a vector map by the layer
    the dataset registered. The extent comes with every kind.
    """
    columns = "name,start_time,end_time"
    if kind is not None:
        if kind.map_kind == "raster":
            columns += ",min,max,datatype,semantic_label"
        elif KINDS[kind.map_kind].has_layer:
            columns += ",layer"
    return columns + ",north,south,east,west,top,bottom"


def _init_text(sp, format_: str, rows) -> str:
    """Return the text of the init file of the archive"""
    string = ""
    # This is optional, if not present strds will be assumed for backward
    # compatibility
    string += "%s=%s\n" % ("stds_type", sp.get_type())
    # This is optional, if not present gtiff will be assumed for
    # backward compatibility
    string += "%s=%s\n" % ("format", format_)
    string += "%s=%s\n" % ("temporal_type", sp.get_temporal_type())
    string += "%s=%s\n" % ("semantic_type", sp.get_semantic_type())
    if sp.is_time_relative():
        string += "%s=%s\n" % ("relative_time_unit", sp.get_relative_time_unit())
    # replace sp.metadata.get_number_of_maps() with len(rows)
    # sp.metadata.get_number_of_maps() doesn't  work with where option
    string += "%s=%s\n" % ("number_of_maps", len(rows))
    # The extent of the selected maps; the dataset's own extent covers
    # maps that where= left out.
    north, south, east, west, top, bottom = (
        _extent_of_maps(rows) or sp.get_spatial_extent_as_tuple()
    )
    string += "%s=%s\n" % ("north", north)
    string += "%s=%s\n" % ("south", south)
    string += "%s=%s\n" % ("east", east)
    string += "%s=%s\n" % ("west", west)
    return string


def _readme_text(sp, kind: str | None, format_: str) -> str:
    """Return the text of the readme file of the archive"""
    lines = []
    if kind in _README_HEADS:
        lines.append(_README_HEADS[kind])
    lines += ["", "Files:"]
    files = _README_FILES.get(kind, {})
    lines += files.get(format_, files.get(None, ()))
    lines += [
        f"{proj_file_name:>13} -- Projection information in PROJ.4 format",
        f"{init_file_name:>13} -- GRASS space time "
        f"{sp.get_new_map_instance(None).get_type()} dataset information",
        f"{list_file_name:>13} -- Time series file, lists all maps by name "
        "with interval",
        "                 time stamps in ISO-Format. Field separator is |",
        f"{metadata_file_name:>13} -- The output of t.info",
        f"{read_file_name:>13} -- This file",
    ]
    return "\n".join(lines) + "\n"


@contextlib.contextmanager
def _scratch_directory(directory: str | Path) -> Iterator[Path]:
    """Work in a new directory inside directory, which is removed again

    Whatever stops the export, the process is back in the directory it was
    in and the new one is gone.
    """
    old_cwd = Path.cwd()
    work = Path(tempfile.mkdtemp(dir=directory)).absolute()
    try:
        os.chdir(work)
        yield work
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(work, ignore_errors=True)


def export_stds(
    input,
    output,
    compression,
    directory,
    where,
    format_="pack",
    type_="strds",
    datatype=None,
    **kwargs,
) -> None:
    """Export space time datasets as tar archive with optional compression

    This method should be used to export space time datasets
    of type raster and vector as tar archive that can be reimported
    with the method import_stds().

    :param input: The name of the space time dataset to export
    :param output: The name of the archive file
    :param compression: The compression of the archive file:

          - "no"  no compression
          - "gzip" GNU zip compression
          - "bzip2" Bzip compression

    :param directory: The working directory used for extraction and packing. It
                      must exist and be writable, as must the directory of
                      output; otherwise the export stops with a message
                      before it makes anything. The directory it makes inside
                      is removed whatever the outcome.
    :param where: The temporal WHERE SQL statement to select a subset
                  of maps from the space time dataset
    :param format\\_: The export format:

          - "GTiff" Geotiff format, only for raster maps
          - "AAIGrid" Arc/Info ASCII Grid format, only for raster maps
          - "pack" The GRASS raster or vector Pack format,
                   this is the default setting
          - "GML" GML file export format, only for vector maps,
                  v.out.ogr export option
          - "GPKG" GPKG file export format, only for vector maps,
                  v.out.ogr export option

    :param type\\_: The space time dataset type

          - "strds" Space time raster dataset
          - "stvds" Space time vector dataset

          A space time 3D raster dataset cannot be exported, GRASS has no
          module to pack a 3D raster map.
    :param datatype: Force the output datatype for r.out.gdal
    """

    # open_old_stds() also takes the name of the map type, "raster" for a space
    # time raster dataset, and an unknown name is refused by it.
    stds_kind = stds_kind_of(type_) if find_kind(type_) else None
    kind = stds_kind.name if stds_kind else None
    if kind == "str3ds":
        get_tgis_message_interface().fatal(
            _(
                "A space time 3D raster dataset cannot be exported, GRASS has no "
                "module to pack a 3D raster map."
            )
        )

    _check_directory(directory)
    _check_output_directory(output)
    # The archive is moved to its place from inside the work directory, where
    # a relative output would mean another place.
    output = Path(output).absolute()

    with _scratch_directory(directory) as work:
        sp = open_old_stds(input, type_)
        try:
            rows = sp.get_registered_maps(
                _map_columns(stds_kind), where, "start_time", None
            )
        except SQLStatementError as error:
            gs.fatal(_("Invalid where condition <{}>: {}").format(where, error))

        flag = {"gzip": "w:gz", "bzip2": "w:bz2"}.get(compression, "w:")
        with tarfile.open(tmp_tar_file_name, flag) as tar:
            fs = "|"
            if not rows:
                gs.warning(
                    _(
                        "The selection contains no map of <{}>; the archive holds no map."
                    ).format(input)
                )
            with open(list_file_name, "w") as list_file:
                if rows:
                    _export_maps(
                        rows, tar, list_file, fs, kind, format_, datatype, kwargs
                    )

            # Write projection and metadata
            Path(proj_file_name).write_text(
                gs.read_command("g.proj", flags="p", format="proj4")
            )
            Path(init_file_name).write_text(_init_text(sp, format_, rows))
            Path(metadata_file_name).write_text(
                gs.read_command("t.info", type=sp.get_type(), input=sp.get_id())
            )
            Path(read_file_name).write_text(_readme_text(sp, kind, format_))

            # Append the file list
            tar.add(list_file_name)
            tar.add(proj_file_name)
            tar.add(init_file_name)
            tar.add(read_file_name)
            tar.add(metadata_file_name)

        # Move the archive to its destination
        shutil.move(work / tmp_tar_file_name, output)
