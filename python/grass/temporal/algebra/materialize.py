"""Plan and materialize series: module calls, map names and registration"""

from dataclasses import dataclass

import grass.script as gs
from grass.exceptions import FatalError
from grass.pygrass.modules import Module, MultiModule, ParallelModuleQueue
from grass.temporal.core import (
    get_current_mapset,
    get_tgis_message_interface,
    init_dbif,
)
from grass.temporal.datetime_math import (
    create_numeric_suffix,
    create_suffix_from_datetime,
    create_time_suffix,
)
from grass.temporal.factory import dataset_factory
from grass.temporal.open_stds import open_new_stds
from grass.temporal.space_time_datasets import VectorDataset
from grass.temporal.temporal_granularity import compute_absolute_time_granularity

from ._adapters import as_map
from .backends import MapcalcStyle, ModuleCall, describe, backend_for
from .content import Call, MapRef, SeriesAggregate, SeriesReduce
from .maptypes import ELEMENTS, KINDS_OF_STDS, MAP_CLASSES, STDS_TYPES

TIME_SUFFIXES = (None, "gran", "time")


@dataclass(frozen=True)
class PlannedMap:
    """A result map: its name, its time stamp and the calls that compute it"""

    name: str
    extent: object
    calls: tuple


@dataclass(frozen=True)
class ProcessChain:
    """What materialize() would do, without doing it"""

    name: str
    stds_type: str
    temporal_type: str
    maps: tuple
    remove: tuple

    @property
    def processes(self):
        """All module calls in the order to run them"""
        return [call for planned in self.maps for call in planned.calls]

    @property
    def register(self):
        """(map name, start, end) of each map to register

        The times are the values of the time stamp, not strings: datetimes
        or numbers, and None as end of an instant.
        """
        return [
            (planned.name, planned.extent.start, planned.extent.end)
            for planned in self.maps
        ]


def _input_idents(series):
    """The identifiers of the maps the slots read"""
    idents = set()
    stack = [slot.content for slot in series.slots]
    while stack:
        node = stack.pop()
        if isinstance(node, MapRef):
            idents.add(node.ident)
        elif isinstance(node, (Call, SeriesReduce, SeriesAggregate)):
            stack.extend(node.args)
    return idents


def _replaces(name, idents):
    """Tell whether a result map of this name would replace one of the maps

    A result is written to the current mapset, so a map of the same name in
    another mapset stays untouched. The mapset is looked up only when a name
    matches, which keeps plan() free of a session otherwise.
    """
    mapset = None
    for ident in idents:
        base, _, ident_mapset = ident.partition("@")
        if base != name:
            continue
        if mapset is None:
            mapset = get_current_mapset()
        if not ident_mapset or ident_mapset == mapset:
            return True
    return False


def _is_legal_name(name):
    """Tell whether a map name is legal, as gs.legal_name() but silently

    gs.legal_name() warns on its own, and the ValueError of plan() would
    report the same name a second time.
    """
    return (
        bool(name)
        and name[0] != "."
        and not any(c in "/\"'@,=*~" or c <= " " or c >= "\177" for c in name)
    )


def reject_input_names(series, names):
    """Reject names that would replace an input map of series

    Only a map of the current mapset (or without a mapset) counts, as a run
    that overwrites would destroy it. Unlike materialize(), which sees only
    the maps of the series it is given, this checks any series, such as the
    full input of an aggregation whose reduced series lost maps.

    :raises ValueError: for the name of an input map of the current mapset
    """
    inputs = _input_idents(series)
    for name in names:
        if _replaces(name, inputs):
            msg = f"The result map <{name}> has the name of an input map"
            raise ValueError(msg)


def _check_given_names(series, names):
    """Reject names that would not be written as given

    :raises ValueError: for a mapset, an illegal name, or the name of an input
        map of the current mapset, which a run that overwrites would destroy
    """
    for name in names:
        if "@" in name:
            msg = f"A map name must not contain '@', got {name!r}"
            raise ValueError(msg)
        if not _is_legal_name(name):
            msg = f"{name!r} is not a legal map name"
            raise ValueError(msg)
    reject_input_names(series, names)


