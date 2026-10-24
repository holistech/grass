"""The classic profile of the algebra core against the classic algebra, for vector maps

As t_rast_algebra_classic_profile_test.py, on the datasets of the vector
fixture; per map the name, the time stamps and the numbers of points, lines
and areas are compared, or the class of the error.
"""

import pytest

from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.expressions import RUNNERS, compare, outcome

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

EXPRESSIONS = [
    "aa & ab",
    "aa | ab",
    "aa ^ ab",
    "aa ~ ab",
    "aa + ab",
    "ac & ab",
    "wide {&,contains} aa",
    "wide {&,contains,r} aa",
    "wide {|,contains,r} aa",
    "wide {&,contains,u} aa",
    "wide {+,contains,i} aa",
    "aa {&,during} wide",
    "aa {&,during,r} wide",
    "aa {:,contains} wide",
    "aa {!:,during} wide",
    "aa {:,during,r} wide",
    "aa {:,during,i} wide",
    "wide {:,contains,u} aa",
    "aa : tmap(ev)",
    "aa {:,during} tmap(ev)",
    "buff_p(pa, 1)",
    "buff_p(pa, 6) & buff_a(aa, 20)",
    "buff_l(la, 2) & aa",
    "if(td(aa) == 1, aa)",
    "if({during}, td(wide) == 2, aa)",
    "if({during}, td(wide) == 2, aa, ab)",
    "if(aa {#,during} wide == 1, aa)",
    'buff_t(aa, "-1 day")',
    'buff_t(wide, "-1 day")',
    'tshift(aa, "1 day") & ab',
    "merge(aa, ab)",
    "merge(aa, aa)",
    "pc & pc",
    "aa {&,equal|overlap} ab",
    "pa & pb",
    "la & la",
    "(aa & ab) & pa",
    "aa & pb",
    "aa + ab & ac",
    "aa | ab & ac",
    "aa ~ aa",
    "tmap(ev) & aa",
    "wide {&,during|starts} aa",
]


def both(expression):
    """The outcomes of the reference and of the profile"""
    reference = reference_outcome("vector", expression)
    profile = outcome("vector", expression, RUNNERS["classic"], basename="fb")
    return reference, profile


@pytest.mark.parametrize("expression", EXPRESSIONS)
def test_profile_equals_reference(vector_series, expression):
    reference, profile = both(expression)
    assert compare("vector", expression, reference, profile) is None


def test_comparison_sees_a_different_result(vector_series):
    """Negative test: compare() reports two expressions that differ"""
    reference, _ = both("aa & ab")
    _, profile = both("aa | ab")
    assert compare("vector", "aa & ab", reference, profile) is not None
