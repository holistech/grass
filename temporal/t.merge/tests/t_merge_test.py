"""Test t.merge: overlapping datasets, an existing output, types and refusals

Six maps <prefix>_1 to <prefix>_6, map n with the value n from day n-1 to
day n (the day 0 is 2001-01-01), are registered in three datasets that
overlap as the former shell test had them: A holds maps 1 to 3, B maps 3 to 5
and C maps 4 to 6. The time belongs to the map, so every dataset shows the
same times for a map.
"""

import pytest

from grass.temporal.testing.data import MapSpec, day, make_map, register_stds
from grass.temporal.testing.readback import list_maps, stds_info
from grass.tools import ToolError

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

MEMBERS = {"a": (1, 2, 3), "b": (3, 4, 5), "c": (4, 5, 6)}


def _make(tools, prefix, stds_type="strds", members=MEMBERS, temporaltype="absolute"):
    """Create the maps and the datasets <prefix>_a ...; returns the map names"""
    map_type = {"strds": "raster", "str3ds": "raster_3d", "stvds": "vector"}[stds_type]
    numbers = sorted({n for ns in members.values() for n in ns})
    specs = {}
    for n in numbers:
        make_map(tools, map_type, f"{prefix}_{n}", n)
        times = (day(n - 1), day(n)) if temporaltype == "absolute" else (n - 1, n)
        specs[n] = MapSpec(f"{prefix}_{n}", n, *times)
    options = {"temporaltype": temporaltype}
    if temporaltype == "relative":
        options["unit"] = "days"
    for key, ns in members.items():
        register_stds(
            tools, stds_type, f"{prefix}_{key}", [specs[n] for n in ns], **options
        )
    return [specs[n].name for n in numbers]


def _names(tools, name, stds_type="strds"):
    return [row.name for row in list_maps(tools, stds_type, name)]


def _numbers(tools, prefix, name, stds_type="strds"):
    """The numbers n of the maps <prefix>_n of a dataset, in time order"""
    return [int(m.rsplit("_", 1)[1]) for m in _names(tools, name, stds_type)]


def test_a_single_dataset_is_copied(tools, prefix):
    _make(tools, prefix)

    tools.t_merge(inputs=f"{prefix}_a", output=f"{prefix}_out")

    assert _numbers(tools, prefix, f"{prefix}_out") == [1, 2, 3]
    info = stds_info(tools, "strds", f"{prefix}_out")
    assert info["start_time"] == "'2001-01-01 00:00:00'"
    assert info["end_time"] == "'2001-01-04 00:00:00'"


def test_overlapping_datasets_register_every_map_once(tools, prefix):
    _make(tools, prefix)

    tools.t_merge(inputs=f"{prefix}_a,{prefix}_b,{prefix}_c", output=f"{prefix}_out")

    assert _numbers(tools, prefix, f"{prefix}_out") == [1, 2, 3, 4, 5, 6]
    # Six one-day maps from 2001-01-01 to 2001-01-07 with the values 1 to 6.
    info = stds_info(tools, "strds", f"{prefix}_out")
    assert info["number_of_maps"] == 6
    assert info["start_time"] == "'2001-01-01 00:00:00'"
    assert info["end_time"] == "'2001-01-07 00:00:00'"
    assert info["granularity"] == "'1 day'"
    assert (info["min_min"], info["max_max"]) == (1, 6)
    # The inputs are as they were.
    for key, numbers in MEMBERS.items():
        assert _numbers(tools, prefix, f"{prefix}_{key}") == list(numbers)


def test_the_output_gets_a_default_title_and_the_semantic_type_mean(tools, prefix):
    _make(tools, prefix)

    tools.t_merge(inputs=f"{prefix}_a", output=f"{prefix}_out")

    text = " ".join(
        tools.t_info(type="strds", input=f"{prefix}_out")
        .stdout.replace("|", " ")
        .split()
    )
    assert "Title: Merged space time dataset" in text
    assert "Description: Merged space time dataset" in text
    assert stds_info(tools, "strds", f"{prefix}_out")["semantic_type"] == "mean"


def test_a_map_of_the_output_belongs_to_all_its_datasets(tools, prefix):
    maps = _make(tools, prefix)

    tools.t_merge(inputs=f"{prefix}_a,{prefix}_b", output=f"{prefix}_out")

    text = " ".join(tools.t_info(type="raster", input=maps[2]).stdout.split())
    # Map 3 is in A and in B, and now in the output.
    registered = text.split("Registered datasets")[1].split()[1].split(",")
    assert set(registered) == {
        f"{prefix}_a@PERMANENT",
        f"{prefix}_b@PERMANENT",
        f"{prefix}_out@PERMANENT",
    }


def test_the_same_input_twice_registers_the_maps_once(tools, prefix):
    _make(tools, prefix)

    tools.t_merge(inputs=f"{prefix}_a,{prefix}_a", output=f"{prefix}_out")

    assert _numbers(tools, prefix, f"{prefix}_out") == [1, 2, 3]


def test_an_existing_output_is_refused_without_overwrite(tools, prefix):
    _make(tools, prefix)
    tools.t_merge(inputs=f"{prefix}_a", output=f"{prefix}_out")

    with pytest.raises(ToolError, match=r"please\s+use\s+the\s+overwrite\s+flag"):
        tools.t_merge(inputs=f"{prefix}_b", output=f"{prefix}_out")

    assert _numbers(tools, prefix, f"{prefix}_out") == [1, 2, 3]


