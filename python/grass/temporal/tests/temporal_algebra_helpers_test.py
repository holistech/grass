"""Tests of the helper methods of TemporalAlgebraParser on in-memory maps.

The helpers do the real work behind the grammar rules: building the
spatio-temporal topology, assigning boolean condition values, evaluating
temporal functions and combining conditions. Here they are called directly
with raster map objects which exist only in memory, so every input and every
expected result is visible in the test.

All maps get a spatial extent because the temporal extent operators also
intersect the spatial extents.

Time lines used throughout (one month per cell, 2001):

.. code-block:: text

          Jan  Feb  Mar  Apr  May
    A     a1   a2   a3   a4
    B          b2   b3        b5
    C     c1------  c3------
"""

import gc
import weakref
from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.temporal.temporal_algebra import GlobalTemporalVar, TemporalAlgebraParser

BOX = {"north": 10, "south": 0, "east": 10, "west": 0, "top": 0, "bottom": 0}


@pytest.fixture
def raw_parser(temporal_exit_session):
    """A parser as constructed by the user, before parse() was ever called"""
    return TemporalAlgebraParser()


@pytest.fixture
def parser(raw_parser):
    """A parser with the attributes which parse() would set"""
    raw_parser.count = 0
    raw_parser.stdstype = "strds"
    raw_parser.mapclass = tgis.RasterDataset
    return raw_parser


def month(number, year=2001):
    return datetime(year, number, 1)


def make_map(name, start, end=None, *, relative=False, box=BOX):
    """A raster map object with time stamp and spatial extent, not in a database"""
    map_id = f"{name}@PERMANENT"
    map_object = tgis.RasterDataset(map_id)
    map_object.uid = map_id
    if relative:
        map_object.set_relative_time(start, end, "days")
    else:
        map_object.set_absolute_time(start, end)
    map_object.set_spatial_extent_from_values(**box)
    return map_object


def monthly(prefix, months):
    """Maps prefix+number covering one month each, for the given month numbers"""
    return [
        make_map(f"{prefix}{number}", month(number), month(number + 1))
        for number in months
    ]


def series_a():
    return monthly("a", [1, 2, 3, 4])


def series_b():
    return monthly("b", [2, 3, 5])


def series_c():
    return [
        make_map("c1", month(1), month(3)),
        make_map("c3", month(3), month(5)),
    ]


def names(map_list):
    return [map_object.get_name() for map_object in map_list]


def extents(map_list):
    """(start month, end month) for each absolute-time map"""
    return [
        (
            map_object.get_absolute_time()[0].month,
            map_object.get_absolute_time()[1].month,
        )
        for map_object in map_list
    ]


def with_condition(map_list, values):
    for map_object, value in zip(map_list, values, strict=True):
        map_object.condition_value = [value]
    return map_list


# --- build_spatio_temporal_topology_list --------------------------------------


@pytest.mark.parametrize(
    ("maps_a", "maps_b", "relations", "expected"),
    [
        (series_a, series_b, ["EQUAL"], ["a2", "a3"]),
        (series_a, series_b, ["equal"], ["a2", "a3"]),
        (series_a, series_b, ["Equal"], ["a2", "a3"]),
        (series_b, series_a, ["EQUAL"], ["b2", "b3"]),
        (series_a, series_c, ["DURING"], ["a1", "a2", "a3", "a4"]),
        (series_c, series_a, ["CONTAINS"], ["c1", "c3"]),
        (series_c, series_a, ["DURING"], []),
        (series_a, series_c, ["CONTAINS"], []),
        (series_a, series_c, ["STARTS"], ["a1", "a3"]),
        (series_a, series_c, ["FINISHES"], ["a2", "a4"]),
        (series_c, series_a, ["STARTED"], ["c1", "c3"]),
        (series_c, series_a, ["FINISHED"], ["c1", "c3"]),
        (series_a, series_b, ["FOLLOWS"], ["a3", "a4"]),
        (series_a, series_b, ["PRECEDES"], ["a1", "a2", "a4"]),
        (series_a, series_b, ["FOLLOWS", "PRECEDES"], ["a1", "a2", "a3", "a4"]),
        (series_a, series_b, ["EQUAL", "PRECEDES"], ["a1", "a2", "a3", "a4"]),
        (series_a, series_b, ["EQUAL", "FOLLOWS"], ["a2", "a3", "a4"]),
        (series_a, series_b, ["OVERLAPS"], []),
        (series_a, series_b, ["EQUAL", "EQUAL"], ["a2", "a3"]),
        (series_a, list, ["EQUAL"], []),
        (list, series_a, ["EQUAL"], []),
    ],
)
def test_topology_list(parser, maps_a, maps_b, relations, expected):
    """The result holds the maps of the first list which have one of the
    relations to a map of the second list"""
    result = parser.build_spatio_temporal_topology_list(maps_a(), maps_b(), relations)
    assert names(result) == expected


def test_topology_list_overlaps(parser):
    """overlaps and overlapped are the two directions of partial overlap"""
    left = [make_map("l", datetime(2001, 1, 1), datetime(2001, 3, 1))]
    right = [make_map("r", datetime(2001, 2, 1), datetime(2001, 4, 1))]
    assert names(
        parser.build_spatio_temporal_topology_list(left, right, ["OVERLAPS"])
    ) == ["l"]
    assert (
        names(parser.build_spatio_temporal_topology_list(left, right, ["OVERLAPPED"]))
        == []
    )
    assert names(
        parser.build_spatio_temporal_topology_list(right, left, ["OVERLAPPED"])
    ) == ["r"]


def test_topology_list_default_is_equal(parser):
    """Without a relation list maps are compared for equal time"""
    assert names(
        parser.build_spatio_temporal_topology_list(series_a(), series_b())
    ) == [
        "a2",
        "a3",
    ]


def test_topology_list_relative_time(parser):
    """Relative time is handled like absolute time"""
    left = [make_map(f"l{i}", i, i + 1, relative=True) for i in range(5)]
    right = [make_map(f"r{i}", i + 2, i + 3, relative=True) for i in range(5)]
    assert names(parser.build_spatio_temporal_topology_list(left, right)) == [
        "l2",
        "l3",
        "l4",
    ]


def test_topology_list_time_instances(parser):
    """Instants are compared with instants by equal time"""
    left = [make_map("p1", month(1)), make_map("p2", month(2))]
    right = [make_map("q2", month(2)), make_map("q3", month(3))]
    assert names(parser.build_spatio_temporal_topology_list(left, right)) == ["p2"]


