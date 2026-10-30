"""Seeded random expressions for differential tests of the temporal algebras

The fuzzer generates expressions in the syntax of the classic algebra, runs
them on two implementations with the runners of
``grass.temporal.testing.differential`` and compares the registered maps.
The same seed always gives the same expression and options, so a difference
can be reproduced from its seed alone.

Functions:

- ``generate(kind, seed)`` returns an expression and the parser options of one
  run. ``boundary_forms(kind)`` lists fixed forms on the border between the
  grammar of the classic algebra and that of the core.
- ``check_seed(kind, seed)`` runs the expression of a seed through
  ``differential.check_agreement``.

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

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import signal
import sys
import tempfile
from pathlib import Path

from .differential import (
    RUNNERS,
    Timeout,
    accepted_error_pair,
    check_agreement,
    cluster,
    compare_runs,
    comparison_key,
    outcome,
    prepare,
)
from .expressions_generator import generate
from .reference import KINDS


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
            if comparison_key(old[seed]["outcome"])
            != comparison_key(new[seed]["outcome"])
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

    from . import io_cache
    from .session import temporal_session

    with (
        tempfile.TemporaryDirectory() as directory,
        temporal_session(Path(directory) / "project") as session,
    ):
        prepare(args.kind, session, directory)
        with io_cache.cached_io(io_cache.CacheStorage()):
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
