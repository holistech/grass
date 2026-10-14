"""Tests of the batch runner of grass.temporal.mapcalc."""

import pytest

from grass.temporal.mapcalc import _run_in_batches


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
    assert _run_in_batches(ctx, print, ["a", "b", "c"], 2)
    started = [s for event, s in ctx.log if event == "start"]
    joined = [s for event, s in ctx.log if event == "join"]
    assert started == joined == ["a", "b", "c"]


def test_a_batch_is_joined_before_the_next_starts():
    ctx = FakeContext()
    _run_in_batches(ctx, print, ["a", "b", "c"], 2)
    assert ctx.log.index(("join", "b")) < ctx.log.index(("start", "c"))


def test_a_failing_statement_fails_the_run():
    assert not _run_in_batches(FakeContext(failing={"b"}), print, ["a", "b"], 2)


def test_no_statements():
    assert _run_in_batches(FakeContext(), print, [], 4)


@pytest.mark.parametrize("nprocs", [0, -1, 10])
def test_all_at_once_when_nprocs_is_below_one_or_not_below_the_count(nprocs):
    ctx = FakeContext()
    assert _run_in_batches(ctx, print, ["a", "b", "c"], nprocs)
    events = [event for event, _statement in ctx.log]
    assert events == ["start"] * 3 + ["join"] * 3


def test_progress_is_reported_after_each_batch():
    ctx = FakeContext()
    reported = []

    def progress(done, total):
        # A batch is reported only after it ran.
        reported.append((done, total, ("join", "c") in ctx.log))

    _run_in_batches(ctx, print, ["a", "b", "c"], 2, progress=progress)
    assert reported == [(2, 3, False), (3, 3, True)]


def test_progress_is_not_reported_for_a_failed_batch():
    reported = []
    _run_in_batches(
        FakeContext(failing={"a"}),
        print,
        ["a", "b"],
        1,
        progress=lambda done, total: reported.append(done),
    )
    assert reported == []