def test_topology_list_is_sorted_by_start_time(parser):
    """The result is chronological whatever the input order"""
    maps_a = list(reversed(series_a()))
    assert names(parser.build_spatio_temporal_topology_list(maps_a, series_a())) == [
        "a1",
        "a2",
        "a3",
        "a4",
    ]


def test_topology_list_keeps_maps_with_equal_names(parser):
    """Maps are told apart by uid, so equal map names do not collapse"""
    first = make_map("x", month(1), month(2))
    second = make_map("x", month(1), month(2))
    first.uid = "x_first"
    second.uid = "x_second"
    reference = [make_map("y", month(1), month(2))]
    result = parser.build_spatio_temporal_topology_list([first, second], reference)
    assert [map_object.uid for map_object in result] == ["x_first", "x_second"]


@pytest.mark.parametrize("relations", [["BOGUS"], ["EQUAL", "bogus"], ["during|equal"]])
def test_topology_list_unknown_relation(parser, relations):
    """An unknown relation name raises SyntaxError naming it"""
    with pytest.raises(SyntaxError, match="Unpermitted topological relation name"):
        parser.build_spatio_temporal_topology_list(series_a(), series_b(), relations)


def test_topology_list_count_map_without_map_value(parser):
    """count_map stores the number of related maps in map_value.td"""
    maps_c = series_c()
    result = parser.build_spatio_temporal_topology_list(
        maps_c, series_a(), ["CONTAINS"], count_map=True
    )
    assert [map_object.map_value.td for map_object in result] == [2, 2]


def test_topology_list_count_map_appends_to_map_value(parser):
    """If map_value is a list (as after check_stds) the count is appended"""
    maps_c = series_c()
    for map_object in maps_c:
        map_object.map_value = []
    parser.build_spatio_temporal_topology_list(
        maps_c, series_a(), ["CONTAINS"], count_map=True
    )
    assert [[gvar.td for gvar in map_object.map_value] for map_object in maps_c] == [
        [2],
        [2],
    ]


def test_topology_list_count_map_with_several_relations(parser):
    """The count covers the maps related by any of the relations (hash operator
    with several relations, as in A {#,equal|precedes} B)"""
    maps_a = series_a()
    for map_object in maps_a:
        map_object.map_value = []
    parser.build_spatio_temporal_topology_list(
        maps_a, series_b(), ["EQUAL", "PRECEDES"], count_map=True
    )
    counts = {
        map_object.get_name(): [g.td for g in map_object.map_value]
        for map_object in maps_a
    }
    # a2 is equal to b2 and precedes b3; a3 is equal to b3 only; a1 and a4
    # precede one map each
    assert counts == {"a1": [1], "a2": [2], "a3": [1], "a4": [1]}


def test_topology_list_spatial_relation_requires_spatial_neighbour(parser):
    """A spatial relation in the list keeps only maps which have it"""
    near = [make_map("n", month(1), month(2))]
    same_place = [make_map("s", month(1), month(2))]
    elsewhere = [
        make_map(
            "e",
            month(1),
            month(2),
            box={
                "north": 30,
                "south": 20,
                "east": 30,
                "west": 20,
                "top": 0,
                "bottom": 0,
            },
        )
    ]
    assert names(
        parser.build_spatio_temporal_topology_list(
            near, same_place, ["EQUAL", "EQUIVALENT"]
        )
    ) == ["n"]
    assert (
        names(
            parser.build_spatio_temporal_topology_list(
                near, elsewhere, ["EQUAL", "EQUIVALENT"]
            )
        )
        == []
    )
    assert names(
        parser.build_spatio_temporal_topology_list(near, elsewhere, ["EQUAL"])
    ) == ["n"]


# --- assign_bool_value / compare_bool_value -----------------------------------


def test_assign_bool_value_copies_related_condition(parser):
    """A map gets the condition value of the equal map of the other list"""
    maps_a = series_a()
    maps_b = with_condition(series_b(), [True, False, True])
    parser.build_spatio_temporal_topology_list(maps_a, maps_b, ["EQUAL"])
    by_name = {m.get_name(): m for m in maps_a}
    assert parser.assign_bool_value(by_name["a2"], ["EQUAL"]) is True
    assert parser.assign_bool_value(by_name["a3"], ["EQUAL"]) is False
    assert by_name["a2"].condition_value == [True]
    assert by_name["a3"].condition_value == [False]


def test_assign_bool_value_all_related_must_hold(parser):
    """If several maps are related all their conditions must be true"""
    maps_c = series_c()
    maps_a = with_condition(series_a(), [True, True, True, False])
    parser.build_spatio_temporal_topology_list(maps_c, maps_a, ["CONTAINS"])
    assert parser.assign_bool_value(maps_c[0], ["CONTAINS"]) is True
    assert parser.assign_bool_value(maps_c[1], ["CONTAINS"]) is False


def test_assign_bool_value_ignores_non_boolean_values(parser):
    """Only booleans count, other condition entries (operators) are skipped"""
    maps_a = series_a()
    maps_b = series_b()
    maps_b[0].condition_value = [True, "&&"]
    parser.build_spatio_temporal_topology_list(maps_a, maps_b, ["EQUAL"])
    assert parser.assign_bool_value(maps_a[1], ["EQUAL"]) is True


@pytest.mark.parametrize(
    ("compop", "aggregate", "expected"),
    [
        # a1 [T] precedes b2 [T]; a2 [T] is equal to b2 [T] and precedes b3 [F];
        # a3 [T] is equal to b3 [F]. The own value is combined with the
        # aggregate of the related values.
        ("&", "&", {"a1": True, "a2": False, "a3": False}),
        ("|", "|", {"a1": True, "a2": True, "a3": True}),
        ("&", "|", {"a1": True, "a2": True, "a3": False}),
        ("|", "&", {"a1": True, "a2": True, "a3": True}),
    ],
)
def test_compare_bool_value(parser, compop, aggregate, expected):
    """The condition of a map is its own value combined by compop with the
    aggregate of the values of related maps"""
    maps_a = with_condition(series_a(), [True] * 4)
    maps_b = with_condition(series_b(), [True, False, True])
    result = parser.build_spatio_temporal_topology_list(
        maps_a,
        maps_b,
        ["EQUAL", "PRECEDES"],
        compare_bool=True,
        compop=compop,
        aggregate=aggregate,
    )
    assert {
        m.get_name(): m.condition_value for m in result if m.get_name() in expected
    } == {name: [value] for name, value in expected.items()}


