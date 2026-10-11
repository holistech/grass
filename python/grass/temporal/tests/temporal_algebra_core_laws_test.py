"""Laws and rules of the algebra core

The laws hold for any series; random series with a fixed seed test them.
The rules pin the semantics of conditions in the Python API: a relation in
a condition reads from the condition map to the conclusion map, a
conclusion map gets one result, and a condition without else gives null.
"""

import datetime
import random

import pytest

import grass.temporal.algebra as ta
from grass.temporal.algebra.content import NULL, Call, Const, MapRef
from grass.temporal.algebra.relations import TEMPORAL_RELATIONS

# Spans (start, end) in days of a slot x that stands in the relation to a
# slot l = (s, e) with e - s >= 3, so that "l relation x" holds. The random
# series alone meet equal, finishes and some other relations rarely or never,
# which would make the laws below hold vacuously for them.
PARTNER = {
    "equal": lambda s, e: (s, e),
    "during": lambda s, e: (s - 1, e + 1),
    "contains": lambda s, e: (s + 1, e - 1),
    "starts": lambda s, e: (s, e + 1),
    "started": lambda s, e: (s, e - 1),
    "finishes": lambda s, e: (s - 1, e),
    "finished": lambda s, e: (s + 1, e),
    "precedes": lambda s, e: (e, e + 1),
    "follows": lambda s, e: (s - 1, s),
    "overlaps": lambda s, e: (s + 1, e + 1),
    "overlapped": lambda s, e: (s - 1, e - 1),
}


def day(number):
    return datetime.datetime(2001, 1, number)


def ref(name):
    return MapRef(f"{name}@PERMANENT")


def contents(series):
    return [slot.content for slot in series]


def random_spans(seed, count=10):
    rng = random.Random(seed)
    spans = []
    for _ in range(count):
        start = rng.randint(2, 24)
        spans.append((start, rng.randint(start + 3, 28)))
    return spans


def related_pair(make_series, name):
    """Return a target and an other series of random slots, the other one with
    two slots that stand in the relation to slots of the target"""
    spans = random_spans(name)
    partners = [PARTNER[name](*span) for span in spans[:2]]
    other = random_spans(name + "x") + partners
    return make_series("t", *spans), make_series("x", *other)


@pytest.fixture
def a(make_series):
    return make_series("a", (1, 2), (2, 3), (3, 4), (4, 5))


@pytest.fixture
def b(make_series):
    return make_series("b", (1, 3), (3, 5))


@pytest.mark.parametrize("name", TEMPORAL_RELATIONS)
def test_select_partitions(make_series, name):
    left, other = related_pair(make_series, name)
    kept = ta.select(left, ta.relation(name), other)
    dropped = ta.select(left, ta.relation(name), other, related=False)
    assert kept.slots
    assert dropped.slots
    assert not set(kept.slots) & set(dropped.slots)
    assert sorted(kept.slots + dropped.slots, key=lambda s: s.extent.sort_key()) == (
        list(left.slots)
    )


@pytest.mark.parametrize("name", TEMPORAL_RELATIONS)
def test_count_against_select(make_series, name):
    target, other = related_pair(make_series, name)
    counted = ta.gather(target, ta.relation(name), other, reduce="count")
    assert counted.slots
    assert counted.times() == ta.select(target, ta.relation(name), other).times()


@pytest.mark.parametrize("name", TEMPORAL_RELATIONS)
def test_gather_needs_only_the_inversely_related(make_series, name):
    target, other = related_pair(make_series, name)
    rel = ta.relation(name)
    narrowed = ta.select(other, ta.inverse(rel), target)
    assert 0 < len(narrowed) < len(other)
    gathered = ta.gather(target, rel, other, reduce="sum")
    assert gathered.slots
    assert gathered.slots == ta.gather(target, rel, narrowed, reduce="sum").slots


