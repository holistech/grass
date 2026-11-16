"""Raster and 3D raster map calculation on the temporal algebra core

t.rast.mapcalc samples its inputs by the first input and runs one r.mapcalc
per sampler granule. The inputs and the temporal relations between their maps
come from grass.temporal.algebra (source()), timevar() gives td() and the
calendar functions, and the start_time()/end_time() offsets are computed from
the slot extents. The expression itself stays a text: a dataset name is
replaced by the map name where it stands as a whole name, not as a part of a
longer name and not as the name of a function, and the function tokens by
their values. The sampling follows the rules of sample_by_dataset() of the
releases up to GRASS 8.5, through grass.temporal.related_maps, which explains
the one deliberate difference.

SPDX-FileCopyrightText: 2012-2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import re
from functools import partial

import grass.script as gs
from grass.exceptions import FatalError
from grass.script.utils import _get_multiprocessing_context, get_num_suffix

from .algebra.content import Const
from .algebra.series import Series, Slot
from .algebra.sources import source
from .algebra.time_functions import timevar
from .batches import run_in_batches, run_mapcalc
from .db import SQLDatabaseInterfaceConnection, SQLStatementError, connection
from .state import get_current_mapset, get_tgis_message_interface
from .tool_steps import mapcalc_name
from .datetime_math import time_delta_to_relative_time
from .factory import dataset_factory
from .kinds import KINDS, stds_kind_of
from .open_stds import check_new_stds, open_new_stds, open_old_stds
from .related_maps import method_relations, related_per_granule, sampler_refusal

# The calendar tokens need absolute time, as in the tool of GRASS 8.5.
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

# A name in an r.mapcalc expression is made of word characters, and a raster
# map name may hold dots and an "@" before the mapset. A dataset name is
# replaced only where no word character or dot comes before it and no word
# character or dot after it, so "day" stays in "start_day()" and "soil" stays
# in "soil_deep". The mapset of the dataset that was found may follow, as in
# "ds@first", and is replaced together with the name, because mapcalc_name()
# writes a map of another mapset with its mapset already.
# An "@" before the name is refused only when a name character precedes it,
# as in the mapset of "map@ds": a leading "@" is the label operator of
# r.mapcalc, so "@ds" reads the category labels of the map of ds.
_NAME_BEFORE = r"(?<![\w.])(?<![\w.]@)"
_NAME_AFTER = r"(?![\w.])"
# The tokens of the temporal functions, with blanks allowed around the
# parentheses as r.mapcalc allows them
_TIME_TOKEN_PATTERNS = {
    name: re.compile(_NAME_BEFORE + re.escape(name) + r"\s*\(\s*\)")
    for name in _TIME_TOKENS
}


def _time_token_value(name, first_extent, extent, is_absolute, msgr):
    """The value of a temporal-function token for one granule, as a string

    start_time()/end_time() are the offset of the granule from the start of the
    first granule, in days for absolute time and in the unit for relative time;
    timevar() has no such offset, so it is computed here, with
    time_delta_to_relative_time() so that the float form (90.0, not 90) is
    kept. td() and the calendar functions come from timevar(). A calendar token
    on relative time is fatal, as in the tool of GRASS 8.5. A value that does
    not exist, such as the end of an instant, becomes "null()".
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
    if name == "td" and extent.end is None:
        # timevar() refuses td() of an instant, as the algebra does; this tool
        # has always written null() for it.
        return "null()"
    value = timevar(Series((Slot(extent, Const(None)),)), name).slots[0].content.value
    return "null()" if value is None else str(value)


def _substitute_time_tokens(expr, first_extent, extent, is_absolute, msgr):
    """Replace every temporal-function token in expr by its value"""
    for name, pattern in _TIME_TOKEN_PATTERNS.items():
        if pattern.search(expr):
            value = _time_token_value(name, first_extent, extent, is_absolute, msgr)
            expr = pattern.sub(lambda _match, value=value: value, expr)
    return expr


