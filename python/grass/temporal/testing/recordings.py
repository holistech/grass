"""Recorded results of the extent, granularity, date and topology functions

A refactor of the library must not change what these functions compute. This
module records their results on fixed, complete grids of inputs and compares
a later run with the record, so a change shows with the name of the case.
The record is proof, not a test oracle: it holds what the code computed on the
day it was recorded (the date and the commit are in the commit message that
added the files), including results that are surprising.

Records are named ``spatial_extent``, ``temporal_extent``, ``granularity``,
``datetime_math`` and ``topology``. Each is a gzip file ``<name>.json.gz`` of a
JSON object that maps the name of a case to its result. A result is the
``repr()`` of the value, or ``"raise <Class>: <text>"`` for an exception. A
case groups the calls that differ in one argument (for example one box against
every other box), which keeps the number of cases and the size of the files
small; the result of such a case is the ``repr()`` of the list of the results.

The grids are explicit and ordered: nothing depends on the order of a set or
on the clock, and nothing is random. The cases need ``grass.temporal`` to be
initialised in a session, because the topology builder uses the R-tree of the
C library and the objects use the messenger. The error mode of the messenger
does not change a result: fatal errors are recorded as ``raise FatalError`` or
``raise SystemExit`` and a case that ends in one is not part of the grids.

To record again (only with the permission of the maintainer, after a fix of a
bug that changes a result, never to make a refactor pass), run in a session::

    grass --tmp-project XY --exec python3 -m grass.temporal.testing.recordings \
        record <directory>

``compare <directory>`` prints the differences. The database image
(``database_write.sql`` and ``database_read.json.gz``) is recorded outside a
session with ``python3 -m grass.temporal.testing.recordings image <directory>``.
The module does not import pytest.
"""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import io
import itertools
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

NAMES = (
    "spatial_extent",
    "temporal_extent",
    "granularity",
    "datetime_math",
    "topology",
)

# The longest result text that a message of a difference shows
_SHOWN = 300


def outcome(function: Callable, *args) -> str:
    """Return repr() of the result of function(*args), or the exception"""
    try:
        return repr(function(*args))
    except (Exception, SystemExit) as error:
        return f"raise {type(error).__name__}: {error}"


def _file(name: str, path: Path) -> Path:
    return Path(path) / f"{name}.json.gz"


def _run(cases: Iterable[tuple[str, Callable[[], object]]]) -> dict[str, str]:
    results: dict[str, str] = {}
    for case, function in cases:
        if case in results:
            msg = f"Case {case!r} is listed twice"
            raise ValueError(msg)
        results[case] = outcome(function)
    return results


def record(
    name: str, cases: Iterable[tuple[str, Callable[[], object]]], path: Path
) -> None:
    """Run the cases and write their results to <path>/<name>.json.gz

    The file is written with a fixed time stamp, so recording twice gives the
    same bytes.
    """
    results = _run(cases)
    text = json.dumps(results, sort_keys=True, separators=(",", ":"))
    with (
        _file(name, path).open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, compresslevel=9) as packed,
    ):
        packed.write(text.encode("utf-8"))


def load(name: str, path: Path) -> dict[str, str]:
    """Return the recorded results"""
    with gzip.open(_file(name, path), "rt", encoding="utf-8") as packed:
        return json.load(packed)


def _shown(text: str) -> str:
    return text if len(text) <= _SHOWN else text[:_SHOWN] + "..."


def compare(
    name: str, cases: Iterable[tuple[str, Callable[[], object]]], path: Path
) -> list[str]:
    """Run the cases and list their differences to the record

    :return: one text per case that differs, is missing in the record or is
             missing in the cases; the list is empty if all is equal
    """
    recorded = load(name, path)
    results = _run(cases)
    differences = []
    for case, result in results.items():
        if case not in recorded:
            differences.append(f"{case}: not recorded, got {_shown(result)}")
        elif recorded[case] != result:
            differences.append(
                f"{case}: recorded {_shown(recorded[case])}, got {_shown(result)}"
            )
    differences.extend(
        f"{case}: recorded but not run" for case in recorded if case not in results
    )
    return differences


###############################################################################
# Spatial extents


def _described(value):
    """Make the result of a spatial or temporal method comparable"""
    from grass.temporal.spatial_extent import SpatialExtent  # noqa: PLC0415
    from grass.temporal.temporal_extent import TemporalExtent  # noqa: PLC0415

    if isinstance(value, SpatialExtent):
        return ("SpatialExtent", value.get_spatial_extent_as_tuple(), value.proj)
    if isinstance(value, TemporalExtent):
        return (
            type(value).__name__,
            value.get_start_time(),
            value.get_end_time(),
            getattr(value, "unit", None),
        )
    return value


def _described_outcome(function, *args) -> str:
    try:
        return repr(_described(function(*args)))
    except (Exception, SystemExit) as error:
        return f"raise {type(error).__name__}: {error}"


# Methods that take the whole box into account, and the same in two dimensions
_SPATIAL_3D = (
    "overlapping",
    "is_in",
    "contain",
    "equivalent",
    "cover",
    "covered",
    "overlap",
    "meet",
    "disjoint",
    "spatial_relation",
    "intersect",
    "union",
    "disjoint_union",
)
_SPATIAL_2D = tuple(f"{name}_2d" for name in _SPATIAL_3D)

