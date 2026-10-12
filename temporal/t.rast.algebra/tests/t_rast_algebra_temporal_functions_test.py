"""Test temporal functions in t.rast.algebra conditions

The datasets are described in the time_series fixture in conftest.py.
"""

import pytest

from grass.tools import ToolError, Tools


def selected_maps(session, expression, output):
    """Run the algebra and return start time and value of the selected maps"""
    tools = Tools(session=session, overwrite=True)
    tools.t_rast_algebra(expression=f"{output} = {expression}", basename=output)
    result = tools.t_rast_list(input=output, columns="start_time,min", format="json")
    return [(row["start_time"], row["min"]) for row in result["data"]]


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        # Hours 10 to 19 were not recognized as part of a datetime literal.
        (
            'start_datetime(intervals) > "2001-02-01 15:00:00"',
            [("2001-03-01 23:00:00", 3)],
        ),
        (
            'start_datetime(intervals) >= "2001-02-01 15:00:00"',
            [("2001-02-01 15:00:00", 2), ("2001-03-01 23:00:00", 3)],
        ),
        (
            'start_datetime(intervals) < "2001-02-01 09:00:00"',
            [("2001-01-01 06:00:00", 1)],
        ),
        (
            'end_datetime(intervals) == "2001-03-01 15:00:00"',
            [("2001-02-01 15:00:00", 2)],
        ),
    ],
)
def test_datetime_functions(time_series, condition, expected):
    """Datetime functions compare date and time of day"""
    assert (
        selected_maps(time_series.session, f"if({condition}, intervals)", "result")
        == expected
    )


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ('start_time(intervals) == "15:00:00"', [("2001-02-01 15:00:00", 2)]),
        ('start_time(intervals) < "12:00:00"', [("2001-01-01 06:00:00", 1)]),
        ('end_time(intervals) > "20:00:00"', [("2001-03-01 23:00:00", 3)]),
    ],
)
def test_time_functions(time_series, condition, expected):
    """Time functions compare only the time of day"""
    assert (
        selected_maps(time_series.session, f"if({condition}, intervals)", "result")
        == expected
    )


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("start_doy(instants) > 40", [("2001-03-15 00:00:00", 2)]),
        ("start_month(instants) == 1", [("2001-01-10 00:00:00", 1)]),
        ('start_date(instants) > "2001-02-01"', [("2001-03-15 00:00:00", 2)]),
    ],
)
def test_start_functions_on_time_instances(time_series, condition, expected):
    """Start time functions work for maps without end time"""
    assert (
        selected_maps(time_series.session, f"if({condition}, instants)", "result")
        == expected
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "undecided: end_* of a time instance and the calendar functions of "
        "relative time are null, so the condition selects no map and the "
        "result is empty; the classic algebra stops with an error"
    ),
)
@pytest.mark.parametrize(
    ("expression", "map_id"),
    [
        ("if(end_doy(instants) > 40, instants)", "<i1@PERMANENT>"),
        ("if(start_doy(relative) > 0, relative)", "<r1@PERMANENT>"),
    ],
)
def test_unavailable_time_function_is_reported(time_series, expression, map_id):
    """An end time function on time instances and any time function on relative
    time fail with an error message naming the map"""
    tools = Tools(session=time_series.session, overwrite=True)
    with pytest.raises(ToolError) as error:
        tools.t_rast_algebra(expression=f"result = {expression}", basename="result")
    assert "ERROR:" in error.value.stderr
    assert map_id in error.value.stderr
