"""Tests for choose(), where() and merge() of the algebra core"""

import pytest

from grass.temporal.algebra import operations
from grass.temporal.algebra.content import NULL, Call, Const, MapRef
from grass.temporal.algebra.operations import choose, gather, merge, where
from grass.temporal.algebra.relations import equal
from grass.temporal.algebra.series import Series


def ref(name):
    return MapRef(f"{name}@PERMANENT")


def contents(series):
    return [slot.content for slot in series]


@pytest.fixture
def a(make_series):
    return make_series("a", (1, 2), (2, 3), (3, 4), (4, 5))


@pytest.fixture
def n(make_series):
    return make_series("n", (1, 2), (2, 3), (3, 4), (4, 5))


@pytest.fixture
def condition(make_series):
    return make_series("k", (1, 2), (2, 3), (3, 4), (4, 5), values=[1, 0, None, 1])


def test_choose_selects_whole_slots(a, condition):
    assert choose(condition, a).slots == (a.slots[0], a.slots[3])


def test_choose_with_otherwise_and_null(a, n, condition):
    """A null condition chooses neither branch"""
    assert choose(condition, a, n).slots == (a.slots[0], n.slots[1], a.slots[3])


def test_choose_needs_a_scalar_condition(a):
    with pytest.raises(TypeError, match="scalar condition"):
        choose(a > 1, a)


def test_choose_leaves_out_slots_without_a_condition(a, make_series):
    k = make_series("k", (1, 2), (4, 5), values=[1, 1])
    assert choose(k, a).slots == (a.slots[0], a.slots[3])


def test_choose_takes_branches_of_different_time_stamps(a, make_series):
    """Each branch slot is judged by the condition of its own time stamp"""
    y = make_series("y", (6, 7), (7, 8))
    k = make_series(
        "k",
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (6, 7),
        (7, 8),
        values=[1, 0, None, 1, 0, 1],
    )
    assert choose(k, a, y).slots == (a.slots[0], a.slots[3], y.slots[0])
    assert choose(k, a).slots == (a.slots[0], a.slots[3])


def test_choose_works_on_a_condition_made_by_gather(a, make_series):
    """The default missing="drop" of gather() leaves slots without condition"""
    c = make_series("c", (1, 2), (2, 3), (4, 5), values=[1, 0, 1])
    k = gather(a, equal, c, reduce="all", equal_times="pairwise")
    assert [slot.content for slot in k] == [Const(1), Const(0), Const(1)]
    assert choose(k, a).slots == (a.slots[0], a.slots[3])


def test_choose_pairs_conditions_of_one_time_stamp_in_order(make_series):
    m = make_series("m", (1, 2), (1, 2))
    n = make_series("n", (1, 2), (1, 2))
    k = make_series("k", (1, 2), (1, 2), values=[1, 0])
    assert choose(k, m).slots == (m.slots[0],)
    assert choose(k, m, n).slots == (m.slots[0], n.slots[1])


def test_choose_needs_as_many_conditions_as_maps_of_a_time_stamp(make_series):
    m = make_series("m", (1, 2), (1, 2), (1, 2))
    k = make_series("k", (1, 2), (1, 2), values=[1, 0])
    with pytest.raises(ValueError, match="2 conditions with 3 maps of 2001-01-01"):
        choose(k, m)


def test_choose_does_not_mix_temporal_types(a, make_series):
    k = make_series("k", (1, 2), values=[1], unit="days")
    with pytest.raises(ValueError, match="temporal types"):
        choose(k, a)


def test_choose_of_empty_series(a):
    empty = Series(sort="scalar")
    assert choose(empty, Series()).slots == ()
    assert choose(empty, a, Series()).slots == ()
    assert choose(empty, Series(), a).slots == ()


def test_where_chooses_per_cell_and_gives_null_without_else(a):
    assert contents(where(a > 2, a))[0] == Call(
        "if", (Call(">", (ref("a1"), Const(2))), ref("a1"), NULL)
    )
    assert contents(where(a > 2, a, 0))[0] == Call(
        "if", (Call(">", (ref("a1"), Const(2))), ref("a1"), Const(0))
    )


def test_where_lifts_a_scalar_condition(a, condition):
    assert contents(where(condition, a)) == [ref("a1"), NULL, NULL, ref("a4")]


def test_where_agrees_with_choose_on_aligned_series(a, n, condition):
    chosen = choose(condition, a, n)
    per_cell = where(condition, a, n)
    assert [slot.content for slot in per_cell if slot.content != NULL] == [
        slot.content for slot in chosen
    ]


def test_where_needs_then_and_else_of_equal_time(a, make_series):
    b = make_series("b", (1, 3), (3, 5))
    with pytest.raises(ValueError, match="equal time stamps"):
        where(a > 2, a, b)


def test_where_of_empty_series(a):
    assert where(Series(), Series()).slots == ()
    assert where(Series(sort="scalar"), Series(), 0).slots == ()


class Messages:
    def __init__(self):
        self.warnings = []

    def warning(self, message):
        self.warnings.append(message)


@pytest.fixture
def messages(monkeypatch):
    collected = Messages()
    monkeypatch.setattr(operations, "get_tgis_message_interface", lambda: collected)
    return collected


def test_merge_keeps_identical_slots_once_with_a_warning(a, messages):
    assert merge(a, a).slots == a.slots
    assert len(messages.warnings) == 1
    assert "4" in messages.warnings[0]


def test_merge_warns_through_python_before_init(a, monkeypatch):
    monkeypatch.setattr(operations, "get_tgis_message_interface", lambda: None)
    with pytest.warns(UserWarning, match="4 maps") as caught:
        assert merge(a, a).slots == a.slots
    assert caught[0].filename == __file__


def test_merge_keeps_different_maps_of_equal_time(a, n, messages):
    merged = merge(a + 1, a + 2)
    assert len(merged) == 8
    assert merge(a, n).times() == sorted(a.times() + n.times())
    assert messages.warnings == []


def test_merge_needs_series_of_one_sort_and_type(a, make_series):
    with pytest.raises(ValueError, match="sort"):
        merge(a, make_series("s", (1, 2), values=[1]))
    with pytest.raises(ValueError, match="temporal types"):
        merge(a, make_series("r", (1, 2), unit="days"))


def test_merge_of_empty_series(a):
    assert merge(Series(), a).slots == a.slots
    assert merge(Series(), Series()).slots == ()
