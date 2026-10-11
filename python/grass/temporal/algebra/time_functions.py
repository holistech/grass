"""Operations on the time stamps of a series"""

import datetime
from dataclasses import replace

from grass.temporal.abstract_space_time_dataset import AbstractSpaceTimeDataset
from grass.temporal.datetime_math import (
    check_datetime_string,
    increment_datetime_by_string,
    time_delta_to_relative_time,
)
from grass.temporal.temporal_granularity import check_granularity_string

from ._adapters import as_map, extent_of
from ._checks import check_int, check_series
from .content import NULL, Const
from .series import Extent, Series, Slot

TIME_FIELDS = {
    "doy": lambda timestamp: timestamp.timetuple().tm_yday,
    "dow": lambda timestamp: timestamp.isoweekday(),
    "year": lambda timestamp: timestamp.year,
    "month": lambda timestamp: timestamp.month,
    "week": lambda timestamp: timestamp.isocalendar()[1],
    "day": lambda timestamp: timestamp.day,
    "hour": lambda timestamp: timestamp.hour,
    "minute": lambda timestamp: timestamp.minute,
    "second": lambda timestamp: timestamp.second,
    "date": lambda timestamp: timestamp.date(),
    "datetime": lambda timestamp: timestamp,
    "time": lambda timestamp: timestamp.time(),
}
TIMEVARS = (
    "td",
    *(f"{side}_{field}" for side in ("start", "end") for field in TIME_FIELDS),
)


def _time_value(extent, name):
    if name == "td":
        if extent.end is None:
            return None
        if extent.unit is None:
            return time_delta_to_relative_time(extent.end - extent.start)
        return extent.end - extent.start
    if extent.unit is not None:
        return None
    side, field = name.split("_", 1)
    timestamp = extent.start if side == "start" else extent.end
    return None if timestamp is None else TIME_FIELDS[field](timestamp)


def timevar(series, name):
    """The scalar series of a temporal variable, e.g. "td" or "start_doy"

    td is the length of the interval, in days for absolute time and in the
    time unit for relative time. Values that do not exist are null: the
    calendar variables for relative time, td and the end variables for an
    instant.
    """
    check_series(series)
    if name not in TIMEVARS:
        msg = f"Unknown temporal variable {name!r}, use one of {', '.join(TIMEVARS)}"
        raise ValueError(msg)
    if series.timeless:
        msg = "A map without time stamp has no temporal variables"
        raise ValueError(msg)
    slots = tuple(
        Slot(slot.extent, Const(_time_value(slot.extent, name)), slot.space)
        for slot in series.slots
    )
    return Series(slots, series.kind, "scalar", series.spatial)


def _is_number(increment):
    return isinstance(increment, (int, float)) or (
        isinstance(increment, str) and increment.strip().lstrip("-").isdigit()
    )


def _checked_increment(series, increment):
    """Return the increment in the form the map objects take

    The map objects fail late and obscurely for increments they cannot read,
    so they are checked here. Measured 2026-10-11 with a throw-away script
    that called shift_map_list() and temporal_buffer() on map objects made
    by as_map(), in a plain Python process without session:

    - "a while" on absolute time: shift_map_list() returns None,
      temporal_buffer() raises an AttributeError (missing message interface);
    - the number 5 on absolute time: temporal_buffer() raises an
      AttributeError;
    - "1 day" on relative time: shift_map_list() returns None;
    - 0.5 on relative time: shift_map_list() leaves [2, 5] unchanged and
      temporal_buffer() gives [1, 5], so the fraction is truncated.
    """
    if series.temporal_type == "relative":
        if not _is_number(increment):
            msg = f"Relative time is changed by a number of its unit, not {increment!r}"
            raise ValueError(msg)
        if int(float(increment)) != float(increment):
            msg = f"Relative time is changed by whole units, not {increment!r}"
            raise ValueError(msg)
        return int(float(increment))
    if _is_number(increment):
        msg = f'Absolute time needs a time unit, e.g. "{increment} days"'
        raise ValueError(msg)
    if not check_granularity_string(increment, "absolute"):
        msg = f'Cannot read {increment!r} as a time step, use e.g. "1 day"'
        raise ValueError(msg)
    return increment


