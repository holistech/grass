"""The sampling of t.rast.mapcalc against the classic sample_by_dataset()

The tool has no switch to the classic algebra, so its choice of the map per
sampler granule must stay that of AbstractSpaceTimeDataset.sample_by_dataset(),
which the classic dataset_mapcalculator used: gap granules skipped, and per
granule the first sample. Both paths get the same random time stamps; the
sampler is always an interval series (sample_by_dataset requires it).

The series have no two maps with the same start time inside one dataset. Where
two partners in the winning relation start at the same time, the classic pick
follows the hit order of the R-tree that builds the topology, which is
undefined, while the tool follows the order of source(). That is a known limit
of the comparison, not a defect, so the generators avoid such ties.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os
import random

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal.algebra.sources import source
from grass.temporal.core import get_tgis_message_interface
from grass.temporal.mapcalc import _method_relation_names, _sample_column

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
CASES = 20


@pytest.fixture(scope="module")
def temporal_session(tmp_path_factory):
    """A session with the temporal database that the map objects need"""
    project = tmp_path_factory.mktemp("mapcalc_sampling") / "project"
    gs.create_project(project)
    with (
        pytest.MonkeyPatch.context() as monkeypatch,
        gs.setup.init(project, env=os.environ.copy()) as session,
    ):
        # tgis reads the session from os.environ, so mirror it for the module.
        for key, value in session.env.items():
            if os.environ.get(key) != value:
                monkeypatch.setenv(key, value)
        gs.run_command("g.gisenv", set="TGIS_USE_CURRENT_MAPSET=1")
        gs.run_command("g.region", s=0, n=10, w=0, e=10, res=1)
        tgis.init()
        yield session


def interval_spans(generator):
    """Two to five non-overlapping intervals in days"""
    spans = []
    time = generator.randint(0, 3)
    for _ in range(generator.randint(2, 5)):
        length = generator.randint(1, 4)
        spans.append((time, time + length))
        time += length + generator.randint(0, 2)
    return spans


def mixed_spans(generator):
    """Two to five non-overlapping intervals and instants in days"""
    spans = []
    time = generator.randint(0, 3)
    for _ in range(generator.randint(2, 5)):
        if generator.random() < 0.4:
            spans.append((time, None))
            time += generator.randint(1, 3)
        else:
            length = generator.randint(1, 4)
            spans.append((time, time + length))
            time += length + generator.randint(0, 2)
    return spans


def overlapping_spans(generator):
    """Three to six intervals that may overlap, with distinct start times, so
    that one granule can have partners in more than one relation"""
    starts = generator.sample(range(12), generator.randint(3, 6))
    return [(start, start + generator.randint(1, 5)) for start in sorted(starts)]


def register(name, spans, prefix):
    """Create one raster per span and register each on its own

    One call per map because t.register does not read a file with mixed
    interval and instant lines reliably (measured 2026-10-14). The library call
    is used instead of the tool because the tool's start-up dominates the run
    time of this test.
    """
    gs.run_command(
        "t.create",
        type="strds",
        temporaltype="relative",
        output=name,
        title="t",
        description="t",
        overwrite=True,
    )
    for i, (start, end) in enumerate(spans, 1):
        mapname = f"{prefix}{i}"
        gs.run_command("r.mapcalc", expression=f"{mapname} = {i}", overwrite=True)
        tgis.register_maps_in_space_time_dataset(
            "raster",
            name,
            maps=mapname,
            start=str(start),
            end=None if end is None else str(end),
            unit="days",
        )
    return tgis.open_old_stds(name, "strds")


def classic_column(input_stds, sampler_stds, method):
    """The first sample per sampler granule, None where no map relates

    Gap granules (id None) are skipped as the classic dataset_mapcalculator
    loop did.
    """
    entries = input_stds.sample_by_dataset(stds=sampler_stds, method=method)
    column = []
    for entry in entries:
        if entry["granule"].get_id() is None:
            continue
        first = entry["samples"][0].get_id()
        column.append(None if first is None else first.split("@")[0])
    return column


def tool_column(sampler_name, input_name, names):
    """The tool's pick per sampler granule for relation names, in that order"""
    first_series = source(sampler_name, stds_type="strds")
    return _sample_column(
        first_series,
        input_name,
        names,
        False,
        None,
        "strds",
        get_tgis_message_interface(),
    )


def make_case(tag, case, generator, input_spans):
    """Register a sampler and an input series and return the dataset objects"""
    sampler = register(f"s{tag}{case}", interval_spans(generator), f"sm{tag}{case}_")
    inp = register(f"i{tag}{case}", input_spans(generator), f"in{tag}{case}_")
    return sampler, inp


@pytest.mark.parametrize(
    ("seed", "input_spans"),
    [(7, interval_spans), (11, mixed_spans), (5, overlapping_spans)],
    ids=["intervals", "intervals-and-instants", "overlapping-intervals"],
)
def test_tool_sampling_matches_sample_by_dataset(temporal_session, seed, input_spans):
    """For every method and random series the tool picks the same first map per
    granule as the classic sample_by_dataset(); None marks a granule without
    a related map on both sides"""
    generator = random.Random(seed)
    compared = 0
    for case in range(CASES):
        sampler, inp = make_case(seed, case, generator, input_spans)
        for method in SINGLE_METHODS + MULTI_METHODS:
            classic = classic_column(inp, sampler, method)
            tool = tool_column(
                sampler.get_name(), inp.get_name(), _method_relation_names(method)
            )
            assert tool == classic, f"seed {seed}, case {case}, method {method}"
            compared += 1
    assert compared == CASES * len(SINGLE_METHODS + MULTI_METHODS)


def test_the_comparison_detects_a_wrong_relation(temporal_session):
    """Negative check: the tool's 'during' against the classic 'contain' must
    differ on some case, so the comparison above is not vacuously true"""
    generator = random.Random(11)
    for case in range(CASES):
        sampler, inp = make_case("n", case, generator, mixed_spans)
        classic = classic_column(inp, sampler, ["contain"])
        tool = tool_column(sampler.get_name(), inp.get_name(), ["during"])
        if tool != classic:
            return
    pytest.fail("a wrong relation went unnoticed")


def test_the_comparison_detects_a_swapped_relation_order(temporal_session):
    """Negative check for the order: the classic order of a multi-method list
    against the swapped order of the tool's names must differ on some case"""
    generator = random.Random(5)
    for case in range(CASES):
        sampler, inp = make_case("o", case, generator, overlapping_spans)
        for method in MULTI_METHODS:
            swapped = list(reversed(_method_relation_names(method)))
            classic = classic_column(inp, sampler, method)
            tool = tool_column(sampler.get_name(), inp.get_name(), swapped)
            if tool != classic:
                return
    pytest.fail("a swapped relation order went unnoticed")