# The intervals of one axis. "all" holds every pair of bounds in {0, 1, 2, 3}
# in order, also the empty ones that start and end in the same place; "wide"
# leaves those out and is used where the product of three axes would be too big.
_ALL = tuple(itertools.combinations_with_replacement((0, 1, 2, 3), 2))
_WIDE = tuple(itertools.combinations((0, 1, 2, 3), 2))
# Longitudes around the date line, also with west east of east
_LONGITUDES = tuple(itertools.product((-180, -170, 170, 180, 190), repeat=2))


def _box(proj, x, y, z=None):
    from grass.temporal.spatial_extent import SpatialExtent  # noqa: PLC0415

    west, east = x
    south, north = y
    top = bottom = None
    if z is not None:
        bottom, top = z
    return SpatialExtent(
        north=north,
        south=south,
        east=east,
        west=west,
        top=top,
        bottom=bottom,
        proj=proj,
    )


def _spatial_grid(label, proj, xs, ys, zs):
    """One case for every method and every box A; B runs through all boxes"""
    zs = zs or (None,)
    boxes = [(x, y, z) for x in xs for y in ys for z in zs]
    methods = _SPATIAL_3D if zs != (None,) else _SPATIAL_2D
    for method in methods:
        for a in boxes:

            def run(method=method, a=a):
                results = []
                for b in boxes:
                    first = _box(proj, *a)
                    second = _box(proj, *b)
                    results.append(_described_outcome(getattr(first, method), second))
                return results

            yield f"{label}/{method}/A={a}", run


def spatial_extent_cases():
    """The cases of the record ``spatial_extent``"""
    # 2D: every pair of bounds on both axes, projection XY
    yield from _spatial_grid("xy2d", "XY", _ALL, _ALL, None)
    # 3D: five intervals per axis keep the product at 125 boxes
    five = ((0, 1), (0, 2), (1, 2), (1, 3), (2, 3))
    yield from _spatial_grid("xy3d", "XY", five, five, five)
    # Latitude and longitude with values over the date line
    yield from _spatial_grid("ll2d", "LL", _LONGITUDES, _WIDE[:3], None)
    yield from _spatial_grid("ll3d", "LL", _LONGITUDES[:10], ((0, 2),), _WIDE[:2])

    # Two projections cannot be compared
    for method in ("overlapping_2d", "spatial_relation_2d", "intersect_2d"):

        def mixed(method=method):
            return [
                _described_outcome(
                    getattr(_box("XY", (0, 2), (0, 2)), method),
                    _box("LL", (1, 3), (1, 3)),
                )
            ]

        yield f"mixed/{method}", mixed


###############################################################################
# Temporal extents

# An interval has a start and an end from {0, 1, 2, 3}, or a start only
_INTERVALS = (*_ALL, *((value, None) for value in (0, 1, 2, 3)))
_TEMPORAL = (
    "starts",
    "started",
    "finishes",
    "finished",
    "after",
    "before",
    "follows",
    "precedes",
    "during",
    "contains",
    "equal",
    "overlaps",
    "overlapped",
    "temporal_relation",
    "intersect",
    "union",
    "disjoint_union",
)
_START = datetime(2001, 1, 1)


def _extent(kind, interval):
    from grass.temporal import (  # noqa: PLC0415
        AbsoluteTemporalExtent,
        RelativeTemporalExtent,
    )

    start, end = interval
    if kind == "absolute":
        return AbsoluteTemporalExtent(
            start_time=_START + timedelta(days=start),
            end_time=None if end is None else _START + timedelta(days=end),
        )
    return RelativeTemporalExtent(start_time=start, end_time=end, unit="days")


def temporal_extent_cases():
    """The cases of the record ``temporal_extent``"""
    for kind in ("absolute", "relative"):
        for method in _TEMPORAL:
            for a in _INTERVALS:

                def run(kind=kind, method=method, a=a):
                    return [
                        _described_outcome(
                            getattr(_extent(kind, a), method), _extent(kind, b)
                        )
                        for b in _INTERVALS
                    ]

                yield f"{kind}/{method}/A={a}", run


###############################################################################
# Granularity

_GRANULARITIES = (
    "1 second",
    "30 seconds",
    "1 minute",
    "90 minutes",
    "1 hour",
    "12 hours",
    "1 day",
    "7 days",
    "1 month",
    "3 months",
    "1 year",
    "1 month, 1 day",
)
_RELATIVE = (1, 2, 3, 4, 6, 10, 12, 15, 30, 60)


def _subsets(items, largest):
    for size in range(largest + 1):
        yield from itertools.combinations(items, size)


