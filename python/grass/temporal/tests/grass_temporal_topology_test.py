"""Tests for the temporal topology builder, the map list sorting keys and the
SQL condition of a temporal relation

The relations follow Allen and Ferguson 1994, as cited by
grass.temporal.temporal_extent: an interval starting earlier and ending inside
a later one "overlaps" it, and the later one is "overlapped" by it.

Most maps are built in memory and need no GRASS session. The maps stored with
an end before their start are registered in a temporary project, because only
the temporal database can hold them.
"""

import itertools
from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.temporal import topology
from grass.temporal.abstract_dataset import (
    AbstractDatasetComparisonKeyEndTime,
    AbstractDatasetComparisonKeyStartTime,
)
from grass.temporal.space_time_datasets import RasterDataset
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.topology import (
    SpatioTemporalTopologyBuilder,
    create_temporal_relation_sql_where_statement,
)
from grass.tools import Tools


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


# A map whose stored interval ends before it starts. Registering refuses such
# an interval, but an older database or an edit by hand can hold one, so the
# tests below write the end into the database after the registration.

COUNTER = itertools.count(1)


def month(number):
    """The first day of the month that lies number months after January 2001"""
    year, index = divmod(number, 12)
    return datetime(2001 + year, index + 1, 1)


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    return tools


@pytest.fixture
def reversed_dataset(tools):
    """Function that registers maps and stores some of them reversed

    make(temporaltype, spans, reversed_numbers) creates the maps
    <prefix>_1, <prefix>_2, ... of the (start, end) spans, counted in months
    from January 2001 or in days of relative time, registers them in a
    dataset and stores the end of each map whose number is in
    reversed_numbers one unit before its start. Returns the dataset and the
    map ids in the order of the spans.
    """

    def make(temporaltype, spans, reversed_numbers):
        prefix = f"reversed{next(COUNTER)}"
        times = spans
        if temporaltype == "absolute":
            times = [(month(start), month(end)) for start, end in spans]
        create_stds(
            tools,
            "strds",
            f"{prefix}_ds",
            [
                MapSpec(f"{prefix}_{number}", number, start, end)
                for number, (start, end) in enumerate(times, 1)
            ],
            temporaltype=temporaltype,
            unit="days" if temporaltype == "relative" else None,
            via="library",
        )
        mapset = tgis.get_current_mapset()
        for number in reversed_numbers:
            map_ = tgis.RasterDataset(f"{prefix}_{number}@{mapset}")
            map_.select()
            end = spans[number - 1][0] - 1
            if temporaltype == "absolute":
                extent, end = map_.absolute_time, month(end)
            else:
                extent = map_.relative_time
            # The setter and update() do not check the order of start and end.
            extent.set_end_time(end)
            extent.update()
        stds = tgis.open_old_stds(f"{prefix}_ds", "strds")
        ids = [f"{prefix}_{number}@{mapset}" for number in range(1, len(spans) + 1)]
        return stds, ids

    return make


def stored_maps(stds):
    """The registered maps of the dataset, sorted by start time, as stored

    get_registered_maps_as_objects() sets the times of a map through
    set_absolute_time() or set_relative_time(), which refuse an end before the
    start and leave the map without time. select() reads the row as it is.
    """
    maps = []
    for row in stds.get_registered_maps("id", order="start_time"):
        map_ = stds.get_new_map_instance(row["id"])
        map_.select()
        maps.append(map_)
    return maps


def read_as_stored(monkeypatch, stds):
    """Make the dataset read its maps with stored_maps()

    The list with gaps reads the maps through get_registered_maps_as_objects(),
    which leaves a reversed map without time.
    """
    monkeypatch.setattr(
        stds,
        "get_registered_maps_as_objects",
        lambda *args, **kwargs: stored_maps(stds),
    )


def relations_by_id(maps):
    """The relations of each map except NEXT and PREV, as ids, by map id"""
    return {
        map_.get_id(): {
            name: sorted(related.get_id() for related in links)
            for name, links in map_.get_temporal_relations().items()
            if name not in {"NEXT", "PREV"}
        }
        for map_ in maps
    }