def _dataset_name_pattern(names):
    """A pattern that matches each name where it stands as a dataset name

    names holds pairs of a dataset name without the mapset and the mapset of
    the dataset; a match is the name, optionally followed by "@" and that
    mapset. A name followed by "(" (blanks allowed) is the name of a function,
    such as a dataset "td" in "td()", and stays. Longer names come first in
    the alternation, so that "x.label" wins over "x" at the same place.
    """
    alternatives = "|".join(
        f"{re.escape(name)}(?:@{re.escape(mapset)})?"
        for name, mapset in sorted(
            set(names), key=lambda pair: len(pair[0]), reverse=True
        )
    )
    return re.compile(rf"{_NAME_BEFORE}(?:{alternatives}){_NAME_AFTER}(?!\s*\()")


def _qualified(name, dataset):
    """The name with the mapset of the dataset that open_old_stds() found for it

    With the mapset source() looks in that mapset only, where it tries a name
    with a dot whole before it reads the text after the dot as a semantic
    label, as open_old_stds() does, so both read the same dataset.
    """
    return name if "@" in name else f"{name}@{dataset.get_mapset()}"


# Each type has a message of its own rather than one with the name of the
# type inserted, so that translators can inflect the whole sentence. The
# raster text is the one of t.rast.series.
def _where_selects_nothing(stds_type):
    return {
        "strds": _(
            "The where condition selects no map of space time raster dataset <{}>"
        ),
        "str3ds": _(
            "The where condition selects no map of space time 3D raster dataset <{}>"
        ),
    }[stds_type]


def _warn_nothing_selected(dataset, where, stds_type, empty_text, msgr):
    """Warn that an input gives no map to compute with

    A warning, not an error, so that a script that computes possibly empty
    selections keeps running, as with t.rast.series. With a where condition
    the warning names it, because the dataset itself may have maps;
    otherwise it is empty_text. The dataset is named with its semantic label,
    which also selects the maps.
    """
    if where:
        msgr.warning(
            _where_selects_nothing(stds_type).format(
                f"{dataset.get_name()}@{dataset.get_mapset()}"
            )
        )
    else:
        msgr.warning(empty_text)


def _read_series(name, where, stds_type, msgr):
    """source() of the name; a dataset that source() does not find ends the run

    source() raises FatalError for a missing dataset, which a tool would show
    as a traceback; the message goes to msgr.fatal() instead.
    """
    try:
        return source(name, where=where, stds_type=stds_type)
    except FatalError as error:
        msgr.fatal(str(error))


def _sample_column(first_series, name, names, spatial, where, stds_type, msgr):
    """The input name's first related map per sampler granule

    Returns a list with one entry per granule: the map used as mapcalc_name()
    writes it, or None where none relates.

    The map used is the one sample_by_dataset() of the releases up to GRASS
    8.5 took, the first of the first relation in names that has one;
    related_maps explains why gather() does not do that.

    Warns, as the tool of GRASS 8.5 did, once per granule that relates more
    than one map. An input without registered maps gives a column of None.
    Ends with a message if the input has times with a time zone offset and
    the sampler times without one, or the other way round.
    """
    inputs = _read_series(name, where, stds_type, msgr)
    try:
        per_granule = related_per_granule(first_series, names, inputs, spatial=spatial)
    except ValueError as error:
        # Datasets with and without a time zone offset cannot be related; the
        # refusal comes before the first map is computed.
        msgr.fatal(str(error))
    column = []
    for found in per_granule:
        if len(found) > 1:
            msgr.warning(
                _(
                    "Found more than a single map in a sample granule. Only "
                    "the first map is used for computation. Use "
                    "t.rast.aggregate.ds to create synchronous raster "
                    "datasets."
                )
            )
        column.append(mapcalc_name(found[0].content.ident) if found else None)

    return column


