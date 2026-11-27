"""Test the 3D raster mask on the functions that read cells of the map

Rast3d_get_value_region() and Rast3d_get_block() take cell coordinates of
the map, so the mask applies at the centres of the cells of the map. The
tiles in the cache of a map open for reading hold the values of the file,
so these functions apply the mask to each value they read; for a map
without a cache, Rast3d_get_block() reads the tiles with Rast3d_read_tile(),
which masks them.
"""

import json
import os
import subprocess
import sys

import pytest

import grass.script as gs
from grass.tools import Tools

READ_SCRIPT = """\
import json
from ctypes import POINTER, byref, c_double, cast, sizeof

from grass.lib.gis import G_gisinit, G_mapset
from grass.lib.raster import DCELL_TYPE
from grass.lib.raster3d import (
    RASTER3D_DEFAULT_WINDOW,
    RASTER3D_NO_CACHE,
    RASTER3D_USE_CACHE_DEFAULT,
    RASTER3D_Map,
    Rast3d_close,
    Rast3d_get_block,
    Rast3d_get_value_region,
    Rast3d_init_defaults,
    Rast3d_is_null_value_num,
    Rast3d_mask_on,
    Rast3d_open_cell_old,
)

G_gisinit("test")
Rast3d_init_defaults()


def open_map(cache):
    handle = Rast3d_open_cell_old(
        "values", G_mapset(), RASTER3D_DEFAULT_WINDOW, DCELL_TYPE, cache
    )
    if not handle:
        raise SystemExit("Rast3d_open_cell_old failed")
    map_ptr = cast(handle, POINTER(RASTER3D_Map))
    Rast3d_mask_on(map_ptr)
    return map_ptr


def values(buffer):
    return [
        None
        if Rast3d_is_null_value_num(byref(buffer, i * sizeof(c_double)), DCELL_TYPE)
        else buffer[i]
        for i in range(len(buffer))
    ]


def block(map_ptr, read):
    buffer = (c_double * 2)()
    read(map_ptr, 0, 0, 0, 2, 1, 1, buffer, DCELL_TYPE)
    return values(buffer)


def value_region(map_ptr):
    buffer = (c_double * 2)()
    for x in range(2):
        Rast3d_get_value_region(
            map_ptr, x, 0, 0, byref(buffer, x * sizeof(c_double)), DCELL_TYPE
        )
    return values(buffer)


cached = open_map(RASTER3D_USE_CACHE_DEFAULT)
uncached = open_map(RASTER3D_NO_CACHE)
print(
    json.dumps(
        {
            "Rast3d_get_value_region": value_region(cached),
            "Rast3d_get_block": block(cached, Rast3d_get_block),
            "Rast3d_get_block without cache": block(uncached, Rast3d_get_block),
        }
    )
)
Rast3d_close(cached)
Rast3d_close(uncached)
"""


@pytest.fixture
def session(tmp_path):
    """Active session in an XY project (scope: function)"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        yield session


def test_cells_of_the_map_are_masked_at_their_centres(session, tmp_path):
    # A map of one row of two cells, 1 in x 0-1 and 2 in x 1-2, and a mask
    # from a map of the same resolution shifted west by 0.7, null in
    # x 0.3-1.3. The mask is null at the centre x 0.5 of the first cell of
    # the map and not at the centre x 1.5 of the second.
    with Tools(session=session) as tools:
        tools.g_region(s=0, n=1, w=-0.7, e=2.3, b=0, t=1, res=1, res3=1, tbres=1)
        tools.r3_mapcalc(expression="shifted = col()")
        tools.r3_mask(map="shifted", maskvalues=2)
        tools.g_region(s=0, n=1, w=0, e=2, b=0, t=1, res=1, res3=1, tbres=1)
        tools.r3_mapcalc(expression="values = col()")
    script = tmp_path / "read.py"
    script.write_text(READ_SCRIPT, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(script)],
        env=session.env,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )

    assert json.loads(result.stdout) == {
        "Rast3d_get_value_region": [None, 2.0],
        "Rast3d_get_block": [None, 2.0],
        "Rast3d_get_block without cache": [None, 2.0],
    }
