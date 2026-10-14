"""Raster and 3D raster map calculation on the temporal algebra core

t.rast.mapcalc samples its inputs by the first input and runs one r.mapcalc
per sampler granule. The sampling and the values of the temporal functions
come from grass.temporal.algebra: gather() relates the inputs, timevar() gives
td() and the calendar functions, and the start_time()/end_time() offsets are
computed from the slot extents. The expression itself stays a text, and the
dataset names and function tokens are substituted textually, as before, so the
result maps, their names and the warnings are unchanged; there is no classic
switch for this tool.

SPDX-FileCopyrightText: 2012-2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import sys

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.script.utils import _get_multiprocessing_context, get_num_suffix

from .algebra.content import Const
from .algebra.operations import gather
from .algebra.relations import (
    contains,
    during,
    equal,
    finishes,
    follows,
    overlapped,
    overlaps,
    precedes,
    relation,
    started,
    starts,
)
from .algebra.series import Series, Slot
from .algebra.sources import source
from .algebra.time_functions import timevar
from .core import (
    SQLDatabaseInterfaceConnection,
    get_current_mapset,
    get_tgis_message_interface,
)
from .datetime_math import time_delta_to_relative_time
from .open_stds import check_new_stds, open_new_stds, open_old_stds

_ONLY_ABSOLUTE = "The temporal operators <%s> support only absolute time."

# Each sampling method name, read as "first R input". gather() reads the
# relation from the target side, and the target is the first input (the
# sampler), which is the side AbstractSpaceTimeDataset.sample_by_dataset()
# reads from as well. So the method name maps straight to a relation; there is
# no inversion. "start" leaves equal out to match a long-standing quirk of
# sample_by_dataset(): it appends "equals", which upper-cases to the key
# "EQUALS" that the topology builder never files (it files "EQUAL"), so the
# classic "start" never matches a map of equal time.
_METHOD_RELATIONS = {
    "equal": equal,
    "during": during,
    "contain": contains,
    "overlap": overlaps | overlapped,
    "follows": follows,
    "precedes": precedes,
    "start": overlapped | starts | started | finishes | contains,
}

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


def _method_relation(method):
    """Return the core relation of a list of sampling method names"""
    rel = None
    for name in method:
        if name not in _METHOD_RELATIONS:
            msg = f"Unknown sampling method <{name}>"
            raise ValueError(msg)
        part = _METHOD_RELATIONS[name]
        rel = part if rel is None else rel | part
    return rel


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
        msgr.fatal(_(_ONLY_ABSOLUTE) % side)
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


def _sample_columns(first_series, others, relation_, where, stds_type, msgr):
    """The map name of each extra input's first related map per granule

    Returns a dict from input name to a list with one entry per sampler
    granule: the name of the first (earliest-start) related map, or None where
    none relates. Warns, as the classic tool does, when a granule relates more
    than one map. Returns None if an input has no registered map.
    """
    columns = {}
    for name in others:
        inp = source(name, where=where, stds_type=stds_type)
        if len(inp.slots) == 0:
            return None
        picked = gather(first_series, relation_, inp, reduce="first", missing="null")
        counts = gather(first_series, relation_, inp, reduce="count")
        # One warning per granule with several related maps, as the classic
        # tool gave.
        for slot in counts.slots:
            if (slot.content.value or 0) > 1:
                msgr.warning(
                    _(
                        "Found more than a single map in a sample granule. Only "
                        "the first map is used for computation. Use "
                        "t.rast.aggregate.ds to create synchronous raster "
                        "datasets."
                    )
                )
        column = []
        for slot in picked.slots:
            content = slot.content
            is_null = isinstance(content, Const) and content.value is None
            column.append(None if is_null else content.ident.split("@")[0])
        columns[name] = column
    return columns


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
    :param spatial: relate maps spatially as well
    :param where: SQL WHERE on the registered maps of every input
    """
    msgr = get_tgis_message_interface()
    names = inputs.split(",")
    stds_type = {"raster": "strds", "raster3d": "str3ds"}[type]

    # No sampling when the inputs reduce to a single dataset, deduplicated by
    # name without the semantic label, as in the classic tool. The expression
    # refers to a dataset by the name it has without the mapset, which can
    # differ from what was typed in inputs, so that name is what is substituted.
    uniq = []
    display_names = {}
    first_dataset = None
    for name in names:
        dataset = open_old_stds(name, type)
        display_names[name] = dataset.get_name()
        if first_dataset is None:
            first_dataset = dataset
        if dataset.get_name(semantic_label=False) not in uniq:
            uniq.append(dataset.get_name(semantic_label=False))
    do_sampling = len(uniq) > 1

    # Fail before any computation if the output cannot be created.
    check_new_stds(output, type, None, gs.overwrite())

    first_series = source(names[0], where=where, stds_type=stds_type)
    if len(first_series.slots) == 0:
        msgr.message(
            _("No maps registered in input dataset <{}>").format(
                display_names[names[0]]
            )
        )
        return 0
    is_absolute = first_series.temporal_type == "absolute"
    first_extent = first_series.slots[0].extent
    sample_extents = [slot.extent for slot in first_series.slots]

    # The extra inputs in reverse sorted order, so that a longer dataset name is
    # substituted before a name that is its prefix, as the classic tool does.
    others = sorted(names[1:])
    others.reverse()
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
    # (Raster3DMetadata has no get_semantic_label), so it is only read for
    # raster; the shared function serves both types.
    mapset = get_current_mapset()
    map_class = first_series_map_class(type)
    labels = {}
    if type == "raster":
        for registered in (
            first_dataset.get_registered_maps_as_objects(
                where=where, order="start_time"
            )
            or []
        ):
            labels[registered.get_id()] = registered.metadata.get_semantic_label()
    labels = [labels.get(slot.content.ident) for slot in first_series.slots]

    if do_sampling:
        if spatial:
            msgr.message(_("Starting spatio-temporal sampling..."))
        else:
            msgr.message(_("Starting temporal sampling..."))
        relation_ = _method_relation(method)
        if spatial:
            relation_ = relation(str(relation_), spatial=True)
        sampled = _sample_columns(
            first_series, others, relation_, where, stds_type, msgr
        )
        if sampled is None:
            msgr.message(_("No samples found for map calculation"))
            return 0
        columns.update(sampled)
    else:
        # Inputs that differ only in their semantic label are not sampled: the
        # n-th map of each is used with the n-th map of the first, as in the
        # classic tool.
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
        proc_list = []
        proc_count = 0
        count = 0
        runner = _run_mapcalc2d if type == "raster" else _run_mapcalc3d
        for i in range(num):
            count += 1
            msgr.percent(count, num, 10)
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
            new_map = map_class(map_id)
            # A result map that is already registered is replaced only with
            # overwrite, and its entry must go first or insert() fails.
            if new_map.is_in_db(dbif):
                if gs.overwrite():
                    new_map.delete(dbif)
                    new_map = map_class(map_id)
                else:
                    msgr.error(
                        _(
                            "Map <{}> is already in temporal database, "
                            "use overwrite flag to overwrite"
                        ).format(map_id)
                    )
                    continue
            extent = sample_extents[i]
            if is_absolute:
                new_map.set_absolute_time(extent.start, extent.end)
            else:
                new_map.set_relative_time(extent.start, extent.end, extent.unit)
            if labels[i] is not None:
                new_map.set_semantic_label(labels[i])
            result_maps.append(new_map)
            proc_list.append(ctx.Process(target=runner, args=(statement,)))
            proc_list[proc_count].start()
            proc_count += 1
            if proc_count in {nprocs, num} or count == num:
                exitcodes = 0
                for proc in proc_list:
                    proc.join()
                    exitcodes += proc.exitcode
                if exitcodes != 0:
                    msgr.fatal(_("Error while mapcalc computation"))
                proc_list = []
                proc_count = 0
    finally:
        dbif.close()

    _register_results(output, type, names[0], result_maps, register_null)
    return 0


