"""Tests for the raster backend and plan() of the algebra core

plan() runs nothing, so these tests need no session.
"""

import datetime
from dataclasses import replace

import pytest

from grass.temporal.algebra import parser as algebra_parser
from grass.temporal.algebra.backends import ModuleCall, Raster3DBackend, RasterBackend
from grass.temporal.algebra.content import (
    NULL,
    Call,
    Const,
    MapRef,
    SeriesAggregate,
    SeriesReduce,
)
from grass.temporal.algebra.materialize import plan
from grass.temporal.algebra.operations import gather, where
from grass.temporal.algebra.relations import contains
from grass.temporal.algebra.series import Series, Slot
from grass.temporal.algebra.time_functions import retime, timevar

A1 = MapRef("a1@PERMANENT")
A2 = MapRef("a2@PERMANENT")


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (A1, '"a1@PERMANENT"'),
        (MapRef("a1@PERMANENT", (1, 0)), '"a1@PERMANENT"[1,0]'),
        (Const(5), "5"),
        (Const(2.0), "2.0"),
        (Const(1e-05), "1.0e-05"),
        (Const(1e16), "1.0e+16"),
        (Const(1.5e-07), "1.5e-07"),
        (Const(2**31 - 1), "2147483647"),
        (Const(-(2**31) + 1), "-2147483647"),
        (Const(2**31), "2147483648.0"),
        (Const(-(2**31)), "-2147483648.0"),
        (Const(3000000000), "3000000000.0"),
        (Const(True), "1"),
        (NULL, "null()"),
        (Call("+", (A1, Const(1))), '("a1@PERMANENT" + 1)'),
        (
            Call("*", (Call("+", (A1, A2)), Const(2))),
            '(("a1@PERMANENT" + "a2@PERMANENT") * 2)',
        ),
        (Call("neg", (A1,)), '(-"a1@PERMANENT")'),
        (Call("neg", (Call("neg", (A1,)),)), '(-(-"a1@PERMANENT"))'),
        (Call("neg", (Const(-1),)), "(-(-1))"),
        (Call("-", (A1, Const(-1))), '("a1@PERMANENT" - -1)'),
        (Call("!", (A1,)), '(!"a1@PERMANENT")'),
        (Call("!=", (A1, Const(0))), '("a1@PERMANENT" != 0)'),
        (Call("&&", (A1, A2)), '("a1@PERMANENT" && "a2@PERMANENT")'),
        (Call("||", (A1, A2)), '("a1@PERMANENT" || "a2@PERMANENT")'),
        (
            Call("-", (A1, A2, Const(1))),
            '("a1@PERMANENT" - "a2@PERMANENT" - 1)',
        ),
        (
            Call("min", (A1, A2, Const(1))),
            'min("a1@PERMANENT", "a2@PERMANENT", 1)',
        ),
        (Call("^", (A1, A2)), '("a1@PERMANENT" ^ "a2@PERMANENT")'),
        (Call("if", (A1, A2, NULL)), 'if("a1@PERMANENT", "a2@PERMANENT", null())'),
        (Call("isnull", (A1,)), 'isnull("a1@PERMANENT")'),
        (Call("nmin", (A1, A2)), 'nmin("a1@PERMANENT", "a2@PERMANENT")'),
        (Call("nmax", (A1, A2)), 'nmax("a1@PERMANENT", "a2@PERMANENT")'),
        (Call("abs", (A1,)), 'abs("a1@PERMANENT")'),
    ],
)
def test_expression(content, expected):
    assert RasterBackend().expression(content) == expected


@pytest.mark.parametrize(
    "value", [datetime.date(2001, 1, 1), "text", float("nan"), float("inf")]
)
def test_value_without_raster_form_is_rejected(value):
    with pytest.raises(TypeError, match="raster map expression"):
        RasterBackend().expression(Const(value))


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (Call("frobnicate", (A1,)), "neither an operator nor a function"),
        # ^ is right-associative in r.mapcalc, so it is never written as one
        # flat call.
        (Call("^", (A1, A2, A1)), "needs two operands"),
        (Call("+", (A1,)), "at least two operands"),
        (Call("neg", (A1, A2)), "needs one operand"),
        # A unary minus is spelled neg, so that no reader takes it for a
        # subtraction with a missing operand.
        (Call("-", (A1,)), "at least two operands"),
    ],
)
def test_function_without_raster_form_is_rejected(content, message):
    with pytest.raises(ValueError, match=message):
        RasterBackend().expression(content)


