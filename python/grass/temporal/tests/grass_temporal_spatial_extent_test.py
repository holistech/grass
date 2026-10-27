"""Tests for the 2D and 3D spatial extent relations

Extents are plain value objects, so no GRASS session and no temporal database
are needed here.
"""

from types import SimpleNamespace

import pytest

from grass.temporal.kinds import KINDS
from grass.temporal.spatial_extent import SpatialExtent, SpatialExtentRow

# The extent every case below is compared against.
REFERENCE = {"north": 80, "south": 20, "east": 60, "west": 10, "bottom": -50, "top": 50}


def extent(**kwargs):
    """Return the reference extent with the given bounds overridden

    Called with no arguments it returns the reference extent itself; each
    keyword argument (north, south, east, west, bottom, top) replaces that
    one bound.
    """
    return SpatialExtent(**{**REFERENCE, **kwargs})


@pytest.mark.parametrize(
    "other",
    [
        # The intersection of the reference extent with an extent it fully
        # covers is that extent itself, in 2D and in 3D.
        {},
        {"north": 40, "south": 30},
        {"north": 40, "south": 30, "west": 30},
        {"north": 40, "south": 30, "west": 30, "bottom": -30},
        {"north": 40, "south": 30, "west": 30, "bottom": -30, "top": 30},
    ],
)
def test_intersect_with_covered_extent_returns_that_extent(other) -> None:
    covered = extent(**other)
    result = extent().intersect(covered)

    assert result.get_north() == covered.get_north()
    assert result.get_south() == covered.get_south()
    assert result.get_west() == covered.get_west()
    assert result.get_east() == covered.get_east()
    assert result.get_bottom() == covered.get_bottom()
    assert result.get_top() == covered.get_top()


@pytest.mark.parametrize(
    ("other", "expected_2d", "expected_3d"),
    [
        # Identical extents are equivalent in both 2D and 3D.
        ({}, "equivalent", "equivalent"),
        # Sharing a boundary while being smaller in one direction is "cover".
        ({"north": 70}, "cover", "cover"),
        ({"north": 70, "south": 30}, "cover", "cover"),
        ({"north": 70, "south": 30, "east": 50}, "cover", "cover"),
        # Strictly inside in 2D, but the top and bottom still touch, so the 3D
        # relation stays "cover" rather than becoming "contain".
        ({"north": 70, "south": 30, "east": 50, "west": 20}, "contain", "cover"),
        # Strictly inside in every direction is "contain".
        (
            {
                "north": 70,
                "south": 30,
                "east": 50,
                "west": 20,
                "bottom": -40,
                "top": 40,
            },
            "contain",
            "contain",
        ),
    ],
)
def test_spatial_relation_of_smaller_extent(other, expected_2d, expected_3d) -> None:
    assert extent().spatial_relation_2d(extent(**other)) == expected_2d
    assert extent().spatial_relation(extent(**other)) == expected_3d


@pytest.mark.parametrize(
    ("other", "expected"),
    [
        # The inverse of "cover" is "covered" and the inverse of "contain" is "in".
        ({"north": 70, "south": 30}, "covered"),
        (
            {
                "north": 70,
                "south": 30,
                "east": 50,
                "west": 20,
                "bottom": -40,
                "top": 40,
            },
            "in",
        ),
    ],
)
def test_spatial_relation_is_inverted_when_arguments_swap(other, expected) -> None:
    assert extent(**other).spatial_relation(extent()) == expected


@pytest.mark.parametrize(
    ("other", "expected_2d", "expected_3d"),
    [
        # Reaching past the reference extent in one direction only is an overlap.
        (
            {
                "north": 90,
                "south": 30,
                "east": 50,
                "west": 20,
                "bottom": -40,
                "top": 40,
            },
            "overlap",
            "overlap",
        ),
        # The reference extent lies inside the other one in 2D, but sticks out
        # in the third dimension, so in 3D the two only overlap.
        (
            {"north": 90, "south": 5, "east": 70, "west": 5, "bottom": -40, "top": 40},
            "in",
            "overlap",
        ),
    ],
)
def test_spatial_relation_of_overlapping_extent(
    other, expected_2d, expected_3d
) -> None:
    assert extent().spatial_relation_2d(extent(**other)) == expected_2d
    assert extent().spatial_relation(extent(**other)) == expected_3d


