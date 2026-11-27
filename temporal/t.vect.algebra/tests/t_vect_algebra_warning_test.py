"""Test the empty-result warning of t.vect.algebra

The datasets are described in the vector_series fixture in conftest.py.
"""

import pytest

from grass.tools import Tools

pytestmark = pytest.mark.real_io


def run_tool(session, expression):
    """Run the tool and return its stderr

    The fixture keeps one session for all tests, which pytest-xdist may run in
    any order, so the maps take the name of the result as basename: with one
    basename for all, the run of a test after another one warned that it
    overwrote the maps of that test.
    """
    tools = Tools(session=session, overwrite=True, consistent_return_value=True)
    basename = expression.split("=")[0].strip()
    return tools.t_vect_algebra(expression=expression, basename=basename).stderr


def test_result_with_maps_gives_no_warning(vector_series):
    """A successful run is not reported as empty"""
    stderr = run_tool(vector_series.session, "warnfull = buff_p(pa, 1)")
    assert "WARNING" not in stderr


def test_empty_result_gives_a_warning(vector_series):
    """A run which creates no map says so"""
    stderr = run_tool(vector_series.session, "warnempty = aa {:,during} tmap(ev)")
    assert "result is empty" in stderr


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("warnoverlay = aa & ab", "v.overlay complete"),
        ('warncopy = tshift(aa, "1 day")', "Copying vector"),
        ("warnbuffer = buff_a(aa, 1)", "Buffering areas"),
    ],
)
def test_the_modules_run_quietly(vector_series, expression, message):
    """The progress of the modules does not drown the warnings of the tool"""
    stderr = run_tool(vector_series.session, expression)
    assert message not in stderr