def test_unrenderable_function_is_rejected_when_planning(make_series):
    a = make_series("a", (1, 2))
    with pytest.raises(ValueError, match="neither an operator nor a function"):
        plan(Series((Slot(a.slots[0].extent, Call("frobnicate", (A1,))),)), "R")


def test_negative_literal_outside_int32_keeps_its_sign():
    assert RasterBackend().expression(Call("neg", (Const(3000000000),))) == (
        "(-3000000000.0)"
    )
    assert RasterBackend().expression(Call("neg", (Const(-3000000000),))) == (
        "(-(-3000000000.0))"
    )


def test_if_without_else_is_rejected():
    with pytest.raises(ValueError, match="three or four arguments"):
        RasterBackend().expression(Call("if", (A1, A2)))


def test_if_with_three_branches_is_written_as_it_is():
    assert RasterBackend().expression(Call("if", (A1, A2, Const(0), NULL))) == (
        'if("a1@PERMANENT", "a2@PERMANENT", 0, null())'
    )


def test_if_with_more_than_four_arguments_is_rejected_by_the_backend():
    with pytest.raises(ValueError, match="three or four arguments"):
        RasterBackend().expression(Call("if", (A1, A2, A2, A2, A2)))


def test_integer_too_large_for_a_float_is_rejected(make_series):
    with pytest.raises(ValueError, match="too large"):
        RasterBackend().expression(Const(10**400))
    a = make_series("a", (1, 2))
    with pytest.raises(ValueError, match="too large"):
        plan(a + 10**400, "R")


@pytest.mark.parametrize("keyword", [{}, {"basename": 'b"c'}])
def test_output_name_with_a_double_quote_is_rejected(make_series, keyword):
    """The expression is "name"=..., so a quote in the name would end it"""
    a = make_series("a", (1, 2))
    with pytest.raises(ValueError, match="quote"):
        plan(a * 1, 'a"b', **keyword)


def test_names_with_operator_characters_are_quoted(make_series):
    odd = Series(
        (
            Slot(
                make_series("a", (1, 2)).slots[0].extent,
                Call("+", (MapRef("a-b@PERMANENT", (0, 1)), MapRef("5@PERMANENT"))),
            ),
        )
    )
    (call,) = plan(odd, "my-res").processes
    assert call.parameters["expression"] == (
        '"my-res_0"=("a-b@PERMANENT"[0,1] + "5@PERMANENT")'
    )


def test_temporary_maps_of_an_odd_name_are_quoted_in_expressions_only(make_series):
    a = make_series("a", (1, 2), (2, 3))
    b = make_series("b", (1, 3))
    reduced = gather(b, contains, a * 2, reduce="sum", nulls="skip")
    chain = plan(reduced + 1, "my-res")
    assert [call.name for call in chain.processes] == [
        "r.mapcalc",
        "r.mapcalc",
        "r.series",
        "r.mapcalc",
    ]
    assert chain.processes[0].parameters["expression"] == (
        '"my-res_0_tmp0"=("a1@PERMANENT" * 2)'
    )
    assert chain.processes[2] == ModuleCall(
        "r.series",
        {"output": "my-res_0_tmp2", "method": "sum"},
        inputs=("my-res_0_tmp0", "my-res_0_tmp1"),
    )
    assert chain.processes[3].parameters["expression"] == (
        '"my-res_0"=("my-res_0_tmp2" + 1)'
    )
    assert chain.remove == ("my-res_0_tmp0", "my-res_0_tmp1", "my-res_0_tmp2")


