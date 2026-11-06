"""Test the refusals, the method start and the expression of t.rast.mapcalc

A sampler that cannot sample ends the run with an error. The method start
selects a map of the same time as the granule. A dataset name in the
expression is replaced only where it stands as a whole name, and not where
it is followed by "(", also after the label operator "@" and the grey
operator "#" of r.mapcalc. Two inputs of the same name are refused, and the
expression reaches r.mapcalc with its blanks. An older dataset with a dot in
its name is read as an input; a dotted name that names no dataset ends the
run with an error message. A where condition that selects no map of the
sampler or of the only dataset gives a warning that names it, a dataset
without maps a warning with its own text; neither makes an output dataset.
"""

from datetime import datetime
from io import StringIO

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, insert_old_stds
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


def old_dotted_dataset_tools(session):
    """Tools of session with the dataset a.b of an older release, no dataset a

    The dataset is made with the dataset class, as the older release did, and
    holds the maps m1 and m2 with the values 1 and 2.
    """
    tools = Tools(
        session=session,
        consistent_return_value=True,
        capture_stderr=True,
        errors="ignore",
    )
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    for name, value in (("m1", 1), ("m2", 2)):
        tools.r_mapcalc(expression=f"{name} = {value}")
    insert_old_stds("a.b")
    tools.t_register(input="a.b", maps="m1,m2", start="2001-01-01", increment="1 day")
    return tools


def test_old_dataset_with_dot_ends_with_an_error_message(tmp_path):
    """A dotted name that names no dataset, next to a.b of an older release

    a.c is neither a dataset nor the dataset a with the label c: the run
    ends with an error message, not a traceback. The dataset a.b itself is
    read (test_dotted_input_is_read).
    """
    with temporal_session(tmp_path / "project") as session:
        tools = old_dotted_dataset_tools(session)

        result = tools.t_rast_mapcalc(
            inputs="a.c", expression="a.c + 1", output="calc", basename="calc"
        )

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "ERROR: Space time dataset <a> of type <strds> not found" in result.stderr


def test_dotted_input_is_read(tmp_path):
    """Only the dataset a.b of an older release, no dataset a: 1 + 1, 2 + 1"""
    with temporal_session(tmp_path / "project") as session:
        tools = old_dotted_dataset_tools(session)

        result = tools.t_rast_mapcalc(
            inputs="a.b", expression="a.b + 1", output="calc", basename="calc"
        )

        assert result.returncode == 0, result.stderr
        assert [row.min for row in list_maps(tools, "strds", "calc")] == [2.0, 3.0]


def make_where_datasets(tools, prefix):
    """The datasets <prefix>_s and <prefix>_p, each of two daily intervals in
    January 2026, and the dataset <prefix>_e without maps"""
    for name, value in (("s", 1), ("p", 10)):
        create_stds(
            tools,
            "strds",
            f"{prefix}_{name}",
            [
                MapSpec(
                    f"{prefix}_{name}{day}", value, D(2026, 1, day), D(2026, 1, day + 1)
                )
                for day in (1, 2)
            ],
        )
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output=f"{prefix}_e",
        title="t",
        description="t",
    )


@pytest.mark.parametrize("inputs", ["{}_s,{}_p", "{}_s"], ids=["sampler", "single"])
def test_where_selects_nothing_warns(tools, prefix, inputs):
    """The warning names the where condition and the dataset it emptied"""
    make_where_datasets(tools, prefix)
    names = inputs.format(prefix, prefix)
    before = inventory(tools)
    result = tools.t_rast_mapcalc(
        inputs=names,
        expression=" + ".join(names.split(",")),
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        where="start_time >= '2027-01-01'",
    )
    assert result.returncode == 0
    assert (
        "WARNING: The where condition selects no map of space time raster "
        f"dataset <{prefix}_s@PERMANENT>"
    ) in message(result)
    assert inventory(tools) == before


def test_empty_dataset_without_where_warns(tools, prefix):
    make_where_datasets(tools, prefix)
    before = inventory(tools)
    result = tools.t_rast_mapcalc(
        inputs=f"{prefix}_e",
        expression=f"{prefix}_e + 1",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
    )
    assert result.returncode == 0
    assert f"WARNING: No maps registered in input dataset <{prefix}_e>" in message(
        result
    )
    assert "where condition" not in message(result)
    assert inventory(tools) == before


def test_empty_dataset_with_where_names_the_where_condition(tools, prefix):
    """With where, a dataset without maps gets the warning about the where
    condition, as in t.rast.series"""
    make_where_datasets(tools, prefix)
    before = inventory(tools)
    result = tools.t_rast_mapcalc(
        inputs=f"{prefix}_e",
        expression=f"{prefix}_e + 1",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        where="start_time >= '2026-01-01'",
    )
    assert result.returncode == 0
    assert (
        "WARNING: The where condition selects no map of space time raster "
        f"dataset <{prefix}_e@PERMANENT>"
    ) in message(result)
    assert "No maps registered" not in message(result)
    assert inventory(tools) == before


