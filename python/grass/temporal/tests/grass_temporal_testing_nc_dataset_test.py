# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Tests of the helpers that run manual examples in the North Carolina dataset

The tests that read the dataset fail without it, as the manual tests do: a
missing dataset must never pass unseen. The tests of the guards against a
change of the dataset use a small project made in tmp_path instead, so that
nothing is ever written into the real one.
"""

import os
import sqlite3
from pathlib import Path

import pytest

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.grassdb.create import create_mapset
from grass.temporal.testing import manual_examples as me
from grass.temporal.testing import nc_dataset as nc

pytestmark = pytest.mark.real_io


def write_manual(tmp_path, head, tool="t.x"):
    """Write a manual with one example and the example-project comment head"""
    folder = tmp_path / tool
    folder.mkdir()
    path = folder / f"{tool}.md"
    path.write_text(
        "## DESCRIPTION\n\nText.\n\n## EXAMPLES\n\n"
        f"{head}\n\n### T\n\n"
        '=== "Command line"\n\n    ```sh\n    true\n    ```\n\n'
        '=== "Python (grass.tools)"\n\n    ```python\n    pass\n    ```\n'
    )
    return path


def fake_dataset(tmp_path):
    """Return a small XY project that stands in for the dataset"""
    path = tmp_path / "fake_dataset"
    gs.create_project(path)
    return path


def test_missing_dataset_fails_with_a_message(monkeypatch, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv(nc.VARIABLE, str(empty))
    with pytest.raises(nc.MissingDataset) as error:
        nc.find_dataset()
    message = str(error.value)
    assert nc.VARIABLE in message
    assert nc.DOWNLOAD in message
    assert str(empty) in message
    # pytest reports an AssertionError of a test as a failure, not an error.
    assert isinstance(error.value, AssertionError)


def test_without_variable_and_defaults_the_message_names_the_defaults(
    monkeypatch, tmp_path
):
    monkeypatch.delenv(nc.VARIABLE, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(nc.MissingDataset) as error:
        nc.find_dataset()
    message = str(error.value)
    assert nc.VARIABLE in message
    assert nc.DOWNLOAD in message
    for name in ("nc_spm_08_grass7", "nc_spm_full_v2beta1"):
        assert str(tmp_path / "grassdata" / name) in message


def test_the_variable_comes_before_the_defaults(monkeypatch, tmp_path):
    chosen = fake_dataset(tmp_path)
    home = tmp_path / "home"
    (home / "grassdata").mkdir(parents=True)
    gs.create_project(home / "grassdata" / "nc_spm_08_grass7")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv(nc.VARIABLE, str(chosen))
    assert nc.find_dataset() == chosen


@pytest.mark.parametrize("variable", [None, ""])
def test_without_variable_the_first_default_that_exists_is_taken(
    monkeypatch, tmp_path, variable
):
    if variable is None:
        monkeypatch.delenv(nc.VARIABLE, raising=False)
    else:
        monkeypatch.setenv(nc.VARIABLE, variable)
    monkeypatch.setenv("HOME", str(tmp_path))
    full = tmp_path / "grassdata" / "nc_spm_full_v2beta1"
    gs.create_project(full)
    assert nc.find_dataset() == full
    basic = tmp_path / "grassdata" / "nc_spm_08_grass7"
    gs.create_project(basic)
    assert nc.find_dataset() == basic


def test_project_in_dataset_links_permanent(tmp_path):
    dataset = nc.find_dataset()
    before = nc.snapshot(dataset)
    project = nc.project_in_dataset(dataset, tmp_path / "grassdata")
    assert project == tmp_path / "grassdata" / "nc_spm_08_grass7"
    assert (project / "PERMANENT").is_symlink()
    assert (project / "PERMANENT").resolve() == (dataset / "PERMANENT").resolve()
    create_mapset(project / "start")
    with gs.setup.init(project / "start", env=os.environ.copy()) as session:
        gs.run_command("g.mapset", flags="c", mapset="probe", env=session.env)
        region = gs.parse_command(
            "g.region",
            raster="elev_state_500m",
            res=1000,
            flags="ag",
            env=session.env,
        )
        gs.mapcalc("doubled = 2 * elev_state_500m", env=session.env)
        gs.read_command("v.db.select", map="precip_30ynormals", env=session.env)
    # Measured 2026-11-03 in such a project with g.region -g.
    assert (int(region["rows"]), int(region["cols"])) == (335, 839)
    assert (project / "probe" / "fcell" / "doubled").is_file()
    assert nc.differences(before, nc.snapshot(dataset)) == []


def test_used_data_have_the_recorded_fingerprint():
    dataset = nc.find_dataset()
    assert nc.differences(nc.USED_DATA, nc.fingerprint(dataset)) == [], dataset


def test_fingerprint_sees_a_changed_file_and_a_changed_table(tmp_path):
    """The fingerprint covers file contents, extra files and table rows;
    probed on a copy of the used files and the attribute database, never on
    the dataset"""
    dataset = nc.find_dataset()
    copy = tmp_path / "copy"
    for key in nc.USED_DATA:
        if key.startswith("table:"):
            continue
        target = copy / "PERMANENT" / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((dataset / "PERMANENT" / key).read_bytes())
    database = copy / "PERMANENT" / "sqlite" / "sqlite.db"
    database.parent.mkdir()
    database.write_bytes((dataset / "PERMANENT" / "sqlite" / "sqlite.db").read_bytes())
    assert nc.differences(nc.USED_DATA, nc.fingerprint(copy)) == []

    hist = copy / "PERMANENT" / "hist" / "elev_state_500m"
    hist.write_bytes(hist.read_bytes() + b"x")
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE precip_30ynormals SET jul = 0 WHERE cat = 1")
    connection.close()
    (copy / "PERMANENT" / "colr" / "ncmask_500m").write_text("% 0 1\n")
    assert nc.differences(nc.USED_DATA, nc.fingerprint(copy)) == [
        "new: colr/ncmask_500m",
        "changed: hist/elev_state_500m",
        "changed: table:precip_30ynormals",
    ]


def test_snapshot_sees_new_changed_and_removed_files(tmp_path):
    dataset = fake_dataset(tmp_path)
    permanent = dataset / "PERMANENT"
    before = nc.snapshot(dataset)
    assert "DEFAULT_WIND" in before
    (permanent / "new").write_text("x")
    wind = permanent / "WIND"
    wind.write_text(wind.read_text() + "\n")
    (permanent / "PROJ_UNITS").unlink(missing_ok=True)
    (permanent / "DEFAULT_WIND").rename(permanent / "DEFAULT_WIND.moved")
    after = nc.snapshot(dataset)
    changes = nc.differences(before, after)
    assert "new: new" in changes
    assert "changed: WIND" in changes
    assert "missing: DEFAULT_WIND" in changes
    # The directory changes with every entry that is added or removed.
    assert "changed: ." in changes


def test_snapshot_sees_a_changed_time_of_the_same_size(tmp_path):
    dataset = fake_dataset(tmp_path)
    wind = dataset / "PERMANENT" / "WIND"
    before = nc.snapshot(dataset)
    stat = wind.stat()
    os.utime(wind, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    assert nc.differences(before, nc.snapshot(dataset)) == ["changed: WIND"]


def test_differences_lists_each_key_once_in_order():
    assert nc.differences({"a": 1, "b": 2, "c": 3}, {"b": 2, "c": 4, "d": 5}) == [
        "missing: a",
        "changed: c",
        "new: d",
    ]


def test_the_dataset_keys_of_example_project_are_read(tmp_path):
    head = "<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_x -->"
    parsed = me.parse_manual(write_manual(tmp_path, head))
    assert parsed.project == {"dataset": "nc_spm_08_grass7", "mapset": "t_x"}


def test_unknown_dataset_in_example_project_is_an_error(tmp_path):
    head = "<!-- example-project: dataset=nc_basic_spm_grass7 mapset=t_x -->"
    with pytest.raises(me.ManualFormatError, match="nc_basic_spm_grass7"):
        me.parse_manual(write_manual(tmp_path, head))


@pytest.mark.parametrize(
    ("head", "message"),
    [
        ("dataset=nc_spm_08_grass7", "mapset"),
        ("mapset=t_x", "dataset"),
        ("dataset=nc_spm_08_grass7 mapset=PERMANENT", "PERMANENT"),
        ("dataset=nc_spm_08_grass7 mapset=start", "start"),
        ("dataset=nc_spm_08_grass7 mapset=t_x crs=EPSG:3358", "crs"),
        ("dataset=nc_spm_08_grass7 mapset=t_x mapset=t_y", "twice"),
        ("dataset= mapset=t_x", "dataset"),
        ("location=x", "location"),
    ],
)
def test_invalid_example_project_is_an_error(tmp_path, head, message):
    with pytest.raises(me.ManualFormatError, match=message):
        me.parse_manual(write_manual(tmp_path, f"<!-- example-project: {head} -->"))


def dataset_manual(tmp_path, monkeypatch):
    """A manual with mapset t_x in the fake dataset, which the variable names"""
    dataset = fake_dataset(tmp_path)
    monkeypatch.setenv(nc.VARIABLE, str(dataset))
    head = "<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_x -->"
    return me.parse_manual(write_manual(tmp_path, head)), dataset


def test_example_session_starts_in_mapset_start_of_the_dataset(tmp_path, monkeypatch):
    manual, dataset = dataset_manual(tmp_path, monkeypatch)
    parent = tmp_path / "run"
    with me.example_session(manual, parent) as session:
        gisenv = gs.gisenv(env=session.env)
        project = Path(gisenv["GISDBASE"]) / gisenv["LOCATION_NAME"]
        gs.run_command("g.mapset", flags="c", mapset="t_x", env=session.env)
    assert Path(gisenv["GISDBASE"]) == parent / "grassdata"
    assert gisenv["LOCATION_NAME"] == "nc_spm_08_grass7"
    assert gisenv["MAPSET"] == "start"
    assert (project / "PERMANENT").resolve() == (dataset / "PERMANENT").resolve()


def test_example_session_without_dataset_is_a_new_project(tmp_path):
    head = "<!-- example-project: crs=EPSG:3358 -->"
    manual = me.parse_manual(write_manual(tmp_path, head))
    with me.example_session(manual, tmp_path / "run") as session:
        gisenv = gs.gisenv(env=session.env)
        projection = gs.parse_command("g.proj", flags="g", env=session.env)
    assert Path(gisenv["GISDBASE"]) == tmp_path / "run" / "grassdata"
    assert gisenv["MAPSET"] == "PERMANENT"
    assert projection["srid"] == "EPSG:3358"


# The way an example could change the dataset: g.region -s writes the default
# region in PERMANENT only; in any other mapset it ends with an error (measured
# 2026-11-03 in a mapset of a project linked to a copy of the dataset).
SAVE_DEFAULT_REGION = (
    ("g.mapset", {"mapset": "PERMANENT"}),
    ("g.region", {"flags": "s", "res": 2}),
)


def run_in_session(manual, parent, *commands):
    """Run each (tool, keywords) in the example session of manual"""
    with me.example_session(manual, parent) as session:
        for tool, keywords in commands:
            gs.run_command(tool, env=session.env, **keywords)


def test_example_session_fails_when_the_dataset_changed(tmp_path, monkeypatch):
    manual, _ = dataset_manual(tmp_path, monkeypatch)
    with pytest.raises(AssertionError, match=r"changed: DEFAULT_WIND") as error:
        run_in_session(
            manual,
            tmp_path / "run",
            ("g.mapset", {"flags": "c", "mapset": "t_x"}),
            *SAVE_DEFAULT_REGION,
        )
    assert str(manual.path) in str(error.value)


def test_a_change_of_the_dataset_wins_over_a_failing_block(tmp_path, monkeypatch):
    """A failure after the change must not hide it: the reader lost data"""
    manual, _ = dataset_manual(tmp_path, monkeypatch)
    with pytest.raises(AssertionError, match=r"changed: DEFAULT_WIND") as error:
        run_in_session(
            manual,
            tmp_path / "run",
            *SAVE_DEFAULT_REGION,
            ("g.region", {"raster": "missing"}),
        )
    assert isinstance(error.value.__context__, CalledModuleError)


def test_example_session_fails_when_the_mapset_is_never_made(tmp_path, monkeypatch):
    manual, _ = dataset_manual(tmp_path, monkeypatch)
    with pytest.raises(AssertionError, match=r"mapset <t_x>"):
        run_in_session(
            manual,
            tmp_path / "run",
            ("g.mapset", {"flags": "c", "mapset": "other"}),
        )