def granularity_cases():
    """The cases of the record ``granularity``"""
    import grass.temporal as tgis  # noqa: PLC0415

    for subset in _subsets(_GRANULARITIES, 3):
        grans = list(subset)
        yield (
            f"common_absolute/{grans}",
            lambda grans=grans: (
                tgis.temporal_granularity.compute_common_absolute_time_granularity(
                    grans
                )
            ),
        )
        yield (
            f"common_absolute_simple/{grans}",
            lambda grans=grans: (
                tgis.temporal_granularity.compute_common_absolute_time_granularity_simple(
                    grans
                )
            ),
        )
    # Start dates move the common granule
    for grans, starts in (
        (["1 month", "1 month"], [datetime(2001, 1, 1), datetime(2001, 1, 15)]),
        (["1 day", "1 day"], [datetime(2001, 1, 1), datetime(2001, 1, 1, 12)]),
        (["1 year", "1 month"], [datetime(2001, 1, 1), datetime(2001, 7, 1)]),
        (["1 hour", "30 minutes"], [datetime(2001, 1, 1), datetime(2001, 1, 1, 0, 10)]),
    ):
        yield (
            f"common_absolute_starts/{grans}/{starts}",
            lambda grans=grans, starts=starts: (
                tgis.temporal_granularity.compute_common_absolute_time_granularity(
                    grans, starts
                )
            ),
        )
    for subset in _subsets(_RELATIVE, 3):
        grans = list(subset)
        yield (
            f"common_relative/{grans}",
            lambda grans=grans: (
                tgis.temporal_granularity.compute_common_relative_time_granularity(
                    grans
                )
            ),
        )
    for gran in (*_GRANULARITIES, "5 months", "0 days", "1 fortnight", "day", ""):
        yield (
            f"check_absolute/{gran}",
            lambda gran=gran: tgis.check_granularity_string(gran, "absolute"),
        )
        yield f"singular/{gran}", lambda gran=gran: tgis.gran_singular_unit(gran)
    for gran in (1, 2.5, "1", "1 day", "x", -1, 0):
        yield (
            f"check_relative/{gran!r}",
            lambda gran=gran: tgis.check_granularity_string(gran, "relative"),
        )
    for source, target in itertools.product(
        (*_GRANULARITIES[:11], "2 weeks", "x"),
        (
            "1 second",
            "1 minute",
            "1 hour",
            "1 day",
            "1 week",
            "1 month",
            "1 year",
            "days",
        ),
    ):
        yield (
            f"gran_to_gran/{source}/{target}",
            lambda source=source, target=target: [
                tgis.gran_to_gran(source, target),
                tgis.gran_to_gran(source, target, True),
            ],
        )
    yield from _granularity_of_maps_cases()


def _map(kind, index, start, end, unit="days"):
    import grass.temporal as tgis  # noqa: PLC0415

    new = tgis.RasterDataset(f"m{index}@PERMANENT")
    if kind == "absolute":
        new.set_absolute_time(
            _START + timedelta(days=start),
            None if end is None else _START + timedelta(days=end),
        )
    else:
        new.set_relative_time(start, end, unit)
    return new


# Series of maps whose granularity is computed
_MAP_SERIES = {
    "daily": ((0, 1), (1, 2), (2, 3), (3, 4)),
    "gap": ((0, 1), (1, 2), (4, 5)),
    "weekly": ((0, 7), (7, 14), (14, 21)),
    "points": ((0, None), (1, None), (2, None)),
    "mixed": ((0, 1), (1, 3), (3, 6)),
    "overlap": ((0, 2), (1, 3), (2, 4)),
    "one": ((0, 1),),
    "none": (),
    "duplicate": ((0, 1), (0, 1), (1, 2)),
    "unsorted": ((2, 3), (0, 1), (1, 2)),
}


def _granularity_of_maps_cases():
    import grass.temporal as tgis  # noqa: PLC0415

    for label, series in _MAP_SERIES.items():
        yield (
            f"maps_absolute/{label}",
            lambda series=series: tgis.compute_absolute_time_granularity(
                [_map("absolute", i, *item) for i, item in enumerate(series)]
            ),
        )
        yield (
            f"maps_relative/{label}",
            lambda series=series: tgis.compute_relative_time_granularity(
                [_map("relative", i, *item) for i, item in enumerate(series)]
            ),
        )


###############################################################################
# Date arithmetic


def _dates():
    """Days around the end of January and February in a leap and a common year"""
    for year in (2000, 2001):
        first = datetime(year, 1, 28)
        for day in range(36):
            yield first + timedelta(days=day)
    # Month ends, a day with a time and the borders of the year
    yield from (
        datetime(2001, 3, 31),
        datetime(2001, 4, 30),
        datetime(2001, 5, 31),
        datetime(2001, 12, 31),
        datetime(2001, 12, 31, 23, 59, 59),
        datetime(2001, 6, 15, 12, 30, 45),
        datetime(1999, 12, 31),
        datetime(2000, 12, 31),
    )


_STEPS = (
    "1 second",
    "59 seconds",
    "1 minute",
    "1 hour",
    "25 hours",
    "1 day",
    "1 week",
    "2 weeks",
    "1 month",
    "2 months",
    "12 months",
    "13 months",
    "1 year",
    "4 years",
    "1 month, 1 day",
    "1 year, 2 months",
    "0 days",
    "1 fortnight",
    "day",
)


