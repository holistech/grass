"""Extract functions for space time raster, 3d raster and vector datasets.

SPDX-FileCopyrightText: 2012-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import re
import sys

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.script.utils import _get_multiprocessing_context

from .abstract_map_dataset import AbstractMapDataset
from .batches import run_in_batches, run_mapcalc
from .db import SQLDatabaseInterfaceConnection, SQLStatementError, connection
from .state import get_current_mapset, get_tgis_db_version, get_tgis_message_interface
from .datetime_math import map_name_suffix
from .open_stds import check_new_stds, open_new_stds, open_old_stds


def compile_new_map_name(
    sp,
    base: str,
    count: int,
    map_id: str,
    semantic_label: str | None,
    time_suffix: str,
    dbif: SQLDatabaseInterfaceConnection,
) -> str:
    """Compile new map name with suffix and semantic label.

    :param sp: An open SpaceTimeDataSet (STDS)
    :param count: Running number of the map to be used as numeric suffix (if not time suffix)
    :param map_id: Map ID to compile new map name for
    :param time_suffix: Type of suffix to use: gran, time, num or num%NN
    :param dbif: initialized TGIS database interface
    :raises ValueError: for another time_suffix
    """
    if semantic_label:
        base = f"{base}_{semantic_label}"
    # The temporal type of a new map instance is absolute until select()
    # reads the real one (checked 23.10.2026 with is_time_absolute() of a new
    # RasterDataset), so a relative dataset would get time suffixes.
    old_map = sp.get_new_map_instance(map_id)
    old_map.select(dbif)
    suffix = map_name_suffix(old_map, time_suffix, sp.get_granularity(), count)
    return f"{base}_{suffix}"


def number_clashing_names(names: list[str]) -> list[str]:
    """Give every repeated name after its first use the number _2, _3, ...

    Two different maps at one time get the same name from the time suffix.
    The first map in the given order keeps its name, so a name that works
    without numbering stays as it is. A number that another name of the list
    already has is skipped, so the result has no repeated name. Names of maps
    that exist outside this run are not considered; the caller refuses those
    as it does for any other name.
    """
    taken = set(names)
    seen = set()
    result = []
    for name in names:
        if name in seen:
            number = 2
            while f"{name}_{number}" in taken:
                number += 1
            name = f"{name}_{number}"
            taken.add(name)
        seen.add(name)
        result.append(name)
    return result


def replace_stds_names(expression: str, simple_name: str, full_name: str) -> str:
    """Safely replace simple with full STDS names.

     When users provide inconsistent input for STDS in the expression
     (with and without mapset componenet) or if the STDS name is part
     of the name of other raster maps in the expression, the final
     mapcalc expression may become invalid when the STDS name later is
     replaced with the name of the individual maps in the time series.
     The replacement with the fully qualified STDS names avoids that
     confusion.

    :param expression: The mapcalc expression to replace names in
    :param simple_name: STDS name *without* mapset component
    :param full_name: STDS name *with* mapset component
    """
    separators = r""" ,-+*/^:&|"'`()<>#^"""
    name_matches = re.finditer(simple_name, expression)
    new_expression = ""
    old_idx = 0
    for match in name_matches:
        # Fill-in expression component between matches
        new_expression += expression[old_idx : match.start()]
        # Only replace STDS name if pre- and succeeded by a separator
        # Match is either at the start or preceeeded by a separator
        if match.start() == 0 or expression[match.start() - 1] in separators:
            # Match is either at the end or succeeded by a separator
            if (
                match.end() + 1 > len(expression)
                or expression[match.end()] in separators
            ):
                new_expression += full_name
            else:
                new_expression += simple_name
        else:
            new_expression += simple_name
        old_idx = match.end()
    new_expression += expression[old_idx:]
    return new_expression