def _open_inputs(names, stds_type):
    """Open the input datasets and tell whether they are to be sampled

    No sampling when the inputs reduce to a single dataset, deduplicated by
    name without the semantic label, as in the tool of GRASS 8.5. The
    expression refers to a dataset by the name it has without the mapset,
    which can differ from what was typed in inputs, so that name is what is
    substituted.
    Two inputs with the same such name, as in "x,x" or "x,x@other", are
    refused, because the expression cannot tell them apart.

    :return: the datasets and their display names by the name in inputs, and
        whether more than one dataset is left
    """
    msgr = get_tgis_message_interface()
    uniq = []
    display_names = {}
    datasets = {}
    for name in names:
        # Opened as strds / str3ds because only that type reads "name.label".
        dataset = open_old_stds(name, stds_type)
        if dataset.get_name() in display_names.values():
            msgr.fatal(
                _(
                    "The name <{}> stands more than once in inputs, so the "
                    "expression cannot tell the inputs apart"
                ).format(dataset.get_name())
            )
        datasets[name] = dataset
        display_names[name] = dataset.get_name()
        if dataset.get_name(semantic_label=False) not in uniq:
            uniq.append(dataset.get_name(semantic_label=False))
    return datasets, display_names, len(uniq) > 1


def _semantic_labels(first_dataset, first_series, where, map_kind):
    """Return the semantic label of the sampler granule of each slot

    The sampler granule carries the time stamp and, for raster, the semantic
    label of the result map, as in the tool of GRASS 8.5. The label is read from
    the registered maps of the sampler, where t.register stored it: select()
    on a single map does not return it (measured 2026-10-14 with a map
    labelled by r.support before t.register), load() reads the GRASS map
    instead of the temporal database. 3D rasters have no semantic label
    (the 3D raster metadata has no semantic label), so it is only read for
    raster; the shared function serves both types.
    """
    labels = {}
    if map_kind == "raster":
        for registered in (
            first_dataset.get_registered_maps_as_objects(
                where=where, order="start_time"
            )
            or []
        ):
            labels[registered.get_id()] = registered.metadata.get_semantic_label()
    return [labels.get(slot.content.ident) for slot in first_series.slots]


