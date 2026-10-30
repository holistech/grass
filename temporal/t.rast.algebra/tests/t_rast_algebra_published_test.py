"""The expressions of the paper that introduced the algebra, in a gold corpus

Gebbert, Leppelt and Pebesma (2019): A Topology Based Spatio-Temporal Map
Algebra for Big Data Analysis. Data 4(2), 86. The expressions are the printed
ones, with the names of the datasets replaced. The corpus checks that the
classic profile (what -c runs) computes what the reference implementation
(grass.temporal.classic) computes. The paper writes the relation equals; both
read it as another name of equal.

t_rast_algebra_paper_test.py checks the figures of the paper against their
printed results; this module compares the two implementations on the
expressions and pins three results computed by hand.

Every printed expression runs in the reference, the profile and the core. The
caption of one figure misspells precedes; that spelling is a syntax error in
all three and the only printed form that is refused.
"""

import datetime

import pytest

from grass.temporal.testing import io_cache
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.differential import (
    RUNNERS,
    compare,
    outcome,
    outcome_of_runner,
)
from grass.tools import Tools

KIND = "raster"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# (expression, options of the runners, data). The test ids name the section
# of the paper; the data are those of the fixture below. A name other than
# "paper" in the last field would name another fixture.
PUBLISHED = [
    pytest.param(
        "(NIR - RED) / (NIR + RED)", {}, "paper", id="section 4.1, Landsat NDVI"
    ),
    pytest.param(
        "(NIR {-,equal|equivalent,l} RED) {/,equal|equivalent,l} "
        "(NIR {+,equal|equivalent,l} RED)",
        {"spatial": True},
        "paper",
        id="section 4.2, Sentinel-2 NDVI",
    ),
    pytest.param(
        "(DM {+,contains,l} if(T >= 10.0, P, 0.0)) / "
        "(DM {+,contains,l} if(T >= 10.0, T / 10.0, 0.0))",
        {},
        "paper",
        id="section 4.3, hydrothermal coefficient",
    ),
    pytest.param(
        "(A {+,contains,l} E) {/,equals,l} (A {#,contains,l} E)",
        {},
        "paper",
        id="appendix A.1, hash operator with equals",
    ),
    pytest.param(
        "E {+,equals|during|equivalent,l} A",
        {},
        "paper",
        id="section 3.1.3, list of relations",
    ),
    pytest.param("E {:,during,l} A", {}, "paper", id="appendix C.1, selection"),
    pytest.param(
        "A !: B {:,contains,l} E", {}, "paper", id="appendix C.1, inverse selection"
    ),
    pytest.param("A {+,contains,l} E", {}, "paper", id="appendix C.2, contains"),
    pytest.param("E {+,during,l} A", {}, "paper", id="appendix C.2, during"),
    pytest.param(
        "A {+,follows|precedes,d} G", {}, "paper", id="appendix C.2, disjoint union"
    ),
    pytest.param("A {-,overlaps,i} B", {}, "paper", id="appendix C.2, intersection"),
    pytest.param("A {+,equals|equivalent,l} F", {}, "paper", id="appendix C.2, equals"),
    pytest.param(
        'buff_t(A, "1 month") {+,equals|overlaps|overlapped,u} buff_t(B, "1 month")',
        {},
        "paper",
        id="appendix C.3, temporal buffer with equals",
    ),
    pytest.param(
        "(H[-2] + H[-1] + H + H[1] + H[2]) / 5.0",
        {},
        "paper",
        id="appendix C.4, moving average",
    ),
    pytest.param("(A[-1] + A) / td(A)", {}, "paper", id="appendix C.4, gradient"),
    pytest.param(
        "if(A > 1 {&&,equals,&,l} F > 6, A)",
        {},
        "paper",
        id="section 3.2.1, logical operator with equals",
    ),
    pytest.param(
        "((NIR - RED) * (map(L) + 1)) / (NIR + RED + map(L))",
        {},
        "paper",
        id="appendix C.3, SAVI",
    ),
    pytest.param(
        "if(A > 1 {&&,contains,&,l} E > 1, A)",
        {},
        "paper",
        id="section 3.2.1, logical operator with contains",
    ),
]

