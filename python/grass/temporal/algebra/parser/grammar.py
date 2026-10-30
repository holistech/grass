"""Grammar of the temporal algebra

The rules only build syntax tree nodes; no rule computes or reads data, so
parsing needs no GRASS session. Precedence and parentheses are settled here
alone: the precedence table orders the operators, so the grammar needs one
expression nonterminal for maps, numbers and conditions alike.
"""

from __future__ import annotations

import functools

from grass.temporal.ply import yacc

from . import ast
from .lexer import TOKENS, build_lexer


class Grammar:
    """The PLY rules; each p_ function documents its productions"""

    tokens = TOKENS
    start = "statement"
    # From the weakest to the strongest binding. Selection binds weakest as
    # in the earlier parser; && binds stronger than ||, as in r.mapcalc and
    # most languages, which the earlier parser did only for map values.
    precedence = (
        ("left", "SELECT", "NOT_SELECT", "SELECT_OP"),
        ("left", "OR", "OR_OP"),
        ("left", "AND", "AND_OP"),
        ("nonassoc", "EQ", "NE", "LT", "LE", "GT", "GE", "CMP_OP"),
        # The overlays of vector maps bind as + does, from left to right, as
        # in the classic vector grammar, where they share one level with +,
        # the v.patch of vector maps.
        (
            "left",
            "PLUS",
            "MINUS",
            "ADD_OP",
            "HASH",
            "HASH_OP",
            "AMP",
            "PIPE",
            "CARET",
            "TILDE",
            "OVERLAY_OP",
        ),
        ("left", "TIMES", "DIVIDE", "MODULO", "MUL_OP"),
        ("right", "NEGATIVE"),
    )

    @staticmethod
    def p_statement(p):
        """statement : NAME ASSIGN expression"""
        p[0] = ast.Statement(p[1], p[3])

    @staticmethod
    def p_binary(p):
        """
        expression : expression SELECT expression
                   | expression NOT_SELECT expression
                   | expression OR expression
                   | expression AND expression
                   | expression EQ expression
                   | expression NE expression
                   | expression LT expression
                   | expression LE expression
                   | expression GT expression
                   | expression GE expression
                   | expression PLUS expression
                   | expression MINUS expression
                   | expression HASH expression
                   | expression TIMES expression
                   | expression DIVIDE expression
                   | expression MODULO expression
                   | expression AMP expression
                   | expression PIPE expression
                   | expression CARET expression
                   | expression TILDE expression
        """
        p[0] = ast.Binary(p[2], p[1], p[3])

    @staticmethod
    def p_operator(p):
        """
        expression : expression SELECT_OP expression
                   | expression OR_OP expression
                   | expression AND_OP expression
                   | expression ADD_OP expression
                   | expression HASH_OP expression
                   | expression MUL_OP expression
                   | expression OVERLAY_OP expression
                   | expression CMP_OP expression
        """
        p[0] = ast.Binary(p[2].symbol, p[1], p[3], p[2])

    @staticmethod
    def p_negative(p):
        """expression : MINUS expression %prec NEGATIVE"""
        # A negative literal stays a Number, so that arguments such as the
        # -1 of start_doy(A, -1) reach the translator as plain numbers.
        if isinstance(p[2], ast.Number):
            p[0] = ast.Number(-p[2].value)
        else:
            p[0] = ast.Negative(p[2])

    @staticmethod
    def p_group(p):
        """expression : LPAREN expression RPAREN"""
        p[0] = p[2]

    @staticmethod
    def p_number(p):
        """
        expression : INT
                   | FLOAT
        """
        p[0] = ast.Number(p[1])

    @staticmethod
    def p_text(p):
        """expression : STRING"""
        p[0] = ast.Text(p[1])

    @staticmethod
    def p_name(p):
        """expression : NAME"""
        p[0] = ast.Name(p[1])

    @staticmethod
    def p_index(p):
        """expression : NAME LBRACKET offsets RBRACKET"""
        p[0] = ast.Index(p[1], tuple(p[3]))

    @staticmethod
    def p_offsets(p):
        """
        offsets : offset
                | offsets COMMA offset
        """
        p[0] = [p[1]] if len(p) == 2 else [*p[1], p[3]]

    @staticmethod
    def p_offset(p):
        """
        offset : INT
               | MINUS INT
        """
        p[0] = p[1] if len(p) == 2 else -p[2]

    @staticmethod
    def p_function(p):
        """
        expression : NAME LPAREN RPAREN
                   | NAME LPAREN arguments RPAREN
                   | NAME LPAREN RELATION COMMA arguments RPAREN
        """
        if len(p) == 4:
            p[0] = ast.Function(p[1], ())
        elif len(p) == 5:
            p[0] = ast.Function(p[1], tuple(p[3]))
        else:
            p[0] = ast.Function(p[1], tuple(p[5]), p[3])

    @staticmethod
    def p_arguments(p):
        """
        arguments : expression
                  | arguments COMMA expression
        """
        p[0] = [p[1]] if len(p) == 2 else [*p[1], p[3]]

    @staticmethod
    def p_error(p):
        """Raise a SyntaxError for the token p, or for the end of the input"""
        if p is None:
            msg = "Unexpected end of the expression"
            raise SyntaxError(msg)
        msg = f"Syntax error near '{p.value}' at position {p.lexpos}"
        raise SyntaxError(msg)


def build_parser(errorlog=None):
    """Build the LALR tables; errorlog receives the warnings of PLY

    PLY reports shift/reduce and reduce/reduce conflicts only in debug mode.
    The null debug log keeps that mode from writing a parser.out file.
    """
    return yacc.yacc(
        module=Grammar,
        debug=True,
        debuglog=yacc.NullLogger(),
        errorlog=errorlog,
    )


@functools.cache
def _parser():
    return build_parser()


def parse(text):
    """Return the syntax tree of the statement "name = expression"

    :raises SyntaxError: with the position of the first error
    """
    return _parser().parse(text, lexer=build_lexer())
