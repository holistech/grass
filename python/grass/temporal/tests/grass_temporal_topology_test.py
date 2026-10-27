"""Tests for the temporal topology builder, the map list sorting keys and the
SQL condition of a temporal relation

The relations follow Allen and Ferguson 1994, as cited by
grass.temporal.temporal_extent: an interval starting earlier and ending inside
a later one "overlaps" it, and the later one is "overlapped" by it.

Maps are built in memory only, so no GRASS session and no temporal database
are needed here.
"""

from datetime import datetime

import pytest

from grass.temporal.abstract_dataset import (
    AbstractDatasetComparisonKeyEndTime,
    AbstractDatasetComparisonKeyStartTime,
)
from grass.temporal.space_time_datasets import RasterDataset
from grass.temporal.topology import (
    SpatioTemporalTopologyBuilder,
    create_temporal_relation_sql_where_statement,
)


def maps_from(intervals):
    """Return maps for a list of (identifier, start, end) tuples"""
    maps = []
    for ident, start, end in intervals:
        map_ = RasterDataset(ident=ident)
        map_.set_absolute_time(start, end)
        maps.append(map_)
    return maps


@pytest.fixture
def consecutive_maps():
    """Five maps covering consecutive months without gaps"""
    return maps_from(
        [
            ("d_%i@a" % (i + 1), datetime(2001, i + 1, 1), datetime(2001, i + 2, 1))
            for i in range(5)
        ]
    )


@pytest.fixture
def overlapping_maps():
    """Five maps with overlapping, contained and disjoint intervals"""
    return maps_from(
        [
            ("d_1@b", datetime(2001, 1, 14), datetime(2001, 3, 14)),
            ("d_2@b", datetime(2001, 2, 1), datetime(2001, 4, 1)),
            ("d_3@b", datetime(2001, 2, 14), datetime(2001, 4, 30)),
            ("d_4@b", datetime(2001, 4, 2), datetime(2001, 4, 30)),
            ("d_5@b", datetime(2001, 5, 1), datetime(2001, 5, 14)),
        ]
    )


def related_ids(maps, relation):
    """Return the identifiers related to each map by the given relation"""
    return [
        [related.get_id() for related in (getattr(map_, "get_" + relation)() or [])]
        for map_ in maps
    ]


def test_builder_iterates_in_input_order(consecutive_maps) -> None:
    builder = SpatioTemporalTopologyBuilder()
    builder.build(consecutive_maps)

    assert [map_.get_id() for map_ in builder] == [
        map_.get_id() for map_ in consecutive_maps
    ]


def test_consecutive_maps_only_follow_and_precede(consecutive_maps) -> None:
    """Intervals that touch but do not overlap only follow and precede"""
    builder = SpatioTemporalTopologyBuilder()
    builder.build(consecutive_maps)

    assert related_ids(consecutive_maps, "precedes") == [
        ["d_2@a"],
        ["d_3@a"],
        ["d_4@a"],
        ["d_5@a"],
        [],
    ]
    assert related_ids(consecutive_maps, "follows") == [
        [],
        ["d_1@a"],
        ["d_2@a"],
        ["d_3@a"],
        ["d_4@a"],
    ]
    assert related_ids(consecutive_maps, "overlaps") == [[]] * 5


def test_overlaps_points_from_the_earlier_to_the_later_interval(
    overlapping_maps,
) -> None:
    """d_1@b starts before d_2@b and d_3@b and ends inside them, so it overlaps them"""
    builder = SpatioTemporalTopologyBuilder()
    builder.build(overlapping_maps)

    assert related_ids(overlapping_maps, "overlaps") == [
        ["d_2@b", "d_3@b"],
        ["d_3@b"],
        [],
        [],
        [],
    ]
    assert related_ids(overlapping_maps, "overlapped") == [
        [],
        ["d_1@b"],
        ["d_1@b", "d_2@b"],
        [],
        [],
    ]


def test_contains_and_during_are_inverse(overlapping_maps) -> None:
    """d_4@b lies inside d_3@b, so d_3@b contains it and it is during d_3@b"""
    builder = SpatioTemporalTopologyBuilder()
    builder.build(overlapping_maps)

    assert related_ids(overlapping_maps, "contains") == [[], [], ["d_4@b"], [], []]
    assert related_ids(overlapping_maps, "during") == [[], [], [], ["d_3@b"], []]


