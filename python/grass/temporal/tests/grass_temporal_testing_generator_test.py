"""Tests for the expression generator of grass.temporal.testing

The generator needs no temporal database. The forms of the published paper
must appear in a few hundred seeds, because a fuzz run that never writes them
cannot find a difference in them; the other kinds and the other seeds must
stay as they were, so that older fuzz results remain comparable.
"""

import re

import pytest

from grass.temporal.testing.expressions_generator import generate

# An operand that is no dataset: a number or a map read with map()
ATOM = r"(?:map\(\w+\)|\b\d+(?:\.\d+)?)"
OPERATOR = r" [-+*/%] "
COMPARISON = r"(?:==|!=|<=|>=|<|>)"

FORMS = {
    "number chain": re.compile(ATOM + OPERATOR + ATOM + OPERATOR + r"[\w(]"),
    "map() with a number": re.compile(
        rf"map\(\w+\){OPERATOR}\d|\b\d+(?:\.\d+)?{OPERATOR}map\("
    ),
    "td() on the left": re.compile(r"td\(\w+\) [*/%] "),
    "comparison operator": re.compile(r"\{" + COMPARISON + ","),
    "bare comparison of datasets": re.compile(
        rf"(?<![\w)\]])[A-Z][A-Za-z0-9]* {COMPARISON} [A-Z][A-Za-z0-9]*\b"
    ),
}
CAPITALS = re.compile(r"\b(?:STRDS|STR3DS|STVDS)\(")
RASTER_FORMS = list(FORMS)

# Expressions of the generator before the forms of the paper were written
# (observed 2026-10-17 with the generator of the previous commit, seeds 1 to
# 3 per kind): a share of 0, and every kind that has no such forms, must give
# them again.
BEFORE = {
    ("raster", 1): ("AF {-,precedes} A", {"register_null": True}),
    ("raster", 2): ("int(A) {!:,equal,d} C + A", {"register_null": False}),
    ("raster", 3): ("merge(OV, C)", {"register_null": False}),
    ("raster3d", 1): (
        "if({overlaps|finished}, td(Z) > 2, A * 3, null())",
        {"register_null": False},
    ),
    ("raster3d", 2): ("A * Z : Q", {"register_null": False, "spatial": True}),
    ("raster3d", 3): ("D % Q : (W)", {"register_null": False}),
    ("vector", 1): ("pa !: pa !: ac", {}),
    ("vector", 2): ("pb {^,finishes|precedes} aa", {}),
    ("vector", 3): (
        "pa {+,during,u} pa ^ wide {&,overlaps|finished|started,l} merge(aa, aa)",
        {},
    ),
    ("select", 1): ('tshift(Z, "-3 hours")', {}),
    ("select", 2): ("RT {!:,finished|equal|during,l} I", {}),
    ("select", 3): (
        "merge(C !: A, tmap(sinst) {!:,overlaps,r} AF)",
        {"spatial": True},
    ),
}


def expressions(kind, count=1000, **options):
    return [generate(kind, seed, **options)[0] for seed in range(count)]


@pytest.mark.parametrize("kind", ["raster", "raster3d"])
@pytest.mark.parametrize("form", RASTER_FORMS)
def test_each_form_of_the_paper_appears_in_a_thousand_seeds(kind, form):
    found = [text for text in expressions(kind) if FORMS[form].search(text)]
    assert found, form


@pytest.mark.parametrize("kind", ["raster", "raster3d"])
def test_granularity_seeds_write_the_comparison_without_braces(kind):
    """The granularity mode refuses temporal operators, so the comparison of
    two datasets can only be the bare one there"""
    texts = expressions(kind, 3000, granularity_share=1.0)
    assert any(FORMS["bare comparison of datasets"].search(text) for text in texts)
    assert not any(FORMS["comparison operator"].search(text) for text in texts)


def test_select_writes_the_dataset_functions_in_capitals_and_lower_case():
    texts = expressions("select")
    for spelling in ("STRDS", "STR3DS", "STVDS", "strds", "str3ds", "stvds"):
        assert any(f"{spelling}(" in text for text in texts), spelling


@pytest.mark.parametrize("kind", ["vector", "select"])
def test_vector_and_select_get_no_raster_forms(kind):
    for text in expressions(kind, 3000):
        for form, pattern in FORMS.items():
            assert not pattern.search(text), (form, text)


@pytest.mark.parametrize("kind", ["raster", "raster3d", "vector"])
def test_the_dataset_functions_stay_out_of_other_kinds(kind):
    assert not any(CAPITALS.search(text) for text in expressions(kind, 3000))


@pytest.mark.parametrize(("kind", "seed"), sorted(BEFORE))
def test_without_the_paper_share_a_seed_gives_its_old_expression(kind, seed):
    assert generate(kind, seed, paper_share=0.0) == BEFORE[kind, seed]


@pytest.mark.parametrize("kind", ["raster", "raster3d", "select"])
def test_a_seed_that_draws_no_paper_forms_keeps_its_old_expression(kind):
    """At the default share each seed is either a paper seed, the same as with
    a share of 1, or gives the expression of a share of 0; whether it is one is
    drawn apart from the expression, so the other seeds stay comparable"""
    old = 0
    for seed in range(400):
        default = generate(kind, seed)
        if default == generate(kind, seed, paper_share=0.0):
            old += 1
        else:
            assert default == generate(kind, seed, paper_share=1.0), seed
    # A quarter of the seeds are paper seeds by default; some of them may
    # draw no new form and so match the old expression.
    assert old >= 250


def test_the_paper_share_leaves_the_vector_kind_alone():
    for seed in range(500):
        assert generate("vector", seed) == generate("vector", seed, paper_share=0.0)


def test_the_same_seed_gives_the_same_expression():
    for kind in ("raster", "raster3d", "vector", "select"):
        assert generate(kind, 77) == generate(kind, 77)


def test_a_share_of_one_writes_paper_forms_into_every_raster_seed_stream():
    """Every seed then draws from the stream with the builders, so the mix
    differs from a share of 0 for most seeds"""
    changed = sum(
        generate("raster", seed, paper_share=1.0)
        != generate("raster", seed, paper_share=0.0)
        for seed in range(200)
    )
    assert changed > 150
