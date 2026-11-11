"""Tests that run plan() and materialize() on real datasets

The datasets of grass.temporal.testing.expressions_data are used (raster
and vector).

The tests that need no session are in temporal_algebra_core_plan_options_test.py.
"""

import pytest

import grass.temporal.algebra as ta
from grass.temporal.testing import differential, readback
from grass.tools import Tools


@pytest.fixture(scope="module")
def session(temporal_module_session, tmp_path_factory):
    directory = tmp_path_factory.mktemp("data")
    for kind in ("raster", "vector"):
        differential.prepare(kind, temporal_module_session, directory)
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    return temporal_module_session


def test_an_empty_result_has_absolute_time(session):
    import grass.temporal as tgis

    series = ta.Series((), "raster")
    ta.materialize(series, "EmptyAbsolute", overwrite=True)
    dataset = tgis.open_old_stds("EmptyAbsolute", "strds")
    assert dataset.get_temporal_type() == "absolute"


def test_materialize_runs_a_given_chain(session):
    """A chain from plan() gives the maps that its options give to
    materialize() directly; options of plan() or another dataset name next to
    it contradict it"""
    tools = Tools(session=session, overwrite=True, quiet=True)
    series = ta.source("A") * 2

    def maps():
        return [
            (row, readback.cell_values(tools, row.name))
            for row in readback.list_maps(tools, "strds", "Given")
        ]

    ta.materialize(series, "Given", basename="given", overwrite=True)
    expected = maps()
    assert [row.name for row, _ in expected] == [f"given_{i}" for i in range(4)]
    chain = ta.plan(series, "Given", basename="given")
    ta.materialize(series, "Given", chain=chain, overwrite=True)
    assert maps() == expected
    with pytest.raises(ValueError, match="basename"):
        ta.materialize(series, "Given", chain=chain, basename="other", overwrite=True)
    with pytest.raises(ValueError, match="Other"):
        ta.materialize(series, "Other", chain=chain, overwrite=True)
    assert not stds_exists("Other")


def test_materialize_refuses_a_chain_of_another_map_type(session):
    """A chain planned for raster maps does not run for a vector series of
    the same name, and nothing is written"""
    tools = Tools(session=session, consistent_return_value=True)
    chain = ta.plan(ta.source("A") * 2, "Typed", basename="typed")
    before = readback.inventory(tools)
    with pytest.raises(ValueError, match="strds <Typed>, not the stvds <Typed>"):
        ta.materialize(ta.Series((), "vector"), "Typed", chain=chain, overwrite=True)
    assert readback.inventory(tools) == before


def stds_exists(name, stds_type="strds"):
    import grass.temporal as tgis

    return tgis.dataset_factory(stds_type, f"{name}@PERMANENT").is_in_db()
