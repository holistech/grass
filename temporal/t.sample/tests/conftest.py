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

import os
from datetime import datetime, timedelta

import pytest

import grass.script as gs
from grass.tools import Tools

# type option -> map type of t.register
MAP_TYPE = {"strds": "raster", "str3ds": "raster_3d", "stvds": "vector"}

DAY0 = datetime(2001, 1, 1)

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


def day(offset, hours=0):
    """Timestamp of the day offset (and hours) relative to 2001-01-01"""
    return (DAY0 + timedelta(days=offset, hours=hours)).strftime("%Y-%m-%d %H:%M:%S")


def _make_map(tools, kind, name, number):
    if kind == "strds":
        tools.r_mapcalc(expression=f"{name} = {number}", overwrite=True)
    elif kind == "str3ds":
        tools.r3_mapcalc(expression=f"{name} = {number}", overwrite=True)
    else:
        tools.v_random(output=name, npoints=1, seed=number, overwrite=True)


def _register(
    tools, kind, stds, temporaltype, maps, rows, tmp_path, regions=None, **reg
):
    """Create a dataset of the given type, its maps and register them

    maps are the map names in order; rows are the lines of the register file
    (a bare name for an instant input with start/increment, otherwise
    "name|start|end"). regions optionally maps a map name to the g.region
    arguments it is created under; the default region is restored afterwards.
    """
    for number, name in enumerate(maps, start=1):
        if regions and name in regions:
            tools.g_region(**regions[name])
        _make_map(tools, kind, name, number)
        if regions and name in regions:
            tools.g_region(**DEFAULT_REGION)
    tools.t_create(
        type=kind,
        output=stds,
        temporaltype=temporaltype,
        title=stds,
        description=stds,
        overwrite=True,
    )
    file = tmp_path / f"{stds}.txt"
    file.write_text("\n".join(rows) + "\n")
    tools.t_register(type=MAP_TYPE[kind], input=stds, file=file, overwrite=True, **reg)


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


