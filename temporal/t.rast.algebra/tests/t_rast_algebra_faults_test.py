"""Test the granularity of a month series from a month end in t.rast.algebra

The core algebra takes the granularity of the library: a month step that is
cut to the end of a shorter month is a month, so the series from 31 January
has the granularity "1 month". The time suffix "gran" names its result maps
by the month, the granularity mode (-g) has a granule per month, and tsnap()
ends a last time instance one month later, on the month series of the first
map. The classic algebra (-c, or GRASS_TEMPORAL_ALGEBRA=classic) keeps the
granularity "1 day" of the releases before GRASS 8.6;
grass_temporal_classic_frozen_library_test.py holds its results.
"""

from datetime import datetime
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import list_maps
from grass.tools import Tools

D = datetime
ENDS = [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)]

# Every test chooses its algebra itself: the core by the variable, the classic
# algebra by -c.
pytestmark = pytest.mark.fixed_algebra


@pytest.fixture(scope="module")
def core_env(xy_module_session):
    return {**xy_module_session.env, "GRASS_TEMPORAL_ALGEBRA": "core"}


@pytest.fixture(scope="module")
def core_tools(core_env):
    tools = Tools(env=core_env, consistent_return_value=True, quiet=True)
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


@pytest.mark.parametrize(
    ("flags", "algebra", "names"),
    [
        ("", "core", ["n_2026_01", "n_2026_02", "n_2026_03"]),
        ("c", "core", ["nc_2026_01_31", "nc_2026_02_28", "nc_2026_03_31"]),
        ("", "classic", ["nv_2026_01_31", "nv_2026_02_28", "nv_2026_03_31"]),
    ],
    ids=["core", "classic flag", "classic variable"],
)
def test_gran_suffix_of_month_end_series(core_tools, core_env, flags, algebra, names):
    basename = names[0].split("_")[0]
    output = basename.upper()
    core_tools.t_rast_algebra(
        expression=f"{output} = MON * 1",
        basename=basename,
        suffix="gran",
        flags=flags,
        env={**core_env, "GRASS_TEMPORAL_ALGEBRA": algebra},
    )
    assert [row.name for row in list_maps(core_tools, "strds", output)] == names


INSTANTS = {
    "to 31 March": [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31)],
    "to 30 April": [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)],
}


@pytest.mark.parametrize(
    ("series", "flags", "last_end"),
    [
        # The core takes the granularity of the library, one month, and counts
        # the end from the first map: 31 March plus one month is 30 April,
        # 30 April plus one month on the series from 31 January is 31 May.
        ("to 31 March", "", "2026-04-30 00:00:00"),
        ("to 30 April", "", "2026-05-31 00:00:00"),
        # The classic algebra computes the granularity one day.
        ("to 31 March", "c", "2026-04-01 00:00:00"),
        ("to 30 April", "c", "2026-05-01 00:00:00"),
    ],
    ids=["core 31 March", "core 30 April", "classic 31 March", "classic 30 April"],
)
def test_tsnap_ends_last_instant_of_month_end_series(
    core_tools, series, flags, last_end
):
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
    output = f"S{name}{flags.upper()}"
    core_tools.t_rast_algebra(
        expression=f"{output} = tsnap({name})", basename=output.lower(), flags=flags
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