@pytest.mark.parametrize("inputs", ["{}_s,{}_p", "{}_s"], ids=["sampler", "single"])
def test_where_with_maps_gives_no_warning(tools, prefix, inputs):
    make_where_datasets(tools, prefix)
    names = inputs.format(prefix, prefix)
    result = tools.t_rast_mapcalc(
        inputs=names,
        expression=" + ".join(names.split(",")),
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        where="start_time >= '2026-01-02'",
    )
    assert "WARNING" not in result.stderr
    assert [row.min for row in list_maps(tools, "strds", f"{prefix}_out")] == [
        11.0 if "," in names else 1.0
    ]


@pytest.mark.parametrize("where", [None, "start_time < '2026-01-02'"])
def test_label_without_maps_warns(tools, prefix, where):
    """Two labels of one dataset are not sampled; the second one gives no map

    The map with the label B4 is on 1 January, the one with B8 on 2 January,
    so the where condition leaves a map of B4 only. Without it, the label B9
    selects no map.
    """
    create_stds(
        tools,
        "strds",
        f"{prefix}_x",
        [
            MapSpec(f"{prefix}_b4", 1, D(2026, 1, 1), D(2026, 1, 2), "B4"),
            MapSpec(f"{prefix}_b8", 2, D(2026, 1, 2), D(2026, 1, 3), "B8"),
        ],
    )
    second = "B8" if where else "B9"
    before = inventory(tools)
    result = tools.t_rast_mapcalc(
        inputs=f"{prefix}_x.B4,{prefix}_x.{second}",
        expression=f"{prefix}_x.B4 + {prefix}_x.{second}",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        **({"where": where} if where else {}),
    )
    assert result.returncode == 0
    if where:
        expected = (
            "WARNING: The where condition selects no map of space time raster "
            f"dataset <{prefix}_x.B8@PERMANENT>"
        )
    else:
        expected = f"WARNING: No maps registered in input dataset <{prefix}_x.B9>"
    assert expected in message(result)
    assert inventory(tools) == before


def test_label_without_maps_as_sampler_warns(tools, prefix):
    """A label without maps samples another dataset; nothing is computed

    No where condition is given, so the tool warns that no sample was found,
    makes no dataset and ends with status 0.
    """
    create_stds(
        tools,
        "strds",
        f"{prefix}_x",
        [MapSpec(f"{prefix}_b4", 1, D(2026, 1, 1), D(2026, 1, 2), "B4")],
    )
    create_stds(
        tools,
        "strds",
        f"{prefix}_p",
        [MapSpec(f"{prefix}_p1", 2, D(2026, 1, 1), D(2026, 1, 2))],
    )
    before = inventory(tools)
    result = tools.t_rast_mapcalc(
        inputs=f"{prefix}_x.B9,{prefix}_p",
        expression=f"{prefix}_x.B9 + {prefix}_p",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
    )
    assert result.returncode == 0
    assert "WARNING: No samples found for map calculation" in message(result)
    assert inventory(tools) == before


def test_empty_sampler_warns(tools, prefix):
    """A sampler without maps has no granules: a warning, not a refusal

    It has no map time either, so the check for interval time must not
    fire. Nothing is computed and no dataset is made.
    """
    make_where_datasets(tools, prefix)
    before = inventory(tools)
    result = tools.t_rast_mapcalc(
        inputs=f"{prefix}_e,{prefix}_p",
        expression=f"{prefix}_e + {prefix}_p",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
    )
    assert result.returncode == 0
    assert "WARNING: No samples found for map calculation" in message(result)
    assert "must be interval" not in message(result)
    assert inventory(tools) == before


def test_empty_sampler_of_other_temporal_type_is_refused(tools, prefix):
    """The refusal for another temporal type holds without maps in the sampler"""
    make_where_datasets(tools, prefix)
    create_stds(
        tools,
        "strds",
        f"{prefix}_r",
        [MapSpec(f"{prefix}_r1", 2, 0, 1)],
        temporaltype="relative",
        unit="days",
    )
    text = refused(
        tools,
        inputs=f"{prefix}_e,{prefix}_r",
        expression=f"{prefix}_e + {prefix}_r",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
    )
    assert "The space time datasets must be of the same temporal type" in text
    assert "No samples found" not in text


def test_where_emptied_sampler_of_instants_is_still_refused(tools, prefix):
    """A sampler of time instants that where empties keeps its map type

    The interval check is dropped only for a sampler without registered
    maps; this one has maps, so the refusal stays.
    """
    make_where_datasets(tools, prefix)
    create_stds(
        tools,
        "strds",
        f"{prefix}_i",
        [MapSpec(f"{prefix}_i{k}", k, D(2026, 1, k)) for k in (1, 2)],
    )
    text = refused(
        tools,
        inputs=f"{prefix}_i,{prefix}_p",
        expression=f"{prefix}_i + {prefix}_p",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        where="start_time >= '2027-01-01'",
    )
    assert "The temporal map type of the sample dataset must be interval" in text
    assert "No samples found" not in text
