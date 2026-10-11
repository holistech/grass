"""@package grass.temporal

Temporal operator evaluation with PLY

SPDX-FileCopyrightText: 2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Thomas Leppelt and Soeren Gebbert

.. code-block:: pycon

    >>> p = TemporalOperatorParser()
    >>> expression = "{equal|equivalent|cover|in|meet|contain|overlap}"
    >>> p.parse(expression, optype="relation")
    >>> print((p.relations, p.temporal, p.function))
    (['equal', 'equivalent', 'cover', 'in', 'meet', 'contain', 'overlap'], None, None)

    >>> p = TemporalOperatorParser()
    >>> expression = "{equal| during}"
    >>> p.parse(expression, optype="relation")
    >>> print((p.relations, p.temporal, p.function))
    (['equal', 'during'], None, None)
    >>> p = TemporalOperatorParser()
    >>> expression = "{contains | starts}"
    >>> p.parse(expression)
    >>> print((p.relations, p.temporal, p.function))
    (['contains', 'starts'], None, None)
    >>> p = TemporalOperatorParser()
    >>> expression = "{&&, during}"
    >>> p.parse(expression, optype="boolean")
    >>> print((p.relations, p.temporal, p.function, p.aggregate))
    (['during'], 'l', '&&', '&')
    >>> p = TemporalOperatorParser()
    >>> expression = "{||, equal | during}"
    >>> p.parse(expression, optype="boolean")
    >>> print((p.relations, p.temporal, p.function, p.aggregate))
    (['equal', 'during'], 'l', '||', '|')
    >>> p = TemporalOperatorParser()
    >>> expression = "{||, equal | during, &}"
    >>> p.parse(expression, optype="boolean")
    >>> print((p.relations, p.temporal, p.function, p.aggregate))
    (['equal', 'during'], 'l', '||', '&')
    >>> p = TemporalOperatorParser()
    >>> expression = "{&&, during, |}"
    >>> p.parse(expression, optype="boolean")
    >>> print((p.relations, p.temporal, p.function, p.aggregate))
    (['during'], 'l', '&&', '|')
    >>> p = TemporalOperatorParser()
    >>> expression = "{&&, during, |, r}"
    >>> p.parse(expression, optype="boolean")
    >>> print((p.relations, p.temporal, p.function, p.aggregate))
    (['during'], 'r', '&&', '|')
    >>> p = TemporalOperatorParser()
    >>> expression = "{&&, during, u}"
    >>> p.parse(expression, optype="boolean")
    >>> print((p.relations, p.temporal, p.function, p.aggregate))
    (['during'], 'u', '&&', '&')
    >>> p = TemporalOperatorParser()
    >>> expression = "{:, during, r}"
    >>> p.parse(expression, optype="select")
    >>> print((p.relations, p.temporal, p.function))
    (['during'], 'r', ':')
    >>> p = TemporalOperatorParser()
    >>> expression = "{!:, equal | contains, d}"
    >>> p.parse(expression, optype="select")
    >>> print((p.relations, p.temporal, p.function))
    (['equal', 'contains'], 'd', '!:')
    >>> p = TemporalOperatorParser()
    >>> expression = "{#, during, r}"
    >>> p.parse(expression, optype="hash")
    >>> print((p.relations, p.temporal, p.function))
    (['during'], 'r', '#')
    >>> p = TemporalOperatorParser()
    >>> expression = "{#, equal | contains}"
    >>> p.parse(expression, optype="hash")
    >>> print((p.relations, p.temporal, p.function))
    (['equal', 'contains'], 'l', '#')
    >>> p = TemporalOperatorParser()
    >>> expression = "{+, during, r}"
    >>> p.parse(expression, optype="raster")
    >>> print((p.relations, p.temporal, p.function))
    (['during'], 'r', '+')
    >>> p = TemporalOperatorParser()
    >>> expression = "{/, equal | contains}"
    >>> p.parse(expression, optype="raster")
    >>> print((p.relations, p.temporal, p.function))
    (['equal', 'contains'], 'l', '/')
    >>> p = TemporalOperatorParser()
    >>> expression = "{+, equal | contains,intersect}"
    >>> p.parse(expression, optype="raster")
    >>> print((p.relations, p.temporal, p.function))
    (['equal', 'contains'], 'i', '+')
    >>> p = TemporalOperatorParser()
    >>> expression = "{*, contains,disjoint}"
    >>> p.parse(expression, optype="raster")
    >>> print((p.relations, p.temporal, p.function))
    (['contains'], 'd', '*')
    >>> p = TemporalOperatorParser()
    >>> expression = "{~, equal,left}"
    >>> p.parse(expression, optype="overlay")
    >>> print((p.relations, p.temporal, p.function))
    (['equal'], 'l', '~')
    >>> p = TemporalOperatorParser()
    >>> expression = "{^, over,right}"
    >>> p.parse(expression, optype="overlay")
    >>> print((p.relations, p.temporal, p.function))
    (['overlaps', 'overlapped'], 'r', '^')
    >>> p = TemporalOperatorParser()
    >>> expression = "{&&, equal | during | contains | starts, &}"
    >>> p.parse(expression, optype="boolean")
    >>> print((p.relations, p.temporal, p.function, p.aggregate))
    (['equal', 'during', 'contains', 'starts'], 'l', '&&', '&')
    >>> p = TemporalOperatorParser()
    >>> expression = "{&&, equal | during | contains | starts, &&&&&}"
    >>> p.parse(expression, optype="boolean")
    Traceback (most recent call last):
    SyntaxError: Unexpected syntax error in expression "{&&, equal | during | contains | starts, &&&&&}" at position 42 near &
    >>> p = TemporalOperatorParser()
    >>> expression = "{+, starting}"
    >>> p.parse(expression)
    Traceback (most recent call last):
    SyntaxError: syntax error on line 1 position 4 near 'starting'
    >>> p = TemporalOperatorParser()
    >>> expression = "{nope, start, |, l}"
    >>> p.parse(expression)
    Traceback (most recent call last):
    SyntaxError: syntax error on line 1 position 1 near 'nope'
    >>> p = TemporalOperatorParser()
    >>> expression = "{++, start, |, l}"
    >>> p.parse(expression)
    Traceback (most recent call last):
    SyntaxError: Unexpected syntax error in expression "{++, start, |, l}" at position 2 near +
    >>> p = TemporalOperatorParser()
    >>> p.parse("{:}", optype="select")
    >>> print((p.relations, p.temporal, p.function))
    (['equal'], 'l', ':')
    >>> p = TemporalOperatorParser()
    >>> p.parse("{+}", optype="overlay")
    >>> print((p.relations, p.temporal, p.function))
    (['equal'], 'l', '+')
    >>> p = TemporalOperatorParser()
    >>> p.parse("{:}", optype="raster")
    Traceback (most recent call last):
    SyntaxError: Wrong optype "raster" for the operator "{:}", it is a select operator
    >>> p = TemporalOperatorParser()
    >>> p.parse("{:, during", optype="select")
    Traceback (most recent call last):
    SyntaxError: Unexpected end of the operator expression
    >>> p = TemporalOperatorParser()
    >>> expression = "{^, over, right}"
    >>> p.parse(expression, optype="rter")
    Traceback (most recent call last):
    SyntaxError: Unknown optype rter, must be one of ['select', 'boolean', 'raster', 'hash', 'relation', 'overlay']

"""  # noqa: E501

