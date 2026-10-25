"""Test the registry of dataset types and the entry functions that use it"""

import re
from pathlib import Path

import pytest

import grass.temporal as tgis
from grass.pygrass.messages import FatalError
from grass.temporal import kinds, list_stds

IMAGE = Path(__file__).parent / "recordings" / "database_write.sql"

# Every name an entry function accepted before the registry, and the kind
# it selects as a map or dataset type.
ALIASES = {
    "strds": "strds",
    "str3ds": "str3ds",
    "stvds": "stvds",
    "rast": "raster",
    "raster": "raster",
    "raster_3d": "raster3d",
    "rast3d": "raster3d",
    "raster3d": "raster3d",
    "vect": "vector",
    "vector": "vector",
}
STDS_OF = {
    "strds": "strds",
    "rast": "strds",
    "raster": "strds",
    "str3ds": "str3ds",
    "raster_3d": "str3ds",
    "rast3d": "str3ds",
    "raster3d": "str3ds",
    "stvds": "stvds",
    "vect": "stvds",
    "vector": "stvds",
}


@pytest.fixture(scope="module", autouse=True)
def session(temporal_module_session):
    tgis.init(raise_fatal_error=True)
    return temporal_module_session


@pytest.mark.parametrize(("alias", "name"), ALIASES.items())
def test_alias_selects_kind(alias, name):
    assert kinds.kind_of(alias).name == name
    assert kinds.find_kind(alias) is kinds.KINDS[name]


@pytest.mark.parametrize(("alias", "name"), STDS_OF.items())
def test_stds_kind_of(alias, name):
    assert kinds.stds_kind_of(alias).name == name


def test_the_registry_knows_no_other_name():
    assert set(kinds.KINDS) == {
        "raster",
        "raster3d",
        "vector",
        "strds",
        "str3ds",
        "stvds",
    }
    assert {alias for kind in kinds.KINDS.values() for alias in kind.aliases} == set(
        ALIASES
    )


@pytest.mark.parametrize("name", ["", "raster_2d", "STRDS", "stds", "strd"])
def test_unknown_name(name):
    assert kinds.find_kind(name) is None
    with pytest.raises(ValueError, match="Unknown dataset type"):
        kinds.kind_of(name)
    with pytest.raises(ValueError, match="Unknown dataset type"):
        kinds.stds_kind_of(name)


def test_stds_and_map_kinds_point_at_each_other():
    for kind in kinds.KINDS.values():
        if kind.is_stds:
            assert kinds.KINDS[kind.map_kind].stds_kind == kind.name
            assert kind.ciface_prefix is None
        else:
            assert kinds.KINDS[kind.stds_kind].map_kind == kind.name
            assert hasattr(tgis.CLibrariesInterface, f"read_{kind.ciface_prefix}_info")


def test_the_dataset_classes_name_their_kind():
    for name in kinds.KINDS:
        assert tgis.dataset_factory(name, "x@PERMANENT").get_type() == name


def test_tables_exist_in_the_schema():
    """Every table name is one the SQL templates create (database image)"""
    image = IMAGE.read_text(encoding="utf-8")
    tables = set(re.findall(r"CREATE TABLE (\w+)", image))
    views = set(re.findall(r"CREATE VIEW (\w+)", image))
    for kind in kinds.KINDS.values():
        for part in (
            "base",
            "spatial_extent",
            "absolute_time",
            "relative_time",
            "metadata",
        ):
            assert kind.table(part) in tables, (kind.name, part)
        if kind.is_stds:
            prefix = kind.table("register")
            assert re.search(rf"CREATE TABLE {prefix}_[0-9a-f]{{32}} ", image)
        else:
            assert kind.table("register") in tables
        for part in ("view_abs_time", "view_rel_time"):
            assert kind.table(part) in views, (kind.name, part)


def test_unknown_part():
    with pytest.raises(ValueError, match="Unknown table part"):
        kinds.KINDS["strds"].table("history")


@pytest.mark.parametrize(("alias", "name"), ALIASES.items())
def test_dataset_factory_accepts_every_alias(alias, name):
    assert tgis.dataset_factory(alias, "x@PERMANENT").get_type() == name


def test_dataset_factory_unknown_type_is_an_error_and_none():
    assert tgis.dataset_factory("stds", "x@PERMANENT") is None


def test_open_old_stds_unknown_type():
    with pytest.raises(FatalError, match="Unknown type: stds"):
        tgis.open_old_stds("x", "stds")


def test_check_new_stds_unknown_type():
    assert tgis.check_new_stds("x", "stds") is None


@pytest.mark.parametrize(("alias", "name"), STDS_OF.items())
def test_check_new_stds_takes_every_alias(alias, name):
    assert tgis.check_new_stds("newone", alias).get_type() == name


@pytest.mark.parametrize(("alias", "name"), ALIASES.items())
def test_view_name_follows_the_kind(alias, name):
    prefix = kinds.KINDS[name].table_prefix
    assert list_stds._view_name(alias, "absolute") == f"{prefix}_view_abs_time"
    assert list_stds._view_name(alias, "relative") == f"{prefix}_view_rel_time"


def test_view_name_of_unknown_type_is_left_alone():
    assert list_stds._view_name("nothing", "absolute") == "nothing_view_abs_time"


@pytest.mark.parametrize("alias", ["strds", "rast", "raster"])
def test_open_old_stds_reads_a_map_type_as_its_dataset(alias):
    """open_old_stds() takes "raster" for the strds, as the opening code did"""
    tgis.open_new_stds(
        "kinds_old", "strds", "absolute", "t", "d", "mean", overwrite=True
    )
    assert tgis.open_old_stds("kinds_old", alias).get_type() == "strds"


class _StubMap:
    """A map object with the calls that register_map_object_list() makes"""

    def __init__(self, name, empty):
        self.name = name
        self.empty = empty
        self.metadata = self

    def load(self):
        pass

    def get_min(self):
        return None if self.empty else 1

    get_max = get_min

    def get_number_of_primitives(self):
        return 0 if self.empty else 3

    def get_temporal_extent_as_tuple(self):
        return ("2001-01-01", None)

    def get_id(self):
        return f"{self.name}@PERMANENT"

    def get_name(self):
        # No name: nothing is removed from the mapset by the test
        return None

    def is_in_db(self, dbif):
        return False


@pytest.mark.parametrize("alias", sorted(kinds.MAP_ALIASES))
def test_register_map_object_list_skips_empty_maps_of_every_alias(
    temporal_module_session, monkeypatch, alias
):
    # "raster3d" and "vect" were accepted but their empty maps were registered
    # all the same, because the check compared the type with a list of its own.
    registered = []

    def read_file(type, stds, unit=None, file=None):
        registered.append(Path(file).read_text())

    monkeypatch.setattr(tgis.register, "register_maps_in_space_time_dataset", read_file)
    tgis.init(raise_fatal_error=True)

    tgis.register_map_object_list(
        alias, [_StubMap("full", False), _StubMap("empty", True)], None, True
    )

    assert registered == ["full@PERMANENT|2001-01-01|2001-01-01\n"]
