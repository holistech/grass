"""The reference implementation of t.select against the comparison helpers

The reference implementation (grass.temporal.classic) fails where a
selection would hold the value of a time function; the comparison of
grass.temporal.testing.differential accepts only that class of error against
the refusal of the core.
"""

import pytest

from grass.temporal.testing import differential

TIME_FUNCTION_SELECTED = "if(start_doy(A)<3,start_doy(A, 1), A)"


def selection_outcome(
    runner, basename, expression=TIME_FUNCTION_SELECTED, stdstype="strds"
):
    return differential.outcome(
        "select",
        expression,
        differential.RUNNERS[runner],
        basename=basename,
        stdstype=stdstype,
    )


def test_the_reference_fails_on_a_time_function_as_the_selected_maps(series):
    """The reference never computes the value of start_doy(A, 1) and fails
    when it copies that map into the result"""
    reference = selection_outcome("reference", "tfref")
    assert reference["error"] == "Other:CalledModuleError"
    assert "g.copy raster=tmp_map_name_" in reference["msg"]


@pytest.mark.parametrize(
    ("first", "second"),
    [
        # A failed copy of a map that is not a temporary one
        (
            {"error": "Other:CalledModuleError", "msg": "g.copy raster=a@x,b"},
            {
                "error": "Other:ValueError",
                "msg": "A time function such as start_doy()"
                " cannot be the result of a selection: more",
            },
        ),
        # Another ValueError of the core
        (
            {"error": "Other:CalledModuleError", "msg": "g.copy raster=tmp_map_name_1"},
            {"error": "Other:ValueError", "msg": "t.select selects maps"},
        ),
        # Another failing module of the reference
        (
            {"error": "Other:CalledModuleError", "msg": "r.mapcalc expression=a"},
            {
                "error": "Other:ValueError",
                "msg": "A time function such as start_doy()"
                " cannot be the result of a selection: more",
            },
        ),
    ],
)
def test_other_pairs_with_a_value_error_are_differences(first, second):
    """Only the class of the time function is accepted"""
    assert differential.accepted_error_pair("select", "A", first, second) is None
