"""What the algebra core needs to know about a map type, apart from
computing its maps

The backends know how a map is computed. This module knows how a map type
is named in the temporal database and by the tools of GRASS, and in how
many dimensions its maps are related in space.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
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
# as in the classic algebra (_SPATIAL_DIMENSIONS in classic/temporal_algebra.py).
DIMENSIONS = {"raster": "2D", "raster3d": "3D", "vector": "2D"}
# r.mapcalc reads a map at a row and column offset, r3.mapcalc at a row,
# column and depth offset; vector maps have no cells.
OFFSET_COUNTS = {"raster": 2, "raster3d": 3, "vector": 0}