def _map_names(series, basename, time_suffix, names=None, slots=None, repeatable=False):
    """The names of the result maps

    slots are the slots of series in the order of the names, by default those
    of the series (see plan() for list_order).

    With names the caller gives one name per slot verbatim, which the
    aggregation tools use for their own numbering (count from one, with an
    offset and a gap for a dropped empty granule). Without names the maps are
    numbered from zero as t.rast.algebra does, or for absolute time get a
    suffix from the start time.

    With repeatable the names that a time suffix gives to maps of equal time
    may repeat; names given by the caller may not.

    :raises ValueError: for an unknown time_suffix, a names length other than
        the number of slots, names that would collide, are illegal or equal an
        input map, or names together with time_suffix
    """
    if slots is None:
        slots = series.slots
    if names is not None:
        if time_suffix is not None:
            # The names are final; a suffix has nothing to attach to.
            msg = "names cannot be combined with time_suffix"
            raise ValueError(msg)
        if len(names) != len(slots):
            msg = f"Got {len(names)} names for {len(slots)} maps"
            raise ValueError(msg)
        if len(set(names)) != len(names):
            msg = "Several maps would get the same name"
            raise ValueError(msg)
        _check_given_names(series, names)
        return list(names)
    if time_suffix not in TIME_SUFFIXES:
        msg = f"time_suffix must be None, 'gran' or 'time', got {time_suffix!r}"
        raise ValueError(msg)
    absolute = series.temporal_type == "absolute"
    granularity = None
    if absolute and time_suffix == "gran":
        granularity = compute_absolute_time_granularity(
            [as_map(slot.extent) for slot in slots]
        )
    digits = len(str(len(slots)))
    names = []
    for number, slot in enumerate(slots):
        if granularity:
            suffix = create_suffix_from_datetime(slot.extent.start, granularity)
            names.append(f"{basename}_{suffix}")
        elif absolute and time_suffix == "time":
            names.append(f"{basename}_{create_time_suffix(as_map(slot.extent))}")
        else:
            names.append(create_numeric_suffix(basename, number, f"%0{digits}"))
    if len(set(names)) != len(names) and not repeatable:
        msg = (
            "Several maps would get the same name; maps of equal time need the "
            "numeric suffix"
        )
        raise ValueError(msg)
    return names


def _check_name(label, value, stds_type):
    """Reject names that grass.temporal would split into several parts

    _parse_id() in open_stds.py takes "a.b" of a raster dataset for the
    name "a" with the semantic label "b", exits the process for "a.b.c", and
    reads "@" as the mapset; materialize() would find out only after
    computing the maps.
    """
    # A map name may contain a dot, only the name of the dataset is split.
    forbidden = "@." if label == "name" and stds_type == "strds" else "@"
    for character in forbidden:
        if character in value:
            msg = f"The {label} must not contain {character!r}, got {value!r}"
            raise ValueError(msg)


