"""Tests for the temporal relation of two temporal extents

Extents are plain value objects, so no GRASS session and no temporal database
are needed here.
"""

import copy
import itertools
import pickle
import re
from collections import Counter
from datetime import UTC, datetime

import pytest

from grass.temporal.kinds import KINDS
from grass.temporal.temporal_extent import (
    AbsoluteTemporalExtent,
    AbsoluteTimeRow,
    RelativeTemporalExtent,
    RelativeTimeRow,
    TemporalExtent,
    ends_before_start,
)

# The order in which the first matching predicate names the relation. It is the
# order in which temporal_relation() asks the predicates.
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

# Points, intervals and intervals that start and end at the same time. An
# extent that ends before it starts is refused, see the tests at the end.
EXTENTS = [(start, end) for start in range(6) for end in [None, *range(start, 6)]]


def chain(a, b):
    """Name the relation as the predicates, asked one after the other, do"""
    for name in CHAIN:
        if getattr(a, name)(b):
            return name
    return None


def test_the_relation_names_every_pair_as_the_chain_of_predicates():
    for (start, end), (other_start, other_end) in itertools.product(EXTENTS, EXTENTS):
        a = TemporalExtent(start_time=start, end_time=end)
        b = TemporalExtent(start_time=other_start, end_time=other_end)
        assert a.temporal_relation(b) == chain(a, b), (a.D, b.D)


def test_the_relations_of_all_pairs_are_counted_as_before():
    # Counted on 25.10.2026 with the chain of predicates before any change; a
    # different order of the chain moves pairs from one name to another. Since
    # an extent that ends before it starts is refused, the pairs with such an
    # extent are left out; the remaining 729 pairs were counted on 26.10.2026
    # with the code before the refusal and kept their names.
    names = Counter(
        TemporalExtent(start_time=a, end_time=b).temporal_relation(
            TemporalExtent(start_time=c, end_time=d)
        )
        for (a, b), (c, d) in itertools.product(EXTENTS, EXTENTS)
    )
    assert names == {
        "after": 155,
        "before": 155,
        "contains": 70,
        "during": 70,
        "equal": 27,
        "finished": 35,
        "finishes": 35,
        "follows": 41,
        "overlapped": 15,
        "overlaps": 15,
        "precedes": 41,
        "started": 35,
        "starts": 35,
    }


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


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ((5, 6, "days"), (1, 2, "years")),
        ((5, 6, "days"), (5, 7, "years")),
    ],
    ids=["disjoint numbers", "overlapping numbers"],
)
def test_intersect_of_different_relative_units_is_none(first, second):
    a = RelativeTemporalExtent(start_time=first[0], end_time=first[1], unit=first[2])
    b = RelativeTemporalExtent(start_time=second[0], end_time=second[1], unit=second[2])

    assert a.intersect(b) is None
    assert b.intersect(a) is None


@pytest.mark.parametrize(
    "first",
    [
        RelativeTemporalExtent(start_time=1, end_time=5, unit=None),
        RelativeTemporalExtent(start_time=1, unit=None),
    ],
    ids=["interval", "instant"],
)
@pytest.mark.parametrize(
    "second",
    [
        RelativeTemporalExtent(start_time=10, end_time=12, unit="days"),
        TemporalExtent(start_time=10, end_time=12),
    ],
    ids=["relative with unit", "plain"],
)
def test_intersect_of_disjoint_relative_numbers_is_none(first, second):
    assert first.intersect(second) is None
    if isinstance(second, RelativeTemporalExtent):
        assert second.intersect(first) is None


def test_intersect_of_overlapping_numbers_without_a_unit_is_unchanged():
    a = RelativeTemporalExtent(start_time=3, end_time=6, unit=None)
    b = RelativeTemporalExtent(start_time=5, end_time=7, unit="days")

    for result in (a.intersect(b), b.intersect(a)):
        assert (result.D["start_time"], result.D["end_time"]) == (5, 6)


def _plain(extent):
    return TemporalExtent(
        start_time=extent.D["start_time"], end_time=extent.D["end_time"]
    )


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ((3, 6), (5, 7)),
        ((5, 7), (3, 6)),
        ((3, 8), (5, 6)),
        ((5, 6), (5, None)),
        ((5, None), (3, 6)),
        ((5, 8), (3, 4)),
    ],
)
def test_intersect_in_the_same_unit_is_that_of_plain_extents(first, second):
    a = RelativeTemporalExtent(start_time=first[0], end_time=first[1], unit="days")
    b = RelativeTemporalExtent(start_time=second[0], end_time=second[1], unit="days")

    expected = _plain(a).intersect(_plain(b))
    result = a.intersect(b)

    if expected is None:
        assert result is None
        return
    assert (result.D["start_time"], result.D["end_time"]) == (
        expected.D["start_time"],
        expected.D["end_time"],
    )
    # An instant stays a plain extent, as the classic algebra tells it by type.
    if expected.D["end_time"] is None:
        assert type(result) is type(expected)


