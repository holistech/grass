"""The syntax of the temporal algebra on the core of grass.temporal.algebra

The parser reads an expression such as ``C = A {+,during} B`` into a syntax
tree, and the translator turns the tree into calls of the core operations.
evaluate() does with an expression what the parser classes of grass.temporal
do, and returns the same process chain dictionary.
"""

from __future__ import annotations

from grass.temporal.algebra.maptypes import ELEMENTS, KINDS_OF_STDS
from grass.temporal.algebra.materialize import check_absent, materialize, plan

from .grammar import parse
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
):
    """Parse, translate and compute "name = expression"

    Without run only the syntax is checked. With dry_run the maps are
    planned but neither computed nor registered; without overwrite it still
    stops at an existing result, as the run would. debug prints the module
    calls.

    :param kind: the map type, "raster", "raster3d" or "vector"
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
    name, series = Translator(kind=kind, spatial=spatial).statement(statement)
    suffix = time_suffix if time_suffix in _TIME_SUFFIXES else None
    planned = plan(series, name, basename=basename, time_suffix=suffix)
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
        )
    return chain


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
