"""Run algebra expressions on the reference, the classic profile and the core

The functions run an expression with a runner and return the error class or
the result dataset with its maps, and compare two such outcomes. The fixed
differential tests of the tools and the fuzz tests of
grass.temporal.testing.expressions use them alike.

Functions:

- ``outcome(kind, expression, runner, **options)`` runs ``R = expression`` with
  a runner and returns the error class or the result dataset with its maps.
  A runner is any callable with the signature of
  ``grass.temporal.testing.reference.run_reference``. ``RUNNERS`` names the
  ones at hand: ``reference`` (the earlier implementation), ``core``
  (``grass.temporal.algebra.parser.evaluate``, which the parser classes call
  when the classic algebra is not chosen) and ``classic`` (the same function
  with the classic profile).
- ``outcome_of_runner(kind, expression, runner, basename)`` is ``outcome``
  with a runner chosen by its name in ``RUNNERS`` and with ``-n``;
  ``constant_values(result)`` reads the values of the maps of an outcome.
- ``compare(kind, expression, first, second)`` returns None for equal outcomes
  and a short description of the difference otherwise. ``compare_runs`` is
  ``compare`` for the earlier implementation against the classic profile; it
  accepts the pairs of error classes of ``accepted_error_pair``, which the
  batch counts by pair.
- ``prepare(kind, session, directory)`` creates the datasets of a kind, see
  ``expressions_data``.

The datasets need a ``temporal_session``, because the algebras run in this
process. This module imports no pytest.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import collections
import json
import re

import grass.script as gs
import grass.temporal as tgis

from . import corpus
from .data import STDS_TYPE_OF_KIND
from .expressions_data import build

STDS_TYPES = {**STDS_TYPE_OF_KIND, "select": "strds"}


def _granularity_parser_class(kind):
    """Return the public parser class of a kind, which the tools call"""
    from grass.temporal.algebra.parser import facade

    from .reference import check_granularity_kind

    check_granularity_kind(kind)
    return {
        "raster": facade.TemporalRasterAlgebraParser,
        "raster3d": facade.TemporalRaster3DAlgebraParser,
        "vector": facade.TemporalVectorAlgebraParser,
    }[kind]


def _granularity_parser(kind, expression, options):
    """Take the option ``granularity`` from options; if true, return the parser

    The parser is the public class of the kind with ``classic=False``, after
    ``setup_granularity``: the granularity mode lives in its ``parse()``.
    Returns None for a run without the mode.
    """
    if not options.pop("granularity", False):
        return None
    from .reference import setup_granularity

    parser = _granularity_parser_class(kind)(classic=False, **options)
    setup_granularity(parser, kind, expression)
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


def core_runner(kind, expression, *, basename, overwrite=False, **options):
    """Compute an expression with ``grass.temporal.algebra.parser.evaluate``

    ``evaluate`` is what the parser classes call when the classic algebra is
    not chosen; calling it directly leaves ``GRASS_TEMPORAL_ALGEBRA`` and the
    parser classes out of the picture. Takes the signature of ``run_reference``;
    the option ``stdstype`` of kind ``"select"`` is read like there. With
    ``granularity=True`` the parser class of the kind runs instead, with
    ``classic=False``, after ``setup_granularity``: the evaluation of the
    granularity mode lives in its ``parse()``.
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


def classic_runner(kind, expression, *, basename, overwrite=False, **options):
    """Compute an expression with the classic profile of the algebra core

    The profile ``CLASSIC`` is what ``evaluate`` runs for the classic
    algebra. Takes the signature of ``run_reference``; ``stdstype`` of kind
    ``"select"`` is read like there. For ``granularity=True`` the datasets are
    sampled by ``setup_granularity`` on a parser of the kind, whose
    granularity then goes to ``evaluate``.
    """
    from grass.temporal.algebra.parser import evaluate
    from grass.temporal.algebra.parser.classic import CLASSIC

    parser = _granularity_parser(kind, expression, options)
    granularity = None if parser is None else parser.granularity
    kind, selection = _selection(kind, options)
    return evaluate(
        expression,
        kind=kind,
        basename=basename,
        overwrite=overwrite,
        selection=selection,
        granularity=granularity,
        profile=CLASSIC,
        **options,
    )