def test_intersect_without_a_set_unit_on_both_sides_is_unchanged():
    with_unit = RelativeTemporalExtent(start_time=3, end_time=6, unit="days")
    no_unit = RelativeTemporalExtent(start_time=5, end_time=7)
    plain = TemporalExtent(start_time=5, end_time=7)

    for first, second in [
        (with_unit, no_unit),
        (no_unit, with_unit),
        (with_unit, plain),
        (plain, with_unit),
    ]:
        expected = TemporalExtent.intersect(first, second)
        result = first.intersect(second)
        assert expected is not None
        assert (result.D["start_time"], result.D["end_time"]) == (
            expected.D["start_time"],
            expected.D["end_time"],
        )


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


def refusal(start, end):
    return pytest.raises(
        ValueError, match=re.escape(f"End time {end} is before start time {start}")
    )


@pytest.mark.parametrize(
    ("start", "end"), [(5, 3), (datetime(2001, 1, 5), datetime(2001, 1, 3))]
)
def test_a_reversed_extent_is_refused(start, end):
    with refusal(start, end):
        TemporalExtent(start_time=start, end_time=end)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (datetime(2001, 1, 1), 5),
        (5, datetime(2001, 1, 1)),
        (datetime(2001, 1, 1), datetime(2001, 1, 2, tzinfo=UTC)),
    ],
    ids=["date and number", "number and date", "naive and aware"],
)
def test_start_and_end_that_cannot_be_compared_are_refused(start, end):
    with pytest.raises(ValueError, match="cannot be compared") as excinfo:
        TemporalExtent(start_time=start, end_time=end)
    # A chained TypeError would show Python's wording in the traceback.
    assert excinfo.value.__context__ is None


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [(5, 3, True), (3, 5, False), (3, 3, False), (3, None, False), (None, 3, False)],
)
def test_ends_before_start(start, end, expected):
    assert ends_before_start(start, end) is expected


@pytest.mark.parametrize(
    "build",
    [
        lambda: AbsoluteTemporalExtent(
            start_time=datetime(2001, 1, 5), end_time=datetime(2001, 1, 3)
        ),
        lambda: RelativeTemporalExtent(start_time=5, end_time=3, unit="days"),
        lambda: AbsoluteTimeRow(
            KINDS["strds"],
            start_time=datetime(2001, 1, 5),
            end_time=datetime(2001, 1, 3),
        ),
        lambda: RelativeTimeRow(KINDS["raster"], start_time=5, end_time=3, unit="days"),
    ],
    ids=["absolute", "relative", "absolute row", "relative row"],
)
def test_the_subclasses_refuse_a_reversed_extent(build):
    with pytest.raises(ValueError, match="is before start time"):
        build()


def test_an_extent_that_starts_and_ends_at_once_is_accepted():
    extent = TemporalExtent(start_time=5, end_time=5)

    assert (extent.get_start_time(), extent.get_end_time()) == (5, 5)


def reversed_by_setter(extent):
    # The setters do not check: t.shift and t.snap set the start and the end
    # one after the other and pass through such a state.
    extent.set_end_time(3)
    return extent


@pytest.mark.parametrize(
    ("build", "other"),
    [
        (
            lambda: TemporalExtent(start_time=5, end_time=6),
            lambda: TemporalExtent(start_time=1, end_time=2),
        ),
        (
            lambda: RelativeTemporalExtent(start_time=5, end_time=6, unit="days"),
            lambda: RelativeTemporalExtent(start_time=1, end_time=2, unit="days"),
        ),
        # Different units have no relation, a reversed extent is refused anyway.
        (
            lambda: RelativeTemporalExtent(start_time=5, end_time=6, unit="days"),
            lambda: RelativeTemporalExtent(start_time=1, end_time=2, unit="years"),
        ),
    ],
    ids=["plain", "relative", "relative other unit"],
)
def test_the_relation_of_a_reversed_extent_is_refused(build, other):
    reversed_extent = reversed_by_setter(build())

    with refusal(5, 3):
        reversed_extent.temporal_relation(other())
    with refusal(5, 3):
        other().temporal_relation(reversed_extent)


