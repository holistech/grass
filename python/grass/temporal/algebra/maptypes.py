"""What the algebra core needs to know about a map type, apart from
computing its maps

The backends know how a map is computed. This module knows how a map type
is named in the temporal database and by the tools of GRASS, and in how
many dimensions its maps are related in space.
"""

from grass.temporal.space_time_datasets import (
    Raster3DDataset,
    RasterDataset,
    VectorDataset,
)

STDS_TYPES = {"raster": "strds", "raster3d": "str3ds", "vector": "stvds"}
KINDS_OF_STDS = {stds_type: kind for kind, stds_type in STDS_TYPES.items()}
MAP_CLASSES = {
    "raster": RasterDataset,
    "raster3d": Raster3DDataset,
    "vector": VectorDataset,
}
# The type names of g.remove and the parameter names of g.copy.
ELEMENTS = {"raster": "raster", "raster3d": "raster_3d", "vector": "vector"}
# Raster3D maps are related in space as boxes and the others as rectangles,
# as in the classic algebra (_SPATIAL_DIMENSIONS in temporal_algebra.py).
DIMENSIONS = {"raster": "2D", "raster3d": "3D", "vector": "2D"}
