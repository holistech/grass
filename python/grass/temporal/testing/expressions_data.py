"""Datasets for the expression fuzzer

``build(kind, tools, directory)`` creates the datasets of one map type in the
session of ``tools``; the session must come from ``temporal_session`` because
the datasets are registered with the library. ``NAMES[kind]`` lists the
dataset names that the generator may use, with weights. ``SINGLE[kind]`` lists
the single maps for ``tmap()`` and ``map()``, ``FAMILY[kind]`` datasets with
equal time stamps, which make the default relation ``equal`` find partners
more often than a draw over all datasets.

The raster datasets cover the topologies that the expression tests of the
algebra rely on (adjacent and overlapping intervals, instants, gaps, one time
stamp for several maps, relative time, null cells, floating point maps, maps
of different extent). Kind ``select`` runs on the raster datasets.

This module must not import pytest.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import datetime
from pathlib import Path

import grass.temporal as tgis
from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    day,
    horizontal_line,
    import_ascii_vector,
    points_map,
    register_stds,
    small_region,
    square_area,
)

NAMES = {
    "raster": {
        "A": 10, "N": 4, "B": 6, "C": 4, "D": 5, "HA": 2, "HB": 2, "I": 4,
        "E": 3, "Q": 4, "GP": 3, "Z": 3, "W": 3, "OV": 3, "RT": 2, "RH": 1,
        "rel": 1, "ref": 2, "SA": 1, "PA": 1, "AF": 3,
    },
    "select": {
        "A": 10, "N": 4, "B": 6, "C": 4, "D": 5, "HA": 2, "HB": 2, "I": 4,
        "E": 3, "Q": 4, "GP": 3, "Z": 3, "W": 3, "OV": 3, "RT": 2, "RH": 1,
        "rel": 1, "ref": 2, "AF": 3,
    },
    "raster3d": {
        "A": 10, "B": 6, "W": 4, "D": 3, "E": 2, "Q": 2, "Q2": 1, "EQ": 3,
        "Z": 3, "I": 3, "RT": 1,
    },
    "vector": {
        "aa": 8, "ab": 6, "ac": 2, "pa": 4, "pb": 3, "pc": 1, "la": 2,
        "wide": 4, "ne": 2, "eq": 3, "pi": 2, "rel": 1,
    },
}  # fmt: skip

# The granularity mode (-g) needs a common granularity, so these datasets have
# absolute intervals of whole days only (no instants, no relative time).
GRANULARITY_NAMES = {
    "raster": {
        "A": 10, "N": 4, "B": 6, "C": 4, "D": 5, "Z": 3, "AF": 3, "W": 3,
        "OV": 3, "GP": 3, "HA": 2, "HB": 2,
    },
    "raster3d": {"A": 10, "B": 6, "W": 4, "D": 3, "Z": 3, "EQ": 3},
}  # fmt: skip

GRANULARITY_FAMILY = {"raster": ["A", "N", "Z", "AF"], "raster3d": ["A", "B", "Z"]}

GRANULARITY_SINGLE = {"raster": ["singletmap"], "raster3d": ["single"]}

FAMILY = {
    "raster": ["A", "N", "Z", "AF"],
    "select": ["A", "N", "Z", "AF"],
    "raster3d": ["A", "B", "Z"],
    "vector": ["aa", "ab", "ac", "pa", "pb", "la"],
}

SINGLE = {
    "raster": ["sinst", "singletmap"],
    "select": ["sinst", "singletmap"],
    "raster3d": ["single"],
    "vector": ["ev"],
}

# Probe maps of the dataset "rel": (first day, last day) in January 2001 of
# the maps p1..p13. The reference map ref1 covers days 10 to 20, so each probe
# stands in another temporal relation to it.
_PROBES = [
    (10, 20), (12, 18), (5, 25), (10, 15), (10, 25), (15, 20), (5, 20),
    (5, 10), (20, 25), (5, 15), (15, 25), (1, 3), (27, 30),
]  # fmt: skip

# Maps of the raster datasets as r.mapcalc expressions.
_RASTER_MAPS = {
    "a1": "1", "a2": "2", "a3": "3", "a4": "4", "b1": "5", "b2": "6",
    "c1": "7", "d1": "8", "d2": "9", "d3": "10", "singletmap": "99",
    "sinst": "100", "e1": "1", "e2": "2", "e3": "3", "e4": "4", "i1": "1",
    "i2": "2", "i3": "3", "x1": "1", "x2": "2", "x3": "3", "ref1": "100",
    "hb1": "7", "hb2": "8", "n1": "11", "n2": "12", "n3": "13", "n4": "14",
    "q1": "21", "q2": "22", "q3": "23", "gp1": "31", "gp2": "32", "gp3": "33",
    "z1": "null()", "z2": "0", "z3": "if(row() == 1, null(), 2)", "z4": "-1",
    "w1": "50", "ov1": "61", "ov2": "62", "rh1": "71", "rh2": "72",
    "af1": "0.5", "af2": "1.5", "af3": "2.5", "af4": "3.5",
}  # fmt: skip


def build(kind, tools, directory):
    """Create the datasets of kind in the session of tools

    :param kind: ``"raster"``, ``"raster3d"``, ``"vector"`` or ``"select"``
    :param tools: ``grass.tools.Tools`` of a ``temporal_session``
    :param directory: Existing directory for the scratch files of the import
    """
    builders = {
        "raster": _raster,
        "select": _raster,
        "raster3d": _raster3d,
        "vector": _vector,
    }
    builders[kind](tools, Path(directory))


def _raster(tools, directory):
    small_region(tools, 3, 3)
    expressions = dict(_RASTER_MAPS)
    expressions.update({f"p{number}": str(number) for number in range(1, 14)})
    expressions.update({f"ha{number}": str(number) for number in range(1, 7)})
    # Truth table series: map k = 4a + 2b + c of PA holds the bit a.
    expressions.update({f"pa{number}": str(number >> 2 & 1) for number in range(8)})
    script = directory / "fuzz_maps.txt"
    script.write_text(
        "".join(f"{name} = {text}\n" for name, text in expressions.items())
    )
    tools.r_mapcalc(file=script)

    def daily(dataset, names, first_day, step=1, *, instants=False):
        """Register names as consecutive intervals of step days or as instants"""
        specs = []
        for number, name in enumerate(names):
            if instants:
                start, end = day(first_day - 1), None
            else:
                start = day(first_day - 1 + number * step)
                end = day(first_day - 1 + (number + 1) * step)
            specs.append(MapSpec(name, None, start, end))
        register_stds(tools, "strds", dataset, specs, via="library")

    daily("A", ["a1", "a2", "a3", "a4"], 1)
    daily("N", ["n1", "n2", "n3", "n4"], 1)
    daily("B", ["b1", "b2"], 1, step=2)
    daily("C", ["c1"], 2, step=2)
    daily("D", ["d1", "d2", "d3"], 3)
    daily("HA", [f"ha{n}" for n in range(1, 7)], 1)
    daily("HB", ["hb1", "hb2"], 2, step=2)
    daily("E", ["e1", "e2", "e3", "e4"], 1, instants=True)
    register_stds(
        tools,
        "strds",
        "I",
        [MapSpec(f"i{n}", None, day(n - 1)) for n in (1, 2, 3)],
        via="library",
    )
    specs = []
    for number in range(8):
        start = datetime.datetime(
            2001, 1 + (number >> 2 & 1), 1 + (number >> 1 & 1), 12 * (number & 1)
        )
        specs.append(
            MapSpec(f"pa{number}", None, start, start + datetime.timedelta(hours=1))
        )
    register_stds(tools, "strds", "PA", specs, via="library")
    register_stds(
        tools, "strds", "ref", [MapSpec("ref1", None, day(9), day(19))], via="library"
    )
    register_stds(
        tools,
        "strds",
        "rel",
        [
            MapSpec(f"p{number}", None, day(first - 1), day(last - 1))
            for number, (first, last) in enumerate(_PROBES, 1)
        ],
        via="library",
    )
    register_stds(
        tools,
        "strds",
        "RT",
        [MapSpec(f"x{n}", None, n - 1, n) for n in (1, 2, 3)],
        temporaltype="relative",
        unit="days",
        via="library",
    )
    tgis.register_maps_in_space_time_dataset(
        "raster", None, "singletmap", start="2001-01-03", end="2001-01-04"
    )
    tgis.register_maps_in_space_time_dataset(
        "raster", None, "sinst", start="2001-01-01"
    )

    # Pairs of datasets with the same time stamps whose maps differ in extent
    # are what the spatial option needs. The extent of a map decides which
    # maps are related; spa2 contains spa3.
    extents = {1: (0, 30), 2: (20, 50), 3: (25, 40), 4: (40, 60)}
    for number, (low, high) in extents.items():
        tools.g_region(n=high, s=low, e=high, w=low, res=10)
        tools.r_mapcalc(expression=f"spa{number} = {number}")
    small_region(tools, 3, 3)
    register_stds(
        tools,
        "strds",
        "SA",
        [MapSpec(f"spa{n}", None, day(0)) for n in extents],
        via="library",
    )

    # Topologies the datasets above lack: several maps with one time stamp,
    # gaps, a wide interval, overlapping intervals, relative time in hours and
    # floating point maps with the times of A. Maps with null cells and
    # zero are in Z.
    def intervals(dataset, names, times, **options):
        specs = [
            MapSpec(name, None, start, end)
            for name, (start, end) in zip(names, times, strict=True)
        ]
        register_stds(tools, "strds", dataset, specs, via="library", **options)

    intervals(
        "Q", ["q1", "q2", "q3"], [(day(0), day(2)), (day(0), day(2)), (day(2), day(3))]
    )
    intervals(
        "GP",
        ["gp1", "gp2", "gp3"],
        [(day(0), day(1)), (day(3), day(4)), (day(7), day(8))],
    )
    intervals(
        "Z", [f"z{n}" for n in range(1, 5)], [(day(n - 1), day(n)) for n in range(1, 5)]
    )
    intervals("W", ["w1"], [(day(0), day(4))])
    intervals(
        "AF",
        [f"af{n}" for n in range(1, 5)],
        [(day(n - 1), day(n)) for n in range(1, 5)],
    )
    intervals("OV", ["ov1", "ov2"], [(day(1), day(3)), (day(3), day(6))])
    intervals(
        "RH", ["rh1", "rh2"], [(0, 1), (1, 2)], temporaltype="relative", unit="hours"
    )


def _raster3d(tools, directory):
    tools.g_region(n=3, s=0, e=3, w=0, t=3, b=0, res=1, res3=1, tbres=1)

    def make(name, specs, **options):
        create_stds(tools, "str3ds", name, specs, via="library", **options)

    make("A", [MapSpec(f"a{i}", i, day(i - 1), day(i)) for i in range(1, 5)])
    make("B", [MapSpec(f"b{i}", 10 * i, day(i - 1), day(i)) for i in range(1, 5)])
    for i in range(1, 4):
        tools.r3_mapcalc(expression=f"d{i} = depth()")
    register_stds(
        tools,
        "str3ds",
        "D",
        [MapSpec(f"d{i}", None, day(i - 1), day(i)) for i in range(1, 4)],
        via="library",
    )
    make("W", [MapSpec("w1", 100, day(0), day(2)), MapSpec("w2", 200, day(2), day(4))])
    tools.r3_mapcalc(expression="single = 1000")
    # Maps of E lie east of all others, so that no map is spatially related.
    tools.g_region(w=10, e=13)
    tools.r3_mapcalc(expression="e1 = 7")
    tools.r3_mapcalc(expression="e2 = 8")
    tools.g_region(w=0, e=3)
    register_stds(
        tools,
        "str3ds",
        "E",
        [MapSpec("e1", None, day(0), day(1)), MapSpec("e2", None, day(1), day(2))],
        via="library",
    )
    make("Q", [MapSpec("q1", 5, day(0, hours=12), day(1, hours=12))])
    make("Q2", [MapSpec("q2", 50, day(3, hours=12), day(4, hours=12))])
    make(
        "EQ",
        [
            MapSpec("eq1", 11, day(0), day(2)),
            MapSpec("eq2", 12, day(0), day(2)),
            MapSpec("eq3", 13, day(2), day(3)),
        ],
    )
    tools.r3_mapcalc(expression="z1 = null()")
    tools.r3_mapcalc(expression="z2 = 0")
    tools.r3_mapcalc(expression="z3 = if(depth() == 1, null(), 2)")
    register_stds(
        tools,
        "str3ds",
        "Z",
        [MapSpec(f"z{n}", None, day(n - 1), day(n)) for n in range(1, 4)],
        via="library",
    )
    make("I", [MapSpec(f"i{n}", n, day(n - 1)) for n in range(1, 4)])
    make(
        "RT",
        [MapSpec(f"x{n}", n, n - 1, n) for n in range(1, 4)],
        temporaltype="relative",
        unit="days",
    )
    tgis.register_maps_in_space_time_dataset(
        "raster_3d", None, "single", start="2001-01-02", end="2001-01-03"
    )


def _vector(tools, directory):
    tools.g_region(n=100, s=0, e=100, w=0, res=10)
    days = [day(n) for n in range(6)]

    def register(name, triples, **options):
        register_stds(
            tools,
            "stvds",
            name,
            [MapSpec(vector, None, start, end) for vector, start, end in triples],
            via="library",
            **options,
        )

    pa, pb, pc = [], [], []
    for i in (1, 2, 3):
        points_map(tools, directory, f"pa{i}", [(10 * j, 10 * i) for j in range(i)])
        points_map(tools, directory, f"pb{i}", [(3 + 10 * i, 5), (4 + 10 * i, 6)])
        points_map(tools, directory, f"pc{i}", [(0, 0), (10, 10)])
        pa.append((f"pa{i}", days[i - 1], days[i]))
        pb.append((f"pb{i}", days[i - 1], days[i]))
        pc.append((f"pc{i}", days[i - 1], days[i]))
    register("pa", pa)
    register("pb", pb)
    register("pc", pc)
    aa, ab, la = [], [], []
    for i, (xa, xb) in enumerate([(0, 5), (20, 25), (40, 70)], 1):
        square_area(tools, directory, f"aa{i}", xa, 0)
        square_area(tools, directory, f"ab{i}", xb, 0)
        horizontal_line(tools, directory, f"la{i}", xa, 5)
        aa.append((f"aa{i}", days[i - 1], days[i]))
        ab.append((f"ab{i}", days[i - 1], days[i]))
        la.append((f"la{i}", days[i - 1], days[i]))
    register("aa", aa)
    register("ab", ab)
    register("la", la)
    ac = []
    for i in (1, 2, 3):
        import_ascii_vector(
            tools,
            directory,
            f"ac{i}",
            "standard",
            "B 5\n 0 0\n 10 0\n 10 10\n 0 10\n 0 0\nC 1 1\n 5 5\n 1 1\n"
            "B 5\n 50 20\n 60 20\n 60 30\n 50 30\n 50 20\nC 1 1\n 55 25\n 1 1\n",
            flags="n",
        )
        ac.append((f"ac{i}", days[i - 1], days[i]))
    register("ac", ac)
    square_area(tools, directory, "wide1", 5, 0)
    square_area(tools, directory, "wide2", 45, 0)
    register("wide", [("wide1", days[0], days[2]), ("wide2", days[2], days[4])])
    # Maps without primitives
    for i in (1, 2):
        tools.v_edit(map=f"nv{i}", tool="create")
    register("ne", [("nv1", days[0], days[1]), ("nv2", days[1], days[2])])
    # Two maps with one time stamp, then a third
    square_area(tools, directory, "eq1", 0, 0)
    square_area(tools, directory, "eq2", 5, 0)
    square_area(tools, directory, "eq3", 20, 0)
    register(
        "eq",
        [
            ("eq1", days[0], days[1]),
            ("eq2", days[0], days[1]),
            ("eq3", days[1], days[2]),
        ],
    )
    # Time instances
    for i in (1, 2):
        points_map(tools, directory, f"pi{i}", [(5 * i, 5), (5 * i + 1, 6)])
    register("pi", [("pi1", days[0], None), ("pi2", days[1], None)])
    tools.g_copy(vector="pa1,rp1")
    tools.g_copy(vector="pa2,rp2")
    register(
        "rel", [("rp1", 0, 1), ("rp2", 1, 2)], temporaltype="relative", unit="days"
    )
    square_area(tools, directory, "ev", 2, 0)
    tgis.register_maps_in_space_time_dataset(
        "vector", None, "ev", start="2001-01-02", end="2001-01-03"
    )
