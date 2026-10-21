"""Test t.register with raster maps: start, increment, interval, end and unit

Every test creates its own maps and dataset, named after the test, because the
module shares one project. Map number n has the value n. Times are derived
from the start and the increment in the comments of each case.
"""

import pytest

from grass.temporal.testing.readback import list_maps, stds_info
from grass.tools import ToolError

# Almost every test of the module runs longer than one second (measured
# 18.10.2026 with pytest --durations).
pytestmark = pytest.mark.slow

# Each case: start, increment, interval flag, then the (start, end) of the
# three maps, the granularity and the end of the dataset.
INCREMENTS = {
    # 1 second after each other: 00:00:00-01, 01-02, 02-03; the dataset ends
    # where the last map ends.
    "seconds": (
        "2001-01-01",
        "1 seconds",
        True,
        [
            ("2001-01-01 00:00:00", "2001-01-01 00:00:01"),
            ("2001-01-01 00:00:01", "2001-01-01 00:00:02"),
            ("2001-01-01 00:00:02", "2001-01-01 00:00:03"),
        ],
        "1 second",
        "2001-01-01 00:00:03",
    ),
    # "20 seconds, 5 minutes" is 20 + 300 = 320 s = 5 min 20 s: 00:00:00,
    # 00:05:20, 00:10:40, 00:16:00.
    "seconds_and_minutes": (
        "2001-01-01",
        "20 seconds, 5 minutes",
        True,
        [
            ("2001-01-01 00:00:00", "2001-01-01 00:05:20"),
            ("2001-01-01 00:05:20", "2001-01-01 00:10:40"),
            ("2001-01-01 00:10:40", "2001-01-01 00:16:00"),
        ],
        "320 seconds",
        "2001-01-01 00:16:00",
    ),
    # 8 hours: 00:00-08:00, 08:00-16:00, 16:00-24:00 (= next day 00:00).
    "hours": (
        "2001-01-01",
        "8 hours",
        True,
        [
            ("2001-01-01 00:00:00", "2001-01-01 08:00:00"),
            ("2001-01-01 08:00:00", "2001-01-01 16:00:00"),
            ("2001-01-01 16:00:00", "2001-01-02 00:00:00"),
        ],
        "8 hours",
        "2001-01-02 00:00:00",
    ),
    # Without the interval flag the maps are time points: Jan 1, 4 and 7.
    "days_as_points": (
        "2001-01-01",
        "3 days",
        False,
        [
            ("2001-01-01 00:00:00", None),
            ("2001-01-04 00:00:00", None),
            ("2001-01-07 00:00:00", None),
        ],
        "3 days",
        "2001-01-07 00:00:00",
    ),
    # 4 weeks = 28 days: Jan 1, Jan 29 (1 + 28), Feb 26 (29 + 28 = 57 = Jan 31
    # + 26).
    "weeks_as_points": (
        "2001-01-01",
        "4 weeks",
        False,
        [
            ("2001-01-01 00:00:00", None),
            ("2001-01-29 00:00:00", None),
            ("2001-02-26 00:00:00", None),
        ],
        "28 days",
        "2001-02-26 00:00:00",
    ),
    # Calendar months: Aug 1, Oct 1, Dec 1.
    "months_as_points": (
        "2001-08-01",
        "2 months",
        False,
        [
            ("2001-08-01 00:00:00", None),
            ("2001-10-01 00:00:00", None),
            ("2001-12-01 00:00:00", None),
        ],
        "2 months",
        "2001-12-01 00:00:00",
    ),
}


def _topology(tools, name):
    """The verdict of t.topology on the time topology: valid or invalid"""
    lines = tools.t_topology(input=name).stdout.splitlines()
    (verdict,) = [line.split()[-1] for line in lines if "Temporal topology is" in line]
    return verdict