def datetime_math_cases():
    """The cases of the record ``datetime_math``"""
    import grass.temporal as tgis  # noqa: PLC0415

    dates = list(_dates())
    for step in _STEPS:
        for mult in (1, 2, 3):
            yield (
                f"increment/{step}/{mult}",
                lambda step=step, mult=mult: [
                    outcome(tgis.increment_datetime_by_string, date, step, mult)
                    for date in dates
                ],
            )
        yield (
            f"decrement/{step}",
            lambda step=step: [
                outcome(tgis.datetime_math.decrement_datetime_by_string, date, step)
                for date in dates
            ],
        )
        for count in (0, 1, 2, 5, 13):
            yield (
                f"after_steps/{step}/{count}",
                lambda step=step, count=count: [
                    outcome(tgis.datetime_after_steps, date, step, count)
                    for date in dates
                ],
            )
    for gran in (*_GRANULARITIES, "1 fortnight"):
        yield (
            f"adjust/{gran}",
            lambda gran=gran: [
                outcome(tgis.adjust_datetime_to_granularity, date, gran)
                for date in dates
            ],
        )
    for start in dates:
        yield (
            f"delta/{start}",
            lambda start=start: [
                outcome(tgis.datetime_math.compute_datetime_delta, start, end)
                for end in dates
            ],
        )
    for cycle, offset in (
        ("1 month", None),
        ("1 month", "1 day"),
        ("1 week", "1 week"),
        ("1 day", "1 month"),
        ("1 year", None),
    ):
        for origin in (
            datetime(2001, 1, 31),
            datetime(2001, 1, 1),
            datetime(2000, 2, 29),
        ):
            yield (
                f"next_cycle/{cycle}/{offset}/{origin}",
                lambda cycle=cycle, offset=offset, origin=origin: [
                    outcome(
                        tgis.next_cycle, origin, number, origin, cycle, offset, True
                    )
                    for number in range(14)
                ],
            )
    for cycle, offset in ((5, 0), (5, 2), (1.5, 0.5)):
        yield (
            f"next_cycle_relative/{cycle}/{offset}",
            lambda cycle=cycle, offset=offset: [
                outcome(tgis.next_cycle, 0, number, 10, cycle, offset, False)
                for number in range(5)
            ],
        )
    yield from _datetime_conversion_cases(dates)


_TEXTS = (
    "2001-01-31",
    "2001-01-31 12:30:45",
    "2000-02-29 00:00:00",
    "2001-02-29",
    "2001-13-01",
    "2001-01-31 25:00:00",
    "2001-01-31T12:30:45",
    "2001-01-31 12:30:45+02:00",
    "2001-01-31 12:30:45.5",
    "31.01.2001",
    "0",
    "-1",
    "1 day",
    "",
    "x",
)
_MODIFIERS = (
    {"months": 1},
    {"months": -1},
    {"years": 1},
    {"years": 1, "months": 11},
    {"months": 23},
    {"weeks": 1, "days": 1},
    {"hours": 25, "minutes": 61, "seconds": 61},
    {"months": 1, "days": 1},
    {"years": -1},
    {},
)


def _datetime_conversion_cases(dates):
    """Modification, parsing and formatting of dates, suffixes and deltas"""
    import grass.temporal as tgis  # noqa: PLC0415
    from grass.temporal import datetime_math  # noqa: PLC0415

    for index, modifier in enumerate(_MODIFIERS):
        yield (
            f"modify/{index}/{modifier}",
            lambda modifier=modifier: [
                outcome(lambda date: datetime_math.modify_datetime(date, **modifier), d)
                for d in dates
            ],
        )
    for step in _STEPS:
        for mult, sign in ((1, 1), (2, -1), (0, 1)):
            yield (
                f"modify_by_string/{step}/{mult}/{sign}",
                lambda step=step, mult=mult, sign=sign: [
                    outcome(
                        datetime_math.modify_datetime_by_string, date, step, mult, sign
                    )
                    for date in dates
                ],
            )
    for text in _TEXTS:
        yield (
            f"string_to_datetime/{text}",
            lambda text=text: [
                outcome(tgis.string_to_datetime, text),
                outcome(datetime_math.check_datetime_string, text),
                outcome(datetime_math.check_datetime_string, text, False),
            ],
        )
    yield (
        "to_grass_string",
        lambda: [
            outcome(tgis.datetime_to_grass_datetime_string, date)
            for date in (*dates, None)
        ],
    )
    for gran in (*_GRANULARITIES, "1 fortnight"):
        yield (
            f"suffix_from_datetime/{gran}",
            lambda gran=gran: [
                outcome(datetime_math.create_suffix_from_datetime, date, gran)
                for date in dates
            ],
        )
    yield (
        "numeric_suffix",
        lambda: [
            outcome(datetime_math.create_numeric_suffix, base, count, zeros)
            for base in ("m", "")
            for count in (0, 1, 9, 10, 123)
            for zeros in ("%05d", "%d", "%02d", "")
        ],
    )
    yield (
        "relative_conversions",
        lambda: (
            [
                outcome(function, timedelta(**kwargs))
                for function in (
                    datetime_math.time_delta_to_relative_time,
                    datetime_math.time_delta_to_relative_time_seconds,
                )
                for kwargs in (
                    {},
                    {"days": 1},
                    {"days": 1, "seconds": 1, "microseconds": 250000},
                    {"days": -2},
                    {"hours": 36},
                )
            ]
        ),
    )
    yield (
        "gcd",
        lambda: (
            [
                outcome(tgis.temporal_granularity.gcd, a, b)
                for a in (0, 1, 6, 12, 35)
                for b in (0, 1, 4, 18)
            ]
            + [
                outcome(tgis.temporal_granularity.gcd_list, items)
                for items in ([], [4], [4, 6], [12, 18, 8])
            ]
        ),
    )


###############################################################################
# Topology

_TEMPORAL_GETTERS = (
    "get_equal",
    "get_starts",
    "get_started",
    "get_finishes",
    "get_finished",
    "get_overlaps",
    "get_overlapped",
    "get_follows",
    "get_precedes",
    "get_during",
    "get_contains",
)
_SPATIAL_GETTERS = (
    "get_equivalent",
    "get_overlap",
    "get_in",
    "get_contain",
    "get_meet",
    "get_cover",
    "get_covered",
)

