"""Test the flags of t.rast.colors

-n, -g, -a, -e, -r, -w and -l. The rules of the file used throughout run from
red at 1 to blue at 90, so the colour of a value follows from its position on
that range:

- linear: the red part falls and the blue part rises with (v - 1) / 89;
- logarithmic (-g and -a): with ln v / ln 90 instead. The table is cut into
  about 100 steps, so the colours of a value are those of the nearest step,
  within 3 of the continuous value in each part.
"""

import math

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

WHITE = ["nv 255:255:255", "default 255:255:255"]


@pytest.fixture
def red_to_blue(tmp_path):
    rules = tmp_path / "rules.txt"
    rules.write_text("1 red\n90 blue\n")
    return str(rules)


def _mix(fraction):
    return (255 * (1 - fraction), 0, 255 * fraction)


def _close(colour, expected, tolerance=3):
    return all(abs(a - b) <= tolerance for a, b in zip(colour, expected, strict=True))


def test_the_n_flag_inverts_the_colours(tools, colored, colour_of, red_to_blue):
    # Without the flag 1 is red and 90 blue; with it the other way round, for
    # both maps (1 is in the first, 90 in the second).
    name, first, second = colored

    tools.t_rast_colors(input=name, rules=red_to_blue, flags="n")

    assert colour_of(first, 1) == (0, 0, 255)
    assert colour_of(second, 90) == (255, 0, 0)


def test_without_the_n_flag_the_colours_follow_the_rules(
    tools, colored, colour_of, red_to_blue
):
    name, first, second = colored

    tools.t_rast_colors(input=name, rules=red_to_blue)

    assert colour_of(first, 1) == (255, 0, 0)
    assert colour_of(second, 90) == (0, 0, 255)


def test_the_n_flag_is_not_shown_by_r_colors_out(tools, colored, table, red_to_blue):
    # r.colors.out prints the same rules with and without -n; the inversion
    # is only in the colour of a value (see the test above). Measured
    # 18.10.2026 with r.colors alone on one map: the same.
    name, first, _ = colored

    tools.t_rast_colors(input=name, rules=red_to_blue, flags="n")

    assert table(first) == ["1 255:0:0", "90 0:0:255", *WHITE]


def test_a_linear_table_has_two_rules(tools, colored, table, red_to_blue):
    name, first, _ = colored

    tools.t_rast_colors(input=name, rules=red_to_blue)

    assert len(table(first)) == 4


@pytest.mark.parametrize("flag", ["g", "a"])
def test_logarithmic_scaling_bends_the_colours(
    tools, colored, colour_of, table, red_to_blue, flag
):
    # The map holds 9 at the nine cells' end: linear its colour is
    # (1 - 8/89) red = 232 and 23 blue; logarithmic ln 9 / ln 90 = 0.488
    # puts it near the middle, 130 and 125.
    name, first, _ = colored

    tools.t_rast_colors(input=name, rules=red_to_blue, flags=flag)

    assert len(table(first)) > 50
    assert colour_of(first, 1) == (255, 0, 0)
    assert _close(colour_of(first, 9), _mix(math.log(9) / math.log(90)))
    assert not _close(colour_of(first, 9), _mix(8 / 89))


def test_logarithmic_absolute_scaling_is_symmetric(
    tools, colored, colour_of, table, red_to_blue
):
    # -a adds the rules for the negative values: -9 has the colour of 9.
    name, first, _ = colored

    tools.t_rast_colors(input=name, rules=red_to_blue, flags="a")

    lines = table(first)
    assert any(line.startswith("-") for line in lines)
    assert _close(colour_of(first, -9), colour_of(first, 9), tolerance=2)


def test_histogram_equalisation_spreads_the_values_evenly(tools, colored, table):
    # The 18 values of the dataset occur once each, so equalisation gives the
    # value of rank k (1 to 18, in ascending order) the grey level
    # 255 (k - 0.5) / 18, within 1 of that. 20 lines: 18 values, null and
    # default.
    name, first, _ = colored

    tools.t_rast_colors(input=name, color="grey", flags="e")

    lines = table(first)
    assert len(lines) == 20
    values = [*range(1, 10), *range(10, 100, 10)]
    for rank, (value, line) in enumerate(zip(values, lines[:-2], strict=True), 1):
        number, colour = line.split()
        assert float(number) == value
        level = int(colour.split(":")[0])
        assert abs(level - 255 * (rank - 0.5) / 18) <= 1, line


def test_the_r_flag_removes_the_colour_table(tools, colored, table, red_to_blue):
    name, first, second = colored
    tools.t_rast_colors(input=name, rules=red_to_blue)
    # The default table of a map without a colour file, for the range of the
    # map: the table a map of the same values gets when it is made.
    tools.r_mapcalc(expression=f"{name}_fresh_a = (row() - 1) * 3 + col()")
    tools.r_mapcalc(expression=f"{name}_fresh_b = ((row() - 1) * 3 + col()) * 10")
    defaults = [table(f"{name}_fresh_a"), table(f"{name}_fresh_b")]
    assert [table(first), table(second)] != defaults

    tools.t_rast_colors(input=name, flags="r")

    assert [table(first), table(second)] == defaults


def test_the_w_flag_writes_to_maps_without_a_table(tools, colored, table):
    name, first, second = colored
    assert len(table(first)) > 100

    tools.t_rast_colors(input=name, color="grey", flags="w")

    assert table(first)[:2] == ["1 0:0:0", "90 255:255:255"]
    assert table(second)[:2] == ["1 0:0:0", "90 255:255:255"]


def test_the_w_flag_keeps_an_existing_table(tools, colored, table, red_to_blue):
    name, first, _ = colored
    tools.t_rast_colors(input=name, rules=red_to_blue)

    with pytest.raises(ToolError) as error:
        tools.t_rast_colors(input=name, color="grey", flags="w")

    text = message(error.value)
    assert f"Color table exists for raster map <{first}@PERMANENT>. Exiting." in text
    assert "Error in r.colors call" in text
    assert table(first) == ["1 255:0:0", "90 0:0:255", *WHITE]


def test_the_w_flag_writes_no_map_if_one_map_has_a_table(tools, colored, table):
    # Only the second map has a table. r.colors checks every map of its list
    # for a table before it writes any and ends with an error at the first it
    # finds (raster/r.colors/edit_colors.c), so the first map, which has none,
    # gets no table either. That is r.colors with a list of maps, which
    # t.rast.colors passes on unchanged.
    name, first, second = colored
    tools.r_colors(map=second, color="grey")
    before = table(first)

    with pytest.raises(ToolError) as error:
        tools.t_rast_colors(input=name, color="viridis", flags="w")

    assert f"Color table exists for raster map <{second}@PERMANENT>" in message(
        error.value
    )
    assert table(first) == before


def test_today_the_l_flag_cannot_be_used(tools, colored):
    # The tool passes the list of maps to r.colors, which does not allow the
    # list of rules together with a map list.
    name, _, _ = colored

    with pytest.raises(ToolError) as error:
        tools.t_rast_colors(input=name, flags="l")

    text = message(error.value)
    assert "Options <map>, <file> and <-l> are mutually exclusive" in text
    assert "Error in r.colors call" in text


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_the_l_flag_lists_the_rules(tools, colored):
    name, _, _ = colored

    result = tools.t_rast_colors(input=name, flags="l")

    assert "viridis" in result.stdout
