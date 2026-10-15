"""Test the empty-result warning of t.vect.algebra

The datasets are described in the vector_series fixture in conftest.py.
"""

import pytest

from grass.tools import Tools

pytestmark = pytest.mark.real_io


def run_tool(session, expression):
    """Run the tool and return its stderr"""
    tools = Tools(session=session, overwrite=True, consistent_return_value=True)
    return tools.t_vect_algebra(expression=expression, basename="warn").stderr


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
@pytest.mark.fixed_algebra
def test_the_modules_run_quietly(vector_series, expression, message):
    """The progress of the modules does not drown the warnings of the tool"""
    # The classic algebra runs g.copy without --quiet, so this holds for the
    # core only.
    env = {**vector_series.session.env, "GRASS_TEMPORAL_ALGEBRA": "core"}
    tools = Tools(env=env, overwrite=True, consistent_return_value=True)
    result = tools.t_vect_algebra(expression=expression, basename="warn")
    assert message not in result.stderr