class Recorder:
    """The message interface of the library, which also keeps the warnings"""

    def __init__(self, messenger):
        self.messenger = messenger
        self.warnings = []

    def warning(self, message):
        self.warnings.append(message)
        self.messenger.warning(message)

    def __getattr__(self, name):
        return getattr(self.messenger, name)


@pytest.fixture
def warnings(monkeypatch):
    """The warnings that the topology module gives, as a list of texts"""
    recorder = Recorder(topology.get_tgis_message_interface())
    monkeypatch.setattr(topology, "get_tgis_message_interface", lambda: recorder)
    return recorder.warnings


def reversed_warning(map_id):
    return f"Map <{map_id}> ends before it starts; it gets no temporal relations"


# Each map starts one unit after the one before and lasts two units, so a map
# overlaps its neighbours and precedes the map two places later.
OVERLAPPING = [(0, 2), (1, 3), (2, 4), (3, 5), (4, 6)]
TEMPORAL_TYPES = ["absolute", "relative"]


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
@pytest.mark.parametrize("spatial", [None, "2D", "3D"])
@pytest.mark.parametrize("reversed_numbers", [(2,), (2, 4)])
def test_a_stored_reversed_interval_gets_no_relations(
    reversed_dataset, temporaltype, spatial, reversed_numbers
):
    stds, ids = reversed_dataset(temporaltype, OVERLAPPING, reversed_numbers)
    reversed_ids = {ids[number - 1] for number in reversed_numbers}
    maps = stored_maps(stds)

    builder = SpatioTemporalTopologyBuilder()
    builder.build(maps, spatial=spatial)

    good = [map_ for map_ in stored_maps(stds) if map_.get_id() not in reversed_ids]
    SpatioTemporalTopologyBuilder().build(good, spatial=spatial)
    expected = relations_by_id(good)
    assert all(expected.values()), "the maps left must be related to each other"
    found = relations_by_id(maps)
    assert {map_id: found[map_id] for map_id in expected} == expected
    assert all(found[map_id] == {} for map_id in reversed_ids)
    # The reversed maps keep their place in the iteration by start time.
    assert [map_.get_id() for map_ in builder] == ids


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
def test_a_stored_reversed_interval_warns_once(
    reversed_dataset, warnings, temporaltype
):
    stds, ids = reversed_dataset(temporaltype, OVERLAPPING, (2, 4))
    maps = stored_maps(stds)

    SpatioTemporalTopologyBuilder().build(maps)
    assert warnings == [reversed_warning(ids[1]), reversed_warning(ids[3])]

    # Each call warns again, and a map in both lists warns once.
    warnings.clear()
    SpatioTemporalTopologyBuilder().build(maps, stored_maps(stds))
    assert warnings == [reversed_warning(ids[1]), reversed_warning(ids[3])]


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
def test_a_list_of_reversed_intervals_has_no_relations(
    reversed_dataset, warnings, monkeypatch, temporaltype
):
    spans = [(0, 1), (1, 2), (2, 3)]
    stds, ids = reversed_dataset(temporaltype, spans, (1, 2, 3))
    maps = stored_maps(stds)

    builder = SpatioTemporalTopologyBuilder()
    builder.build(maps)

    assert relations_by_id(maps) == {map_id: {} for map_id in ids}
    assert [map_.get_id() for map_ in builder] == ids
    assert warnings == [reversed_warning(map_id) for map_id in ids]
    assert topology.count_gaps(maps) == 0
    read_as_stored(monkeypatch, stds)
    ids_with_gaps = [
        map_.get_id() for map_ in stds.get_registered_maps_as_objects_with_gaps()
    ]
    assert ids_with_gaps == ids


