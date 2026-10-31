"""Fixtures shared by the tests of the temporal tools

python/grass/temporal/tests is not below this directory, so the session
fixtures are defined in its conftest.py as well; the logic lives in
grass.temporal.testing.
A conftest.py in a tests directory that defines a fixture of the same name
takes precedence over the one here.
"""

import os
import re
import shlex
import shutil
import zlib
from types import SimpleNamespace
from typing import NamedTuple

import pytest

# pytest rewrites the assert statements of test modules and conftest.py only. The
# helpers of grass.temporal.testing compare with a plain assert, which on failure
# shows no values unless the package is registered before its first import.
pytest.register_assert_rewrite("grass.temporal.testing")
# The registration has to precede these imports, so they follow a statement.
from grass.temporal.testing import postgresql  # noqa: E402
from grass.temporal.testing.data import (  # noqa: E402
    TIME_FORMAT,
    MapSpec,
    create_daily_stds,
    create_stds,
    day,
)
from grass.temporal.testing.readback import map_info  # noqa: E402
from grass.temporal.testing.session import (  # noqa: E402
    mapset_session,
    project_session,
    temporal_session,
)
from grass.tools import Tools  # noqa: E402


@pytest.fixture(params=("core", "classic"))
def algebra_setting(request):
    """Name of the algebra a test runs on, "core" or "classic"

    Not autouse, so a directory chooses whether it runs on both algebras. One
    that does writes an autouse fixture which requests this one and sets the
    name in the session the tools use:
    `session.env[ALGEBRA_VARIABLE] = algebra_setting`, with ALGEBRA_VARIABLE
    from grass.temporal.algebra.parser.switch.
    """
    return request.param


@pytest.fixture(scope="module")
def temporal_module_session(tmp_path_factory):
    """Session in an XY project for a whole module, with grass.temporal usable

    The session environment is mirrored into os.environ for the module, see
    grass.temporal.testing.session.temporal_session. Each test module
    gets its own session, also when several directories run together.
    """
    with temporal_session(tmp_path_factory.mktemp("temporal") / "project") as session:
        yield session


@pytest.fixture(scope="module")
def xy_module_session(tmp_path_factory):
    """Session in an XY project for a whole module, without touching os.environ

    For tests that run tools only; pass env=session.env or Tools(session=...).
    Use temporal_module_session when the test calls grass.temporal itself.
    """
    with project_session(tmp_path_factory.mktemp("temporal") / "project") as session:
        yield session


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    """Tools in an XY project of its own for a whole module

    The 2D and the 3D region are one cell, so a constant map is cheap.
    Messages of a successful run are kept in result.stderr, because the
    warnings and the reports of the tools are part of their behaviour. A
    directory whose tests need another project defines its own tools.
    """
    with project_session(tmp_path_factory.mktemp("tools") / "project") as session:
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        tools.g_region(n=1, s=0, e=1, w=0, res=1, b=0, t=1, res3=1)
        yield tools


@pytest.fixture
def broken_tools(tools, tmp_path):
    """Function that gives Tools in which the named tools do not work

    broken_tools("r.series") returns Tools in the session of the tools
    fixture, with a stand-in for r.series in front of the real one in PATH
    that exits with 1 without a message; broken_tools("r.series", status=0)
    exits with 0 and makes nothing. It reaches the branches of a tool that
    calls another tool and has no way to make it fail or stay silent by its
    input. The stand-in hands --interface-description to the real tool,
    because pygrass asks for it before it runs a tool. With passing, a call
    that has this argument runs the real tool as well, for a tool that is
    called for other purposes before the call that is to fail, such as
    v.db.connect -g. With failing, it is the other way round: a call runs
    the real tool unless one of its arguments starts with failing, for a tool
    that is called several times with arguments that differ in a prefix, such
    as g.region with and without tbres=. passing and failing exclude each
    other. The stand-ins only exist for the Tools it returns.
    """

    def make(*names, status=1, passing=None, failing=None):
        if passing and failing:
            msg = "passing and failing exclude each other"
            raise ValueError(msg)
        search = tools._original_env["PATH"]  # noqa: SLF001
        for name in names:
            real = shlex.quote(shutil.which(name, path=search))
            run_real = ""
            final = f"exit {status}\n"
            if passing:
                run_real = (
                    f'for arg in "$@"; do\n'
                    f'[ "$arg" = {shlex.quote(passing)} ] && exec {real} "$@"\n'
                    f"done\n"
                )
            if failing:
                # Prefix match on each argument; a call without it runs the real
                # tool, so there is no exit after the loop.
                run_real = (
                    f'for arg in "$@"; do\n'
                    f'case "$arg" in {shlex.quote(failing)}*) exit {status} ;; esac\n'
                    f"done\n"
                )
                final = f'exec {real} "$@"\n'

            stand_in = tmp_path / name
            stand_in.write_text(
                f'#!/bin/sh\ncase "$1" in\n'
                f'--interface-description) exec {real} "$@" ;;\n'
                f"esac\n{run_real}{final}"
            )
            stand_in.chmod(0o755)
        # Tools has no public access to the environment it runs the tools in
        # (grass.tools of 21.10.2026); a session of its own would need the
        # project of the module again.
        env = dict(tools._original_env)  # noqa: SLF001
        env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
        return Tools(env=env, consistent_return_value=True, capture_stderr=True)

    return make


@pytest.fixture
def prefix(request):
    """A name prefix that is unique for the test within its module

    The tests of a module share the project of tools, so each names its maps
    and datasets with this prefix: the test name, shortened, and a checksum of
    the full name, which tells the parameters of a test apart.
    """
    node = re.sub(r"\W+", "_", request.node.name).strip("_").lower()
    return f"{node[:24]}_{zlib.crc32(request.node.name.encode()) % 100000}"