def reference_runner(kind, expression, *, basename, overwrite=False, **options):
    """Compute an expression with the earlier implementation, see run_reference"""
    from .reference import run_reference

    return run_reference(
        kind, expression, basename=basename, overwrite=overwrite, **options
    )


RUNNERS = {
    "reference": reference_runner,
    "core": core_runner,
    "classic": classic_runner,
}


class Timeout(BaseException):  # noqa: N818, not an error of the algebra
    """Raised by the alarm of a batch

    A BaseException so that no ``except Exception`` of the algebras swallows it.
    """


def _normalise(error):
    name = type(error).__name__
    if name in {"SyntaxError", "FatalError", "Timeout"}:
        return name
    if isinstance(error, SystemExit):
        return "Exit"
    return f"Other:{name}"


def _message(error, result, basename):
    """The text of an error without what varies between runs and runners

    Quoted and bracketed names, numbers, paths and the generated names are
    replaced, so two files of outcomes can be compared with a plain diff.
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


def outcome(kind, expression, runner, *, basename="fz", **options):
    """Run ``R<basename> = expression`` with a runner and describe what it made

    :param kind: ``"raster"``, ``"raster3d"``, ``"vector"`` or ``"select"``
    :param expression: Right hand side of the statement
    :param runner: Callable with the signature of ``run_reference``
    :param basename: Prefix of the new maps and suffix of the result dataset.
        Two runs that are compared need different basenames, because the
        second would overwrite the maps of the first; the basename is cut
        from the map names of the outcome.
    :param options: Options for the runner, as ``generate`` returns them.
        ``run=True`` and ``debug=False`` are set here. The kind ``"select"``
        reads its result as the dataset type of ``stdstype``; the option
        ``result_type``, which the runner does not get, names another type.
    :return: ``{"error": class}`` when the runner raises (``SyntaxError``,
        ``FatalError``, ``Timeout``, ``Exit`` or ``Other:<name>``, plus the
        message under ``"msg"`` with quoted names, numbers, paths and the
        basename replaced, so that a plain diff of two files of outcomes shows
        real differences only; ``compare`` ignores it), otherwise ``{"stds": False}`` when no result
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
        runner(
            kind,
            f"{result} = {expression}",
            basename=basename,
            overwrite=True,
            **options,
        )
    except (Exception, SystemExit, Timeout) as error:  # noqa: BLE001
        return {"error": _normalise(error), "msg": _message(error, result, basename)}
    return _read_result(kind, result, basename, stdstype)


def outcome_of_runner(kind, expression, runner, basename, **options):
    """``outcome`` of the runner that ``RUNNERS`` names, with option ``-n``

    :param runner: Key of ``RUNNERS``
    :param options: Options for the runner; ``register_null=True`` is set here
        unless an option says otherwise, because a map that is null everywhere
        is a result worth comparing.
    """
    options = {"register_null": True, **options}
    return outcome(kind, expression, RUNNERS[runner], basename=basename, **options)


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


def cluster(records):
    """Group differing outcomes by their signature

    :param records: Iterable of ``(seed, expression, first, second)``
    :return: List of ``(count, signature, seed, expression)``, most frequent
        first; ``seed`` and ``expression`` belong to the shortest expression
        of the group
    """
    counts = collections.Counter()
    example = {}
    for seed, expression, first, second in records:
        if comparison_key(first) == comparison_key(second):
            continue
        detail = None
        if "error" not in first and "error" not in second:
            detail = _detail(first, second)
        signature = (_signature(first), _signature(second), detail)
        counts[signature] += 1
        if signature not in example or len(expression) < len(example[signature][1]):
            example[signature] = (seed, expression)
    return [
        (count, signature, *example[signature])
        for signature, count in counts.most_common()
    ]


