"""Test the search path and the calendar functions on relative time in t.select

The algebra looks for a dataset name without a mapset in the current mapset
and then in the search path. A calendar function such as start_month() needs
absolute time; on relative time the algebra stops with an error and creates no
dataset.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_daily_stds, create_stds
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.temporal.testing.session import mapset_session, project_session
from grass.tools import ToolError, Tools


@pytest.fixture(scope="module")
def work(tmp_path_factory):
    """Tools in the mapset "work", with the mapset "other" in its search path

    The dataset A with the daily maps a_1 and a_2 is in "other". The dataset
    R in "work" has the maps r_1 and r_2 of relative time, days 0 to 2 and 2
    to 4.
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
    work.t_select(expression="FOUND = A : A", type="strds")

    rows = list_maps(work, "strds", "FOUND")
    assert [row.name for row in rows] == ["a_1", "a_2"]


def test_calendar_function_on_relative_time_message(work):
    text = (
        "Temporal function start_month() is not available for map <r_1@work>: "
        "it needs absolute time, and the end functions also an end time"
    )
    output = "MONTH"
    with pytest.raises(ToolError) as error:
        work.t_select(expression=f"{output} = if(start_month(R) == 1, R)", type="strds")

    assert error.value.returncode == 1
    assert text in message(error.value)
    assert not work.t_list(type="strds", where=f"name = '{output}'").stdout
    assert not work.g_list(type="raster", pattern="month*").stdout


DATE_AND_NUMBER = (
    "Dates and times, such as those of start_date() or start_time(), cannot be "
    "compared with the number 10; compare them with a date or time in quotes, "
    'such as "2001-01-03" or "12:00:00"'
)


@pytest.mark.parametrize(
    ("expression", "text"),
    [("if(start_date(A) > 10, A)", DATE_AND_NUMBER)],
    ids=["date and number"],
)
def test_the_tool_reports_the_error_and_writes_nothing(work, expression, text):
    """t.select stops with the message of the core, without a traceback,
    before it creates a dataset"""
    before = inventory(work)
    with pytest.raises(ToolError) as error:
        work.t_select(expression=f"REFUSED = {expression}", type="strds")

    assert text in message(error.value)
    assert "Traceback" not in error.value.stderr
    assert inventory(work) == before