@pytest.fixture
def make_stds(tools, prefix):
    """Function that creates maps and datasets that hold all of them

    make(count) creates the maps <prefix>_1 to <prefix>_<count> of the kind
    that stds_type holds, where map n holds the value n and lasts one day
    from day n-1 to day n, and the datasets <prefix>_ds0, <prefix>_ds1, ...
    that each register all of them. Returns the map names and the dataset
    names.
    """

    def make(count, *, stds_type="strds", datasets=1):
        names = [f"{prefix}_ds{index}" for index in range(datasets)]
        maps = create_daily_stds(tools, stds_type, names, count, map_prefix=prefix)
        return maps, names

    return make


class Mapsets(NamedTuple):
    """Tools in the two mapsets of the two_mapsets fixture"""

    work: Tools
    other: Tools


@pytest.fixture(scope="module")
def two_mapsets(tmp_path_factory):
    """Tools in the mapsets "work" and "other" of one XY project

    Both run at the same time. "work" is the mapset the tool under test runs
    in, with "other" in its search path; make the maps and datasets that are
    to belong to another mapset with the "other" tools. Both have a region of
    one cell in 2D and 3D, and keep the messages of successful runs in
    result.stderr like the tools fixture.
    """
    project = tmp_path_factory.mktemp("two_mapsets") / "project"
    with (
        project_session(project, mapset="work") as work,
        mapset_session(work, "other") as other,
    ):
        tools = []
        for session in (work, other):
            tools.append(
                Tools(
                    session=session, consistent_return_value=True, capture_stderr=True
                )
            )
            tools[-1].g_region(n=1, s=0, e=1, w=0, res=1, b=0, t=1, res3=1)
        tools[0].g_mapsets(operation="add", mapset="other")
        yield Mapsets(*tools)


@pytest.fixture
def has_dataset(tools):
    """Function that tells whether a space time dataset of that name exists

    Looks in the mapsets of the search path of the tools fixture.
    """

    def check(name, stds_type="strds"):
        return name in tools.t_list(type=stds_type, columns="name").stdout.split()

    return check


@pytest.fixture
def registered(tools):
    """Function that tells for each map whether the temporal database holds it"""

    def check(maps, map_type="raster"):
        return [map_info(tools, map_type, name) is not None for name in maps]

    return check


@pytest.fixture
def existing(tools):
    """Function that tells for each map whether it exists in the mapset"""

    def check(maps, map_type="raster"):
        listed = set(tools.g_list(type=map_type).stdout.split())
        return [name in listed for name in maps]

    return check


# The granule G is day 10 to day 20 (counted from 2001-01-01). The map
# "anchor" on day 0 to day 1 starts the grid there, so a granularity of
# 10 days gives the granules [0,10), [10,20) and [20,30), and G is the second.
# Every other map has a value that is a power of two, so a sum tells which
# maps a sampling relation collected. The relation is that of the granule to
# the map: G equals e, contains c, lies inside d, and so on.
_SAMPLING_MAPS = [
    # name, start day, end day, value
    ("e", 10, 20, 1),  # equal
    ("c", 12, 18, 2),  # G contains c
    ("d", 5, 25, 4),  # G is during d
    ("o1", 15, 25, 8),  # G overlaps o1
    ("o2", 5, 15, 16),  # G is overlapped by o2
    ("s1", 10, 15, 32),  # same start, shorter: G is started by s1
    ("s2", 10, 25, 64),  # same start, longer: G starts s2
    ("f1", 15, 20, 128),  # same end, shorter: G is finished by f1
    ("f2", 5, 20, 256),  # same end, longer: G finishes f2
]

# GRASS files a map that starts or finishes together with the granule under
# "during" as well, and the inverse under "contains" (see
# topology.py), so "contains" collects c, s1 and f1
# (2 + 32 + 128) and "during" collects d, s2 and f2 (4 + 64 + 256).
_SAMPLING_SUMS = {
    "equal": 1,
    "contains": 2 + 32 + 128,
    "during": 4 + 64 + 256,
    "overlaps": 8,
    "overlapped": 16,
    "started": 32,
    "starts": 64,
    "finished": 128,
    "finishes": 256,
    "overlaps,overlapped": 8 + 16,
    "equal,contains": 1 + 2 + 32 + 128,
}


@pytest.fixture(scope="module")
def sampling_relations(tools):
    """A dataset and a sampler for one sampling relation at a time

    Returns the names of the dataset "sampling_relations" of ten maps (the
    maps of the comment above and the anchor), of the dataset
    "sampling_relations_sampler" of the three intervals [0,10), [10,20) and
    [20,30), the sum that each sampling value must give for the granule G,
    and the start of G as t.rast.list prints it.
    """
    maps = [MapSpec("rel_anchor", 1024, day(0), day(1))] + [
        MapSpec(f"rel_{name}", value, day(start), day(end))
        for name, start, end, value in _SAMPLING_MAPS
    ]
    create_stds(tools, "strds", "sampling_relations", maps)
    create_stds(
        tools,
        "strds",
        "sampling_relations_sampler",
        [MapSpec(f"rel_smp{k}", k, day(10 * k), day(10 * k + 10)) for k in range(3)],
    )
    return SimpleNamespace(
        dataset="sampling_relations",
        sampler="sampling_relations_sampler",
        sums=_SAMPLING_SUMS,
        start=day(10).strftime(TIME_FORMAT),
    )


@pytest.fixture
def postgresql_database():
    """Yield the connection string of a new, empty database on the test server

    Skips without GRASS_TEMPORAL_TEST_POSTGRESQL or when the server does not
    answer. The database is dropped after the test.
    """
    postgresql.server_or_skip()
    with postgresql.fresh_database("t") as dbstring:
        yield dbstring
