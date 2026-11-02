"""Test which levels r.contour takes from step, minlevel and maxlevel"""

import importlib.util
import json
import os
from pathlib import Path

import pytest

import grass.script as gs
from grass.tools import Tools

TESTS = Path(__file__).parent


def load_recorder():
    """Import record_lines.py, which pytest does not collect"""
    spec = importlib.util.spec_from_file_location(
        "record_lines", TESTS / "record_lines.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def session(tmp_path):
    """A session in an XY project"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        yield session


@pytest.fixture
def tools(session):
    """Tools in the session"""
    with Tools(session=session, consistent_return_value=True) as tools:
        yield tools


def contour(tools, expression, columns, **options):
    """Run r.contour on a one row map and return the levels and the line count

    The levels are read from the attribute table, because a level without a
    line is only listed there.
    """
    tools.g_region(n=1, s=0, w=0, e=columns, res=1)
    tools.r_mapcalc(expression=f"m = {expression}", overwrite=True)
    tools.r_contour(input="m", output="lines", overwrite=True, quiet=True, **options)
    table = tools.v_db_select(map="lines", columns="level", flags="c").text
    levels = sorted({float(row) for row in table.split()})
    lines = tools.v_info(map="lines", flags="t").keyval["lines"]
    return levels, lines


def test_a_negative_minimum_keeps_the_lowest_level_of_the_step_grid(tools):
    # Values -2.5 to 2.5
    levels, _ = contour(tools, "col() - 3.5", 6, step=2)

    assert levels == [-2, 0, 2]


def test_a_map_below_minlevel_gets_no_line(tools):
    # Values 21 to 23.29, the manual of t.rast.contour has such a map.
    levels, lines = contour(
        tools, "21 + col() * 0.2 + row() * 0.09", 6, step=1, minlevel=24, maxlevel=26
    )

    assert levels == []
    assert lines == 0


def test_a_map_above_maxlevel_gets_no_line(tools):
    # Values 21 to 29
    levels, lines = contour(
        tools, "float(20 + col())", 9, minlevel=18, maxlevel=20, step=1
    )

    assert levels == []
    assert lines == 0


def test_maxlevel_off_the_step_grid_is_no_level(tools):
    levels, _ = contour(
        tools, "float(20 + col())", 9, step=1, minlevel=22, maxlevel=23.5
    )

    assert levels == [22, 23]


def test_minlevel_anchors_the_grid(tools):
    # Values 21 to 25
    levels, _ = contour(tools, "float(20 + col())", 5, step=1, minlevel=22.5)

    assert levels == [22.5, 23.5, 24.5]


def test_only_maxlevel_anchors_at_zero(tools):
    # Values 1 to 9
    levels, _ = contour(tools, "float(col())", 9, step=2, maxlevel=5)

    assert levels == [2, 4]


def test_a_step_of_zero_or_less_is_an_error(tools):
    tools.g_region(n=1, s=0, w=0, e=3, res=1)
    tools.r_mapcalc(expression="m = float(col())")

    for step in (0, -1):
        with pytest.raises(Exception, match="step value is not allowed"):
            tools.r_contour(input="m", output="lines", step=step, overwrite=True)


def test_lines_without_nulls_are_unchanged(session, monkeypatch):
    # The recording was made before r.contour changed, see record_lines.py.
    # record_lines.py calls grass.script without an env, so the session
    # is mirrored into the environment of the process.
    for key, value in session.env.items():
        monkeypatch.setenv(key, value)
    recorder = load_recorder()
    recording = json.loads((TESTS / "data" / "lines_without_nulls.json").read_text())
    made = None
    for case, expected in recording.items():
        name = expected["map"]
        if name != made:
            rows, columns, expression = recorder.MAPS[name]
            gs.run_command("g.region", n=rows, s=0, e=columns, w=0, res=1)
            gs.mapcalc(f"{name} = {expression}", overwrite=True)
            made = name
        got = recorder.record_case(name, expected["arguments"])
        gs.run_command("g.remove", type="vector", name="lines", flags="f", quiet=True)
        assert got["levels"] == pytest.approx(expected["levels"], abs=1e-9), case
        assert got["number_of_lines"] == expected["number_of_lines"], case
        assert got["number_of_nodes"] == expected["number_of_nodes"], case
        assert len(got["lines"]) == len(expected["lines"]), case
        for line, want in zip(got["lines"], expected["lines"], strict=True):
            assert line["level"] == pytest.approx(want["level"], abs=1e-9), case
            assert len(line["vertices"]) == len(want["vertices"]), case
            for vertex, want_vertex in zip(
                line["vertices"], want["vertices"], strict=True
            ):
                assert vertex == pytest.approx(want_vertex, abs=1e-9), case
