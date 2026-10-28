"""Test t.unregister with raster maps: datasets, names, files and warnings

Six maps a1 to a6 (here <prefix>_1 to <prefix>_6) last one day each, map n
from day n-1 to day n, and are registered in two datasets. The time belongs to
the map, so both datasets show the same times.
"""

import re

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    day,
    register_file,
    relative_intervals,
)
from grass.temporal.testing.readback import list_maps, map_info, stds_info

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _names(tools, dataset):
    return [row.name for row in list_maps(tools, "strds", dataset)]


def _message(result):
    """The messages of a call as one line: the tool wraps long ones"""
    return " ".join(result.stderr.split())


def _quoted(moment):
    return f"'{moment:%Y-%m-%d %H:%M:%S}'"


def _in_database(tools, maps, map_type="raster"):
    return [map_info(tools, map_type, name) is not None for name in maps]


def test_unregister_from_a_dataset_keeps_the_maps_elsewhere(tools, make_stds):
    maps, (first, second) = make_stds(6, datasets=2)

    tools.t_unregister(input=first, maps=",".join(maps[:3]))

    assert _names(tools, first) == maps[3:]
    assert _names(tools, second) == maps
    # Maps 4 to 6 lie in days 3 to 6; the dataset is updated from them.
    info = stds_info(tools, "strds", first)
    assert info["number_of_maps"] == 3
    assert info["start_time"] == _quoted(day(3))
    assert info["end_time"] == _quoted(day(6))
    assert stds_info(tools, "strds", second)["number_of_maps"] == 6
    # The maps are still in the temporal database, because the second dataset
    # holds them and the first one only forgot them.
    assert _in_database(tools, maps) == [True] * 6


def test_unregister_from_the_database_leaves_every_dataset(tools, make_stds):
    maps, (first, second) = make_stds(6, datasets=2)

    tools.t_unregister(maps=",".join(maps[:3]))

    assert _in_database(tools, maps) == [False] * 3 + [True] * 3
    for dataset in (first, second):
        assert _names(tools, dataset) == maps[3:]
        info = stds_info(tools, "strds", dataset)
        assert info["number_of_maps"] == 3
        assert info["start_time"] == _quoted(day(3))
        assert info["end_time"] == _quoted(day(6))
    # The temporal database is all that changes: the maps exist.
    existing = tools.g_list(type="raster").stdout.split()
    assert set(maps) <= set(existing)


def test_maps_stay_in_the_database_when_their_datasets_are_removed(tools, make_stds):
    # The former test removed the datasets without -f, which removes nothing,
    # so it never saw this. With -f the datasets go and the maps stay.
    maps, datasets = make_stds(6, datasets=2)

    tools.t_remove(inputs=",".join(datasets), flags="f")

    assert _in_database(tools, maps) == [True] * 6
    tools.t_unregister(maps=",".join(maps))
    assert _in_database(tools, maps) == [False] * 6


@pytest.mark.parametrize(
    ("unregistered", "number", "first_day", "last_day"),
    [
        # Map n lasts from day n-1 to day n.
        pytest.param((1,), 5, 1, 6, id="first"),
        pytest.param((6,), 5, 0, 5, id="last"),
        pytest.param((3,), 5, 0, 6, id="middle"),
        pytest.param((1, 2, 5, 6), 2, 2, 4, id="both_ends"),
    ],
)
def test_the_dataset_is_updated_from_the_maps_that_are_left(
    tools, make_stds, unregistered, number, first_day, last_day
):
    maps, (name,) = make_stds(6)

    tools.t_unregister(
        input=name, maps=",".join(maps[index - 1] for index in unregistered)
    )

    info = stds_info(tools, "strds", name)
    assert info["number_of_maps"] == number
    assert info["start_time"] == _quoted(day(first_day))
    assert info["end_time"] == _quoted(day(last_day))


def test_unregistering_the_last_map_leaves_an_empty_dataset(tools, make_stds):
    maps, (name,) = make_stds(2)

    tools.t_unregister(input=name, maps=",".join(maps))

    assert _names(tools, name) == []
    assert stds_info(tools, "strds", name)["number_of_maps"] == 0


def test_a_map_can_be_given_with_its_mapset(tools, make_stds):
    maps, (name,) = make_stds(3)

    tools.t_unregister(input=name, maps=f"{maps[0]}@PERMANENT,{maps[2]}")

    assert _names(tools, name) == [maps[1]]


