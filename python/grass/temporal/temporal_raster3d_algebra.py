"""!@package grass.temporal

Temporal raster algebra

SPDX-FileCopyrightText: 2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Thomas Leppelt and Soeren Gebbert

"""

from __future__ import annotations

from .algebra.parser import evaluate
from .algebra.parser.switch import classic_selected
from .space_time_datasets import Raster3DDataset
from .temporal_raster_base_algebra import TemporalRasterBaseAlgebraParser


class TemporalRaster3DAlgebraParser(TemporalRasterBaseAlgebraParser):
    """The temporal raster algebra class"""

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
        classic: bool | None = None,
    ) -> None:
        """Create the parser; the defaults ``run=False, debug=True`` differ from
        the base class and are kept for compatibility with existing callers

        classic selects the classic algebra of this module (True) or the
        algebra core (False); None follows the environment variable
        GRASS_TEMPORAL_ALGEBRA, whose default is the core.
        """
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
        self.classic = classic

    def parse(self, expression, basename=None, overwrite=False):
        """Parse the expression and compute the result

        The expression is translated onto grass.temporal.algebra, with the
        rules of the core or, if the classic algebra is selected (see
        __init__), with those of its classic profile. After
        setup_common_granularity() both sample the datasets with their common
        granularity.

        :return: the process chain dictionary
        """
        # Loaded on use: the classic profile imports the classic lexers,
        # which live in modules that import this one.
        from .algebra.profile import CLASSIC, CORE

        return evaluate(
            expression,
            kind="raster3d",
            basename=basename,
            overwrite=overwrite,
            run=self.run,
            dry_run=self.dry_run,
            debug=self.debug,
            spatial=self.spatial,
            register_null=self.register_null,
            nprocs=self.nprocs,
            time_suffix=self.time_suffix,
            granularity=self.granularity if self.use_granularity else None,
            profile=CLASSIC if self._classic() else CORE,
        )

    def _classic(self):
        return classic_selected(self.classic)

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