from typing import NamedTuple

from .ply import lex, yacc


class _Operator(NamedTuple):
    """Result of the grammar: the parsed components and the optypes that allow them"""

    optypes: set
    relations: list
    temporal: str
    function: str
    aggregate: str


# The operator symbols and the optypes they are valid for. "+" is both an
# arithmetic and an overlay operator, so the grammar cannot tell them apart.
_SYMBOL_OPTYPES = {
    ":": {"select"},
    "!:": {"select"},
    "#": {"hash"},
    "%": {"raster"},
    "/": {"raster"},
    "*": {"raster"},
    "-": {"raster"},
    "+": {"raster", "overlay"},
    "&": {"overlay"},
    "|": {"overlay"},
    "^": {"overlay"},
    "~": {"overlay"},
}

# Temporal reference words and the token they produce. The token value is the
# first letter of the word.
_TEMPORAL_WORDS = {
    "l": "LEFTREF",
    "left": "LEFTREF",
    "r": "RIGHTREF",
    "right": "RIGHTREF",
    "u": "UNION",
    "union": "UNION",
    "d": "DISJOINT",
    "disjoint": "DISJOINT",
    "i": "INTERSECT",
    "intersect": "INTERSECT",
}

# Relation of the operators without an explicit relation, e.g. {:} or {+}
_DEFAULT_RELATIONS = ["equal"]


