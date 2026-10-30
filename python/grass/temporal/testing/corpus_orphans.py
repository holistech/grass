"""Find the entries of the gold corpus that no test reads

A test run with ``GRASS_TEMPORAL_CORPUS_TRACE_DIR`` set records each key that
``grass.temporal.testing.corpus`` looks up (one file per process). This
module compares those keys with the entries of the corpus::

    python3 -m grass.temporal.testing.corpus_orphans <trace dir>

It prints one line ``<kind>: <count>`` for each kind of the corpus, followed
by the unread keys of that kind, and exits with 1 if any key is unread. Run
the tests in both settings of the algebra into the same trace directory
first: some cases only exist in one of them.

The check only reports. Deleting an entry drops an outcome of the earlier
implementation that can be recorded again only by running that
implementation.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from grass.temporal.testing import corpus

__all__ = ["main", "unread_entries"]

_SUFFIXES = (".jsonl.gz", ".jsonl")


def _kinds(directory):
    """Return the kinds that have a file in the corpus directory, sorted"""
    kinds = set()
    for path in directory.iterdir():
        for suffix in _SUFFIXES:
            if path.name.endswith(suffix):
                kinds.add(path.name[: -len(suffix)])
    return sorted(kinds)


def _read_keys(trace_dir):
    """Return the looked-up keys of all processes as a dict kind -> set"""
    read = {}
    for path in sorted(Path(trace_dir).glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            read.setdefault(record["kind"], set()).add(record["key"])
    return read


def unread_entries(trace_dir, corpus_dir=None):
    """Return the corpus keys that no traced lookup read, by kind

    :param trace_dir: The directory ``GRASS_TEMPORAL_CORPUS_TRACE_DIR`` named
    :param corpus_dir: The corpus directory, ``corpus.CORPUS_DIR`` by default
    :return: A dict from each kind that has a file in the corpus directory to
        its sorted unread keys; the list is empty when every entry was read,
        so the caller sees which kinds were checked
    """
    directory = Path(corpus_dir or corpus.CORPUS_DIR)
    read = _read_keys(trace_dir)
    return {
        kind: sorted(set(corpus.load(kind, directory)) - read.get(kind, set()))
        for kind in _kinds(directory)
    }


def main(argv=None):
    """Run the command line, see the module documentation"""
    parser = argparse.ArgumentParser(
        prog="python3 -m grass.temporal.testing.corpus_orphans",
        description="List the corpus entries that no traced test run read",
    )
    parser.add_argument("trace_dir", type=Path)
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=None,
        help="the corpus directory (default: the installed corpus)",
    )
    args = parser.parse_args(argv)
    unread = unread_entries(args.trace_dir, args.corpus_dir)
    for kind, keys in unread.items():
        print(f"{kind}: {len(keys)}")
        for key in keys:
            print(key)
    return 1 if any(unread.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
