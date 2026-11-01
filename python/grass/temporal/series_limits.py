"""The open files r.series needs, counted before it runs

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import os
from pathlib import Path

from grass.script.utils import available_cpus, resolve_nprocs

# Files r.series holds besides the maps: the standard streams, the list of
# names and the output map. They were 6 with one thread and with 24 (measured
# 2026-10-31 in grass --tmp-project XY with r.series file=... method=sum over
# 21 maps of 2x2 cells: nprocs=1 ran at ulimit -n 48 and failed at 46,
# nprocs=24 ran at 1014 and failed at 1012); 64 leaves a margin.
SPARE_FILES = 64


def _gisrc_variables():
    """Return the variables of the file GISRC names, read as the C library does

    The file is read here and not through g.gisenv, because plan() needs no
    session. Like the C library, the first colon splits a line, an empty
    name or value is passed over and the last line wins.
    """
    gisrc = os.environ.get("GISRC")
    if not gisrc:
        return {}
    try:
        # The C library reads bytes; a value in another encoding must not
        # stop the plan, and the variables read here are ASCII.
        lines = Path(gisrc).read_text(errors="replace").splitlines()
    except OSError:
        return {}
    variables = {}
    for line in lines:
        name, colon, value = line.partition(":")
        name, value = name.strip(), value.strip()
        if colon and name and value:
            variables[name] = value
    return variables


def session_nprocs():
    """Return NPROCS of the session file as r.series reads it, else 0

    Without nprocs= r.series takes NPROCS of the file GISRC names (set with
    g.gisenv) as its default.
    """
    try:
        return int(_gisrc_variables().get("NPROCS", "0"))
    except ValueError:
        return 0


def series_threads(nprocs=None):
    """Return the number of threads r.series runs

    Without nprocs r.series is given no nprocs= and takes NPROCS of the
    session; a positive number is the count, a negative one is taken from
    the usable processors. 0 makes it ask OpenMP, which takes the first
    number of OMP_NUM_THREADS and otherwise one thread per usable processor.
    A passed nprocs is the value given to r.series as nprocs=: it counts as
    it stands, 0 asks OpenMP and NPROCS of the session is not looked at
    (measured 2026-10-31 by bisection at ulimit -n 1024 with NPROCS=4 in the
    session: 127 maps without nprocs, 21 with nprocs=0 on 24 processors, 63
    with nprocs=0 and OMP_NUM_THREADS=8). A GRASS without
    OpenMP, or a raster mask, runs one thread; counting more only switches
    to -z earlier than needed.
    """
    if nprocs is None:
        nprocs = session_nprocs()
    if nprocs != 0:
        return resolve_nprocs(nprocs)
    first = os.environ.get("OMP_NUM_THREADS", "").split(",")[0].strip()
    try:
        threads = int(first)
    except ValueError:
        threads = 0
    return threads if threads > 0 else available_cpus()


def series_map_limit(nprocs=None):
    """Return how many maps r.series can keep open in this process, or None

    r.series opens every map once per thread and needs two files per map
    and thread: with ulimit -n 1024 it ran with 509 maps on one thread, 127 on
    four and 21 on 24 and failed with one map more, for CELL, FCELL and
    DCELL maps alike (measured 2026-10-31 by bisection with r.series
    file=... method=sum nprocs=1, 4 and 24 over 2x2 maps in grass
    --tmp-project XY). The modules inherit the soft limit of this process.
    None means no limit, or a system without the resource module, where the
    maps stay open as before. nprocs is the one passed to r.series, see
    series_threads().
    """
    try:
        import resource  # noqa: PLC0415 - not on Windows
    except ImportError:
        return None
    soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft == resource.RLIM_INFINITY:
        return None
    return max(0, (soft - SPARE_FILES) // (2 * series_threads(nprocs)))


def exceeded_series_limit(count, *, file_limit=None, nprocs=None):
    """Return the limit that count maps exceed, or None if r.series may stay open

    The limits are file_limit, the number of maps a caller lets r.series
    keep open whatever the process allows, and series_map_limit(nprocs).
    The smaller of the two is returned when count is above either of them,
    which is when r.series must run with -z. A limit that is None does not
    count.
    """
    limits = [file_limit, series_map_limit(nprocs)]
    limits = [limit for limit in limits if limit is not None]
    if not limits or count <= min(limits):
        return None
    return min(limits)


def series_limit_warning(limit, count):
    """Return the warning that r.series runs with -z for count maps

    The text is that of t.rast.aggregate before the rule moved here, so its
    translations stay valid.
    """
    return _(
        "The limit of open files ({}) was reached ({}). The module r.series "
        "will be run with flag z, to avoid open files limit exceeding."
    ).format(limit, count)
