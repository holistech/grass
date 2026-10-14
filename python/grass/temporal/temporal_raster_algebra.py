"""!@package grass.temporal

Temporal raster algebra

SPDX-FileCopyrightText: 2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Thomas Leppelt and Soeren Gebbert

.. code-block:: pycon

    >>> p = TemporalRasterAlgebraLexer()
    >>> p.build()
    >>> p.debug = True
    >>> expression = "R = A[0,1,0] / B[0,0,1] * 20 + C[0,1,1] - 2.45"
    >>> p.test(expression)
    R = A[0,1,0] / B[0,0,1] * 20 + C[0,1,1] - 2.45
    LexToken(NAME,'R',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'A',1,4)
    LexToken(L_SPAREN,'[',1,5)
    LexToken(INT,0,1,6)
    LexToken(COMMA,',',1,7)
    LexToken(INT,1,1,8)
    LexToken(COMMA,',',1,9)
    LexToken(INT,0,1,10)
    LexToken(R_SPAREN,']',1,11)
    LexToken(DIV,'/',1,13)
    LexToken(NAME,'B',1,15)
    LexToken(L_SPAREN,'[',1,16)
    LexToken(INT,0,1,17)
    LexToken(COMMA,',',1,18)
    LexToken(INT,0,1,19)
    LexToken(COMMA,',',1,20)
    LexToken(INT,1,1,21)
    LexToken(R_SPAREN,']',1,22)
    LexToken(MULT,'*',1,24)
    LexToken(INT,20,1,26)
    LexToken(ADD,'+',1,29)
    LexToken(NAME,'C',1,31)
    LexToken(L_SPAREN,'[',1,32)
    LexToken(INT,0,1,33)
    LexToken(COMMA,',',1,34)
    LexToken(INT,1,1,35)
    LexToken(COMMA,',',1,36)
    LexToken(INT,1,1,37)
    LexToken(R_SPAREN,']',1,38)
    LexToken(SUB,'-',1,40)
    LexToken(FLOAT,2.45,1,42)

"""

from __future__ import annotations

from .algebra.parser import evaluate
from .algebra.parser.switch import (  # noqa: F401, imported by callers and tests
    ALGEBRA_VARIABLE,
    DEFAULT_ALGEBRA,
    classic_selected,
)
from .temporal_raster_base_algebra import (
    TemporalRasterAlgebraLexer,  # noqa: F401, used by the doctest above
    TemporalRasterBaseAlgebraParser,
)


class TemporalRasterAlgebraParser(TemporalRasterBaseAlgebraParser):
    """The temporal raster algebra class"""

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

        classic selects the classic algebra of this module (True) or the core
        (False); None follows the environment variable GRASS_TEMPORAL_ALGEBRA.
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

        The expression is translated onto grass.temporal.algebra, unless the
        classic algebra of this module is selected (see __init__). After
        setup_common_granularity() both algebras sample the datasets with
        their common granularity.

        :return: the process chain dictionary
        """
        if self._classic():
            return super().parse(expression, basename, overwrite)
        return evaluate(
            expression,
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
        )

    def _classic(self):
        return classic_selected(self.classic)

    def p_ts_neighbour_operation(self, t) -> None:
        # Spatial and temporal neighbour operations via indexing
        # Examples:
        # A[1,0]
        # B[-2]
        # C[-2,1,3]
        """
        expr : stds L_SPAREN number COMMA number R_SPAREN
             | stds L_SPAREN number R_SPAREN
             | stds L_SPAREN number COMMA number COMMA number R_SPAREN
        """
        if not self.run:
            t[0] = self._dry_name(t[1])
            return
        # One index is the temporal, two are the row and column offset
        if len(t) == 5:
            temporal_offset, spatial_offsets = t[3], ()
        elif len(t) == 7:
            temporal_offset, spatial_offsets = 0, (t[3], t[5])
        else:
            temporal_offset, spatial_offsets = t[7], (t[3], t[5])
        t[0] = self._neighbour_maps(t[1], temporal_offset, spatial_offsets)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
