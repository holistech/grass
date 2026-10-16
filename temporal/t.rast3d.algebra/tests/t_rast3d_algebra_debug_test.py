"""Test the debug output of the temporal 3D raster algebra parser

The datasets are described in the series_3d fixture in conftest.py.
"""

import pytest

import grass.temporal as tgis
from grass.temporal.testing.reference import reference_parser


def parse_with_debug(run, classic):
    """Parse "dbg = (A + A) * 2" with debug=True and the given run"""
    parser = tgis.TemporalRaster3DAlgebraParser(
        run=run, debug=True, dry_run=True, classic=classic
    )
    parser.parse("dbg = (A + A) * 2", "dbg", True)


@pytest.mark.fixed_algebra
def test_debug_output_of_a_run(series_3d, capsys):
    """debug=True prints each planned module call as a command line"""
    parse_with_debug(run=True, classic=False)
    assert (
        'r3.mapcalc expression="dbg_0"=(("a1@PERMANENT" + "a1@PERMANENT") * 2)'
        in capsys.readouterr().out
    )


@pytest.mark.fixed_algebra
def test_debug_output_without_run(series_3d, capsys):
    """With run=False only the syntax is checked, so nothing is planned and
    debug=True prints nothing"""
    parse_with_debug(run=False, classic=False)
    assert not capsys.readouterr().out


@pytest.mark.fixed_algebra
def test_debug_output_of_the_classic_profile(series_3d, capsys):
    """-c prints each planned module call as a command line, with the
    r3.mapcalc text of the classic algebra, and with run=False nothing"""
    parse_with_debug(run=True, classic=True)
    assert (
        "r3.mapcalc expression=dbg_0=((a1@PERMANENT + a1@PERMANENT) * 2)"
        in capsys.readouterr().out
    )
    parse_with_debug(run=False, classic=True)
    assert not capsys.readouterr().out


@pytest.mark.fixed_algebra
def test_debug_output_of_the_reference(series_3d, capsys):
    """The earlier implementation prints the r3.mapcalc commands and the
    resulting statement, and without run the statement with the placeholder
    name. Only the reference keeps this output; the classic profile prints the
    module calls like the core."""
    for run in (True, False):
        parser = reference_parser("raster3d", run=run, debug=True, dry_run=True)
        parser.parse("dbg = (A + A) * 2", "dbg", True)
        output = capsys.readouterr().out
        if run:
            assert "((a1@PERMANENT + a1@PERMANENT) * 2)" in output
            assert "dbg = [" in output
        else:
            assert "dbg = A**" in output


@pytest.mark.parametrize("run", [True, False])
def test_no_debug_output_without_debug_flag(series_3d, capsys, run):
    """debug=False keeps the parser quiet"""
    parser = tgis.TemporalRaster3DAlgebraParser(run=run, debug=False, dry_run=True)
    parser.parse("dbg = (A + A) * 2", "dbg", True)
    assert capsys.readouterr().out == ""
