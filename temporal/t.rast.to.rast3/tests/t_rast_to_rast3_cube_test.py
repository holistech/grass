"""Test the 3D raster maps that t.rast.to.rast3 makes

The tool puts the maps of a dataset on top of each other, in the order of time,
one layer per step of the granularity. Gaps get a layer without values. The
vertical extent of the cube is derived from the start time: months and years
count from 1900 (month number (year - 1900) * 12 + month, year number
year - 1900), days and shorter units are days since 1900-01-01 as decimal
numbers; the resolution is the granularity in that unit.
"""

from datetime import datetime, timedelta

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import map_info

# Every test takes more than a second (measured 18.10.2026 with a serial
# pytest --durations=0).
pytestmark = pytest.mark.slow


def _cube(tools, name):
    keys = tools.r3_info(map=name, flags="g").keyval
    return {
        key: keys[key]
        for key in ("bottom", "top", "tbres", "depths", "rows", "cols", "datatype")
    } | {
        "unit": keys["vertical_units"].strip('"'),
        "timestamp": keys["timestamp"].strip('"'),
    }


def _days(moment):
    return (moment - datetime(1900, 1, 1)).total_seconds() / 86400


def _make(tools, name, starts, step, expression="1"):
    create_stds(
        tools,
        "strds",
        name,
        [
            MapSpec(f"{name}_{index}", expression, start, start + step)
            for index, start in enumerate(starts)
        ],
    )


def _starts(first, count, step):
    return [first + index * step for index in range(count)]


@pytest.mark.parametrize(
    ("unit", "step", "bottom", "resolution", "timestamp"),
    [
        (
            "days",
            timedelta(days=7),
            _days(datetime(2000, 1, 1)),
            7,
            "1 Jan 2000 00:00:00 / 22 Jan 2000 00:00:00",
        ),
        (
            "hours",
            timedelta(hours=3),
            _days(datetime(2000, 1, 1)),
            3 / 24,
            "1 Jan 2000 00:00:00 / 1 Jan 2000 09:00:00",
        ),
        (
            "minutes",
            timedelta(minutes=17),
            _days(datetime(2000, 1, 1)),
            17 / 1440,
            "1 Jan 2000 00:00:00 / 1 Jan 2000 00:51:00",
        ),
        (
            "seconds",
            timedelta(seconds=30),
            _days(datetime(2000, 1, 1)),
            30 / 86400,
            "1 Jan 2000 00:00:00 / 1 Jan 2000 00:01:30",
        ),
    ],
)
def test_short_units_count_days_from_1900(
    tools, prefix, unit, step, bottom, resolution, timestamp
):
    _make(tools, f"{prefix}_in", _starts(datetime(2000, 1, 1), 3, step), step)

    tools.t_rast_to_rast3(input=f"{prefix}_in", output=prefix)

    cube = _cube(tools, prefix)
    assert cube["unit"] == unit
    assert cube["depths"] == 3
    assert cube["timestamp"] == timestamp
    assert cube["bottom"] == pytest.approx(bottom, rel=1e-6)
    assert cube["tbres"] == pytest.approx(resolution, rel=1e-3)
    assert cube["top"] == pytest.approx(bottom + 3 * resolution, rel=1e-6)


def test_months_count_from_1900(tools, prefix):
    starts = [datetime(2001, 1 + 3 * index, 1) for index in range(3)]
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_{index}", "1", start, datetime(2001, 4 + 3 * index, 1))
            for index, start in enumerate(starts)
        ],
    )

    tools.t_rast_to_rast3(input=f"{prefix}_in", output=prefix)

    # January 2001 is the month (2001 - 1900) * 12 + 1 = 1213
    cube = _cube(tools, prefix)
    assert (cube["bottom"], cube["top"], cube["tbres"], cube["depths"]) == (
        1213,
        1222,
        3,
        3,
    )
    assert cube["unit"] == "months"
    assert cube["timestamp"] == "1 Jan 2001 00:00:00 / 1 Oct 2001 00:00:00"


def test_years_count_from_1900(tools, prefix):
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_{index}",
                "1",
                datetime(2000 + 5 * index, 1, 1),
                datetime(2005 + 5 * index, 1, 1),
            )
            for index in range(3)
        ],
    )

    tools.t_rast_to_rast3(input=f"{prefix}_in", output=prefix)

    cube = _cube(tools, prefix)
    assert (cube["bottom"], cube["top"], cube["tbres"], cube["unit"]) == (
        100,
        115,
        5,
        "years",
    )


def test_relative_time_keeps_start_and_unit(tools, prefix):
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_{index}", "1", 1000 + 100 * index, 1100 + 100 * index)
            for index in range(3)
        ],
        temporaltype="relative",
        unit="years",
    )

    tools.t_rast_to_rast3(input=f"{prefix}_in", output=prefix)

    cube = _cube(tools, prefix)
    assert (cube["bottom"], cube["top"], cube["tbres"], cube["unit"]) == (
        1000,
        1300,
        100,
        "years",
    )
    info = map_info(tools, "raster3d", prefix)
    assert info["temporal_type"] == "relative"
    assert (info["start_time"], info["end_time"]) == ("'1000'", "'1300'")


def test_the_cube_is_registered_with_the_extent_in_time(tools, prefix):
    starts = [datetime(2001, 1 + 3 * index, 1) for index in range(3)]
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_{index}", "1", start, datetime(2001, 4 + 3 * index, 1))
            for index, start in enumerate(starts)
        ],
    )

    tools.t_rast_to_rast3(input=f"{prefix}_in", output=prefix)

    info = map_info(tools, "raster3d", prefix)
    assert info["temporal_type"] == "absolute"
    assert (info["start_time"], info["end_time"]) == (
        "'2001-01-01 00:00:00'",
        "'2001-10-01 00:00:00'",
    )
