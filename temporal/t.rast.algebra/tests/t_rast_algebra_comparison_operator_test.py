"""A comparison of two datasets with a temporal relation, inside if()

The published algebra paper (section 3.2.1) writes the comparison of related
maps as an operator in braces, {>=, equal|contains, |, l}, and as the short
form A >= F. The condition of a map holds one comparison with every related
map, joined by the aggregation (& is and, | is or). The expected values are
derived by hand from the data. The new algebra reads the forms as well; where
it differs, the test says why. A has four monthly maps with the values 1.5,
2.5, 3.5 and 4.5, F the values 5, 6, 7 and 8 on the same months, G the values
10, 20 and 30 on February to April, and E three maps on 5 to 7 January with
the values 1.5, 2.5 and 3.5, all contained in the January map of A.
"""

import datetime

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.expressions import RUNNERS, compare, outcome
from grass.tools import Tools

KIND = "raster"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

MONTHS = [
    (datetime.datetime(2001, month, 1), datetime.datetime(2001, month + 1, 1))
    for month in range(1, 5)
]
DAYS = [
    (datetime.datetime(2001, 1, day), datetime.datetime(2001, 1, day + 1))
    for day in (5, 6, 7)
]

JAN = ["2001-01-01"]
FEB_TO_APR = ["2001-02-01", "2001-03-01", "2001-04-01"]
ALL = ["2001-01-01", "2001-02-01", "2001-03-01", "2001-04-01"]

# (expression, start dates of the result maps, values)
BRACES = [
    # a1 = 1.5 against e1, e2, e3 = 1.5, 2.5, 3.5
    # 1.5 < 1.5 is false: and is false
    ("if(A {<,contains,&} E, A, -1)", JAN, [-1]),
    # 1.5 < 2.5 is true: or is true
    ("if(A {<,contains,|} E, A, -1)", JAN, [1.5]),
    # the default aggregation is and: 1.5 >= 2.5 is false
    ("if(A {>=,contains} E, A, -1)", JAN, [-1]),
    # 1.5 <= 1.5, 2.5 and 3.5 is true
    ("if(A {<=,contains} E, A, -1)", JAN, [1.5]),
    # 1.5 == 1.5 is true
    ("if(A {==,contains,|} E, A, -1)", JAN, [1.5]),
    # 1.5 != 1.5 is false
    ("if(A {!=,contains,&} E, A, -1)", JAN, [-1]),
    # 2 a1 = 3: 3 >= 3.5 is false
    ("if(A * 2 {>=,contains,&} E, A, -1)", JAN, [-1]),
    # 3 >= 1.5 is true
    ("if(A * 2 {>=,contains,|} E, A, -1)", JAN, [1.5]),
    # the right reference gives a map for each partner with the whole
    # condition, 1.5 < 2.5 is true for or on all three: the values of E
    (
        "if(A {<,contains,|,r} E, E, 0)",
        ["2001-01-05", "2001-01-06", "2001-01-07"],
        [1.5, 2.5, 3.5],
    ),
    # 1.5 < 1.5 is false for and on all three
    (
        "if(A {<,contains,&,r} E, E, 0)",
        ["2001-01-05", "2001-01-06", "2001-01-07"],
        [0, 0, 0],
    ),
    # a < f is true on every month, so a >= f is false: the else part F
    ("if(A {>=,equals,l} F, A, F)", ALL, [5, 6, 7, 8]),
    # true, and 1.5 > 1 is true
    ("if(A {>=,contains,|} E && A > 1, A, 0)", JAN, [1.5]),
    # equal named twice relates a partner twice; a > f is false either way
    ("if(A {>,equal|equals} F, A, 0)", ALL, [0, 0, 0, 0]),
    # The union of a1 with e1, e2 and e3, which lie inside it, is January:
    # 1.5 >= 1.5 and 1.5 >= 2.5 is false
    ("if(A {>=,contains,&,u} E, A, 0)", JAN, [0]),
    # The disjoint union is January as well: 1.5 < 2.5 is true for or
    ("if(A {<,contains,|,d} E, 1, 0)", JAN, [1]),
    # the condition has the time of a1, which is equal to the map a1: 1.5 >= 1.5
    ("if({equal}, A {>=,contains,|} E, A, 0)", JAN, [1.5]),
]

