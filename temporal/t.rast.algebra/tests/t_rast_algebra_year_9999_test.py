"""A date step beyond the year 9999 ends t.rast.algebra with a message

datetime holds no date after 9999-12-31. A step in days past it used to raise
OverflowError, which neither the core nor the reference implementation
(grass.temporal.classic) catches, so the tool ended with a traceback. The step
now raises ValueError, as the step in months does, and the tool reports it as
an error of the input.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.reference import run_reference
from grass.tools import ToolError, Tools

EXPRESSIONS = [
    'buff_t(E, "365 days")',
    'buff_t(E, "-365 days")',
    'tshift(E, "365 days")',
]


@pytest.fixture(scope="module")
def end_of_time(temporal_module_session):
    """Dataset E with one map from 9999-06-01 to 9999-12-01"""
    tools = Tools(session=temporal_module_session)
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    create_stds(
        tools,
        "strds",
        "E",
        [MapSpec("e1", 1, datetime(9999, 6, 1), datetime(9999, 12, 1))],
    )
    return temporal_module_session


# The tool runs on the algebra that GRASS_TEMPORAL_ALGEBRA names: the core
# without the variable, the classic profile with "classic".
@pytest.mark.parametrize("expression", EXPRESSIONS)
def test_a_step_of_days_beyond_9999_ends_with_a_message(end_of_time, expression):
    tools = Tools(session=end_of_time, overwrite=True)
    with pytest.raises(ToolError) as error:
        tools.t_rast_algebra(expression=f"R = {expression}", basename="r")

    assert "Traceback" not in error.value.stderr
    assert "beyond the year 9999" in " ".join(error.value.stderr.split())
    assert tools.t_list(type="strds").stdout.count("R@") == 0


@pytest.mark.fixed_algebra
@pytest.mark.parametrize("expression", EXPRESSIONS)
def test_the_earlier_implementation_raises_a_value_error(end_of_time, expression):
    # The reference passes the library error on: ValueError, which outcome() of
    # the expression fuzzer reports as "Other:ValueError".
    with pytest.raises(ValueError, match="beyond the year 9999"):
        run_reference(
            "raster", f"R = {expression}", basename="r", overwrite=True, run=True
        )
