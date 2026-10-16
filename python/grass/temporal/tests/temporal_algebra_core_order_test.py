"""Tests for the sort key and the list order of Series

The expected orders come from the classic algebra, which numbers the result
maps of an expression in the order of its map list. The probe is
ai-analysis/scratch/classic_profile/task11/probe_order.py: it runs the
expression with run_reference() in a session with the datasets of
grass.temporal.testing.expressions_data and prints the result maps by their
number. It ran on 2026-10-16; the series below have the time stamps of the
datasets A, N, AF (daily from 1 January 2001), W (one map, 1 to 5 January),
Z (daily) and E (four instants on 1 January) of that module. Each test
names the expression it follows.
"""

from dataclasses import replace

import pytest

from grass.temporal.algebra.content import Call, MapRef
from grass.temporal.algebra.operations import (
    apply,
    buffer,
    cell_offset,
    choose,
    gather,
    merge,
    pairs,
    select,
    where,
)
from grass.temporal.algebra.relations import relation
from grass.temporal.algebra.series import Series, Space
from grass.temporal.algebra.time_functions import retime, timevar

DAILY = ((1, 2), (2, 3), (3, 4), (4, 5))
NAMES_OF_A = ["a1", "a2", "a3", "a4"]
NAMES_OF_N = ["n1", "n2", "n3", "n4"]


def first_map(content):
    """The first map that a content reads, in the order of the arguments"""
    if isinstance(content, MapRef):
        return content.ident.split("@")[0]
    if isinstance(content, Call):
        for argument in content.args:
            found = first_map(argument)
            if found is not None:
                return found
    return None


def names(slots):
    """The map that each slot reads, which tells the slots apart whatever was
    computed from them"""
    return [first_map(slot.content) for slot in slots]


def in_given_order(make_series, order, *spans):
    """A series whose slots are the maps a1, a2, ... in the order given"""
    slots = [make_series("a", span).slots[0] for span in spans]
    slots = [
        replace(slot, content=MapRef(f"a{number}@PERMANENT"))
        for number, slot in enumerate(slots, start=1)
    ]
    return Series(tuple(slots), order=order)


@pytest.fixture
def datasets(make_series):
    return {
        "A": make_series("a", *DAILY),
        "N": make_series("n", *DAILY),
        "AF": make_series("af", *DAILY),
        "W": make_series("w", (1, 5)),
        "Z": make_series("z", *DAILY),
        "E": make_series("e", 1, 1, 1, 1),
    }


# The default sort key


def test_the_default_key_orders_by_start_then_end(make_series):
    series = in_given_order(make_series, "time", (1, 5), (1, 2))
    assert names(series.slots) == ["a2", "a1"]


def test_the_start_key_orders_by_start_only(make_series):
    series = in_given_order(make_series, "start", (1, 5), (1, 2))
    assert names(series.slots) == ["a1", "a2"]


def test_the_start_key_still_orders_by_start(make_series):
    series = in_given_order(make_series, "start", (3, 4), (1, 5), (1, 2))
    assert names(series.slots) == ["a2", "a3", "a1"]


def test_unknown_order(make_series):
    with pytest.raises(ValueError, match="Unknown order 'end'"):
        replace(make_series("a", (1, 2)), order="end")


# The start key follows the operations. The classic tsnap(merge(W, A)) lists
# the map of W before the first map of A although the map of A ends first
# (reference: maps 0 to 4 are w1, a1, a2, a3, a4).


def test_merge_of_start_ordered_series_keeps_the_start_key(datasets):
    wide, daily = (replace(datasets[key], order="start") for key in ("W", "A"))
    merged = merge(wide, daily)
    assert merged.order == "start"
    assert names(merged.slots) == ["w1", "a1", "a2", "a3", "a4"]
    assert names(merge(datasets["W"], datasets["A"]).slots) == [
        "a1",
        "w1",
        "a2",
        "a3",
        "a4",
    ]


def test_snapped_list_in_start_order(datasets):
    wide, daily = (replace(datasets[key], order="start") for key in ("W", "A"))
    snapped = retime(merge(wide, daily), snap=True)
    assert names(snapped.listed()) == ["w1", "a1", "a2", "a3", "a4"]