# The short form is the operator with the relation equal, the aggregation and
# and the left reference
BARE = [
    # a >= f is false on every month
    ("if(A >= F, A, F)", ALL, [5, 6, 7, 8]),
    # g2, g3, g4 = 10, 20, 30 against f2, f3, f4 = 6, 7, 8: true
    ("if(G > F, G, 0)", FEB_TO_APR, [10, 20, 30]),
    # f1 has no partner and is dropped; 6 > 10, 7 > 20, 8 > 30 is false
    ("if(F > G, F, 0)", FEB_TO_APR, [0, 0, 0]),
    # a1 has no partner in G >= F; for February to April a > 1 and g >= f hold
    ("if(A > 1 && G >= F, A)", FEB_TO_APR, [2.5, 3.5, 4.5]),
]


@pytest.fixture(scope="module")
def comparisons(temporal_module_session):
    """The datasets A, F, G and E"""
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=3, s=0, e=3, w=0, res=1)

    def specs(prefix, values, times):
        return [
            MapSpec(f"{prefix}{number}", value, start, end)
            for number, (value, (start, end)) in enumerate(
                zip(values, times, strict=True), start=1
            )
        ]

    create_stds(tools, "strds", "A", specs("a", [1.5, 2.5, 3.5, 4.5], MONTHS))
    create_stds(tools, "strds", "F", specs("f", [5, 6, 7, 8], MONTHS))
    create_stds(tools, "strds", "G", specs("g", [10, 20, 30], MONTHS[1:]))
    create_stds(tools, "strds", "E", specs("e", [1.5, 2.5, 3.5], DAYS))
    # Two maps with the time of January, which no time stamp tells apart
    create_stds(tools, "strds", "D", specs("d", [1, 2], [MONTHS[0], MONTHS[0]]))
    with fakes.cached_io(fakes.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(comparisons):
    """Replace the fixture of conftest.py: the caches run through comparisons"""


def run(runner, expression, basename, **options):
    return outcome(
        KIND,
        expression,
        RUNNERS[runner],
        basename=basename,
        register_null=True,
        **options,
    )


def starts_and_values(result):
    assert "error" not in result, result
    return (
        [row[1][:10] for row in result["maps"]],
        [pytest.approx(row[3], rel=1e-5) for row in result["maps"]],
    )


# The new algebra pairs the maps of the right reference one by one: every pair
# is compared on its own and takes the value of its own condition, where the
# classic algebra gives each partner the whole condition of the left map.
# {<,contains,|,r} and {<,contains,&,r}: 1.5 < 1.5 is false and 1.5 < 2.5 and
# 1.5 < 3.5 are true, so e1 gives the else part 0 and e2 and e3 their values
# 2.5 and 3.5, whatever the aggregation is.
PAIRS = (["2001-01-05", "2001-01-06", "2001-01-07"], [0, 2.5, 3.5])
CORE_PAIRS = {
    "if(A {<,contains,|,r} E, E, 0)": PAIRS,
    "if(A {<,contains,&,r} E, E, 0)": PAIRS,
}
# The bare comparison of the new algebra needs maps of equal time stamps
DIFFERENT_TIMES = ("if(G > F, G, 0)", "if(F > G, F, 0)", "if(A > 1 && G >= F, A)")


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "starts", "values"), BRACES + BARE)
def test_a_comparison_by_hand(comparisons, runner, expression, starts, values):
    result = run(runner, expression, "fa")
    if runner == "core":
        if expression in DIFFERENT_TIMES:
            pytest.skip("the bare comparison of maps of different times is an error")
        # A map of A without related map stays as a null map in the new algebra
        # and is left out in the classic algebra.
        result = dict(
            result, maps=[row for row in result["maps"] if row[3] is not None]
        )
        starts, values = CORE_PAIRS.get(expression, (starts, values))
    assert starts_and_values(result) == (starts, values)


@pytest.mark.parametrize("runner", ["reference", "classic"])
def test_a_condition_without_an_equal_map_is_empty(comparisons, runner):
    """The intersection of e1 and e2 is empty, the condition keeps 5 to 6 January

    No map of A has that time, so no map is left.
    """
    result = run(runner, "if(A {>=,contains,&,i} E, A, 0)", "fa")
    assert result["maps"] == []


