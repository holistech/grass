"""Cases where the classic profile once differed from the classic algebra

Each expression runs on the classic profile (what -c runs), on the datasets
of the expression fuzzer, and is compared with the outcome of the classic
algebra of the parser classes, the reference, that
grass.temporal.testing.corpus holds. The registered maps or the class of the
error must be equal. The cases came from fuzz runs and from the analysis of
single differences; they are the rules that the hard cases in
t_rast_algebra_classic_profile_test.py do not cover.
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.expressions import (
    RUNNERS,
    compare,
    failed_module_pair,
    outcome,
    prepare,
)
from grass.tools import Tools

KIND = "raster"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# Targeted probes (2026-10-16, the 11 expressions below on the reference and
# the profile, and none in the fuzzer runs of that day): arithmetic on a count
# and time conditions on both sides of && and || with a computed argument on
# either side give the registered maps of the classic algebra.
COUNT_ARITHMETIC = [
    "(Z # A) + 1",
    "if((Z # A) + 1 > 2, A, B)",
    "if(td(Z # A) > 1, A)",
    "td(Z # A) + 1",
]
BOTH_SIDES_OF_LOGICAL = [
    "if(td(A) > 0 && td(Z) < 5, A)",
    "if(start_day(A * 2) < 3 && start_day(Z * 2) > 1, A)",
    "if(start_day(A) < 3 && start_day(Z * 2) > 1, A)",
    "if(start_day(A * 2) < 3 && start_day(Z) > 1, A)",
    "if(start_day(A * 2) < 3 || start_day(Z * 2) > 1, A)",
    "if(start_day(sin(A)) < 3 && start_day(N + HA) > 1, Z)",
    "if(A > 1 && start_day(Z * 2) > 1, Z)",
]

# A condition on a merged list with numbers as then and else is the list of
# the condition as it stands, in the order of the merge and not by time.
LISTED_CONDITIONS = [
    "if(merge(D, AF) != 3, 1, 2)",
    "if(merge(D, AF) != 3, 1)",
    "if(isnull(merge(D, AF)), 1, 2)",
    "if(merge(D[2], AF) != 3000000000, null(), null())",
]

# Computed maps keep the id of the map they were made of, so the selection in
# braces of a merge with a computed copy keeps one of the two, the later one
# (A : B keeps both). An operation of two maps is a new map with its own id.
COMPUTED_COPIES = [
    "merge(A, sqrt(A)) {:,equal} HA",
    "merge(A, A + 1) {!:,equal} HA",
    "merge(A + 1, A) {:,equal} HA",
    'buff_t(merge(A / AF, float(A)) : AF, "1 day")',
    "merge(A / AF, A * 1) : AF",
    "merge(A, A / AF) : AF",
    "merge(A, A # N) {:,equal} HA",
    "merge(A # N, A) {:,equal} HA",
    "merge(A, A # D) {:,equal} HA",
    "merge(A, (A # N) + 1) {:,equal} HA",
    "merge(A, (A # N) * 2) {:,equal} HA",
    "merge(A, (A # N) - 1) {:,equal} HA",
    "merge(A, abs(A # N)) {:,equal} HA",
    "merge(A, ((A # N) + 1) * 2) {:,equal} HA",
    "merge(A, 1 + (A # N)) {:,equal} HA",
    "merge(A, 2 * (A # N)) {:,equal} HA",
    "merge(A, if(A # N > 1, A # N)) {:,equal} HA",
    "merge(A, sqrt(A)) {:,overlapped|equal} if(AF < 3000000000 || td(D) >= 2, HA)",
]

# A constant beyond 32 bits is read by r.mapcalc with an overflow, also next
# to the number of a time function, so it is not folded.
LARGE_CONSTANTS_WITH_TIME = [
    "3000000000 % start_dow(N, 1)",
    "3000000000 % start_dow(N, 1) / tsnap(AF)",
    "3000000000 + A",
    "4000000000 * 2 - A",
    # r.mapcalc cuts 3000000000 to 32 bits (3000000000 - 2^32 = -1294967296)
    # before abs() takes the absolute value, 1294967296. The profile must
    # hand the number on, not fold abs(3000000000) to 3000000000 itself.
    "abs(if(td(A) <= 0.5, A, 3000000000))",
    # Every map of A lasts one day, so each slot holds the number as well.
    # -1294967296 + 1.0 = -1294967295.0, folded 3000000001.0.
    "if(td(A) <= 0.5, A, 3000000000) + 1.0",
    # C keeps the sign of the dividend: -1294967296 % 7 = 0, as
    # 1294967296 = 7 * 184995328; folded 3000000000 % 7 = 4.
    "if(td(A) <= 0.5, A, 3000000000) % 7",
    # -1294967296 > 5 is false, so 2; folded 3000000000 > 5 gives 1.
    "if(if(td(A) <= 0.5, A, 3000000000) > 5, 1, 2)",
]

# Where two series meet, the classic algebra writes both numbers for r.mapcalc,
# which reads an integer beyond 32 bits with atoi() and keeps 32 bits of it.
# Every map of A lasts one day, so td(A) is 1.0 and the condition puts
# 3000000000 into each slot; r.mapcalc reads 3000000000 - 2^32 = -1294967296.
# The outcomes have 6 significant digits.
LARGE_CONSTANTS_BETWEEN_SERIES = [
    # -1294967296 + 1.0 = -1294967295.0, -1294970000; folded 3000000000.
    "if(td(A) <= 0.5, A, 3000000000) + td(A)",
    # -1294967296 / 1.0 = -1294967296.0, -1294970000.
    "if(td(A) <= 0.5, A, 3000000000) / td(A)",
    "if(td(A) <= 0.5, A, 3000000000) {+,equal,r} td(A)",
    # -1294967296 * 2.0 = -2589934592.0, -2589930000; folded 6000000000.
    "if(td(A) <= 0.5, A, 3000000000) {*,equal} if(td(A) <= 0.5, A, 2.0)",
    # C keeps the sign of the dividend: -1294967296 % 7 = 0, as
    # 1294967296 = 7 * 184995328; folded 3000000000 % 7 = 4.
    "if(td(A) <= 0.5, A, 3000000000) {%,equal} if(td(A) <= 0.5, A, 7)",
    # -1294967296 > 5 is false, so 2; folded 1.
    "if(if(td(A) <= 0.5, A, 3000000000) {>,equal} if(td(A) <= 0.5, A, 5), 1, 2)",
    # The minus is an operator on the number read: -(-1294967296) + 1.0 =
    # 1294967297.0, 1294970000; folded -2999999999.0.
    "if(td(A) <= 0.5, A, -3000000000) + td(A)",
    # 2147483648 - 2^32 = -2147483648 is the null of a CELL map, so null.
    "if(td(A) <= 0.5, A, 2147483648) + td(A)",
    # A condition on a time function joined with one on cells takes the cells
    # of the argument (see the profile): 4294967296 - 2^32 = 0 is false, so 2;
    # folded 1 && 4294967296 is true, 1.
    "if(if(td(A) <= 0.5, A, 5) > 1 && start_month(if(td(A) <= 0.5, A, 4294967296)) "
    "== 1, 1, 2)",
    # A floating point number is no integer literal and stays 3000000001.0,
    # 3000000000.
    "if(td(A) <= 0.5, A, 3000000000.0) + td(A)",
]

# A right-hand temporal operator makes a map of its own for each partner, so
# the maps stay apart in an inverse selection although they come from one map.
PARTNER_MAPS = [
    'int(N) {%,finishes|started,r} Q !: A {:,overlaps|during} buff_t(HB, "2 hours")',
    "int(N) {%,finishes|started,r} Q !: A",
    "(int(N) {%,finishes|started,r} Q + 1) !: A",
]

# The classic merge() tells maps apart by id, time and the commands that made
# them, so a map read at a time offset, a buffer or a time function at an
# offset (each a new map) stays next to the map it was read from, and two
# readings stay apart. The profile marks such a content with a map object of
# its own.
MERGED_COMPUTED_MAPS = [
    "merge(A[0], A[0])",
    "merge(A + 1, A[0] + 1)",
    "merge(A[0,1], A[0,1])",
    "merge(A[1], A[1])",
    "merge(A[0], A)",
    "merge(A[0] + 0, A[0])",
    "merge(start_day(A, 1), start_day(A, 1))",
    "merge(start_day(A, 1) + 0, start_day(A, 1))",
]

# The object of a map goes through a selection, a count and a number
MERGED_COMPUTED_MAPS_BEYOND_MERGE = [
    "merge(A[0], A) {:,equal} HA",
    "merge(A[0], A) : HA",
    "merge(A[0] # N, A # N)",
    "merge((A # N) + 0, A # N)",
    "merge((A # N) * 1, (A # N) + 0)",
    "merge(A[0] * 1, A[0])",
    "merge(A[0] # N, A[0] # N)",
    "merge(if(isnull(A[0]), 1, 2), A[0])",
]

# Expressions that must still collapse or stay as they are, with the number
# of maps of the classic algebra: a map and its count is one object with one
# command, a different offset or a number on a map another command.
SAME_MAP_OBJECT = [
    ("merge(A # N, A # N)", 4),
    ("merge(A # A[0], A # A[0])", 4),
    ("merge((A # N) + 0, (A # N) + 0)", 4),
    ("merge(A * 1, A * 1)", 4),
    ("merge(A + 0, A)", 8),
    ("merge(A[0,1], A[0,0])", 8),
]

# Absolute and relative time, and relative time of different units, are never
# related in the classic algebra: the relation is empty, and an error comes
# only from reading datasets of another temporal type or from registering.
MIXED_TIME = [
    "RT * tmap(sinst) : Z",
    "RT {-,finished|precedes} tmap(sinst)",
    "tmap(sinst) {:,over} RT",
    "RT {!:,follows|overlapped} tmap(sinst)",
    "tmap(singletmap) * RT {+,contains,u} td(AF {/,during,r} HB)",
    "RT + tmap(singletmap)",
    "RT + RH",
    "RT : RH",
    "RT # RH",
    "RT {+,equal} RH",
    "if(RT > 0, RH)",
    "if(RT > 0, RT, RH)",
    "if(RT > 0 && RH > 0, RT)",
    "merge(RT, RH)",
    "merge(RH, RT)",
    "merge(RT, tmap(sinst))",
    "merge(tmap(sinst), RT)",
]

# A merge() of maps of different units fails only when its maps are
# registered in one dataset; what selects or relates the maps of one unit
# gives a result, as maps of different units relate to nothing.
MERGED_UNITS = [
    "tmap(singletmap) !: merge(RT, RH)",
    "tmap(singletmap) : merge(RT, RH)",
    "tmap(singletmap) {+,equal,l} merge(RT, RH)",
    "merge(RT, RH) : RT",
    "merge(RT, RH) : RH",
    "merge(RT, RH) !: RT",
    "merge(RT, RH) {:,during} RT",
    "merge(merge(RT, RH), RT) : RH",
    "merge(merge(RT, RH), merge(RH, RT)) !: RH",
    "merge(tshift(RT, 70), RH) : RH",
    "(merge(RT, RH) + 1) : RT",
    "tshift(merge(RT, RH), 1) : RT",
    "if(RT > 0, merge(RT, RH)) : RT",
    "if(merge(RT, RH) > 0, RT) : RT",
    "if(td(merge(RT, RH)) > 0, RT)",
    "if(RT > 0 {&&,equal} merge(RH, RT) > 0, RT)",
    "RT {+,equal,r} merge(RH, RT)",
    "merge(RH, RT) {+,equal,l} RT",
    "RT # merge(RH, RT)",
    "merge(RT, RH) + 1",
    "if(merge(RT, RH) > 0, 1)",
    "tsnap(merge(RT, RH))",
    "buff_t(merge(tmap(sinst), RT), 1)",
]

# A floating point map is no operand of && and || in r.mapcalc, also where
# the core writes a comparison with zero.
FLOATING_POINT_CONDITIONS = [
    "if(isnull(AF) || exist(AF), GP)",
    "if(isnull(AF) && exist(AF), GP)",
    "if(exist(AF) && A > 1, GP)",
    "if(exist(AF * 1) || A > 2, GP)",
    "if(A > 1 && exist(A / 2), GP)",
    "if(A > 1 && exist(A), GP)",
    "if(isnull(A) || exist(A), GP)",
]

# A condition on a time function of an expression, joined with a condition on
# cells, is replaced by the value of the expression where that has a cell
# command of its own.
TIME_AND_CELL_CONDITIONS = [
    "if(A > 4 && A > 1 || start_month(N + HA) == 4, Z)",
    "if(A > 99 || start_month(A * 0) == 1, Z)",
    "if(start_month(A * 0) == 1 || A > 99, Z)",
    "if(start_month(A * 0) == 1 && A > 0, Z)",
    "if(A > 99 || start_month(sin(A)) == 1, Z)",
    "if(A > 99 || start_month(A) == 1, Z)",
    "if(A > 99 || start_month(merge(A, N)) == 1, Z)",
    "if(A > 99 || start_month(tsnap(A)) == 1, Z)",
    'if(A > 99 || start_month(tshift(A, "1 day")) == 1, Z)',
    "if(A > 99 || start_month(A : N) == 1, Z)",
    "if(A > 99 || start_month(A {:,equal} N) == 1, Z)",
    "if(A > 99 || start_month(tmap(singletmap)) == 1, Z)",
    "if(A > 99 || start_month(A {+,equal} N) == 1, Z)",
    "if(A > 99 || start_month(int(A)) == 1, Z)",
    "if(A > 99 || start_month(A[1]) == 1, Z)",
    "if(A > 99 || start_month(A[0, 1]) == 1, Z)",
    "if(A > 99 || start_month(if(A > 1, A)) == 1, Z)",
    "if(A > 99 && start_month(A * 0) == 1, Z)",
    "if(end_year(A[0]) == 1 && exist(A), null())",
    "if(end_year(A[1]) == 1 && exist(A), A)",
    "if(end_year(A[1]) == 1 || A > 2, A)",
    "if(A > 2 && end_year(A[0, 1]) == 1, A)",
]

# && binds stronger than || in r.mapcalc, which reads the text of the classic
# algebra as a || (b && c) also where the || has a relation.
LOGICAL_GROUPING = [
    "if(A > 1 || A < 3 && A > 2, A)",
    "if(A > 1 {||,equal} N > 11 && A > 2, A)",
    "if(A > 1 {||,during} B > 5 && A > 2, A)",
    "if(A > 1 && A < 4 || A > 2, A)",
    "if(end_doy(2 / Z) >= 4 && start_day(Z) < 1 || isntnull(HA), Z)",
    "if(start_day(Z) < 1 && A > 3 || isntnull(HA), Z)",
]

# A time function with an offset asks only the maps whose value it reads, and
# its value is a number in the map, so a condition on it judges cells.
TIME_FUNCTION_OFFSETS = [
    "start_hour(RH, 2)",
    "start_hour(RH, -1)",
    "start_hour(RH, 0)",
    "start_hour(A, 5)",
    "start_doy(A, -1)",
    "if(start_year(AF, 1) <= 1.5, AF)",
    "if(end_hour(A, 0) == 3, AF)",
]

# Computed maps that look alike stay apart in merge(): the classic lists tell
# them apart by the map they came from.
MERGED_COMPUTED = [
    'merge(if({equal|over}, end_date(PA) == "2001-01-01", Q, null()), A - N)',
    "merge(if(start_month(A) == 1, Q, null()), A - N)",
    "merge(AF[2] % 60 * tmap(singletmap) {+,over,i} td(D % D), "
    "HB {*,overlapped|started,r} start_month(Q, 1))",
    "merge(A # N, N # A)",
    "merge(A # N, D # A)",
    "merge(A, if((A # N) + 1 > 1, A))",
]

# A count stays on the map object of its left map in the classic algebra,
# through numbers, functions, selections and merge(). As an operand of an
# operation with another map, and in if() on cells, the classic text takes
# the first count of that map, not the expression built on it: exp(A # A) + N
# computes 1 + N, and a number next to such a count in if() is lost. Only the
# comparison of the hash operator itself, A # N > 1, is a condition on time,
# decided on the first count.
FIRST_COUNT = [
    "exp(10.25 * A # A) % N",
    "exp(A # A) + N",
    "((A # N) + 1) + N",
    "A # N + 1 + N",
    "sqrt((A # N) * 4) + N",
    "float(A # N) / N",
    "merge(A # N, N # A) + N",
    "if((A # N) - 1 > 0, A)",
    "if(abs(A # N) > 1, A, 2)",
    "if(A > 0, (A # N) + 1, N)",
    "if(isnull((A # N) * 2), N, (A # N) * 3)",
    "if(isnull(A # N), 1, 2) + N",
    "if(start_day(A) > 2, A # N, 5) + N",
    "if((A # D) # N >= 2, A, 7)",
    "if(A # N >= 3000000000, A)",
]

# td() of a counted map is its duration. The earlier implementation appended
# the duration after the count and read the first value, the count, in a
# comparison and as an operand (corrected 17.10.2026, both implementations
# give the duration). A # merge(N, HA) counts 2 for maps of one day.
COUNTED_DURATION = [
    "if(td(A # merge(N, HA)) > 1.5, A)",
    "if(td(A # merge(N, HA)) < 1.5, A)",
    "N + td(A # merge(N, HA))",
    # The count and td() of the same count side by side, a count of a map
    # read at an offset, a shifted count and td() in both branches of if()
    "(A # merge(N, HA)) + td(A # merge(N, HA))",
    "if(td(A # merge(N, HA)) == 1, A # merge(N, HA), N)",
    "N + td(A[1] # merge(N, HA))",
    'N + td(tshift(A # merge(N, HA), "1 day"))',
    "if(td(A # merge(N, HA)) > 1.5 && A # merge(N, HA) == 2, A)",
]

# if() on time with maps as then and else clears the values of the selected
# map objects, the count among them, and keeps their text: after it a count
# is the expression again. With a number as else the count stays.
CLEARED_COUNT = [
    "exp(if(start_day(A) > 2, A # merge(N, HA))) + N",
    "exp(if(td(A) > 0, A # merge(N, HA))) + N",
    "exp(if({equal}, start_day(A) > 2, A # merge(N, HA))) + N",
    "exp(if(start_day(A) > 2, A # merge(N, HA), N)) + N",
    "(if(start_day(A) > 2, A # merge(N, HA)) * 3) + N",
    "if(start_day(A) > 2, (A # merge(N, HA)) * 3) + N",
    "if(A > 0, if(start_day(A) > 2, A # merge(N, HA)) * 3, N)",
    "if(if(start_day(A) > 2, A # merge(N, HA)) # D > 1, A)",
    "N + td(if(start_day(A) > 2, A # merge(N, HA)))",
    "if(td(if(start_day(A) > 2, A # merge(N, HA))) > 1.5, A)",
    "exp(if(start_day(A) > 2, A # merge(N, HA), 5)) + N",
    "merge(A, if(start_day(A) > 2, A # N)) {:,equal} HA",
]

# A : B and A !: B keep every selected map, also a computed copy next to
# its map; only the selection in braces keeps one map per id. An operation
# of two map lists gives new maps, also where one list holds no map (td(N)).
PLAIN_SELECTIONS = [
    "merge(A * 1, A) : N",
    "merge(A + 1, A) : N",
    "merge(A, sqrt(A)) : N",
    "merge(A + 1, A) !: N",
    "merge(A * td(N), A) {!:,follows|overlaps} N",
    "merge(A * td(N), A) {:,equal} N",
    "merge(sqrt(N), merge(A * td(N), A) {!:,follows|overlaps} N {%,overlapped} B)",
]

# The partners of a map are visited in the order of their list, which a
# merge() or buff_t() sets apart from the time order.
LIST_ORDER_PARTNERS = [
    'tshift(Z, "-3 hour") {:,over,r} merge(merge(ref, Z), buff_t(AF, "2 day"))',
    'tshift(Z, "-3 hour") {:,during|overlapped,r} merge(Z, buff_t(AF, "2 day"))',
    'tshift(Z, "-3 hour") {-,over,u} merge(Z, buff_t(AF, "2 day"))',
    'tshift(Z, "-3 hour") {/,overlapped,l} merge(buff_t(AF, "2 day"), Z)',
]

# && and || with r give a map per partner whose content joins the left
# condition with all its partners (a > 1 && (b1 > 1 && b2 > 1)), as arithmetic
# with r does; l, u, i and d give one map per left map.
LOGICAL_WITH_ALL_PARTNERS = [
    f"if(B > 0 {{{symbol},contains,{reference}}} A > 1, 1, 0)"
    for symbol in ("&&", "||")
    for reference in ("l", "r", "u", "i", "d")
] + [
    'if(tshift(Z, "-3 hour") > 0 {&&,over,r} Z > 0, 1)',
    'if(tshift(Z, "-3 hour") > 0 {&&,over,r} merge(Z, AF) > 0, 1)',
    'if(tshift(Z, "-3 hour") > 0 {&&,over,r} merge(buff_t(AF, "2 day"), Z) > 0, A)',
    'if(tshift(Z, "-3 hour") > 0 {||,over,r} Z > 0, 1)',
    'if(tshift(Z, "-3 hour") > 0 {||,over,r} merge(Z, AF) > 0, 1)',
    'if(tshift(Z, "-3 hour") > 0 {||,over,r} merge(buff_t(AF, "2 day"), Z) > 0, A)',
    "if(B > 0 {&&,contains,|,r} A > 1, 1, 0)",
    "B > 0 {&&,contains,r} A > 1",
    "if(start_day(A) > 1 {&&,during,r} td(D) > 0, A)",
]

# A condition on time is decided in Python by the classic algebra, so a
# number beyond 32 bits does not overflow as it would in r.mapcalc.
TIME_CONDITIONS_BEYOND_32_BITS = [
    "if(start_month(A) >= 3000000000, A)",
    "if(start_month(A) < 3000000000, A, 2)",
    "if(td(A) >= 3000000000, A)",
    "if(start_day(A * 2) < 3000000000, A)",
]

# The maps of then and else are numbered in one list in time order, the maps
# that share a start in the order of the database. In the granularity mode
# every dataset is sampled first.
IF_ORDER = [
    "if({finished}, end_dow(A) != 1, rel, 5)",
    "if({finished}, end_dow(A) != 1, rel)",
]
GRANULARITY_ORDER = [
    "if(end_month(Z) >= 0 && td(AF) > 0, merge(D, Z % Z), tsnap(D))",
    "if(end_year(log(A)) < 1 || end_week(AF) < 3 && B # W == 1, merge(A, W))",
]

# A number next to a count is lost: the count is the then part
COUNT_BRANCHES = [
    "if(isnull(A / A), Z # A, 19)",
    "if(isnull(A), 19, Z # A)",
    "if(isnull(A), Z # A, A)",
    "if(isnull(A), Z # A)",
    "if(isnull(A), Z # A, null())",
    "if(isnull(A), (A # D) + 1, 3)",
    "if(isnull(A), 3, (A # D) * 2)",
    "if(isnull(A), abs(A # D), 3)",
]

# isnull(), isntnull() and exist() of a count as condition: the count itself
COUNT_CONDITIONS = [
    "if(isnull(N # AF), HA)",
    "if(isntnull(N # AF), HA)",
    "if(exist(N # AF), HA)",
    "if(isnull(Z # A), A, B)",
]

# A map read at a time offset has the box of the map it takes the cells from,
# which decides whether it meets the boxes of its partners.
NEIGHBOURS = [
    "Z {/,contains,u} SA[1]",
    "Z {/,contains} SA[-1]",
    "Z {/,contains} SA[2]",
    "Z {/,contains} SA[0]",
    "A {/,contains} SA[1]",
    "Z {/,precedes,l} SA[1]",
]


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    """The datasets of the fuzzer, then the test-only caches"""
    prepare(KIND, temporal_module_session, tmp_path_factory.mktemp("cases"))
    with fakes.cached_io(fakes.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(datasets):
    """Replace the fixture of conftest.py: the caches run through datasets"""


def difference(expression, reference, profile):
    """compare() of the outcomes, except for a module that failed at run time
    in both, which the profile reports as the FatalError of materialize()

    No other pair of error classes is accepted here, unlike in compare_runs().
    """
    if failed_module_pair(reference, profile):
        return None
    return compare(KIND, expression, reference, profile)


def assert_equal(expression, *, maps=None, **options):
    """The profile gives what the reference gives, with maps maps if given"""
    options = {"register_null": True, **options}
    reference = reference_outcome(KIND, expression, **options)
    profile = outcome(KIND, expression, RUNNERS["classic"], basename="fb", **options)
    assert difference(expression, reference, profile) is None
    if maps is not None:
        assert len(profile["maps"]) == maps


@pytest.mark.parametrize("expression", MIXED_TIME)
def test_mixed_time_is_unrelated(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("suffix", ["time", "gran"])
@pytest.mark.parametrize(
    "expression", ["Q + 1", "E + 1", "Q * 10", "merge(A, W) + 1", "merge(W, A) + 1"]
)
def test_equal_names_from_the_time_suffix(datasets, expression, suffix):
    """Maps of equal time get one name; the last of them stays"""
    assert_equal(expression, time_suffix=suffix)


@pytest.mark.parametrize("expression", FLOATING_POINT_CONDITIONS)
def test_floating_point_operands_of_logical_operators(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", TIME_AND_CELL_CONDITIONS)
def test_time_and_cell_conditions(datasets, expression):
    assert_equal(expression)


def test_only_the_report_of_a_failed_module_is_accepted(datasets):
    """A failed module of the reference equals the report of a failed module
    by the profile, not another FatalError of the profile"""
    failed = {
        "error": "Other:CalledModuleError",
        "msg": "Module run `r.mapcalc expression=B_#=a#` ended with an error.",
    }
    reported = {
        "error": "FatalError",
        "msg": "Module # failed with return code #, see the error output above",
    }
    other = {"error": "FatalError", "msg": "Dataset # not found"}
    assert difference("A", failed, reported) is None
    assert difference("A", failed, other) is not None


# A time function of a map read at an offset, joined with a condition on
# cells, is a truth value like the one of any registered map. The earlier
# implementation wrote the neighbour map itself as the operand of && and ||
# (if(a2 && a1, ...)), so a map with a value other than 0 was true whatever
# the time function said (corrected 17.10.2026). A has the values 1 to 4 in
# four daily maps. The years and months of the maps are 2001 and 1, so each
# time condition is false and && gives 0, || the cell condition alone. A[1]
# has no map for the last day, A[0,1] has one for each day; if() without
# else is 0 in the classic algebra.
NEIGHBOUR_TRUTH_VALUES = [
    ("if(end_year(A[1]) == 1 && exist(A), A)", [0, 0, 0]),
    ("if(end_year(A[1]) == 1 || A > 2, A)", [0, 0, 3]),
    ("if(A > 2 && end_year(A[0, 1]) == 1, A)", [0, 0, 0, 0]),
    ("if(exist(A) && start_month(A[1]) == 3, A)", [0, 0, 0]),
    # Joined with a time condition of another map first: the result of the
    # two time conditions is a copy of the neighbour map. A[-1] has no map
    # for the first day.
    ("if(end_year(A[1]) == 1 && end_year(N) == 1 && A > 0, A)", [0, 0, 0]),
    ("if(end_year(A[1]) == 1 || end_year(N) == 1 || A > 2, A)", [0, 0, 3]),
    ("if(end_year(A[1]) == 1 && end_year(A[-1]) == 1 && A > 0, A)", [0, 0]),
    # A true time condition of a neighbour map whose cells are 0: Z[1] is z2
    # (0), z3 and z4 for the first three days, so the map itself would be
    # false on the first day.
    ("if(end_year(Z[1]) == 2001 && A > 0, A)", [1, 2, 3]),
    ("if(end_year(Z[1]) == 2001 && end_year(N) == 2001 && A > 0, A)", [1, 2, 3]),
]

# A neighbour map as a cell value, the value of a time function at an offset
# and a time function of an expression keep their command
NEIGHBOUR_UNCHANGED = [
    ("if(A[1] > 1 && A > 1, A)", [0, 2, 3]),
    ("if(exist(A[1]) && A > 1, A)", None),
    ("if(A[0, 1] > 1 || A > 2, A)", None),
    ("if(start_month(A * 0) == 1 && A > 0, Z)", None),
    ("if(start_month(A[1]) == 1 {&&,equal} start_month(N) == 1, A)", None),
    ("if(A > 1 && start_doy(A, 1) > 1, A)", None),
]


@pytest.mark.parametrize("runner", ["reference", "classic"])
@pytest.mark.parametrize(("expression", "values"), NEIGHBOUR_TRUTH_VALUES)
def test_a_neighbour_map_is_a_truth_value_by_hand(datasets, runner, expression, values):
    result = outcome(
        KIND, expression, RUNNERS[runner], basename="fa", register_null=True
    )
    assert "error" not in result
    assert [row[3] for row in result["maps"]] == values


@pytest.mark.parametrize(("expression", "values"), NEIGHBOUR_TRUTH_VALUES)
@pytest.mark.parametrize("granularity", [False, True])
def test_a_neighbour_map_as_a_truth_value_in_both_implementations(
    datasets, expression, values, granularity
):
    assert_equal(expression, granularity=granularity)


@pytest.mark.parametrize("runner", ["reference", "classic"])
def test_a_neighbour_map_as_a_cell_value_by_hand(datasets, runner):
    """A[1] is 2, 3, 4 for the first three maps, so A[1] > 1 is true; A > 1 is
    false for the value 1: 0, 2, 3"""
    result = outcome(
        KIND,
        "if(A[1] > 1 && A > 1, A)",
        RUNNERS[runner],
        basename="fa",
        register_null=True,
    )
    assert [row[3] for row in result["maps"]] == [0, 2, 3]


@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize(("expression", "values"), NEIGHBOUR_UNCHANGED)
def test_a_neighbour_map_as_a_cell_value_keeps_its_command(
    datasets, expression, values, granularity
):
    assert_equal(expression, granularity=granularity)


@pytest.mark.parametrize("expression", LOGICAL_GROUPING)
def test_logical_operators_group_as_r_mapcalc_reads_them(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", TIME_FUNCTION_OFFSETS)
def test_time_functions_with_an_offset(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", MERGED_COMPUTED)
def test_merge_keeps_alike_computed_maps(datasets, expression):
    assert_equal(expression)
    assert_equal(expression, register_null=False)


@pytest.mark.parametrize("expression", IF_ORDER)
def test_conditions_list_the_maps_in_time_order(datasets, expression):
    assert_equal(expression)
    assert_equal(expression, register_null=False)


@pytest.mark.parametrize("expression", GRANULARITY_ORDER)
def test_granularity_mode_lists_the_maps_in_time_order(datasets, expression):
    assert_equal(expression, granularity=True)


@pytest.mark.parametrize("expression", COUNT_BRANCHES)
def test_a_number_next_to_a_count(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", COUNT_CONDITIONS)
def test_a_count_as_condition(datasets, expression):
    assert_equal(expression)


def test_a_number_next_to_a_count_in_the_granularity_mode(datasets):
    assert_equal(
        "if(start_week(W, -1) >= 22 && isnull(A / A), Z # A, 19)", granularity=True
    )


@pytest.mark.parametrize("expression", NEIGHBOURS)
def test_a_neighbour_has_its_own_box(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", COUNT_ARITHMETIC + BOTH_SIDES_OF_LOGICAL)
def test_counts_and_time_conditions_on_both_sides(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", MERGED_COMPUTED_MAPS)
def test_merge_keeps_computed_maps_that_look_alike(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", MERGED_COMPUTED_MAPS_BEYOND_MERGE)
def test_the_object_of_a_map_goes_through_selections_and_counts(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize(("expression", "maps"), SAME_MAP_OBJECT)
def test_a_map_and_its_count_stay_one_object(datasets, expression, maps):
    assert_equal(expression, maps=maps)


@pytest.mark.parametrize(
    ("expression", "core_maps", "classic_maps"),
    [
        ("merge(A[0], A[0])", 4, 8),
        ("merge(A + 1, A[0] + 1)", 4, 8),
        ("merge(start_day(A, 1), start_day(A, 1))", 3, 6),
    ],
)
def test_the_core_keeps_one_of_two_equal_new_maps(
    datasets, expression, core_maps, classic_maps
):
    """A difference of the two algebras that the manual lists: the core has no
    map objects, it compares content and time"""
    options = {"register_null": True}
    core = outcome(KIND, expression, RUNNERS["core"], basename="fc", **options)
    profile = outcome(KIND, expression, RUNNERS["classic"], basename="fb", **options)
    assert len(core["maps"]) == core_maps
    assert len(profile["maps"]) == classic_maps


# In the granularity mode A[0] is a map read at a time offset as well.
def test_merge_keeps_a_neighbour_map_in_the_granularity_mode(datasets):
    assert_equal("merge(A[0], A)", granularity=True)


@pytest.mark.parametrize("expression", LISTED_CONDITIONS)
def test_a_condition_without_maps_in_then_and_else_keeps_its_list(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", COMPUTED_COPIES)
def test_a_computed_copy_replaces_its_map_in_a_selection(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", ["merge(Z, Z[0] : OV)", "0 + merge(Z, Z[0])"])
def test_merge_keeps_a_neighbour_map_next_to_its_map(datasets, expression):
    assert_equal(expression, granularity=True)


@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", LARGE_CONSTANTS_WITH_TIME)
def test_constants_beyond_32_bits_next_to_time_functions(
    datasets, expression, granularity
):
    assert_equal(expression, granularity=granularity)


# The operators in braces fail in the granularity mode in both algebras, so
# there the forms with + and / carry the test.
@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", LARGE_CONSTANTS_BETWEEN_SERIES)
def test_constants_beyond_32_bits_between_two_series(datasets, expression, granularity):
    assert_equal(expression, granularity=granularity)


@pytest.fixture(scope="module")
def long_durations(datasets, temporal_module_session):
    """RS: two maps of relative time in seconds, each 3000000000 seconds long"""
    create_stds(
        Tools(session=temporal_module_session),
        "strds",
        "RS",
        [MapSpec("rs1", 1, 0, 3000000000), MapSpec("rs2", 2, 3000000000, 6000000000)],
        temporaltype="relative",
        unit="seconds",
        via="library",
    )


# td() of relative time is an integer, which the classic algebra writes for
# r.mapcalc like a constant: 1.5 + 3000000000 is 1.5 - 1294967296 =
# -1294967294.5, -1294970000; folded 3000000001.5.
def test_a_duration_beyond_32_bits_between_two_series(long_durations):
    assert_equal("if(td(RS) <= 0.5, RS, 1.5) + td(RS)")


def test_a_condition_on_two_durations_compares_the_numbers_as_they_are(
    long_durations,
):
    """The profile decides a condition on time functions in Python, also one
    on two of them combined, so the durations keep all their bits there:
    3000000000 * 3000000000 = 9e18 > 1.8e18 holds and both maps of RS (cell
    values 1 and 2) are taken. With the durations read as r.mapcalc reads
    them, (-1294967296)^2 = 1.677e18 would not exceed 1.8e18.

    The reference gives the same maps by another way: it computes this
    condition in r.mapcalc, where the product wraps around to -494665728 and
    1800000000000000000 reads as -1816920064, so the condition holds as well.
    """
    expression = "if(td(RS) * td(RS) > 1800000000000000000, RS, 1)"
    for runner, basename in (("classic", "fb"), ("reference", "fa")):
        result = outcome(
            KIND, expression, RUNNERS[runner], basename=basename, register_null=True
        )
        assert [row[3:] for row in result["maps"]] == [[1.0, 1.0], [2.0, 2.0]]


def test_the_core_keeps_a_constant_beyond_32_bits_between_two_series(datasets):
    """The core writes the integer as a floating point number: 3000000000 +
    1.0 = 3000000001.0, 3000000000 in 6 significant digits, for each of the
    four maps of A"""
    result = outcome(
        KIND,
        "if(td(A) <= 0.5, A, 3000000000) + td(A)",
        RUNNERS["core"],
        basename="fc",
        register_null=True,
    )
    assert [row[3:] for row in result["maps"]] == [[3e9, 3e9]] * 4


@pytest.mark.parametrize("expression", PARTNER_MAPS)
def test_a_map_for_each_partner_stays_in_a_selection(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize(
    "expression",
    [
        "merge(A, ((A # N) + 1) + N) {:,equal} HA",
        "merge(A, if((A # N) + 1 > 1, A)) {:,equal} HA",
    ],
)
def test_a_count_keeps_its_id_beyond_arithmetic_with_a_number(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", FIRST_COUNT)
def test_a_counted_map_is_its_first_count_next_to_maps(
    datasets, expression, granularity
):
    assert_equal(expression, granularity=granularity)


@pytest.mark.parametrize(
    "expression",
    [
        "(if(N == 3 && exist(OV), 4, 2) # GP + 4 - Z)",
        "if(N >= 2.0 && W # AF == 2, 2.0, 3)",
    ],
)
def test_a_count_in_the_granularity_mode(datasets, expression):
    assert_equal(expression, granularity=True)


@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", COUNTED_DURATION)
def test_td_of_a_counted_map_is_its_duration(datasets, expression, granularity):
    assert_equal(expression, granularity=granularity)


@pytest.mark.parametrize("runner", ["reference", "classic"])
@pytest.mark.parametrize("counted", ["A # merge(N, HA)", "A # merge(A, N)"])
def test_td_of_a_counted_map_as_an_operand_by_hand(datasets, runner, counted):
    """N holds 11 to 14 and its maps last one day, as do the maps of A; both
    counts are 2, which is not the duration: 11 + 1, 12 + 1, 13 + 1, 14 + 1.
    The second is the example of the manual."""
    count = outcome(KIND, counted, RUNNERS[runner], basename="fc")
    assert [values[3] for values in count["maps"]] == [2, 2, 2, 2]
    result = outcome(KIND, f"N + td({counted})", RUNNERS[runner], basename="fa")
    assert [values[3] for values in result["maps"]] == [12, 13, 14, 15]


@pytest.mark.parametrize("runner", ["reference", "classic"])
@pytest.mark.parametrize(
    "expression",
    [
        "(A # merge(N, HA)) + td(A # merge(N, HA))",
        "exp(A # merge(N, HA)) + td(A # merge(N, HA))",
    ],
)
def test_a_count_next_to_td_of_the_count_by_hand(datasets, runner, expression):
    """The count is still read as the count, also as the first count of exp()
    next to a map (see _first_counts()), and td() as the duration: 2 + 1"""
    result = outcome(KIND, expression, RUNNERS[runner], basename="fa")
    assert [values[3] for values in result["maps"]] == [3, 3, 3, 3]


@pytest.mark.parametrize("runner", ["reference", "classic"])
@pytest.mark.parametrize(
    ("expression", "maps"),
    [
        # The count 2 is above 1.5, the duration of one day is not
        ("if(td(A # merge(N, HA)) > 1.5, A)", 0),
        ("if(td(A # merge(N, HA)) < 1.5, A)", 4),
        ("if(td(A # merge(N, HA)) == 1, A)", 4),
    ],
)
def test_td_of_a_counted_map_in_a_condition_by_hand(datasets, runner, expression, maps):
    result = outcome(KIND, expression, RUNNERS[runner], basename="fa")
    # An error would pass for no maps
    assert "error" not in result
    assert len(result["maps"]) == maps


@pytest.mark.parametrize("runner", ["reference", "classic"])
@pytest.mark.parametrize("granularity", [False, True])
def test_td_of_a_counted_map_is_td_of_the_map(datasets, runner, granularity):
    """Counting does not change what td() says, and td() of a map that is
    not counted is as it was"""
    counted, plain = (
        outcome(
            KIND,
            f"N + td({operand})",
            RUNNERS[runner],
            basename=name,
            granularity=granularity,
        )
        for operand, name in (("A # merge(N, HA)", "fa"), ("A", "fb"))
    )
    assert compare(KIND, "td", counted, plain) is None
    assert [values[3] for values in plain["maps"]] == [12, 13, 14, 15]


# The classic merge() compares the texts if(1, 1,2) and (1) of two objects of
# the same map and keeps both (8 maps); the profile folds the text of if() to
# the number 1, equal to the count, and remembers the text on the content.
def test_merge_of_a_folded_if_and_its_count(datasets):
    assert_equal("merge(if(isnull(A # N), 1, 2), A # N)")


def test_merge_of_a_folded_if_and_its_count_in_the_reference(datasets):
    """The classic algebra keeps both lists, 8 maps"""
    reference = outcome(
        KIND,
        "merge(if(isnull(A # N), 1, 2), A # N)",
        RUNNERS["reference"],
        basename="fa",
        register_null=True,
    )
    assert len(reference["maps"]) == 8


@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", CLEARED_COUNT)
def test_if_on_time_clears_a_count(datasets, expression, granularity):
    assert_equal(expression, granularity=granularity)


@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", TIME_CONDITIONS_BEYOND_32_BITS)
def test_time_conditions_beyond_32_bits(datasets, expression, granularity):
    assert_equal(expression, granularity=granularity)


@pytest.mark.parametrize("register_null", [False, True])
@pytest.mark.parametrize("expression", PLAIN_SELECTIONS)
def test_a_plain_selection_keeps_every_map(datasets, expression, register_null):
    assert_equal(expression, register_null=register_null)


@pytest.mark.parametrize("expression", LIST_ORDER_PARTNERS)
def test_partners_in_the_order_of_their_list(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", LOGICAL_WITH_ALL_PARTNERS)
def test_logical_operators_join_all_partners(datasets, expression, granularity):
    assert_equal(expression, granularity=granularity)


@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", MERGED_UNITS)
def test_a_merge_of_units_fails_only_when_registered(datasets, expression, granularity):
    assert_equal(expression, granularity=granularity)


# A relation over a list that mixes maps of absolute and relative time stops
# the previous implementation with a TypeError while it builds the topology,
# as it compares the start times of the two types. That crash is no result to
# reproduce; the classic algebra relates the two types to nothing, so each
# expression gives the result of the one without the maps of the other type.
CRASHED_MIXED_RELATIONS = [
    ("merge(tmap(sinst), RT) : RT", "RT : RT"),
    ("RT : merge(tmap(sinst), RT)", "RT : RT"),
    ("tmap(sinst) : merge(tmap(sinst), RT)", "tmap(sinst) : tmap(sinst)"),
    ("merge(tmap(sinst), RT) {+,equal,l} RT", "RT {+,equal,l} RT"),
]


@pytest.mark.parametrize(("expression", "unmixed"), CRASHED_MIXED_RELATIONS)
def test_a_relation_over_absolute_and_relative_time(datasets, expression, unmixed):
    reference = outcome(
        KIND, expression, RUNNERS["reference"], basename="fa", register_null=True
    )
    assert reference["error"] == "Other:TypeError"
    profile = outcome(
        KIND, expression, RUNNERS["classic"], basename="fb", register_null=True
    )
    expected = reference_outcome(KIND, unmixed, register_null=True)
    assert "error" not in expected
    assert compare(KIND, expression, expected, profile) is None
