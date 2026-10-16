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


# if() on time with maps as then and else clears the count of A # B: the
# contents keep the map but are no longer counted, see
# ClassicTranslator._uncounted().
CLEARED_COUNT = "R = if(start_day(A) > 1, A # B, B) + B"


@pytest.mark.parametrize(
    "expression",
    [
        "R = if(A > 0 && (A # B) + 1 >= 1, 2.0, 3)",
        "R = if(isnull(A), if(A > 0 && exp(A # B) >= 1, B), 4)",
        "R = if(isnull((A # B) * 2), B, merge(A # B, B # A) * 3)",
        "R = if(start_day(A) > 1, A # B, 5) + B",
        CLEARED_COUNT,
    ],
)
def test_the_tables_of_the_translator_keep_their_keys(in_memory_datasets, expression):
    """A table keyed by id() must hold the object of the key: once that object
    is gone, a later object can take its id and read another entry. A table
    of counts keyed by the id of a series it did not keep made if() take a
    count for its then part in some runs only, depending on the memory."""
    translator = classic.ClassicTranslator(kind="raster")
    translator.statement(classic_grammar("raster").parse(expression))
    for name in ("_commands", "_hashes"):
        for key, (series, _value) in getattr(translator, name)._notes.items():
            assert id(series) == key, name


def test_clearing_a_count_keeps_the_map_it_counted(in_memory_datasets, monkeypatch):
    """if() on time with maps clears the count but not the map object"""
    translator = classic.ClassicTranslator(kind="raster")
    seen = []
    uncounted = translator._uncounted

    def spy(series):
        result = uncounted(series)
        seen.append((series, result))
        return result

    monkeypatch.setattr(translator, "_uncounted", spy)
    translator.statement(classic_grammar("raster").parse(CLEARED_COUNT))
    cleared = 0
    for before, after in seen:
        for old, new in zip(before.slots, after.slots, strict=True):
            if translator._counted(old.content):
                cleared += 1
                assert not translator._counted(new.content)
                assert translator._source(new.content) is translator._source(
                    old.content
                )
    assert cleared
