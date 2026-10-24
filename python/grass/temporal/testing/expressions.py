"""Seeded random expressions for differential tests of the temporal algebras

The fuzzer generates expressions in the syntax of the classic algebra, runs
them on two implementations and compares the registered maps. The same seed
always gives the same expression and options, so a difference can be
reproduced from its seed alone.

Functions:

- ``generate(kind, seed)`` returns an expression and the parser options of one
  run. ``boundary_forms(kind)`` lists fixed forms on the border between the
  grammar of the classic algebra and that of the core.
- ``outcome(kind, expression, runner, **options)`` runs ``R = expression`` with
  a runner and returns the error class or the result dataset with its maps.
  A runner is any callable with the signature of
  ``grass.temporal.testing.reference.run_reference``. ``RUNNERS`` names the
  ones at hand: ``reference`` (the earlier implementation), ``core``
  (``grass.temporal.algebra.parser.evaluate``, which the parser classes call
  when the classic algebra is not chosen) and ``classic`` (the same function
  with the classic profile).
- ``compare(kind, expression, first, second)`` returns None for equal outcomes
  and a short description of the difference otherwise. ``compare_runs`` is
  ``compare`` for the earlier implementation against the classic profile; it
  accepts the pairs of error classes of ``accepted_error_pair``, which the
  batch counts by pair.
- ``prepare(kind, session, directory)`` creates the datasets the generator
  names, see ``expressions_data``.

The datasets need a ``temporal_session``, because the algebras run in this
process. This module imports no pytest.

Batch use outside pytest. Each line of the output file is a JSON object with
the seed, the expression, the options and the outcome; the outcome contains
no time stamp and no random name, so two runs of the same code give the same
line for the same seed. That makes before and after runs of a fix comparable::

    python3 -m grass.temporal.testing.expressions --kind raster \\
        --seeds 0-3999 --runner reference --out before.jsonl
    python3 -m grass.temporal.testing.expressions --kind raster \\
        --seeds 0-3999 --runner reference --out after.jsonl
    python3 -m grass.temporal.testing.expressions --diff before.jsonl after.jsonl

``--spatial-share`` and ``--granularity-share`` set the share of the seeds in
the spatial mode (-s) and in the granularity mode (-g, raster and raster3d
only); ``--paper-share`` the share of the seeds that also draw the forms of the
published paper (number chains, td() on the left, the comparison operator,
capital dataset functions in t.select). The summary counts the outcomes of
class ``Other:<name>``: a campaign that raises one for every expression,
because an option does not reach the parser, would otherwise look like
agreement.

``--against core`` computes every expression with a second runner and adds the
other outcome and the difference to each line; ``--cluster FILE`` groups the
differences in such a file by what differs. ``run_batch`` does the same from
Python. A batch runs in a temporary project and gives each expression
``timeout`` seconds (SIGALRM, main thread only).

The test modules that use this fuzzer run the seeds 0 to 199 per map type
through ``check_seed``, ``check_agreement`` and ``check_difference_seen``,
which take the outcome of the earlier implementation from the corpus of
``grass.temporal.testing.corpus``. ``GRASS_TEMPORAL_FUZZ_COUNT`` sets another
count and ``GRASS_TEMPORAL_FUZZ_SEED`` the first seed for acceptance runs.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import signal
import sys
import tempfile
from pathlib import Path

import grass.script as gs
import grass.temporal as tgis

from . import corpus
from .expressions_data import build
from .expressions_generator import KINDS, boundary_forms, generate

__all__ = ["KINDS", "RUNNERS", "boundary_forms", "generate"]

STDS_TYPES = {
    "raster": "strds",
    "raster3d": "str3ds",
    "vector": "stvds",
    "select": "strds",
}


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
    if options.pop("granularity", False):
        from .reference import _classes, setup_granularity

        parser = _classes(kind)[0](classic=False, **options)
        setup_granularity(parser, kind, expression)
        return parser.parse(expression, basename=basename, overwrite=overwrite)
    from grass.temporal.algebra.maptypes import KINDS_OF_STDS
    from grass.temporal.algebra.parser import evaluate

    selection = kind == "select"
    if selection:
        stdstype = options.pop("stdstype", "strds")
        kind = KINDS_OF_STDS[stdstype]
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
    from grass.temporal.algebra.maptypes import KINDS_OF_STDS
    from grass.temporal.algebra.parser import evaluate
    from grass.temporal.algebra.profile import CLASSIC

    granularity = None
    if options.pop("granularity", False):
        from .reference import _classes, setup_granularity

        parser = _classes(kind)[0](classic=False, **options)
        setup_granularity(parser, kind, expression)
        granularity = parser.granularity
    selection = kind == "select"
    if selection:
        stdstype = options.pop("stdstype", "strds")
        kind = KINDS_OF_STDS[stdstype]
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


def _key(result):
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
    if _key(first) == _key(second):
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
        if _key(first) == _key(second):
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


#: The two runners that the test modules compare, as keys of ``RUNNERS``: the
#: earlier implementation of the classic algebra and the classic profile of
#: the core, which ``-c`` runs. The test modules take the pair from here, so
#: switching is one edit.
DIFFERENTIAL = ("reference", "classic")


def check_agreement(kind, expression, **options):
    """Run an expression on the runners of ``DIFFERENTIAL`` and compare them

    The outcome of the earlier implementation is ``corpus.reference_outcome``:
    in a pytest test it comes from the corpus, which is faster than a run;
    ``GRASS_TEMPORAL_REFERENCE=live`` computes it on that implementation.

    :raises AssertionError: with the text of ``compare`` when they differ
    """
    if DIFFERENTIAL[0] == "reference":
        first = corpus.reference_outcome(kind, expression, **options)
    else:
        first = outcome(
            kind, expression, RUNNERS[DIFFERENTIAL[0]], basename="fa", **options
        )
    second = outcome(
        kind, expression, RUNNERS[DIFFERENTIAL[1]], basename="fb", **options
    )
    difference = compare_runs(kind, expression, first, second, **options)
    if difference is not None:
        raise AssertionError(difference)


def check_seed(kind, seed, **generate_options):
    """``check_agreement`` for the expression and options of a seed

    :param generate_options: Arguments of ``generate`` such as
        ``granularity_share``
    """
    expression, options = generate(kind, seed, **generate_options)
    try:
        check_agreement(kind, expression, **options)
    except AssertionError as error:
        msg = f"seed {seed}: {error}"
        raise AssertionError(msg) from None


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


def seed_range():
    """The seeds of a test run: 200 from 0, or what the environment sets"""
    first = int(os.environ.get("GRASS_TEMPORAL_FUZZ_SEED", "0"))
    count = int(os.environ.get("GRASS_TEMPORAL_FUZZ_COUNT", "200"))
    return range(first, first + count)


def _alarm(signum, frame):
    raise Timeout


def run_batch(
    kind,
    seeds,
    runner,
    out,
    *,
    against=None,
    timeout=300,
    depth=3,
    spatial_share=0.1,
    granularity_share=0.0,
    paper_share=0.25,
):
    """Compute the expressions of seeds and write one JSON line per seed

    Must run inside a ``temporal_session`` with the datasets of ``prepare``.
    A line holds ``seed``, ``expression``, ``options`` and ``outcome``; with
    ``against`` also ``other``, ``difference`` (None or the text of
    ``compare_runs``) and ``error_pair`` (the accepted pair of error classes,
    which is no difference, see ``accepted_error_pair``, else None). The lines
    depend only on the seed and the code.

    :param runner: A runner as for ``outcome``
    :param against: A second runner to compare with
    :param timeout: Seconds per outcome (SIGALRM, main thread only)
    :param depth: See ``generate``, as are the two shares
    :return: The number of differences when ``against`` is set, else 0
    """
    differences = 0
    previous = signal.signal(signal.SIGALRM, _alarm)
    try:
        with Path(out).open("w") as handle:
            for seed in seeds:
                expression, options = generate(
                    kind,
                    seed,
                    depth=depth,
                    spatial_share=spatial_share,
                    granularity_share=granularity_share,
                    paper_share=paper_share,
                )
                signal.alarm(timeout)
                try:
                    result = outcome(kind, expression, runner, basename="fa", **options)
                    other = None
                    if against is not None:
                        other = outcome(
                            kind, expression, against, basename="fb", **options
                        )
                finally:
                    signal.alarm(0)
                line = {
                    "seed": seed,
                    "expression": expression,
                    "options": options,
                    "outcome": result,
                }
                if against is not None:
                    line["other"] = other
                    line["difference"] = compare_runs(
                        kind, expression, result, other, **options
                    )
                    line["error_pair"] = accepted_error_pair(
                        kind, expression, result, other, **options
                    )
                    differences += line["difference"] is not None
                handle.write(json.dumps(line, sort_keys=True) + "\n")
                handle.flush()
    finally:
        signal.signal(signal.SIGALRM, previous)
    return differences


def count_others(outcomes):
    """Count the outcomes that raised something other than the usual errors

    ``Other:<name>`` is every exception class except ``SyntaxError`` and
    ``FatalError``. The algebras raise some of them for invalid expressions
    (``ValueError`` of the core), but a broken campaign raises one for every
    expression, for example a ``TypeError`` for an option that a parser does
    not take, and then both sides agree on it. The count makes that visible.

    :return: ``collections.Counter`` of the classes
    """
    return collections.Counter(
        result["error"]
        for result in outcomes
        if result is not None and result.get("error", "").startswith("Other:")
    )


def _print_others(outcomes):
    for name, count in sorted(count_others(outcomes).items()):
        print(f"{count} outcomes of class {name}")


def _lines(path):
    with Path(path).open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _print_clusters(records):
    records = list(records)
    _print_others(
        outcome for _, _, first, second in records for outcome in (first, second)
    )
    for count, signature, seed, expression in cluster(records):
        print(f"{count} {signature}")
        print(f"      {seed} {expression}")


def main(argv=None):
    """Command line of the batch, see the module docstring"""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--kind", choices=KINDS)
    parser.add_argument("--seeds", help="first-last, both included, or one seed")
    parser.add_argument("--runner", choices=RUNNERS, default="reference")
    parser.add_argument("--against", choices=RUNNERS)
    parser.add_argument("--out")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--spatial-share", type=float, default=0.1)
    parser.add_argument(
        "--paper-share",
        type=float,
        default=0.25,
        help="share of the seeds with the forms of the published paper "
        "(raster, raster3d, select)",
    )
    parser.add_argument(
        "--granularity-share",
        type=float,
        default=0.0,
        help="share of the seeds in the granularity mode (raster, raster3d)",
    )
    parser.add_argument("--diff", nargs=2, metavar=("OLD", "NEW"))
    parser.add_argument("--cluster", metavar="FILE")
    args = parser.parse_args(argv)

    if args.cluster:
        _print_clusters(
            (line["seed"], line["expression"], line["outcome"], line["other"])
            for line in _lines(args.cluster)
        )
        return 0
    if args.diff:
        old = {line["seed"]: line for line in _lines(args.diff[0])}
        new = {line["seed"]: line for line in _lines(args.diff[1])}
        changed = [
            (seed, new[seed]["expression"], old[seed]["outcome"], new[seed]["outcome"])
            for seed in sorted(old.keys() & new.keys())
            if _key(old[seed]["outcome"]) != _key(new[seed]["outcome"])
        ]
        print(
            f"{len(changed)} of {len(old.keys() & new.keys())} seeds differ"
            f" ({len(old.keys() ^ new.keys())} only in one file)"
        )
        for seed, expression, _, _ in changed:
            print(f"{seed}\t{expression}")
        _print_clusters(changed)
        return 1 if changed else 0

    if not (args.kind and args.seeds and args.out):
        parser.error("--kind, --seeds and --out are required")
    first, _, last = args.seeds.partition("-")
    seeds = range(int(first), int(last or first) + 1)

    from . import fakes
    from .session import temporal_session

    with (
        tempfile.TemporaryDirectory() as directory,
        temporal_session(Path(directory) / "project") as session,
    ):
        prepare(args.kind, session, directory)
        with fakes.cached_io(fakes.CacheStorage()):
            differences = run_batch(
                args.kind,
                seeds,
                RUNNERS[args.runner],
                args.out,
                against=RUNNERS[args.against] if args.against else None,
                timeout=args.timeout,
                depth=args.depth,
                spatial_share=args.spatial_share,
                granularity_share=args.granularity_share,
                paper_share=args.paper_share,
            )
    lines = _lines(args.out)
    _print_others(
        outcome for line in lines for outcome in (line["outcome"], line.get("other"))
    )
    pairs = collections.Counter(
        line["error_pair"] for line in lines if line.get("error_pair")
    )
    print(f"{len(seeds)} seeds, {differences} differences")
    for pair, count in sorted(pairs.items()):
        print(f"{count} accepted pairs of error classes {pair}")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())
