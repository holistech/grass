"""Comparison of the algebra core with the classic algebra for 3D rasters

Both algebras compute each expression; the registered maps (start, end,
minimum, maximum) must agree, except for the differences that the manual
lists between the core and the classic algebra.
"""

import itertools

import pytest

import grass.temporal as tgis
from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE

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
    "if(td(A) == 1, A)",
    "if(start_day(A) > 2, A, B)",
    'tshift(A, "1 day")',
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
    "if(A > 2, A)": (
        "maps",
        "an if without else is null where a map condition is false",
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
    "A {+,equal|overlap} B": (
        "ValueError",
        "a spatial relation needs the spatial flag",
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


def outcome(monkeypatch, expression, algebra):
    """The registered maps, or the name of the error"""
    monkeypatch.setenv(ALGEBRA_VARIABLE, algebra)
    # Every run has its own result name: a result of an earlier expression
    # would otherwise stand in for the empty result of this one.
    name = f"diff_{algebra}_{next(counter)}"
    parser = tgis.TemporalRaster3DAlgebraParser(
        run=True, debug=False, register_null=True
    )
    try:
        parser.parse(f"{name} = {expression}", name, True)
    except (SyntaxError, ValueError, TypeError, tgis.FatalError) as error:
        return type(error).__name__
    return rows(name)


@pytest.mark.parametrize("expression", SAME)
def test_same_result(series_3d, monkeypatch, expression):
    assert outcome(monkeypatch, expression, "core") == outcome(
        monkeypatch, expression, "classic"
    )


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_still_differ(series_3d, monkeypatch, expression):
    """A listed difference that no longer differs must leave the list"""
    core = outcome(monkeypatch, expression, "core")
    assert core != outcome(monkeypatch, expression, "classic")
    assert ("maps" if isinstance(core, list) else core) == DIFFERENT[expression][0]