def error_classes_differ(first, second):
    """Tell whether two outcomes are both errors of different classes"""
    return "error" in first and "error" in second and first["error"] != second["error"]


# The text of the profile that refuses a dataset of another temporal type
_TYPE_REFUSALS = re.compile(r"wrong temporal type")
# The crash of the earlier implementation when it orders a list that mixes
# maps of absolute and of relative time (datetime against int), and the
# refusal to register such a list as one result
_MIXED_TIME_CRASH = re.compile(r"not supported between instances of")
_MIXED_TIME_REGISTRATION = re.compile(
    r"temporal type of space time dataset .* and its maps are different"
)
# The selection of a value of a time function: the earlier implementation
# copies the map it never computed (g.copy of a temporary map name), the
# profile refuses the expression before it creates anything. The option of
# g.copy names the map type; outcome() replaces the 3 of raster_3d by #.
_UNCOMPUTED_COPY = re.compile(r"g\.copy (?:raster|raster_[3#]d|vector)=tmp_map_name_")
_TIME_FUNCTION_REFUSAL = (
    "A time function such as start_doy() cannot be the result of a selection"
)
# A module that fails at run time: the earlier implementation lets the
# CalledModuleError through, the profile reports it as the FatalError of
# materialize(). outcome() replaces the module name and the numbers by #.
_MODULE_RUN = "Module run `"
_MODULE_FAILURE = "Module # failed with return code #, see the error output above"


def failed_module_pair(first, second):
    """Name the pair if a module failed at run time in both outcomes

    The classic profile computes its maps with materialize(), which reports
    a failed module as a ``FatalError``; the earlier implementation lets the
    ``CalledModuleError`` of the same failing module call through. Before
    materialize() reported it, both outcomes had the same class.

    :param first: The outcome of the earlier implementation
    :param second: The outcome of the classic profile
    :return: ``"Other:CalledModuleError/FatalError"``, or None
    """
    if (first.get("error"), second.get("error")) != (
        "Other:CalledModuleError",
        "FatalError",
    ):
        return None
    failed = first.get("msg", "").startswith(_MODULE_RUN)
    reported = second.get("msg", "") == _MODULE_FAILURE
    return "Other:CalledModuleError/FatalError" if failed and reported else None


