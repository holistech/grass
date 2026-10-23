"""Recorded outcomes of the earlier classic implementation for the tests

The differential tests compare the classic profile of the algebra core, and
in places the core itself, with the earlier implementation of the classic
algebra (``grass.temporal.testing.reference``). That implementation is to be
deleted after the profile has served one release, and the comparison has to
outlive it. This module keeps what the earlier implementation computed for
each case of the test suite in a corpus and hands the stored outcome to the
tests in place of a run.

Two functions take the place of the runs of the earlier implementation:

- ``reference_outcome(kind, expression, **options)`` is
  ``outcome(kind, expression, RUNNERS["reference"], basename="fa", **options)``
  of ``grass.temporal.testing.expressions``.
- ``reference_rejects_syntax(kind, expression, **options)`` tells whether the
  earlier implementation rejects the expression with a ``SyntaxError`` when it
  runs without computing (``run=False``, without the granularity mode), the
  run that ``accepted_error_pair`` makes.

The corpus is the directory ``corpus`` next to this module, one file per kind
(``raster``, ``raster3d``, ``vector``, ``select``): ``<kind>.jsonl``, or
``<kind>.jsonl.gz`` when the plain file would be larger than ``SIZE_LIMIT``.
Each line is a JSON object with ``key`` and ``value``. The key is
``corpus_key()``: the node id of the test (``case_id()``), the kind, the
expression and the options, plus the mark ``"dry_run"`` for the run without
computing. So the same expression in two tests has two entries, and a test
that changes its data or its options cannot read an outcome of other data.
The value is the outcome or, for the run without computing, true or false.

The variable ``GRASS_TEMPORAL_REFERENCE`` chooses where the outcome comes
from:

- unset or ``corpus``: from the corpus, without running the earlier
  implementation. A case without entry fails with an ``AssertionError`` that
  names the key and how to record. If the variable is unset and
  ``GRASS_TEMPORAL_FUZZ_SEED`` or ``GRASS_TEMPORAL_FUZZ_COUNT`` is set, the
  run is an acceptance run with seeds outside the corpus, and the mode is
  ``live``.
- ``live``: the earlier implementation runs. Where the corpus holds the
  case, both must be equal, as ``expressions.compare()`` sees it and in the
  message, which ``compare()`` leaves out. A run of the suite in this mode
  shows that the corpus still holds what the implementation computes.
- ``record``: the earlier implementation runs, and each result is appended to
  a file in the directory that ``GRASS_TEMPORAL_REFERENCE_RECORD_DIR`` names,
  one file per process: ``<worker>-<pid>.jsonl``, with the worker of
  pytest-xdist or ``main``.

Outside a pytest test there is no case to look up; the earlier
implementation runs in every mode but ``record``, which needs the case.

To record the corpus again, run all test directories that use the earlier
implementation in one recording, then merge the files of the processes from
the root of the source tree and install the package::

    export GRASS_TEMPORAL_REFERENCE=record
    export GRASS_TEMPORAL_REFERENCE_RECORD_DIR=/tmp/corpus-records
    pytest -n auto <test directories>
    python3 -m grass.temporal.testing.corpus merge /tmp/corpus-records
    make -C python/grass/temporal

The record directory should be empty before the recording. ``merge`` writes
into ``python/grass/temporal/testing/corpus`` below the current directory,
because the tests import the installed package, whose directory is not the
one in version control; ``--corpus-dir`` names another directory. ``merge``
replaces the file of each kind in the records: a recording of only some
directories drops the cases of the others for that kind, which the next run
in mode ``corpus`` reports as missing.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import argparse
import collections
import copy
import gzip
import json
import os
import re
import sys
from pathlib import Path

MODE_VARIABLE = "GRASS_TEMPORAL_REFERENCE"
RECORD_DIR_VARIABLE = "GRASS_TEMPORAL_REFERENCE_RECORD_DIR"
MODES = ("corpus", "live", "record")
FUZZ_VARIABLES = ("GRASS_TEMPORAL_FUZZ_SEED", "GRASS_TEMPORAL_FUZZ_COUNT")

#: The directory the tests read
CORPUS_DIR = Path(__file__).with_name("corpus")
#: Where ``merge`` writes without ``--corpus-dir``, relative to the root of the
#: source tree
SOURCE_CORPUS_DIR = Path("python/grass/temporal/testing/corpus")
#: Bytes of a plain file above which ``merge`` writes it with gzip
SIZE_LIMIT = 1_000_000

_PHASE = re.compile(r" \((?:setup|call|teardown)\)$")
_MISSING = object()
# Parsed corpus files by (directory, kind); each test process reads a file
# once
_loaded = {}


def mode():
    """Return the mode: ``"corpus"``, ``"live"`` or ``"record"``

    :raises ValueError: for another value of ``GRASS_TEMPORAL_REFERENCE``
    """
    value = os.environ.get(MODE_VARIABLE)
    if not value:
        if any(os.environ.get(name) for name in FUZZ_VARIABLES):
            return "live"
        return "corpus"
    if value not in MODES:
        msg = f"{MODE_VARIABLE}={value} is none of {', '.join(MODES)}"
        raise ValueError(msg)
    return value


def case_id():
    """Return the node id of the running pytest test

    ``PYTEST_CURRENT_TEST`` is the node id followed by the phase in brackets,
    ``(setup)``, ``(call)`` or ``(teardown)``; only that suffix is removed,
    so a parameter that contains such text stays as it is.

    :raises RuntimeError: when no pytest test runs
    """
    current = os.environ.get("PYTEST_CURRENT_TEST")
    if current is None:
        msg = "case_id() needs a running pytest test"
        raise RuntimeError(msg)
    return _PHASE.sub("", current)


def corpus_key(kind, expression, options, *, dry_run=False):
    """Return the key of a case of the running test

    ``json.dumps([case_id(), kind, expression, options], sort_keys=True)``,
    with ``"dry_run"`` appended for the run without computing. The order of
    the options does not matter; a value that JSON cannot hold is written with
    ``repr``, which must not change between runs for the key to be found.
    """
    parts = [case_id(), kind, expression, options]
    if dry_run:
        parts.append("dry_run")
    return json.dumps(parts, sort_keys=True, default=repr)


def reference_outcome(kind, expression, **options):
    """Return the outcome of the earlier implementation for an expression

    The outcome is that of ``expressions.outcome()`` with the runner
    ``"reference"`` and the basename ``fa``, taken from the corpus or computed,
    as the mode says. Taken from the corpus, it leaves no dataset ``Rfa`` and
    no maps behind for the caller to read.

    :raises AssertionError: in mode ``corpus`` when the corpus lacks the case,
        in mode ``live`` when the corpus holds another outcome
    """
    return _reference(kind, expression, options, _run_outcome, dry_run=False)


def reference_rejects_syntax(kind, expression, **options):
    """Tell whether the earlier implementation rejects the syntax

    The earlier implementation runs ``Rfa = expression`` without computing
    (``run=False``) and without the granularity mode, which would read and
    sample the datasets before it parses. Any other error than a
    ``SyntaxError`` is no rejection.

    :raises AssertionError: as ``reference_outcome``
    """
    return _reference(kind, expression, options, _run_rejects_syntax, dry_run=True)


def _run_outcome(kind, expression, options):
    # Imported here: expressions uses this module, and a module level import
    # in both directions fails for whichever of the two is imported first
    from . import expressions

    return expressions.outcome(
        kind, expression, expressions.RUNNERS["reference"], basename="fa", **options
    )


def _run_rejects_syntax(kind, expression, options):
    from . import expressions

    options = {**options, "run": False, "debug": False}
    options.pop("granularity", None)
    try:
        expressions.RUNNERS["reference"](
            kind, f"Rfa = {expression}", basename="fa", overwrite=True, **options
        )
    except SyntaxError:
        return True
    except Exception:  # noqa: BLE001, any other error means: not rejected
        return False
    return False


def _reference(kind, expression, options, run, *, dry_run):
    chosen = mode()
    if chosen != "record" and "PYTEST_CURRENT_TEST" not in os.environ:
        return run(kind, expression, options)
    key = corpus_key(kind, expression, options, dry_run=dry_run)
    if chosen == "corpus":
        stored = _lookup(kind, key)
        if stored is _MISSING:
            msg = (
                f"The corpus {CORPUS_DIR}/{kind}.jsonl[.gz] holds no outcome of the "
                f"earlier implementation for {key}; record it with "
                f"{MODE_VARIABLE}=record, see grass.temporal.testing.corpus"
            )
            raise AssertionError(msg)
        return stored
    value = run(kind, expression, options)
    if chosen == "record":
        _append(kind, key, value)
        return value
    stored = _lookup(kind, key)
    if stored is not _MISSING and not _same(kind, expression, stored, value, dry_run):
        msg = (
            f"The earlier implementation no longer computes what the corpus "
            f"holds for {key}: corpus {stored}, now {value}"
        )
        raise AssertionError(msg)
    return value


def _same(kind, expression, stored, value, dry_run):
    if dry_run:
        return stored == value
    from . import expressions

    if expressions.compare(kind, expression, stored, value) is not None:
        return False
    return stored.get("msg") == value.get("msg")


def _lookup(kind, key):
    """Return a copy of the stored value, or _MISSING"""
    entries = load(kind)
    if key not in entries:
        return _MISSING
    # A copy, so that a test that changes what it got cannot change what
    # later tests of the process read
    return copy.deepcopy(entries[key])


def load(kind, directory=None):
    """Return the corpus of a kind as a dict from key to value

    :param directory: The corpus directory, ``CORPUS_DIR`` by default
    :return: An empty dict when the directory has no file of the kind
    :raises RuntimeError: when it has both a plain and a gzip file
    """
    directory = Path(directory or CORPUS_DIR)
    if (directory, kind) in _loaded:
        return _loaded[directory, kind]
    plain = directory / f"{kind}.jsonl"
    packed = directory / f"{kind}.jsonl.gz"
    if plain.exists() and packed.exists():
        msg = f"Both {plain} and {packed} exist; remove the one that is stale"
        raise RuntimeError(msg)
    if packed.exists():
        text = gzip.decompress(packed.read_bytes()).decode("utf-8")
    elif plain.exists():
        text = plain.read_text(encoding="utf-8")
    else:
        text = ""
    entries = {}
    for line in text.splitlines():
        record = json.loads(line)
        entries[record["key"]] = record["value"]
    _loaded[directory, kind] = entries
    return entries


def _append(kind, key, value):
    directory = os.environ.get(RECORD_DIR_VARIABLE)
    if not directory:
        msg = f"{MODE_VARIABLE}=record needs {RECORD_DIR_VARIABLE}"
        raise RuntimeError(msg)
    worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
    # The process id keeps two pytest runs that record at the same time, each
    # with a worker gw0, out of one file
    path = Path(directory) / f"{worker}-{os.getpid()}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"kind": kind, "key": key, "value": value}, sort_keys=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def merge_records(record_dir, corpus_dir):
    """Write the files of a recording as the corpus of their kinds

    Reads every ``*.jsonl`` file of ``record_dir`` before it writes. A key
    that occurs more than once with the same value is kept once. The file of
    each kind is replaced, sorted by key; a kind without records keeps its
    file. A file larger than ``SIZE_LIMIT`` bytes is written with gzip
    (without time stamp, so the same corpus gives the same bytes), and the
    other form of the kind is removed.

    :return: The number of entries by kind
    :raises ValueError: when one key has two values, or no record exists
    """
    entries = collections.defaultdict(dict)
    paths = sorted(Path(record_dir).glob("*.jsonl"))
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            record = json.loads(line)
            known = entries[record["kind"]].setdefault(record["key"], record["value"])
            if known != record["value"]:
                msg = (
                    f"{path}:{number}: two values for {record['key']}: "
                    f"{known} and {record['value']}"
                )
                raise ValueError(msg)
    if not entries:
        msg = f"There are no records in {record_dir}"
        raise ValueError(msg)
    corpus_dir = Path(corpus_dir)
    corpus_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for kind in sorted(entries):
        values = entries[kind]
        data = "".join(
            json.dumps({"key": key, "value": values[key]}, sort_keys=True) + "\n"
            for key in sorted(values)
        ).encode("utf-8")
        plain = corpus_dir / f"{kind}.jsonl"
        packed = corpus_dir / f"{kind}.jsonl.gz"
        if len(data) > SIZE_LIMIT:
            packed.write_bytes(gzip.compress(data, mtime=0))
            plain.unlink(missing_ok=True)
        else:
            plain.write_bytes(data)
            packed.unlink(missing_ok=True)
        _loaded.pop((corpus_dir, kind), None)
        counts[kind] = len(values)
    return counts


def main(argv=None):
    """Run the command line, see the module documentation"""
    parser = argparse.ArgumentParser(
        prog="python3 -m grass.temporal.testing.corpus",
        description="Manage the recorded outcomes of the earlier classic algebra",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    merge = commands.add_parser(
        "merge", help="write the files of a recording as the corpus"
    )
    merge.add_argument("record_dir", type=Path)
    merge.add_argument(
        "--corpus-dir",
        type=Path,
        default=SOURCE_CORPUS_DIR,
        help=f"the corpus directory (default: {SOURCE_CORPUS_DIR})",
    )
    args = parser.parse_args(argv)
    if not args.corpus_dir.parent.is_dir():
        parser.error(
            f"{args.corpus_dir.parent} does not exist; run from the root of the "
            "source tree or give --corpus-dir"
        )
    for kind, count in merge_records(args.record_dir, args.corpus_dir).items():
        print(f"{kind}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
