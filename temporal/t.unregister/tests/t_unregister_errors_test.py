"""Test the refusals of t.unregister: option combinations, datasets and files

The messages of the two checks on maps= and file= name the options maps= and
file=. A mapset without a temporal database stays without one.
"""

import os
from datetime import datetime
from pathlib import Path

import pytest

import grass.script as gs
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import message, stds_info
from grass.temporal.testing.session import mapset_session, project_session
from grass.tools import ToolError, Tools

# Only the tests that make maps run longer than one second; the others fail
# before they read anything (measured 18.10.2026 with a serial pytest
# --durations=0).


@pytest.mark.slow
def test_maps_and_file_exclude_each_other(tools, make_stds, tmp_path):
    maps, _ = make_stds(1)
    file = tmp_path / "maps.txt"
    file.write_text(maps[0] + "\n")

    with pytest.raises(ToolError, match=r"are\s+mutually\s+exclusive"):
        tools.t_unregister(maps=maps[0], file=file)

    assert (
        tools.t_info(type="raster", input=maps[0], flags="g").keyval["name"]
        == (maps[0])
    )


def test_the_exclusion_names_the_options_maps_and_file(tools, tmp_path):
    with pytest.raises(
        ToolError, match=r"maps=\s+and\s+file=\s+are\s+mutually\s+exclusive"
    ):
        tools.t_unregister(maps="a", file=tmp_path / "maps.txt")


def test_maps_or_file_is_needed(tools):
    with pytest.raises(ToolError, match=r"must\s+be\s+specified"):
        tools.t_unregister()


def test_an_empty_maps_option_counts_as_missing(tools):
    with pytest.raises(ToolError, match=r"must\s+be\s+specified"):
        tools.t_unregister(maps="")


def test_the_requirement_names_the_options_maps_and_file(tools):
    with pytest.raises(ToolError, match=r"maps=\s+or\s+file=\s+must\s+be\s+specified"):
        tools.t_unregister()


@pytest.mark.slow
def test_an_unknown_dataset_is_refused(tools, make_stds):
    maps, _ = make_stds(1)

    with pytest.raises(ToolError, match=r"of\s+type\s+<raster>\s+not\s+found"):
        tools.t_unregister(input="no_such_dataset", maps=maps[0])

    assert (
        tools.t_info(type="raster", input=maps[0], flags="g").keyval["name"]
        == (maps[0])
    )


@pytest.mark.slow
def test_a_dataset_of_another_type_is_not_found(tools, make_stds):
    # The type of the maps selects the type of the dataset.
    maps, (name,) = make_stds(1, stds_type="stvds")

    with pytest.raises(ToolError, match=r"of\s+type\s+<raster>\s+not\s+found"):
        tools.t_unregister(input=name, maps=maps[0])


def test_an_unknown_type_is_refused(tools):
    with pytest.raises(ToolError, match=r"out\s+of\s+range\s+for\s+parameter\s+<type>"):
        tools.t_unregister(type="strds", maps="a")


def test_a_missing_file_is_refused_with_a_message(tools, tmp_path):
    with pytest.raises(ToolError) as error:
        tools.t_unregister(file=tmp_path / "missing.txt")

    assert "Traceback" not in message(error.value)
    assert "not found" in message(error.value)


def _database_file(session):
    """Path of the default temporal database of the current mapset"""
    env = gs.gisenv(env=session.env)
    return (
        Path(env["GISDBASE"])
        / env["LOCATION_NAME"]
        / env["MAPSET"]
        / "tgis"
        / "sqlite.db"
    )


def _series_in_other_mapset(work):
    """Make the dataset series of three daily maps in the mapset other of work"""
    with mapset_session(work, "other") as other:
        other_tools = Tools(session=other, consistent_return_value=True)
        other_tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_stds(
            other_tools,
            "strds",
            "series",
            [
                MapSpec(f"m{n}", n, datetime(2026, 1, n), datetime(2026, 1, n + 1))
                for n in (1, 2, 3)
            ],
        )


def test_without_database_warns_and_creates_none(tmp_path):
    with project_session(tmp_path / "project", mapset="work") as work:
        tools = Tools(session=work, consistent_return_value=True, capture_stderr=True)
        assert not _database_file(work).exists()

        result = tools.t_unregister(maps="x")

        assert (
            "WARNING: Unable to connect to a temporal database in the current "
            "mapset. Nothing to unregister"
        ) in message(result)
        assert result.returncode == 0
        assert not _database_file(work).exists()


def test_without_database_a_dataset_of_another_mapset_is_left_alone(tmp_path):
    # The dataset is named with its mapset, which the tool can read; without
    # a database in the current mapset there is nowhere to unregister.
    with project_session(tmp_path / "project", mapset="work") as work:
        _series_in_other_mapset(work)
        tools = Tools(session=work, consistent_return_value=True, capture_stderr=True)

        result = tools.t_unregister(input="series@other", maps="m1")

        assert "Nothing to unregister" in message(result)
        assert not _database_file(work).exists()
        assert stds_info(tools, "strds", "series@other")["number_of_maps"] == 3


def test_a_dataset_of_another_mapset_is_refused_with_a_database(tmp_path):
    with project_session(tmp_path / "project", mapset="work") as work:
        _series_in_other_mapset(work)
        tools = Tools(session=work, consistent_return_value=True, capture_stderr=True)
        tools.t_create(type="strds", output="mine", title="t", description="d")

        with pytest.raises(ToolError) as error:
            tools.t_unregister(input="series@other", maps="m1")

        assert "The mapset of the database does not match the current mapset" in (
            message(error.value)
        )
        assert stds_info(tools, "strds", "series@other")["number_of_maps"] == 3


def test_a_file_that_cannot_be_read_is_refused_with_a_message(tools, tmp_path):
    file = tmp_path / "maps.txt"
    file.write_bytes(b"\xff\xfe\n")

    with pytest.raises(ToolError) as error:
        tools.t_unregister(file=file)

    assert "Traceback" not in message(error.value)
    assert f"Unable to read map list from file <{file}>" in message(error.value)


def test_a_file_without_the_right_to_read_is_refused_with_a_message(tools, tmp_path):
    file = tmp_path / "maps.txt"
    file.write_text("a\n")
    file.chmod(0)
    if os.access(file, os.R_OK):
        pytest.skip("the user can read a file without a permission")

    with pytest.raises(ToolError) as error:
        tools.t_unregister(file=file)

    assert "Traceback" not in message(error.value)
    assert f"Unable to read map list from file <{file}>" in message(error.value)
