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
        f"WARNING: Space time raster dataset <{stats}@PERMANENT> is empty"
        in message(result)
    )
    assert inventory(tools) == before