# Each map is (id, start, end, (west, east), (south, north), (bottom, top)) in
# days and map units. The series contain what the builder must tell apart:
# every temporal relation, equal extents, touching boxes and duplicate ids.
_TOPOLOGY_SERIES = {
    "identical": [("a", 0, 1, (0, 1), (0, 1), (0, 1)) for _ in range(1)]
    + [("b", 0, 1, (0, 1), (0, 1), (0, 1)), ("c", 0, 1, (0, 1), (0, 1), (0, 1))],
    "consecutive": [(f"m{i}", i, i + 1, (i, i + 1), (0, 1), (0, 1)) for i in range(5)],
    "shifted": [(f"m{i}", i, i + 2, (i, i + 2), (0, 2), (0, 1)) for i in range(5)],
    "gap": [
        ("m0", 0, 1, (0, 1), (0, 1), (0, 1)),
        ("m1", 1, 2, (1, 2), (0, 1), (0, 1)),
        ("m2", 4, 5, (4, 5), (0, 1), (0, 1)),
        ("m3", 6, 8, (6, 8), (0, 1), (0, 1)),
    ],
    "nested": [
        ("outer", 0, 8, (0, 8), (0, 8), (0, 8)),
        ("inner", 2, 6, (2, 6), (2, 6), (2, 6)),
        ("core", 3, 4, (3, 4), (3, 4), (3, 4)),
        ("start", 0, 3, (0, 3), (0, 3), (0, 3)),
        ("end", 5, 8, (5, 8), (5, 8), (5, 8)),
        ("point", 4, None, (4, 4), (4, 4), (4, 4)),
    ],
    "overlapping": [
        ("m0", 0, 3, (0, 3), (0, 3), (0, 3)),
        ("m1", 2, 5, (2, 5), (2, 5), (2, 5)),
        ("m2", 4, 7, (4, 7), (4, 7), (4, 7)),
        ("m3", 1, 6, (1, 6), (1, 6), (1, 6)),
    ],
    "points": [(f"p{i}", i, None, (i, i), (0, 0), (0, 0)) for i in (0, 1, 1, 2)],
    "duplicate_ids": [
        ("same", 0, 1, (0, 1), (0, 1), (0, 1)),
        ("same", 1, 2, (1, 2), (0, 1), (0, 1)),
        ("same", 0, 1, (0, 1), (0, 1), (0, 1)),
        ("other", 1, 3, (0, 2), (0, 1), (0, 1)),
    ],
    "unsorted": [
        ("m2", 2, 3, (2, 3), (0, 1), (0, 1)),
        ("m0", 0, 1, (0, 1), (0, 1), (0, 1)),
        ("m3", 3, 4, (3, 4), (0, 1), (0, 1)),
        ("m1", 1, 2, (1, 2), (0, 1), (0, 1)),
    ],
    "one": [("only", 0, 1, (0, 1), (0, 1), (0, 1))],
    "empty": [],
}


def _topology_maps(kind, series):
    import grass.temporal as tgis  # noqa: PLC0415

    maps = []
    for ident, start, end, (west, east), (south, north), (bottom, top) in series:
        new = tgis.RasterDataset(f"{ident}@PERMANENT")
        if kind == "absolute":
            new.set_absolute_time(
                _START + timedelta(days=start),
                None if end is None else _START + timedelta(days=end),
            )
        else:
            new.set_relative_time(start, end, "days")
        new.set_spatial_extent_from_values(
            north=north, south=south, east=east, west=west, top=top, bottom=bottom
        )
        maps.append(new)
    return maps


def _relation_list(map_, getter):
    """The maps of the relation a getter is named after

    Read from the relation dictionaries, which the algebra and the tools read
    as well, so the record does not depend on one accessor method per
    relation. Temporal and spatial names do not overlap: overlaps and overlap,
    contains and contain, equal and equivalent.
    """
    links = {**map_.get_temporal_relations(), **map_.get_spatial_relations()}
    return links.get(getter.removeprefix("get_").upper())


def _topology_result(maps, builder, getters):
    """The relation lists as "<index>:<id>" in the order the builder made them

    The index is the position in the list that was built, because ids can
    occur twice and then name no single map.
    """
    position = {id(map_): index for index, map_ in enumerate(maps)}

    def named(items):
        return [
            f"{position.get(id(item), '?')}:{item.get_id()}" for item in items or []
        ]

    result = []
    for index, map_ in enumerate(maps):
        result.append(
            {
                "map": f"{index}:{map_.get_id()}",
                "next": named([map_.next()] if map_.next() else []),
                "prev": named([map_.prev()] if map_.prev() else []),
                **{name: named(_relation_list(map_, name)) for name in getters},
            }
        )
    result.append({"iteration": named(list(builder)), "length": len(builder)})
    return result


def _build(kind, series, spatial, second):
    import grass.temporal as tgis  # noqa: PLC0415

    maps = _topology_maps(kind, _TOPOLOGY_SERIES[series])
    others = None
    if second:
        # A second list: the same series shifted by one day
        others = _topology_maps(
            kind,
            [
                (ident + "_b", start + 1, None if end is None else end + 1, x, y, z)
                for ident, start, end, x, y, z in _TOPOLOGY_SERIES[series]
            ],
        )
    builder = tgis.SpatioTemporalTopologyBuilder()
    builder.build(maps, others, spatial)
    getters = _TEMPORAL_GETTERS + (_SPATIAL_GETTERS if spatial else ())
    result = _topology_result(maps, builder, getters)
    if others is not None:
        result.append({"second": _topology_result(others, builder, getters)})
    return result


