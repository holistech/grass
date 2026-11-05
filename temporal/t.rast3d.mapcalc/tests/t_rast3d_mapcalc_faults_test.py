"""Test the refusals, the method start and the expression of t.rast3d.mapcalc

The tool shares its code with t.rast.mapcalc: a sampler that cannot sample
ends the run with an error, the method start selects a map of the same time
as the granule, a dataset name in the expression is replaced only where it
stands as a whole name and not before "(", also after the label operator
"@" and the grey operator "#", two inputs of the same name are refused, and
the expression reaches r3.mapcalc with its blanks.
"""

from datetime import datetime
from io import StringIO

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.tools import ToolError

D = datetime


def values(tools, name):
    """(name, start, end, min) of the maps of a result dataset"""
    return [
        (row.name, row.start, row.end, row.min)
        for row in list_maps(tools, "str3ds", name)
    ]


def refused(tools, **options):
    """The message of a refused run, after checking that it left nothing"""
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_rast3d_mapcalc(**options)
    assert inventory(tools) == before
    return message(error.value)


def test_sampler_of_instants_fails(tools, prefix):
    """A sampler of time instants has no granules: an error, not a message"""
    create_stds(
        tools,
        "str3ds",
        f"{prefix}_s",
        [MapSpec(f"{prefix}_s{k}", k, D(2026, 1, k)) for k in (1, 2)],
    )
    create_stds(
        tools,
        "str3ds",
        f"{prefix}_p",
        [MapSpec(f"{prefix}_p1", 3, D(2026, 1, 1), D(2026, 1, 2))],
    )
    text = refused(
        tools,
        inputs=f"{prefix}_s,{prefix}_p",
        expression=f"{prefix}_s + {prefix}_p",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
    )
    assert "The temporal map type of the sample dataset must be interval" in text
    assert text.count("ERROR") == 1
    assert "No samples found" not in text


def test_method_start_keeps_equal_maps(tools, prefix):
    """The partner map with the time of the granule is taken: 1 + 10"""
    for name, value in (("s", 1), ("p", 10)):
        create_stds(
            tools,
            "str3ds",
            f"{prefix}_{name}",
            [MapSpec(f"{prefix}_{name}1", value, D(2026, 1, 1), D(2026, 1, 3))],
        )
    tools.t_rast3d_mapcalc(
        inputs=f"{prefix}_s,{prefix}_p",
        expression=f"{prefix}_s + {prefix}_p",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        method="start",
    )
    assert values(tools, f"{prefix}_out") == [
        (f"{prefix}_out_1", "2026-01-01 00:00:00", "2026-01-03 00:00:00", 11.0)
    ]


def test_dataset_name_inside_function_name(tools):
    """The dataset h stays in start_month(): 3 * 1 in January"""
    create_stds(
        tools, "str3ds", "h", [MapSpec("h_map", 3, D(2026, 1, 5), D(2026, 1, 6))]
    )
    tools.t_rast3d_mapcalc(
        inputs="h", expression="h * start_month()", output="h_out", basename="h_out"
    )
    assert values(tools, "h_out") == [
        ("h_out_1", "2026-01-05 00:00:00", "2026-01-06 00:00:00", 3.0)
    ]


def test_dataset_name_prefix_of_other(tools):
    """a is the start of ab: 1 + 10, in both orders of inputs"""
    create_stds(
        tools, "str3ds", "a", [MapSpec("a_map", 1, D(2026, 1, 5), D(2026, 1, 6))]
    )
    create_stds(
        tools, "str3ds", "ab", [MapSpec("ab_map", 10, D(2026, 1, 5), D(2026, 1, 6))]
    )
    for inputs in ("a,ab", "ab,a"):
        tools.t_rast3d_mapcalc(
            inputs=inputs,
            expression="a + ab",
            output="a_out",
            basename="a_out",
            overwrite=True,
        )
        assert values(tools, "a_out") == [
            ("a_out_1", "2026-01-05 00:00:00", "2026-01-06 00:00:00", 11.0)
        ]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        # The name after "@" is replaced by the map of the granule; both
        # branches give its value 2.
        ("if(isnull(@{ds}), {ds}, {ds})", 2.0),
        # The label 7.5 of the category 2, copied with r3.support
        ("@{ds}", 7.5),
        # The grey value of the colour 100:100:100
        ("#{ds} * 1", 100.0),
    ],
)
def test_dataset_name_after_label_or_grey_operator(tools, prefix, expression, expected):
    """A dataset name after "@" or "#" is replaced by the map of the granule"""
    name = f"{prefix}_lab"
    create_stds(
        tools, "str3ds", name, [MapSpec(f"{name}1", 2, D(2026, 1, 5), D(2026, 1, 6))]
    )
    tools.r_mapcalc(expression=f"{name}_labels = 2")
    tools.r_category(map=f"{name}_labels", rules=StringIO("2:7.5\n"), separator=":")
    tools.r3_support(map=f"{name}1", raster=f"{name}_labels")
    tools.r3_colors(map=f"{name}1", rules=StringIO("2 100:100:100\n"))
    tools.t_rast3d_mapcalc(
        inputs=name,
        expression=expression.format(ds=name),
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
    )
    assert [row[3] for row in values(tools, f"{prefix}_out")] == [expected]


def test_duplicate_input_is_refused(tools, prefix):
    """Two inputs of one name cannot be told apart in the expression"""
    name = f"{prefix}_x"
    create_stds(
        tools,
        "str3ds",
        name,
        [MapSpec(f"{prefix}_x1", 1, D(2026, 1, 5), D(2026, 1, 6))],
    )
    text = refused(
        tools,
        inputs=f"{name},{name}",
        expression=f"{name} + 1",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
    )
    assert (
        f"The name <{name}> stands more than once in inputs, so the expression "
        "cannot tell the inputs apart"
    ) in text


def test_expression_keeps_spaces(tools):
    """r3.mapcalc gets the expression with its blanks

    The names are short, so that the verbose message is not wrapped; the
    messages print a run of blanks as one, so the expression has single
    blanks.
    """
    create_stds(
        tools, "str3ds", "sp", [MapSpec("sp1", 1, D(2026, 1, 5), D(2026, 1, 6))]
    )
    result = tools.t_rast3d_mapcalc(
        inputs="sp",
        expression="sp + start_day ()",
        output="sp_out",
        basename="sp_out",
        verbose=True,
    )
    assert 'Apply mapcalc expression: "sp_out_1=sp1 + 5"' in result.stderr
    assert values(tools, "sp_out")[0][3] == 6.0
