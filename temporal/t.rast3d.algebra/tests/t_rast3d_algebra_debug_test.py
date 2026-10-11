"""Test the debug output of the temporal 3D raster algebra parser

The datasets are described in the series_3d fixture in conftest.py.
"""

import pytest

import grass.temporal as tgis


def parse_with_debug(run):
    """Parse "dbg = (A + A) * 2" with debug=True and the given run"""
    parser = tgis.TemporalRaster3DAlgebraParser(run=run, debug=True, dry_run=True)
    parser.parse("dbg = (A + A) * 2", "dbg", True)


def test_debug_output_of_a_run(series_3d, capsys):
    """debug=True prints the r3.mapcalc commands and the resulting statement"""
    parse_with_debug(run=True)
    output = capsys.readouterr().out
    assert "((a1@PERMANENT + a1@PERMANENT) * 2)" in output
    assert "dbg = [" in output


def test_debug_output_without_run(series_3d, capsys):
    """With run=False debug=True prints the statement with the placeholder name"""
    parse_with_debug(run=False)
    assert "dbg = A**" in capsys.readouterr().out


@pytest.mark.parametrize("run", [True, False])
def test_no_debug_output_without_debug_flag(series_3d, capsys, run):
    """debug=False keeps the parser quiet"""
    parser = tgis.TemporalRaster3DAlgebraParser(run=run, debug=False, dry_run=True)
    parser.parse("dbg = (A + A) * 2", "dbg", True)
    assert capsys.readouterr().out == ""