def topology_cases():
    """The cases of the record ``topology``"""
    for kind, series, spatial, second in itertools.product(
        ("absolute", "relative"), _TOPOLOGY_SERIES, (None, "2D", "3D"), (False, True)
    ):
        yield (
            f"{kind}/{series}/spatial={spatial}/second={second}",
            lambda kind=kind, series=series, spatial=spatial, second=second: _build(  # noqa: E501
                kind, series, spatial, second
            ),
        )


###############################################################################
# Database image


def write_scenario(tools) -> None:
    """Write every kind of record the library writes to the temporal database

    Creates datasets of the three types in absolute and in relative time,
    registers maps through the tools and through the library (a raster map
    with a semantic label, a vector map with a second layer), updates the
    metadata, shifts, snaps, renames, copies, merges, unregisters and
    removes. The session must be a temporal_session(), because the library
    route runs in this process. What the scenario writes is the image that
    normalized_dump() turns into text.
    """
    saved_argv = sys.argv
    # The library stores the command line of the process in the command
    # history of a dataset it writes itself. The command line of pytest or
    # of the recording differs between runs, so the history gets a fixed one.
    sys.argv = ["scenario"]
    try:
        _write_scenario(tools)
    finally:
        sys.argv = saved_argv


def _write_scenario(tools) -> None:
    from grass.temporal.testing import data  # noqa: PLC0415

    tools.g_region(n=1, s=0, e=1, w=0, res=1, b=0, t=1, res3=1)
    spec = data.MapSpec
    day = data.day

    raster = [
        spec("img_1", 1, day(0), day(31), "S2_1"),
        spec("img_2", 2, day(31), day(59), "S2_1"),
        spec("img_3", 3, day(59), day(90), "S2_2"),
        spec("img_4", 4, day(100), day(120)),
    ]
    data.create_stds(tools, "strds", "abs_raster", raster, title="Absolute raster")
    data.create_stds(
        tools,
        "strds",
        "rel_raster",
        [spec(f"rel_{n}", n, n * 10, n * 10 + 10) for n in (1, 2, 3)],
        temporaltype="relative",
        unit="days",
        title="Relative raster",
    )
    data.create_stds(
        tools,
        "str3ds",
        "abs_raster3d",
        [spec(f"vol_{n}", n, day(n), day(n + 1)) for n in (1, 2, 3)],
        title="Absolute 3D raster",
    )
    data.create_stds(
        tools,
        "str3ds",
        "rel_raster3d",
        [spec(f"rvol_{n}", n, n, n + 2) for n in (1, 2)],
        temporaltype="relative",
        unit="years",
    )
    # A vector map with two layers is registered once per layer.
    data.vector_points(
        tools, "pts_a", [(0.5, 0.5), (0.2, 0.2)], attributes={"v": [1.0, 2.0]},
        layers=(1, 2),
    )  # fmt: skip
    data.make_map(tools, "vector", "pts_b", 2)
    data.make_map(tools, "vector", "pts_c", 3)
    data.make_map(tools, "vector", "pts_d", 4)
    data.make_map(tools, "vector", "pts_e", 5)
    data.register_stds(
        tools,
        "stvds",
        "abs_vector",
        [
            spec("pts_a", None, day(0), day(10)),
            spec("pts_a:2", None, day(0), day(10)),
            spec("pts_b", None, day(10)),
            spec("pts_c", None, day(20), day(30)),
        ],
    )
    data.register_stds(
        tools,
        "stvds",
        "rel_vector",
        [spec("pts_d", None, 1, 3), spec("pts_e", None, 3, 8)],
        temporaltype="relative",
        unit="months",
    )
    # The route through the library writes the same rows by other calls.
    for name in ("lib_1", "lib_2", "lib_3", "lib_4"):
        data.make_map(tools, "raster", name, 1)
    data.register_stds(
        tools,
        "strds",
        "lib_abs",
        [spec("lib_1", 1, day(0), day(5)), spec("lib_2", 2, day(5), day(9))],
        via="library",
    )
    data.register_stds(
        tools,
        "strds",
        "lib_rel",
        [spec("lib_3", 1, 0, 4), spec("lib_4", 2, 4, 9)],
        temporaltype="relative",
        unit="days",
        via="library",
    )

    # Metadata, title, description and semantic type; -m reads the maps again.
    tools.t_support(
        input="abs_raster", type="strds", title="Changed title",
        description="Changed description", semantictype="max", flags="m",
    )  # fmt: skip
    tools.t_support(input="abs_vector", type="stvds", flags="m")
    tools.t_support(input="abs_raster3d", type="str3ds", flags="m")
    tools.r_support(map="img_4", semantic_label="S2_3")
    tools.t_support(input="abs_raster", type="strds", flags="m")

    tools.t_shift(input="lib_abs", type="strds", granularity="2 days")
    tools.t_shift(input="abs_raster3d", type="str3ds", granularity="1 month")
    tools.t_shift(input="rel_raster", type="strds", granularity="5")
    tools.t_snap(input="abs_raster", type="strds")
    tools.t_snap(input="rel_raster", type="strds")
    tools.t_rename(input="lib_rel", output="renamed_rel", type="strds")
    tools.t_copy(input="abs_raster", output="copied", type="strds")
    tools.t_merge(input="abs_raster,lib_abs", output="merged", type="strds")

    with TemporaryDirectory() as directory:
        names = data.register_file(Path(directory) / "maps.txt", ["img_4"])
        tools.t_unregister(type="raster", input="abs_raster", file=names)
    tools.t_unregister(type="vector", input="abs_vector", maps="pts_b")
    data.create_stds(
        tools,
        "str3ds",
        "gone_raster3d",
        [spec("gone_1", 1, day(0), day(2))],
    )
    tools.t_remove(inputs="gone_raster3d", type="str3ds", flags="f")
    # -d removes the maps from the database too, so the dataset has maps of
    # its own.
    data.create_stds(
        tools,
        "strds",
        "doomed",
        [spec(f"dm_{n}", n, day(n), day(n + 1)) for n in (1, 2)],
    )
    tools.t_remove(inputs="doomed", type="strds", flags="df")