@pytest.mark.parametrize("case", INCREMENTS)
def test_start_and_increment(tools, make_maps, dataset, case):
    start, increment, interval, times, granularity, end = INCREMENTS[case]
    maps = make_maps(3)
    name = dataset()

    tools.t_register(
        type="raster",
        input=name,
        maps=",".join(maps),
        start=start,
        increment=increment,
        flags="i" if interval else "",
    )

    rows = list_maps(tools, "strds", name)
    assert [(row.name, row.start, row.end) for row in rows] == [
        (map_name, *time) for map_name, time in zip(maps, times, strict=True)
    ]
    info = stds_info(tools, "strds", name)
    assert info["number_of_maps"] == 3
    assert info["granularity"] == f"'{granularity}'"
    assert info["start_time"] == f"'{times[0][0]}'"
    assert info["end_time"] == f"'{end}'"
    assert info["map_time"] == ("interval" if interval else "point")
    # Adjacent intervals and equally spaced points have no overlap.
    assert _topology(tools, name) == "valid"


def test_the_time_is_written_to_the_maps(tools, make_maps, dataset):
    # An interval is stored as "start / end" in the time stamp of the map in
    # the GRASS database, a point as the start alone.
    maps = make_maps(2)
    name = dataset()
    tools.t_register(
        type="raster",
        input=name,
        maps=",".join(maps),
        start="2001-01-01",
        increment="8 hours",
        flags="i",
    )
    points = dataset(suffix="_points")
    tools.t_register(
        type="raster",
        input=points,
        maps=maps[0],
        start="2002-03-04 05:06:07",
        overwrite=True,
    )

    assert tools.r_timestamp(map=maps[1]).stdout.strip() == (
        "1 Jan 2001 08:00:00 / 1 Jan 2001 16:00:00"
    )
    assert tools.r_timestamp(map=maps[0]).stdout.strip() == "4 Mar 2002 05:06:07"


def test_start_without_increment_puts_all_maps_at_the_start(tools, make_maps, dataset):
    maps = make_maps(3)
    name = dataset()

    tools.t_register(type="raster", input=name, maps=",".join(maps), start="2001-05-06")

    rows = list_maps(tools, "strds", name)
    assert {(row.start, row.end) for row in rows} == {("2001-05-06 00:00:00", None)}
    assert stds_info(tools, "strds", name)["granularity"] == "'None'"
    # Several maps at one point in time are not a valid topology.
    assert _topology(tools, name) == "invalid"


def test_start_and_end_give_every_map_the_same_interval(tools, make_maps, dataset):
    maps = make_maps(2)
    name = dataset()

    tools.t_register(
        type="raster",
        input=name,
        maps=",".join(maps),
        start="2001-01-01",
        end="2001-03-01",
    )

    rows = list_maps(tools, "strds", name)
    assert {(row.start, row.end) for row in rows} == {
        ("2001-01-01 00:00:00", "2001-03-01 00:00:00")
    }


@pytest.mark.parametrize(
    ("start", "expected"),
    [
        ("2001-02-03", "2001-02-03 00:00:00"),
        ("2001-02-03 04:05", "2001-02-03 04:05:00"),
        ("2001-02-03 04:05:06", "2001-02-03 04:05:06"),
        ("2001-02-03T04:05:06", "2001-02-03 04:05:06"),
    ],
)
def test_start_formats(tools, make_maps, dataset, start, expected):
    maps = make_maps(1)
    name = dataset()

    tools.t_register(type="raster", input=name, maps=maps[0], start=start)

    assert list_maps(tools, "strds", name)[0].start == expected