def test_one_mapcalc_call_per_map(make_series):
    a = make_series("a", (1, 2), (2, 3))
    chain = plan(a + 1, "R")
    assert [m.name for m in chain.maps] == ["R_0", "R_1"]
    assert chain.processes == [
        ModuleCall(
            "r.mapcalc", {"expression": '"R_0"=("a1@PERMANENT" + 1)', "nprocs": 1}
        ),
        ModuleCall(
            "r.mapcalc", {"expression": '"R_1"=("a2@PERMANENT" + 1)', "nprocs": 1}
        ),
    ]
    assert chain.register == [
        ("R_0", datetime.datetime(2001, 1, 1), datetime.datetime(2001, 1, 2)),
        ("R_1", datetime.datetime(2001, 1, 2), datetime.datetime(2001, 1, 3)),
    ]
    assert chain.name == "R"
    assert chain.stds_type == "strds"
    assert chain.temporal_type == "absolute"
    assert chain.remove == ()


def test_instant_registers_without_end(make_series):
    a = make_series("a", 1, 2)
    chain = plan(a + 1, "R")
    assert chain.register == [
        ("R_0", datetime.datetime(2001, 1, 1), None),
        ("R_1", datetime.datetime(2001, 1, 2), None),
    ]


def test_relative_time_registers_numbers(make_series):
    r = make_series("r", (0, 1), (1, 3), unit="days")
    assert plan(r + 1, "R").register == [("R_0", 0, 1), ("R_1", 1, 3)]


def test_basename_and_digits(make_series):
    a = make_series("a", *[(day, day + 1) for day in range(1, 12)])
    names = [m.name for m in plan(a * 1, "R", basename="out").maps]
    assert names[0] == "out_00"
    assert names[-1] == "out_10"


def test_spatial_series_computes_in_the_union_of_regions(make_series):
    a = make_series("a", (1, 2))
    spatial = Series(a.slots, spatial=True)
    (call,) = plan(spatial, "R").processes
    assert call.parameters["region"] == "union"


def test_series_that_is_not_spatial_sets_no_region(make_series):
    a = make_series("a", (1, 2))
    (call,) = plan(a * 1, "R").processes
    assert "region" not in call.parameters


def test_a_copy_names_its_source(make_series):
    """A planned map that copies a map unchanged names it, so materialize()
    can tell an empty copy of a map with data from an empty result"""
    a = make_series("a", (1, 2))
    retimed = Series((replace(a.slots[0], origin=None),))
    assert plan(retimed, "R").maps[0].source == "a1@PERMANENT"
    # r.mapcalc copies a slot that kept its origin as well.
    assert plan(a, "R").maps[0].source == "a1@PERMANENT"
    assert plan(a + 1, "R").maps[0].source is None
    offset = Series((Slot(a.slots[0].extent, MapRef("a1@PERMANENT", (1, 0))),))
    assert plan(offset, "R").maps[0].source is None
    selected = plan(retime(a, shift="1 day"), "R", selection=True)
    assert selected.maps[0].source == "a1@PERMANENT"
    # A selection registers a slot with an origin itself, without a copy.
    assert plan(a, "R", selection=True).maps[0].source is None


def test_skip_reduction_of_maps_writes_the_result_with_r_series(make_series):
    a = make_series("a", (1, 2), (2, 3))
    b = make_series("b", (1, 3))
    chain = plan(gather(b, contains, a, reduce="sum", nulls="skip"), "R")
    assert chain.processes == [
        ModuleCall(
            "r.series",
            {"output": "R_0", "method": "sum"},
            inputs=("a1@PERMANENT", "a2@PERMANENT"),
        )
    ]
    assert chain.remove == ()


