"""Operations on the time stamps of a series"""

import datetime
from dataclasses import replace

from grass.temporal.abstract_space_time_dataset import AbstractSpaceTimeDataset
from grass.temporal.datetime_math import (
    check_datetime_string,
    datetime_after_steps,
    decrement_datetime_by_string,
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
        replace(slot, content=Const(_time_value(slot.extent, name)), origin=None)
        for slot in series.slots
    )
    return Series(slots, series.kind, "scalar", series.spatial, series.order)


class TimeStepError(ValueError):
    """An increment of tshift() or buff_t() of the wrong kind for the time type

    A profile that follows the classic algebra reports it as a SyntaxError.
    """


class TimeFunctionError(ValueError):
    """A temporal function that a map has no value for

    function is the name of the function and ident the identifier of the map,
    None for a map without origin. A profile that follows the classic algebra
    reports it as a FatalError.
    """

    def __init__(self, message, function, ident=None):
        super().__init__(message)
        self.function = function
        self.ident = ident


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
            raise TimeStepError(msg)
        if int(float(increment)) != float(increment):
            msg = f"Relative time is changed by whole units, not {increment!r}"
            raise ValueError(msg)
        return int(float(increment))
    if _is_number(increment):
        msg = f'Absolute time needs a time unit, e.g. "{increment} days"'
        raise TimeStepError(msg)
    if not check_granularity_string(increment, "absolute"):
        msg = f'Cannot read {increment!r} as a time step, use e.g. "1 day"'
        raise TimeStepError(msg)
    return increment


def retime(series, *, shift=None, buffer=None, snap=False):
    """Shift, buffer or snap the time stamps; the contents stay

    :param shift: e.g. "1 day" for absolute time, a number of the time unit
        for relative time
    :param buffer: the same, taken off the start and added to the end. A
        negative buffer shrinks the maps and raises ValueError for a map
        that would keep no time (see _shrink())
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
    if buffer is not None and str(buffer).strip().startswith("-"):
        return _shrink(series, buffer)
    maps = [as_map(slot.extent) for slot in series.slots]
    if shift is not None:
        maps = AbstractSpaceTimeDataset.shift_map_list(maps, shift)
    elif buffer is not None:
        for map_ in maps:
            map_.temporal_buffer(buffer)
    else:
        maps = AbstractSpaceTimeDataset.snap_map_list(maps)
    slots = tuple(
        # Keep the origin where the new time stamp equals the old one, e.g.
        # tsnap of gapless maps: the slot is then still the registered map
        # unchanged, which is what Slot.origin documents. A selection
        # registers such a map instead of copying it.
        Slot(
            extent_of(map_),
            slot.content,
            slot.space,
            slot.origin if extent_of(map_) == slot.extent else None,
            # A snapped list is sorted, as the classic tsnap() sorts it.
            None if snap else slot.rank,
        )
        for map_, slot in zip(maps, series.slots, strict=True)
    )
    return replace(series, slots=slots)


def _shrink(series, buffer):
    """Take a negative buffer off both ends of every slot

    temporal_buffer() cannot be used: for an end before the start it prints
    an error and keeps the old time stamp, for an end equal to the start it
    stores an instant (set_absolute_time() and set_relative_time(); measured
    2026-10-14 with t.rast.algebra -c, the classic algebra silently leaves
    such maps unchanged or makes instants of them). Both would register a
    map whose time is not the buffered one, so the new extent is computed
    here and a slot that keeps no interval (end <= start, GRASS intervals
    need end > start) raises ValueError. The new extent is computed before it
    is compared, because a month has no fixed length.
    """
    slots = []
    for position, slot in enumerate(series.slots, 1):
        extent = slot.extent
        name = f"map <{slot.origin}>" if slot.origin else f"slot {position}"
        if extent.end is None:
            msg = (
                f"Buffering {name} at {extent.start} by {buffer} leaves no time: "
                "an instant has no duration to shrink"
            )
            raise ValueError(msg)
        shown = f"{name} [{extent.start}, {extent.end}] by {buffer}"
        if extent.unit is None:
            size = str(buffer).strip().lstrip("-").strip()
            try:
                start = increment_datetime_by_string(extent.start, size)
                end = decrement_datetime_by_string(extent.end, size)
            except ValueError as error:
                # E.g. a month or year step past the year 9999.
                msg = f"Buffering {shown} failed: {error}"
                raise ValueError(msg) from error
        else:
            start = extent.start - buffer
            end = extent.end + buffer
        if end <= start:
            msg = f"Buffering {shown} leaves no time"
            raise ValueError(msg)
        # The new stamp differs from the old one, so no slot is still the
        # registered map and the origin goes.
        slots.append(
            Slot(
                Extent(start, end, extent.unit),
                slot.content,
                slot.space,
                rank=slot.rank,
            )
        )
    return replace(series, slots=tuple(slots))


def neighbour(series, offset, *, space="own"):
    """Each slot with the content of the slot offset positions away

    Slots without such a neighbour are left out, as A[1] and A[-1] of the
    algebra do.

    :param space: the spatial extent of a slot: its own ("own") or that of the
        neighbour whose content it takes ("neighbour")
    :raises ValueError: for another space
    """
    check_series(series)
    check_int(offset, "offset")
    if space not in ("own", "neighbour"):
        msg = f"space must be one of own, neighbour, got {space!r}"
        raise ValueError(msg)
    slots = []
    for index, slot in enumerate(series.slots):
        other = index + offset
        if 0 <= other < len(series.slots):
            neighbour_slot = series.slots[other]
            slots.append(
                Slot(
                    slot.extent,
                    neighbour_slot.content,
                    slot.space if space == "own" else neighbour_slot.space,
                )
            )
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
        # Each start counts from the first one, so that a cut to the end of a
        # shorter month does not carry over: from 31 January the granules
        # start on 28 February and 31 March, not on 28 February and 28 March.
        anchor = current
        count = 0
        while current < stop:
            count += 1
            following = datetime_after_steps(anchor, granularity, count)
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
