"""Tests for the parsing of dataset names in open_stds.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import pytest

from grass.exceptions import FatalError
import grass.temporal as tgis
from grass.temporal.open_stds import _parse_id, check_new_stds_name
from grass.temporal.testing.data import insert_old_stds
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools


def test_label_is_split_for_strds():
    assert _parse_id("test.S2_8@m", stds_type="strds") == ("test", "m", "S2_8")


@pytest.mark.parametrize("stds_type", ["str3ds", "raster3d", "stvds", "vector"])
def test_other_types_keep_the_dot(stds_type):
    assert _parse_id("test.S2_8", stds_type=stds_type) == ("test.S2_8", None, None)


@pytest.mark.parametrize("stds_type", ["raster", "rast", "strds"])
def test_parse_id_splits_the_label_for_raster_types(stds_type):
    """Tools reach the dataset with the map type, not only with strds."""
    assert _parse_id("sat.S2_1@m", stds_type) == ("sat", "m", "S2_1")
    assert _parse_id("sat.S2_1", stds_type) == ("sat", None, "S2_1")


@pytest.mark.parametrize("stds_type", ["raster_3d", "raster3d", "vector", "vect"])
def test_parse_id_keeps_the_dot_for_types_without_labels(stds_type):
    assert _parse_id("sat.S2_1@m", stds_type) == ("sat.S2_1", "m", None)


@pytest.mark.parametrize("stds_type", ["raster", "rast", "strds"])
def test_parse_id_rejects_double_dot(project_session, stds_type):
    """A label has no dot of its own."""
    with pytest.raises(FatalError, match="Invalid semantic_label"):
        _parse_id("sat.S2.1", stds_type)


@pytest.fixture
def project_session(tmp_path):
    with temporal_session(tmp_path / "project") as session:
        yield session


def test_old_strds_is_opened_with_its_label(project_session):
    tgis.open_new_stds("test", "strds", "absolute", "t", "d", "mean")
    sp = tgis.open_old_stds("test.S2_8", "strds")
    assert sp.get_name() == "test.S2_8"
    assert sp.get_name(semantic_label=False) == "test"


@pytest.mark.parametrize("stds_type", ["raster", "rast"])
def test_old_raster_dataset_is_opened_with_its_label(project_session, stds_type):
    """The raster tools pass the map type, which reads a label like strds."""
    tgis.open_new_stds("test", "strds", "absolute", "t", "d", "mean")
    sp = tgis.open_old_stds("test.S2_8", stds_type)
    assert sp.get_name() == "test.S2_8"
    assert sp.get_name(semantic_label=False) == "test"


def test_new_raster_dataset_with_dot_can_be_read_again(project_session):
    """A dataset that already has a dot in its name is found again.

    Such a dataset can only be made past the check of new names, here with
    the dataset class directly, as one made by an older release.
    """
    insert_old_stds("a.b")
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


def test_an_existing_dataset_with_a_dot_stays_usable(project_session):
    """A dataset made past the check can be read, listed and removed."""
    mapset = tgis.get_current_mapset()
    insert_old_stds("old.name", "str3ds")

    sp = tgis.open_old_stds("old.name", "str3ds")
    assert sp.get_id() == f"old.name@{mapset}"
    sp.delete()
    assert not tgis.dataset_factory("str3ds", f"old.name@{mapset}").is_in_db()


# A strds is not in this list because t.remove and t.register on a strds with a
# dot in its name are covered by temporal/t.remove/tests/t_remove_label_test.py
# and temporal/t.register/tests/t_register_label_test.py.
@pytest.mark.parametrize("stds_type", ["str3ds", "stvds"])
def test_the_tools_work_on_an_existing_dataset_with_a_dot(project_session, stds_type):
    """t.info and t.remove accept a dataset that was made past the check."""
    mapset = tgis.get_current_mapset()
    insert_old_stds("old.name", stds_type)
    tools = Tools(session=project_session)

    info = tools.t_info(input="old.name", type=stds_type)
    assert "old.name" in info.stdout

    tools.t_remove(inputs="old.name", type=stds_type, flags="f")
    assert not tgis.dataset_factory(stds_type, f"old.name@{mapset}").is_in_db()
