"""@package grass.temporal

Temporal algebra parser class

SPDX-FileCopyrightText: 2014 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Thomas Leppelt and Soeren Gebbert

.. code-block:: pycon

    >>> import grass.temporal as tgis
    >>> tgis.init(True)
    >>> p = tgis.TemporalAlgebraLexer()
    >>> p.build()
    >>> p.debug = True
    >>> expression = "C = A : B"
    >>> p.test(expression)
    C = A : B
    LexToken(NAME,'C',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'A',1,4)
    LexToken(T_SELECT,':',1,6)
    LexToken(NAME,'B',1,8)
    >>> expression = "C = test1 !: test2"
    >>> p.test(expression)
    C = test1 !: test2
    LexToken(NAME,'C',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'test1',1,4)
    LexToken(T_NOT_SELECT,'!:',1,10)
    LexToken(NAME,'test2',1,13)
    >>> expression = "C = test1 {:,equal} test2"
    >>> p.test(expression)
    C = test1 {:,equal} test2
    LexToken(NAME,'C',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'test1',1,4)
    LexToken(T_SELECT_OPERATOR,'{:,equal}',1,10)
    LexToken(NAME,'test2',1,20)
    >>> expression = "C = test1 {!:,equal} test2"
    >>> p.test(expression)
    C = test1 {!:,equal} test2
    LexToken(NAME,'C',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'test1',1,4)
    LexToken(T_SELECT_OPERATOR,'{!:,equal}',1,10)
    LexToken(NAME,'test2',1,21)
    >>> expression = "C = test1 # test2"
    >>> p.test(expression)
    C = test1 # test2
    LexToken(NAME,'C',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'test1',1,4)
    LexToken(HASH,'#',1,10)
    LexToken(NAME,'test2',1,12)
    >>> expression = "C = test1 {#} test2"
    >>> p.test(expression)
    C = test1 {#} test2
    LexToken(NAME,'C',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'test1',1,4)
    LexToken(T_HASH_OPERATOR,'{#}',1,10)
    LexToken(NAME,'test2',1,14)
    >>> expression = "C = test1 {#,equal} test2"
    >>> p.test(expression)
    C = test1 {#,equal} test2
    LexToken(NAME,'C',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'test1',1,4)
    LexToken(T_HASH_OPERATOR,'{#,equal}',1,10)
    LexToken(NAME,'test2',1,20)
    >>> expression = "C = test1 {#,equal|during} test2"
    >>> p.test(expression)
    C = test1 {#,equal|during} test2
    LexToken(NAME,'C',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'test1',1,4)
    LexToken(T_HASH_OPERATOR,'{#,equal|during}',1,10)
    LexToken(NAME,'test2',1,27)
    >>> expression = "E = test1 : test2 !: test1"
    >>> p.test(expression)
    E = test1 : test2 !: test1
    LexToken(NAME,'E',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'test1',1,4)
    LexToken(T_SELECT,':',1,10)
    LexToken(NAME,'test2',1,12)
    LexToken(T_NOT_SELECT,'!:',1,18)
    LexToken(NAME,'test1',1,21)
    >>> expression = 'D = buff_t(test1,"10 months")'
    >>> p.test(expression)
    D = buff_t(test1,"10 months")
    LexToken(NAME,'D',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(BUFF_T,'buff_t',1,4)
    LexToken(LPAREN,'(',1,10)
    LexToken(NAME,'test1',1,11)
    LexToken(COMMA,',',1,16)
    LexToken(QUOTE,'"',1,17)
    LexToken(INT,10,1,18)
    LexToken(NAME,'months',1,21)
    LexToken(QUOTE,'"',1,27)
    LexToken(RPAREN,')',1,28)
    >>> expression = "H = tsnap(test1)"
    >>> p.test(expression)
    H = tsnap(test1)
    LexToken(NAME,'H',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(TSNAP,'tsnap',1,4)
    LexToken(LPAREN,'(',1,9)
    LexToken(NAME,'test1',1,10)
    LexToken(RPAREN,')',1,15)
    >>> expression = 'H = tsnap(test2 {:,during} buff_t(test1, "1 days"))'
    >>> p.test(expression)
    H = tsnap(test2 {:,during} buff_t(test1, "1 days"))
    LexToken(NAME,'H',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(TSNAP,'tsnap',1,4)
    LexToken(LPAREN,'(',1,9)
    LexToken(NAME,'test2',1,10)
    LexToken(T_SELECT_OPERATOR,'{:,during}',1,16)
    LexToken(BUFF_T,'buff_t',1,27)
    LexToken(LPAREN,'(',1,33)
    LexToken(NAME,'test1',1,34)
    LexToken(COMMA,',',1,39)
    LexToken(QUOTE,'"',1,41)
    LexToken(INT,1,1,42)
    LexToken(NAME,'days',1,44)
    LexToken(QUOTE,'"',1,48)
    LexToken(RPAREN,')',1,49)
    LexToken(RPAREN,')',1,50)
    >>> expression = 'H = tshift(test2 {:,during} buff_t(test1, "1 days"), "1 months")'
    >>> p.test(expression)
    H = tshift(test2 {:,during} buff_t(test1, "1 days"), "1 months")
    LexToken(NAME,'H',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(TSHIFT,'tshift',1,4)
    LexToken(LPAREN,'(',1,10)
    LexToken(NAME,'test2',1,11)
    LexToken(T_SELECT_OPERATOR,'{:,during}',1,17)
    LexToken(BUFF_T,'buff_t',1,28)
    LexToken(LPAREN,'(',1,34)
    LexToken(NAME,'test1',1,35)
    LexToken(COMMA,',',1,40)
    LexToken(QUOTE,'"',1,42)
    LexToken(INT,1,1,43)
    LexToken(NAME,'days',1,45)
    LexToken(QUOTE,'"',1,49)
    LexToken(RPAREN,')',1,50)
    LexToken(COMMA,',',1,51)
    LexToken(QUOTE,'"',1,53)
    LexToken(INT,1,1,54)
    LexToken(NAME,'months',1,56)
    LexToken(QUOTE,'"',1,62)
    LexToken(RPAREN,')',1,63)
    >>> expression = "H = tshift(A , 10)"
    >>> p.test(expression)
    H = tshift(A , 10)
    LexToken(NAME,'H',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(TSHIFT,'tshift',1,4)
    LexToken(LPAREN,'(',1,10)
    LexToken(NAME,'A',1,11)
    LexToken(COMMA,',',1,13)
    LexToken(INT,10,1,15)
    LexToken(RPAREN,')',1,17)
    >>> expression = "H = if(td(A) > 10, A)"
    >>> p.test(expression)
    H = if(td(A) > 10, A)
    LexToken(NAME,'H',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(IF,'if',1,4)
    LexToken(LPAREN,'(',1,6)
    LexToken(TD,'td',1,7)
    LexToken(LPAREN,'(',1,9)
    LexToken(NAME,'A',1,10)
    LexToken(RPAREN,')',1,11)
    LexToken(GREATER,'>',1,13)
    LexToken(INT,10,1,15)
    LexToken(COMMA,',',1,17)
    LexToken(NAME,'A',1,19)
    LexToken(RPAREN,')',1,20)
    >>> expression = "H = if(td(A) > 10, A, B)"
    >>> p.test(expression)
    H = if(td(A) > 10, A, B)
    LexToken(NAME,'H',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(IF,'if',1,4)
    LexToken(LPAREN,'(',1,6)
    LexToken(TD,'td',1,7)
    LexToken(LPAREN,'(',1,9)
    LexToken(NAME,'A',1,10)
    LexToken(RPAREN,')',1,11)
    LexToken(GREATER,'>',1,13)
    LexToken(INT,10,1,15)
    LexToken(COMMA,',',1,17)
    LexToken(NAME,'A',1,19)
    LexToken(COMMA,',',1,20)
    LexToken(NAME,'B',1,22)
    LexToken(RPAREN,')',1,23)
    >>> expression = "I = if(equals,td(A) > 10 {||,equals} td(B) < 10, A)"
    >>> p.test(expression)
    I = if(equals,td(A) > 10 {||,equals} td(B) < 10, A)
    LexToken(NAME,'I',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(IF,'if',1,4)
    LexToken(LPAREN,'(',1,6)
    LexToken(NAME,'equals',1,7)
    LexToken(COMMA,',',1,13)
    LexToken(TD,'td',1,14)
    LexToken(LPAREN,'(',1,16)
    LexToken(NAME,'A',1,17)
    LexToken(RPAREN,')',1,18)
    LexToken(GREATER,'>',1,20)
    LexToken(INT,10,1,22)
    LexToken(T_COMP_OPERATOR,'{||,equals}',1,25)
    LexToken(TD,'td',1,37)
    LexToken(LPAREN,'(',1,39)
    LexToken(NAME,'B',1,40)
    LexToken(RPAREN,')',1,41)
    LexToken(LOWER,'<',1,43)
    LexToken(INT,10,1,45)
    LexToken(COMMA,',',1,47)
    LexToken(NAME,'A',1,49)
    LexToken(RPAREN,')',1,50)
    >>> expression = "I = if(equals,td(A) > 10 || start_day() < 10, A)"
    >>> p.test(expression)
    I = if(equals,td(A) > 10 || start_day() < 10, A)
    LexToken(NAME,'I',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(IF,'if',1,4)
    LexToken(LPAREN,'(',1,6)
    LexToken(NAME,'equals',1,7)
    LexToken(COMMA,',',1,13)
    LexToken(TD,'td',1,14)
    LexToken(LPAREN,'(',1,16)
    LexToken(NAME,'A',1,17)
    LexToken(RPAREN,')',1,18)
    LexToken(GREATER,'>',1,20)
    LexToken(INT,10,1,22)
    LexToken(OR,'|',1,25)
    LexToken(OR,'|',1,26)
    LexToken(START_DAY,'start_day',1,28)
    LexToken(LPAREN,'(',1,37)
    LexToken(RPAREN,')',1,38)
    LexToken(LOWER,'<',1,40)
    LexToken(INT,10,1,42)
    LexToken(COMMA,',',1,44)
    LexToken(NAME,'A',1,46)
    LexToken(RPAREN,')',1,47)
    >>> expression = "E = if({equals},td(A) >= 4 {&&,contain} td(B) == 2, C : D)"
    >>> p.test(expression)
    E = if({equals},td(A) >= 4 {&&,contain} td(B) == 2, C : D)
    LexToken(NAME,'E',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(IF,'if',1,4)
    LexToken(LPAREN,'(',1,6)
    LexToken(T_REL_OPERATOR,'{equals}',1,7)
    LexToken(COMMA,',',1,15)
    LexToken(TD,'td',1,16)
    LexToken(LPAREN,'(',1,18)
    LexToken(NAME,'A',1,19)
    LexToken(RPAREN,')',1,20)
    LexToken(GREATER_EQUALS,'>=',1,22)
    LexToken(INT,4,1,25)
    LexToken(T_COMP_OPERATOR,'{&&,contain}',1,27)
    LexToken(TD,'td',1,40)
    LexToken(LPAREN,'(',1,42)
    LexToken(NAME,'B',1,43)
    LexToken(RPAREN,')',1,44)
    LexToken(CEQUALS,'==',1,46)
    LexToken(INT,2,1,49)
    LexToken(COMMA,',',1,50)
    LexToken(NAME,'C',1,52)
    LexToken(T_SELECT,':',1,54)
    LexToken(NAME,'D',1,56)
    LexToken(RPAREN,')',1,57)
    >>> expression = "F = if({equals},A {#,equal}, B, C : D)"
    >>> p.test(expression)
    F = if({equals},A {#,equal}, B, C : D)
    LexToken(NAME,'F',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(IF,'if',1,4)
    LexToken(LPAREN,'(',1,6)
    LexToken(T_REL_OPERATOR,'{equals}',1,7)
    LexToken(COMMA,',',1,15)
    LexToken(NAME,'A',1,16)
    LexToken(T_HASH_OPERATOR,'{#,equal}',1,18)
    LexToken(COMMA,',',1,27)
    LexToken(NAME,'B',1,29)
    LexToken(COMMA,',',1,30)
    LexToken(NAME,'C',1,32)
    LexToken(T_SELECT,':',1,34)
    LexToken(NAME,'D',1,36)
    LexToken(RPAREN,')',1,37)
    >>> p = tgis.TemporalAlgebraParser()
    >>> p.run = False
    >>> p.debug = True
    >>> expression = "D = A {!:} B {:,during} C"
    >>> print(expression)
    D = A {!:} B {:,during} C
    >>> ret = p.parse(expression)
    A* =  A {!:} B
    A** =  A* {:,during} C
    D = A**
    >>> expression = "D = A {:} B {!:,during} C"
    >>> print(expression)
    D = A {:} B {!:,during} C
    >>> ret = p.parse(expression)
    A* =  A {:} B
    A** =  A* {!:,during} C
    D = A**
    >>> p.run = False
    >>> p.debug = False
    >>> expression = "C = test1 : test2"
    >>> print(expression)
    C = test1 : test2
    >>> ret = p.parse(expression, "stvds")
    >>> expression = 'D = buff_t(test1,"10 months")'
    >>> print(expression)
    D = buff_t(test1,"10 months")
    >>> ret = p.parse(expression, "stvds")
    >>> expression = 'E = test2 {:,during} buff_t(test1,"1 days")'
    >>> print(expression)
    E = test2 {:,during} buff_t(test1,"1 days")
    >>> ret = p.parse(expression, "stvds")
    >>> expression = 'F = test2 {:,equal} buff_t(test1,"1 days")'
    >>> print(expression)
    F = test2 {:,equal} buff_t(test1,"1 days")
    >>> ret = p.parse(expression, "stvds")
    >>> p.debug = True
    >>> expression = 'H = tsnap(test2 {:,during} buff_t(test1, "1 days"))'
    >>> ret = p.parse(expression, "stvds")
    test1* = buff_t( test1 , " 1 days " )
    test2* =  test2 {:,during} test1*
    test2** = tsnap( test2* )
    H = test2**
    >>> expression = 'H = tshift(test2 {:,during} test1, "1 days")'
    >>> ret = p.parse(expression, "stvds")
    test2* =  test2 {:,during} test1
    test2** = tshift( test2* , " 1 days " )
    H = test2**
    >>> expression = "H = tshift(H, 3)"
    >>> ret = p.parse(expression, "stvds")
    H* = tshift( H , 3 )
    H = H*
    >>> expression = "C = if(td(A) == 2, A)"
    >>> ret = p.parse(expression, "stvds")
    td(A)
    td(A) == 2
    A* =  if condition None  then  A
    C = A*
    >>> expression = "C = if(td(A) == 5, A, B)"
    >>> ret = p.parse(expression, "stvds")
    td(A)
    td(A) == 5
    A* =  if condition None  then  A  else  B
    C = A*
    >>> expression = 'C = if(td(A) == 5 || start_date(A) > "2010-01-01", A, B)'
    >>> ret = p.parse(expression, "stvds")
    td(A)
    td(A) == 5
    start_date A > "2010-01-01"
    None || None
    A* =  if condition None  then  A  else  B
    C = A*

    >>> p = tgis.TemporalAlgebraLexer()
    >>> p.build()
    >>> p.debug = True
    >>> expression = "D = strds(A) : stvds(B) : str3ds(C)"
    >>> p.test(expression)
    D = strds(A) : stvds(B) : str3ds(C)
    LexToken(NAME,'D',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(STRDS,'strds',1,4)
    LexToken(LPAREN,'(',1,9)
    LexToken(NAME,'A',1,10)
    LexToken(RPAREN,')',1,11)
    LexToken(T_SELECT,':',1,13)
    LexToken(STVDS,'stvds',1,15)
    LexToken(LPAREN,'(',1,20)
    LexToken(NAME,'B',1,21)
    LexToken(RPAREN,')',1,22)
    LexToken(T_SELECT,':',1,24)
    LexToken(STR3DS,'str3ds',1,26)
    LexToken(LPAREN,'(',1,32)
    LexToken(NAME,'C',1,33)
    LexToken(RPAREN,')',1,34)

    >>> p = tgis.TemporalAlgebraLexer()
    >>> p.build()
    >>> p.debug = True
    >>> expression = "R = if(A {#,during} stvds(C) == 1, A)"
    >>> p.test(expression)
    R = if(A {#,during} stvds(C) == 1, A)
    LexToken(NAME,'R',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(IF,'if',1,4)
    LexToken(LPAREN,'(',1,6)
    LexToken(NAME,'A',1,7)
    LexToken(T_HASH_OPERATOR,'{#,during}',1,9)
    LexToken(STVDS,'stvds',1,20)
    LexToken(LPAREN,'(',1,25)
    LexToken(NAME,'C',1,26)
    LexToken(RPAREN,')',1,27)
    LexToken(CEQUALS,'==',1,29)
    LexToken(INT,1,1,32)
    LexToken(COMMA,',',1,33)
    LexToken(NAME,'A',1,35)
    LexToken(RPAREN,')',1,36)

    >>> p = tgis.TemporalAlgebraLexer()
    >>> p.build()
    >>> p.debug = True
    >>> expression = "R = if({during}, stvds(C) {#,contains} A == 2, A)"
    >>> p.test(expression)
    R = if({during}, stvds(C) {#,contains} A == 2, A)
    LexToken(NAME,'R',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(IF,'if',1,4)
    LexToken(LPAREN,'(',1,6)
    LexToken(T_REL_OPERATOR,'{during}',1,7)
    LexToken(COMMA,',',1,15)
    LexToken(STVDS,'stvds',1,17)
    LexToken(LPAREN,'(',1,22)
    LexToken(NAME,'C',1,23)
    LexToken(RPAREN,')',1,24)
    LexToken(T_HASH_OPERATOR,'{#,contains}',1,26)
    LexToken(NAME,'A',1,39)
    LexToken(CEQUALS,'==',1,41)
    LexToken(INT,2,1,44)
    LexToken(COMMA,',',1,45)
    LexToken(NAME,'A',1,47)
    LexToken(RPAREN,')',1,48)

"""

