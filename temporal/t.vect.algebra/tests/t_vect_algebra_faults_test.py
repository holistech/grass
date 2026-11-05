"""Test the search path and the numbers of the result maps of t.vect.algebra

The core algebra looks for a dataset name without a mapset in the current
mapset and then in the search path, the classic algebra (-c) in the current
mapset only. The core numbers only the maps it registers, so a computed map
without primitives, which is not registered, leaves no gap. A map that the
result takes over unchanged keeps its name and is never renamed, and a
computed map is only renamed to a name that the run planned for a computed
map, so that a map of the user and the maps of the inputs stay as they are.
"""

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_daily_stds,
    create_stds,
    day,
    make_map,
)
from grass.temporal.testing.readback import list_maps, message
from grass.temporal.testing.session import mapset_session, project_session
from grass.tools import ToolError, Tools

# Every test chooses its algebra itself: the core by the variable, the classic
# algebra by -c.
pytestmark = pytest.mark.fixed_algebra


@pytest.fixture(scope="module")
def work(tmp_path_factory):
    """Tools in the mapset "work", with the mapset "other" in its search path

    The dataset A in "other" has the daily maps a_1 and a_2, a point at (1, 1)
    and one at (2, 2). The dataset B in "work" has maps of the same days, a
    point at (10, 10) and one at (2, 2). The tools run the core algebra unless
    a test passes -c.
    """
    project = tmp_path_factory.mktemp("search_path") / "project"
    with (
        project_session(project, mapset="work") as work_session,
        mapset_session(work_session, "other") as other,
    ):
        env = {**work_session.env, "GRASS_TEMPORAL_ALGEBRA": "core"}
        tools = Tools(env=env, consistent_return_value=True, quiet=True)
        other_tools = Tools(session=other, consistent_return_value=True, quiet=True)
        create_daily_stds(other_tools, "stvds", ["A"], 2, map_prefix="a")
        create_stds(
            tools,
            "stvds",
            "B",
            [MapSpec("b_1", 10, day(0), day(1)), MapSpec("b_2", 2, day(1), day(2))],
        )
        tools.g_mapsets(operation="add", mapset="other")
        yield tools


def test_core_finds_dataset_in_search_path(work):
    work.t_vect_algebra(expression="FOUND = A {:,equal} B", basename="found")

    rows = list_maps(work, "stvds", "FOUND")
    assert [row.name for row in rows] == ["a_1", "a_2"]


def test_classic_keeps_current_mapset_only(work):
    with pytest.raises(ToolError) as error:
        work.t_vect_algebra(
            expression="NOT_FOUND = A {:,equal} B", basename="not_found", flags="c"
        )

    assert error.value.returncode == 1
    assert "Space time vector dataset <A@work> not found" in message(error.value)
    assert not work.t_list(type="stvds", where="name = 'NOT_FOUND'").stdout
    assert not work.g_list(type="vector", pattern="not_found*").stdout


@pytest.mark.parametrize(
    ("flags", "names"),
    [("", ["num_0"]), ("c", ["numc_0"])],
    ids=["core", "classic"],
)
def test_core_numbers_only_registered_maps(work, flags, names):
    basename = f"num{flags}"
    # The buffers of the first pair do not meet, so their intersection has no
    # primitives and is not registered.
    work.t_vect_algebra(
        expression=(
            f"{basename.upper()} = buff_p(A@other, 1) {{&,equal}} buff_p(B, 1)"
        ),
        basename=basename,
        flags=flags,
    )

    rows = list_maps(work, "stvds", basename.upper())
    assert [(row.name, row.start) for row in rows] == [
        (names[0], "2001-01-02 00:00:00")
    ]
    assert work.g_list(type="vector", pattern=f"{basename}_*").stdout.split() == names