@pytest.mark.parametrize(
    ("own", "other", "compop", "expected"),
    [
        (True, True, "&", True),
        (True, False, "&", False),
        (False, True, "&", False),
        (False, False, "&", False),
        (True, True, "|", True),
        (True, False, "|", True),
        (False, True, "|", True),
        (False, False, "|", False),
    ],
)
def test_compare_bool_value_truth_table(parser, own, other, compop, expected):
    """Truth table of & and | between two equal maps"""
    left = with_condition([make_map("l", month(1), month(2))], [own])
    right = with_condition([make_map("r", month(1), month(2))], [other])
    parser.build_spatio_temporal_topology_list(
        left, right, ["EQUAL"], compare_bool=True, compop=compop, aggregate=compop
    )
    assert left[0].condition_value == [expected]


def test_compare_bool_value_without_related_maps_keeps_value(parser):
    """A map without related map keeps its own condition"""
    left = with_condition([make_map("l", month(1), month(2))], [False])
    right = with_condition([make_map("r", month(3), month(4))], [True])
    parser.build_spatio_temporal_topology_list(
        left, right, ["EQUAL"], compare_bool=True, compop="|", aggregate="|"
    )
    assert left[0].condition_value == [False]


def test_compare_bool_value_requires_boolean(parser):
    """A non-boolean own value is refused, because the combination is
    evaluated as a Python expression"""
    left = [make_map("l", month(1), month(2))]
    left[0].condition_value = ["__import__('os')"]
    with pytest.raises(TypeError, match="must be a bool"):
        parser.compare_bool_value(left[0], "&", "&", ["EQUAL"])


# --- perform_temporal_selection / eval_map_list ---------------------------------


def test_selection(parser):
    """Selection keeps the maps with the relation"""
    assert names(
        parser.perform_temporal_selection(series_a(), series_b(), ["EQUAL"])
    ) == [
        "a2",
        "a3",
    ]


def test_selection_inverse(parser):
    """Inverse selection keeps the others, in chronological order"""
    maps_a = list(reversed(series_a()))
    result = parser.perform_temporal_selection(
        maps_a, series_b(), ["EQUAL"], inverse=True
    )
    assert names(result) == ["a1", "a4"]


def test_selection_inverse_with_several_relations(parser):
    """Inverse selection removes maps having any of the relations"""
    result = parser.perform_temporal_selection(
        series_a(), series_b(), ["EQUAL", "PRECEDES"], inverse=True
    )
    assert names(result) == []


def test_selection_with_assign_val(parser):
    """assign_val transfers the condition of the related maps"""
    maps_b = with_condition(series_b(), [True, False, True])
    result = parser.perform_temporal_selection(
        series_a(), maps_b, ["EQUAL"], assign_val=True
    )
    assert [(m.get_name(), m.condition_value) for m in result] == [
        ("a2", [True]),
        ("a3", [False]),
    ]


def test_eval_map_list(parser):
    """eval_map_list moves conditions onto the maps of the then list"""
    conditions = with_condition(series_a(), [True, False, True, True])
    result = parser.eval_map_list(conditions, series_b(), ["EQUAL"])
    assert [(m.get_name(), m.condition_value) for m in result] == [
        ("b2", [False]),
        ("b3", [True]),
    ]


# --- set_granularity ---------------------------------------------------------------


def test_set_granularity_left_reference(parser):
    """Left reference keeps the extent of every map"""
    result = parser.set_granularity(series_a(), series_c(), "l", ["DURING"])
    assert extents(result) == [(1, 2), (2, 3), (3, 4), (4, 5)]


@pytest.mark.parametrize("operator", ["r", "u", "d"])
def test_set_granularity_takes_the_larger_extent(parser, operator):
    """For maps inside C, right reference, union and disjoint union all give
    the extent of C"""
    result = parser.set_granularity(series_a(), series_c(), operator, ["DURING"])
    assert extents(result) == [(1, 3), (1, 3), (3, 5), (3, 5)]
    assert sorted(names(result)) == ["a1", "a2", "a3", "a4"]


def test_set_granularity_intersection(parser):
    """Intersection of a map inside C is the map itself"""
    result = parser.set_granularity(series_a(), series_c(), "i", ["DURING"])
    assert extents(result) == [(1, 2), (2, 3), (3, 4), (4, 5)]


def test_set_granularity_partial_overlap(parser):
    """Union and intersection of partially overlapping maps"""

    def left():
        return [make_map("l", datetime(2001, 1, 1), datetime(2001, 3, 1))]

    right = [make_map("r", datetime(2001, 2, 1), datetime(2001, 4, 1))]
    assert extents(parser.set_granularity(left(), right, "u", ["OVERLAPS"])) == [(1, 4)]
    assert extents(parser.set_granularity(left(), right, "i", ["OVERLAPS"])) == [(2, 3)]
    assert extents(parser.set_granularity(left(), right, "r", ["OVERLAPS"])) == [(2, 4)]
    assert extents(parser.set_granularity(left(), right, "l", ["OVERLAPS"])) == [(1, 3)]


def test_set_granularity_adjacent_maps_union(parser):
    """Union of adjacent maps spans both"""
    maps_a = [make_map("l", month(1), month(2))]
    maps_b = [make_map("r", month(2), month(4))]
    assert extents(parser.set_granularity(maps_a, maps_b, "u", ["PRECEDES"])) == [
        (1, 4)
    ]


def test_set_granularity_relative_time(parser):
    """Relative time extents are updated with the unit kept"""
    maps_a = [make_map(f"l{i}", i, i + 1, relative=True) for i in range(4)]
    maps_b = [make_map("r", 0, 2, relative=True), make_map("s", 2, 4, relative=True)]
    result = parser.set_granularity(maps_a, maps_b, "u", ["DURING"])
    assert sorted((m.get_name(), m.get_relative_time()) for m in result) == [
        ("l0", (0, 2, "days")),
        ("l1", (0, 2, "days")),
        ("l2", (2, 4, "days")),
        ("l3", (2, 4, "days")),
    ]


