"""Sampling with a common granularity: the algebra core against the
classic algebra

The classic algebra samples datasets with
AbstractSpaceTimeDataset.resample_maplist_by_granularity(), and
sample_by_granularity() rebuilds it from the core operations. Both get the
same random time stamps, which have a valid temporal topology, as the
granularity mode requires.
"""

import os
import random

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal.abstract_space_time_dataset import AbstractSpaceTimeDataset
from grass.temporal.algebra.content import MapRef
from grass.temporal.algebra.parser.granularity import sample_by_granularity
from grass.temporal.algebra.series import Extent, Series, Slot


@pytest.fixture(scope="module")
def temporal_session(tmp_path_factory):
    """A session, which the map objects of grass.temporal need"""
    project = tmp_path_factory.mktemp("granularity") / "project"
    gs.create_project(project)
    # tgis reads the session from os.environ, see grass_temporal_gui_support_test
    with (
        pytest.MonkeyPatch.context() as monkeypatch,
        gs.setup.init(project, env=os.environ.copy()) as session,
    ):
        for key, value in session.env.items():
            if os.environ.get(key) != value:
                monkeypatch.setenv(key, value)
        tgis.init()
        yield session


def random_spans(generator):
    """Up to six time stamps in days without overlaps; (start, None) is an
    instant"""
    spans = []
    time = generator.randint(0, 3)
    for _ in range(generator.randint(1, 6)):
        if generator.random() < 0.2:
            spans.append((time, None))
            time += generator.randint(1, 3)
        else:
            length = generator.randint(1, 4)
            spans.append((time, time + length))
            time += length + generator.randint(0, 2)
    return spans


def classic(spans, granularity):
    """The sampled maps of the classic algebra as (id, start, end)"""
    maps = []
    for number, (start, end) in enumerate(spans, start=1):
        map_ = tgis.RasterDataset(f"m{number}@PERMANENT")
        map_.set_relative_time(start, end, "days")
        map_.set_spatial_extent_from_values(3, 0, 3, 0, 1, 0)
        maps.append(map_)
    # The start and end that get_registered_maps_as_objects_by_granularity()
    # passes on
    start = spans[0][0]
    end = spans[-1][0] if spans[-1][1] is None else spans[-1][1]
    if any(span_end is None for _, span_end in spans):
        end += granularity
    entries = AbstractSpaceTimeDataset.resample_maplist_by_granularity(
        maps, start, end, granularity
    )
    return [
        (entry[0].get_id(), *entry[0].get_temporal_extent_as_tuple()[:2])
        for entry in entries or []
        if entry[0].get_id() is not None
    ]


def core(spans, granularity):
    """The sampled maps of the core as (id, start, end)"""
    slots = tuple(
        Slot(
            Extent(start, end, "days"),
            MapRef(f"m{n}@PERMANENT"),
            None,
            f"m{n}@PERMANENT",
        )
        for n, (start, end) in enumerate(spans, start=1)
    )
    sampled = sample_by_granularity(Series(slots), granularity)
    return [
        (slot.content.ident, slot.extent.start, slot.extent.end)
        for slot in sampled.slots
    ]


def test_core_samples_as_the_classic_algebra(temporal_session):
    generator = random.Random(4)
    for _ in range(300):
        spans = random_spans(generator)
        granularity = generator.randint(1, 3)
        assert core(spans, granularity) == classic(spans, granularity), (
            spans,
            granularity,
        )
