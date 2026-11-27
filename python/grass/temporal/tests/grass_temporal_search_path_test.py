"""Datasets of another mapset and the search path

The temporal database belongs to a mapset. The library opens the databases of
the mapsets that have one and are in the search path of the current mapset
(get_available_temporal_mapsets() asks t.connect -p), and the database of a
mapset that a name gives with @mapset, as raster and vector tools read
name@mapset of any mapset of the project. These tests pin down what a tool
does with a dataset of a mapset that is not in the search path and what it
does once the mapset is in it, in a project with the mapsets "second" (the
one the tools run in) and "first" (the one that holds the datasets).
"""

import pytest

from grass.temporal.db import get_available_temporal_mapsets
from grass.temporal.testing.data import create_daily_stds
from grass.temporal.testing.readback import message
from grass.temporal.testing.session import (
    add_mapset,
    mapset_session,
    project_session,
)
from grass.tools import ToolError, Tools

# What a tool prints when the mapset of a dataset has no accessible database
# (db.py, _create_mapset_error_message()). It lists no accessible mapsets,
# because any mapset of the project with a temporal database is readable.
REFUSAL = (
    "You have no permission to access mapset <nodb>, or mapset <nodb> has no"
    " temporal database."
)


@pytest.fixture(scope="module")
def sessions(tmp_path_factory):
    """Tools in the mapsets "second" and "first" of one XY project

    The datasets ds (raster), ds3 (3D raster) and dsv (vector), each with two
    maps, are in "first". "third" holds the dataset dup with two maps, for the
    tests of names without a mapset. "nodb" is a mapset without a temporal
    database.
    """
    project = tmp_path_factory.mktemp("search_path") / "project"
    with (
        project_session(project, mapset="second") as second,
        mapset_session(second, "first") as first,
        mapset_session(second, "third") as third,
    ):
        add_mapset(second, "nodb")
        tools = []
        for session in (second, first, third):
            tools.append(
                Tools(
                    session=session,
                    consistent_return_value=True,
                    capture_stderr=True,
                )
            )
            tools[-1].g_region(n=1, s=0, e=1, w=0, res=1, b=0, t=1, res3=1)
        work, owner, other = tools
        create_daily_stds(owner, "strds", ["ds"], 2, map_prefix="r")
        create_daily_stds(owner, "str3ds", ["ds3"], 2, map_prefix="r3")
        create_daily_stds(owner, "stvds", ["dsv"], 2, map_prefix="v")
        create_daily_stds(owner, "strds", ["extract_fails"], 2, map_prefix="x1")
        create_daily_stds(owner, "strds", ["extract_works"], 2, map_prefix="x2")
        create_daily_stds(owner, "strds", ["dup", "dup2"], 1, map_prefix="d1")
        create_daily_stds(other, "strds", ["dup", "dup2"], 2, map_prefix="d3")
        create_daily_stds(work, "strds", ["dup"], 3, map_prefix="d2")
        yield work


@pytest.fixture
def tools(sessions):
    """The tools of "second" with only "second" in the search path"""
    sessions.g_mapsets(operation="set", mapset="second,PERMANENT")
    yield sessions
    sessions.g_mapsets(operation="set", mapset="second,PERMANENT")


def add_first(tools):
    tools.g_mapsets(operation="add", mapset="first")


def lines(result):
    return result.stdout.splitlines()


def two_rows(tools, result):
    """A listing with the header and the two maps of the dataset"""
    return len(lines(result)) == 3 and all(
        "first" in line for line in lines(result)[1:]
    )


def univar_ids(result):
    return [line.split("|")[0] for line in lines(result)[1:]]


def listed_rows(tools, name):
    """The number of lines t.rast.list prints for the dataset name"""
    return len(lines(tools.t_rast_list(input=name)))


