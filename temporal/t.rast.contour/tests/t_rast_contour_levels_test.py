"""Test the levels of t.rast.contour on a column ramp and a row ramp

See conftest.py for the geometry. The number of lines of a map is the number
of requested levels that lie strictly above its lowest value and not above its
highest; each line is straight (two nodes) and runs across the whole map.

- column ramp (values 1 to 4): a line at level L stands at x = L - 0.5;
- row ramp (values 2, 4, 6, 8 from the top): a line at level L stands at
  y = 4.5 - L / 2.
"""

import pytest

from grass.temporal.testing.readback import list_maps


def _lines(tools, name):
    """(lines, west, east, south, north) of a vector map"""
    box = tools.v_info(map=name, flags="g").keyval
    count = tools.v_info(map=name, flags="t").keyval["lines"]
    # The box of a line is cut from floating point arithmetic (0.500000000000001).
    corners = (round(box[key], 6) for key in ("west", "east", "south", "north"))
    return count, *corners


def _contour(tools, input, prefix, **options):
    tools.t_rast_contour(input=input, output=prefix, basename=prefix, **options)
    return [_lines(tools, row.name) for row in list_maps(tools, "stvds", prefix)]


def test_levels_between_the_values(tools, ramps, prefix):
    # Levels 1.5, 2.5, 3.5: three lines of the column ramp at x = 1, 2, 3. The
    # row ramp starts at 2, so 1.5 gives no line there; 2.5 and 3.5 stand at
    # y = 4.5 - 1.25 = 3.25 and 4.5 - 1.75 = 2.75.
    maps = _contour(tools, ramps, prefix, levels="1.5,2.5,3.5")

    assert maps == [(3, 1.0, 3.0, 0.5, 3.5), (2, 0.5, 3.5, 2.75, 3.25)]


def test_the_lowest_level_of_a_map_has_no_line(tools, ramps, prefix):
    # Levels 1 to 4: the column ramp has lines at 2, 3 and 4 (x = 1.5, 2.5,
    # 3.5), not at 1. The row ramp (2, 4, 6, 8) has lines at 3 (y = 3.0) and
    # 4 (y = 2.5): level 2 is its lowest value.
    maps = _contour(tools, ramps, prefix, levels="1,2,3,4")

    assert maps == [(3, 1.5, 3.5, 0.5, 3.5), (2, 0.5, 3.5, 2.5, 3.0)]


def test_the_highest_level_of_a_map_has_a_line(tools, ramps, prefix):
    # Level 4 of the column ramp is its highest value, at x = 3.5.
    maps = _contour(tools, ramps, prefix, levels="4")

    assert maps[0] == (1, 3.5, 3.5, 0.5, 3.5)


def test_levels_outside_the_values_give_no_line(tools, ramps, prefix):
    result = tools.t_rast_contour(
        input=ramps, output=prefix, basename=prefix, levels="20,30"
    )

    assert list_maps(tools, "stvds", prefix) == []
    assert result.returncode == 0


def test_a_step_uses_the_range_of_each_map(tools, ramps, prefix):
    # Step 1 without limits: the levels are the whole numbers of the range.
    # Column ramp 1 to 4: lines at 2, 3, 4. Row ramp 2 to 8: lines at 3 to 8,
    # six lines at y = 3.0, 2.5, 2.0, 1.5, 1.0 and 0.5.
    maps = _contour(tools, ramps, prefix, step=1)

    assert maps == [(3, 1.5, 3.5, 0.5, 3.5), (6, 0.5, 3.5, 0.5, 3.0)]


def test_a_half_step(tools, ramps, prefix):
    # Column ramp: levels 1.5, 2, 2.5, 3, 3.5, 4 (x = 1.0 to 3.5), six lines.
    # Row ramp: levels 2.5 to 8 in steps of 0.5, eleven lines.
    maps = _contour(tools, ramps, prefix, step=0.5)

    assert maps[0] == (6, 1.0, 3.5, 0.5, 3.5)
    assert maps[1][0] == 12


def test_a_step_of_two(tools, ramps, prefix):
    # Column ramp: levels 2 and 4. Row ramp: levels 4, 6, 8 (2 is the lowest).
    maps = _contour(tools, ramps, prefix, step=2)

    assert maps == [(2, 1.5, 3.5, 0.5, 3.5), (3, 0.5, 3.5, 0.5, 2.5)]


def test_minlevel_and_maxlevel_limit_the_steps(tools, ramps, prefix):
    # Levels 2 and 3: the column ramp has both (x = 1.5 and 2.5); the row ramp
    # has the line at 3 only, 2 being its lowest value.
    maps = _contour(tools, ramps, prefix, step=1, minlevel=2, maxlevel=3)

    assert maps == [(2, 1.5, 2.5, 0.5, 3.5), (1, 0.5, 3.5, 3.0, 3.0)]


def test_minlevel_alone(tools, ramps, prefix):
    maps = _contour(tools, ramps, prefix, step=1, minlevel=3)

    assert maps[0] == (2, 2.5, 3.5, 0.5, 3.5)
    assert maps[1][0] == 6


def test_maxlevel_alone(tools, ramps, prefix):
    maps = _contour(tools, ramps, prefix, step=1, maxlevel=3)

    assert maps == [(2, 1.5, 2.5, 0.5, 3.5), (1, 0.5, 3.5, 3.0, 3.0)]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_levels_win_over_a_step(tools, ramps, prefix):
    # The manual of r.contour: when both are given the list is used and the
    # step is ignored. Level 2 alone is a line at x = 1.5.
    maps = _contour(tools, ramps, prefix, step=1, levels="2")

    assert maps[0] == (1, 1.5, 1.5, 0.5, 3.5)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize(
    ("cut", "lines"),
    [(0, 1), (3, 1), (4, 1), (5, 0)],
)
def test_cut_drops_short_lines(tools, ramps, prefix, cut, lines):
    # The line of level 2 in the column ramp has four points, one for each
    # row, so a minimum of up to four keeps it and five drops it.
    maps = _contour(tools, ramps, prefix, levels="2", cut=cut)

    assert [entry[0] for entry in maps if entry[0]] == ([1] if lines else [])
