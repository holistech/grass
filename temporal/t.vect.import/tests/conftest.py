"""Fixtures for t.vect.import tests.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import MapSpec, register_stds, vector_points
from grass.temporal.testing.session import project_session
from grass.tools import Tools

VECTOR_NAMES = ["soil_1", "soil_2", "soil_3"]

ARCHIVE_SPECS = [
    ("GML", "bzip2", "gml_bz2.tar.bz2"),
    ("GML", "gzip", "gml_gz.tar.gz"),
    ("GML", "no", "gml_nocomp.tar"),
    ("pack", "no", "pack_nocomp.tar"),
    ("pack", "gzip", "pack_gz.tar.gz"),
    ("pack", "bzip2", "pack_bz2.tar.bz2"),
]


@pytest.fixture(scope="module")
def stvds_session(tmp_path_factory):
    """GRASS session with a three-map absolute-time STVDS and pre-exported archives.

    Vector maps are created with v.random (-z, seeded) and registered in an
    absolute-time STVDS. Archives for GML- and pack-format are created
    with all available compressions: bzip2, gzip, and no compression.
    """
    tmp_path = tmp_path_factory.mktemp("t_vect_import")
    project = tmp_path / "test"
    archive_dir = tmp_path / "archives"
    archive_dir.mkdir()

    with project_session(project) as session:
        tools = Tools(session=session, overwrite=True)
        tools.g_region(s=0, n=80, w=0, e=120, b=0, t=50, res=10, res3=10)
        for i, name in enumerate(VECTOR_NAMES, start=1):
            tools.v_random(
                flags="z",
                output=name,
                n=100,
                zmin=0,
                zmax=100,
                column="height",
                seed=i,
            )

        register_file = tmp_path / "register.txt"
        register_file.write_text(
            "\n".join(VECTOR_NAMES) + "\n",
            encoding="utf-8",
        )
        tools.t_create(
            type="stvds",
            temporaltype="absolute",
            output="soil_abs1",
            title="A test",
            description="A test",
        )
        tools.t_register(
            flags="i",
            type="vector",
            input="soil_abs1",
            file=str(register_file),
            start="2001-01-01",
            increment="1 months",
        )

        archives = {}
        for fmt, compression, suffix in ARCHIVE_SPECS:
            archive = archive_dir / suffix
            tools.t_vect_export(
                format=fmt,
                input="soil_abs1",
                output=str(archive),
                compression=compression,
                directory=str(archive_dir),
            )
            archives[fmt, compression] = str(archive)

        yield SimpleNamespace(
            session=session,
            archives=archives,
            archive_dir=str(archive_dir),
        )


def _points(tools, name, k, *, layers=(1,)):
    """Two points (k, 1) and (k, 2); point i has value 10 k + i and name k_i"""
    vector_points(
        tools,
        name,
        [(k, 1), (k, 2)],
        attributes={"value": [10 * k + 1, 10 * k + 2], "name": [f"{k}_1", f"{k}_2"]},
        layers=layers,
    )


@pytest.fixture(scope="module")
def archives(tools, tmp_path_factory):
    """Uncompressed archives made by t.vect.export, as a dict of name to path

    "pair" holds the maps vi_1 (January 2001) and vi_2 (February 2001) in the
    formats GML and pack: archives["GML"] and archives["pack"]. Map vi_k has
    the points (k, 1) and (k, 2) with the columns value = 10 k + i and
    name = "k_i" for point i. "layer" (archives["layer GML"] and
    archives["layer pack"]) holds the map vi_3 with the points (3, 1) and
    (3, 2) in two layers, registered as vi_3:2 for January 2001; the value
    of layer 2 is that of layer 1 plus 100 (131 and 132). "relative" (GML and
    pack) holds vi_4 (years 1 to 2) and vi_5 (years 2 to 3) in the unit
    years.
    """
    base = tmp_path_factory.mktemp("vi_archives")
    _points(tools, "vi_1", 1)
    _points(tools, "vi_2", 2)
    register_stds(
        tools,
        "stvds",
        "vi_pair",
        [
            MapSpec("vi_1", None, datetime(2001, 1, 1), datetime(2001, 2, 1)),
            MapSpec("vi_2", None, datetime(2001, 2, 1), datetime(2001, 3, 1)),
        ],
    )
    _points(tools, "vi_3", 3, layers=(1, 2))
    tools.db_execute(sql="UPDATE vi_3_2 SET value = value + 100")
    register_stds(
        tools,
        "stvds",
        "vi_layer",
        [MapSpec("vi_3:2", None, datetime(2001, 1, 1), datetime(2001, 2, 1))],
    )
    _points(tools, "vi_4", 4)
    _points(tools, "vi_5", 5)
    register_stds(
        tools,
        "stvds",
        "vi_relative",
        [MapSpec("vi_4", None, 1, 2), MapSpec("vi_5", None, 2, 3)],
        temporaltype="relative",
        unit="years",
    )
    paths = {}
    for fmt in ("GML", "pack"):
        for label, dataset in (
            ("", "vi_pair"),
            ("layer ", "vi_layer"),
            ("relative ", "vi_relative"),
        ):
            path = base / f"{label.strip() or 'pair'}_{fmt}.tar"
            tools.t_vect_export(
                input=dataset, output=str(path), format=fmt, compression="no"
            )
            paths[f"{label}{fmt}"] = path
    return paths


@pytest.fixture
def other(tmp_path):
    """Tools in a new unprojected project, where the original names are free"""
    with project_session(tmp_path / "other") as session:
        yield Tools(session=session, consistent_return_value=True, capture_stderr=True)
