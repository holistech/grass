"""Test the search path and the calendar functions on relative time in t.select

The algebra looks for a dataset name without a mapset in the current mapset
and then in the search path. A calendar function such as start_month() needs
absolute time; on relative time the algebra stops with an error and creates no
dataset. So does an expression the core refuses, with the message of the core.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_daily_stds, create_stds, day
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.temporal.testing.session import mapset_session, project_session
from grass.tools import ToolError, Tools


@pytest.fixture(scope="module")
def work(tmp_path_factory):
    """Tools in the mapset "work", with the mapset "other" in its search path

    The dataset A with the daily maps a_1 and a_2 is in "other". The dataset
    R in "work" has the maps r_1 and r_2 of relative time, days 0 to 2 and 2
    to 4, and the dataset I in "work" the time instances i_1 and i_2 on the
    first two days.
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
        create_stds(
            tools, "strds", "I", [MapSpec("i_1", 1, day(0)), MapSpec("i_2", 2, day(1))]
        )
        tools.g_mapsets(operation="add", mapset="other")
        yield tools


def test_core_finds_dataset_in_search_path(work):
    work.t_select(expression="FOUND = A : A", type="strds")

    rows = list_maps(work, "strds", "FOUND")
    assert [row.name for row in rows] == ["a_1", "a_2"]


def test_a_time_of_day_still_compares_with_start_time(work):
    """start_time() against a time of day selects, unlike a date alone

    Both maps of A start at 00:00:00, which is before 12:00:00, so the
    condition holds for a_1 and a_2.
    """
    work.t_select(
        expression='MORNING = if(start_time(A) < "12:00:00", A)', type="strds"
    )

    rows = list_maps(work, "strds", "MORNING")
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
DATE_ALONE = (
    "'2001-03-01' is a date without a time of day, but start_time() and "
    "end_time() give only the time of day; compare dates with start_date() or "
    "end_date(), or a date and time with start_datetime() or end_datetime()"
)
TD_OF_AN_INSTANCE = (
    "td() requires a time interval, but map <i_1@work> is a time instance"
)
UNEQUAL_BRANCHES = (
    "where() needs maps with equal time stamps; they differ at map 1: "
    "2001-01-01 00:00:00 .. 2001-01-02 00:00:00 and 2001-01-01 00:00:00. Select "
    "the maps with matching time stamps first, for example B : A"
)


@pytest.mark.parametrize(
    ("expression", "text"),
    [
        ("if(start_date(A) > 10, A)", DATE_AND_NUMBER),
        ('if(start_time(A) >= "2001-03-01", A)', DATE_ALONE),
        ("if(td(I) > 0, I)", TD_OF_AN_INSTANCE),
        ("if(A > 1, A, I)", UNEQUAL_BRANCHES),
    ],
    ids=["date and number", "date alone", "td of an instance", "unequal branches"],
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