def test_set_granularity_unknown_relation(parser):
    """An unknown relation raises SyntaxError"""
    with pytest.raises(SyntaxError, match="Unpermitted temporal relation name"):
        parser.set_granularity(series_a(), series_c(), "l", ["BOGUS"])


def test_set_granularity_rejects_spatial_relation(parser):
    """Spatial relation names are not allowed here, only temporal ones"""
    with pytest.raises(SyntaxError, match="Unpermitted temporal relation name"):
        parser.set_granularity(series_a(), series_c(), "l", ["EQUAL", "EQUIVALENT"])


# --- get_temporal_func_dict ---------------------------------------------------------


def test_func_dict_interval(parser):
    """All 24 functions of an interval, worked out from the calendar.

    2001-03-10 is a Saturday, day 31 + 28 + 10 = 69 of the year, in ISO week
    10. 2001-12-31 is a Monday, day 365, and belongs to ISO week 1 of 2002.
    """
    interval = make_map(
        "m", datetime(2001, 3, 10, 15, 30, 45), datetime(2001, 12, 31, 23, 59, 58)
    )
    result = parser.get_temporal_func_dict(interval)
    assert result == {
        "START_DOY": 69,
        "START_DOW": 6,
        "START_YEAR": 2001,
        "START_MONTH": 3,
        "START_WEEK": 10,
        "START_DAY": 10,
        "START_HOUR": 15,
        "START_MINUTE": 30,
        "START_SECOND": 45,
        "START_DATE": datetime(2001, 3, 10).date(),
        "START_DATETIME": datetime(2001, 3, 10, 15, 30, 45),
        "START_TIME": datetime(2001, 3, 10, 15, 30, 45).time(),
        "END_DOY": 365,
        "END_DOW": 1,
        "END_YEAR": 2001,
        "END_MONTH": 12,
        "END_WEEK": 1,
        "END_DAY": 31,
        "END_HOUR": 23,
        "END_MINUTE": 59,
        "END_SECOND": 58,
        "END_DATE": datetime(2001, 12, 31).date(),
        "END_DATETIME": datetime(2001, 12, 31, 23, 59, 58),
        "END_TIME": datetime(2001, 12, 31, 23, 59, 58).time(),
    }


def test_func_dict_time_instance(parser):
    """A time instance has start functions only, end functions are None"""
    result = parser.get_temporal_func_dict(
        make_map("m", datetime(2001, 3, 10, 15, 30, 45))
    )
    assert result["START_DOY"] == 69
    assert result["START_SECOND"] == 45
    assert all(value is None for key, value in result.items() if key.startswith("END_"))
    assert all(
        value is not None for key, value in result.items() if key.startswith("START_")
    )


def test_func_dict_relative_time(parser):
    """Relative time has no calendar, every function is None"""
    result = parser.get_temporal_func_dict(make_map("m", 1, 3, relative=True))
    assert len(result) == 24
    assert set(result.values()) == {None}


@pytest.mark.parametrize(
    ("stamp", "key", "value"),
    [
        (datetime(2000, 12, 31), "START_DOY", 366),  # leap year
        (datetime(2001, 12, 31), "START_DOY", 365),
        (datetime(2001, 3, 11), "START_DOW", 7),  # Sunday
        (datetime(2001, 3, 12), "START_DOW", 1),  # Monday
        (datetime(2001, 1, 1), "START_WEEK", 1),
        (datetime(2000, 1, 1), "START_WEEK", 52),  # Saturday, ISO week 52 of 1999
        (datetime(2001, 1, 1, 0, 0, 0), "START_HOUR", 0),
        (datetime(2001, 1, 1, 23, 59, 59), "START_SECOND", 59),
        (datetime(2001, 1, 1, 12, 0, 0, 999999), "START_SECOND", 0),
    ],
)
def test_func_dict_calendar_edge_cases(parser, stamp, key, value):
    """Leap years, week boundaries and sub-second parts"""
    assert (
        parser.get_temporal_func_dict(make_map("m", stamp, datetime(2010, 1, 1)))[key]
        == value
    )


# --- eval_global_var ----------------------------------------------------------------


def global_var(tfunc, compop, value):
    var = GlobalTemporalVar()
    var.tfunc = tfunc
    var.compop = compop
    var.value = value
    return var


@pytest.mark.parametrize(
    ("compop", "expected"),
    [
        ("==", [False, True, False]),
        ("!=", [True, False, True]),
        ("<", [True, False, False]),
        ("<=", [True, True, False]),
        (">", [False, False, True]),
        (">=", [False, True, True]),
    ],
)
def test_eval_global_var_comparison_operators(parser, compop, expected):
    """Each comparison operator against the start month of Jan, Feb, Mar"""
    maps_a = series_a()[:3]
    for map_object in maps_a:
        map_object.condition_value = []
    parser.eval_global_var(global_var("start_month", compop, 2), maps_a)
    assert [m.condition_value for m in maps_a] == [[value] for value in expected]


@pytest.mark.parametrize(
    ("tfunc", "value", "expected"),
    [
        ("start_doy", 32, [False, True, False]),
        ("end_doy", 60, [False, True, False]),
        ("start_year", 2001, [True, True, True]),
        ("start_dow", 4, [False, True, True]),
        ("start_week", 5, [False, True, False]),
        ("start_day", 1, [True, True, True]),
        ("start_hour", 0, [True, True, True]),
        ("end_month", 4, [False, False, True]),
        ("end_day", 1, [True, True, True]),
        ("start_second", 0, [True, True, True]),
        ("start_minute", 0, [True, True, True]),
        ("start_month", 2.0, [False, True, False]),
        ("START_MONTH", 2, [False, True, False]),
    ],
)
def test_eval_global_var_number_functions(parser, tfunc, value, expected):
    """Number functions compare with == against ints and floats, in any case"""
    maps_a = series_a()[:3]
    for map_object in maps_a:
        map_object.condition_value = []
    parser.eval_global_var(global_var(tfunc, "==", value), maps_a)
    assert [m.condition_value[0] for m in maps_a] == expected


