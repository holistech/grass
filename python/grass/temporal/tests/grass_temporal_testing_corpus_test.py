"""Tests for the recorded corpus of the earlier classic implementation

A stand-in replaces the earlier implementation: differential.outcome() for the
outcome and RUNNERS["reference"] for the run without computing. No test runs
GRASS. The keys hold the node id of the running test, which pytest sets at
the start of each phase; a test that needs another id sets it itself.
"""

import gzip
import json

import pytest

from grass.temporal.testing import corpus, differential

CASE = 'temporal/t.x/tests/t_x_test.py::test_case[if(A, "x", B)]'
EXPRESSION = 'if(start_doy(A) < 3, "x", A)'
MAPS = {"stds": True, "ttype": "absolute", "maps": [["N_1", "2001-01-01", None, 1.0]]}
SYNTAX = {"error": "SyntaxError", "msg": "Syntax error near #"}


@pytest.fixture
def setting(monkeypatch, tmp_path):
    """An empty corpus directory and a record directory, no mode set"""
    monkeypatch.setattr(corpus, "CORPUS_DIR", tmp_path / "corpus")
    for name in (
        corpus.MODE_VARIABLE,
        corpus.RECORD_DIR_VARIABLE,
        "GRASS_TEMPORAL_FUZZ_SEED",
        "GRASS_TEMPORAL_FUZZ_COUNT",
        "PYTEST_XDIST_WORKER",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(corpus.RECORD_DIR_VARIABLE, str(tmp_path / "records"))
    return tmp_path


@pytest.fixture
def reference(monkeypatch):
    """Replace the earlier implementation by a stand-in

    The returned dict sets what the stand-in gives: the outcome under
    "outcome", and under "rejects" whether the run without computing raises a
    SyntaxError. "calls" counts the runs of both.
    """
    stand_in = {"outcome": MAPS, "rejects": True, "calls": []}

    def fake_outcome(kind, expression, runner, *, basename, **options):
        assert runner is differential.RUNNERS["reference"]
        stand_in["calls"].append(("outcome", kind, expression, basename, options))
        return json.loads(json.dumps(stand_in["outcome"]))

    def fake_runner(kind, expression, *, basename, overwrite, **options):
        stand_in["calls"].append(("dry_run", kind, expression, basename, options))
        if stand_in["rejects"]:
            msg = "rejected"
            raise SyntaxError(msg)

    monkeypatch.setattr(differential, "outcome", fake_outcome)
    monkeypatch.setitem(differential.RUNNERS, "reference", fake_runner)
    return stand_in


def write_corpus(directory, kind, entries, *, packed=False):
    """Write a corpus file of a kind from (key, value) pairs by hand"""
    directory.mkdir(parents=True, exist_ok=True)
    text = "".join(
        json.dumps({"key": key, "value": value}, sort_keys=True) + "\n"
        for key, value in entries
    )
    if packed:
        (directory / f"{kind}.jsonl.gz").write_bytes(gzip.compress(text.encode()))
    else:
        (directory / f"{kind}.jsonl").write_text(text)


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
def test_case_id_drops_the_phase(monkeypatch, phase):
    """Only the phase that pytest appends goes, not a phase inside the id"""
    node = "temporal/t.x/tests/t_x_test.py::test_case[A (call) B]"
    monkeypatch.setenv("PYTEST_CURRENT_TEST", f"{node} ({phase})")
    assert corpus.case_id() == node


def test_case_id_needs_a_test(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    with pytest.raises(RuntimeError, match="pytest"):
        corpus.case_id()


def test_the_key_is_stable_for_quotes_and_brackets(setting, monkeypatch):
    """The same case gives the same key, serially and in a worker of xdist"""
    monkeypatch.setenv("PYTEST_CURRENT_TEST", f"{CASE} (call)")
    options = {"spatial": True, "stdstype": "strds"}
    first = corpus.corpus_key("select", EXPRESSION, options)
    assert corpus.corpus_key("select", EXPRESSION, dict(reversed(options.items()))) == (
        first
    )
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw3")
    assert corpus.corpus_key("select", EXPRESSION, options) == first
    assert json.loads(first) == [CASE, "select", EXPRESSION, options]
    dry_run = corpus.corpus_key("select", EXPRESSION, options, dry_run=True)
    assert dry_run != first


def test_the_key_writes_other_values_with_repr(setting):
    key = corpus.corpus_key("raster", "A", {"where": {1, 2}})
    assert json.loads(key)[3] == {"where": "{1, 2}"}


def test_corpus_mode_reads_without_running(setting, reference):
    """Outcome and run without computing of one case are two entries"""
    write_corpus(
        setting / "corpus",
        "raster",
        [
            (corpus.corpus_key("raster", EXPRESSION, {"spatial": True}), SYNTAX),
            (
                corpus.corpus_key(
                    "raster", EXPRESSION, {"spatial": True}, dry_run=True
                ),
                False,
            ),
        ],
    )
    assert corpus.reference_outcome("raster", EXPRESSION, spatial=True) == SYNTAX
    assert corpus.reference_rejects_syntax("raster", EXPRESSION, spatial=True) is False
    assert reference["calls"] == []


def test_corpus_mode_fails_for_a_missing_case(setting, reference, monkeypatch):
    """The same expression of another test case is no entry for this one"""
    write_corpus(
        setting / "corpus",
        "raster",
        [(corpus.corpus_key("raster", EXPRESSION, {}), MAPS)],
    )
    monkeypatch.setenv("PYTEST_CURRENT_TEST", f"{CASE} (call)")
    with pytest.raises(AssertionError, match="GRASS_TEMPORAL_REFERENCE=record"):
        corpus.reference_outcome("raster", EXPRESSION)
    with pytest.raises(AssertionError, match="GRASS_TEMPORAL_REFERENCE=record"):
        corpus.reference_rejects_syntax("raster", EXPRESSION)
    assert reference["calls"] == []


def test_a_returned_outcome_does_not_change_the_corpus(setting, reference):
    write_corpus(
        setting / "corpus",
        "raster",
        [(corpus.corpus_key("raster", EXPRESSION, {}), MAPS)],
    )
    corpus.reference_outcome("raster", EXPRESSION)["maps"].clear()
    assert corpus.reference_outcome("raster", EXPRESSION) == MAPS


def test_live_mode_runs_the_reference(setting, reference, monkeypatch):
    """Without entry the outcome of the reference passes through"""
    monkeypatch.setenv(corpus.MODE_VARIABLE, "live")
    assert corpus.reference_outcome("vector", EXPRESSION, spatial=True) == MAPS
    assert corpus.reference_rejects_syntax("vector", EXPRESSION, granularity=True)
    assert reference["calls"] == [
        ("outcome", "vector", EXPRESSION, "fa", {"spatial": True}),
        (
            "dry_run",
            "vector",
            f"Rfa = {EXPRESSION}",
            "fa",
            {"run": False, "debug": False},
        ),
    ]


def test_live_mode_accepts_the_reference_that_equals_the_corpus(
    setting, reference, monkeypatch
):
    write_corpus(
        setting / "corpus",
        "raster",
        [
            (corpus.corpus_key("raster", EXPRESSION, {}), MAPS),
            (corpus.corpus_key("raster", EXPRESSION, {}, dry_run=True), True),
        ],
    )
    monkeypatch.setenv(corpus.MODE_VARIABLE, "live")
    assert corpus.reference_outcome("raster", EXPRESSION) == MAPS
    assert corpus.reference_rejects_syntax("raster", EXPRESSION) is True
    assert len(reference["calls"]) == 2


@pytest.mark.parametrize(
    "now",
    [
        {"error": "FatalError", "msg": SYNTAX["msg"]},
        {"error": "SyntaxError", "msg": "Syntax error at end of input"},
        {**MAPS, "maps": [["N_1", "2001-01-01", None, 2.0]]},
    ],
    ids=["class", "message", "value"],
)
def test_live_mode_fails_when_the_reference_differs_from_the_corpus(
    setting, reference, monkeypatch, now
):
    """compare() sees class and value, the message is compared besides"""
    stored = MAPS if "maps" in now else SYNTAX
    write_corpus(
        setting / "corpus",
        "raster",
        [(corpus.corpus_key("raster", EXPRESSION, {}), stored)],
    )
    monkeypatch.setenv(corpus.MODE_VARIABLE, "live")
    reference["outcome"] = now
    with pytest.raises(AssertionError, match="no longer computes"):
        corpus.reference_outcome("raster", EXPRESSION)


def test_live_mode_fails_when_the_dry_run_differs_from_the_corpus(
    setting, reference, monkeypatch
):
    write_corpus(
        setting / "corpus",
        "raster",
        [(corpus.corpus_key("raster", EXPRESSION, {}, dry_run=True), True)],
    )
    monkeypatch.setenv(corpus.MODE_VARIABLE, "live")
    reference["rejects"] = False
    with pytest.raises(AssertionError, match="no longer computes"):
        corpus.reference_rejects_syntax("raster", EXPRESSION)


@pytest.mark.parametrize(
    "variable", ["GRASS_TEMPORAL_FUZZ_SEED", "GRASS_TEMPORAL_FUZZ_COUNT"]
)
def test_fuzz_seeds_run_the_reference_live(setting, reference, monkeypatch, variable):
    """Seeds outside the corpus run on the reference, entries still count"""
    write_corpus(
        setting / "corpus",
        "raster",
        [(corpus.corpus_key("raster", EXPRESSION, {}), SYNTAX)],
    )
    monkeypatch.setenv(variable, "5000")
    assert corpus.mode() == "live"
    assert corpus.reference_outcome("raster", "A") == MAPS
    with pytest.raises(AssertionError, match="no longer computes"):
        corpus.reference_outcome("raster", EXPRESSION)
    monkeypatch.setenv(corpus.MODE_VARIABLE, "corpus")
    assert corpus.mode() == "corpus"


def test_outside_pytest_the_reference_runs(setting, reference, monkeypatch):
    """A batch has no test case to look up"""
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    assert corpus.reference_outcome("raster", EXPRESSION) == MAPS
    assert len(reference["calls"]) == 1


def test_an_unknown_mode_is_refused(setting, reference, monkeypatch):
    monkeypatch.setenv(corpus.MODE_VARIABLE, "corpora")
    with pytest.raises(ValueError, match="corpora"):
        corpus.reference_outcome("raster", EXPRESSION)
    assert reference["calls"] == []


def test_record_mode_needs_a_directory(setting, reference, monkeypatch):
    monkeypatch.setenv(corpus.MODE_VARIABLE, "record")
    monkeypatch.delenv(corpus.RECORD_DIR_VARIABLE)
    with pytest.raises(RuntimeError, match=corpus.RECORD_DIR_VARIABLE):
        corpus.reference_outcome("raster", EXPRESSION)


def test_record_and_merge_round_trip(setting, reference, monkeypatch):
    """Two processes, one case in both; merge keeps it once, in key order"""
    monkeypatch.setenv(corpus.MODE_VARIABLE, "record")
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw0")
    corpus.reference_outcome("raster", "B")
    corpus.reference_rejects_syntax("raster", "B")
    reference["outcome"] = SYNTAX
    corpus.reference_outcome("vector", "A")
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw1")
    corpus.reference_outcome("vector", "A")
    reference["outcome"] = MAPS
    corpus.reference_outcome("raster", "A", spatial=True)
    records = setting / "records"
    assert sorted(path.name.split("-")[0] for path in records.iterdir()) == [
        "gw0",
        "gw1",
    ]

    counts = corpus.merge_records(records, setting / "corpus")

    assert counts == {"raster": 3, "vector": 1}
    lines = (setting / "corpus" / "raster.jsonl").read_text().splitlines()
    keys = [json.loads(line)["key"] for line in lines]
    assert keys == sorted(keys)
    monkeypatch.setenv(corpus.MODE_VARIABLE, "corpus")
    reference["outcome"] = None
    assert corpus.reference_outcome("raster", "B") == MAPS
    assert corpus.reference_rejects_syntax("raster", "B") is True
    assert corpus.reference_outcome("raster", "A", spatial=True) == MAPS
    assert corpus.reference_outcome("vector", "A") == SYNTAX
    # 3 outcomes and 1 run without computing while recording, none after
    assert len(reference["calls"]) == 5


def test_merge_replaces_the_corpus_of_a_kind(setting, reference, monkeypatch):
    """A case that the new recording lacks leaves the corpus"""
    write_corpus(setting / "corpus", "raster", [("old", MAPS)])
    write_corpus(setting / "corpus", "vector", [("kept", MAPS)])
    monkeypatch.setenv(corpus.MODE_VARIABLE, "record")
    corpus.reference_outcome("raster", "A")
    corpus.merge_records(setting / "records", setting / "corpus")
    lines = (setting / "corpus" / "raster.jsonl").read_text().splitlines()
    assert [json.loads(line)["key"] for line in lines] == [
        corpus.corpus_key("raster", "A", {})
    ]
    assert "kept" in (setting / "corpus" / "vector.jsonl").read_text()


def test_merge_refuses_two_values_for_one_key(setting, reference, monkeypatch):
    """A later file contradicts an earlier one; nothing is written"""
    monkeypatch.setenv(corpus.MODE_VARIABLE, "record")
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw0")
    corpus.reference_outcome("raster", "A")
    corpus.reference_outcome("raster", "B")
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw1")
    corpus.reference_outcome("raster", "B")
    reference["outcome"] = SYNTAX
    corpus.reference_outcome("raster", "A")
    with pytest.raises(ValueError, match="two values"):
        corpus.merge_records(setting / "records", setting / "corpus")
    assert not (setting / "corpus").exists()


def test_merge_refuses_an_empty_record_directory(setting):
    (setting / "records").mkdir()
    with pytest.raises(ValueError, match="no records"):
        corpus.merge_records(setting / "records", setting / "corpus")


def test_a_gzip_corpus_is_read(setting, reference):
    write_corpus(
        setting / "corpus",
        "raster3d",
        [(corpus.corpus_key("raster3d", EXPRESSION, {}), MAPS)],
        packed=True,
    )
    assert corpus.reference_outcome("raster3d", EXPRESSION) == MAPS
    assert reference["calls"] == []


def test_two_files_of_one_kind_are_refused(setting, reference):
    """Which of a plain and a packed file is current cannot be told"""
    entries = [(corpus.corpus_key("raster", EXPRESSION, {}), MAPS)]
    write_corpus(setting / "corpus", "raster", entries)
    write_corpus(setting / "corpus", "raster", entries, packed=True)
    with pytest.raises(RuntimeError, match=r"raster\.jsonl\.gz"):
        corpus.reference_outcome("raster", EXPRESSION)


def test_merge_packs_a_corpus_above_the_limit(setting, reference, monkeypatch):
    """Above the limit only the packed file stays, below only the plain one"""
    monkeypatch.setenv(corpus.MODE_VARIABLE, "record")
    corpus.reference_outcome("raster", "A")
    corpus.merge_records(setting / "records", setting / "corpus")
    plain = (setting / "corpus" / "raster.jsonl").read_bytes()
    monkeypatch.setattr(corpus, "SIZE_LIMIT", 10)
    corpus.merge_records(setting / "records", setting / "corpus")
    assert sorted(path.name for path in (setting / "corpus").iterdir()) == [
        "raster.jsonl.gz"
    ]
    packed = (setting / "corpus" / "raster.jsonl.gz").read_bytes()
    monkeypatch.setenv(corpus.MODE_VARIABLE, "corpus")
    assert corpus.reference_outcome("raster", "A") == MAPS

    monkeypatch.setattr(corpus, "SIZE_LIMIT", 10**6)
    corpus.merge_records(setting / "records", setting / "corpus")
    assert sorted(path.name for path in (setting / "corpus").iterdir()) == [
        "raster.jsonl"
    ]
    assert gzip.decompress(packed) == plain
    assert (setting / "corpus" / "raster.jsonl").read_bytes() == plain


def test_merge_packs_all_kinds_when_together_above_the_limit(
    setting, reference, monkeypatch
):
    """The limit holds for the corpus, so kinds below it alone are packed too

    The limit is set to the larger of the two plain files: neither is above it
    alone, both together are. The vector file comes from an earlier recording
    and is packed with the same content.
    """
    write_corpus(setting / "corpus", "vector", [("kept", MAPS)])
    vector_bytes = (setting / "corpus" / "vector.jsonl").read_bytes()
    monkeypatch.setenv(corpus.MODE_VARIABLE, "record")
    corpus.reference_outcome("raster", "A")
    corpus.merge_records(setting / "records", setting / "corpus")
    raster_bytes = (setting / "corpus" / "raster.jsonl").read_bytes()
    monkeypatch.setattr(corpus, "SIZE_LIMIT", max(len(raster_bytes), len(vector_bytes)))
    corpus.merge_records(setting / "records", setting / "corpus")
    assert sorted(path.name for path in (setting / "corpus").iterdir()) == [
        "raster.jsonl.gz",
        "vector.jsonl.gz",
    ]
    for kind, plain in [("raster", raster_bytes), ("vector", vector_bytes)]:
        packed = (setting / "corpus" / f"{kind}.jsonl.gz").read_bytes()
        assert gzip.decompress(packed) == plain


def test_merge_packs_without_a_time_stamp(setting, reference, monkeypatch):
    """The same corpus gives the same bytes, so a new recording diffs cleanly

    Bytes 4 to 7 of a gzip file are its time stamp (RFC 1952); two merges in
    one second would agree even with one.
    """
    monkeypatch.setenv(corpus.MODE_VARIABLE, "record")
    corpus.reference_outcome("raster", "A")
    monkeypatch.setattr(corpus, "SIZE_LIMIT", 10)
    corpus.merge_records(setting / "records", setting / "corpus")
    assert (setting / "corpus" / "raster.jsonl.gz").read_bytes()[4:8] == bytes(4)


def test_the_command_merges_into_the_source_tree(
    setting, reference, monkeypatch, capsys
):
    """Without --corpus-dir the command writes below the current directory"""
    monkeypatch.setenv(corpus.MODE_VARIABLE, "record")
    corpus.reference_outcome("raster", "A")
    tree = setting / "tree"
    (tree / "python/grass/temporal/testing").mkdir(parents=True)
    monkeypatch.chdir(tree)
    assert corpus.main(["merge", str(setting / "records")]) == 0
    assert (tree / "python/grass/temporal/testing/corpus/raster.jsonl").is_file()
    assert "raster: 1" in capsys.readouterr().out


def test_the_command_refuses_to_run_outside_the_source_tree(
    setting, reference, monkeypatch
):
    monkeypatch.setenv(corpus.MODE_VARIABLE, "record")
    corpus.reference_outcome("raster", "A")
    monkeypatch.chdir(setting)
    with pytest.raises(SystemExit):
        corpus.main(["merge", str(setting / "records")])
    assert not (setting / "python").exists()
