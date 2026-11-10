"""Test the option type of t.vect.what.strds, which goes to v.what.rast

v.what.rast reads the features of the types it is given: points by default,
and centroids of areas with type=centroid. The area map of these tests has two
squares of the size of a cell of the 2 by 2 region with their centroids at
(0.5, 1.5) and (1.5, 1.5), that is in the cells (row 1, column 1) and (1, 2).
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    import_ascii_vector,
    register_stds,
    small_region,
    vector_points,
)

# The two squares with the centroids 1 and 2, in the format of v.out.ascii (layer, then category)
AREAS = (
    "B 5\n 0 1\n 1 1\n 1 2\n 0 2\n 0 1\n"
    "B 5\n 1 1\n 2 1\n 2 2\n 1 2\n 1 1\n"
    "C 1 1\n 0.5 1.5\n 1 1\n"
    "C 1 1\n 1.5 1.5\n 1 2\n"
)


@pytest.fixture(scope="module")
def rasters(tools):
    """The dataset wt_a with the map wt_1 that holds 10 col, in March 2001"""
    small_region(tools, 2, 2)
    create_stds(
        tools,
        "strds",
        "wt_a",
        [MapSpec("wt_1", "10 * col()", datetime(2001, 3, 1), datetime(2001, 4, 1))],
    )


@pytest.fixture
def areas(tools, tmp_path, prefix):
    """The dataset <prefix>_ds with the map <prefix>_areas of two areas"""
    name = f"{prefix}_areas"
    import_ascii_vector(tools, tmp_path, name, "standard", AREAS, flags="n")
    tools.v_db_addtable(map=name)
    register_stds(
        tools,
        "stvds",
        f"{prefix}_ds",
        [MapSpec(name, None, datetime(2001, 1, 1), datetime(2001, 6, 1))],
    )
    return name


def _what(tools, prefix, **options):
    tools.t_vect_what_strds(input=f"{prefix}_ds", strds="wt_a", **options)


def _rows(tools, vector):
    text = tools.v_db_select(map=vector, columns="cat,wt_1", flags="c").stdout
    return [tuple(line.split("|")) for line in text.splitlines()]


def test_centroids_sampled_with_type_centroid(tools, rasters, areas, prefix):
    _what(tools, prefix, type="centroid")

    # wt_1 holds 10 col: the centroids are in the columns 1 and 2.
    assert _rows(tools, areas) == [("1", "10"), ("2", "20")]


def test_centroids_empty_without_type(tools, rasters, areas, prefix):
    _what(tools, prefix)

    # The default type is point, and the map has no point.
    assert _rows(tools, areas) == [("1", ""), ("2", "")]


def test_points_unchanged(tools, rasters, prefix):
    points = f"{prefix}_pts"
    vector_points(tools, points, [(0.5, 1.5), (1.5, 1.5)], attributes={"h": [1, 2]})
    register_stds(
        tools,
        "stvds",
        f"{prefix}_ds",
        [MapSpec(points, None, datetime(2001, 1, 1), datetime(2001, 6, 1))],
    )

    _what(tools, prefix, type="point")
    explicit = _rows(tools, points)
    tools.v_db_dropcolumn(map=points, columns="wt_1")
    _what(tools, prefix)

    assert explicit == [("1", "10"), ("2", "20")]
    assert _rows(tools, points) == explicit
