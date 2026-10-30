"""Run the reference implementation of the temporal algebra

The reference implementation (``grass.temporal.classic``) is the
implementation of the classic algebra that tests compare the classic profile
of the algebra core with. The public parser classes choose between the core
and the classic profile in ``parse()`` and run ``-c`` on the profile, so they
never reach the reference; this module builds the parsers of the reference
directly, independent of ``GRASS_TEMPORAL_ALGEBRA``.

``sample_by_dataset`` keeps the sampling of a dataset by the granules of
another in its classic form, which the sampling of
``grass.temporal.related_maps`` is compared with.

The module does not import pytest and does not touch ``os.environ``.

SPDX-FileCopyrightText: 2012-2013, 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import copy

KINDS = ("raster", "raster3d", "vector", "select")


def _reference_class(kind):
    """Return the parser class of the reference for a kind"""
    # Imported on use, so that importing the testing package does not load
    # the parser modules of the algebras a test does not need.
    if kind == "raster":
        from grass.temporal.classic.temporal_raster_algebra import (
            TemporalRasterAlgebraParser,
        )

        return TemporalRasterAlgebraParser
    if kind == "raster3d":
        from grass.temporal.classic.temporal_raster3d_algebra import (
            TemporalRaster3DAlgebraParser,
        )

        return TemporalRaster3DAlgebraParser
    if kind == "vector":
        from grass.temporal.classic.temporal_vector_algebra import (
            TemporalVectorAlgebraParser,
        )

        return TemporalVectorAlgebraParser
    if kind == "select":
        from grass.temporal.classic.temporal_algebra import TemporalAlgebraParser

        return TemporalAlgebraParser
    msg = f"kind is one of {', '.join(KINDS)}, not {kind!r}"
    raise ValueError(msg)


class _SelectReference:
    """The parser of t.select in the reference, with the ``parse`` of the others"""

    def __init__(self, parser, stdstype):
        self._parser = parser
        self._stdstype = stdstype

    def parse(self, expression, basename=None, overwrite=False):
        # Mirrors t.select: the dataset type is the only extra argument.
        return self._parser.parse(
            expression, self._stdstype, basename=basename, overwrite=overwrite
        )

    def __getattr__(self, name):
        return getattr(self._parser, name)


def reference_parser(kind, **options):
    """Create a parser of the reference

    :param kind: ``"raster"``, ``"raster3d"``, ``"vector"`` or ``"select"``
    :param options: Arguments of the constructor of the parser class, such as
        ``run``, ``debug``, ``spatial``, ``register_null``, ``dry_run``,
        ``nprocs`` and ``time_suffix``. The kind ``"select"`` also takes
        ``stdstype`` (default ``"strds"``), the dataset type that t.select
        passes to ``TemporalAlgebraParser.parse``.
    :return: A parser object of the reference, independent of
        ``GRASS_TEMPORAL_ALGEBRA``. Its ``parse`` takes ``(expression,
        basename=None, overwrite=False)`` for every kind; for ``"select"`` the
        dataset type is fixed by ``stdstype``.
    """
    parser_class = _reference_class(kind)
    stdstype = options.pop("stdstype", "strds") if kind == "select" else None
    parser = parser_class(**options)
    if kind == "select":
        return _SelectReference(parser, stdstype)
    return parser


def check_granularity_kind(kind):
    """Raise ValueError for a kind without a granularity mode"""
    if kind not in {"raster", "raster3d", "vector"}:
        msg = (
            f"The granularity mode exists for raster, raster3d and vector, not {kind!r}"
        )
        raise ValueError(msg)


def setup_granularity(parser, kind, expression):
    """Sample the datasets of an expression with their common granularity

    Does what the granularity mode (-g) of t.rast.algebra and t.rast3d.algebra
    does before ``parse()``: ``parser.setup_common_granularity`` with the lexer
    and dataset type of the kind. It works on a parser of the reference and on
    an object of the public parser classes alike, so the algebra core can be
    run in the mode too.

    :param parser: A parser of ``reference_parser`` or an object of a public
        parser class
    :param kind: ``"raster"``, ``"raster3d"`` or ``"vector"``; the tool for
        vector maps has no such mode, the parser has
    :param expression: The whole statement, ``"R = A + B"``
    :raises FatalError: when no common granularity exists (the tool stops with
        "Unable to process the expression in granularity algebra mode")
    :raises ValueError: for kind ``"select"``, which has no such mode
    """
    from grass.exceptions import FatalError
    from grass.temporal.classic.temporal_raster_base_algebra import (
        TemporalRasterAlgebraLexer,
    )
    from grass.temporal.classic.temporal_vector_algebra import (
        TemporalVectorAlgebraLexer,
    )

    check_granularity_kind(kind)
    if kind == "raster":
        arguments = {"stdstype": "strds", "lexer": TemporalRasterAlgebraLexer()}
    elif kind == "raster3d":
        arguments = {"stdstype": "str3ds", "lexer": TemporalRasterAlgebraLexer()}
    else:
        arguments = {"stdstype": "stvds", "lexer": TemporalVectorAlgebraLexer()}
    if not parser.setup_common_granularity(expression=expression, **arguments):
        msg = "Unable to process the expression in granularity algebra mode"
        raise FatalError(msg)


def run_reference(kind, expression, *, basename, overwrite=False, **options):
    """Compute an expression with the reference

    :param kind: ``"raster"``, ``"raster3d"``, ``"vector"`` or ``"select"``
    :param expression: The algebra expression, e.g. ``"R = A + B"``
    :param basename: Prefix of the names of the new maps
    :param overwrite: Overwrite existing result maps and datasets
    :param options: See ``reference_parser``. With ``run=False`` the
        expression is only parsed, which tells accepted from rejected
        expressions. ``granularity=True`` first calls ``setup_granularity``.
    :return: The process chain dictionary, like ``parse()``
    :raises SyntaxError: for expressions that the grammar of the reference
        rejects
    :raises FatalError: see ``setup_granularity``
    """
    granularity = options.pop("granularity", False)
    parser = reference_parser(kind, **options)
    if granularity:
        setup_granularity(parser, kind, expression)
    return parser.parse(expression, basename=basename, overwrite=overwrite)


def _maps_with_gaps_classic(sampler, where, dbif):
    """List the maps of sampler by start time with a gap map between neighbours

    The classic rule of get_registered_maps_as_objects_with_gaps(), which the
    reference keeps: a gap is only inserted between two adjacent maps, and
    never next to a map without time or one that ends before it starts. The
    method of the library passes over a map without start time instead and
    puts the gap before the next map with one.

    :return: The map objects with the gaps (maps with id None) in between
    """
    from grass.temporal.topology import reversed_map_ids

    maps = sampler.get_registered_maps_as_objects(where, "start_time", dbif)
    obj_list = []
    if not maps:
        return obj_list
    reversed_ids = reversed_map_ids(maps)
    for i, map_ in enumerate(maps):
        obj_list.append(map_)
        if (
            i < len(maps) - 1
            and reversed_ids.isdisjoint((map_.get_id(), maps[i + 1].get_id()))
            and maps[i + 1].temporal_relation(map_) == "after"
        ):
            start1, end1 = map_.get_temporal_extent_as_tuple()
            end = maps[i + 1].get_temporal_extent_as_tuple()[0]
            start = end1 if end1 is not None else start1
            gap = sampler.get_new_map_instance(None)
            if sampler.is_time_absolute():
                gap.set_absolute_time(start, end)
            elif sampler.is_time_relative():
                gap.set_relative_time(start, end, sampler.get_relative_time_unit())
            gap.set_spatial_extent_from_values(0, 0, 0, 0, 0, 0)
            obj_list.append(copy.copy(gap))
    return obj_list


def _sampling_relations(method):
    """Return the upper case relation names that the sampling methods select

    "start", "overlap" and "contain" are shorthands for several relations
    of the topology builder and are replaced by them; "over" only adds
    relations and stays in the list as "OVER".
    """
    relations = copy.deepcopy(method)

    if "start" in relations:
        for name in ("overlapped", "starts", "started", "finishes", "contains"):
            if name not in relations:
                relations.append(name)
        if "equals" not in relations:
            relations.append("equals")

    if "overlap" in relations or "over" in relations:
        for name in ("overlapped", "overlaps"):
            if name not in relations:
                relations.append(name)

    if "contain" in relations and "contains" not in relations:
        relations.append("contains")

    return [
        relation.upper().strip()
        for relation in relations
        if relation not in {"start", "overlap", "contain"}
    ]


def sample_by_dataset(stds, sampler, method, spatial=False, dbif=None, where=None):
    """Sample a dataset with the granules of a sampler dataset, the classic way

    This is the classic AbstractSpaceTimeDataset.sample_by_dataset(), kept so
    that t.sample, t.rast.mapcalc, t.rast3d.mapcalc and
    sample_stds_by_stds_topology(), which take their granules and related maps
    from grass.temporal.related_maps, are compared with it.

    The sampler must have interval time and the temporal type of stds,
    otherwise the function reports an error and returns None. A gap between
    the maps of the sampler is a granule whose map has no identifier. Each
    entry of the result is a dictionary with the map object of the "granule"
    and the list of its "samples"; a granule without a related map has one
    sample without identifier and with the extents of the granule.

    The methods are "start", "during", "overlap", "contain", "equal",
    "follows" and "precedes" as names of the standard option, or relation
    names of the topology builder in lower case. "start" appends the relation
    "equals", which the topology builder never files (it files "EQUAL"), so
    that "start" finds no map of the same time as a granule. That is the
    measured behaviour, which related_maps keeps (see there).

    :param stds: The space time dataset to sample
    :param sampler: The space time dataset whose maps are the granules
    :param method: A list of method names
    :param spatial: If True a map must also overlap the granule in 2D
    :param dbif: The database interface to be used
    :param where: Temporal WHERE condition to filter the maps of both datasets
    :return: A list of dictionaries, None if the datasets cannot be sampled
    """
    from grass.temporal.db import connection
    from grass.temporal.topology import SpatioTemporalTopologyBuilder

    if stds.get_temporal_type() != sampler.get_temporal_type():
        stds.msgr.error(_("The space time datasets must be of the same temporal type"))
        return None

    if sampler.get_map_time() != "interval":
        stds.msgr.error(
            _("The temporal map type of the sample dataset must be interval")
        )
        return None

    with connection(dbif) as dbif:
        relations = _sampling_relations(method)

        mapsA = stds.get_registered_maps_as_objects(where=where, dbif=dbif)
        mapsB = _maps_with_gaps_classic(sampler, where, dbif)
        SpatioTemporalTopologyBuilder().build(mapsB, mapsA, "2D" if spatial else None)

        obj_list = []
        for granule in mapsB:
            map_relations = granule.get_temporal_relations()

            # Append the maps that fulfill the relations
            maplist = []
            for relation in relations:
                if relation in map_relations:
                    for sample_map in map_relations[relation]:
                        if sample_map not in maplist:
                            maplist.append(sample_map)

            # Add an empty map if no map was found
            if not maplist:
                empty_map = stds.get_new_map_instance(None)
                empty_map.set_spatial_extent(granule.get_spatial_extent())
                empty_map.set_temporal_extent(granule.get_temporal_extent())
                maplist.append(empty_map)

            obj_list.append({"granule": granule, "samples": maplist})

        return obj_list
