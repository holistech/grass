"""The syntax of the temporal algebra on the core of grass.temporal.algebra

The parser reads an expression such as ``C = A {+,during} B`` into a syntax
tree, and the translator turns the tree into calls of the core operations.
evaluate() computes an expression for the public parser classes and t.select,
and returns the process chain dictionary in the form of the reference
implementation (grass.temporal.classic).

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import functools

from grass.exceptions import FatalError
from grass.temporal.algebra import time_functions
from grass.temporal.algebra.maptypes import ELEMENTS, KINDS_OF_STDS, STDS_TYPES
from grass.temporal.algebra.materialize import check_absent, materialize, plan
from grass.temporal.algebra.profile import CORE
from grass.temporal.algebra.sources import source
from grass.temporal.state import get_current_mapset

from . import translate
from .grammar import parse as _parse_core
from .granularity import sample_by_granularity
from .translate import Translator

__all__ = ["Translator", "evaluate", "parse"]

# The public parser classes take "num" for numbered map names; the core takes
# None.
_TIME_SUFFIXES = ("gran", "time")


def parse(text, *, grammar=None):
    """Return the syntax tree of the statement "name = expression"

    :param grammar: an object with parse(text) that returns the tree of the
        statement; None reads the syntax of the core
    :raises SyntaxError: with the position of the first error
    """
    return (_parse_core if grammar is None else grammar.parse)(text)


def evaluate(
    expression,
    *,
    kind="raster",
    basename=None,
    overwrite=False,
    run=True,
    dry_run=False,
    debug=False,
    spatial=False,
    register_null=False,
    nprocs=1,
    time_suffix=None,
    granularity=None,
    selection=False,
    profile=CORE,
):
    """Parse, translate and compute "name = expression"

    Without run only the syntax is checked. With dry_run the maps are
    planned but neither computed nor registered; without overwrite it still
    stops at an existing result, as the run would. debug prints the module
    calls.

    With granularity every space time dataset of the expression is sampled
    with this common granularity before the translation, as in the
    granularity mode of t.rast.algebra; the caller has checked the
    expression with setup_common_granularity() of the public parser classes.

    With selection no map is computed: every result slot must be a registered
    map, which is registered unchanged or, when a temporal operator retimed
    it, copied with g.copy, as a selection needs it (see plan()).

    :param kind: the map type, "raster", "raster3d" or "vector"
    :param profile: the variant of the algebra: its grammar reads the
        expression and its translator class translates the tree; the default
        is the algebra of the core. A grammar of a variant that reads
        different syntax per map type has for_kind(kind, selection), which
        returns the object with parse(text) for this expression.
    :param granularity: the common granularity of the datasets, a text such
        as "1 day" for absolute time or a whole number for relative time;
        None reads the datasets as they are
    :return: the process chain dictionary of the public parser classes:
        "processes" in the form of Module.get_dict(), "register" as (name,
        start, end) strings, "remove" and "STDS"
    :raises SyntaxError: for an error in the expression
    :raises ValueError, TypeError: as the core operations, for an expression
        that cannot be computed
    :raises FatalError: for a missing dataset or map, and without overwrite
        for an existing result dataset or map
    """
    grammar = profile.grammar
    if hasattr(grammar, "for_kind"):
        grammar = grammar.for_kind(kind, selection)
    statement = parse(expression, grammar=grammar)
    chain = {"processes": [], "register": [], "remove": [], "STDS": {}}
    if not run:
        return chain
    types = _TemporalTypes(profile.one_temporal_type)
    resolve = _resolver(kind, profile, granularity, types)
    translator = (profile.translator or Translator)(
        kind=kind,
        spatial=spatial,
        resolve=resolve,
        profile=profile,
        selection=selection,
    )
    try:
        name, series = translator.statement(statement)
        planned = plan(
            series,
            name,
            basename=basename,
            time_suffix=time_suffix if time_suffix in _TIME_SUFFIXES else None,
            selection=selection,
            # Known only now, after the datasets are read
            temporal_type=types.first if profile.empty_result_type_from_input else None,
            mapcalc=profile.mapcalc,
            union_region=profile.union_region_when_spatial and spatial,
            list_order=profile.list_order,
            copies_by_position=profile.copies_by_position,
            last_of_equal_names=profile.last_of_equal_names,
        )
        # A vector result without maps has no dataset, if the profile says so.
        # A selection always creates its dataset, as t.select.md promises for
        # both algebras. The reference creates none for an empty selection of
        # vector maps; the classic profile follows the manual instead.
        dataset_if_empty = profile.vector_dataset_if_empty or selection
        if dataset_if_empty or kind != "vector" or planned.maps:
            chain["STDS"] = {
                "name": name,
                # The type the run creates, so that a dry run shows what the
                # run makes. The reference plans the type of the call, also
                # where a mixed selection creates another one.
                "stdstype": planned.stds_type,
                "temporal_type": planned.temporal_type,
            }
        chain["processes"] = [
            _as_process_dict(call, overwrite) for call in planned.processes
        ]
        chain["register"] = [
            (map_name, str(start), str(end))
            for map_name, start, end in planned.register
        ]
        if planned.remove:
            chain["remove"] = [
                {
                    "name": "g.remove",
                    "inputs": [
                        ("type", ELEMENTS[KINDS_OF_STDS[planned.stds_type]]),
                        ("name", ",".join(planned.remove)),
                    ],
                    "outputs": [],
                    "flags": ["f"],
                }
            ]
        if debug:
            for call in planned.processes:
                print(_command(call))
        if dry_run:
            if not overwrite:
                check_absent(planned, classic=profile.classic_absence_check)
        else:
            materialize(
                series,
                name,
                overwrite=overwrite,
                register_null=register_null,
                nprocs=int(nprocs),
                classic_absence_check=profile.classic_absence_check,
                keep_empty_vector_maps=profile.keep_empty_vector_maps,
                vector_dataset_if_empty=dataset_if_empty,
                chain=planned,
            )
    except ValueError as error:
        mapped = _classic_error(error) if profile.classic_errors else None
        if mapped is None:
            raise
        raise mapped from error
    return chain


class _TemporalTypes:
    """The temporal type of the first dataset with maps that an expression reads

    A dataset without maps has no temporal type and is passed over, as is a
    single map, which the reference does not check either.
    """

    def __init__(self, refuse_others):
        self.first = None
        self._refuse_others = refuse_others

    def watch(self, resolve):
        """Return resolve, noting the temporal type of the series it gives"""

        def read(name, *args, **keywords):
            series = resolve(name, *args, **keywords)
            if series.temporal_type is None:
                return series
            if self.first is None:
                self.first = series.temporal_type
            elif self._refuse_others and series.temporal_type != self.first:
                ident = name if "@" in name else f"{name}@{get_current_mapset()}"
                msg = _(
                    "Wrong temporal type of space time dataset <{stds}> <{type}> "
                    "time is required"
                ).format(stds=ident, type=self.first)
                raise FatalError(msg)
            return series

        return read


def _resolver(kind, profile, granularity, types):
    """The function that reads a dataset for the translator, or None for the
    one of the translator

    :param types: the _TemporalTypes that watches the datasets; it watches
        only where the profile asks for it
    """
    order = "start" if profile.database_order else "time"
    watched = profile.one_temporal_type or profile.empty_result_type_from_input
    if granularity is not None:
        resolve = functools.partial(
            _sampled_source, stds_type=STDS_TYPES[kind], granularity=granularity
        )
    elif order != "time" or watched:
        resolve = functools.partial(
            translate.source, stds_type=STDS_TYPES[kind], order=order
        )
    else:
        return None
    return types.watch(resolve) if watched else resolve


def _classic_error(error):
    """The exception of the reference for a ValueError of the core, or None

    The core reports an expression it cannot compute with a ValueError, the
    reference with the class that fits the cause. The causes the core
    knows are subclasses of ValueError (time_functions.py), so the mapping
    does not depend on the wording of a message.
    """
    if isinstance(error, time_functions.TimeFunctionError):
        if error.ident is None:
            return FatalError(str(error))
        return FatalError(
            _(
                "Temporal function {func}() is not available for map <{map}>. "
                "It requires absolute time, end time functions also an end time."
            ).format(func=error.function, map=error.ident)
        )
    if isinstance(error, time_functions.TimeStepError):
        return SyntaxError(str(error))
    return None


def _sampled_source(name, *, stds_type, granularity):
    """The maps of a dataset on granules of the common granularity"""
    return sample_by_granularity(source(name, stds_type=stds_type), granularity)


def _as_process_dict(call, overwrite):
    """A planned call in the form of Module.get_dict()

    The related maps of an r.series call (call.inputs) are listed as one
    input, "input" with the names joined by commas. The real call reads them
    from a file that is written only at run time (see materialize._module),
    so a dry run has no file name to show.
    """
    parameters = _shown_parameters(call)
    return {
        "name": call.name,
        "inputs": [(key, value) for key, value in parameters if key != "output"],
        "outputs": [(key, value) for key, value in parameters if key == "output"],
        "flags": ["overwrite"] if overwrite else [],
    }


def _shown_parameters(call):
    # The joined maps come first, so that the dry run of a reduction that
    # skips null cells keeps the order it has always shown.
    inputs = [("input", ",".join(call.inputs))] if call.inputs else []
    return [*inputs, *call.parameters.items()]


def _command(call):
    arguments = (
        f"{key}={','.join(value) if isinstance(value, tuple) else value}"
        for key, value in _shown_parameters(call)
    )
    return " ".join((call.name, *arguments))
