"""The expressions of the paper that introduced the algebra, with fixed values

Gebbert, Leppelt and Pebesma (2019): A Topology Based Spatio-Temporal Map
Algebra for Big Data Analysis. Data 4(2), 86. The expressions are the printed
ones, with the names of the datasets replaced; the data are those of the
fixture below. The paper writes the relation equals, which the algebra reads
as another name of equal.

Each expected map is derived by hand in the comment above it. The values
equal those the reference implementation of the releases before GRASS 8.6
computed, recorded from the reference implementation on 2026-11-11, with one
difference under -n that the case itself describes.

t_rast_algebra_paper_test.py checks the figures of the paper against their
printed results. The caption of one figure misspells precedes; that spelling
is a syntax error. The manual names the other misprints of the paper.
"""

import datetime

import pytest

import grass.temporal as tgis
from grass.temporal.algebra.parser import evaluate
from grass.temporal.testing import io_cache
from grass.temporal.testing.data import MapSpec, create_stds
from grass.tools import Tools

KIND = "raster"

# The tests call the algebra core directly, whatever GRASS_TEMPORAL_ALGEBRA
# says, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]


def months(*values, first=1):
    """Monthly maps of 2001 from month first on, as (start, end, value)"""
    return [
        (f"2001-{month:02d}-01", f"2001-{month + 1:02d}-01", value)
        for month, value in enumerate(values, first)
    ]


def january(first, *values):
    """Daily maps of January 2001 from day first on, as (start, end, value)"""
    return [
        (f"2001-01-{day:02d}", f"2001-01-{day + 1:02d}", value)
        for day, value in enumerate(values, first)
    ]


