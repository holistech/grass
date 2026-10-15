"""Test t.rast.mapcalc with where option.

This test verifies that the where parameter correctly filters:
a) maps in a single STRDS (no sampling case)
b) maps in all input STRDS when sampling is enabled

SPDX-FileCopyrightText: 2025 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

@author GRASS Development Team
"""

import pytest

from grass.temporal.testing.session import project_session
from grass.tools import Tools


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    """Pytest fixture to create a temporary GRASS project with raster maps.

    This setup initializes the GRASS environment in the mapset "perc", sets
    the computational region and creates the raster maps prec_1..prec_3 that
    the tests register in their own SpaceTimeRasterDataSets (STRDS).

    Yields:
        session: active GRASS session with the prepared project and rasters.

    """
    project = tmp_path_factory.mktemp("raster_mapcalc_where") / "project"
    with project_session(project, mapset="perc") as session:
        tools = Tools(session=session)
        tools.g_region(s=0, n=80, w=0, e=120, b=0, t=50, res=10, res3=10)

        for i in range(1, 4):
            mapname = f"prec_{i}"
            tools.r_mapcalc(expression=f"{mapname} = {i}00", overwrite=True)

        yield session


def test_single_strds_with_where(session):
    """Test where filter with single STRDS (no sampling)."""
    tools = Tools(session=session)

    # Create STRDS and register maps
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output="precip_where_single",
        title="Test where single",
        description="Test",
        overwrite=True,
    )
    tools.t_register(
        type="raster",
        input="precip_where_single",
        maps="prec_1,prec_2,prec_3",
        start="2001-01-01",
        increment="1 month",
        flags="i",
        overwrite=True,
    )

    # Run t.rast.mapcalc with where filter
    tools.t_rast_mapcalc(
        inputs="precip_where_single",
        output="precip_where_single_out",
        expression="precip_where_single * 2",
        basename="new_prec",
        where="start_time >= '2001-02-01'",
        overwrite=True,
    )

    # Verify that only 2 maps remain after filtering
    strds_info = tools.t_info(
        input="precip_where_single_out", type="strds", flags="g"
    ).keyval
    assert int(strds_info["number_of_maps"]) == 2, (
        f"Expected 2 maps after filtering, got {strds_info['number_of_maps']}"
    )


def test_multiple_strds_with_where_sampling(session):
    """Test where filter with multiple STRDS (sampling case).

    This verifies that the where filter applies to ALL input STRDS,
    including the sampler dataset.
    """
    tools = Tools(session=session)

    # Create two STRDS with identical temporal extents
    for strds_name in ["precip_where_a", "precip_where_b"]:
        tools.t_create(
            type="strds",
            temporaltype="absolute",
            output=strds_name,
            title=f"Test where {strds_name[-1]}",
            description="Test",
            overwrite=True,
        )
        tools.t_register(
            type="raster",
            input=strds_name,
            maps="prec_1,prec_2,prec_3",
            start="2001-01-01",
            increment="1 month",
            flags="i",
            overwrite=True,
        )

    # Run t.rast.mapcalc with where filter and sampling
    tools.t_rast_mapcalc(
        inputs="precip_where_a,precip_where_b",
        output="precip_where_multi_out",
        expression="precip_where_a + precip_where_b",
        basename="new_prec",
        method="equal",
        where="start_time >= '2001-02-01'",
        overwrite=True,
    )

    # Verify that only 2 maps remain after filtering
    # This confirms where filter applies to all input STRDS
    strds_info = tools.t_info(
        input="precip_where_multi_out", type="strds", flags="g"
    ).keyval
    assert int(strds_info["number_of_maps"]) == 2, (
        f"Expected 2 maps after filtering all STRDS, got {strds_info['number_of_maps']}"
    )
