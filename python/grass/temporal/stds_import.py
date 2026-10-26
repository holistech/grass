"""Space time dataset import functions.

Usage:

.. code-block:: python

    import grass.temporal as tgis

    input = "/tmp/temp_1950_2012.tar.gz"
    output = "temp_1950_2012"
    directory = "/tmp"
    title = "My new dataset"
    descr = "My new shiny dataset"
    location = None
    link = True
    exp = True
    overr = False
    create = False
    tgis.import_stds(
        input,
        output,
        directory,
        title,
        descr,
        location,
        link,
        exp,
        overr,
        create,
        "strds",
    )


SPDX-FileCopyrightText: 2012-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import contextlib
import math
import os
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Self

import grass.script as gs
from grass.exceptions import CalledModuleError

from .state import get_current_mapset, get_tgis_message_interface, init
from .factory import dataset_factory
from .register import register_maps_in_space_time_dataset

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .abstract_space_time_dataset import AbstractSpaceTimeDataset

proj_file_name = Path("proj.txt")
init_file_name = Path("init.txt")
list_file_name = Path("list.txt")

# The suffix of the file that an archive holds for each map, by export format
_FORMAT_SUFFIX = {
    "GTiff": ".tif",
    "AAIGrid": ".asc",
    "GML": ".xml",
    "GPKG": ".gpkg",
    "pack": ".pack",
}

############################################################################


def _refuse_existing_maps(
    maplist: list[dict[str, str]], element: Literal["cell", "vector"], mapset: str
) -> None:
    """Stop before the first import if a map of the archive exists already

    The import writes the maps one by one, so a clash found at the Nth map
    would leave the N-1 maps before it behind. Without the overwrite flag every
    name is checked first. The layer of a vector map is not part of its name.
    """
    if gs.overwrite():
        return
    for row in maplist:
        name = row["name"].split(":")[0]
        if gs.find_file(name=name, element=element, mapset=mapset)["name"]:
            gs.fatal(_("<%s> exists. To overwrite, use the --overwrite flag") % name)


def _import_raster_maps_from_gdal(
    maplist: list[dict[str, str]],
    *,
    overr: bool,
    exp: bool,
    location: str | None,
    link: bool,
    format_: Literal["GTiff", "AAIGrid"],
    set_current_region: bool = False,
    memory: int = 300,
) -> None:
    # An Arc/Info ASCII Grid file carries no projection, which r.in.gdal
    # accepts only with the override flag.
    impflags = "o" if overr or format_ == "AAIGrid" else ""
    if exp or location:
        impflags += "e"
    for row in maplist:
        name = row["name"]
        filename = row["filename"] + _FORMAT_SUFFIX[format_]

        try:
            if link:
                gs.run_command(
                    "r.external",
                    input=filename,
                    output=name,
                    flags=impflags,
                    overwrite=gs.overwrite(),
                )
            else:
                gs.run_command(
                    "r.in.gdal",
                    input=filename,
                    output=name,
                    memory=memory,
                    flags=impflags,
                    overwrite=gs.overwrite(),
                )

        except CalledModuleError:
            gs.fatal(
                _("Unable to import/link raster map <%s> from file %s.")
                % (name, filename)
            )

        _set_color_rules(name, row["filename"] + ".color")

    # Set the computational region from the last map imported
    if set_current_region is True:
        gs.run_command("g.region", raster=name)


def _set_color_rules(name: str, filename: str) -> None:
    """Set the color rules of a raster map from the file, if the archive has one"""
    if not Path(filename).is_file():
        return
    try:
        gs.run_command("r.colors", map=name, rules=filename, overwrite=gs.overwrite())
    except CalledModuleError:
        gs.fatal(_("Unable to set the color rules for raster map <%s>.") % name)


############################################################################


def _import_raster_maps(
    maplist: list[dict[str, str]],
    *,
    set_current_region: bool = False,
) -> None:
    # We need to disable the projection check because of its
    # simple implementation
    impflags = "o"
    for row in maplist:
        name = row["name"]
        filename = row["filename"] + _FORMAT_SUFFIX["pack"]
        try:
            gs.run_command(
                "r.unpack",
                input=filename,
                output=name,
                flags=impflags,
                overwrite=gs.overwrite(),
                verbose=True,
            )

        except CalledModuleError:
            gs.fatal(
                _("Unable to unpack raster map <%s> from file %s.") % (name, filename)
            )

    # Set the computational region from the last map imported
    if set_current_region is True:
        gs.run_command("g.region", raster=name)


############################################################################


def _import_vector_maps_from_ogr(
    maplist: list[dict[str, str]],
    *,
    overr: bool,
    exp: bool,
    location: str | None,
    link: bool,
    format_: Literal["GML", "GPKG"],
) -> None:
    impflags = ""
    if overr:
        impflags += "o"
    if not link and (exp or location):
        impflags += "e"
    for row in maplist:
        name = row["name"]
        filename = row["filename"] + _FORMAT_SUFFIX[format_]

        try:
            if link:
                gs.run_command(
                    "v.external",
                    input=filename,
                    output=name,
                    flags=impflags or None,
                    overwrite=gs.overwrite(),
                )
            else:
                gs.run_command(
                    "v.in.ogr",
                    input=filename,
                    output=name,
                    flags=impflags or None,
                    overwrite=gs.overwrite(),
                )

        except CalledModuleError:
            gs.fatal(
                _("Unable to import vector map <%s> from file %s.") % (name, filename)
            )


############################################################################


def _import_vector_maps(maplist: list[dict[str, str]], *, extend: bool = False) -> None:
    # We need to disable the projection check because of its
    # simple implementation
    impflags = "o"
    unpacked = []
    for row in maplist:
        # Separate the name from the layer
        name = row["name"].split(":")[0]
        # A vector map with several layers is listed once per layer but
        # unpacked once. The set is per call: a set of the module would skip
        # the maps of every later import in the same process.
        if name in unpacked:
            continue
        filename = row["filename"] + _FORMAT_SUFFIX["pack"]
        try:
            gs.run_command(
                "v.unpack",
                input=filename,
                output=name,
                flags=impflags,
                overwrite=gs.overwrite(),
                verbose=True,
            )

        except CalledModuleError:
            gs.fatal(
                _("Unable to unpack vector map <%s> from file %s.") % (name, filename)
            )

        unpacked.append(name)

    # v.unpack has no flag to extend the region, unlike v.in.ogr with -e
    if extend and unpacked:
        _extend_region_to_vector_maps(unpacked)


def _extend_region_to_vector_maps(names: list[str]) -> None:
    """Grow the region to cover the vector maps, as v.in.ogr -e does

    In the PERMANENT mapset the default region of the project is the base and
    is saved again; elsewhere the current region is the base. The new bounds
    are aligned to the resolution from the north and west edges.
    """
    in_permanent = get_current_mapset() == "PERMANENT"
    if in_permanent:
        gs.run_command("g.region", flags="d")
    region = gs.region()
    north, south = region["n"], region["s"]
    east, west = region["e"], region["w"]
    for name in names:
        info = gs.parse_command("v.info", map=name, flags="g")
        north = max(north, float(info["north"]))
        south = min(south, float(info["south"]))
        east = max(east, float(info["east"]))
        west = min(west, float(info["west"]))
    rows = math.ceil((north - south) / region["nsres"])
    cols = math.ceil((east - west) / region["ewres"])
    gs.run_command(
        "g.region",
        n=north,
        s=north - rows * region["nsres"],
        e=west + cols * region["ewres"],
        w=west,
        rows=rows,
        cols=cols,
        flags="s" if in_permanent else None,
    )


############################################################################


def _check_archive(
    input: str | Path, create: bool, directory: str | Path | None
) -> tuple[Path, str | Path | None]:
    """Stop with a message unless the archive and the extraction directory exist

    Return the path of the archive and the extraction directory, which is a
    temporary directory of the session if none was given. Creating a project
    only needs the archive, so its directory is not checked or defaulted.
    """
    input_path = Path(input)
    if not input_path.exists():
        gs.fatal(_("Space time raster dataset archive <%s> not found") % str(input))
    if not tarfile.is_tarfile(input_path):
        gs.fatal(_("File <%s> is not a tar archive") % str(input))
    if not create:
        directory = directory or gs.tempdir()
        if not Path(directory).exists():
            gs.fatal(_("Extraction directory <%s> not found") % directory)
    return input_path, directory


def _extract_archive(input_path: Path, directory: str | Path | None) -> None:
    """Check that the archive holds the files of an export and extract it"""
    try:
        with tarfile.open(name=input_path, mode="r") as tar:
            # Check for important files
            msgr = get_tgis_message_interface()
            msgr.message(
                _(
                    "Checking validity of input file (size: %0.1f MB). Make take a while..."
                )
                % (input_path.stat().st_size / (1024 * 1024.0)),
            )
            # Make sure that the basenames of the files are used for comparison
            member_basenames = [Path(name).name for name in tar.getnames()]

            if str(init_file_name) not in member_basenames:
                gs.fatal(_("Unable to find init file <%s>") % init_file_name)
            if str(list_file_name) not in member_basenames:
                gs.fatal(_("Unable to find list file <%s>") % list_file_name)
            if str(proj_file_name) not in member_basenames:
                gs.fatal(_("Unable to find projection file <%s>") % proj_file_name)

            msgr.message(_("Extracting data..."))
            # The 'data' extraction filter was added in Python 3.12 and backported to
            # 3.11.4 (PEP 706). Refuse to extract without it rather than
            # extracting unsafely.
            if not hasattr(tarfile, "data_filter"):
                gs.fatal(
                    _("Extracting may be unsafe; upgrade Python to 3.11.4 or newer")
                )
            tar.extractall(path=directory, filter="data")
    except tarfile.TarError as error:
        gs.fatal(_("Unable to read the archive <%s>: %s") % (input_path, error))


@contextlib.contextmanager
def _working_directory(directory: str | Path) -> Iterator[None]:
    """Work in directory and go back to where the caller was, however it ends

    The change is of the whole process, so a caller that is left in the
    extraction directory by a refused import would read and write relative
    paths there.
    """
    old_cwd = Path.cwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(old_cwd)


class _ProjectSession:
    """The session of the caller, which can be switched to a new project

    Used as a context manager: on exit, whatever way out it is, a switched
    session is switched back, the temporal framework is initialized for the
    session of the caller again and the temporary session file is removed.
    Nothing is restored if switch_to() did not get as far as the session
    file.
    """

    def __init__(self) -> None:
        self._old_gisrc = os.environ.get("GISRC")
        self._target_gisrc: str | None = None

    def __enter__(self) -> Self:
        return self

    def switch_to(self, dbase: str, location: str) -> None:
        """Make the PERMANENT mapset of the project the session of the process

        :param dbase: The GRASS database of the project
        :param location: The name of the project, which must exist
        """
        try:
            self._target_gisrc, _target_env = gs.create_environment(
                dbase, location, "PERMANENT"
            )
            os.environ["GISRC"] = self._target_gisrc
        except OSError as e:
            gs.fatal(
                _("Unable to create environment for location %s. Reason: %s")
                % (location, e)
            )
        # create default database connection
        try:
            gs.run_command("t.connect", flags="d")
        except CalledModuleError:
            gs.fatal(
                _("Unable to create default temporal database in new location %s")
                % location
            )

    def __exit__(self, *exc_info: object) -> None:
        if not self._target_gisrc:
            return
        # Restore the original session
        if self._old_gisrc is not None:
            os.environ["GISRC"] = self._old_gisrc
        else:
            os.environ.pop("GISRC", None)

        init()

        # Delete the temporary session file
        gs.try_remove(self._target_gisrc)


def _check_projection(overr: bool) -> None:
    """Stop unless the projection of the archive is that of the current project

    With overr only a warning is given. Both sides are written as PROJ.4
    strings, one key per line, so that the files can be compared as key-value
    text. Reads proj.txt of the working directory.
    """
    temp_name = gs.tempfile()
    proj_name = proj_file_name.absolute()

    # We need to convert projection strings generated
    # from other programs than g.proj into
    # new line format so that the grass file comparison function
    # can be used to compare the projections
    proj_content = proj_name.read_text(encoding="utf-8")
    proj_content = proj_content.replace(" +", "\n+")
    proj_content = proj_content.replace("\t+", "\n+")

    proj_name_tmp = f"{temp_name}_in_projection"
    Path(proj_name_tmp).write_text(proj_content)

    with Path(temp_name).open("w") as temp_file:
        p = gs.start_command("g.proj", flags="p", format="proj4", stdout=temp_file)
        p.communicate()

    if not gs.compare_key_value_text_files(temp_name, proj_name_tmp, sep="="):
        if overr:
            gs.warning(_("Projection information does not match. Proceeding..."))
        else:
            diff = "".join(gs.diff_files(temp_name, proj_name))
            gs.warning(
                _(
                    "Difference between PROJ_INFO file of "
                    "imported map and of current location:"
                    "\n{diff}"
                ).format(diff=diff)
            )
            gs.fatal(_("Projection information does not match. Aborting."))


def _create_project(dbase: str, location: str, overr: bool) -> bool:
    """Create the project from the projection file of the archive

    Return the override flag the imports of the new project need: set for an
    unprojected archive, otherwise the value that was passed.
    """
    try:
        proj4_string = proj_file_name.read_text(encoding="utf-8").strip()
        # g.proj prints this text for an unprojected project, which is not
        # a PROJ string; a project without a CRS is the XY project.
        if proj4_string.startswith("XY location"):
            gs.create_location(dbase=dbase, location=location)
            # The GeoTIFFs of an unprojected project carry no CRS, which
            # r.in.gdal accepts only with the override flag.
            return True
        gs.create_location(dbase=dbase, location=location, proj4=proj4_string)
    except Exception as e:
        gs.fatal(
            _("Unable to create location %(l)s. Reason: %(e)s")
            % {"l": location, "e": str(e)}
        )
    return overr


def _read_map_list(base: str | None, mapset: str) -> tuple[list[dict[str, str]], int]:
    """Read list.txt of the working directory

    Return one dictionary per map and the number of lines of the file, blank
    ones included. The "filename" of a map is the base name of its files,
    which the format adds a suffix to; with base the maps are renamed to the
    base and a numerical suffix.
    """
    fs = "|"
    maplist = []
    semantic_label_column = 4
    with list_file_name.open("r") as list_file:
        lines = list_file.readlines()
    # the number of lines is needed to correctly form the suffix
    max_count = len(lines)

    for line_count, line in enumerate(lines, 1):
        map_line = line.rstrip()
        if not map_line:
            continue

        line_list = map_line.split(fs)

        # The filename is actually the base name of the map
        # that must be extended by the file suffix
        filename, _separator, layer = line_list[0].strip().partition(":")
        mapname = (
            f"{base}_{gs.get_num_suffix(line_count, max_count)}" if base else filename
        )

        maplist.append(
            {
                "filename": filename,
                "layer": layer,
                "name": mapname,
                "id": f"{mapname}@{mapset}",
                "start": line_list[1].strip(),
                "end": line_list[2].strip(),
                "semantic_label": line_list[3].strip()
                if len(line_list) == semantic_label_column
                else "",
            }
        )
    return maplist, max_count


def _read_init_file() -> dict[str, str]:
    """Read init.txt of the working directory as a dictionary"""
    fs = "="
    init_data = {}
    with init_file_name.open("r") as init_file:
        for line in init_file:
            init_line = line.rstrip()
            if not init_line:
                continue

            kv = init_line.split(fs)
            init_data[kv[0]] = kv[1].strip()
    return init_data


def _check_init(
    init_data: dict[str, str], map_count: int, stds_type: str
) -> tuple[str, str]:
    """Stop with a message unless the init file describes an importable dataset

    :param init_data: The content of the init file
    :param map_count: The number of lines of the list file
    :param stds_type: The type that the caller wants to import
    :return: The type and the format of the archive
    """
    if (
        "temporal_type" not in init_data
        or "semantic_type" not in init_data
        or "number_of_maps" not in init_data
    ):
        gs.fatal(
            _("Key words %(t)s, %(s)s or %(n)s not found in init file.")
            % {
                "t": "temporal_type",
                "s": "semantic_type",
                "n": "number_of_maps",
            }
        )

    if map_count != int(init_data["number_of_maps"]):
        gs.fatal(_("Number of maps mismatch in init and list file."))
    # Checked here and not where the dataset is made, after the maps
    # are imported: a refusal then leaves no imported map behind.
    if (
        init_data["temporal_type"] == "relative"
        and "relative_time_unit" not in init_data
    ):
        gs.fatal(_("Key word %s not found in init file.") % ("relative_time_unit"))

    # Both keys are optional for archives of older versions, which held
    # GeoTIFF files of raster maps only.
    type_ = init_data.get("stds_type", "strds")
    format_ = init_data.get("format", "GTiff")

    if stds_type != type_:
        gs.fatal(_("The archive file is of wrong space time dataset type"))
    return type_, format_


def _check_files(maplist: list[dict[str, str]], format_: str) -> None:
    """Stop with a message unless the archive holds the file of every map"""
    suffix = _FORMAT_SUFFIX.get(format_)
    if suffix is None:
        gs.fatal(_("Unsupported input format"))
    messages = {
        "GTiff": _("Unable to find GeoTIFF raster file <%s> in archive."),
        "AAIGrid": _("Unable to find AAIGrid raster file <%s> in archive."),
        "GML": _("Unable to find GML vector file <%s> in archive."),
        "GPKG": _("Unable to find GPKG vector file <%s> in archive."),
        "pack": _("Unable to find GRASS package file <%s> in archive."),
    }
    for row in maplist:
        # Appended and not set as the suffix: with_suffix() would take ".a" of
        # the raster map "dot.a" for a suffix and look for "dot.tif".
        filename = Path(row["filename"] + suffix)
        if not filename.exists():
            gs.fatal(messages[format_] % filename)


def _write_new_list(
    maplist: list[dict[str, str]], format_: str, list_file: Path
) -> None:
    """Write the list file for the registration of the maps

    A pack archive holds the whole vector map with all its layers, so the
    layer that the exported dataset registered stays part of the map name;
    the GML and GPKG files hold the single layer as layer 1.
    """
    fs = "|"
    with list_file.open("w") as new_list_file:
        for row in maplist:
            layer = f":{row['layer']}" if row["layer"] and format_ == "pack" else ""
            new_list_file.write(
                f"{row['name']}{layer}{fs}{row['start']}{fs}{row['end']}"
                f"{fs}{row['semantic_label']}\n",
            )


def _import_maps(
    maplist: list[dict[str, str]],
    type_: str,
    format_: str,
    *,
    mapset: str,
    overr: bool,
    exp: bool,
    location: str | None,
    link: bool,
    set_current_region: bool,
    memory: int,
) -> None:
    """Import the maps of the archive with the module of the format"""
    _refuse_existing_maps(maplist, "cell" if type_ == "strds" else "vector", mapset)
    if type_ == "strds":
        if format_ in {"GTiff", "AAIGrid"}:
            _import_raster_maps_from_gdal(
                maplist,
                overr=overr,
                exp=exp,
                location=location,
                link=link,
                format_=format_,
                set_current_region=set_current_region,
                memory=memory,
            )
        if format_ == "pack":
            _import_raster_maps(maplist, set_current_region=set_current_region)
    elif type_ == "stvds":
        if format_ in {"GML", "GPKG"}:
            _import_vector_maps_from_ogr(
                maplist,
                overr=overr,
                exp=exp,
                location=location,
                link=link,
                format_=format_,
            )
        if format_ == "pack":
            _import_vector_maps(maplist, extend=bool(exp or location))


def _make_stds(
    sp: AbstractSpaceTimeDataset,
    ident: str,
    init_data: dict[str, str],
    title: str | None,
    descr: str | None,
) -> tuple[AbstractSpaceTimeDataset, str | None]:
    """Insert the space time dataset, replacing one that exists with overwrite

    Return the dataset and the unit of its relative time, None for absolute
    time.
    """
    if sp.is_in_db() and gs.overwrite() is True:
        gs.info(
            _("Overwriting space time %(sp)s dataset <%(id)s> and unregister all maps.")
            % {
                "sp": sp.get_new_map_instance(None).get_type(),
                "id": sp.get_id(),
            }
        )
        sp.delete()
        sp = sp.get_new_instance(ident)

    temporal_type = init_data["temporal_type"]
    semantic_type = init_data["semantic_type"]
    relative_time_unit = None
    if temporal_type == "relative":
        relative_time_unit = init_data["relative_time_unit"]
        sp.set_relative_time_unit(relative_time_unit)

    gs.verbose(
        _("Create space time %s dataset.") % sp.get_new_map_instance(None).get_type()
    )

    sp.set_initial_values(
        temporal_type=temporal_type,
        semantic_type=semantic_type,
        title=title,
        description=descr,
    )
    sp.insert()
    return sp, relative_time_unit


def import_stds(
    input: str | Path,
    output: str,
    directory: str | Path | None = None,
    title: str | None = None,
    descr: str | None = None,
    location: str | None = None,
    link: bool = False,
    exp: bool = False,
    overr: bool = False,
    create: bool = False,
    stds_type: str = "strds",
    base: str | None = None,
    set_current_region: bool = False,
    memory: int = 300,
) -> None:
    """Import space time datasets of type raster and vector.

    The process is left in the working directory and the session it was in,
    also when the import is refused.

    :param input: Name of the input archive file
    :param output: The name of the output space time dataset
    :param directory: The extraction directory
    :param title: The title of the new created space time dataset
    :param descr: The description of the new created space time dataset
    :param location: The name of the location that should be created,
                    maps are imported into this location
    :param link: Switch to link raster maps instead importing them
    :param exp: Extend location extents based on new dataset
    :param overr: Override projection (use location's projection)
    :param create: Create the location specified by the "location"
                  parameter and exit.
                  Do not import the space time datasets.
    :param stds_type: The type of the space time dataset that should be imported
    :param base: The base name of the new imported maps, it will be
                 extended using a numerical index.
    :param memory: Cache size for raster rows, used in r.in.gdal
    """
    # The checks of the archive come first and use the plain gs.fatal(), which
    # ends a tool with a message. After the extraction every gs.fatal() raises
    # ScriptError, which the tools report as a message; the finally at the end
    # restores the raise-on-error state of the caller on every way out.
    input_path, directory = _check_archive(input, create, directory)

    if stds_type == "stvds" and not overr:
        gs.warning(
            _(
                "Re-projection on import is currently not supported for "
                "space time vector datasets. Ignoring projection information."
            ),
        )
        overr = True

    _extract_archive(input_path, directory)

    old_state = gs.get_raise_on_error()
    gs.set_raise_on_error(True)
    try:
        # The managers exit in reverse order: the working directory is
        # restored first, and the temporal framework of the caller is
        # initialized again from the directory the caller was in.
        with _ProjectSession() as session, _working_directory(directory):
            if location:
                # Create a new location based on the projection information
                # and switch into it
                dbase = gs.gisenv()["GISDBASE"]
                overr = _create_project(dbase, location, overr)
                # Just create a new location and return
                if create:
                    return
                session.switch_to(dbase, location)
            else:
                _check_projection(overr)

            # Make sure the temporal database exists
            init()

            mapset = get_current_mapset()
            maplist, map_count = _read_map_list(base, mapset)
            init_data = _read_init_file()
            type_, format_ = _check_init(init_data, map_count, stds_type)
            _check_files(maplist, format_)

            # We use a new list file name for map registration
            new_list_file_name = list_file_name.with_name(f"{list_file_name.stem}_new")
            _write_new_list(maplist, format_, new_list_file_name)

            # Check the space time dataset
            ident = f"{output}@{mapset}"
            sp = dataset_factory(type_, ident)
            if sp.is_in_db() and gs.overwrite() is False:
                gs.fatal(
                    _(
                        "Space time %(t)s dataset <%(sp)s> is already in"
                        " the database. Use the overwrite flag."
                    )
                    % {"t": type_, "sp": sp.get_id()}
                )

            _import_maps(
                maplist,
                type_,
                format_,
                mapset=mapset,
                overr=overr,
                exp=exp,
                location=location,
                link=link,
                set_current_region=set_current_region,
                memory=memory,
            )
            sp, relative_time_unit = _make_stds(sp, ident, init_data, title, descr)

            # register the maps
            register_maps_in_space_time_dataset(
                type=sp.get_new_map_instance(None).get_type(),
                name=output,
                file=new_list_file_name,
                start="file",
                end="file",
                unit=relative_time_unit,
                fs="|",
                update_cmd_list=False,
            )
    finally:
        gs.set_raise_on_error(old_state)