def plan(
    series,
    name,
    *,
    basename=None,
    time_suffix=None,
    selection=False,
    names=None,
    mapcalc=MapcalcStyle(),
    union_region=False,
    list_order=False,
    copies_by_position=False,
    temporal_type=None,
    last_of_equal_names=False,
):
    """Return the process chain of materialize() without running anything

    For vector maps, a registered map that reaches the result unchanged is
    planned with its own name and without module call.

    With selection no map is computed: a slot with an origin is registered
    unchanged, a retimed map (a slot that lost its origin but still holds a
    plain map reference) is copied with g.copy under <basename>_N numbered
    from 1, and any other content raises ValueError. This holds for every map
    type, so a selection copies retimed raster maps with g.copy as the classic
    algebra does, not with r.mapcalc.

    :param name: the space time dataset to create
    :param basename: the prefix of the map names, by default the name
    :param time_suffix: None for numbered maps, "gran" or "time" for a
        suffix from the start time (absolute time only)
    :param names: one finished map name per slot, used instead of basename and
        time_suffix; none may repeat
    :param mapcalc: how the r.mapcalc text is written, see MapcalcStyle
    :param union_region: compute every raster map in the union of the regions
        of its input maps, not only where a spatial relation was used
        (Series.spatial); 3D raster maps have no such option
    :param list_order: take the slots in the list order of the series
        (Series.listed()) for the names, the calls and the registration; the
        names then also number the slots in that order, and names are given
        in it. The default is the time order.
    :param copies_by_position: number the copies of a selection by the
        position of the slot among all result slots, counted from one, so a
        registered map before a copy takes a number it does not use; the
        default counts the copies only
    :param temporal_type: the temporal type of a result without slots, which
        has no maps to tell it; None means "absolute"
    :param last_of_equal_names: let the maps that get the same name from
        time_suffix overwrite each other: only the last of them (in the order
        of the slots) is planned, with its content and time stamp. Without it
        equal names are an error.
    :raises ValueError: for a map without time stamp, a name or basename with
        "@" (or a name with "." for a raster dataset), an unknown time_suffix,
        maps that would get the same name, names that do not match the
        slots, are illegal, equal an input map or are combined with selection
        or time_suffix, or a time_suffix combined with selection; with
        selection also for a result slot that is not a registered map or a
        copy that would get the name of a registered one
    """
    if selection and names is not None:
        # In a selection registered maps keep their names and only the copies
        # are counted, so there is no name per slot to give.
        msg = "names cannot be combined with selection"
        raise ValueError(msg)
    if selection and time_suffix is not None:
        # The copies are numbered; a suffix from the time would be ignored.
        msg = "time_suffix cannot be combined with selection"
        raise ValueError(msg)
    stds_type = STDS_TYPES[series.kind]
    _check_name("name", name, stds_type)
    if basename is not None:
        _check_name("basename", basename, stds_type)
    if series.timeless:
        msg = "A map without time stamp cannot be registered in a space time dataset"
        raise ValueError(msg)
    slots = series.listed() if list_order else series.slots
    result_type = series.temporal_type or temporal_type or "absolute"
    if selection:
        return _plan_selection(
            series,
            slots,
            name,
            basename or name,
            stds_type,
            copies_by_position,
            result_type,
        )
    backend = backend_for(series.kind)
    map_names = _map_names(
        series,
        basename or name,
        time_suffix,
        names=names,
        slots=slots,
        repeatable=last_of_equal_names,
    )
    last = {map_name: number for number, map_name in enumerate(map_names)}
    maps = []
    remove = []
    for number, (slot, map_name) in enumerate(zip(slots, map_names, strict=True)):
        if last[map_name] != number:
            continue
        if backend.registers_origins and slot.origin is not None:
            # The registered map itself goes into the result.
            maps.append(PlannedMap(slot.origin, slot.extent, ()))
            continue
        calls, temporaries = backend.plan(
            slot.content,
            map_name,
            spatial=series.spatial or union_region,
            style=mapcalc,
        )
        maps.append(PlannedMap(map_name, slot.extent, tuple(calls)))
        remove.extend(temporaries)
    return ProcessChain(name, stds_type, result_type, tuple(maps), tuple(remove))


def _plan_selection(
    series, slots, name, basename, stds_type, copies_by_position, result_type
):
    """Plan a selection result: register unchanged maps, copy retimed ones

    A slot with an origin is the registered map itself. A slot whose origin
    was dropped by a temporal operator but still holds a plain map reference
    is a retimed map, copied with g.copy; the copies are numbered
    <basename>_1, _2, ..., as the classic t.select names them. Numbering runs
    over the copies only, so it does not depend on how many maps are
    registered unchanged. Any other content cannot be selected. With
    copies_by_position the copies are numbered by the position of their slot
    among all of slots, as the classic t.select numbers them.

    :raises ValueError: for a result slot that is not a registered map, e.g.
        an expression or a map read at a cell offset, and for a copy that
        would get the name of a map registered unchanged
    """
    digits = len(str(len(slots)))
    maps = []
    number = 0
    registered = {slot.origin for slot in slots if slot.origin}
    for position, slot in enumerate(slots, start=1):
        if slot.origin is not None:
            maps.append(PlannedMap(slot.origin, slot.extent, ()))
            continue
        if not isinstance(slot.content, MapRef) or slot.content.offset:
            # describe() starts a sentence; here it follows a semicolon.
            what = describe(slot.content)
            msg = (
                "t.select selects and retimes maps, it computes none; "
                f"{what[0].lower()}{what[1:]} cannot be selected. Use "
                "t.rast.algebra, t.rast3d.algebra or t.vect.algebra to compute maps"
            )
            raise ValueError(msg)
        number = position if copies_by_position else number + 1
        map_name = create_numeric_suffix(basename, number, f"%0{digits}")
        if _replaces(map_name, registered):
            msg = f"The copy <{map_name}> has the name of a map in the result"
            raise ValueError(msg)
        call = ModuleCall(
            "g.copy", {ELEMENTS[series.kind]: (slot.content.ident, map_name)}
        )
        maps.append(PlannedMap(map_name, slot.extent, (call,)))
    return ProcessChain(name, stds_type, result_type, tuple(maps), ())


