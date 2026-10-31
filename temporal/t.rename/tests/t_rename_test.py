"""Test t.rename: what a renamed dataset keeps, the name check and the overwrite

The dataset <prefix>_ds holds three maps, map n from day n-1 to day n
(2001-01-01 to 2001-01-04), with the title, description and semantic type set
by the test, so that the tests can tell what the rename keeps.
"""

import sqlite3

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, stds_info
from grass.temporal.testing.session import project_session
from grass.temporal.testing.versions import database_file
from grass.tools import ToolError, Tools

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

TYPES = [("strds", "raster"), ("str3ds", "raster_3d"), ("stvds", "vector")]


def _make(tools, prefix, stds_type="strds", suffix="", temporaltype="absolute"):
    """Create <prefix>_ds<suffix> with three maps; returns its name and the maps"""
    name = f"{prefix}_ds{suffix}"
    if temporaltype == "absolute":
        times = [(day(n), day(n + 1)) for n in range(3)]
    else:
        times = [(n, n + 1) for n in range(3)]
    maps = [
        MapSpec(f"{prefix}{suffix}_{n}", n, start, end)
        for n, (start, end) in enumerate(times, 1)
    ]
    options = {"temporaltype": temporaltype}
    if temporaltype == "relative":
        options["unit"] = "days"
    create_stds(
        tools,
        stds_type,
        name,
        maps,
        title=f"Title of {name}",
        description=f"Description of {name}",
        **options,
    )
    return name, [spec.name for spec in maps]


def _text(tools, stds_type, name):
    """t.info as one line of text, the frame and the line breaks left out

    t.info draws a frame and breaks long lines, so a name or a command is
    found only after the frame characters and the breaks are gone.
    """
    return " ".join(
        tools.t_info(type=stds_type, input=name).stdout.replace("|", " ").split()
    )


def _names(tools, stds_type, name):
    return [row.name for row in list_maps(tools, stds_type, name)]


def test_rename_keeps_the_maps_and_the_metadata(tools, prefix, has_dataset):
    name, maps = _make(tools, prefix)
    new = f"{prefix}_new"

    tools.t_rename(input=name, output=new)

    assert not has_dataset(name)
    assert has_dataset(new)
    assert _names(tools, "strds", new) == maps
    # Three maps of one day each, from 2001-01-01 to 2001-01-04.
    info = stds_info(tools, "strds", new)
    assert info["id"] == f"{new}@PERMANENT"
    assert info["name"] == new
    assert info["number_of_maps"] == 3
    assert info["start_time"] == "'2001-01-01 00:00:00'"
    assert info["end_time"] == "'2001-01-04 00:00:00'"
    assert info["granularity"] == "'1 day'"
    assert info["semantic_type"] == "mean"
    text = _text(tools, "strds", new)
    assert f"Title: Title of {name} " in text
    assert f"Description: Description of {name} " in text


def test_the_command_history_names_t_rename(tools, prefix):
    name, _ = _make(tools, prefix)
    new = f"{prefix}_new"

    tools.t_rename(input=name, output=new)

    history = _text(tools, "strds", new).split("Command history:")[1]
    assert f't.rename input="{name}" output="{new}"' in history


def test_the_maps_know_the_new_name(tools, prefix):
    name, maps = _make(tools, prefix)
    new = f"{prefix}_new"

    tools.t_rename(input=name, output=new)

    text = _text(tools, "raster", maps[0])
    assert f"Registered datasets ........ {new}@PERMANENT" in text
    assert name not in text


def test_the_type_defaults_to_strds(tools, prefix, has_dataset):
    name, _ = _make(tools, prefix)

    tools.t_rename(type="strds", input=name, output=f"{prefix}_a")
    tools.t_rename(input=f"{prefix}_a", output=f"{prefix}_b")

    assert has_dataset(f"{prefix}_b")


@pytest.mark.parametrize(("stds_type", "map_type"), TYPES)
def test_each_dataset_type(tools, prefix, has_dataset, stds_type, map_type):
    name, maps = _make(tools, prefix, stds_type)
    new = f"{prefix}_new"

    tools.t_rename(type=stds_type, input=name, output=new)

    assert not has_dataset(name, stds_type)
    assert _names(tools, stds_type, new) == maps
    assert stds_info(tools, stds_type, new)["number_of_maps"] == 3