class TemporalOperatorLexer:
    """Lexical analyzer for the GRASS temporal operator"""

    # Functions that defines topological relations.
    relations = {
        # temporal relations
        "equal": "EQUAL",
        "follows": "FOLLOWS",
        "precedes": "PRECEDES",
        "overlaps": "OVERLAPS",
        "overlapped": "OVERLAPPED",
        "during": "DURING",
        "starts": "STARTS",
        "finishes": "FINISHES",
        "contains": "CONTAINS",
        "started": "STARTED",
        "finished": "FINISHED",
        "over": "OVER",
        # spatial relations
        "equivalent": "EQUIVALENT",
        "cover": "COVER",
        "overlap": "OVERLAP",
        "in": "IN",
        "contain": "CONTAIN",
        "meet": "MEET",
    }

    # This is the list of token names.
    tokens = (
        "COMMA",
        "LEFTREF",
        "RIGHTREF",
        "UNION",
        "DISJOINT",
        "INTERSECT",
        "HASH",
        "OR",
        "AND",
        "XOR",
        "NOT",
        "MOD",
        "DIV",
        "MULT",
        "ADD",
        "SUB",
        "T_SELECT",
        "T_NOT_SELECT",
        "CLPAREN",
        "CRPAREN",
    )

    # Build the token list
    tokens += tuple(relations.values())

    # Regular expression rules for simple tokens. The temporal reference
    # tokens (LEFTREF etc.) are produced by t_NAME: a pattern like "[l|left]"
    # for them would be a character class and also match a leading "|".
    t_T_SELECT = r":"
    t_T_NOT_SELECT = r"!:"
    t_COMMA = r","
    t_HASH = r"\#"
    t_OR = r"[\|]"
    t_AND = r"[&]"
    t_XOR = r"\^"
    t_NOT = r"\~"
    t_MOD = r"[\%]"
    t_DIV = r"[\/]"
    t_MULT = r"[\*]"
    t_ADD = r"[\+]"
    t_SUB = r"[-]"
    t_CLPAREN = r"\{"
    t_CRPAREN = r"\}"

    # These are the things that should be ignored.
    t_ignore = " \t\n"

    def t_NAME(self, t):
        r"[a-zA-Z_][a-zA-Z_0-9]*"
        return self.temporal_symbol(t)

    # Parse symbols
    def temporal_symbol(self, t):
        """Turn a word into the token of a relation or a temporal reference"""
        if t.value in TemporalOperatorLexer.relations:
            t.type = TemporalOperatorLexer.relations[t.value]
        elif t.value in _TEMPORAL_WORDS:
            t.type = _TEMPORAL_WORDS[t.value]
            t.value = t.value[0]
        else:
            self.t_error(t)
        return t

    # Handle errors.
    def t_error(self, t):
        raise SyntaxError(
            "syntax error on line %d position %i near '%s'"
            % (t.lineno, t.lexpos, t.value)
        )

    # Build the lexer
    def build(self, **kwargs) -> None:
        self.lexer = lex.lex(module=self, debug=0, **kwargs)


###############################################################################


def _as_list(value):
    """Return value as a list, a list stays as it is"""
    return value if isinstance(value, list) else [value]


