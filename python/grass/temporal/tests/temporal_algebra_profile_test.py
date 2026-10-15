"""Tests for the profile and the grammar parameter of evaluate()

The datasets are series in memory, so that no temporal database is read.
"""

import pytest

from grass.temporal.algebra import CORE, Profile
from grass.temporal.algebra.parser import ast, evaluate, parse
from grass.temporal.algebra.parser import translate
from grass.temporal.algebra.parser.translate import Translator

EXPRESSIONS = (
    "R = A",
    "R = A + B",
    "R = A * 2",
    "R = A {+, during} B",
    "R = A {+, equal, u} B",
    "R = B {:, contains} A",
    "R = A : B",
    "R = B !: A",
    "R = A # B",
    "R = if(A > 1, A, C)",
    "R = if({equal}, start_day(A) > 1, C)",
    "R = if(start_doy(A) == 1, A)",
    "R = A[1] - A",
    "R = sin(A) + abs(B)",
    "R = merge(A, B)",
    "R = tshift(A, '1 day')",
    "R = tsnap(A)",
    "R = buff_t(A, '1 day')",
    "R = A - td(A)",
    "R = null() + A",
)


@pytest.fixture
def in_memory_datasets(monkeypatch, make_series):
    datasets = {
        "A": make_series("a", (1, 2), (2, 3), (3, 4)),
        "B": make_series("b", (1, 2), (2, 3), (3, 4), (1, 4)),
        "C": make_series("c", (1, 2), (2, 3), (3, 4)),
    }
    monkeypatch.setattr(translate, "source", lambda name, **_: datasets[name])
    return datasets


def chain(expression, **keywords):
    return evaluate(expression, overwrite=True, dry_run=True, **keywords)


@pytest.mark.parametrize("expression", EXPRESSIONS)
def test_core_profile_gives_the_chain_without_profile(in_memory_datasets, expression):
    plain = chain(expression)
    # An empty chain would make the comparison say nothing.
    assert plain["register"]
    assert chain(expression, profile=CORE) == plain
    assert chain(expression, profile=Profile()) == plain


def test_custom_grammar_supplies_the_tree(in_memory_datasets):
    seen = []

    class Fixed:
        def parse(self, text):
            seen.append(text)
            return ast.Statement("R", ast.Name("A"))

    fixed = chain("anything that is no expression", profile=Profile(grammar=Fixed()))
    assert seen == ["anything that is no expression"]
    assert fixed == chain("R = A")


def test_grammar_parameter_of_parse():
    class Fixed:
        def parse(self, text):
            return ast.Statement("R", ast.Name("A"))

    assert parse("no expression", grammar=Fixed()) == ast.Statement("R", ast.Name("A"))
    assert parse("R = A") == parse("R = A", grammar=None)


def test_custom_translator_is_built_with_the_profile(in_memory_datasets):
    made = []

    class Recording(Translator):
        def __init__(self, **keywords):
            super().__init__(**keywords)
            made.append((self.profile, self._kind))

    profile = Profile(translator=Recording)
    assert chain("R = A + B", profile=profile) == chain("R = A + B")
    assert made == [(profile, "raster")]


def test_translator_defaults_to_the_core_profile():
    assert Translator().profile is CORE


def test_profile_is_immutable():
    with pytest.raises(AttributeError):
        CORE.grammar = object()


def test_extension_points_are_methods_of_the_translator():
    for name in Translator.EXTENSION_POINTS:
        assert callable(getattr(Translator, name)), name


def test_an_override_of_an_extension_point_is_reached(in_memory_datasets):
    """Each hook of retime and merge is called as a method of self"""
    calls = []

    class Recording(Translator):
        def _tsnap(self, series):
            calls.append("tsnap")
            return super()._tsnap(series)

        def _tshift(self, series, increment):
            calls.append("tshift")
            return super()._tshift(series, increment)

        def _buff_t(self, series, increment):
            calls.append("buff_t")
            return super()._buff_t(series, increment)

        def _merge(self, first, second):
            calls.append("merge")
            return super()._merge(first, second)

        def _operands(self, node):
            calls.append("operands")
            return super()._operands(node)

    profile = Profile(translator=Recording)
    for expression in (
        "R = tsnap(A)",
        "R = tshift(A, '1 day')",
        "R = buff_t(A, '1 day')",
        "R = merge(A, B)",
        "R = A + B",
    ):
        chain(expression, profile=profile)
    assert calls == ["tsnap", "tshift", "buff_t", "merge", "operands"]
