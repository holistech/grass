"""Create and tear down the GRASS sessions that temporal tests run in

The helpers start every session from a copy of os.environ, as
doc/development/testing.md requires. Only temporal_session changes
os.environ, and it restores the environment completely on exit.

This module must not import pytest; fixtures belong in conftest.py files.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import contextlib
import os
from pathlib import Path

import grass.script as gs
import grass.temporal as tgis
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
    saved_module_flag = tgis.get_raise_on_error()
    try:
        with project_session(path, crs=crs, mapset=mapset) as session:
            os.environ.update(session.env)
            tgis.init(raise_fatal_error=True)
            # Applies to the Messenger even if it was created before init().
            tgis.set_raise_on_error(True)
            yield session
    finally:
        tgis.set_raise_on_error(saved_module_flag)
        # init() creates the Messenger when none existed.
        get_msgr().set_raise_on_error(saved_msgr_flag)
        os.environ.clear()
        os.environ.update(saved_environ)
