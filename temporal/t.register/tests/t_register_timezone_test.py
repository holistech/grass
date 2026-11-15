"""Test t.register with time zones in the start and end times

Absolute times may carry an offset, "2001-01-01 10:00:00 +02:00". The database
keeps the offset; the time stamp that GRASS writes to the map is built by
datetime_to_grass_datetime_string(). The results must not depend on the time
zone of the process, so the module runs with three values of TZ in the
environment of the tools.
"""

import pytest

from grass.temporal.testing.data import make_map, register_file
from grass.temporal.testing.readback import list_maps, message, stds_info
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


def other_offset_message(map_id, name, offset, other):
    """The refusal of a time whose offset is not that of the dataset"""
    return (
        f"Unable to register raster map <{map_id}>. Its time has the time zone "
        f"offset {offset}, the space time dataset <{name}> has {other}. A space "
        "time dataset holds one offset and no daylight saving time; write the "
        f"times with the offset {other}."
    )


def test_file_with_start_and_end_in_different_zones_is_refused(
    zone_tools, prefix, tmp_path
):
    """Start in +01:00, end in -01:00: a dataset holds one offset, so nothing
    is written"""
    maps, name = _maps_and_dataset(zone_tools, prefix, 2)
    file = register_file(
        tmp_path / "maps.txt",
        [
            (maps[0], "2001-01-01 12:00:00 +01:00", "2001-04-01 14:00:00 -01:00"),
            (maps[1], "2001-04-01 12:00:00 +01:00", "2001-07-01 14:00:00 -01:00"),
        ],
    )

    with pytest.raises(ToolError) as error:
        zone_tools.t_register(type="raster", input=name, file=file)

    assert other_offset_message(
        f"{maps[0]}@PERMANENT", name, "-01:00", "+01:00"
    ) in message(error.value)
    assert "Traceback" not in error.value.stderr
    assert list_maps(zone_tools, "strds", name) == []


def test_a_day_into_summer_time_is_refused(zone_tools, prefix, tmp_path):
    """The day of the change from +01:00 to +02:00 lasts 23 hours; the map
    after it is refused as well, and no map of the file is written"""
    maps, name = _maps_and_dataset(zone_tools, prefix, 3)
    file = register_file(
        tmp_path / "maps.txt",
        [
            (maps[0], "2001-03-24 00:00:00 +01:00", "2001-03-25 00:00:00 +01:00"),
            (maps[1], "2001-03-25 00:00:00 +01:00", "2001-03-26 00:00:00 +02:00"),
            (maps[2], "2001-03-26 00:00:00 +02:00", "2001-03-27 00:00:00 +02:00"),
        ],
    )

    with pytest.raises(ToolError) as error:
        zone_tools.t_register(type="raster", input=name, file=file)

    assert other_offset_message(
        f"{maps[1]}@PERMANENT", name, "+02:00", "+01:00"
    ) in message(error.value)
    assert list_maps(zone_tools, "strds", name) == []


@pytest.mark.parametrize(
    ("first", "second", "offset", "other"),
    [
        ("+01:00", "+02:00", "+02:00", "+01:00"),
        # +00:00 is an offset of length zero, still an offset of its own.
        ("+01:00", "+00:00", "+00:00", "+01:00"),
        ("+00:00", "-05:00", "-05:00", "+00:00"),
    ],
)
def test_another_offset_than_that_of_the_dataset_is_refused(
    zone_tools, prefix, first, second, offset, other
):
    maps, name = _maps_and_dataset(zone_tools, prefix, 2)
    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start=f"2001-01-01 10:00:00{first}"
    )

    with pytest.raises(ToolError) as error:
        zone_tools.t_register(
            type="raster",
            input=name,
            maps=maps[1],
            start=f"2001-01-02 10:00:00{second}",
        )

    assert other_offset_message(f"{maps[1]}@PERMANENT", name, offset, other) in message(
        error.value
    )
    assert _rows(zone_tools, name) == [(maps[0], f"2001-01-01 10:00:00{first}", None)]
    # The refused map got no time stamp either (r.timestamp fails without one).
    with pytest.raises(ToolError):
        zone_tools.r_timestamp(map=maps[1])