@pytest.fixture(scope="module")
def mixed(tmp_path_factory):
    """Tools in an XY project of their own with the datasets PA, PB, M and N

    PA and PB have maps of two days from 1 January 2001: points at (0, 0),
    except pb_1 at (100, 100), so the buffers of the first pair do not meet.
    M has the point m_1 and N the point orig_1 at (50, 50) for 2 January,
    which a merge() takes over unchanged between the two intersections.
    """
    project = tmp_path_factory.mktemp("mixed") / "project"
    with project_session(project, mapset="work") as session:
        env = {**session.env, "GRASS_TEMPORAL_ALGEBRA": "core"}
        tools = Tools(env=env, consistent_return_value=True, quiet=True)
        create_stds(
            tools,
            "stvds",
            "PA",
            [MapSpec("pa_1", 0, day(0), day(2)), MapSpec("pa_2", 0, day(2), day(4))],
        )
        create_stds(
            tools,
            "stvds",
            "PB",
            [
                MapSpec("pb_1", 100, day(0), day(2)),
                MapSpec("pb_2", 0, day(2), day(4)),
            ],
        )
        create_stds(tools, "stvds", "M", [MapSpec("m_1", 50, day(1), day(2))])
        create_stds(tools, "stvds", "N", [MapSpec("orig_1", 50, day(1), day(2))])
        yield tools


MERGED = "merge(buff_p(PA, 1) {{&,equal}} buff_p(PB, 1), {unchanged})"


def time_stamp(tools, name):
    """The time stamp of a vector map, None if it has none

    v.timestamp ends with 1 and prints nothing for a map without a time
    stamp; a missing map gives an error message.
    """
    try:
        return tools.v_timestamp(map=name).text
    except ToolError as error:
        if error.returncode == 1 and not message(error):
            return None
        raise


def points_and_areas(tools, name):
    info = tools.v_info(map=name, flags="t").keyval
    return info["points"], info["areas"]


@pytest.mark.parametrize("overwrite", [False, True], ids=["new", "overwrite"])
def test_core_renumbering_leaves_a_map_of_the_user_alone(mixed, overwrite):
    basename = f"mix{int(overwrite)}"
    # A map of the user with the name that the unchanged map of M would have
    # if it were numbered
    make_map(mixed, "vector", f"{basename}_1", 7)

    mixed.t_vect_algebra(
        expression=f"{basename.upper()} = {MERGED.format(unchanged='M')}",
        basename=basename,
        overwrite=overwrite,
    )

    rows = list_maps(mixed, "stvds", basename.upper())
    assert [(row.name, row.start, row.end) for row in rows] == [
        ("m_1", "2001-01-02 00:00:00", "2001-01-03 00:00:00"),
        (f"{basename}_0", "2001-01-03 00:00:00", "2001-01-05 00:00:00"),
    ]
    assert points_and_areas(mixed, f"{basename}_1") == (1, 0)
    assert time_stamp(mixed, f"{basename}_1") is None
    assert mixed.g_list(type="vector", pattern=f"{basename}_*").text.split() == [
        f"{basename}_0",
        f"{basename}_1",
    ]
    assert [
        (row.name, row.start, row.end) for row in list_maps(mixed, "stvds", "M")
    ] == [("m_1", "2001-01-02 00:00:00", "2001-01-03 00:00:00")]
    assert points_and_areas(mixed, "m_1") == (1, 0)


def test_core_renumbering_never_renames_an_unchanged_map(mixed):
    # The unchanged map of N has the name of a number of the result.
    mixed.t_vect_algebra(
        expression=f"ORIG = {MERGED.format(unchanged='N')}",
        basename="orig",
        overwrite=True,
    )

    rows = list_maps(mixed, "stvds", "ORIG")
    assert [(row.name, row.start, row.end) for row in rows] == [
        ("orig_1", "2001-01-02 00:00:00", "2001-01-03 00:00:00"),
        ("orig_0", "2001-01-03 00:00:00", "2001-01-05 00:00:00"),
    ]
    assert [
        (row.name, row.start, row.end) for row in list_maps(mixed, "stvds", "N")
    ] == [("orig_1", "2001-01-02 00:00:00", "2001-01-03 00:00:00")]
    assert points_and_areas(mixed, "orig_1") == (1, 0)
    assert mixed.g_list(type="vector", pattern="orig_*").text.split() == [
        "orig_0",
        "orig_1",
    ]
