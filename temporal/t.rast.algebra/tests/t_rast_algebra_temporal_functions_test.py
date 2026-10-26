"""Test temporal functions in t.rast.algebra conditions

The datasets are described in the time_series fixture in conftest.py.
"""

import pytest

from grass.exceptions import FatalError
from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE
from grass.temporal.testing.reference import run_reference
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


def duration_arithmetic(algebra, monkeypatch, expression, implementation):
    """Return (start day, end day, value) of "R = <expression>" computed by the
    core or by the earlier implementation, whatever GRASS_TEMPORAL_ALGEBRA says"""
    algebra.remove("R")
    if implementation == "core":
        monkeypatch.delenv(ALGEBRA_VARIABLE, raising=False)
        return algebra.triples(expression)
    run_reference("raster", f"R = {expression}", basename="r", overwrite=True, run=True)
    return [(row.start.day, row.end.day, row.min) for row in algebra.maps("R")]


@pytest.mark.fixed_algebra
@pytest.mark.parametrize("implementation", ["core", "reference"])
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
def test_duration_of_an_expression_in_arithmetic(
    algebra, monkeypatch, implementation, expression, expected
):
    """td() of a computed expression is the duration of its maps on the right
    of an operator, as td() of a dataset is"""
    assert (
        duration_arithmetic(algebra, monkeypatch, expression, implementation)
        == expected
    )


def outcome(algebra, monkeypatch, expression, implementation):
    """Return (result dataset exists, (start day, end day, value) of its maps)
    for "R = <expression>" computed by the core or by the earlier
    implementation, whatever GRASS_TEMPORAL_ALGEBRA says"""
    algebra.remove("R")
    if implementation == "core":
        monkeypatch.delenv(ALGEBRA_VARIABLE, raising=False)
        algebra.parse(expression)
    else:
        run_reference(
            "raster", f"R = {expression}", basename="r", overwrite=True, run=True
        )
    if not algebra.exists():
        return False, None
    return True, [(row.start.day, row.end.day, row.min) for row in algebra.maps("R")]


@pytest.mark.fixed_algebra
@pytest.mark.parametrize("implementation", ["core", "reference"])
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
def test_tsnap_and_tshift_of_no_maps_give_an_empty_result(
    algebra, monkeypatch, implementation, expression
):
    """Without maps to snap or shift the result is an empty dataset, like any
    other empty result, and the enclosing expression goes on with no maps"""
    assert outcome(algebra, monkeypatch, expression, implementation) == (True, [])


@pytest.mark.fixed_algebra
@pytest.mark.parametrize("implementation", ["core", "reference"])
def test_merge_with_tsnap_of_no_maps_keeps_the_other_maps(
    algebra, monkeypatch, implementation
):
    """An empty list from tsnap() adds nothing to merge()"""
    assert outcome(
        algebra, monkeypatch, "merge(A, tsnap(A {:,equal} B))", implementation
    ) == (True, [(1, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 4)])


@pytest.mark.fixed_algebra
@pytest.mark.parametrize(
    "expression",
    [
        # The unit is case sensitive and has no abbreviation.
        'tshift(A, "1 DAY")',
        'tshift(A, "1 d")',
        'tshift(A, "1 fortnight")',
        # Relative time is shifted by a number of its unit only.
        'tshift(RT, "1 month")',
        'tshift(RT, "1 day")',
    ],
)
def test_tshift_with_a_refused_increment_is_a_syntax_error(
    algebra, monkeypatch, expression
):
    """An increment that the library refuses is reported as the error of
    a number without unit on absolute time, not as an absent result.

    Checked on the earlier implementation only: the core raises a ValueError
    with its own message for the same expressions.
    """
    algebra.remove("R")
    with pytest.raises(SyntaxError, match="tshift"):
        run_reference(
            "raster", f"R = {expression}", basename="r", overwrite=True, run=True
        )
    assert not algebra.exists()


@pytest.mark.fixed_algebra
def test_tshift_with_a_refused_increment_inside_an_expression(algebra):
    """The error is reported to the caller and not as the type of the input
    of the enclosing operator"""
    algebra.remove("R")
    with pytest.raises(SyntaxError, match="tshift"):
        run_reference(
            "raster",
            'R = A + tshift(A, "1 DAY")',
            basename="r",
            overwrite=True,
            run=True,
        )


@pytest.mark.fixed_algebra
@pytest.mark.parametrize(
    "expression",
    [
        # End functions of time instants and any function of relative time
        "end_month(I, 0)",
        "end_month(E, 0)",
        "start_month(RT, 0)",
        "A + end_month(I, 0)",
        "A + start_month(RT, 1)",
    ],
)
def test_time_constant_with_offset_needs_absolute_time(algebra, expression):
    """A temporal function of a neighbour map is refused where the map has no
    such value, like the same function in a condition. It was written as None
    into the r.mapcalc expression, which failed when the maps were computed.

    Checked on the earlier implementation only: the core raises a ValueError
    with its own message for the same expressions.
    """
    algebra.remove("R")
    with pytest.raises(FatalError, match="requires absolute time"):
        run_reference(
            "raster", f"R = {expression}", basename="r", overwrite=True, run=True
        )
    assert not algebra.exists()


@pytest.mark.fixed_algebra
@pytest.mark.parametrize("condition", ["end_month(I) == 1", "start_month(RT) == 1"])
def test_time_function_in_a_condition_needs_absolute_time(algebra, condition):
    """The condition form, which the offset form is measured against"""
    stds = condition.split("(")[1].split(")")[0]
    algebra.remove("R")
    with pytest.raises(FatalError, match="requires absolute time"):
        run_reference(
            "raster",
            f"R = if({condition}, {stds})",
            basename="r",
            overwrite=True,
            run=True,
        )