@pytest.mark.parametrize(
    ("one", "other", "expected"),
    [
        # Extents that only touch along a face "meet", never overlap.
        (
            {"north": 80, "south": 60},
            {"north": 60, "south": 20},
            "meet",
        ),
        (
            {"north": 60, "south": 40},
            {"north": 80, "south": 60},
            "meet",
        ),
        (
            {"north": 80, "south": 40, "east": 60, "west": 40},
            {"north": 80, "south": 40, "east": 40, "west": 20},
            "meet",
        ),
        # Touching only along the top and bottom faces also "meets".
        (
            {"east": 60, "west": 20, "north": 80, "south": 40, "bottom": 0, "top": 50},
            {"east": 60, "west": 20, "north": 80, "south": 40, "bottom": -50, "top": 0},
            "meet",
        ),
    ],
)
def test_spatial_relation_of_touching_extents(one, other, expected) -> None:
    assert extent(**one).spatial_relation(extent(**other)) == expected


def test_spatial_relation_of_separate_extents_is_disjoint() -> None:
    one = extent(north=80, south=40, east=40, west=20)
    other = extent(north=40, south=20, east=60, west=40)

    assert one.spatial_relation_2d(other) == "disjoint"
    assert one.spatial_relation(other) == "disjoint"


@pytest.mark.parametrize(
    ("method", "named"),
    [
        ("overlapping", "overlapping_2d"),
        ("overlapping_2d", "overlapping_2d"),
        ("is_in", "is_in_2d"),
        ("is_in_2d", "is_in_2d"),
        ("equivalent", "equivalent_2d"),
        ("equivalent_2d", "equivalent_2d"),
        ("cover", "cover"),
        ("cover_2d", "cover_2d"),
    ],
)
def test_different_projections_are_reported_and_never_related(
    method, named, monkeypatch
) -> None:
    # The 3D methods ask their 2D twin first, so their message names that
    # twin. Only cover has a message of its own for each.
    errors = []
    monkeypatch.setattr(
        "grass.temporal.rows.get_tgis_message_interface",
        lambda: SimpleNamespace(error=errors.append),
    )
    other = SpatialExtent(**{**REFERENCE, "proj": "LL"})
    assert getattr(extent(), method)(other) is False
    assert errors == [
        f"Projections are different. Unable to compute {named} for spatial extents"
    ]


def box(*bounds):
    """Return an extent from (north, south, east, west[, bottom, top])"""
    names = ("north", "south", "east", "west", "bottom", "top")
    return SpatialExtent(**dict(zip(names, bounds, strict=False)))