def test_overwrite_adds_the_maps_to_an_existing_output(tools, prefix):
    _make(tools, prefix)
    tools.t_merge(inputs=f"{prefix}_a", output=f"{prefix}_out")

    tools.t_merge(inputs=f"{prefix}_b", output=f"{prefix}_out", overwrite=True)

    # A's maps 1 to 3 stay, B adds 4 and 5; map 3 is registered once.
    assert _numbers(tools, prefix, f"{prefix}_out") == [1, 2, 3, 4, 5]
    info = stds_info(tools, "strds", f"{prefix}_out")
    assert info["number_of_maps"] == 5
    assert info["end_time"] == "'2001-01-06 00:00:00'"


def test_the_output_may_be_one_of_the_inputs(tools, prefix):
    # The former shell test: merge A into the output, take away A's maps, merge
    # A, B and C into it, then merge A, B, C and the output itself.
    _make(tools, prefix)
    out = f"{prefix}_out"
    inputs = ",".join(f"{prefix}_{key}" for key in "abc")
    tools.t_merge(inputs=f"{prefix}_a", output=out)
    tools.t_unregister(input=out, maps=",".join(f"{prefix}_{n}" for n in (1, 2, 3)))
    assert _names(tools, out) == []

    tools.t_merge(inputs=inputs, output=out, overwrite=True)
    assert _numbers(tools, prefix, out) == [1, 2, 3, 4, 5, 6]

    tools.t_merge(inputs=f"{inputs},{out}", output=out, overwrite=True)
    assert _numbers(tools, prefix, out) == [1, 2, 3, 4, 5, 6]
    assert stds_info(tools, "strds", out)["number_of_maps"] == 6


def test_datasets_of_relative_time(tools, prefix):
    _make(tools, prefix, temporaltype="relative")

    tools.t_merge(inputs=f"{prefix}_a,{prefix}_c", output=f"{prefix}_out")

    info = stds_info(tools, "strds", f"{prefix}_out")
    assert info["temporal_type"] == "relative"
    # Maps 1 to 3 and 4 to 6 give [0,3] and [3,6], so [0,6] days.
    assert (info["start_time"], info["end_time"]) == ("'0'", "'6'")
    assert info["number_of_maps"] == 6


@pytest.mark.parametrize("stds_type", ["str3ds", "stvds"])
def test_datasets_of_each_type(tools, prefix, stds_type):
    _make(tools, prefix, stds_type)

    tools.t_merge(
        type=stds_type, inputs=f"{prefix}_a,{prefix}_b", output=f"{prefix}_out"
    )

    assert _numbers(tools, prefix, f"{prefix}_out", stds_type) == [1, 2, 3, 4, 5]
    assert stds_info(tools, stds_type, f"{prefix}_out")["number_of_maps"] == 5


def test_the_type_defaults_to_strds(tools, prefix):
    _make(tools, prefix)

    tools.t_merge(type="strds", inputs=f"{prefix}_a", output=f"{prefix}_x")
    tools.t_merge(inputs=f"{prefix}_x", output=f"{prefix}_y")

    assert _numbers(tools, prefix, f"{prefix}_y") == [1, 2, 3]


def test_datasets_of_different_temporal_types_are_refused(tools, prefix):
    _make(tools, prefix)
    _make(tools, f"{prefix}_r", members={"a": (1,)}, temporaltype="relative")

    with pytest.raises(ToolError, match="must have the same temporal type"):
        tools.t_merge(inputs=f"{prefix}_a,{prefix}_r_a", output=f"{prefix}_out")

    assert f"{prefix}_out" not in tools.t_list(type="strds", columns="name").stdout


def test_an_unknown_input_is_refused(tools, prefix):
    _make(tools, prefix)

    with pytest.raises(ToolError, match=r"Space time dataset <nope> of type\s+<strds>"):
        tools.t_merge(inputs=f"{prefix}_a,nope", output=f"{prefix}_out")

    assert f"{prefix}_out" not in tools.t_list(type="strds", columns="name").stdout


def test_a_dataset_of_another_type_is_not_found(tools, prefix):
    _make(tools, prefix)

    with pytest.raises(ToolError, match=r"of type\s+<stvds> not found"):
        tools.t_merge(type="stvds", inputs=f"{prefix}_a", output=f"{prefix}_out")


def test_inputs_and_output_are_required(tools):
    with pytest.raises(ToolError, match=r"Required parameter <inputs> not set"):
        tools.t_merge(output="a")
    with pytest.raises(ToolError, match=r"Required parameter <output> not set"):
        tools.t_merge(inputs="a")


def test_an_unknown_type_is_refused(tools):
    with pytest.raises(ToolError, match="out of range for parameter <type>"):
        tools.t_merge(type="raster", inputs="a", output="b")


def test_today_an_output_with_the_current_mapset_ends_in_a_traceback(tools, prefix):
    _make(tools, prefix)

    with pytest.raises(ToolError, match="UnboundLocalError"):
        tools.t_merge(inputs=f"{prefix}_a", output=f"{prefix}_out@PERMANENT")


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_the_output_may_name_the_current_mapset(tools, prefix):
    _make(tools, prefix)

    tools.t_merge(inputs=f"{prefix}_a", output=f"{prefix}_out@PERMANENT")

    assert _numbers(tools, prefix, f"{prefix}_out") == [1, 2, 3]
