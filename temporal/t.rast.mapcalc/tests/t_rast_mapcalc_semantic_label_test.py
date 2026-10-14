"""Test t.rast.mapcalc with semantic labels in the names of the inputs.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os

import pytest

import grass.script as gs
from grass.tools import Tools


@pytest.fixture(scope="module")
def label_session(tmp_path_factory):
    """STRDS "test" with one S2_8 and one S2_4 map in each of two months."""
    tmp_path = tmp_path_factory.mktemp("t_rast_mapcalc_label")
    project = tmp_path / "test"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        tools = Tools(session=session, overwrite=True)
        tools.g_gisenv(set="TGIS_USE_CURRENT_MAPSET=1")
        tools.g_region(s=0, n=80, w=0, e=120, res=10)
        rows = []
        for name, value, label, start in [
            ("b8_1", 8, "S2_8", "2001-01-01"),
            ("b4_1", 4, "S2_4", "2001-01-01"),
            ("b8_2", 16, "S2_8", "2001-02-01"),
            ("b4_2", 2, "S2_4", "2001-02-01"),
        ]:
            tools.r_mapcalc(expression=f"{name} = {value}")
            tools.r_support(map=name, semantic_label=label)
            rows.append(f"{name}|{start}|{label}")
        maps_file = tmp_path / "maps.txt"
        maps_file.write_text("\n".join(rows) + "\n", encoding="utf-8")
        tools.t_create(
            type="strds",
            temporaltype="absolute",
            output="test",
            title="A test",
            description="A test",
        )
        tools.t_register(type="raster", input="test", file=str(maps_file))
        yield session


def test_inputs_with_semantic_labels(label_session):
    """The inputs of the manual example (test.S2_8 and test.S2_4) are found."""
    tools = Tools(session=label_session, overwrite=True)
    tools.t_rast_mapcalc(
        inputs="test.S2_8,test.S2_4",
        output="ratio",
        basename="ratio",
        expression="float(test.S2_8) / test.S2_4",
    )
    names = tools.t_rast_list(input="ratio", columns="name", flags="u").text.split()
    assert len(names) == 2
    values = sorted(
        float(tools.r_univar(map=name, flags="g").keyval["mean"]) for name in names
    )
    assert values == [2.0, 8.0]
