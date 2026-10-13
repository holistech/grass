"""Comparison of the algebra core with the classic algebra for vector maps

Both algebras compute each expression; the registered maps (identifier,
start, end and the numbers of points, lines, areas and centroids) must
agree, except for the differences that the manual lists between the core and
the classic algebra.
"""

import itertools

import pytest

import grass.temporal as tgis
from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE

SAME = [
    "aa & ab",
    "aa | ab",
    "aa ^ ab",
    "aa ~ ab",
    "aa + ab",
    "aa & ab | ac",
    "aa {&,equal} ab",
    "aa {|,during} wide",
    "wide {|,contains} aa",
    "aa : ab",
    "aa {:,during} wide",
    "aa !: wide",
    "buff_p(pa, 1)",
    "buff_l(la, 1)",
    "buff_a(aa, 1) & ab",
    "if(td(aa) == 1, aa)",
    "if(start_day(aa) > 1, aa, ab)",
    'tshift(aa, "1 day")',
    "merge(aa, ac)",
]

# Each changed rule with a short form of its item in the list of differences
# in the manual, and what the core gives: "maps" for registered maps, which
# may be none, or the name of the error. A crash of the core then does not
# pass for a difference.
DIFFERENT = {
    "aa {:,contains} wide": ("maps", "an empty result creates an empty dataset"),
    # wide1 contains aa1 and aa2, which do not overlap, so that the
    # intersection with both has no primitives. The classic algebra
    # registers that map empty.
    "wide {&,contains} aa": (
        "maps",
        "a vector map without primitives is not registered",
    ),
    "aa {#,during} wide": (
        "ValueError",
        "the core reads # in a vector expression and rejects a result without "
        "vector maps",
    ),
    # The classic vector grammar has no neighbour rule and reports a syntax
    # error.
    "aa[1]": ("maps", "the core reads A[1] and A[-1] also for vector datasets"),
    "aa[-1]": ("maps", "the core reads A[1] and A[-1] also for vector datasets"),
    "wide {:,contains,r} aa": (
        "maps",
        "a selection with r gives one map per related pair",
    ),
    "wide {&,contains,r} aa": (
        "maps",
        "an operator with r gives each pair its own value",
    ),
    "aa {&,equal|overlap} ab": (
        "ValueError",
        "a spatial relation needs the spatial flag",
    ),
}


counter = itertools.count()


def rows(name):
    """Identifier, time and feature counts of each map of a space time dataset

    New maps carry the name of the result dataset, which differs between the
    runs, so that only the part after it is compared. Maps that the algebra
    registers unchanged keep their identifier.
    """
    dataset = tgis.open_old_stds(name, "stvds")
    result = []
    for vector in dataset.get_registered_maps_as_objects(order="start_time") or []:
        vector.select()
        start, end = vector.get_absolute_time()
        meta = vector.metadata
        map_id = vector.get_id().replace(name, "diff", 1)
        result.append(
            (
                map_id,
                start,
                end,
                meta.get_number_of_points(),
                meta.get_number_of_lines(),
                meta.get_number_of_areas(),
                meta.get_number_of_centroids(),
            )
        )
    return result


def outcome(monkeypatch, expression, algebra):
    """The registered maps, None for no dataset, or the name of the error"""
    monkeypatch.setenv(ALGEBRA_VARIABLE, algebra)
    # Every run has its own result name: a result of an earlier expression
    # would otherwise stand in for the missing result of this one. Removing
    # it is no option, because the algebra registers unchanged maps of the
    # fixture in its result and removing the maps would delete them.
    name = f"diff_{algebra}_{next(counter)}"
    parser = tgis.TemporalVectorAlgebraParser(run=True, debug=False)
    try:
        parser.parse(f"{name} = {expression}", name, True)
    except (SyntaxError, ValueError, TypeError, tgis.FatalError) as error:
        return type(error).__name__
    if not tgis.dataset_factory(
        "stvds", f"{name}@{tgis.get_current_mapset()}"
    ).is_in_db():
        return None
    return rows(name)


@pytest.mark.parametrize("expression", SAME)
def test_same_result(vector_series, monkeypatch, expression):
    assert outcome(monkeypatch, expression, "core") == outcome(
        monkeypatch, expression, "classic"
    )


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_still_differ(vector_series, monkeypatch, expression):
    """A listed difference that no longer differs must leave the list"""
    core = outcome(monkeypatch, expression, "core")
    assert core != outcome(monkeypatch, expression, "classic")
    kind = "maps" if isinstance(core, list) else core
    assert kind == DIFFERENT[expression][0]