def first_series_map_class(type):
    """The map class of a dataset type"""
    from .space_time_datasets import Raster3DDataset, RasterDataset

    return RasterDataset if type == "raster" else Raster3DDataset


def _register_results(output, type, first_name, result_maps, register_null):
    """Register the computed maps, removing null maps unless register_null"""
    msgr = get_tgis_message_interface()
    dbif = SQLDatabaseInterfaceConnection()
    dbif.connect()
    first_stds = open_old_stds(first_name, type, dbif)
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
    for new_map in result_maps:
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
        element = "raster" if type == "raster" else "raster_3d"
        gs.run_command(
            "g.remove",
            flags="f",
            type=element,
            name=",".join(m.get_name() for m in empty_maps),
            quiet=True,
        )
    dbif.close()


def _run_mapcalc2d(expr) -> None:
    """Run r.mapcalc in a child process"""
    try:
        gs.run_command(
            "r.mapcalc", expression=expr, nprocs=1, overwrite=gs.overwrite(), quiet=True
        )
    except CalledModuleError:
        sys.exit(1)


def _run_mapcalc3d(expr) -> None:
    """Run r3.mapcalc in a child process"""
    try:
        gs.run_command(
            "r3.mapcalc", expression=expr, overwrite=gs.overwrite(), quiet=True
        )
    except CalledModuleError:
        sys.exit(1)
