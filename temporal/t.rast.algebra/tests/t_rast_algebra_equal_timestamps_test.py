"""Test datasets with several maps of identical time stamps in t.rast.algebra

Dataset E holds the instants e1..e4 (values 1..4) at day 1 of January 2001,
sinst (100) is a single map at the same instant. The datasets are described
in the algebra fixture in conftest.py.
"""

import pytest


def test_complex_operator_aggregates_all_equal_maps(algebra):
    """E {+,equal,l} E sums all four maps into every result: e<i> + (1 + 2 + 3 + 4)
    where the equal relation includes the map itself"""
    assert algebra.values("E {+,equal,l} E") == [11, 12, 13, 14]


@pytest.mark.xfail(
    strict=True,
    reason="H1: simple + aggregates only the last of several maps with equal time",
)
def test_simple_operator_equals_complex_operator(algebra):
    """The manual: E + E is the same as E {+,equal,l} E"""
    assert algebra.values("E + E") == [11, 12, 13, 14]


@pytest.mark.xfail(
    strict=True,
    reason="H1: simple + aggregates only the last of several maps with equal time",
)
def test_single_map_with_simple_operator(algebra):
    """tmap(sinst) + E sums the single map with all four maps: 100 + 10"""
    assert algebra.values("tmap(sinst) + E") == [110]


def test_single_map_with_complex_operator(algebra):
    """With the explicit operator the single map is aggregated correctly,
    with the left reference to one map and with the right reference to four"""
    assert algebra.values("tmap(sinst) {+,equal,l} E") == [110]
    assert algebra.values("tmap(sinst) {+,equal,r} E") == [110, 110, 110, 110]


def test_arithmetic_with_number_and_select(algebra):
    """Operations that need no relation keep the four maps"""
    assert algebra.values("E * 2") == [2, 4, 6, 8]
    assert algebra.values("E : E") == [1, 2, 3, 4]
    assert algebra.values("E {#,equal} E") == [4, 4, 4, 4]


def test_neighbour_of_maps_with_equal_time(algebra):
    """The temporal neighbours follow the order in the dataset"""
    assert algebra.values("E[1]") == [2, 3, 4]


@pytest.mark.xfail(
    strict=True,
    reason="new: if/then with several maps of equal time stamps pairs every "
    "condition map with every conclusion map",
)
def test_condition_on_maps_with_equal_time(algebra):
    """if(E > 2, E, null()) keeps e3 and e4"""
    assert algebra.values("if(E > 2, E, null())") == [3, 4]
