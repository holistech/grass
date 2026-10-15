"""Run the earlier implementation of the temporal algebra

The classic algebra of the parser classes in ``temporal_raster_algebra``,
``temporal_raster3d_algebra``, ``temporal_vector_algebra`` and
``temporal_algebra`` is the reference that tests compare the classic profile
of the algebra core with. The parser classes choose between the core and the
classic algebra in ``parse()``; once ``-c`` runs on the profile, that
``parse()`` no longer reaches the earlier implementation. This module therefore
calls the parse method of the base classes (or ``_parse_classic``) directly,
independent of ``GRASS_TEMPORAL_ALGEBRA`` and of the ``classic`` argument.

The module does not import pytest and does not touch ``os.environ``.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import functools

KINDS = ("raster", "raster3d", "vector", "select")


def _classes(kind):
    """Return the parser class and the unbound earlier ``parse`` of a kind"""
    # Imported on use, so that importing the testing package does not load
    # the parser modules of the algebras a test does not need.
    if kind == "raster":
        from grass.temporal.temporal_raster_algebra import TemporalRasterAlgebraParser
        from grass.temporal.temporal_raster_base_algebra import (
            TemporalRasterBaseAlgebraParser,
        )

        return TemporalRasterAlgebraParser, TemporalRasterBaseAlgebraParser.parse
    if kind == "raster3d":
        from grass.temporal.temporal_raster3d_algebra import (
            TemporalRaster3DAlgebraParser,
        )
        from grass.temporal.temporal_raster_base_algebra import (
            TemporalRasterBaseAlgebraParser,
        )

        return TemporalRaster3DAlgebraParser, TemporalRasterBaseAlgebraParser.parse
    if kind == "vector":
        from grass.temporal.temporal_vector_algebra import TemporalVectorAlgebraParser

        return TemporalVectorAlgebraParser, TemporalVectorAlgebraParser._parse_classic
    if kind == "select":
        from grass.temporal.temporal_algebra import TemporalAlgebraParser

        return TemporalAlgebraParser, TemporalAlgebraParser.parse
    msg = f"kind is one of {', '.join(KINDS)}, not {kind!r}"
    raise ValueError(msg)


def reference_parser(kind, **options):
    """Create a parser of the earlier implementation

    :param kind: ``"raster"``, ``"raster3d"``, ``"vector"`` or ``"select"``
    :param options: Arguments of the constructor of the parser class, such as
        ``run``, ``debug``, ``spatial``, ``register_null``, ``dry_run``,
        ``nprocs`` and ``time_suffix``. The kind ``"select"`` also takes
        ``stdstype`` (default ``"strds"``), the dataset type that t.select
        passes to ``TemporalAlgebraParser.parse``.
    :return: The parser instance. Its ``parse`` always runs the earlier
        implementation: the method is bound on the instance, so it stays so
        when the class method is routed elsewhere. It takes ``(expression,
        basename=None, overwrite=False)`` for every kind; for ``"select"`` the
        dataset type is fixed by ``stdstype``.
    """
    parser_class, earlier_parse = _classes(kind)
    stdstype = options.pop("stdstype", "strds") if kind == "select" else None
    if kind in {"raster", "raster3d", "vector"}:
        options["classic"] = True
    parser = parser_class(**options)
    bound = functools.partial(earlier_parse, parser)
    if kind == "select":

        def parse(expression, basename=None, overwrite=False):
            # Mirrors t.select: the dataset type is the only extra argument.
            return bound(expression, stdstype, basename=basename, overwrite=overwrite)

        parser.parse = parse
    else:
        parser.parse = bound
    return parser


def run_reference(kind, expression, *, basename, overwrite=False, **options):
    """Compute an expression with the earlier implementation

    :param kind: ``"raster"``, ``"raster3d"``, ``"vector"`` or ``"select"``
    :param expression: The algebra expression, e.g. ``"R = A + B"``
    :param basename: Prefix of the names of the new maps
    :param overwrite: Overwrite existing result maps and datasets
    :param options: See ``reference_parser``. With ``run=False`` the
        expression is only parsed, which tells accepted from rejected
        expressions.
    :return: The process chain dictionary, like ``parse()``
    :raises SyntaxError: for expressions that the earlier grammar rejects
    """
    parser = reference_parser(kind, **options)
    return parser.parse(expression, basename=basename, overwrite=overwrite)
