"""Tests for the trace of corpus lookups and the check for unread entries

A temporary corpus directory with two entries of the kind ``raster`` and two
of the kind ``select`` stands in for the real corpus. The lookups run through
``corpus.reference_outcome()`` in the mode ``corpus``, the way the tests of the
algebra read the corpus.
"""

import json
import os
import subprocess
import sys

import pytest

from grass.temporal.testing import corpus, corpus_orphans

SYNTAX = {"error": "SyntaxError", "msg": "Syntax error near #"}
CASE = "temporal/t.x/tests/t_x_test.py::test_case"
EXPRESSIONS = ("A + B", "A - B")


def key_of(kind, expression):
    """Return the corpus key of an expression in the test case"""
    return corpus.corpus_key(kind, expression, {})


def use_case(monkeypatch):
    """Fix the node id that the keys hold; pytest resets it at each phase"""
    monkeypatch.setenv("PYTEST_CURRENT_TEST", f"{CASE} (call)")


@pytest.fixture
def setting(monkeypatch, tmp_path):
    """A corpus directory with two entries per kind and the mode ``corpus``"""
    directory = tmp_path / "corpus"
    directory.mkdir()
    monkeypatch.setattr(corpus, "CORPUS_DIR", directory)
    use_case(monkeypatch)
    monkeypatch.setenv(corpus.MODE_VARIABLE, "corpus")
    monkeypatch.delenv(corpus_orphans.TRACE_DIR_VARIABLE, raising=False)
    for kind in ("raster", "select"):
        lines = [
            json.dumps({"key": key_of(kind, expression), "value": SYNTAX})
            for expression in EXPRESSIONS
        ]
        (directory / f"{kind}.jsonl").write_text("\n".join(lines) + "\n")
    return tmp_path


def test_lookup_writes_the_key_when_tracing(setting, monkeypatch):
    use_case(monkeypatch)
    trace = setting / "trace"
    monkeypatch.setenv(corpus_orphans.TRACE_DIR_VARIABLE, str(trace))
    assert corpus.reference_outcome("raster", EXPRESSIONS[0]) == SYNTAX
    files = list(trace.iterdir())
    assert len(files) == 1
    lines = files[0].read_text().splitlines()
    assert [json.loads(line) for line in lines] == [
        {"kind": "raster", "key": key_of("raster", EXPRESSIONS[0])}
    ]


def test_lookup_writes_nothing_without_the_variable(setting, monkeypatch):
    use_case(monkeypatch)
    assert corpus.reference_outcome("raster", EXPRESSIONS[0]) == SYNTAX
    assert sorted(path.name for path in setting.iterdir()) == ["corpus"]


def test_unread_entries_names_the_entry_no_test_read(setting, monkeypatch):
    use_case(monkeypatch)
    trace = setting / "trace"
    monkeypatch.setenv(corpus_orphans.TRACE_DIR_VARIABLE, str(trace))
    corpus.reference_outcome("raster", EXPRESSIONS[0])
    corpus.reference_outcome("select", EXPRESSIONS[0])
    corpus.reference_outcome("select", EXPRESSIONS[1])
    # Every kind of the corpus shows up, the one without orphans with an empty
    # list, so that the caller sees which kinds were checked
    assert corpus_orphans.unread_entries(trace) == {
        "raster": [key_of("raster", EXPRESSIONS[1])],
        "select": [],
    }


def test_unread_entries_reads_the_traces_of_all_processes(setting, monkeypatch):
    use_case(monkeypatch)
    trace = setting / "trace"
    trace.mkdir()
    for pid, expression in enumerate(EXPRESSIONS):
        line = json.dumps({"kind": "raster", "key": key_of("raster", expression)})
        (trace / f"{pid}.jsonl").write_text(line + "\n")
    unread = corpus_orphans.unread_entries(trace)
    assert unread["raster"] == []
    assert unread["select"] == sorted(key_of("select", e) for e in EXPRESSIONS)


def test_unread_entries_takes_another_corpus_directory(setting, tmp_path):
    trace = tmp_path / "trace"
    trace.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    (other / "vector.jsonl").write_text(
        json.dumps({"key": "k", "value": SYNTAX}) + "\n"
    )
    assert corpus_orphans.unread_entries(trace, other) == {"vector": ["k"]}


def run_script(trace, corpus_dir):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "grass.temporal.testing.corpus_orphans",
            str(trace),
            "--corpus-dir",
            str(corpus_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"},
    )


def test_the_script_exits_with_1_when_an_entry_is_unread(setting, monkeypatch):
    use_case(monkeypatch)
    trace = setting / "trace"
    monkeypatch.setenv(corpus_orphans.TRACE_DIR_VARIABLE, str(trace))
    corpus.reference_outcome("raster", EXPRESSIONS[0])
    result = run_script(trace, setting / "corpus")
    assert result.returncode == 1, result.stderr
    lines = result.stdout.splitlines()
    assert "raster: 1" in lines
    assert "select: 2" in lines
    assert key_of("raster", EXPRESSIONS[1]) in lines


def test_the_script_exits_with_0_when_all_are_read(setting, monkeypatch):
    use_case(monkeypatch)
    trace = setting / "trace"
    monkeypatch.setenv(corpus_orphans.TRACE_DIR_VARIABLE, str(trace))
    for kind in ("raster", "select"):
        for expression in EXPRESSIONS:
            corpus.reference_outcome(kind, expression)
    result = run_script(trace, setting / "corpus")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["raster: 0", "select: 0"]
