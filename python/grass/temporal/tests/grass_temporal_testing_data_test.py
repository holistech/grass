"""Tests for the data helpers of grass.temporal.testing.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from grass.exceptions import CalledModuleError

from grass.temporal.testing.data import (
    DAY0,
    MapSpec,
    create_stds,
    day,
    intervals,
    make_map,
    register_file,
    register_stds,
    relative_intervals,
    small_region,
    timestamp,
    vector_points,
)
from grass.temporal.testing.readback import list_maps
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools

MAP_KIND = {"strds": "raster", "str3ds": "raster_3d", "stvds": "vector"}


def test_day_and_timestamp():
    assert day(0) == DAY0 == datetime(2001, 1, 1)
    assert day(1, hours=6) == datetime(2001, 1, 2, 6)
    assert timestamp(31) == "2001-02-01"


def test_intervals_by_month():
    assert intervals(3) == [
        (datetime(2001, 1, 1), datetime(2001, 2, 1)),
        (datetime(2001, 2, 1), datetime(2001, 3, 1)),
        (datetime(2001, 3, 1), datetime(2001, 4, 1)),
    ]


def test_intervals_by_month_cross_a_year_end():
    assert intervals(2, start=11) == [
        (datetime(2001, 12, 1), datetime(2002, 1, 1)),
        (datetime(2002, 1, 1), datetime(2002, 2, 1)),
    ]


def test_intervals_by_day_from_start():
    assert intervals(2, granularity="day", start=5) == [
        (datetime(2001, 1, 6), datetime(2001, 1, 7)),
        (datetime(2001, 1, 7), datetime(2001, 1, 8)),
    ]


def test_intervals_rejects_unknown_granularity():
    with pytest.raises(ValueError, match="year"):
        intervals(1, granularity="year")


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    with temporal_session(tmp_path_factory.mktemp("data") / "project") as session:
        yield Tools(session=session)


def _specs(stds_type, case):
    """Three maps for case "interval", "point" or "relative"."""
    names = [f"{stds_type}_{case}_{number}" for number in (1, 2, 3)]
    if case == "interval":
        times = [(start, end) for start, end in intervals(3)]
    elif case == "point":
        times = [(day(number), None) for number in (0, 10, 20)]
    else:
        times = [(0, 1), (1, 3), (3, 6)]
    return [
        MapSpec(name, number, start, end)
        for number, (name, (start, end)) in enumerate(
            zip(names, times, strict=True), start=1
        )
    ]


def _expected(specs, case):
    """Times as the list tools print them: text for absolute, numbers for relative"""
    if case == "relative":
        return [(spec.name, spec.start, spec.end) for spec in specs]
    fmt = "%Y-%m-%d %H:%M:%S"
    return [
        (
            spec.name,
            spec.start.strftime(fmt),
            None if spec.end is None else spec.end.strftime(fmt),
        )
        for spec in specs
    ]


@pytest.mark.needs_solo_run
@pytest.mark.parametrize("via", ["tool", "library"])
@pytest.mark.parametrize("case", ["interval", "point", "relative"])
@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_create_stds_registers_the_given_times(tools, stds_type, case, via):
    specs = [
        MapSpec(f"{via}_{spec.name}", spec.value, spec.start, spec.end)
        for spec in _specs(stds_type, case)
    ]
    options = {"temporaltype": "relative", "unit": "days"} if case == "relative" else {}
    create_stds(
        tools, stds_type, f"{via}_{stds_type}_{case}", specs, via=via, **options
    )

    rows = list_maps(tools, stds_type, f"{via}_{stds_type}_{case}")

    assert [(row.name, row.start, row.end) for row in rows] == _expected(specs, case)


@pytest.mark.needs_solo_run
@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_both_routes_give_the_same_rows(tools, stds_type):
    results = []
    for via in ("tool", "library"):
        specs = [
            MapSpec(
                f"same_{stds_type}_{via}{spec.name[-1]}",
                spec.value,
                spec.start,
                spec.end,
            )
            for spec in _specs(stds_type, "interval")
        ]
        create_stds(tools, stds_type, f"same_{stds_type}_{via}", specs, via=via)
        rows = list_maps(tools, stds_type, f"same_{stds_type}_{via}")
        # The map names differ by route; times and values must not.
        results.append([row._replace(name=row.name[-1]) for row in rows])
    assert results[0] == results[1]


def test_make_map_values(tools):
    make_map(tools, "raster", "mm_r", 7)
    make_map(tools, "raster_3d", "mm_r3", 8)
    make_map(tools, "vector", "mm_v", 9)

    assert tools.r_univar(map="mm_r", format="json").json["max"] == 7
    assert tools.r3_univar(map="mm_r3", format="json").json["max"] == 8
    rows = tools.v_db_select(map="mm_v", format="json").json["records"]
    assert [(row["x"], row["y"], row["value"]) for row in rows] == [(9, 9, 9)]


def test_semantic_label_is_set(tools):
    specs = [
        MapSpec("sl_1", 1, day(0), day(1), semantic_label="S2_1"),
        MapSpec("sl_2", 2, day(1), day(2), semantic_label="S2_2"),
    ]
    create_stds(tools, "strds", "sl", specs)

    result = tools.t_rast_list(input="sl", columns="name,semantic_label", format="json")

    assert [(r["name"], r["semantic_label"]) for r in result.json["data"]] == [
        ("sl_1", "S2_1"),
        ("sl_2", "S2_2"),
    ]


def test_semantic_label_on_a_vector_dataset_is_an_error(tools):
    specs = [MapSpec("slv_1", 1, day(0), day(1), semantic_label="x")]
    with pytest.raises(ValueError, match="semantic label"):
        create_stds(tools, "stvds", "slv", specs)


def test_make_map_region_is_used_for_the_map_only(tools):
    def region():
        return tools.g_region(flags="g3").keyval

    tools.g_region(n=10, s=0, e=10, w=0, t=4, b=0, res=1, res3=1)
    before = region()

    make_map(tools, "raster", "rg_small", 1, region={"n": 2, "s": 0, "e": 2, "w": 0})

    assert region() == before
    assert tools.r_info(map="rg_small", flags="g").keyval["rows"] == 2


def test_make_map_restores_the_3d_resolution(tools):
    def region():
        return tools.g_region(flags="g3").keyval

    tools.g_region(n=10, s=0, e=10, w=0, t=4, b=0, res=1, res3=1)
    before = region()

    make_map(tools, "raster_3d", "rg_coarse", 1, region={"res3": 5, "tbres": 2})

    assert region() == before


@pytest.mark.needs_solo_run
@pytest.mark.parametrize("via", ["tool", "library"])
def test_registering_twice_with_overwrite(tools, via):
    specs = [MapSpec(f"ow_{via}_1", 1, day(0), day(1))]
    create_stds(tools, "strds", f"ow_{via}", specs, via=via)

    create_stds(tools, "strds", f"ow_{via}", specs, via=via, overwrite=True)

    assert [row.name for row in list_maps(tools, "strds", f"ow_{via}")] == [
        f"ow_{via}_1"
    ]


@pytest.mark.needs_solo_run
@pytest.mark.parametrize("via", ["tool", "library"])
def test_description_defaults_to_title_and_can_be_set(tools, via):
    create_stds(
        tools,
        "strds",
        f"desc_{via}_default",
        [MapSpec(f"desc_{via}_1", 1, day(0), day(1))],
        via=via,
        title="A title",
    )
    create_stds(
        tools,
        "strds",
        f"desc_{via}_given",
        [MapSpec(f"desc_{via}_2", 1, day(0), day(1))],
        via=via,
        title="A title",
        description="Another text",
    )

    default = _field(tools, f"desc_{via}_default", "Description:")
    given = _field(tools, f"desc_{via}_given", "Description:")

    assert default == "A title"
    assert given == "Another text"
    assert _field(tools, f"desc_{via}_given", "Title:") == "A title"


def _field(tools, name, label):
    """The line that t.info prints below the heading label of a strds"""
    lines = [
        line.strip(" |")
        for line in tools.t_info(type="strds", input=name).text.splitlines()
    ]
    return lines[lines.index(label) + 1]


def test_relative_intervals_default():
    assert relative_intervals(3) == [(0, 1), (1, 2), (2, 3)]


def test_relative_intervals_with_step_and_start():
    assert relative_intervals(2, step=5, start=10) == [(10, 15), (15, 20)]


def test_register_file_writes_one_line_per_row(tmp_path):
    rows = [
        "only_a_name",
        ("point", day(1, hours=6)),
        ("interval", day(2), day(3)),
        ("relative", 4, 6.5),
    ]

    path = register_file(tmp_path / "maps.txt", rows)

    assert path == tmp_path / "maps.txt"
    assert path.read_text().splitlines() == [
        "only_a_name",
        "point|2001-01-02 06:00:00",
        "interval|2001-01-03 00:00:00|2001-01-04 00:00:00",
        "relative|4|6.5",
    ]


def test_register_file_separator(tmp_path):
    path = register_file(tmp_path / "m.txt", [("a", 1, 2)], separator=",")

    assert path.read_text() == "a,1,2\n"


def test_register_file_refuses_a_missing_field(tmp_path):
    with pytest.raises(ValueError, match="None"):
        register_file(tmp_path / "m.txt", [("a", day(0), None)])


def test_register_file_is_read_by_t_register(tools):
    for number in (1, 2):
        make_map(tools, "raster", f"rf_m{number}", number)
    tools.t_create(type="strds", output="rf", title="rf", description="rf")
    with TemporaryDirectory() as directory:
        path = register_file(
            Path(directory) / "maps.txt",
            [("rf_m1", day(0), day(1)), ("rf_m2", day(1), day(2))],
        )
        tools.t_register(type="raster", input="rf", file=path)

    rows = list_maps(tools, "strds", "rf")

    assert [(row.name, row.start, row.end) for row in rows] == [
        ("rf_m1", "2001-01-01 00:00:00", "2001-01-02 00:00:00"),
        ("rf_m2", "2001-01-02 00:00:00", "2001-01-03 00:00:00"),
    ]


def test_register_file_names_only_take_their_times_from_t_register(tools):
    for number in (1, 2):
        make_map(tools, "raster", f"rn_m{number}", number)
    tools.t_create(type="strds", output="rn", title="rn", description="rn")
    with TemporaryDirectory() as directory:
        path = register_file(Path(directory) / "maps.txt", ["rn_m1", "rn_m2"])
        tools.t_register(
            type="raster", input="rn", file=path, start="2001-03-01", increment="1 days"
        )

    rows = list_maps(tools, "strds", "rn")

    assert [(row.name, row.start) for row in rows] == [
        ("rn_m1", "2001-03-01 00:00:00"),
        ("rn_m2", "2001-03-02 00:00:00"),
    ]


def _records(tools, name, layer=1):
    return tools.v_db_select(map=name, layer=layer, format="json").json["records"]


def test_vector_points_without_attributes(tools):
    vector_points(tools, "vp_plain", [(1, 2), (3.5, 4)])

    assert _records(tools, "vp_plain") == [{"cat": 1}, {"cat": 2}]
    assert tools.v_info(map="vp_plain", flags="t").keyval["points"] == 2


def test_vector_points_attributes_keep_their_types(tools):
    vector_points(
        tools,
        "vp_attr",
        [(1, 1), (2, 2), (3, 3)],
        attributes={"count": [10, 20, 30], "ratio": [0.5, 1.5, 2.5], "kind": "abc"},
    )

    rows = _records(tools, "vp_attr")

    assert [(r["cat"], r["count"], r["ratio"], r["kind"]) for r in rows] == [
        (1, 10, 0.5, "a"),
        (2, 20, 1.5, "b"),
        (3, 30, 2.5, "c"),
    ]


def test_vector_points_text_values(tools):
    vector_points(
        tools, "vp_text", [(1, 1), (2, 2)], attributes={"name": ["north", "south"]}
    )

    assert [r["name"] for r in _records(tools, "vp_text")] == ["north", "south"]


def test_vector_points_coordinates(tools):
    vector_points(tools, "vp_xy", [(1, 2), (3, 4)])

    out = tools.v_out_ascii(input="vp_xy", format="point", separator="comma")

    assert out.text.splitlines() == ["1,2,1", "3,4,2"]


def _tables(tools, name):
    """The table linked to each layer of the vector map name"""
    lines = tools.v_db_connect(map=name, flags="g").text.splitlines()
    return {line.split("|")[0].split("/")[0]: line.split("|")[1] for line in lines}


def test_vector_points_in_several_layers(tools):
    vector_points(
        tools, "vp_layer", [(1, 1), (2, 2)], attributes={"v": [5, 6]}, layers=(1, 3)
    )

    layers = tools.v_category(input="vp_layer", option="layers").text.split()
    assert layers == ["1", "3"]
    assert _tables(tools, "vp_layer") == {"1": "vp_layer", "3": "vp_layer_3"}
    for layer in (1, 3):
        assert [(r["cat"], r["v"]) for r in _records(tools, "vp_layer", layer)] == [
            (1, 5),
            (2, 6),
        ]
    listed = tools.g_list(type="vector", pattern="vp_layer*").text.split()
    assert listed == ["vp_layer"]


def test_vector_points_layers_are_registered_as_map_and_layer(tools):
    vector_points(tools, "vp_ml", [(1, 1)], layers=(1, 2))
    register_stds(
        tools,
        "stvds",
        "vp_ml_ds",
        [
            MapSpec("vp_ml:1", None, day(0), day(1)),
            MapSpec("vp_ml:2", None, day(1), day(2)),
        ],
    )

    listed = tools.t_vect_list(
        input="vp_ml_ds", columns="name,layer", order="start_time", flags="u"
    ).text.split()

    assert listed == ["vp_ml|1", "vp_ml|2"]


def test_vector_points_layers_must_include_layer_1(tools):
    with pytest.raises(ValueError, match="include 1"):
        vector_points(tools, "vp_bad", [(1, 1)], layers=(2,))


def test_vector_points_refuses_existing_map_without_overwrite(tools):
    vector_points(tools, "vp_twice", [(1, 1)], attributes={"v": [1]})

    with pytest.raises(CalledModuleError):
        vector_points(tools, "vp_twice", [(1, 1)], attributes={"v": [1]})

    vector_points(
        tools, "vp_twice", [(5, 5), (6, 6)], attributes={"v": [5, 6]}, overwrite=True
    )
    assert [r["v"] for r in _records(tools, "vp_twice")] == [5, 6]


def test_vector_points_several_layers_overwrite(tools):
    vector_points(tools, "vp_lo", [(1, 1)], attributes={"v": [1]}, layers=(1, 2))

    vector_points(
        tools,
        "vp_lo",
        [(7, 7), (8, 8)],
        attributes={"v": [7, 8]},
        layers=(1, 2),
        overwrite=True,
    )

    for layer in (1, 2):
        assert [r["v"] for r in _records(tools, "vp_lo", layer)] == [7, 8]


def test_vector_points_attribute_length_must_match(tools):
    with pytest.raises(ValueError, match="2 points"):
        vector_points(tools, "vp_bad", [(1, 1), (2, 2)], attributes={"v": [1]})


def test_vector_points_text_may_not_contain_the_separator(tools):
    with pytest.raises(ValueError, match="comma"):
        vector_points(tools, "vp_bad", [(1, 1)], attributes={"v": ["a,b"]})


def test_vector_points_is_registered_like_any_vector(tools):
    vector_points(tools, "vp_reg1", [(1, 1)])
    vector_points(tools, "vp_reg2", [(2, 2)])
    register_stds(
        tools,
        "stvds",
        "vp_reg",
        [
            MapSpec("vp_reg1", None, day(0), day(1)),
            MapSpec("vp_reg2", None, day(1), day(2)),
        ],
    )

    rows = list_maps(tools, "stvds", "vp_reg")

    assert [row.name for row in rows] == ["vp_reg1", "vp_reg2"]


def test_small_region_sets_rows_and_columns(tools):
    small_region(tools, 4, 6)

    values = tools.g_region(flags="g").keyval
    assert (values["rows"], values["cols"]) == (4, 6)
    assert (values["n"], values["s"], values["e"], values["w"]) == (4, 0, 6, 0)


def test_small_region_with_depths(tools):
    small_region(tools, 2, 3, depths=5)

    values = tools.g_region(flags="g3").keyval
    assert (values["rows3"], values["cols3"], values["depths"]) == (2, 3, 5)


def test_small_region_returns_the_previous_region(tools):
    tools.g_region(n=10, s=0, e=10, w=0, t=4, b=0, res=1, res3=1)
    before = tools.g_region(flags="g3").keyval

    previous = small_region(tools, 2, 2)
    tools.g_region(**previous)

    assert tools.g_region(flags="g3").keyval == before


def test_small_region_decides_the_cells_of_a_new_map(tools):
    small_region(tools, 3, 5)
    make_map(tools, "raster", "sr_map", 9)

    info = tools.r_info(map="sr_map", flags="g").keyval
    assert (info["rows"], info["cols"]) == (3, 5)
