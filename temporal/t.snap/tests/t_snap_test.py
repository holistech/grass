"""Test t.snap: the end of every map becomes the start of the next map

The maps are taken in the order of their start time. The last map ends one
granularity of the dataset after its start unless it has an end of its own.
Granularity of a dataset: the largest step that fits all starts and ends, so
points on day 0, 2 and 6 give 2 days. The expected times are calculated by
hand in the cases.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, register_stds
from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.tools import ToolError

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _text(offset, *, hours=0):
    """day(offset, hours) in the form that t.rast.list prints"""
    return day(offset, hours=hours).strftime("%Y-%m-%d %H:%M:%S")


def _dataset(tools, prefix, times, *, stds_type="strds", **options):
    """Make a dataset <prefix>_ds of constant maps with the times (start, end)"""
    maps = [
        MapSpec(f"{prefix}_{number}", number, start, end)
        for number, (start, end) in enumerate(times, 1)
    ]
    create_stds(tools, stds_type, f"{prefix}_ds", maps, **options)
    return f"{prefix}_ds"


def _times(tools, name, stds_type="strds"):
    return [(row.start, row.end) for row in list_maps(tools, stds_type, name)]


def test_points_become_adjacent_intervals(tools, prefix):
    # Points on day 0, 2 and 6: the steps are 2 and 4 days, so the granularity
    # is 2 days and the last map ends on day 6 + 2 = 8.
    name = _dataset(tools, prefix, [(day(0), None), (day(2), None), (day(6), None)])
    assert stds_info(tools, "strds", name)["granularity"] == "'2 days'"

    tools.t_snap(input=name)

    assert _times(tools, name) == [
        (_text(0), _text(2)),
        (_text(2), _text(6)),
        (_text(6), _text(8)),
    ]
    info = stds_info(tools, "strds", name)
    assert info["map_time"] == "interval"
    assert info["end_time"] == f"'{_text(8)}'"
    assert info["granularity"] == "'2 days'"


def test_the_points_of_the_old_shell_test(tools, prefix):
    # Six points 14 days apart, from 2001-01-01 12:00:00. The sixth is on
    # day 70 (2001-03-12), its end 14 days later.
    starts = [day(14 * number, hours=12) for number in range(6)]
    name = _dataset(tools, prefix, [(start, None) for start in starts])

    tools.t_snap(input=name)

    expected = [
        (_text(14 * n, hours=12), _text(14 * (n + 1), hours=12)) for n in range(6)
    ]
    assert _times(tools, name) == expected
    assert expected[-1] == ("2001-03-12 12:00:00", "2001-03-26 12:00:00")


def test_overlapping_intervals_become_adjacent(tools, prefix):
    # The six intervals of the old shell test. In the order of the starts
    # (the first of January to the first of June) the first five end on the
    # start of the next map; the sixth keeps its end.
    first = [datetime(2001, month, 1) for month in range(1, 7)]
    ends = [datetime(2001, month, 1) for month in (7, 4, 4, 6, 6, 7)]
    name = _dataset(tools, prefix, list(zip(first, ends, strict=True)))

    tools.t_snap(input=name)

    assert _times(tools, name) == [
        ("2001-01-01 00:00:00", "2001-02-01 00:00:00"),
        ("2001-02-01 00:00:00", "2001-03-01 00:00:00"),
        ("2001-03-01 00:00:00", "2001-04-01 00:00:00"),
        ("2001-04-01 00:00:00", "2001-05-01 00:00:00"),
        ("2001-05-01 00:00:00", "2001-06-01 00:00:00"),
        ("2001-06-01 00:00:00", "2001-07-01 00:00:00"),
    ]


def test_gaps_between_intervals_are_closed(tools, prefix):
    # (day 0, 1), (3, 4), (10, 12): the gaps end on day 3 and day 10.
    name = _dataset(
        tools, prefix, [(day(0), day(1)), (day(3), day(4)), (day(10), day(12))]
    )

    tools.t_snap(input=name)

    # The last map has an end and keeps it.
    assert _times(tools, name) == [
        (_text(0), _text(3)),
        (_text(3), _text(10)),
        (_text(10), _text(12)),
    ]


def test_months_are_calendar_months(tools, prefix):
    # Points on the first of January, February and March: the granularity is
    # one month, so the last map ends on 1 April, not 30 days after 1 March.
    starts = [datetime(2001, month, 1) for month in (1, 2, 3)]
    name = _dataset(tools, prefix, [(start, None) for start in starts])
    assert stds_info(tools, "strds", name)["granularity"] == "'1 month'"

    tools.t_snap(input=name)

    assert _times(tools, name) == [
        ("2001-01-01 00:00:00", "2001-02-01 00:00:00"),
        ("2001-02-01 00:00:00", "2001-03-01 00:00:00"),
        ("2001-03-01 00:00:00", "2001-04-01 00:00:00"),
    ]


def test_a_second_snap_changes_nothing(tools, prefix):
    name = _dataset(tools, prefix, [(day(0), None), (day(2), None), (day(6), None)])
    tools.t_snap(input=name)
    once = _times(tools, name)

    tools.t_snap(input=name)

    assert _times(tools, name) == once


def test_a_single_point_stays_a_point(tools, prefix):
    # With one map the dataset has no granularity, so the map gets no end.
    name = _dataset(tools, prefix, [(day(0), None)])

    result = tools.t_snap(input=name)

    assert result.returncode == 0
    assert _times(tools, name) == [(_text(0), None)]
    assert stds_info(tools, "strds", name)["map_time"] == "point"


def _snap_tied(tools, prefix):
    """Snap maps of which two start together; return their times by name

    Maps 1 [day 0, day 1) and 2 [day 0, day 3) start together, map 3 is a
    point on day 5; the granularity is 1 day. The tool orders the maps by
    start time only, so which of maps 1 and 2 it takes first is not defined:
    the one it takes second is snapped to day 5, the one it takes first is
    the case under test. Returns the times of maps 1 to 3 after the snap, the
    original ends of maps 1 and 2, and the names of the map snapped to day 5
    and of the other tied map.
    """
    name = _dataset(tools, prefix, [(day(0), day(1)), (day(0), day(3)), (day(5), None)])
    tools.t_snap(input=name)
    times = {row.name: (row.start, row.end) for row in list_maps(tools, "strds", name)}
    ends = {f"{prefix}_1": _text(1), f"{prefix}_2": _text(3)}
    (snapped,) = [map_name for map_name in ends if times[map_name][1] == _text(5)]
    (other,) = [map_name for map_name in ends if map_name != snapped]
    return times, ends, snapped, other


def test_maps_with_the_start_of_the_next_map_are_not_snapped(tools, prefix):
    times, _, snapped, _ = _snap_tied(tools, prefix)

    # One tied map ends on the start of map 3 (found by that in the helper),
    # map 3 gets the granularity.
    assert times[snapped] == (_text(0), _text(5))
    assert times[f"{prefix}_3"] == (_text(5), _text(6))


def test_a_map_with_the_start_of_the_next_map_keeps_its_times(tools, prefix):
    times, ends, _, other = _snap_tied(tools, prefix)

    assert times[other] == (_text(0), ends[other])


@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_each_dataset_type_with_absolute_time(tools, prefix, stds_type):
    name = _dataset(
        tools, prefix, [(day(0), None), (day(1), None)], stds_type=stds_type
    )

    tools.t_snap(type=stds_type, input=name)

    assert _times(tools, name, stds_type) == [
        (_text(0), _text(1)),
        (_text(1), _text(2)),
    ]


@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_each_dataset_type_with_relative_time(tools, prefix, stds_type):
    # Points at 0, 3 and 5: the steps are 3 and 2, the granularity is 1.
    name = _dataset(
        tools,
        prefix,
        [(0, None), (3, None), (5, None)],
        stds_type=stds_type,
        temporaltype="relative",
        unit="days",
    )

    tools.t_snap(type=stds_type, input=name)

    assert _times(tools, name, stds_type) == [(0, 3), (3, 5), (5, 6)]
    assert stds_info(tools, stds_type, name)["map_time"] == "interval"


def test_the_points_of_the_old_shell_test_with_relative_time(tools, prefix):
    # Points 0, 14, ..., 70; the last map ends at 70 + 14.
    name = _dataset(
        tools,
        prefix,
        [(14 * n, None) for n in range(6)],
        temporaltype="relative",
        unit="days",
    )

    tools.t_snap(input=name)

    assert _times(tools, name) == [(14 * n, 14 * (n + 1)) for n in range(6)]


def test_a_map_in_two_datasets_is_snapped_in_both(tools, prefix):
    # The time belongs to the map: the first of three points (days 0, 2, 4)
    # also lies in a second dataset, which sees the new end on day 2.
    maps = [MapSpec(f"{prefix}_{n}", n, day(2 * n), None) for n in range(3)]
    create_stds(tools, "strds", f"{prefix}_a", maps)
    register_stds(tools, "strds", f"{prefix}_b", maps[:1])

    tools.t_snap(input=f"{prefix}_a")

    assert _times(tools, f"{prefix}_b") == [(_text(0), _text(2))]


def test_the_command_is_added_to_the_history(tools, prefix):
    name = _dataset(tools, prefix, [(day(0), None), (day(1), None)])

    tools.t_snap(input=name)

    history = tools.t_info(type="strds", input=name, flags="h").stdout
    assert f't.snap input="{name}"' in history.replace("\\\n", "")


def test_a_dataset_without_maps_is_left_as_it_is(tools, prefix):
    # t.shift does nothing for such a dataset.
    name = _dataset(tools, prefix, [])

    result = tools.t_snap(input=name)

    assert result.returncode == 0


def test_a_dataset_of_another_mapset_is_refused(two_mapsets, prefix):
    work, other = two_mapsets
    name = _dataset(other, prefix, [(day(0), None), (day(1), None)])

    with pytest.raises(ToolError) as error:
        work.t_snap(input=f"{name}@other")

    text = message(error.value)
    assert f"Unable to snap dataset <{name}@other> of type strds" in text
    assert "The mapset of the database does not match the current mapset" in text
    assert _times(other, name) == [(_text(0), None), (_text(1), None)]


def test_an_unknown_dataset_is_refused(tools):
    with pytest.raises(ToolError) as error:
        tools.t_snap(input="no_such_dataset")

    assert "Space time dataset <no_such_dataset> of type <strds> not found" in message(
        error.value
    )


def test_the_type_selects_the_dataset(tools, prefix):
    name = _dataset(tools, prefix, [(day(0), None), (day(1), None)])

    with pytest.raises(ToolError) as error:
        tools.t_snap(type="stvds", input=name)

    assert f"Space time dataset <{name}> of type <stvds> not found" in message(
        error.value
    )


def test_input_is_required(tools):
    with pytest.raises(ToolError) as error:
        tools.t_snap()

    assert "Required parameter <input> not set" in message(error.value)
