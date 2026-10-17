"""Comparison of the algebra core with the classic algebra for 3D rasters

Both algebras compute each expression; the registered maps (start, end,
minimum, maximum) must agree, except for the differences that the manual
lists between the core and the classic algebra.
"""

import itertools

import pytest

import grass.temporal as tgis
from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE
from grass.temporal.testing.reference import reference_parser, setup_granularity

SAME = [
    "A + B",
    "A - B - 1",
    "A * 2",
    "A / B",
    "A % 3",
    "abs(A - 3)",
    "A {+,during} W",
    "W {+,contains} A",
    "W {+,contains,u} A",
    "A {:,during} W",
    "A !: Q",
    "A {#,during} W",
    "if(A > 2, A, B)",
    "if(A > 2, A)",
    "A {+,equal|overlap} B",
    "if(td(A) == 1, A)",
    "if(start_day(A) > 2, A, B)",
    'tshift(A, "1 day")',
    # Shrinks the two-day maps of W to one day, so each keeps an interval.
    'buff_t(W, "-12 hours")',
    "merge(A, D)",
    "A[1]",
    "A[-1]",
    "D[0,0,1]",
    "A + map(single)",
]

# Each changed rule with a short form of its item in the list of differences
# in the manual, and what the core gives: "maps" for registered maps, which
# may be none, or the name of the error. A crash of the core then does not
# pass for a difference.
DIFFERENT = {
    # Where a negative buffer leaves a map no time, the core stops with an
    # error. The classic algebra stores an instant when the end equals the
    # start, and keeps the old time stamp with an error message when the end
    # would precede it. Measured 2026-10-14 with t.rast.algebra -c only; the
    # 3D algebra takes the same classic code path, buff_t() calling
    # temporal_buffer() of the map dataset.
    'buff_t(W, "-1 day")': (
        "ValueError",
        "a negative buffer must leave every map some time (end == start)",
    ),
    'buff_t(A, "-1 day")': (
        "ValueError",
        "a negative buffer must leave every map some time (end < start)",
    ),
    "W {:,contains,r} A": (
        "maps",
        "a selection with r gives one map per related pair",
    ),
    "W {+,contains,r} A": (
        "maps",
        "an operator with r gives each pair its own value",
    ),
    "if({during}, A > 1, W, 0)": ("maps", "one result per conclusion map"),
    "if(A > 2, A, W)": (
        "ValueError",
        "then and else of a map condition need equal time stamps",
    ),
}

# The granularity mode (-g) samples each dataset with the common granularity
# of the expression before both algebras compute it.
GRANULARITY_SAME = [
    # W has maps of two days, so that each counts for two days of A.
    "A + W",
    "W * 2",
    "A : W",
    "if(W > 150, A, B)",
    "if(W > 150, A)",
    "A[1] + W",
    # Q starts at noon, so that the common granularity is shorter than a day.
    "A + Q",
    "A + map(single)",
]

GRANULARITY_DIFFERENT = {
    "if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)": (
        "maps",
        "&& binds stronger than ||",
    ),
}


counter = itertools.count()


def rows(name):
    """Start, end, minimum and maximum of each map of a space time dataset"""
    dataset = tgis.open_old_stds(name, "str3ds")
    result = []
    for map_ in dataset.get_registered_maps_as_objects(order="start_time") or []:
        map_.select()
        start, end = map_.get_absolute_time()
        result.append((start, end, map_.metadata.get_min(), map_.metadata.get_max()))
    return result


def outcome(monkeypatch, expression, algebra, granularity=False):
    """The registered maps, or the name of the error

    algebra is "core", "classic" (the profile) or "reference" (the earlier
    implementation of the classic algebra).
    """
    monkeypatch.setenv(ALGEBRA_VARIABLE, algebra)
    # Every run has its own result name: a result of an earlier expression
    # would otherwise stand in for the empty result of this one.
    name = f"diff_{algebra}_{next(counter)}"
    options = {"run": True, "debug": False, "register_null": True}
    if algebra == "reference":
        parser = reference_parser("raster3d", **options)
    else:
        parser = tgis.TemporalRaster3DAlgebraParser(**options)
    statement = f"{name} = {expression}"
    if granularity:
        setup_granularity(parser, "raster3d", statement)
    try:
        parser.parse(statement, name, True)
    except (SyntaxError, ValueError, TypeError, tgis.FatalError) as error:
        return type(error).__name__
    return rows(name)


@pytest.mark.parametrize("expression", SAME)
@pytest.mark.fixed_algebra
def test_same_result(series_3d, monkeypatch, expression):
    assert outcome(monkeypatch, expression, "core") == outcome(
        monkeypatch, expression, "classic"
    )


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
@pytest.mark.fixed_algebra
def test_listed_differences_still_differ(series_3d, monkeypatch, expression):
    """A listed difference that no longer differs must leave the list"""
    core = outcome(monkeypatch, expression, "core")
    assert core != outcome(monkeypatch, expression, "classic")
    assert ("maps" if isinstance(core, list) else core) == DIFFERENT[expression][0]


@pytest.mark.parametrize("expression", GRANULARITY_SAME)
@pytest.mark.fixed_algebra
def test_granularity_same_result(series_3d, monkeypatch, expression):
    assert outcome(monkeypatch, expression, "core", granularity=True) == outcome(
        monkeypatch, expression, "classic", granularity=True
    )


@pytest.mark.parametrize("expression", sorted(GRANULARITY_DIFFERENT))
@pytest.mark.fixed_algebra
def test_granularity_listed_differences_still_differ(
    series_3d, monkeypatch, expression
):
    """A listed difference that no longer differs must leave the list"""
    core = outcome(monkeypatch, expression, "core", granularity=True)
    assert core != outcome(monkeypatch, expression, "classic", granularity=True)
    assert ("maps" if isinstance(core, list) else core) == GRANULARITY_DIFFERENT[
        expression
    ][0]


@pytest.mark.parametrize("expression", [*SAME, *sorted(DIFFERENT)])
@pytest.mark.fixed_algebra
def test_profile_equals_reference(series_3d, monkeypatch, expression):
    """-c computes what the earlier implementation of the classic algebra
    computed, also where the core differs"""
    assert outcome(monkeypatch, expression, "classic") == outcome(
        monkeypatch, expression, "reference"
    )


@pytest.mark.parametrize(
    "expression", [*GRANULARITY_SAME, *sorted(GRANULARITY_DIFFERENT)]
)
@pytest.mark.fixed_algebra
def test_granularity_profile_equals_reference(series_3d, monkeypatch, expression):
    assert outcome(monkeypatch, expression, "classic", granularity=True) == outcome(
        monkeypatch, expression, "reference", granularity=True
    )
