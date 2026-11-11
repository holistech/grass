"""Test month-end granularity, the search path and map names of t.rast.algebra

The algebra takes the granularity of the library: a month step that is cut to
the end of a shorter month is a month, so the series from 31 January has the
granularity "1 month". The time suffix "gran" names its result maps by the
month, the granularity mode (-g) has a granule per month, and tsnap() ends a
last time instance one month later, on the month series of the first map. The
releases before GRASS 8.6 computed the granularity "1 day" for this series. In
the granularity mode, datasets whose starts differ in a finer unit than their
common granularity are sampled in granules of that finer unit.

The algebra looks for a dataset name without a mapset in the current mapset
and then in the search path. It pads numbered map names to the NN digits of
the suffix num%NN and numbers only the maps it registers.
"""

from datetime import datetime
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_daily_stds, create_stds
from grass.temporal.testing.readback import list_maps
from grass.temporal.testing.session import mapset_session, project_session
from grass.tools import Tools

D = datetime
ENDS = [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)]


@pytest.fixture(scope="module")
def core_tools(xy_module_session):
    tools = Tools(session=xy_module_session, consistent_return_value=True, quiet=True)
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    create_stds(
        tools,
        "strds",
        "MON",
        [
            MapSpec(f"mon_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ENDS), start=1)
        ],
    )
    return tools


def test_gran_suffix_of_month_end_series(core_tools):
    core_tools.t_rast_algebra(expression="N = MON * 1", basename="n", suffix="gran")
    assert [row.name for row in list_maps(core_tools, "strds", "N")] == [
        "n_2026_01",
        "n_2026_02",
        "n_2026_03",
    ]


INSTANTS = {
    "to 31 March": [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31)],
    "to 30 April": [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)],
}


@pytest.mark.parametrize(
    ("series", "last_end"),
    [
        # The core takes the granularity of the library, one month, and counts
        # the end from the first map: 31 March plus one month is 30 April,
        # 30 April plus one month on the series from 31 January is 31 May.
        ("to 31 March", "2026-04-30 00:00:00"),
        ("to 30 April", "2026-05-31 00:00:00"),
    ],
    ids=["core 31 March", "core 30 April"],
)
def test_tsnap_ends_last_instant_of_month_end_series(core_tools, series, last_end):
    name = "I" + series.split()[-1].upper()
    if not core_tools.t_list(type="strds", where=f"name = '{name}'").stdout.strip():
        create_stds(
            core_tools,
            "strds",
            name,
            [
                MapSpec(f"{name.lower()}_{number}", number, start)
                for number, start in enumerate(INSTANTS[series], start=1)
            ],
        )
    output = f"S{name}"
    core_tools.t_rast_algebra(
        expression=f"{output} = tsnap({name})", basename=output.lower()
    )
    rows = list_maps(core_tools, "strds", output)
    assert [row.start for row in rows] == [
        f"{start:%Y-%m-%d %H:%M:%S}" for start in INSTANTS[series]
    ]
    assert rows[-1].end == last_end


def test_granularity_mode_has_a_granule_per_month(core_tools):
    core_tools.t_rast_algebra(expression="G = MON * 1", basename="g", flags="g")
    rows = list_maps(core_tools, "strds", "G")
    assert [(row.start, row.end, row.min) for row in rows] == [
        ("2026-01-31 00:00:00", "2026-02-28 00:00:00", 1),
        ("2026-02-28 00:00:00", "2026-03-31 00:00:00", 2),
        ("2026-03-31 00:00:00", "2026-04-30 00:00:00", 3),
    ]


# A month series from the first and one from the fifteenth: the common granule
# of their granularities "1 month" is the day, the finest unit in which their
# starts differ, so that a granule starts with each map of both datasets.
FIRSTS = [D(2001, 1, 1), D(2001, 2, 1), D(2001, 3, 1), D(2001, 4, 1)]
FIFTEENTHS = [D(2001, 1, 15), D(2001, 2, 15), D(2001, 3, 15), D(2001, 4, 15)]