@pytest.mark.parametrize(
    "operation",
    [
        lambda s: apply("+", s, 1),
        lambda s: apply("+", s, s),
        lambda s: where(apply(">", s, 1), s),
        lambda s: choose(timevar(s, "td") > 0, s),
        lambda s: retime(s, shift="1 day"),
        lambda s: retime(s, buffer="1 day"),
        lambda s: retime(s, snap=True),
        lambda s: timevar(s, "td"),
        lambda s: gather(s, relation("equal"), s, reduce="first"),
        lambda s: pairs(s, relation("equal"), s),
        lambda s: select(s, relation("equal"), s),
        lambda s: merge(s, apply("+", s, 1)),
    ],
    ids=[
        "number",
        "series",
        "where",
        "choose",
        "shift",
        "buffer",
        "snap",
        "timevar",
        "gather",
        "pairs",
        "select",
        "merge",
    ],
)
def test_the_key_is_kept_by_the_operations(datasets, operation):
    series = replace(datasets["A"], order="start")
    assert operation(series).order == "start"


# The list order of merge()


def test_merge_lists_the_maps_in_written_order(datasets):
    # merge(N, A): maps 0 to 3 are those of N, maps 4 to 7 those of A,
    # whereas the time order interleaves them.
    merged = merge(datasets["N"], datasets["A"])
    assert names(merged.listed()) == NAMES_OF_N + NAMES_OF_A
    assert names(merged.slots) == ["n1", "a1", "n2", "a2", "n3", "a3", "n4", "a4"]


def test_merge_in_the_other_order(datasets):
    merged = merge(datasets["A"], datasets["N"])
    assert names(merged.listed()) == NAMES_OF_A + NAMES_OF_N


def test_a_series_without_merge_is_listed_in_time_order(datasets):
    series = datasets["A"]
    assert series.listed() == series.slots


def test_the_list_order_is_not_part_of_the_identity_of_a_slot(datasets):
    merged = merge(datasets["A"], datasets["N"])
    assert merged.slots[0] == replace(merged.slots[0], rank=None)


def test_nested_merge_lists_the_inner_merge_where_it_was_written(datasets):
    # merge(W, merge(Z, E)): maps 0 to 8 are W, Z (four maps), E (four).
    # In time order the instants of E come first, and the inner list is
    # not in time order either.
    inner = merge(datasets["Z"], datasets["E"])
    merged = merge(datasets["W"], inner)
    expected = ["w1", "z1", "z2", "z3", "z4", "e1", "e2", "e3", "e4"]
    assert names(merged.listed()) == expected
    assert names(merged.slots) != expected


def test_nested_merge_with_the_inner_merge_first(datasets):
    inner = merge(datasets["Z"], datasets["E"])
    merged = merge(inner, datasets["W"])
    expected = ["z1", "z2", "z3", "z4", "e1", "e2", "e3", "e4", "w1"]
    assert names(merged.listed()) == expected


def test_merge_drops_a_duplicate_without_a_gap_in_the_list(datasets):
    with pytest.warns(UserWarning, match="dropped 4 duplicate"):
        merged = merge(datasets["N"], datasets["A"], datasets["N"])
    assert [slot.rank for slot in merged.listed()] == list(range(8))


# The 1:1 operations keep the list order. Each follows a probe of the
# reference with merge(N, A) or merge(N, buff_t(AF, "3 days")).


def test_merge_with_a_buffered_series(datasets):
    # merge(N, buff_t(AF, "3 days")): maps 4 to 7 are those of AF, which
    # begin on 29 December and are listed after those of N although they
    # start first.
    buffered = retime(datasets["AF"], buffer="3 days")
    merged = merge(datasets["N"], buffered)
    assert names(merged.listed()) == NAMES_OF_N + ["af1", "af2", "af3", "af4"]
    assert names(merged.slots)[:4] == ["af1", "af2", "af3", "n1"]


@pytest.mark.parametrize(
    "operation",
    [
        lambda s: apply("+", s, 1),
        lambda s: apply("-", 5, s),
        lambda s: apply("+", s, 2),
        lambda s: apply("abs", s),
        lambda s: apply("neg", s),
        lambda s: where(apply(">", s, 3), 7),
        lambda s: retime(s, shift="1 day"),
        lambda s: retime(s, buffer="1 day"),
        lambda s: retime(s, buffer="-1 hour"),
    ],
    ids=[
        "plus number",
        "number minus",
        "plus number 2",
        "function",
        "negation",
        "if with a number",
        "tshift",
        "buff_t",
        "shrinking buff_t",
    ],
)
def test_one_to_one_operations_keep_the_list(datasets, operation):
    # merge(A, N) - 5, merge(N, A) + 1, abs(merge(N, A)),
    # if(merge(N, A) > 3, 7), tshift(merge(N, A), "1 day") and
    # buff_t(merge(N, A), "1 day") number the maps of N first.
    merged = merge(datasets["N"], datasets["A"])
    assert names(operation(merged).listed()) == NAMES_OF_N + NAMES_OF_A