MONTHS = [
    (datetime.datetime(2001, month, 1), datetime.datetime(2001, month + 1, 1))
    for month in range(1, 5)
]


def days(first, last):
    """Daily intervals from day first to day last of January 2001"""
    return [
        (
            datetime.datetime(2001, 1, day),
            datetime.datetime(2001, 1, day) + datetime.timedelta(days=1),
        )
        for day in range(first, last + 1)
    ]


def specs(names, values, times):
    return [
        MapSpec(name, value, start, end)
        for name, value, (start, end) in zip(names, values, times, strict=True)
    ]


@pytest.fixture(scope="module")
def paper(temporal_module_session):
    """Small datasets for the expressions of the paper

    The values are floating point numbers, because r.mapcalc divides whole
    numbers as whole numbers. A, F: four monthly maps; G: February to April;
    B: two maps of one month that start on the 15th; C: one map of two
    months; E: three days inside January; H: six days of January; NIR,
    RED: three days with equal time; DM: January and February; STRDS: four
    monthly maps, a dataset named like a function; T, P: one map per day of
    January and February 2001 (59 days); L: a map without time
    stamp.
    """
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    day_1 = datetime.datetime(2001, 1, 1)
    day = datetime.timedelta(days=1)
    create_stds(
        tools,
        "strds",
        "A",
        specs(["a1", "a2", "a3", "a4"], [1.5, 2.5, 3.5, 4.5], MONTHS),
    )
    create_stds(
        tools, "strds", "F", specs(["f1", "f2", "f3", "f4"], [5, 6, 7, 8], MONTHS)
    )
    create_stds(
        tools, "strds", "G", specs(["g1", "g2", "g3"], [10, 20, 30], MONTHS[1:])
    )
    create_stds(
        tools,
        "strds",
        "B",
        specs(
            ["b1", "b2"],
            [10, 20],
            [
                (datetime.datetime(2001, 1, 15), datetime.datetime(2001, 2, 15)),
                (datetime.datetime(2001, 2, 15), datetime.datetime(2001, 3, 15)),
            ],
        ),
    )
    create_stds(
        tools,
        "strds",
        "C",
        specs(["c1"], [100], [(MONTHS[0][0], MONTHS[1][1])]),
    )
    create_stds(
        tools, "strds", "E", specs(["e1", "e2", "e3"], [1.5, 2.5, 3.5], days(5, 7))
    )
    create_stds(
        tools,
        "strds",
        "NIR",
        specs(["nir1", "nir2", "nir3"], [8.5, 9.5, 10.5], days(1, 3)),
    )
    create_stds(
        tools,
        "strds",
        "RED",
        specs(["red1", "red2", "red3"], [2.5, 3.5, 4.5], days(1, 3)),
    )
    create_stds(
        tools,
        "strds",
        "H",
        specs(
            [f"h{number}" for number in range(1, 7)],
            [1.5, 2.5, 3.5, 4.5, 5.5, 6.5],
            days(10, 15),
        ),
    )
    create_stds(tools, "strds", "DM", specs(["dm1", "dm2"], [1, 2], MONTHS[:2]))
    create_stds(
        tools,
        "strds",
        "STRDS",
        specs(["s1", "s2", "s3", "s4"], [10, 20, 30, 40], MONTHS),
    )
    daily = [(day_1 + number * day, day_1 + (number + 1) * day) for number in range(59)]
    create_stds(
        tools,
        "strds",
        "T",
        specs(
            [f"t{number}" for number in range(59)], [n % 20 for n in range(59)], daily
        ),
    )
    create_stds(
        tools,
        "strds",
        "P",
        specs(
            [f"p{number}" for number in range(59)],
            [n % 7 + 1 for n in range(59)],
            daily,
        ),
    )
    tools.r_mapcalc(expression="L = 0.5")
    with io_cache.cached_io(io_cache.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(paper):
    """Replace the fixture of conftest.py: the caches run through paper"""


def run(runner, expression, basename, **options):
    return outcome_of_runner(KIND, expression, runner, basename, **options)


@pytest.mark.parametrize(("expression", "options", "data"), PUBLISHED)
def test_the_profile_computes_what_the_reference_computes(
    paper, expression, options, data
):
    assert data == "paper"
    reference = reference_outcome(KIND, expression, register_null=True, **options)
    profile = run("classic", expression, "fb", **options)
    assert compare(KIND, expression, reference, profile) is None
    # Two refusals would make the comparison vacuous.
    assert "error" not in reference
    assert reference["maps"]


@pytest.mark.parametrize(("expression", "options", "data"), PUBLISHED)
def test_the_core_computes_what_the_reference_computes(
    paper, expression, options, data
):
    """Every printed expression runs in the core and gives the maps of the
    reference

    One expression differs by the meaning of -n, which the runner sets: the
    core also registers a null map for each map of A that contains no map of E
    (a2 to a4), the reference registers only the map with partners. The map
    with partners is the same.
    """
    assert data == "paper"
    reference = reference_outcome(KIND, expression, register_null=True, **options)
    core = run("core", expression, "fc", **options)
    assert "error" not in core, core
    assert core["maps"]
    difference = compare(KIND, expression, reference, core)
    if difference is None:
        return
    assert "{&&,contains" in expression, difference
    kept = [row for row in core["maps"] if row[3] is not None]
    assert [row[1:] for row in kept] == [row[1:] for row in reference["maps"]]
    assert len(core["maps"]) - len(kept) == 3


@pytest.mark.parametrize("runner", ["reference", "classic"])
def test_equals_by_hand(paper, runner):
    """A and F have four monthly maps each, month for month the same time

    {+,equals,l}: a + f = 1.5 + 5, 2.5 + 6, 3.5 + 7, 4.5 + 8 = 6.5, 8.5,
    10.5, 12.5.
    equals|equal names the relation twice and relates the partner twice:
    a + f + f = 1.5 + 10, 2.5 + 12, 3.5 + 14, 4.5 + 16 = 11.5, 14.5, 17.5,
    20.5.
    """
    once = values(run(runner, "A {+,equals,l} F", "fa"))
    twice = values(run(runner, "A {+,equals|equal,l} F", "fb"))
    assert [row[2] for row in once] == [6.5, 8.5, 10.5, 12.5]
    assert [row[2] for row in twice] == [11.5, 14.5, 17.5, 20.5]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_a_spatial_relation_name_works_without_the_flag(paper, runner):
    """Appendix C.2 prints equals|equivalent without -s

    A and F have four monthly maps each, month for month the same time and
    the same region, so each pair is spatially equivalent:
    a + f = 1.5 + 5, 2.5 + 6, 3.5 + 7, 4.5 + 8 = 6.5, 8.5, 10.5, 12.5.
    The regions are equivalent, not a cover of one another, so the name cover
    relates no pair and no map results.
    """
    related = run(runner, "A {+,equal|equivalent,l} F", "fa")
    assert [row[2] for row in values(related)] == [6.5, 8.5, 10.5, 12.5]
    unrelated = run(runner, "A {+,equal|cover,l} F", "fb")
    assert "error" not in unrelated
    assert not unrelated["maps"]


@pytest.mark.parametrize("spatial", [False, True], ids=["", "-s"])
@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_a_spatial_relation_name_alone_is_refused(paper, runner, spatial):
    """A spatial name needs a temporal one beside it, as in equal|equivalent

    A related map is found by the temporal relations; with none written no map
    can relate. The reference used to give an empty result without a message
    for every data; all three now refuse the expression with the same error.
    """
    refused = run(runner, "A {+,equivalent,l} F", "fa", spatial=spatial)
    assert refused["error"] == "Other:ValueError"
    assert "needs a temporal one" in refused["msg"]


@pytest.mark.parametrize("register_null", [False, True], ids=["", "-n"])
@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        # a > 1 holds for 1.5, 2.5, 3.5 and 4.5; f > 6 holds for 7 and 8 only
        # (f is 5, 6, 7, 8), so the conjunction is false, false, true, true.
        # r.mapcalc gives 0 where an if without else is false, so the result
        # is 0, 0, 3.5, 4.5 in four maps.
        ("if(A > 1 && F > 6, A)", [0, 0, 3.5, 4.5]),
        # a > 9 is false everywhere: four maps of 0, which are no null maps
        # and so are registered even without -n.
        ("if(A > 9, A)", [0, 0, 0, 0]),
        # a1 contains e1, e2, e3 (1.5, 2.5, 3.5, all above 1) and a1 > 1, so
        # the conjunction holds for a1 (1.5); a2 to a4 contain no map of E.
        ("if(A > 1 {&&,contains,&,l} E > 1, A)", [1.5]),
    ],
)
def test_if_without_else_gives_zero(paper, runner, expression, expected, register_null):
    """An if without else is 0 where the condition is false, as in r.mapcalc

    The reference and the classic profile register these maps with and
    without -n. With -n the core also registers a null map for each map of A
    without a partner in E, which is what -n asks for (a left map without
    related map), not a property of the missing else.
    """
    result = outcome(
        KIND,
        expression,
        RUNNERS[runner],
        basename="fa",
        register_null=register_null,
    )
    assert "error" not in result
    found = [row[3] for row in result["maps"]]
    if runner == "core" and register_null and "contains" in expression:
        expected = [*expected, None, None, None]
    assert found == pytest.approx(expected)


