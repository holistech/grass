"""Test which levels r.contour takes from step, minlevel and maxlevel"""

import importlib.util
import os
from pathlib import Path

import pytest

import grass.script as gs
from grass.exceptions import CalledModuleError
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


def contour(tools, expression, columns, rows=1, **options):
    """Run r.contour on a one row map and return the levels and the line count

    The levels are read from the attribute table, because a level without a
    line is only listed there. A one row map has no line at all, so a test
    that counts lines needs rows of at least 2.
    """
    tools.g_region(n=rows, s=0, w=0, e=columns, res=1)
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
    # Values 21.29 to 22.47, the manual of t.rast.contour has such a map.
    levels, lines = contour(
        tools,
        "21 + col() * 0.2 + row() * 0.09",
        6,
        rows=3,
        step=1,
        minlevel=24,
        maxlevel=26,
    )

    assert levels == []
    assert lines == 0


def test_a_map_above_maxlevel_gets_no_line(tools):
    # Values 21 to 29
    levels, lines = contour(
        tools, "float(20 + col())", 9, rows=3, minlevel=18, maxlevel=20, step=1
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


def test_a_step_that_would_create_too_many_levels_is_an_error(tools):
    # Measured 2026-11-02: before the check, step=1e-12 on the values 0 to 15
    # ended in a failing G_realloc() of a huge size.
    tools.g_region(n=1, s=0, w=0, e=3, res=1)
    tools.r_mapcalc(expression="m = float(col()) * 7")

    with pytest.raises(Exception, match=r"more than .* contour levels"):
        tools.r_contour(input="m", output="lines", step=1e-12, overwrite=True)


def lines_of_three_rows(tools, expression):
    """Return the level of each vertex of the lines of a map of 3 rows by 4"""
    tools.g_region(n=3, s=0, w=0, e=4, res=1)
    tools.r_mapcalc(expression=f"m = {expression}", overwrite=True)
    tools.r_contour(input="m", output="lines", step=0.1, overwrite=True, quiet=True)
    text = tools.v_out_ascii(input="lines", format="standard", precision=17).text
    rows = iter(text.splitlines())
    lines = []
    for row in rows:
        words = row.split()
        if words and words[0] == "L":
            lines.append([float(next(rows).split()[2]) for _ in range(int(words[1]))])
    return lines


def test_a_level_beyond_the_range_by_rounding_is_clamped_to_the_limit(tools):
    # Values 0 to 0.3. The fourth level is 0 + 3 * 0.1, which is
    # 0.30000000000000004 and lies above the maximum 0.3 by rounding, so
    # no cell value equals it and it got no line. Clamped to the maximum it
    # is the level 0.3 and gets a line, as in a map built with a
    # multiplication, where the maximum is 0.30000000000000004 itself (the
    # last line of that map has this level). The vertices are read with 17
    # digits, the two values differ in the 17th.
    # The first level, 0, lies on the minimum and has a line as well, see
    # r_contour_extreme_levels_test.py.
    lines = lines_of_three_rows(tools, "double(col() - 1) / 10.0")

    product = lines_of_three_rows(tools, "(col() - 1) * 0.1")
    assert len(lines) == len(product)
    assert lines[:3] == product[:3]
    assert product[-1] == [0.1 * 3] * 3
    assert len(lines) == 4
    assert lines[-1] == [0.3] * 3


def test_step_one_tenth_keeps_the_last_level_of_zero_to_one(tools):
    # Values 0 to 1: 11 levels, the last one at the maximum.
    levels, _ = contour(tools, "double(col() - 1) / 10.0", 11, step=0.1)

    assert len(levels) == 11
    assert levels[-1] == 1.0


def test_minlevel_above_maxlevel_gives_an_empty_map(tools):
    # Values 1 to 9. Before 2026-11-02 the old code swapped the limits;
    # from then to 2026-11-04 it gave an empty map without a message. It is
    # now an error that leaves no map behind, see the manual and
    # r_contour_bounds_test.py for the message.
    tools.g_region(n=3, s=0, w=0, e=9, res=1)
    tools.r_mapcalc(expression="m = float(col())")

    with pytest.raises(CalledModuleError, match="greater than"):
        tools.r_contour(input="m", output="lines", step=1, minlevel=7, maxlevel=3)

    assert tools.g_list(type="vector").text.split() == []


@pytest.mark.parametrize("step", ["nan", "inf", "-inf"])
def test_a_step_that_is_not_a_finite_number_is_an_error(tools, step):
    tools.g_region(n=1, s=0, w=0, e=3, res=1)
    tools.r_mapcalc(expression="m = float(col())")

    with pytest.raises(Exception, match="step value is not allowed"):
        tools.r_contour(input="m", output="lines", step=step, overwrite=True)


def test_lines_without_nulls_are_unchanged(session, monkeypatch):
    # The recording was made before r.contour changed, see record_lines.py.
    # record_lines.py calls grass.script without an env, so the session
    # is mirrored into the environment of the process.
    for key, value in session.env.items():
        monkeypatch.setenv(key, value)
    load_recorder().assert_cases_as_recorded()