def extract_dataset(
    input: str,
    output: str,
    type: str,
    where: str,
    expression: str,
    base: str,
    time_suffix: str,
    nprocs: int = 1,
    register_null: bool = False,
    layer: int = 1,
    vtype: str = "point,line,boundary,centroid,area,face",
) -> None:
    """Extract a subset of a space time raster, raster3d or vector dataset.

    A mapcalc expression can be provided to process the temporal extracted
    maps.
    Mapcalc expressions are supported for raster and raster3d maps.

    :param input: The name of the input space time raster/raster3d dataset
    :param output: The name of the extracted new space time raster/raster3d
                  dataset
    :param type: The type of the dataset: "raster", "raster3d" or vector
    :param where: The temporal SQL WHERE statement for subset extraction
    :param expression: The r(3).mapcalc expression or the v.extract where
                      statement
    :param base: The base name of the new created maps in case a mapclac
                expression is provided
    :param time_suffix: string to choose which suffix to use: gran, time, num%*
                       (where * are digits)
    :param nprocs: The number of parallel processes to be used for mapcalc
                  processing
    :param register_null: Set this number True to register empty maps
                         (only raster and raster3d maps)
    :param layer: The vector layer number to be used when no timestamped
           layer is present, default is 1
    :param vtype: The feature type to be extracted for vector maps, default
           is point,line,boundary,centroid,area and face
    """
    # Check the parameters
    msgr = get_tgis_message_interface()

    if expression and not base:
        msgr.fatal(_("You need to specify the base name of new created maps"))

    with connection() as dbif:
        mapset = get_current_mapset()

        tgis_version = get_tgis_db_version()

        sp = open_old_stds(input, type, dbif)
        has_semantic_labels = bool(
            tgis_version > 2 and type == "raster" and sp.metadata.semantic_labels,
        )

        # Check the new stds
        new_sp = check_new_stds(output, type, dbif, gs.overwrite())
        rows = _registered_rows(sp, type, where, has_semantic_labels, dbif, msgr)

        new_maps = {}
        if not rows:
            gs.warning(
                _(
                    "Nothing found in the database for space time dataset <{name}> "
                    "(type: {element_type}): {detail}",
                ).format(
                    name=input,
                    element_type=type,
                    detail=(
                        _(
                            "Dataset is empty or where clause is too constrained or "
                            "incorrect",
                        )
                        if where
                        else _("Dataset is empty")
                    ),
                ),
            )
            return

        num_rows = len(rows)

        msgr.percent(0, num_rows, 1)

        # Run the mapcalc expression
        if expression:
            new_maps = _compute_new_maps(
                sp,
                rows,
                type,
                expression,
                base,
                time_suffix,
                nprocs,
                layer,
                vtype,
                has_semantic_labels,
                dbif,
                mapset,
            )

        msgr.percent(0, num_rows, 1)

        _temporal_type, semantic_type, title, description = sp.get_initial_values()
        new_sp = open_new_stds(
            output,
            type,
            sp.get_temporal_type(),
            title,
            description,
            semantic_type,
            dbif,
            gs.overwrite(),
        )

        empty_maps = _register_maps(
            sp,
            new_sp,
            rows,
            new_maps,
            type,
            expression,
            register_null,
            has_semantic_labels,
            dbif,
        )

        # Update the spatio-temporal extent and the metadata table entries
        new_sp.update_from_registered_maps(dbif)

        msgr.percent(num_rows, num_rows, 1)

        # Remove empty maps
        if len(empty_maps) > 0:
            gs.run_command(
                "g.remove",
                flags="f",
                type=type.replace("_", ""),
                name=",".join(
                    [
                        empty_map.get_name()
                        for empty_map in empty_maps
                        if empty_map.get_name()
                    ]
                ),
                superquiet=True,
            )


###############################################################################
# Helper functions


def _registered_rows(sp, type, where, has_semantic_labels, dbif, msgr):
    """Return the registered maps of the dataset that the condition selects"""
    try:
        if type == "vector":
            return sp.get_registered_maps(
                "id,name,mapset,layer", where, "start_time,id", dbif
            )
        return sp.get_registered_maps(
            f"id{',semantic_label' if has_semantic_labels else ''}",
            where,
            "start_time,id",
            dbif,
        )
    except SQLStatementError as error:
        msgr.fatal(_("Invalid where condition <{}>: {}").format(where, error))
        return None