@pytest.mark.parametrize(
    ("tfunc", "compop", "literal", "expected"),
    [
        ("start_date", "==", '"2001-02-01"', [False, True, False]),
        ("start_date", ">", '"2001-02-01"', [False, False, True]),
        ("end_date", "<=", '"2001-03-01"', [True, True, False]),
        ("start_time", "==", '"00:00:00"', [True, True, True]),
        ("start_time", "<", '"12:00:00"', [True, True, True]),
        ("end_time", ">", '"12:00:00"', [False, False, False]),
        ("start_datetime", "==", '"2001-02-01 00:00:00"', [False, True, False]),
        ("start_datetime", ">", '"2001-01-31 23:59:59"', [False, True, True]),
        ("end_datetime", ">=", '"2001-03-01 00:00:00"', [False, True, True]),
        ("start_datetime", "<", '"2001-02-15 15:00:00"', [True, True, False]),
        ("start_datetime", "<", '"2001-02-15 09:00:00"', [True, True, False]),
        ("start_datetime", "<", '"2001-02-15 23:00:00"', [True, True, False]),
    ],
)
def test_eval_global_var_time_literals(parser, tfunc, compop, literal, expected):
    """Literals are converted to date, time or datetime to match the function"""
    maps_a = series_a()[:3]
    for map_object in maps_a:
        map_object.condition_value = []
    parser.eval_global_var(global_var(tfunc, compop, literal), maps_a)
    assert [m.condition_value[0] for m in maps_a] == expected


def test_eval_global_var_time_of_day(parser):
    """Time functions look at the time of day only"""
    maps_h = [
        make_map(
            "h1", datetime(2001, 1, 1, 6, 10, 20), datetime(2001, 2, 1, 6, 10, 20)
        ),
        make_map(
            "h2", datetime(2001, 2, 1, 15, 20, 30), datetime(2001, 3, 1, 15, 20, 30)
        ),
    ]
    for map_object in maps_h:
        map_object.condition_value = []
    parser.eval_global_var(global_var("start_time", ">", '"12:00:00"'), maps_h)
    assert [m.condition_value[0] for m in maps_h] == [False, True]


def test_eval_global_var_without_condition_value_attribute(parser):
    """A map without condition_value gets the plain boolean"""
    maps_a = series_a()[:2]
    parser.eval_global_var(global_var("start_month", "==", 1), maps_a)
    assert [m.condition_value for m in maps_a] == [True, False]


def test_eval_global_var_returns_the_list(parser):
    """The same list object is returned"""
    maps_a = series_a()
    assert parser.eval_global_var(global_var("start_month", "==", 1), maps_a) is maps_a


@pytest.mark.parametrize("tfunc", ["end_doy", "end_hour", "end_date", "end_datetime"])
def test_eval_global_var_end_of_instant_aborts(parser, tfunc):
    """End functions need an end time"""
    value = (
        '"2001-01-01"'
        if tfunc == "end_date"
        else '"2001-01-01 00:00:00"'
        if tfunc == "end_datetime"
        else 1
    )
    with pytest.raises(SystemExit):
        parser.eval_global_var(
            global_var(tfunc, "==", value), [make_map("p", month(1))]
        )


@pytest.mark.parametrize("tfunc", ["start_doy", "start_date", "end_month"])
def test_eval_global_var_relative_time_aborts(parser, tfunc):
    """Temporal functions are defined for absolute time only"""
    value = '"2001-01-01"' if tfunc == "start_date" else 1
    with pytest.raises(SystemExit):
        parser.eval_global_var(
            global_var(tfunc, "==", value), [make_map("r", 0, 1, relative=True)]
        )


def test_eval_global_var_unknown_operator(parser):
    """An unknown comparison operator is a ValueError"""
    with pytest.raises(ValueError, match="Unknown comparison operator"):
        parser.eval_global_var(global_var("start_month", "=<", 1), series_a())


def test_eval_datetime_str_is_alias(parser):
    """The deprecated name delegates to compare_values"""
    assert parser.eval_datetime_str(1, "<", 2) is True
    assert parser.eval_datetime_str(2, "<", 1) is False


# --- build_condition_list / eval_condition_list --------------------------------------------


def test_build_condition_list_global_variable(parser):
    """A single global variable is evaluated on the then list"""
    then_list = series_a()
    for map_object in then_list:
        map_object.condition_value = []
    result = parser.build_condition_list(global_var("start_month", ">", 2), then_list)
    assert [(m.get_name(), m.condition_value) for m in result] == [
        ("a1", [False]),
        ("a2", [False]),
        ("a3", [True]),
        ("a4", [True]),
    ]


def test_build_condition_list_map_list(parser):
    """A list of maps with conditions is related to the then list"""
    conditions = with_condition(series_a(), [True, False, True, True])
    result = parser.build_condition_list(conditions, series_b(), ["EQUAL"])
    assert [(m.get_name(), m.condition_value) for m in result] == [
        ("b2", [False]),
        ("b3", [True]),
    ]


def test_build_condition_list_relation_between_condition_and_then(parser):
    """The relation list sets how conditions and then maps are related

    It reads from the condition to the then map: the maps of A lie during
    the maps of C.
    """
    conditions = with_condition(series_a(), [True, True, False, True])
    result = parser.build_condition_list(conditions, series_c(), ["DURING"])
    assert [(m.get_name(), m.condition_value) for m in result] == [
        ("c1", [True]),
        ("c3", [False]),
    ]


def test_build_condition_list_unsupported_structure(parser):
    """Only a global variable or a list of maps with conditions is a condition.

    The branch for lists of condition lists and operators never worked
    (Review M2) and was removed; the grammar cannot produce such a list.
    """
    left = with_condition(series_a(), [True] * 4)
    operator = GlobalTemporalVar()
    operator.relationop = "&&"
    operator.topology = ["EQUAL"]
    with pytest.raises(ValueError, match="condition must be"):
        parser.build_condition_list([left, operator, left], series_a(), ["EQUAL"])


CONDITION_CASES = [
    # (condition list, expected selection) from left to right
    ([True], True),
    ([False], False),
    ([True, "&&", True], True),
    ([True, "&&", False], False),
    ([False, "||", True], True),
    ([True, "||", False], True),
    ([True, "&&", True, "&&", True], True),
    ([False, "&&", True, "&&", True], False),
    ([False, "&&", True], False),
    ([False, "||", False], False),
    ([True, "||", False, "&&", False], False),
    ([True, "&&", False, "&&", True], False),
    ([False, "||", True, "||", False], True),
    ([True, "||", False, "&&", True], True),
]


@pytest.mark.parametrize(("condition", "expected"), CONDITION_CASES)
def test_eval_condition_list(parser, condition, expected):
    """Conditions combine from left to right, && and || with equal precedence"""
    map_object = make_map("m", month(1), month(2))
    map_object.condition_value = list(condition)
    selected = parser.eval_condition_list([map_object])
    assert (selected == [map_object]) is expected