@pytest.mark.parametrize("runner", ["reference", "classic"])
@pytest.mark.parametrize("name", ["EQUALS", "Equals", "EQUAL"])
def test_the_relation_names_stay_lower_case(paper, runner, name):
    assert run(runner, f"A {{+,{name},l}} F", "fa")["error"] == "SyntaxError"


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_a_dataset_may_be_named_like_a_capital_function(paper, runner):
    """STRDS is a function name only before an opening parenthesis

    The dataset STRDS has the values 10, 20, 30, 40 on the months of A (1.5,
    2.5, 3.5, 4.5).
    STRDS + 1 = 11, 21, 31, 41; A + STRDS = 11.5, 22.5, 33.5, 44.5.
    """
    plus_one = values(run(runner, "STRDS + 1", "fa"))
    assert [row[2] for row in plus_one] == [11, 21, 31, 41]
    sums = values(run(runner, "A + STRDS", "fb"))
    assert [row[2] for row in sums] == [11.5, 22.5, 33.5, 44.5]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_the_dataset_function_is_no_raster_operand(paper, runner):
    """STRDS(A) is the selection form of t.select, not an operand here"""
    assert run(runner, "STRDS(A) + 1", "fa")["error"] == "SyntaxError"


def test_the_spelling_preceedes_of_the_caption_is_refused(paper):
    """The caption of the paper misspells precedes; no version reads it"""
    expression = "A {+,follows|preceedes,d} G"
    for runner in ("reference", "classic", "core"):
        assert run(runner, expression, "fa")["error"] == "SyntaxError"