# (expression, options of the algebra, expected maps). The test ids name the
# section of the paper. A map is (start, end, value); the value None is a map
# without a valid cell, which -n registers.
PUBLISHED = [
    # (nir - red) / (nir + red) on the three days:
    # (8.5 - 2.5) / (8.5 + 2.5) = 6 / 11, (9.5 - 3.5) / (9.5 + 3.5) = 6 / 13,
    # (10.5 - 4.5) / (10.5 + 4.5) = 6 / 15.
    pytest.param(
        "(NIR - RED) / (NIR + RED)",
        {},
        january(1, 6 / 11, 6 / 13, 6 / 15),
        id="section 4.1, Landsat NDVI",
    ),
    # The maps of NIR and RED have equal times and extents, so the spatial
    # relation equivalent holds beside equal: the values of section 4.1.
    pytest.param(
        "(NIR {-,equal|equivalent,l} RED) {/,equal|equivalent,l} "
        "(NIR {+,equal|equivalent,l} RED)",
        {"spatial": True},
        january(1, 6 / 11, 6 / 13, 6 / 15),
        id="section 4.2, Sentinel-2 NDVI",
    ),
    # Day number n (from 0 on) has T = n % 20 and P = n % 7 + 1; DM adds its
    # value once to numerator and denominator.
    # January, DM = 1, days 0 to 30: T >= 10 on days 10 to 19 (T = 10 to 19)
    # and day 30 (T = 10). P is 4 5 6 7 1 2 3 4 5 6 (sum 43) and 3: numerator
    # 1 + 46 = 47; T sums to 145 + 10 = 155: denominator 1 + 15.5 = 16.5.
    # February, DM = 2, days 31 to 58: T >= 10 on days 31 to 39 (T = 11 to
    # 19) and 50 to 58 (T = 10 to 18). P is 4 5 6 7 1 2 3 4 5 (sum 37) and
    # 2 3 4 5 6 7 1 2 3 (sum 33): numerator 2 + 70 = 72; T sums to
    # 135 + 126 = 261: denominator 2 + 26.1 = 28.1.
    pytest.param(
        "(DM {+,contains,l} if(T >= 10.0, P, 0.0)) / "
        "(DM {+,contains,l} if(T >= 10.0, T / 10.0, 0.0))",
        {},
        months(47 / 16.5, 72 / 28.1),
        id="section 4.3, hydrothermal coefficient",
    ),
    # a1 contains e1, e2, e3: (1.5 + 1.5 + 2.5 + 3.5) / 3 = 3. a2 to a4
    # contain no map of E and give no map.
    pytest.param(
        "(A {+,contains,l} E) {/,equals,l} (A {#,contains,l} E)",
        {},
        months(3),
        id="appendix A.1, hash operator with equals",
    ),
    # e1 to e3 are during a1: 1.5 + 1.5, 2.5 + 1.5, 3.5 + 1.5.
    pytest.param(
        "E {+,equals|during|equivalent,l} A",
        {},
        january(5, 3, 4, 5),
        id="section 3.1.3, list of relations",
    ),
    # e1 to e3 are during a1 and are selected with their values.
    pytest.param(
        "E {:,during,l} A",
        {},
        january(5, 1.5, 2.5, 3.5),
        id="appendix C.1, selection",
    ),
    # From left to right: no map of A is equal to b1 or b2, so A !: B is A;
    # of its maps only a1 contains maps of E.
    pytest.param(
        "A !: B {:,contains,l} E",
        {},
        months(1.5),
        id="appendix C.1, inverse selection",
    ),
    # a1 contains e1 to e3: 1.5 + 1.5 + 2.5 + 3.5 = 9.
    pytest.param("A {+,contains,l} E", {}, months(9), id="appendix C.2, contains"),
    # As in section 3.1.3: 1.5 + 1.5, 2.5 + 1.5, 3.5 + 1.5.
    pytest.param(
        "E {+,during,l} A", {}, january(5, 3, 4, 5), id="appendix C.2, during"
    ),
    # G has g1 = 10, g2 = 20, g3 = 30 on February to April. a1 precedes g1:
    # January to March, 1.5 + 10. a2 precedes g2: February to April,
    # 2.5 + 20. a3 follows g1 and precedes g3: February to May,
    # 3.5 + 10 + 30. a4 follows g2: March to May, 4.5 + 20.
    pytest.param(
        "A {+,follows|precedes,d} G",
        {},
        [
            ("2001-01-01", "2001-03-01", 11.5),
            ("2001-02-01", "2001-04-01", 22.5),
            ("2001-02-01", "2001-05-01", 43.5),
            ("2001-03-01", "2001-05-01", 24.5),
        ],
        id="appendix C.2, disjoint union",
    ),
    # b1 = 10 runs from January 15 to February 15, b2 = 20 from February 15
    # to March 15. a1 overlaps b1: January 15 to February 1, 1.5 - 10. a2
    # overlaps b2: February 15 to March 1, 2.5 - 20.
    pytest.param(
        "A {-,overlaps,i} B",
        {},
        [("2001-01-15", "2001-02-01", -8.5), ("2001-02-15", "2001-03-01", -17.5)],
        id="appendix C.2, intersection",
    ),
    # Month for month a + f: 1.5 + 5, 2.5 + 6, 3.5 + 7, 4.5 + 8.
    pytest.param(
        "A {+,equals|equivalent,l} F",
        {},
        months(6.5, 8.5, 10.5, 12.5),
        id="appendix C.2, equals",
    ),
    # The buffered maps: a1 December 1 to March 1, a2 January 1 to April 1,
    # a3 February 1 to May 1, a4 March 1 to June 1; b1 December 15 to March
    # 15, b2 January 15 to April 15. a1 overlaps b1 and b2; a2 is overlapped
    # by b1 and overlaps b2; a3 and a4 are overlapped by b1 and b2. Each map
    # of A is the union with both maps of B: 1.5 + 30, 2.5 + 30, 3.5 + 30,
    # 4.5 + 30.
    pytest.param(
        'buff_t(A, "1 month") {+,equals|overlaps|overlapped,u} buff_t(B, "1 month")',
        {},
        [
            ("2000-12-01", "2001-04-15", 31.5),
            ("2000-12-15", "2001-04-15", 32.5),
            ("2000-12-15", "2001-05-01", 33.5),
            ("2000-12-15", "2001-06-01", 34.5),
        ],
        id="appendix C.3, temporal buffer with equals",
    ),
    # H has 1.5 to 6.5 on January 10 to 15; only h3 and h4 have two
    # neighbours on each side: (1.5 + 2.5 + 3.5 + 4.5 + 5.5) / 5 and
    # (2.5 + 3.5 + 4.5 + 5.5 + 6.5) / 5.
    pytest.param(
        "(H[-2] + H[-1] + H + H[1] + H[2]) / 5.0",
        {},
        january(12, 3.5, 4.5),
        id="appendix C.4, moving average",
    ),
    # The first map has no predecessor and gives no map. February has 28
    # days, March 31 and April 30 (2001 is no leap year):
    # (1.5 + 2.5) / 28, (2.5 + 3.5) / 31, (3.5 + 4.5) / 30.
    pytest.param(
        "(A[-1] + A) / td(A)",
        {},
        months(4 / 28, 6 / 31, 8 / 30, first=2),
        id="appendix C.4, gradient",
    ),
    # a > 1 holds on each month, f > 6 for f = 7 and 8 only, so the
    # condition is false, false, true, true. r.mapcalc gives 0 where an if
    # without else is false: 0, 0, 3.5, 4.5.
    pytest.param(
        "if(A > 1 {&&,equals,&,l} F > 6, A)",
        {},
        months(0, 0, 3.5, 4.5),
        id="section 3.2.1, logical operator with equals",
    ),
    # With L = 0.5 the numerator is (nir - red) * 1.5 = 6 * 1.5 = 9 on each
    # day and the denominator nir + red + 0.5: 11.5, 13.5, 15.5.
    pytest.param(
        "((NIR - RED) * (map(L) + 1)) / (NIR + RED + map(L))",
        {},
        january(1, 9 / 11.5, 9 / 13.5, 9 / 15.5),
        id="appendix C.3, SAVI",
    ),
    # a1 contains e1 to e3, all above 1, and a1 > 1: the condition holds and
    # the result is a1 = 1.5. a2 to a4 contain no map of E. Under -n the core
    # registers a map without a valid cell for each of them, which -n asks
    # for (a left map without related map); the reference implementation
    # registered only the map of January. This is how the core behaves.
    pytest.param(
        "if(A > 1 {&&,contains,&,l} E > 1, A)",
        {},
        months(1.5, None, None, None),
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


def day_text(moment):
    """The date of a time stamp; every time of these data is at midnight"""
    assert moment.time() == datetime.time(), moment
    return f"{moment:%Y-%m-%d}"


def run(expression, basename="fc", **options):
    """Compute R = expression on the algebra core and return the maps of R

    Calls the core as t.rast.algebra does without -c, with -n unless
    register_null says otherwise. A map is (start, end, value) with the
    dates only; every map of these data is constant, so its minimum is its
    value, and None is a map without a valid cell.
    """
    result = tgis.SpaceTimeRasterDataset("R@PERMANENT")
    if result.is_in_db():
        result.delete()
    options = {"register_null": True, **options}
    evaluate(
        f"R = {expression}", kind=KIND, basename=basename, overwrite=True, **options
    )
    rows = []
    dataset = tgis.open_old_stds("R", "strds")
    for raster in dataset.get_registered_maps_as_objects(order="start_time") or []:
        raster.select()
        start, end = raster.get_temporal_extent_as_tuple()
        low, high = raster.metadata.get_min(), raster.metadata.get_max()
        assert low == high, raster.get_id()
        rows.append((day_text(start), None if end is None else day_text(end), low))
    return sorted(rows, key=lambda row: (row[0], row[1] or "", row[2] or 0))


def approximately(maps):
    """The expected maps with each value compared up to rounding"""
    return [
        (start, end, None if value is None else pytest.approx(value))
        for start, end, value in maps
    ]


@pytest.mark.parametrize(("expression", "options", "expected"), PUBLISHED)
def test_the_core_computes_what_the_reference_computes(
    paper, expression, options, expected
):
    """Every printed expression runs in the core and gives the expected maps"""
    assert run(expression, **options) == approximately(expected)


def test_a_spatial_relation_name_works_without_the_flag(paper):
    """Appendix C.2 prints equals|equivalent without -s

    A and F have four monthly maps each, month for month the same time and
    the same region, so each pair is spatially equivalent:
    a + f = 1.5 + 5, 2.5 + 6, 3.5 + 7, 4.5 + 8 = 6.5, 8.5, 10.5, 12.5.
    The regions are equivalent, not a cover of one another, so the name cover
    relates no pair and no map results.
    """
    related = run("A {+,equal|equivalent,l} F", "fa")
    assert related == approximately(months(6.5, 8.5, 10.5, 12.5))
    assert run("A {+,equal|cover,l} F", "fb") == []


@pytest.mark.parametrize("spatial", [False, True], ids=["", "-s"])
def test_a_spatial_relation_name_alone_is_refused(paper, spatial):
    """A spatial name needs a temporal one beside it, as in equal|equivalent

    A related map is found by the temporal relations; with none written no map
    can relate.
    """
    with pytest.raises(ValueError, match="needs a temporal one"):
        run("A {+,equivalent,l} F", "fa", spatial=spatial)


@pytest.mark.parametrize("register_null", [False, True], ids=["", "-n"])
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
def test_if_without_else_gives_zero(paper, expression, expected, register_null):
    """An if without else is 0 where the condition is false, as in r.mapcalc

    With -n the core also registers a null map for each map of A without a
    partner in E, which is what -n asks for (a left map without related map),
    not a property of the missing else.
    """
    found = [value for *_, value in run(expression, register_null=register_null)]
    if register_null and "contains" in expression:
        expected = [*expected, None, None, None]
    assert found == pytest.approx(expected)


def test_a_dataset_may_be_named_like_a_capital_function(paper):
    """STRDS is a function name only before an opening parenthesis

    The dataset STRDS has the values 10, 20, 30, 40 on the months of A (1.5,
    2.5, 3.5, 4.5).
    STRDS + 1 = 11, 21, 31, 41; A + STRDS = 11.5, 22.5, 33.5, 44.5.
    """
    assert run("STRDS + 1", "fa") == approximately(months(11, 21, 31, 41))
    assert run("A + STRDS", "fb") == approximately(months(11.5, 22.5, 33.5, 44.5))


def test_the_dataset_function_is_no_raster_operand(paper):
    """STRDS(A) is the selection form of t.select, not an operand here"""
    with pytest.raises(SyntaxError):
        run("STRDS(A) + 1", "fa")


def test_the_spelling_preceedes_of_the_caption_is_refused(paper):
    """The caption of the paper misspells precedes; no version reads it"""
    with pytest.raises(SyntaxError):
        run("A {+,follows|preceedes,d} G", "fa")


@pytest.mark.parametrize(
    "expression", ["if(A {>=,equals,l} F, A, F)", "if(A {>=,equal,l} F, A, F)"]
)
def test_the_long_form_of_a_comparison(paper, expression):
    """Section 3.2.1 prints {>=,equals,l} as the long form of >=

    a >= f is false on each month (1.5 < 5, 2.5 < 6, 3.5 < 7, 4.5 < 8), so
    the else part F is the result: 5, 6, 7 and 8.
    """
    assert run(expression, "fa") == approximately(months(5, 6, 7, 8))