def test_eval_condition_list_inverse(parser):
    """inverse=True returns the maps where the condition is false"""
    maps_a = with_condition(series_a(), [True, False, True, False])
    assert names(parser.eval_condition_list(maps_a, inverse=True)) == ["a2", "a4"]


def test_eval_condition_list_selects_in_input_order(parser):
    """Selection keeps the order of the list"""
    maps_a = with_condition(series_a(), [True, False, True, True])
    assert names(parser.eval_condition_list(maps_a)) == ["a1", "a3", "a4"]


def test_eval_condition_list_skips_maps_without_condition(parser):
    """Maps without condition_value are neither selected nor in the inverse"""
    maps_a = series_a()
    maps_a[0].condition_value = [True]
    assert names(parser.eval_condition_list(maps_a)) == ["a1"]
    assert names(parser.eval_condition_list(maps_a, inverse=True)) == []


# --- check_stds ----------------------------------------------------------------------------


def test_check_stds_list_initializes_values(parser):
    """Maps in a list get empty map_value and condition_value"""
    result = parser.check_stds(series_a())
    assert [(m.map_value, m.condition_value) for m in result] == [([], [])] * 4


def test_check_stds_list_keeps_values(parser):
    """Existing values survive unless clear=True"""
    maps_a = with_condition(series_a(), [True] * 4)
    parser.check_stds(maps_a)
    assert [m.condition_value for m in maps_a] == [[True]] * 4
    parser.check_stds(maps_a, clear=True)
    assert [m.condition_value for m in maps_a] == [[]] * 4


def test_check_stds_single_map(parser):
    """A single map becomes a list of one"""
    map_object = make_map("m", month(1), month(2))
    assert parser.check_stds(map_object) == [map_object]


def test_check_stds_assigns_unique_uids(parser):
    """Every map gets a fresh unique uid for the topology analysis"""
    first = parser.check_stds(series_a())
    second = parser.check_stds(series_a())
    uids = [m.uid for m in first + second]
    assert len(set(uids)) == 8
    assert all(uid.startswith("tmp_map_name_") for uid in uids)


@pytest.mark.parametrize("value", [5, None, 1.5, ("a",)])
def test_check_stds_wrong_type_aborts(parser, value):
    """Anything but a name, map or list is a fatal error"""
    with pytest.raises(SystemExit):
        parser.check_stds(value)


def test_check_stds_on_fresh_parser(raw_parser):
    """Helpers work without parse() having been called (count, stdstype and
    mapclass are initialized by the constructor)"""
    assert len(raw_parser.check_stds(series_a())) == 4


# --- map names, overlay, extents -----------------------------------------------------------


def test_generate_map_name(parser):
    """Names combine pid and a counter and are registered"""
    parser.pid = 4711
    assert parser.generate_map_name() == "tmp_map_name_4711_1"
    assert parser.generate_map_name() == "tmp_map_name_4711_2"
    assert set(parser.names) == {"tmp_map_name_4711_1", "tmp_map_name_4711_2"}


def test_generate_new_map_copies_extent(parser):
    """The new map copies the temporal and spatial extent and gets a new name"""
    base = make_map("base", month(1), month(3))
    base.condition_value = [True]
    base.cmd_list = "cmd"
    new = parser.generate_new_map(base, copy=True, rename=True)
    assert new.get_absolute_time() == base.get_absolute_time()
    assert new.get_spatial_extent_as_tuple() == base.get_spatial_extent_as_tuple()
    assert new.get_name().startswith("tmp_map_name_")
    assert new.uid == new.get_name()
    assert new.condition_value == [True]
    assert new.cmd_list == "cmd"


def test_generate_new_map_keeps_base_name(parser):
    """rename=False keeps the id of the base map"""
    base = make_map("base", month(1), month(3))
    assert parser.generate_new_map(base, rename=False).get_id() == "base@PERMANENT"


def test_generate_new_map_remove_registers_for_removal(parser):
    """remove=True marks the intermediate map for later removal"""
    base = make_map("base", month(1), month(3))
    new = parser.generate_new_map(base, remove=True)
    assert parser.removable_maps == {new.uid: new}


def spatial(map_object):
    north, south, east, west = map_object.get_spatial_extent_as_tuple()[:4]
    return north, south, east, west


def box_map(box, start=month(1), end=month(3)):
    return make_map("x", start, end, box=box)


OTHER = {"north": 15, "south": 5, "east": 15, "west": 5, "top": 0, "bottom": 0}
FAR = {"north": 30, "south": 20, "east": 30, "west": 20, "top": 0, "bottom": 0}


@pytest.mark.parametrize(
    ("bool_op", "expected"),
    [("and", (10, 5, 10, 5)), ("or", (15, 0, 15, 0)), ("xor", (15, 0, 15, 0))],
)
def test_overlay_map_extent_spatial(parser, bool_op, expected):
    """and intersects, or and xor unite the spatial extents"""
    target = box_map(BOX)
    assert parser.overlay_map_extent(target, box_map(OTHER), bool_op, "l") == 1
    assert spatial(target) == expected


def test_overlay_map_extent_disjoint_union(parser):
    """disor of separate boxes spans both"""
    target = box_map(BOX)
    assert parser.overlay_map_extent(target, box_map(FAR), "disor", "l") == 1
    assert spatial(target) == (30, 0, 30, 0)


@pytest.mark.parametrize("bool_op", ["and", "or"])
def test_overlay_map_extent_spatially_disjoint(parser, bool_op):
    """Separate boxes have no intersection or overlapping union: return 0"""
    target = box_map(BOX)
    assert parser.overlay_map_extent(target, box_map(FAR), bool_op, "l") == 0
    assert spatial(target) == (10, 0, 10, 0)


@pytest.mark.parametrize(
    ("temp_op", "expected"),
    [("l", (1, 3)), ("i", (2, 3)), ("u", (1, 4)), ("d", (1, 4)), ("r", (2, 4))],
)
def test_overlay_map_extent_temporal(parser, temp_op, expected):
    """Left reference keeps, i intersects, u/d unite, r takes the other extent"""
    target = box_map(BOX, month(1), month(3))
    other = box_map(BOX, month(2), month(4))
    assert parser.overlay_map_extent(target, other, "and", temp_op) == 1
    assert extents([target]) == [expected]