class TemporalOperatorParser:
    """The temporal operator class

    The grammar rules are static methods that depend only on their arguments,
    so the LALR tables are built once for the class and shared by all
    instances. Everything that depends on the optype is checked in
    :meth:`parse`, because PLY swallows any ``SyntaxError`` raised inside a
    grammar rule.
    """

    # The LALR parser, built on first use
    _yacc_parser = None

    def __init__(self) -> None:
        self.lexer = TemporalOperatorLexer()
        self.lexer.build()
        if TemporalOperatorParser._yacc_parser is None:
            TemporalOperatorParser._yacc_parser = yacc.yacc(
                module=TemporalOperatorParser, debug=False
            )
        self.parser = TemporalOperatorParser._yacc_parser
        self.relations = None  # Temporal relations (equals, contain, during, ...)
        self.temporal = None  # Temporal operation (intersect, left, right, ...)
        self.function = None  # Actual operation (+, -, /, *, ... )
        self.aggregate = None  # Aggregation function (|, &)

        self.optype_list = [
            "select",
            "boolean",
            "raster",
            "hash",
            "relation",
            "overlay",
        ]

    def parse(self, expression, optype="relation"):
        """Parse the expression and fill the object variables

        :param expression:
        :param optype: The parameter optype can be
            of type:

            - select   { :, during,   r}
            - boolean  {&&, contains, \\|}
            - raster   { \\*, equal,    \\|}
            - overlay  { \\|, starts,   &}
            - hash     { #, during,   l}
            - relation {during}

        :raises SyntaxError: If the expression is not a valid operator or the
            operator does not belong to optype
        """
        if optype not in self.optype_list:
            raise SyntaxError(
                "Unknown optype %s, must be one of %s" % (optype, str(self.optype_list))
            )
        self.optype = optype
        self.expression = expression
        self.relations = None
        self.temporal = None
        self.function = None
        self.aggregate = None

        operator = self.parser.parse(expression, lexer=self.lexer.lexer)

        if optype not in operator.optypes:
            raise SyntaxError(
                'Wrong optype "%s" for the operator "%s", it is a %s operator'
                % (optype, expression, " or ".join(sorted(operator.optypes)))
            )
        self.relations = operator.relations
        self.temporal = operator.temporal
        self.function = operator.function
        self.aggregate = operator.aggregate

    # Get the tokens from the lexer class
    tokens = TemporalOperatorLexer.tokens

    # Error rule for syntax errors.
    @staticmethod
    def p_error(t):
        if t is None:
            message = "Unexpected end of the operator expression"
            raise SyntaxError(message)
        raise SyntaxError(
            "Unexpected syntax error in expression"
            ' "%s" at position %i near %s' % (t.lexer.lexdata, t.lexpos, t.value)
        )

    @staticmethod
    def p_relation_operator(t):
        # {during}
        # {during | equal | starts}
        """
        operator : CLPAREN relations CRPAREN
        """
        t[0] = _Operator({"relation"}, t[2], None, None, None)

    @staticmethod
    def p_symbol_operator(t):
        # {:}
        # {!:, during}
        # {+, during | equal | starts}
        # {#, during | equal | starts, l}
        # {^, during, left}
        """
        operator : CLPAREN symbol CRPAREN
                 | CLPAREN symbol COMMA relations CRPAREN
                 | CLPAREN symbol COMMA relations COMMA temporal CRPAREN
        """
        relations = t[4] if len(t) > 4 else _DEFAULT_RELATIONS
        temporal = t[6] if len(t) > 6 else "l"
        t[0] = _Operator(_SYMBOL_OPTYPES[t[2]], relations, temporal, t[2], None)

    @staticmethod
    def p_boolean_operator(t):
        # {||, during}
        # {&&, during | equal | starts, |}
        # {||, during, left}
        # {&&, during | equal | starts, &, union}
        """
        operator : CLPAREN boolean COMMA relations booleanoptions CRPAREN
        """
        aggregate, temporal = t[5]
        t[0] = _Operator({"boolean"}, t[4], temporal or "l", t[2], aggregate or t[2][0])

    @staticmethod
    def p_boolean_options(t):
        # Aggregation operator and temporal operator are both optional
        """
        booleanoptions :
                       | COMMA aggregate
                       | COMMA temporal
                       | COMMA aggregate COMMA temporal
        """
        aggregate = temporal = None
        for index in range(2, len(t), 2):
            if t.slice[index].type == "aggregate":
                aggregate = t[index]
            else:
                temporal = t[index]
        t[0] = (aggregate, temporal)

    @staticmethod
    def p_boolean(t):
        """
        boolean : OR  OR
                | AND AND
        """
        t[0] = t[1] + t[2]

    @staticmethod
    def p_aggregate(t):
        """
        aggregate : OR
                  | AND
        """
        t[0] = t[1]

    @staticmethod
    def p_relation(t) -> None:
        # The list of relations. Temporal and spatial relations are supported
        """
        relation : EQUAL
                 | FOLLOWS
                 | PRECEDES
                 | OVERLAPS
                 | OVERLAPPED
                 | DURING
                 | STARTS
                 | FINISHES
                 | CONTAINS
                 | STARTED
                 | FINISHED
                 | EQUIVALENT
                 | COVER
                 | OVERLAP
                 | IN
                 | CONTAIN
                 | MEET
        """
        t[0] = t[1]

    @staticmethod
    def p_over(t) -> None:
        # The over keyword
        """
        relation : OVER
        """
        t[0] = ["overlaps", "overlapped"]

    @staticmethod
    def p_relationlist(t) -> None:
        # The list of relations.
        """
        relationlist : relation OR relation
                     | relation OR relationlist
        """
        t[0] = _as_list(t[1]) + _as_list(t[3])

    @staticmethod
    def p_relations(t) -> None:
        # One relation or a list of them, always as a list.
        """
        relations : relation
                  | relationlist
        """
        t[0] = _as_list(t[1])

    @staticmethod
    def p_temporal_operator(t) -> None:
        # The temporal operator of the result extent
        """
        temporal : LEFTREF
                 | RIGHTREF
                 | UNION
                 | DISJOINT
                 | INTERSECT
        """
        t[0] = t[1]

    @staticmethod
    def p_symbol(t) -> None:
        # The select, hash, arithmetic and overlay operators
        """
        symbol : T_SELECT
               | T_NOT_SELECT
               | HASH
               | MOD
               | DIV
               | MULT
               | ADD
               | SUB
               | AND
               | OR
               | XOR
               | NOT
        """
        t[0] = t[1]


###############################################################################

if __name__ == "__main__":
    import doctest

    doctest.testmod()
