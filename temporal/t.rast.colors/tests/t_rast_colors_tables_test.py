"""Test the sources of colours of t.rast.colors: names, rules and other maps

The tool gives all maps of the dataset to one r.colors run, which makes a
table for the combined range of the maps, so every map of the dataset gets the
same rules, here from 1 (the smallest cell of the first map) to 90 (the
largest of the second).
"""

import re

import pytest

from grass.temporal.testing.data import small_region

GREY = ["1 0:0:0", "90 255:255:255", "nv 255:255:255", "default 255:255:255"]
WHITE = ["nv 255:255:255", "default 255:255:255"]


def test_a_colour_table_by_name(tools, colored, table):
    # grey runs from black at the smallest to white at the largest value.
    name, first, second = colored

    tools.t_rast_colors(input=name, color="grey")

    assert table(first) == GREY
    assert table(second) == GREY


def test_the_rules_of_a_file(tools, colored, table, tmp_path):
    name, first, second = colored
    rules = tmp_path / "rules.txt"
    rules.write_text("1 red\n90 blue\n")

    tools.t_rast_colors(input=name, rules=str(rules))

    expected = ["1 255:0:0", "90 0:0:255", *WHITE]
    assert table(first) == expected
    assert table(second) == expected


def test_rules_with_more_than_two_colours(tools, colored, table, tmp_path):
    name, first, _ = colored
    rules = tmp_path / "rules.txt"
    rules.write_text("1 red\n45 255:255:0\n90 0:0:255\n")

    tools.t_rast_colors(input=name, rules=str(rules))

    assert table(first) == ["1 255:0:0", "45 255:255:0", "90 0:0:255", *WHITE]


def test_a_colour_table_is_copied_from_a_raster_map(tools, colored, table, tmp_path):
    name, first, second = colored
    tools.r_mapcalc(expression=f"{name}_src = 7")
    rules = tmp_path / "rules.txt"
    rules.write_text("1 red\n5 yellow\n")
    tools.r_colors(map=f"{name}_src", rules=str(rules))

    tools.t_rast_colors(input=name, raster=f"{name}_src")

    expected = ["1 255:0:0", "5 255:255:0", *WHITE]
    assert table(first) == expected
    assert table(second) == expected


def test_a_colour_table_is_copied_from_a_3d_raster_map(tools, colored, table, tmp_path):
    name, first, second = colored
    small_region(tools, 3, 3, depths=1)
    tools.r3_mapcalc(expression=f"{name}_vol = 5.0")
    rules = tmp_path / "rules3.txt"
    rules.write_text("0 yellow\n10 green\n")
    tools.r3_colors(map=f"{name}_vol", rules=str(rules))
    small_region(tools, 3, 3)

    tools.t_rast_colors(input=name, raster_3d=f"{name}_vol")

    expected = ["0 255:255:0", "10 0:255:0", *WHITE]
    assert table(first) == expected
    assert table(second) == expected


def test_random_colours_have_the_structure_of_a_table(tools, colored, table):
    # One rule for each integer from 1 to 90 with an arbitrary colour, then
    # the two lines for null and the default; the colours are not tested.
    name, first, second = colored

    tools.t_rast_colors(input=name, color="random")

    for lines in (table(first), table(second)):
        assert len(lines) == 92
        assert lines[-2:] == WHITE
        for number, line in enumerate(lines[:-2], 1):
            match = re.fullmatch(rf"{number} (\d+):(\d+):(\d+)", line)
            assert match, line
            assert all(0 <= int(part) <= 255 for part in match.groups())


def test_the_measured_tables_of_grey_eq_and_grey_log(tools, colored, table):
    # The greys are derived from lib/raster/color_hist.c for the 18 values
    # of the dataset, each in one cell. grey.eq gives the value at rank i
    # (from 0) the grey (i + 0.5) 256 / 18, cut to an integer: 7, 21, 35 for
    # 1, 2, 3 and 248 for 90 (rank 17). grey.log gives
    # int(255 ln(v) / ln(90)): 0, 39, 62 for 1, 2, 3 and 255 for 90.
    # The number of lines is measured, not derived: r.colors.out joins the
    # ranges of equal grey into 26 rules, plus the lines for null and the
    # default (measured 18.10.2026 with this test; the joining is a matter of
    # the output format, not of the tool under test).
    name, first, _ = colored

    tools.t_rast_colors(input=name, color="grey.eq")
    equalised = table(first)
    tools.t_rast_colors(input=name, color="grey.log", overwrite=True)
    logarithmic = table(first)

    assert len(equalised) == 28
    assert equalised[:3] == ["1 7:7:7", "2 21:21:21", "3 35:35:35"]
    assert equalised[-3] == "90 248:248:248"
    assert len(logarithmic) == 28
    assert logarithmic[:3] == ["1 0:0:0", "2 39:39:39", "3 62:62:62"]
    assert logarithmic[-3] == "90 255:255:255"


@pytest.mark.parametrize("name", ["viridis", "ryb", "bcyr"])
def test_other_names_of_r_colors_are_accepted(tools, colored, table, name):
    dataset, first, second = colored

    tools.t_rast_colors(input=dataset, color=name)

    assert table(first) == table(second)
    assert table(first)[-2:] == WHITE
