"""Test temporal functions in t.rast.algebra conditions

The datasets are described in the time_series fixture in conftest.py.
"""

import pytest

from grass.temporal.testing.readback import inventory, message
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


# The messages of the core for expressions it refuses, as the tool prints them.
DATE_AND_NUMBER = (
    "Dates and times, such as those of start_date() or start_time(), cannot be "
    "compared with the number 12; compare them with a date or time in quotes, "
    'such as "2001-01-03" or "12:00:00"'
)
DATE_ALONE = (
    "'2001-03-01' is a date without a time of day, but start_time() and "
    "end_time() give only the time of day; compare dates with start_date() or "
    "end_date(), or a date and time with start_datetime() or end_datetime()"
)
TWO_KINDS = (
    "Numbers, such as those of start_doy() or td(), cannot be compared with "
    "times of day, such as those of start_time(); compare time functions that "
    "give the same kind of value, such as start_date() with end_date()"
)
TD_OF_AN_INSTANCE = (
    "td() requires a time interval, but map <i1@PERMANENT> is a time instance"
)
# The first map of intervals starts on 2001-01-01 at 06:00.
DATE_ARITHMETIC = (
    "-() computes with numbers, not with a date (2001-01-01); use the numbers "
    "of time functions such as start_doy() or td()"
)
MAP_AND_DATE = (
    ">() cannot combine maps with a date (2001-01-01): maps hold numbers; "
    "compare time functions with each other or with a date in quotes, or use "
    "the numbers of time functions such as start_doy() or td()"
)
DATE_AS_CONDITION = "if() needs a number as condition, not a date (2001-01-01)"
UNEQUAL_BRANCHES = (
    "where() needs maps with equal time stamps; they differ at map 1: "
    "2001-01-01 06:00:00 .. 2001-02-01 06:00:00 and 2001-01-10 00:00:00. Select "
    "the maps with matching time stamps first, for example B : A"
)


@pytest.mark.parametrize(
    ("expression", "text"),
    [
        ("if(start_time(intervals) > 12, intervals)", DATE_AND_NUMBER),
        ('if(start_time(intervals) >= "2001-03-01", intervals)', DATE_ALONE),
        ("if(start_doy(intervals) > start_time(intervals), intervals)", TWO_KINDS),
        ("if(td(instants) > 0, instants)", TD_OF_AN_INSTANCE),
        ("if(intervals > 1, intervals, instants)", UNEQUAL_BRANCHES),
        (
            "if(start_date(intervals) - end_date(intervals) > 0, intervals)",
            DATE_ARITHMETIC,
        ),
        ("intervals > start_date(intervals)", MAP_AND_DATE),
        ("if(start_date(intervals), intervals)", DATE_AS_CONDITION),
    ],
    ids=[
        "date and number",
        "date alone",
        "two kinds",
        "td of an instance",
        "unequal branches",
        "date arithmetic",
        "map and date",
        "date as condition",
    ],
)
def test_the_tool_reports_the_error_and_writes_nothing(time_series, expression, text):
    """The tool stops with the message of the core, without a traceback,
    before it writes a map or a dataset"""
    tools = Tools(session=time_series.session, consistent_return_value=True)
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_rast_algebra(expression=f"refused = {expression}", basename="refused")
    assert text in message(error.value)
    assert "Traceback" not in error.value.stderr
    assert inventory(tools) == before


def duration_arithmetic(algebra, expression):
    """Return (start day, end day, value) of each map of R = <expression>"""
    algebra.remove("R")
    return algebra.triples(expression)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        # The maps of A and N last one day, so td() of any expression over
        # them is 1 and not the value of the expression.
        ("N - td(A * 2)", [(1, 2, 10), (2, 3, 11), (3, 4, 12), (4, 5, 13)]),
        ("N - td(A + N)", [(1, 2, 10), (2, 3, 11), (3, 4, 12), (4, 5, 13)]),
        ("D - td(A[1])", [(3, 4, 7)]),
        # The duration of the maps of B is two days.
        ("B - td(B * 2)", [(1, 3, 3), (3, 5, 4)]),
    ],
)
def test_duration_of_an_expression_in_arithmetic(algebra, expression, expected):
    """td() of a computed expression is the duration of its maps on the right
    of an operator, as td() of a dataset is"""
    assert duration_arithmetic(algebra, expression) == expected


def outcome(algebra, expression):
    """Return (result dataset exists, (start day, end day, value) of its
    maps) for R = <expression>"""
    algebra.remove("R")
    algebra.parse(expression)
    if not algebra.exists():
        return False, None
    return True, [(row.start.day, row.end.day, row.min) for row in algebra.maps("R")]


@pytest.mark.parametrize(
    "expression",
    [
        # A and B have no map that is equal in time.
        "tsnap(A {:,equal} B)",
        'tshift(A {:,equal} B, "1 day")',
        "tshift(A {:,equal} B, 1)",
        "tsnap(tsnap(A {:,equal} B))",
        "A + tsnap(A {:,equal} B)",
        'A + tshift(A {:,equal} B, "1 day")',
        "tsnap(A {:,equal} B) {:,equal} A",
    ],
)
def test_tsnap_and_tshift_of_no_maps_give_an_empty_result(algebra, expression):
    """Without maps to snap or shift the result is an empty dataset, like any
    other empty result, and the enclosing expression goes on with no maps"""
    assert outcome(algebra, expression) == (True, [])


def test_merge_with_tsnap_of_no_maps_keeps_the_other_maps(algebra):
    """An empty list from tsnap() adds nothing to merge()"""
    assert outcome(algebra, "merge(A, tsnap(A {:,equal} B))") == (
        True,
        [(1, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 4)],
    )


def test_round_of_the_paper_is_no_function(time_series):
    """Table A2 of the paper lists round() among the spatial functions, but
    the algebra has no such function and says so without a traceback"""
    tools = Tools(session=time_series.session, consistent_return_value=True)
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_rast_algebra(expression="R = round(intervals)", basename="r")
    assert "Unknown function round()" in message(error.value)
    assert "Traceback" not in error.value.stderr
    assert inventory(tools) == before
