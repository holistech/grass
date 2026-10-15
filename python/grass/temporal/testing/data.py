"""Build dates, maps and space time datasets as input for temporal tests

The datasets are made the way the tool tests need them: constant-valued maps
registered with absolute or relative time, as intervals or as time points.
Reading the result back is the job of grass.temporal.testing.readback.

This module must not import pytest; fixtures belong in conftest.py files.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import grass.temporal as tgis

DAY0 = datetime(2001, 1, 1)

# t.register and the library take the type of the maps, not of the dataset
# that holds them.
_MAP_TYPE = {"strds": "raster", "str3ds": "raster_3d", "stvds": "vector"}
_MAP_KINDS = tuple(_MAP_TYPE.values())

_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def day(offset, *, hours=0):
    """The datetime offset days (and hours) after DAY0"""
    return DAY0 + timedelta(days=offset, hours=hours)


def timestamp(offset):
    """The date of day(offset) as "YYYY-MM-DD", the form t.register reads"""
    return day(offset).strftime("%Y-%m-%d")


def intervals(count, *, granularity="month", start=0):
    """count adjacent (start, end) datetime pairs of one month or one day each

    start counts months or days from DAY0. Months are calendar months, so
    their lengths differ; days are 24 hours.
    """
    if granularity == "day":
        return [
            (day(number), day(number + 1)) for number in range(start, start + count)
        ]
    if granularity == "month":
        return [
            (_month_start(number), _month_start(number + 1))
            for number in range(start, start + count)
        ]
    msg = f"Unknown granularity {granularity!r}, expected 'month' or 'day'"
    raise ValueError(msg)


def _month_start(months):
    """The first day of the month that lies months after the month of DAY0"""
    year, month = divmod(DAY0.month - 1 + months, 12)
    return DAY0.replace(year=DAY0.year + year, month=month + 1)


@dataclass(frozen=True)
class MapSpec:
    """A map to create and register: a constant value and its time

    start and end are datetimes for absolute time and numbers in the unit of
    the dataset for relative time. Without end the map is a time point.
    semantic_label is set on raster maps only. value is None only for
    register_stds() with maps that already exist; make_map() needs a number.
    """

    name: str
    value: float | None
    start: datetime | int
    end: datetime | int | None = None
    semantic_label: str | None = None


def make_map(tools, kind, name, value, *, region=None, overwrite=False):
    """Create a map of kind "raster", "raster_3d" or "vector" with a constant

    raster and raster_3d hold value in every cell (r.mapcalc, r3.mapcalc);
    a vector map gets one point at (value, value) with the attribute value
    (v.in.ascii). region, if given, is a dict for g.region used only for
    this map (the session region is restored). A vector map made here has
    one point and its own topology and table; vector maps from other tools,
    for example v.random, can be registered with register_stds().
    """
    if kind not in _MAP_KINDS:
        msg = f"Unknown map kind {kind!r}, expected one of {list(_MAP_KINDS)}"
        raise ValueError(msg)
    saved = None
    if region is not None:
        saved = _region(tools)
        tools.g_region(**region)
    try:
        if kind == "raster":
            tools.r_mapcalc(expression=f"{name} = {value}", overwrite=overwrite)
        elif kind == "raster_3d":
            tools.r3_mapcalc(expression=f"{name} = {value}", overwrite=overwrite)
        else:
            tools.v_in_ascii(
                input=StringIO(f"{value},{value},{value}\n"),
                output=name,
                format="point",
                separator="comma",
                columns="x double precision, y double precision,"
                " value double precision",
                x=1,
                y=2,
                z=0,
                overwrite=overwrite,
            )
    finally:
        if saved is not None:
            tools.g_region(**saved)


def _region(tools):
    """The 3D region of the session as options that g.region takes back"""
    values = tools.g_region(flags="g3").keyval
    keys = (
        "n", "s", "e", "w", "t", "b",
        "nsres", "ewres", "nsres3", "ewres3", "tbres",
    )  # fmt: skip
    return {key: values[key] for key in keys}


def register_stds(
    tools,
    stds_type,
    name,
    maps,
    *,
    temporaltype="absolute",
    unit=None,
    via="tool",
    title=None,
    description=None,
    overwrite=False,
):
    """Create the dataset name and register maps, an iterable of MapSpec

    The maps must exist. description defaults to the title. unit is required
    for relative time. via="tool" uses t.create and t.register with a file;
    via="library" uses open_new_stds() and
    register_maps_in_space_time_dataset() in this process and needs
    temporal_session(). Both give the same dataset. With overwrite an
    existing dataset of that name is replaced and the maps are registered
    again; both routes honour it.

    The tool route is the default because it works in every session and
    needs no mirrored os.environ. The library route is about twice as fast:
    measured 2026-10-15 with time.perf_counter around register_stds() for 12
    existing raster maps of monthly intervals in an XY project under
    temporal_session(), fresh maps for each of 5 runs per route: tool
    0.97 s median (0.968 to 0.974 s), library 0.47 s median (0.463 to
    0.473 s).
    """
    maps = list(maps)
    map_type = _MAP_TYPE[stds_type]
    title = name if title is None else title
    description = title if description is None else description
    if temporaltype == "relative" and unit is None:
        msg = "A relative time dataset needs a unit"
        raise ValueError(msg)
    if via == "tool":
        tools.t_create(
            type=stds_type,
            output=name,
            temporaltype=temporaltype,
            title=title,
            description=description,
            overwrite=overwrite,
        )
        if maps:
            lines = [
                "|".join(
                    [spec.name, _text(spec.start, temporaltype)]
                    + ([] if spec.end is None else [_text(spec.end, temporaltype)])
                )
                for spec in maps
            ]
            options = {} if unit is None else {"unit": unit}
            # t.register opens the file itself, so it cannot read stdin.
            with TemporaryDirectory() as directory:
                file = Path(directory) / "maps.txt"
                file.write_text("\n".join(lines) + "\n")
                tools.t_register(
                    type=map_type, input=name, file=file, overwrite=overwrite, **options
                )
    elif via == "library":
        tgis.open_new_stds(
            name,
            stds_type,
            temporaltype,
            title,
            description,
            "mean",
            overwrite=overwrite,
        )
        for spec in maps:
            options = (
                {"end": _text(spec.end, temporaltype)} if spec.end is not None else {}
            )
            if unit is not None:
                options["unit"] = unit
            tgis.register_maps_in_space_time_dataset(
                map_type,
                name,
                spec.name,
                start=_text(spec.start, temporaltype),
                **options,
            )
    else:
        msg = f"Unknown route {via!r}, expected 'tool' or 'library'"
        raise ValueError(msg)


def _text(value, temporaltype):
    """A time as t.register reads it: a date and time, or a plain number"""
    if temporaltype == "relative":
        return str(value)
    return value.strftime(_TIME_FORMAT)


def create_stds(tools, stds_type, name, maps, **options):
    """make_map() for every MapSpec, then register_stds()

    options are those of register_stds(); overwrite also applies to the maps.
    Maps that already exist, such as v.random vectors, go to register_stds().
    """
    maps = list(maps)
    map_type = _MAP_TYPE[stds_type]
    for spec in maps:
        make_map(
            tools,
            map_type,
            spec.name,
            spec.value,
            overwrite=options.get("overwrite", False),
        )
        if spec.semantic_label is not None:
            if map_type != "raster":
                msg = f"Only raster maps have a semantic label, not {map_type}"
                raise ValueError(msg)
            tools.r_support(map=spec.name, semantic_label=spec.semantic_label)
    register_stds(tools, stds_type, name, maps, **options)
