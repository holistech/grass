"""Raster and 3D raster map calculation on the temporal algebra core

t.rast.mapcalc samples its inputs by the first input and runs one r.mapcalc
per sampler granule. The inputs and the temporal relations between their maps
come from grass.temporal.algebra (source()), timevar() gives td() and the
calendar functions, and the start_time()/end_time() offsets are computed from
the slot extents. The expression itself stays a text, and the dataset names
and function tokens are substituted textually, as before, so the result maps,
their names and the warnings are unchanged. The tool has no switch between
the classic and the core algebra, so the sampling follows the classic rules of
the classic sample_by_dataset() exactly (kept as the reference in
grass.temporal.testing.reference), through grass.temporal.related_maps.

SPDX-FileCopyrightText: 2012-2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from functools import partial

import grass.script as gs
from grass.script.utils import _get_multiprocessing_context, get_num_suffix

from .algebra.content import Const
from .algebra.series import Series, Slot
from .algebra.sources import source
from .algebra.time_functions import timevar
from .batches import run_in_batches, run_mapcalc
from .db import SQLDatabaseInterfaceConnection, SQLStatementError
from .state import get_current_mapset, get_tgis_message_interface
from .datetime_math import time_delta_to_relative_time
from .factory import dataset_factory
from .kinds import KINDS, stds_kind_of
from .open_stds import check_new_stds, open_new_stds, open_old_stds
from .related_maps import method_relations, related_per_granule, sampler_refused

# The calendar tokens need absolute time, as in the classic tool.
_CALENDAR_TOKENS = tuple(
    f"{side}_{field}"
    for side in ("start", "end")
    for field in (
        "doy",
        "dow",
        "year",
        "month",
        "week",
        "day",
        "hour",
        "minute",
        "second",
    )
)
_TIME_TOKENS = ("td", "start_time", "end_time", *_CALENDAR_TOKENS)


def _time_token_value(name, first_extent, extent, is_absolute, msgr):
    """The value of a temporal-function token for one granule, as a string

    start_time()/end_time() are the offset of the granule from the start of the
    first granule, in days for absolute time and in the unit for relative time;
    timevar() has no such offset, so it is computed here, with
    time_delta_to_relative_time() so that the float form (90.0, not 90) is
    kept. td() and the calendar functions come from timevar(). A calendar token
    on relative time is fatal, as in the classic tool. A value that does not
    exist, such as the end of an instant, becomes "null()".
    """
    if name in ("start_time", "end_time"):
        stamp = extent.start if name == "start_time" else extent.end
        if stamp is None:
            return "null()"
        if is_absolute:
            return str(time_delta_to_relative_time(stamp - first_extent.start))
        return str(stamp - first_extent.start)
    if name in _CALENDAR_TOKENS and not is_absolute:
        side = "start_*" if name.startswith("start") else "end_*"
        msgr.fatal(
            _("The temporal operators <{}> support only absolute time.").format(side)
        )
    value = timevar(Series((Slot(extent, Const(None)),)), name).slots[0].content.value
    return "null()" if value is None else str(value)


def _substitute_time_tokens(expr, first_extent, extent, is_absolute, msgr):
    """Replace every temporal-function token in expr by its value"""
    for name in _TIME_TOKENS:
        token = f"{name}()"
        if token in expr:
            expr = expr.replace(
                token,
                _time_token_value(name, first_extent, extent, is_absolute, msgr),
            )
    return expr


def _sample_column(first_series, name, names, spatial, where, stds_type, msgr):
    """The map name of the input name's first related map per sampler granule

    Returns a list with one entry per granule: the name of the map used, or
    None where none relates.

    The tool has no switch between the classic and the core algebra, so the
    map used is the one sample_by_dataset() takes, the first of the first
    relation in names that has one; related_maps explains why gather() does
    not do that.

    Warns, as the classic tool does, once per granule that relates more than
    one map. An input without registered maps gives a column of None.
    """
    inputs = source(name, where=where, stds_type=stds_type)
    column = []
    for found in related_per_granule(first_series, names, inputs, spatial=spatial):
        if len(found) > 1:
            msgr.warning(
                _(
                    "Found more than a single map in a sample granule. Only "
                    "the first map is used for computation. Use "
                    "t.rast.aggregate.ds to create synchronous raster "
                    "datasets."
                )
            )
        column.append(found[0].content.ident.split("@")[0] if found else None)

    return column


def dataset_mapcalculator(
    inputs,
    output,
    type,
    expression,
    base,
    method,
    nprocs: int = 1,
    register_null: bool = False,
    spatial: bool = False,
    where=None,
):
    """Perform map calculations on temporally sampled maps of space time
    raster or 3D raster datasets

    The first input is the sampler; every other input is sampled by it with the
    given method, and one r.mapcalc expression is run per sampler granule. The
    sampling and the temporal functions are computed on the algebra core; see
    the module docstring.

    Temporal operators in the expression, besides the r.mapcalc operators:
    td(), start_time(), end_time() (the latter two as the offset from the first
    granule, in days or units), and for absolute time the calendar functions
    start_doy()/dow()/year()/month()/week()/day()/hour()/minute()/second() and
    their end_* counterparts.

    :param inputs: comma-separated names of the input datasets
    :param output: the new output dataset
    :param type: "raster" or "raster3d"
    :param expression: the r(3).mapcalc expression
    :param base: the basename of the result maps
    :param method: list of sampling method names
    :param nprocs: number of parallel r.mapcalc processes
    :param register_null: keep (register) null result maps
    :param spatial: also require the 2D extents of related maps to touch or
        overlap
    :param where: SQL WHERE on the registered maps of every input
    """
    msgr = get_tgis_message_interface()
    names = inputs.split(",")
    stds_type = stds_kind_of(type).name
    map_kind = KINDS[stds_kind_of(type).map_kind].name

    # No sampling when the inputs reduce to a single dataset, deduplicated by
    # name without the semantic label, as in the classic tool. The expression
    # refers to a dataset by the name it has without the mapset, which can
    # differ from what was typed in inputs, so that name is what is substituted.
    uniq = []
    display_names = {}
    datasets = {}
    first_dataset = None
    for name in names:
        # Opened as strds / str3ds because only that type reads "name.label".
        dataset = open_old_stds(name, stds_type)
        datasets[name] = dataset
        display_names[name] = dataset.get_name()
        if first_dataset is None:
            first_dataset = dataset
        if dataset.get_name(semantic_label=False) not in uniq:
            uniq.append(dataset.get_name(semantic_label=False))
    do_sampling = len(uniq) > 1

    # Fail before any computation if the output cannot be created.
    check_new_stds(output, type, None, gs.overwrite())

    # The extra inputs in reverse sorted order, so that a longer dataset name is
    # substituted before a name that is its prefix, as the classic tool does.
    others = sorted(names[1:])
    others.reverse()

    if spatial:
        msgr.message(_("Starting spatio-temporal sampling..."))
    else:
        msgr.message(_("Starting temporal sampling..."))

    try:
        first_series = source(names[0], where=where, stds_type=stds_type)
    except SQLStatementError as error:
        msgr.fatal(_("Invalid where condition <{}>: {}").format(where, error))
    if len(first_series.slots) == 0:
        if not do_sampling:
            msgr.message(
                _("No maps registered in input dataset <{}>").format(
                    display_names[names[0]]
                )
            )
            return 0
        sampler_refused(first_dataset, datasets[others[0]], msgr)
        msgr.message(_("No samples found for map calculation"))
        return 0
    is_absolute = first_series.temporal_type == "absolute"
    first_extent = first_series.slots[0].extent
    sample_extents = [slot.extent for slot in first_series.slots]

    id_list = [names[0], *others]
    columns = {
        names[0]: [slot.content.ident.split("@")[0] for slot in first_series.slots]
    }

    # The sampler granule carries the time stamp and, for raster, the semantic
    # label of the result map, as in the classic tool. The label is read from
    # the registered maps of the sampler, where t.register stored it: select()
    # on a single map does not return it (measured 2026-10-14 with a map
    # labelled by r.support before t.register), load() reads the GRASS map
    # instead of the temporal database. 3D rasters have no semantic label
    # (the 3D raster metadata has no semantic label), so it is only read for
    # raster; the shared function serves both types.
    mapset = get_current_mapset()
    labels = {}
    if map_kind == "raster":
        for registered in (
            first_dataset.get_registered_maps_as_objects(
                where=where, order="start_time"
            )
            or []
        ):
            labels[registered.get_id()] = registered.metadata.get_semantic_label()
    labels = [labels.get(slot.content.ident) for slot in first_series.slots]

    if do_sampling:
        method_names = method_relations(method)
        for name in others:
            if sampler_refused(first_dataset, datasets[name], msgr):
                msgr.message(_("No samples found for map calculation"))
                return 0
            columns[name] = _sample_column(
                first_series, name, method_names, spatial, where, stds_type, msgr
            )
    else:
        # Inputs that name one dataset (x,x) are not sampled: the n-th map of
        # each is used with the n-th map of the first, as in the classic tool.
        for name in others:
            other_series = source(name, where=where, stds_type=stds_type)
            if len(other_series.slots) == 0:
                msgr.message(
                    _("No maps registered in input dataset <{}>").format(
                        display_names[name]
                    )
                )
                return 0
            columns[name] = [
                slot.content.ident.split("@")[0] for slot in other_series.slots
            ]

    msgr.message(_("Starting mapcalc computation..."))

    dbif = SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        ctx = _get_multiprocessing_context()
        num = len(sample_extents)
        result_maps = []
        statements = []
        count = 0
        # r3.mapcalc is left to decide its number of threads, as it always was
        runner = partial(
            run_mapcalc,
            "r.mapcalc" if map_kind == "raster" else "r3.mapcalc",
            nprocs=1 if map_kind == "raster" else None,
        )
        for i in range(num):
            count += 1
            map_name = f"{base}_{get_num_suffix(count, num)}"
            expr = expression.replace(" ", "")
            valid = True
            for dataset_name in id_list:
                column = columns[dataset_name]
                map_in_slot = column[i] if i < len(column) else None
                if map_in_slot is None:
                    valid = False
                    break
                expr = expr.replace(display_names[dataset_name], map_in_slot)
            if not valid:
                continue
            expr = _substitute_time_tokens(
                expr, first_extent, sample_extents[i], is_absolute, msgr
            )
            statement = f"{map_name}={expr}"
            map_id = f"{map_name}@{mapset}"
            new_map = dataset_factory(map_kind, map_id)
            # A result map that is already registered is replaced only with
            # overwrite, and its entry must go first or insert() fails.
            if new_map.is_in_db(dbif):
                if gs.overwrite():
                    new_map.delete(dbif)
                    new_map = dataset_factory(map_kind, map_id)
                else:
                    # The batches run after this loop, so nothing is computed
                    # and the result dataset is not made yet.
                    msgr.fatal(
                        _(
                            "Map <{}> is already in temporal database, "
                            "use overwrite flag to overwrite"
                        ).format(map_id)
                    )
            extent = sample_extents[i]
            if is_absolute:
                new_map.set_absolute_time(extent.start, extent.end)
            else:
                new_map.set_relative_time(extent.start, extent.end, extent.unit)
            if labels[i] is not None:
                new_map.set_semantic_label(labels[i])
            result_maps.append(new_map)
            msgr.verbose(_('Apply mapcalc expression: "{}"').format(statement))
            statements.append(statement)
        if not run_in_batches(
            ctx,
            runner,
            statements,
            nprocs,
            progress=lambda done, total: msgr.percent(done, total, 10),
        ):
            msgr.fatal(_("Error while mapcalc computation"))
    finally:
        dbif.close()

    _register_results(output, type, names[0], result_maps, register_null, num)
    return 0


def _register_results(output, type, first_name, result_maps, register_null, num):
    """Register the computed maps, removing null maps unless register_null

    num is the number of sampler granules, the denominator of the progress
    that is reported while the maps are registered.
    """
    msgr = get_tgis_message_interface()
    msgr.message(_("Starting map registration in temporal database..."))
    dbif = SQLDatabaseInterfaceConnection()
    dbif.connect()
    # The name may carry a semantic label, which only strds reads.
    stds_type = stds_kind_of(type).name
    first_stds = open_old_stds(first_name, stds_type, dbif)
    temporal_type, semantic_type, title, description = first_stds.get_initial_values()
    new_sp = open_new_stds(
        output,
        type,
        temporal_type,
        title,
        description,
        semantic_type,
        dbif,
        gs.overwrite(),
    )
    empty_maps = []
    for count, new_map in enumerate(result_maps, 1):
        msgr.percent(count, num, 10)
        new_map.load()
        if new_map.metadata.get_min() is None and new_map.metadata.get_max() is None:
            if not register_null:
                empty_maps.append(new_map)
                continue
        new_map.insert(dbif)
        new_sp.register_map(new_map, dbif)
    new_sp.update_from_registered_maps(dbif)
    if empty_maps:
        n_empty, n_tot = len(empty_maps), len(result_maps)
        msgr.warning(
            _("Removing {}/{} ({}%) maps because empty...").format(
                n_empty, n_tot, n_empty * 100.0 / n_tot
            )
        )
        element = "raster" if stds_type == "strds" else "raster_3d"
        gs.run_command(
            "g.remove",
            flags="f",
            type=element,
            name=",".join(m.get_name() for m in empty_maps),
            quiet=True,
        )
    dbif.close()
