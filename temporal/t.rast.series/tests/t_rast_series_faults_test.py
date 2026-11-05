"""Test the warning of t.rast.series for a selection without maps"""

from grass.temporal.testing.readback import inventory, message


def test_empty_where_warns(tools, stats, prefix):
    """No map and no error, but a warning that names the dataset"""
    before = inventory(tools)
    result = tools.t_rast_series(
        input=stats,
        method="sum",
        output=f"{prefix}_o",
        where="start_time > '2010-01-01'",
    )
    assert result.returncode == 0
    assert (
        "WARNING: The where condition selects no map of space time raster "
        f"dataset <{stats}@PERMANENT>"
    ) in message(result)
    assert inventory(tools) == before


def test_dataset_without_maps_warns_that_it_is_empty(tools, prefix):
    """Without a where condition the warning says that the dataset is empty"""
    tools.t_create(
        output=f"{prefix}_empty", title="empty", description="no maps", quiet=True
    )
    before = inventory(tools)
    result = tools.t_rast_series(
        input=f"{prefix}_empty", method="sum", output=f"{prefix}_o"
    )
    assert result.returncode == 0
    assert (
        f"WARNING: Space time raster dataset <{prefix}_empty@PERMANENT> is empty"
        in message(result)
    )
    assert inventory(tools) == before
