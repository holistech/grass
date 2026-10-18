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

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
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


def test_the_w_flag_keeps_the_tables_that_exist(tools, colored, table, red_to_blue):
    name, first, _ = colored
    tools.t_rast_colors(input=name, rules=red_to_blue)

    # Both maps have a table now: nothing is left to write, and no error.
    result = tools.t_rast_colors(input=name, color="grey", flags="w")

    assert result.returncode == 0
    assert table(first) == ["1 255:0:0", "90 0:0:255", *WHITE]


def test_the_w_flag_writes_to_the_maps_without_a_table_only(tools, prefix, table):
    # Changed on 18.10.2026: r.colors with -w stops at the first map that has
    # a table and writes none, so the tool leaves such maps out of its list.
    # Of the three maps (1 to 9, 10 to 90, 100 to 900) the second has a grey
    # table, the others none (a new map has no colour file). They get viridis
    # for their common range 1 to 900, the second keeps grey for its own range.
    small_region(tools, 3, 3)
    number = "(row() - 1) * 3 + col()"
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_{k}", f"({number}) * {m}", day(k), day(k + 1))
            for k, m in enumerate((1, 10, 100))
        ],
    )
    tools.r_colors(map=f"{prefix}_1", color="grey")
    for k, m in ((0, 1), (1, 10), (2, 100)):
        tools.r_mapcalc(expression=f"{prefix}_ref{k} = ({number}) * {m}")
    tools.r_colors(map=f"{prefix}_ref0,{prefix}_ref2", color="viridis")
    grey_before = table(f"{prefix}_1")

    tools.t_rast_colors(input=f"{prefix}_in", color="viridis", flags="w")

    assert table(f"{prefix}_0")[0].startswith("1 ")
    assert table(f"{prefix}_0")[-3].startswith("900 ")
    assert table(f"{prefix}_0") == table(f"{prefix}_ref0")
    assert table(f"{prefix}_2") == table(f"{prefix}_ref2")
    assert table(f"{prefix}_1") == grey_before


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_w_flag_sees_the_tables_of_maps_of_another_mapset(two_mapsets, prefix):
    # r.colors writes the table of a map of another mapset into the current
    # mapset (colr2), and -w finds it there. Map a of the other mapset has
    # such a grey table in "work", b none: -w writes viridis to b only.
    work, other = two_mapsets
    create_stds(
        other,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_a", 1, day(0), day(1)),
            MapSpec(f"{prefix}_b", 2, day(1), day(2)),
        ],
    )
    work.r_colors(map=f"{prefix}_a@other", color="grey")
    grey = work.r_colors_out(map=f"{prefix}_a@other").stdout
    work.r_mapcalc(expression=f"{prefix}_c = 2")
    work.r_colors(map=f"{prefix}_c", color="viridis")

    work.t_rast_colors(input=f"{prefix}_in@other", color="viridis", flags="w")

    assert work.r_colors_out(map=f"{prefix}_a@other").stdout == grey
    # b gets the table that r.colors makes for a map of the same value 2.
    assert (
        work.r_colors_out(map=f"{prefix}_b@other").stdout
        == work.r_colors_out(map=f"{prefix}_c").stdout
    )


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
