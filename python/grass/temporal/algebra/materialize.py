"""Plan and materialize series: module calls, map names and registration

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import inspect
from dataclasses import dataclass, replace

import grass.script as gs
from grass.exceptions import CalledModuleError, FatalError
from grass.pygrass.modules import Module, MultiModule, ParallelModuleQueue
from grass.temporal.datetime_math import (
    create_numeric_suffix,
    create_suffix_from_datetime,
    create_time_suffix,
)
from grass.temporal.db import connection
from grass.temporal.factory import dataset_factory
from grass.temporal.open_stds import open_new_stds
from grass.temporal.space_time_datasets import VectorDataset
from grass.temporal.state import get_current_mapset, get_tgis_message_interface
from grass.temporal.temporal_granularity import compute_absolute_time_granularity

from .adapters import as_map
from .backends import ModuleCall, backend_for, describe
from .content import Call, MapRef, SeriesAggregate, SeriesReduce
from .maptypes import ELEMENTS, KINDS_OF_STDS, MAP_CLASSES, STDS_TYPES

TIME_SUFFIXES = (None, "gran", "time")


@dataclass(frozen=True)
class PlannedMap:
    """A result map: its name, its time stamp and the calls that compute it

    source is the identifier of the map that the calls copy unchanged, None
    for a map they compute otherwise and for a registered map without calls.
    """

    name: str
    extent: object
    calls: tuple
    source: str | None = None


@dataclass(frozen=True)
class ProcessChain:
    """What materialize() would do, without doing it

    renumber is True when the computed maps are numbered and materialize()
    numbers only the maps it registers; False keeps the planned names.
    """

    name: str
    stds_type: str
    temporal_type: str
    maps: tuple
    remove: tuple
    renumber: bool = False

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


def _map_names(series, basename, time_suffix, names=None, digits=None):
    """The names of the result maps, one per slot of series

    With names the caller gives one name per slot verbatim, which the
    aggregation tools use for their own numbering (count from one, with an
    offset and a gap for a dropped empty granule). Without names the maps are
    numbered from zero as t.rast.algebra does, or for absolute time get a
    suffix from the start time.

    digits is the number of digits of a numbered name, None takes as many as
    the number of slots has.

    :raises ValueError: for an unknown time_suffix, a names length other than
        the number of slots, names that would collide, are illegal or equal an
        input map, or names together with time_suffix
    """
    return _naming(series, basename, time_suffix, names, digits)[0]


def _naming(series, basename, time_suffix, names, digits):
    """The names of _map_names() and whether they are numbers after the basename"""
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
        return list(names), False
    if time_suffix not in TIME_SUFFIXES:
        msg = f"time_suffix must be None, 'gran' or 'time', got {time_suffix!r}"
        raise ValueError(msg)
    absolute = series.temporal_type == "absolute"
    granularity = None
    if absolute and time_suffix == "gran":
        granularity = compute_absolute_time_granularity(
            [as_map(slot.extent) for slot in slots]
        )
    if digits is None:
        digits = len(str(len(slots)))
    numbered = False
    names = []
    for number, slot in enumerate(slots):
        if granularity:
            suffix = create_suffix_from_datetime(slot.extent.start, granularity)
            names.append(f"{basename}_{suffix}")
        elif absolute and time_suffix == "time":
            names.append(f"{basename}_{create_time_suffix(as_map(slot.extent))}")
        else:
            numbered = True
            names.append(create_numeric_suffix(basename, number, f"%0{digits}"))
    if len(set(names)) != len(names):
        msg = (
            "Several maps would get the same name; maps of equal time need the "
            "numeric suffix"
        )
        raise ValueError(msg)
    return names, numbered


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
    digits=None,
):
    """Return the process chain of materialize() without running anything

    For vector maps, a registered map that reaches the result unchanged is
    planned with its own name and without module call.

    The maps are planned in the time order of the slots. A raster map is
    computed in the union of the regions of its inputs where a spatial
    relation related them (Series.spatial), in the current region otherwise.
    A result without slots has absolute time. Numbered maps are renumbered by
    materialize() so that a map left out, because it has no valid cell or was
    dropped, gives its name to the next computed map; a registered vector map
    that reaches the result unchanged keeps its name. The planned names are
    those of a run that leaves out no map.

    With selection no map is computed: a slot with an origin is registered
    unchanged, a retimed map (a slot that lost its origin but still holds a
    plain map reference) is copied with g.copy under <basename>_N numbered
    from 1, and any other content raises ValueError. This holds for every map
    type, so a selection copies retimed raster maps with g.copy as the classic
    algebra does, not with r.mapcalc.

    :param series: the Series whose slots become maps; its kind decides the
        type of the dataset and of the maps
    :param name: the space time dataset to create, without a mapset; it must
        not contain "@", nor "." for a raster dataset
    :param basename: the prefix of the map names, by default the name
    :param selection: plan a selection, see above; False plans module calls
        for every slot, and only a vector map that reaches the result
        unchanged is registered as it is
    :param time_suffix: None for numbered maps, "gran" or "time" for a
        suffix from the start time (absolute time only)
    :param names: one finished map name per slot, used instead of basename and
        time_suffix; none may repeat
    :param digits: the number of digits of a numbered map name, as the
        suffix "num%NN" of the tools gives it; None takes as many digits as
        the number of slots has
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
    result_type = series.temporal_type or "absolute"
    if selection:
        return _plan_selection(series, name, basename or name, stds_type, result_type)
    backend = backend_for(series.kind)
    map_names, numbered = _naming(series, basename or name, time_suffix, names, digits)
    maps = []
    remove = []
    for slot, map_name in zip(series.slots, map_names, strict=True):
        if backend.registers_origins and slot.origin is not None:
            # The registered map itself goes into the result.
            maps.append(PlannedMap(slot.origin, slot.extent, ()))
            continue
        calls, temporaries = backend.plan(
            slot.content, map_name, spatial=series.spatial
        )
        maps.append(
            PlannedMap(map_name, slot.extent, tuple(calls), _copied_map(slot.content))
        )
        remove.extend(temporaries)
    return ProcessChain(
        name, stds_type, result_type, tuple(maps), tuple(remove), numbered
    )


