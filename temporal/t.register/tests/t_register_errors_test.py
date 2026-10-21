"""Test the checks of t.register: contradicting options and unusable input

Each case names the message that the library prints. The text is checked
whitespace-normalised, because the messenger wraps long lines.
"""

import pytest

from grass.temporal.testing.readback import list_maps
from grass.tools import ToolError


def _normalised(error):
    return " ".join(str(error).split())


def _register(tools, **options):
    options.setdefault("type", "raster")
    with pytest.raises(ToolError) as raised:
        tools.t_register(**options)
    return _normalised(raised.value)


def test_maps_and_file_exclude_each_other(tools, make_maps, tmp_path):
    maps = make_maps(1)
    file = tmp_path / "maps.txt"
    file.write_text(f"{maps[0]}\n")

    message = _register(tools, maps=maps[0], file=file, start="2001-01-01")

    assert "maps and file are mutually exclusive" in message


def test_end_and_increment_exclude_each_other(tools, make_maps):
    maps = make_maps(1)

    message = _register(
        tools, maps=maps[0], start="2001-01-01", end="2001-02-01", increment="1 days"
    )

    assert "end and increment are mutually exclusive" in message


def test_end_and_the_interval_flag_exclude_each_other(tools, make_maps):
    maps = make_maps(1)

    message = _register(
        tools, maps=maps[0], start="2001-01-01", end="2001-02-01", flags="i"
    )

    assert "end and the interval flag are mutually exclusive" in message


def test_increment_needs_start(tools, make_maps):
    maps = make_maps(1)

    message = _register(tools, maps=maps[0], increment="1 days")

    assert "The increment option requires the start option" in message


def test_interval_flag_needs_start(tools, make_maps):
    maps = make_maps(1)

    message = _register(tools, maps=maps[0], flags="i")

    assert "The interval flag requires the start option" in message


def test_end_needs_start(tools, make_maps):
    maps = make_maps(1)

    message = _register(tools, maps=maps[0], end="2001-02-01")

    assert "Please specify start_time and end_time" in message


def test_maps_or_file_is_needed(tools, dataset):
    message = _register(tools, input=dataset(), start="2001-01-01")

    assert "Please specify maps or file" in message


def test_unknown_dataset(tools, make_maps):
    maps = make_maps(1)

    message = _register(
        tools, input="no_such_dataset", maps=maps[0], start="2001-01-01"
    )

    assert "Space time dataset <no_such_dataset> of type <raster> not found" in message


@pytest.mark.slow
def test_unknown_map_registers_nothing(tools, make_maps, dataset):
    maps = make_maps(1)
    name = dataset()

    message = _register(
        tools, input=name, maps=f"{maps[0]},no_such_map", start="2001-01-01"
    )

    assert "Map <no_such_map> of element type 'raster' not found" in message
    assert list_maps(tools, "strds", name) == []


def test_map_without_time_needs_a_start(tools, make_maps, dataset):
    maps = make_maps(1)
    name = dataset()

    message = _register(tools, input=name, maps=maps[0])

    assert "The map has no timestamp and the start time is not set" in message


def test_absolute_time_with_a_unit(tools, make_maps, dataset):
    maps = make_maps(1)
    name = dataset()

    message = _register(
        tools, input=name, maps=maps[0], start="2001-01-01", unit="days"
    )

    assert "unit can only be set for relative time" in message


def test_relative_time_needs_a_unit(tools, make_maps, dataset):
    maps = make_maps(1)
    name = dataset(temporaltype="relative")

    message = _register(tools, input=name, maps=maps[0], start=5)

    assert "with relative time found, but no relative unit set" in message


def test_relative_time_needs_a_unit_without_a_dataset(tools, make_maps):
    maps = make_maps(1)

    message = _register(tools, maps=maps[0], start=5)

    assert "unit must be set in case of relative time stamps" in message


def test_start_that_is_no_date_counts_as_relative_time(tools, make_maps, dataset):
    maps = make_maps(1)
    name = dataset()

    message = _register(tools, input=name, maps=maps[0], start="not a date")

    assert "unit must be set in case of relative time stamps" in message


@pytest.mark.slow
def test_absolute_map_in_a_relative_dataset(tools, make_maps, dataset):
    maps = make_maps(1)
    absolute = dataset()
    relative = dataset(temporaltype="relative", suffix="_rel")
    tools.t_register(type="raster", input=absolute, maps=maps[0], start="2001-01-01")

    message = _register(
        tools, input=relative, maps=maps[0], start=3, unit="days", overwrite=True
    )

    assert "The temporal types are different" in message


def test_dataset_of_another_type(tools, make_maps, dataset):
    maps = make_maps(1)
    name = dataset(stds_type="stvds")

    message = _register(tools, input=name, maps=maps[0], start="2001-01-01")

    # The dataset is looked up among the datasets of raster maps.
    assert f"Space time dataset <{name}> of type <raster> not found" in message


def test_type_outside_the_options(tools, make_maps):
    maps = make_maps(1)

    message = _register(tools, type="bogus", maps=maps[0], start="2001-01-01")

    assert "Value <bogus> out of range for parameter <type>" in message


def _timestamp(tools, name):
    """The GRASS timestamp of a raster map, "" for a map without one"""
    try:
        return tools.r_timestamp(map=name).stdout
    except ToolError:
        return ""


def _untouched(tools, name, timestamp):
    """Assert that a refused run left the map out of the database and as it was"""
    assert name not in tools.t_list(type="raster", columns="name").stdout.split()
    assert _timestamp(tools, name) == timestamp


def test_a_map_of_the_other_temporal_type_is_not_written(tools, make_maps, dataset):
    maps = make_maps(1)
    name = dataset()
    before = _timestamp(tools, maps[0])

    message = _register(tools, input=name, maps=maps[0], start=0, unit="days")

    assert "are different" in message
    assert f"Temporal type of space time dataset <{name}@PERMANENT>" in message
    _untouched(tools, maps[0], before)


def test_a_map_with_another_relative_unit_is_not_written(tools, make_maps, dataset):
    first, second = make_maps(2)
    name = dataset(temporaltype="relative")
    tools.t_register(type="raster", input=name, maps=first, start=0, unit="days")
    before = _timestamp(tools, second)

    message = _register(tools, input=name, maps=second, start=5, unit="hours")

    assert f"Relative time units of space time dataset <{name}@PERMANENT>" in message
    _untouched(tools, second, before)


def test_a_registered_map_of_the_other_type_stops_the_run_before_writing(
    tools, make_maps, dataset
):
    fresh, registered = make_maps(2)
    tools.t_register(
        type="raster",
        input=dataset(temporaltype="relative", suffix="_rel"),
        maps=registered,
        start=0,
        unit="days",
    )
    name = dataset()
    before = _timestamp(tools, fresh)

    # Without --overwrite the registered map keeps its relative time, which
    # the absolute dataset refuses; the first map must not be written.
    message = _register(
        tools, input=name, maps=f"{fresh},{registered}", start="2001-01-01"
    )

    assert f"Temporal type of space time dataset <{name}@PERMANENT>" in message
    _untouched(tools, fresh, before)
