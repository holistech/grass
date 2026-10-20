"""Test the options of t.rast.export that change the exported rasters

The data type, the creation options, the metadata and the nodata value of a
GTiff file are read back with gdalinfo (ex_c holds 7 and null cells, see
conftest.py). The tests are skipped without it.
"""

import json
import shutil
import subprocess
import tarfile

import pytest

from grass.temporal.testing.readback import message

pytestmark = pytest.mark.skipif(
    shutil.which("gdalinfo") is None, reason="gdalinfo is not installed"
)


def _gdalinfo(tmp_path, archive, member):
    with tarfile.open(archive) as tar:
        tar.extract(member, tmp_path / "x", filter="data")
    result = subprocess.run(
        ["gdalinfo", "-json", str(tmp_path / "x" / member)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _export(tools, absolute, tmp_path, **options):
    archive = tmp_path / "out"
    result = tools.t_rast_export(
        input=absolute, output=str(archive), compression="no", **options
    )
    return archive, result


def test_the_type_sets_the_data_type_of_the_bands(tools, absolute, tmp_path):
    archive, _ = _export(tools, absolute, tmp_path, type="Int16")

    for member in ("ex_a.tif", "ex_c.tif"):
        assert _gdalinfo(tmp_path, archive, member)["bands"][0]["type"] == "Int16"


def test_without_type_the_type_follows_the_map(tools, absolute, tmp_path):
    archive, _ = _export(tools, absolute, tmp_path)

    # ex_b holds 1.5 and 2.5, which need a float type; ex_a holds 10
    assert _gdalinfo(tmp_path, archive, "ex_b.tif")["bands"][0]["type"] == "Float64"
    assert _gdalinfo(tmp_path, archive, "ex_a.tif")["bands"][0]["type"] == "Byte"


def test_createopt_goes_to_the_driver(tools, absolute, tmp_path):
    archive, _ = _export(tools, absolute, tmp_path, createopt="COMPRESS=DEFLATE")

    info = _gdalinfo(tmp_path, archive, "ex_a.tif")
    assert info["metadata"]["IMAGE_STRUCTURE"]["COMPRESSION"] == "DEFLATE"


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_metaopt_is_written_as_metadata(tools, absolute, tmp_path):
    archive, _ = _export(tools, absolute, tmp_path, metaopt="TAG=hello")

    assert _gdalinfo(tmp_path, archive, "ex_a.tif")["metadata"][""]["TAG"] == "hello"


def test_nodata_is_written_to_the_bands(tools, absolute, tmp_path):
    archive, _ = _export(tools, absolute, tmp_path, type="Int16", nodata=-9)

    for member in ("ex_a.tif", "ex_c.tif"):
        assert _gdalinfo(tmp_path, archive, member)["bands"][0]["noDataValue"] == -9


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("fmt", ["pack", "AAIGrid"])
def test_type_is_skipped_for_the_other_formats_with_a_warning(
    tools, absolute, tmp_path, fmt
):
    _, result = _export(tools, absolute, tmp_path, format=fmt, type="Int16")

    assert "Type options is not working with pack format" in message(result)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("fmt", ["pack", "AAIGrid"])
def test_createopt_metaopt_and_nodata_are_skipped_with_a_warning(
    tools, absolute, tmp_path, fmt
):
    _, result = _export(
        tools, absolute, tmp_path, format=fmt, type="Int16", createopt="A=B"
    )

    assert "Createopt, metaopt and nodata options are not working" in " ".join(
        message(result).split()
    )


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("fmt", ["pack", "AAIGrid"])
def test_createopt_without_type_is_skipped_with_a_warning(
    tools, absolute, tmp_path, fmt
):
    _, result = _export(tools, absolute, tmp_path, format=fmt, createopt="A=B")

    assert "not working" in message(result)


# For an integer map without type= the tool takes the smallest unsigned type
# that holds the values and one more, which it writes as the nodata value; a
# map with negative values gets Int32 (python/grass/temporal/stds_export.py).
# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize(
    ("expression", "data_type", "nodata"),
    [
        ("0", "Byte", 1),
        ("254", "Byte", 255),
        ("255", "UInt16", 256),
        ("65534", "UInt16", 65535),
        ("65535", "UInt32", 65536),
        ("if(col() == 1, 0, 300)", "UInt16", 301),
        ("if(col() == 1, 0, 70000)", "UInt32", 70001),
        ("-1", "Int32", 0),
    ],
)
def test_the_type_of_an_integer_map_holds_its_values_and_a_nodata_value(
    tools, absolute, tmp_path, expression, data_type, nodata
):
    tools.r_mapcalc(expression=f"ex_int = {expression}", overwrite=True)
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output="ex_int_ds",
        title="t",
        description="d",
        overwrite=True,
    )
    tools.t_register(
        type="raster",
        input="ex_int_ds",
        maps="ex_int",
        start="2001-01-01",
        increment="1 months",
        overwrite=True,
    )

    archive, _ = _export(tools, "ex_int_ds", tmp_path)

    band = _gdalinfo(tmp_path, archive, "ex_int.tif")["bands"][0]
    assert band["type"] == data_type
    if data_type != "Int32":
        assert band["noDataValue"] == nodata