def _copied_map(content):
    """The identifier of the map that content copies unchanged, or None"""
    if isinstance(content, MapRef) and not content.offset:
        return content.ident
    return None


def _plan_selection(series, name, basename, stds_type, result_type):
    """Plan a selection result: register unchanged maps, copy retimed ones

    A slot with an origin is the registered map itself. A slot whose origin
    was dropped by a temporal operator but still holds a plain map reference
    is a retimed map, copied with g.copy; the copies are numbered
    <basename>_1, _2, ..., as the classic t.select names them. Numbering runs
    over the copies only, so it does not depend on how many maps are
    registered unchanged. Any other content cannot be selected.

    :raises ValueError: for a result slot that is not a registered map, e.g.
        an expression or a map read at a cell offset, and for a copy that
        would get the name of a map registered unchanged
    """
    slots = series.slots
    digits = len(str(len(slots)))
    maps = []
    number = 0
    registered = {slot.origin for slot in slots if slot.origin}
    for slot in slots:
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
        number += 1
        map_name = create_numeric_suffix(basename, number, f"%0{digits}")
        if _replaces(map_name, registered):
            msg = f"The copy <{map_name}> has the name of a map in the result"
            raise ValueError(msg)
        call = ModuleCall(
            "g.copy", {ELEMENTS[series.kind]: (slot.content.ident, map_name)}
        )
        maps.append(PlannedMap(map_name, slot.extent, (call,), slot.content.ident))
    return ProcessChain(name, stds_type, result_type, tuple(maps), ())


def _kind(chain):
    return KINDS_OF_STDS[chain.stds_type]


def _check_absent(chain, mapset, dbif):
    """Stop before anything is computed if a result exists

    :raises grass.exceptions.FatalError: if the dataset or a result map exists
    """
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


