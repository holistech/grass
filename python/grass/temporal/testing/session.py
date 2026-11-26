"""Create and tear down the GRASS sessions that temporal tests run in

The helpers start every session from a copy of os.environ, as
doc/development/testing.md requires. Only temporal_session changes
os.environ, and it restores the environment completely on exit.

This module must not import pytest; fixtures belong in conftest.py files.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import contextlib
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import grass.script as gs
import grass.temporal as tgis
from grass.temporal.state import get_raise_on_error, set_raise_on_error
from grass.grassdb.create import create_mapset
from grass.pygrass.messages import get_msgr


def add_mapset(session, name):
    """Create the mapset name in the project of session, without switching"""
    env = session.env
    gisenv = gs.gisenv(env=env)
    create_mapset(Path(gisenv["GISDBASE"]) / gisenv["LOCATION_NAME"] / name)


@contextlib.contextmanager
def mapset_session(session, name):
    """Yield a second session in the mapset name of the project of session

    The mapset is created if it does not exist. The two sessions are
    independent and can be used at the same time, each with its own current
    mapset and region; the mapset search path of session is not changed, so
    a test that wants to see maps of name from session adds the mapset with
    g.mapsets. This is how a test makes data that belong to another mapset.
    """
    gisenv = gs.gisenv(env=session.env)
    path = Path(gisenv["GISDBASE"]) / gisenv["LOCATION_NAME"] / name
    if not path.exists():
        create_mapset(path)
    with gs.setup.init(path, env=os.environ.copy()) as other:
        yield other


@contextlib.contextmanager
def project_session(path, *, crs=None, mapset=None):
    """Create a project at path and yield a session in it

    The project is XY unless crs is given (anything gs.create_project takes).
    With mapset the session runs in that mapset, which is created. The
    session starts from a copy of os.environ, as doc/development/testing.md
    requires, so the process environment is not changed.
    """
    path = Path(path)
    gs.create_project(path, crs=crs)
    if mapset is None:
        mapset_path = path
    else:
        create_mapset(path / mapset)
        mapset_path = path / mapset
    with gs.setup.init(mapset_path, env=os.environ.copy()) as session:
        yield session


@contextlib.contextmanager
def temporal_session(path, *, crs=None, mapset=None):
    """Like project_session, with grass.temporal usable in this process

    grass.temporal reads the session from os.environ and cannot take an env,
    so the session environment is mirrored into os.environ, tgis.init() runs,
    and errors raise instead of exiting.

    On exit, also after an exception, os.environ, the module flag of
    grass.temporal and the error mode of the messenger are restored. The
    globals that init() binds (database connection, mapset) stay bound until
    the next init().
    """
    saved_environ = dict(os.environ)
    # get_msgr() returns one Messenger per process, and tgis.init() does not
    # change the error mode of an existing one. Later tests of the process
    # expect the exit mode, so the mode of an existing Messenger and the
    # module flag are saved here, before init() sets the flag itself, and
    # both are restored below.
    #
    # The Messenger is not created here. For the first session of a process
    # this avoids a fork warning: a Messenger created now has a dead server
    # by the time init() starts the RPC server thread (measured 2026-10-15
    # with a traced os.fork), and its restart forks a multi-threaded process.
    # Later sessions of a process can still warn, because init() stops the
    # messenger when the project changes and the restart comes after that
    # thread started. get_msgr offers no way to ask whether an instance
    # exists, so the cache in its default argument is read. Without an
    # earlier Messenger, "restore" means the exit mode, which is what the
    # first init() of a process creates.
    existing = get_msgr.__defaults__[0][0]
    saved_msgr_flag = existing.raise_on_error if existing else False
    saved_module_flag = get_raise_on_error()
    try:
        with project_session(path, crs=crs, mapset=mapset) as session:
            os.environ.update(session.env)
            tgis.init(raise_fatal_error=True)
            # Applies to the Messenger even if it was created before init().
            set_raise_on_error(True)
            yield session
    finally:
        set_raise_on_error(saved_module_flag)
        # init() creates the Messenger when none existed.
        get_msgr().set_raise_on_error(saved_msgr_flag)
        os.environ.clear()
        os.environ.update(saved_environ)


# The return code that a process stopped by stop_process_tree gets from the
# helpers that report it: on POSIX the one subprocess reports for SIGKILL.
# Windows has no SIGKILL; the number only has to be below 0, which tells a
# stopped process from one that ended by itself.
STOPPED_RETURNCODE = -getattr(signal, "SIGKILL", 9)


def find_program(name, env):
    """Return the path of the program name in the PATH of env

    On Windows, subprocess does not add .exe or .bat to a name that already
    has a dot in it, as every GRASS tool name has, so a tool has to be
    resolved before it is started; shutil.which tries the extensions of
    PATHEXT. An env without PATH is searched with the PATH of os.environ,
    as shutil.which does for no path, because subprocess also starts a
    program from the PATH of the test process then. Raises
    FileNotFoundError naming the program and the PATH searched when it is
    not found.
    """
    search = env.get("PATH")
    path = shutil.which(name, path=search)
    if path is None:
        searched = os.environ.get("PATH") if search is None else search
        msg = f"Program {name} not found in PATH {searched}"
        raise FileNotFoundError(msg)
    return path


def start_process_tree(arguments, **options):
    """Start a process that stop_process_tree can stop with its descendants

    options are passed on to subprocess.Popen. On POSIX the process leads a
    session and process group of its own; on Windows it starts a process
    group of its own.
    """
    if sys.platform == "win32":
        options["creationflags"] = (
            options.get("creationflags", 0) | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        options["start_new_session"] = True
    return subprocess.Popen(arguments, **options)


def stop_process_tree(process):
    """Kill a process of start_process_tree and every process it started

    Killing the process alone is not enough: a tool runs below the wrapper
    that subprocess knows, and a block of a manual starts tools below bash
    or Python. A tree that is gone already is no error.
    """
    if sys.platform == "win32":
        # Windows has no os.killpg; taskkill /T follows the parent process
        # ids down from the process.
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(process.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)


def run_with_timeout(session, arguments, seconds):
    """Run a tool with a time limit; None if it did not end in time

    Returns the return code and the messages. The tool name in arguments is
    looked up in the PATH of the session (find_program). At the limit, the
    tool and every process it started are killed (stop_process_tree).
    """
    arguments = [find_program(arguments[0], session.env), *arguments[1:]]
    process = start_process_tree(
        arguments,
        env=session.env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _, messages = process.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        stop_process_tree(process)
        process.communicate()
        return None
    return process.returncode, messages