def test_the_predicates_of_a_reversed_extent_still_answer():
    # The classic algebra calls the predicates by name; they stay unchecked.
    reversed_extent = reversed_by_setter(TemporalExtent(start_time=5, end_time=6))
    other = TemporalExtent(start_time=1, end_time=2)

    assert reversed_extent.after(other)
    assert not reversed_extent.before(other)


# The predicate, the start and end of the two extents and the answer. These
# cases were the examples in the docstrings of TemporalExtent, which now keep
# one example each.
PREDICATES = [
    ("after", (8, 9), (6, 7), True),
    ("after", (6, 7), (8, 9), False),
    ("before", (6, 7), (8, 9), True),
    ("before", (8, 9), (6, 7), False),
    ("contains", (4, 9), (5, 8), True),
    ("contains", (5, 8), (4, 9), False),
    ("during", (5, 7), (4, 9), True),
    ("during", (4, 9), (5, 7), False),
    ("equal", (5, 6), (5, 6), True),
    ("finished", (5, 7), (6, 7), True),
    ("finished", (6, 7), (5, 7), False),
    ("finishes", (6, 7), (5, 7), True),
    ("finishes", (5, 7), (6, 7), False),
    ("follows", (5, 7), (3, 5), True),
    ("follows", (3, 5), (5, 7), False),
    ("overlapped", (6, 8), (5, 7), True),
    ("overlapped", (5, 7), (6, 8), False),
    ("overlapped", (6, 8), (5, 6), False),
    ("overlapped", (5, 6), (6, 8), False),
    ("overlaps", (5, 7), (6, 8), True),
    ("overlaps", (6, 8), (5, 7), False),
    ("overlaps", (5, 6), (6, 8), False),
    ("overlaps", (6, 8), (5, 6), False),
    ("precedes", (5, 7), (7, 9), True),
    ("precedes", (7, 9), (5, 7), False),
    ("started", (5, 7), (5, 6), True),
    ("started", (5, 6), (5, 7), False),
    ("starts", (5, 6), (5, 7), True),
    ("starts", (5, 7), (5, 6), False),
]


@pytest.mark.parametrize(("predicate", "a", "b", "expected"), PREDICATES)
def test_a_predicate_of_two_extents(predicate, a, b, expected):
    first = TemporalExtent(start_time=a[0], end_time=a[1])
    second = TemporalExtent(start_time=b[0], end_time=b[1])

    assert getattr(first, predicate)(second) is expected


# The method, the start and end of the two extents and the start and end of
# the result, None if there is none. Docstring examples like PREDICATES.
COMBINATIONS = [
    ("intersect", (5, 6), (5, 6), (5, 6)),
    ("intersect", (5, 6), (5, 7), (5, 6)),
    ("intersect", (5, 7), (5, 6), (5, 6)),
    ("intersect", (3, 6), (5, 7), (5, 6)),
    ("intersect", (5, 7), (3, 6), (5, 6)),
    ("intersect", (3, 8), (5, 6), (5, 6)),
    ("intersect", (5, 6), (3, 8), (5, 6)),
    ("intersect", (5, 8), (3, 6), (5, 6)),
    ("intersect", (3, 6), (5, 8), (5, 6)),
    ("intersect", (5, None), (3, 6), (5, None)),
    ("intersect", (3, 6), (5, None), (5, None)),
    ("intersect", (5, 8), (3, 4), None),
    ("intersect", (5, 8), (3, None), None),
    ("disjoint_union", (5, 6), (5, 7), (5, 7)),
    ("disjoint_union", (5, 7), (5, 6), (5, 7)),
    ("disjoint_union", (3, 6), (5, 7), (3, 7)),
    ("disjoint_union", (5, 7), (3, 6), (3, 7)),
    ("disjoint_union", (3, 8), (5, 6), (3, 8)),
    ("disjoint_union", (5, 6), (3, 8), (3, 8)),
    ("disjoint_union", (5, 8), (3, 6), (3, 8)),
    ("disjoint_union", (3, 6), (5, 8), (3, 8)),
    ("disjoint_union", (5, None), (3, 6), (3, 6)),
    ("disjoint_union", (3, 6), (5, None), (3, 6)),
    ("disjoint_union", (5, 8), (3, 4), (3, 8)),
    ("disjoint_union", (3, 4), (5, 8), (3, 8)),
    ("disjoint_union", (5, 8), (3, None), (3, 8)),
    ("disjoint_union", (3, None), (5, 8), (3, 8)),
    ("disjoint_union", (5, None), (3, 8), (3, 8)),
    ("disjoint_union", (3, 8), (5, None), (3, 8)),
    ("disjoint_union", (5, None), (3, None), (3, 5)),
    ("disjoint_union", (3, None), (5, None), (3, 5)),
]