def retime(series, *, shift=None, buffer=None, snap=False):
    """Shift, buffer or snap the time stamps; the contents stay

    :param shift: e.g. "1 day" for absolute time, a number of the time unit
        for relative time
    :param buffer: the same, taken off the start and added to the end; it
        must not be negative
    :param snap: set the end of each map to the start of the next one
    """
    check_series(series)
    if [shift is not None, buffer is not None, bool(snap)].count(True) != 1:
        msg = "retime() needs exactly one of shift, buffer and snap"
        raise ValueError(msg)
    # Without slots the temporal type is unknown, so no increment can be checked.
    if not series.slots:
        return series
    if series.timeless:
        msg = "A map without time stamp cannot be moved in time"
        raise ValueError(msg)
    if shift is not None:
        shift = _checked_increment(series, shift)
    if buffer is not None:
        buffer = _checked_increment(series, buffer)
        # temporal_buffer() would let the end fall before the start.
        if str(buffer).strip().startswith("-"):
            msg = f"The buffer must not be negative, got {buffer!r}"
            raise ValueError(msg)
    maps = [as_map(slot.extent) for slot in series.slots]
    if shift is not None:
        maps = AbstractSpaceTimeDataset.shift_map_list(maps, shift)
    elif buffer is not None:
        for map_ in maps:
            map_.temporal_buffer(buffer)
    else:
        maps = AbstractSpaceTimeDataset.snap_map_list(maps)
    slots = tuple(
        Slot(extent_of(map_), slot.content, slot.space)
        for map_, slot in zip(maps, series.slots, strict=True)
    )
    return replace(series, slots=slots)


def neighbour(series, offset):
    """Each slot with the content of the slot offset positions away

    Slots without such a neighbour are left out, as A[1] and A[-1] of the
    algebra do.
    """
    check_series(series)
    check_int(offset, "offset")
    slots = []
    for index, slot in enumerate(series.slots):
        other = index + offset
        if 0 <= other < len(series.slots):
            slots.append(Slot(slot.extent, series.slots[other].content, slot.space))
    return replace(series, slots=tuple(slots))


def _datetime(value):
    if isinstance(value, datetime.datetime):
        return value
    # check_datetime_string() reports an unreadable string as its return
    # value; string_to_datetime() sends it to a message interface that
    # exists only in a session and raises an AttributeError without one.
    result = check_datetime_string(value) if isinstance(value, str) else None
    if not isinstance(result, datetime.datetime):
        msg = f"Cannot read {value!r} as date and time"
        raise ValueError(msg)
    return result


def _whole_number(value, what):
    # Relative time is integral, and as_map() rejects a fractional stamp.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = f"The {what} of relative granules must be a whole number, not {value!r}"
        raise ValueError(msg)
    if int(value) != value:
        msg = f"The {what} of relative granules must be a whole number, not {value!r}"
        raise ValueError(msg)
    return int(value)


def granules(
    start, end, granularity, *, temporal_type="absolute", unit=None, kind="raster"
):
    """Empty slots on a regular grid from start to end, targets for gather()

    For absolute time start and end are datetime objects or strings such as
    "2001-01-01", and granularity is e.g. "1 month". For relative time they
    are whole numbers and the granularity is a whole number of the unit. The
    last granule may end after end: granules are added while their start is
    before end, so the last one covers end.
    """
    slots = []
    if temporal_type == "absolute":
        current, stop = _datetime(start), _datetime(end)
        if not check_granularity_string(granularity, "absolute"):
            msg = f'Cannot read {granularity!r} as a time step, use e.g. "1 day"'
            raise ValueError(msg)
        if increment_datetime_by_string(current, granularity) <= current:
            msg = f"The granularity {granularity!r} must be positive"
            raise ValueError(msg)
        while current < stop:
            following = increment_datetime_by_string(current, granularity)
            slots.append(Slot(Extent(current, following), NULL))
            current = following
    elif temporal_type == "relative":
        if unit is None:
            msg = "Relative granules need a unit"
            raise ValueError(msg)
        current = _whole_number(start, "start")
        stop = _whole_number(end, "end")
        step = _whole_number(granularity, "granularity")
        if step <= 0:
            msg = f"The granularity {granularity!r} must be positive"
            raise ValueError(msg)
        while current < stop:
            slots.append(Slot(Extent(current, current + step, unit), NULL))
            current += step
    else:
        msg = f"temporal_type must be absolute or relative, got {temporal_type!r}"
        raise ValueError(msg)
    return Series(tuple(slots), kind)
