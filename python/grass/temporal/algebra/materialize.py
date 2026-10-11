"""Plan and materialize series: module calls, map names and registration"""

from dataclasses import dataclass

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
from grass.temporal.space_time_datasets import RasterDataset
from grass.temporal.temporal_granularity import compute_absolute_time_granularity

from ._adapters import as_map
from .backends import backend_for

STDS_TYPES = {"raster": "strds", "raster3d": "str3ds", "vector": "stvds"}
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


def _map_names(series, basename, time_suffix):
    """The names of the result maps: basename with a number from 0 as
    t.rast.algebra does, or for absolute time with a suffix from the start
    time

    :raises ValueError: for an unknown time_suffix, or if several maps would
        get the same name
    """
    if time_suffix not in TIME_SUFFIXES:
        msg = f"time_suffix must be None, 'gran' or 'time', got {time_suffix!r}"
        raise ValueError(msg)
    absolute = series.temporal_type == "absolute"
    granularity = None
    if absolute and time_suffix == "gran":
        granularity = compute_absolute_time_granularity(
            [as_map(slot.extent) for slot in series.slots]
        )
    digits = len(str(len(series.slots)))
    names = []
    for number, slot in enumerate(series.slots):
        if granularity:
            suffix = create_suffix_from_datetime(slot.extent.start, granularity)
            names.append(f"{basename}_{suffix}")
        elif absolute and time_suffix == "time":
            names.append(f"{basename}_{create_time_suffix(as_map(slot.extent))}")
        else:
            names.append(create_numeric_suffix(basename, number, f"%0{digits}"))
    if len(set(names)) != len(names):
        msg = (
            "Several maps would get the same name; maps of equal time need the "
            "numeric suffix"
        )
        raise ValueError(msg)
    return names


def plan(series, name, *, basename=None, time_suffix=None):
    """Return the process chain of materialize() without running anything

    :param name: the space time dataset to create
    :param basename: the prefix of the map names, by default the name
    :param time_suffix: None for numbered maps, "gran" or "time" for a
        suffix from the start time (absolute time only)
    :raises ValueError: for a map without time stamp, an unknown
        time_suffix, or maps that would get the same name
    """
    if series.timeless:
        msg = "A map without time stamp cannot be registered in a space time dataset"
        raise ValueError(msg)
    backend = backend_for(series.kind)
    names = _map_names(series, basename or name, time_suffix)
    maps = []
    remove = []
    for slot, map_name in zip(series.slots, names, strict=True):
        calls, temporaries = backend.plan(
            slot.content, map_name, spatial=series.spatial
        )
        maps.append(PlannedMap(map_name, slot.extent, tuple(calls)))
        remove.extend(temporaries)
    return ProcessChain(
        name,
        STDS_TYPES[series.kind],
        series.temporal_type or "absolute",
        tuple(maps),
        tuple(remove),
    )


def _check_absent(chain, mapset, dbif):
    """Stop before anything is computed if a result exists

    :raises FatalError: if the dataset or a result map exists
    """
    dataset = dataset_factory(chain.stds_type, f"{chain.name}@{mapset}")
    if dataset.is_in_db(dbif):
        raise FatalError(
            _("Space time dataset <{name}> exists. Use the overwrite flag.").format(
                name=dataset.get_id()
            )
        )
    for planned in chain.maps:
        map_ = RasterDataset(f"{planned.name}@{mapset}")
        if map_.map_exists():
            raise FatalError(
                _("Map <{name}> exists. Use the overwrite flag.").format(
                    name=map_.get_id()
                )
            )


def _module(call, overwrite):
    module = Module(call.name, run_=False, **call.parameters)
    module.flags["overwrite"].value = overwrite
    return module


def _run(chain, overwrite, nprocs):
    """Compute the maps in parallel; the calls of one map run in order"""
    queue = ParallelModuleQueue(nprocs=int(nprocs))
    for planned in chain.maps:
        modules = [_module(call, overwrite) for call in planned.calls]
        queue.put(modules[0] if len(modules) == 1 else MultiModule(modules, sync=False))
    queue.wait()


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
    stored = RasterDataset(map_.get_id())
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


def _remove(names):
    if names:
        Module("g.remove", flags="f", type="raster", name=",".join(names), quiet=True)


def materialize(
    series,
    name,
    *,
    basename=None,
    overwrite=False,
    register_null=False,
    nprocs=1,
    time_suffix=None,
):
    """Compute the maps of a series and register them in a new space time
    dataset

    Needs a GRASS session and a temporal database. Maps without any valid
    cell are removed and not registered unless register_null is True; if
    that leaves no map, the dataset stays empty and a warning says so.
    Result maps registered with the other temporal type are replaced when
    overwriting.

    :raises FatalError: if the dataset or a result map exists and overwrite
        is False; nothing is computed then
    :raises ValueError: as plan()
    :return: the space time dataset
    """
    chain = plan(series, name, basename=basename, time_suffix=time_suffix)
    mapset = get_current_mapset()
    dbif, connection_state_changed = init_dbif(None)
    try:
        if not overwrite:
            _check_absent(chain, mapset, dbif)
        _run(chain, overwrite, nprocs)
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
        for planned in chain.maps:
            map_ = RasterDataset(f"{planned.name}@{mapset}")
            if not map_.load():
                raise FatalError(
                    _("Map <{name}> was not computed").format(name=map_.get_id())
                )
            _set_time(map_, planned.extent)
            if (
                not register_null
                and map_.metadata.get_min() is None
                and map_.metadata.get_max() is None
            ):
                empty.append(planned.name)
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
        _remove([*chain.remove, *empty])
    finally:
        if connection_state_changed:
            dbif.close()
    return dataset