def test_a_dataset_of_relative_time(tools, prefix):
    name, maps = _make(tools, prefix, temporaltype="relative")
    new = f"{prefix}_new"

    tools.t_rename(input=name, output=new)

    info = stds_info(tools, "strds", new)
    assert info["temporal_type"] == "relative"
    # Maps [0,1], [1,2], [2,3] days.
    assert (info["start_time"], info["end_time"]) == ("'0'", "'3'")


def test_the_name_can_carry_the_current_mapset(tools, prefix, has_dataset):
    name, _ = _make(tools, prefix)

    tools.t_rename(input=f"{name}@PERMANENT", output=f"{prefix}_new@PERMANENT")

    assert has_dataset(f"{prefix}_new")
    assert not has_dataset(name)


def test_an_older_register_index_follows_the_new_name(tmp_path):
    # Older databases have an index on the id of each register table, named
    # after the table; new ones have none, because SQLite indexes the
    # primary key itself.
    with project_session(tmp_path / "project") as session:
        tools = Tools(session=session, consistent_return_value=True)
        name, _ = _make(tools, "older")
        database = database_file(session)

        def register_indexes():
            with sqlite3.connect(database) as connection:
                (table,) = connection.execute(
                    "SELECT raster_register FROM strds_metadata"
                ).fetchone()
                rows = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index'"
                    " AND tbl_name = ? AND name NOT LIKE 'sqlite_%'",
                    (table,),
                ).fetchall()
            return table, [row[0] for row in rows]

        table, indexes = register_indexes()
        assert indexes == []
        with sqlite3.connect(database) as connection:
            connection.execute(f"CREATE INDEX {table}_index ON {table} (id)")

        tools.t_rename(input=name, output="renamed")

        new_table, indexes = register_indexes()
        assert new_table != table
        assert indexes == [f"{new_table}_index"]


def test_renaming_to_the_same_name_changes_nothing(tools, prefix):
    name, maps = _make(tools, prefix)

    tools.t_rename(input=name, output=name)
    tools.t_rename(input=name, output=f"{name}@PERMANENT")

    assert _names(tools, "strds", name) == maps
    assert "t.rename" not in _text(tools, "strds", name)


def test_an_existing_name_is_refused_without_overwrite(tools, prefix, has_dataset):
    name, maps = _make(tools, prefix)
    other, other_maps = _make(tools, prefix, suffix="2")

    with pytest.raises(
        ToolError, match=r"is\s+in\s+use,\s+please\s+use\s+the\s+overwrite\s+flag"
    ):
        tools.t_rename(input=name, output=other)

    # Neither dataset has changed.
    assert _names(tools, "strds", name) == maps
    assert _names(tools, "strds", other) == other_maps


def test_overwrite_replaces_the_dataset_and_keeps_its_maps(
    tools, prefix, has_dataset, registered
):
    name, maps = _make(tools, prefix)
    other, other_maps = _make(tools, prefix, suffix="2")

    tools.t_rename(input=name, output=other, overwrite=True)

    assert not has_dataset(name)
    assert _names(tools, "strds", other) == maps
    assert f"Description: Description of {name} " in _text(tools, "strds", other)
    # The replaced dataset is gone, its maps are not.
    assert registered(other_maps) == [True] * 3


def test_an_unknown_dataset_is_refused(tools, prefix):
    with pytest.raises(
        ToolError, match=r"Space\s+time\s+raster\s+dataset\s+<nope@PERMANENT>"
    ):
        tools.t_rename(input="nope", output=f"{prefix}_new")


def test_a_dataset_of_another_type_is_not_found(tools, prefix, has_dataset):
    name, _ = _make(tools, prefix)

    with pytest.raises(
        ToolError, match=r"Space\s+time\s+vector\s+dataset\s+<.*>\s+not\s+found"
    ):
        tools.t_rename(type="stvds", input=name, output=f"{prefix}_new")

    assert has_dataset(name)


def test_an_unknown_type_is_refused(tools):
    with pytest.raises(ToolError, match=r"out\s+of\s+range\s+for\s+parameter\s+<type>"):
        tools.t_rename(type="raster", input="a", output="b")