def test_known_maps_with_another_offset_are_refused(zone_tools, prefix):
    """Maps entered without a dataset keep their times; added to a dataset
    later, those are checked as new times are"""
    maps, name = _maps_and_dataset(zone_tools, prefix, 2)
    zone_tools.t_register(
        type="raster", maps=maps[0], start="2001-03-24 00:00:00 +01:00"
    )
    zone_tools.t_register(
        type="raster", maps=maps[1], start="2001-03-26 00:00:00 +02:00"
    )

    with pytest.raises(ToolError) as error:
        zone_tools.t_register(type="raster", input=name, maps=",".join(maps))

    assert other_offset_message(
        f"{maps[1]}@PERMANENT", name, "+02:00", "+01:00"
    ) in message(error.value)
    assert list_maps(zone_tools, "strds", name) == []


def test_a_new_time_with_another_offset_is_refused_for_the_datasets_of_the_map(
    zone_tools, prefix
):
    """--overwrite without input updates the datasets that hold the map"""
    maps, name = _maps_and_dataset(zone_tools, prefix, 2)
    zone_tools.t_register(
        type="raster",
        input=name,
        maps=",".join(maps),
        start="2001-01-01 00:00:00 +01:00",
        increment="1 day",
        flags="i",
    )
    before = _rows(zone_tools, name)

    with pytest.raises(ToolError) as error:
        zone_tools.t_register(
            type="raster",
            maps=maps[1],
            start="2001-01-02 00:00:00 +02:00",
            overwrite=True,
        )

    assert other_offset_message(
        f"{maps[1]}@PERMANENT", f"{name}@PERMANENT", "+02:00", "+01:00"
    ) in message(error.value)
    assert _rows(zone_tools, name) == before


def test_the_only_map_of_a_dataset_takes_another_offset(zone_tools, prefix):
    """The old time of the map is replaced, so it does not count"""
    maps, name = _maps_and_dataset(zone_tools, prefix, 1)
    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start="2001-01-01 00:00:00 +01:00"
    )

    zone_tools.t_register(
        type="raster",
        maps=maps[0],
        start="2001-01-01 00:00:00 +02:00",
        overwrite=True,
    )

    assert _rows(zone_tools, name) == [(maps[0], "2001-01-01 00:00:00+02:00", None)]


def test_the_same_offset_with_another_spelling_is_registered(zone_tools, prefix):
    maps, name = _maps_and_dataset(zone_tools, prefix, 2)
    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start="2001-01-01 10:00:00+01:00"
    )

    zone_tools.t_register(
        type="raster", input=name, maps=maps[1], start="2001-01-02 10:00:00 +0100"
    )

    assert [row[1] for row in _rows(zone_tools, name)] == [
        "2001-01-01 10:00:00+01:00",
        "2001-01-02 10:00:00+01:00",
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


def test_a_failed_call_does_not_change_the_dataset(zone_tools, prefix):
    maps, name = _maps_and_dataset(zone_tools, prefix, 2)
    zone_tools.t_register(
        type="raster", input=name, maps=maps[0], start="2001-01-01 10:00:00 +02:00"
    )

    with pytest.raises(ToolError) as error:
        zone_tools.t_register(
            type="raster", input=name, maps=maps[1], start="2001-01-02 10:00:00"
        )

    assert "time zone" in str(error.value)
    assert "Traceback" not in str(error.value)
    assert stds_info(zone_tools, "strds", name)["number_of_maps"] == 1
    # The refused map got no time stamp either (r.timestamp fails without one).
    with pytest.raises(ToolError):
        zone_tools.r_timestamp(map=maps[1])


def test_a_refusal_later_in_the_list_writes_no_map(zone_tools, prefix, tmp_path):
    # The first map of the file agrees with itself, the second has no time
    # zone: the refusal must come before the first map is written.
    maps, name = _maps_and_dataset(zone_tools, prefix, 2)
    file = register_file(
        tmp_path / "maps.txt",
        [(maps[0], "2001-01-01 10:00:00 +02:00"), (maps[1], "2001-01-02 10:00:00")],
    )

    with pytest.raises(ToolError, match="time zone"):
        zone_tools.t_register(type="raster", input=name, file=file)

    assert list_maps(zone_tools, "strds", name) == []
    # Neither map got a time stamp (r.timestamp fails without one).
    for map_name in maps:
        with pytest.raises(ToolError):
            zone_tools.r_timestamp(map=map_name)