@pytest.mark.parametrize(
    "expression", ["if(A {>=,equals,l} F, A, F)", "if(A {>=,equal,l} F, A, F)"]
)
def test_the_long_form_of_a_comparison(paper, expression):
    """Section 3.2.1 prints {>=,equals,l} as the long form of >=

    a >= f is false on each month (1.5 < 5, 2.5 < 6, 3.5 < 7, 4.5 < 8), so
    the else part F is the result: 5, 6, 7 and 8.
    """
    for runner in ("reference", "classic", "core"):
        result = run(runner, expression, "fa")
        assert [row[3] for row in result["maps"]] == [5, 6, 7, 8]


def values(result):
    """The maps of an outcome as (start, end, value) with the dates only

    Every map of these data is constant, so its minimum is its value.
    """
    assert result["stds"], result
    assert all(low == high for *_, low, high in result["maps"]), result
    return [
        (start[:10], end[:10] if end else None, pytest.approx(low, rel=1e-5))
        for _name, start, end, low, _high in result["maps"]
    ]


@pytest.mark.parametrize("runner", ["reference", "classic"])
def test_landsat_ndvi_by_hand(paper, runner):
    """(NIR - RED) / (NIR + RED) of the maps of one day each

    day 1: (8.5 - 2.5) / (8.5 + 2.5) = 6 / 11
    day 2: (9.5 - 3.5) / (9.5 + 3.5) = 6 / 13
    day 3: (10.5 - 4.5) / (10.5 + 4.5) = 6 / 15
    """
    result = run(runner, "(NIR - RED) / (NIR + RED)", "fa")
    assert values(result) == [
        ("2001-01-01", "2001-01-02", 6 / 11),
        ("2001-01-02", "2001-01-03", 6 / 13),
        ("2001-01-03", "2001-01-04", 6 / 15),
    ]