def test_skip_reduction_of_expressions_uses_temporary_maps(make_series):
    a = make_series("a", (1, 2), (2, 3))
    b = make_series("b", (1, 3))
    reduced = gather(b, contains, a * 2, reduce="mean", nulls="skip")
    chain = plan(reduced + 1, "R")
    assert chain.processes == [
        ModuleCall(
            "r.mapcalc", {"expression": '"R_0_tmp0"=("a1@PERMANENT" * 2)', "nprocs": 1}
        ),
        ModuleCall(
            "r.mapcalc", {"expression": '"R_0_tmp1"=("a2@PERMANENT" * 2)', "nprocs": 1}
        ),
        ModuleCall(
            "r.series",
            {"output": "R_0_tmp2", "method": "average"},
            inputs=("R_0_tmp0", "R_0_tmp1"),
        ),
        ModuleCall("r.mapcalc", {"expression": '"R_0"=("R_0_tmp2" + 1)', "nprocs": 1}),
    ]
    assert chain.remove == ("R_0_tmp0", "R_0_tmp1", "R_0_tmp2")


def test_skip_reduction_of_a_map_at_an_offset_uses_a_temporary_map():
    reduced = SeriesReduce("sum", (MapRef("a1@PERMANENT", (1, 0)), A2))
    calls, temporaries = RasterBackend().plan(reduced, "R_0")
    assert [call.name for call in calls] == ["r.mapcalc", "r.series"]
    assert calls[0].parameters["expression"] == '"R_0_tmp0"="a1@PERMANENT"[1,0]'
    assert calls[1].inputs == ("R_0_tmp0", "a2@PERMANENT")
    assert temporaries == ["R_0_tmp0"]


def test_a_reduction_skipping_nulls_reads_its_maps_from_a_file(make_series):
    """The maps reach r.series in a file, as for an aggregation, because the
    kernel limits a single argument such as input=a,b,... to 131071
    characters, 131072 bytes with the terminating NUL"""
    a = make_series("a", (1, 2), (2, 3))
    b = make_series("b", (1, 3))
    (call,) = plan(gather(b, contains, a, reduce="sum", nulls="skip"), "R").processes
    assert call.inputs == ("a1@PERMANENT", "a2@PERMANENT")
    assert "input" not in call.parameters


def test_the_dry_run_of_a_reduction_skipping_nulls_is_unchanged(make_series):
    """The process chain and the debug lines of a dry run still list the maps
    as one input, as they did when the maps were passed on the command line

    The expected values were recorded before the maps went into a file.
    repr() compares them character by character, so a change of the order of
    the keys or of the inputs is seen too.
    """
    a = make_series("a", (1, 2), (2, 3))
    b = make_series("b", (1, 3))
    reduced = gather(b, contains, a * 2, reduce="mean", nulls="skip")
    calls = plan(reduced + 1, "R").processes
    described = [algebra_parser._as_process_dict(call, True) for call in calls]
    assert repr(described) == repr(
        [
            {
                "name": "r.mapcalc",
                "inputs": [
                    ("expression", '"R_0_tmp0"=("a1@PERMANENT" * 2)'),
                    ("nprocs", 1),
                ],
                "outputs": [],
                "flags": ["overwrite"],
            },
            {
                "name": "r.mapcalc",
                "inputs": [
                    ("expression", '"R_0_tmp1"=("a2@PERMANENT" * 2)'),
                    ("nprocs", 1),
                ],
                "outputs": [],
                "flags": ["overwrite"],
            },
            {
                "name": "r.series",
                "inputs": [("input", "R_0_tmp0,R_0_tmp1"), ("method", "average")],
                "outputs": [("output", "R_0_tmp2")],
                "flags": ["overwrite"],
            },
            {
                "name": "r.mapcalc",
                "inputs": [("expression", '"R_0"=("R_0_tmp2" + 1)'), ("nprocs", 1)],
                "outputs": [],
                "flags": ["overwrite"],
            },
        ]
    )
    assert [algebra_parser._command(call) for call in calls] == [
        'r.mapcalc expression="R_0_tmp0"=("a1@PERMANENT" * 2) nprocs=1',
        'r.mapcalc expression="R_0_tmp1"=("a2@PERMANENT" * 2) nprocs=1',
        "r.series input=R_0_tmp0,R_0_tmp1 output=R_0_tmp2 method=average",
        'r.mapcalc expression="R_0"=("R_0_tmp2" + 1) nprocs=1',
    ]