from __future__ import annotations

import copy
import os
from contextlib import contextmanager
from operator import eq, ge, gt, le, lt, ne
from typing import Literal

import grass.pygrass.modules as pymod
from grass.exceptions import FatalError

from .abstract_dataset import AbstractDatasetComparisonKeyStartTime
from .abstract_map_dataset import AbstractMapDataset
from .abstract_space_time_dataset import AbstractSpaceTimeDataset
from .core import (
    SQLDatabaseInterfaceConnection,
    get_current_mapset,
    get_tgis_message_interface,
    init_dbif,
)
from .datetime_math import (
    create_numeric_suffix,
    create_suffix_from_datetime,
    create_time_suffix,
    string_to_datetime,
    time_delta_to_relative_time,
)
from .factory import dataset_factory
from .open_stds import open_new_stds, open_old_stds
from .ply import lex, yacc
from .space_time_datasets import RasterDataset
from .spatio_temporal_relationships import SpatioTemporalTopologyBuilder
from .temporal_granularity import (
    compute_absolute_time_granularity,
    compute_common_absolute_time_granularity,
    compute_common_relative_time_granularity,
)
from .temporal_operator import TemporalOperatorParser


class TemporalAlgebraLexer:
    """Lexical analyzer for the GRASS temporal algebra"""

    # Functions that defines an if condition, temporal buffering, snapping and
    # selection of maps with temporal extent.
    conditional_functions = {
        "if": "IF",
        "buff_t": "BUFF_T",
        "tsnap": "TSNAP",
        "tshift": "TSHIFT",
        "tmap": "TMAP",
        "merge": "MERGE",
        "strds": "STRDS",
        "str3ds": "STR3DS",
        "stvds": "STVDS",
    }

    # Variables with date and time strings
    datetime_functions = {
        "start_time": "START_TIME",  # start time as HH::MM:SS
        "start_date": "START_DATE",  # start date as yyyy-mm-DD
        "start_datetime": "START_DATETIME",  # start datetime as yyyy-mm-DD HH:MM:SS
        "end_time": "END_TIME",  # end time as HH:MM:SS
        "end_date": "END_DATE",  # end date as yyyy-mm-DD
        "end_datetime": "END_DATETIME",  # end datetime as  yyyy-mm-DD HH:MM:SS
    }

    # Time functions
    time_functions = {
        "td": "TD",  # The size of the current
        # sample time interval in days and
        # fraction of days for absolute time,
        # and in relative units in case of relative time.
        # 'start_td'    : 'START_TD',     # The time difference between the start
        # time of the sample space time raster
        # dataset and the start time of the
        # current sample interval or instance.
        # The time is measured in days and
        # fraction of days for absolute time,
        # and in relative units in case of relative time.
        # 'end_td'      : 'END_TD',       # The time difference between the
        # start time of the sample
        # space time raster dataset and the
        # end time of the current sample interval.
        # The time is measured in days and
        # fraction of days for absolute time,
        # and in relative units in case of relative time.
        # The end_time() will be represented by null() in case of a time instance.
        "start_doy": "START_DOY",  # Day of year (doy) from the start time [1 - 366]
        "start_dow": "START_DOW",  # Day of week (dow) from the start time [1 - 7],
        # the start of the week is Monday == 1
        "start_year": "START_YEAR",  # The year of the start time [0 - 9999]
        "start_month": "START_MONTH",  # The month of the start time [1 - 12]
        "start_week": "START_WEEK",  # Week of year of the start time [1 - 54]
        "start_day": "START_DAY",  # Day of month from the start time [1 - 31]
        "start_hour": "START_HOUR",  # The hour of the start time [0 - 23]
        "start_minute": "START_MINUTE",  # The minute of the start time [0 - 59]
        "start_second": "START_SECOND",  # The second of the start time [0 - 59]
        "end_doy": "END_DOY",  # Day of year (doy) from the end time [1 - 366]
        "end_dow": "END_DOW",  # Day of week (dow) from the end time [1 - 7], the
        # start of the week is Monday == 1
        "end_year": "END_YEAR",  # The year of the end time [0 - 9999]
        "end_month": "END_MONTH",  # The month of the end time [1 - 12]
        "end_week": "END_WEEK",  # Week of year of the end time [1 - 54]
        "end_day": "END_DAY",  # Day of month from the start time [1 - 31]
        "end_hour": "END_HOUR",  # The hour of the end time [0 - 23]
        "end_minute": "END_MINUTE",  # The minute of the end time [0 - 59]
        "end_second": "END_SECOND",  # The second of the end time [0 - 59]
    }

    # This is the list of token names.
    tokens = (
        "DATETIME",
        "TIME",
        "DATE",
        "INT",
        "FLOAT",
        "LPAREN",
        "RPAREN",
        "COMMA",
        "CEQUALS",
        "EQUALS",
        "UNEQUALS",
        "LOWER",
        "LOWER_EQUALS",
        "GREATER",
        "GREATER_EQUALS",
        "HASH",
        "OR",
        "AND",
        "T_SELECT_OPERATOR",
        "T_HASH_OPERATOR",
        "T_COMP_OPERATOR",
        "T_REL_OPERATOR",
        "T_SELECT",
        "T_NOT_SELECT",
        "NAME",
        "QUOTE",
    )

    # Build the token list
    tokens = (
        tokens
        + tuple(datetime_functions.values())
        + tuple(time_functions.values())
        + tuple(conditional_functions.values())
    )

    # Regular expression rules for simple tokens
    # The temporal operator may follow the relations after a comma and blanks.
    _OPERATOR_TAIL = r"([,][ ]*)?([lrudi]|left|right|union|disjoint|intersect)?\}"
    t_T_SELECT_OPERATOR = r"\{[!]?[:][,]?[a-zA-Z\| ]*" + _OPERATOR_TAIL
    t_T_HASH_OPERATOR = r"\{[#][,]?[a-zA-Z\| ]*" + _OPERATOR_TAIL
    t_T_COMP_OPERATOR = r"\{(\|\||&&)[,][a-zA-Z\| ]*([,][ ]*[\|&])?" + _OPERATOR_TAIL
    t_T_REL_OPERATOR = r"\{([a-zA-Z\| ])+\}"
    t_T_SELECT = r":"
    t_T_NOT_SELECT = r"!:"
    t_LPAREN = r"\("
    t_RPAREN = r"\)"
    t_COMMA = r","
    t_CEQUALS = r"=="
    t_EQUALS = r"="
    t_UNEQUALS = r"!="
    t_LOWER = r"<"
    t_LOWER_EQUALS = r"<="
    t_GREATER = r">"
    t_GREATER_EQUALS = r">="
    t_HASH = r"\#"
    t_OR = r"[\|]"
    t_AND = r"[&]"
    t_QUOTE = r"[\"\']"

    # Newlines are not ignored so that t_newline can count the lines.
    t_ignore = " \t"

    # Regular expression parts shared by the literals below. Hours end at 23
    # and minutes and seconds at 59, since the literals are converted with
    # string_to_datetime, which rejects hour 24 and the 60th minute or second.
    _DATE_PATTERN = r"\d\d\d\d-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])"
    _TIME_PATTERN = r"(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"

    # A date and a time of day, separated by a blank or a T
    @lex.TOKEN(r'"' + _DATE_PATTERN + r"[ T]" + _TIME_PATTERN + r'"')
    def t_DATETIME(self, t):
        return t

    @lex.TOKEN(r'"' + _DATE_PATTERN + r'"')
    def t_DATE(self, t):
        return t

    @lex.TOKEN(r'"' + _TIME_PATTERN + r'"')
    def t_TIME(self, t):
        return t

    # This rule has to be defined before the int rule.
    def t_FLOAT(self, t):
        r"-?\d+\.\d*(e-?\d+)?"
        t.value = float(t.value)
        return t

    def t_INT(self, t):
        r"-?\d+"
        t.value = int(t.value)
        return t

    def t_newline(self, t) -> None:
        r"\n+"
        t.lexer.lineno += len(t.value)

    def t_NAME(self, t):
        r"[a-zA-Z_][a-zA-Z_0-9\@]*"
        return self.temporal_symbol(t)

    # Names of the class attributes with the reserved words (word to token type);
    # the lexers of the other algebras extend it.
    _reserved_tables = ("time_functions", "datetime_functions", "conditional_functions")

    def temporal_symbol(self, t):
        """Set the token type of a name: a reserved word or NAME"""
        for table in self._reserved_tables:
            reserved = getattr(self, table)
            if t.value in reserved:
                t.type = reserved[t.value]
                return t
        t.type = "NAME"
        return t

    # Handle errors.
    def t_error(self, t):
        raise SyntaxError(
            "syntax error on line %d position %i near '%s'"
            % (t.lineno, t.lexpos, t.value)
        )

    # Build the lexer
    def build(self, **kwargs) -> None:
        """Build the PLY lexer of this class; kwargs go to ``lex.lex``."""
        self.lexer = lex.lex(module=self, debug=0, **kwargs)

    def test(self, data) -> None:
        """Print the data and the tokens it is split into.

        The doctests of this module show the tokens of expressions with it.
        """
        print(data)
        self.lexer.input(data)
        while True:
            tok = self.lexer.token()
            if not tok:
                break
            print(tok)


class GlobalTemporalVar:
    """This class handles global temporal variable conditional expressions,
    like start_doy() == 3.
    The three parts of the statement are stored separately in
    tfunc (START_DOY), compop (==) and value (3).
    But also boolean values, time differences and relation operators for comparison in
    if-statements can be stored in this class.
    """

    def __init__(self) -> None:
        self.tfunc = None
        self.compop = None
        self.value = None
        self.boolean = None
        self.relationop = None
        self.topology = []
        self.td = None

    def get_type(self) -> Literal["global", "boolean", "operator", "timediff"] | None:
        """Return which kind of expression this variable holds, None if empty."""
        if (
            self.tfunc is not None
            and self.compop is not None
            and self.value is not None
        ):
            return "global"
        if self.boolean is not None:
            return "boolean"
        if self.relationop is not None and self.topology != []:
            return "operator"
        if self.td is not None:
            return "timediff"

    def get_type_value(self):
        """Return the values of this variable as a list, depending on its type."""
        typename = self.get_type()
        valuelist = []
        if typename == "global":
            valuelist = [self.tfunc, self.compop, self.value]
        elif typename == "operator":
            valuelist.append(self.topology)
            valuelist.append(self.relationop)
        elif typename == "boolean":
            valuelist = self.boolean
        elif typename == "timediff":
            valuelist.append(self.td)

        return valuelist

    def __str__(self) -> str:
        return str(self.tfunc) + str(self.compop) + str(self.value)


# LR tables per parser class, see TemporalAlgebraParser._build_parser
_PARSER_TEMPLATES: dict = {}

_COMPARISONS = {"<": lt, ">": gt, "==": eq, "<=": le, ">=": ge, "!=": ne}

# The inverse of each relation name. The relation of a condition reads from
# the condition to the conclusion, the selection relates the conclusion
# maps to the condition maps, see eval_map_list().
_INVERSE_RELATIONS = {
    "EQUAL": "EQUAL",
    "FOLLOWS": "PRECEDES",
    "PRECEDES": "FOLLOWS",
    "OVERLAPS": "OVERLAPPED",
    "OVERLAPPED": "OVERLAPS",
    "DURING": "CONTAINS",
    "CONTAINS": "DURING",
    "STARTS": "STARTED",
    "STARTED": "STARTS",
    "FINISHES": "FINISHED",
    "FINISHED": "FINISHES",
    "EQUIVALENT": "EQUIVALENT",
    "COVER": "COVERED",
    "COVERED": "COVER",
    "OVERLAP": "OVERLAP",
    "IN": "CONTAIN",
    "CONTAIN": "IN",
    "MEET": "MEET",
}

