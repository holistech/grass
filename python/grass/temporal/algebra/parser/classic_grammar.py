"""The grammar of the classic temporal algebra, building syntax trees of the core

The classic algebra reads ``name = expression`` with the productions of the
parser classes in ``temporal_algebra``, ``temporal_raster_base_algebra``,
``temporal_raster_algebra``, ``temporal_raster3d_algebra`` and
``temporal_vector_algebra``. This module holds a frozen copy of those
productions and of the precedence tables as data, and one generic action that
turns every production into nodes of ``grass.temporal.algebra.parser.ast``.
What the classic grammar reads, what it rejects and how it groups therefore
stays as it was, while the meaning is given by a translator of the core.

The copy is frozen because the parser classes are going to be removed; the
grammar must not depend on their ``p_`` methods then. The lexers are still
those of the parser modules and move here together with them. As long as the
parser classes exist, a test compares every production text, the precedence
and the tokens with the copy, so that a change of one of them is noticed.

The PLY version of the package builds its tables in memory and writes nothing
next to the source; debug=False also keeps it from writing a parser.out.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import dataclasses
import functools

from grass.temporal.algebra.parser import ast
from grass.temporal.algebra.parser.operators import (
    TemporalOperator,
    parse_operator,
    relation_names,
)
from grass.temporal.algebra.relations import SPATIAL_RELATIONS, TEMPORAL_RELATIONS
from grass.temporal.ply import yacc

KINDS = ("raster", "raster3d", "vector", "select")

# The productions of every p_ method of the parser classes, by method name.
# A name that two classes share has the same text in both.
_TEXTS = {
    "p_statement_assign": """
        statement : stds EQUALS expr
    """,
    "p_stds_1": """
        stds : NAME
    """,
    "p_paren_expr": """
        expr : LPAREN expr RPAREN
    """,
    "p_number": """
        number : INT
                | FLOAT
    """,
    "p_expr_strds_function": """
        expr : STRDS LPAREN stds RPAREN
    """,
    "p_expr_str3ds_function": """
        expr : STR3DS LPAREN stds RPAREN
    """,
    "p_expr_stvds_function": """
        expr : STVDS LPAREN stds RPAREN
    """,
    "p_expr_tmap_function": """
        expr : TMAP LPAREN stds RPAREN
    """,
    "p_expr_tmerge_function": """
        expr : MERGE LPAREN stds COMMA stds RPAREN
             | MERGE LPAREN expr COMMA stds RPAREN
             | MERGE LPAREN stds COMMA expr RPAREN
             | MERGE LPAREN expr COMMA expr RPAREN
    """,
    "p_t_hash": """
        t_hash_var : stds HASH stds
                   | expr HASH stds
                   | stds HASH expr
                   | expr HASH expr
    """,
    "p_t_hash2": """
        t_hash_var : stds T_HASH_OPERATOR stds
                   | stds T_HASH_OPERATOR expr
                   | expr T_HASH_OPERATOR stds
                   | expr T_HASH_OPERATOR expr
    """,
    "p_t_hash_paren": """
        t_hash_var : LPAREN t_hash_var RPAREN
    """,
    "p_t_td_var": """
        t_td_var : TD LPAREN stds RPAREN
                 | TD LPAREN expr RPAREN
    """,
    "p_t_time_var": """
        t_var : START_DOY
              | START_DOW
              | START_YEAR
              | START_MONTH
              | START_WEEK
              | START_DAY
              | START_HOUR
              | START_MINUTE
              | START_SECOND
              | END_DOY
              | END_DOW
              | END_YEAR
              | END_MONTH
              | END_WEEK
              | END_DAY
              | END_HOUR
              | END_MINUTE
              | END_SECOND
    """,
    "p_compare_op": """
        comp_op : CEQUALS
                | UNEQUALS
                | LOWER
                | LOWER_EQUALS
                | GREATER
                | GREATER_EQUALS
    """,
    "p_t_var_expr_td_hash": """
        t_var_expr : t_td_var   comp_op number
                   | t_hash_var comp_op number
    """,
    "p_t_var_expr_number": """
        t_var_expr : t_var LPAREN stds RPAREN comp_op number
                   | t_var LPAREN expr RPAREN comp_op number
    """,
    "p_t_var_expr_time": """
        t_var_expr : START_TIME     LPAREN stds RPAREN comp_op TIME
                   | START_DATE     LPAREN stds RPAREN comp_op DATE
                   | START_DATETIME LPAREN stds RPAREN comp_op DATETIME
                   | END_TIME       LPAREN stds RPAREN comp_op TIME
                   | END_DATE       LPAREN stds RPAREN comp_op DATE
                   | END_DATETIME   LPAREN stds RPAREN comp_op DATETIME
                   | START_TIME     LPAREN expr RPAREN comp_op TIME
                   | START_DATE     LPAREN expr RPAREN comp_op DATE
                   | START_DATETIME LPAREN expr RPAREN comp_op DATETIME
                   | END_TIME       LPAREN expr RPAREN comp_op TIME
                   | END_DATE       LPAREN expr RPAREN comp_op DATE
                   | END_DATETIME   LPAREN expr RPAREN comp_op DATETIME
    """,
    "p_t_var_expr_comp": """
        t_var_expr : t_var_expr AND AND t_var_expr
                   | t_var_expr OR OR t_var_expr
    """,
    "p_t_var_expr_comp_op": """
        t_var_expr : t_var_expr T_COMP_OPERATOR t_var_expr
    """,
    "p_expr_t_select": """
        expr : stds T_SELECT stds
             | expr T_SELECT stds
             | stds T_SELECT expr
             | expr T_SELECT expr
    """,
    "p_expr_t_not_select": """
        expr : stds T_NOT_SELECT stds
             | expr T_NOT_SELECT stds
             | stds T_NOT_SELECT expr
             | expr T_NOT_SELECT expr
    """,
    "p_expr_t_select_operator": """
        expr : stds T_SELECT_OPERATOR stds
             | expr T_SELECT_OPERATOR stds
             | stds T_SELECT_OPERATOR expr
             | expr T_SELECT_OPERATOR expr
    """,
    "p_expr_condition_if": """
        expr : IF LPAREN t_var_expr COMMA stds RPAREN
             | IF LPAREN t_var_expr COMMA expr RPAREN
    """,
    "p_expr_condition_if_relation": """
        expr : IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA expr RPAREN
    """,
    "p_expr_condition_elif": """
        expr : IF LPAREN t_var_expr COMMA stds COMMA stds RPAREN
             | IF LPAREN t_var_expr COMMA stds COMMA expr RPAREN
             | IF LPAREN t_var_expr COMMA expr COMMA stds RPAREN
             | IF LPAREN t_var_expr COMMA expr COMMA expr RPAREN
    """,
    "p_expr_condition_elif_relation": """
        expr : IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA stds COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA stds COMMA expr RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA expr COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA expr COMMA expr RPAREN
    """,
    "p_expr_t_buff": """
        expr : BUFF_T LPAREN stds COMMA QUOTE  number NAME QUOTE RPAREN
             | BUFF_T LPAREN expr COMMA QUOTE  number NAME QUOTE RPAREN
             | BUFF_T LPAREN stds COMMA number RPAREN
             | BUFF_T LPAREN expr COMMA number RPAREN
    """,
    "p_expr_t_snap": """
        expr : TSNAP LPAREN stds RPAREN
             | TSNAP LPAREN expr RPAREN
    """,
    "p_expr_t_shift": """
        expr : TSHIFT LPAREN stds COMMA QUOTE  number NAME QUOTE RPAREN
             | TSHIFT LPAREN expr COMMA QUOTE  number NAME QUOTE RPAREN
             | TSHIFT LPAREN stds COMMA number RPAREN
             | TSHIFT LPAREN expr COMMA number RPAREN
    """,
    "p_expr_time_const": """
        expr : t_var LPAREN NAME COMMA INT RPAREN
    """,
    "p_ts_neighbour_operation": """
        expr : stds L_SPAREN number COMMA number R_SPAREN
             | stds L_SPAREN number R_SPAREN
             | stds L_SPAREN number COMMA number COMMA number R_SPAREN
    """,
    "p_expr_spmap_function": """
        mapexpr : MAP LPAREN stds RPAREN
    """,
    "p_arith1_operation": """
        expr : stds MOD  stds
             | expr MOD  stds
             | stds MOD  expr
             | expr MOD  expr
             | stds DIV  stds
             | expr DIV  stds
             | stds DIV  expr
             | expr DIV  expr
             | stds MULT stds
             | expr MULT stds
             | stds MULT expr
             | expr MULT expr
             | stds MOD  t_td_var
             | expr MOD  t_td_var
             | stds DIV  t_td_var
             | expr DIV  t_td_var
             | stds MULT t_td_var
             | expr MULT t_td_var
    """,
    "p_arith1_operation_numeric1": """
        expr : stds MOD  number
             | expr MOD  number
             | stds DIV  number
             | expr DIV  number
             | stds MULT number
             | expr MULT number
             | stds MOD  numberstr
             | expr MOD  numberstr
             | stds DIV  numberstr
             | expr DIV  numberstr
             | stds MULT numberstr
             | expr MULT numberstr
             | stds MOD  mapexpr
             | expr MOD  mapexpr
             | stds DIV  mapexpr
             | expr DIV  mapexpr
             | stds MULT mapexpr
             | expr MULT mapexpr
    """,
    "p_arith1_operation_numeric2": """
        expr : number    MOD  stds
             | number    MOD  expr
             | number    DIV  stds
             | number    DIV  expr
             | number    MULT stds
             | number    MULT expr
             | numberstr MOD  stds
             | numberstr MOD  expr
             | numberstr DIV  stds
             | numberstr DIV  expr
             | numberstr MULT stds
             | numberstr MULT expr
             | mapexpr   MOD  stds
             | mapexpr   MOD  expr
             | mapexpr   DIV  stds
             | mapexpr   DIV  expr
             | mapexpr   MULT stds
             | mapexpr   MULT expr
    """,
    "p_arith2_operation": """
        expr : stds ADD stds
             | expr ADD stds
             | stds ADD expr
             | expr ADD expr
             | stds SUB stds
             | expr SUB stds
             | stds SUB expr
             | expr SUB expr
             | stds ADD t_td_var
             | expr ADD t_td_var
             | expr SUB t_td_var
             | stds SUB t_td_var
    """,
    "p_arith2_operation_numeric1": """
        expr : stds ADD number
             | expr ADD number
             | stds SUB number
             | expr SUB number
             | stds ADD numberstr
             | expr ADD numberstr
             | stds SUB numberstr
             | expr SUB numberstr
             | stds ADD mapexpr
             | expr ADD mapexpr
             | stds SUB mapexpr
             | expr SUB mapexpr
    """,
    "p_arith2_operation_numeric2": """
        expr : number    ADD stds
             | number    ADD expr
             | number    SUB stds
             | number    SUB expr
             | numberstr ADD stds
             | numberstr ADD expr
             | numberstr SUB stds
             | numberstr SUB expr
             | mapexpr   ADD stds
             | mapexpr   ADD expr
             | mapexpr   SUB stds
             | mapexpr   SUB expr
    """,
    "p_arith1_operation_relation": """
        expr : stds T_ARITH1_OPERATOR stds
             | expr T_ARITH1_OPERATOR stds
             | stds T_ARITH1_OPERATOR expr
             | expr T_ARITH1_OPERATOR expr
             | stds T_ARITH1_OPERATOR t_td_var
             | expr T_ARITH1_OPERATOR t_td_var
    """,
    "p_arith2_operation_relation": """
        expr : stds T_ARITH2_OPERATOR stds
             | expr T_ARITH2_OPERATOR stds
             | stds T_ARITH2_OPERATOR expr
             | expr T_ARITH2_OPERATOR expr
             | stds T_ARITH2_OPERATOR t_td_var
             | expr T_ARITH2_OPERATOR t_td_var
    """,
    "p_arith_operation_numeric_string": """
        numberstr : number ADD number
                  | number SUB number
                  | number DIV number
                  | number MULT number
                  | number MOD number
    """,
    "p_mapcalc_function": """
        mapcalc_arith : ABS
                      | LOG
                      | SQRT
                      | EXP
                      | COS
                      | ACOS
                      | SIN
                      | ASIN
                      | TAN
                      | DOUBLE
                      | FLOATEXP
                      | INTEXP
    """,
    "p_mapcalc_operation1": """
        expr : mapcalc_arith LPAREN stds RPAREN
             | mapcalc_arith LPAREN expr RPAREN
    """,
    "p_mapexpr_operation": """
        mapexpr : mapcalc_arith LPAREN mapexpr RPAREN
    """,
    "p_s_var_expr_1": """
        s_var_expr : ISNULL LPAREN stds RPAREN
                   | ISNULL LPAREN expr RPAREN
    """,
    "p_s_var_expr_2": """
        s_var_expr : ISNTNULL LPAREN stds RPAREN
                   | ISNTNULL LPAREN expr RPAREN
    """,
    "p_s_var_expr_3": """
        s_var_expr : stds comp_op number
                   | expr comp_op number
    """,
    "p_s_var_expr_4": """
        s_var_expr : EXIST LPAREN stds RPAREN
                   | EXIST LPAREN expr RPAREN
    """,
    "p_s_var_expr_comp": """
        s_var_expr : s_var_expr AND AND s_var_expr
                   | s_var_expr OR  OR  s_var_expr
    """,
    "p_s_var_expr_comp_op": """
        s_var_expr : s_var_expr T_COMP_OPERATOR s_var_expr
    """,
    "p_s_expr_condition_if": """
        expr : IF LPAREN s_var_expr  COMMA stds RPAREN
             | IF LPAREN s_var_expr  COMMA expr RPAREN
             | IF LPAREN ts_var_expr COMMA stds RPAREN
             | IF LPAREN ts_var_expr COMMA expr RPAREN
    """,
    "p_s_numeric_condition_if": """
        expr : IF LPAREN s_var_expr  COMMA number RPAREN
             | IF LPAREN s_var_expr  COMMA NULL   LPAREN RPAREN RPAREN
             | IF LPAREN ts_var_expr COMMA number RPAREN
             | IF LPAREN ts_var_expr COMMA NULL   LPAREN RPAREN RPAREN
    """,
    "p_t_numeric_else_condition_if": """
        expr : IF LPAREN t_var_expr COMMA stds COMMA number RPAREN
             | IF LPAREN t_var_expr COMMA stds COMMA NULL LPAREN RPAREN RPAREN
             | IF LPAREN t_var_expr COMMA expr COMMA number RPAREN
             | IF LPAREN t_var_expr COMMA expr COMMA NULL LPAREN RPAREN RPAREN
    """,
    "p_t_numeric_else_condition_if_relation": """
        expr : IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA stds COMMA number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA stds COMMA NULL LPAREN RPAREN RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA expr COMMA number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA expr COMMA NULL LPAREN RPAREN RPAREN
    """,
    "p_s_expr_condition_if_relation": """
        expr : IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA expr RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA expr RPAREN
    """,
    "p_s_expr_condition_elif": """
        expr : IF LPAREN s_var_expr  COMMA stds COMMA stds RPAREN
             | IF LPAREN s_var_expr  COMMA stds COMMA expr RPAREN
             | IF LPAREN s_var_expr  COMMA expr COMMA stds RPAREN
             | IF LPAREN s_var_expr  COMMA expr COMMA expr RPAREN
             | IF LPAREN ts_var_expr COMMA stds COMMA stds RPAREN
             | IF LPAREN ts_var_expr COMMA stds COMMA expr RPAREN
             | IF LPAREN ts_var_expr COMMA expr COMMA stds RPAREN
             | IF LPAREN ts_var_expr COMMA expr COMMA expr RPAREN
    """,
    "p_s_numeric_condition_elif": """
        expr : IF LPAREN s_var_expr  COMMA number COMMA  number RPAREN
             | IF LPAREN s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  number RPAREN
             | IF LPAREN s_var_expr  COMMA number COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN ts_var_expr COMMA number COMMA  number RPAREN
             | IF LPAREN ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  number RPAREN
             | IF LPAREN ts_var_expr COMMA number COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  NULL   LPAREN RPAREN RPAREN
    """,
    "p_s_numeric_expr_condition_elif": """
        expr : IF LPAREN s_var_expr  COMMA number COMMA  stds   RPAREN
             | IF LPAREN s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  stds   RPAREN
             | IF LPAREN s_var_expr  COMMA number COMMA  expr   RPAREN
             | IF LPAREN s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  expr   RPAREN
             | IF LPAREN s_var_expr  COMMA stds   COMMA  number RPAREN
             | IF LPAREN s_var_expr  COMMA stds   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN s_var_expr  COMMA expr   COMMA  number RPAREN
             | IF LPAREN s_var_expr  COMMA expr   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN ts_var_expr COMMA number COMMA  stds   RPAREN
             | IF LPAREN ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  stds   RPAREN
             | IF LPAREN ts_var_expr COMMA number COMMA  expr   RPAREN
             | IF LPAREN ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  expr   RPAREN
             | IF LPAREN ts_var_expr COMMA stds   COMMA  number RPAREN
             | IF LPAREN ts_var_expr COMMA stds   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN ts_var_expr COMMA expr   COMMA  number RPAREN
             | IF LPAREN ts_var_expr COMMA expr   COMMA  NULL   LPAREN RPAREN RPAREN
    """,
    "p_s_numeric_expr_condition_elif_relation": """
        expr : IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA number COMMA  stds   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  stds   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA number COMMA  expr   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  expr   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA stds   COMMA  number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA stds   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA expr   COMMA  number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA expr   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA number COMMA  stds   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  stds   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA number COMMA  expr   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  expr   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA stds   COMMA  number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA stds   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA expr   COMMA  number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA expr   COMMA  NULL   LPAREN RPAREN RPAREN
    """,
    "p_s_expr_condition_elif_relation": """
        expr : IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA stds COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA stds COMMA expr RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA expr COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA expr COMMA expr RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA stds COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA stds COMMA expr RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA expr COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA expr COMMA expr RPAREN
    """,
    "p_ts_var_expr1": """
        ts_var_expr : s_var_expr  AND AND t_var_expr
                    | t_var_expr  AND AND s_var_expr
                    | t_var_expr  OR  OR  s_var_expr
                    | s_var_expr  OR  OR  t_var_expr
                    | ts_var_expr AND AND s_var_expr
                    | ts_var_expr AND AND t_var_expr
                    | ts_var_expr OR  OR  s_var_expr
                    | ts_var_expr OR  OR  t_var_expr
                    | s_var_expr  AND AND ts_var_expr
                    | t_var_expr  AND AND ts_var_expr
                    | s_var_expr  OR  OR  ts_var_expr
                    | t_var_expr  OR  OR  ts_var_expr
    """,
    "p_hash_operation": """
        expr : t_hash_var
    """,
    "p_mapexpr_numeric": """
        mapexpr : mapexpr   MOD  number
                | mapexpr   DIV  number
                | mapexpr   MULT number
                | mapexpr   ADD  number
                | mapexpr   SUB  number
                | number    MOD  mapexpr
                | number    DIV  mapexpr
                | number    MULT mapexpr
                | number    ADD  mapexpr
                | number    SUB  mapexpr
                | mapexpr   MOD  numberstr
                | mapexpr   DIV  numberstr
                | mapexpr   MULT numberstr
                | mapexpr   ADD  numberstr
                | mapexpr   SUB  numberstr
                | numberstr MOD  mapexpr
                | numberstr DIV  mapexpr
                | numberstr MULT mapexpr
                | numberstr ADD  mapexpr
                | numberstr SUB  mapexpr
                | mapexpr   MOD  mapexpr
                | mapexpr   DIV  mapexpr
                | mapexpr   MULT mapexpr
                | mapexpr   ADD  mapexpr
                | mapexpr   SUB  mapexpr
    """,
    "p_mapexpr_paren": """
        mapexpr : LPAREN mapexpr RPAREN
    """,
    "p_numberstr_chain": """
        numberstr : numberstr MOD  number
                  | numberstr DIV  number
                  | numberstr MULT number
                  | numberstr ADD  number
                  | numberstr SUB  number
                  | number    MOD  numberstr
                  | number    DIV  numberstr
                  | number    MULT numberstr
                  | number    ADD  numberstr
                  | number    SUB  numberstr
                  | numberstr MOD  numberstr
                  | numberstr DIV  numberstr
                  | numberstr MULT numberstr
                  | numberstr ADD  numberstr
                  | numberstr SUB  numberstr
    """,
    "p_td_operation": """
        expr : t_td_var MOD  stds
             | t_td_var MOD  expr
             | t_td_var MOD  number
             | t_td_var MOD  mapexpr
             | t_td_var MOD  t_td_var
             | t_td_var DIV  stds
             | t_td_var DIV  expr
             | t_td_var DIV  number
             | t_td_var DIV  mapexpr
             | t_td_var DIV  t_td_var
             | t_td_var MULT stds
             | t_td_var MULT expr
             | t_td_var MULT number
             | t_td_var MULT mapexpr
             | t_td_var MULT t_td_var
    """,
    "p_td_operation_relation": """
        expr : t_td_var T_ARITH1_OPERATOR stds
             | t_td_var T_ARITH1_OPERATOR expr
             | t_td_var T_ARITH1_OPERATOR t_td_var
    """,
    "p_ts_neighbor_operation": """
        expr : stds L_SPAREN number COMMA number COMMA number R_SPAREN
             | stds L_SPAREN number R_SPAREN
             | stds L_SPAREN number COMMA number COMMA number COMMA number R_SPAREN
    """,
    "p_overlay_operation": """
        expr : stds AND stds
             | expr AND stds
             | stds AND expr
             | expr AND expr
             | stds OR stds
             | expr OR stds
             | stds OR expr
             | expr OR expr
             | stds XOR stds
             | expr XOR stds
             | stds XOR expr
             | expr XOR expr
             | stds NOT stds
             | expr NOT stds
             | stds NOT expr
             | expr NOT expr
             | stds DISOR stds
             | expr DISOR stds
             | stds DISOR expr
             | expr DISOR expr
    """,
    "p_overlay_operation_relation": """
        expr : stds T_OVERLAY_OPERATOR stds
             | expr T_OVERLAY_OPERATOR stds
             | stds T_OVERLAY_OPERATOR expr
             | expr T_OVERLAY_OPERATOR expr
    """,
    "p_buffer_operation": """
        expr : buff_function LPAREN stds COMMA number RPAREN
             | buff_function LPAREN expr COMMA number RPAREN
    """,
    "p_buff_function": """
        buff_function    : BUFF_POINT
                | BUFF_LINE
                | BUFF_AREA
    """,
}

# The order in which PLY read the rules of each class: by line number, then
# module, then name. Reduce/reduce conflicts are resolved in this order.
_ORDER = {
    "select": (
        "p_statement_assign",
        "p_stds_1",
        "p_paren_expr",
        "p_number",
        "p_expr_strds_function",
        "p_expr_str3ds_function",
        "p_expr_stvds_function",
        "p_expr_tmap_function",
        "p_expr_tmerge_function",
        "p_t_hash",
        "p_t_hash2",
        "p_t_hash_paren",
        "p_t_td_var",
        "p_t_time_var",
        "p_compare_op",
        "p_t_var_expr_td_hash",
        "p_t_var_expr_number",
        "p_t_var_expr_time",
        "p_t_var_expr_comp",
        "p_t_var_expr_comp_op",
        "p_expr_t_select",
        "p_expr_t_not_select",
        "p_expr_t_select_operator",
        "p_expr_condition_if",
        "p_expr_condition_if_relation",
        "p_expr_condition_elif",
        "p_expr_condition_elif_relation",
        "p_expr_t_buff",
        "p_expr_t_snap",
        "p_expr_t_shift",
        "p_expr_time_const",
    ),
    "raster": (
        "p_ts_neighbour_operation",
        "p_expr_spmap_function",
        "p_arith1_operation",
        "p_arith1_operation_numeric1",
        "p_arith1_operation_numeric2",
        "p_arith2_operation",
        "p_arith2_operation_numeric1",
        "p_arith2_operation_numeric2",
        "p_arith1_operation_relation",
        "p_arith2_operation_relation",
        "p_arith_operation_numeric_string",
        "p_mapcalc_function",
        "p_mapcalc_operation1",
        "p_mapexpr_operation",
        "p_s_var_expr_1",
        "p_s_var_expr_2",
        "p_s_var_expr_3",
        "p_s_var_expr_4",
        "p_s_var_expr_comp",
        "p_s_var_expr_comp_op",
        "p_s_expr_condition_if",
        "p_s_numeric_condition_if",
        "p_t_numeric_else_condition_if",
        "p_t_numeric_else_condition_if_relation",
        "p_s_expr_condition_if_relation",
        "p_s_expr_condition_elif",
        "p_s_numeric_condition_elif",
        "p_s_numeric_expr_condition_elif",
        "p_s_numeric_expr_condition_elif_relation",
        "p_s_expr_condition_elif_relation",
        "p_ts_var_expr1",
        "p_hash_operation",
        "p_mapexpr_numeric",
        "p_mapexpr_paren",
        "p_numberstr_chain",
        "p_td_operation",
        "p_td_operation_relation",
        "p_statement_assign",
        "p_stds_1",
        "p_paren_expr",
        "p_number",
        "p_expr_strds_function",
        "p_expr_str3ds_function",
        "p_expr_stvds_function",
        "p_expr_tmap_function",
        "p_expr_tmerge_function",
        "p_t_hash",
        "p_t_hash2",
        "p_t_hash_paren",
        "p_t_td_var",
        "p_t_time_var",
        "p_compare_op",
        "p_t_var_expr_td_hash",
        "p_t_var_expr_number",
        "p_t_var_expr_time",
        "p_t_var_expr_comp",
        "p_t_var_expr_comp_op",
        "p_expr_t_select",
        "p_expr_t_not_select",
        "p_expr_t_select_operator",
        "p_expr_condition_if",
        "p_expr_condition_if_relation",
        "p_expr_condition_elif",
        "p_expr_condition_elif_relation",
        "p_expr_t_buff",
        "p_expr_t_snap",
        "p_expr_t_shift",
        "p_expr_time_const",
    ),
    "raster3d": (
        "p_ts_neighbor_operation",
        "p_expr_spmap_function",
        "p_arith1_operation",
        "p_arith1_operation_numeric1",
        "p_arith1_operation_numeric2",
        "p_arith2_operation",
        "p_arith2_operation_numeric1",
        "p_arith2_operation_numeric2",
        "p_arith1_operation_relation",
        "p_arith2_operation_relation",
        "p_arith_operation_numeric_string",
        "p_mapcalc_function",
        "p_mapcalc_operation1",
        "p_mapexpr_operation",
        "p_s_var_expr_1",
        "p_s_var_expr_2",
        "p_s_var_expr_3",
        "p_s_var_expr_4",
        "p_s_var_expr_comp",
        "p_s_var_expr_comp_op",
        "p_s_expr_condition_if",
        "p_s_numeric_condition_if",
        "p_t_numeric_else_condition_if",
        "p_t_numeric_else_condition_if_relation",
        "p_s_expr_condition_if_relation",
        "p_s_expr_condition_elif",
        "p_s_numeric_condition_elif",
        "p_s_numeric_expr_condition_elif",
        "p_s_numeric_expr_condition_elif_relation",
        "p_s_expr_condition_elif_relation",
        "p_ts_var_expr1",
        "p_hash_operation",
        "p_mapexpr_numeric",
        "p_mapexpr_paren",
        "p_numberstr_chain",
        "p_td_operation",
        "p_td_operation_relation",
        "p_statement_assign",
        "p_stds_1",
        "p_paren_expr",
        "p_number",
        "p_expr_strds_function",
        "p_expr_str3ds_function",
        "p_expr_stvds_function",
        "p_expr_tmap_function",
        "p_expr_tmerge_function",
        "p_t_hash",
        "p_t_hash2",
        "p_t_hash_paren",
        "p_t_td_var",
        "p_t_time_var",
        "p_compare_op",
        "p_t_var_expr_td_hash",
        "p_t_var_expr_number",
        "p_t_var_expr_time",
        "p_t_var_expr_comp",
        "p_t_var_expr_comp_op",
        "p_expr_t_select",
        "p_expr_t_not_select",
        "p_expr_t_select_operator",
        "p_expr_condition_if",
        "p_expr_condition_if_relation",
        "p_expr_condition_elif",
        "p_expr_condition_elif_relation",
        "p_expr_t_buff",
        "p_expr_t_snap",
        "p_expr_t_shift",
        "p_expr_time_const",
    ),
    "vector": (
        "p_overlay_operation",
        "p_overlay_operation_relation",
        "p_buffer_operation",
        "p_buff_function",
        "p_statement_assign",
        "p_stds_1",
        "p_paren_expr",
        "p_number",
        "p_expr_strds_function",
        "p_expr_str3ds_function",
        "p_expr_stvds_function",
        "p_expr_tmap_function",
        "p_expr_tmerge_function",
        "p_t_hash",
        "p_t_hash2",
        "p_t_hash_paren",
        "p_t_td_var",
        "p_t_time_var",
        "p_compare_op",
        "p_t_var_expr_td_hash",
        "p_t_var_expr_number",
        "p_t_var_expr_time",
        "p_t_var_expr_comp",
        "p_t_var_expr_comp_op",
        "p_expr_t_select",
        "p_expr_t_not_select",
        "p_expr_t_select_operator",
        "p_expr_condition_if",
        "p_expr_condition_if_relation",
        "p_expr_condition_elif",
        "p_expr_condition_elif_relation",
        "p_expr_t_buff",
        "p_expr_t_snap",
        "p_expr_t_shift",
        "p_expr_time_const",
    ),
}

# From the weakest to the strongest binding, as PLY reads the tables.
_PRECEDENCE = {
    "select": (
        (
            "left",
            "T_SELECT_OPERATOR",
            "T_SELECT",
            "T_NOT_SELECT",
            "T_HASH_OPERATOR",
            "HASH",
        ),
        ("left", "AND", "OR", "T_COMP_OPERATOR"),
    ),
    "raster": (
        ("left", "T_SELECT_OPERATOR", "T_SELECT", "T_NOT_SELECT"),
        ("left", "ADD", "SUB", "T_ARITH2_OPERATOR", "T_HASH_OPERATOR", "HASH"),
        (
            "left",
            "AND",
            "OR",
            "T_COMP_OPERATOR",
            "MOD",
            "DIV",
            "MULT",
            "T_ARITH1_OPERATOR",
        ),
    ),
    "vector": (
        (
            "left",
            "T_SELECT_OPERATOR",
            "T_SELECT",
            "T_NOT_SELECT",
            "T_HASH_OPERATOR",
            "HASH",
        ),
        (
            "left",
            "AND",
            "OR",
            "T_COMP_OPERATOR",
            "T_OVERLAY_OPERATOR",
            "DISOR",
            "NOT",
            "XOR",
        ),
    ),
}

# The classes of 3D raster maps inherit the precedence of those of raster maps.
PRECEDENCE = {**_PRECEDENCE, "raster3d": _PRECEDENCE["raster"]}

# Every class starts at the statement.
START = "statement"


def productions(kind):
    """Return the productions of a kind as ``(method name, text)`` pairs

    :param kind: one of ``KINDS``
    :return: the pairs in the order in which PLY read them in the parser class
    """
    return tuple((name, _TEXTS[name]) for name in _ORDER[kind])


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
        from grass.temporal.temporal_vector_algebra import TemporalVectorAlgebraLexer

        return TemporalVectorAlgebraLexer
    if kind == "select":
        from grass.temporal.temporal_algebra import TemporalAlgebraLexer

        return TemporalAlgebraLexer
    from grass.temporal.temporal_raster_base_algebra import TemporalRasterAlgebraLexer

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
            "precedence": PRECEDENCE[self.kind],
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

    :param kind: one of ``KINDS``
    :return: an object with ``parse(text)``, which fits ``Profile.grammar``
    :raises ValueError: for another kind
    """
    if kind not in KINDS:
        msg = f"kind is one of {', '.join(KINDS)}, not {kind!r}"
        raise ValueError(msg)
    return ClassicGrammar(kind)