def test_overlay_map_extent_temporally_disjoint(parser):
    """No temporal intersection returns 0"""
    target = box_map(BOX, month(1), month(2))
    other = box_map(BOX, month(3), month(4))
    assert parser.overlay_map_extent(target, other, "and", "i") == 0


def test_overlay_map_extent_copy(parser):
    """copy=True takes the extents of the second map unconditionally"""
    target = box_map(BOX, month(1), month(2))
    other = box_map(FAR, month(3), month(4))
    assert parser.overlay_map_extent(target, other, copy=True) == 1
    assert extents([target]) == [(3, 4)]
    assert spatial(target) == (30, 20, 30, 20)


def test_set_temporal_extent_list_left_reference(parser):
    """Left reference leaves every extent as it is"""
    maps_a, maps_c = series_a(), series_c()
    parser.build_spatio_temporal_topology_list(maps_a, maps_c, ["DURING"])
    result = parser.set_temporal_extent_list(maps_a, ["DURING"], "l")
    assert extents(result) == [(1, 2), (2, 3), (3, 4), (4, 5)]


@pytest.mark.parametrize("temporal", ["r", "u"])
def test_set_temporal_extent_list_reference_extent(parser, temporal):
    """Right reference and union put maps inside C on the extent of C"""
    maps_a, maps_c = series_a(), series_c()
    parser.build_spatio_temporal_topology_list(maps_a, maps_c, ["DURING"])
    result = parser.set_temporal_extent_list(maps_a, ["DURING"], temporal)
    assert extents(result) == [(1, 3), (1, 3), (3, 5), (3, 5)]


def test_set_temporal_extent_list_returns_new_maps(parser):
    """The result holds new intermediate maps, the input is left alone"""
    maps_a, maps_c = series_a(), series_c()
    parser.build_spatio_temporal_topology_list(maps_a, maps_c, ["DURING"])
    result = parser.set_temporal_extent_list(maps_a, ["DURING"], "r")
    assert all(m.get_name().startswith("tmp_map_name_") for m in result)
    assert extents(maps_a) == [(1, 2), (2, 3), (3, 4), (4, 5)]


def test_set_temporal_extent_list_needs_the_relation(parser):
    """Maps without the relation are dropped"""
    maps_a, maps_b = series_a(), series_b()
    parser.build_spatio_temporal_topology_list(maps_a, maps_b, ["EQUAL"])
    assert extents(parser.set_temporal_extent_list(maps_a, ["EQUAL"], "l")) == [
        (2, 3),
        (3, 4),
    ]


def test_set_temporal_extent_list_unknown_relation(parser):
    """An unknown relation raises SyntaxError"""
    with pytest.raises(SyntaxError, match="Unpermitted topological relation name"):
        parser.set_temporal_extent_list(series_a(), ["BOGUS"], "l")


def test_set_temporal_extent_list_spatial_relation_missing(parser):
    """If the related maps fail the spatial check the map is simply dropped
    (Review M3: this used to end in UnboundLocalError)"""
    maps_a, maps_c = series_a(), series_c()
    parser.build_spatio_temporal_topology_list(maps_a, maps_c, ["DURING"])
    assert parser.set_temporal_extent_list(maps_a, ["DURING", "COVER"], "l") == []


# --- operators, topology names, removal ----------------------------------------------------


@pytest.mark.parametrize(
    ("operator", "optype", "expected"),
    [
        ("{:,equal|during,r}", "select", (["EQUAL", "DURING"], "r", ":", None)),
        ("{!:,during}", "select", (["DURING"], "l", "!:", None)),
        ("{#,contains}", "hash", (["CONTAINS"], "l", "#", None)),
        ("{#}", "hash", (["EQUAL"], "l", "#", None)),
        ("{||,equal,l}", "boolean", (["EQUAL"], "l", "||", "|")),
        ("{&&,equal|during,u}", "boolean", (["EQUAL", "DURING"], "u", "&&", "&")),
        ("{equal|during}", "relation", (["EQUAL", "DURING"], None, None, None)),
    ],
)
def test_eval_toperator(parser, operator, optype, expected):
    """The operator string is split into relations (upper case), temporal
    operator, function and aggregate"""
    assert parser.eval_toperator(operator, optype) == expected


def test_eval_toperator_wrong_type(parser):
    """A hash operator is not valid as a select operator"""
    with pytest.raises(SyntaxError):
        parser.eval_toperator("{#,equal}", "select")


def test_check_topology_splits_temporal_and_spatial(parser):
    """Temporal and spatial relation names are returned separately, in upper case"""
    assert parser._check_topology(["equal", "Cover", "DURING", "in"]) == (
        ["EQUAL", "DURING"],
        ["COVER", "IN"],
    )


def test_check_topology_unknown(parser):
    """Unknown names raise SyntaxError"""
    with pytest.raises(SyntaxError, match="'sideways'"):
        parser._check_topology(["equal", "sideways"])


def test_known_relation_names(parser):
    """The eleven temporal and six spatial relations"""
    assert parser.temporal_topology_list == [
        "EQUAL",
        "FOLLOWS",
        "PRECEDES",
        "OVERLAPS",
        "OVERLAPPED",
        "DURING",
        "STARTS",
        "FINISHES",
        "CONTAINS",
        "STARTED",
        "FINISHED",
    ]
    assert parser.spatial_topology_list == [
        "EQUIVALENT",
        "COVER",
        "COVERED",
        "OVERLAP",
        "IN",
        "CONTAIN",
        "MEET",
    ]


def test_remove_maps_groups_by_type(parser):
    """Intermediate maps are removed with one g.remove call per map type"""
    parser.run = True
    parser.dry_run = True
    for name in ("x1", "x2", "x3"):
        parser.removable_maps[name] = make_map(name, month(1), month(2))
    parser.remove_maps()
    assert parser.process_chain_dict["remove"] == [
        {
            "name": "g.remove",
            "inputs": [("type", ["raster"]), ("name", ["x1,x2,x3"])],
            "outputs": [],
            "flags": ["f"],
        }
    ]


def test_remove_maps_chunks_of_100(parser):
    """g.remove gets at most 100 names per call"""
    parser.run = True
    parser.dry_run = True
    parser._remove_maps([f"m{i}" for i in range(250)], "raster")
    sizes = [
        len(call["inputs"][1][1][0].split(","))
        for call in parser.process_chain_dict["remove"]
    ]
    assert sizes == [100, 100, 50]


