"""Test the refusals of t.unregister: option combinations, datasets and files

The messages of the two checks on maps= and file= name the options input= and
file=, although the options are maps= and file=. Each is pinned as it is today
next to a strict xfail for the right text.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

# Only the tests that make maps run longer than one second; the others fail
# before they read anything (measured 18.10.2026 with a serial pytest
# --durations=0).


@pytest.mark.slow
def test_maps_and_file_exclude_each_other(tools, make_stds, tmp_path):
    maps, _ = make_stds(1)
    file = tmp_path / "maps.txt"
    file.write_text(maps[0] + "\n")

    with pytest.raises(ToolError, match="are mutually exclusive"):
        tools.t_unregister(maps=maps[0], file=file)

    assert (
        tools.t_info(type="raster", input=maps[0], flags="g").keyval["name"]
        == (maps[0])
    )


def test_today_the_exclusion_names_the_wrong_options(tools, tmp_path):
    with pytest.raises(ToolError, match="input= and file= are mutually exclusive"):
        tools.t_unregister(maps="a", file=tmp_path / "maps.txt")


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_the_exclusion_names_the_options_maps_and_file(tools, tmp_path):
    with pytest.raises(ToolError, match=r"maps= and file= are mutually exclusive"):
        tools.t_unregister(maps="a", file=tmp_path / "maps.txt")


def test_maps_or_file_is_needed(tools):
    with pytest.raises(ToolError, match="must be specified"):
        tools.t_unregister()


def test_an_empty_maps_option_counts_as_missing(tools):
    with pytest.raises(ToolError, match="must be specified"):
        tools.t_unregister(maps="")


def test_today_the_requirement_names_the_wrong_options(tools):
    with pytest.raises(ToolError, match="input= or file= must be specified"):
        tools.t_unregister()


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_the_requirement_names_the_options_maps_and_file(tools):
    with pytest.raises(ToolError, match=r"maps= or file= must be specified"):
        tools.t_unregister()


@pytest.mark.slow
def test_an_unknown_dataset_is_refused(tools, make_stds):
    maps, _ = make_stds(1)

    with pytest.raises(ToolError, match=r"of type\s+<raster> not found"):
        tools.t_unregister(input="no_such_dataset", maps=maps[0])

    assert (
        tools.t_info(type="raster", input=maps[0], flags="g").keyval["name"]
        == (maps[0])
    )


@pytest.mark.slow
def test_a_dataset_of_another_type_is_not_found(tools, make_stds):
    # The type of the maps selects the type of the dataset.
    maps, (name,) = make_stds(1, stds_type="stvds")

    with pytest.raises(ToolError, match=r"of type\s+<raster> not found"):
        tools.t_unregister(input=name, maps=maps[0])


def test_an_unknown_type_is_refused(tools):
    with pytest.raises(ToolError, match="out of range for parameter <type>"):
        tools.t_unregister(type="strds", maps="a")


def test_today_a_missing_file_ends_in_a_traceback(tools, tmp_path):
    with pytest.raises(ToolError, match="FileNotFoundError"):
        tools.t_unregister(file=tmp_path / "missing.txt")


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_a_missing_file_is_refused_with_a_message(tools, tmp_path):
    with pytest.raises(ToolError) as error:
        tools.t_unregister(file=tmp_path / "missing.txt")

    assert "Traceback" not in message(error.value)
