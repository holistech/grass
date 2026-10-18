"""Datasets for the tests of t.vect.univar

uv_pts has three monthly point maps (January to March 2001) with the columns
value (integers) and height (value / 2, floats):

- up_1 has the values 1, 2, 3, 4,
- up_2 has 2, 4, 6, 8 and a fifth point whose attributes are NULL,
- up_3 has 10 and 20.

uv_lines (map ul_1, January) has two lines with the values 10 and 20, uv_areas
(map ua_1, January) two squares with the values 100 and 200 in their
centroids. uv_lay has the map lm with two layers, registered as lm:2 in
January, and the map lu, registered without a layer in February; the layer 1
of both holds 1, 2, 3 and the layer 2 holds 101, 102, 103.
"""

from datetime import datetime
from io import StringIO

import pytest

from grass.temporal.testing.data import MapSpec, register_stds, vector_points


@pytest.fixture(autouse=True)
def _work_in_tmp_path(tmp_path, monkeypatch):
    # A file named by output= lands in the current directory.
    monkeypatch.chdir(tmp_path)


MONTH = [datetime(2001, number, 1) for number in range(1, 6)]


@pytest.fixture(scope="module")
def points(tools):
    """The dataset uv_pts described above; returns its name"""
    data = {
        "up_1": [1, 2, 3, 4],
        "up_2": [2, 4, 6, 8, 10],
        "up_3": [10, 20],
    }
    for name, values in data.items():
        vector_points(
            tools,
            name,
            [(number, number) for number in range(1, len(values) + 1)],
            attributes={"value": values, "height": [value / 2 for value in values]},
        )
    tools.db_execute(sql="UPDATE up_2 SET value = NULL, height = NULL WHERE cat = 5")
    register_stds(
        tools,
        "stvds",
        "uv_pts",
        [
            MapSpec(name, None, MONTH[number], MONTH[number + 1])
            for number, name in enumerate(data)
        ],
    )
    return "uv_pts"


def _standard(tools, name, body, values):
    """A map from the ASCII standard format with the attribute value = cat * k"""
    tools.v_in_ascii(input=StringIO("VERTI:\n" + body), output=name, format="standard")
    tools.v_db_addtable(map=name, columns="value integer")
    tools.db_execute(sql=f"UPDATE {name} SET value = cat * {values}")


@pytest.fixture(scope="module")
def lines(tools):
    """uv_lines: two lines with the categories 1 and 2 (values 10 and 20)"""
    _standard(
        tools,
        "ul_1",
        "L 2 1\n 0 0\n 2 0\n 1 1\nL 2 1\n 0 1\n 2 1\n 1 2\n",
        10,
    )
    register_stds(
        tools, "stvds", "uv_lines", [MapSpec("ul_1", None, MONTH[0], MONTH[1])]
    )
    return "uv_lines"


@pytest.fixture(scope="module")
def areas(tools):
    """uv_areas: two squares, centroids with the categories 1 and 2 (100, 200)"""
    _standard(
        tools,
        "ua_1",
        "B 5\n 0 0\n 1 0\n 1 1\n 0 1\n 0 0\n"
        "B 5\n 2 0\n 3 0\n 3 1\n 2 1\n 2 0\n"
        "C 1 1\n 0.5 0.5\n 1 1\nC 1 1\n 2.5 0.5\n 1 2\n",
        100,
    )
    register_stds(
        tools, "stvds", "uv_areas", [MapSpec("ua_1", None, MONTH[0], MONTH[1])]
    )
    return "uv_areas"


@pytest.fixture(scope="module")
def layers(tools):
    """uv_lay described above; returns its name"""
    for name in ("lm", "lu"):
        vector_points(
            tools,
            name,
            [(1, 1), (2, 2), (3, 3)],
            attributes={"value": [1, 2, 3]},
            layers=(1, 2),
        )
        tools.db_execute(sql=f"UPDATE {name}_2 SET value = value + 100")
    register_stds(
        tools,
        "stvds",
        "uv_lay",
        [
            MapSpec("lm:2", None, MONTH[0], MONTH[1]),
            MapSpec("lu", None, MONTH[1], MONTH[2]),
        ],
    )
    return "uv_lay"
