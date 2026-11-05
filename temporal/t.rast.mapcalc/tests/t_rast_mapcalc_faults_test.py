"""Test the refusals, the method start and the expression of t.rast.mapcalc

A sampler that cannot sample ends the run with an error. The method start
selects a map of the same time as the granule. A dataset name in the
expression is replaced only where it stands as a whole name, and not where
it is followed by "(", also after the label operator "@" and the grey
operator "#" of r.mapcalc. Two inputs of the same name are refused, and the
expression reaches r.mapcalc with its blanks. An input that only an older
dataset with a dot in its name matches ends the run with an error message.
"""

from datetime import datetime
from io import StringIO

import pytest

import grass.temporal as tgis
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.temporal.testing.session import (
    mapset_session,
    project_session,
    temporal_session,
)
from grass.tools import ToolError, Tools

D = datetime


def values(tools, name):
    """(name, start, end, min) of the maps of a result dataset"""
    return [
        (row.name, row.start, row.end, row.min)
        for row in list_maps(tools, "strds", name)
    ]


def refused(tools, **options):
    """The message of a refused run, after checking that it left nothing"""
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_rast_mapcalc(**options)
    assert inventory(tools) == before
    return message(error.value)


def test_sampler_of_instants_fails(tools, prefix):
    """A sampler of time instants has no granules: an error, not a message"""
    create_stds(
        tools,
        "strds",
        f"{prefix}_s",
        [MapSpec(f"{prefix}_s{k}", k, D(2026, 1, k)) for k in (1, 2)],
    )
    create_stds(
        tools,
        "strds",
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


def test_sampler_of_another_temporal_type_fails(tools, prefix):
    """A partner of relative time cannot be sampled by absolute time"""
    create_stds(
        tools,
        "strds",
        f"{prefix}_s",
        [MapSpec(f"{prefix}_s1", 1, D(2026, 1, 1), D(2026, 1, 2))],
    )
    create_stds(
        tools,
        "strds",
        f"{prefix}_p",
        [MapSpec(f"{prefix}_p1", 2, 0, 1)],
        temporaltype="relative",
        unit="days",
    )
    text = refused(
        tools,
        inputs=f"{prefix}_s,{prefix}_p",
        expression=f"{prefix}_s + {prefix}_p",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
    )
    assert "The space time datasets must be of the same temporal type" in text
    assert text.count("ERROR") == 1
    assert "No samples found" not in text


def test_method_start_keeps_equal_maps(tools, prefix):
    """The partner map with the time of the granule is taken: 1 + 10"""
    create_stds(
        tools,
        "strds",
        f"{prefix}_s",
        [MapSpec(f"{prefix}_s1", 1, D(2026, 1, 1), D(2026, 1, 3))],
    )
    create_stds(
        tools,
        "strds",
        f"{prefix}_p",
        [MapSpec(f"{prefix}_p1", 10, D(2026, 1, 1), D(2026, 1, 3))],
    )
    tools.t_rast_mapcalc(
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
    """The dataset day stays in start_day(): 3 * 5 on 5 January"""
    create_stds(
        tools, "strds", "day", [MapSpec("day_map", 3, D(2026, 1, 5), D(2026, 1, 6))]
    )
    tools.t_rast_mapcalc(
        inputs="day",
        expression="day * start_day()",
        output="day_out",
        basename="day_out",
    )
    assert values(tools, "day_out") == [
        ("day_out_1", "2026-01-05 00:00:00", "2026-01-06 00:00:00", 15.0)
    ]


def test_dataset_name_prefix_of_other(tools):
    """soil is the start of soil_deep: 1 + 10, in both orders of inputs"""
    create_stds(
        tools, "strds", "soil", [MapSpec("soil_map", 1, D(2026, 1, 5), D(2026, 1, 6))]
    )
    create_stds(
        tools,
        "strds",
        "soil_deep",
        [MapSpec("soil_deep_map", 10, D(2026, 1, 5), D(2026, 1, 6))],
    )
    for inputs in ("soil,soil_deep", "soil_deep,soil"):
        tools.t_rast_mapcalc(
            inputs=inputs,
            expression="soil + soil_deep",
            output="soil_out",
            basename="soil_out",
            overwrite=True,
        )
        assert values(tools, "soil_out") == [
            ("soil_out_1", "2026-01-05 00:00:00", "2026-01-06 00:00:00", 11.0)
        ]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        # The label 7.5 of the category 2
        ("@{ds} + 0", 7.5),
        ("{ds} + @{ds}", 9.5),
        ("(@{ds})", 7.5),
        # The grey value of the colour 100:100:100
        ("#{ds} * 1", 100.0),
    ],
)
def test_dataset_name_after_label_or_grey_operator(tools, prefix, expression, expected):
    """A dataset name after "@" or "#" is replaced by the map of the granule

    The map has the value 2, the label 7.5 and the colour 100:100:100. Only
    an "@" after a name character is the mapset of a map name.
    """
    name = f"{prefix}_lab"
    create_stds(
        tools, "strds", name, [MapSpec(f"{name}1", 2, D(2026, 1, 5), D(2026, 1, 6))]
    )
    tools.r_category(map=f"{name}1", rules=StringIO("2:7.5\n"), separator=":")
    tools.r_colors(map=f"{name}1", rules=StringIO("2 100:100:100\n"))
    tools.t_rast_mapcalc(
        inputs=name,
        expression=expression.format(ds=name),
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
    )
    assert [row[3] for row in values(tools, f"{prefix}_out")] == [expected]


