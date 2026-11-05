"""Test the label operator @ of r3.mapcalc against the one of r.mapcalc

A 3D map gets the category labels of a 2D map with r3.support raster=. The
labels cover two blocks of 64 categories, which r.mapcalc and r3.mapcalc read
one block at a time. One label is not a number, one only starts with a
number, and one category has no label.
"""

from io import StringIO

import pytest

from grass.tools import Tools

REGION = {"s": 0, "n": 2, "w": 0, "e": 3, "b": 0, "t": 2, "res": 1, "res3": 1}
CATEGORY = "if(col() == 3, 70, col() + 2 * (row() - 1))"
LABELS = "1:1.5\n2:two\n4:4.5 m\n70:70.5\n"


@pytest.fixture
def tools(session_in_mapset):
    with Tools(session=session_in_mapset, consistent_return_value=True) as tools:
        tools.g_region(**REGION)
        tools.r_mapcalc(expression=f"categories = {CATEGORY}")
        tools.r_category(map="categories", separator=":", rules=StringIO(LABELS))
        tools.r3_mapcalc(expression=f"categories = {CATEGORY}")
        tools.r3_support(map="categories", raster="categories")
        yield tools


def _cells(text):
    """The values of r.out.ascii or r3.out.ascii -h output, None for null"""
    return [None if word == "*" else float(word) for word in text.split()]


def test_label_operator_gives_label_value(tools):
    tools.r3_mapcalc(expression="labels = @categories")
    tools.r_mapcalc(expression="labels = @categories")

    volume = _cells(tools.r3_out_ascii(input="labels", flags="h").text)
    plane = _cells(tools.r_out_ascii(input="labels", flags="h", null_value="*").text)

    assert plane == [1.5, None, 70.5, None, 4.5, 70.5]
    assert volume == plane * 2
