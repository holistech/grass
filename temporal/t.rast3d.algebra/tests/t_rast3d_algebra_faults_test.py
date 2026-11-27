"""Test month-end granularity, the search path and map names of t.rast3d.algebra

The algebra takes the granularity of the library: the series from
31 January (28 February, 31 March) has the granularity "1 month", so the
granularity mode (-g) has a granule per month.

The algebra looks for a dataset name without a mapset in the current mapset
and then in the search path. It numbers only the maps it registers.
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


def test_granularity_mode_of_month_end_series(xy_module_session):
    tools = Tools(
        session=xy_module_session,
        consistent_return_value=True,
        quiet=True,
        overwrite=True,
    )
    tools.g_region(n=1, s=0, e=1, w=0, t=1, b=0, res=1, res3=1)
    create_stds(
        tools,
        "str3ds",
        "MON",
        [
            MapSpec(f"mon_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ENDS), start=1)
        ],
        overwrite=True,
    )
    tools.t_rast3d_algebra(expression="G = MON * 1", basename="g", flags="g")
    rows = list_maps(tools, "str3ds", "G")
    assert len(rows) == 3
    assert (rows[0].start, rows[-1].end) == (
        "2026-01-31 00:00:00",
        "2026-04-30 00:00:00",
    )


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
            each.g_region(n=1, s=0, e=1, w=0, t=1, b=0, res=1, res3=1)
        create_daily_stds(other_tools, "str3ds", ["A"], 2, map_prefix="a")
        tools.g_mapsets(operation="add", mapset="other")
        yield tools


def test_core_finds_dataset_in_search_path(work):
    work.t_rast3d_algebra(expression="FOUND = A * 2", basename="found")

    rows = list_maps(work, "str3ds", "FOUND")
    assert [(row.name, row.min) for row in rows] == [("found_0", 2), ("found_1", 4)]


def test_core_numbers_only_registered_maps(work):
    basename = "num"
    names = ["num_0"]
    # The first map is null everywhere and is not registered.
    work.t_rast3d_algebra(
        expression=f"{basename.upper()} = if(A@other > 1, A@other, null())",
        basename=basename,
    )

    rows = list_maps(work, "str3ds", basename.upper())
    assert [(row.name, row.min) for row in rows] == [(names[0], 2)]
    assert work.g_list(type="raster_3d", pattern=f"{basename}_*").stdout.split() == (
        names
    )
