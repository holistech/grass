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
from grass.tools import ToolError

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

    # The warning names the format the user chose, not always pack.
    assert f"type option is not used with the {fmt} format" in message(result)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_createopt_metaopt_and_nodata_are_skipped_with_a_warning(
    tools, absolute, tmp_path
):
    _, result = _export(
        tools, absolute, tmp_path, format="pack", type="Int16", createopt="A=B"
    )

    assert "Createopt, metaopt and nodata options are not working" in " ".join(
        message(result).split()
    )


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_createopt_without_type_is_skipped_with_a_warning(tools, absolute, tmp_path):
    _, result = _export(tools, absolute, tmp_path, format="pack", createopt="A=B")

    assert "not working" in message(result)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("options", [{}, {"type": "Int16"}])
def test_aaigrid_applies_nodata_without_a_warning(tools, absolute, tmp_path, options):
    # AAIGrid is written by r.out.gdal, which gets nodata= like GTiff does; the
    # AAIGrid driver writes it as NODATA_value in the header and in the null
    # cells. ex_c is null in columns 1 and 2 and 7 in column 3 of both rows.
    archive, result = _export(
        tools, absolute, tmp_path, format="AAIGrid", nodata=200, **options
    )

    assert "Createopt, metaopt and nodata options" not in " ".join(
        message(result).split()
    )
    with tarfile.open(archive) as tar:
        lines = tar.extractfile("ex_c.asc").read().decode().splitlines()
    assert "NODATA_value 200" in [" ".join(line.split()) for line in lines]
    assert [line.split() for line in lines[-2:]] == [["200", "200", "7"]] * 2


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


def _register_map_with_null(
    tools, name="ex_nd", expression="if(col() == 3, 5, null())"
):
    """Register a map of expression, by default 5 in column 3 and NULL elsewhere"""
    tools.r_mapcalc(expression=f"{name} = {expression}", overwrite=True)
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output=f"{name}_ds",
        title="t",
        description="d",
        overwrite=True,
    )
    tools.t_register(
        type="raster",
        input=f"{name}_ds",
        maps=name,
        start="2001-01-01",
        increment="1 months",
        overwrite=True,
    )
    return f"{name}_ds"


def test_a_nodata_value_outside_byte_gives_the_smallest_type_that_holds_it(
    tools, absolute, tmp_path
):
    dataset = _register_map_with_null(tools)

    archive, _ = _export(tools, dataset, tmp_path, nodata=-77)

    # The values are 5 and NULL. Byte (0 to 255) and UInt16 (0 to 65535)
    # cannot hold -77, Int16 (-32768 to 32767) can and is the smallest signed
    # type.
    band = _gdalinfo(tmp_path, archive, "ex_nd.tif")["bands"][0]
    assert band["type"] == "Int16"
    assert band["noDataValue"] == -77
    # The NULL cells stay NULL when the file is read back: 2 rows with one
    # value in column 3 give 2 valid and 4 NULL cells.
    tools.r_in_gdal(
        input=str(tmp_path / "x" / "ex_nd.tif"), output="ex_nd_back", flags="o"
    )
    stats = tools.r_univar(map="ex_nd_back", format="json")
    assert stats["n"] == 2
    assert stats["null_cells"] == 4


def test_a_nodata_value_inside_byte_gives_byte(tools, absolute, tmp_path):
    dataset = _register_map_with_null(tools)

    archive, _ = _export(tools, dataset, tmp_path, nodata=200)

    # 5 and 200 are in 0 to 255.
    band = _gdalinfo(tmp_path, archive, "ex_nd.tif")["bands"][0]
    assert band["type"] == "Byte"
    assert band["noDataValue"] == 200


def test_a_map_without_a_valid_cell_takes_its_type_from_nodata(
    tools, absolute, tmp_path
):
    dataset = _register_map_with_null(tools, "ex_nd", expression="null()")

    archive, _ = _export(tools, dataset, tmp_path, nodata=-77)

    # The map has no minimum and maximum; -77 alone needs a signed type, the
    # smallest is Int16.
    band = _gdalinfo(tmp_path, archive, "ex_nd.tif")["bands"][0]
    assert band["type"] == "Int16"
    assert band["noDataValue"] == -77


@pytest.mark.parametrize("fmt", ["GTiff", "AAIGrid"])
def test_a_nodata_value_no_integer_type_holds_stops_with_a_message(
    tools, absolute, tmp_path, fmt
):
    dataset = _register_map_with_null(tools)

    # The parser takes nan as a double. No integer type holds it, so the
    # choice is left to r.out.gdal, which refuses it for the type it picks.
    with pytest.raises(ToolError) as error:
        _export(tools, dataset, tmp_path, format=fmt, nodata="nan")

    assert "Unable to export raster map <ex_nd@PERMANENT>" in message(error.value)
    assert "Traceback" not in message(error.value)


def test_aaigrid_with_a_nodata_value_outside_byte_succeeds(tools, absolute, tmp_path):
    dataset = _register_map_with_null(tools)

    archive, _ = _export(tools, dataset, tmp_path, format="AAIGrid", nodata=-77)

    # NULL in the columns 1 and 2 and 5 in column 3 of both rows.
    with tarfile.open(archive) as tar:
        lines = tar.extractfile("ex_nd.asc").read().decode().splitlines()
    assert "NODATA_value -77" in [" ".join(line.split()) for line in lines]
    assert [line.split() for line in lines[-2:]] == [["-77", "-77", "5"]] * 2


def test_aaigrid_warns_only_about_metaopt(tools, absolute, tmp_path):
    _, result = _export(
        tools,
        absolute,
        tmp_path,
        format="AAIGrid",
        metaopt="TAG=x",
        createopt="DECIMAL_PRECISION=3",
        nodata=200,
    )

    # r.out.gdal writes metaopt to ex_*.asc.aux.xml, which the archive does not
    # hold; nodata and createopt reach the .asc file and are not mentioned
    # (r.out.gdal's own messages are in the text too, so only the tool's
    # phrases are counted).
    text = message(result)
    assert "metaopt option is not used with the AAIGrid format" in text
    assert text.count("option is not used") == 1
    assert "Createopt, metaopt and nodata" not in text


def test_aaigrid_without_metaopt_gives_no_warning(tools, absolute, tmp_path):
    _, result = _export(
        tools, absolute, tmp_path, format="AAIGrid", createopt="DECIMAL_PRECISION=3"
    )

    assert "option is not used" not in message(result)


def test_a_selection_without_maps_warns_and_keeps_the_archive(
    tools, absolute, tmp_path
):
    archive, result = _export(
        tools, absolute, tmp_path, where="start_time > '2020-01-01'"
    )

    with tarfile.open(archive) as tar:
        init = tar.extractfile("init.txt").read().decode().splitlines()
    assert "number_of_maps=0" in init
    assert "selection contains no map" in message(result)