# The method, the bounds of the two extents as for box() and the result. These
# cases were the examples in the docstrings of SpatialExtent, which now keep
# one example each.
RELATIONS = [
    ("contain", (80, 20, 60, 10, -50, 50), (79, 21, 59, 11, -49, 49), True),
    ("contain", (79, 21, 59, 11, -49, 49), (80, 20, 60, 10, -50, 50), False),
    ("contain_2d", (80, 20, 60, 10), (79, 21, 59, 11), True),
    ("contain_2d", (79, 21, 59, 11), (80, 20, 60, 10), False),
    ("equivalent", (80, 20, 60, 10, -50, 50), (80, 20, 60, 10, -50, 50), True),
    ("equivalent_2d", (80, 20, 60, 10), (80, 20, 60, 10), True),
    ("is_in", (79, 21, 59, 11, -49, 49), (80, 20, 60, 10, -50, 50), True),
    ("is_in", (80, 20, 60, 10, -50, 50), (79, 21, 59, 11, -49, 49), False),
    ("overlapping", (80, 20, 60, 10, -50, 50), (80, 20, 60, 10, -50, 50), True),
    ("overlapping_2d", (80, 20, 60, 10), (80, 20, 60, 10), True),
    (
        "spatial_relation_2d",
        (70, 30, 60, 10, -50, 50),
        (80, 20, 60, 10, -50, 50),
        "covered",
    ),
    (
        "spatial_relation_2d",
        (70, 30, 50, 10, -50, 50),
        (80, 20, 60, 10, -50, 50),
        "covered",
    ),
    (
        "spatial_relation",
        (70, 30, 50, 20, -50, 50),
        (80, 20, 60, 10, -50, 50),
        "covered",
    ),
    ("spatial_relation", (80, 20, 60, 10, -50, 50), (70, 30, 50, 20, -40, 50), "cover"),
    ("spatial_relation", (80, 20, 60, 10, -50, 50), (90, 5, 70, 5, -40, 60), "overlap"),
    ("spatial_relation", (80, 20, 60, 10, -50, 50), (90, 5, 70, 5, -60, 60), "in"),
    (
        "spatial_relation_2d",
        (80, 60, 60, 10, -50, 50),
        (60, 20, 60, 10, -50, 50),
        "meet",
    ),
    (
        "spatial_relation_2d",
        (60, 40, 60, 10, -50, 50),
        (80, 60, 60, 10, -50, 50),
        "meet",
    ),
    (
        "spatial_relation_2d",
        (80, 40, 60, 40, -50, 50),
        (80, 40, 40, 20, -50, 50),
        "meet",
    ),
    (
        "spatial_relation_2d",
        (80, 40, 40, 20, -50, 50),
        (90, 30, 60, 40, -50, 50),
        "meet",
    ),
    ("spatial_relation", (80, 40, 40, 20, -50, 50), (90, 30, 60, 40, -50, 50), "meet"),
    (
        "spatial_relation_2d",
        (80, 40, 40, 20, -50, 50),
        (70, 50, 60, 40, -50, 50),
        "meet",
    ),
    ("spatial_relation", (80, 40, 40, 20, -50, 50), (70, 50, 60, 40, -50, 50), "meet"),
    (
        "spatial_relation_2d",
        (80, 40, 40, 20, -50, 50),
        (60, 20, 60, 40, -50, 50),
        "meet",
    ),
    ("spatial_relation", (80, 40, 40, 20, -50, 50), (60, 20, 60, 40, -50, 50), "meet"),
    ("spatial_relation", (80, 40, 40, 20, -50, 50), (60, 20, 60, 40, -60, 60), "meet"),
    ("spatial_relation", (80, 40, 40, 20, -50, 50), (90, 30, 60, 40, -40, 40), "meet"),
    ("spatial_relation", (80, 40, 60, 20, 0, 50), (80, 50, 60, 30, -50, 0), "meet"),
    ("spatial_relation", (80, 40, 60, 20, 0, 50), (70, 50, 50, 30, -50, 0), "meet"),
    ("spatial_relation", (80, 40, 60, 20, 0, 50), (90, 30, 70, 10, -50, 0), "meet"),
    ("spatial_relation", (80, 40, 60, 20, 0, 50), (70, 30, 50, 10, -50, 0), "meet"),
    ("spatial_relation", (80, 40, 60, 20, -50, 0), (80, 40, 60, 20, 0, 50), "meet"),
    ("spatial_relation", (80, 40, 60, 20, -50, 0), (80, 50, 60, 30, 0, 50), "meet"),
    ("spatial_relation", (80, 40, 60, 20, -50, 0), (70, 50, 50, 30, 0, 50), "meet"),
    ("spatial_relation", (80, 40, 60, 20, -50, 0), (90, 30, 70, 10, 0, 50), "meet"),
    ("spatial_relation", (80, 40, 60, 20, -50, 0), (70, 30, 50, 10, 0, 50), "meet"),
    (
        "spatial_relation",
        (80, 20, 60, 10, -50, 50),
        (90, 81, 60, 10, -50, 50),
        "disjoint",
    ),
    ("spatial_relation", (80, 20, 60, 10, -50, 50), (90, 80, 60, 10, -50, 50), "meet"),
]


