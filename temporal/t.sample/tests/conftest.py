"""Fixtures for the t.sample characterization tests

Intervals are written [start,end) with the end excluded. In the first group
the numbers are days of January 2001; in the later groups dN is the date
2001-01-01 plus N days.

The datasets are an interval sampler with one gap (samp_1 [1,3), samp_2
[5,7), samp_3 [7,9); the hole [3,5) is the gap), an instant input (in_1..in_6
on 2001-01-01..06), an interval input (sec_1 [1,3), sec_2 [3,5), sec_3 [5,7)),
an input equal to two granules (eq_1 [1,3), eq_2 [5,7)), relative mirrors
(rinput as instants on days 0..3, rsampler [0,2) and [4,6)) and str3ds and
stvds mirrors of input and sampler. Without -s the map geometry never enters
the printed matrix, which is read from the temporal relations alone, so the
vector seeds and the 3D region of these datasets are arbitrary.

The remaining datasets pin what the first ones cannot show; each is described
at its definition below.
"""

import pytest

from grass.temporal.testing.data import MapSpec, day, make_map, register_stds
from grass.tools import Tools

# Region of the datasets without per-map geometry, see sample_session.
DEFAULT_REGION = {
    "s": 0,
    "n": 80,
    "w": 0,
    "e": 120,
    "res": 10,
    "res3": 10,
    "t": 10,
    "b": 0,
}

# type option -> map kind of make_map
MAP_KIND = {"strds": "raster", "str3ds": "raster_3d"}


def _register(
    tools, kind, stds, temporaltype, times, *, order=None, regions=None, **options
):
    """Create a dataset of the given type, its maps and register them

    times maps each map name to its (start, end), end None for an instant. The
    maps are numbered from 1 in the order of times, and the number is the
    constant of a raster map or the seed of a v.random vector map. order lists
    the names in the order they are registered, if that differs. regions
    optionally maps a map name to the g.region arguments it is created under;
    the session region is restored afterwards. Vector maps come from
    v.random, which make_map does not offer, so they are made here.
    """
    numbers = {name: number for number, name in enumerate(times, start=1)}
    for name, number in numbers.items():
        if kind == "stvds":
            tools.v_random(output=name, npoints=1, seed=number, overwrite=True)
        else:
            make_map(
                tools,
                MAP_KIND[kind],
                name,
                number,
                region=(regions or {}).get(name),
                overwrite=True,
            )
    register_stds(
        tools,
        kind,
        stds,
        [MapSpec(name, numbers[name], *times[name]) for name in order or times],
        temporaltype=temporaltype,
        overwrite=True,
        **options,
    )


def _instants(names, first=0, step=1):
    """names as time points on the days first, first + step, ..."""
    return {name: (day(first + i * step), None) for i, name in enumerate(names)}


# Extents (w, e, s, n) of the spatial fixture, see sample_session.
SHAPES = {
    "identical": (40, 80, 20, 60),
    "partial": (60, 100, 40, 80),
    "inside": (50, 70, 30, 50),
    "covering": (0, 120, 0, 80),
    "east_edge": (80, 120, 20, 60),
    "corner": (80, 120, 60, 100),
    "north_edge": (40, 80, 60, 90),
    "one_cell_off": (90, 120, 20, 60),
}


def _region(w, e, s, n, **extra):
    return {"w": w, "e": e, "s": s, "n": n, "res": 10, "res3": 10, **extra}


def _register_areas(tools, stds, extents, times):
    """Create a stvds of area maps and register them

    extents maps a map name to the (w, e, s, n) of its single area, made with
    v.in.region so that the vector extent equals the region. v.random points
    would give point extents, which can be inside or disjoint but cannot be
    identical to the sampler's extent or share an edge with it.
    """
    for name, extent in extents.items():
        tools.g_region(**_region(*extent))
        tools.v_in_region(output=name, overwrite=True)
    tools.g_region(**DEFAULT_REGION)
    register_stds(
        tools,
        "stvds",
        stds,
        [MapSpec(name, 0, *times[name]) for name in extents],
        overwrite=True,
    )