# The fields of a time stamp which the temporal functions of the algebra
# (start_doy(), end_date(), ...) return. The week is the ISO week.
_TIME_FIELDS = {
    "DOY": lambda timestamp: timestamp.timetuple().tm_yday,
    "DOW": lambda timestamp: timestamp.isoweekday(),
    "YEAR": lambda timestamp: timestamp.year,
    "MONTH": lambda timestamp: timestamp.month,
    "WEEK": lambda timestamp: timestamp.isocalendar()[1],
    "DAY": lambda timestamp: timestamp.day,
    "HOUR": lambda timestamp: timestamp.hour,
    "MINUTE": lambda timestamp: timestamp.minute,
    "SECOND": lambda timestamp: timestamp.second,
    "DATE": lambda timestamp: timestamp.date(),
    "DATETIME": lambda timestamp: timestamp,
    "TIME": lambda timestamp: timestamp.time(),
}


class TemporalAlgebraParser:
    """The temporal algebra class"""

    # Get the tokens from the lexer class
    tokens = TemporalAlgebraLexer.tokens

    # Setting equal precedence level for select and hash operations.
    precedence = (
        (
            "left",
            "T_SELECT_OPERATOR",
            "T_SELECT",
            "T_NOT_SELECT",
            "T_HASH_OPERATOR",
            "HASH",
        ),  # 1
        ("left", "AND", "OR", "T_COMP_OPERATOR"),  # 2
    )

    # PLY takes the rule with the lowest line number as start symbol if none is
    # given. The line numbers of inherited rules come from several files, so
    # the subclasses would depend on where their own rules stand.
    start = "statement"

    temporal_topology_list = [
        "EQUAL",
        "FOLLOWS",
        "PRECEDES",
        "OVERLAPS",
        "OVERLAPPED",
        "DURING",
        "STARTS",
        "FINISHES",
        "CONTAINS",
        "STARTED",
        "FINISHED",
    ]
    spatial_topology_list = [
        "EQUIVALENT",
        "COVER",
        "COVERED",
        "OVERLAP",
        "IN",
        "CONTAIN",
        "MEET",
    ]

    # Map type of AbstractMapDataset.get_type() as g.remove and g.copy write it
    _G_MODULE_TYPES = {"raster": "raster", "raster3d": "raster_3d", "vector": "vector"}

    # Dimensions of the spatial topology per type of space time dataset
    _SPATIAL_DIMENSIONS = {"strds": "2D", "stvds": "2D", "str3ds": "3D"}

    # Maps the operator letters of the algebra to the methods of a map that
    # compute the spatial and the temporal extent of two related maps
    _SPATIAL_OVERLAY = {
        "and": "spatial_intersection",
        "or": "spatial_union",
        "xor": "spatial_union",
        "disor": "spatial_disjoint_union",
    }
    _TEMPORAL_OVERLAY = {
        "i": "temporal_intersection",
        "u": "temporal_union",
        "d": "temporal_disjoint_union",
    }

    def __init__(
        self,
        pid: int | None = None,
        run: bool = True,
        debug: bool = False,
        spatial: bool = False,
        register_null: bool = False,
        dry_run: bool = False,
        nprocs: int = 1,
        time_suffix=None,
    ) -> None:
        self.run = run
        # Compute the processes and output but Do not start the processes
        self.dry_run = dry_run
        # All processes, the maps to register and remove and the STDS to create
        self.process_chain_dict = {
            "processes": [],  # The mapcalc and v.patch module calls
            "register": [],  # Maps to register, update or insert in a new STDS
            "remove": [],  # The g.remove module calls
            "STDS": {},  # The STDS that must be created
        }
        self.debug = debug
        self.pid = pid
        # Intermediate map names
        self.names = {}
        self.spatial = spatial
        self.mapset = get_current_mapset()
        self.temporaltype = None
        self.msgr = get_tgis_message_interface()
        self.dbif = SQLDatabaseInterfaceConnection()
        self.dbif.connect()
        self.register_null = register_null
        self.removable_maps = {}
        self.m_mremove = self._new_module("g.remove")
        self.m_copy = self._new_module("g.copy")
        self.nprocs = nprocs
        self.use_granularity = False
        self.granularity = None
        self.time_suffix = time_suffix
        self._reported_errors = []
        # Set by parse(), listed here so that the helper methods also work on
        # a parser which was never asked to parse
        self.lexer = None
        self.parser = None
        self.count = 0
        self.stdstype = "strds"
        self.maptype = "rast"
        self.mapclass = RasterDataset
        self.basename = None
        self.overwrite = False
        self.expression = ""

    def __del__(self) -> None:
        if self.dbif.connected:
            self.dbif.close()

    def setup_common_granularity(
        self, expression, stdstype="strds", lexer=None
    ) -> bool:
        """Configure the temporal algebra to use the common granularity of all
        space time datasets in the expression to generate the map lists.

        This function will analyze the expression to detect space time datasets
        and computes the common granularity from all granularities of the input space
        time datasets.

        This granularity is then be used to generate the map lists. Hence, all
        maps from all STDS will have equidistant temporal extents. The only meaningful
        temporal relation is therefore "equal".

        :param expression: The algebra expression to analyze

        :param lexer: The temporal algebra lexer (select, raster, voxel, vector) that
                      should be used to parse the expression, default is
                      TemporalAlgebraLexer

        :return: True if successful, False otherwise
        """
        expression = " ".join(expression.split("=")[1:])

        # Check if spatio-temporal operators are present in the expression
        if "{" in expression or "}" in expression:
            self.msgr.error(
                _(
                    "Spatio-temporal topological operators are not"
                    " supported in granularity algebra mode"
                )
            )
            return False

        dbif, _connection_state_changed = init_dbif(self.dbif)
        granularities = []
        start_times = []
        temporal_types = set()
        for name in self._stds_names_in(expression, lexer):
            stds = open_old_stds(name, stdstype, dbif)
            # We need valid temporal topology
            if stds.check_temporal_topology() is False:
                self.msgr.error(
                    _(
                        "All input space time datasets must have a valid temporal "
                        "topology."
                    )
                )
                return False

            granularities.append(stds.get_granularity())
            start_times.append(stds.get_temporal_extent_as_tuple()[0])
            temporal_types.add(stds.get_temporal_type())

        # Only one temporal type is allowed
        if len(temporal_types) > 1:
            self.msgr.error(
                _("All input space time datasets must have the same temporal type.")
            )
            return False

        if "absolute" in temporal_types:
            self.granularity = compute_common_absolute_time_granularity(
                granularities, start_times
            )
        else:
            self.granularity = compute_common_relative_time_granularity(granularities)

        self.use_granularity = True

        return True

    @staticmethod
    def _stds_names_in(expression, lexer=None):
        """Return the names of the space time datasets used in the expression.

        The argument of ``map()`` and ``tmap()`` is a single map, not a dataset.

        :param lexer: The lexer used to split the expression, default is
                      TemporalAlgebraLexer
        """
        lexer = TemporalAlgebraLexer() if lexer is None else lexer
        lexer.build()
        lexer.lexer.input(expression)
        names = []
        # The types of the preceding two tokens
        previous = [None, None]
        for token in iter(lexer.lexer.token, None):
            if token.type == "NAME" and previous[0] not in {"MAP", "TMAP"}:
                names.append(token.value)
            previous = [previous[1], token.type]
        return names

    def parse(
        self,
        expression,
        stdstype="strds",
        maptype="rast",
        mapclass=RasterDataset,
        basename=None,
        overwrite: bool = False,
    ):
        """Parse the algebra expression and run the computation

        :param expression:
        :param stdstype:
        :param maptype:
        :param mapclass:
        :param basename:
        :param overwrite:
        :return: The process chain dictionary: the processes, the maps to register
            and remove and the space time dataset to create. With ``dry_run`` it is
            filled but nothing is run.
        """
        return self._parse(
            TemporalAlgebraLexer(),
            expression,
            stdstype,
            maptype,
            mapclass,
            basename,
            overwrite,
        )

    @staticmethod
    def _reject_dataset_type_tokens(lexer, expression) -> None:
        """Refuse strds(), str3ds() and stvds(), which select the dataset type in
        the temporal algebra of the base class; the other algebras fix it.

        :param lexer: The not yet built lexer object of the algebra
        :raises SyntaxError: if the expression contains one of them
        """
        lexer.build()
        lexer.lexer.input(expression)
        for token in iter(lexer.lexer.token, None):
            if token.type in {"STVDS", "STRDS", "STR3DS"}:
                msg = f"Syntax error near '{token.type}'"
                raise SyntaxError(msg)

    def _parse(
        self, lexer, expression, stdstype, maptype, mapclass, basename, overwrite
    ):
        """Set up the lexer, the parser and the state of the run, then parse.

        Shared by the ``parse`` methods of all algebras, which differ in the
        lexer and in the type of the datasets and maps they handle.

        :param lexer: The not yet built lexer object of the algebra
        :return: The process chain dictionary
        """
        self.lexer = lexer
        self.lexer.build()
        self.parser = self._build_parser()

        self.overwrite = overwrite
        self.count = 0
        self.stdstype = stdstype
        self.maptype = maptype
        self.mapclass = mapclass
        self.basename = basename
        self.expression = expression
        self._run_parser(expression)

        return self.process_chain_dict

    @staticmethod
    def _new_module(name, **kwargs):
        """Return the module, prepared but not run: callers copy it, set the
        parameters and run it themselves or put it into a process queue."""
        return pymod.Module(name, run_=False, **kwargs)

    def _build_parser(self):
        """Return an LR parser for the grammar of this class bound to this instance.

        Building the LALR tables takes about 0.75 s (measured 2026-10-11 with
        cProfile on t.rast.algebra), so they are built once per class and
        shared. Only the rule callables and the error function are bound anew,
        because they are methods of the instance.
        """
        template = _PARSER_TEMPLATES.get(type(self))
        if template is None:
            template = yacc.yacc(module=self, debug=False)
            # The rule callables are bound methods of this instance. The cached
            # template must not keep the instance (and its database connection)
            # alive, so only the tables stay in it.
            for prod in template.productions:
                prod.callable = None
            template.errorfunc = None
            _PARSER_TEMPLATES[type(self)] = template
        parser = copy.copy(template)
        parser.productions = [copy.copy(prod) for prod in template.productions]
        for prod in parser.productions:
            if prod.func:
                prod.callable = getattr(self, prod.func)
        parser.errorfunc = self.p_error
        return parser

    def _report_error(self, message: str) -> None:
        """Record a syntax error found in a grammar rule.

        PLY swallows a SyntaxError raised inside a ``p_*`` rule, so rules
        report instead; ``_run_parser`` raises the first report afterwards.
        """
        self._reported_errors.append(message)

    def _run_parser(self, expression: str) -> None:
        """Parse the expression with ``self.parser`` and ``self.lexer``.

        :raises SyntaxError: for the first error reported by a grammar rule
            (see ``_report_error``), also if a later rule failed on the
            result of the faulty one
        """
        self._reported_errors = []
        try:
            self.parser.parse(expression, lexer=self.lexer.lexer)
        except Exception:
            if not self._reported_errors:
                raise
        if self._reported_errors:
            raise SyntaxError(self._reported_errors[0])

    def generate_map_name(self):
        """Generate an unique  map name and register it in the objects map list

        The map names are unique between processes. Do not use the
        same object for map name generation in multiple threads.
        """
        self.count += 1
        pid = self.pid if self.pid is not None else os.getpid()
        name = "tmp_map_name_%i_%i" % (pid, self.count)
        self.names[name] = name
        return name

    def generate_new_map(
        self,
        base_map,
        bool_op="and",
        copy: bool = True,
        rename: bool = True,
        remove: bool = False,
    ):
        """Generate a new map using the spatio-temporal extent of the base map

        :param base_map: This map is used to create the new map
        :param bool_op: The boolean operator specifying the spatial extent
               operation (intersection, union, disjoint union)
        :param copy: Specifies if the temporal extent of mapB should be
               copied to mapA
        :param rename: Specifies if the generated map get a random name or get
               the id from the base map.
        :param remove: Set this True if this map is an intermediate or empty map that
               should be removed
        :return: Map object
        """
        # Generate an intermediate name for the result map list.
        name = self.generate_map_name()
        # Check for mapset in given stds input.
        mapname = name + "@" + self.mapset
        # Create new map based on the related map list.
        map_new = base_map.get_new_instance(mapname)
        # Set initial map extend of new vector map.
        self.overlay_map_extent(map_new, base_map, bool_op=bool_op, copy=copy)
        if not rename:
            name = base_map.get_id()
            map_new.set_id(name)
        if remove is True:
            self.removable_maps[name] = map_new
        # Make sure to set the uid that is used in several dictionaries
        map_new.uid = name
        return map_new

    def overlay_map_extent(
        self, mapA, mapB, bool_op=None, temp_op="l", copy: bool = False
    ):
        """Compute the spatio-temporal extent of two topological related maps

        :param mapA: The first map
        :param mapB: The second maps
        :param bool_op: The boolean operator specifying the spatial extent
               operation (intersection, union, disjoint union)
        :param temp_op: The temporal operator specifying the temporal
               extent operation (intersection, union, disjoint union, right reference)
               Left reference is the default temporal extent behaviour.
        :param copy: Specifies if the temporal extent of mapB should be
               copied to mapA
        :return: 0 if there is no overlay
        """
        if copy:
            mapA.set_spatial_extent(mapB.get_spatial_extent())
            mapA.set_temporal_extent(mapB.get_temporal_extent())
            for attribute in ("cmd_list", "condition_value"):
                if hasattr(mapB, attribute):
                    setattr(mapA, attribute, getattr(mapB, attribute))
            return 1
        spatial_overlay = self._overlay_spatial_extent(mapA, mapB, bool_op)
        temporal_overlay = self._overlay_temporal_extent(mapA, mapB, temp_op)
        return 1 if spatial_overlay and temporal_overlay else 0

    def _overlay_spatial_extent(self, mapA, mapB, bool_op) -> bool:
        """Set the spatial extent of mapA to the result of the boolean operator.

        :return: False if the extents of both maps do not combine
        """
        method = self._SPATIAL_OVERLAY.get(bool_op)
        if method is None:
            return True
        extent = getattr(mapA, method)(mapB)
        if extent is None:
            return False
        mapA.set_spatial_extent(extent)
        return True

    def _overlay_temporal_extent(self, mapA, mapB, temp_op) -> bool:
        """Set the temporal extent of mapA according to the temporal operator.

        The left reference (``l``) keeps the extent of mapA.

        :return: False if the extents of both maps do not combine
        """
        if temp_op == "r":
            extent = mapB.get_temporal_extent()
        elif temp_op in self._TEMPORAL_OVERLAY:
            extent = getattr(mapA, self._TEMPORAL_OVERLAY[temp_op])(mapB)
        else:
            return True
        if extent is None:
            return False
        mapA.set_temporal_extent(extent)
        return True

    def set_temporal_extent_list(
        self,
        maplist,
        topolist=("EQUAL",),
        temporal="l",
        bool_op="and",
        combine=None,
        pair_equal_times: bool = False,
    ):
        """Change temporal extent of map list based on temporal relations to
            other map list and given temporal operator.

        :param maplist: List of map objects for which relations has been build
                                    correctly.
        :param topolist: List of strings of temporal relations.
        :param temporal: The temporal operator specifying the temporal
                                        extent operation (intersection, union, disjoint
                                        union, right reference, left reference).
        :param bool_op: The spatial extent operation: "and" intersects the
            extents, anything else takes the extent covering both maps. Only
            the intersection can be empty, so only "and" drops maps.
        :param combine: Optional ``combine(map_new, map_i, map_j)``, called after
            the extent of map_j was combined into the result map map_new of
            map_i. Subclasses use it to attach the commands of the operation.
        :param pair_equal_times: Pair maps of equal time one to one instead of
            relating each of them to all others, see ``_equal_time_partners``.

        :return: Map list with specified temporal extent.
        """
        topolist = ("EQUAL",) if topolist is None else topolist
        temporal_topo_list, spatial_topo_list = self._check_topology(topolist=topolist)
        resultdict = {}
        positions = self._equal_time_positions(maplist) if pair_equal_times else None

        for map_i in maplist:
            # Generate an intermediate map for the result map list.
            map_new = self._new_result_map(map_i)
            related = self._related_maps(map_i, temporal_topo_list, spatial_topo_list)
            if positions is not None:
                related = self._equal_time_partners(map_i, related, positions)
            # Combine temporal and spatial extents of the intermediate map with
            # the related maps, until one of them does not combine.
            for map_j in related:
                if temporal == "r":
                    # Every related map gets its own result map.
                    map_new = self._new_result_map(map_i)
                if not self.overlay_map_extent(
                    map_new, map_j, bool_op, temp_op=temporal
                ):
                    # No overlap: the result would be empty.
                    break
                if combine is not None:
                    combine(map_new, map_i, map_j)
                resultdict[map_new.get_id()] = map_new
        return sorted(resultdict.values(), key=AbstractDatasetComparisonKeyStartTime)

    @staticmethod
    def _equal_time_positions(maplist):
        """Return the position of each map among the maps of its time.

        :return: dict from ``id(map)`` to (position, number of maps of that time)
        """
        groups = {}
        for map_i in maplist:
            groups.setdefault(map_i.get_temporal_extent_as_tuple(), []).append(map_i)
        return {
            id(map_i): (position, len(group))
            for group in groups.values()
            for position, map_i in enumerate(group)
        }

    def _equal_time_partners(self, map_i, related, positions):
        """Restrict the related maps of map_i to its partners of equal time.

        Maps of equal time cannot be told apart by their time, so relating
        each to all would pair every map of a time with every other. Instead,
        like broadcasting in numpy: a single map on one side is paired with all
        maps of a time on the other, n maps with n maps one to one in the order
        of the datasets. Different numbers of several maps cannot be paired.

        :param positions: The result of ``_equal_time_positions`` for the list
            of map_i
        """
        position, count = positions[id(map_i)]
        groups = {}
        for map_j in related:
            groups.setdefault(map_j.get_temporal_extent_as_tuple(), []).append(map_j)
        partners = []
        for group in groups.values():
            if count == 1 or len(group) == 1:
                partners.extend(group)
            elif len(group) == count:
                partners.append(group[position])
            else:
                self.msgr.fatal(
                    _(
                        "Unable to pair {count} maps with {number} maps of equal "
                        "time stamps: <{map}> and <{maps}>"
                    ).format(
                        count=count,
                        number=len(group),
                        map=map_i.get_id(),
                        maps=",".join(map_j.get_id() for map_j in group),
                    )
                )
        return partners

    def _new_result_map(self, map_i):
        """Create the result map of an overlay for map_i: a copy of its extent.

        Hook: the vector algebra keeps the id of map_i instead (see there).
        """
        return self.generate_new_map(
            base_map=map_i, bool_op="and", copy=True, rename=True
        )

    def _related_maps(self, map_i, temporal_topo_list, spatial_topo_list):
        """Yield the maps which have one of the temporal relations to map_i.

        If spatial relations are given, a related map must also have one of
        them to map_i. The topology of the maps must have been built before.
        """
        temporal_relations = map_i.get_temporal_relations()
        for topology in temporal_topo_list:
            for map_j in temporal_relations.get(topology.upper(), ()):
                if self._check_spatial_topology_relation(
                    spatial_topo_list, map_i, map_j
                ):
                    yield map_j

    def remove_maps(self) -> None:
        """Removes empty or intermediate maps of different type."""

        map_names = {"raster": [], "raster3d": [], "vector": []}
        for map_i in self.removable_maps.values():
            map_names[map_i.get_type()].append(map_i.get_name())

        for map_type, names in map_names.items():
            if names:
                self.msgr.message(
                    _("Removing un-needed or empty {type} maps").format(type=map_type)
                )
                self._remove_maps(names, self._G_MODULE_TYPES[map_type])

    def _remove_maps(self, namelist, map_type) -> None:
        """Remove maps of specific type

        :param namelist: List of map names to be removed
        :param map_type: The type of the maps  (raster, raster_3d or vector)
        """
        chunk_size = 100
        chunklist = [
            namelist[i : i + chunk_size] for i in range(0, len(namelist), chunk_size)
        ]
        for chunk in chunklist:
            if self.run:
                module = copy.deepcopy(self.m_mremove)
                module.inputs["type"].value = map_type
                module.inputs["name"].value = ",".join(chunk)
                module.flags["f"].value = True
                self.process_chain_dict["remove"].append(module.get_dict())

                if self.dry_run is False:
                    module.run()

    def check_stds(
        self, input, clear: bool = False, stds_type=None, check_type: bool = True
    ):
        """Check if input space time dataset exist in database and return its map list.

        :param input: Name of space time data set as string or list of maps.
        :param clear: Reset the stored conditional values to empty list.
        :param check_type: Ignored, only kept for compatibility. The type of the
                           space time dataset is not checked here.
        :param stds_type: The type of the space time dataset to be opened, if not
                          provided then self.stdstype will be used

        :return: List of maps.
        """
        if isinstance(input, str):
            maplist = self._maplist_of_stds(input, stds_type)
        elif isinstance(input, self.mapclass):
            # A single map is returned as list with one entry.
            maplist = [input]
        elif isinstance(input, list):
            maplist = input
            for map_i in maplist:
                self._init_map_values(map_i, clear)
        elif self._reported_errors:
            # A faulty rule left None as its value. Its own message is the
            # cause; complaining about the type here would hide it.
            raise SyntaxError(self._reported_errors[0])
        else:
            self.msgr.fatal(_("Wrong type of input {input}").format(input=input))

        # We generate a unique map id that will be used
        # in the topology analysis, since the maplist can
        # contain maps with equal map ids
        for map_i in maplist:
            map_i.uid = self.generate_map_name()
            if self.debug:
                print(map_i.get_name(), map_i.uid, map_i.get_temporal_extent_as_tuple())

        return maplist

    def _maplist_of_stds(self, name, stds_type=None):
        """Return the registered maps of the space time dataset with this name.

        :param stds_type: The type of the dataset, default is self.stdstype
        :raises FatalError: if the dataset does not exist
        """
        # Check for mapset in given stds input.
        id_input = name if "@" in name else f"{name}@{self.mapset}"
        stds = dataset_factory(stds_type or self.stdstype, id_input)
        if stds.is_in_db(dbif=self.dbif) is False:
            raise FatalError(
                _("Space time {type} dataset <{id}> not found").format(
                    type=stds.get_new_map_instance(None).get_type(), id=id_input
                )
            )
        stds.select(dbif=self.dbif)
        if self.use_granularity:
            # We create the maplist out of the map array from none-gap objects
            granules = stds.get_registered_maps_as_objects_by_granularity(
                gran=self.granularity, dbif=self.dbif
            )
            maplist = [entry[0] for entry in granules if entry[0].get_id() is not None]
        else:
            maplist = stds.get_registered_maps_as_objects(dbif=self.dbif)
        for map_i in maplist:
            self._init_map_values(map_i)
            self._check_temporal_type(map_i, id_input)
        return maplist

    @staticmethod
    def _init_map_values(map_i, clear: bool = False) -> None:
        """Give the map empty lists for the values the algebra attaches to it"""
        for attribute in ("map_value", "condition_value"):
            if clear or not hasattr(map_i, attribute):
                setattr(map_i, attribute, [])

    def _check_temporal_type(self, map_i, id_input) -> None:
        """Set the temporal type of the expression or check the map against it"""
        if map_i.is_time_absolute():
            map_type = "absolute"
        elif map_i.is_time_relative():
            map_type = "relative"
        else:
            return
        if self.temporaltype is None:
            self.temporaltype = map_type
        elif self.temporaltype != map_type:
            self.msgr.fatal(
                _(
                    "Wrong temporal type of space time dataset "
                    "<{stds}> <{type}> time is required"
                ).format(stds=id_input, type=self.temporaltype)
            )

    def _check_spatial_topology_relation(self, spatial_topo_list, map_a, map_b):
        """Check if map_b has one of the spatial topological relations to map_a that is
        defined in spatial_topo_list

        :param spatial_topo_list:
        :param map_a:
        :param map_b:
        :return:
        """
        if not spatial_topo_list:
            return True
        spatial_relations = map_a.get_spatial_relations()
        return any(
            map_b in spatial_relations[topology]
            for topology in spatial_topo_list
            if topology in spatial_relations
        )

    def _check_topology(self, topolist):
        """Check the topology definitions of the expression

        :param topolist: List of strings of temporal and spatial relations.

        :return: A tuple of spatial and temporal topology lists
                (temporal_topo_list, spatial_topo_list)

        :raises SyntaxError:
            This method will raise a syntax error in case the topology name is unknown
        """
        temporal_topo_list = []
        spatial_topo_list = []
        for topo in topolist:
            name = topo.upper()
            if name in self.temporal_topology_list:
                temporal_topo_list.append(name)
            elif name in self.spatial_topology_list:
                spatial_topo_list.append(name)
            else:
                msg = f"Unpermitted topological relation name '{topo}'"
                raise SyntaxError(msg)

        return temporal_topo_list, spatial_topo_list

    def build_spatio_temporal_topology_list(
        self,
        maplistA,
        maplistB=None,
        topolist=("EQUAL",),
        assign_val: bool = False,
        count_map: bool = False,
        compare_bool: bool = False,
        compare_cmd: bool = False,
        compop=None,
        aggregate=None,
        convert: bool = False,
        operator_cmd: bool = False,
    ):
        """Build spatio-temporal topology for two space time data sets, copy map objects
        for given relation into map list.

        :param maplistA: List of maps.
        :param maplistB: List of maps.
        :param topolist: List of strings of spatio-temporal relations.
        :param assign_val: Boolean for assigning a boolean map value based on
                           the map_values from the compared map list by
                           topological relationships.
        :param count_map: Boolean if the number of topological related maps
                          should be returned.
        :param compare_bool: Boolean for comparing boolean map values based on
                             related map list and comparison operator.
        :param compare_cmd: Boolean for comparing command list values (hook
                    ``compare_cmd_value``, implemented by the raster algebra).
        :param compop: Comparison operator, && or ||; with ``operator_cmd`` the
                    operator of the algebra.
        :param aggregate: Aggregation operator for relation map list, & or \\|.
        :param convert: Boolean if conditional values should be converted to
                    command strings (``compare_cmd``).
        :param operator_cmd: Boolean for aggregating the commands of the related
                    maps with the operator ``compop`` (hook ``operator_cmd_value``).

        :return: List of maps from maplistA that fulfil the topological relationships
                 to maplistB specified in topolist.

        .. code-block:: pycon

            >>> # Example with two lists of maps
            >>> from datetime import datetime
            >>> import grass.temporal as tgis
            >>> tgis.init(True)
            >>> l = tgis.TemporalAlgebraParser()
            >>> # Create two list of maps with equal time stamps
            >>> mapsA = []
            >>> mapsB = []
            >>> for i in range(10):
            ...     idA = "a%i@B" % (i)
            ...     mapA = tgis.RasterDataset(idA)
            ...     mapA.uid = idA
            ...     idB = "b%i@B" % (i)
            ...     mapB = tgis.RasterDataset(idB)
            ...     mapB.uid = idB
            ...     check = mapA.set_relative_time(i, i + 1, "months")
            ...     check = mapB.set_relative_time(i, i + 1, "months")
            ...     mapsA.append(mapA)
            ...     mapsB.append(mapB)
            >>> resultlist = l.build_spatio_temporal_topology_list(
            ...     mapsA, mapsB, ["EQUAL"]
            ... )
            >>> for map in resultlist:
            ...     if map.get_equal():
            ...         relations = map.get_equal()
            ...         print(
            ...             "Map %s has equal relation to map %s"
            ...             % (map.get_name(), relations[0].get_name())
            ...         )
            Map a0 has equal relation to map b0
            Map a1 has equal relation to map b1
            Map a2 has equal relation to map b2
            Map a3 has equal relation to map b3
            Map a4 has equal relation to map b4
            Map a5 has equal relation to map b5
            Map a6 has equal relation to map b6
            Map a7 has equal relation to map b7
            Map a8 has equal relation to map b8
            Map a9 has equal relation to map b9
            >>> resultlist = l.build_spatio_temporal_topology_list(
            ...     mapsA, mapsB, ["DURING"]
            ... )
            >>> print(resultlist)
            []
            >>> # Create two list of maps with equal time stamps
            >>> mapsA = []
            >>> mapsB = []
            >>> for i in range(10):
            ...     idA = "a%i@B" % (i)
            ...     mapA = tgis.RasterDataset(idA)
            ...     mapA.uid = idA
            ...     idB = "b%i@B" % (i)
            ...     mapB = tgis.RasterDataset(idB)
            ...     mapB.uid = idB
            ...     check = mapA.set_relative_time(i, i + 1, "months")
            ...     check = mapB.set_relative_time(i, i + 2, "months")
            ...     mapsA.append(mapA)
            ...     mapsB.append(mapB)
            >>> resultlist = l.build_spatio_temporal_topology_list(
            ...     mapsA, mapsB, ["starts", "during"]
            ... )
            >>> for map in resultlist:
            ...     if map.get_starts():
            ...         relations = map.get_starts()
            ...         print(
            ...             "Map %s has start relation to map %s"
            ...             % (map.get_name(), relations[0].get_name())
            ...         )
            Map a0 has start relation to map b0
            Map a1 has start relation to map b1
            Map a2 has start relation to map b2
            Map a3 has start relation to map b3
            Map a4 has start relation to map b4
            Map a5 has start relation to map b5
            Map a6 has start relation to map b6
            Map a7 has start relation to map b7
            Map a8 has start relation to map b8
            Map a9 has start relation to map b9
            >>> for map in resultlist:
            ...     if map.get_during():
            ...         relations = map.get_during()
            ...         print(
            ...             "Map %s has during relation to map %s"
            ...             % (map.get_name(), relations[0].get_name())
            ...         )
            Map a0 has during relation to map b0
            Map a1 has during relation to map b0
            Map a2 has during relation to map b1
            Map a3 has during relation to map b2
            Map a4 has during relation to map b3
            Map a5 has during relation to map b4
            Map a6 has during relation to map b5
            Map a7 has during relation to map b6
            Map a8 has during relation to map b7
            Map a9 has during relation to map b8
            >>> # Create two list of maps with equal time stamps and map_value method.
            >>> mapsA = []
            >>> mapsB = []
            >>> for i in range(10):
            ...     idA = "a%i@B" % (i)
            ...     mapA = tgis.RasterDataset(idA)
            ...     mapA.uid = idA
            ...     idB = "b%i@B" % (i)
            ...     mapB = tgis.RasterDataset(idB)
            ...     mapB.uid = idB
            ...     check = mapA.set_relative_time(i, i + 1, "months")
            ...     check = mapB.set_relative_time(i, i + 1, "months")
            ...     mapB.map_value = True
            ...     mapsA.append(mapA)
            ...     mapsB.append(mapB)
            >>> # Create two list of maps with equal time stamps
            >>> mapsA = []
            >>> mapsB = []
            >>> for i in range(10):
            ...     idA = "a%i@B" % (i)
            ...     mapA = tgis.RasterDataset(idA)
            ...     mapA.uid = idA
            ...     mapA.map_value = True
            ...     idB = "b%i@B" % (i)
            ...     mapB = tgis.RasterDataset(idB)
            ...     mapB.uid = idB
            ...     mapB.map_value = False
            ...     check = mapA.set_absolute_time(
            ...         datetime(2000, 1, i + 1), datetime(2000, 1, i + 2)
            ...     )
            ...     check = mapB.set_absolute_time(
            ...         datetime(2000, 1, i + 6), datetime(2000, 1, i + 7)
            ...     )
            ...     mapsA.append(mapA)
            ...     mapsB.append(mapB)
            >>> resultlist = l.build_spatio_temporal_topology_list(mapsA, mapsB)
            >>> for map in resultlist:
            ...     print(map.get_id())
            a5@B
            a6@B
            a7@B
            a8@B
            a9@B
            >>> resultlist = l.build_spatio_temporal_topology_list(
            ...     mapsA, mapsB, ["during"]
            ... )
            >>> for map in resultlist:
            ...     print(map.get_id())

        """
        # Check the topology definitions and return the list of temporal and spatial
        # topological relations that must be fulfilled
        topolist = ("EQUAL",) if topolist is None else topolist
        temporal_topo_list, spatial_topo_list = self._check_topology(topolist=topolist)
        if self.spatial and not spatial_topo_list:
            # Select only spatially related maps, whatever the relation is
            spatial_topo_list = list(self.spatial_topology_list)

        self._build_topology(maplistA, maplistB, bool(spatial_topo_list))

        resultdict = {}
        for map_i in maplistA:
            if assign_val:
                self.assign_bool_value(map_i, temporal_topo_list, spatial_topo_list)
            elif compare_bool:
                self.compare_bool_value(
                    map_i, compop, aggregate, temporal_topo_list, spatial_topo_list
                )
            elif compare_cmd:
                self.compare_cmd_value(
                    map_i,
                    compop,
                    aggregate,
                    temporal_topo_list,
                    spatial_topo_list,
                    convert,
                )
            elif operator_cmd:
                self.operator_cmd_value(
                    map_i, compop, temporal_topo_list, spatial_topo_list
                )

            related = list(
                self._related_maps(map_i, temporal_topo_list, spatial_topo_list)
            )
            if not related:
                continue
            if count_map:
                gvar = GlobalTemporalVar()
                gvar.td = len(related)
                self._add_map_value(map_i, gvar)
            # Use unique identifier, since map names may be equal
            resultdict[map_i.uid] = map_i

        # Sort list of maps chronological.
        return sorted(resultdict.values(), key=AbstractDatasetComparisonKeyStartTime)

    def _build_topology(self, maplistA, maplistB, spatial: bool) -> None:
        """Build the temporal and, if requested, the spatial topology of the maps"""
        builder = SpatioTemporalTopologyBuilder()
        if spatial:
            builder.build(
                maplistA, maplistB, spatial=self._SPATIAL_DIMENSIONS[self.stdstype]
            )
        else:
            builder.build(maplistA, maplistB)

    def assign_bool_value(
        self, map_i, temporal_topo_list=("EQUAL",), spatial_topo_list=()
    ) -> bool:
        """Function to assign boolean map value based on the map_values from the
        compared map list by topological relationships.

          :param map_i: Map object with temporal extent.
          :param temporal_topo_list: List of strings for given temporal relations.
          :param spatial_topo_list: List of strings for given spatial relations.

          :return: Map object with conditional value that has been assigned by
                        relation maps that fulfil the topological relationships to
                        maplistB specified in temporal_topo_list.
        """
        result = all(
            self._condition_booleans(map_i, temporal_topo_list, spatial_topo_list)
        )
        map_i.condition_value = [result]

        return result

    def _condition_booleans(self, map_i, temporal_topo_list, spatial_topo_list):
        """Yield the booleans among the condition values of the related maps"""
        for related in self._related_maps(map_i, temporal_topo_list, spatial_topo_list):
            for value in related.condition_value:
                if isinstance(value, bool):
                    yield value

    def compare_bool_value(
        self,
        map_i,
        compop,
        aggregate,
        temporal_topo_list=("EQUAL",),
        spatial_topo_list=(),
    ):
        """Function to evaluate two map lists with boolean values by boolean
          comparison operator.

        :param map_i: Map object with temporal extent.
        :param compop: Comparison operator, && or ||.
        :param aggregate: Aggregation operator for relation map list, & or \\|.
        :param temporal_topo_list: List of strings for given temporal relations.
        :param spatial_topo_list: List of strings for given spatial relations.

        :return: Map object with conditional value that has been evaluated by
                      comparison operators.
        """
        left = map_i.condition_value[0]
        if not isinstance(left, bool):
            msg = f"Condition value must be a bool, got {type(left)}"
            raise TypeError(msg)
        related = list(
            self._condition_booleans(map_i, temporal_topo_list, spatial_topo_list)
        )
        # Without related maps nothing is combined with the value of the map
        if related:
            left = self._combine_booleans(
                compop, [left, self._combine_booleans(aggregate, related)]
            )
        map_i.condition_value = [left]

        return left

    def compare_cmd_value(
        self,
        map_i,
        compop,
        aggregate,
        temporal_topo_list=None,
        spatial_topo_list=None,
        convert: bool = False,
    ):
        """Hook of ``build_spatio_temporal_topology_list``: compare the command
        list values of map_i with those of its related maps.

        Only the algebras which build commands for the maps (raster) implement it.
        """
        raise NotImplementedError

    def operator_cmd_value(
        self, map_i, operator, temporal_topo_list=None, spatial_topo_list=None
    ):
        """Hook of ``build_spatio_temporal_topology_list``: aggregate the commands
        of the maps related to map_i with the operator.

        Only the algebras which build commands for the maps (raster, vector)
        implement it.
        """
        raise NotImplementedError

    @staticmethod
    def _combine_booleans(operator, values) -> bool:
        """Combine booleans with the operator & (and) or | (or), also as && and ||"""
        if operator in {"&", "&&"}:
            return all(values)
        if operator in {"|", "||"}:
            return any(values)
        msg = f"Unknown boolean operator: {operator}"
        raise ValueError(msg)

    def eval_toperator(self, operator, optype="relation"):
        """This function evaluates a string containing temporal operations.

        :param operator: String of temporal operations, e.g. {!=,equal|during,l}.
        :param optype: String to define operator type.
        :return: List of temporal relations (equal, during), the given function
            (!:) and the interval/instances (l).

        .. code-block:: pycon

            >>> import grass.temporal as tgis
            >>> tgis.init()
            >>> p = tgis.TemporalOperatorParser()
            >>> operator = "{+, during}"
            >>> p.parse(operator, optype="raster")
            >>> print((p.relations, p.temporal, p.function))
            (['during'], 'l', '+')

        """
        p = TemporalOperatorParser()
        try:
            p.parse(operator, optype)
        except SyntaxError as error:
            # Called from grammar rules, where PLY swallows the SyntaxError;
            # unknown relation names would otherwise be ignored silently.
            self._report_error(str(error))
            raise
        p.relations = [rel.upper() for rel in p.relations]

        return (p.relations, p.temporal, p.function, p.aggregate)

    def perform_temporal_selection(
        self,
        maplistA,
        maplistB,
        topolist=("EQUAL",),
        inverse: bool = False,
        assign_val: bool = False,
    ):
        """This function performs temporal selection operation.

        :param maplistA:   List of maps representing the left side of a temporal
                           expression.
        :param maplistB:   List of maps representing the right side of a temporal
                           expression.
        :param topolist: List of strings of temporal relations.
        :param inverse: Boolean value that specifies if the selection should be
                           inverted.
        :param assign_val: Boolean for assigning a boolean map value based on
                          the map_values from the compared map list by
                          topological relationships.

        :return: List of selected maps from maplistA.

        .. code-block:: pycon

            >>> import grass.temporal as tgis
            >>> tgis.init()
            >>> l = tgis.TemporalAlgebraParser()
            >>> # Example with two lists of maps
            >>> # Create two list of maps with equal time stamps
            >>> mapsA = []
            >>> mapsB = []
            >>> for i in range(10):
            ...     idA = "a%i@B" % (i)
            ...     mapA = tgis.RasterDataset(idA)
            ...     mapA.uid = idA
            ...     idB = "b%i@B" % (i)
            ...     mapB = tgis.RasterDataset(idB)
            ...     mapB.uid = idB
            ...     check = mapA.set_relative_time(i, i + 1, "months")
            ...     check = mapB.set_relative_time(i + 5, i + 6, "months")
            ...     mapsA.append(mapA)
            ...     mapsB.append(mapB)
            >>> resultlist = l.perform_temporal_selection(
            ...     mapsA, mapsB, ["EQUAL"], False
            ... )
            >>> for map in resultlist:
            ...     if map.get_equal():
            ...         relations = map.get_equal()
            ...         print(
            ...             "Map %s has equal relation to map %s"
            ...             % (map.get_name(), relations[0].get_name())
            ...         )
            Map a5 has equal relation to map b0
            Map a6 has equal relation to map b1
            Map a7 has equal relation to map b2
            Map a8 has equal relation to map b3
            Map a9 has equal relation to map b4
            >>> resultlist = l.perform_temporal_selection(mapsA, mapsB, ["EQUAL"], True)
            >>> for map in resultlist:
            ...     if not map.get_equal():
            ...         print(
            ...             "Map %s has no equal relation to mapset mapsB"
            ...             % (map.get_name())
            ...         )
            Map a0 has no equal relation to mapset mapsB
            Map a1 has no equal relation to mapset mapsB
            Map a2 has no equal relation to mapset mapsB
            Map a3 has no equal relation to mapset mapsB
            Map a4 has no equal relation to mapset mapsB

        """
        selected = self.build_spatio_temporal_topology_list(
            maplistA, maplistB, topolist, assign_val=assign_val
        )
        if inverse:
            selected = [map_i for map_i in maplistA if map_i not in selected]

        # Sort list of maps chronological.
        return sorted(selected, key=AbstractDatasetComparisonKeyStartTime)

    def set_granularity(self, maplistA, maplistB, toperator="l", topolist=("EQUAL",)):
        """This function sets the temporal extends of a list of maps based on
           another map list.

        :param maplistB: List of maps.
        :param maplistB: List of maps.
        :param toperator: String containing the temporal operator: l, r, d, i, u.
        :param topolist: List of topological relations.

        :return: List of maps with the new temporal extends.

        .. code-block:: pycon

            >>> import grass.temporal as tgis
            >>> tgis.init()
            >>> p = tgis.TemporalAlgebraParser()
            >>> # Create two list of maps with equal time stamps
            >>> mapsA = []
            >>> mapsB = []
            >>> for i in range(10):
            ...     idA = "a%i@B" % (i)
            ...     mapA = tgis.RasterDataset(idA)
            ...     mapA.uid = idA
            ...     idB = "b%i@B" % (i)
            ...     mapB = tgis.RasterDataset(idB)
            ...     mapB.uid = idB
            ...     check = mapA.set_relative_time(i, i + 1, "months")
            ...     check = mapB.set_relative_time(i * 2, i * 2 + 2, "months")
            ...     mapsA.append(mapA)
            ...     mapsB.append(mapB)
            >>> resultlist = p.set_granularity(
            ...     mapsA, mapsB, toperator="u", topolist=["during"]
            ... )
            >>> for map in resultlist:
            ...     start, end, unit = map.get_relative_time()
            ...     print(
            ...         map.get_id() + " - start: " + str(start) + " end: " + str(end)
            ...     )
            a1@B - start: 0 end: 2
            a0@B - start: 0 end: 2
            a3@B - start: 2 end: 4
            a2@B - start: 2 end: 4
            a5@B - start: 4 end: 6
            a4@B - start: 4 end: 6
            a7@B - start: 6 end: 8
            a6@B - start: 6 end: 8
            a9@B - start: 8 end: 10
            a8@B - start: 8 end: 10

        :raises SyntaxError: If an unpermitted temporal relation name is used in ``topolist``
        """
        for topo in topolist:
            if topo.upper() not in self.temporal_topology_list:
                msg = f"Unpermitted temporal relation name '{topo}'"
                raise SyntaxError(msg)

        self._build_topology(maplistA, maplistB, self.spatial)

        resultdict = {}
        for map_i in maplistA:
            tbrelations = map_i.get_temporal_relations()
            for topo in topolist:
                if topo.upper() not in tbrelations:
                    # The map keeps its extent
                    resultdict[map_i.get_id()] = map_i
                    continue
                for relationmap in tbrelations[topo.upper()]:
                    extent = self._extent_by_operator(map_i, relationmap, toperator)
                    if extent is not None:
                        self._set_temporal_extent(map_i, extent)
                        resultdict[map_i.get_id()] = map_i

        return sorted(resultdict.values(), key=AbstractDatasetComparisonKeyStartTime)

    def _extent_by_operator(self, map_i, relationmap, toperator):
        """Return the temporal extent of map_i after applying the temporal operator
        (l, r, i, u, d) with the related map, or None for an unknown operator"""
        if toperator == "l":
            return map_i.get_temporal_extent()
        if toperator == "r":
            return relationmap.get_temporal_extent()
        if toperator in self._TEMPORAL_OVERLAY:
            return getattr(map_i, self._TEMPORAL_OVERLAY[toperator])(relationmap)
        return None

    @staticmethod
    def _set_temporal_extent(map_i, extent) -> None:
        """Set the extent of the map in the time type and unit of the map"""
        start = extent.get_start_time()
        end = extent.get_end_time()
        if map_i.is_time_absolute():
            map_i.set_absolute_time(start, end)
        else:
            map_i.set_relative_time(
                int(start), int(end), map_i.get_relative_time_unit()
            )

    def get_temporal_func_dict(self, map):  # noqa: A002 (name of the public API)
        """This function creates a dictionary containing temporal functions for a
           map dataset with time stamp.

        :param map: Map object with time stamps.

        :return: Dictionary with temporal functions for given input map.

        .. code-block:: pycon

            >>> import grass.temporal as tgis
            >>> import datetime
            >>> tgis.init()
            >>> l = tgis.TemporalAlgebraParser()
            >>> # Example with one list of maps
            >>> # Create one list of maps with equal time stamps
            >>> for i in range(1):
            ...     idA = "a%i@B" % (i)
            ...     mapA = tgis.RasterDataset(idA)
            ...     mapA.uid = idA
            ...     check = mapA.set_absolute_time(
            ...         datetime.datetime(2000, 1, 1), datetime.datetime(2000, 10, 1)
            ...     )
            ...     tfuncdict = l.get_temporal_func_dict(mapA)
            >>> print(tfuncdict["START_YEAR"])
            2000
            >>> print(tfuncdict["START_TIME"])
            00:00:00
            >>> print(tfuncdict["START_DATE"])
            2000-01-01
            >>> print(tfuncdict["START_DATETIME"])
            2000-01-01 00:00:00

        """
        map_i = map
        tvardict = {
            f"{side}_{field}": None
            for side in ("START", "END")
            for field in _TIME_FIELDS
        }

        # The functions are defined for absolute time only. Values which cannot
        # be computed (relative time, end of a time instance) stay None.
        if not map_i.is_time_absolute():
            return tvardict
        start, end = map_i.get_absolute_time()
        for side, timestamp in (("START", start), ("END", end)):
            if timestamp is None:
                continue
            for field, getter in _TIME_FIELDS.items():
                tvardict[f"{side}_{field}"] = getter(timestamp)
        return tvardict

    def compare_values(self, left, comp, right):
        """Compare two values with the given comparison operator."""
        if comp not in _COMPARISONS:
            msg = f"Unknown comparison operator: {comp}"
            raise ValueError(msg)
        return _COMPARISONS[comp](left, right)

    def eval_datetime_str(self, tfuncval, comp, value):
        """Compare two values with the given comparison operator.

        .. deprecated:: 8.6.0
            Use :func:`compare_values` instead.
        """
        return self.compare_values(tfuncval, comp, value)

    def eval_global_var(self, gvar, maplist):
        """This function evaluates a global variable expression for a map list.
           For example: start_day() > 5 , end_month() == 2.

        :param gvar: Object of type GlobalTemporalVar containing temporal.
        :param maplist: List of map objects.

        :return: List of maps from maplist with added conditional boolean values.
        """
        tfunc = gvar.tfunc.upper()
        for map_i in maplist:
            tfuncval = self._temporal_function_value(gvar.tfunc, map_i)
            # The literal has to have the same type as the function value,
            # otherwise the comparison fails or, for ==, is always False.
            value = self._literal_like(tfunc, gvar.value)
            self._add_condition_value(
                map_i, self.compare_values(tfuncval, gvar.compop, value)
            )
        return maplist

    def _temporal_function_value(self, function, map_i):
        """Return the value of a temporal function such as end_month for the map

        :raises FatalError: if the map has no such value, which is the case for
                            relative time and for end functions of an instant
        """
        value = self.get_temporal_func_dict(map_i)[function.upper()]
        if value is None:
            self.msgr.fatal(
                _(
                    "Temporal function {func}() is not available for map <{map}>."
                    " It requires absolute time, end time functions also an end"
                    " time."
                ).format(func=function, map=map_i.get_id())
            )
        return value

    @staticmethod
    def _literal_like(tfunc, value):
        """Convert the string literal of a date, time or datetime function.

        Numbers (from the INT and FLOAT tokens) are used as they are.
        """
        if tfunc.endswith("_DATETIME"):
            return string_to_datetime(value.replace('"', ""))
        if tfunc.endswith("_DATE"):
            return string_to_datetime(value.replace('"', "")).date()
        if tfunc.endswith("_TIME"):
            return string_to_datetime(value.replace('"', "")).time()
        return value

    @staticmethod
    def _add_condition_value(map_i, value) -> None:
        """Append the boolean to the condition values of the map"""
        if hasattr(map_i, "condition_value"):
            map_i.condition_value.append(value)
        else:
            map_i.condition_value = value

    @staticmethod
    def _add_map_value(map_i, value) -> None:
        """Append the value to the map values of the map"""
        if hasattr(map_i, "map_value"):
            map_i.map_value.append(value)
        else:
            map_i.map_value = value

    def eval_map_list(self, maplist, thenlist, topolist=("EQUAL",)):
        """This function transfers boolean values from temporal expression
           from one map list to another by their topology. These boolean
           values are added to the maps as condition_value.

        :param maplist:  List of map objects containing boolean map values.
        :param thenlist: List of map objects where the boolean values
                        should be added.
        :param topolist: The relations of if({R}, condition, conclusion),
                         which read "condition R conclusion"

        :return: List of maps from thenlist with added conditional boolean values.
        """
        # The selection keeps the maps of thenlist that are related to a map
        # of maplist, which reads from conclusion to condition.
        return self.perform_temporal_selection(
            thenlist,
            maplist,
            assign_val=True,
            topolist=[_INVERSE_RELATIONS[name.upper()] for name in topolist],
        )

    def build_condition_list(self, tvarexpr, thenlist, topolist=("EQUAL",)):
        """This function evaluates temporal variable expressions of a conditional
        expression in two steps.
        At first it combines stepwise the single conditions by their relations with
        LALR. In this process sub condition map lists will be created which will
        include information of the underlying single conditions. Important: The
        temporal relations between conditions are evaluated by implicit aggregation.
        In the second step the aggregated condition map list will be compared with the
        map list of conclusion statements by the given temporal relation.

        The result is written as 'condition_value' attribute to the resulting map
        objects. These attribute consists of boolean expressions and operators which
        can be evaluated with the eval_condition_list function.
        [True,  '||', False, '&&', True]

        For example: td(A) == 1 && start_day() > 5 --> [True || False]
                     (for one map.condition_value in a then map list)

        :param tvarexpr: List of GlobalTemporalVar objects and map lists.
                    The list is constructed by the TemporalAlgebraParser
                    in order of expression evaluation in the parser.

        :param thenlist: Map list object of the conclusion statement.
                    It will be compared and evaluated by the conditions.

        :param topolist: List of temporal relations between the conditions and the
                    conclusions.

        :return: Map list with conditional values for all temporal expressions.

        """
        if isinstance(tvarexpr, GlobalTemporalVar) and tvarexpr.get_type() == "global":
            resultlist = self.eval_global_var(tvarexpr, thenlist)
        elif isinstance(tvarexpr, list) and all(
            isinstance(ele, AbstractMapDataset) for ele in tvarexpr
        ):
            resultlist = self.eval_map_list(tvarexpr, thenlist, topolist)
        else:
            msg = (
                "A condition must be a global temporal variable or a list of "
                "maps with condition values"
            )
            raise ValueError(msg)

        # Sort resulting list of maps chronological.
        return sorted(resultlist, key=AbstractDatasetComparisonKeyStartTime)

    def eval_condition_list(self, maplist, inverse: bool = False):
        """This function evaluates conditional values of a map list.
        A recursive function is used to evaluate comparison statements
        from left to right in the given conditional list.

        For example::

             - [True,  '||', False, '&&', True]  -> True
             - [True,  '||', False, '&&', False] -> False
             - [True,  '&&', False, '&&', True]  -> False
             - [False, '||', True,  '||', False] -> True
             - [False, '&&', True,  '&&', True]  -> False
             - [True,  '&&', True,  '&&', True]  -> True
             - [True,  '&&', True]               -> True
             - [True,  '&&', False]              -> False
             - [False, '||', True]               -> True

        :param maplist: A list of maps
        :param inverse:
        :return: Map list with conditional values evaluated
        """
        selected = []
        rejected = []
        for map_i in maplist:
            if not hasattr(map_i, "condition_value"):
                continue
            result = self._evaluate_conditions(map_i.condition_value)
            map_i.condition_value = [result]
            (selected if result else rejected).append(map_i)
        return rejected if inverse else selected

    @staticmethod
    def _evaluate_conditions(conditions) -> bool:
        """Evaluate [value, operator, value, ...] from left to right.

        && and || have the same precedence. The values are booleans.
        """
        if len(conditions) % 2 == 0:
            msg = f"Incomplete list of conditions: {conditions}"
            raise ValueError(msg)
        result = conditions[0]
        for operator, value in zip(conditions[1::2], conditions[2::2], strict=True):
            if operator == "&&":
                result = result and value
            elif operator == "||":
                result = result or value
            else:
                msg = f"Unknown boolean operator: {operator}"
                raise ValueError(msg)
        return result

    def p_statement_assign(self, t) -> None:
        # The expression should always return a list of maps
        # This function starts all the work and is the last one that is called from the
        # parser
        """
        statement : stds EQUALS expr

        """
        t[0] = t[3]
        if self.run and isinstance(t[3], list):
            self._create_result(t[1], t[3])
        self._trace(t[1], "=", t[3])

    def _create_result(self, stds_name, maps):
        """Make the maps of the expression real and register them in a new dataset.

        The steps are hooks which the algebras override where they differ in
        what a result map is: ``_needs_new_map`` and ``_materialize_maps``
        (copy, mapcalc, overlay), ``_handle_empty_result`` and the names via
        ``_first_result_number``. Naming, the check for existing maps, the
        registration and the removal of intermediate maps are shared.

        :param stds_name: Name of the result dataset
        :param maps: The maps of the expression, possibly with commands
        :return: The list of result maps
        """
        dbif, connection_state_changed = init_dbif(self.dbif)
        try:
            names = self._result_map_names(maps, stds_name)
            needs_new = [self._needs_new_map(map_i, dbif) for map_i in maps]
            # All names are checked before any map is created, so that no
            # result is partly overwritten.
            self._check_result_maps_absent(
                [name for name, new in zip(names, needs_new, strict=True) if new]
            )
            result_maps = self._materialize_maps(maps, names, needs_new)
            if result_maps:
                self._register_result_maps(stds_name, result_maps, dbif)
            else:
                self._handle_empty_result(stds_name)
            self.remove_maps()
        finally:
            if connection_state_changed:
                dbif.close()
        return result_maps

    def _handle_empty_result(self, stds_name) -> None:
        """Hook: warn about a result without maps and create the empty dataset."""
        self.msgr.warning(
            _(
                "Empty result space time dataset. No map has been registered in {name}"
            ).format(name=stds_name)
        )
        if self.dry_run is False:
            resultstds = self._open_result_stds(
                stds_name, self.stdstype, self._result_temporal_type([])
            )
            # Without it the metadata of the empty dataset stay None, not 0
            resultstds.update_from_registered_maps(self.dbif)

    def _result_temporal_type(self, maps):
        """Return the temporal type of the result: the type of its maps, or of
        the datasets read so far if there is no map."""
        if maps:
            return "absolute" if maps[0].is_time_absolute() else "relative"
        return self.temporaltype or "absolute"

    def _needs_new_map(self, map_i, dbif) -> bool:
        """Hook: tell if the result needs a new map for map_i.

        Here: only if its temporal extent differs from the stored one, which
        the temporal operators, the buffer, shift and snap functions cause. The
        original maps stay untouched then.
        """
        stored = map_i.get_new_instance(map_i.get_id())
        stored.select(dbif)
        return map_i.get_temporal_extent_as_tuple() != (
            stored.get_temporal_extent_as_tuple()
        )

    def _materialize_maps(self, maps, names, needs_new):
        """Hook: create the new maps and return the maps to register.

        Here: the maps flagged in needs_new are copied under their names, the
        others are registered as they are.

        :param names: The result name of each map
        :param needs_new: Per map, the answer of ``_needs_new_map``
        """
        queue = None
        if self.dry_run is False:
            queue = pymod.ParallelModuleQueue(int(self.nprocs))
        result_maps = [
            self._copy_map(map_i, name, queue) if new else map_i
            for map_i, name, new in zip(maps, names, needs_new, strict=True)
        ]
        if queue is not None:
            queue.wait()
        return result_maps

    def _time_granularity(self, maps):
        """Return the granularity for the time suffix "gran", else None"""
        if maps and self.time_suffix == "gran" and maps[0].is_time_absolute():
            return compute_absolute_time_granularity(maps)
        return None

    # Number of the first result map in the numeric suffix of the names
    _first_result_number = 1

    def _result_map_names(self, maps, stds_name):
        """Return the names (without mapset) of the result maps: the basename
        (default: the name of the result dataset) with a number or, as
        requested by ``time_suffix``, a time suffix."""
        granularity = self._time_granularity(maps)
        digits = len(str(len(maps)))
        basename = self.basename or stds_name
        return [
            self._result_map_name(basename, map_i, number, digits, granularity)
            for number, map_i in enumerate(maps, start=self._first_result_number)
        ]

    def _result_map_name(self, basename, map_i, number, digits, granularity):
        """Return the name of a result map: basename plus numeric or time suffix"""
        absolute = map_i.is_time_absolute()
        if absolute and self.time_suffix == "gran" and granularity:
            suffix = create_suffix_from_datetime(
                map_i.temporal_extent.get_start_time(), granularity
            )
        elif absolute and self.time_suffix == "time":
            suffix = create_time_suffix(map_i)
        else:
            return create_numeric_suffix(basename, number, "%0" + str(digits))
        return f"{basename}_{suffix}"

    def _check_result_maps_absent(self, names) -> None:
        """Stop if a result map exists and overwriting is not enabled"""
        if self.overwrite:
            return
        for name in names:
            ident = f"{name}@{self.mapset}"
            if self.mapclass(ident).map_exists():
                self.msgr.fatal(
                    _(
                        "Error maps with basename {name} exist. "
                        "Use --o flag to overwrite existing file"
                    ).format(name=ident)
                )

    def _open_result_stds(self, name, stds_type, temporal_type):
        """Create the space time dataset with the result of the expression"""
        return open_new_stds(
            name,
            stds_type,
            temporal_type,
            name,
            name,
            "mean",
            self.dbif,
            overwrite=self.overwrite,
        )

    def _register_result_maps(self, stds_name, maplist, dbif) -> None:
        """Register the result maps in a new dataset of the temporal type of the maps"""
        stds_type = self._check_result_maps(maplist)
        temporal_type = self._result_temporal_type(maplist)

        resultstds = None
        if self.dry_run is False:
            resultstds = self._open_result_stds(stds_name, stds_type, temporal_type)

        for map_i in maplist:
            if self.dry_run is False:
                map_i.load()
            start, end = map_i.get_temporal_extent_as_tuple()
            self.process_chain_dict["register"].append(
                (map_i.get_name(), str(start), str(end))
            )
            self._register_map(map_i, resultstds, dbif)

        if resultstds is not None:
            resultstds.update_from_registered_maps(dbif)

        self.process_chain_dict["STDS"]["name"] = stds_name
        self.process_chain_dict["STDS"]["stdstype"] = self.stdstype
        self.process_chain_dict["STDS"]["temporal_type"] = temporal_type

    def _register_map(self, map_i, resultstds, dbif) -> None:
        """Store a new map in the temporal database and register it in the dataset.

        Maps which are not new exist in the database already, but a selected
        map of another mapset only in the database of its own mapset.
        """
        if hasattr(map_i, "is_new"):
            if not self._store_new_map(map_i, dbif):
                return
        elif self.dry_run is False and not map_i.is_in_db(dbif, mapset=self.mapset):
            # Reference the map instead of copying it, as t.register does.
            map_i.insert(dbif)
        if resultstds is not None and not resultstds.register_map(map_i, dbif):
            self.msgr.warning(
                _("Unable to register map layers in STDS {name}").format(
                    name=resultstds.get_name()
                )
            )

    def _check_result_maps(self, maplist):
        """Check that the maps are of one type and return the STDS type for them"""
        stds_type = maplist[0].get_new_stds_instance(None).get_type()
        if stds_type != self.stdstype:
            self.msgr.warning(
                _(
                    "The resulting space time dataset type <{result}> "
                    "is different from the requested type <{requested}>"
                ).format(result=stds_type, requested=self.stdstype)
            )
        map_type = maplist[0].get_type()
        if any(map_i.get_type() != map_type for map_i in maplist[1:]):
            self.msgr.fatal(
                _(
                    "Maps that should be registered in the "
                    "resulting space time dataset have different "
                    "types."
                )
            )
        return stds_type

    def _copy_map(self, map_i, name, process_queue):
        """Copy the map under the name, the copy gets the extent of the map.

        :return: The new map object, marked with the attribute ``is_new``
        """
        map_result = map_i.get_new_instance(f"{name}@{self.mapset}")
        map_result.set_temporal_extent(map_i.get_temporal_extent())
        map_result.set_spatial_extent(map_i.get_spatial_extent())
        map_result.is_new = True

        module = copy.deepcopy(self.m_copy)
        module.flags["overwrite"].value = self.overwrite
        module.inputs[self._G_MODULE_TYPES[map_i.get_type()]].value = (
            map_i.get_id(),
            name,
        )
        self.process_chain_dict["processes"].append(module.get_dict())
        if process_queue is not None:
            process_queue.put(module)
        return map_result

    def _store_new_map(self, map_i, dbif) -> bool:
        """Insert or update a new map in the temporal database.

        :return: False if the map is empty and must not be registered
        """
        # Do not register empty (null) maps if not required
        # A dry run computes nothing, so the maps cannot be empty there.
        if (
            self.dry_run is False
            and map_i.get_type() in {"raster", "raster3d"}
            and map_i.metadata.get_min() is None
            and map_i.metadata.get_max() is None
            and not self.register_null
        ):
            self.removable_maps[map_i.get_name()] = map_i
            return False

        if map_i.is_in_db(dbif):
            if not self.overwrite:
                self.msgr.fatal(
                    _(
                        "Map <{name}> exists in the temporal database. Use the overwrite flag."
                    ).format(name=map_i.get_map_id())
                )
            if self.dry_run is False:
                stored = map_i.get_new_instance(map_i.get_id())
                stored.select(dbif)
                if stored.get_temporal_type() == map_i.get_temporal_type():
                    map_i.update_all(dbif)
                else:
                    # Measured 2026-10-11 (A + N, then RT * 2, same names):
                    # update_all() sets the new type in the base table, but
                    # its UPDATE of the time table of the new type matches no
                    # row, so the maps get no time, while the row of the old
                    # type stays behind. Delete() is called on the stored
                    # copy because it resets the instance, which would
                    # discard the time of map_i.
                    stored.delete(dbif)
                    map_i.insert(dbif)
        elif self.dry_run is False:
            map_i.insert(dbif)
        return True

    def p_stds_1(self, t) -> None:
        # Definition of a space time dataset
        """
        stds : NAME
        """
        t[0] = t[1]

    def p_paren_expr(self, t) -> None:
        """expr : LPAREN expr RPAREN"""
        t[0] = t[2]

    def p_number(self, t) -> None:
        """number : INT
        | FLOAT
        """
        t[0] = t[1]

    def p_expr_strds_function(self, t) -> None:
        # Explicitly specify a space time raster dataset
        # R = A : strds(B)
        """
        expr : STRDS LPAREN stds RPAREN
        """
        t[0] = self._typed_stds(t[3], "strds")

    def _typed_stds(self, name, stds_type):
        """The maps of the dataset of this type, or a placeholder if not running"""
        if self.run:
            return self.check_stds(name, stds_type=stds_type, check_type=False)
        return name

    def p_expr_str3ds_function(self, t) -> None:
        # Explicitly specify a space time raster dataset
        # R = A : str3ds(B)
        """
        expr : STR3DS LPAREN stds RPAREN
        """
        t[0] = self._typed_stds(t[3], "str3ds")

    def p_expr_stvds_function(self, t) -> None:
        # Explicitly specify a space time vector dataset
        # R = A : stvds(B)
        """
        expr : STVDS LPAREN stds RPAREN
        """
        t[0] = self._typed_stds(t[3], "stvds")

    def p_expr_tmap_function(self, t):
        # Add a single map.
        # Only the spatial extent of the map is evaluated.
        # Temporal extent is not existing.
        # Examples:
        #    R = tmap(A)
        """
        expr : TMAP LPAREN stds RPAREN
        """
        if self.run:
            t[0] = [self._open_single_map(t[3])]
        else:
            t[0] = f"tmap({t[3]})"
        self._trace("tmap(", t[3], ")")

    def _open_single_map(self, name):
        """Open a map of the map type of the expression.

        The map need not be registered in the temporal database: then its time
        stamp is read from the GRASS database.

        :raises FatalError: if the map does not exist or has no time stamp
        """
        id_input = name if "@" in name else f"{name}@{self.mapset}"
        map_i = dataset_factory(self.maptype, id_input)
        if map_i.map_exists() is False:
            raise FatalError(
                _("{type} map <{id}> not found in GRASS spatial database").format(
                    type=map_i.get_type(), id=id_input
                )
            )
        if map_i.is_in_db(dbif=self.dbif):
            map_i.select(dbif=self.dbif)
        else:
            map_i.load()
            map_i.read_timestamp_from_grass()
        if map_i.get_temporal_extent_as_tuple()[0] is None:
            raise FatalError(
                _(
                    "Map <{id}> has no time stamp and is not registered in the "
                    "temporal database"
                ).format(id=id_input)
            )
        return map_i

    def p_expr_tmerge_function(self, t):
        # Merge two maplists of same STDS type into a result map list.
        # Examples:
        #    R = merge(A, B)
        """
        expr : MERGE LPAREN stds COMMA stds RPAREN
             | MERGE LPAREN expr COMMA stds RPAREN
             | MERGE LPAREN stds COMMA expr RPAREN
             | MERGE LPAREN expr COMMA expr RPAREN
        """
        if self.run:
            t[0] = self._merge(self.check_stds(t[3]), self.check_stds(t[5]))
        else:
            t[0] = f"merge({t[3]},{t[5]})"
        self._trace("merge(", t[3], ",", t[5], ")")

    def _merge(self, maplistA, maplistB):
        """Return the union of two map lists

        A map which occurs identically in both lists is kept once and a warning
        reports how many were left out.
        """
        if not maplistA and not maplistB:
            self.msgr.warning(_("Merging empty map lists"))
            return []
        if not maplistA:
            self.msgr.message(
                _("First Map list is empty, can't merge it. Return only last map list")
            )
            return maplistB
        if not maplistB:
            self.msgr.message(
                _(
                    "Second Map list is empty, can't merge it. "
                    "Return only first map list"
                )
            )
            return maplistA
        # The data types are not compared. The maps of a dataset have none
        # loaded here, so a comparison would fail for every merge with a
        # single map from tmap() and never for two datasets. A dataset may
        # hold maps of different types anyway.
        merged = list(maplistA)
        known = {self._merge_key(map_i) for map_i in maplistA}
        duplicates = 0
        for map_i in maplistB:
            key = self._merge_key(map_i)
            if key in known:
                duplicates += 1
            else:
                known.add(key)
                merged.append(map_i)
        if duplicates:
            self.msgr.warning(
                _("merge() keeps {count} maps of both operands only once").format(
                    count=duplicates
                )
            )
        return merged

    @staticmethod
    def _merge_key(map_i):
        """Maps with equal key are the same map: same map, time and command"""
        commands = getattr(map_i, "cmd_list", None)
        if isinstance(commands, list):
            # The vector algebra keeps a list of modules, which is not hashable.
            # Modules compare by identity, which suffices: each module writes
            # its own temporary map, and that map is already the id.
            commands = tuple(commands)
        return (map_i.get_id(), map_i.get_temporal_extent_as_tuple(), commands)

    def p_t_hash(self, t) -> None:
        """
        t_hash_var : stds HASH stds
                   | expr HASH stds
                   | stds HASH expr
                   | expr HASH expr
        """
        if self.run:
            t[0] = self._count_related(t[1], t[3])

    def _count_related(self, left, right, topolist=("EQUAL",)):
        """Count for each map of the left side the maps of the right side which
        have one of the relations to it. Maps without such a map are dropped."""
        return self.build_spatio_temporal_topology_list(
            self.check_stds(left), self.check_stds(right), topolist, count_map=True
        )

    def p_t_hash2(self, t) -> None:
        """
        t_hash_var : stds T_HASH_OPERATOR stds
                   | stds T_HASH_OPERATOR expr
                   | expr T_HASH_OPERATOR stds
                   | expr T_HASH_OPERATOR expr
        """
        if self.run:
            with self._reporting_syntax_errors():
                topolist, temporal = self.eval_toperator(t[2], optype="hash")[:2]
                if temporal != "l":
                    msg = (
                        f"The hash operator {t[2]} counts the related maps of each "
                        "left map and keeps its time stamp, a temporal operator "
                        f"'{temporal}' is not supported"
                    )
                    raise SyntaxError(msg)
                t[0] = self._count_related(t[1], t[3], topolist)

    def p_t_hash_paren(self, t) -> None:
        """
        t_hash_var : LPAREN t_hash_var RPAREN
        """
        t[0] = t[2]

    def p_t_td_var(self, t) -> None:
        """
        t_td_var : TD LPAREN stds RPAREN
                 | TD LPAREN expr RPAREN
        """
        if self.run:
            maplist = self.check_stds(t[3])
            for map_i in maplist:
                gvar = GlobalTemporalVar()
                gvar.td = self._time_difference(map_i)
                self._add_map_value(map_i, gvar)
            t[0] = maplist
        else:
            t[0] = f"td({t[3]})"
        self._trace("td(" + str(t[3]) + ")")

    def _time_difference(self, map_i):
        """The size of the temporal extent of the map: days for absolute time,
        the time unit for relative time"""
        if map_i.is_time_absolute():
            start, end = map_i.get_absolute_time()
        else:
            start, end, _unit = map_i.get_relative_time()
        if end is None:
            self.msgr.fatal(
                _(
                    "Function td() requires a time interval, but map <{map}> is a "
                    "time instance."
                ).format(map=map_i.get_id())
            )
        if map_i.is_time_absolute():
            return time_delta_to_relative_time(end - start)
        return end - start

    def p_t_time_var(self, t) -> None:
        # Temporal variables that return a double or integer value
        """
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
        """

        t[0] = t[1]

    def p_compare_op(self, t) -> None:
        # Compare operators that are supported for temporal expressions
        """
        comp_op : CEQUALS
                | UNEQUALS
                | LOWER
                | LOWER_EQUALS
                | GREATER
                | GREATER_EQUALS
        """
        t[0] = t[1]

    def p_t_var_expr_td_hash(self, t) -> None:
        # Examples:
        #    A # B == 2
        #    td(A) < 31
        """
        t_var_expr : t_td_var   comp_op number
                   | t_hash_var comp_op number
        """
        if self.run:
            maplist = self.check_stds(t[1])
            for map_i in maplist:
                # t[3] is already an int/float from the lexer (t_INT/t_FLOAT).
                self._add_condition_value(
                    map_i,
                    self.compare_values(self._counted_value(map_i), t[2], t[3]),
                )
            t[0] = maplist
        self._trace(t[1], t[2], t[3])

    def _counted_value(self, map_i):
        """The time difference or number of related maps of a map, as stored by
        td() and the hash operator"""
        try:
            return map_i.map_value[0].td
        except (IndexError, AttributeError, TypeError):
            self.msgr.fatal(
                _(
                    "Error: the given expression does not contain a correct time "
                    "difference object."
                )
            )

    def p_t_var_expr_number(self, t) -> None:
        # Examples:
        #    start_month(A) > 2
        #    start_day(B) < 14
        #    start_day(B) < start_month(A)
        """
        t_var_expr : t_var LPAREN stds RPAREN comp_op number
                   | t_var LPAREN expr RPAREN comp_op number
        """
        # Not implemented: comparing the functions of two map lists with each
        # other, and the backward direction (number before the function).
        if self.run:
            t[0] = self._eval_time_condition(t[1], t[3], t[5], t[6])
        self._trace(t[1], t[3], t[5], t[6])

    def _eval_time_condition(self, tfunc, stds, compop, value):
        """Evaluate a temporal function of the maps against a value: the
        condition values of the maps are set and the maps returned."""
        gvar = GlobalTemporalVar()
        gvar.tfunc = tfunc
        gvar.compop = compop
        gvar.value = value
        return self.eval_global_var(gvar, self.check_stds(stds))

    def p_t_var_expr_time(self, t) -> None:
        # Examples:
        #   start_time(A) == "12:30:00"
        #   start_date(B) <= "2001-01-01"
        #   start_datetime(C) > "2001-01-01 12:30:00"
        # Not implemented: the backward direction (value before the function).
        """
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
        """
        if self.run:
            t[0] = self._eval_time_condition(t[1], t[3], t[5], t[6])
        self._trace(t[1], t[3], t[5], t[6])

    def p_t_var_expr_comp(self, t) -> None:
        """
        t_var_expr : t_var_expr AND AND t_var_expr
                   | t_var_expr OR OR t_var_expr
        """
        if self.run:
            # && and || combine the conditions of maps with equal time
            t[0] = self._combine_conditions(
                t[1], t[4], ["EQUAL"], "l", t[2] + t[3], t[2]
            )
        self._trace(t[1], t[2] + t[3], t[4])

    def _combine_conditions(
        self, left, right, relations, temporal, function, aggregate
    ):
        """Combine the boolean conditions of two map lists.

        :param function: The boolean operator & or | (also as && or ||) which
            joins the condition of a map with the aggregate of the related maps
        :param aggregate: The boolean operator which joins the conditions of
            several related maps
        """
        complist = self.build_spatio_temporal_topology_list(
            left,
            right,
            topolist=relations,
            compare_bool=True,
            compop=function[0],
            aggregate=aggregate,
        )
        return self.set_temporal_extent_list(
            complist, topolist=relations, temporal=temporal
        )

    def p_t_var_expr_comp_op(self, t) -> None:
        """
        t_var_expr : t_var_expr T_COMP_OPERATOR t_var_expr
        """
        if self.run:
            with self._reporting_syntax_errors():
                relations, temporal, function, aggregate = self.eval_toperator(
                    t[2], optype="boolean"
                )
                t[0] = self._combine_conditions(
                    t[1], t[3], relations, temporal, function, aggregate
                )
        self._trace(t[1], t[2], t[3])

    def p_expr_t_select(self, t) -> None:
        # Temporal equal selection
        # The temporal topology relation equals is implicit
        # Examples:
        #    A : B  # Select the part of A that is temporally equal B
        """
        expr : stds T_SELECT stds
             | expr T_SELECT stds
             | stds T_SELECT expr
             | expr T_SELECT expr
        """
        if self.run:
            t[0] = self.perform_temporal_selection(
                self.check_stds(t[1]), self.check_stds(t[3])
            )
        else:
            t[0] = self._placeholder(t[1])
        self._trace(str(t[1]), "* = ", t[1], t[2], t[3])

    @staticmethod
    def _placeholder(operand) -> str:
        """The value of an expression which is only parsed, not evaluated"""
        return f"{operand}*"

    def p_expr_t_not_select(self, t) -> None:
        # Temporal equal selection
        # The temporal topology relation equals is implicit
        # Examples:
        #    A !: B  # Select the part of A that is temporally unequal to B
        """
        expr : stds T_NOT_SELECT stds
             | expr T_NOT_SELECT stds
             | stds T_NOT_SELECT expr
             | expr T_NOT_SELECT expr
        """
        if self.run:
            t[0] = self.perform_temporal_selection(
                self.check_stds(t[1]), self.check_stds(t[3]), inverse=True
            )
        else:
            t[0] = self._placeholder(t[1])
        self._trace(f"{t[1]}* = ", t[1], t[2], t[3])

    def p_expr_t_select_operator(self, t) -> None:
        # Temporal equal selection
        # The temporal topology relation equals is implicit
        # Examples:
        #    A {!:} B  # Select the part of A that is temporally unequal to B
        #    A { :} B  # Select the part of A that is temporally equal B
        #    A {!:, equals} B          # Select the part of A that is temporally unequal
        #                              # to B
        #    A {!:, during} B          # Select the part of A that is temporally not
        #                              # during B
        #    A {:, overlaps} B         # Select the part of A that temporally overlaps B
        #    A {:, overlaps|equals} B  # Select the part of A that temporally overlaps
        #                              # or equals B
        """
        expr : stds T_SELECT_OPERATOR stds
             | expr T_SELECT_OPERATOR stds
             | stds T_SELECT_OPERATOR expr
             | expr T_SELECT_OPERATOR expr
        """
        if self.run:
            with self._reporting_syntax_errors():
                maplistA = self.check_stds(t[1])
                maplistB = self.check_stds(t[3])
                relations, temporal, function, _aggregate = self.eval_toperator(
                    t[2], optype="select"
                )
                selected = self.perform_temporal_selection(
                    maplistA, maplistB, topolist=relations, inverse=function == "!:"
                )
                t[0] = self.set_granularity(selected, maplistB, temporal, relations)
        else:
            t[0] = self._placeholder(t[1])
        self._trace(f"{t[1]}* = ", t[1], t[2], t[3])

    @contextmanager
    def _reporting_syntax_errors(self):
        """Report a SyntaxError raised in the block instead of raising it.

        PLY swallows a SyntaxError raised in a grammar rule, see _report_error.
        """
        try:
            yield
        except SyntaxError as error:
            self._report_error(str(error))

    def p_expr_condition_if(self, t) -> None:
        # Examples
        # if( start_date() < "2005-06-01", A:B)
        """
        expr : IF LPAREN t_var_expr COMMA stds RPAREN
             | IF LPAREN t_var_expr COMMA expr RPAREN
        """
        if self.run:
            t[0] = self._evaluate_if(t[3], t[5])
        else:
            t[0] = self._placeholder(t[5])
        self._trace(str(t[5]) + "* = ", "if condition", str(t[3]), " then ", str(t[5]))

    def _evaluate_if(self, tvarexpr, then_arg, else_arg=None, topolist=None):
        """Evaluate a conditional statement.

        :param tvarexpr: The condition, a map list with condition values
        :param then_arg: The maps (or a dataset name) taken where the condition
            is true
        :param else_arg: The maps (or a dataset name) taken where it is false
        :param topolist: The relations between condition and conclusions as
            written in braces, None without braces
        :return: The selected maps, sorted by time, without condition values
        """
        takes_unrelated = self._else_takes_unrelated(topolist)
        topolist = topolist or ("EQUAL",)
        thenlist = self.check_stds(then_arg)
        condition = self.build_condition_list(tvarexpr, thenlist, topolist)
        selected = self.eval_condition_list(condition)
        if else_arg is not None:
            elselist = self.check_stds(else_arg)
            condition = self.build_condition_list(tvarexpr, elselist, topolist)
            selected += self.eval_condition_list(condition, inverse=True)
            if takes_unrelated:
                selected += self._unrelated(elselist, condition)
            selected.sort(key=AbstractDatasetComparisonKeyStartTime)
        # Clear the map and conditional values of the map list.
        return self.check_stds(selected, clear=True)

    def _else_takes_unrelated(self, topolist):
        """True if else takes the maps that no condition is related to

        The paper that introduced the algebra defines else as applying "if no
        topological relation to the if statement exists or if they are false"
        (Gebbert, Leppelt and Pebesma 2019, section 3.2.1). This holds for
        temporal relations beyond equal only, so that if({equal}, ...) means
        the same as if(...), whose condition speaks of maps of equal time.
        """
        return topolist is not None and any(
            name.upper() in self.temporal_topology_list and name.upper() != "EQUAL"
            for name in topolist
        )

    @staticmethod
    def _unrelated(maplist, related):
        """The maps of maplist that are not in related"""
        uids = {map_i.uid for map_i in related}
        return [map_i for map_i in maplist if map_i.uid not in uids]

    def p_expr_condition_if_relation(self, t) -> None:
        # Examples
        # if({equal} start_date() < "2005-06-01", A:B)
        """
        expr : IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA expr RPAREN
        """
        if self.run:
            with self._reporting_syntax_errors():
                topolist = self.eval_toperator(t[3], optype="relation")[0]
                t[0] = self._evaluate_if(t[5], t[7], topolist=topolist)
        else:
            t[0] = self._placeholder(t[7])
        self._trace(
            "result* = ", "if ", str(t[3]), "condition", str(t[5]), " then ", str(t[7])
        )

    def p_expr_condition_elif(self, t) -> None:
        # Examples
        # if( start_date() < "2005-06-01", if(start_time() < "12:30:00", A:B), A!:B)
        """
        expr : IF LPAREN t_var_expr COMMA stds COMMA stds RPAREN
             | IF LPAREN t_var_expr COMMA stds COMMA expr RPAREN
             | IF LPAREN t_var_expr COMMA expr COMMA stds RPAREN
             | IF LPAREN t_var_expr COMMA expr COMMA expr RPAREN
        """
        if self.run:
            t[0] = self._evaluate_if(t[3], t[5], t[7])
        else:
            t[0] = self._placeholder(t[5])
        self._trace(
            str(t[5]) + "* = ",
            "if condition",
            str(t[3]),
            " then ",
            str(t[5]),
            " else ",
            str(t[7]),
        )

    def p_expr_condition_elif_relation(self, t) -> None:
        # Examples
        # if({equal}, start_date() < "2005-06-01",
        #                               if(start_time() < "12:30:00", A:B), A!:B)
        # The then and else statement using the same topological relationships.
        # Feature request: Independent relationships for then and else to conditions.
        """
        expr : IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA stds COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA stds COMMA expr RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA expr COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA expr COMMA expr RPAREN
        """
        if self.run:
            with self._reporting_syntax_errors():
                topolist = self.eval_toperator(t[3], optype="relation")[0]
                t[0] = self._evaluate_if(t[5], t[7], t[9], topolist)
        else:
            t[0] = self._placeholder(t[7])
        self._trace(
            str(t[7] if t[5] else t[9]),
            "* = ",
            "if condition",
            str(t[5]),
            " then ",
            str(t[7]),
            " else ",
            str(t[9]),
        )

    def p_expr_t_buff(self, t) -> None:
        # Examples
        # buff_t(A : B, "10 minutes")  # Select the part of A that is temporally
        #                                equal to B and create a buffer of 10 minutes
        #                                around
        """
        expr : BUFF_T LPAREN stds COMMA QUOTE  number NAME QUOTE RPAREN
             | BUFF_T LPAREN expr COMMA QUOTE  number NAME QUOTE RPAREN
             | BUFF_T LPAREN stds COMMA number RPAREN
             | BUFF_T LPAREN expr COMMA number RPAREN
        """
        if self.run:
            maplist = self.check_stds(t[3])
            with self._reporting_syntax_errors():
                self._check_increment(
                    "buff_t", maplist, self._increment(t), with_unit=len(t) == 10
                )
                for map_i in maplist:
                    # Relative time is buffered by a number of time units
                    map_i.temporal_buffer(
                        self._increment(t, as_number=map_i.is_time_relative())
                    )
                # Assigned last: after a refused increment the rule has no
                # value, so that no result is registered.
                t[0] = maplist
        else:
            t[0] = self._placeholder(t[3])
        self._trace_increment("buff_t", t)

    def _trace(self, *parts) -> None:
        """Print the parts of a parsed rule when debugging (documented in the
        doctests of this module)"""
        if self.debug:
            print(*parts)

    def _trace_increment(self, function, t) -> None:
        """Print the buff_t() or tshift() rule that was parsed, when debugging"""
        if len(t) == 10:
            self._trace(
                f"{t[3]}* = {function}(",
                str(t[3]),
                ",",
                '"',
                str(t[6]),
                str(t[7]),
                '"',
                ")",
            )
        else:
            self._trace(f"{t[3]}* = {function}(", str(t[3]), ",", str(t[5]), ")")

    @staticmethod
    def _increment(t, as_number: bool = False):
        """The increment of buff_t() and tshift(): "10 minutes" (a quoted number
        and a unit) or, without a unit, a number"""
        if len(t) == 10:
            return f"{t[6]} {t[7]}"
        return int(t[5]) if as_number else str(t[5])

    @staticmethod
    def _check_increment(function, maplist, increment, with_unit=False) -> None:
        """Refuse an increment of the wrong kind for the time type of the maps.

        Absolute time takes a number and a unit, relative time a number of its
        unit. Without the check temporal_buffer() fails with a bare Exception
        for the first and a TypeError for the second.

        with_unit tells a quoted number and unit from a plain number. Only the
        first is refused for relative time, so that a fractional number keeps
        being truncated to a whole one there.

        :raises SyntaxError: if a map has absolute time and no unit is given,
                             or a map has relative time and a unit is given
        """
        is_number = str(increment).strip().lstrip("-").isdigit()
        if is_number and any(map_i.is_time_absolute() for map_i in maplist):
            msg = (
                "Function {function}() needs a time unit for absolute time, "
                'e.g. "{increment} days", but got {increment}'
            ).format(function=function, increment=increment)
            raise SyntaxError(msg)
        if with_unit and any(map_i.is_time_relative() for map_i in maplist):
            msg = (
                "Function {function}() needs a number without a time unit for "
                'relative time, e.g. 3, but got "{increment}"'
            ).format(function=function, increment=increment)
            raise SyntaxError(msg)

    def p_expr_t_snap(self, t) -> None:
        # Examples
        # tsnap(A : B)  # Snap the maps of A temporally.
        """
        expr : TSNAP LPAREN stds RPAREN
             | TSNAP LPAREN expr RPAREN
        """
        if self.run:
            maplist = self.check_stds(t[3])
            # snap_map_list() returns None for an empty list, which would
            # reach the enclosing rule as a value that is no map list.
            t[0] = AbstractSpaceTimeDataset.snap_map_list(maplist) if maplist else []
        else:
            t[0] = self._placeholder(t[3])
        self._trace(str(t[3]) + "* = tsnap(", str(t[3]), ")")

    def p_expr_t_shift(self, t) -> None:
        # Examples
        # tshift(A : B, "10 minutes")  # Shift the selection from A temporally
        #                                by 10 minutes.
        """
        expr : TSHIFT LPAREN stds COMMA QUOTE  number NAME QUOTE RPAREN
             | TSHIFT LPAREN expr COMMA QUOTE  number NAME QUOTE RPAREN
             | TSHIFT LPAREN stds COMMA number RPAREN
             | TSHIFT LPAREN expr COMMA number RPAREN
        """
        if self.run:
            maplist = self.check_stds(t[3])
            with self._reporting_syntax_errors():
                self._check_increment(
                    "tshift", maplist, self._increment(t), with_unit=len(t) == 10
                )
                # shift_map_list() fails on an empty list and returns None
                # for an increment the library does not accept.
                shifted = (
                    AbstractSpaceTimeDataset.shift_map_list(maplist, self._increment(t))
                    if maplist
                    else []
                )
                if shifted is None:
                    msg = (
                        'Function tshift() cannot shift {type} time by "{increment}"'
                    ).format(
                        type=maplist[-1].get_temporal_type(),
                        increment=self._increment(t),
                    )
                    raise SyntaxError(msg)
                t[0] = shifted
        else:
            t[0] = self._placeholder(t[3])
        self._trace_increment("tshift", t)

    def p_expr_time_const(self, t) -> None:
        # Examples
        # start_doy(A, -1)  # Get the start DOY from the preceding map
        #                     of the time series as a numerical constant
        #                     for the mapcalculator expression
        """
        expr : t_var LPAREN NAME COMMA INT RPAREN
        """
        if self.run:
            t[0] = self._neighbour_constants(t[1], t[3], int(t[5]))
        else:
            t[0] = self._placeholder(t[3])
        self._trace(str(t[3]), "* = ", str(t[0]), "(", str(t[3]), ",", str(t[4]), ")")

    def _neighbour_constants(self, function, stds, offset):
        """Give each map the value of a temporal function of its neighbour.

        The neighbour is the map ``offset`` positions away in the time series;
        maps without such a neighbour are dropped. The new maps have the
        temporal extent of the original and carry the value as ``cmd_list``.
        """
        map_list = self.check_stds(stds)
        result_list = []
        for index, map_i in enumerate(map_list):
            neighbour_index = index + offset
            if not 0 <= neighbour_index < len(map_list):
                continue
            map_n = map_list[neighbour_index]
            map_new = self.generate_new_map(map_n, bool_op="and", copy=True)
            map_new.set_temporal_extent(map_i.get_temporal_extent())
            map_new.cmd_list = str(self._temporal_function_value(function, map_n))
            result_list.append(map_new)
        return result_list

    def p_error(self, t):
        # Handle errors.
        if t:
            raise SyntaxError(
                "syntax error on line %d, position %i token %s near '%s' expression "
                "'%s'" % (t.lineno, t.lexpos, t.type, t.value, self.expression)
            )
        msg = "Unexpected syntax error"
        raise SyntaxError(msg)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
