"""Datasets and readers for the tests of t.rast.colors

The tool changes the colour tables of the maps of its input, so every test
makes a dataset of its own (the prefix fixture). The dataset holds two integer
maps in a region of three rows and three columns:

- <prefix>_a: 1 to 9 row by row,
- <prefix>_b: 10 to 90 in steps of 10,

so the combined range of the dataset is 1 to 90 and its 18 values are all
different, each in one cell.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region


@pytest.fixture
def colored(tools, prefix):
    """The names of the dataset and its two maps (a, b) of the test"""
    small_region(tools, 3, 3)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_a", "(row() - 1) * 3 + col()", day(0), day(1)),
            MapSpec(f"{prefix}_b", "((row() - 1) * 3 + col()) * 10", day(1), day(2)),
        ],
    )
    return f"{prefix}_in", f"{prefix}_a", f"{prefix}_b"


@pytest.fixture
def table(tools):
    """Function that returns the colour rules of a map as r.colors.out prints them

    The lines are "value r:g:b", then "nv r:g:b" and "default r:g:b". Note that
    r.colors.out does not show an inversion by -n, see colour_of().
    """

    def read(name):
        return tools.r_colors_out(map=name).stdout.strip().split("\n")

    return read


@pytest.fixture
def colour_of(tools):
    """Function that returns the colour of a value in a map as (r, g, b)

    The colour is looked up with r.what.color, which applies the table the way
    the map is displayed. That is the effect to check for -n: r.colors.out
    prints the same rules with and without the inversion.
    """

    def look(name, value):
        text = tools.r_what_color(input=name, value=[value], format="%d:%d:%d").stdout
        return tuple(int(part) for part in text.split(": ")[1].strip().split(":"))

    return look
