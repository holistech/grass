"""The productions and precedence tables of the classic grammar as data

A frozen copy of the p_ methods and precedence tables of the parser classes
of grass.temporal.classic, from which classic_grammar.py builds the classic
grammar; a test compares the copy with the parser classes. These tables are
for variants of the algebra, not for users.

SPDX-FileCopyrightText: 2013-2014 Thomas Leppelt
SPDX-FileCopyrightText: 2013-2014, 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Thomas Leppelt and Soeren Gebbert
"""

# The productions of every p_ method of the parser classes, by method name.
# A name that two classes share has the same text in both.
TEXTS = {
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
    "p_s_var_expr_compare": """
        s_var_expr : stds comp_op stds
                   | expr comp_op stds
                   | stds comp_op expr
                   | expr comp_op expr
    """,
    "p_s_var_expr_compare_relation": """
        s_var_expr : stds T_COMPARISON_OPERATOR stds
                   | expr T_COMPARISON_OPERATOR stds
                   | stds T_COMPARISON_OPERATOR expr
                   | expr T_COMPARISON_OPERATOR expr
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
# module, then name. Reduce/reduce conflicts are resolved in this order. The
# parser classes of the map types read the rules of the t.select class last.
ORDER = {
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
    )
}
ORDER["raster"] = (
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
    "p_s_var_expr_compare",
    "p_s_var_expr_compare_relation",
    *ORDER["select"],
)
ORDER["raster3d"] = (
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
    "p_s_var_expr_compare",
    "p_s_var_expr_compare_relation",
    *ORDER["select"],
)
ORDER["vector"] = (
    "p_overlay_operation",
    "p_overlay_operation_relation",
    "p_buffer_operation",
    "p_buff_function",
    *ORDER["select"],
)

# From the weakest to the strongest binding, as PLY reads the tables.
PRECEDENCE = {
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
PRECEDENCE["raster3d"] = PRECEDENCE["raster"]
