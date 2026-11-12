"""The ported grouping against the picks of the classic routine it replaced

sample_by_dataset() was the routine the old tool called to group the related
maps per sampler granule. The port groups them with
grass.temporal.related_maps instead, the same functions the tool calls. The
file data/sample_groupings.json holds 20 random scenarios, with random extents
and with maps that share a start time, and for every method list, with and
without the spatial check, the grouping that sample_by_dataset() made, recorded
from the reference implementation on 2026-11-12: the related maps in the same
order per granule, gap granules and empty granules included. A granule or map
is named by its number (the id is the name of the dataset and the number), a
gap granule by None. The file also holds the time stamps, the shuffled numbers
and the boxes of each scenario, so the datasets are rebuilt exactly and no
random generator is involved.

One difference is wanted: the method "start" lists a map of the same time as
the granule, which sample_by_dataset() never did, because it ended "start"
with the relation "EQUALS" that the topology builder never files. For a
method list with "start" the recorded grouping is that of the routine given the
relation names of method_relations(), which it reads as plain names in that
order, "equal" as the relation the builder files.
"""

import json
from pathlib import Path

from grass.temporal.algebra.sources import source
from grass.temporal.related_maps import (
    method_relations,
    related_per_granule,
    with_gaps,
)
from grass.tools import Tools

SCENARIOS = json.loads(
    (Path(__file__).parent / "data" / "sample_groupings.json").read_text()
)
# Every method of G_OPT_T_SAMPLE on its own, a few lists, and the default.
METHODS = [
    ["start"],
    ["during"],
    ["overlap"],
    ["contain"],
    ["equal"],
    ["follows"],
    ["precedes"],
    ["contain", "start"],
    ["precedes", "follows", "overlap"],
    ["during", "overlap", "contain", "equal"],
]


def register(tools, name, spans, numbers, boxes, tmp_path):
    """One strds whose maps have the given day spans; end None is an instant

    The map ids are numbered as given, so that the order of the ids is
    neither the order of the start times nor the order of registration.
    """
    instants, intervals = [], []
    for number, (start, end), box in zip(numbers, spans, boxes, strict=True):
        map_name = f"{name}_{number}"
        tools.g_region(res=10, **box)
        tools.r_mapcalc(expression=f"{map_name} = {number}", overwrite=True)
        stamp = f"2001-01-{start + 1:02d}"
        if end is None:
            instants.append(f"{map_name}|{stamp}")
        else:
            intervals.append(f"{map_name}|{stamp}|2001-01-{end + 1:02d}")
    tools.t_create(
        type="strds",
        output=name,
        temporaltype="absolute",
        title=name,
        description=name,
        overwrite=True,
    )
    # One call per kind of stamp: a file that mixed intervals and instants
    # failed on 2026-10-14 with "End time must be greater than start time" for
    # the instant after an interval. register.py keeps the end time of the
    # previous line for a line without one, which explains it (read, not
    # separately tested).
    for kind, lines in (("instants", instants), ("intervals", intervals)):
        if lines:
            file = tmp_path / f"{name}_{kind}.txt"
            file.write_text("\n".join(lines) + "\n")
            tools.t_register(type="raster", input=name, file=file, overwrite=True)


def number_of(ident):
    """The number of a map id such as name_3@PERMANENT, None for a gap"""
    if ident is None or ident == "None":
        return None
    return int(ident.split("@")[0].rsplit("_", 1)[1])


def tool_grouping(sampler_name, input_name, method, spatial):
    """(granule numbers, related map numbers per granule) from the library
    functions"""
    granules = with_gaps(source(sampler_name, stds_type="strds"))
    rows = related_per_granule(
        granules,
        method_relations(method),
        source(input_name, stds_type="strds"),
        spatial=spatial,
    )
    granule_ids = [number_of(str(slot.origin)) for slot in granules.slots]
    return granule_ids, [
        [number_of(slot.content.ident) for slot in row] for row in rows
    ]


def test_core_groups_as_sample_by_dataset(temporal_module_session, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("t_sample_core_data")
    tools = Tools(session=temporal_module_session)
    for scenario, recorded in enumerate(SCENARIOS):
        sampler_name = f"csamp_{scenario}"
        input_name = f"cinput_{scenario}"
        for name, role in ((sampler_name, "sampler"), (input_name, "input")):
            data = recorded[role]
            register(
                tools,
                name,
                data["spans"],
                data["numbers"],
                data["boxes"],
                tmp_path,
            )
        for method in METHODS:
            for spatial in (False, True):
                expected = recorded["groupings"][f"{'+'.join(method)}|{spatial}"]
                assert list(
                    tool_grouping(sampler_name, input_name, method, spatial)
                ) == (expected), (scenario, method, spatial)


def test_equal_start_times_come_in_map_id_order(
    temporal_module_session, tmp_path_factory
):
    """Three maps start on day 1 and lie in one granule; by end time they
    would be ids 1, 3, 2, and sample_by_dataset() listed them by id

    The random scenarios rarely produce such a tie inside one granule, so
    this case makes sure the order of the ids is compared (checked
    2026-10-14: ordering the ties by end time instead lets the random test
    pass and fails this one).
    """
    tmp_path = tmp_path_factory.mktemp("t_sample_core_ties")
    tools = Tools(session=temporal_module_session)
    box = {"w": 0, "e": 10, "s": 0, "n": 10}
    register(tools, "tsamp", [(0, 6)], [1], [box], tmp_path)
    register(
        tools,
        "tinput",
        [(1, 2), (1, 3), (1, 4)],
        [1, 3, 2],
        [box, box, box],
        tmp_path,
    )
    assert tool_grouping("tsamp", "tinput", ["contain"], False) == ([1], [[1, 2, 3]])
