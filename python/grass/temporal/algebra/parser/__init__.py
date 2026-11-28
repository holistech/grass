"""The syntax of the temporal algebra on the core of grass.temporal.algebra

The parser reads an expression such as ``C = A {+,during} B`` into a syntax
tree, and the translator turns the tree into calls of the core operations.
evaluate() computes an expression for the public parser classes and t.select,
and returns the process chain dictionary in the form that the classic
algebra returned.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import functools
import re

from grass.temporal.algebra.maptypes import ELEMENTS, KINDS_OF_STDS, STDS_TYPES
from grass.temporal.algebra.materialize import check_absent, materialize, plan
from grass.temporal.algebra.sources import source

from .grammar import parse
from .granularity import sample_by_granularity
from .translate import Translator

__all__ = ["Translator", "evaluate", "parse"]

# The public parser classes take "num" or "num%NN" for numbered map names; the
# core takes None, with the digits of "num%NN" as a separate option.
_TIME_SUFFIXES = ("gran", "time")


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

    :param expression: the statement "name = expression"; name is the space
        time dataset that the result is registered in
    :param kind: the map type, "raster", "raster3d" or "vector"
    :param basename: the prefix of the result map names, by default the name of
        the result dataset
    :param overwrite: replace an existing result dataset and maps, and pass
        --overwrite to every module call; without it an existing result stops
        the run before any map is computed
    :param run: False only checks the syntax and returns an empty chain
    :param dry_run: plan the module calls and fill the chain, but compute and
        register nothing
    :param debug: print each planned module call as a command line
    :param spatial: relate the maps in space as well, as the spatial flag of
        t.rast.algebra does; rasters are then computed in the union of the
        regions of their inputs where a spatial relation related them
    :param register_null: register result maps without a valid cell too; by
        default they are removed
    :param nprocs: the number of module processes that run at once; 1 runs
        them one after another, and vector maps need 1
    :param time_suffix: how result maps are named after the basename: "gran"
        or "time" for a suffix from the start time of an absolute-time map;
        any other value numbers the maps, with the digits of "num%NN" if it
        is given in that form
    :param selection: register the registered maps unchanged and copy retimed
        ones instead of computing a map
    :param granularity: the common granularity of the datasets, a text such
        as "1 day" for absolute time or a whole number for relative time;
        None reads the datasets as they are
    :return: the process chain dictionary of the public parser classes:
        "processes" in the form of Module.get_dict(), "register" as (name,
        start, end) strings, "remove" and "STDS"
    :raises SyntaxError: for an error in the expression
    :raises ValueError, TypeError: as the core operations, for an expression
        that cannot be computed
    :raises grass.exceptions.FatalError: for a missing dataset or map, and
        without overwrite for an existing result dataset or map
    """
    statement = parse(expression)
    chain = {"processes": [], "register": [], "remove": [], "STDS": {}}
    if not run:
        return chain
    translator = Translator(
        kind=kind,
        spatial=spatial,
        resolve=_resolver(kind, granularity),
        selection=selection,
    )
    name, series = translator.statement(statement)
    planned = plan(
        series,
        name,
        basename=basename,
        time_suffix=time_suffix if time_suffix in _TIME_SUFFIXES else None,
        selection=selection,
        digits=_suffix_digits(time_suffix),
    )
    # Also for a result without maps, which gets an empty dataset.
    chain["STDS"] = {
        "name": name,
        # The type the run creates, so that a dry run shows what the run
        # makes. The classic algebra planned the type of the call, also where
        # a mixed selection created another one.
        "stdstype": planned.stds_type,
        "temporal_type": planned.temporal_type,
    }
    chain["processes"] = [
        _as_process_dict(call, overwrite) for call in planned.processes
    ]
    chain["register"] = [
        (map_name, str(start), str(end)) for map_name, start, end in planned.register
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
            check_absent(planned)
    else:
        materialize(
            series,
            name,
            overwrite=overwrite,
            register_null=register_null,
            nprocs=int(nprocs),
            chain=planned,
        )
    return chain


def _suffix_digits(time_suffix):
    """The number of digits that the suffix "num%NN" gives, None for another"""
    match = re.fullmatch(r"num%(\d+)", time_suffix or "")
    return int(match.group(1)) if match else None


def _resolver(kind, granularity):
    """Return the function that reads a dataset for the translator

    The result is None where the translator's own reader is meant.
    """
    if granularity is None:
        return None
    return functools.partial(
        _sampled_source, stds_type=STDS_TYPES[kind], granularity=granularity
    )


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
    # The joined maps come first, where r.series input=... output=... names
    # them: the dry run of a reduction that skips null cells shows its maps
    # in that place (temporal_algebra_core_plan_test.py holds it). An
    # aggregation gets the same order, though no tool shows its dry run.
    inputs = [("input", ",".join(call.inputs))] if call.inputs else []
    return [*inputs, *call.parameters.items()]


def _command(call):
    arguments = (
        f"{key}={','.join(value) if isinstance(value, tuple) else value}"
        for key, value in _shown_parameters(call)
    )
    return " ".join((call.name, *arguments))