def accepted_error_pair(kind, expression, first, second, **options):
    """Name the pair of error classes of two outcomes if the rule accepts it

    Two errors of different classes are no difference when the expression is
    invalid on its own, so that the class only tells which check came first.
    That holds for two pairs. The classic profile reports a ``SyntaxError``
    and the earlier implementation another class, if that implementation
    also rejects the expression as a syntax error when it runs without
    computing. Or the earlier implementation reports a ``SyntaxError`` and the
    classic profile a ``FatalError`` that refuses a dataset of another
    temporal type: the profile reads a dataset that is a bare argument
    before the arguments after it, which the earlier implementation reads
    first. Or the earlier implementation crashes with a ``TypeError`` while
    it orders a list that mixes absolute and relative time, as in
    ``tsnap(merge(tmap(sinst), RT))``, and the profile refuses to register
    that list as one result with a ``FatalError``; the earlier
    implementation refuses the same list with that error where it does not
    order it first (``merge(tmap(sinst), RT)``), and the manual names the
    crash among the differences of the classic algebra. Or a selection whose
    result is a time function (``if(start_doy(A) < 3, start_doy(A, 1), A)``):
    the earlier implementation fails to copy the map it never computed with a
    ``CalledModuleError`` of ``g.copy``, and the profile refuses the
    expression with a ``ValueError`` of the message of the core. Or a module
    fails at run time in both, as r.mapcalc on a floating point operand of
    ``&&`` (``failed_module_pair``): the profile runs on materialize(),
    which reports the failure as a ``FatalError``, the earlier
    implementation lets the ``CalledModuleError`` of the same call through.
    Before that report both had the same class, so this pair accepts no
    more than before. Every other pair is a difference.

    :param first: The outcome of the earlier implementation
    :param second: The outcome of the classic profile
    :param options: The options of the runs. The granularity mode is left
        out of the run without computing: that run must reach the syntax
        check, and the granularity mode first reads the datasets and samples
        them, which stops it with the errors of a computation before it
        parses. In a pytest test the result of that run comes from the
        corpus, see ``corpus.reference_rejects_syntax``.
    :return: ``"<class of first>/<class of second>"``, or None
    """
    if not error_classes_differ(first, second):
        return None
    pair = (first["error"], second["error"])
    label = "/".join(pair)
    if pair == ("SyntaxError", "FatalError"):
        message = second.get("msg", "").lower()
        return label if _TYPE_REFUSALS.search(message) else None
    if pair == ("Other:TypeError", "FatalError"):
        crash = _MIXED_TIME_CRASH.search(first.get("msg", ""))
        refusal = _MIXED_TIME_REGISTRATION.search(second.get("msg", "").lower())
        return label if crash and refusal else None
    if pair == ("Other:CalledModuleError", "FatalError"):
        return failed_module_pair(first, second)
    if pair == ("Other:CalledModuleError", "Other:ValueError"):
        copy = _UNCOMPUTED_COPY.search(first.get("msg", ""))
        refusal = second.get("msg", "").startswith(_TIME_FUNCTION_REFUSAL)
        return label if copy and refusal else None
    if second["error"] != "SyntaxError":
        return None
    return (
        label if corpus.reference_rejects_syntax(kind, expression, **options) else None
    )


def compare_runs(kind, expression, first, second, **options):
    """``compare`` of the outcomes of the earlier implementation and the
    classic profile, except for a pair of errors that ``accepted_error_pair``
    accepts; ``run_batch`` counts those
    """
    if accepted_error_pair(kind, expression, first, second, **options):
        return None
    return compare(kind, expression, first, second)


def check_agreement(kind, expression, **options):
    """Compare the earlier implementation with the classic profile of the core

    The outcome of the earlier implementation is ``corpus.reference_outcome``:
    in a pytest test it comes from the corpus, without running that
    implementation; ``GRASS_TEMPORAL_REFERENCE=live`` computes it on it.

    :raises AssertionError: with the text of ``compare`` when they differ
    """
    first = corpus.reference_outcome(kind, expression, **options)
    second = outcome(kind, expression, RUNNERS["classic"], basename="fb", **options)
    difference = compare_runs(kind, expression, first, second, **options)
    if difference is not None:
        raise AssertionError(difference)


def check_difference_seen(kind, expression, **options):
    """Show that ``compare`` sees a known difference of the core

    Takes the outcome of the earlier implementation from
    ``corpus.reference_outcome``, runs the expression on the core, whose
    results are known to differ, and requires ``compare`` to say so. This is
    the negative test of the fuzzer.

    :raises AssertionError: when ``compare`` finds the outcomes equal
    """
    first = corpus.reference_outcome(kind, expression, **options)
    second = outcome(kind, expression, RUNNERS["core"], basename="fb", **options)
    if compare(kind, expression, first, second) is None:
        msg = f"{kind}: {expression}: the known difference was not seen: {first}"
        raise AssertionError(msg)


def prepare(kind, session, directory):
    """Create the datasets of a kind and return the ``Tools`` of the session

    :param session: A ``temporal_session``
    :param directory: Existing directory for scratch files
    """
    from grass.tools import Tools

    tools = Tools(session=session, overwrite=True, quiet=True)
    build(kind, tools, directory)
    return tools