@pytest.mark.parametrize(("method", "a", "b", "expected"), COMBINATIONS)
def test_intersection_and_disjoint_union_of_two_extents(method, a, b, expected):
    first = TemporalExtent(start_time=a[0], end_time=a[1])
    second = TemporalExtent(start_time=b[0], end_time=b[1])

    result = getattr(first, method)(second)

    if expected is None:
        assert result is None
    else:
        assert type(result) is TemporalExtent
        assert (result.get_start_time(), result.get_end_time()) == expected


# Equal times of two types (5 and 5.0) show which extent a result takes a
# time from when the times tie. The intersection takes the start of the
# argument and the end of the extent, the disjoint union the start of the
# argument; its end is the end of the extent if both are intervals and the time
# of the argument otherwise.
TIES = [
    ("intersect", (5, 7.0), (5.0, 7), "(5.0, 7.0)"),
    ("intersect", (5.0, 7), (5, 7.0), "(5, 7)"),
    ("intersect", (5, None), (5.0, 7), "(5, None)"),
    ("intersect", (5, 7), (5.0, None), "(5.0, None)"),
    ("disjoint_union", (5, 7.0), (5.0, 7), "(5.0, 7.0)"),
    ("disjoint_union", (5.0, 7), (5, 7.0), "(5, 7)"),
    ("disjoint_union", (5, None), (5.0, None), "(5.0, 5.0)"),
    ("disjoint_union", (5.0, None), (5, None), "(5, 5)"),
    ("disjoint_union", (7, None), (5, 7.0), "(5, 7.0)"),
    ("disjoint_union", (7.0, None), (5, 7), "(5, 7)"),
    ("disjoint_union", (5, 7.0), (7, None), "(5, 7)"),
    ("disjoint_union", (5, 7), (7.0, None), "(5, 7.0)"),
    ("union", (5, 7.0), (5.0, 7), "(5.0, 7.0)"),
]


@pytest.mark.parametrize(("method", "a", "b", "expected"), TIES)
def test_the_time_a_result_takes_when_two_times_tie(method, a, b, expected):
    first = TemporalExtent(start_time=a[0], end_time=a[1])
    second = TemporalExtent(start_time=b[0], end_time=b[1])

    result = getattr(first, method)(second)

    assert repr((result.get_start_time(), result.get_end_time())) == expected


# A row of the temporal database gives the extent class it derives from, with
# the unit in relative time.
ROWS = [
    (
        AbsoluteTimeRow(
            KINDS["raster"],
            start_time=datetime(2001, 1, 1),
            end_time=datetime(2001, 3, 1),
        ),
        AbsoluteTimeRow(
            KINDS["raster"],
            start_time=datetime(2001, 2, 1),
            end_time=datetime(2001, 4, 1),
        ),
        AbsoluteTemporalExtent,
        None,
    ),
    (
        RelativeTimeRow(KINDS["strds"], start_time=1, end_time=3, unit="days"),
        RelativeTimeRow(KINDS["strds"], start_time=2, end_time=4, unit="days"),
        RelativeTemporalExtent,
        "days",
    ),
]


@pytest.mark.parametrize("method", ["intersect", "disjoint_union", "union"])
@pytest.mark.parametrize(("a", "b", "cls", "unit"), ROWS)
def test_a_row_gives_the_extent_class_it_derives_from(method, a, b, cls, unit):
    result = getattr(a, method)(b)

    assert type(result) is cls
    assert result.D.get("unit") == unit


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (
            RelativeTemporalExtent(start_time=5, end_time=None, unit="years"),
            RelativeTemporalExtent(start_time=3, end_time=None, unit="years"),
        ),
        (
            AbsoluteTemporalExtent(
                start_time=datetime(2001, 1, 10), end_time=datetime(2003, 1, 1)
            ),
            AbsoluteTemporalExtent(
                start_time=datetime(2005, 1, 10), end_time=datetime(2008, 1, 1)
            ),
        ),
    ],
)
@pytest.mark.parametrize("swap", [False, True])
def test_the_disjoint_union_keeps_the_class_and_unit(a, b, swap, capsys):
    """Two points give the interval between them, two intervals the span"""
    if swap:
        a, b = b, a
    a.disjoint_union(b).print_info()
    if isinstance(a, RelativeTemporalExtent):
        expected = [
            " +-------------------- Relative time -----------------------------------------+",
            " | Start time:................. 3",
            " | End time:................... 5",
            " | Relative time unit:......... years",
        ]
    else:
        expected = [
            " +-------------------- Absolute time -----------------------------------------+",
            " | Start time:................. 2001-01-10 00:00:00",
            " | End time:................... 2008-01-01 00:00:00",
        ]
    assert capsys.readouterr().out.splitlines() == expected