def test_dataset_name_after_a_map_name_is_a_mapset(tmp_path):
    """In "elevation@soil" the name soil is the mapset and stays: 10 + 1"""
    with project_session(tmp_path / "project") as work:
        with mapset_session(work, "soil") as other:
            other_tools = Tools(session=other, consistent_return_value=True)
            other_tools.g_region(n=1, s=0, e=1, w=0, res=1)
            other_tools.r_mapcalc(expression="elevation = 10")
        tools = Tools(session=work, consistent_return_value=True)
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_stds(
            tools, "strds", "soil", [MapSpec("soil1", 1, D(2026, 1, 5), D(2026, 1, 6))]
        )
        tools.t_rast_mapcalc(
            inputs="soil",
            expression="elevation@soil + soil",
            output="sum",
            basename="sum",
        )
        assert values(tools, "sum") == [
            ("sum_1", "2026-01-05 00:00:00", "2026-01-06 00:00:00", 11.0)
        ]


def test_dataset_name_before_parenthesis_is_a_function(tools):
    """The dataset td stays in td(): the map 4 times the length of 2 days"""
    create_stds(
        tools, "strds", "td", [MapSpec("td_map", 4, D(2026, 1, 5), D(2026, 1, 7))]
    )
    tools.t_rast_mapcalc(
        inputs="td",
        expression="td * td ( )",
        output="td_out",
        basename="td_out",
    )
    assert values(tools, "td_out") == [
        ("td_out_1", "2026-01-05 00:00:00", "2026-01-07 00:00:00", 8.0)
    ]


@pytest.mark.parametrize("second", ["{name}", "{name}@PERMANENT"])
def test_duplicate_input_is_refused(tools, prefix, second):
    """Two inputs of one name cannot be told apart in the expression"""
    create_stds(
        tools,
        "strds",
        f"{prefix}_x",
        [MapSpec(f"{prefix}_x1", 1, D(2026, 1, 5), D(2026, 1, 6))],
    )
    name = f"{prefix}_x"
    text = refused(
        tools,
        inputs=f"{name},{second.format(name=name)}",
        expression=f"{name} + 1",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
    )
    assert (
        f"The name <{name}> stands more than once in inputs, so the expression "
        "cannot tell the inputs apart"
    ) in text


def test_expression_keeps_spaces(tools):
    """r.mapcalc gets the expression with its blanks

    The names are short, so that the verbose message is not wrapped; the
    messages print a run of blanks as one, so the expression has single
    blanks.
    """
    create_stds(tools, "strds", "sp", [MapSpec("sp1", 1, D(2026, 1, 5), D(2026, 1, 6))])
    result = tools.t_rast_mapcalc(
        inputs="sp",
        expression="sp + start_day ()",
        output="sp_out",
        basename="sp_out",
        verbose=True,
    )
    assert 'Apply mapcalc expression: "sp_out_1=sp1 + 5"' in result.stderr
    assert values(tools, "sp_out")[0][3] == 6.0


def test_old_dataset_with_dot_ends_with_an_error_message(tmp_path):
    """Only the dataset a.b of an older release, no dataset a: no traceback

    The dataset is made with the dataset class, as the older release did.
    """
    with temporal_session(tmp_path / "project") as session:
        tools = Tools(
            session=session,
            consistent_return_value=True,
            capture_stderr=True,
            errors="ignore",
        )
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        for name, value in (("m1", 1), ("m2", 2)):
            tools.r_mapcalc(expression=f"{name} = {value}")
        dataset = tgis.dataset_factory("strds", f"a.b@{tgis.get_current_mapset()}")
        dataset.set_initial_values("absolute", "mean", "t", "d")
        dataset.insert()
        tools.t_register(
            input="a.b", maps="m1,m2", start="2001-01-01", increment="1 day"
        )

        result = tools.t_rast_mapcalc(
            inputs="a.b", expression="a.b + 1", output="calc", basename="calc"
        )

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "ERROR: Space time raster dataset <a.b@" in result.stderr
