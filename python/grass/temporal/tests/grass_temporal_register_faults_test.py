"""Test the warning for a known map when the start is the number 0

A relative start of 0 is a time like any other; it must not be taken for
"no start" and silence the warning that the time of a known map is kept.
"""

import pytest

import grass.temporal as tgis
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools


@pytest.mark.parametrize("start", [0, "0"])
def test_known_map_with_a_start_of_zero_warns(tmp_path, capfd, start):
    with temporal_session(tmp_path / "project") as session:
        tools = Tools(session=session, overwrite=True, quiet=True)
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        tools.r_mapcalc(expression="m = 1")
        for name in ("one", "two"):
            tgis.open_new_stds(name, "strds", "relative", "t", "d", "mean")
        tgis.register_maps_in_space_time_dataset(
            "raster", "one", maps="m", start="1", unit="days"
        )
        capfd.readouterr()

        tgis.register_maps_in_space_time_dataset(
            "raster", "two", maps="m", start=start, unit="days"
        )

        assert "already registered" in capfd.readouterr().err


def test_closing_the_interface_forgets_the_cached_database_versions(tmp_path):
    """A reconnected interface asks the database again, as t.upgrade may have run"""
    with temporal_session(tmp_path / "project"):
        dbif = tgis.SQLDatabaseInterfaceConnection()
        dbif.connect()
        tgis.RasterDataset(f"m@{tgis.get_current_mapset()}").select(dbif)
        assert dbif.__dict__["_semantic_label_columns"]
        dbif.close()
        assert "_semantic_label_columns" not in dbif.__dict__
        dbif.connect()
        assert "_semantic_label_columns" not in dbif.__dict__
        dbif.close()
