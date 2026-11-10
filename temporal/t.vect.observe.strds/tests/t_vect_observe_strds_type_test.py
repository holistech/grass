"""Test the option type of t.vect.observe.strds, which goes to v.what.rast

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
    """The dataset ty_a: map ty_1 holds 10 col, map ty_2 holds 100 + 10 col"""
    small_region(tools, 2, 2)
    create_stds(
        tools,
        "strds",
        "ty_a",
        [
            MapSpec("ty_1", "10 * col()", datetime(2001, 3, 1), datetime(2001, 4, 1)),
            MapSpec(
                "ty_2", "100 + 10 * col()", datetime(2001, 4, 1), datetime(2001, 5, 1)
            ),
        ],
    )


@pytest.fixture
def areas(tools, tmp_path, prefix):
    """The map <prefix>_areas with two areas, the categories 1 and 2"""
    name = f"{prefix}_areas"
    import_ascii_vector(tools, tmp_path, name, "standard", AREAS, flags="n")
    tools.v_db_addtable(map=name)
    return name


def _observe(tools, vector, prefix, **options):
    tools.t_vect_observe_strds(
        input=vector,
        strds="ty_a",
        output=prefix,
        vector_output=f"{prefix}_v",
        columns="obs",
        **options,
    )
    return f"{prefix}_v"


def _rows(tools, vector, layer):
    text = tools.v_db_select(
        map=vector, layer=layer, columns="cat,obs", flags="c"
    ).stdout
    return [tuple(line.split("|")) for line in text.splitlines()]


@pytest.mark.parametrize(("layer", "values"), [(1, ("10", "20")), (2, ("110", "120"))])
def test_centroids_sampled_with_type_centroid(
    tools, rasters, areas, prefix, layer, values
):
    vector = _observe(tools, areas, prefix, type="centroid")

    # ty_1 holds 10 col and ty_2 holds 100 + 10 col: the centroids are in the
    # columns 1 and 2.
    assert _rows(tools, vector, layer) == [("1", values[0]), ("2", values[1])]


def test_centroids_empty_without_type(tools, rasters, areas, prefix):
    vector = _observe(tools, areas, prefix)

    # The default type is point, and the map has no point.
    assert _rows(tools, vector, 1) == [("1", ""), ("2", "")]


def test_observe_keeps_centroids(tools, rasters, areas, prefix):
    vector = _observe(tools, areas, prefix, type="centroid")

    topology = tools.v_info(map=vector, flags="t").stdout
    assert "centroids=2" in topology
    assert "areas=2" in topology


def test_points_unchanged(tools, rasters, prefix):
    points = f"{prefix}_pts"
    vector_points(tools, points, [(0.5, 1.5), (1.5, 1.5)], attributes={"h": [1, 2]})

    explicit = _observe(tools, points, prefix, type="point")
    default = _observe(tools, points, f"{prefix}_d")

    assert _rows(tools, explicit, 1) == [("1", "10"), ("2", "20")]
    assert _rows(tools, default, 1) == _rows(tools, explicit, 1)
    assert _rows(tools, default, 2) == _rows(tools, explicit, 2)
