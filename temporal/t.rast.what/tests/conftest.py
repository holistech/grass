"""Datasets for the tests of t.rast.what

The region has three rows and three columns of size 1, so the cell in row r and
column c (both counted from 1, row 1 in the north) has its centre at
(c - 0.5, 3.5 - r). The dataset wh_a has three daily maps:

- wh_1 holds 10 r + c in every cell,
- wh_2 holds 10 r + c + 100, but nothing in the middle column,
- wh_3 holds 10 r + c + 200.

The points of wh_pts are (0.5, 2.5) in the cell (1, 1) with the category 7,
(2.5, 0.5) in the cell (3, 3) with the category 8 and (1.5, 1.5) in the cell
(2, 2) with the category 9. The values at the points are therefore 11, 111, 211
for the first, 33, 133, 233 for the second and 22, nothing, 222 for the third.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region


@pytest.fixture(autouse=True)
def _work_in_tmp_path(tmp_path, monkeypatch):
    # For more than 400 maps the tool writes a file in the current directory
    # (see t_rast_what_many_maps_test.py), and pytest may run from the
    # source tree.
    monkeypatch.chdir(tmp_path)


@pytest.fixture(scope="module")
def sampled(tools, tmp_path_factory):
    """The dataset and the point map described above; returns the dataset name"""
    small_region(tools, 3, 3)
    create_stds(
        tools,
        "strds",
        "wh_a",
        [
            MapSpec("wh_1", "row() * 10 + col()", day(0), day(1)),
            MapSpec(
                "wh_2",
                "if(col() == 2, null(), row() * 10 + col() + 100)",
                day(1),
                day(2),
            ),
            MapSpec("wh_3", "row() * 10 + col() + 200", day(2), day(3)),
        ],
    )
    points = tmp_path_factory.mktemp("wh_points") / "points.txt"
    points.write_text("0.5|2.5|7\n2.5|0.5|8\n1.5|1.5|9\n", encoding="utf-8")
    tools.v_in_ascii(
        input=str(points), output="wh_pts", separator="pipe", x=1, y=2, cat=3
    )
    return "wh_a"
