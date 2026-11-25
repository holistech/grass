# SPDX-License-Identifier: GPL-2.0-or-later
"""Test which maps each sampling method of t.sample selects for one granule

Each map lists the methods which select it. Interval maps are named after
their relation to the granule as defined by TemporalExtent: the map
"overlapped" (15 to 25 January) is overlapped by the granule (10 to 20
January). The methods are read from the side of the granule, so the method
"overlap" selects both overlapping maps, and "follows" selects the map that
the granule follows.

The method "start" selects every map whose start time lies in the granule,
from its start to its end without the end: the map "overlapped", which starts
inside the granule and ends after it, but not the maps "overlaps" and
"finished", which start before it.
"""

from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.temporal.testing.data import MapSpec, create_stds
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")

METHODS = ("start", "contain", "during", "overlap", "equal", "follows", "precedes")
MAPS = {
    "equal": ((10, 20), {"start", "equal"}),
    "during": ((12, 18), {"start", "contain"}),
    "contains": ((5, 25), {"during"}),
    "starts": ((10, 15), {"start", "contain"}),
    "started": ((10, 25), {"start", "during"}),
    "finishes": ((15, 20), {"start", "contain"}),
    "finished": ((5, 20), {"during"}),
    "overlaps": ((5, 15), {"overlap"}),
    "overlapped": ((15, 25), {"start", "overlap"}),
    "precedes": ((1, 10), {"follows"}),
    "follows": ((20, 30), {"precedes"}),
    "before": ((1, 5), set()),
    "after": ((25, 30), set()),
    "instance_before": ((5, None), set()),
    "instance_at_start": ((10, None), {"start", "contain"}),
    "instance_inside": ((12, None), {"start", "contain"}),
    "instance_at_end": ((20, None), {"precedes"}),
    "instance_after": ((25, None), set()),
}


def january(day):
    return datetime(2001, 1, day)


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    """Tools in the session of the module, with the sampler and the input

    The sampler "sampler" has the one granule 10 to 20 January 2001, the
    input "sampled" the maps of MAPS.
    """
    tools = Tools(session=temporal_module_session)
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    create_stds(
        tools,
        "strds",
        "sampler",
        [MapSpec("granule", 1, january(10), january(20))],
    )
    create_stds(
        tools,
        "strds",
        "sampled",
        [
            MapSpec(name, 1, january(start), january(end) if end else None)
            for name, ((start, end), _) in MAPS.items()
        ],
    )
    return tools


def listed_maps(tools, method):
    """The names of the maps that t.sample lists for the granule, in order"""
    (row,) = tools.t_sample(
        inputs="sampled", sample="sampler", method=method
    ).text.splitlines()
    cell = row.split("|")[1]
    if cell == "None":
        return []
    return [ident.removesuffix("@PERMANENT") for ident in cell.split(",")]


@pytest.fixture(scope="module")
def selected(tools):
    """The set of names that t.sample lists for each method"""
    return {method: set(listed_maps(tools, method)) for method in METHODS}


@pytest.mark.parametrize("name", MAPS)
def test_sampling_methods(selected, name):
    """Check which sampling methods select the map for the granule."""
    methods = {method for method in METHODS if name in selected[method]}
    assert methods == MAPS[name][1]


@pytest.mark.parametrize("method", METHODS)
def test_python_api_selects_the_same_maps(tools, method):
    """sample_stds_by_stds_topology() selects the maps of MAPS for a method"""
    (matrix,) = tgis.sample_stds_by_stds_topology(
        "strds",
        "strds",
        "sampled",
        "sampler",
        header=False,
        separator="|",
        method=method,
        print_only=False,
    )
    (entry,) = matrix
    names = {
        sample.get_name() for sample in entry["samples"] if sample.get_id() is not None
    }
    assert names == {name for name, (_, methods) in MAPS.items() if method in methods}


def test_start_with_during_lists_each_map_once(tools):
    """start,during lists the union of both methods, each map once

    The maps come relation by relation in the order of method_relations():
    the plain name "during" first, then the relations of "start" (starts,
    started, contains, equal, overlaps, read from the granule). Within a
    relation they come by start time, then by name. "during" gives the maps
    the granule lies in: contains and finished (from the 5th) and started
    (from the 10th). "starts" gives started again, "started" gives starts.
    "contains" gives the maps in the granule, which include the ones that
    start or end with it: instance_at_start and starts (the 10th, starts
    already listed), during and instance_inside (the 12th) and finishes (the
    15th). Then equal, and overlapped, which the granule overlaps.
    """
    assert listed_maps(tools, "start,during") == [
        "contains",
        "finished",
        "started",
        "starts",
        "instance_at_start",
        "during",
        "instance_inside",
        "finishes",
        "equal",
        "overlapped",
    ]
