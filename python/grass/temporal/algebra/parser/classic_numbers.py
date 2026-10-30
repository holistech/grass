"""The numbers of r.mapcalc as the classic profile computes them

The classic algebra writes numbers into the expressions of r.mapcalc, which
reads integers with 32 bits; the core computes them in Python. These
functions give ClassicTranslator (classic.py) the numbers that r.mapcalc
computes; they are for variants of the algebra, not for users.
"""

import dataclasses

from grass.temporal.algebra.content import Const, evaluate
from grass.temporal.algebra.series import Series

from .classic_maps import like

_INT32_MAX = 2**31 - 1
_INT64_MAX = 2**63 - 1


def beyond_int32(content):
    """Whether content is an integer constant that r.mapcalc reads with an
    overflow"""
    return (
        isinstance(content, Const)
        and isinstance(content.value, int)
        and abs(content.value) > _INT32_MAX
    )


def as_mapcalc_reads(value):
    """The number that r.mapcalc computes for the integer value written in
    its expression, None for null

    The scanner of r.mapcalc reads the digits with atoi(), which glibc
    implements as strtol() cast to int: the number saturates at 2**63 - 1 and
    keeps its lower 32 bits, and -2**31 is the null of a CELL map. A minus in
    front is an operator on the number read. Measured 2026-10-23 with
    r.mapcalc "x = <literal>" in a temporary project, one literal per run;
    the values are those of temporal_algebra_classic_profile_test.py.
    """
    if value < 0:
        read = as_mapcalc_reads(-value)
        return None if read is None else -read
    read = min(value, _INT64_MAX) % 2**32
    if read > _INT32_MAX:
        read -= 2**32
    return None if read == -(2**31) else read


def mapcalc_arithmetic(symbol, left, right):
    """The number that r.mapcalc computes for left symbol right, None for
    null

    left and right are numbers as r.mapcalc holds them: int for a CELL
    value, float for a DCELL value and None for null, as as_mapcalc_reads()
    gives them. Two integers give an integer of 32 bits, whose value -2**31
    is null; the product of two such integers stays below the saturation of
    as_mapcalc_reads(), so it keeps exactly the lower 32 bits. Division and
    remainder are those of the core (C rules, null for a divisor 0).
    Measured 2026-10-24 with r.mapcalc "x = <left> <symbol> <right>" in a
    temporary project, one expression per run, value with r.stats -n1; the
    values are those of temporal_algebra_classic_profile_test.py.
    """
    value = evaluate(symbol, [left, right])
    if isinstance(value, int):
        return as_mapcalc_reads(value)
    return value


def mapcalc_number(content):
    """The number of a constant as r.mapcalc holds it, see
    mapcalc_arithmetic()"""
    value = content.value
    return as_mapcalc_reads(value) if isinstance(value, int) else value


def time_values(operand):
    """Whether operand is a series of numbers that time functions such as
    td() gave, which the classic algebra writes into the expression of
    r.mapcalc when it computes with them"""
    return (
        isinstance(operand, Series)
        and not operand.timeless
        and operand.sort == "scalar"
        and all(number(slot.content) for slot in operand.slots)
    )


def number(content):
    """Whether content is a number or null; a time function such as
    start_time() gives a date instead"""
    return isinstance(content, Const) and (
        content.value is None or type(content.value) in {int, float}
    )


def same_times(series):
    """Whether all series have the time stamps of the first, in its order"""
    first = series[0]
    return all(
        len(other.slots) == len(first.slots)
        and all(
            a.extent == b.extent for a, b in zip(other.slots, first.slots, strict=True)
        )
        for other in series
    )


def read_as_mapcalc(left, right):
    """left and right, where one of them is a series of cells, with each
    integer constant beyond 32 bits in their slots replaced by the number
    r.mapcalc reads for it

    Where a series of cells meets another series, the classic algebra writes
    the numbers of both, also those of time functions such as td() of
    relative time, into the expression of r.mapcalc, while the core folds two
    constants in Python. Two series of time function values are computed by
    mapcalc_arithmetic() instead (see ClassicTranslator._combine()), which reads their
    integers as r.mapcalc does.
    """
    if "field" not in (left.sort, right.sort):
        return left, right
    return _read_operand_as_mapcalc(left), _read_operand_as_mapcalc(right)


def _read_operand_as_mapcalc(operand):
    """operand with the integer constants of read_as_mapcalc() replaced"""
    if not any(beyond_int32(slot.content) for slot in operand.slots):
        return operand
    return like(
        operand,
        (
            dataclasses.replace(
                slot,
                content=dataclasses.replace(
                    slot.content, value=as_mapcalc_reads(slot.content.value)
                ),
            )
            if beyond_int32(slot.content)
            else slot
            for slot in operand.slots
        ),
    )
