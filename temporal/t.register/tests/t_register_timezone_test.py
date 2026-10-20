"""Test t.register with time zones in the start and end times

Absolute times may carry an offset, "2001-01-01 10:00:00 +02:00". The database
keeps the offset; the time stamp that GRASS writes to the map is built by
datetime_to_grass_datetime_string(). The results must not depend on the time
zone of the process, so the module runs with three values of TZ in the
environment of the tools.
"""

import pytest

from grass.temporal.testing.data import make_map, register_file
from grass.temporal.testing.readback import list_maps, stds_info
from grass.temporal.testing.session import project_session
from grass.tools import ToolError, Tools

# Almost every test of the module runs longer than one second (measured
# 18.10.2026 with pytest --durations).
pytestmark = pytest.mark.slow

ZONES = ["UTC", "Asia/Kathmandu", "America/New_York"]


@pytest.fixture(scope="module", params=ZONES)
def zone_tools(request, tmp_path_factory):
    """Tools whose subprocesses run with TZ set to the parameter"""
    with project_session(tmp_path_factory.mktemp("zone") / "project") as session:
        session.env["TZ"] = request.param
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        yield tools


def _maps_and_dataset(tools, prefix, count):
    names = []
    for number in range(1, count + 1):
        make_map(tools, "raster", f"{prefix}_{number}", number)
        names.append(f"{prefix}_{number}")
    tools.t_create(output=prefix, title="t", description="d")
    return names, prefix


def _rows(tools, name):
    return [(row.name, row.start, row.end) for row in list_maps(tools, "strds", name)]


OFFSET_IN_JANUARY = {
    "UTC": "+0000",
    "Asia/Kathmandu": "+0545",
    "America/New_York": "-0500",
}


def test_the_environment_reaches_the_tools(zone_tools, request):
    # Without this the module would test one zone three times.
    result = zone_tools.run_cmd(["date", "-d", "2001-01-01 12:00", "+%z"])

    zone = request.node.callspec.params["zone_tools"]
    assert result.stdout.strip() == OFFSET_IN_JANUARY[zone]


def test_start_with_an_offset_is_kept(zone_tools, prefix):
    maps, name = _maps_and_dataset(zone_tools, prefix, 1)

    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start="2001-01-01 10:00:00 +02:00"
    )

    assert _rows(zone_tools, name) == [(maps[0], "2001-01-01 10:00:00+02:00", None)]


@pytest.mark.parametrize(
    "start",
    [
        "2001-01-01 10:00:00 +0200",
        "2001-01-01 10:00:00+02:00",
        "2001-01-01T10:00:00+02:00",
    ],
)
def test_forms_of_the_offset(zone_tools, prefix, start):
    maps, name = _maps_and_dataset(zone_tools, prefix, 1)

    zone_tools.t_register(type="raster", input=name, maps=maps[0], start=start)

    assert _rows(zone_tools, name)[0][1] == "2001-01-01 10:00:00+02:00"


def test_offset_with_minutes(zone_tools, prefix):
    maps, name = _maps_and_dataset(zone_tools, prefix, 1)

    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start="2001-01-01 10:00:00+05:45"
    )

    assert _rows(zone_tools, name)[0][1] == "2001-01-01 10:00:00+05:45"


def test_utc_designator(zone_tools, prefix):
    maps, name = _maps_and_dataset(zone_tools, prefix, 1)

    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start="2001-01-01 10:00:00 Z"
    )

    assert _rows(zone_tools, name)[0][1] == "2001-01-01 10:00:00+00:00"


def test_time_without_an_offset_stays_as_given(zone_tools, prefix):
    # No conversion to or from the zone of the process.
    maps, name = _maps_and_dataset(zone_tools, prefix, 1)

    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start="2001-01-01 10:00:00"
    )

    assert _rows(zone_tools, name) == [(maps[0], "2001-01-01 10:00:00", None)]


def test_file_with_start_times_and_offsets(zone_tools, prefix, tmp_path):
    maps, name = _maps_and_dataset(zone_tools, prefix, 3)
    file = register_file(
        tmp_path / "maps.txt",
        [
            (maps[0], "2001-01-01 10:00:00 +02:00"),
            (maps[1], "2001-02-01 10:00:00 +02:00"),
            (maps[2], "2001-03-01 10:00:00 +02:00"),
        ],
    )

    zone_tools.t_register(type="raster", input=name, file=file)

    assert _rows(zone_tools, name) == [
        (maps[0], "2001-01-01 10:00:00+02:00", None),
        (maps[1], "2001-02-01 10:00:00+02:00", None),
        (maps[2], "2001-03-01 10:00:00+02:00", None),
    ]


