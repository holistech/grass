"""The public parser classes of the temporal algebra

``TemporalRasterAlgebraParser``, ``TemporalRaster3DAlgebraParser`` and
``TemporalVectorAlgebraParser`` are what the tools t.rast.algebra,
t.rast3d.algebra and t.vect.algebra and the addons call. ``parse()`` computes
the expression with the algebra core or, if the classic algebra is selected,
with its classic profile (see ``switch.classic_selected``). Neither needs the
classic engine in ``grass.temporal.classic``.

The engine is only built when something asks for it: the granularity mode
(``setup_common_granularity``) and attributes that only the engine has. It
gets the arguments of the constructor of the facade. The facade does not
inherit from the engine, so that the engine stays what it was written as, the
reference of the classic algebra, and the core does not depend on it.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

from grass.temporal.algebra.profile import CORE
from grass.temporal.classic.temporal_raster3d_algebra import (
    TemporalRaster3DAlgebraParser as _Raster3DEngine,
)
from grass.temporal.classic.temporal_raster_algebra import (
    TemporalRasterAlgebraParser as _RasterEngine,
)
from grass.temporal.classic.temporal_vector_algebra import (
    TemporalVectorAlgebraParser as _VectorEngine,
)

from . import evaluate
from .switch import classic_selected


class _AlgebraParser:
    """What the three parser classes share; the subclasses name the engine

    The constructor arguments are kept as attributes with the same names that
    the engine has, so that code which reads or sets ``run`` or ``debug`` after
    the construction keeps working. They are handed to the engine again each
    time it is asked for.
    """

    _engine_class: type
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

        The defaults ``run=False, debug=True`` are those of the parser classes
        before the engine was separated.

        classic selects the classic algebra (True) or the algebra core (False);
        None follows the environment variable GRASS_TEMPORAL_ALGEBRA, whose
        default is the core.
        """
        self.pid = pid
        self.run = run
        self.debug = debug
        self.spatial = spatial
        self.classic = classic
        self._engine_object = None

    def _engine(self):
        """Return the classic engine, built with the current options"""
        if self._engine_object is None:
            self._engine_object = self._engine_class(**self._engine_arguments())
        else:
            # Options set after the construction reach the engine too.
            for name in self._options:
                setattr(self._engine_object, name, getattr(self, name))
        return self._engine_object

    def _engine_arguments(self) -> dict:
        return {name: getattr(self, name) for name in self._options}

    def __getattr__(self, name):
        """Hand everything the facade does not have to the engine"""
        # Called only for names not found on the facade. A name with an
        # underscore must not build an engine: copy and pickle look for
        # __getstate__ and the like on an object that has no attributes yet.
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._engine(), name)

    def __dir__(self):
        # The names of the engine class, which this class used to inherit.
        # The attributes that an engine object sets in its constructor are only
        # listed once the engine exists.
        names = set(super().__dir__()) | set(dir(self._engine_class))
        if self._engine_object is not None:
            names |= set(vars(self._engine_object))
        return sorted(names)

    @property
    def granularity(self):
        """The common granularity of the granularity mode, None before it"""
        return None if self._engine_object is None else self._engine_object.granularity

    @property
    def use_granularity(self) -> bool:
        """True after ``setup_common_granularity`` succeeded"""
        return self._engine_object is not None and self._engine_object.use_granularity

    def setup_common_granularity(
        self, expression, stdstype="strds", lexer=None
    ) -> bool:
        """Use the common granularity of all datasets of the expression

        Analyzes the expression for space time datasets, computes the common
        granularity of their maps and samples all datasets with it in
        ``parse()``. The only meaningful temporal relation is then "equal".

        :param expression: The whole statement, ``"R = A + B"``
        :param stdstype: The dataset type of the datasets in the expression
        :param lexer: The lexer that finds the dataset names, the one of the
            map type of the tool
        :return: True if successful, False otherwise (a message tells why)
        """
        return self._engine().setup_common_granularity(
            expression=expression, stdstype=stdstype, lexer=lexer
        )

    def _classic(self) -> bool:
        return classic_selected(self.classic)

    def _evaluate(self, expression, basename, overwrite, **arguments):
        # Imported here: import grass.temporal loads this module, and the
        # classic profile with its grammar and production tables is only
        # needed when the classic algebra is selected.
        from .classic import CLASSIC

        return evaluate(
            expression,
            kind=self._kind,
            basename=basename,
            overwrite=overwrite,
            run=self.run,
            debug=self.debug,
            spatial=self.spatial,
            profile=CLASSIC if self._classic() else CORE,
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
        _AlgebraParser.__init__(self, pid, run, debug, spatial, classic)
        self.register_null = register_null
        self.dry_run = dry_run
        self.nprocs = nprocs
        self.time_suffix = time_suffix

    def parse(self, expression, basename=None, overwrite=False):
        """Parse the expression and compute the result

        The expression is translated onto grass.temporal.algebra, with the
        rules of the core or, if the classic algebra is selected (see
        __init__), with those of its classic profile. After
        setup_common_granularity() both sample the datasets with their common
        granularity.

        :return: the process chain dictionary
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
    """The temporal raster algebra class"""

    _engine_class = _RasterEngine
    _kind = "raster"


class TemporalRaster3DAlgebraParser(_GriddedAlgebraParser):
    """The temporal 3D raster algebra class"""

    _engine_class = _Raster3DEngine
    _kind = "raster3d"


class TemporalVectorAlgebraParser(_AlgebraParser):
    """The temporal vector algebra class"""

    _engine_class = _VectorEngine
    _kind = "vector"

    def parse(self, expression, basename: str | None = None, overwrite: bool = False):
        """Parse the expression and run the computation

        The expression is translated onto grass.temporal.algebra, with the
        rules of the core or, if the classic algebra is selected (see
        __init__), with those of its classic profile.

        :param expression: The assignment, e.g. ``"R = A & B"``
        :param basename: Prefix of the names of the new vector maps
        :param overwrite: Overwrite existing result maps and datasets
        :return: The process chain dictionary; its ``register`` entry lists the
            (name, start, end) of the registered maps
        :raises SyntaxError: for invalid expressions
        """
        return self._evaluate(expression, basename, overwrite)
