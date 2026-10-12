"""Tests for the grammar of the temporal algebra syntax"""

import io

import pytest

from grass.temporal.algebra.parser.ast import (
    Binary,
    Function,
    Index,
    Name,
    Negative,
    Number,
    Statement,
    Text,
)
from grass.temporal.algebra.parser.grammar import Grammar, build_parser, parse
from grass.temporal.algebra.parser.operators import TemporalOperator
from grass.temporal.ply import yacc

A, B, C = Name("A"), Name("B"), Name("C")


def expression(text):
    return parse(f"R = {text}").expression


def test_statement():
    assert parse("R = A") == Statement("R", A)


@pytest.mark.parametrize(
    ("text", "tree"),
    [
        ("A + B * C", Binary("+", A, Binary("*", B, C))),
        ("A - B - C", Binary("-", Binary("-", A, B), C)),
        ("(A + B) * C", Binary("*", Binary("+", A, B), C)),
        ("A : B + C", Binary(":", A, Binary("+", B, C))),
        ("A : B !: C", Binary("!:", Binary(":", A, B), C)),
        ("A # B + 1", Binary("+", Binary("#", A, B), Number(1))),
        ("A + 1 > 2", Binary(">", Binary("+", A, Number(1)), Number(2))),
        (
            "A > 1 && B < 2",
            Binary("&&", Binary(">", A, Number(1)), Binary("<", B, Number(2))),
        ),
        ("A || B && C", Binary("||", A, Binary("&&", B, C))),
        ("(A || B) && C", Binary("&&", Binary("||", A, B), C)),
        ("A && B || C", Binary("||", Binary("&&", A, B), C)),
        ("-A * 2", Binary("*", Negative(A), Number(2))),
        ("A - -2", Binary("-", A, Number(-2))),
        ("-2.5", Number(-2.5)),
        ("2 < A", Binary("<", Number(2), A)),
    ],
)
def test_precedence(text, tree):
    assert expression(text) == tree


def test_operators_in_braces_take_the_precedence_of_their_symbol():
    plus = TemporalOperator("+", ("during",), temporal="r")
    times = TemporalOperator("*", ("during",))
    assert expression("A {+,during,r} B {*,during} C") == Binary(
        "+", A, Binary("*", B, C, times), plus
    )
    select = TemporalOperator(":", ("during",))
    assert expression("A {:,during} B + C") == Binary(":", A, Binary("+", B, C), select)
    both = TemporalOperator("&&", ("during",), "|", "l")
    assert expression("A {&&,during,|} B || C") == Binary(
        "||", Binary("&&", A, B, both), C
    )


@pytest.mark.parametrize(
    ("text", "tree"),
    [
        ("sin(A)", Function("sin", (A,))),
        ("null()", Function("null", ())),
        ('buff_t(A, "10 months")', Function("buff_t", (A, Text("10 months")))),
        ("start_doy(A, -1)", Function("start_doy", (A, Number(-1)))),
        ("if(A > 1, B)", Function("if", (Binary(">", A, Number(1)), B))),
        (
            "if({during,|}, A > 1, B, 0)",
            Function(
                "if",
                (Binary(">", A, Number(1)), B, Number(0)),
                TemporalOperator(None, ("during",), "|"),
            ),
        ),
        ("A[1]", Index("A", (1,))),
        ("A[-1, 0]", Index("A", (-1, 0))),
        ("A[0,1,-2]", Index("A", (0, 1, -2))),
        ("td(A@PERMANENT)", Function("td", (Name("A@PERMANENT"),))),
        ("td + 1", Binary("+", Name("td"), Number(1))),
    ],
)
def test_functions_and_indices(text, tree):
    assert expression(text) == tree


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("R = A +", "Unexpected end of the expression"),
        ("R = A ) B", r"Syntax error near '\)' at position 6"),
        ("R = A < B < C", r"Syntax error near '<' at position 10"),
        ("R = A[1.5]", r"Syntax error near '1.5' at position 6"),
        ("R = A[B]", r"Syntax error near 'B' at position 6"),
        ("R = f({during})", r"Syntax error near '\)' at position 14"),
        ("A + B", r"Syntax error near '\+' at position 2"),
    ],
)
def test_syntax_errors(text, message):
    with pytest.raises(SyntaxError, match=message):
        parse(text)


def test_grammar_has_no_conflicts():
    """Every ambiguity is settled by the precedence table, not by PLY

    The log must be empty: it would also show unused tokens and rules.
    """
    log = io.StringIO()
    build_parser(errorlog=yacc.PlyLogger(log))
    assert log.getvalue() == ""


def test_conflict_check_sees_a_missing_precedence(monkeypatch):
    """Negative control: build_parser reports the conflicts PLY finds"""
    # Only the level for NEGATIVE stays, so that %prec still resolves. The
    # patch touches the class attribute only and is undone after the test;
    # build_parser caches nothing, and the test does not call parse(), whose
    # cached parser must not be built from the patched table.
    monkeypatch.setattr(Grammar, "precedence", (("right", "NEGATIVE"),))
    log = io.StringIO()
    build_parser(errorlog=yacc.PlyLogger(log))
    assert "shift/reduce conflicts" in log.getvalue()