def _kind(chain):
    return KINDS_OF_STDS[chain.stds_type]


def _check_absent_classic(chain, mapset, dbif, with_dataset):
    """Stop before anything is computed if a result exists, in the order and
    with the words of the parser classes

    They look at the result maps first, and only at the files of the maps
    (not at a row of the temporal database), then at the dataset. The
    parser classes find the dataset only after the maps are computed; this
    check is made before, as the one of the core, so that nothing is lost.
    A dry run of the parser classes never looks at the dataset (measured
    2026-10-16 with an existing dataset and no existing map: the dry run
    passes, the run stops), so with_dataset is False there.

    :raises FatalError: if a result map or, with_dataset, the dataset exists
    """
    for planned in chain.maps:
        if not planned.calls:
            continue
        map_ = MAP_CLASSES[_kind(chain)](f"{planned.name}@{mapset}")
        if map_.map_exists():
            raise FatalError(
                _(
                    "Error maps with basename {name} exist. "
                    "Use --o flag to overwrite existing file"
                ).format(name=map_.get_id())
            )
    if not with_dataset:
        return
    dataset = dataset_factory(chain.stds_type, f"{chain.name}@{mapset}")
    if dataset.is_in_db(dbif):
        raise FatalError(
            _(
                "Space time {type} dataset <{name}> is already in the database. "
                "Use the overwrite flag."
            ).format(
                type=dataset.get_new_map_instance(None).get_type(), name=chain.name
            )
        )


def _check_absent(chain, mapset, dbif, classic=False, dry_run=False):
    """Stop before anything is computed if a result exists

    classic selects the check of _check_absent_classic(), which depends on
    dry_run; the check of the core does not.

    :raises FatalError: if the dataset or a result map exists
    """
    if classic:
        _check_absent_classic(chain, mapset, dbif, not dry_run)
        return
    dataset = dataset_factory(chain.stds_type, f"{chain.name}@{mapset}")
    if dataset.is_in_db(dbif):
        raise FatalError(
            _("Space time dataset <{name}> exists. Use the overwrite flag.").format(
                name=dataset.get_id()
            )
        )
    for planned in chain.maps:
        if not planned.calls:
            # A registered map that goes into the result unchanged exists by
            # nature.
            continue
        map_ = MAP_CLASSES[_kind(chain)](f"{planned.name}@{mapset}")
        # A row can outlive its map, e.g. after g.remove.
        if map_.map_exists() or map_.is_in_db(dbif):
            raise FatalError(
                _("Map <{name}> exists. Use the overwrite flag.").format(
                    name=map_.get_id()
                )
            )


def check_absent(chain, *, classic=False):
    """Stop if the dataset or a result map of a process chain exists

    materialize() does this check itself when not overwriting; a dry run
    calls it to fail where the run would fail.

    :param classic: look at the result maps first and report in the words of
        the parser classes, see materialize(); like the dry run of the parser
        classes, do not look at the dataset
    :raises FatalError: if the dataset or a result map exists
    """
    dbif, connection_state_changed = init_dbif(None)
    try:
        _check_absent(chain, get_current_mapset(), dbif, classic, dry_run=True)
    finally:
        if connection_state_changed:
            dbif.close()