def test_nested_condition_stays_one_call_per_map(make_series):
    """if({during,|}, A > 1 && start_day(A) == 1, B, 0) gives one r.mapcalc
    call per map of B, however many maps of A each of them contains"""
    a = make_series("a", (1, 2), (2, 3), (3, 4), (4, 5))
    b = make_series("b", (1, 3), (3, 5))
    condition = (a > 1) & (timevar(a, "start_day") == 1)
    chain = plan(where(gather(b, contains, condition, reduce="any"), b, 0), "C")
    assert [call.name for call in chain.processes] == ["r.mapcalc", "r.mapcalc"]
    assert chain.processes[0].parameters["expression"] == (
        '"C_0"=if(((("a1@PERMANENT" > 1) && 1) || (("a2@PERMANENT" > 1) && 0)), '
        '"b1@PERMANENT", 0)'
    )


def test_a_dot_is_rejected_in_the_name_but_not_in_the_basename(make_series):
    a = make_series("a", (1, 2))
    assert [m.name for m in plan(a * 1, "R", basename="a.b").maps] == ["a.b_0"]
    with pytest.raises(ValueError, match=r"name must not contain '\.'"):
        plan(a * 1, "a.b")


def test_time_suffix(make_series):
    a = make_series("a", (1, 2), (2, 3))
    assert [m.name for m in plan(a * 1, "R", time_suffix="gran").maps] == [
        "R_2001_01_01",
        "R_2001_01_02",
    ]
    assert [m.name for m in plan(a * 1, "R", time_suffix="time").maps] == [
        "R_2001_01_01T00_00_00",
        "R_2001_01_02T00_00_00",
    ]


@pytest.mark.parametrize("time_suffix", ["gran", "time"])
def test_colliding_map_names_are_rejected(make_series, time_suffix):
    x = make_series("x", (1, 2), (1, 2))
    with pytest.raises(ValueError, match="same name"):
        plan(x * 1, "R", time_suffix=time_suffix)


def test_maps_of_equal_time_get_distinct_numeric_names(make_series):
    x = make_series("x", (1, 2), (1, 2))
    assert [m.name for m in plan(x * 1, "R").maps] == ["R_0", "R_1"]


def test_relative_time_has_numeric_suffixes(make_series):
    r = make_series("r", (0, 1), unit="days")
    chain = plan(r * 1, "R", time_suffix="gran")
    assert [m.name for m in chain.maps] == ["R_0"]
    assert chain.temporal_type == "relative"


def test_map_without_time_stamp_cannot_be_planned():
    with pytest.raises(ValueError, match="without time stamp"):
        plan(Series((Slot(None, A1),)), "R")


@pytest.mark.parametrize("time_suffix", [None, "gran", "time"])
def test_empty_series_plans_an_empty_dataset(time_suffix):
    chain = plan(Series(), "R", time_suffix=time_suffix)
    assert chain.maps == ()
    assert chain.processes == []
    assert chain.register == []
    assert chain.temporal_type == "absolute"


def test_unknown_time_suffix(make_series):
    with pytest.raises(ValueError, match="time_suffix"):
        plan(make_series("a", (1, 2)), "R", time_suffix="date")


def test_reduction_node_inside_expression_is_not_rendered_directly():
    with pytest.raises(ValueError, match=r"r\.series"):
        RasterBackend().expression(SeriesReduce("sum", (A1, A2)))


def test_map_name_with_a_quote_is_rejected():
    with pytest.raises(ValueError, match="quote"):
        RasterBackend().expression(MapRef('a"b@PERMANENT'))


def test_3d_series_aggregate_names_r_series_and_the_method():
    node = SeriesAggregate("median", (A1, A2))
    with pytest.raises(ValueError, match=r"r\.series aggregation median") as error:
        Raster3DBackend().plan(node, "out")
    assert "sum or mean" not in str(error.value)


def test_3d_series_reduce_keeps_its_message():
    with pytest.raises(ValueError, match="sum or mean"):
        Raster3DBackend().plan(SeriesReduce("sum", (A1, A2)), "out")
