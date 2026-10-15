"""Tests for the options of the relations and operations of the algebra core

The options give the classic algebra its rules (partners in written order,
no deduplication, fold over all partners, stop at the first failure). Their
defaults are the rules of the core, which the other tests of the core pin.

The expected values of the classic rules come from the classic algebra:
the partners are visited as _related_maps() of temporal_algebra.py (line
1369) does, once per relation name in the written order of the expression
(_check_topology(), line 1530, keeps order and repetitions); the fold and
the stop at the first partner that does not combine are
set_temporal_extent_list() (line 1253).
"""

import pytest

from grass.temporal.algebra.relations import Relation, inverse, related, relation
from grass.temporal.algebra.series import Space


def partners(left, text, other, **options):
    return related(left.slots, relation(text), other.slots, **options)


@pytest.fixture
def around(make_series):
    """One long map and its parts: x1 [1, 2] starts with it, x2 and x3 lie inside"""
    return make_series("l", (1, 10)), make_series("x", (1, 2), (2, 3), (3, 4))


@pytest.fixture
def neighbours(make_series):
    """The map [3, 4] follows x1 [2, 3] and precedes x2 [4, 5]"""
    return make_series("l", (3, 4)), make_series("x", (2, 3), (4, 5))


def test_relation_remembers_the_written_names():
    assert relation("precedes|follows|precedes").written == (
        "precedes",
        "follows",
        "precedes",
    )


def test_written_names_do_not_change_the_identity_of_a_relation():
    assert relation("follows|precedes") == relation("precedes|follows")
    assert relation("follows|precedes").written != relation("precedes|follows").written


def test_written_names_must_be_the_temporal_names():
    with pytest.raises(ValueError, match="written names"):
        Relation(frozenset({"equal"}), written=("during",))


def test_written_names_survive_or_and_inverse():
    both = relation("precedes|follows") | relation("equal")
    assert both.written == ("precedes", "follows", "equal")
    assert inverse(relation("precedes|equal")).written == ("follows", "equal")


def test_partners_are_sorted_by_default(neighbours):
    left, other = neighbours
    assert partners(left, "precedes|follows", other) == [[0, 1]]
    assert partners(left, "follows|precedes", other) == [[0, 1]]


def test_written_order_lists_the_partners_name_by_name(neighbours):
    left, other = neighbours
    assert partners(left, "precedes|follows", other, order="written") == [[1, 0]]
    assert partners(left, "follows|precedes", other, order="written") == [[0, 1]]


def test_written_order_without_written_names_is_sorted_by_name(neighbours):
    left, other = neighbours
    # The constants such as equal or the relations built from sets carry no
    # written order; their names are visited in alphabetical order.
    both = Relation(frozenset({"precedes", "follows"}))
    assert related(left.slots, both, other.slots, order="written") == [[0, 1]]


def test_partners_are_unique_by_default(around):
    left, other = around
    # The builder files x1 under started and under contains, as contains
    # includes started.
    assert partners(left, "contains|started", other) == [[0, 1, 2]]


def test_without_unique_a_partner_is_listed_for_every_name(around):
    left, other = around
    assert partners(left, "contains|started", other, order="written", unique=False) == [
        [0, 1, 2, 0]
    ]
    assert partners(left, "started|contains", other, order="written", unique=False) == [
        [0, 0, 1, 2]
    ]


def test_a_name_written_twice_lists_its_partners_twice(around):
    left, other = around
    assert partners(left, "started|started", other, order="written", unique=False) == [
        [0, 0]
    ]
    assert partners(left, "started|started", other, order="written") == [[0]]


def test_unique_keeps_the_first_position(around):
    left, other = around
    assert partners(left, "contains|started", other, order="written") == [[0, 1, 2]]
    assert partners(left, "started|contains", other, order="written") == [[0, 1, 2]]


def test_sorted_order_without_unique_keeps_the_repetitions(around):
    left, other = around
    assert partners(left, "contains|started", other, unique=False) == [[0, 0, 1, 2]]


def test_written_order_with_spatial_names(make_series):
    box = Space(10, 0, 10, 0, 0, 0)
    left = make_series("l", (3, 4), space=box)
    other = make_series("x", (2, 3), (4, 5), space=box)
    both = relation("precedes|follows|equivalent")
    assert related(left.slots, both, other.slots, order="written") == [[1, 0]]


def test_unknown_order(neighbours):
    left, other = neighbours
    with pytest.raises(ValueError, match="order must be one of sorted, written"):
        partners(left, "precedes", other, order="reverse")
