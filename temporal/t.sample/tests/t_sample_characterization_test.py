"""The printed matrix of t.sample, pinned byte for byte

Every expected string was measured on 2026-10-14 (branch temporal-framework,
autotools build) by running the current tool in a temporary project. The
later groups (several relations per granule, start-time ties, maps outside
the sampler, granules that are not whole days, relative intervals, error
paths, -s with different extents) were measured the same day with the
fixtures of conftest.py and then checked against the temporal relations and
extents derived by hand, which are given at each test. ToolResult.text strips
the trailing newline, so every expectation is compared with .strip().

These tests pass against the unchanged tool and must keep passing after the
port; they are the guard that the port changes nothing in the output.
"""

import pytest

from grass.tools import ToolError

# The default field separator resolves to "|" (G_OPT_F_SEP answer "pipe");
# the option label "default is tabular ' | '" is misleading.
DEFAULT = """\
sampler@PERMANENT|input@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp_1@PERMANENT|in_1@PERMANENT,in_2@PERMANENT|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|in_3@PERMANENT,in_4@PERMANENT|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|in_5@PERMANENT,in_6@PERMANENT|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

ALL_NONE = """\
sampler@PERMANENT|input@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp_1@PERMANENT|None|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|None|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|None|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

PRECEDES = """\
sampler@PERMANENT|input@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp_1@PERMANENT|in_3@PERMANENT|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|in_5@PERMANENT|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|None|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

EQUAL_EQ = """\
sampler@PERMANENT|input_eq@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp_1@PERMANENT|eq_1@PERMANENT|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|None|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|eq_2@PERMANENT|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

START_EQ = """\
sampler@PERMANENT|input_eq@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp_1@PERMANENT|None|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|None|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|None|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

TWO_INPUTS = """\
sampler@PERMANENT|input@PERMANENT|input2@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp_1@PERMANENT|in_1@PERMANENT,in_2@PERMANENT|sec_1@PERMANENT|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|in_3@PERMANENT,in_4@PERMANENT|sec_2@PERMANENT|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|in_5@PERMANENT,in_6@PERMANENT|sec_3@PERMANENT|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|None|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

SPACE = """\
sampler@PERMANENT input@PERMANENT start_time end_time interval_length distance_from_begin
samp_1@PERMANENT in_1@PERMANENT,in_2@PERMANENT 2001-01-01 00:00:00 2001-01-03 00:00:00 2.0 0.0
None in_3@PERMANENT,in_4@PERMANENT 2001-01-03 00:00:00 2001-01-05 00:00:00 2.0 2.0
samp_2@PERMANENT in_5@PERMANENT,in_6@PERMANENT 2001-01-05 00:00:00 2001-01-07 00:00:00 2.0 4.0
samp_3@PERMANENT None 2001-01-07 00:00:00 2001-01-09 00:00:00 2.0 6.0"""

RELATIVE = """\
rsampler@PERMANENT|rinput@PERMANENT|start_time|end_time|interval_length|distance_from_begin
rsamp_1@PERMANENT|rin_1@PERMANENT,rin_2@PERMANENT|0|2|2|0
None|rin_3@PERMANENT,rin_4@PERMANENT|2|4|2|2
rsamp_2@PERMANENT|None|4|6|2|4"""

STR3DS = """\
sampler3@PERMANENT|input3@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp3_1@PERMANENT|in3_1@PERMANENT,in3_2@PERMANENT|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|in3_3@PERMANENT,in3_4@PERMANENT|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp3_2@PERMANENT|in3_5@PERMANENT,in3_6@PERMANENT|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp3_3@PERMANENT|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

STVDS = """\
samplerv@PERMANENT|inputv@PERMANENT|start_time|end_time|interval_length|distance_from_begin
sampv_1@PERMANENT|inv_1@PERMANENT,inv_2@PERMANENT|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|inv_3@PERMANENT,inv_4@PERMANENT|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
sampv_2@PERMANENT|inv_5@PERMANENT,inv_6@PERMANENT|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
sampv_3@PERMANENT|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