# Gaps lie between the first and the second map and between the last two. The
# second map is stored reversed, so only the gap between the last two counts.
WITH_GAPS = [(0, 1), (2, 3), (4, 5), (6, 7)]


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
def test_count_gaps_skips_a_reversed_interval(reversed_dataset, warnings, temporaltype):
    stds, ids = reversed_dataset(temporaltype, WITH_GAPS, (2,))

    assert topology.count_gaps(stored_maps(stds)) == 1
    assert warnings == [reversed_warning(ids[1])]


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
def test_the_list_with_gaps_skips_a_reversed_interval(
    reversed_dataset, warnings, monkeypatch, temporaltype
):
    stds, ids = reversed_dataset(temporaltype, WITH_GAPS, (2,))
    read_as_stored(monkeypatch, stds)

    maps = stds.get_registered_maps_as_objects_with_gaps()

    assert [map_.get_id() for map_ in maps] == [*ids[:3], None, ids[3]]
    assert maps[3].get_temporal_extent_as_tuple() == (
        maps[2].get_temporal_extent_as_tuple()[1],
        maps[4].get_temporal_extent_as_tuple()[0],
    )
    assert warnings == [reversed_warning(ids[1])]


# get_registered_maps_as_objects() refuses a stored end before the start with
# an error that names the map and leaves the map without time. The topology
# builder failed on such a map with a TypeError.


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
@pytest.mark.parametrize("spatial", [None, "2D", "3D"])
def test_a_map_without_time_gets_no_relations(
    reversed_dataset, warnings, temporaltype, spatial
):
    stds, ids = reversed_dataset(temporaltype, OVERLAPPING, (2,))
    maps = stds.get_registered_maps_as_objects(order="start_time")
    assert maps[1].get_temporal_extent_as_tuple() == (None, None)

    builder = SpatioTemporalTopologyBuilder()
    builder.build(maps, spatial=spatial)

    good = [map_ for map_ in stored_maps(stds) if map_.get_id() != ids[1]]
    SpatioTemporalTopologyBuilder().build(good, spatial=spatial)
    expected = relations_by_id(good)
    assert all(expected.values()), "the maps left must be related to each other"
    found = relations_by_id(maps)
    assert {map_id: found[map_id] for map_id in expected} == expected
    assert found[ids[1]] == {}
    # It comes last in the iteration, after the maps with a start time.
    assert [map_.get_id() for map_ in builder] == [*ids[:1], *ids[2:], ids[1]]
    # The reading named the map already.
    assert warnings == []