def test_granularity_mode_aligns_datasets_that_start_on_other_days(core_tools):
    for name, starts, value in (("FIRSTS", FIRSTS, 1), ("FIFTEENTHS", FIFTEENTHS, 10)):
        if not core_tools.t_list(type="strds", where=f"name = '{name}'").stdout.strip():
            create_stds(
                core_tools,
                "strds",
                name,
                [
                    MapSpec(f"{name.lower()}_{number}", value * number, start, end)
                    for number, (start, end) in enumerate(pairwise(starts), start=1)
                ],
            )
    output = "ALIGNED_G"
    core_tools.t_rast_algebra(
        expression=f"{output} = FIRSTS + FIFTEENTHS",
        basename=output.lower(),
        flags="g",
    )
    rows = list_maps(core_tools, "strds", output)
    # Daily granules from 15 January, where both datasets have maps, to
    # 1 April, where the month series from the first ends
    assert (rows[0].start, rows[-1].end) == (
        "2001-01-15 00:00:00",
        "2001-04-01 00:00:00",
    )
    sums = [row.min for row in rows]
    assert [(value, sums.count(value)) for value in sorted(set(sums))] == [
        (11, 17),
        (12, 14),
        (22, 14),
        (23, 14),
        (33, 17),
    ]


@pytest.fixture(scope="module")
def work(tmp_path_factory):
    """Tools in the mapset "work", with the mapset "other" in its search path

    The dataset A with the maps a_1 (1) and a_2 (2) of one day each is in
    "other".
    """
    project = tmp_path_factory.mktemp("search_path") / "project"
    with (
        project_session(project, mapset="work") as work_session,
        mapset_session(work_session, "other") as other,
    ):
        tools = Tools(session=work_session, consistent_return_value=True, quiet=True)
        other_tools = Tools(session=other, consistent_return_value=True, quiet=True)
        for each in (tools, other_tools):
            each.g_region(n=1, s=0, e=1, w=0, res=1)
        create_daily_stds(other_tools, "strds", ["A"], 2, map_prefix="a")
        tools.g_mapsets(operation="add", mapset="other")
        yield tools


def test_core_finds_dataset_in_search_path(work):
    work.t_rast_algebra(expression="FOUND = A * 2", basename="found")

    rows = list_maps(work, "strds", "FOUND")
    assert [(row.name, row.min) for row in rows] == [("found_0", 2), ("found_1", 4)]


def test_core_suffix_num_digits(work):
    work.t_rast_algebra(
        expression="DIGITS = A@other * 2", basename="d", suffix="num%03"
    )

    rows = list_maps(work, "strds", "DIGITS")
    assert [row.name for row in rows] == ["d_000", "d_001"]


@pytest.fixture(scope="module")
def months(core_tools):
    """The dataset MONTHS of five maps from January 2001, one month each"""
    create_stds(
        core_tools,
        "strds",
        "MONTHS",
        [
            MapSpec(
                f"month_{number}", number, D(2001, number, 1), D(2001, number + 1, 1)
            )
            for number in range(1, 6)
        ],
    )
    return core_tools


# The condition reads the map and its two predecessors. The core also computes
# a map for February, where MONTHS[-2] has no map, which is null everywhere and
# not registered.
DOY = (
    "if(MONTHS > 0.0 && MONTHS[-1] > 0.0 && MONTHS[-2] > 0.0, start_doy(MONTHS, -1), 0)"
)


def test_core_numbers_only_registered_maps(months):
    basename = "doy"
    months.t_rast_algebra(expression=f"{basename.upper()} = {DOY}", basename=basename)

    rows = list_maps(months, "strds", basename.upper())
    assert [(row.name, row.start, row.min) for row in rows] == [
        (f"{basename}_0", "2001-03-01 00:00:00", 32),
        (f"{basename}_1", "2001-04-01 00:00:00", 60),
        (f"{basename}_2", "2001-05-01 00:00:00", 91),
    ]
    assert months.g_list(type="raster", pattern=f"{basename}_*").stdout.split() == [
        f"{basename}_0",
        f"{basename}_1",
        f"{basename}_2",
    ]


def test_core_keeps_the_numbers_with_null_maps_registered(months):
    months.t_rast_algebra(expression=f"DOYN = {DOY}", basename="doyn", flags="n")

    rows = list_maps(months, "strds", "DOYN")
    assert [(row.name, row.min) for row in rows] == [
        ("doyn_0", None),
        ("doyn_1", 32),
        ("doyn_2", 60),
        ("doyn_3", 91),
    ]


def test_core_dry_run_shows_the_names_of_every_computed_map(months):
    result = months.t_rast_algebra(
        expression=f"DOYD = {DOY}", basename="doyd", flags="d"
    )

    for number in range(4):
        assert f"'doyd_{number}'" in result.stdout
    assert not months.g_list(type="raster", pattern="doyd_*").stdout