INPUT2_DEFAULT = """\
sampler@PERMANENT|input2@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp_1@PERMANENT|sec_1@PERMANENT|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|sec_2@PERMANENT|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|sec_3@PERMANENT|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

INPUT2_FOLLOWS = """\
sampler@PERMANENT|input2@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp_1@PERMANENT|None|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|sec_1@PERMANENT|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|sec_2@PERMANENT|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|sec_3@PERMANENT|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

INPUT2_PRECEDES = """\
sampler@PERMANENT|input2@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp_1@PERMANENT|sec_2@PERMANENT|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|sec_3@PERMANENT|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|None|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

RIM_PRECEDES = """\
sampler@PERMANENT|rim@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp_1@PERMANENT|None|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|None|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|None|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|rim_2@PERMANENT|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

RIM_NONE = """\
sampler@PERMANENT|rim@PERMANENT|start_time|end_time|interval_length|distance_from_begin
samp_1@PERMANENT|None|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|None|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|None|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

TIME_OF_DAY = """\
tsamp@PERMANENT|tin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
tg_1@PERMANENT|tin_1@PERMANENT|2001-01-01 00:00:00|2001-01-01 06:00:00|0.25|0.0
tg_2@PERMANENT|tin_2@PERMANENT|2001-01-01 06:00:00|2001-01-01 18:00:00|0.5|0.25
None|None|2001-01-01 18:00:00|2001-02-01 00:00:00|30.25|0.75
tg_3@PERMANENT|tin_3@PERMANENT|2001-02-01 00:00:00|2001-03-01 00:00:00|28.0|31.0"""

RELATIVE_INTERVALS = """\
rsampler@PERMANENT|rint@PERMANENT|start_time|end_time|interval_length|distance_from_begin
rsamp_1@PERMANENT|rint_2@PERMANENT,rint_1@PERMANENT|0|2|2|0
None|rint_2@PERMANENT,rint_3@PERMANENT|2|4|2|2
rsamp_2@PERMANENT|None|4|6|2|4"""

RELATIVE_INTERVALS_CONTAIN = """\
rsampler@PERMANENT|rint@PERMANENT|start_time|end_time|interval_length|distance_from_begin
rsamp_1@PERMANENT|rint_1@PERMANENT|0|2|2|0
None|rint_3@PERMANENT|2|4|2|2
rsamp_2@PERMANENT|None|4|6|2|4"""

SPATIAL_ALL = """\
spsamp@PERMANENT|spin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
sp_g1@PERMANENT|spin_1@PERMANENT,spin_2@PERMANENT,spin_3@PERMANENT,spin_4@PERMANENT,spin_5@PERMANENT,spin_6@PERMANENT,spin_7@PERMANENT,spin_8@PERMANENT|2001-01-01 00:00:00|2001-01-09 00:00:00|8.0|0.0
sp_g2@PERMANENT|spin_9@PERMANENT,spin_10@PERMANENT,spin_11@PERMANENT,spin_12@PERMANENT,spin_13@PERMANENT,spin_14@PERMANENT,spin_15@PERMANENT,spin_16@PERMANENT|2001-01-09 00:00:00|2001-01-17 00:00:00|8.0|8.0"""

SPATIAL_S = """\
spsamp@PERMANENT|spin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
sp_g1@PERMANENT|spin_1@PERMANENT,spin_2@PERMANENT,spin_3@PERMANENT,spin_4@PERMANENT,spin_5@PERMANENT,spin_6@PERMANENT,spin_7@PERMANENT|2001-01-01 00:00:00|2001-01-09 00:00:00|8.0|0.0
sp_g2@PERMANENT|spin_9@PERMANENT,spin_12@PERMANENT|2001-01-09 00:00:00|2001-01-17 00:00:00|8.0|8.0"""

GAP_ALL = """\
spgap@PERMANENT|spgapin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
sg_1@PERMANENT|gap_5@PERMANENT|2001-01-01 00:00:00|2001-01-05 00:00:00|4.0|0.0
None|gap_1@PERMANENT,gap_2@PERMANENT,gap_3@PERMANENT,gap_4@PERMANENT|2001-01-05 00:00:00|2001-01-09 00:00:00|4.0|4.0
sg_2@PERMANENT|gap_6@PERMANENT|2001-01-09 00:00:00|2001-01-13 00:00:00|4.0|8.0"""

GAP_S = """\
spgap@PERMANENT|spgapin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
sg_1@PERMANENT|gap_5@PERMANENT|2001-01-01 00:00:00|2001-01-05 00:00:00|4.0|0.0
None|gap_1@PERMANENT,gap_2@PERMANENT,gap_4@PERMANENT|2001-01-05 00:00:00|2001-01-09 00:00:00|4.0|4.0
sg_2@PERMANENT|gap_6@PERMANENT|2001-01-09 00:00:00|2001-01-13 00:00:00|4.0|8.0"""

GAP_PRECEDES = """\
spgap@PERMANENT|spgapin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
sg_1@PERMANENT|gap_1@PERMANENT|2001-01-01 00:00:00|2001-01-05 00:00:00|4.0|0.0
None|None|2001-01-05 00:00:00|2001-01-09 00:00:00|4.0|4.0
sg_2@PERMANENT|None|2001-01-09 00:00:00|2001-01-13 00:00:00|4.0|8.0"""

GAP_PRECEDES_S = """\
spgap@PERMANENT|spgapin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
sg_1@PERMANENT|None|2001-01-01 00:00:00|2001-01-05 00:00:00|4.0|0.0
None|None|2001-01-05 00:00:00|2001-01-09 00:00:00|4.0|4.0
sg_2@PERMANENT|None|2001-01-09 00:00:00|2001-01-13 00:00:00|4.0|8.0"""

SPATIAL_3D_ALL = """\
sp3samp@PERMANENT|sp3in@PERMANENT|start_time|end_time|interval_length|distance_from_begin
sp3_g@PERMANENT|sp3_1@PERMANENT,sp3_2@PERMANENT,sp3_3@PERMANENT|2001-01-01 00:00:00|2001-01-09 00:00:00|8.0|0.0"""

SPATIAL_3D_S = """\
sp3samp@PERMANENT|sp3in@PERMANENT|start_time|end_time|interval_length|distance_from_begin
sp3_g@PERMANENT|sp3_1@PERMANENT,sp3_3@PERMANENT|2001-01-01 00:00:00|2001-01-09 00:00:00|8.0|0.0"""

# A header that names both inputs above a body that has the columns of one only
MIXED_BODY = """\
samp_1@PERMANENT|in_1@PERMANENT,in_2@PERMANENT|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
None|in_3@PERMANENT,in_4@PERMANENT|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
samp_2@PERMANENT|in_5@PERMANENT,in_6@PERMANENT|2001-01-05 00:00:00|2001-01-07 00:00:00|2.0|4.0
samp_3@PERMANENT|None|2001-01-07 00:00:00|2001-01-09 00:00:00|2.0|6.0"""

MIXED_HEADER = (
    "sampler@PERMANENT|{}|start_time|end_time|interval_length|distance_from_begin"
)


def ord_table(stds, first, second):
    """The matrix of ordsamp (og_1 [d10,d20), og_2 [d20,d30)) from two map lists"""

    def maps(names):
        return ",".join(f"{n}@PERMANENT" for n in names) if names else "None"

    return (
        f"ordsamp@PERMANENT|{stds}@PERMANENT|start_time|end_time|"
        "interval_length|distance_from_begin\n"
        f"og_1@PERMANENT|{maps(first)}|2001-01-11 00:00:00|2001-01-21 00:00:00|"
        "10.0|0.0\n"
        f"og_2@PERMANENT|{maps(second)}|2001-01-21 00:00:00|2001-01-31 00:00:00|"
        "10.0|10.0"
    )


# Relations of ordin to the granules, derived from the intervals in conftest.py
# (granule key of the topology, maps in start-time order within a key):
#
#   og_1 [d10,d20):  DURING yy_during | EQUAL ss_equal | OVERLAPPED vv_ovl_early
#                    OVERLAPS uu_ovl_late | FOLLOWS tt_before | PRECEDES pp_after
#                    CONTAINS xx_starts zz_early ww_finishes aa_late
#                    STARTED xx_starts | FINISHED ww_finishes
#   og_2 [d20,d30):  OVERLAPPED yy_during uu_ovl_late | FOLLOWS ss_equal
#                    ww_finishes | CONTAINS pp_after qq_in_og2 | STARTED pp_after
#
# The expected lists follow the relations in the order the method list names
# them (after "start", "overlap" and "contain" are expanded), a map that is
# in two requested relations once, at its first place. "start" expands to
# OVERLAPPED STARTS STARTED FINISHES CONTAINS EQUALS; the last key is never
# filed, which is why "start" drops equal maps.
ORDER_CASES = {
    "during,overlap,contain,equal": (
        [
            "yy_during",
            "ss_equal",
            "vv_ovl_early",
            "uu_ovl_late",
            "xx_starts",
            "zz_early",
            "ww_finishes",
            "aa_late",
        ],
        ["yy_during", "uu_ovl_late", "pp_after", "qq_in_og2"],
    ),
    "equal,contain,overlap,during": (
        [
            "ss_equal",
            "yy_during",
            "vv_ovl_early",
            "uu_ovl_late",
            "xx_starts",
            "zz_early",
            "ww_finishes",
            "aa_late",
        ],
        ["yy_during", "uu_ovl_late", "pp_after", "qq_in_og2"],
    ),
    "start": (
        ["vv_ovl_early", "xx_starts", "zz_early", "ww_finishes", "aa_late"],
        ["yy_during", "uu_ovl_late", "pp_after", "qq_in_og2"],
    ),
    "contain,start": (
        ["vv_ovl_early", "xx_starts", "zz_early", "ww_finishes", "aa_late"],
        ["yy_during", "uu_ovl_late", "pp_after", "qq_in_og2"],
    ),
    "start,during": (
        [
            "yy_during",
            "vv_ovl_early",
            "xx_starts",
            "zz_early",
            "ww_finishes",
            "aa_late",
        ],
        ["yy_during", "uu_ovl_late", "pp_after", "qq_in_og2"],
    ),
    "during": (["yy_during"], []),
    "overlap": (["vv_ovl_early", "uu_ovl_late"], ["yy_during", "uu_ovl_late"]),
    "contain": (
        ["xx_starts", "zz_early", "ww_finishes", "aa_late"],
        ["pp_after", "qq_in_og2"],
    ),
    "equal": (["ss_equal"], []),
    "follows": (["tt_before"], ["ss_equal", "ww_finishes"]),
    "precedes": (["pp_after"], []),
    "follows,precedes": (["tt_before", "pp_after"], ["ss_equal", "ww_finishes"]),
    "precedes,follows": (["pp_after", "tt_before"], ["ss_equal", "ww_finishes"]),
    "during,during,contain,contain": (
        ["yy_during", "xx_starts", "zz_early", "ww_finishes", "aa_late"],
        ["pp_after", "qq_in_og2"],
    ),
    "overlap,during": (
        ["yy_during", "vv_ovl_early", "uu_ovl_late"],
        ["yy_during", "uu_ovl_late"],
    ),
    "contain,overlap": (
        [
            "vv_ovl_early",
            "uu_ovl_late",
            "xx_starts",
            "zz_early",
            "ww_finishes",
            "aa_late",
        ],
        ["yy_during", "uu_ovl_late", "pp_after", "qq_in_og2"],
    ),
}


EQUAL_STARTS = """\
eqsamp@PERMANENT|eqin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
eqs_1@PERMANENT|eqi_1@PERMANENT|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
eqs_2@PERMANENT|eqi_1@PERMANENT,eqi_2@PERMANENT|2001-01-01 00:00:00|2001-01-06 00:00:00|5.0|0.0
None|eqi_3@PERMANENT|2001-01-06 00:00:00|2001-01-08 00:00:00|2.0|5.0
eqs_3@PERMANENT|eqi_4@PERMANENT|2001-01-08 00:00:00|2001-01-10 00:00:00|2.0|7.0"""

EQUAL_STARTS_PRECEDES = """\
eqsamp@PERMANENT|eqin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
eqs_1@PERMANENT|None|2001-01-01 00:00:00|2001-01-03 00:00:00|2.0|0.0
eqs_2@PERMANENT|None|2001-01-01 00:00:00|2001-01-06 00:00:00|5.0|0.0
None|None|2001-01-06 00:00:00|2001-01-08 00:00:00|2.0|5.0
eqs_3@PERMANENT|None|2001-01-08 00:00:00|2001-01-10 00:00:00|2.0|7.0"""

LAYERS = """\
laysamp@PERMANENT|layin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
laysamp_1@PERMANENT|lay:1@PERMANENT,lay:2@PERMANENT|2001-01-01 00:00:00|2001-01-04 00:00:00|3.0|0.0"""

VECTOR_SPATIAL_ALL = """\
svsamp@PERMANENT|svin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
svg@PERMANENT|sv_1@PERMANENT,sv_2@PERMANENT,sv_3@PERMANENT,sv_4@PERMANENT|2001-01-01 00:00:00|2001-01-09 00:00:00|8.0|0.0"""

VECTOR_SPATIAL_S = """\
svsamp@PERMANENT|svin@PERMANENT|start_time|end_time|interval_length|distance_from_begin
svg@PERMANENT|sv_1@PERMANENT,sv_2@PERMANENT,sv_4@PERMANENT|2001-01-01 00:00:00|2001-01-09 00:00:00|8.0|0.0"""


def run(tools, **kwargs):
    """stdout of t.sample, stripped as ToolResult.text returns it"""
    return tools.t_sample(**kwargs).text


def test_default_method_with_header(sample_session):
    assert run(sample_session, input="input", sample="sampler", flags="c") == DEFAULT


def test_method_start_equals_the_default_here(sample_session):
    """The quirk (start drops equal) is pinned on input_eq; on this instant
    input start and the default list select the same maps"""
    assert (
        run(sample_session, input="input", sample="sampler", method="start", flags="c")
        == DEFAULT
    )


def test_method_contain_equals_the_default(sample_session):
    """Only contains fires on the instant input, so contain matches the default"""
    assert (
        run(
            sample_session, input="input", sample="sampler", method="contain", flags="c"
        )
        == DEFAULT
    )


@pytest.mark.parametrize("method", ["during", "overlap", "equal", "follows"])
def test_methods_that_relate_nothing(sample_session, method):
    assert (
        run(sample_session, input="input", sample="sampler", method=method, flags="c")
        == ALL_NONE
    )


def test_method_precedes(sample_session):
    assert (
        run(
            sample_session,
            input="input",
            sample="sampler",
            method="precedes",
            flags="c",
        )
        == PRECEDES
    )


def test_method_equal_lists_the_equal_maps(sample_session):
    assert (
        run(
            sample_session,
            input="input_eq",
            sample="sampler",
            method="equal",
            flags="c",
        )
        == EQUAL_EQ
    )


def test_method_start_drops_the_equal_maps(sample_session):
    """start appends "equals", which upper-cases to the key "EQUALS" that the
    topology never files, so the equal maps are not listed"""
    assert (
        run(
            sample_session,
            input="input_eq",
            sample="sampler",
            method="start",
            flags="c",
        )
        == START_EQ
    )


def test_no_header(sample_session):
    assert run(sample_session, input="input", sample="sampler") == "\n".join(
        DEFAULT.splitlines()[1:]
    )


def test_two_inputs(sample_session):
    assert (
        run(sample_session, input="input,input2", sample="sampler", flags="c")
        == TWO_INPUTS
    )


def test_space_separator(sample_session):
    assert (
        run(
            sample_session,
            input="input",
            sample="sampler",
            separator="space",
            flags="c",
        )
        == SPACE
    )


def test_spatial_flag_does_not_change_the_output(sample_session):
    assert run(sample_session, input="input", sample="sampler", flags="cs") == run(
        sample_session, input="input", sample="sampler", flags="c"
    )


def test_relative_time(sample_session):
    assert run(sample_session, input="rinput", sample="rsampler", flags="c") == RELATIVE


def test_str3ds_type(sample_session):
    assert (
        run(
            sample_session,
            input="input3",
            sample="sampler3",
            intype="str3ds",
            samtype="str3ds",
            flags="c",
        )
        == STR3DS
    )


def test_stvds_type(sample_session):
    assert (
        run(
            sample_session,
            input="inputv",
            sample="samplerv",
            intype="stvds",
            samtype="stvds",
            flags="c",
        )
        == STVDS
    )


def test_default_method_is_during_overlap_contain_equal(sample_session):
    """Without method= the relations are the default list, in its order"""
    first, second = ORDER_CASES["during,overlap,contain,equal"]
    assert run(sample_session, input="ordin", sample="ordsamp", flags="c") == ord_table(
        "ordin", first, second
    )


@pytest.mark.parametrize("method", list(ORDER_CASES))
def test_related_maps_follow_the_relations_in_method_order(sample_session, method):
    """A granule related to many maps lists them relation by relation

    Within one relation the maps are in start-time order (not alphabetical:
    zz_early comes before aa_late). The names in the method list and the
    blocks that "start", "overlap" and "contain" expand to decide the order of
    the relations, so contain,overlap lists overlap before contain, as the
    default does (the maps differ: the default also has the during and equal
    maps). A map in two relations is listed once. A map related to both
    granules (yy_during, uu_ovl_late) is listed in both rows.
    """
    first, second = ORDER_CASES[method]
    assert run(
        sample_session, input="ordin", sample="ordsamp", method=method, flags="c"
    ) == ord_table("ordin", first, second)


@pytest.mark.parametrize(
    ("stds", "first"),
    [
        ("tiein", ["tie_a", "tie_b"]),
        ("tiein2", ["tie_a", "tie_b"]),
        ("tiein3", ["tie_c", "tie_d"]),
    ],
)
def test_maps_with_the_same_start_time(sample_session, stds, first):
    """Ties of the start time come out in map-id order

    Measured with three datasets: tie_b [d12,d15) and tie_a [d12,d17)
    registered in this order (tiein) and in the opposite order (tiein2), and
    tie_d [d12,d17) and tie_c [d12,d15) (tiein3). The registration order does
    not matter, and neither does the length: tie_a before tie_b although it is
    longer, tie_c before tie_d although it is shorter. Both maps of a dataset
    lie inside og_1 (relation CONTAINS).
    """
    assert run(
        sample_session, input=stds, sample="ordsamp", method="contain", flags="c"
    ) == ord_table(stds, first, [])


def test_maps_outside_the_sampler_get_no_row(sample_session):
    """rim_1 (d-1), rim_2 (d8, the excluded end of samp_3) and rim_3 (d9)"""
    assert run(sample_session, input="rim", sample="sampler", flags="c") == RIM_NONE


def test_map_that_starts_at_the_end_of_a_granule_precedes_it(sample_session):
    """rim_2 starts on 2001-01-09, where samp_3 ends: the relation precedes"""
    assert (
        run(sample_session, input="rim", sample="sampler", method="precedes", flags="c")
        == RIM_PRECEDES
    )


def test_granules_that_are_not_whole_days(sample_session):
    """Lengths and distances are fractions of a day; the gap is a row of its own

    tg_1 is 6 hours (0.25), tg_2 12 hours (0.5) from 0.25 days after the
    first start; the gap from 2001-01-01 18:00 to 2001-02-01 is 30 days and
    6 hours, tg_3 is February (28 days) and starts 31 days after the first.
    """
    assert run(sample_session, input="tin", sample="tsamp", flags="c") == TIME_OF_DAY


def test_relative_time_intervals(sample_session):
    """Relative times print as integers without unit; rint_2 [1,3) overlaps
    rsamp_1 [0,2) and is listed before rint_1 [0,1), which lies inside rsamp_1,
    although it starts later: for the granule the key of rint_2 is OVERLAPS
    and the relevant key of rint_1 is CONTAINS (it also carries STARTED, which
    the default method does not list), and the default method lists OVERLAPS
    before CONTAINS"""
    assert (
        run(sample_session, input="rint", sample="rsampler", flags="c")
        == RELATIVE_INTERVALS
    )
    assert (
        run(
            sample_session, input="rint", sample="rsampler", method="contain", flags="c"
        )
        == RELATIVE_INTERVALS_CONTAIN
    )


def test_interval_input_default(sample_session):
    assert (
        run(sample_session, input="input2", sample="sampler", flags="c")
        == INPUT2_DEFAULT
    )


def test_interval_input_follows(sample_session):
    assert (
        run(
            sample_session,
            input="input2",
            sample="sampler",
            method="follows",
            flags="c",
        )
        == INPUT2_FOLLOWS
    )


def test_interval_input_precedes(sample_session):
    assert (
        run(
            sample_session,
            input="input2",
            sample="sampler",
            method="precedes",
            flags="c",
        )
        == INPUT2_PRECEDES
    )


def test_mapset_qualified_names_print_the_same(sample_session):
    assert (
        run(
            sample_session,
            input="input@PERMANENT",
            sample="sampler@PERMANENT",
            flags="c",
        )
        == DEFAULT
    )


def test_tab_separator(sample_session):
    assert run(
        sample_session, input="input", sample="sampler", separator="tab", flags="c"
    ) == DEFAULT.replace("|", "\t")


def test_comma_separator_falls_back_to_pipe_with_spaces(sample_session):
    """A comma would clash with the map list, so " | " is printed instead"""
    assert run(
        sample_session, input="input", sample="sampler", separator="comma", flags="c"
    ) == DEFAULT.replace("|", " | ")


def test_spatial_flag_filters_by_extent(sample_session):
    """-s keeps the maps whose extent touches the granule's, edges and corners

    sp_g1 covers (w 40, e 80, s 20, n 60). The maps spin_1..spin_8 have the
    extents identical, partial overlap, inside, covering, east edge (x = 80
    shared), corner ((80, 60) shared), north edge (y = 60 shared) and
    one cell off in x (w 90): all are kept but spin_8. sp_g2 covers (w 0,
    e 40, s 0, n 20), which touches spin_9 (identical to sp_g1's extent)
    in the corner (40, 20) only, and the covering spin_12.
    """
    assert run(sample_session, input="spin", sample="spsamp", flags="c") == SPATIAL_ALL
    assert run(sample_session, input="spin", sample="spsamp", flags="cs") == SPATIAL_S


@pytest.mark.parametrize("method", ["start", "contain"])
def test_spatial_flag_with_other_methods(sample_session, method):
    assert (
        run(sample_session, input="spin", sample="spsamp", method=method, flags="cs")
        == SPATIAL_S
    )


def test_spatial_flag_on_gap_rows(sample_session):
    """A gap row has the extent (0, 0, 0, 0), so -s keeps only the maps whose
    extent touches the origin: gap_1 in a corner, gap_2 and gap_4, not gap_3"""
    assert run(sample_session, input="spgapin", sample="spgap", flags="c") == GAP_ALL
    assert run(sample_session, input="spgapin", sample="spgap", flags="cs") == GAP_S


def test_spatial_flag_filters_adjacent_maps_too(sample_session):
    """gap_1 starts where sg_1 ends; -s drops it as it is far from sg_1"""
    assert (
        run(
            sample_session,
            input="spgapin",
            sample="spgap",
            method="precedes",
            flags="c",
        )
        == GAP_PRECEDES
    )
    assert (
        run(
            sample_session,
            input="spgapin",
            sample="spgap",
            method="precedes",
            flags="cs",
        )
        == GAP_PRECEDES_S
    )


def test_spatial_flag_on_str3ds_ignores_bottom_and_top(sample_session):
    """sp3_1 lies at b 100, t 110 over the granule's x/y and is kept; sp3_2,
    one cell east of the granule, is dropped; sp3_3 touches along x = 80"""
    kwargs = {
        "input": "sp3in",
        "sample": "sp3samp",
        "intype": "str3ds",
        "samtype": "str3ds",
    }
    assert run(sample_session, flags="c", **kwargs) == SPATIAL_3D_ALL
    assert run(sample_session, flags="cs", **kwargs) == SPATIAL_3D_S


def test_sampler_of_instants_prints_nothing(sample_session):
    result = sample_session.t_sample(input="input", sample="isamp", flags="c")
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == (
        "ERROR: The temporal map type of the sample dataset must be interval\n"
    )


@pytest.mark.parametrize(
    ("inputs", "sampler"), [("rinput", "sampler"), ("input", "rsampler")]
)
def test_mixed_temporal_types_print_nothing(sample_session, inputs, sampler):
    result = sample_session.t_sample(input=inputs, sample=sampler, flags="c")
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == (
        "ERROR: The space time datasets must be of the same temporal type\n"
    )


@pytest.mark.parametrize("inputs", ["input,rinput", "rinput,input"])
def test_failed_input_stays_in_the_header_only(sample_session, inputs):
    """The input of the wrong temporal type is dropped from the rows but not
    from the header, so the header has one column more than the body"""
    result = sample_session.t_sample(input=inputs, sample="sampler", flags="c")
    header = MIXED_HEADER.format(
        "|".join(f"{name}@PERMANENT" for name in inputs.split(","))
    )
    assert result.text == f"{header}\n{MIXED_BODY}"
    assert result.stderr == (
        "ERROR: The space time datasets must be of the same temporal type\n"
    )


@pytest.mark.parametrize(
    ("kwargs", "missing"),
    [
        ({"input": "nonexist", "sample": "sampler"}, "nonexist"),
        ({"input": "input", "sample": "nonexist"}, "nonexist"),
        ({"input": "input", "sample": "sampler", "intype": "stvds"}, "input"),
    ],
)
def test_missing_dataset_is_fatal(sample_session, kwargs, missing):
    with pytest.raises(ToolError) as error:
        sample_session.t_sample(**kwargs)
    assert error.value.returncode == 1
    assert error.value.errors == (
        f"ERROR: Dataset <{missing}@PERMANENT> not found in temporal database\n"
    )


def test_sampler_with_equal_start_times(sample_session):
    """The granules eqs_1 [d0,d2) and eqs_2 [d0,d5) start together

    Such a sampler has an invalid topology, which t.sample does not check.
    The rows follow the order (start, end) in which the core sorts its slots,
    so the shorter granule comes first, and the gap [d5,d7) is a row of its
    own. The instant eqi_1 on d1 lies in both granules; method=start gives
    the same rows because the inputs are instants. The rows were measured on
    2026-10-14 with t.sample on the fixture of conftest.py; the maps in each
    row follow from the instants d1, d3, d6 and d8.
    """
    kwargs = {"input": "eqin", "sample": "eqsamp", "flags": "c"}
    assert run(sample_session, **kwargs) == EQUAL_STARTS
    assert run(sample_session, method="start", **kwargs) == EQUAL_STARTS


def test_sampler_with_equal_start_times_keeps_all_rows_when_nothing_relates(
    sample_session,
):
    """No instant precedes a granule it lies in, but the four rows, the gap
    among them, stay in the same order"""
    assert (
        run(
            sample_session,
            input="eqin",
            sample="eqsamp",
            method="precedes",
            flags="c",
        )
        == EQUAL_STARTS_PRECEDES
    )


@pytest.mark.parametrize("method", [None, "start"])
def test_stvds_layers_print_as_name_layer(sample_session, method):
    """Layers 1 and 2 of the vector map lay are registered as lay:1 and lay:2
    and printed under these ids. The format was measured on 2026-10-14 by
    registering "lay:1|<time>" and listing the result of t.sample. The default
    method and method=start both relate the instants to the granule."""
    assert (
        run(
            sample_session,
            input="layin",
            sample="laysamp",
            intype="stvds",
            samtype="stvds",
            flags="c",
            **({} if method is None else {"method": method}),
        )
        == LAYERS
    )


def test_spatial_flag_on_stvds(sample_session):
    """The sampler svg covers (w 40, e 80, s 20, n 60). sv_1 has the same
    extent, sv_2 lies inside, sv_4 shares the edge x = 80 and sv_3, one cell
    east, is disjoint: -s drops only sv_3"""
    kwargs = {
        "input": "svin",
        "sample": "svsamp",
        "intype": "stvds",
        "samtype": "stvds",
    }
    assert run(sample_session, flags="c", **kwargs) == VECTOR_SPATIAL_ALL
    assert run(sample_session, flags="cs", **kwargs) == VECTOR_SPATIAL_S


@pytest.mark.parametrize("method", ["overlaps", "overlapped"])
def test_methods_overlaps_and_overlapped_are_rejected(sample_session, method):
    """The parser lists start, during, overlap, contain, equal, follows and
    precedes; the inverse relations overlaps and overlapped are not options"""
    with pytest.raises(ToolError) as error:
        sample_session.t_sample(input="input", sample="sampler", method=method)
    assert error.value.returncode == 1
    assert (
        f"ERROR: Value <{method}> out of range for parameter <method>"
        in error.value.errors
    )
