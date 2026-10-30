"""Generator of random expressions in the syntax of the classic algebra

``generate(kind, seed)`` returns the expression and the parser options of one
seed; the same seed always gives the same result. ``boundary_forms(kind)``
lists fixed forms on the border between the grammar of the classic algebra and
the grammar of the core. The module is part of
``grass.temporal.testing.expressions``, which runs and compares the
expressions; see there.

This module imports no pytest.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import random
import re

from .expressions_data import (
    FAMILY,
    GRANULARITY_FAMILY,
    GRANULARITY_NAMES,
    GRANULARITY_SINGLE,
    NAMES,
    SINGLE,
)
from .reference import KINDS

TEMPORAL = (
    "equal", "during", "contains", "starts", "started", "finishes",
    "finished", "precedes", "follows", "overlaps", "overlapped",
)  # fmt: skip
T_VARS = (
    "start_doy", "start_dow", "start_year", "start_month", "start_week",
    "start_day", "start_hour", "start_minute", "start_second", "end_doy",
    "end_dow", "end_year", "end_month", "end_week", "end_day", "end_hour",
)  # fmt: skip
COMPARE = ("==", "!=", "<", "<=", ">", ">=")
MAPCALC = ("abs", "sqrt", "double", "int", "float", "log", "exp")
UNITS = ("day", "days", "hours", "hour", "month", "minutes")
# The kinds with forms of the published paper: number chains, td() on the
# left and the comparison operator for the raster kinds, the dataset
# functions in capitals for t.select. Vector expressions have none.
PAPER_KINDS = ("raster", "raster3d", "select")
DATASET_FUNCTIONS = (
    "STRDS", "STRDS", "STRDS", "STR3DS", "STVDS", "strds", "strds", "str3ds",
    "stvds",
)  # fmt: skip


class Generator:
    """Draw one expression from a random generator

    The productions follow the classic grammar (the docstrings of the ``p_``
    methods of the classic parser classes). Every binary operator is written
    with spaces, because the classic lexer reads ``A-1`` as ``A`` and the
    integer ``-1``. A few forms lie outside the classic grammar on purpose,
    so that both sides must reject them.

    A builder, one of the methods that the tables of ``expr`` list, returns the
    text of one production (``_arith`` the text of ``A + B``) and takes the
    depth that is left for its operands. The draws from ``self.rng`` are
    ``_chance`` and ``_pick`` and the choices in ``expr`` and ``_name``; the
    tables only list builders. The number and the order of the draws decide
    the expression of a seed, and the keys of the corpus hold those
    expressions, so a change to either needs a new recording of the corpus.
    """

    def __init__(self, kind, rng, *, granularity=False, paper=False):
        self.kind = kind
        self.rng = rng
        # A paper seed adds builders for the forms that the published paper
        # prints; the other seeds draw as they did before the builders were
        # written, see generate().
        self.paper = paper
        # The granularity mode refuses temporal operators and relations
        # (setup_common_granularity), so none are written, and it needs the
        # datasets of whole days.
        self.granularity = granularity
        self.family = GRANULARITY_FAMILY[kind] if granularity else FAMILY[kind]
        self.single = GRANULARITY_SINGLE[kind] if granularity else SINGLE[kind]
        names = GRANULARITY_NAMES[kind] if granularity else NAMES[kind]
        self.names = list(names)
        self.weights = list(names.values())

    def _chance(self):
        return self.rng.random()

    def _pick(self, items):
        return self.rng.choice(items)

    def _name(self):
        if self._chance() < 0.4:
            return self._pick(self.family)
        return self.rng.choices(self.names, self.weights)[0]

    def _number(self):
        draw = self._chance()
        if draw < 0.6:
            return str(self.rng.randint(0, 5))
        if draw < 0.85:
            return self._pick(("0.5", "1.5", "2.0", "10.25"))
        if draw < 0.95:
            return str(self.rng.randint(6, 100))
        # Beyond the range of a 32 bit integer
        return "3000000000"

    def _relations(self):
        count = 1 if self._chance() < 0.7 else (2 if self._chance() < 0.85 else 3)
        return "|".join(self._pick(TEMPORAL + ("over",)) for _ in range(count))

    def _operator(self, symbol, *, ref=True, agg=False):
        if self.granularity:
            return symbol
        parts = [symbol, self._relations()]
        # The classic grammar takes the aggregate before the temporal
        # reference: {&&,contains,|,r} parses, {&&,contains,r,|} does not.
        if agg and self._chance() < 0.6:
            parts.append(self._pick("|&"))
        if ref and self._chance() < 0.6:
            parts.append(self._pick("lruid"))
        return "{" + ",".join(parts) + "}"

    def _increment(self, negative_ok):
        n = self.rng.randint(1, 3)
        if negative_ok and self._chance() < 0.4:
            n = -n
        if self._chance() < 0.2:
            return str(n)
        return f'"{n} {self._pick(UNITS)}"'

    def expr(self, depth, top=False):
        """Draw an expression of at most depth levels; top forbids a leaf"""
        leaf = not top and (depth <= 0 or self._chance() < 0.25 + 0.15 * (3 - depth))
        if leaf:
            return self._leaf()
        table = {
            "vector": self._vector_table,
            "select": self._select_table,
        }.get(self.kind, self._raster_table)()
        builders, weights = zip(*table, strict=True)
        return self.rng.choices(builders, weights)[0](depth - 1)

    def _leaf(self):
        if self.paper and self.kind == "select" and self._chance() < 0.3:
            return f"{self._pick(DATASET_FUNCTIONS)}({self._name()})"
        draw = self._chance()
        if draw < 0.9:
            return self._name()
        if draw < 0.96:
            return f"tmap({self._pick(self.single)})"
        if self.kind not in {"vector", "select"}:
            return f"{self._name()}[{self._pick(('1', '-1', '2', '0'))}]"
        return self._name()

    def _raster_table(self):
        table = self._base_raster_table()
        if self.paper:
            table += [(self._number_chain, 8), (self._td_left, 6)]
        return table

    def _base_raster_table(self):
        return [
            (self._arith, 18),
            (self._t_arith, 14),
            (self._arith_number, 8),
            (self._select, 12),
            (self._if, 16),
            (self._shift, 4),
            (self._buff, 5),
            (self._snap, 3),
            (self._merge, 3),
            (self._mapcalc_fn, 3),
            (self._td_arith, 4),
            (self._time_const, 2),
            (self._paren, 3),
            (self._hash_expr, 2),
        ]

    def _vector_table(self):
        return [
            (self._overlay, 20),
            (self._t_overlay, 14),
            (self._select, 14),
            (self._if, 10),
            (self._buffer, 5),
            (self._shift, 4),
            (self._buff, 5),
            (self._snap, 3),
            (self._merge, 4),
            (self._paren, 3),
        ]

    def _select_table(self):
        """t.select: selections, retiming, merge and temporal if() only"""
        return [
            (self._select, 40),
            (self._if, 12),
            (self._shift, 8),
            (self._buff, 8),
            (self._snap, 6),
            (self._merge, 8),
            (self._paren, 3),
        ]

    def _arith(self, depth):
        return f"{self.expr(depth)} {self._pick('+-*/%')} {self.expr(depth)}"

    def _t_arith(self, depth):
        left = self.expr(depth)
        operator = self._operator(self._pick("+-*/%"))
        return f"{left} {operator} {self.expr(depth)}"

    def _arith_number(self, depth):
        op = self._pick("+-*/%")
        if self._chance() < 0.6:
            return f"{self.expr(depth)} {op} {self._number()}"
        return f"{self._number()} {op} {self.expr(depth)}"

    def _atom(self):
        """A number or a single map read with map()"""
        if self._chance() < 0.45:
            return f"map({self._pick(self.single)})"
        return self._number()

    def _number_chain(self, depth):
        """A chain of numbers and map() calls in front of a dataset

        ``1 - 2 - A``, ``2 * map(S) + A`` and ``map(S) - 1`` start with
        operands that are no dataset, which the classic grammar groups on its
        own.
        """
        operators = " ".join(
            f"{self._pick('+-*/%')} {self._atom()}"
            for _ in range(self.rng.randint(0, 2))
        )
        chain = f"{self._atom()} {operators}".strip()
        op = self._pick("+-*/%")
        if self._chance() < 0.25:
            # Only a map() has a number as its partner
            return f"map({self._pick(self.single)}) {op} {self._number()}"
        return f"{chain} {op} {self.expr(depth)}"

    def _td_left(self, depth):
        """td() as left operand of a multiplication, division or modulo"""
        draw = self._chance()
        stronger = self._pick("*/%")
        if draw < 0.35:
            return f"td({self._name()}) {stronger} {self.expr(depth)}"
        if draw < 0.7:
            return (
                f"{self.expr(depth)} {self._pick('+-')} td({self._name()}) "
                f"{stronger} {self.expr(depth)}"
            )
        return (
            f"{self.expr(depth)} {self._pick('+-*')} td({self._name()}) {stronger} "
            f"{self.expr(depth)} {self._pick('+-')} {self.expr(depth)}"
        )

    def _compare_condition(self):
        """Two datasets joined by a comparison, with or without the braces

        ``A >= F`` is the short form of ``{>=, equal, &, l}``. The granularity
        mode writes no braces.
        """
        compare = self._pick(COMPARE)
        # Datasets of equal time stamps relate often enough to give maps
        if self._chance() < 0.7:
            left, right = self._pick(self.family), self._pick(self.family)
        else:
            left, right = self._name(), self._name()
        if self._chance() < 0.35:
            return f"{left} {compare} {right}"
        return f"{left} {self._operator(compare, agg=True)} {right}"

    def _select(self, depth):
        draw = self._chance()
        if draw < 0.35:
            op = ":"
        elif draw < 0.5:
            op = "!:"
        else:
            op = self._operator(self._pick((":", ":", "!:")))
        return f"{self.expr(depth)} {op} {self.expr(depth)}"

    def _overlay(self, depth):
        return f"{self.expr(depth)} {self._pick('&|^~+')} {self.expr(depth)}"

    def _t_overlay(self, depth):
        left = self.expr(depth)
        operator = self._operator(self._pick("&|^~+"))
        return f"{left} {operator} {self.expr(depth)}"

    def _buffer(self, depth):
        function = self._pick(("buff_p", "buff_l", "buff_a"))
        return f"{function}({self.expr(depth)}, {self._pick(('1', '2', '5', '0.5'))})"

    def _shift(self, depth):
        return f"tshift({self.expr(depth)}, {self._increment(negative_ok=True)})"

    def _buff(self, depth):
        return f"buff_t({self.expr(depth)}, {self._increment(negative_ok=True)})"

    def _snap(self, depth):
        return f"tsnap({self.expr(depth)})"

    def _merge(self, depth):
        return f"merge({self.expr(depth)}, {self.expr(depth)})"

    def _mapcalc_fn(self, depth):
        return f"{self._pick(MAPCALC)}({self.expr(depth)})"

    def _td_arith(self, depth):
        draw = self._chance()
        op = self._pick("+-*/")
        if draw < 0.5:
            return f"{self.expr(depth)} {op} td({self.expr(depth)})"
        if draw < 0.75:
            left = self.expr(depth)
            operator = self._operator(self._pick("+*"))
            return f"{left} {operator} td({self.expr(depth)})"
        return f"{self.expr(depth)} {op} td({self._name()})"

    def _time_const(self, depth):
        offset = self._pick(("0", "1", "-1", "2"))
        return f"{self._pick(T_VARS)}({self._name()}, {offset})"

    def _paren(self, depth):
        return f"({self.expr(depth)})"

    def _hash_expr(self, depth):
        return f"{self.expr(depth)} {self._hash_op()} {self.expr(depth)}"

    def _hash_op(self):
        return "#" if self._chance() < 0.5 else self._operator("#")

    def _else_branch(self, depth):
        draw = self._chance()
        if self.kind in {"vector", "select"} or draw < 0.55:
            return self.expr(depth)
        if draw < 0.85:
            return self._number()
        return "null()"

    def _if(self, depth):
        relation = "{" + self._relations() + "}"
        with_relation = not self.granularity and self._chance() < 0.35
        condition = self._condition(max(depth, 0))
        head = f"if({relation}, {condition}" if with_relation else f"if({condition}"
        if self.kind not in {"vector", "select"} and self._chance() < 0.15:
            then = self._pick((self._number(), "null()"))
        else:
            then = self.expr(depth)
        if self._chance() < 0.55:
            return f"{head}, {then}, {self._else_branch(depth)})"
        return f"{head}, {then})"

    def _condition(self, depth):
        if depth > 0 and self._chance() < 0.35:
            left = self._condition(depth - 1)
            right = self._condition(depth - 1)
            draw = self._chance()
            if draw < 0.35:
                return f"{left} && {right}"
            if draw < 0.65:
                return f"{left} || {right}"
            # Every temporal reference: && and || with r give a map per
            # partner, which the comparison must reach as often as l.
            operator = self._operator(self._pick(("&&", "||")), agg=True)
            return f"{left} {operator} {right}"
        if self.paper and self.kind in {"raster", "raster3d"} and self._chance() < 0.35:
            return self._compare_condition()
        if self.kind in {"vector", "select"} or self._chance() < 0.45:
            return self._t_condition(depth)
        return self._s_condition(depth)

    def _s_condition(self, depth):
        operand = self.expr(min(depth, 1))
        draw = self._chance()
        if draw < 0.7:
            return f"{operand} {self._pick(COMPARE)} {self._number()}"
        if draw < 0.8:
            return f"isnull({operand})"
        if draw < 0.9:
            return f"isntnull({operand})"
        return f"exist({operand})"

    def _t_condition(self, depth):
        operand = self.expr(min(depth, 1)) if self._chance() < 0.4 else self._name()
        draw = self._chance()
        compare = self._pick(COMPARE)
        if draw < 0.4:
            return f"{self._pick(T_VARS)}({operand}) {compare} {self.rng.randint(0, 5)}"
        if draw < 0.65:
            return f"td({operand}) {compare} {self._pick(('1', '2', '0.5', '0'))}"
        if draw < 0.85:
            return (
                f"{self._name()} {self._hash_op()} {self._name()} "
                f"{compare} {self.rng.randint(0, 2)}"
            )
        function = self._pick(("start_date", "end_date"))
        return (
            f'{function}({self._name()}) {compare} "2001-01-0{self.rng.randint(1, 5)}"'
        )


def generate(
    kind, seed, *, depth=3, spatial_share=0.1, granularity_share=0.0, paper_share=0.25
):
    """Return the expression and the parser options of one seed

    :param kind: ``"raster"``, ``"raster3d"``, ``"vector"`` or ``"select"``
    :param seed: Non-negative whole number; the same seed always gives the
        same result, independent of the Python hash seed
    :param depth: Largest nesting depth of the expression
    :param spatial_share: Share of the seeds that run with ``spatial=True``
    :param granularity_share: Share of the seeds that run in the granularity
        mode (-g), for the kinds ``"raster"`` and ``"raster3d"``. Such a seed
        draws from other datasets and writes no temporal operators. Whether a
        seed is one is drawn from its own random stream, so a share of 0 (the
        default) leaves every other seed as it was.
    :param paper_share: Share of the seeds that also draw the forms of the
        published paper, for the kinds ``"raster"``, ``"raster3d"`` and
        ``"select"`` (see ``PAPER_KINDS``). Like the granularity mode, it is
        drawn from its own random stream and such a seed has a stream of its
        own, so every other seed gives the expression it gave before these
        forms were generated. The vector kind ignores it.
    :return: ``(expression, options)``. The expression is the right hand side
        of a statement. The options are keyword arguments for the runner:
        ``register_null`` (random for raster kinds), ``spatial`` and
        ``granularity``.
    :raises ValueError: for a granularity share above 0 with a kind that has
        no granularity mode
    """
    if kind not in NAMES:
        msg = f"kind is one of {', '.join(KINDS)}, not {kind!r}"
        raise ValueError(msg)
    granularity = False
    if granularity_share > 0:
        if kind not in GRANULARITY_NAMES:
            msg = f"The granularity mode is generated for {', '.join(GRANULARITY_NAMES)}, not {kind!r}"
            raise ValueError(msg)
        granularity = random.Random(f"gran:{kind}:{seed}").random() < granularity_share
    paper = (
        kind in PAPER_KINDS
        and random.Random(f"paper:{kind}:{seed}").random() < paper_share
    )
    stream = f"{kind}:{seed}"
    if granularity:
        stream = f"{kind}:gran:{seed}"
    if paper:
        stream = f"paper:{stream}"
    generator = Generator(
        kind, random.Random(stream), granularity=granularity, paper=paper
    )
    expression = generator.expr(generator.rng.randint(1, depth), top=True)
    rng = random.Random(f"opts:{kind}:{seed}")
    options = {}
    if kind not in {"vector", "select"}:
        options["register_null"] = rng.random() < 0.5
    if rng.random() < spatial_share:
        options["spatial"] = True
    if granularity:
        options["granularity"] = True
    return expression, options


# Forms on the border between the grammar of the classic algebra and the
# grammar of the core: syntax that one reads and the other may refuse or read
# differently (signs, spacing in increments, relations, spatial relation names
# without a temporal one, neighbour indices, precedence of && and ||, large
# integers). They were found while comparing
# the two grammars; whether a form is read or refused is the result of a run,
# not a property of the list.
_RASTER_FORMS = [
    "A-1", "A -1", "A * 1e-5", "A + (1 + 2)", "A { +, equal , l } N",
    "A { +, equal } N", "if(start_date(A) < 5, A)", 'tshift(A, "+1 day")',
    "if(start_date(A) < '2001-01-03', A)", "td(A)", "A + undefined_fn(A)",
    "A + .5", "A", "-A", "A + -1", "A ^ 2", "A ? 1 : 2", "if(A > 2, A, B, C)",
    "A[1, 1]", "A[0, 0, 1]", "A {+,l} N", "A {+,equal,x} N", "A {+,nonsense} N",
    "strds(A) + 1", "A # N", "A + (A # N)", 'if(start_date(A) < "2001-1-3", A)',
    "start_doy(A) + 1", "if(A == 1 and A == 2, A)", "A + map(L)",
    "if({equal}, A > 1, N, 0) + {during}", "A %% N", "abs(A, N)",
    'tshift(A, "1 DAY")', 'tshift(A, "1 d")', "buff_t(A, 1.5)", "tsnap(A, 1)",
    "merge(A)", "merge(A, N, D)", "A : N : D", "A :: N", "if(A, N)",
    'tshift(A, "1days")', 'tshift(A, "1  day")', 'tshift(A, " 1 day")',
    'tshift(A, "1 day ")', 'buff_t(A, "1days")', 'buff_t(A, " 1 day")',
    "A {+,equal|equal} N", "A {+,EQUAL} N", "A {+,Equal,L} N",
    "if(A > 1 || A < 3 && A > 2, A)", "A + 3000000000", "A {+,over} D",
    "if({over}, A > 1, D)", "start_doy(A, -1) + A", "A {#,equal} N + 1",
    "if(A {#,during} B == 1, A)", "if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)",
    "if(isnull(A) || A > 2 && A < 4, A, 0)", "A {+,equal,l} N {*,equal,r} D",
    "A {+,equivalent,l} N", "if(A {#,in} N > 0, A)",
]  # fmt: skip
_VECTOR_FORMS = [
    "aa && ab", "aa * ab", "aa - ab", "ev", "aa", "aa + 1", "aa & 1",
    "buff_p(aa)", "buff_p(aa, -1)", "aa {&, equal} ab", "if(aa > 1, aa)",
    "aa # ab", "td(aa) + aa", "strds(aa)", "stvds(aa) & ab",
    'tshift(aa, "1days")', "aa {&,equal|equal} ab", "aa {&,over} wide",
    "aa + ab & ac", "aa | ab & ac", "aa ~ aa", 'buff_t(aa, " 1 day")',
    "aa {&,equivalent,l} ab", "buff_p(aa {:,equivalent} ab, 1)",
]  # fmt: skip
_SELECT_FORMS = [
    "A", "A : N : D", "A :: N", 'tshift(A, "+1 day")', "A {:,equal,x} N",
    'tshift(A, "1days")', "A {:,equal|equal} N", "A {:,over} D",
    'buff_t(A, " 1 day")', "A {:,equivalent} N",
]  # fmt: skip


def boundary_forms(kind):
    """Return the fixed forms on the border of the two grammars for a kind

    The names in the forms are those of the datasets of ``expressions_data``.
    Compare the outcome of two runners on each form like on a generated one:
    a classic profile must answer as the classic algebra does, whether it
    reads the form or refuses it.
    """
    if kind == "raster":
        return list(_RASTER_FORMS)
    if kind == "raster3d":
        # The datasets of the 3D kind have no N
        return [re.sub(r"\bN\b", "B", form) for form in _RASTER_FORMS]
    if kind == "vector":
        return list(_VECTOR_FORMS)
    if kind == "select":
        return list(_SELECT_FORMS)
    msg = f"kind is one of {', '.join(KINDS)}, not {kind!r}"
    raise ValueError(msg)
