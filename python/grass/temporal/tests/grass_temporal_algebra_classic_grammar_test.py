"""Tests of the classic grammar, which builds syntax trees of the core

The grammar reads what the parser classes of the classic algebra read. It is
measured against them: for the same text the parser classes (reached through
grass.temporal.testing.reference, with run=False so that nothing is computed)
and the grammar must both accept or both reject, on the expressions of the
tests of the parser class for t.select, on the forms on the border of the two
grammars and on seeded expressions of the fuzzer with damaged variants of
them. The datasets of the fuzzer exist in the session, because the parser
classes open them while parsing and a missing one would hide a later syntax
error.

Checks that a rule of the parser classes makes with the datasets or with the
text of an increment are no syntax; SEMANTIC_ERROR names them, and the
translator of the classic profile has to make them. A missing dataset ends the
parser classes before they reach a later syntax error, so for a text that the
grammar rejects they need only fail somehow.

The last tests keep the frozen copy of the productions in step with the
parser classes for as long as these exist.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import ast as python_ast
import inspect
import random
import re
import sys
import textwrap
from pathlib import Path

import pytest

from grass.temporal.algebra.parser import ast, classic_productions
from grass.temporal.algebra.parser import classic_grammar as classic
from grass.temporal.testing.differential import prepare
from grass.temporal.testing.expressions_generator import boundary_forms, generate
from grass.temporal.testing.expressions import seed_range
from grass.temporal.testing.reference import run_reference
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools

PARSER_TEST = Path(__file__).with_name("temporal_algebra_parser_test.py")


@pytest.fixture(scope="module")
def world(request, tmp_path_factory):
    """The kind and a session with the datasets of the fuzzer of that kind

    Each kind has its own session: the raster and the 3D raster datasets share
    names.
    """
    kind = request.param
    path = tmp_path_factory.mktemp(kind)
    with temporal_session(path / "project") as session:
        prepare(kind, session, path)
        if kind in {"raster", "select"}:
            # Datasets that the expressions of the parser class tests name
            tools = Tools(session=session, overwrite=True, quiet=True)
            for name in ("H", "EMPTY", "REL"):
                tools.t_create(output=name, type="strds", title=name, description=name)
        yield kind, session


# Some rules of the parser classes check their operands (the relations of an
# operator, the unit of an increment) only when they run, so the options must
# let them run. The vector parser class has no dry run and computes.
RUN_OPTIONS = {
    "raster": {"run": True, "dry_run": True},
    "raster3d": {"run": True, "dry_run": True},
    "select": {"run": True, "dry_run": True},
    "vector": {"run": True, "debug": False},
}


def kinds(*names):
    """Run a test once for each of the kinds, each in a session of its own"""
    return pytest.mark.parametrize("world", names, indirect=True)


def old_outcome(kind, expression):
    """How the parser class of the kind ends: None, or the exception it raises"""
    try:
        run_reference(
            kind, expression, basename="gr", overwrite=True, **RUN_OPTIONS[kind]
        )
    except (Exception, SystemExit) as error:  # noqa: BLE001
        return error
    return None


# SyntaxErrors that rules of the parser classes raise for reasons the grammar
# does not see: the temporal type of the datasets, the text of an increment,
# and operator parts that the earlier algebra refuses and the core accepts.
# The translator of the classic profile makes these checks.
SEMANTIC_ERROR = re.compile(
    r"^(Function \w+\(\) (needs a |cannot )"
    r"|The hash operator .* is not supported"
    r"|Unpermitted temporal relation name)"
)


def new_rejects(kind, expression):
    try:
        classic.classic_grammar(kind).parse(expression)
    except SyntaxError:
        return True
    return False


def disagreements(kind, expressions):
    """The expressions that the grammar and the parser class judge differently

    The grammar rejects a text if and only if the parser class does, with two
    allowances that follow from what each of them sees:

    - A rule of the parser class opens the datasets and checks the maps while
      parsing, so a missing dataset or a map without end time stops it with
      another error before it reaches the syntax error that the grammar
      finds. The parser class must raise some error then.
    - Some SyntaxErrors of the parser class are no matter of syntax, see
      SEMANTIC_ERROR.
    """
    found = []
    for expression in expressions:
        old = old_outcome(kind, expression)
        if new_rejects(kind, expression):
            if old is None:
                found.append((expression, "the parser class accepts"))
        elif isinstance(old, SyntaxError) and not SEMANTIC_ERROR.search(str(old)):
            found.append((expression, f"the parser class rejects: {old}"))
    return found


def statements_of_parser_test():
    """The strings "name = expression" in the tests of the parser class"""
    tree = python_ast.parse(PARSER_TEST.read_text(encoding="utf-8"))
    found = {
        node.value
        for node in python_ast.walk(tree)
        if isinstance(node, python_ast.Constant)
        and isinstance(node.value, str)
        and re.fullmatch(r"\w+ = [^\n]+", node.value)
    }
    return sorted(found)


def damaged(statement, seed):
    """Two variants of a statement that are likely not valid syntax any more"""
    rng = random.Random(seed)
    start = statement.index("=") + 2
    cut = rng.randrange(start + 1, len(statement) + 1)
    position = rng.randrange(start, len(statement))
    return [statement[:cut], statement[:position] + statement[position + 1 :]]


@kinds("select", "raster")
def test_accepts_what_the_parser_tests_accept(world):
    """The statements of the parser class tests are read or refused as there"""
    kind, _ = world
    statements = statements_of_parser_test()
    assert len(statements) > 150
    assert disagreements(kind, statements) == []


@kinds("select")
def test_parser_test_statements_include_rejected_ones(world):
    """Negative check: the statements hold some that both sides refuse

    Without them the comparison above would pass for a grammar that accepts
    everything.
    """
    kind, _ = world
    rejected = [
        statement
        for statement in statements_of_parser_test()
        if new_rejects(kind, statement)
    ]
    assert rejected
    assert all(old_outcome(kind, statement) is not None for statement in rejected)


@kinds(*classic.GRAMMARS)
def test_boundary_forms(world):
    """The forms on the border of the classic and the core grammar"""
    kind, _ = world
    forms = [f"R = {form}" for form in boundary_forms(kind)]
    assert disagreements(kind, forms) == []


def braced_operator_statement(kind, operator):
    """A statement that uses a braced operator of the generator where the
    generator writes it: && and || join conditions, the comparison operators
    compare two datasets in a condition, and the hash operator of the vector
    algebra and t.select stands in a condition"""
    symbol = operator[1:].split(",")[0]
    if symbol in {"&&", "||"}:
        return f"R = if(start_doy(A) > 0 {operator} start_doy(B) > 0, A)"
    if symbol == "#" and kind in {"vector", "select"}:
        return f"R = if(A {operator} B > 1, A)"
    if symbol in {"==", "!=", "<", "<=", ">", ">="}:
        # The comparison operator stands in a condition; the generator writes
        # it for the raster kinds only
        return f"R = if(A {operator} B, A)"
    return f"R = A {operator} B"


@pytest.mark.parametrize("kind", classic.GRAMMARS)
def test_the_generator_writes_braced_operators_the_grammar_reads(kind):
    """Every braced operator of generated expressions parses, so that a
    generated relation, aggregate or temporal reference is compared and not
    refused as a syntax error by both implementations"""
    grammar = classic.classic_grammar(kind)
    operators = {
        operator
        for seed in range(300)
        for operator in re.findall(r"\{[^{}]*,[^{}]*\}", generate(kind, seed)[0])
    }
    # The check must see every temporal reference to prove its point.
    assert {
        part for operator in operators for part in operator[1:-1].split(",")
    } >= set("lruid")
    rejected = []
    for operator in sorted(operators):
        try:
            grammar.parse(braced_operator_statement(kind, operator))
        except SyntaxError:
            rejected.append(operator)
    assert rejected == []


@pytest.mark.slow
@kinds(*classic.GRAMMARS)
def test_seeded_expressions_and_damaged_variants(world):
    """Generated expressions and damaged copies are read or refused as before"""
    kind, _ = world
    statements = []
    for seed in seed_range():
        expression, _options = generate(kind, seed)
        statement = f"R = {expression}"
        statements.extend([statement, *damaged(statement, seed)])
    rejected = sum(new_rejects(kind, statement) for statement in statements)
    # The damaged variants must contain refusals, or the check proves little
    assert 0 < rejected < len(statements)
    assert disagreements(kind, statements) == []


def shape(node):
    """The grouping of && and || in a tree; every other node is a leaf"""
    if isinstance(node, ast.Binary) and node.symbol in {"&&", "||"}:
        return (node.symbol, shape(node.left), shape(node.right))
    return "leaf"


def parse_condition(kind, condition):
    return classic.classic_grammar(kind).parse(f"R = if({condition}, A)").expression


def condition_of(tree):
    """The first argument of the if() of a parsed statement"""
    assert isinstance(tree, ast.Function)
    return tree.arguments[0]


@kinds("raster")
def test_precedence_of_and_or_follows_the_classic_algebra(world):
    """&& binds stronger than || in conditions on map values, not in temporal ones

    The expected groupings are what the parser class does, measured 2026-10-16
    with grass.temporal.testing.differential.outcome on the reference runner and
    the datasets of the fuzzer (A holds the values 1 to 4 in its first maps):

    - ``if(A > 1 || A < 3 && A > 2, A)`` keeps the maps with the values 2, 3
      and 4: the map with 2 passes by ``A > 1``, so ``&&`` binds first.
    - ``if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)`` keeps no map although
      every map lasts one day: ``||`` and ``&&`` group from left to right.
    """
    kind, _ = world
    values = condition_of(parse_condition(kind, "A > 1 || A < 3 && A > 2"))
    assert shape(values) == ("||", "leaf", ("&&", "leaf", "leaf"))
    times = condition_of(
        parse_condition(kind, "td(A) == 1 || td(A) == 2 && td(A) == 3")
    )
    assert shape(times) == ("&&", ("||", "leaf", "leaf"), "leaf")
    # Two && chains read the same way in both kinds of condition
    both = condition_of(parse_condition(kind, "A > 1 && A < 3 || A > 3"))
    assert shape(both) == ("||", ("&&", "leaf", "leaf"), "leaf")


@kinds("raster")
def test_precedence_measured_on_the_reference(world):
    """The classic algebra computes the groupings that the test above expects"""
    from grass.temporal.testing.differential import RUNNERS, outcome

    kind, _ = world
    reference = RUNNERS["reference"]

    def minima(condition):
        result = outcome(kind, f"if({condition}, A)", reference, basename="pr")
        return [row[3] for row in result["maps"]]

    # The first map (value 1) is null, the others keep their values
    assert minima("A > 1 || A < 3 && A > 2")[1:4] == [2.0, 3.0, 4.0]
    assert (
        outcome(
            kind,
            "if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)",
            reference,
            basename="pr",
        )["maps"]
        == []
    )


# The drift tests


def class_productions(parser_class):
    """The (name, text) pairs in the order in which PLY reads the class"""
    rules = []
    for name in dir(parser_class):
        if name.startswith("p_") and name != "p_error":
            method = getattr(parser_class, name)
            rules.append(
                (
                    method.__code__.co_firstlineno,
                    str(inspect.getmodule(method)),
                    name,
                    method.__doc__,
                )
            )
    rules.sort()
    return [(name, text) for _, _, name, text in rules]


def lines_of(text):
    """The lines of a production text without indentation; PLY reads no more"""
    return [line.split() for line in textwrap.dedent(text).splitlines() if line.strip()]


def parser_class_of(kind):
    from grass.temporal.classic.temporal_algebra import TemporalAlgebraParser
    from grass.temporal.classic.temporal_raster3d_algebra import (
        TemporalRaster3DAlgebraParser,
    )
    from grass.temporal.classic.temporal_raster_algebra import (
        TemporalRasterAlgebraParser,
    )
    from grass.temporal.classic.temporal_vector_algebra import (
        TemporalVectorAlgebraParser,
    )

    return {
        "raster": TemporalRasterAlgebraParser,
        "raster3d": TemporalRaster3DAlgebraParser,
        "vector": TemporalVectorAlgebraParser,
        "select": TemporalAlgebraParser,
    }[kind]


def drift(kind):
    """What differs between the parser class of a kind and the frozen copy"""
    parser_class = parser_class_of(kind)
    found = []
    old = class_productions(parser_class)
    new = classic.productions(kind)
    if [name for name, _ in old] != [name for name, _ in new]:
        found.append("the rules or their order differ")
    else:
        found.extend(
            f"{name}: the production differs"
            for (name, old_text), (_, new_text) in zip(old, new, strict=True)
            if lines_of(old_text) != lines_of(new_text)
        )
    old_precedence = tuple(tuple(row) for row in parser_class.precedence)
    if old_precedence != classic_productions.PRECEDENCE[kind]:
        found.append("the precedence differs")
    if tuple(parser_class.tokens) != classic.classic_grammar(kind).tokens:
        found.append("the tokens differ")
    if parser_class.start != classic.START:
        found.append("the start symbol differs")
    return found


@pytest.mark.parametrize("kind", classic.GRAMMARS)
def test_frozen_copy_equals_the_parser_classes(kind):
    """Every production, the precedence, the tokens and the start symbol agree"""
    assert drift(kind) == []


def test_drift_check_sees_a_changed_production(monkeypatch):
    """Negative check: a changed text or precedence is reported"""
    changed = dict(classic_productions.TEXTS)
    changed["p_paren_expr"] = "expr : LPAREN expr expr RPAREN"
    monkeypatch.setattr(classic_productions, "TEXTS", changed)
    assert drift("select") == ["p_paren_expr: the production differs"]
    monkeypatch.setattr(
        classic_productions,
        "PRECEDENCE",
        {**classic_productions.PRECEDENCE, "select": (("left", "AND"),)},
    )
    assert "the precedence differs" in drift("select")


@kinds("select")
def test_comparison_sees_a_wrong_grammar(world, monkeypatch):
    """Negative check: a grammar that rejects all or accepts all is reported"""
    kind, _ = world
    monkeypatch.setattr(sys.modules[__name__], "new_rejects", lambda *_: True)
    assert disagreements(kind, ["R = A : B"]) == [
        ("R = A : B", "the parser class accepts")
    ]
    monkeypatch.setattr(sys.modules[__name__], "new_rejects", lambda *_: False)
    found = disagreements(kind, ["R = A B"])
    assert len(found) == 1
    assert found[0][1].startswith("the parser class rejects")
