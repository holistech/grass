"""The syntax of the temporal algebra on the core of grass.temporal.algebra

The parser reads an expression such as ``C = A {+,during} B`` into a syntax
tree, and the translator turns the tree into calls of the core operations.
evaluate() does with an expression what the parser classes of grass.temporal
do, and returns the same process chain dictionary.
"""

from __future__ import annotations

import functools

from grass.temporal.algebra.maptypes import ELEMENTS, KINDS_OF_STDS, STDS_TYPES
from grass.temporal.algebra.materialize import check_absent, materialize, plan
from grass.temporal.algebra.sources import source

from .grammar import parse
from .granularity import sample_by_granularity
from .translate import Translator

__all__ = ["Translator", "evaluate", "parse"]

# The parser classes take "num" for numbered map names; the core takes None.
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
    expression with setup_common_granularity() of the parser classes.

    With selection no map is computed: every result slot must be a registered
    map, which is registered unchanged or, when a temporal operator retimed
    it, copied with g.copy, as a selection needs it (see plan()).

    :param kind: the map type, "raster", "raster3d" or "vector"
    :param granularity: the common granularity of the datasets, a text such
        as "1 day" for absolute time or a whole number for relative time;
        None reads the datasets as they are
    :return: the process chain of the parser classes: "processes" in the form
        of Module.get_dict(), "register" as (name, start, end) strings,
        "remove" and "STDS"
    :raises SyntaxError: for an error in the expression
    :raises ValueError, TypeError: as the core operations, for an expression
        that cannot be computed
    :raises FatalError: for a missing dataset or map, and without overwrite
        for an existing result dataset or map
    """
    statement = parse(expression)
    chain = {"processes": [], "register": [], "remove": [], "STDS": {}}
    if not run:
        return chain
    resolve = None
    if granularity is not None:
        resolve = functools.partial(
            _sampled_source, stds_type=STDS_TYPES[kind], granularity=granularity
        )
    name, series = Translator(kind=kind, spatial=spatial, resolve=resolve).statement(
        statement
    )
    suffix = time_suffix if time_suffix in _TIME_SUFFIXES else None
    planned = plan(
        series, name, basename=basename, time_suffix=suffix, selection=selection
    )
    chain["processes"] = [_module(call, overwrite) for call in planned.processes]
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
    chain["STDS"] = {
        "name": name,
        "stdstype": planned.stds_type,
        "temporal_type": planned.temporal_type,
    }
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
            basename=basename,
            overwrite=overwrite,
            register_null=register_null,
            nprocs=int(nprocs),
            time_suffix=suffix,
            selection=selection,
        )
    return chain


def _sampled_source(name, *, stds_type, granularity):
    """The maps of a dataset on granules of the common granularity"""
    return sample_by_granularity(source(name, stds_type=stds_type), granularity)


def _module(call, overwrite):
    """A planned call in the form of Module.get_dict()"""
    parameters = call.parameters.items()
    return {
        "name": call.name,
        "inputs": [(key, value) for key, value in parameters if key != "output"],
        "outputs": [(key, value) for key, value in parameters if key == "output"],
        "flags": ["overwrite"] if overwrite else [],
    }


def _command(call):
    arguments = (
        f"{key}={','.join(value) if isinstance(value, tuple) else value}"
        for key, value in call.parameters.items()
    )
    return " ".join((call.name, *arguments))