def test_complex_increment_and_re_registering(tools, make_maps, dataset):
    # Calendar arithmetic of the increment "20 years, 3 months, 1 days,
    # 4 hours": map n is at start + (n - 1) times the increment, so map 2 is
    # at 2021-04-02 04:00 (2001 + 20 years, Jan + 3 months, day 1 + 1, +4 h)
    # and map 3 at 2041-07-03 08:00 (twice the increment). The later maps and
    # the second round are the values of the former gunittest, kept as they
    # were: six maps, "99 years, 9 months, 9 days, 9 hours", and with the
    # interval flag the end of an interval is the start plus one increment of
    # the start, not the start of the next map.
    maps = make_maps(6)
    name = dataset()
    options = {"type": "raster", "input": name, "maps": ",".join(maps)}

    tools.t_register(
        start="2001-01-01", increment="20 years, 3 months, 1 days, 4 hours", **options
    )
    first = [row.start for row in list_maps(tools, "strds", name)]
    first_info = stds_info(tools, "strds", name)
    first_topology = _topology(tools, name)
    tools.t_register(
        start="2001-01-01",
        increment="99 years, 9 months, 9 days, 9 hours",
        overwrite=True,
        **options,
    )
    second = [row.start for row in list_maps(tools, "strds", name)]
    second_info = stds_info(tools, "strds", name)
    second_topology = _topology(tools, name)
    tools.t_register(
        start="2001-01-01",
        increment="99 years, 9 months, 9 days, 9 hours",
        flags="i",
        overwrite=True,
        **options,
    )
    third = [(row.start, row.end) for row in list_maps(tools, "strds", name)]
    third_info = stds_info(tools, "strds", name)
    third_topology = _topology(tools, name)

    assert first == [
        "2001-01-01 00:00:00",
        "2021-04-02 04:00:00",
        "2041-07-03 08:00:00",
        "2061-10-04 12:00:00",
        "2082-01-05 16:00:00",
        "2102-04-06 20:00:00",
    ]
    assert second == [
        "2001-01-01 00:00:00",
        "2100-10-10 09:00:00",
        "2200-07-19 18:00:00",
        "2300-04-29 03:00:00",
        "2400-02-07 12:00:00",
        "2499-11-16 21:00:00",
    ]
    assert third == [
        ("2001-01-01 00:00:00", "2100-10-10 09:00:00"),
        ("2100-10-10 09:00:00", "2200-07-19 18:00:00"),
        ("2200-07-19 18:00:00", "2300-04-29 03:00:00"),
        ("2300-04-29 03:00:00", "2400-02-07 12:00:00"),
        ("2400-02-07 12:00:00", "2499-11-17 21:00:00"),
        ("2499-11-16 21:00:00", "2599-08-26 06:00:00"),
    ]
    # The granularity is the greatest common divisor of the gaps between the
    # starts; the intervals of the third round are as long as the gaps. In
    # hours, from the starts above, the first round has the gaps 24 d + 4 with
    # d = 7396, 7397, 7398, 7398, 7395, so 4 divides every gap, and
    # gcd(177508, 177532) = gcd(177508, 24) = 4, because 177508 = 4 * 44377
    # with 44377 odd and its digit sum 25 not divisible by 3. The second
    # round has the gaps 24 d + 9 with d = 36441, 36441, 36442, 36443, 36442,
    # so 3 divides every gap, and gcd(874593, 874617) = gcd(874593, 24) = 3,
    # because 874593 is odd and its digit sum 36 is divisible by 3. The values
    # are those of the former gunittest.
    assert first_info["granularity"] == "'4 hours'"
    assert second_info["granularity"] == "'3 hours'"
    assert third_info["granularity"] == "'3 hours'"
    # The dataset ends with the last start (points) or the last end.
    assert first_info["end_time"] == "'2102-04-06 20:00:00'"
    assert second_info["end_time"] == "'2499-11-16 21:00:00'"
    assert third_info["end_time"] == "'2599-08-26 06:00:00'"
    # Points are valid; the intervals of the last round start where the one
    # before ends only up to the clipped day (2499-11-16 against -17).
    assert (first_topology, second_topology, third_topology) == (
        "valid",
        "valid",
        "invalid",
    )
    # The map time stamp follows the last registration.
    assert tools.r_timestamp(map=maps[2]).stdout.strip() == (
        "19 Jul 2200 18:00:00 / 29 Apr 2300 03:00:00"
    )


