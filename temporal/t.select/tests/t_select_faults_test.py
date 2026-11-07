"""Test the search path and the calendar functions on relative time in t.select

The core algebra looks for a dataset name without a mapset in the current
mapset and then in the search path, the classic algebra (-c) in the current
mapset only. A calendar function such as start_month() needs absolute time;
on relative time both algebras stop with an error and create no dataset.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_daily_stds, create_stds
from grass.temporal.testing.readback import list_maps, message
from grass.temporal.testing.session import mapset_session, project_session
from grass.tools import ToolError, Tools

# Every test chooses its algebra itself: the core by the variable, the classic
# algebra by -c.
pytestmark = pytest.mark.fixed_algebra


@pytest.fixture(scope="module")
def work(tmp_path_factory):
    """Tools in the mapset "work", with the mapset "other" in its search path

    The dataset A with the daily maps a_1 and a_2 is in "other". The dataset
    R in "work" has the maps r_1 and r_2 of relative time, days 0 to 2 and 2
    to 4. The tools run the core algebra unless a test passes -c.
    """
    project = tmp_path_factory.mktemp("search_path") / "project"
    with (
        project_session(project, mapset="work") as work_session,
        mapset_session(work_session, "other") as other,
    ):
        env = {**work_session.env, "GRASS_TEMPORAL_ALGEBRA": "core"}
        tools = Tools(env=env, consistent_return_value=True, quiet=True)
        other_tools = Tools(session=other, consistent_return_value=True, quiet=True)
        for each in (tools, other_tools):
            each.g_region(n=1, s=0, e=1, w=0, res=1)
        create_daily_stds(other_tools, "strds", ["A"], 2, map_prefix="a")
        create_stds(
            tools,
            "strds",
            "R",
            [MapSpec("r_1", 1, 0, 2), MapSpec("r_2", 2, 2, 4)],
            temporaltype="relative",
            unit="days",
        )
        tools.g_mapsets(operation="add", mapset="other")
        yield tools


def test_core_finds_dataset_in_search_path(work):
    # The autouse fixture of the directory runs every test twice; the tools
    # here choose the algebra themselves, so the second run replaces FOUND.
    work.t_select(expression="FOUND = A : A", type="strds", overwrite=True)

    rows = list_maps(work, "strds", "FOUND")
    assert [row.name for row in rows] == ["a_1", "a_2"]


def test_classic_keeps_current_mapset_only(work):
    with pytest.raises(ToolError) as error:
        work.t_select(expression="NOT_FOUND = A : A", type="strds", flags="c")

    assert error.value.returncode == 1
    assert "Space time raster dataset <A@work> not found" in message(error.value)
    assert not work.t_list(type="strds", where="name = 'NOT_FOUND'").stdout


@pytest.mark.parametrize(
    ("flags", "text"),
    [
        (
            "",
            (
                "Temporal function start_month() is not available for map <r_1@work>: "
                "it needs absolute time, and the end functions also an end time"
            ),
        ),
        (
            "c",
            (
                "Temporal function start_month() is not available for map <r_1@work>. "
                "It requires absolute time, end time functions also an end time."
            ),
        ),
    ],
    ids=["core", "classic"],
)
def test_calendar_function_on_relative_time_message(work, flags, text):
    output = f"MONTH{flags.upper()}"
    with pytest.raises(ToolError) as error:
        work.t_select(
            expression=f"{output} = if(start_month(R) == 1, R)",
            type="strds",
            flags=flags,
        )

    assert error.value.returncode == 1
    assert text in message(error.value)
    assert not work.t_list(type="strds", where=f"name = '{output}'").stdout
    assert not work.g_list(type="raster", pattern="month*").stdout
