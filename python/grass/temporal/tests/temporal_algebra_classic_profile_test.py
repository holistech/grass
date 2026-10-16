"""Tests of the classic profile that need no temporal database

The datasets are series in memory. The profile against the classic algebra
itself is compared in the test directories of the algebra tools.
"""

import pytest

from grass.temporal.algebra import CORE, Profile
from grass.temporal.algebra.parser import classic, evaluate, translate
from grass.temporal.algebra.parser.classic_grammar import classic_grammar
from grass.temporal.algebra.profile import CLASSIC
from grass.temporal.algebra.parser.translate import Translator


@pytest.fixture
def in_memory_datasets(monkeypatch, make_series):
    datasets = {
        "A": make_series("a", (1, 2), (2, 3), (3, 4)),
        "B": make_series("b", (1, 2), (2, 3), (3, 4), (1, 4)),
        "RT": make_series("x", (0, 1), (1, 2), (2, 3), unit="days"),
    }
    monkeypatch.setattr(translate, "source", lambda name, **_: datasets[name])
    return datasets


def chain(expression, profile=CLASSIC, **keywords):
    return evaluate(
        expression, overwrite=True, dry_run=True, profile=profile, **keywords
    )


def test_classic_is_a_profile_of_the_classic_translator():
    assert isinstance(CLASSIC, Profile)
    assert CLASSIC.translator is classic.ClassicTranslator
    assert issubclass(classic.ClassicTranslator, Translator)
    assert CLASSIC is not CORE


@pytest.mark.parametrize(
    ("kind", "selection", "expected"),
    [
        ("raster", False, "raster"),
        ("raster3d", False, "raster3d"),
        ("vector", False, "vector"),
        ("raster", True, "select"),
    ],
)
def test_the_grammar_follows_the_map_type_and_t_select(kind, selection, expected):
    assert CLASSIC.grammar.for_kind(kind, selection) is classic_grammar(expected)


def test_the_profile_reaches_the_translator(in_memory_datasets):
    """An if() without else is 0 where the condition is false in the classic
    algebra and null in the core, so the two chains differ"""
    expression = "R = if(A > 1, A)"
    assert chain(expression) != chain(expression, CORE)


def test_a_quoted_name_is_not_written_for_the_classic_algebra(in_memory_datasets):
    expression = "R = A + 1"
    assert '"' in str(chain(expression, CORE))
    assert '"' not in str(chain(expression))


def test_the_translator_knows_about_a_selection(in_memory_datasets):
    seen = []

    class Recording(Translator):
        def __init__(self, **keywords):
            super().__init__(**keywords)
            seen.append(self._selection)

    profile = Profile(translator=Recording)
    chain("R = A", profile, selection=True)
    chain("R = A", profile)
    assert seen == [True, False]


@pytest.mark.parametrize(
    "expression",
    [
        "R = tshift(A, 2)",
        "R = buff_t(A, 2)",
        "R = tshift(RT, '1 day')",
        "R = buff_t(RT, '1 day')",
        "R = tshift(A, '1 DAY')",
        "R = tshift(A, '3 onth')",
    ],
)
def test_an_increment_of_the_wrong_kind_is_a_syntax_error(
    in_memory_datasets, expression
):
    with pytest.raises(SyntaxError):
        chain(expression)


@pytest.mark.parametrize("expression", ["R = B {#,during,r} A", "R = A {#,equal,u} A"])
def test_the_hash_operator_keeps_the_left_time_stamp(in_memory_datasets, expression):
    with pytest.raises(SyntaxError, match="not supported"):
        chain(expression)


def test_a_relation_name_the_selection_does_not_know_is_a_syntax_error(
    in_memory_datasets,
):
    with pytest.raises(SyntaxError, match="Unpermitted"):
        chain("R = A {:,equal|overlap} B")