@pytest.mark.parametrize(("method", "one", "other", "expected"), RELATIONS)
def test_relation_of_two_extents(method, one, other, expected) -> None:
    assert getattr(box(*one), method)(box(*other)) == expected


# The bounds of the two extents as for box() and the union as (north, south,
# east, west, top, bottom), the order of print_info(). Like RELATIONS, the
# cases were examples in a docstring.
DISJOINT_UNIONS = [
    (
        (80, 20, 60, 10, -50, 50),
        (80, 20, 60, 10, -50, 50),
        (80.0, 20.0, 60.0, 10.0, 50.0, -50.0),
    ),
    (
        (80, 20, 60, 10, -50, 50),
        (40, 30, 60, 10, -50, 50),
        (80.0, 20.0, 60.0, 10.0, 50.0, -50.0),
    ),
    (
        (80, 20, 60, 10, -50, 50),
        (40, 30, 60, 30, -50, 50),
        (80.0, 20.0, 60.0, 10.0, 50.0, -50.0),
    ),
    (
        (80, 20, 60, 10, -50, 50),
        (40, 30, 60, 30, -30, 50),
        (80.0, 20.0, 60.0, 10.0, 50.0, -50.0),
    ),
    (
        (80, 20, 60, 10, -50, 50),
        (40, 30, 60, 30, -30, 30),
        (80.0, 20.0, 60.0, 10.0, 50.0, -50.0),
    ),
    (
        (80, 20, 60, 10, -50, 50),
        (90, 80, 70, 20, -30, 60),
        (90.0, 20.0, 70.0, 10.0, 60.0, -50.0),
    ),
]


@pytest.mark.parametrize(("one", "other", "expected"), DISJOINT_UNIONS)
def test_disjoint_union(one, other, expected) -> None:
    union = box(*one).disjoint_union(box(*other))
    assert union.get_spatial_extent_as_tuple() == expected


def test_extent_of_a_map_by_attribute_and_printed(capsys) -> None:
    extent = SpatialExtent(
        table="raster_spatial_extent",
        ident="soil@PERMANENT",
        north=90,
        south=90,
        east=180,
        west=180,
        top=100,
        bottom=-20,
    )
    assert extent.id == "soil@PERMANENT"
    # The bounds are stored as float, whatever number type was given.
    assert (
        extent.north,
        extent.south,
        extent.east,
        extent.west,
        extent.top,
        extent.bottom,
    ) == (90.0, 90.0, 180.0, 180.0, 100.0, -20.0)

    extent.print_info()
    extent.print_shell_info()
    assert capsys.readouterr().out.splitlines() == [
        " +-------------------- Spatial extent ----------------------------------------+",
        " | North:...................... 90.0",
        " | South:...................... 90.0",
        " | East:.. .................... 180.0",
        " | West:....................... 180.0",
        " | Top:........................ 100.0",
        " | Bottom:..................... -20.0",
        "north=90.0",
        "south=90.0",
        "east=180.0",
        "west=180.0",
        "top=100.0",
        "bottom=-20.0",
    ]


@pytest.mark.parametrize(
    "name", ["raster", "raster3d", "vector", "strds", "str3ds", "stvds"]
)
def test_row_of_a_kind_names_its_table(name) -> None:
    extent = SpatialExtentRow(
        KINDS[name],
        ident=f"{name}@PERMANENT",
        north=90,
        south=90,
        east=180,
        west=180,
        top=100,
        bottom=-20,
    )
    assert extent.get_table_name() == f"{name}_spatial_extent"