@pytest.mark.parametrize(
    "expression",
    [row[0] for row in BRACES + BARE]
    + [
        "if(A {>=,contains,&,d} E, A, 0)",
        "if(A {<,contains,|,u} E, E, 0)",
        "if(E {<=,during} A, E, 0)",
        "if(E {<=,during,r} A, A, 0)",
        "if(A[1] >= A, A, 0)",
        "if(A >= A[-1] + 1, A, 0)",
        "if(A {<,contains,|} E {&&,equal} A > 1, A)",
    ],
)
def test_the_profile_computes_what_the_reference_computes(comparisons, expression):
    """Also the time stamps and names, which the tests above leave out"""
    reference = reference_outcome(KIND, expression, register_null=True)
    profile = run("classic", expression, "fb")
    assert compare(KIND, expression, reference, profile) is None
    assert "error" not in reference


def test_a_condition_without_an_equal_map_leaves_null_maps_in_the_new_algebra(
    comparisons,
):
    """The same expression gives a null map for each map of A in the new
    algebra, where the classic algebra leaves them out"""
    result = run("core", "if(A {>=,contains,&,i} E, A, 0)", "fa")
    assert [row[3] for row in result["maps"]] == [None, None, None, None]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("aggregate", "value"), [("|", 1.5), ("&", 0)])
def test_maps_of_equal_time_are_all_related(comparisons, runner, aggregate, value):
    """d1 = 1 and d2 = 2 both have the time of a1 = 1.5, and both are compared

    1.5 >= 1 or 1.5 >= 2 is true: 1.5; 1.5 >= 1 and 1.5 >= 2 is false: 0.
    The other maps of A have no related map (null maps in the new algebra).
    """
    result = run(runner, f"if(A {{>=,equal,{aggregate}}} D, A, 0)", "fa")
    assert "error" not in result, result
    january = [row[3] for row in result["maps"] if row[1].startswith("2001-01")]
    assert january == [pytest.approx(value)]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_a_spatial_relation_in_the_operator(comparisons, runner):
    """With -s the relations of the operator are spatial too: equal maps lie
    on one region, so the result is that of {>=,equal,|}"""
    result = run(runner, "if(A {>=,equal|equivalent,|} F, A, F)", "fa", spatial=True)
    assert starts_and_values(result) == (ALL, [5, 6, 7, 8])


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_the_granularity_mode_reads_the_bare_form_only(comparisons, runner):
    """-g refuses every operator in braces; A >= F has one granularity"""
    bare = run(runner, "if(A >= F, A, F)", "fa", granularity=True)
    assert starts_and_values(bare) == (ALL, [5, 6, 7, 8])
    braces = run(runner, "if(A {>=,equal,l} F, A, F)", "fb", granularity=True)
    assert braces["error"] == "FatalError"


REFUSED = [
    "if(A {>=,nonsense} F, A, F)",
    "if(A {>=,equal,x} F, A, F)",
    "if(A {>=,equal,l} 1, A, F)",
]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize("expression", REFUSED)
def test_forms_that_are_no_comparisons_stay_refused(comparisons, runner, expression):
    assert run(runner, expression, "fa")["error"] == "SyntaxError"


@pytest.mark.parametrize("runner", ["reference", "classic"])
@pytest.mark.parametrize(
    "expression",
    ["A >= F", "if(A {>=} F, A, F)", "if(A # F > A, A, F)"],
)
def test_the_classic_grammar_reads_comparisons_inside_if_only(
    comparisons, runner, expression
):
    """The new algebra reads a comparison anywhere, as A + (A >= F), and the
    operator in braces without a comma, as {+} for the plus"""
    assert run(runner, expression, "fa")["error"] == "SyntaxError"


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_a_temporal_condition_keeps_its_meaning(comparisons, runner):
    """A # B > 1 compares a count with a number, not two datasets"""
    result = run(runner, "if(A {#,contains} E > 1, A, 0)", "fa")
    assert starts_and_values(result) == (JAN, [1.5])