@pytest.mark.parametrize(
    ("start", "end", "printed", "shell"),
    [
        (
            datetime(2001, 1, 1),
            datetime(2005, 1, 1),
            ["2001-01-01 00:00:00", "2005-01-01 00:00:00"],
            ["start_time='2001-01-01 00:00:00'", "end_time='2005-01-01 00:00:00'"],
        ),
        (0, 1, ["0", "1"], ["start_time='0'", "end_time='1'"]),
    ],
)
def test_the_base_class_by_attribute_and_printed(start, end, printed, shell, capsys):
    extent = TemporalExtent(
        table="raster_absolute_time",
        ident="soil@PERMANENT",
        start_time=start,
        end_time=end,
    )
    assert (extent.id, extent.start_time, extent.end_time) == (
        "soil@PERMANENT",
        start,
        end,
    )

    extent.print_info()
    extent.print_shell_info()
    assert capsys.readouterr().out.splitlines() == [
        f" | Start time:................. {printed[0]}",
        f" | End time:................... {printed[1]}",
        *shell,
    ]


def test_an_absolute_extent_printed(capsys):
    extent = AbsoluteTemporalExtent(
        table="raster_absolute_time",
        ident="soil@PERMANENT",
        start_time=datetime(2001, 1, 1),
        end_time=None,
    )

    extent.print_info()
    extent.print_shell_info()
    assert capsys.readouterr().out.splitlines() == [
        " +-------------------- Absolute time -----------------------------------------+",
        " | Start time:................. 2001-01-01 00:00:00",
        " | End time:................... None",
        "start_time='2001-01-01 00:00:00'",
        "end_time='None'",
    ]


def test_a_relative_extent_by_attribute_and_printed(capsys):
    extent = RelativeTemporalExtent(
        table="raster_relative_time",
        ident="soil@PERMANENT",
        start_time=0,
        end_time=1,
        unit="years",
    )
    assert (extent.id, extent.start_time, extent.end_time, extent.unit) == (
        "soil@PERMANENT",
        0,
        1,
        "years",
    )

    extent.print_info()
    extent.print_shell_info()
    assert capsys.readouterr().out.splitlines() == [
        " +-------------------- Relative time -----------------------------------------+",
        " | Start time:................. 0",
        " | End time:................... 1",
        " | Relative time unit:......... years",
        "start_time='0'",
        "end_time='1'",
        "unit=years",
    ]


def test_the_absolute_time_row_of_a_dataset_by_attribute_and_printed(capsys):
    row = AbsoluteTimeRow(
        KINDS["strds"],
        ident="strds@PERMANENT",
        start_time=datetime(2001, 1, 1),
        end_time=datetime(2005, 1, 1),
        granularity="1 days",
        map_time="interval",
    )
    assert (row.id, row.start_time, row.end_time, row.granularity, row.map_time) == (
        "strds@PERMANENT",
        datetime(2001, 1, 1, 0, 0),
        datetime(2005, 1, 1, 0, 0),
        "1 days",
        "interval",
    )

    row.print_info()
    row.print_shell_info()
    assert capsys.readouterr().out.splitlines() == [
        " +-------------------- Absolute time -----------------------------------------+",
        " | Start time:................. 2001-01-01 00:00:00",
        " | End time:................... 2005-01-01 00:00:00",
        " | Granularity:................ 1 days",
        " | Temporal type of maps:...... interval",
        "start_time='2001-01-01 00:00:00'",
        "end_time='2005-01-01 00:00:00'",
        "granularity='1 days'",
        "map_time=interval",
    ]


def test_the_relative_time_row_of_a_dataset_by_attribute_and_printed(capsys):
    row = RelativeTimeRow(
        KINDS["strds"],
        ident="strds@PERMANENT",
        start_time=0,
        end_time=1,
        unit="years",
        granularity=5,
        map_time="interval",
    )
    assert (
        row.id,
        row.start_time,
        row.end_time,
        row.unit,
        row.granularity,
        row.map_time,
    ) == ("strds@PERMANENT", 0, 1, "years", 5, "interval")

    row.print_info()
    row.print_shell_info()
    assert capsys.readouterr().out.splitlines() == [
        " +-------------------- Relative time -----------------------------------------+",
        " | Start time:................. 0",
        " | End time:................... 1",
        " | Relative time unit:......... years",
        " | Granularity:................ 5",
        " | Temporal type of maps:...... interval",
        "start_time='0'",
        "end_time='1'",
        "unit=years",
        "granularity=5",
        "map_time=interval",
    ]
