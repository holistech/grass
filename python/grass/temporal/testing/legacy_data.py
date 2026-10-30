"""Datasets and checks of the algebra cases that moved from the gunittest files

The files python/grass/temporal/testsuite/unittests_temporal_*.py built their
datasets in setUpClass with a map per r.mapcalc call. The builders below make
the same datasets in a test session (times, values and dataset names are those
of the old files, the region is small because every map is constant) and
check_case() and check_dry() compare what an algebra runner makes with the
expected maps. A case is (expression, options of the runner, expected), the
format of the t.rast.algebra cases; ``expected`` is a list of maps
(start, end, min, max) or, for vector maps, (start, end, points, lines,
areas), or the name of the error class that the expression raises.

This module must not import pytest; fixtures belong in conftest.py files.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import datetime
import re

import grass.temporal as tgis
from grass.temporal.testing.data import MapSpec, create_stds, make_map, register_stds
from grass.temporal.testing.differential import RUNNERS, outcome

_STDS = {"raster": "strds", "raster3d": "str3ds", "vector": "stvds"}
_MAP = {"raster": "raster", "raster3d": "raster_3d", "vector": "vector"}


def when(month, day=1, year=2001):
    """A date, by default of 2001"""
    return datetime.datetime(year, month, day)


def january(number):
    """The beginning of the day number of January 2001"""
    return when(1, number)


def single_map(tools, kind, name, value, start=None, end=None):
    """A map in no dataset; with start it gets that time stamp (an instant
    without end)"""
    make_map(tools, _MAP[kind], name, value, overwrite=True)
    if start is not None:
        times = {"start": start.isoformat(sep=" ")}
        if end is not None:
            times["end"] = end.isoformat(sep=" ")
        tools.t_register(type=_MAP[kind], maps=name, **times)


def _small_region(tools, *, depths=False):
    options = {"n": 3, "s": 0, "e": 3, "w": 0, "res": 1}
    if depths:
        options.update({"t": 3, "b": 0, "res3": 1})
    tools.g_region(**options)


def daily_datasets(tools, kind="raster"):
    """A a1..a4 = 1..4 daily from January 1; B b1 = 5 and b2 = 6 on two days
    each from January 1; C c1 = 7 on January 2 and 3; D d1..d3 = 8..10 daily
    from January 3"""
    for name, values, first, length in (
        ("A", [1, 2, 3, 4], 1, 1),
        ("B", [5, 6], 1, 2),
        ("C", [7], 2, 2),
        ("D", [8, 9, 10], 3, 1),
    ):
        create_stds(
            tools,
            _STDS[kind],
            name,
            [
                MapSpec(
                    f"{name.lower()}{number}",
                    value,
                    january(first + length * (number - 1)),
                    january(first + length * number),
                )
                for number, value in enumerate(values, 1)
            ],
        )


def algebra(tools):
    """unittests_temporal_algebra.py: the daily datasets and singletmap = 99
    on January 3"""
    _small_region(tools)
    daily_datasets(tools)
    single_map(tools, "raster", "singletmap", 99, january(3), january(4))


def raster_algebra(tools):
    """unittests_temporal_raster_algebra.py: as algebra() and singlemap = 100
    without time"""
    algebra(tools)
    make_map(tools, "raster", "singlemap", 100, overwrite=True)


def monthly_datasets(tools):
    """A a1..a6 = 1..6 on the months January to June; B b1 = 7 for January to
    March and b2 = 8 for April to June; C c1 = 9 for the year 2001"""
    create_stds(
        tools,
        "strds",
        "A",
        [MapSpec(f"a{k}", k, when(k), when(k + 1)) for k in range(1, 7)],
    )
    create_stds(
        tools,
        "strds",
        "B",
        [MapSpec("b1", 7, when(1), when(4)), MapSpec("b2", 8, when(4), when(7))],
    )
    create_stds(tools, "strds", "C", [MapSpec("c1", 9, when(1), when(1, 1, 2002))])


def algebra_granularity(tools):
    """unittests_temporal_algebra_grs.py: the monthly datasets; D d1..d3 = 10,
    11, 12 for 31 days from the first of January, March and May; singletmap"""
    _small_region(tools)
    monthly_datasets(tools)
    create_stds(
        tools,
        "strds",
        "D",
        [
            MapSpec(f"d{k}", 9 + k, when(m), when(m) + datetime.timedelta(days=31))
            for k, m in enumerate((1, 3, 5), 1)
        ],
    )
    single_map(tools, "raster", "singletmap", 99, january(3), january(4))


def raster_granularity(tools):
    """unittests_temporal_raster_algebra_grs.py: the monthly datasets; D d1..d3
    = 10, 11, 12 for five days from the first of January, March and May;
    singletmap = 99 for March; nullmap, a null map for January to June"""
    _small_region(tools)
    monthly_datasets(tools)
    create_stds(
        tools,
        "strds",
        "D",
        [
            MapSpec(f"d{k}", 9 + k, when(m), when(m, 6))
            for k, m in enumerate((1, 3, 5), 1)
        ],
    )
    single_map(tools, "raster", "singletmap", 99, when(3), when(4))
    single_map(tools, "raster", "nullmap", "null()", when(1), when(7))


def mixed_types(tools):
    """unittests_temporal_algebra_mixed_stds.py: A (str3ds) a1..a4 = 1..4
    daily from January 1, B (strds) b1 = 5 and b2 = 6 on two days each, C
    (stvds) c1 = 20 random points on January 2 and 3"""
    _small_region(tools, depths=True)
    create_stds(
        tools,
        "str3ds",
        "A",
        [MapSpec(f"a{k}", k, january(k), january(k + 1)) for k in range(1, 5)],
    )
    create_stds(
        tools,
        "strds",
        "B",
        [
            MapSpec("b1", 5, january(1), january(3)),
            MapSpec("b2", 6, january(3), january(5)),
        ],
    )
    tools.v_random(output="c1", npoints=20, seed=3)
    register_stds(tools, "stvds", "C", [MapSpec("c1", None, january(2), january(4))])


def conditionals(tools):
    """unittests_temporal_conditionals.py: the daily datasets, E e1..e3 = 11..13
    on two days each from December 31, 2000, and singletmap = 99"""
    algebra(tools)
    start = when(12, 31, 2000)
    create_stds(
        tools,
        "strds",
        "E",
        [
            MapSpec(
                f"e{k}",
                10 + k,
                start + datetime.timedelta(days=2 * (k - 1)),
                start + datetime.timedelta(days=2 * k),
            )
            for k in range(1, 4)
        ],
    )


def raster3d_algebra(tools):
    """unittests_temporal_raster3d_algebra.py: A (str3ds) a1..a4 = 1..4 daily
    from January 1"""
    _small_region(tools, depths=True)
    create_stds(
        tools,
        "str3ds",
        "A",
        [MapSpec(f"a{k}", k, january(k), january(k + 1)) for k in range(1, 5)],
    )


def equal_time_stamps(tools):
    """unittests_temporal_raster_algebra_equal_ts.py: A a1..a4 = 1..4, all four
    at the instant January 1; singletmap = 100 at that instant; singlemap =
    1000 without time"""
    _small_region(tools)
    create_stds(
        tools, "strds", "A", [MapSpec(f"a{k}", k, january(1)) for k in range(1, 5)]
    )
    single_map(tools, "raster", "singletmap", 100, january(1))
    make_map(tools, "raster", "singlemap", 1000, overwrite=True)


def spatial_topology(tools):
    """unittests_temporal_raster_algebra_spatial_topology.py: A a1..a4 and B
    b1..b4, map k holding k, all eight at the instant January 1; the maps k
    cover (west, east, south, north) 0-30, 20-50, 25-40 and 40-60 (the same
    extent in A and B); singletmap = 100 at the instant; singlemap = 1000"""
    extents = {1: (0, 30, 0, 30), 2: (20, 50, 20, 50), 3: (25, 40, 25, 40)}
    extents[4] = (40, 60, 40, 60)
    for k, (west, east, south, north) in extents.items():
        region = {"n": north, "s": south, "e": east, "w": west, "res": 10}
        make_map(tools, "raster", f"a{k}", k, region=region, overwrite=True)
        make_map(tools, "raster", f"b{k}", k, region=region, overwrite=True)
    tools.g_region(n=60, s=0, e=60, w=0, res=10)
    for name in "AB":
        register_stds(
            tools,
            "strds",
            name,
            [MapSpec(f"{name.lower()}{k}", k, january(1)) for k in range(1, 5)],
        )
    single_map(tools, "raster", "singletmap", 100, january(1))
    make_map(tools, "raster", "singlemap", 1000, overwrite=True)


def conditional_complement(tools):
    """unittests_temporal_raster_conditionals_complement_else.py: A a1..a6 =
    1..6 daily from January 1; B b1 = 7 on January 2 and 3, b2 = 8 on January
    4 and 5"""
    _small_region(tools)
    create_stds(
        tools,
        "strds",
        "A",
        [MapSpec(f"a{k}", k, january(k), january(k + 1)) for k in range(1, 7)],
    )
    create_stds(
        tools,
        "strds",
        "B",
        [
            MapSpec("b1", 7, january(2), january(4)),
            MapSpec("b2", 8, january(4), january(6)),
        ],
    )


def raster_conditionals(tools):
    """unittests_temporal_raster_conditionals.py: the daily datasets, but D has
    a fourth map d4 = 11 on January 6"""
    _small_region(tools)
    daily_datasets(tools)
    create_stds(
        tools,
        "strds",
        "D",
        [MapSpec(f"d{k}", 7 + k, january(2 + k), january(3 + k)) for k in range(1, 5)],
        overwrite=True,
    )


def vector_algebra(tools):
    """unittests_temporal_vector_algebra.py: the daily datasets as vector maps
    of 20 random points each, with the seed 1 (A), 2 (B), 3 (C) and 4 (D),
    so the maps of a dataset are copies of each other; singletmap (seed 5)
    on January 3; singlemap (seed 6) without time"""
    tools.g_region(n=80, s=0, e=120, w=0, res=10)
    datasets = {
        "A": (1, 4, 1, 1),
        "B": (2, 2, 1, 2),
        "C": (3, 1, 2, 2),
        "D": (4, 3, 3, 1),
    }
    for name, (seed, count, first, length) in datasets.items():
        maps = []
        for number in range(1, count + 1):
            vector = f"{name.lower()}{number}"
            tools.v_random(output=vector, npoints=20, seed=seed, overwrite=True)
            maps.append(
                MapSpec(
                    vector,
                    None,
                    january(first + length * (number - 1)),
                    january(first + length * number),
                )
            )
        register_stds(tools, "stvds", name, maps)
    single_map(tools, "vector", "singletmap", 5, january(3), january(4))
    make_map(tools, "vector", "singlemap", 6, overwrite=True)


def _date(text):
    """A time stamp of a result without the midnight, so cases stay short"""
    if text is not None and text.endswith("T00:00:00"):
        return text[: -len("T00:00:00")]
    return text


def _order(row):
    # Maps without values (register_null) have None where others have numbers.
    return tuple((value is None, str(value)) for value in row)


def check_case(
    kind, runner, expression, options, expected, shape=None, message=None, names=None
):
    """Run an expression with a runner and compare the result with the case

    :param kind: ``"raster"``, ``"raster3d"``, ``"vector"`` or ``"select"``
    :param runner: ``"reference"``, ``"classic"`` or ``"core"``
    :param expression: The right hand side, run as ``R = <expression>``
    :param expected: See the module docstring; dates are ``"2001-01-02"`` or,
        off midnight, ``"2001-01-02T12:00:00"``; an instant has the end None
    :param options: The options of the runner; ``result_type`` is not one, it
        names the dataset type to read the result as, if it differs from the
        type of the kind (a mixed expression)
    :param shape: ``(check_temporal_topology(), get_granularity())`` of the
        result, checked if given and if the result has maps
    :param message: A regular expression that the message of an expected
        error must match
    :param names: The names of the result maps (without the mapset) in the
        order of their start times
    """
    base = f"lc{runner[:2]}"
    result = outcome(kind, expression, RUNNERS[runner], basename=base, **options)
    if isinstance(expected, str):
        assert result.get("error") == expected, result
        if message:
            assert re.search(message, result["msg"]), result["msg"]
        return
    assert "error" not in result, result
    maps = sorted(
        (
            (_date(start), _date(end), *values)
            for _, start, end, *values in result["maps"]
        ),
        key=_order,
    )
    assert maps == sorted(expected, key=_order)
    if names is not None:
        by_start = sorted(result["maps"], key=lambda row: row[1])
        assert [row[0].split("@")[0] for row in by_start] == names
    if shape is not None and expected:
        stdstype = options.get("stdstype") or _STDS.get(kind, "strds")
        stds = tgis.open_old_stds(f"R{base}", options.get("result_type") or stdstype)
        assert (stds.check_temporal_topology(), stds.get_granularity()) == shape


def check_dry(kind, runner, expression, options, expected):
    """Plan an expression with a runner and compare the process chain

    ``expected`` is a dict with the numbers of the maps to register
    (``register``) and of the planned processes (``processes``), optionally
    the names of the first and last process (``names``) and the type of the
    result (``stdstype``, default strds); the result is always named R.
    """
    chain = RUNNERS[runner](
        kind, f"R = {expression}", basename="r", overwrite=True, run=True,
        dry_run=True, **options,
    )  # fmt: skip
    assert len(chain["register"]) == expected["register"]
    if "processes" in expected:
        assert len(chain["processes"]) == expected["processes"]
    if "names" in expected:
        planned = [process["name"] for process in chain["processes"]]
        assert planned[0] == expected["names"][0]
        assert planned[-1] == expected["names"][-1]
    assert chain["STDS"]["name"] == "R"
    assert chain["STDS"]["stdstype"] == expected.get("stdstype", "strds")
