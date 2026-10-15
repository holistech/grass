"""The ported grouping against the library routine it replaced

AbstractSpaceTimeDataset.sample_by_dataset() is the routine the old tool
called to group the related maps per sampler granule. The port groups them
with grass.temporal.related_maps instead, the same functions the tool calls.
This test builds random sampler and input datasets, with random extents and
with maps that share a start time, and checks for every method list, with and
without the spatial check, that those functions list the same related maps in
the same order per granule as sample_by_dataset() - gap granules and empty
granules included. The library routine stays in place for its other callers.
"""

import random

import grass.temporal as tgis
from grass.temporal.algebra.sources import source
from grass.temporal.related_maps import (
    method_relations,
    related_per_granule,
    with_gaps,
)
from grass.tools import Tools

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


def sampler_spans(generator):
    """Consecutive interval spans with occasional gaps, as a sampler has"""
    spans = []
    day = generator.randint(0, 2)
    for _ in range(generator.randint(2, 4)):
        length = generator.randint(1, 3)
        spans.append((day, day + length))
        day += length + generator.choice([0, 0, 1, 2])
    return spans


def input_spans(generator):
    """A mix of instants and intervals, some starting together"""
    spans = []
    day = generator.randint(0, 2)
    for _ in range(generator.randint(1, 6)):
        if spans and generator.random() < 0.25:
            day = spans[-1][0]
        if generator.random() < 0.4:
            spans.append((day, None))
            day += generator.randint(1, 2)
        else:
            length = generator.randint(1, 3)
            spans.append((day, day + length))
            day += length + generator.randint(0, 1)
    return spans


def random_box(generator):
    """West, east, south, north on a coarse grid, so that edges and corners
    of different boxes coincide often, and boxes at the origin occur"""
    west = 10 * generator.randint(0, 3)
    south = 10 * generator.randint(0, 3)
    return {
        "w": west,
        "e": west + 10 * generator.randint(1, 2),
        "s": south,
        "n": south + 10 * generator.randint(1, 2),
    }


def register(tools, name, spans, tmp_path, generator, numbers=None):
    """One strds whose maps have the given day spans; end None is an instant

    The map ids are a shuffled numbering unless numbers gives it, so that the
    order of the ids is neither the order of the start times nor the order
    of registration.
    """
    if numbers is None:
        numbers = list(range(1, len(spans) + 1))
        generator.shuffle(numbers)
    instants, intervals = [], []
    for number, (start, end) in zip(numbers, spans, strict=True):
        map_name = f"{name}_{number}"
        tools.g_region(res=10, **random_box(generator))
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


def tool_grouping(sampler_name, input_name, method, spatial):
    """(granule ids, related map ids per granule) from the library functions"""
    granules = with_gaps(source(sampler_name, stds_type="strds"))
    rows = related_per_granule(
        granules,
        method_relations(method),
        source(input_name, stds_type="strds"),
        spatial=spatial,
    )
    granule_ids = [str(slot.origin) for slot in granules.slots]
    return granule_ids, [[slot.content.ident for slot in row] for row in rows]


def classic_grouping(sampler_name, input_name, method, spatial):
    """The same from sample_by_dataset(); its empty-granule map has id None"""
    sampler = tgis.open_old_stds(f"{sampler_name}@PERMANENT", "strds")
    inp = tgis.open_old_stds(f"{input_name}@PERMANENT", "strds")
    matrix = inp.sample_by_dataset(sampler, list(method), spatial, None)
    granule_ids = [str(entry["granule"].get_id()) for entry in matrix]
    related = [
        [s.get_id() for s in entry["samples"] if s.get_id() is not None]
        for entry in matrix
    ]
    return granule_ids, related


def test_core_groups_as_sample_by_dataset(temporal_module_session, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("t_sample_core_data")
    tools = Tools(session=temporal_module_session)
    generator = random.Random(7)
    for scenario in range(20):
        sampler_name = f"csamp_{scenario}"
        input_name = f"cinput_{scenario}"
        register(tools, sampler_name, sampler_spans(generator), tmp_path, generator)
        register(tools, input_name, input_spans(generator), tmp_path, generator)
        for method in METHODS:
            for spatial in (False, True):
                assert tool_grouping(
                    sampler_name, input_name, method, spatial
                ) == classic_grouping(sampler_name, input_name, method, spatial), (
                    scenario,
                    method,
                    spatial,
                )


def test_equal_start_times_come_in_map_id_order(
    temporal_module_session, tmp_path_factory
):
    """Three maps start on day 1 and lie in one granule; by end time they
    would be ids 1, 3, 2, and sample_by_dataset() lists them by id

    The random scenarios rarely produce such a tie inside one granule, so
    this case makes sure the order of the ids is compared (checked
    2026-10-14: ordering the ties by end time instead lets the random test
    pass and fails this one).
    """
    tmp_path = tmp_path_factory.mktemp("t_sample_core_ties")
    tools = Tools(session=temporal_module_session)
    generator = random.Random(11)
    register(tools, "tsamp", [(0, 6)], tmp_path, generator, numbers=[1])
    register(
        tools,
        "tinput",
        [(1, 2), (1, 3), (1, 4)],
        tmp_path,
        generator,
        numbers=[1, 3, 2],
    )
    expected = (
        ["tsamp_1@PERMANENT"],
        [["tinput_1@PERMANENT", "tinput_2@PERMANENT", "tinput_3@PERMANENT"]],
    )
    assert classic_grouping("tsamp", "tinput", ["contain"], False) == expected
    assert tool_grouping("tsamp", "tinput", ["contain"], False) == expected