@pytest.mark.parametrize("runner", ["reference", "classic"])
def test_hydrothermal_coefficient_by_hand(paper, runner):
    """The sum of P over the days with T >= 10 divided by the sum of T / 10

    DM adds its value once to numerator and denominator. Day number n (from
    0 on) has T = n % 20 and P = n % 7 + 1.

    January, DM = 1, days 0 to 30. T >= 10 on days 10 to 19 (T = 10 to 19)
    and day 30 (T = 10). P on days 10 to 19 is 4 5 6 7 1 2 3 4 5 6 (sum 43),
    on day 30 it is 3: numerator 1 + 46 = 47. The T of these days sum to
    145 + 10 = 155: denominator 1 + 15.5 = 16.5. 47 / 16.5.

    February, DM = 2, days 31 to 58. T >= 10 on days 31 to 39 (T = 11 to 19)
    and 50 to 58 (T = 10 to 18). P on days 31 to 39 is 4 5 6 7 1 2 3 4 5
    (sum 37), on days 50 to 58 it is 2 3 4 5 6 7 1 2 3 (sum 33): numerator
    2 + 70 = 72. The T sum to 135 + 126 = 261: denominator 2 + 26.1 = 28.1.
    72 / 28.1.
    """
    expression = (
        "(DM {+,contains,l} if(T >= 10.0, P, 0.0)) / "
        "(DM {+,contains,l} if(T >= 10.0, T / 10.0, 0.0))"
    )
    assert values(run(runner, expression, "fa")) == [
        ("2001-01-01", "2001-02-01", 47 / 16.5),
        ("2001-02-01", "2001-03-01", 72 / 28.1),
    ]


@pytest.mark.parametrize("runner", ["reference", "classic"])
def test_gradient_by_hand(paper, runner):
    """(A[-1] + A) / td(A) on the monthly maps 1.5, 2.5, 3.5 and 4.5

    The first map has no predecessor and gives no map. February has 28 days,
    March 31 and April 30 (2001 is no leap year):
    (1.5 + 2.5) / 28, (2.5 + 3.5) / 31, (3.5 + 4.5) / 30.
    """
    assert values(run(runner, "(A[-1] + A) / td(A)", "fa")) == [
        ("2001-02-01", "2001-03-01", 4 / 28),
        ("2001-03-01", "2001-04-01", 6 / 31),
        ("2001-04-01", "2001-05-01", 8 / 30),
    ]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_the_soil_adjusted_vegetation_index(paper, runner):
    """Appendix C.3, a number added to map(L)

    With L = 0.5 the numerator is (NIR - RED) * 1.5 = 6 * 1.5 = 9 on each day
    and the denominator NIR + RED + 0.5: 11.5, 13.5 and 15.5.
    """
    expression = "((NIR - RED) * (map(L) + 1)) / (NIR + RED + map(L))"
    assert values(run(runner, expression, "fa")) == [
        ("2001-01-01", "2001-01-02", 9 / 11.5),
        ("2001-01-02", "2001-01-03", 9 / 13.5),
        ("2001-01-03", "2001-01-04", 9 / 15.5),
    ]