def _map_id(map_name, row, type, mapset):
    """Return the identifier of an extracted map: vector maps have a layer"""
    if type != "vector":
        return AbstractMapDataset.build_id(map_name, mapset)
    return AbstractMapDataset.build_id(map_name, mapset, row["layer"])


def _new_map_names(sp, rows, type, base, time_suffix, layer, has_semantic_labels, dbif):
    """Name every new map after the time suffix and number the clashing names"""
    new_names = []
    for count, row in enumerate(rows, 1):
        map_name = compile_new_map_name(
            sp,
            base,
            count,
            row["id"],
            row["semantic_label"] if has_semantic_labels else None,
            time_suffix,
            dbif,
        )
        new_names.append(map_name)
    if type == "vector":
        # Two layers of one vector map registered for the same time get
        # the same name from the time suffixes, and v.extract refuses to
        # replace the first of them. The layer tells them apart. Maps
        # that share the name and the layer are two different maps of one
        # time; the layer cannot tell those apart, they are numbered below.
        layers_of = {}
        for name, row in zip(new_names, rows, strict=True):
            layers_of.setdefault(name, set()).add(row["layer"] or layer)
        new_names = [
            f"{name}_{row['layer'] or layer}" if len(layers_of[name]) > 1 else name
            for name, row in zip(new_names, rows, strict=True)
        ]
    return number_clashing_names(new_names)


def _compute_new_maps(
    sp,
    rows,
    type,
    expression,
    base,
    time_suffix,
    nprocs,
    layer,
    vtype,
    has_semantic_labels,
    dbif,
    mapset,
):
    """Compute a new map from each registered map and return them by old id

    Stops, with nothing computed, if a new map is already in the temporal
    database and the run does not overwrite. If a process fails, the maps that
    this run made are removed.
    """
    msgr = get_tgis_message_interface()
    num_rows = len(rows)
    new_maps = {}
    ctx = _get_multiprocessing_context()

    # Make sure STRDS is in the expression referenced with fully qualified name
    expression = replace_stds_names(
        expression,
        sp.base.get_name(),
        sp.base.get_map_id(),
    )

    # Name every new map and refuse a known one before the first process
    # starts: nothing is computed and no dataset is made for a refused run.
    new_names = _new_map_names(
        sp, rows, type, base, time_suffix, layer, has_semantic_labels, dbif
    )
    for row, map_name in zip(rows, new_names, strict=True):
        map_id = _map_id(map_name, row, type, mapset)
        if not gs.overwrite() and sp.get_new_map_instance(map_id).is_in_db(dbif):
            msgr.fatal(
                _(
                    "Map <%s> is already in temporal database"
                    ", use overwrite flag to overwrite"
                )
                % map_id
            )

    # The maps that this run has made, to remove them if it fails
    created = []
    # The jobs are prepared and run in groups of nprocs, so the state of
    # the temporal database when a group fails is that of a loop that
    # starts a process per map and joins every nprocs-th.
    group = nprocs if nprocs >= 1 else num_rows

    for first in range(0, num_rows, group):
        jobs = []
        job_names = []
        for count, row in enumerate(rows[first : first + group], first + 1):
            if count % 10 == 0:
                msgr.percent(count, num_rows, 1)

            map_name = new_names[count - 1]
            map_id = _map_id(map_name, row, type, mapset)

            # We need to modify the r(3).mapcalc expression
            if type != "vector":
                expr = expression
                expr = expr.replace(sp.base.get_map_id(), row["id"])
                expr = f"{map_name} = {expr}"

            new_map = sp.get_new_map_instance(map_id)

            # Remove the existing temporal database entry; without
            # overwrite the check above has stopped the run
            if new_map.is_in_db(dbif):
                new_map.delete(dbif)
                new_map = sp.get_new_map_instance(map_id)

            if type == "raster":
                msgr.verbose(_('Applying r.mapcalc expression: "%s"') % expr)
                jobs.append((run_mapcalc, ("r.mapcalc", expr)))
            elif type == "raster3d":
                msgr.verbose(_('Applying r3.mapcalc expression: "%s"') % expr)
                jobs.append((run_mapcalc, ("r3.mapcalc", expr)))
            elif type == "vector":
                msgr.verbose(_('Applying v.extract where statement: "%s"') % expression)
                jobs.append(
                    (
                        run_vector_extraction,
                        (
                            row["name"] + "@" + row["mapset"],
                            map_name,
                            row["layer"] or layer,
                            vtype,
                            expression,
                        ),
                    )
                )
            job_names.append(map_name)

            # Store the new maps
            new_maps[row["id"]] = new_map

        succeeded = []
        done = run_in_batches(ctx, _run_job, jobs, group, succeeded=succeeded)
        created.extend(job_names[index] for index in succeeded)
        if not done:
            # A map that existed before the run and made a process
            # fail is not in the list and stays. A map that existed
            # before and was overwritten by a process that succeeded
            # is in the list and goes, as its old content is gone.
            _remove_new_maps(type, created)
            msgr.fatal(_("Error in computation process"))
    return new_maps


