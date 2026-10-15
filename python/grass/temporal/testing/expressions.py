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
  ones at hand: ``reference`` (the earlier implementation) and ``core``
  (``grass.temporal.algebra.parser.evaluate``, which the parser classes call
  when the classic algebra is not chosen).
- ``compare(kind, expression, first, second)`` returns None for equal outcomes
  and a short description of the difference otherwise.
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

``--against core`` computes every expression with a second runner and adds the
other outcome and the difference to each line; ``--cluster FILE`` groups the
differences in such a file by what differs. ``run_batch`` does the same from
Python. A batch runs in a temporary project and gives each expression
``timeout`` seconds (SIGALRM, main thread only).

The test modules that use this fuzzer run the seeds 0 to 199 per map type.
``GRASS_TEMPORAL_FUZZ_COUNT`` sets another count and
``GRASS_TEMPORAL_FUZZ_SEED`` the first seed for acceptance runs.

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
    the option ``stdstype`` of kind ``"select"`` is read like there.
    """
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


def reference_runner(kind, expression, *, basename, overwrite=False, **options):
    """Compute an expression with the earlier implementation, see run_reference"""
    from .reference import run_reference

    return run_reference(
        kind, expression, basename=basename, overwrite=overwrite, **options
    )


RUNNERS = {"reference": reference_runner, "core": core_runner}


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


def _value(number):
    if number is None:
        return None
    return float(f"{number:.6g}")


def _time(moment):
    if moment is None:
        return None
    return moment.isoformat() if hasattr(moment, "isoformat") else moment


def _read_result(kind, name, basename):
    stds = tgis.dataset_factory(STDS_TYPES[kind], f"{name}@PERMANENT")
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
        if kind == "vector":
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
        ``run=True`` and ``debug=False`` are set here.
    :return: ``{"error": class}`` when the runner raises (``SyntaxError``,
        ``FatalError``, ``Timeout``, ``Exit`` or ``Other:<name>``, plus the
        message under ``"msg"``), otherwise ``{"stds": False}`` when no result
        dataset exists, or ``{"stds": True, "ttype", "maps"}``. A map is
        ``[name, start, end, min, max]``, for kind ``"vector"``
        ``[name, start, end, points, lines, areas]`` from ``v.info -t``, in the
        order of the start time. Numbers have 6 significant digits.
    """
    result = f"R{basename}"
    stds = tgis.dataset_factory(STDS_TYPES[kind], f"{result}@PERMANENT")
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
        return {"error": _normalise(error), "msg": str(error)[:400]}
    return _read_result(kind, result, basename)


def _key(result):
    """What compare looks at: the error class or the result, not the message"""
    if "error" in result:
        return ("error", result["error"])
    return ("result", json.dumps(result, sort_keys=True))


def _signature(result):
    if "error" in result:
        message = re.sub(r"<[^>]*>|\d+|'[^']*'", "#", result["msg"])
        return f"{result['error']}:{message[:60]}"
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


def run_batch(kind, seeds, runner, out, *, against=None, timeout=300, depth=3):
    """Compute the expressions of seeds and write one JSON line per seed

    Must run inside a ``temporal_session`` with the datasets of ``prepare``.
    A line holds ``seed``, ``expression``, ``options`` and ``outcome``; with
    ``against`` also ``other`` and ``difference`` (None or the text of
    ``compare``). The lines depend only on the seed and the code.

    :param runner: A runner as for ``outcome``
    :param against: A second runner to compare with
    :param timeout: Seconds per outcome (SIGALRM, main thread only)
    :return: The number of differences when ``against`` is set, else 0
    """
    differences = 0
    previous = signal.signal(signal.SIGALRM, _alarm)
    try:
        with Path(out).open("w") as handle:
            for seed in seeds:
                expression, options = generate(kind, seed, depth=depth)
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
                    line["difference"] = compare(kind, expression, result, other)
                    differences += line["difference"] is not None
                handle.write(json.dumps(line, sort_keys=True) + "\n")
                handle.flush()
    finally:
        signal.signal(signal.SIGALRM, previous)
    return differences


def _lines(path):
    with Path(path).open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _print_clusters(records):
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
            )
    print(f"{len(seeds)} seeds, {differences} differences")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())
