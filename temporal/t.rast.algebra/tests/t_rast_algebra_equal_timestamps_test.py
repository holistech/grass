"""Test datasets with several maps of identical time stamps in t.rast.algebra

Dataset E holds the instants e1..e4 (values 1..4) at day 1 of January 2001,
sinst (100) is a single map at the same instant. The datasets are described
in the algebra fixture in conftest.py. The argument classic of a test runs
the core (False) or the classic algebra (True) where their results differ.
"""

import pytest

import grass.temporal as tgis
from grass.exceptions import FatalError
from grass.exceptions import FatalError as TemporalAlgebraFatalError
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.differential import RUNNERS, outcome
from grass.tools import Tools


def test_complex_operator_aggregates_all_equal_maps(algebra):
    """E {+,equal,l} E sums all four maps into every result: e<i> + (1 + 2 + 3 + 4)
    where the equal relation includes the map itself"""
    assert algebra.values("E {+,equal,l} E") == [11, 12, 13, 14]


def test_simple_operator_equals_complex_operator(algebra):
    """The manual: E + E is the same as E {+,equal,l} E"""
    assert algebra.values("E + E") == [11, 12, 13, 14]


def test_single_map_with_simple_operator(algebra):
    """tmap(sinst) + E sums the single map with all four maps: 100 + 10"""
    assert algebra.values("tmap(sinst) + E") == [110]


def test_single_map_with_complex_operator(algebra):
    """With the explicit operator the single map is aggregated correctly,
    with the left reference to one map"""
    assert algebra.values("tmap(sinst) {+,equal,l} E") == [110]


@pytest.mark.fixed_algebra
@pytest.mark.parametrize(
    ("classic", "values"),
    [(False, [101, 102, 103, 104]), (True, [110, 110, 110, 110])],
)
def test_single_map_with_right_reference(algebra, classic, values):
    """A right reference gives one map per related pair, with the value of
    that pair; the classic algebra gives each of the four maps the sum of
    all"""
    assert algebra.values("tmap(sinst) {+,equal,r} E", classic=classic) == values


def test_arithmetic_with_number_and_select(algebra):
    """Operations that need no relation keep the four maps"""
    assert algebra.values("E * 2") == [2, 4, 6, 8]
    assert algebra.values("E : E") == [1, 2, 3, 4]
    assert algebra.values("E {#,equal} E") == [4, 4, 4, 4]


def test_neighbour_of_maps_with_equal_time(algebra):
    """The temporal neighbours follow the order in the dataset"""
    assert algebra.values("E[1]") == [2, 3, 4]


def test_condition_on_maps_with_equal_time(algebra):
    """if(E > 2, E, null()) keeps e3 and e4: n condition maps of equal time
    are paired with n conclusion maps of that time in dataset order"""
    assert algebra.values("if(E > 2, E, null())") == [3, 4]


def test_condition_without_else_on_maps_with_equal_time(algebra):
    """if(E > 2, E) gives one map per condition map, 0 where the condition is
    false"""
    assert algebra.values("if(E > 2, E)") == [0, 0, 3, 4]


def test_then_and_else_on_maps_with_equal_time(algebra):
    """The then and else maps of equal time are paired the same way"""
    assert algebra.values("if(E > 2, E, E * 10)") == [3, 4, 10, 20]


def test_single_condition_map_is_broadcast(algebra):
    """One condition map applies to every conclusion map of its time"""
    assert algebra.values("if(tmap(sinst) > 50, E, null())") == [1, 2, 3, 4]


@pytest.mark.fixed_algebra
@pytest.mark.parametrize(
    ("classic", "errors", "message"),
    [
        (False, ValueError, "cannot be paired"),
        (True, (FatalError, TemporalAlgebraFatalError), "maps of equal time stamps"),
    ],
)
def test_condition_on_unequal_numbers_of_equal_maps_fails(
    algebra, classic, errors, message
):
    """Four condition maps and two conclusion maps of the same time cannot
    be paired"""
    tgis.open_new_stds("E2", "strds", "absolute", "E2", "E2", "mean", overwrite=True)
    tgis.register_maps_in_space_time_dataset(
        "raster", "E2", "e1,e2", start="2001-01-01"
    )
    with pytest.raises(errors, match=message):
        algebra.parse("if(E > 2, E2, null())", classic=classic)


@pytest.mark.fixed_algebra
def test_conditions_related_by_two_names_pair_with_maps_of_equal_time(algebra):
    """Two condition maps of one time are paired one to one with two
    conclusion maps of another time, also where each condition map relates
    to each conclusion map by two of the written names: ec1 and ec2 [1,2]
    are during and start ea1 and ea2 [1,3]. A related map counts once, so
    the classic algebra, the classic profile and the core agree. td() is
    one day, so ea1 and ea2 are kept; ea3 [3,4] has no related condition,
    which a relation beyond equal reads as false, so it gets the else 0."""
    tools = Tools(session=algebra.session)
    create_stds(
        tools,
        "strds",
        "EC",
        [
            MapSpec("ec1", 1, algebra.day(1), algebra.day(2)),
            MapSpec("ec2", 2, algebra.day(1), algebra.day(2)),
        ],
        overwrite=True,
    )
    create_stds(
        tools,
        "strds",
        "EA",
        [
            MapSpec("ea1", 10, algebra.day(1), algebra.day(3)),
            MapSpec("ea2", 20, algebra.day(1), algebra.day(3)),
            MapSpec("ea3", 30, algebra.day(3), algebra.day(4)),
        ],
        overwrite=True,
    )
    expected = [
        ["N_0", "2001-01-01T00:00:00", "2001-01-03T00:00:00", 10.0, 10.0],
        ["N_1", "2001-01-01T00:00:00", "2001-01-03T00:00:00", 20.0, 20.0],
        ["N_2", "2001-01-03T00:00:00", "2001-01-04T00:00:00", 0.0, 0.0],
    ]
    for runner, basename in (("reference", "fa"), ("classic", "fc"), ("core", "fk")):
        result = outcome(
            "raster",
            "if({during|starts}, td(EC) > 0, EA, 0)",
            RUNNERS[runner],
            basename=basename,
        )
        assert result.get("maps") == expected, (runner, result)