def test_the_list_is_kept_by_the_cell_offset(datasets):
    # No reference: the grammar of the classic algebra reads an offset of a
    # dataset name only. The offset changes the content of each map and
    # nothing else.
    merged = merge(datasets["N"], datasets["A"])
    shifted = cell_offset(merged, 1, 0)
    assert names(shifted.listed()) == NAMES_OF_N + NAMES_OF_A


def test_the_list_is_kept_by_the_buffer_of_vector_maps(make_series):
    # No reference of the order; the buffer is a function of one series.
    box = Space(10, 0, 10, 0)
    first = make_series("v", (1, 2), (2, 3), kind="vector", space=box)
    second = make_series("u", (1, 2), (2, 3), kind="vector", space=box)
    merged = merge(first, second)
    assert names(buffer(merged, 1.0).listed()) == names(merged.listed())


def test_a_time_variable_keeps_the_list(datasets):
    merged = merge(datasets["N"], datasets["A"])
    listed = timevar(merged, "td").listed()
    assert [slot.rank for slot in listed] == list(range(8))


def test_snap_lists_the_maps_in_time_order(datasets):
    # tsnap(merge(D, A)) is numbered in time order by the classic algebra.
    merged = merge(datasets["N"], datasets["A"])
    snapped = retime(merged, snap=True)
    assert snapped.listed() == snapped.slots
    assert all(slot.rank is None for slot in snapped.slots)


# Operations of two series build a new list in time order. The probes are
# merge(N, A) + merge(A, N), merge(N, A) : A, merge(N, A) {+, equal} A,
# if(merge(N, A) > 3, merge(N, A)) and if(start_day(Z) > 1, merge(N, A)); in
# each of them the result maps 0, 1, ... stand in time order.


def listed_in_time_order(series):
    return all(slot.rank is None for slot in series.slots) and (
        series.listed() == series.slots
    )


def test_an_operation_of_two_series_lists_in_time_order(datasets):
    merged = merge(datasets["N"], datasets["A"])
    other = merge(datasets["A"], datasets["N"])
    assert listed_in_time_order(apply("+", merged, other))


def test_if_of_two_series_lists_in_time_order(datasets):
    merged = merge(datasets["N"], datasets["A"])
    assert listed_in_time_order(where(apply(">", merged, 3), merged))


def test_selection_lists_in_time_order(datasets):
    merged = merge(datasets["N"], datasets["A"])
    selected = select(merged, relation("equal"), datasets["A"])
    assert listed_in_time_order(selected)
    assert names(selected.listed()) == ["n1", "a1", "n2", "a2", "n3", "a3", "n4", "a4"]


def test_selection_with_a_changed_time_lists_in_time_order(datasets):
    merged = merge(datasets["N"], datasets["A"])
    selected = select(merged, relation("equal"), datasets["A"], extent="union")
    assert listed_in_time_order(selected)


def test_gather_lists_in_time_order(datasets):
    merged = merge(datasets["N"], datasets["A"])
    assert listed_in_time_order(
        gather(merged, relation("equal"), datasets["A"], reduce="first")
    )
    kept = gather(
        merged, relation("during"), datasets["A"], reduce="first", missing="keep"
    )
    assert listed_in_time_order(kept)


def test_pairs_lists_in_time_order(datasets):
    merged = merge(datasets["N"], datasets["A"])
    assert listed_in_time_order(pairs(merged, relation("equal"), datasets["A"]))


def test_choose_by_a_timed_condition_lists_in_time_order(datasets):
    merged = merge(datasets["N"], datasets["A"])
    condition = apply(">", timevar(datasets["Z"], "start_day"), 1)
    chosen = choose(condition, merged)
    assert names(chosen.slots) == ["n2", "a2", "n3", "a3", "n4", "a4"]
    assert listed_in_time_order(chosen)


def test_choose_by_a_condition_without_time_keeps_the_list(make_series, datasets):
    # No reference; the condition is no series of maps, so as with a number
    # the list stays.
    merged = merge(datasets["N"], datasets["A"])
    condition = replace(
        make_series("c", (1, 2), values=[True]),
        slots=(replace(make_series("c", (1, 2), values=[True]).slots[0], extent=None),),
    )
    chosen = choose(condition, merged)
    assert names(chosen.listed()) == NAMES_OF_N + NAMES_OF_A
