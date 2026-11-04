"""Test v.unpack for a pack file of a project with a CRS in a project without one"""

import os
import subprocess
from io import StringIO

import pytest

import grass.script as gs
from grass.tools import Tools


@pytest.fixture
def pack_file(tmp_path):
    """A pack file of a point map that was made in a UTM project"""
    gs.create_project(tmp_path / "utm", crs="EPSG:32632")
    path = tmp_path / "pts.pack"
    with gs.setup.init(tmp_path / "utm", env=os.environ.copy()) as session:
        tools = Tools(session=session)
        tools.v_in_ascii(
            input=StringIO("500000,5000000\n"),
            output="pts",
            separator="comma",
            format="point",
        )
        # Tools would run r.unpack and r.pack for a pack file, so the scripts
        # are started directly.
        gs.run_command("v.pack", input="pts", output=str(path), env=session.env)
    return path


@pytest.fixture
def xy_session(tmp_path):
    """A session in a project without a CRS, which has no PROJ_INFO file"""
    gs.create_project(tmp_path / "xy")
    with gs.setup.init(tmp_path / "xy", env=os.environ.copy()) as session:
        yield session


def _unpack(session, pack_file, **options):
    """Run v.unpack and return the return code and the messages"""
    process = gs.start_command(
        "v.unpack",
        input=str(pack_file),
        output="unpacked",
        env=session.env,
        stderr=subprocess.PIPE,
        **options,
    )
    _, stderr = process.communicate()
    return process.returncode, " ".join(stderr.split())


def test_pack_without_proj_info_into_xy(xy_session, pack_file):
    # The project has no PROJ_INFO to compare the one of the pack file with.
    # The CRS differs, so the flag -o is needed to unpack the map.
    code, text = _unpack(xy_session, pack_file, flags="o")

    assert "Traceback" not in text
    assert code == 0
    assert "Projection information does not match. Proceeding..." in text
    tools = Tools(session=xy_session, consistent_return_value=True)
    assert tools.g_list(type="vector", pattern="unpacked").stdout.split() == [
        "unpacked"
    ]
    assert tools.v_info(map="unpacked", flags="t").keyval["points"] == 1


def test_pack_with_proj_info_into_xy_is_refused_without_o(xy_session, pack_file):
    code, text = _unpack(xy_session, pack_file)

    assert "Traceback" not in text
    assert code != 0
    assert "Coordinate reference system of dataset does not appear to match" in text
    tools = Tools(session=xy_session, consistent_return_value=True)
    assert tools.g_list(type="vector", pattern="unpacked").stdout.strip() == ""


def test_a_project_made_from_the_proj_string_of_the_crs_matches(tmp_path, pack_file):
    # A project made from a PROJ string names its CRS "unknown", the UTM
    # project of the pack file uses the name of the EPSG entry; both are one CRS.
    with gs.setup.init(tmp_path / "utm", env=os.environ.copy()) as source:
        proj4 = gs.read_command(
            "g.proj", flags="p", format="proj4", env=source.env
        ).strip()
    gs.create_project(tmp_path / "same", proj4=proj4)
    with gs.setup.init(tmp_path / "same", env=os.environ.copy()) as session:
        code, text = _unpack(session, pack_file)

    assert (code, "does not match" in text) == (0, False), text