def test_apply_commutes_with_retime(a):
    assert (
        ta.retime(a + 1, shift="1 day").slots == (ta.retime(a, shift="1 day") + 1).slots
    )


def test_merge_is_idempotent_and_associative(a, b, make_series, monkeypatch):
    c = make_series("c", (2, 4))
    # Before tgis.init() the duplicate warning goes through Python, after it
    # through the messenger; pin the first so that the test does not depend on
    # which tests ran before.
    monkeypatch.setattr(
        "grass.temporal.algebra.operations.get_tgis_message_interface", lambda: None
    )
    with pytest.warns(UserWarning, match="duplicate"):
        twice = ta.merge(ta.merge(a, b), b)
    assert twice.slots == ta.merge(a, b).slots
    assert ta.merge(ta.merge(a, b), c).slots == ta.merge(a, ta.merge(b, c)).slots


def test_choose_is_a_subset(a, make_series):
    k = make_series("k", (1, 2), (2, 3), (3, 4), (4, 5), values=[1, 0, None, 1])
    assert set(ta.choose(k, a).slots) <= set(a.slots)


def test_where_of_true_is_then(a, make_series):
    n = make_series("n", (1, 2), (2, 3), (3, 4), (4, 5))
    true = make_series("k", (1, 2), (2, 3), (3, 4), (4, 5), values=[1, 1, 1, 1])
    assert ta.where(true, a, n).slots == a.slots


def test_condition_reads_from_condition_to_conclusion(a, make_series):
    """if({contains}, td(B) == 2, A): the maps of A within a map of B whose
    interval is two days long"""
    b = make_series("b", (1, 3), (3, 4))
    condition = ta.timevar(b, "td") == 2
    k = ta.gather(a, ta.inverse(ta.contains), condition, reduce="all", missing="null")
    assert contents(k) == [Const(1), Const(1), NULL, NULL]
    assert ta.choose(k, a).times() == [(day(1), day(2)), (day(2), day(3))]


def test_one_result_per_conclusion_map(a, b):
    """if({during}, A > 1, B): each map of B gets one result, the conditions
    of its maps of A joined with and; false is null without else"""
    k = ta.gather(
        b,
        ta.inverse(ta.during),
        a > 1,
        reduce="all",
        equal_times="pairwise",
        missing="null",
    )
    result = ta.where(k, b)
    assert len(result) == 2
    assert contents(result)[0] == Call(
        "if",
        (
            Call(
                "&&",
                (Call(">", (ref("a1"), Const(1))), Call(">", (ref("a2"), Const(1)))),
            ),
            ref("b1"),
            NULL,
        ),
    )


def test_aggregation_with_or(a, b):
    """if({during,|}, A > 1, B) joins the conditions with or"""
    k = ta.gather(b, ta.inverse(ta.during), a > 1, reduce="any", missing="null")
    assert contents(k)[0].function == "||"


def test_then_and_else_of_a_map_condition_need_equal_time(a, b):
    k = ta.gather(b, ta.inverse(ta.during), a > 1, reduce="all", missing="null")
    with pytest.raises(ValueError, match="equal time stamps"):
        ta.where(k, b, a)


def test_temporal_condition_takes_then_and_else_independently(a, b):
    """if({equal|contains}, start_day(B) > 2, B, A): b2 starts on day 3,
    a1 and a2 lie in b1 (false), a3 and a4 in b2 (true)"""
    rel = ta.inverse(ta.equal | ta.contains)
    condition = ta.timevar(b, "start_day") > 2
    k_then = ta.gather(b, rel, condition, reduce="all", missing="null")
    k_else = ta.gather(a, rel, condition, reduce="all", missing="null")
    result = ta.merge(ta.choose(k_then, b), ta.choose(~k_else, a))
    assert result.times() == [(day(1), day(2)), (day(2), day(3)), (day(3), day(5))]
    assert contents(result) == [ref("a1"), ref("a2"), ref("b2")]
