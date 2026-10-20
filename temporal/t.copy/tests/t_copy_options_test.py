"""Test t.copy inside one mapset: what a copy keeps, the output check, -c

The source <prefix>_src holds three maps, map n with the value n from day n-1
to day n (2001-01-01 to 2001-01-04) on a one-cell region, with a title, a
description, the semantic type sum and the semantic label S2_1 on map 1.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, stds_info
from grass.tools import ToolError

# Every test makes maps or datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

TYPES = [("strds", "raster"), ("str3ds", "raster_3d"), ("stvds", "vector")]


def _make(tools, prefix, stds_type="strds", temporaltype="absolute", count=3):
    """Create <prefix>_src with count maps and return its name and the maps"""
    name = f"{prefix}_src"
    if temporaltype == "absolute":
        times = [(day(n), day(n + 1)) for n in range(count)]
    else:
        times = [(n, n + 1) for n in range(count)]
    maps = [
        MapSpec(f"{prefix}_{n}", n, start, end)
        for n, (start, end) in enumerate(times, 1)
    ]
    if stds_type == "strds":
        maps[0] = MapSpec(maps[0].name, 1, *times[0], semantic_label="S2_1")
    options = {} if temporaltype == "absolute" else {"unit": "days"}
    create_stds(
        tools,
        stds_type,
        name,
        maps,
        temporaltype=temporaltype,
        title=f"Title of {name}",
        description=f"Description of {name}",
        **options,
    )
    return name, [spec.name for spec in maps]


def _text(tools, stds_type, name):
    """t.info as one line of text, the frame and the line breaks left out"""
    return " ".join(
        tools.t_info(type=stds_type, input=name).stdout.replace("|", " ").split()
    )


def _names(tools, stds_type, name):
    return [row.name for row in list_maps(tools, stds_type, name)]


def test_copy_keeps_the_maps_and_the_metadata(tools, prefix):
    name, maps = _make(tools, prefix)
    tools.t_support(input=name, semantictype="sum")
    before = stds_info(tools, "strds", name)

    tools.t_copy(input=name, output=f"{prefix}_copy")

    assert _names(tools, "strds", f"{prefix}_copy") == maps
    info = stds_info(tools, "strds", f"{prefix}_copy")
    # Three one-day maps from 2001-01-01 to 2001-01-04 with the values 1 to 3
    # on the region of one cell (north 1, south 0, east 1, west 0).
    assert info["id"] == f"{prefix}_copy@PERMANENT"
    assert info["number_of_maps"] == 3
    assert info["start_time"] == "'2001-01-01 00:00:00'"
    assert info["end_time"] == "'2001-01-04 00:00:00'"
    assert info["granularity"] == "'1 day'"
    assert info["map_time"] == "interval"
    assert info["semantic_type"] == "sum"
    assert (info["north"], info["south"], info["east"], info["west"]) == (1, 0, 1, 0)
    assert (info["min_min"], info["min_max"]) == (1, 3)
    assert (info["max_min"], info["max_max"]) == (1, 3)
    text = _text(tools, "strds", f"{prefix}_copy")
    assert f"Title: Title of {name} " in text
    assert f"Description: Description of {name} " in text
    assert "Number of semantic labels:.. 1 Semantic labels:............ S2_1" in text
    assert f't.copy input="{name}" output="{prefix}_copy"' in text
    # The source is as it was, and its maps belong to both datasets.
    assert stds_info(tools, "strds", name) == before
    registered = _text(tools, "raster", maps[1]).split("Registered datasets")[1]
    assert set(registered.split()[1].split(",")) == {
        f"{name}@PERMANENT",
        f"{prefix}_copy@PERMANENT",
    }


@pytest.mark.parametrize(("stds_type", "map_type"), TYPES)
def test_each_dataset_type(tools, prefix, stds_type, map_type):
    name, maps = _make(tools, prefix, stds_type)

    tools.t_copy(type=stds_type, input=name, output=f"{prefix}_copy")

    assert _names(tools, stds_type, f"{prefix}_copy") == maps
    assert stds_info(tools, stds_type, f"{prefix}_copy")["number_of_maps"] == 3


def test_the_type_defaults_to_strds(tools, prefix):
    name, maps = _make(tools, prefix)

    tools.t_copy(type="strds", input=name, output=f"{prefix}_a")
    tools.t_copy(input=f"{prefix}_a", output=f"{prefix}_b")

    assert _names(tools, "strds", f"{prefix}_b") == maps


def test_a_dataset_of_relative_time(tools, prefix):
    name, maps = _make(tools, prefix, temporaltype="relative")

    tools.t_copy(input=name, output=f"{prefix}_copy")

    info = stds_info(tools, "strds", f"{prefix}_copy")
    assert info["temporal_type"] == "relative"
    # Maps [0,1], [1,2], [2,3] days.
    assert (info["start_time"], info["end_time"]) == ("'0'", "'3'")
    assert info["number_of_maps"] == 3


def test_an_empty_dataset_is_not_copied(tools, prefix):
    tools.t_create(output=f"{prefix}_empty", title="t", description="d")

    result = tools.t_copy(input=f"{prefix}_empty", output=f"{prefix}_copy")

    assert "nothing to copy" in " ".join(result.stderr.split())
    assert f"{prefix}_copy" not in tools.t_list(type="strds", columns="name").stdout


def test_an_existing_output_is_refused_without_overwrite(tools, prefix):
    name, maps = _make(tools, prefix)
    existing, existing_maps = _make(tools, f"{prefix}_x")

    with pytest.raises(
        ToolError, match=r"is\s+already\s+in\s+the\s+database\.\s+Use\s+the\s+overwrite"
    ):
        tools.t_copy(input=name, output=existing)

    assert _names(tools, "strds", existing) == existing_maps


def test_overwrite_replaces_the_output(tools, prefix):
    name, maps = _make(tools, prefix)
    existing, _ = _make(tools, f"{prefix}_x", count=2)

    result = tools.t_copy(input=name, output=existing, overwrite=True)

    assert "Overwriting space time raster dataset" in " ".join(result.stderr.split())
    assert _names(tools, "strds", existing) == maps
    assert f"Title of {name} " in _text(tools, "strds", existing)


def test_today_copying_a_dataset_onto_itself_keeps_its_maps(tools, prefix):
    name, maps = _make(tools, prefix)

    tools.t_copy(input=name, output=name, overwrite=True)

    assert _names(tools, "strds", name) == maps


def test_c_in_the_same_mapset_is_refused_without_overwrite(tools, prefix):
    name, maps = _make(tools, prefix)

    with pytest.raises(ToolError, match=r"already\s+in\s+temporal\s+database"):
        tools.t_copy(input=name, output=f"{prefix}_copy", flags="c")

    assert f"{prefix}_copy" not in tools.t_list(type="strds", columns="name").stdout


def test_c_with_overwrite_leaves_the_source_as_it_was(tools, prefix):
    name, maps = _make(tools, prefix)

    tools.t_copy(input=name, output=f"{prefix}_copy", flags="c", overwrite=True)

    assert _names(tools, "strds", name) == maps


@pytest.mark.parametrize(("stds_type", "map_type"), TYPES[1:])
def test_c_copies_3d_and_vector_datasets(tools, prefix, stds_type, map_type):
    name, maps = _make(tools, prefix, stds_type)

    tools.t_copy(
        type=stds_type, input=name, output=f"{prefix}_copy", flags="c", overwrite=True
    )

    assert _names(tools, stds_type, f"{prefix}_copy") == maps
