"""Tests of the batch runner of grass.temporal.batches."""

import pytest

from grass.exceptions import CalledModuleError
from grass.temporal import batches
from grass.temporal.batches import run_in_batches


class FakeProcess:
    def __init__(self, log, target, args, exitcode):
        self.log = log
        self.statement = args[0]
        self.exitcode = None
        self._exitcode = exitcode

    def start(self):
        self.log.append(("start", self.statement))

    def join(self):
        self.log.append(("join", self.statement))
        self.exitcode = self._exitcode


class FakeContext:
    def __init__(self, failing=()):
        self.log = []
        self.failing = set(failing)

    def Process(self, target, args):
        return FakeProcess(self.log, target, args, 1 if args[0] in self.failing else 0)


def test_every_started_process_is_joined_before_return():
    ctx = FakeContext()
    assert run_in_batches(ctx, print, ["a", "b", "c"], 2)
    started = [s for event, s in ctx.log if event == "start"]
    joined = [s for event, s in ctx.log if event == "join"]
    assert started == joined == ["a", "b", "c"]


def test_a_batch_is_joined_before_the_next_starts():
    ctx = FakeContext()
    run_in_batches(ctx, print, ["a", "b", "c"], 2)
    assert ctx.log.index(("join", "b")) < ctx.log.index(("start", "c"))


def test_a_failing_statement_fails_the_run():
    assert not run_in_batches(FakeContext(failing={"b"}), print, ["a", "b"], 2)


def test_no_statements():
    assert run_in_batches(FakeContext(), print, [], 4)


@pytest.mark.parametrize("nprocs", [0, -1, 10])
def test_all_at_once_when_nprocs_is_below_one_or_not_below_the_count(nprocs):
    ctx = FakeContext()
    assert run_in_batches(ctx, print, ["a", "b", "c"], nprocs)
    events = [event for event, _statement in ctx.log]
    assert events == ["start"] * 3 + ["join"] * 3


def test_progress_is_reported_after_each_batch():
    ctx = FakeContext()
    reported = []

    def progress(done, total):
        # A batch is reported only after it ran.
        reported.append((done, total, ("join", "c") in ctx.log))

    run_in_batches(ctx, print, ["a", "b", "c"], 2, progress=progress)
    assert reported == [(2, 3, False), (3, 3, True)]


def test_progress_is_not_reported_for_a_failed_batch():
    reported = []
    run_in_batches(
        FakeContext(failing={"a"}),
        print,
        ["a", "b"],
        1,
        progress=lambda done, total: reported.append(done),
    )
    assert reported == []


def test_the_successful_statements_are_listed_also_from_a_failed_batch():
    succeeded = []

    ok = run_in_batches(
        FakeContext(failing={"b"}), print, ["a", "b", "c", "d"], 2, succeeded=succeeded
    )

    # The first batch is a and b, b fails, c and d never start.
    assert not ok
    assert succeeded == [0]


def test_the_successful_statements_of_every_batch_are_listed():
    succeeded = []

    run_in_batches(FakeContext(), print, ["a", "b", "c"], 2, succeeded=succeeded)

    assert succeeded == [0, 1, 2]


@pytest.mark.parametrize(
    ("nprocs", "options"), [(1, {"nprocs": 1}), (None, {})], ids=["threads", "default"]
)
def test_run_mapcalc_passes_nprocs_only_if_given(monkeypatch, nprocs, options):
    calls = []
    monkeypatch.setattr(
        batches.gs, "run_command", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    batches.run_mapcalc("r3.mapcalc", "a = 1", nprocs=nprocs)

    ((args, kwargs),) = calls
    assert args == ("r3.mapcalc",)
    assert kwargs == {
        "expression": "a = 1",
        "overwrite": batches.gs.overwrite(),
        "quiet": True,
        **options,
    }


def test_run_mapcalc_ends_the_process_with_one_if_the_module_fails(monkeypatch):
    module = "r.mapcalc"

    def fail(*args, **kwargs):
        raise CalledModuleError(module, "", 1)

    monkeypatch.setattr(batches.gs, "run_command", fail)

    with pytest.raises(SystemExit) as stop:
        batches.run_mapcalc("r.mapcalc", "a = 1")

    assert stop.value.code == 1