# A case is the call of a tool with a dataset of the mapset m and the check of
# the result; the calls write to the mapset "second" with overwrite, so the
# cases do not depend on each other. t.select relates ds to itself because the
# classic algebra took no bare dataset there.
CASES = {
    "t.rast.list": (
        lambda t, p, m: t.t_rast_list(input=f"ds@{m}"),
        two_rows,
    ),
    "t.rast3d.list": (
        lambda t, p, m: t.t_rast3d_list(input=f"ds3@{m}"),
        two_rows,
    ),
    "t.vect.list": (
        lambda t, p, m: t.t_vect_list(input=f"dsv@{m}"),
        two_rows,
    ),
    "t.rast.univar": (
        lambda t, p, m: t.t_rast_univar(input=f"ds@{m}"),
        lambda t, r: univar_ids(r) == ["r_1@first", "r_2@first"],
    ),
    "t.rast3d.univar": (
        lambda t, p, m: t.t_rast3d_univar(input=f"ds3@{m}"),
        lambda t, r: univar_ids(r) == ["r3_1@first", "r3_2@first"],
    ),
    "t.copy": (
        lambda t, p, m: t.t_copy(
            type="strds", input=f"ds@{m}", output="copied", overwrite=True
        ),
        lambda t, r: listed_rows(t, "copied") == 3,
    ),
    "t.info": (
        lambda t, p, m: t.t_info(type="strds", input=f"ds@{m}", flags="g"),
        lambda t, r: "id=ds@first" in lines(r),
    ),
    "t.select": (
        lambda t, p, m: t.t_select(
            expression=f"selected = ds@{m} : ds@{m}", type="strds", overwrite=True
        ),
        lambda t, r: listed_rows(t, "selected") == 3,
    ),
    "t.rast.extract": (
        lambda t, p, m: t.t_rast_extract(
            input=f"ds@{m}",
            output="ext",
            expression="ds * 2",
            basename="ext",
            overwrite=True,
        ),
        lambda t, r: listed_rows(t, "ext") == 3,
    ),
    "t.sample": (
        lambda t, p, m: t.t_sample(input=f"ds@{m}", sample=f"ds@{m}"),
        lambda t, r: len(lines(r)) == 2,
    ),
    "t.rast.export": (
        lambda t, p, m: t.t_rast_export(
            input=f"ds@{m}",
            output=str(p / "exported"),
            compression="no",
            overwrite=True,
        ),
        lambda t, r: True,
    ),
    "t.rast.mapcalc": (
        lambda t, p, m: t.t_rast_mapcalc(
            inputs=f"ds@{m}",
            output="calculated",
            basename="calculated",
            expression="ds + 1",
            overwrite=True,
        ),
        lambda t, r: listed_rows(t, "calculated") == 3,
    ),
    "t.rast3d.mapcalc": (
        lambda t, p, m: t.t_rast3d_mapcalc(
            inputs=f"ds3@{m}",
            output="calculated3",
            basename="calculated3",
            expression="ds3 + 1",
            overwrite=True,
        ),
        lambda t, r: len(lines(t.t_rast3d_list(input="calculated3"))) == 3,
    ),
    "t.rast.algebra": (
        lambda t, p, m: t.t_rast_algebra(
            expression=f"algebra = ds@{m} + 1", basename="algebra", overwrite=True
        ),
        lambda t, r: listed_rows(t, "algebra") == 3,
    ),
}


def run(tools, name, tmp_path, mapset="first"):
    """Call the tool of the case; its files go below tmp_path"""
    return CASES[name][0](tools, tmp_path, mapset)


def check(tools, name, result, tmp_path):
    assert CASES[name][1](tools, result)
    if name == "t.rast.export":
        assert (tmp_path / "exported").exists()


@pytest.mark.parametrize("tool", sorted(CASES))
def test_qualified_name_outside_search_path_is_read(tools, tool, tmp_path):
    result = run(tools, tool, tmp_path)

    check(tools, tool, result, tmp_path)


@pytest.mark.parametrize("tool", sorted(CASES))
def test_qualified_name_in_search_path_is_read(tools, tool, tmp_path):
    add_first(tools)

    result = run(tools, tool, tmp_path)

    check(tools, tool, result, tmp_path)


@pytest.mark.parametrize("tool", sorted(CASES))
def test_unknown_mapset_is_refused(tools, tool, tmp_path):
    with pytest.raises(ToolError) as error:
        run(tools, tool, tmp_path, mapset="nosuch")

    assert error.value.returncode == 1
    assert "<nosuch>" in message(error.value)


