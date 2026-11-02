"""Tests for the parsing of dataset names in open_stds.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import pytest

from grass.exceptions import FatalError
import grass.temporal as tgis
from grass.temporal.open_stds import _parse_id, check_new_stds_name
from grass.temporal.testing.session import temporal_session


def test_label_is_split_for_strds():
    assert _parse_id("test.S2_8@m", stds_type="strds") == ("test", "m", "S2_8")


@pytest.mark.parametrize(
    "stds_type", ["raster", "rast", "str3ds", "raster3d", "stvds", "vector"]
)
def test_other_types_keep_the_dot(stds_type):
    assert _parse_id("test.S2_8", stds_type=stds_type) == ("test.S2_8", None, None)


@pytest.fixture
def project_session(tmp_path):
    with temporal_session(tmp_path / "project") as session:
        yield session


def test_new_dataset_with_dot_keeps_its_name(project_session):
    """A dot in the name of a new raster dataset is refused, not kept or split.

    Before a dot was refused, a map type kept the dot in the name while the
    type strds dropped the text after it, so the same name made different
    datasets depending on the tool.
    """
    with pytest.raises(FatalError, match="a dot is not allowed"):
        tgis.open_new_stds("a.b", "raster", "absolute", "t", "d", "mean")
    assert tgis.get_dataset_list("strds", "absolute", columns="name") == {}


def test_old_strds_is_opened_with_its_label(project_session):
    tgis.open_new_stds("test", "strds", "absolute", "t", "d", "mean")
    sp = tgis.open_old_stds("test.S2_8", "strds")
    assert sp.get_name() == "test.S2_8"
    assert sp.get_name(semantic_label=False) == "test"


@pytest.mark.parametrize("stds_type", ["raster", "rast"])
def test_old_raster_dataset_with_dot_is_read_whole(project_session, stds_type):
    """Only the type strds reads a label, so t.register and t.unregister do not.

    A dataset "test" must not be found under the name "test.S2_8".
    """
    tgis.open_new_stds("test", "strds", "absolute", "t", "d", "mean")
    with pytest.raises(FatalError):
        tgis.open_old_stds("test.S2_8", stds_type)


def test_new_raster_dataset_with_dot_can_be_read_again(project_session):
    """A dataset that already has a dot in its name is found again.

    Such a dataset can only be made past the check of new names, here with
    the dataset class directly, as one made by an older release.
    """
    old = tgis.dataset_factory("strds", f"a.b@{tgis.get_current_mapset()}")
    old.set_initial_values("absolute", "mean", "t", "d")
    old.insert()
    sp = tgis.open_old_stds("a.b", "raster")
    assert sp.get_id() == f"a.b@{sp.get_mapset()}"


@pytest.mark.parametrize(
    ("stds_type", "name"),
    [
        ("strds", ".dot"),
        ("raster", ".dot"),
        ("stvds", "a b"),
        ("strds", "a/b"),
        ("strds", "a,b"),
    ],
)
def test_a_name_that_is_not_legal_is_refused(project_session, stds_type, name):
    with pytest.raises(FatalError, match="is not a valid name"):
        tgis.check_new_stds(name, stds_type)


@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds", "raster", "vector"])
@pytest.mark.parametrize("name", ["a.b", "a.b@{mapset}", "a."])
def test_a_dot_in_a_new_name_is_refused(project_session, stds_type, name):
    """No dataset is made and the message names the name as given."""
    name = name.format(mapset=tgis.get_current_mapset())
    with pytest.raises(FatalError, match="a dot is not allowed") as error:
        tgis.open_new_stds(name, stds_type, "absolute", "t", "d", "mean")

    assert f"<{name}>" in str(error.value)
    for kind in ("strds", "str3ds", "stvds"):
        assert tgis.get_dataset_list(kind, "absolute", columns="name") == {}


def test_a_dot_after_the_mapset_is_not_a_dot_in_the_name(project_session):
    """Only the name part before the at sign is checked."""
    check_new_stds_name("ab@a.b")
    check_new_stds_name("ab")


def test_a_label_after_a_dot_still_selects_maps_of_an_existing_dataset(
    project_session,
):
    """Reading is not changed: name.label opens the strds with a label filter."""
    tgis.open_new_stds("test", "strds", "absolute", "t", "d", "mean")
    sp = tgis.open_old_stds("test.S2_8", "strds")
    assert sp.get_name() == "test.S2_8"
    assert sp.get_name(semantic_label=False) == "test"


def test_an_existing_dataset_with_a_dot_stays_usable(project_session):
    """A dataset made past the check can be read, listed and removed."""
    mapset = tgis.get_current_mapset()
    old = tgis.dataset_factory("str3ds", f"old.name@{mapset}")
    old.set_initial_values("absolute", "mean", "t", "d")
    old.insert()

    sp = tgis.open_old_stds("old.name", "str3ds")
    assert sp.get_id() == f"old.name@{mapset}"
    sp.delete()
    assert not tgis.dataset_factory("str3ds", f"old.name@{mapset}").is_in_db()