@pytest.fixture(scope="module")
def sample_session(xy_module_session):
    # consistent_return_value: a run without stdout (the error paths) still
    # returns a result, whose stderr the tests compare.
    tools = Tools(session=xy_module_session, consistent_return_value=True)
    tools.g_region(**DEFAULT_REGION)

    in_names = [f"in_{i}" for i in range(1, 7)]
    _register(tools, "strds", "input", "absolute", _instants(in_names))
    _register(
        tools,
        "strds",
        "input2",
        "absolute",
        {
            "sec_1": (day(0), day(2)),
            "sec_2": (day(2), day(4)),
            "sec_3": (day(4), day(6)),
        },
    )
    _register(
        tools,
        "strds",
        "sampler",
        "absolute",
        {
            "samp_1": (day(0), day(2)),
            "samp_2": (day(4), day(6)),
            "samp_3": (day(6), day(8)),
        },
    )
    _register(
        tools,
        "strds",
        "input_eq",
        "absolute",
        {"eq_1": (day(0), day(2)), "eq_2": (day(4), day(6))},
    )
    _register(
        tools,
        "strds",
        "rinput",
        "relative",
        {f"rin_{i}": (i - 1, None) for i in range(1, 5)},
        unit="days",
    )
    _register(
        tools,
        "strds",
        "rsampler",
        "relative",
        {"rsamp_1": (0, 2), "rsamp_2": (4, 6)},
        unit="days",
    )
    _register(
        tools,
        "str3ds",
        "input3",
        "absolute",
        _instants([f"in3_{i}" for i in range(1, 7)]),
    )
    _register(
        tools,
        "str3ds",
        "sampler3",
        "absolute",
        {
            "samp3_1": (day(0), day(2)),
            "samp3_2": (day(4), day(6)),
            "samp3_3": (day(6), day(8)),
        },
    )
    _register(
        tools,
        "stvds",
        "inputv",
        "absolute",
        _instants([f"inv_{i}" for i in range(1, 7)]),
    )
    _register(
        tools,
        "stvds",
        "samplerv",
        "absolute",
        {
            "sampv_1": (day(0), day(2)),
            "sampv_2": (day(4), day(6)),
            "sampv_3": (day(6), day(8)),
        },
    )

    # Several relations per granule. Sampler: og_1 [d10,d20), og_2
    # [d20,d30). The input maps are named so that the alphabetical order
    # differs from the time order, and the register file lists them in the
    # reverse of the dictionary order; whatever orders the printed maps is
    # therefore visible.
    ord_maps = {
        "yy_during": (5, 25),
        "xx_starts": (10, 15),
        "zz_early": (12, 15),
        "aa_late": (16, 19),
        "ww_finishes": (15, 20),
        "vv_ovl_early": (8, 12),
        "uu_ovl_late": (18, 25),
        "tt_before": (0, 10),
        "ss_equal": (10, 20),
        "rr_far": (40, 45),
        "qq_in_og2": (22, 28),
        "pp_after": (20, 25),
    }
    _register(
        tools,
        "strds",
        "ordsamp",
        "absolute",
        {"og_1": (day(10), day(20)), "og_2": (day(20), day(30))},
    )
    _register(
        tools,
        "strds",
        "ordin",
        "absolute",
        {n: (day(a), day(b)) for n, (a, b) in ord_maps.items()},
        order=list(reversed(ord_maps)),
    )
    # Maps with the same start time d12: tie_a and tie_d end on d17, tie_b
    # and tie_c on d15. tiein registers tie_b before tie_a, tiein2 the
    # other way round, tiein3 registers tie_d before tie_c.
    spans = {"tie_b": 15, "tie_a": 17, "tie_c": 15, "tie_d": 17}
    for stds, names in (
        ("tiein", ("tie_b", "tie_a")),
        ("tiein2", ("tie_a", "tie_b")),
        ("tiein3", ("tie_d", "tie_c")),
    ):
        _register(
            tools,
            "strds",
            stds,
            "absolute",
            {n: (day(12), day(spans[n])) for n in names},
        )

    # Maps outside the sampler: rim_1 is before the first granule, rim_2
    # sits on the end d8 of the last granule (the end is excluded), rim_3
    # is after it.
    _register(
        tools,
        "strds",
        "rim",
        "absolute",
        {"rim_1": (day(-1), None), "rim_2": (day(8), None), "rim_3": (day(9), None)},
    )

    # Granules that are not whole days: tg_1 [d0,d0+6h), tg_2
    # [d0+6h,d0+18h), tg_3 [d31,d59) (1 February to 1 March, 28 days);
    # the gap between tg_2 and tg_3 is a row of its own.
    _register(
        tools,
        "strds",
        "tsamp",
        "absolute",
        {
            "tg_1": (day(0), day(0, hours=6)),
            "tg_2": (day(0, hours=6), day(0, hours=18)),
            "tg_3": (day(31), day(59)),
        },
    )
    _register(
        tools,
        "strds",
        "tin",
        "absolute",
        {
            "tin_1": (day(0, hours=3), None),
            "tin_2": (day(0, hours=12), None),
            "tin_3": (day(45, hours=12), None),
        },
    )

    # Relative intervals against rsampler [0,2) and [4,6).
    _register(
        tools,
        "strds",
        "rint",
        "relative",
        {"rint_1": (0, 1), "rint_2": (1, 3), "rint_3": (3, 4)},
        unit="days",
    )

    # A sampler of instants, which t.sample refuses.
    _register(
        tools,
        "strds",
        "isamp",
        "absolute",
        _instants([f"isamp_{i}" for i in range(1, 4)]),
    )

    # Spatial extents for -s. The sampler granules are sp_g1 [d0,d8) over
    # (w 40, e 80, s 20, n 60) and sp_g2 [d8,d16) over (w 0, e 40, s 0,
    # n 20). spin_1..spin_16 are instants on d0..d15, so spin_1..8 lie in
    # sp_g1 and spin_9..16 in sp_g2; spin_k has the extent
    # number ((k - 1) mod 8) + 1 of SHAPES, so spin_1 and spin_9 are
    # identical to sp_g1 and spin_8 and spin_16 are one_cell_off. sp_g2
    # touches spin_9 only at the corner (40, 20).
    sp_regions = {
        "sp_g1": _region(40, 80, 20, 60),
        "sp_g2": _region(0, 40, 0, 20),
    }
    _register(
        tools,
        "strds",
        "spsamp",
        "absolute",
        {"sp_g1": (day(0), day(8)), "sp_g2": (day(8), day(16))},
        regions=sp_regions,
    )
    shapes = list(SHAPES.values())
    spin = [f"spin_{i}" for i in range(1, 17)]
    _register(
        tools,
        "strds",
        "spin",
        "absolute",
        _instants(spin),
        regions={n: _region(*shapes[i % 8]) for i, n in enumerate(spin)},
    )

    # Gap rows under -s. The gap between the two granules gets the spatial
    # extent (0, 0, 0, 0), a point at the origin, so only maps touching the
    # origin can relate to it. sg_1 [d0,d4) lies over (w 40, e 80, s 20,
    # n 60), sg_2 [d8,d12) over (w 0, e 40, s 0, n 20), the gap is
    # [d4,d8). The instants gap_1..gap_4 lie in the gap: gap_1 is the cell
    # west and south of the origin (w -10, e 0, s -10, n 0) and touches it
    # at a corner, gap_2 covers the whole region, gap_3 (w 10, e 20, s 10,
    # n 20) misses it, gap_4 (w 0, e 10, s 0, n 10) has the origin as a
    # corner. gap_5 on d1 lies in sg_1 over the same extent as sg_1, gap_6
    # on d9 in sg_2 over the whole region.
    gap_regions = {
        "sg_1": _region(40, 80, 20, 60),
        "sg_2": _region(0, 40, 0, 20),
        "gap_1": _region(-10, 0, -10, 0),
        "gap_2": _region(0, 120, 0, 80),
        "gap_3": _region(10, 20, 10, 20),
        "gap_4": _region(0, 10, 0, 10),
        "gap_5": _region(40, 80, 20, 60),
        "gap_6": _region(0, 120, 0, 80),
    }
    _register(
        tools,
        "strds",
        "spgap",
        "absolute",
        {"sg_1": (day(0), day(4)), "sg_2": (day(8), day(12))},
        regions=gap_regions,
    )
    gap_days = {
        "gap_1": 4,
        "gap_2": 5,
        "gap_3": 6,
        "gap_4": 7,
        "gap_5": 1,
        "gap_6": 9,
    }
    _register(
        tools,
        "strds",
        "spgapin",
        "absolute",
        {n: (day(d), None) for n, d in gap_days.items()},
        regions=gap_regions,
    )

    # The same for str3ds: sp3_g [d0,d8) over (w 40, e 80, s 20, n 60,
    # b 0, t 10). sp3_1 has the same x/y but lies at b 100, t 110; sp3_2
    # is one cell east of the granule at b 0, t 10; sp3_3 touches the
    # granule along x = 80 at b 0, t 10.
    _register(
        tools,
        "str3ds",
        "sp3samp",
        "absolute",
        {"sp3_g": (day(0), day(8))},
        regions={"sp3_g": _region(40, 80, 20, 60, b=0, t=10)},
    )
    _register(
        tools,
        "str3ds",
        "sp3in",
        "absolute",
        {"sp3_1": (day(1), None), "sp3_2": (day(2), None), "sp3_3": (day(3), None)},
        regions={
            "sp3_1": _region(40, 80, 20, 60, b=100, t=110),
            "sp3_2": _region(90, 120, 20, 60, b=0, t=10),
            "sp3_3": _region(80, 120, 20, 60, b=0, t=10),
        },
    )

    # A sampler whose first two granules start together: eqs_1 [d0,d5)
    # and eqs_2 [d0,d2), so that the longer one has the smaller id, then the
    # gap [d5,d7) and eqs_3 [d7,d9). The topology is invalid (the granules
    # overlap). The instants eqi_1 (d1) and eqi_2 (d3) lie in eqs_1, eqi_1
    # also in eqs_2, eqi_3 (d6) in the gap and eqi_4 (d8) in eqs_3.
    _register(
        tools,
        "strds",
        "eqsamp",
        "absolute",
        {
            "eqs_1": (day(0), day(5)),
            "eqs_2": (day(0), day(2)),
            "eqs_3": (day(7), day(9)),
        },
    )
    _register(
        tools,
        "strds",
        "eqin",
        "absolute",
        {
            "eqi_1": (day(1), None),
            "eqi_2": (day(3), None),
            "eqi_3": (day(6), None),
            "eqi_4": (day(8), None),
        },
    )

    # Vector maps with layers: lay:1 and lay:2 are ids of the one map lay,
    # registered as separate instants on d1 and d2. v.random writes layer
    # 1 only and t.register does not check the layer, so the ids are
    # registered whether or not the layer holds data.
    tools.v_random(output="lay", npoints=1, seed=1, overwrite=True)
    register_stds(
        tools,
        "stvds",
        "layin",
        [MapSpec("lay:1", 1, day(1)), MapSpec("lay:2", 2, day(2))],
        overwrite=True,
    )
    _register(
        tools,
        "stvds",
        "laysamp",
        "absolute",
        {"laysamp_1": (day(0), day(3))},
    )

    # Area vectors for -s on stvds: svg [d0,d8) over (w 40, e 80, s 20,
    # n 60). sv_1 on d1 has the same extent, sv_2 on d2 lies inside, sv_3
    # on d3 is one cell east (w 90) and disjoint, sv_4 on d4 shares the
    # edge x = 80.
    _register_areas(
        tools,
        "svsamp",
        {"svg": SHAPES["identical"]},
        {"svg": (day(0), day(8))},
    )
    sv_shapes = {
        "sv_1": SHAPES["identical"],
        "sv_2": SHAPES["inside"],
        "sv_3": SHAPES["one_cell_off"],
        "sv_4": SHAPES["east_edge"],
    }
    _register_areas(
        tools,
        "svin",
        sv_shapes,
        {n: (day(i), None) for i, n in enumerate(sv_shapes, start=1)},
    )
    return tools
