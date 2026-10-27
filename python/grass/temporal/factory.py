"""
Object factory

SPDX-FileCopyrightText: 2012-2024 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert, Edouard Choinière
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .datasets import class_of_kind
from .kinds import find_kind
from .state import get_tgis_message_interface

if TYPE_CHECKING:
    from .space_time_datasets import (
        Raster3DDataset,
        RasterDataset,
        SpaceTimeRaster3DDataset,
        SpaceTimeRasterDataset,
        SpaceTimeVectorDataset,
        VectorDataset,
    )


def dataset_factory(
    type: str, id: str | None
) -> (
    SpaceTimeRasterDataset
    | SpaceTimeRaster3DDataset
    | SpaceTimeVectorDataset
    | RasterDataset
    | Raster3DDataset
    | VectorDataset
    | None
):
    """A factory functions to create space time or map datasets

    The return type is the union of the six classes. The former overloads that
    named the class for each literal type are gone with the table of types
    they repeated; a caller that needs the narrow type asserts it.

    :param type: the dataset type: rast or raster; rast3d, raster3d or raster_3d;
                 vect or vector; strds; str3ds; stvds
    :param id: The id of the dataset ("name@mapset")
    :return: The dataset object, None for an unknown type
    """
    kind = find_kind(type)
    if kind is not None:
        return class_of_kind(kind.name)(id)

    msgr = get_tgis_message_interface()
    msgr.error(_("Unknown dataset type: %s") % type)
    return None
