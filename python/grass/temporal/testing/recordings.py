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

``compare <directory>`` prints the differences. The module does not import
pytest.
"""

from __future__ import annotations

import gzip
import itertools
import json
from datetime import datetime, timedelta
from pathlib import Path
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
    from grass.temporal import SpatialExtent, TemporalExtent  # noqa: PLC0415

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
    from grass.temporal import SpatialExtent  # noqa: PLC0415

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
            lambda grans=grans: tgis.compute_common_absolute_time_granularity(grans),
        )
        yield (
            f"common_absolute_simple/{grans}",
            lambda grans=grans: tgis.compute_common_absolute_time_granularity_simple(
                grans
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
                tgis.compute_common_absolute_time_granularity(grans, starts)
            ),
        )
    for subset in _subsets(_RELATIVE, 3):
        grans = list(subset)
        yield (
            f"common_relative/{grans}",
            lambda grans=grans: tgis.compute_common_relative_time_granularity(grans),
        )
    for gran in (*_GRANULARITIES, "5 months", "0 days", "1 fortnight", "day", ""):
        yield (
            f"check_absolute/{gran}",
            lambda gran=gran: tgis.check_granularity_string(gran, "absolute"),
        )
        yield f"singular/{gran}", lambda gran=gran: tgis.gran_singular_unit(gran)
        yield f"plural/{gran}", lambda gran=gran: tgis.gran_plural_unit(gran)
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
                outcome(tgis.decrement_datetime_by_string, date, step) for date in dates
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
                outcome(tgis.compute_datetime_delta, start, end) for end in dates
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
                **{name: named(getattr(map_, name)()) for name in getters},
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
