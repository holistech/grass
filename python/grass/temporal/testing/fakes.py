"""Test-only caches for two slow calls that always give the same answer in a test

Every Module() of pygrass starts the tool once for its --interface-description,
and every SQLDatabaseInterfaceConnection() starts t.connect once for the list
of temporal mapsets. A test series repeats both thousands of times with the
same answer. The context managers here memoise them for the duration of a
`with` block and put the original callables back on exit, also after an
exception. Nothing in the library itself is cached; the answers of a
real session may change at any time, and the keys below are only as good as
the tests that compare them with real IO
(grass_temporal_testing_fakes_test.py).

The module does not import pytest; the fixtures live in conftest.py files.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import contextlib
import os
from pathlib import Path
from types import SimpleNamespace

import grass.pygrass.modules.interface.module as pygrass_module
import grass.temporal as tgis
from grass.temporal import core, db, schema, state


def _gisrc_state():
    """Return (path, content) of the GISRC file of the process, or Nones

    The content is part of every key: g.mapset, g.gisenv and g.mapsets rewrite
    the file in place, so its path alone does not change.
    """
    path = os.environ.get("GISRC")
    if not path:
        return None, None
    try:
        return path, Path(path).read_text()
    except OSError:
        return path, None


def _gisrc_values(content):
    """Return the KEY: value lines of a GISRC content as a dict"""
    values = {}
    for line in (content or "").splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip()
    return values


def _file_state(path):
    """Return (mtime in ns, size) of a file, or None if it does not exist"""
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_mtime_ns, stat.st_size


def mapsets_key(mapsets):
    """Return the cache key of get_available_temporal_mapsets(mapsets)

    The answer depends on the mapsets argument, on the current mapset and the
    search path (GISRC, and the SEARCH_PATH file of the current mapset, which
    g.mapsets rewrites without touching GISRC), and on which mapsets have a
    temporal database. A subprocess such as t.create in another mapset can
    create one at any time, so the existing tgis/sqlite.db files of the
    project are part of the key; a PostgreSQL connection is not visible
    there and is not supported.
    """
    path, content = _gisrc_state()
    values = _gisrc_values(content)
    search_path = None
    databases = ()
    if {"GISDBASE", "LOCATION_NAME", "MAPSET"} <= values.keys():
        project = Path(values["GISDBASE"]) / values["LOCATION_NAME"]
        search_path = _file_state(project / values["MAPSET"] / "SEARCH_PATH")
        databases = tuple(
            sorted(p.parent.parent.name for p in project.glob("*/tgis/sqlite.db"))
        )
    return mapsets, path, content, search_path, databases


def interface_key(name):
    """Return the cache key of the --interface-description of a tool

    G_OPT_M_NPROCS and G_OPT_MEMORYMB take their defaults from the GISRC at
    description time, and pygrass passes every parameter including defaults
    to the run, so the GISRC content has to be part of the key (checked
    2026-10-15 in grass --tmp-project XY: g.gisenv set=NPROCS=3 changes the
    default of r.mapcalc from 0 to 3 and make_cmd() then passes nprocs=3).
    """
    path, content = _gisrc_state()
    return name, path, content


class _Stats(SimpleNamespace):
    """Hit and miss counters, so that a test can see that the cache was used"""


class CacheStorage:
    """The cached answers of both caches, so that they outlive one `with` block

    A fixture that installs the caches around each test creates one of these
    per test module and passes it to cached_io(); the answers of one test then
    serve the next, which is where the time is saved. Keys contain the GISRC
    content of a session, so a storage should not outlive the module whose
    projects it describes.
    """

    def __init__(self):
        self.mapsets = {}
        self.interface = {}


@contextlib.contextmanager
def _replaced(owner_names):
    """Install attributes on modules and put the originals back on exit

    owner_names is a list of (module, attribute name, replacement). The
    originals are restored in reverse order, also after an exception.
    """
    saved = []
    try:
        for owner, name, replacement in owner_names:
            saved.append((owner, name, getattr(owner, name)))
            setattr(owner, name, replacement)
        yield
    finally:
        for owner, name, original in reversed(saved):
            setattr(owner, name, original)


@contextlib.contextmanager
def mapsets_cache(key=mapsets_key, cache=None):
    """Memoise grass.temporal.db.get_available_temporal_mapsets

    Replaces the module attribute in grass.temporal.db, which is where the
    library calls it (SQLDatabaseInterfaceConnection and its add_mapset), and
    the re-exports in grass.temporal.core and, for the names that the package
    still exports (init), in grass.temporal. Only non-empty
    answers are cached: an empty one is what comes back before the first
    init() of a session. The
    cache is also emptied when create_temporal_database() or init() run
    through the module attributes; code that bound init at import time (as
    stds_import does) does not reach the wrapper, which is harmless because
    such a call changes the GISRC or creates a database file, and both are in
    the key.

    key is the function that maps the mapsets argument to a hashable key; it
    is a parameter only so that a test can show that a weaker key goes stale.
    Yields an object with the counters hits and misses.
    """
    real = db.get_available_temporal_mapsets
    stats = _Stats(hits=0, misses=0)
    cache = {} if cache is None else cache

    def cached(mapsets=None):
        cache_key = key(mapsets)
        if cache_key in cache:
            stats.hits += 1
            return dict(cache[cache_key])
        stats.misses += 1
        result = real(mapsets)
        if result:
            cache[cache_key] = dict(result)
        return result

    def clearing(function):
        def wrapper(*args, **kwargs):
            cache.clear()
            try:
                return function(*args, **kwargs)
            finally:
                cache.clear()

        wrapper.__name__ = function.__name__
        wrapper.__doc__ = function.__doc__
        return wrapper

    # grass.temporal.core re-exports the functions of db.py, schema.py and
    # state.py and the package only some of them; the pairs below keep every
    # re-export in step with its home.
    names = [(db, "get_available_temporal_mapsets", cached)]
    names.extend(
        (module, "get_available_temporal_mapsets", cached)
        for module in (core, tgis)
        if hasattr(module, "get_available_temporal_mapsets")
    )
    for name, home in (("create_temporal_database", schema), ("init", state)):
        wrapper = clearing(getattr(home, name))
        names.append((home, name, wrapper))
        names.extend(
            (module, name, wrapper)
            for module in (core, tgis)
            if getattr(module, name, None) is getattr(home, name)
        )
    with _replaced(names):
        yield stats


class _Finished:
    """What Module.__init__ needs of a finished Popen: communicate()"""

    def __init__(self, output, returncode=0):
        self.returncode = returncode
        self._output = output

    def communicate(self, *args, **kwargs):
        return self._output, None


@contextlib.contextmanager
def interface_cache(key=interface_key, cache=None):
    """Memoise the --interface-description call of pygrass Module

    The seam is the name Popen in grass.pygrass.modules.interface.module,
    which Module.__init__ uses for exactly one command line,
    [tool, "--interface-description"], and later for the real run
    (Module.run). Only the first is answered from the cache; every other call
    goes to the real Popen. Only a successful, non-empty description is cached.

    key maps the tool name to a hashable key; it is a parameter only so that
    a test can show that a weaker key goes stale. cache is the dict that holds
    the answers, a fresh one by default. Yields an object with the counters
    hits and misses.
    """
    real = pygrass_module.Popen
    stats = _Stats(hits=0, misses=0)
    cache = {} if cache is None else cache

    def popen(args, *other, **kwargs):
        if (
            isinstance(args, (list, tuple))
            and len(args) == 2
            and args[1] == "--interface-description"
        ):
            cache_key = key(args[0])
            if cache_key in cache:
                stats.hits += 1
                return _Finished(cache[cache_key])
            stats.misses += 1
            process = real(args, *other, **kwargs)
            output = process.communicate()[0]
            if process.returncode == 0 and output:
                cache[cache_key] = output
            return _Finished(output, process.returncode)
        return real(args, *other, **kwargs)

    with _replaced([(pygrass_module, "Popen", popen)]):
        yield stats


@contextlib.contextmanager
def cached_io(storage=None):
    """Apply both caches; yield (mapsets statistics, interface statistics)

    The conftest.py files of the library and of the algebra tools run every
    test with it through an autouse fixture. It replaces two IO calls that
    give the same answer all through a module: the list of mapsets with a
    temporal database (a t.connect run per database connection) and the
    --interface-description of a tool (a tool run per pygrass Module). The
    real IO stays in tests marked real_io (search path, discovery, session
    start and init) and in
    python/grass/temporal/tests/grass_temporal_testing_fakes_test.py, which
    compares every cached answer with the real one. A tool started as a
    subprocess is never affected by the caches, marked or not, because they
    live in the test process. Comparisons of two implementations (core
    against classic) run with real raster and database IO and get these two
    caches, which both sides receive alike. Fixtures of module scope are set
    up before the autouse fixture and therefore use the real IO.
    """
    storage = CacheStorage() if storage is None else storage
    with (
        mapsets_cache(cache=storage.mapsets) as mapsets,
        interface_cache(cache=storage.interface) as interface,
    ):
        yield mapsets, interface
