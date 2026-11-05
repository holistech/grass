"""Test that open_old_stds tries the whole name before it splits a label off

A dataset of an older release can have a dot in its name. The name "name.label"
selects the maps of the dataset "name" that carry the label, unless a dataset
of that whole name exists.
"""

import pytest

from grass.exceptions import FatalError
import grass.temporal as tgis
from grass.temporal.testing.session import temporal_session


@pytest.fixture
def project_session(tmp_path):
    with temporal_session(tmp_path / "project") as session:
        yield session


def insert(name):
    """Insert an empty strds past the check of new names, as an older release did"""
    dataset = tgis.dataset_factory("strds", f"{name}@{tgis.get_current_mapset()}")
    dataset.set_initial_values("absolute", "mean", "t", "d")
    dataset.insert()


@pytest.mark.parametrize("name", ["a.b", "a.b.c", "a.b@{mapset}"])
def test_dataset_with_dot_is_opened_whole(project_session, name):
    insert("a.b.c" if name.startswith("a.b.c") else "a.b")
    sp = tgis.open_old_stds(name.format(mapset=tgis.get_current_mapset()), "strds")
    assert sp.get_name(semantic_label=False) == name.split("@")[0]
    assert sp.semantic_label is None


def test_label_still_selects_the_dataset_without_the_dot(project_session):
    insert("a")
    sp = tgis.open_old_stds("a.S2_8", "strds")
    assert sp.get_name(semantic_label=False) == "a"
    assert sp.semantic_label == "S2_8"


def test_whole_name_wins_over_a_label(project_session):
    insert("a")
    insert("a.S2_8")
    sp = tgis.open_old_stds("a.S2_8", "strds")
    assert sp.get_name(semantic_label=False) == "a.S2_8"
    assert sp.semantic_label is None


def test_missing_dataset_is_still_reported_by_its_name_without_label(project_session):
    with pytest.raises(FatalError, match=r"Space time dataset <nothing> of type"):
        tgis.open_old_stds("nothing.S2_8", "strds")


def test_classic_algebra_still_splits_the_label_first(project_session):
    insert("a")
    insert("a.S2_8")
    sp = tgis.open_old_stds("a.S2_8", "strds", whole_name_first=False)
    assert sp.get_name(semantic_label=False) == "a"
    assert sp.semantic_label == "S2_8"
    insert("b.c")
    with pytest.raises(FatalError, match="not found"):
        tgis.open_old_stds("b.c", "strds", whole_name_first=False)
