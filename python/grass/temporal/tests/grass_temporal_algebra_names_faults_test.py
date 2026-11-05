"""Test how the algebra core finds datasets and names its result maps

source() looks for a dataset name without a mapset in the current mapset and
then in the search path, unless search_path=False, which the classic profile
passes. plan() pads numbered names to the given digits, and materialize()
numbers only the maps it registers unless number_registered=False, which the
classic profile passes: a map without valid cells, which is not registered,
leaves no gap in the numbers.
"""

import datetime

import pytest

import grass.temporal as tgis
from grass.exceptions import FatalError
from grass.temporal import algebra as ta
from grass.temporal.algebra.materialize import plan
from grass.temporal.algebra.parser.classic import CLASSIC
from grass.temporal.algebra.profile import CORE
from grass.temporal.testing.data import create_daily_stds
from grass.temporal.testing.session import mapset_session
from grass.tools import Tools


@pytest.fixture(scope="module")
def core_session(temporal_module_session):
    """The dataset A of four daily maps with the values 1 to 4 in the current
    mapset, and the dataset O of two maps in the mapset "other", which is in
    the search path"""
    session = temporal_module_session
    tools = Tools(session=session)
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    create_daily_stds(tools, "strds", ["A"], 4, map_prefix="a")
    with mapset_session(session, "other") as other:
        other_tools = Tools(session=other)
        other_tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_daily_stds(other_tools, "strds", ["O"], 2, map_prefix="o")
    tools.g_mapsets(operation="add", mapset="other")
    return session


def names(dataset):
    """The names of the registered maps of a dataset, in time order"""
    return [
        map_.get_name()
        for map_ in tgis.open_old_stds(dataset, "strds").get_registered_maps_as_objects(
            order="start_time"
        )
    ]


def test_profiles_differ_in_the_rules_for_names(core_session):
    assert (CORE.search_path, CORE.suffix_digits, CORE.number_registered) == (
        True,
        True,
        True,
    )
    assert (CLASSIC.search_path, CLASSIC.suffix_digits, CLASSIC.number_registered) == (
        False,
        False,
        False,
    )


def test_source_finds_a_dataset_in_the_search_path(core_session):
    assert [slot.origin for slot in ta.source("O")] == ["o_1@other", "o_2@other"]


def test_source_finds_a_dataset_with_a_label_in_the_search_path(core_session):
    # O holds no map with the label, so the label selects none of its maps;
    # a dataset that was not found would be an error.
    assert ta.source("O.label").slots == ()


def test_source_without_search_path_looks_in_the_current_mapset_only(core_session):
    with pytest.raises(FatalError, match=r"<O@PERMANENT> not found"):
        ta.source("O", search_path=False)


def test_source_of_a_dataset_in_no_mapset_names_the_current_mapset(core_session):
    with pytest.raises(FatalError, match=r"<missing@PERMANENT> not found"):
        ta.source("missing")


def test_plan_pads_numbers_to_the_digits(core_session):
    chain = plan(ta.source("A") * 2, "D", basename="d", digits=3)
    assert [planned.name for planned in chain.maps] == [
        "d_000",
        "d_001",
        "d_002",
        "d_003",
    ]


@pytest.mark.parametrize(
    ("options", "renumber"),
    [
        ({}, True),
        ({"number_registered": False}, False),
        ({"time_suffix": "time"}, False),
        ({"names": ["w", "x", "y", "z"]}, False),
    ],
    ids=["numbered", "keep planned names", "time suffix", "given names"],
)
def test_plan_numbers_registered_maps_only_for_numbered_names(
    core_session, options, renumber
):
    chain = plan(ta.source("A") * 2, "D", basename="d", **options)
    assert chain.renumber is renumber


def test_materialize_numbers_only_registered_maps(core_session):
    a = ta.source("A")
    ta.materialize(ta.where(a > 2, a, None), "HIGH", basename="high")
    assert names("HIGH") == ["high_0", "high_1"]
    assert Tools(session=core_session).g_list(
        type="raster", pattern="high_*"
    ).text.split() == ["high_0", "high_1"]


def test_materialize_keeps_the_gap_without_number_registered(core_session):
    a = ta.source("A")
    ta.materialize(
        ta.where(a > 2, a, None), "GAP", basename="gap", number_registered=False
    )
    assert names("GAP") == ["gap_2", "gap_3"]


def test_overwriting_renumbers_and_forgets_the_old_maps(core_session):
    a = ta.source("A")
    condition = ta.where(a > 2, a, None)
    ta.materialize(condition, "OVR", basename="ovr", register_null=True)
    assert names("OVR") == ["ovr_0", "ovr_1", "ovr_2", "ovr_3"]

    ta.materialize(condition, "OVR", basename="ovr", overwrite=True)

    assert names("OVR") == ["ovr_0", "ovr_1"]
    starts = [
        map_.get_temporal_extent_as_tuple()[0]
        for map_ in tgis.open_old_stds("OVR", "strds").get_registered_maps_as_objects(
            order="start_time"
        )
    ]
    assert starts == [datetime.datetime(2001, 1, 3), datetime.datetime(2001, 1, 4)]
    # The names of the run before that are no longer used have no entry in
    # the temporal database and no map.
    for name in ("ovr_2", "ovr_3"):
        assert not tgis.RasterDataset(f"{name}@PERMANENT").is_in_db()
    assert Tools(session=core_session).g_list(
        type="raster", pattern="ovr_*"
    ).text.split() == ["ovr_0", "ovr_1"]