def test_a_registered_map_keeps_its_time_without_overwrite(tools, make_maps, dataset):
    maps = make_maps(1)
    first = dataset()
    second = dataset(suffix="_second")
    tools.t_register(type="raster", input=first, maps=maps[0], start="2001-01-01")

    result = tools.t_register(
        type="raster", input=second, maps=maps[0], start="2005-05-05"
    )

    assert "Overwrite flag is not set" in " ".join(result.stderr.split())
    assert list_maps(tools, "strds", second)[0].start == "2001-01-01 00:00:00"


def test_overwrite_changes_the_time_of_a_registered_map(tools, make_maps, dataset):
    maps = make_maps(1)
    name = dataset()
    tools.t_register(type="raster", input=name, maps=maps[0], start="2001-01-01")

    tools.t_register(
        type="raster", input=name, maps=maps[0], start="2005-05-05", overwrite=True
    )

    assert list_maps(tools, "strds", name)[0].start == "2005-05-05 00:00:00"


def test_maps_can_be_registered_without_a_dataset(tools, make_maps):
    maps = make_maps(2)

    tools.t_register(
        type="raster",
        maps=",".join(maps),
        start="2001-01-01",
        increment="1 days",
        flags="i",
    )

    result = tools.t_list(
        type="raster",
        columns="name,start_time,end_time",
        where=f"name IN ('{maps[0]}', '{maps[1]}')",
        order="start_time",
        format="json",
    )
    assert [
        (row["name"], row["start_time"], row["end_time"]) for row in result.json
    ] == [
        (maps[0], "2001-01-01 00:00:00", "2001-01-02 00:00:00"),
        (maps[1], "2001-01-02 00:00:00", "2001-01-03 00:00:00"),
    ]


def test_type_defaults_to_raster(tools, make_maps, dataset):
    maps = make_maps(1)
    name = dataset()

    tools.t_register(input=name, maps=maps[0], start="2001-01-01")

    assert [row.name for row in list_maps(tools, "strds", name)] == maps


@pytest.mark.parametrize(
    "unit", ["years", "months", "days", "hours", "minutes", "seconds"]
)
def test_relative_time_unit(tools, make_maps, dataset, unit):
    # Relative times are plain numbers in the unit: 10, 15, 20 with the
    # increment 5 and the interval flag.
    maps = make_maps(3)
    name = dataset(temporaltype="relative")

    tools.t_register(
        type="raster",
        input=name,
        maps=",".join(maps),
        start=10,
        increment=5,
        unit=unit,
        flags="i",
    )

    rows = list_maps(tools, "strds", name)
    assert [(row.start, row.end) for row in rows] == [(10, 15), (15, 20), (20, 25)]
    info = stds_info(tools, "strds", name)
    assert info["unit"] == unit
    assert (info["granularity"], info["end_time"]) == (5, "'25'")
    assert tools.r_timestamp(map=maps[0]).stdout.strip() == f"10 {unit} / 15 {unit}"


def test_relative_start_and_end(tools, make_maps, dataset):
    maps = make_maps(2)
    name = dataset(temporaltype="relative")

    tools.t_register(
        type="raster",
        input=name,
        maps=",".join(maps),
        start=3,
        end=8,
        unit="days",
    )

    assert {(row.start, row.end) for row in list_maps(tools, "strds", name)} == {(3, 8)}


def test_unit_is_refused_for_an_invalid_value(tools, make_maps, dataset):
    maps = make_maps(1)
    name = dataset(temporaltype="relative")

    with pytest.raises(
        ToolError,
        match=r"Value\s+<weeks>\s+out\s+of\s+range\s+for\s+parameter\s+<unit>",
    ):
        tools.t_register(type="raster", input=name, maps=maps[0], start=1, unit="weeks")