def _module(call, overwrite):
    parameters = call.parameters
    if call.inputs:
        # The r.series input file is written now, at run time, not when the
        # chain was planned, so that a dry run stays free of side effects
        # while the run matches the classic module call (a file, with -z past
        # the open file limit). The file is not removed here: g.tempfile puts
        # it into the temporary directory of the session, which GRASS cleans
        # up, and the classic aggregation leaves its file the same way.
        filename = gs.tempfile(True)
        with open(filename, "w") as handle:
            handle.write("\n".join(call.inputs) + "\n")
        parameters = {**call.parameters, "file": filename}
    # quiet is set here and not among the parameters of the call, so that
    # plan() and the debug output show the calls as before. Without it the
    # progress of v.overlay drowned the warnings: measured 2026-10-13 in
    # grass --tmp-project XY, t.vect.algebra "C = A & B" over three map pairs
    # wrote 108 lines to stderr, the classic algebra 23.
    module = Module(call.name, run_=False, quiet=True, **parameters)
    module.flags["overwrite"].value = overwrite
    return module


def _overlay_inputs_usable(call, produced, mapset, result):
    """Tell whether v.overlay can run on its inputs for the map result

    v.overlay fails on inputs without areas (measured 2026-10-13 in grass
    --tmp-project XY: "No auto features found" for an empty map, "Invalid
    feature type" for a map of points). An input of the expression without
    areas is an error of the user. An intermediate map without areas comes
    from an overlay whose inputs do not meet; the result map is then empty
    and dropped, as in the classic algebra.

    :raises FatalError: for a missing input, and for an input of the
        expression without areas
    """
    for name in (call.parameters["ainput"], call.parameters["binput"]):
        ident = name if "@" in name else f"{name}@{mapset}"
        map_ = VectorDataset(ident)
        # Also for an intermediate map: v.overlay writes its output even
        # when it is empty (checked 2026-10-13 in grass --tmp-project XY with
        # two squares apart: exit 0, an output map with 0 primitives), so a
        # missing one is a fault, and the result map must not disappear
        # without a message.
        if not map_.map_exists():
            raise FatalError(_("Vector map <{name}> not found").format(name=ident))
        map_.load()
        if not map_.metadata.get_number_of_areas():
            if name not in produced:
                raise FatalError(
                    _("Vector map <{name}> has no areas, v.overlay needs areas").format(
                        name=ident
                    )
                )
            get_tgis_message_interface().warning(
                _(
                    "Result map <{result}> is left out: intermediate map <{name}> "
                    "has no areas"
                ).format(result=result, name=ident)
            )
            return False
    return True


def _run_vector(chain, overwrite):
    """Compute vector maps one call after another, checking the inputs of
    each overlay first"""
    mapset = get_current_mapset()
    msgr = get_tgis_message_interface()
    # Only the temporary maps are intermediate. A result map that is a
    # registered map taken over unchanged is still an input of the
    # expression, and can be the input of an overlay in another slot.
    produced = set(chain.remove)
    dropped = []
    total = _count_computed(chain)
    done = 0
    for planned in chain.maps:
        if not planned.calls:
            continue
        for call in planned.calls:
            if call.name == "v.overlay" and not _overlay_inputs_usable(
                call, produced, mapset, planned.name
            ):
                dropped.append(planned.name)
                break
            _module(call, overwrite).run()
        done += 1
        msgr.percent(done, total, 1)
    return dropped


def _count_computed(chain):
    """The number of result maps that need module calls"""
    return sum(1 for planned in chain.maps if planned.calls)


def _run(chain, overwrite, nprocs):
    """Compute the maps, in parallel for nprocs > 1; the calls of one map run
    in order

    The progress counts the maps handed to the queue when running in
    parallel, as the classic aggregation did, because a finished process is
    not reported back.

    :return: the names of the maps that were dropped before they were
        computed
    """
    if _kind(chain) == "vector":
        return _run_vector(chain, overwrite)
    msgr = get_tgis_message_interface()
    total = _count_computed(chain)
    done = 0
    if int(nprocs) == 1:
        # No queue and no forked process: both are only needed to overlap
        # calls.
        for planned in chain.maps:
            if not planned.calls:
                continue
            for call in planned.calls:
                _module(call, overwrite).run()
            done += 1
            msgr.percent(done, total, 1)
        return []
    queue = ParallelModuleQueue(nprocs=int(nprocs))
    for planned in chain.maps:
        if not planned.calls:
            continue
        modules = [_module(call, overwrite) for call in planned.calls]
        queue.put(modules[0] if len(modules) == 1 else MultiModule(modules, sync=False))
        done += 1
        msgr.percent(done, total, 1)
    queue.wait()
    return []