def test_topology_between_two_map_lists(consecutive_maps, overlapping_maps) -> None:
    """Building with two lists relates the maps of one list to the other"""
    builder = SpatioTemporalTopologyBuilder()
    builder.build(consecutive_maps, overlapping_maps)

    # d_4@a covers April, so it starts inside d_3@b and ends after it.
    assert related_ids(consecutive_maps, "overlapped")[3] == ["d_3@b"]
    assert related_ids(consecutive_maps, "follows")[3] == ["d_2@b"]
    assert related_ids(consecutive_maps, "precedes")[3] == ["d_5@b"]
    assert related_ids(consecutive_maps, "contains")[3] == ["d_4@b"]
    # d_3@a covers March, which lies inside both d_2@b and d_3@b.
    assert related_ids(consecutive_maps, "during")[2] == ["d_2@b", "d_3@b"]


@pytest.fixture
def unsorted_maps():
    """Three maps whose order in the list is not their temporal order"""
    return maps_from(
        [
            ("d_1@a", datetime(2001, 2, 1), datetime(2001, 3, 1)),
            ("d_2@a", datetime(2001, 1, 1), datetime(2001, 2, 1)),
            ("d_3@a", datetime(2001, 3, 1), datetime(2001, 4, 1)),
        ]
    )


@pytest.mark.parametrize(
    "key",
    [AbstractDatasetComparisonKeyStartTime, AbstractDatasetComparisonKeyEndTime],
)
def test_map_list_sorting(unsorted_maps, key) -> None:
    """The maps do not overlap, so start and end time sort them the same way"""
    assert [map_.get_id() for map_ in sorted(unsorted_maps, key=key)] == [
        "d_2@a",
        "d_1@a",
        "d_3@a",
    ]


# The cases below were the examples in the docstrings of topology, which now
# keep one example each.


def year_span(first, last):
    """Return the interval from 1 January of one year to 1 January of another"""
    return (datetime(first, 1, 1), datetime(last, 1, 1))


def second_span(first, last):
    """Return the interval between two seconds of 1 January 2000"""
    return (datetime(2000, 1, 1, 0, 0, first), datetime(2000, 1, 1, 0, 0, last))


def maps_of(prefix, spans, unit=None):
    """Return the maps <prefix><number>@B, in relative time if a unit is given"""
    maps = []
    for number, (start, end) in enumerate(spans):
        map_ = RasterDataset(f"{prefix}{number}@B")
        if unit:
            map_.set_relative_time(start, end, unit)
        else:
            map_.set_absolute_time(start, end)
        maps.append(map_)
    return maps


def first_related(maps):
    """List the extent of each map, followed by its relations except NEXT and
    PREV in sorted order, each with the extent of the first related map"""
    listing = []
    for map_ in maps:
        listing.append(map_.get_temporal_extent_as_tuple())
        relations = map_.get_temporal_relations()
        listing.extend(
            (name, relations[name][0].get_temporal_extent_as_tuple())
            for name in sorted(relations)
            if name not in {"NEXT", "PREV"}
        )
    return listing


def test_two_lists_with_equal_intervals_relate_map_by_map() -> None:
    first = maps_of("a", [(i, i + 1) for i in range(4)], "months")
    second = maps_of("b", [(i, i + 1) for i in range(4)], "months")
    SpatioTemporalTopologyBuilder().build(first, second, None)

    def equal_names(maps):
        return [
            (map_.get_name(), map_.get_equal()[0].get_name())
            for map_ in maps
            if map_.get_equal()
        ]

    assert equal_names(first) == [
        ("a0", "b0"),
        ("a1", "b1"),
        ("a2", "b2"),
        ("a3", "b3"),
    ]
    assert equal_names(second) == [
        ("b0", "a0"),
        ("b1", "a1"),
        ("b2", "a2"),
        ("b3", "a3"),
    ]


