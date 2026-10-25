"""Tests for the temporal relation of two temporal extents

Extents are plain value objects, so no GRASS session and no temporal database
are needed here.
"""

import copy
import itertools
import pickle
from datetime import datetime

import pytest

from grass.temporal.kinds import KINDS
from grass.temporal.temporal_extent import (
    AbsoluteTimeRow,
    RelativeTemporalExtent,
    TemporalExtent,
)

# The order in which the first matching predicate names the relation. It is the
# order of the chain that temporal_relation() used before it read a table.
CHAIN = (
    "equal",
    "during",
    "contains",
    "overlaps",
    "overlapped",
    "after",
    "before",
    "starts",
    "finishes",
    "started",
    "finished",
    "follows",
    "precedes",
)

# Points, intervals and intervals whose end lies before the start: the
# database accepts the latter, so the relation has to name them as before.
EXTENTS = [(start, end) for start in range(6) for end in [None, *range(6)]]


def chain(a, b):
    """Name the relation as the predicates, asked one after the other, do"""
    for name in CHAIN:
        if getattr(a, name)(b):
            return name
    return None


def test_the_table_names_every_pair_as_the_chain_of_predicates():
    for (start, end), (other_start, other_end) in itertools.product(EXTENTS, EXTENTS):
        a = TemporalExtent(start_time=start, end_time=end)
        b = TemporalExtent(start_time=other_start, end_time=other_end)
        assert a.temporal_relation(b) == chain(a, b), (a.D, b.D)


@pytest.mark.parametrize(
    ("a", "b", "relation"),
    [
        ((5, 7), (5, 7), "equal"),
        ((6, 7), (5, 8), "during"),
        ((5, 8), (6, 7), "contains"),
        ((5, 7), (6, 8), "overlaps"),
        ((6, 8), (5, 7), "overlapped"),
        ((8, 9), (6, 7), "after"),
        ((6, 7), (8, 9), "before"),
        ((5, 6), (5, 7), "starts"),
        ((6, 7), (5, 7), "finishes"),
        ((5, 7), (5, 6), "started"),
        ((5, 7), (6, 7), "finished"),
        ((5, 7), (3, 5), "follows"),
        ((5, 7), (7, 9), "precedes"),
        ((5, None), (5, None), "equal"),
        ((6, None), (5, 8), "during"),
        ((5, 8), (6, None), "contains"),
    ],
)
def test_the_relations_of_the_documentation(a, b, relation):
    first = TemporalExtent(start_time=a[0], end_time=a[1])
    second = TemporalExtent(start_time=b[0], end_time=b[1])

    assert first.temporal_relation(second) == relation


def test_dates_are_compared_like_numbers():
    a = TemporalExtent(start_time=datetime(2001, 1, 1), end_time=datetime(2001, 2, 1))
    b = TemporalExtent(start_time=datetime(2001, 2, 1), end_time=datetime(2001, 3, 1))

    assert a.temporal_relation(b) == "precedes"
    assert b.temporal_relation(a) == "follows"


def test_an_extent_without_a_start_has_no_relation():
    a = TemporalExtent(start_time=None, end_time=None)
    b = TemporalExtent(start_time=1, end_time=2)

    assert a.temporal_relation(b) is None
    assert b.temporal_relation(a) is None


def test_relative_extents_with_different_units_have_no_relation():
    a = RelativeTemporalExtent(start_time=1, end_time=2, unit="days")
    b = RelativeTemporalExtent(start_time=1, end_time=2, unit="years")
    c = RelativeTemporalExtent(start_time=1, end_time=2, unit="days")

    assert a.temporal_relation(b) is None
    assert a.temporal_relation(c) == "equal"


def test_extents_survive_copy_and_pickle():
    extents = [
        TemporalExtent(start_time=1, end_time=2),
        AbsoluteTimeRow(
            KINDS["strds"],
            ident="a@PERMANENT",
            start_time=datetime(2001, 1, 1),
            granularity="1 days",
            map_time="point",
        ),
    ]
    for extent in extents:
        for clone in (
            copy.copy(extent),
            copy.deepcopy(extent),
            pickle.loads(pickle.dumps(extent)),  # noqa: S301
        ):
            assert type(clone) is type(extent)
            assert clone.D == extent.D