def _plan_statements(
    expression,
    base,
    id_list,
    columns,
    display_names,
    mapsets,
    first_series,
    labels,
    map_kind,
    dbif,
    msgr,
):
    """Make the result maps and the r.mapcalc statements of the granules

    A granule for which an input has no map is skipped. A result map that is
    already registered is replaced only with overwrite. mapsets holds the
    mapset of the dataset of each name in inputs, which the expression may
    write after the dataset name.

    :return: the new maps, with their time and label, and their statements
    """
    mapset = get_current_mapset()
    names_in_expression = _dataset_name_pattern(
        (display_names[dataset_name], mapsets[dataset_name]) for dataset_name in id_list
    )
    is_absolute = first_series.temporal_type == "absolute"
    first_extent = first_series.slots[0].extent
    sample_extents = [slot.extent for slot in first_series.slots]
    num = len(sample_extents)
    result_maps = []
    statements = []
    count = 0
    for i in range(num):
        count += 1
        map_name = f"{base}_{get_num_suffix(count, num)}"
        maps_in_slot = {
            display_names[name]: columns[name][i] if i < len(columns[name]) else None
            for name in id_list
        }
        if None in maps_in_slot.values():
            continue
        # One pass over the expression, so that a map name that was put in
        # is not read as a dataset name again. A display name holds no "@",
        # so the match without its mapset is the key.
        expr = names_in_expression.sub(
            lambda match, maps=maps_in_slot: maps[match.group().partition("@")[0]],
            expression,
        )
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
    return result_maps, statements


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
    """Perform map calculations on temporally sampled maps.

    The maps belong to space time raster or 3D raster datasets.

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

    datasets, display_names, do_sampling = _open_inputs(names, stds_type)
    first_dataset = datasets[names[0]]

    # Fail before any computation if the output cannot be created.
    check_new_stds(output, type, None, gs.overwrite())

    # The extra inputs in reverse sorted order, as in the tool of GRASS 8.5: the
    # order decides which refusal or warning comes first.
    others = sorted(names[1:])
    others.reverse()

    if spatial:
        msgr.message(_("Starting spatio-temporal sampling..."))
    else:
        msgr.message(_("Starting temporal sampling..."))

    try:
        first_series = _read_series(
            _qualified(names[0], first_dataset), where, stds_type, msgr
        )
    except SQLStatementError as error:
        msgr.fatal(_("Invalid where condition <{}>: {}").format(where, error))
    if len(first_series.slots) == 0:
        if not do_sampling:
            _warn_nothing_selected(
                first_dataset,
                where,
                stds_type,
                _("No maps registered in input dataset <{}>").format(
                    display_names[names[0]]
                ),
                msgr,
            )
            return 0
        # A sampler without registered maps has no map time (get_map_time()
        # gives None), which the interval check would refuse as time instants.
        # A sampler that where emptied still has its maps and keeps the check.
        refusal = sampler_refusal(
            first_dataset,
            datasets[others[0]],
            check_map_time=first_dataset.get_map_time() is not None,
        )
        if refusal is not None:
            msgr.fatal(refusal)
        _warn_nothing_selected(
            first_dataset,
            where,
            stds_type,
            _("No samples found for map calculation"),
            msgr,
        )
        return 0

    id_list = [names[0], *others]
    columns = {
        names[0]: [mapcalc_name(slot.content.ident) for slot in first_series.slots]
    }

    # The sampler granule carries the time stamp and, for raster, the semantic
    # label of the result map, as in the tool of GRASS 8.5. The label is read from
    # the registered maps of the sampler, where t.register stored it: select()
    # on a single map does not return it (measured 2026-10-14 with a map
    # labelled by r.support before t.register), load() reads the GRASS map
    # instead of the temporal database. 3D rasters have no semantic label
    # (the 3D raster metadata has no semantic label), so it is only read for
    # raster; the shared function serves both types.
    labels = _semantic_labels(first_dataset, first_series, where, map_kind)

    if do_sampling:
        method_names = method_relations(method)
        for name in others:
            # A refusal ends the run with an error, so that a script sees
            # that nothing was computed.
            refusal = sampler_refusal(first_dataset, datasets[name])
            if refusal is not None:
                msgr.fatal(refusal)
            columns[name] = _sample_column(
                first_series,
                _qualified(name, datasets[name]),
                method_names,
                spatial,
                where,
                stds_type,
                msgr,
            )
    else:
        # Inputs that name one dataset with different semantic labels
        # (x.B4,x.B8) are not sampled: the n-th map of each is used with the
        # n-th map of the first, as in the tool of GRASS 8.5.
        for name in others:
            other_series = _read_series(
                _qualified(name, datasets[name]), where, stds_type, msgr
            )
            if len(other_series.slots) == 0:
                _warn_nothing_selected(
                    datasets[name],
                    where,
                    stds_type,
                    _("No maps registered in input dataset <{}>").format(
                        display_names[name]
                    ),
                    msgr,
                )
                return 0
            columns[name] = [
                mapcalc_name(slot.content.ident) for slot in other_series.slots
            ]

    msgr.message(_("Starting mapcalc computation..."))

    dbif = SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        ctx = _get_multiprocessing_context()
        num = len(first_series.slots)
        # r3.mapcalc is left to decide its number of threads, as it always was
        runner = partial(
            run_mapcalc,
            KINDS[map_kind].mapcalc_module,
            nprocs=1 if map_kind == "raster" else None,
        )
        result_maps, statements = _plan_statements(
            expression,
            base,
            id_list,
            columns,
            display_names,
            {name: datasets[name].get_mapset() for name in id_list},
            first_series,
            labels,
            map_kind,
            dbif,
            msgr,
        )
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
    with connection() as dbif:
        # The name may carry a semantic label, which only strds reads.
        stds_type = stds_kind_of(type).name
        first_stds = open_old_stds(first_name, stds_type, dbif)
        temporal_type, semantic_type, title, description = (
            first_stds.get_initial_values()
        )
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
            if (
                new_map.metadata.get_min() is None
                and new_map.metadata.get_max() is None
            ) and not register_null:
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
            element = KINDS[stds_kind_of(type).map_kind].remove_type
            gs.run_command(
                "g.remove",
                flags="f",
                type=element,
                name=",".join(m.get_name() for m in empty_maps),
                quiet=True,
            )
