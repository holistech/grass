"""The relation name equals, which the published algebra paper writes

As t_rast_algebra_equals_alias_test.py, for the tool t.select on each dataset
type: the core and the classic profile (-c) read equals as another name of
equal, the reference refuses it. conftest.py describes the datasets; a2 and
b1 have the same time.
"""

import itertools

import pytest

from grass.temporal.testing.expressions import RUNNERS, outcome
from grass.tools import Tools

KINDS = {"strds": "t_rast_list", "stvds": "t_vect_list", "str3ds": "t_rast3d_list"}

SPELLINGS = [
    ("A {:,equals} B", "A {:,equal} B"),
    ("A {!:,equals} B", "A {!:,equal} B"),
    ("A {:,equals|contains} B", "A {:,equal|contains} B"),
]

result_counter = itertools.count(1)


def select(session, expression, kind):
    """Run t.select and return the rows (name, start, end) of its result"""
    result = f"alias{next(result_counter)}"
    tools = Tools(session=session, overwrite=True)
    tools.t_select(expression=f"{result} = {expression}", type=kind)
    listing = getattr(tools, KINDS[kind])(
        input=result, columns="name,start_time,end_time", format="json"
    )
    return sorted(
        (row["name"], row["start_time"], row["end_time"]) for row in listing["data"]
    )


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize(("equals", "equal"), SPELLINGS)
def test_equals_is_another_name_of_equal(series, kind, equals, equal):
    # The classic profile runs with -c, the core without it, see the fixture
    # algebra in conftest.py.
    canonical = select(series.session, equal, kind)
    assert select(series.session, equals, kind) == canonical
    # A refusal on both sides would make the comparison above vacuous.
    assert canonical


@pytest.mark.parametrize(("equals", "equal"), SPELLINGS)
def test_the_reference_refuses_equals(series, equals, equal):
    """A documented difference: the profile runs where the reference fails"""
    refused = outcome("select", equals, RUNNERS["reference"], basename="fa")
    accepted = outcome("select", equal, RUNNERS["reference"], basename="fb")
    assert refused["error"] == "SyntaxError"
    assert "error" not in accepted
