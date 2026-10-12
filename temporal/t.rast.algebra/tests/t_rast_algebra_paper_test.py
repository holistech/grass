"""The examples of the paper that introduced the algebra

Gebbert, Leppelt and Pebesma (2019): A Topology Based Spatio-Temporal Map
Algebra for Big Data Analysis. Data 4(2), 86. conftest.py rebuilds the
datasets of the figures with constant maps. The paper prints the relation
name equals, single quotes, and start_time compared with a date; no version
of the algebra reads these (checked 12 October 2026 with GRASS 8.4.2), so
the expressions use equal, double quotes and start_date.
"""

import pytest

from grass.temporal.temporal_raster_algebra import ALGEBRA_VARIABLE

A1 = "(A1A {+,contains,l} A1B) {/,equal,l} (A1A {#,contains,l} A1B)"


def daily(first, last, value):
    """Daily maps from day first to day last of January 2001"""
    return [
        (f"01-{day:02d}", f"01-{day + 1:02d}", value(day))
        for day in range(first, last + 1)
    ]


# name: (expression, spatial flag, maps as (start, end, value)); start and
# end are month and day, end is None for an instant. The values are those
# of the figures. Where the paper shows no result, they are those of GRASS
# 8.4.2; the hydrothermal coefficient and SAVI, which GRASS 8.4.2 cannot
# compute, are computed by hand.
EXAMPLES = {
    "figure A1": (
        A1,
        False,
        [("01-01", "01-03", 6), ("01-03", "01-05", 13), ("01-05", "01-07", 20),
         ("01-07", "01-11", 18)],
    ),
    "figure A2": (
        'if({equal}, start_date(A1A) >= "2001-01-03" {&&,contains,&,l} '
        f'start_date(A1B) <= "2001-01-09", {A1})',
        False,
        [("01-03", "01-05", 13), ("01-05", "01-07", 20)],
    ),
    # Else takes b5 and b6, whose condition is false, and b7 to b10, which
    # no condition is related to.
    "figure A3": (
        'if({equal|contains}, start_date(A3A) <= "2001-01-03", A3A, A1B)',
        False,
        [("01-01", "01-03", 10), ("01-03", "01-05", 20),
         *daily(5, 10, lambda day: day)],
    ),
    "figure A4": (
        "if({equal}, A4A >= 0 {&&,equal,&,l} A4A <= 1, null(), A4A - 1)",
        False,
        [("01-01", "01-03", -2), ("01-03", "01-05", None), ("01-05", "01-07", None),
         ("01-07", "01-11", 1)],
    ),
    "figure A5": (
        "A5A {+,contains,l} A5B",
        False,
        [("01-01", "01-06", 6), ("01-06", "01-11", 6)],
    ),
    "figure A6": ("A5B {+,during,l} A5A", False, daily(1, 10, lambda day: 2)),
    "figure A7": ("A7A {+,follows|precedes,d} A7B", False, [("01-01", "01-11", 3)]),
    # The caption writes overlaps, which relates no maps in this direction,
    # in no version of the algebra.
    "figure A8": ("A8A {-,overlapped,i} A8B", False, [("01-04", "01-06", 0)]),
    "figure A9": (
        "SA9A {+,equal|equivalent,l} SA9B",
        True,
        [("01-01", None, 2), ("01-01", None, 6), ("01-08", None, 4),
         ("01-08", None, 8)],
    ),
    "section 4.1, Landsat NDVI": (
        "(NIR - RED) / (NIR + RED)",
        False,
        [("01-01", "01-02", 0.6667), ("01-02", "01-03", 0.5), ("01-03", "01-04", 0.4)],
    ),
    "section 4.2, Sentinel-2 NDVI": (
        "(S2B08{-,equal|equivalent,l}S2B04) {/,equal|equivalent,l} "
        "(S2B08{+,equal|equivalent,l}S2B04)",
        True,
        [("01-01", None, 0.5), ("01-01", None, 0.6), ("01-08", None, 0.4),
         ("01-08", None, 0.8)],
    ),
    # The days with T >= 10 have P 2, 3, 5, 6, 8, 9 and T 15, 12, 20, 11,
    # 14, 16: 33 / 8.8 = 3.75.
    "section 4.3, hydrothermal coefficient": (
        "(D {+,contains,l} if(T >= 10.0, P, 0.0)) / "
        "(D {+,contains,l} if(T >= 10.0, T / 10.0, 0.0))",
        False,
        [("01-01", "01-11", 3.75)],
    ),
    "appendix C.1, selection": (
        "A1B {:,during,l} A1A",
        False,
        daily(1, 10, lambda day: day),
    ),
    "appendix C.1, inverse selection": (
        "A1A !: A3A {:,contains,l} A1B",
        False,
        [("01-07", "01-11", 40)],
    ),
    "appendix C.3, temporal buffer": (
        'buff_t(A1A, "1 month") {+,equal|overlaps|overlapped,u} '
        'buff_t(A5A, "1 month")',
        False,
        [("12-01", "02-11", 11), ("12-01", "02-11", 32), ("12-01", "02-11", 41),
         ("12-03", "02-11", 21)],
    ),
    # (NIR - RED) * 1.5 / (NIR + RED + 0.5)
    "appendix C.3, SAVI": (
        "((NIR - RED) * (map(L) + 1)) / (NIR + RED + map(L))",
        False,
        [("01-01", "01-02", 0.5455), ("01-02", "01-03", 0.4615),
         ("01-03", "01-04", 0.4)],
    ),
    "appendix C.4, moving window": (
        "(A1B[-2] + A1B[-1] + A1B + A1B[1] + A1B[2]) / 5.0",
        False,
        daily(3, 8, lambda day: day),
    ),
    "appendix C.4, gradient": (
        "(A1B[-1] + A1B) / td(A1B)",
        False,
        daily(2, 10, lambda day: 2 * day - 1),
    ),
}  # fmt: skip

# Where the classic algebra differs from the paper (checked 12 October 2026).
CLASSIC = {
    # map(L) + 1 is a syntax error.
    "appendix C.3, SAVI": "SyntaxError",
}


def outcome(paper, monkeypatch, name, algebra):
    """The maps of an example as (start, end, value), or the error name"""
    expression, spatial, _maps = EXAMPLES[name]
    monkeypatch.setenv(ALGEBRA_VARIABLE, algebra)
    # A run with the spatial flag leaves the region at the extent of its maps.
    paper.tools.g_region(n=3, s=0, e=3, w=0, res=1)
    try:
        rows = paper.run(expression, spatial=spatial, register_null=True)
    except (*paper.errors, SyntaxError, ValueError, TypeError) as error:
        return type(error).__name__
    # The input maps are constant, so each result map must be as well.
    assert all(row.min == row.max for row in rows)
    return [
        (
            f"{row.start:%m-%d}",
            None if row.end is None else f"{row.end:%m-%d}",
            None if row.min is None else round(row.min, 4),
        )
        for row in rows
    ]


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_core_computes_the_published_maps(paper, monkeypatch, name):
    assert outcome(paper, monkeypatch, name, "core") == EXAMPLES[name][2]


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_classic_algebra_computes_the_published_maps(paper, monkeypatch, name):
    """Results published with the classic algebra stay reproducible"""
    expected = CLASSIC.get(name, EXAMPLES[name][2])
    assert outcome(paper, monkeypatch, name, "classic") == expected