@pytest.fixture(scope="module")
def sample_session(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("t_sample")
    project = tmp_path / "project"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        # consistent_return_value: a run without stdout (the error paths) still
        # returns a result, whose stderr the tests compare.
        tools = Tools(session=session, consistent_return_value=True)
        tools.g_region(**DEFAULT_REGION)

        _register(
            tools,
            "strds",
            "input",
            "absolute",
            [f"in_{i}" for i in range(1, 7)],
            [f"in_{i}" for i in range(1, 7)],
            tmp_path,
            start="2001-01-01",
            increment="1 days",
        )
        _register(
            tools,
            "strds",
            "input2",
            "absolute",
            [f"sec_{i}" for i in range(1, 4)],
            [
                "sec_1|2001-01-01|2001-01-03",
                "sec_2|2001-01-03|2001-01-05",
                "sec_3|2001-01-05|2001-01-07",
            ],
            tmp_path,
        )
        _register(
            tools,
            "strds",
            "sampler",
            "absolute",
            [f"samp_{i}" for i in range(1, 4)],
            [
                "samp_1|2001-01-01|2001-01-03",
                "samp_2|2001-01-05|2001-01-07",
                "samp_3|2001-01-07|2001-01-09",
            ],
            tmp_path,
        )
        _register(
            tools,
            "strds",
            "input_eq",
            "absolute",
            ["eq_1", "eq_2"],
            ["eq_1|2001-01-01|2001-01-03", "eq_2|2001-01-05|2001-01-07"],
            tmp_path,
        )
        _register(
            tools,
            "strds",
            "rinput",
            "relative",
            [f"rin_{i}" for i in range(1, 5)],
            [f"rin_{i}" for i in range(1, 5)],
            tmp_path,
            start=0,
            unit="days",
            increment=1,
        )
        _register(
            tools,
            "strds",
            "rsampler",
            "relative",
            ["rsamp_1", "rsamp_2"],
            ["rsamp_1|0|2", "rsamp_2|4|6"],
            tmp_path,
            unit="days",
        )
        _register(
            tools,
            "str3ds",
            "input3",
            "absolute",
            [f"in3_{i}" for i in range(1, 7)],
            [f"in3_{i}" for i in range(1, 7)],
            tmp_path,
            start="2001-01-01",
            increment="1 days",
        )
        _register(
            tools,
            "str3ds",
            "sampler3",
            "absolute",
            [f"samp3_{i}" for i in range(1, 4)],
            [
                "samp3_1|2001-01-01|2001-01-03",
                "samp3_2|2001-01-05|2001-01-07",
                "samp3_3|2001-01-07|2001-01-09",
            ],
            tmp_path,
        )
        _register(
            tools,
            "stvds",
            "inputv",
            "absolute",
            [f"inv_{i}" for i in range(1, 7)],
            [f"inv_{i}" for i in range(1, 7)],
            tmp_path,
            start="2001-01-01",
            increment="1 days",
        )
        _register(
            tools,
            "stvds",
            "samplerv",
            "absolute",
            [f"sampv_{i}" for i in range(1, 4)],
            [
                "sampv_1|2001-01-01|2001-01-03",
                "sampv_2|2001-01-05|2001-01-07",
                "sampv_3|2001-01-07|2001-01-09",
            ],
            tmp_path,
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
            ["og_1", "og_2"],
            [f"og_1|{day(10)}|{day(20)}", f"og_2|{day(20)}|{day(30)}"],
            tmp_path,
        )
        _register(
            tools,
            "strds",
            "ordin",
            "absolute",
            list(ord_maps),
            [f"{n}|{day(a)}|{day(b)}" for n, (a, b) in reversed(ord_maps.items())],
            tmp_path,
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
                list(names),
                [f"{n}|{day(12)}|{day(spans[n])}" for n in names],
                tmp_path,
            )

        # Maps outside the sampler: rim_1 is before the first granule, rim_2
        # sits on the end d8 of the last granule (the end is excluded), rim_3
        # is after it.
        _register(
            tools,
            "strds",
            "rim",
            "absolute",
            ["rim_1", "rim_2", "rim_3"],
            [f"rim_1|{day(-1)}", f"rim_2|{day(8)}", f"rim_3|{day(9)}"],
            tmp_path,
        )

        # Granules that are not whole days: tg_1 [d0,d0+6h), tg_2
        # [d0+6h,d0+18h), tg_3 [d31,d59) (1 February to 1 March, 28 days);
        # the gap between tg_2 and tg_3 is a row of its own.
        _register(
            tools,
            "strds",
            "tsamp",
            "absolute",
            ["tg_1", "tg_2", "tg_3"],
            [
                f"tg_1|{day(0)}|{day(0, 6)}",
                f"tg_2|{day(0, 6)}|{day(0, 18)}",
                f"tg_3|{day(31)}|{day(59)}",
            ],
            tmp_path,
        )
        _register(
            tools,
            "strds",
            "tin",
            "absolute",
            ["tin_1", "tin_2", "tin_3"],
            [f"tin_1|{day(0, 3)}", f"tin_2|{day(0, 12)}", f"tin_3|{day(45, 12)}"],
            tmp_path,
        )

        # Relative intervals against rsampler [0,2) and [4,6).
        _register(
            tools,
            "strds",
            "rint",
            "relative",
            ["rint_1", "rint_2", "rint_3"],
            ["rint_1|0|1", "rint_2|1|3", "rint_3|3|4"],
            tmp_path,
            unit="days",
        )

        # A sampler of instants, which t.sample refuses.
        _register(
            tools,
            "strds",
            "isamp",
            "absolute",
            [f"isamp_{i}" for i in range(1, 4)],
            [f"isamp_{i}" for i in range(1, 4)],
            tmp_path,
            start="2001-01-01",
            increment="1 days",
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
            ["sp_g1", "sp_g2"],
            [f"sp_g1|{day(0)}|{day(8)}", f"sp_g2|{day(8)}|{day(16)}"],
            tmp_path,
            regions=sp_regions,
        )
        shapes = list(SHAPES.values())
        spin = [f"spin_{i}" for i in range(1, 17)]
        _register(
            tools,
            "strds",
            "spin",
            "absolute",
            spin,
            [f"{name}|{day(i)}" for i, name in enumerate(spin)],
            tmp_path,
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
            ["sg_1", "sg_2"],
            [f"sg_1|{day(0)}|{day(4)}", f"sg_2|{day(8)}|{day(12)}"],
            tmp_path,
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
            list(gap_days),
            [f"{n}|{day(d)}" for n, d in gap_days.items()],
            tmp_path,
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
            ["sp3_g"],
            [f"sp3_g|{day(0)}|{day(8)}"],
            tmp_path,
            regions={"sp3_g": _region(40, 80, 20, 60, b=0, t=10)},
        )
        _register(
            tools,
            "str3ds",
            "sp3in",
            "absolute",
            ["sp3_1", "sp3_2", "sp3_3"],
            [f"sp3_1|{day(1)}", f"sp3_2|{day(2)}", f"sp3_3|{day(3)}"],
            tmp_path,
            regions={
                "sp3_1": _region(40, 80, 20, 60, b=100, t=110),
                "sp3_2": _region(90, 120, 20, 60, b=0, t=10),
                "sp3_3": _region(80, 120, 20, 60, b=0, t=10),
            },
        )
        yield tools