def chain_of(maps):
    """The ids of NEXT and PREV of each map, as (prev, next), by map id"""
    return {
        map_.get_id(): (
            map_.prev().get_id() if map_.prev() else None,
            map_.next().get_id() if map_.next() else None,
        )
        for map_ in maps
    }


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
def test_a_map_without_time_has_no_neighbours(reversed_dataset, temporaltype):
    stds, ids = reversed_dataset(temporaltype, OVERLAPPING, (2,))
    maps = stds.get_registered_maps_as_objects(order="start_time")

    builder = SpatioTemporalTopologyBuilder()
    builder.build(maps)

    chain = chain_of(maps)
    assert chain[ids[1]] == (None, None)
    # The chain of the other maps runs past it.
    assert chain[ids[0]] == (None, ids[2])
    assert chain[ids[2]] == (ids[0], ids[3])
    assert chain[ids[-1]][1] is None
    assert [map_.get_id() for map_ in builder] == [ids[0], *ids[2:], ids[1]]
    assert builder.get_first().get_id() == ids[0]
    assert len(builder) == len(ids)


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
def test_a_map_without_time_first_in_the_list(reversed_dataset, temporaltype):
    stds, ids = reversed_dataset(temporaltype, OVERLAPPING, (2,))
    maps = stds.get_registered_maps_as_objects(order="start_time")
    maps.insert(0, maps.pop(1))
    assert maps[0].get_id() == ids[1]

    builder = SpatioTemporalTopologyBuilder()
    builder.build(maps)

    assert builder.get_first().get_id() == ids[0]
    assert [map_.get_id() for map_ in builder] == [ids[0], *ids[2:], ids[1]]
    assert chain_of(maps)[ids[1]] == (None, None)


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
def test_only_maps_without_time(reversed_dataset, temporaltype):
    stds, ids = reversed_dataset(temporaltype, [(0, 1), (1, 2)], (1, 2))
    maps = stds.get_registered_maps_as_objects(order="start_time")
    assert all(map_.get_temporal_extent_as_tuple()[0] is None for map_ in maps)

    builder = SpatioTemporalTopologyBuilder()
    builder.build(maps)

    assert builder.get_first() is None
    assert [map_.get_id() for map_ in builder] == [map_.get_id() for map_ in maps]
    assert len(builder) == 2
    assert relations_by_id(maps) == {map_.get_id(): {} for map_ in maps}
    assert set(chain_of(maps).values()) == {(None, None)}


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
def test_a_map_without_time_only_in_the_second_list(reversed_dataset, temporaltype):
    stds, ids = reversed_dataset(temporaltype, OVERLAPPING, (2,))
    good = [map_ for map_ in stored_maps(stds) if map_.get_id() != ids[1]]
    maps = stds.get_registered_maps_as_objects(order="start_time")
    alone = [map_ for map_ in stored_maps(stds) if map_.get_id() != ids[1]]
    SpatioTemporalTopologyBuilder().build(alone)

    SpatioTemporalTopologyBuilder().build(good, maps)

    assert chain_of(good) == chain_of(alone)
    chain = chain_of(maps)
    assert chain[ids[1]] == (None, None)
    assert chain[ids[0]] == (None, ids[2])
    assert chain[ids[2]] == (ids[0], ids[3])


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
def test_a_map_without_time_in_both_lists(reversed_dataset, temporaltype):
    stds, ids = reversed_dataset(temporaltype, OVERLAPPING, (2,))
    first = stds.get_registered_maps_as_objects(order="start_time")
    second = stds.get_registered_maps_as_objects(order="start_time")

    SpatioTemporalTopologyBuilder().build(first, second)

    good = [
        [map_ for map_ in stored_maps(stds) if map_.get_id() != ids[1]]
        for _ in range(2)
    ]
    SpatioTemporalTopologyBuilder().build(*good)
    for maps, good_maps in zip((first, second), good, strict=True):
        expected = relations_by_id(good_maps)
        assert all(expected.values())
        found = relations_by_id(maps)
        assert {map_id: found[map_id] for map_id in expected} == expected
        assert found[ids[1]] == {}


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
def test_the_gaps_skip_a_map_without_time(reversed_dataset, warnings, temporaltype):
    """The maps with a start time before and after it are compared

    A map without time has no relation to a neighbour, so it is passed over
    like it is when the granularity is computed.
    """
    stds, ids = reversed_dataset(temporaltype, WITH_GAPS, (2,))

    assert stds.count_gaps() == 2
    maps = stds.get_registered_maps_as_objects_with_gaps()
    assert [map_.get_id() for map_ in maps] == [
        ids[0],
        ids[1],
        None,
        ids[2],
        None,
        ids[3],
    ]
    assert maps[2].get_temporal_extent_as_tuple() == (
        maps[0].get_temporal_extent_as_tuple()[1],
        maps[3].get_temporal_extent_as_tuple()[0],
    )
    assert warnings == []


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
def test_two_maps_without_time_in_a_row(reversed_dataset, temporaltype):
    """One gap covers the span between the maps with a start time"""
    stds, ids = reversed_dataset(temporaltype, WITH_GAPS, (2, 3))

    assert stds.count_gaps() == 1
    maps = stds.get_registered_maps_as_objects_with_gaps()
    assert [map_.get_id() for map_ in maps] == [*ids[:3], None, ids[3]]


EDGE_LISTS = {
    1: lambda ids: [ids[0], ids[1], None, ids[2], None, ids[3]],
    4: lambda ids: [ids[0], None, ids[1], None, ids[2], ids[3]],
}


@pytest.mark.parametrize("temporaltype", TEMPORAL_TYPES)
@pytest.mark.parametrize("edge", EDGE_LISTS)
def test_a_map_without_time_at_the_edge(reversed_dataset, temporaltype, edge):
    """No gap appears before or after a map without time at either end"""
    stds, ids = reversed_dataset(temporaltype, WITH_GAPS, (edge,))

    assert stds.count_gaps() == 2
    maps = stds.get_registered_maps_as_objects_with_gaps()
    assert [map_.get_id() for map_ in maps] == EDGE_LISTS[edge](ids)
