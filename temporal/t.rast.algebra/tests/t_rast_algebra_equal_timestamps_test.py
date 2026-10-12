"""Test datasets with several maps of identical time stamps in t.rast.algebra

Dataset E holds the instants e1..e4 (values 1..4) at day 1 of January 2001,
sinst (100) is a single map at the same instant. The datasets are described
in the algebra fixture in conftest.py.
"""

import pytest

import grass.temporal as tgis


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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "undecided: {+,equal,r} gives one map per related pair (101 to 104); "
        "the classic algebra gives the sum of all related maps (110) at the "
        "time stamp of each"
    ),
)
def test_single_map_with_right_reference(algebra):
    """With the right reference the sum is repeated for each of the four maps"""
    assert algebra.values("tmap(sinst) {+,equal,r} E") == [110, 110, 110, 110]


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
    """if(E > 2, E) gives null where the condition is false, so e1 and e2
    are left out"""
    assert algebra.values("if(E > 2, E)") == [3, 4]


def test_then_and_else_on_maps_with_equal_time(algebra):
    """The then and else maps of equal time are paired the same way"""
    assert algebra.values("if(E > 2, E, E * 10)") == [3, 4, 10, 20]


def test_single_condition_map_is_broadcast(algebra):
    """One condition map applies to every conclusion map of its time"""
    assert algebra.values("if(tmap(sinst) > 50, E, null())") == [1, 2, 3, 4]


def test_condition_on_unequal_numbers_of_equal_maps_fails(algebra):
    """Four condition maps and two conclusion maps of the same time cannot
    be paired"""
    tgis.open_new_stds("E2", "strds", "absolute", "E2", "E2", "mean", overwrite=True)
    tgis.register_maps_in_space_time_dataset(
        "raster", "E2", "e1,e2", start="2001-01-01"
    )
    with pytest.raises(ValueError, match="cannot be paired"):
        algebra.parse("if(E > 2, E2, null())")
