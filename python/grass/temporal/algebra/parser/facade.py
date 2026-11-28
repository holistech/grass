"""The public parser classes of the temporal algebra

``TemporalRasterAlgebraParser``, ``TemporalRaster3DAlgebraParser`` and
``TemporalVectorAlgebraParser`` are what the tools t.rast.algebra,
t.rast3d.algebra and t.vect.algebra and the addons call. ``parse()`` computes
the expression with the core.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

from grass.temporal.state import get_tgis_message_interface

from . import evaluate
from .granularity import GranularityModeError, common_granularity, dataset_names


class _AlgebraParser:
    """What the three public parser classes share

    The subclasses name the map type. The constructor arguments are kept as
    attributes, so that code which reads or sets ``run`` or ``debug`` after
    the construction keeps working.
    """

    _kind: str

    def __init__(
        self,
        pid: int | None = None,
        run: bool = False,
        debug: bool = True,
        spatial: bool = False,
    ) -> None:
        """Create the parser

        The defaults ``run=False, debug=True`` are those that callers of the
        classes of the releases before GRASS 8.6 relied on.

        :param pid: kept for callers of those releases; the core does not use
            it
        :param run: compute the expression; False only checks its syntax
        :param debug: print the module calls
        :param spatial: relate the maps in space as well as in time, the flag
            -s of the tools
        """
        self.pid = pid
        self.run = run
        self.debug = debug
        self.spatial = spatial
        self.granularity = None
        self.use_granularity = False

    def setup_common_granularity(self, expression, stdstype="strds") -> bool:
        """Use the common granularity of all datasets of the expression

        Finds the space time datasets of the expression, computes the common
        granularity of their maps and samples all datasets with it in
        ``parse()``. The only meaningful temporal relation is then "equal".

        The core reads the names of the datasets from its syntax tree (see
        ``granularity.dataset_names()``), takes the granularity that the
        library stored with the maps and the common granule of the library.
        An expression without any dataset, only single maps of ``map()`` and
        ``tmap()``, has nothing to sample: a warning says so and ``parse()``
        computes it as without the mode.

        After a success ``granularity`` is the common granularity and
        ``use_granularity`` says whether ``parse()`` samples with it; a
        failure leaves both as they were.

        :param expression: The whole statement, ``"R = A + B"``
        :param stdstype: The dataset type of the datasets in the expression
        :return: True if successful, False otherwise (a message tells why)
        :raises SyntaxError: for a statement that the parser of the core
            refuses
        :raises grass.exceptions.FatalError: for a dataset that does not
            exist
        """
        msgr = get_tgis_message_interface()
        if any(brace in expression.partition("=")[2] for brace in "{}"):
            msgr.error(
                _(
                    "Spatio-temporal topological operators are not"
                    " supported in granularity algebra mode"
                )
            )
            return False
        names = dataset_names(expression)
        if not names:
            msgr.warning(
                _(
                    "The expression names no space time dataset; it is computed "
                    "without granularity sampling"
                )
            )
            self.granularity = None
            self.use_granularity = False
            return True
        try:
            self.granularity = common_granularity(names, stdstype)
        except GranularityModeError as error:
            msgr.error(str(error))
            return False
        self.use_granularity = True
        return True

    def _evaluate(self, expression, basename, overwrite, **arguments):
        return evaluate(
            expression,
            kind=self._kind,
            basename=basename,
            overwrite=overwrite,
            run=self.run,
            debug=self.debug,
            spatial=self.spatial,
            **arguments,
        )


class _GriddedAlgebraParser(_AlgebraParser):
    """Raster and 3D raster: the options that the map calculation takes"""

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
        """Create the parser

        :param register_null: register result maps that have only null cells
            (flag -n)
        :param dry_run: plan the maps without computing or registering them
            (flag -d)
        :param nprocs: the number of processes that compute maps
        :param time_suffix: "gran" or "time" names the maps of absolute time
            after their start time; any other value, and any value for
            relative time, numbers them

        The other parameters are those of _AlgebraParser.__init__().
        """
        _AlgebraParser.__init__(self, pid, run, debug, spatial)
        self.register_null = register_null
        self.dry_run = dry_run
        self.nprocs = nprocs
        self.time_suffix = time_suffix

    def parse(self, expression, basename=None, overwrite=False):
        """Parse the expression and compute the result

        The expression is translated onto the core. After
        setup_common_granularity() the datasets are sampled with their common
        granularity.

        :param expression: the assignment, e.g. ``"R = A + B"``
        :param basename: the prefix of the names of the new maps
        :param overwrite: overwrite existing result maps and datasets
        :return: the process chain dictionary; its ``register`` entry lists
            the (name, start, end) of the registered maps
        :raises SyntaxError: for an invalid expression
        :raises ValueError, TypeError: for an expression that cannot be
            computed
        :raises grass.exceptions.FatalError: for a missing dataset or map, and without
            overwrite for an existing result
        """
        return self._evaluate(
            expression,
            basename,
            overwrite,
            dry_run=self.dry_run,
            register_null=self.register_null,
            nprocs=self.nprocs,
            time_suffix=self.time_suffix,
            granularity=self.granularity if self.use_granularity else None,
        )


class TemporalRasterAlgebraParser(_GriddedAlgebraParser):
    """The temporal algebra of space time raster datasets (t.rast.algebra)"""

    _kind = "raster"


class TemporalRaster3DAlgebraParser(_GriddedAlgebraParser):
    """The temporal algebra of space time 3D raster datasets (t.rast3d.algebra)"""

    _kind = "raster3d"


class TemporalVectorAlgebraParser(_AlgebraParser):
    """The temporal algebra of space time vector datasets (t.vect.algebra)"""

    _kind = "vector"

    def parse(self, expression, basename: str | None = None, overwrite: bool = False):
        """Parse the expression and compute the result

        The expression is translated onto the core.

        :param expression: the assignment, e.g. ``"R = A & B"``
        :param basename: the prefix of the names of the new vector maps
        :param overwrite: overwrite existing result maps and datasets
        :return: the process chain dictionary; its ``register`` entry lists
            the (name, start, end) of the registered maps
        :raises SyntaxError: for an invalid expression
        :raises ValueError, TypeError: for an expression that cannot be
            computed
        :raises grass.exceptions.FatalError: for a missing dataset or map, and without
            overwrite for an existing result
        """
        return self._evaluate(expression, basename, overwrite)
