"""Test the choice of the GDAL type for integer maps and a nodata value

Without type, the tool chooses the smallest integer type that holds the map
and the nodata value. A nodata value that no integer type holds, such as nan,
needs a type of the user; the data are described in conftest.py (ex_a holds 10
in every cell). The tests are skipped without gdalinfo.
"""

import json
import shutil
import subprocess
import tarfile

import pytest

from grass.temporal.testing.readback import inventory, message
from grass.tools import ToolError

pytestmark = pytest.mark.skipif(
    shutil.which("gdalinfo") is None, reason="gdalinfo is not installed"
)

# Selects ex_a, the map of integer cells
INTEGER_MAP = "start_time < '2001-02-01'"


def _band(tmp_path, archive):
    with tarfile.open(archive) as tar:
        tar.extract("ex_a.tif", tmp_path / "x", filter="data")
    result = subprocess.run(
        ["gdalinfo", "-json", str(tmp_path / "x" / "ex_a.tif")],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)["bands"][0]


@pytest.mark.parametrize(
    ("options", "gdal_type", "nodata"),
    [
        # The smallest type that holds 10 and the nodata value
        ({"nodata": 300}, "UInt16", 300),
        ({"nodata": -77}, "Int16", -77),
        # A given type is not changed, also for nan
        ({"nodata": "nan", "type": "Float32"}, "Float32", "NaN"),
    ],
    ids=["300", "-77", "nan with type"],
)
def test_type_choice_with_nodata(tools, absolute, tmp_path, options, gdal_type, nodata):
    archive = tmp_path / "out"

    tools.t_rast_export(
        input=absolute,
        output=str(archive),
        compression="no",
        where=INTEGER_MAP,
        **options,
    )

    band = _band(tmp_path, archive)
    assert (band["type"], band["noDataValue"]) == (gdal_type, nodata)


def test_type_choice_with_nan_nodata(tools, absolute, tmp_path):
    """No integer type holds nan, so r.out.gdal gets no type and refuses it"""
    archive = tmp_path / "out"
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_export(
            input=absolute,
            output=str(archive),
            compression="no",
            where=INTEGER_MAP,
            nodata="nan",
        )

    assert "Unable to export raster map <ex_a@PERMANENT>" in message(error.value)
    assert not archive.exists()
    assert inventory(tools) == before
