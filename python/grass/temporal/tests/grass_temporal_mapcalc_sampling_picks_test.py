"""The sampling of t.rast.mapcalc against the picks of the classic routine

The tool has no switch to the classic algebra, so its choice of the map per
sampler granule must stay that of the classic sample_by_dataset(), which the
classic dataset_mapcalculator used: gap granules skipped, and per granule the
first sample. The picks of that routine are in
data/mapcalc_sampling_picks.json, recorded from the reference implementation
on 2026-11-12 for 60 random cases (20 each of three kinds of series) with every
method list, without and with the 2D spatial test. The file holds the time
stamps and boxes of each case, so the series are rebuilt exactly and no random
generator is involved. A pick is the number of the input map, None where no map
relates to the granule. The sampler is always an interval series
(sample_by_dataset requires it).

One difference is wanted: the method "start" selects a map of the same time as
the granule, which the classic routine never did. For a list with "start" the
file holds the pick of the routine given the relation names of
method_relations(), where "equal" is the relation the topology builder files;
"start_plain" holds the pick of the unchanged routine and "equal_first" that
of the method "equal".

The maps have boxes on a small grid, so that disjoint boxes, boxes that share
only an edge or a corner, and overlapping boxes all occur.

The comparison is exact only for series without a tie. Where two partners in
the winning relation start at the same time, the classic pick followed the hit
order of the R-tree that builds the topology, which is undefined, while the
tool takes the map with the lower id. That is a known limit of the comparison,
not a defect. The series here (two to six maps per dataset) avoid such ties by
their distinct start times; a long series would meet ties.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import itertools
import json
from pathlib import Path

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal.algebra.sources import source
from grass.temporal.mapcalc import _sample_column
from grass.temporal.related_maps import method_relations
from grass.temporal.state import get_tgis_message_interface

RECORDED = json.loads(
    (Path(__file__).parent / "data" / "mapcalc_sampling_picks.json").read_text()
)
SEEDS = {"intervals": "7", "mixed": "11", "overlapping": "5"}

SINGLE_METHODS = [
    ["equal"],
    ["during"],
    ["contain"],
    ["overlap"],
    ["follows"],
    ["precedes"],
    ["start"],
]
# The order of the names matters for the map used (the first relation with a
# partner wins), so every pair is given in both orders.
MULTI_METHODS = [
    ["equal", "during"],
    ["during", "equal"],
    ["precedes", "follows"],
    ["follows", "precedes"],
    ["contain", "overlap"],
    ["overlap", "contain"],
    ["start", "equal"],
]


@pytest.fixture(scope="module")
def sampling_session(temporal_module_session):
    """A session with the temporal database that the map objects need"""
    gs.run_command(
        "g.region", s=0, n=10, w=0, e=10, res=1, env=temporal_module_session.env
    )
    return temporal_module_session


def register(session, name, spans, prefix, boxes):
    """Create one raster per span and register each on its own

    The library call registers each map with its own start and end, so
    interval and instant maps mix freely. It is used instead of t.register
    because of the run time: the module took 291 s with one t.register file
    per map and 131 s with this in-process call (pytest --durations,
    2026-10-14).
    """
    gs.run_command(
        "t.create",
        type="strds",
        temporaltype="relative",
        output=name,
        title="t",
        description="t",
        overwrite=True,
        env=session.env,
    )
    for i, ((start, end), (west, south, east, north)) in enumerate(
        zip(spans, boxes, strict=True), 1
    ):
        mapname = f"{prefix}{i}"
        gs.run_command(
            "g.region", w=west, s=south, e=east, n=north, res=1, env=session.env
        )
        gs.run_command(
            "r.mapcalc",
            expression=f"{mapname} = {i}",
            overwrite=True,
            env=session.env,
        )
        tgis.register_maps_in_space_time_dataset(
            "raster",
            name,
            maps=mapname,
            start=str(start),
            end=None if end is None else str(end),
            unit="days",
        )


def tool_column(sampler_name, input_name, names, spatial):
    """The pick of the tool per sampler granule for relation names, in that
    order, as the number of the input map"""
    picks = _sample_column(
        source(sampler_name, stds_type="strds"),
        input_name,
        names,
        spatial,
        None,
        "strds",
        get_tgis_message_interface(),
    )
    return [None if pick is None else int(pick.rsplit("_", 1)[1]) for pick in picks]


def recorded_pick(case, method, spatial):
    """The pick of the classic routine for a method list"""
    return case["picks"][f"{'+'.join(method)}|{spatial}"]


@pytest.fixture(scope="module")
def series(sampling_session):
    """The recorded cases of one seed as datasets, built when first asked for

    Returns a function of the seed that gives number -> (case, sampler,
    input). Building all three seeds at once took 87 s on every pytest-xdist
    worker that ran a test of this module; one seed takes 27 s (pytest -n
    auto --durations on this module alone, 2026-11-12: wall clock 98.5 s
    before, 38.7 s after). A worker that gets every test of the module still
    builds all three.
    """
    made = {}

    def cases_of(seed):
        if seed not in made:
            made[seed] = {}
            for number, case in enumerate(RECORDED[seed]["cases"]):
                sampler = f"s{seed}{number}"
                inp = f"i{seed}{number}"
                register(
                    sampling_session,
                    sampler,
                    case["sampler"],
                    f"sm{seed}{number}_",
                    case["sampler_boxes"],
                )
                register(
                    sampling_session,
                    inp,
                    case["input"],
                    f"in{seed}{number}_",
                    case["input_boxes"],
                )
                made[seed][number] = (case, sampler, inp)
        return made[seed]

    return cases_of


@pytest.mark.parametrize("seed", SEEDS.values(), ids=SEEDS)
def test_tool_sampling_matches_the_recorded_picks(series, seed):
    """For every method and recorded series the tool picks the same first map
    per granule as the classic sample_by_dataset(); None marks a granule
    without a related map on both sides"""
    found_a_pick = False
    for number, (case, sampler, inp) in series(seed).items():
        for method, spatial in itertools.product(
            SINGLE_METHODS + MULTI_METHODS, (False, True)
        ):
            tool = tool_column(sampler, inp, method_relations(method), spatial)
            assert tool == recorded_pick(case, method, spatial), (
                f"seed {seed}, case {number}, method {method}, spatial {spatial}"
            )
            found_a_pick = found_a_pick or any(pick is not None for pick in tool)
    # All columns empty on both sides would make the equality above vacuous.
    assert found_a_pick


def touches_only(first, second):
    """Whether closed boxes meet while their interiors do not"""
    west1, south1, east1, north1 = first
    west2, south2, east2, north2 = second
    closed = west1 <= east2 and west2 <= east1 and south1 <= north2 and south2 <= north1
    open_ = west1 < east2 and west2 < east1 and south1 < north2 and south2 < north1
    return closed and not open_


def test_the_recorded_boxes_include_edge_and_corner_contact():
    """The module docstring promises boxes that share only an edge or corner:
    a sampler map and an input map of one case touching only at an edge or
    corner"""
    assert any(
        touches_only(a, b)
        for kind in RECORDED.values()
        for case in kind["cases"]
        for a in case["sampler_boxes"]
        for b in case["input_boxes"]
    )


def test_the_comparison_detects_a_wrong_relation(series):
    """Negative check: the tool's 'during' against the recorded 'contain' must
    differ on some case, so the comparison above is not vacuously true"""
    for case, sampler, inp in series(SEEDS["mixed"]).values():
        tool = tool_column(sampler, inp, ["during"], False)
        if tool != recorded_pick(case, ["contain"], False):
            return
    pytest.fail("a wrong relation went unnoticed")


def test_the_comparison_detects_a_swapped_relation_order(series):
    """Negative check for the order: the recorded pick of a multi-method list
    against the swapped order of the tool's names must differ on some case"""
    for case, sampler, inp in series(SEEDS["overlapping"]).values():
        for method in MULTI_METHODS:
            swapped = list(reversed(method_relations(method)))
            tool = tool_column(sampler, inp, swapped, False)
            if tool != recorded_pick(case, method, False):
                return
    pytest.fail("a swapped relation order went unnoticed")


def test_the_comparison_detects_a_missing_spatial_test(series):
    """Negative check: the recorded pick without the spatial test against the
    tool's pick with it must differ on some case, so the boxes make the
    spatial half of the comparison able to fail"""
    for case, sampler, inp in series(SEEDS["intervals"]).values():
        for method in SINGLE_METHODS:
            tool = tool_column(sampler, inp, method_relations(method), True)
            if tool != recorded_pick(case, method, False):
                return
    pytest.fail("the spatial test never changed a pick")


def test_start_differs_from_the_classic_routine_only_by_equal_maps():
    """The wanted difference occurs in the recorded cases, and only there

    Where the unchanged classic "start" and the recorded pick of "start"
    differ, the classic routine found no map and the pick is the map of the
    same time as the granule, the one the method "equal" picks.
    """
    differences = 0
    for case in RECORDED[SEEDS["intervals"]]["cases"]:
        new = recorded_pick(case, ["start"], False)
        for old, pick, same_time in zip(
            case["start_plain"], new, case["equal_first"], strict=True
        ):
            if old != pick:
                differences += 1
                assert old is None
                assert pick == same_time
    assert differences
