"""Plan and materialize series: module calls, map names and registration"""

from dataclasses import dataclass

from grass.temporal.datetime_math import (
    create_numeric_suffix,
    create_suffix_from_datetime,
    create_time_suffix,
)
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