def test_remove_maps_nothing_to_do(parser):
    """No intermediate maps, no call"""
    parser.run = True
    parser.dry_run = True
    parser.remove_maps()
    assert parser.process_chain_dict["remove"] == []


def test_new_parser_state(raw_parser):
    """Initial state of a parser"""
    assert raw_parser.run is True
    assert raw_parser.process_chain_dict == {
        "processes": [],
        "register": [],
        "remove": [],
        "STDS": {},
    }
    assert raw_parser.use_granularity is False
    assert raw_parser.temporaltype is None
    assert raw_parser.removable_maps == {}
    assert raw_parser.names == {}


# --- spatial relations ----------------------------------------------------------------------


def spatial_pair_maps():
    """x1 (Jan, BOX) against y1 (Jan, FAR) and y2 (Feb, BOX).

    x1 is equal in time to y1 only and equivalent in space to y2 only.
    """
    left = [make_map("x1", month(1), month(2))]
    right = [
        make_map("y1", month(1), month(2), box=FAR),
        make_map("y2", month(2), month(3)),
    ]
    return left, right


def test_topology_list_spatial_relation_belongs_to_the_related_map(parser):
    """The map with the temporal relation must also have the spatial relation;
    a spatial relation to another map does not count"""
    left, right = spatial_pair_maps()
    result = parser.build_spatio_temporal_topology_list(
        left, right, ["EQUAL", "EQUIVALENT"]
    )
    assert names(result) == []


def test_topology_list_spatial_flag_requires_any_spatial_relation(parser):
    """With the spatial flag only spatially related maps are selected,
    whichever spatial relation they have"""
    parser.spatial = True
    left, right = spatial_pair_maps()
    assert names(parser.build_spatio_temporal_topology_list(left, right)) == []
    near = [make_map("y3", month(1), month(2))]
    assert names(parser.build_spatio_temporal_topology_list(left, near)) == ["x1"]


def test_topology_list_without_spatial_flag_ignores_space(parser):
    """Without the flag only time counts"""
    left, right = spatial_pair_maps()
    assert names(parser.build_spatio_temporal_topology_list(left, right)) == ["x1"]


# --- helpers of the grammar rules -------------------------------------------------------------


def test_neighbour_constants_with_equal_maps(parser):
    """Neighbours are found by position, also if the list holds maps which
    compare equal (Review M4: list.index found the first of them)"""
    maps_a = [make_map("a", month(1), month(2)) for _ in range(2)]
    maps_b = [make_map("b", month(3), month(4))]
    parser.check_stds = lambda stds: maps_a + maps_b
    result = parser._neighbour_constants("start_month", "ignored", 1)
    assert [m.cmd_list for m in result] == ["1", "3"]
    assert extents(result) == [(1, 2), (1, 2)]


def test_remove_maps_names_3d_raster_type_for_g_remove(parser):
    """g.remove calls the type of 3D rasters raster_3d, not raster3d"""
    parser.run = True
    parser.dry_run = True
    voxel = tgis.Raster3DDataset("cube@PERMANENT")
    parser.removable_maps["cube"] = voxel
    parser.remove_maps()
    assert parser.process_chain_dict["remove"][0]["inputs"][0] == (
        "type",
        ["raster_3d"],
    )


def test_parser_tables_do_not_keep_the_first_instance_alive(temporal_exit_session):
    """The cached tables are shared by the instances of a class, but must not
    hold the instance which built them (and with it its database connection)"""

    class Fresh(TemporalAlgebraParser):
        """Own class, so that no table of another test is reused"""

    first = Fresh()
    first.parser = first._build_parser()
    reference = weakref.ref(first)
    second = Fresh()
    second.parser = second._build_parser()
    del first
    gc.collect()
    assert reference() is None
    assert second.parser.productions[1].callable is not None


def test_add_map_value_sets_then_appends(parser):
    """The first map value is stored as it is, later ones are appended"""
    map_a = make_map("m", month(1), month(2))
    parser._add_map_value(map_a, "first")
    assert map_a.map_value == "first"
    map_a.map_value = ["first"]
    parser._add_map_value(map_a, "second")
    assert map_a.map_value == ["first", "second"]


def test_set_temporal_extent_list_calls_combine_for_each_related_map(parser):
    """The hook of the algebras sees the result map, the map and its related map"""
    maps_a, maps_b = series_a(), series_b()
    related = parser.build_spatio_temporal_topology_list(maps_a, maps_b)
    seen = []
    parser.set_temporal_extent_list(
        related,
        combine=lambda new, map_i, map_j: seen.append(
            (map_i.get_name(), map_j.get_name())
        ),
    )
    assert seen == [("a2", "b2"), ("a3", "b3")]


def test_set_temporal_extent_list_bool_op_disor_keeps_disjoint_maps(parser):
    """The disjoint union of two far apart maps exists, their intersection not"""
    far = {"north": 30, "south": 20, "east": 30, "west": 20, "top": 0, "bottom": 0}
    maps_a = [make_map("a1", month(1), month(2))]
    maps_b = [make_map("b1", month(1), month(2), box=far)]
    related = parser.build_spatio_temporal_topology_list(maps_a, maps_b)
    assert parser.set_temporal_extent_list(related, bool_op="and") == []
    result = parser.set_temporal_extent_list(related, bool_op="disor")
    assert len(result) == 1


@pytest.mark.parametrize(
    ("time_suffix", "expected"),
    [
        (None, ["r_1", "r_2"]),
        ("time", ["r_2001_01_01T00_00_00", "r_2001_02_01T00_00_00"]),
        ("gran", ["r_2001_01", "r_2001_02"]),
    ],
)
def test_result_map_names(parser, time_suffix, expected):
    """Result names: basename plus number, start time or time rounded to the
    granularity, numbering from the first number of the algebra"""
    parser.time_suffix = time_suffix
    parser.basename = "r"
    maps = [make_map("x", month(1), month(2)), make_map("y", month(2), month(3))]
    assert parser._result_map_names(maps, "stds") == expected


def test_result_map_names_default_to_the_dataset_name(parser):
    """Without basename the name of the result dataset is the basename"""
    parser.basename = None
    maps = [make_map("x", month(1), month(2))]
    assert parser._result_map_names(maps, "stds") == ["stds_1"]
