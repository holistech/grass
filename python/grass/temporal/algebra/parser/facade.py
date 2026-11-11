"""The public parser classes of the temporal algebra

``TemporalRasterAlgebraParser``, ``TemporalRaster3DAlgebraParser`` and
``TemporalVectorAlgebraParser`` are what the tools t.rast.algebra,
t.rast3d.algebra and t.vect.algebra and the addons call. ``parse()`` computes
the expression with the core or, if the classic algebra is selected, with the
classic profile (see ``switch.classic_selected``).

Each class keeps an object of the class of the reference implementation
(``grass.temporal.classic``) for its map type, built only when something asks
for it: ``setup_common_granularity()`` of the classic algebra is computed by
the reference, and an attribute that the facade does not have is read from
the reference object, so that code written for the classes of the reference
keeps working. The object gets the arguments of the constructor of the
facade. The facade does not inherit from the reference, so that the reference
stays as it is, the implementation that tests compare the classic profile
with. This module imports the three classes of the reference, so
``import grass.temporal`` loads ``grass.temporal.classic``.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

from grass.temporal.algebra.profile import CORE
from grass.temporal.classic.temporal_raster3d_algebra import (
    TemporalRaster3DAlgebraParser as _Raster3DReference,
)
from grass.temporal.classic.temporal_raster_algebra import (
    TemporalRasterAlgebraParser as _RasterReference,
)
from grass.temporal.classic.temporal_raster_base_algebra import (
    TemporalRasterAlgebraLexer,
)
from grass.temporal.classic.temporal_vector_algebra import (
    TemporalVectorAlgebraLexer,
    TemporalVectorAlgebraParser as _VectorReference,
)
from grass.temporal.state import get_tgis_message_interface

from . import evaluate
from .granularity import GranularityModeError, common_granularity, dataset_names
from .switch import classic_selected


class _AlgebraParser:
    """What the three public parser classes share

    The subclasses name the class of the reference, the class of the lexer
    that the reference finds the datasets of the granularity mode with, and
    the map type. The
    constructor arguments are kept as attributes with the same names that
    the reference has, so that code which reads or sets ``run`` or ``debug``
    after the construction keeps working. They are handed to the reference
    object again each time it is asked for.
    """

    _reference_class: type
    _reference_lexer: type
    _kind: str
    _options = ("pid", "run", "debug", "spatial")

    def __init__(
        self,
        pid: int | None = None,
        run: bool = False,
        debug: bool = True,
        spatial: bool = False,
        classic: bool | None = None,
    ) -> None:
        """Create the parser

        The defaults ``run=False, debug=True`` are those of the classes of the
        reference, so that a caller written for them gets the same behaviour.

        :param pid: the process id in the names of the temporary maps of the
            reference object; the core does not use it
        :param run: compute the expression; False only checks its syntax
        :param debug: print the module calls
        :param spatial: relate the maps in space as well as in time, the flag
            -s of the tools
        :param classic: True selects the classic algebra, False the core;
            None follows the environment variable GRASS_TEMPORAL_ALGEBRA,
            whose default is the core
        """
        self.pid = pid
        self.run = run
        self.debug = debug
        self.spatial = spatial
        self.classic = classic
        self.granularity = None
        self.use_granularity = False
        self._reference_object = None

    def _reference(self):
        """Return the reference object, built with the current options"""
        if self._reference_object is None:
            self._reference_object = self._reference_class(
                **self._reference_arguments()
            )
        else:
            # Options set after the construction reach the reference too.
            for name in self._options:
                setattr(self._reference_object, name, getattr(self, name))
        return self._reference_object

    def _reference_arguments(self) -> dict:
        return {name: getattr(self, name) for name in self._options}

    def __getattr__(self, name):
        """Hand everything the facade does not have to the reference"""
        # Called only for names not found on the facade. A name with an
        # underscore must not build a reference object: copy and pickle look for
        # __getstate__ and the like on an object that has no attributes yet.
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._reference(), name)

    def __dir__(self):
        # The names of the class of the reference too, so that dir() lists
        # what __getattr__ reads from it. The attributes that the reference
        # object sets in its constructor are only listed once it exists.
        names = set(super().__dir__()) | set(dir(self._reference_class))
        if self._reference_object is not None:
            names |= set(vars(self._reference_object))
        return sorted(names)

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
        computes it as without the mode. The classic algebra computes the
        mode with the reference implementation, which computes the
        granularity of each dataset and their common granule with its own
        copies of the functions of the library.

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
        if self._classic():
            return self._classic_granularity(expression, stdstype)
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

    def _classic_granularity(self, expression, stdstype) -> bool:
        """setup_common_granularity() of the reference, for the classic algebra

        The reference finds the dataset names with the lexer of the classic
        algebra of the map type, the one that t.rast.algebra and
        t.rast3d.algebra gave it.
        """
        reference = self._reference()
        succeeded = reference.setup_common_granularity(
            expression=expression,
            stdstype=stdstype,
            lexer=self._reference_lexer(),
        )
        if succeeded:
            self.granularity = reference.granularity
            self.use_granularity = reference.use_granularity
        return succeeded

    def _classic(self) -> bool:
        return classic_selected(self.classic)

    def _evaluate(self, expression, basename, overwrite, **arguments):
        profile = CORE
        if self._classic():
            # Imported here: import grass.temporal loads this module, and the
            # classic profile with its grammar and production tables is only
            # needed when the classic algebra is selected.
            from .classic import CLASSIC

            profile = CLASSIC
        return evaluate(
            expression,
            kind=self._kind,
            basename=basename,
            overwrite=overwrite,
            run=self.run,
            debug=self.debug,
            spatial=self.spatial,
            profile=profile,
            **arguments,
        )


class _GriddedAlgebraParser(_AlgebraParser):
    """Raster and 3D raster: the options that the map calculation takes"""

    _options = (
        *_AlgebraParser._options,
        "register_null",
        "dry_run",
        "nprocs",
        "time_suffix",
    )

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
        _AlgebraParser.__init__(self, pid, run, debug, spatial, classic)
        self.register_null = register_null
        self.dry_run = dry_run
        self.nprocs = nprocs
        self.time_suffix = time_suffix

    def parse(self, expression, basename=None, overwrite=False):
        """Parse the expression and compute the result

        The expression is translated onto the core, with the rules of the core
        or, if the classic algebra is selected (see __init__), with those of
        the classic profile. After setup_common_granularity() both sample the
        datasets with their common granularity.

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
    """The temporal algebra of space time raster datasets (t.rast.algebra)

    parse() computes an expression with the core or with the classic profile,
    as the option classic of the constructor selects.
    """

    _reference_class = _RasterReference
    _reference_lexer = TemporalRasterAlgebraLexer
    _kind = "raster"


class TemporalRaster3DAlgebraParser(_GriddedAlgebraParser):
    """The temporal algebra of space time 3D raster datasets (t.rast3d.algebra)

    parse() computes an expression with the core or with the classic profile,
    as the option classic of the constructor selects.
    """

    _reference_class = _Raster3DReference
    _reference_lexer = TemporalRasterAlgebraLexer
    _kind = "raster3d"


class TemporalVectorAlgebraParser(_AlgebraParser):
    """The temporal algebra of space time vector datasets (t.vect.algebra)

    parse() computes an expression with the core or with the classic profile,
    as the option classic of the constructor selects.
    """

    _reference_class = _VectorReference
    _reference_lexer = TemporalVectorAlgebraLexer
    _kind = "vector"

    def parse(self, expression, basename: str | None = None, overwrite: bool = False):
        """Parse the expression and compute the result

        The expression is translated onto the core, with the rules of the core
        or, if the classic algebra is selected (see __init__), with those of
        the classic profile.

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