def test_file_with_start_and_end_in_different_zones(zone_tools, prefix, tmp_path):
    # Start in +01:00, end in -01:00: both offsets are kept as written.
    maps, name = _maps_and_dataset(zone_tools, prefix, 2)
    file = register_file(
        tmp_path / "maps.txt",
        [
            (maps[0], "2001-01-01 12:00:00 +01:00", "2001-04-01 14:00:00 -01:00"),
            (maps[1], "2001-04-01 12:00:00 +01:00", "2001-07-01 14:00:00 -01:00"),
        ],
    )

    zone_tools.t_register(type="raster", input=name, file=file)

    assert _rows(zone_tools, name) == [
        (maps[0], "2001-01-01 12:00:00+01:00", "2001-04-01 14:00:00-01:00"),
        (maps[1], "2001-04-01 12:00:00+01:00", "2001-07-01 14:00:00-01:00"),
    ]


def test_increment_keeps_the_offset(zone_tools, prefix):
    maps, name = _maps_and_dataset(zone_tools, prefix, 2)

    zone_tools.t_register(
        type="raster",
        input=name,
        maps=",".join(maps),
        start="2001-01-30 10:00:00 +01:00",
        increment="1 days",
    )

    assert [row[1] for row in _rows(zone_tools, name)] == [
        "2001-01-30 10:00:00+01:00",
        "2001-01-31 10:00:00+01:00",
    ]


@pytest.mark.parametrize(
    ("offset", "written"), [("+01:00", "+0100"), ("-01:00", "-0100")]
)
def test_grass_time_stamp_for_whole_hours_up_to_one(
    zone_tools, prefix, offset, written
):
    maps, name = _maps_and_dataset(zone_tools, prefix, 1)

    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start=f"2001-01-01 10:00:00 {offset}"
    )

    assert zone_tools.r_timestamp(map=maps[0]).stdout.strip() == (
        f"1 Jan 2001 10:00:00 {written}"
    )


@pytest.mark.parametrize(
    ("start", "expected"),
    [
        ("2001-01-01 10:00:00 +05:45", "1 Jan 2001 10:00:00 +0545"),
        ("2001-01-01 10:00:00 -03:30", "1 Jan 2001 10:00:00 -0330"),
        ("2001-01-01 10:00:00 +00:00", "1 Jan 2001 10:00:00 +0000"),
    ],
)
def test_grass_time_stamp_has_hours_and_minutes_of_the_offset(
    zone_tools, prefix, start, expected
):
    maps, name = _maps_and_dataset(zone_tools, prefix, 1)

    zone_tools.t_register(type="raster", input=name, maps=maps[0], start=start)

    assert zone_tools.r_timestamp(map=maps[0]).stdout.strip() == expected


def test_grass_time_stamp_of_two_hours(zone_tools, prefix):
    maps, name = _maps_and_dataset(zone_tools, prefix, 1)

    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start="2001-01-01 10:00:00 +02:00"
    )

    assert zone_tools.r_timestamp(map=maps[0]).stdout.strip() == (
        "1 Jan 2001 10:00:00 +0200"
    )


def test_today_a_time_without_offset_in_a_dataset_with_offsets_fails(
    zone_tools, prefix
):
    maps, name = _maps_and_dataset(zone_tools, prefix, 2)
    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start="2001-01-01 10:00:00 +02:00"
    )

    with pytest.raises(
        ToolError, match=r"can't\s+compare\s+offset-naive\s+and\s+offset-aware"
    ):
        zone_tools.t_register(
            type="raster", input=name, maps=maps[1], start="2001-01-02 10:00:00"
        )

    # The map is in the dataset although the call failed.
    assert stds_info(zone_tools, "strds", name)["number_of_maps"] == 2


@pytest.mark.xfail(
    strict=True,
    reason="a failed t.register of a time without offset into a dataset with offsets leaves the dataset changed",
)
def test_a_failed_call_does_not_change_the_dataset(zone_tools, prefix):
    maps, name = _maps_and_dataset(zone_tools, prefix, 2)
    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start="2001-01-01 10:00:00 +02:00"
    )

    with pytest.raises(ToolError):
        zone_tools.t_register(
            type="raster", input=name, maps=maps[1], start="2001-01-02 10:00:00"
        )

    assert stds_info(zone_tools, "strds", name)["number_of_maps"] == 1
