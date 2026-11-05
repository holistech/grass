"""Test that open_old_stds tries the whole name before it splits a label off

A dataset of an older release can have a dot in its name. The name "name.label"
selects the maps of the dataset "name" that carry the label, unless a dataset
of that whole name exists. The whole name wins only within one mapset: the
current mapset is searched first, as in every other lookup.
"""

import subprocess
import sys

import pytest

import grass.script as gs

from grass.exceptions import FatalError
import grass.temporal as tgis
from grass.temporal.testing.session import mapset_session, temporal_session


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


INSERT_IN_OWN_MAPSET = """
import sys
import grass.temporal as tgis
tgis.init()
dataset = tgis.dataset_factory("strds", f"{sys.argv[1]}@{tgis.get_current_mapset()}")
dataset.set_initial_values("absolute", "mean", "t", "d")
dataset.insert()
"""


def test_label_of_current_mapset_wins_over_whole_name_in_search_path(tmp_path):
    """a in the current mapset, a.S2 in "first" of the search path: a with S2

    The dataset of "first" is inserted by a process of its own, which runs in
    that mapset.
    """
    with temporal_session(tmp_path / "project", mapset="second") as session:
        insert("a")
        with mapset_session(session, "first") as first:
            subprocess.run(
                [sys.executable, "-c", INSERT_IN_OWN_MAPSET, "a.S2"],
                env=first.env,
                check=True,
            )
        gs.run_command("g.mapsets", operation="add", mapset="first", env=session.env)

        sp = tgis.open_old_stds("a.S2", "strds")
        whole = tgis.open_old_stds("a.S2@first", "strds")

    assert sp.get_id() == "a@second"
    assert sp.semantic_label == "S2"
    assert whole.get_id() == "a.S2@first"
    assert whole.semantic_label is None


def test_whole_name_in_search_path_wins_over_a_label_without_dataset(tmp_path):
    """Without a dataset a, the name a.S2 opens a.S2 of the search path"""
    with temporal_session(tmp_path / "project", mapset="second") as session:
        with mapset_session(session, "first") as first:
            subprocess.run(
                [sys.executable, "-c", INSERT_IN_OWN_MAPSET, "a.S2"],
                env=first.env,
                check=True,
            )
        gs.run_command("g.mapsets", operation="add", mapset="first", env=session.env)

        sp = tgis.open_old_stds("a.S2", "strds")

    assert sp.get_id() == "a.S2@first"
    assert sp.semantic_label is None