@pytest.mark.parametrize("tool", sorted(CASES))
def test_mapset_without_temporal_database_is_refused(tools, tool, tmp_path):
    with pytest.raises(ToolError) as error:
        run(tools, tool, tmp_path, mapset="nodb")

    assert error.value.returncode == 1
    assert REFUSAL in message(error.value)
    assert "Accessible mapsets" not in message(error.value)


def extract(tools, name):
    return tools.t_rast_extract(
        input=f"{name}@first",
        output=f"{name}_out",
        where="start_time > '2000-01-01'",
        basename=f"{name}_out",
        overwrite=True,
    )


def test_extract_of_dataset_of_mapset_in_search_path_needs_maps_in_the_database(tools):
    """The maps are put into the database of "second", the extract is made"""
    add_first(tools)

    extract(tools, "extract_fails")

    listing = tools.t_rast_list(input="extract_fails_out", columns="name,mapset")
    assert lines(listing) == ["name|mapset", "x1_1|first", "x1_2|first"]


def test_extract_of_dataset_of_mapset_in_search_path_after_maps_are_in_the_database(
    tools,
):
    add_first(tools)
    # t.select inserts the maps of the dataset into the database of "second";
    # see CASES for the relation.
    tools.t_select(
        expression="inserted = extract_works@first : extract_works@first",
        type="strds",
        overwrite=True,
    )

    extract(tools, "extract_works")

    listing = tools.t_rast_list(input="extract_works_out", columns="name,mapset")
    assert lines(listing) == ["name|mapset", "x2_1|first", "x2_2|first"]


def test_a_dataset_copied_without_search_path_registers_the_maps_of_the_original(tools):
    tools.t_copy(type="strds", input="ds@first", output="copy_of_ds")

    listing = tools.t_rast_list(input="copy_of_ds", columns="name,mapset")

    assert lines(listing) == ["name|mapset", "r_1|first", "r_2|first"]


def test_name_without_mapset_outside_search_path_is_not_found(tools):
    with pytest.raises(ToolError) as error:
        tools.t_rast_list(input="ds")

    assert error.value.returncode == 1
    assert "Space time dataset <ds> of type <strds> not found" in message(error.value)


def test_name_without_mapset_in_search_path_is_found(tools):
    add_first(tools)

    result = tools.t_rast_list(input="ds", columns="name,mapset")

    assert lines(result) == ["name|mapset", "r_1|first", "r_2|first"]


def listed_mapsets(tools):
    return {
        line.split("|")[1]
        for line in lines(tools.t_rast_list(input="dup", columns="name,mapset"))[1:]
    }


def test_name_without_mapset_takes_the_current_mapset_first(tools):
    tools.g_mapsets(operation="set", mapset="second,first,third")

    assert listed_mapsets(tools) == {"second"}
    assert len(lines(tools.t_rast_list(input="dup"))) == 1 + 3


@pytest.mark.parametrize(
    ("path", "mapsets"),
    [("first,third", {"first"}), ("third,first", {"third"})],
)
def test_name_without_mapset_takes_the_first_mapset_of_the_search_path(
    tools, path, mapsets
):
    tools.g_mapsets(operation="set", mapset=f"second,{path}")

    listing = tools.t_rast_list(input="dup2", columns="name,mapset")

    assert {line.split("|")[1] for line in lines(listing)[1:]} == mapsets


def test_mapset_without_temporal_database_is_not_listed(
    temporal_module_session,
):
    session = temporal_module_session
    add_mapset(session, "nodb")
    add_mapset(session, "withdb")
    with mapset_session(session, "withdb") as withdb:
        Tools(session=withdb).t_create(
            output="in_withdb", title="t", description="d", quiet=True
        )
    tools = Tools(session=session, consistent_return_value=True, capture_stderr=True)
    tools.g_mapsets(operation="add", mapset="nodb,withdb")

    # The mapset without a database is in the search path, so its absence
    # below comes from the missing database.
    assert "nodb" in tools.g_mapsets(flags="p").text.split()
    try:
        listed = get_available_temporal_mapsets()
    finally:
        tools.g_mapsets(operation="remove", mapset="nodb,withdb")

    assert set(listed) == {"PERMANENT", "withdb"}
