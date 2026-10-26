"""!@package grass.temporal

Temporal raster algebra

SPDX-FileCopyrightText: 2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Thomas Leppelt and Soeren Gebbert

"""

from __future__ import annotations

from grass.temporal.space_time_datasets import Raster3DDataset
from .temporal_raster_base_algebra import TemporalRasterBaseAlgebraParser


class TemporalRaster3DAlgebraParser(TemporalRasterBaseAlgebraParser):
    """The classic temporal 3D raster algebra engine

    The defaults ``run=False, debug=True`` differ from the base class: they are
    those of the public parser class that this engine used to be.
    """

    _default_stdstype = "str3ds"
    _default_maptype = "raster_3d"
    _default_mapclass = Raster3DDataset

    def __init__(
        self,
        pid: int | None = None,
        run: bool = False,
        debug: bool = True,
        spatial: bool = False,
        register_null: bool = False,
        dry_run: bool = False,
        nprocs: int = 1,
        time_suffix=None,
    ) -> None:
        TemporalRasterBaseAlgebraParser.__init__(
            self,
            pid=pid,
            run=run,
            debug=debug,
            spatial=spatial,
            register_null=register_null,
            dry_run=dry_run,
            nprocs=nprocs,
            time_suffix=time_suffix,
        )

    def _create_mapcalc_module(self, spatial):
        """Return the not yet executed r3.mapcalc module"""
        return self._new_module("r3.mapcalc")

    def p_ts_neighbor_operation(self, t) -> None:
        # Examples:
        # A[1,0,-1]
        # B[-2]
        # C[1,-2,1,3]
        """
        expr : stds L_SPAREN number COMMA number COMMA number R_SPAREN
             | stds L_SPAREN number R_SPAREN
             | stds L_SPAREN number COMMA number COMMA number COMMA number R_SPAREN
        """
        if not self.run:
            t[0] = self._dry_name(t[1])
            return
        # One index is the temporal, three are the row, column and depth offset
        if len(t) == 5:
            temporal_offset, spatial_offsets = t[3], ()
        elif len(t) == 9:
            temporal_offset, spatial_offsets = 0, (t[3], t[5], t[7])
        else:
            temporal_offset, spatial_offsets = t[9], (t[3], t[5], t[7])
        t[0] = self._neighbour_maps(t[1], temporal_offset, spatial_offsets)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