_REGISTER_TABLE = re.compile(
    r"\b(?:raster|raster3d|vector)_map_register_[0-9a-f]{32}(?![0-9a-f])"
)
_COMMAND_TIME = re.compile(r"# \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ")
_TEMPORARY_DIRECTORY = re.compile(r"[^\s\"=]*/tmp[0-9a-z_]{8}/")
# A fixed moment that parses like a real one, so that the read image can
# print it.
_MOMENT = "2000-01-01 00:00:00"
_USER = "user"


def normalized_dump(path: Path) -> str:
    """Return the temporal database at path as SQL text that equals between runs

    The schema first, then one INSERT per row; tables and rows are sorted.
    Values that differ between runs are replaced: the creation and
    modification times (also the one in tgis_metadata) by a fixed moment, creator and modifier by a fixed
    name, the time stamps and temporary directories in the stored command
    history, and the 32 hex digits of a register table name by the digest of
    the id of the dataset that owns the table, so the text does not depend
    on the order in which datasets were made. The result loads into an
    empty SQLite database.

    :raises ValueError: for a register table that no dataset owns
    """
    connection = sqlite3.connect(path)
    try:
        names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
                " AND name NOT LIKE 'sqlite_%'"
            )
        ]
        owners = {}
        for name in names:
            columns = [
                row[1] for row in connection.execute(f'PRAGMA table_info("{name}")')
            ]
            for column in columns:
                if column.endswith("_register") and name.endswith("_metadata"):
                    for ident, table in connection.execute(
                        f'SELECT id, "{column}" FROM "{name}"'
                    ):
                        owners[table] = hashlib.md5(  # noqa: S324
                            ident.encode(), usedforsecurity=False
                        ).hexdigest()

        def register_name(match):
            table = match.group(0)
            if table not in owners:
                msg = f"Register table {table} has no owner"
                raise ValueError(msg)
            return table[: -len("0" * 32)] + owners[table]

        def clean(text: str) -> str:
            text = _REGISTER_TABLE.sub(register_name, text)
            text = _COMMAND_TIME.sub("# TIME ", text)
            return _TEMPORARY_DIRECTORY.sub("TMPDIR/", text)

        lines = []
        for kind in ("table", "index", "view", "trigger"):
            statements = sorted(
                clean(row[0])
                for row in connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type = ? AND sql IS NOT NULL"
                    " AND name NOT LIKE 'sqlite_%'",
                    (kind,),
                )
            )
            lines.extend(f"{statement};" for statement in statements)
        for name in sorted(names, key=clean):
            cursor = connection.execute(f'SELECT * FROM "{name}"')
            columns = [column[0] for column in cursor.description]
            rows = []
            for row in cursor:
                values = []
                for column, value in zip(columns, row, strict=True):
                    if column in {"creation_time", "modification_time"}:
                        value = _MOMENT if value is not None else None
                    elif (
                        name == "tgis_metadata"
                        and column == "value"
                        and row[0] == "creation_time"
                    ):
                        value = _MOMENT
                    elif column in {"creator", "modifier"}:
                        value = _USER if value is not None else None
                    elif isinstance(value, str):
                        value = clean(value)
                    values.append(
                        connection.execute("SELECT quote(?)", (value,)).fetchone()[0]
                    )
                rows.append(f'INSERT INTO "{clean(name)}" VALUES({",".join(values)});')
            lines.extend(sorted(rows))
    finally:
        connection.close()
    return "\n".join(lines) + "\n"


