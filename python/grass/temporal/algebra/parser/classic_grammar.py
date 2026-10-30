"""The grammar of the classic temporal algebra, building syntax trees of the core

The classic algebra reads ``name = expression`` with the productions of the
parser classes of ``grass.temporal.classic`` (``temporal_algebra``,
``temporal_raster_base_algebra``, ``temporal_raster_algebra``,
``temporal_raster3d_algebra`` and ``temporal_vector_algebra``).
``classic_productions`` holds a frozen copy of those productions and of the
precedence tables as data, and this module one generic action that turns
every production into nodes of ``grass.temporal.algebra.parser.ast``.
What the classic grammar reads, what it rejects and how it groups therefore
stays as it was, while the meaning is given by a translator of the core.

The copy is frozen so that it states what the classic grammar reads
independently of the ``p_`` methods of the parser classes. A test compares
every production text, the precedence and the tokens with the copy, so that a
change of either side is noticed.

The PLY version of the package builds its tables in memory and writes nothing
next to the source; debug=False also keeps it from writing a parser.out.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import dataclasses
import functools

from grass.temporal.algebra.parser import ast, classic_productions
from grass.temporal.algebra.parser.operators import (
    TemporalOperator,
    parse_operator,
    relation_names,
)
from grass.temporal.algebra.relations import SPATIAL_RELATIONS, TEMPORAL_RELATIONS
from grass.temporal.ply import yacc

GRAMMARS = ("raster", "raster3d", "vector", "select")


# Every class starts at the statement.
START = "statement"


def productions(kind):
    """Return the productions of a kind as ``(method name, text)`` pairs

    :param kind: one of ``GRAMMARS``
    :return: the pairs in the order in which PLY read them in the parser class
    """
    return tuple(
        (name, classic_productions.TEXTS[name])
        for name in classic_productions.ORDER[kind]
    )


# Every written relation name, the shorthands "over" and "equals" included
_NAMES = {*TEMPORAL_RELATIONS, *SPATIAL_RELATIONS, "over", "equals"}

# Tokens whose text is the symbol of a binary operation
_SYMBOL_TOKENS = {
    "MOD", "DIV", "MULT", "ADD", "SUB", "HASH", "T_SELECT", "T_NOT_SELECT",
    "AND", "OR", "XOR", "NOT", "DISOR",
}  # fmt: skip
_OPERATOR_TOKENS = {
    "T_SELECT_OPERATOR", "T_HASH_OPERATOR", "T_COMP_OPERATOR",
    "T_ARITH1_OPERATOR", "T_ARITH2_OPERATOR", "T_OVERLAY_OPERATOR",
    "T_COMPARISON_OPERATOR",
}  # fmt: skip
# Nonterminals whose value is the name of a function or a comparison
_WORDS = ("comp_op", "t_var", "mapcalc_arith", "buff_function")
_TIME_LITERALS = {"DATE", "TIME", "DATETIME"}

# Conditions on map values (and mixed ones) are r.mapcalc text in the classic
# algebra, joined as "left && (right)": the right operand is parenthesized,
# the left is not, so r.mapcalc applies its precedence along the left spine.
_TEXT_HEADS = {"s_var_expr", "ts_var_expr"}


class _Run:
    """The state of one parse

    PLY swallows a SyntaxError raised inside a rule, so the actions collect
    their errors here, as the parser classes do, and parse() raises the first.
    """

    def __init__(self):
        self.errors = []
        self.expression = ""
        # The nodes of _chain() that read as r.mapcalc text, by id()
        self.text_nodes = {}


def _chain(symbol, left, right, text_nodes):
    """Join two conditions of a text chain as r.mapcalc would read them

    The grammar groups a || b && c from left to right; the classic text
    "a||(b)&&(c)" makes r.mapcalc read a || (b && c).
    """
    if (
        symbol == "&&"
        and id(left) in text_nodes
        and left.symbol == "||"
        and left.operator is None
    ):
        node = ast.Binary("||", left.left, _chain("&&", left.right, right, text_nodes))
    else:
        node = ast.Binary(symbol, left, right)
    text_nodes[id(node)] = node
    return node


def _operator(text, errors):
    """The operator, with its relation list as written

    The classic operator parser keeps a relation named twice, and the
    classic algebra then relates a partner once per name (A {+,equal|equal} N
    adds n twice); parse_operator() of the core drops the repetition.
    """
    try:
        operator = parse_operator(text)
    except SyntaxError as error:
        errors.append(str(error))
        return parse_operator("{" + text.strip()[1:-1].split(",")[0] + "}")
    parts = [part.strip() for part in text.strip()[1:-1].split(",")]
    for part in parts:
        for word in part.split("|"):
            word = word.strip()
            if word.lower() in _NAMES and word != word.lower():
                # The classic operator lexer knows the relation names in
                # lower case only (found by the fuzzer, 15.10.2026:
                # A {+,EQUAL} N); parse_operator() lowers them.
                errors.append(f"syntax error on line 1 position 3 near '{word}'")
    lists = [part for part in parts if "|" in part or part.lower() in _NAMES]
    if lists:
        written = []
        for word in lists[0].lower().split("|"):
            word = word.strip()
            written.extend(relation_names(word))
        if sorted(set(written)) == sorted(operator.relations):
            operator = dataclasses.replace(operator, relations=tuple(written))
    return operator


def _argument(items, errors):
    """The node of one comma separated argument of a function"""
    types = [kind for kind, _ in items]
    values = [value for _, value in items]
    if types == ["NULL", "LPAREN", "RPAREN"]:
        return ast.Function("null", ())
    if types[0] == "QUOTE":
        # "1 day" is read as QUOTE number NAME QUOTE
        return ast.Text(f"{values[1].value} {values[2]}")
    if types in (["INT"], ["FLOAT"]):
        return ast.Number(values[0])
    if types == ["NAME"]:
        return ast.Name(values[0])
    if types == ["T_REL_OPERATOR"]:
        return _operator(values[0], errors)
    (value,) = values
    return value


def _literal(kind, value):
    if kind in _TIME_LITERALS:
        return ast.Text(value.strip("\"'"))
    if kind in {"INT", "FLOAT"}:
        return ast.Number(value)
    return value


def _call(items, errors):
    """FUNC ( arguments ) [comp_op literal]"""
    name = items[0][1].lower()
    arguments, current, depth, index = [], [], 0, 2
    while True:
        kind, value = items[index]
        index += 1
        if kind == "LPAREN":
            depth += 1
        elif kind == "RPAREN":
            if depth == 0:
                if current:
                    arguments.append(_argument(current, errors))
                break
            depth -= 1
        elif kind == "COMMA" and depth == 0:
            arguments.append(_argument(current, errors))
            current = []
            continue
        current.append((kind, value))
    relation = None
    if arguments and isinstance(arguments[0], TemporalOperator):
        relation = arguments.pop(0)
    node = ast.Function(name, tuple(arguments), relation)
    rest = items[index:]
    if rest:
        (_, symbol), (kind, value) = rest
        node = ast.Binary(symbol, node, _literal(kind, value))
    return node


def _build(p, run):
    """The generic action: the node of the production that PLY reduced

    One function serves all productions because it reads the shape of the
    right-hand side (the token types), not the name of the rule.
    """
    head = p.slice[0].type
    items = [(p.slice[i].type, p[i]) for i in range(1, len(p))]
    types = [kind for kind, _ in items]
    values = [value for _, value in items]
    if head == "statement":
        return ast.Statement(values[0].ident, values[2])
    if head == "stds":
        return ast.Name(values[0])
    if head == "number":
        return ast.Number(values[0])
    if head in _WORDS:
        return values[0]
    if len(items) == 1:
        return values[0]
    if types[0] == "LPAREN" and len(items) == 3:
        return values[1]
    if len(items) > 1 and types[1] == "LPAREN":
        return _call(items, run.errors)
    if types[1] == "L_SPAREN":
        offsets = tuple(value.value for value in values[2:-1:2])
        return ast.Index(values[0].ident, offsets)
    if len(items) == 4 and types[1] == types[2] and types[1] in {"AND", "OR"}:
        symbol = "&&" if types[1] == "AND" else "||"
        if head in _TEXT_HEADS:
            return _chain(symbol, values[0], values[3], run.text_nodes)
        return ast.Binary(symbol, values[0], values[3])
    left, (kind, middle), right = values[0], items[1], _literal(*items[2])
    if kind in _OPERATOR_TOKENS:
        operator = _operator(middle, run.errors)
        return ast.Binary(operator.symbol, left, right, operator)
    if kind in _SYMBOL_TOKENS or kind == "comp_op":
        return ast.Binary(middle, left, right)
    msg = f"No syntax tree node for {head} : {' '.join(types)}"
    raise AssertionError(msg)


def _lexer_class(kind):
    # Imported on use: the parser modules import the algebra core, which
    # imports this package.
    if kind == "vector":
        from grass.temporal.classic.temporal_vector_algebra import (
            TemporalVectorAlgebraLexer,
        )

        return TemporalVectorAlgebraLexer
    if kind == "select":
        from grass.temporal.classic.temporal_algebra import TemporalAlgebraLexer

        return TemporalAlgebraLexer
    from grass.temporal.classic.temporal_raster_base_algebra import (
        TemporalRasterAlgebraLexer,
    )

    return TemporalRasterAlgebraLexer


class ClassicGrammar:
    """Reads the classic syntax of one kind of space time dataset

    Use ``classic_grammar(kind)``; building the LALR tables takes some time,
    so one object per kind is shared. A parse is not reentrant.
    """

    def __init__(self, kind):
        self.kind = kind
        self._run = _Run()
        lexer = _lexer_class(kind)()
        lexer.build()
        self._lexer = lexer.lexer
        self.tokens = tuple(lexer.tokens)
        self._parser = yacc.yacc(
            module=self._module(self.tokens),
            debug=False,
            errorlog=yacc.NullLogger(),
        )

    def _module(self, tokens):
        """The class that PLY reads the grammar from"""
        run = self._run
        namespace = {
            "tokens": tokens,
            "precedence": classic_productions.PRECEDENCE[self.kind],
            "start": START,
        }
        for position, (name, text) in enumerate(productions(self.kind), start=1):

            def rule(p):
                p[0] = _build(p, run)

            rule.__doc__ = text
            # PLY orders the rules by line and module; the position gives the
            # order of the parser class, which decides reduce/reduce conflicts.
            rule.co_firstlineno = position
            namespace[name] = staticmethod(rule)

        def p_error(t):
            if t:
                msg = (
                    "syntax error on line %d, position %i token %s near '%s' "
                    "expression '%s'"
                    % (t.lineno, t.lexpos, t.type, t.value, run.expression)
                )
                raise SyntaxError(msg)
            msg = "Unexpected syntax error"
            raise SyntaxError(msg)

        namespace["p_error"] = staticmethod(p_error)
        return type(f"Classic{self.kind.title()}Grammar", (), namespace)

    def parse(self, text):
        """Return the syntax tree of the statement "name = expression"

        :param text: the statement
        :return: ``ast.Statement``
        :raises SyntaxError: as the parser classes raise it for the text
        """
        if self.kind != "select":
            self._reject_dataset_type_tokens(text)
        run = self._run
        run.errors.clear()
        run.expression = text
        run.text_nodes = {}
        try:
            tree = self._parser.parse(text, lexer=self._lexer.clone())
        except Exception:
            # An error of a later rule that followed an earlier reported one
            # is not the one to show.
            if not run.errors:
                raise
        if run.errors:
            raise SyntaxError(run.errors[0])
        return tree

    def _reject_dataset_type_tokens(self, text):
        """Refuse strds(), str3ds() and stvds(), as the parser classes do

        Only the base class of t.select takes the dataset type from them; the
        other algebras fix it.
        """
        scanner = self._lexer.clone()
        scanner.input(text)
        for token in iter(scanner.token, None):
            if token.type in {"STVDS", "STRDS", "STR3DS"}:
                msg = f"Syntax error near '{token.type}'"
                raise SyntaxError(msg)


@functools.cache
def classic_grammar(kind):
    """Return the shared grammar object of a kind

    :param kind: one of ``GRAMMARS``
    :return: an object with ``parse(text)``, which fits ``Profile.grammar``
    :raises ValueError: for another kind
    """
    if kind not in GRAMMARS:
        msg = f"kind is one of {', '.join(GRAMMARS)}, not {kind!r}"
        raise ValueError(msg)
    return ClassicGrammar(kind)
