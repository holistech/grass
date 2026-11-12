"""Run an expression on the algebra core and describe what it made

The functions run ``R = expression`` with the core and return the error class
or the result dataset with its maps, in a form that a test compares with
values it has derived by hand.

Functions:

- ``outcome(kind, expression, **options)`` runs the expression and returns the
  error class or the result dataset with its maps.
- ``run_core(kind, expression, *, basename, **options)`` is the runner behind
  it. It computes with ``grass.temporal.algebra.parser.evaluate``, which the
  public parser classes call, or with the public parser class of the kind
  when the granularity mode is asked for.
- ``constant_values(result)`` reads the values of the maps of an outcome.
- ``compare(kind, expression, first, second)`` returns None for equal outcomes
  and a short description of the difference otherwise, for two spellings of
  one expression.
- ``prepare(kind, session, directory)`` creates the datasets of a kind, see
  ``expressions_data``.

The datasets need a ``temporal_session``, because the algebra runs in this
process. This module imports no pytest.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import json
import re

import grass.script as gs
import grass.temporal as tgis
from grass.exceptions import FatalError

from .data import STDS_TYPE_OF_KIND
from .expressions_data import build

STDS_TYPES = {**STDS_TYPE_OF_KIND, "select": "strds"}


def _granularity_parser(kind, expression, options):
    """Take the option ``granularity`` from options; if true, return the parser

    The parser is the public class of the kind after
    ``setup_common_granularity``: the granularity mode lives in its
    ``parse()``. Returns None for a run without the mode.

    :raises ValueError: for a kind without a granularity mode, such as
        ``"select"``
    :raises grass.exceptions.FatalError: when no common granularity exists
    """
    if not options.pop("granularity", False):
        return None
    from grass.temporal.algebra.parser import facade

    classes = {
        "raster": (facade.TemporalRasterAlgebraParser, "strds"),
        "raster3d": (facade.TemporalRaster3DAlgebraParser, "str3ds"),
        "vector": (facade.TemporalVectorAlgebraParser, "stvds"),
    }
    if kind not in classes:
        msg = (
            f"The granularity mode exists for raster, raster3d and vector, not {kind!r}"
        )
        raise ValueError(msg)
    parser_class, stdstype = classes[kind]
    parser = parser_class(**options)
    if not parser.setup_common_granularity(expression=expression, stdstype=stdstype):
        msg = "Unable to process the expression in granularity algebra mode"
        raise FatalError(msg)
    return parser


def _selection(kind, options):
    """Return the kind of the datasets and whether the run is a selection

    The kind ``"select"`` runs on the datasets of the type that the option
    ``stdstype`` names, which is taken from options.
    """
    from grass.temporal.algebra.maptypes import KINDS_OF_STDS

    if kind != "select":
        return kind, False
    return KINDS_OF_STDS[options.pop("stdstype", "strds")], True


def run_core(kind, expression, *, basename, overwrite=False, **options):
    """Compute an expression with ``grass.temporal.algebra.parser.evaluate``

    ``evaluate`` is what the public parser classes call; calling it directly
    leaves those classes out of the picture. With ``granularity=True`` the
    public parser class of the kind runs instead, after
    ``setup_common_granularity``: the evaluation of the granularity mode lives
    in its ``parse()``.

    :param kind: ``"raster"``, ``"raster3d"``, ``"vector"`` or ``"select"``
    :param expression: The whole statement, ``"R = A + B"``
    :param basename: Prefix of the names of the new maps
    :param overwrite: Overwrite existing result maps and datasets
    :param options: Options of ``evaluate``; the option ``stdstype`` of kind
        ``"select"`` is the dataset type that t.select passes
    :return: The process chain dictionary, like ``parse()``
    """
    parser = _granularity_parser(kind, expression, options)
    if parser is not None:
        return parser.parse(expression, basename=basename, overwrite=overwrite)
    from grass.temporal.algebra.parser import evaluate

    kind, selection = _selection(kind, options)
    return evaluate(
        expression,
        kind=kind,
        basename=basename,
        overwrite=overwrite,
        selection=selection,
        **options,
    )


def _normalise(error):
    name = type(error).__name__
    if name in {"SyntaxError", "FatalError"}:
        return name
    if isinstance(error, SystemExit):
        return "Exit"
    return f"Other:{name}"


def _message(error, result, basename):
    """The text of an error without what varies between runs

    Quoted and bracketed names, numbers, paths and the generated names are
    replaced.
    """
    text = str(error)
    text = re.sub(r"<[^>]*>|'[^']*'|\"[^\"]*\"", "#", text)
    text = re.sub(r"/\S+", "/PATH", text)
    text = text.replace(result, "R").replace(f"{basename}_", "B_")
    return re.sub(r"\d+", "#", text)[:200]


def _value(number):
    if number is None:
        return None
    return float(f"{number:.6g}")


def _time(moment):
    if moment is None:
        return None
    return moment.isoformat() if hasattr(moment, "isoformat") else moment


def _read_result(kind, name, basename, stdstype=None):
    stds_type = stdstype or STDS_TYPES[kind]
    stds = tgis.dataset_factory(stds_type, f"{name}@PERMANENT")
    if not stds.is_in_db():
        return {"stds": False}
    stds.select()
    rows = []
    for item in stds.get_registered_maps_as_objects(order="start_time") or []:
        item.select()
        start, end = item.get_temporal_extent_as_tuple()
        map_name = item.get_name()
        if map_name.startswith(f"{basename}_"):
            map_name = "N_" + map_name[len(basename) + 1 :]
        if stds_type == "stvds":
            # The temporal database holds no primitive counts for maps the
            # algebra registers (all None, seen 15.10.2026), so they are read
            # from the map itself.
            topology = gs.vector_info_topo(item.get_id())
            values = [topology["points"], topology["lines"], topology["areas"]]
        else:
            values = [_value(item.metadata.get_min()), _value(item.metadata.get_max())]
        rows.append([map_name, _time(start), _time(end), *values])
    return {"stds": True, "ttype": stds.get_temporal_type(), "maps": rows}


def outcome(kind, expression, *, basename="fz", **options):
    """Run ``R<basename> = expression`` on the core and describe what it made

    :param kind: ``"raster"``, ``"raster3d"``, ``"vector"`` or ``"select"``
    :param expression: Right hand side of the statement
    :param basename: Prefix of the new maps and suffix of the result dataset.
        Two runs that are compared need different basenames, because the
        second would overwrite the maps of the first; the basename is cut
        from the map names of the outcome.
    :param options: Options for ``run_core``. ``run=True`` and ``debug=False``
        are set here. The kind ``"select"`` reads its result as the dataset
        type of ``stdstype``; the option ``result_type``, which the runner
        does not get, names another type.
    :return: ``{"error": class}`` when the run raises (``SyntaxError``,
        ``FatalError``, ``Exit`` or ``Other:<name>``, plus the message under
        ``"msg"`` with quoted names, numbers, paths and the basename replaced;
        ``compare`` ignores it), otherwise ``{"stds": False}`` when no result
        dataset exists, or ``{"stds": True, "ttype", "maps"}``. A map is
        ``[name, start, end, min, max]``, for kind ``"vector"``
        ``[name, start, end, points, lines, areas]`` from ``v.info -t``, in the
        order of the start time. Numbers have 6 significant digits. Raster
        equality is the minimum and maximum of each map, not identical pixels.
    """
    result = f"R{basename}"
    # The kind "select" makes a dataset of the type that stdstype names, unless
    # the maps decide otherwise: result_type then names the type to read
    result_type = options.pop("result_type", None)
    stdstype = result_type or (options.get("stdstype") if kind == "select" else None)
    stds = tgis.dataset_factory(stdstype or STDS_TYPES[kind], f"{result}@PERMANENT")
    if stds.is_in_db():
        stds.delete()
    options = {"run": True, "debug": False, **options}
    try:
        run_core(
            kind,
            f"{result} = {expression}",
            basename=basename,
            overwrite=True,
            **options,
        )
    # Every failure of a run is an outcome to look at, so none may escape.
    except (Exception, SystemExit) as error:  # noqa: BLE001
        return {"error": _normalise(error), "msg": _message(error, result, basename)}
    return _read_result(kind, result, basename, stdstype)


def constant_values(result):
    """The value of each map of an outcome, in the order of the outcome

    For data whose every input map is constant: a map with a minimum that
    differs from its maximum is a failure of the test, not a value.
    """
    assert "error" not in result, result
    assert all(low == high for *_, low, high in result["maps"]), result
    return [low for *_, low, _high in result["maps"]]


def comparison_key(result):
    """What compare looks at: the error class or the result, not the message"""
    if "error" in result:
        return ("error", result["error"])
    return ("result", json.dumps(result, sort_keys=True))


def _signature(result):
    if "error" in result:
        return f"{result['error']}:{result['msg'][:60]}"
    if not result["stds"]:
        return "nostds"
    return "empty" if not result["maps"] else "maps"


def _detail(first, second):
    """What differs between two outcomes that are both results"""
    if first["stds"] != second["stds"]:
        return "existence"
    if not first["stds"]:
        return None
    if first["ttype"] != second["ttype"]:
        return "ttype"
    a, b = first["maps"], second["maps"]
    if len(a) != len(b):
        return "count"
    if sorted(map(repr, (m[1:] for m in a))) == sorted(map(repr, (m[1:] for m in b))):
        return "names"
    if sorted(map(repr, (m[1:3] for m in a))) == sorted(map(repr, (m[1:3] for m in b))):
        return "values"
    return "times"


def compare(kind, expression, first, second):
    """Compare two outcomes of one expression

    The error class is compared, not the message. The maps are compared with
    their names (without basename), times, values and order.

    :return: None for equal outcomes, otherwise a line that names the kind,
        the expression and what differs
    """
    if comparison_key(first) == comparison_key(second):
        return None
    if "error" in first or "error" in second:
        what = f"{_signature(first)} against {_signature(second)}"
    else:
        what = f"result differs in {_detail(first, second)}"
    return f"{kind}: {expression}: {what}"


def prepare(kind, session, directory):
    """Create the datasets of a kind and return the ``Tools`` of the session

    :param kind: ``"raster"``, ``"raster3d"``, ``"vector"`` or ``"select"``;
        decides which datasets are built
    :param session: A ``temporal_session``
    :param directory: Existing directory for scratch files
    """
    from grass.tools import Tools

    tools = Tools(session=session, overwrite=True, quiet=True)
    build(kind, tools, directory)
    return tools