@pytest.mark.parametrize(
    ("spans", "other_spans", "unit", "expected"),
    [
        (
            [(i, i + 1) for i in range(4)],
            [(i + 1, i + 2) for i in range(4)],
            "months",
            [
                (0, 1),
                ("PRECEDES", (1, 2)),
                (1, 2),
                ("EQUAL", (1, 2)),
                ("PRECEDES", (2, 3)),
                (2, 3),
                ("EQUAL", (2, 3)),
                ("FOLLOWS", (1, 2)),
                ("PRECEDES", (3, 4)),
                (3, 4),
                ("EQUAL", (3, 4)),
                ("FOLLOWS", (2, 3)),
                ("PRECEDES", (4, 5)),
            ],
        ),
        (
            [year_span(2000 + i, 2001 + i) for i in range(4)],
            [year_span(2001 + i, 2002 + i) for i in range(4)],
            None,
            [
                year_span(2000, 2001),
                ("PRECEDES", year_span(2001, 2002)),
                year_span(2001, 2002),
                ("EQUAL", year_span(2001, 2002)),
                ("PRECEDES", year_span(2002, 2003)),
                year_span(2002, 2003),
                ("EQUAL", year_span(2002, 2003)),
                ("FOLLOWS", year_span(2001, 2002)),
                ("PRECEDES", year_span(2003, 2004)),
                year_span(2003, 2004),
                ("EQUAL", year_span(2003, 2004)),
                ("FOLLOWS", year_span(2002, 2003)),
                ("PRECEDES", year_span(2004, 2005)),
            ],
        ),
        (
            [year_span(2000 + i, 2001 + i) for i in range(4)],
            [year_span(2000 + i, 2003 + i) for i in range(4)],
            None,
            [
                year_span(2000, 2001),
                ("DURING", year_span(2000, 2003)),
                ("PRECEDES", year_span(2001, 2004)),
                ("STARTS", year_span(2000, 2003)),
                year_span(2001, 2002),
                ("DURING", year_span(2000, 2003)),
                ("PRECEDES", year_span(2002, 2005)),
                ("STARTS", year_span(2001, 2004)),
                year_span(2002, 2003),
                ("DURING", year_span(2000, 2003)),
                ("FINISHES", year_span(2000, 2003)),
                ("PRECEDES", year_span(2003, 2006)),
                ("STARTS", year_span(2002, 2005)),
                year_span(2003, 2004),
                ("DURING", year_span(2001, 2004)),
                ("FINISHES", year_span(2001, 2004)),
                ("FOLLOWS", year_span(2000, 2003)),
                ("STARTS", year_span(2003, 2006)),
            ],
        ),
        (
            [year_span(2000 + i, 2002 + i) for i in range(4)],
            [year_span(2000 + i, 2003 + i) for i in range(4)],
            None,
            [
                year_span(2000, 2002),
                ("DURING", year_span(2000, 2003)),
                ("OVERLAPS", year_span(2001, 2004)),
                ("PRECEDES", year_span(2002, 2005)),
                ("STARTS", year_span(2000, 2003)),
                year_span(2001, 2003),
                ("DURING", year_span(2000, 2003)),
                ("FINISHES", year_span(2000, 2003)),
                ("OVERLAPS", year_span(2002, 2005)),
                ("PRECEDES", year_span(2003, 2006)),
                ("STARTS", year_span(2001, 2004)),
                year_span(2002, 2004),
                ("DURING", year_span(2001, 2004)),
                ("FINISHES", year_span(2001, 2004)),
                ("OVERLAPPED", year_span(2000, 2003)),
                ("OVERLAPS", year_span(2003, 2006)),
                ("STARTS", year_span(2002, 2005)),
                year_span(2003, 2005),
                ("DURING", year_span(2002, 2005)),
                ("FINISHES", year_span(2002, 2005)),
                ("FOLLOWS", year_span(2000, 2003)),
                ("OVERLAPPED", year_span(2001, 2004)),
                ("STARTS", year_span(2003, 2006)),
            ],
        ),
        (
            [second_span(i, i + 2) for i in range(4)],
            [second_span(i + 1, i + 3) for i in range(4)],
            None,
            [
                second_span(0, 2),
                ("OVERLAPS", second_span(1, 3)),
                ("PRECEDES", second_span(2, 4)),
                second_span(1, 3),
                ("EQUAL", second_span(1, 3)),
                ("OVERLAPS", second_span(2, 4)),
                ("PRECEDES", second_span(3, 5)),
                second_span(2, 4),
                ("EQUAL", second_span(2, 4)),
                ("OVERLAPPED", second_span(1, 3)),
                ("OVERLAPS", second_span(3, 5)),
                ("PRECEDES", second_span(4, 6)),
                second_span(3, 5),
                ("EQUAL", second_span(3, 5)),
                ("FOLLOWS", second_span(1, 3)),
                ("OVERLAPPED", second_span(2, 4)),
                ("OVERLAPS", second_span(4, 6)),
            ],
        ),
        (
            [second_span(i, i + 2) for i in range(4)],
            None,
            None,
            [
                second_span(0, 2),
                ("OVERLAPS", second_span(1, 3)),
                ("PRECEDES", second_span(2, 4)),
                second_span(1, 3),
                ("OVERLAPPED", second_span(0, 2)),
                ("OVERLAPS", second_span(2, 4)),
                ("PRECEDES", second_span(3, 5)),
                second_span(2, 4),
                ("FOLLOWS", second_span(0, 2)),
                ("OVERLAPPED", second_span(1, 3)),
                ("OVERLAPS", second_span(3, 5)),
                second_span(3, 5),
                ("FOLLOWS", second_span(1, 3)),
                ("OVERLAPPED", second_span(2, 4)),
            ],
        ),
    ],
)
def test_relations_of_the_first_list(spans, other_spans, unit, expected) -> None:
    maps = maps_of("a", spans, unit)
    others = None if other_spans is None else maps_of("b", other_spans, unit)
    SpatioTemporalTopologyBuilder().build(maps, others, None)

    assert first_related(maps) == expected