def _set_time(map_, extent):
    if extent.unit is None:
        map_.set_absolute_time(extent.start, extent.end)
    else:
        map_.set_relative_time(extent.start, extent.end, extent.unit)


def _store(map_, overwrite, dbif):
    """Insert the map into the temporal database or update it"""
    if not map_.is_in_db(dbif):
        map_.insert(dbif)
        return
    if not overwrite:
        raise FatalError(
            _(
                "Map <{name}> exists in the temporal database. Use the overwrite flag."
            ).format(name=map_.get_map_id())
        )
    stored = type(map_)(map_.get_id())
    stored.select(dbif)
    if stored.get_temporal_type() == map_.get_temporal_type():
        map_.update_all(dbif)
        return
    # update_all() sets the new type in the base table, but its UPDATE of the
    # time table of the new type matches no row, so the map gets no time
    # while the row of the old type stays behind (measured 2026-10-11 with
    # t.rast.algebra, see _store_new_map() in temporal_algebra.py). delete()
    # runs on the stored copy because it resets the object, which would
    # discard the time of map_.
    stored.delete(dbif)
    map_.insert(dbif)


# Names per g.remove call, so that the list of arguments of the process stays
# small however many maps a series has; the same chunk size as t.rast.algebra.
_REMOVE_CHUNK = 100


def _remove(names, kind):
    for start in range(0, len(names), _REMOVE_CHUNK):
        chunk = names[start : start + _REMOVE_CHUNK]
        Module(
            "g.remove", flags="f", type=ELEMENTS[kind], name=",".join(chunk), quiet=True
        )


def _is_empty(map_, kind):
    """Tell whether a computed map holds nothing: no valid cell, or no
    feature for a vector map"""
    if kind == "vector":
        return not map_.metadata.get_number_of_primitives()
    return map_.metadata.get_min() is None and map_.metadata.get_max() is None


def _forget(ident, kind, dbif):
    """Delete a map from the temporal database, which also unregisters it
    from the datasets"""
    MAP_CLASSES[kind](ident).delete(dbif)