def test_time_read_from_the_map_is_used_without_start(tools, make_maps, dataset):
    # r.timestamp sets the time in the GRASS database; t.register without
    # start takes it from there, intervals and points alike. The dataset
    # orders the maps by time: 1950, 1995, 1996, 1998. The shortest interval
    # is one day, so that is the granularity; there are three gaps between
    # four maps.
    maps = make_maps(4)
    times = [
        "1 jan 1995 / 23 sep 1995",
        "14 jul 1996 / 15 jul 1996",
        "1 mar 1998",
        "17 mar 1950 / 28 apr 1960",
    ]
    for map_name, time in zip(maps, times, strict=True):
        tools.r_timestamp(map=map_name, date=time)
    name = dataset()

    tools.t_register(type="raster", input=name, maps=",".join(maps))

    rows = list_maps(tools, "strds", name)
    assert [(row.name, row.start, row.end) for row in rows] == [
        (maps[3], "1950-03-17 00:00:00", "1960-04-28 00:00:00"),
        (maps[0], "1995-01-01 00:00:00", "1995-09-23 00:00:00"),
        (maps[1], "1996-07-14 00:00:00", "1996-07-15 00:00:00"),
        (maps[2], "1998-03-01 00:00:00", None),
    ]
    info = stds_info(tools, "strds", name)
    assert (info["start_time"], info["end_time"]) == (
        "'1950-03-17 00:00:00'",
        "'1998-03-01 00:00:00'",
    )
    assert (info["granularity"], info["map_time"]) == ("'1 day'", "mixed")


def test_time_and_label_are_read_from_the_map(tools, make_maps, dataset):
    # Three maps with an interval of 8 hours each, set with r.timestamp, and
    # a semantic label, set with r.support: registered without any option
    # but the dataset.
    maps = make_maps(3)
    stamps = [
        "1 jan 2001 00:00:00 / 1 jan 2001 08:00:00",
        "1 jan 2001 08:00:00 / 1 jan 2001 16:00:00",
        "1 jan 2001 16:00:00 / 2 jan 2001 00:00:00",
    ]
    for map_name, stamp in zip(maps, stamps, strict=True):
        tools.r_timestamp(map=map_name, date=stamp)
        tools.r_support(map=map_name, semantic_label="S2_1")
    name = dataset()

    tools.t_register(type="raster", input=name, maps=",".join(maps))

    rows = list_maps(tools, "strds", name)
    assert [(row.name, row.start, row.end) for row in rows] == [
        (maps[0], "2001-01-01 00:00:00", "2001-01-01 08:00:00"),
        (maps[1], "2001-01-01 08:00:00", "2001-01-01 16:00:00"),
        (maps[2], "2001-01-01 16:00:00", "2001-01-02 00:00:00"),
    ]
    info = stds_info(tools, "strds", name)
    assert info["granularity"] == "'8 hours'"
    assert (info["start_time"], info["end_time"]) == (
        "'2001-01-01 00:00:00'",
        "'2001-01-02 00:00:00'",
    )
    assert (info["number_of_semantic_labels"], info["semantic_labels"]) == (1, "S2_1")
    assert _topology(tools, name) == "valid"


def test_semantic_label_is_read_from_the_map(tools, make_maps, dataset):
    maps = make_maps(2)
    tools.r_support(map=maps[0], semantic_label="S2_1")
    tools.r_support(map=maps[1], semantic_label="S2_1")
    name = dataset()

    tools.t_register(
        type="raster",
        input=name,
        maps=",".join(maps),
        start="2001-01-01",
        increment="1 days",
    )

    info = stds_info(tools, "strds", name)
    assert (info["number_of_semantic_labels"], info["semantic_labels"]) == (1, "S2_1")
    result = tools.t_rast_list(input=name, columns="name,semantic_label", format="json")
    assert [row["semantic_label"] for row in result.json["data"]] == ["S2_1", "S2_1"]


def test_a_month_increment_from_day_31_fails(tools, make_maps, dataset):
    # January 31 plus one month is no date. The call stops with the message of
    # the date arithmetic and registers nothing.
    maps = make_maps(2)
    name = dataset()

    with pytest.raises(ToolError, match=r"day\s+is\s+out\s+of\s+range\s+for\s+month"):
        tools.t_register(
            type="raster",
            input=name,
            maps=",".join(maps),
            start="2001-01-31",
            increment="1 months",
        )

    assert list_maps(tools, "strds", name) == []