def _register_maps(
    sp,
    new_sp,
    rows,
    new_maps,
    type,
    expression,
    register_null,
    has_semantic_labels,
    dbif,
):
    """Register the maps in the new dataset and return the empty new maps

    Without an expression the source maps are registered. With one, the new
    maps are, with the time of the source map; an empty one is not registered
    unless register_null, it is returned so that the caller removes it.
    """
    msgr = get_tgis_message_interface()
    num_rows = len(rows)
    # collect empty maps to remove them
    empty_maps = []

    # Register the maps in the database
    for count, row in enumerate(rows, 1):
        if count % 10 == 0:
            msgr.percent(count, num_rows, 1)

        old_map = sp.get_new_map_instance(row["id"])
        old_map.select(dbif)

        if not expression:
            # Just register the source map in the new STRDS if no
            # the expression option is not used
            if not old_map.is_in_db():
                # Maps that are not part of the temporal database
                # in the current mapset need to be inserted first
                old_map.insert(dbif)
            new_sp.register_map(old_map, dbif)
            continue

        # Register the new maps
        if row["id"] in new_maps:
            new_map = new_maps[row["id"]]

            # Read the raster map data
            new_map.load()

            # In case of a empty map continue, do not register empty
            # maps
            if not register_null and (
                (
                    type in {"raster", "raster3d"}
                    and new_map.metadata.get_min() is None
                    and new_map.metadata.get_max() is None
                )
                or (
                    type == "vector" and not new_map.metadata.get_number_of_primitives()
                )
            ):
                empty_maps.append(new_map)
                continue

            # Set the time stamp
            new_map.set_temporal_extent(old_map.get_temporal_extent())

            if type == "raster" and has_semantic_labels:
                # Set the semantic label
                new_map.set_semantic_label(row["semantic_label"])

            # Insert map in temporal database
            new_map.insert(dbif)
            new_sp.register_map(new_map, dbif)
    return empty_maps


def _run_job(job) -> None:
    """Run one job of extract_dataset() in a child process

    :param job: A function and the tuple of its arguments
    """
    function, args = job
    function(*args)


def _remove_new_maps(type, names):
    """Remove the maps that a failed extraction has made

    :param type: The map type of the extraction, as in extract_dataset()
    :param names: The names of the maps, empty for nothing to remove
    """
    if names:
        gs.run_command(
            "g.remove",
            flags="f",
            type=type.replace("_", ""),
            name=",".join(names),
            superquiet=True,
        )


def run_vector_extraction(
    input_map: str,
    output: str,
    layer: str | int,
    type: str,
    where: str,
) -> None:
    """Run v.extract in quiet mode.

    Wrapper function setting verbosity to quiet. It is intended to be
    run in parallel in `extract_dataset`. Parallel execution requires
    a database backend that support it, like PostgreSQL.
    """
    try:
        gs.run_command(
            "v.extract",
            input=input_map,
            output=output,
            layer=layer,
            type=type,
            where=where,
            overwrite=gs.overwrite(),
            quiet=True,
        )
    except CalledModuleError:
        sys.exit(1)