DATES = (datetime(2001, 1, 1, 12, 30), datetime(2001, 3, 31, 14, 30))


@pytest.mark.parametrize(
    ("start", "end", "selection", "expected"),
    [
        (1, 2, {"use_start": False}, None),
        (1, 2, {}, "((start_time >= 1 and start_time < 2) )"),
        (
            1,
            2,
            {"use_start": False, "use_during": True},
            "(((start_time > 1 and end_time < 2) OR (start_time >= 1 and end_time < 2) OR (start_time > 1 and end_time <= 2)))",
        ),
        (
            1,
            2,
            {"use_start": False, "use_overlap": True},
            "(((start_time < 1 and end_time > 1 and end_time < 2) OR (start_time < 2 and start_time > 1 and end_time > 2)))",
        ),
        (
            1,
            2,
            {"use_start": False, "use_contain": True},
            "(((start_time < 1 and end_time > 2) OR (start_time <= 1 and end_time > 2) OR (start_time < 1 and end_time >= 2)))",
        ),
        (
            1,
            2,
            {"use_start": False, "use_equal": True},
            "((start_time = 1 and end_time = 2))",
        ),
        (1, 2, {"use_start": False, "use_follows": True}, "((start_time = 2))"),
        (1, 2, {"use_start": False, "use_precedes": True}, "((end_time = 1))"),
        (
            1,
            2,
            {
                "use_during": True,
                "use_overlap": True,
                "use_contain": True,
                "use_equal": True,
                "use_follows": True,
                "use_precedes": True,
            },
            "((start_time >= 1 and start_time < 2)  OR ((start_time > 1 and end_time < 2) OR (start_time >= 1 and end_time < 2) OR (start_time > 1 and end_time <= 2)) OR ((start_time < 1 and end_time > 1 and end_time < 2) OR (start_time < 2 and start_time > 1 and end_time > 2)) OR ((start_time < 1 and end_time > 2) OR (start_time <= 1 and end_time > 2) OR (start_time < 1 and end_time >= 2)) OR (start_time = 1 and end_time = 2) OR (start_time = 2) OR (end_time = 1))",
        ),
        (*DATES, {"use_start": False}, None),
        (
            *DATES,
            {},
            "((start_time >= '2001-01-01 12:30:00' and start_time < '2001-03-31 14:30:00') )",
        ),
        (
            *DATES,
            {"use_start": False, "use_during": True},
            "(((start_time > '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time >= '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time > '2001-01-01 12:30:00' and end_time <= '2001-03-31 14:30:00')))",
        ),
        (
            *DATES,
            {"use_start": False, "use_overlap": True},
            "(((start_time < '2001-01-01 12:30:00' and end_time > '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time < '2001-03-31 14:30:00' and start_time > '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00')))",
        ),
        (
            *DATES,
            {"use_start": False, "use_contain": True},
            "(((start_time < '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00') OR (start_time <= '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00') OR (start_time < '2001-01-01 12:30:00' and end_time >= '2001-03-31 14:30:00')))",
        ),
        (
            *DATES,
            {"use_start": False, "use_equal": True},
            "((start_time = '2001-01-01 12:30:00' and end_time = '2001-03-31 14:30:00'))",
        ),
        (
            *DATES,
            {"use_start": False, "use_follows": True},
            "((start_time = '2001-03-31 14:30:00'))",
        ),
        (
            *DATES,
            {"use_start": False, "use_precedes": True},
            "((end_time = '2001-01-01 12:30:00'))",
        ),
        (
            *DATES,
            {
                "use_during": True,
                "use_overlap": True,
                "use_contain": True,
                "use_equal": True,
                "use_follows": True,
                "use_precedes": True,
            },
            "((start_time >= '2001-01-01 12:30:00' and start_time < '2001-03-31 14:30:00')  OR ((start_time > '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time >= '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time > '2001-01-01 12:30:00' and end_time <= '2001-03-31 14:30:00')) OR ((start_time < '2001-01-01 12:30:00' and end_time > '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time < '2001-03-31 14:30:00' and start_time > '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00')) OR ((start_time < '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00') OR (start_time <= '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00') OR (start_time < '2001-01-01 12:30:00' and end_time >= '2001-03-31 14:30:00')) OR (start_time = '2001-01-01 12:30:00' and end_time = '2001-03-31 14:30:00') OR (start_time = '2001-03-31 14:30:00') OR (end_time = '2001-01-01 12:30:00'))",
        ),
    ],
)
def test_sql_where_statement_of_a_temporal_relation(
    start, end, selection, expected
) -> None:
    assert (
        create_temporal_relation_sql_where_statement(start, end, **selection)
        == expected
    )
