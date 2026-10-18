"""Test t.register with 3D raster maps in space time 3D raster datasets

The maps are constant (map number n has the value n). The time arithmetic is
that of the raster module; these tests show that type=raster_3d reaches the
3D raster tables and the 3D time stamp.
"""

import pytest

from grass.temporal.testing.readback import list_maps, stds_info


def test_intervals_of_seconds(tools, make_maps, dataset):
    maps = make_maps(3, kind="raster_3d")
    name = dataset(stds_type="str3ds")

    tools.t_register(
        type="raster_3d",
        input=name,
        maps=",".join(maps),
        start="2001-01-01",
        increment="1 seconds",
        flags="i",
    )

    rows = list_maps(tools, "str3ds", name)
    assert [(row.name, row.start, row.end, row.min, row.max) for row in rows] == [
        (maps[0], "2001-01-01 00:00:00", "2001-01-01 00:00:01", 1.0, 1.0),
        (maps[1], "2001-01-01 00:00:01", "2001-01-01 00:00:02", 2.0, 2.0),
        (maps[2], "2001-01-01 00:00:02", "2001-01-01 00:00:03", 3.0, 3.0),
    ]
    info = stds_info(tools, "str3ds", name)
    assert info["number_of_maps"] == 3
    assert info["granularity"] == "'1 second'"


@pytest.mark.parametrize(
    ("increment", "starts", "granularity"),
    [
        # Every 3 days: Jan 1, 4, 7.
        ("3 days", ["2001-01-01", "2001-01-04", "2001-01-07"], "3 days"),
        # Every 4 weeks = 28 days: Jan 1, Jan 29, Feb 26.
        ("4 weeks", ["2001-01-01", "2001-01-29", "2001-02-26"], "28 days"),
        # Every 2 months.
        ("2 months", ["2001-01-01", "2001-03-01", "2001-05-01"], "2 months"),
    ],
)
def test_time_points(tools, make_maps, dataset, increment, starts, granularity):
    maps = make_maps(3, kind="raster_3d")
    name = dataset(stds_type="str3ds")

    tools.t_register(
        type="raster_3d",
        input=name,
        maps=",".join(maps),
        start="2001-01-01",
        increment=increment,
    )

    rows = list_maps(tools, "str3ds", name)
    assert [(row.start, row.end) for row in rows] == [
        (f"{start} 00:00:00", None) for start in starts
    ]
    assert stds_info(tools, "str3ds", name)["granularity"] == f"'{granularity}'"


def test_time_is_written_to_the_3d_map(tools, make_maps, dataset):
    maps = make_maps(1, kind="raster_3d")
    name = dataset(stds_type="str3ds")

    tools.t_register(
        type="raster_3d",
        input=name,
        maps=maps[0],
        start="2001-01-01",
        end="2001-02-01",
    )

    assert tools.r3_timestamp(map=maps[0]).stdout.strip() == (
        "1 Jan 2001 00:00:00 / 1 Feb 2001 00:00:00"
    )


def test_relative_time(tools, make_maps, dataset):
    maps = make_maps(2, kind="raster_3d")
    name = dataset(stds_type="str3ds", temporaltype="relative")

    tools.t_register(
        type="raster_3d",
        input=name,
        maps=",".join(maps),
        start=5,
        increment=2,
        unit="hours",
        flags="i",
    )

    assert [(row.start, row.end) for row in list_maps(tools, "str3ds", name)] == [
        (5, 7),
        (7, 9),
    ]
    assert stds_info(tools, "str3ds", name)["unit"] == "hours"


def test_maps_without_a_dataset(tools, make_maps):
    # t.list type=raster_3d cannot be used to read this back: it queries a
    # view that does not exist (see the findings of t.list).
    maps = make_maps(1, kind="raster_3d")

    tools.t_register(type="raster_3d", maps=maps[0], start="2001-06-01")

    info = tools.t_info(type="raster_3d", input=maps[0], flags="g").keyval
    assert (info["start_time"], info["end_time"]) == ("'2001-06-01 00:00:00'", "'None'")
