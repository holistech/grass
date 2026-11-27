"""Tests for the session helpers of grass.temporal.testing.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import contextlib
import os
import signal
import subprocess
import sys
import time

import pytest

import grass.script as gs
import grass.temporal as tgis
import grass.temporal.testing.session
from grass.temporal.state import get_raise_on_error, set_raise_on_error
from grass.exceptions import FatalError
from grass.pygrass.messages import get_msgr
from grass.temporal.state import STATE
from grass.temporal.testing.session import (
    add_mapset,
    find_program,
    mapset_session,
    output_after_stop,
    project_session,
    start_process_tree,
    stop_process_tree,
    temporal_session,
)

pytestmark = pytest.mark.real_io


def test_project_session_leaves_os_environ_alone(tmp_path):
    before = dict(os.environ)
    with project_session(tmp_path / "p") as session:
        assert session.env["GISRC"]
        assert dict(os.environ) == before
    assert dict(os.environ) == before


def test_temporal_session_mirrors_and_restores_os_environ(tmp_path):
    before = dict(os.environ)
    with temporal_session(tmp_path / "p") as session:
        assert os.environ["GISRC"] == session.env["GISRC"]
    assert dict(os.environ) == before


def test_temporal_session_restores_os_environ_after_exception(tmp_path):
    before = dict(os.environ)
    with pytest.raises(ZeroDivisionError), temporal_session(tmp_path / "p"):
        raise ZeroDivisionError
    assert dict(os.environ) == before


def test_temporal_session_raises_and_restores_module_flag(tmp_path):
    # A known value, so that the restore is not compared with the value
    # that the block sets anyway.
    before = get_raise_on_error()
    set_raise_on_error(False)
    try:
        with temporal_session(tmp_path / "p"):
            assert get_raise_on_error() is True
        assert get_raise_on_error() is False
    finally:
        set_raise_on_error(before)


@pytest.mark.parametrize("before_block", [False, True])
def test_messenger_mode_is_set_and_restored(tmp_path, before_block):
    """Both orders: the messenger exists with either mode before the block.

    init() does not change the mode of an existing messenger, so the helper
    has to set it and put the old mode back. After the block the mode is
    probed with msgr.fatal(), because open_old_stds() cannot run there: with
    no session it fails with OSError (t.connect not found; probed 2026-10-15).
    """
    msgr = get_msgr()
    found = msgr.raise_on_error
    msgr.set_raise_on_error(before_block)
    try:
        with temporal_session(tmp_path / "p"):
            assert msgr.raise_on_error is True
            with pytest.raises(FatalError):
                tgis.open_old_stds("missing", "strds")
        assert msgr.raise_on_error is before_block
        if not before_block:
            with pytest.raises(SystemExit):
                msgr.fatal("probe")
    finally:
        msgr.set_raise_on_error(found)


def test_messenger_created_by_the_block_is_left_in_exit_mode(tmp_path):
    """A messenger that init() creates in the block is back in exit mode after.

    This pins the restore rule for a process without a messenger: later tests
    expect sys.exit on fatal errors. The cache of get_msgr() and
    STATE.message_interface are emptied for the test, because there is no
    other way to start from "no messenger", and both are put back afterwards.
    """
    cache = get_msgr.__defaults__[0]
    original = cache[0]
    original_interface = STATE.message_interface
    cache[0] = None
    STATE.message_interface = None
    try:
        with temporal_session(tmp_path / "p"):
            assert get_msgr().raise_on_error is True
        created = get_msgr()
        assert created is not original
        assert created.raise_on_error is False
        created.server.terminate()
    finally:
        cache[0] = original
        STATE.message_interface = original_interface


def test_mapset_is_created_and_entered(tmp_path):
    with project_session(tmp_path / "p", mapset="other") as session:
        assert gs.read_command("g.gisenv", get="MAPSET", env=session.env).strip() == (
            "other"
        )


def test_add_mapset_keeps_current_mapset(tmp_path):
    with project_session(tmp_path / "p") as session:
        add_mapset(session, "user1")
        mapsets = gs.read_command("g.mapsets", flags="l", env=session.env)
        assert "user1" in mapsets.split()
        current = gs.read_command("g.gisenv", get="MAPSET", env=session.env)
        assert current.strip() == "PERMANENT"


def test_mapset_session_runs_next_to_the_first_session(tmp_path):
    with (
        project_session(tmp_path / "p", mapset="work") as work,
        mapset_session(work, "other") as other,
    ):
        for session, mapset in ((work, "work"), (other, "other")):
            current = gs.read_command("g.gisenv", get="MAPSET", env=session.env)
            assert current.strip() == mapset
        gs.run_command("g.region", n=1, s=0, e=1, w=0, res=1, env=other.env)
        gs.mapcalc("m = 1", env=other.env)
        # The first session does not see the map before it adds the mapset.
        assert gs.list_strings("raster", env=work.env) == []
        gs.run_command("g.mapsets", operation="add", mapset="other", env=work.env)
        assert gs.list_strings("raster", env=work.env) == ["m@other"]


def test_mapset_session_takes_an_existing_mapset(tmp_path):
    with project_session(tmp_path / "p", mapset="work") as work:
        add_mapset(work, "other")
        with mapset_session(work, "other") as other:
            current = gs.read_command("g.gisenv", get="MAPSET", env=other.env)
            assert current.strip() == "other"


# The parent starts a child that sleeps, prints the pid of the child and
# sleeps itself. Both write to the stdout pipe of the test, so the test reads
# the end of the pipe only when both processes are gone; that works the same
# on every platform.
PARENT_WITH_CHILD = (
    "import subprocess, sys, time\n"
    "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
    "print(child.pid, flush=True)\n"
    "time.sleep(120)\n"
)


def start_parent_with_child():
    """Start the parent and return it with the pid of its child"""
    process = start_process_tree(
        [sys.executable, "-c", PARENT_WITH_CHILD],
        stdout=subprocess.PIPE,
        text=True,
    )
    return process, int(process.stdout.readline())


def test_stop_process_tree_kills_the_process_and_its_child():
    process, _child = start_parent_with_child()
    try:
        stop_process_tree(process)
        # Raises TimeoutExpired while the child still holds the pipe open.
        process.communicate(timeout=30)
    finally:
        stop_process_tree(process)
    assert process.returncode != 0


def test_killing_only_the_process_leaves_its_child():
    """The check of the test above sees a child that survives"""
    process, child = start_parent_with_child()
    try:
        process.kill()
        with pytest.raises(subprocess.TimeoutExpired):
            process.communicate(timeout=2)
    finally:
        # On Windows stop_process_tree no longer reaches the child of a
        # killed parent (see its docstring), so the child is ended by its pid.
        stop_process_tree(process)
        with contextlib.suppress(ProcessLookupError):
            os.kill(child, signal.SIGTERM)
        process.communicate(timeout=30)


def test_output_after_stop_gives_up_on_a_descendant_that_holds_the_pipe(
    monkeypatch,
):
    # Killing only the parent leaves the child with the pipe, as
    # stop_process_tree leaves a descendant that it does not reach.
    monkeypatch.setattr(grass.temporal.testing.session, "STOPPED_OUTPUT_SECONDS", 1)
    process = start_process_tree(
        [sys.executable, "-c", PARENT_WITH_CHILD], stdout=subprocess.PIPE, text=True
    )
    child = int(process.stdout.readline())
    try:
        process.kill()
        process.wait(timeout=30)
        start = time.monotonic()

        output = output_after_stop(process)

        # The child sleeps 120 s; without the limit the wait would last that long.
        assert time.monotonic() - start < 30
        assert output == ("", None)
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.kill(child, signal.SIGTERM)
        process.communicate(timeout=30)


def test_stop_process_tree_of_an_ended_process_is_no_error():
    process = start_process_tree([sys.executable, "-c", "pass"])
    process.wait(timeout=30)
    stop_process_tree(process)


def test_on_windows_the_tree_starts_as_a_process_group(monkeypatch):
    # The flag exists in subprocess on Windows only.
    monkeypatch.setattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    calls = []
    monkeypatch.setattr(
        subprocess, "Popen", lambda arguments, **options: calls.append(options)
    )
    start_process_tree(["tool"], creationflags=0x8, text=True)
    assert calls == [{"creationflags": 0x208, "text": True}]


def test_on_windows_taskkill_stops_the_tree(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    # Windows has no os.killpg to remove.
    monkeypatch.delattr(os, "killpg", raising=False)
    calls = []
    monkeypatch.setattr(
        subprocess, "run", lambda arguments, **options: calls.append(arguments)
    )

    class Process:
        pid = 4321

    stop_process_tree(Process())
    assert calls == [["taskkill", "/T", "/F", "/PID", "4321"]]


def test_find_program_finds_a_tool_with_a_dot_in_its_name(tmp_path):
    with project_session(tmp_path / "p") as session:
        path = find_program("g.region", session.env)
        assert os.path.basename(path).startswith("g.region")
        # The path is what subprocess can start on every platform.
        result = subprocess.run(
            [path, "--interface-description"],
            env=session.env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert '<task name="g.region">' in result.stdout


def test_find_program_names_the_program_and_the_path():
    env = {"PATH": os.pathsep.join(["/no/such/dir", "/nor/this"])}
    with pytest.raises(FileNotFoundError) as error:
        find_program("t.missing", env)
    assert "t.missing" in str(error.value)
    assert env["PATH"] in str(error.value)


def test_find_program_without_path_searches_the_path_of_the_process(monkeypatch):
    folder = os.path.dirname(sys.executable)
    monkeypatch.setenv("PATH", folder)
    assert find_program(os.path.basename(sys.executable), {}) == sys.executable
    with pytest.raises(FileNotFoundError) as error:
        find_program("t.missing", {})
    assert f"PATH {folder}" in str(error.value)