def test_the_type_defaults_to_raster(tools, make_stds):
    maps, (name,) = make_stds(2)

    tools.t_unregister(type="raster", maps=maps[0])
    tools.t_unregister(maps=maps[1])

    assert _in_database(tools, maps) == [False, False]
    assert _names(tools, name) == []


def test_names_come_from_a_file(tools, make_stds, tmp_path):
    maps, (first, second) = make_stds(4, datasets=2)
    file = register_file(tmp_path / "maps.txt", [maps[0], maps[3]])

    tools.t_unregister(file=file)

    assert _in_database(tools, maps) == [False, True, True, False]
    assert _names(tools, first) == maps[1:3]
    assert _names(tools, second) == maps[1:3]


def test_names_from_a_file_and_a_dataset(tools, make_stds, tmp_path):
    maps, (first, second) = make_stds(4, datasets=2)
    file = register_file(tmp_path / "maps.txt", maps[:2])

    tools.t_unregister(input=first, file=file)

    assert _names(tools, first) == maps[2:]
    assert _names(tools, second) == maps
    assert _in_database(tools, maps) == [True] * 4


def test_a_blank_line_in_the_file_is_skipped(tools, make_stds, tmp_path):
    # The blank line lies before a later valid name, so that a tool which
    # stopped at the blank line would leave the last map registered.
    maps, _ = make_stds(3)
    file = tmp_path / "maps.txt"
    file.write_text(f"{maps[0]}\n\n{maps[2]}\n")

    result = tools.t_unregister(file=file)

    assert "WARNING" not in result.stderr
    assert _in_database(tools, maps) == [False, True, False]


def test_a_map_that_is_not_in_the_database_is_a_warning(tools, make_stds, prefix):
    maps, (name,) = make_stds(3)
    tools.r_mapcalc(expression=f"{prefix}_loose = 1")

    result = tools.t_unregister(maps=f"{maps[0]},{prefix}_loose,{maps[1]}")

    assert (
        f"WARNING: Unable to find raster map <{prefix}_loose@PERMANENT> in "
        "temporal database"
    ) in _message(result)
    # The warning is about that map only: the others are unregistered.
    assert _in_database(tools, maps) == [False, False, True]
    assert _names(tools, name) == [maps[2]]


def test_a_map_that_is_not_in_the_dataset_is_a_warning(tools, make_stds):
    maps, (first, second) = make_stds(3, datasets=2)
    tools.t_unregister(input=first, maps=maps[0])

    result = tools.t_unregister(input=first, maps=f"{maps[0]},{maps[1]}")

    assert f"Map <{maps[0]}@PERMANENT> is not registered in space time dataset" in (
        _message(result)
    )
    assert _names(tools, first) == [maps[2]]
    assert _names(tools, second) == maps


def test_a_map_of_another_type_is_not_found(tools, make_stds):
    maps, (name,) = make_stds(2)

    result = tools.t_unregister(type="vector", maps=maps[0])

    assert f"Unable to find vector map <{maps[0]}@PERMANENT>" in _message(result)
    assert _in_database(tools, maps) == [True, True]
    assert _names(tools, name) == maps


def test_a_dataset_of_relative_time(tools, prefix):
    # Three maps of relative time, each one unit long from 0: [0,1], [1,2], [2,3].
    specs = [
        MapSpec(f"{prefix}_{number}", number, start, end)
        for number, (start, end) in enumerate(relative_intervals(3), 1)
    ]
    create_stds(
        tools, "strds", f"{prefix}_rel", specs, temporaltype="relative", unit="years"
    )

    tools.t_unregister(input=f"{prefix}_rel", maps=specs[0].name)

    info = stds_info(tools, "strds", f"{prefix}_rel")
    assert info["number_of_maps"] == 2
    assert info["start_time"] == "'1'"
    assert info["end_time"] == "'3'"


def test_the_progress_of_the_dataset_update_ends_below_100_percent(tools, make_stds):
    maps, _ = make_stds(1, datasets=2)

    result = tools.t_unregister(maps=maps[0])

    maps_part, datasets_part = result.stderr.split(
        "Unregister maps from the temporal database"
    )
    assert "100%" in maps_part
    # The update of each dataset is shown before it is counted, so two
    # datasets show 0% and 50%, and no 100% follows.
    assert re.findall(r"\d+%", datasets_part) == ["0%", "50%"]