def check_absent(chain):
    """Stop if the dataset or a result map of a process chain exists

    materialize() does this check itself when not overwriting; a dry run
    calls it to fail where the run would fail.

    :param chain: the ProcessChain that plan() made, whose result dataset and
        map names are looked up in the current mapset
    :raises grass.exceptions.FatalError: if the dataset or a result map exists
    """
    with connection(None) as dbif:
        _check_absent(chain, get_current_mapset(), dbif)


def _module(call, overwrite):
    parameters = call.parameters
    if call.inputs:
        # The r.series input file is written now, at run time, not when the
        # chain was planned, so that a dry run stays free of side effects.
        # A file and not input=, because one argument is limited in size (see
        # RasterBackend); an aggregation so calls r.series as
        # aggregate_raster_maps() in aggregation.py does (a file, with -z past
        # the open file limit). The file is not removed here: g.tempfile puts
        # it into the temporary directory of the session, which GRASS cleans
        # up, and aggregate_raster_maps() leaves its file the same way.
        filename = gs.tempfile(True)
        with open(filename, "w") as handle:
            handle.write("\n".join(call.inputs) + "\n")
        parameters = {**call.parameters, "file": filename}
    # quiet is set here and not among the parameters of the call, so that the
    # process chain of plan() and the debug output carry no switch that only
    # changes the messages of a module. Without it the progress of v.overlay
    # drowned the warnings: measured 2026-10-13 in grass --tmp-project XY,
    # t.vect.algebra "C = A & B" over three map pairs wrote 108 lines to
    # stderr, the classic algebra 23.
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

    :raises grass.exceptions.FatalError: for a missing input, and for an input of the
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
    """Compute vector maps one call after another

    The inputs of each overlay are checked first.
    """
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
    """Compute the maps, in parallel for nprocs > 1

    The calls of one map run in order. The progress counts the maps handed to
    the queue when running in parallel, because a finished process is not
    reported back.

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
    # t.rast.algebra, see _store_new_map() in temporal_algebra.py of the
    # reference). delete() runs on the stored copy because it resets the
    # object, which would discard the time of map_.
    stored.delete(dbif)
    map_.insert(dbif)


# Names per g.remove call, so that the list of arguments of the process stays
# small however many maps a series has; the chunk size of the classic algebra.
_REMOVE_CHUNK = 100


def _remove(names, kind):
    for start in range(0, len(names), _REMOVE_CHUNK):
        chunk = names[start : start + _REMOVE_CHUNK]
        Module(
            "g.remove", flags="f", type=ELEMENTS[kind], name=",".join(chunk), quiet=True
        )


def _is_empty(map_, kind):
    """Tell whether a computed map holds nothing

    That is no valid cell, or no feature for a vector map.
    """
    if kind == "vector":
        return not map_.metadata.get_number_of_primitives()
    return map_.metadata.get_min() is None and map_.metadata.get_max() is None


def _emptied_by_region(planned, kind):
    """Tell whether an empty computed map copies a map that has data

    Only raster and 3D raster maps are meant. A computed map can be empty by
    right, as if(A > 1000, A) of small values is. A copy of a map with data is
    empty only because r.mapcalc and r3.mapcalc compute it in the current
    region, whose extent (or resolution) can miss the data of the map.
    g.copy, which copies a vector map and any map of a selection, takes the
    whole map, and its copy is never empty for this reason.
    """
    if planned.source is None or kind == "vector":
        return False
    source = MAP_CLASSES[kind](planned.source)
    return source.load() and not _is_empty(source, kind)


def _forget(ident, kind, dbif):
    """Delete a map from the temporal database

    That also unregisters it from the datasets.
    """
    MAP_CLASSES[kind](ident).delete(dbif)


def _register_results(chain, dataset, mapset, dbif, keep_empty, dropped, overwrite):
    """Register the maps of chain in dataset and return the empty ones

    The result holds the names of the empty maps. A map in dropped was not
    computed, and an empty map is not registered unless keep_empty is set;
    their old entries in the temporal database are deleted and the maps are
    removed. A map that the chain computes no call
    for is registered as it is, also from another mapset. With renumber the
    registered computed maps are renamed, see _renumbered().
    """
    kind = _kind(chain)
    empty = []
    # (planned map, loaded map); the loaded map is None for a map without
    # calls, which is registered as it is.
    kept = []
    for planned in chain.maps:
        if planned.name in dropped:
            empty.append(planned.name)
            continue
        if not planned.calls:
            kept.append((planned, None))
            continue
        map_ = MAP_CLASSES[kind](f"{planned.name}@{mapset}")
        if not map_.load():
            raise FatalError(
                _("Map <{name}> was not computed").format(name=map_.get_id())
            )
        if not keep_empty and _is_empty(map_, kind):
            if _emptied_by_region(planned, kind):
                get_tgis_message_interface().warning(
                    _(
                        "Map <{map}> is empty in the current region and is "
                        "not registered; it copies <{source}>, which has data "
                        "outside the region. Set the region with g.region, or "
                        "register empty maps with -n where the tool offers it."
                    ).format(map=map_.get_id(), source=planned.source)
                )
            empty.append(planned.name)
            continue
        kept.append((planned, map_))
    for name in empty:
        # An earlier run may have registered a map of this name.
        _forget(f"{name}@{mapset}", kind, dbif)
    # Removed before the renaming below, which can give a kept map the name
    # of an empty one.
    _remove(empty, kind)
    if chain.renumber and empty:
        kept = _renumbered(chain, kept, mapset, dbif)
    for planned, map_ in kept:
        if map_ is None:
            map_ = MAP_CLASSES[kind](planned.name)
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
                        "Unable to register map <{map}> in space time dataset <{name}>"
                    ).format(map=map_.get_id(), name=dataset.get_id())
                )
            continue
        _set_time(map_, planned.extent)
        _store(map_, overwrite, dbif)
        dataset.register_map(map_, dbif)
    return empty


def _renumbered(chain, kept, mapset, dbif):
    """Give the computed maps of kept the planned names, in order

    The maps left out then leave no gap. Only the names of maps with calls are
    given, which the check for existing maps has seen; a map registered
    unchanged keeps its name, also when it looks like a number of the result,
    and takes none. A kept map
    takes a name of an earlier or the same position, which is that of a map
    left out, removed before, or of a kept map renamed before it.

    :param kept: (planned map, loaded map) pairs as in _register_results()
    :return: kept with the new names and the maps loaded under them
    """
    kind = _kind(chain)
    names = iter([planned.name for planned in chain.maps if planned.calls])
    renamed = []
    for planned, map_ in kept:
        if map_ is not None:
            name = next(names)
            if name != planned.name:
                Module("g.rename", quiet=True, **{ELEMENTS[kind]: (planned.name, name)})
                # An earlier run may have registered a map of the old name.
                _forget(f"{planned.name}@{mapset}", kind, dbif)
                planned = replace(planned, name=name)
                map_ = MAP_CLASSES[kind](f"{name}@{mapset}")
                map_.load()
        renamed.append((planned, map_))
    return renamed


def _planned(series, name, chain, options):
    """The chain to run: the given one, or the one plan() makes of options

    A given chain was planned with options of its own, so an option given
    here as well, which differs from the default of materialize(), could only
    contradict it.
    """
    if chain is None:
        return plan(series, name, **options)
    # The signature is the one source of the defaults; a copy here would have
    # to follow it. It is that of materialize(), not of plan(), because an
    # option the caller left out has the default of materialize() (the two
    # agree, compared 2026-10-30 with inspect.signature()).
    defaults = inspect.signature(materialize).parameters
    given = [key for key, value in options.items() if value != defaults[key].default]
    if given:
        msg = f"A planned chain takes no options of plan(), got {', '.join(given)}"
        raise ValueError(msg)
    stds_type = STDS_TYPES[series.kind]
    if (chain.name, chain.stds_type) != (name, stds_type):
        msg = (
            f"The chain plans the {chain.stds_type} <{chain.name}>, not the "
            f"{stds_type} <{name}>"
        )
        raise ValueError(msg)
    return chain


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
    digits=None,
    chain: ProcessChain | None = None,
):
    """Compute the maps of a series and register them in a new space time dataset

    Needs a GRASS session and a temporal database. Maps without any valid
    cell are removed and not registered unless register_null is True; if
    that leaves no map, the dataset stays empty and a warning says so. Their
    entries in the temporal database are deleted as well, and the numbered
    maps after them are renamed to close the gap (see plan()). A warning
    names each such map that copies a raster or 3D raster map with data,
    which the current region missed.
    Result maps registered with the other temporal type are replaced when
    overwriting.

    Vector maps are computed one call after another; a registered vector map
    that reaches the result unchanged is registered, not copied, and never
    removed.

    With selection no map is computed: registered maps reach the result
    unchanged and retimed maps are copied with g.copy (see plan()).

    With names the result maps get the given names, one per slot (see plan()).

    Callers that need exceptions instead of a process exit for unforeseen
    database errors call ``tgis.init(raise_fatal_error=True)``.

    :param series: the Series whose slots become maps; its kind decides the
        type of the dataset and of the maps
    :param name: the new space time dataset, without a mapset (the current
        mapset is meant); it must not contain "@", nor "." for a raster dataset
    :param basename: the prefix of the map names, by default the name; see
        plan()
    :param overwrite: replace result maps and a dataset that exist, and pass
        --overwrite on to every module call. If False, an existing result map
        or dataset stops the run before any map is computed.
    :param register_null: also register maps without a valid cell or, for a
        vector result, without primitives; by default they are removed, with
        their entries in the temporal database
    :param nprocs: the number of module processes that run at once; 1 runs the
        calls one after another in this process, and a vector result needs 1
    :param time_suffix: None for numbered maps, "gran" or "time" for a name
        from the start time of the slot (absolute time only); see plan()
    :param selection: register the registered maps unchanged and copy retimed
        ones, without computing a map; see plan()
    :param names: one finished map name per slot instead of basename and
        time_suffix; see plan()
    :param digits: the number of digits of a numbered map name, None for as
        many as the number of slots needs; see plan()
    :param chain: the chain that plan() made of series and name, which is run
        instead of planning again; the options of plan() are then not given
    :raises grass.exceptions.FatalError: if the dataset or a result map exists
        and overwrite is False; nothing is computed then. Also if a module
        fails; the message names the module and its return code
    :raises ValueError: as plan(), for nprocs other than 1 with vector
        maps, or for a chain together with options of plan(), or with
        another name or map type
    :return: the space time dataset
    """
    if series.kind == "vector" and int(nprocs) != 1:
        msg = (
            "Vector maps are computed one call after another, because each "
            f"overlay checks its inputs first; nprocs must be 1, got {nprocs}"
        )
        raise ValueError(msg)
    chain = _planned(
        series,
        name,
        chain,
        {
            "basename": basename,
            "time_suffix": time_suffix,
            "selection": selection,
            "names": names,
            "digits": digits,
        },
    )
    mapset = get_current_mapset()
    with connection(None) as dbif:
        if not overwrite:
            _check_absent(chain, mapset, dbif)
        try:
            dropped = _run(chain, overwrite, nprocs)
        except CalledModuleError as error:
            # The tools report a FatalError as a message; a CalledModuleError
            # would reach the user as a traceback. The module has written its
            # own error output already.
            raise FatalError(
                _(
                    "Module <{module}> failed with return code {code}, see the "
                    "error output above"
                ).format(module=error.module, code=error.returncode)
            ) from error
        finally:
            # Also when a call fails part-way: its temporary maps would
            # otherwise stay in the mapset. g.remove ignores names that were
            # never written.
            _remove(chain.remove, _kind(chain))
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
        empty = _register_results(
            chain, dataset, mapset, dbif, register_null, dropped, overwrite
        )
        dataset.update_from_registered_maps(dbif)
        if len(empty) == len(chain.maps):
            get_tgis_message_interface().warning(
                _(
                    "Empty result space time dataset. No map has been registered "
                    "in {name}"
                ).format(name=name)
            )
        return dataset