def materialize(
    series,
    name,
    *,
    basename=None,
    overwrite=False,
    register_null=False,
    nprocs=1,
    time_suffix=None,
    selection=False,
    names=None,
    mapcalc=MapcalcStyle(),
    union_region=False,
    list_order=False,
    copies_by_position=False,
    temporal_type=None,
    last_of_equal_names=False,
    classic_absence_check=False,
    keep_empty_vector_maps=False,
    vector_dataset_if_empty=True,
):
    """Compute the maps of a series and register them in a new space time
    dataset

    Needs a GRASS session and a temporal database. Maps without any valid
    cell are removed and not registered unless register_null is True; if
    that leaves no map, the dataset stays empty and a warning says so. Their
    entries in the temporal database are deleted as well.
    Result maps registered with the other temporal type are replaced when
    overwriting.

    Vector maps are computed one call after another; a registered vector map
    that reaches the result unchanged is registered, not copied, and never
    removed.

    With selection no map is computed: registered maps reach the result
    unchanged and retimed maps are copied with g.copy (see plan()).

    With names the result maps get the given names, one per slot (see plan()).

    mapcalc, union_region, list_order, copies_by_position, temporal_type and
    last_of_equal_names are options of plan(). The others change what is done with the maps:

    - classic_absence_check looks for existing result maps before the dataset
      and reports in the words of the parser classes, see check_absent();
    - keep_empty_vector_maps registers a computed vector map that has no
      primitives, as if register_null were set for vector maps;
    - vector_dataset_if_empty=False creates no dataset and gives no warning
      for a vector result that has no map, either because the series has no
      slot or because every overlay was dropped for an input without areas.
      Nothing is checked or written then, and the result is None.

    Callers that need exceptions instead of a process exit for unforeseen
    database errors call ``tgis.init(raise_fatal_error=True)``.

    :raises FatalError: if the dataset or a result map exists and overwrite
        is False; nothing is computed then
    :raises ValueError: as plan(), or for nprocs other than 1 with vector
        maps
    :return: the space time dataset, or None for a vector result without maps
        if vector_dataset_if_empty is False
    """
    if series.kind == "vector" and int(nprocs) != 1:
        msg = (
            "Vector maps are computed one call after another, because each "
            f"overlay checks its inputs first; nprocs must be 1, got {nprocs}"
        )
        raise ValueError(msg)
    chain = plan(
        series,
        name,
        basename=basename,
        time_suffix=time_suffix,
        selection=selection,
        names=names,
        mapcalc=mapcalc,
        union_region=union_region,
        list_order=list_order,
        copies_by_position=copies_by_position,
        temporal_type=temporal_type,
        last_of_equal_names=last_of_equal_names,
    )
    no_dataset = series.kind == "vector" and not vector_dataset_if_empty
    if no_dataset and not chain.maps:
        return None
    mapset = get_current_mapset()
    dbif, connection_state_changed = init_dbif(None)
    try:
        if not overwrite:
            _check_absent(chain, mapset, dbif, classic_absence_check)
        try:
            dropped = _run(chain, overwrite, nprocs)
        finally:
            # Also when a call fails part-way: its temporary maps would
            # otherwise stay in the mapset. g.remove ignores names that were
            # never written.
            _remove(chain.remove, _kind(chain))
        if no_dataset and len(dropped) == len(chain.maps):
            for planned in chain.maps:
                # An earlier run may have registered a map of this name.
                _forget(f"{planned.name}@{mapset}", _kind(chain), dbif)
            return None
        dataset = open_new_stds(
            name,
            chain.stds_type,
            chain.temporal_type,
            name,
            name,
            "mean",
            dbif,
            overwrite=overwrite,
        )
        empty = []
        keep_empty = register_null or (
            keep_empty_vector_maps and _kind(chain) == "vector"
        )
        for planned in chain.maps:
            if planned.name in dropped:
                empty.append(planned.name)
                # An earlier run may have registered a map of this name.
                _forget(f"{planned.name}@{mapset}", _kind(chain), dbif)
                continue
            if not planned.calls:
                map_ = MAP_CLASSES[_kind(chain)](planned.name)
                map_.select(dbif)
                if not map_.is_in_db(dbif, mapset=mapset):
                    # A map of another mapset is only in the database of its
                    # own mapset, but register_map() needs it in this one; it
                    # is referenced there, not copied, as t.register does.
                    map_.insert(dbif)
                if not dataset.register_map(map_, dbif):
                    # register_map() refuses a map that is registered already,
                    # e.g. one taken over unchanged in two slots.
                    get_tgis_message_interface().warning(
                        _(
                            "Unable to register map <{map}> in space time "
                            "dataset <{name}>"
                        ).format(map=map_.get_id(), name=dataset.get_id())
                    )
                continue
            map_ = MAP_CLASSES[_kind(chain)](f"{planned.name}@{mapset}")
            if not map_.load():
                raise FatalError(
                    _("Map <{name}> was not computed").format(name=map_.get_id())
                )
            _set_time(map_, planned.extent)
            if not keep_empty and _is_empty(map_, _kind(chain)):
                empty.append(planned.name)
                # An earlier run may have registered a map of this name.
                _forget(map_.get_id(), _kind(chain), dbif)
                continue
            _store(map_, overwrite, dbif)
            dataset.register_map(map_, dbif)
        dataset.update_from_registered_maps(dbif)
        if len(empty) == len(chain.maps):
            get_tgis_message_interface().warning(
                _(
                    "Empty result space time dataset. No map has been registered "
                    "in {name}"
                ).format(name=name)
            )
        _remove(empty, _kind(chain))
    finally:
        if connection_state_changed:
            dbif.close()
    return dataset