def load_image(text: str, path: Path) -> None:
    """Replace the SQLite database at path by the image in text"""
    Path(path).unlink(missing_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(text)
        connection.commit()
    finally:
        connection.close()


def _printed(function) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        function()
    return buffer.getvalue()


def _rows(value):
    """Rows of a query as tuples, a dictionary of them per mapset"""
    if isinstance(value, dict):
        return {key: _rows(rows) for key, rows in sorted(value.items())}
    return [tuple(row) for row in value]


_STDS_TYPES = ("strds", "str3ds", "stvds")
_MAP_TYPES_OF_STDS = {"strds": "raster", "str3ds": "raster_3d", "stvds": "vector"}
_TEMPORAL_TYPES = ("absolute", "relative")


def read_cases():
    """The cases of the read image: what the library reads from the image

    The temporal database of the session must hold the image that
    database_write.sql restores. Time stamps and the user were replaced
    there, so the result does not depend on when the image was recorded.
    """
    import grass.temporal as tgis  # noqa: PLC0415

    listing = []
    for temporal in _TEMPORAL_TYPES:
        for kind in (*_STDS_TYPES, *_MAP_TYPES_OF_STDS.values()):
            for label, options in (
                ("all", {}),
                ("columns", {"columns": "id,name,creator"}),
                ("ordered", {"columns": "id", "order": "id DESC"}),
                ("where", {"columns": "id", "where": "name LIKE '%a%'"}),
            ):
                yield (
                    f"list/{kind}/{temporal}/{label}",
                    lambda kind=kind, temporal=temporal, options=options: _rows(
                        tgis.get_dataset_list(kind, temporal, **options)
                    ),
                )
            listing.append((kind, temporal))
    both = ["strds", "stvds"]
    yield "list/several", lambda: _rows(
        {k: [tuple(dict(r).items()) for r in v] for k, v in
         tgis.get_dataset_list(both, ["absolute", "relative"], columns="id").items()}
    )  # fmt: skip

    identifiers = {}
    for kind in (*_STDS_TYPES, *_MAP_TYPES_OF_STDS.values()):
        found = set()
        for temporal in _TEMPORAL_TYPES:
            for rows in tgis.get_dataset_list(
                kind, temporal, columns="id", order="id"
            ).values():
                found.update(row["id"] for row in rows)
        identifiers[kind] = sorted(found)

    variants = (
        {},
        {"columns": "id"},
        {"columns": "id,start_time,end_time", "order": "start_time"},
        {"columns": "id,start_time", "where": "start_time > '2001-01-15'"},
        {"columns": "id", "order": "id DESC"},
        {"columns": "id,name,mapset", "where": "id LIKE '%1%'"},
        {"columns": "id,start_time", "where": "start_time > '2001-01-15';"},
    )
    for kind in _STDS_TYPES:
        for ident in identifiers[kind]:

            def stds(kind=kind, ident=ident):
                dataset = tgis.dataset_factory(kind, ident)
                dataset.select()
                return dataset

            yield (
                f"stds/{kind}/{ident}/info",
                lambda stds=stds: [
                    _printed(lambda: stds().print_info()),
                    _printed(lambda: stds().print_shell_info()),
                ],
            )
            for number, options in enumerate(variants):
                yield (
                    f"stds/{kind}/{ident}/maps/{number}",
                    lambda stds=stds, options=options: _rows(
                        stds().get_registered_maps(**options) or []
                    ),
                )
            yield (
                f"stds/{kind}/{ident}/lists",
                lambda stds=stds: [
                    stds().get_map_time(),
                    stds().count_gaps() if stds().is_time_absolute() else None,
                    stds().get_temporal_type(),
                ],
            )
    for kind in _MAP_TYPES_OF_STDS.values():
        for ident in identifiers[kind]:

            def one(kind=kind, ident=ident):
                dataset = tgis.dataset_factory(kind, ident)
                dataset.select()
                return dataset

            yield (
                f"map/{kind}/{ident}",
                lambda one=one: [
                    _printed(lambda: one().print_info()),
                    _printed(lambda: one().print_shell_info()),
                    one().get_registered_stds(),
                ],
            )


def record_database_image(directory: Path) -> None:
    """Run the scenario in a project of its own and record both images

    Writes database_write.sql, then loads it into a second project and writes
    database_read.json.gz from there. Run it outside a GRASS session, with
    the GRASS tools in PATH.
    """
    import grass.temporal as tgis  # noqa: PLC0415
    from grass.temporal.testing.session import temporal_session  # noqa: PLC0415
    from grass.tools import Tools  # noqa: PLC0415

    directory = Path(directory)
    with TemporaryDirectory() as work:
        with temporal_session(Path(work) / "write") as session:
            tools = Tools(session=session, consistent_return_value=True)
            write_scenario(tools)
            text = normalized_dump(Path(tgis.get_tgis_database_string()))
        (directory / "database_write.sql").write_text(text, encoding="utf-8")
        with temporal_session(Path(work) / "read"):
            load_image(text, Path(tgis.get_tgis_database_string()))
            record("database_read", read_cases(), directory)


###############################################################################
# Command line

CASES = {
    "spatial_extent": spatial_extent_cases,
    "temporal_extent": temporal_extent_cases,
    "granularity": granularity_cases,
    "datetime_math": datetime_math_cases,
    "topology": topology_cases,
}


def main(argv: list[str]) -> int:
    """Record or compare: ``record|compare <directory> [name ...]``"""
    import grass.temporal as tgis  # noqa: PLC0415

    if len(argv) == 2 and argv[0] == "image":
        record_database_image(Path(argv[1]))
        print("database image: recorded")
        return 0
    if len(argv) < 2 or argv[0] not in {"record", "compare"}:
        print(__doc__)
        return 2
    action, directory, names = argv[0], Path(argv[1]), argv[2:] or list(NAMES)
    tgis.init(raise_fatal_error=True)
    failed = False
    for name in names:
        if action == "record":
            record(name, CASES[name](), directory)
            print(f"{name}: recorded")
        else:
            differences = compare(name, CASES[name](), directory)
            failed = failed or bool(differences)
            print(f"{name}: {len(differences)} differences")
            for line in differences[:20]:
                print(f"  {line}")
    return 1 if failed else 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
