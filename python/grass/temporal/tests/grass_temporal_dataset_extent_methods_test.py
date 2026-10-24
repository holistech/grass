"""Tests for the spatial extent methods of the dataset classes and the map list string

The dataset objects are built without a database: an identifier and a spatial
extent are enough for the spatial methods. The expected values are those of the
classes before their shared methods moved into a mixin.
"""

import pytest

from grass.temporal import (
    Raster3DDataset,
    RasterDataset,
    SpaceTimeRaster3DDataset,
    SpaceTimeRasterDataset,
    SpaceTimeVectorDataset,
    VectorDataset,
)
from grass.temporal.spatial_topology_dataset_connector import (
    SpatialTopologyDatasetConnector,
)
from grass.temporal.temporal_topology_dataset_connector import (
    TemporalTopologyDatasetConnector,
)

CLASSES = {
    "raster": RasterDataset,
    "raster3d": Raster3DDataset,
    "vector": VectorDataset,
    "strds": SpaceTimeRasterDataset,
    "str3ds": SpaceTimeRaster3DDataset,
    "stvds": SpaceTimeVectorDataset,
}

# Two boxes that overlap in the plane (north 5..10, east 5..10) and lie apart
# in the third dimension: A from 0 to 10, B from 20 to 30. The planar methods
# see an overlap, the volume methods see disjoint boxes.
BOX_A = (10, 0, 10, 0, 10, 0)  # north, south, east, west, top, bottom
BOX_B = (15, 5, 15, 5, 30, 20)

PLANAR = {
    "overlapping": True,
    "relation": "overlap",
    # The planar results carry no top and bottom: both are 0.
    "intersection": (10, 5, 10, 5, 0, 0),
    "union": (15, 0, 15, 0, 0, 0),
    "disjoint_union": (15, 0, 15, 0, 0, 0),
}
VOLUME = {
    "overlapping": False,
    "relation": "disjoint",
    "intersection": None,
    "union": None,
    "disjoint_union": (15, 0, 15, 0, 30, 0),
}


def _dataset(kind, box, name):
    dataset = CLASSES[kind](f"{name}@mapset")
    north, south, east, west, top, bottom = box
    dataset.spatial_extent.set_spatial_extent_from_values(
        north, south, east, west, top, bottom
    )
    return dataset


def _results(first, second):
    """Return the results of the five spatial methods of first with second"""
    results = {
        "overlapping": first.spatial_overlapping(second),
        "relation": first.spatial_relation(second),
    }
    for name in ("intersection", "union", "disjoint_union"):
        extent = getattr(first, f"spatial_{name}")(second)
        results[name] = None if extent is None else extent.get_spatial_extent_as_tuple()
    return results


# Each pair gives the methods that compute in the plane and those that compute
# in space. The volume methods are used when the other dataset is a 3D raster
# map or a space time 3D raster dataset (and when both have the same type).
PAIRS = [
    ("raster", "raster", PLANAR),
    ("raster3d", "raster3d", VOLUME),
    ("raster3d", "raster", PLANAR),
    ("raster3d", "str3ds", VOLUME),
    ("str3ds", "strds", PLANAR),
    ("str3ds", "str3ds", VOLUME),
    ("vector", "stvds", PLANAR),
    ("strds", "raster", PLANAR),
    # The space time 3D raster dataset takes str3ds for the space in
    # overlapping and relation but raster3d and str3ds in intersection, union
    # and disjoint union. This pins today's inconsistent result for the pair.
    (
        "str3ds",
        "raster3d",
        {
            "overlapping": PLANAR["overlapping"],
            "relation": PLANAR["relation"],
            "intersection": VOLUME["intersection"],
            "union": VOLUME["union"],
            "disjoint_union": VOLUME["disjoint_union"],
        },
    ),
]


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    PAIRS,
    ids=[f"{first}-{second}" for first, second, _ in PAIRS],
)
def test_the_extent_methods_compute_in_the_plane_or_in_space(first, second, expected):
    results = _results(_dataset(first, BOX_A, "a"), _dataset(second, BOX_B, "b"))

    assert results == expected


@pytest.mark.parametrize("kind", sorted(CLASSES))
def test_every_dataset_class_can_be_instantiated(kind):
    # The methods are abstract in AbstractDataset; a class that does not
    # provide them cannot be instantiated.
    assert CLASSES[kind]("a@mapset").get_type() == kind


@pytest.mark.parametrize(
    "connector", [SpatialTopologyDatasetConnector, TemporalTopologyDatasetConnector]
)
def test_the_map_list_string_wraps_after_three_maps(connector):
    maps = [RasterDataset(f"m{n}@mapset") for n in range(1, 5)]

    assert connector()._generate_map_list_string(maps) == (
        "m1@mapset,m2@mapset,m3@mapset\n | ............................ m4@mapset"
    )
    assert connector()._generate_map_list_string(maps[:2], line_wrap=False) == (
        "m1@mapset,m2@mapset"
    )
    assert connector()._generate_map_list_string(maps, line_wrap=False) == (
        "m1@mapset,m2@mapset,m3@mapset,m4@mapset"
    )
