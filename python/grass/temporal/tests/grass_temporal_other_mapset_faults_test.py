"""Tools and datasets of another mapset

The datasets live in the mapset "first"; the tools run in "second", a mapset
of the same project, with only "second" and PERMANENT in the search path
unless a test adds "first". The tests check that a refusal happens before
anything is written, that a name without a mapset is searched only in the
current mapset and the search path, and that the maps of a dataset of another
mapset reach the tool with their mapset.
"""

import tarfile
from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_daily_stds, create_stds
from grass.temporal.testing.readback import message
from grass.temporal.testing.session import mapset_session, project_session
from grass.tools import ToolError, Tools

D = datetime

CURRENT = "second"
OWNER = "first"


@pytest.fixture(scope="module")
def sessions(tmp_path_factory):
    """Tools in "second" (work) and "first" (owner) of one XY project

    "first" holds ds (strds, four daily maps r_1 to r_4 with the values 1 to
    4), ds3 (str3ds, two maps), dsv (stvds, two maps), gapds (two maps with a
    day between them), sampler (two one-day maps), the thresholds low and
    high (the values 0 and 100 on the days of ds) and the dataset only_first.
    """
    project = tmp_path_factory.mktemp("other_mapset") / "project"
    with (
        project_session(project, mapset=CURRENT) as second,
        mapset_session(second, OWNER) as first,
    ):
        tools = []
        for session in (second, first):
            tools.append(
                Tools(
                    session=session,
                    consistent_return_value=True,
                    capture_stderr=True,
                )
            )
            tools[-1].g_region(n=1, s=0, e=1, w=0, res=1, b=0, t=1, res3=1)
        work, owner = tools
        create_daily_stds(owner, "strds", ["ds"], 4, map_prefix="r")
        create_daily_stds(owner, "str3ds", ["ds3"], 2, map_prefix="r3")
        create_daily_stds(owner, "stvds", ["dsv"], 2, map_prefix="v")
        create_daily_stds(owner, "strds", ["sampler", "only_first"], 2, map_prefix="s")
        for name, value in (("low", 0), ("high", 100)):
            create_stds(
                owner,
                "strds",
                name,
                [
                    MapSpec(f"{name}_{n}", value, D(2001, 1, n), D(2001, 1, n + 1))
                    for n in range(1, 5)
                ],
            )
        create_stds(
            owner,
            "strds",
            "gapds",
            [
                MapSpec("gap_1", 1, D(2001, 1, 1), D(2001, 1, 2)),
                MapSpec("gap_2", 2, D(2001, 1, 3), D(2001, 1, 4)),
            ],
        )
        yield work, owner


@pytest.fixture
def tools(sessions):
    """The tools of "second" with only "second" and PERMANENT in the search path"""
    work, _owner = sessions
    work.g_mapsets(operation="set", mapset=f"{CURRENT},PERMANENT")
    yield work
    work.g_mapsets(operation="set", mapset=f"{CURRENT},PERMANENT")


@pytest.fixture
def owner(sessions):
    return sessions[1]


def add_first(tools):
    tools.g_mapsets(operation="add", mapset=OWNER)


def lines(result):
    return result.stdout.splitlines()


def snapshot(tools, owner):
    """What the two mapsets hold: maps of every type and the temporal database"""
    state = []
    for session, mapset in ((tools, CURRENT), (owner, OWNER)):
        state.append(
            session.g_list(type="raster,raster_3d,vector", mapset=mapset).stdout
        )
        for stds_type in ("strds", "str3ds", "stvds"):
            state.append(session.t_list(type=stds_type).stdout)
        for map_type in ("raster", "raster3d", "vector"):
            state.append(session.t_list(type=map_type).stdout)
    return state


OWNER_MAPS = {"r_1", "r_2", "r_3", "r_4", "r3_1", "r3_2", "v_1", "v_2"}
KIND_OF = {
    "t.rast.extract": "strds",
    "t.rast3d.extract": "str3ds",
    "t.vect.extract": "stvds",
}


def phantoms(tools):
    """The maps of "first" that "second" lists as its own"""
    listed = tools.g_list(type="raster,raster_3d,vector", mapset=CURRENT).stdout
    return OWNER_MAPS & set(listed.split())


def snapshot_of_owner(owner):
    """Maps and datasets of "first", which a tool of "second" must not change"""
    return [
        owner.g_list(type="raster,raster_3d,vector", mapset=OWNER).stdout,
        *(owner.t_list(type=kind).stdout for kind in ("strds", "str3ds", "stvds")),
        *(
            owner.t_list(type=kind, columns="id,start_time,end_time").stdout
            for kind in ("raster", "raster3d", "vector")
        ),
    ]


def refused(tools, owner, call, expected):
    """Run the call, expect a refusal with the text and nothing changed"""
    before = snapshot(tools, owner)
    with pytest.raises(ToolError) as error:
        call()
    assert error.value.returncode == 1
    assert expected in message(error.value)
    assert snapshot(tools, owner) == before
    return message(error.value)


def listing(tools, name, columns="name,mapset,start_time"):
    return lines(tools.t_rast_list(input=name, columns=columns))


EXTRACTS = {
    "t.rast.extract": (
        lambda t, name, output: t.t_rast_extract(input=f"{name}@first", output=output),
        "ds",
        lambda t, name: lines(t.t_rast_list(input=name, columns="name,mapset")),
        ["name|mapset", "r_1|first", "r_2|first", "r_3|first", "r_4|first"],
    ),
    "t.rast3d.extract": (
        lambda t, name, output: t.t_rast3d_extract(
            input=f"{name}@first", output=output
        ),
        "ds3",
        lambda t, name: lines(t.t_rast3d_list(input=name, columns="name,mapset")),
        ["name|mapset", "r3_1|first", "r3_2|first"],
    ),
    "t.vect.extract": (
        lambda t, name, output: t.t_vect_extract(input=f"{name}@first", output=output),
        "dsv",
        lambda t, name: lines(t.t_vect_list(input=name, columns="name,mapset")),
        ["name|mapset", "v_1|first", "v_2|first"],
    ),
}


@pytest.mark.parametrize("tool", sorted(EXTRACTS))
def test_extract_without_expression_from_other_mapset(tools, owner, tool):
    """The new dataset holds the maps of the original, which stay in "first\""""
    call, name, read, expected = EXTRACTS[tool]
    output = f"{name}_copy"

    call(tools, name, output)

    assert read(tools, output) == expected
    # The maps were not copied: "second" holds none of them, "first" still all.
    assert not phantoms(tools)
    assert read(tools, f"{name}@first") == expected
    # The register of the maps in "second" names only the new dataset, so the
    # extract can be removed with its registrations.
    before = snapshot_of_owner(owner)
    tools.t_remove(type=KIND_OF[tool], inputs=output, flags="rf")
    assert snapshot_of_owner(owner) == before
    assert read(tools, f"{name}@first") == expected


def test_extract_of_the_maps_of_other_mapset_keeps_their_times(tools):
    tools.t_rast_extract(
        input="ds@first", output="timed", where="start_time >= '2001-01-02'"
    )

    assert listing(tools, "timed") == [
        "name|mapset|start_time",
        "r_2|first|2001-01-02 00:00:00",
        "r_3|first|2001-01-03 00:00:00",
        "r_4|first|2001-01-04 00:00:00",
    ]


def test_gaps_of_dataset_of_other_mapset_are_refused_first(tools, owner):
    """t.rast.gapfill: no interpolated map stays without an entry"""
    refused(
        tools,
        owner,
        lambda: tools.t_rast_gapfill(input="gapds@first", basename="filled"),
        "Unable to register maps in the space time dataset <gapds@first>. "
        "The mapset of the dataset does not match the current mapset",
    )


def test_dataset_of_other_mapset_is_refused_first(tools, owner):
    """t.rast.gapfill refuses before it looks for gaps, with or without any"""
    refused(
        tools,
        owner,
        lambda: tools.t_rast_gapfill(input="ds@first", basename="filled"),
        "does not match the current mapset",
    )


def accumulate_with_output(tools, output):
    return tools.t_rast_accumulate(
        input="ds@first",
        output=output,
        basename="acc",
        start="2001-01-01",
        cycle="2 days",
        limits="0,100",
    )


REFUSALS = {
    "t.unregister": (
        lambda t: t.t_unregister(type="raster", input="ds@first", maps="r_1"),
        (
            "Unable to update dataset <ds@first> of type strds in the temporal "
            "database. The mapset of the database does not match the current mapset"
        ),
    ),
    "t.support": (
        lambda t: t.t_support(input="ds@first", type="strds", title="changed"),
        (
            "Unable to update dataset <ds@first> of type strds in the temporal "
            "database. The mapset of the database does not match the current mapset"
        ),
    ),
    "t.support -m": (
        lambda t: t.t_support(input="ds@first", type="strds", flags="m"),
        "does not match the current mapset",
    ),
    "t.remove": (
        lambda t: t.t_remove(inputs="ds@first", type="strds"),
        (
            "Unable to delete dataset <ds@first> of type strds from the temporal "
            "database. The mapset of the database does not match the current mapset"
        ),
    ),
    "t.remove -f": (
        lambda t: t.t_remove(inputs="ds@first", type="strds", flags="f"),
        "does not match the current mapset",
    ),
    "t.rast.accumulate": (
        lambda t: accumulate_with_output(t, "acc@first"),
        "Space time datasets can only be created in the current mapset",
    ),
}


@pytest.mark.parametrize("tool", sorted(REFUSALS))
def test_other_mapset_is_refused_before_reading(tools, owner, tool):
    call, expected = REFUSALS[tool]

    text = refused(tools, owner, lambda: call(tools), expected)

    # Nothing was read or computed before the refusal.
    for progress in ("Unregister maps", "Processing cycle"):
        assert progress not in text


def test_dataset_of_other_mapset(tools, owner, tmp_path):
    """The tools that only read a dataset of another mapset read it"""
    export = tools.t_rast_export(
        input="ds@first", output=str(tmp_path / "exported"), compression="no"
    )
    assert "File <r_1.tif> created" in export.stderr
    with tarfile.open(tmp_path / "exported") as archive:
        assert {f"r_{n}.tif" for n in range(1, 5)} <= set(archive.getnames())

    what = tools.t_rast_what(strds="ds@first", coordinates="0.5,0.5")
    assert [line.split("|")[-1] for line in lines(what)] == ["1", "2", "3", "4"]

    tools.t_rast_to_rast3(input="ds@first", output="stack")
    info = tools.r3_info(map="stack", flags="g").keyval
    assert info["depths"] == 4
    # The maps of the original are read, the result is made in "second".
    assert tools.g_list(type="raster_3d", mapset=CURRENT).stdout.split() == ["stack"]


# The tools that look for a name without a mapset: the call with the name of
# a dataset of "first" and the check of the result.
def accdetect(tools, input_name="ds", **options):
    return tools.t_rast_accdetect(
        input=input_name,
        occurrence="occurrence",
        basename="occ",
        start="2001-01-01",
        cycle="4 days",
        overwrite=True,
        **options,
    )


FOUND = {
    "t.vect.univar": (
        lambda t: t.t_vect_univar(input="dsv", column="value"),
        lambda t, r: (
            [line.split("|")[0] for line in lines(r)[1:]] == ["v_1@first", "v_2@first"]
        ),
    ),
    "t.rast.accdetect": (
        lambda t: accdetect(t, range="1,3"),
        lambda t, r: len(listing(t, "occurrence")) == 2,
    ),
    "t.rast.accdetect minimum maximum": (
        lambda t: accdetect(t, minimum="low", maximum="high"),
        lambda t, r: len(listing(t, "occurrence")) == 5,
    ),
    "t.rast.accumulate": (
        lambda t: t.t_rast_accumulate(
            input="ds",
            output="accumulated",
            basename="acc",
            start="2001-01-01",
            cycle="4 days",
            limits="0,100",
            overwrite=True,
        ),
        lambda t, r: len(listing(t, "accumulated")) == 5,
    ),
    "t.rast.aggregate.ds": (
        lambda t: t.t_rast_aggregate_ds(
            input="ds",
            sample="sampler",
            output="aggregated",
            basename="aggr",
            method="sum",
            sampling="equal",
            overwrite=True,
        ),
        lambda t, r: len(listing(t, "aggregated")) == 3,
    ),
    "t.info": (
        lambda t: t.t_info(type="strds", input="ds", flags="g"),
        lambda t, r: "id=ds@first" in lines(r),
    ),
    "t.rast.mapcalc": (
        lambda t: t.t_rast_mapcalc(
            inputs="ds",
            output="calculated",
            basename="calc",
            expression="ds + 1",
            overwrite=True,
        ),
        lambda t, r: len(listing(t, "calculated")) == 5,
    ),
}


@pytest.mark.parametrize("tool", sorted(FOUND))
def test_name_without_mapset_found_in_search_path(tools, tool):
    add_first(tools)

    result = FOUND[tool][0](tools)

    assert FOUND[tool][1](tools, result)


@pytest.mark.parametrize("tool", sorted(FOUND))
def test_name_without_mapset_outside_search_path_is_not_found(tools, owner, tool):
    refused(tools, owner, lambda: FOUND[tool][0](tools), "not found")


def test_accdetect_occurrence_has_the_days_in_range(tools):
    add_first(tools)

    accdetect(tools, range="1,3")

    rows = listing(tools, "occurrence", columns="name,min,max")
    assert rows == ["name|min|max", "occ_2001_01_02|1.0|1.0"]


def test_input_of_mapset_outside_search_path_accdetect(tools):
    """The maps of ds@first reach r.mapcalc with their mapset"""
    accdetect(tools, "ds@first", range="1,3")

    assert listing(tools, "occurrence", columns="name,min,max") == [
        "name|min|max",
        "occ_2001_01_02|1.0|1.0",
    ]


def test_input_of_mapset_outside_search_path_accdetect_thresholds(tools):
    accdetect(tools, "ds@first", minimum="low@first", maximum="high@first")

    assert listing(tools, "occurrence", columns="name,min,max") == [
        "name|min|max",
        "occ_2001_01_01|0.0|0.0",
        "occ_2001_01_02|1.0|1.0",
        "occ_2001_01_03|2.0|2.0",
        "occ_2001_01_04|3.0|3.0",
    ]


def test_input_of_mapset_outside_search_path_mapcalc(tools):
    tools.t_rast_mapcalc(
        inputs="ds@first",
        output="plus_one",
        basename="plus",
        expression="ds + 1",
    )

    assert listing(tools, "plus_one", columns="name,min,max") == [
        "name|min|max",
        "plus_1|2.0|2.0",
        "plus_2|3.0|3.0",
        "plus_3|4.0|4.0",
        "plus_4|5.0|5.0",
    ]


def test_input_of_mapset_outside_search_path_mapcalc_with_two_inputs(tools):
    tools.t_rast_mapcalc(
        inputs="ds@first,low@first",
        output="sum_of_two",
        basename="sum",
        expression="ds + low",
    )

    assert listing(tools, "sum_of_two", columns="name,min,max")[1:] == [
        "sum_1|1.0|1.0",
        "sum_2|2.0|2.0",
        "sum_3|3.0|3.0",
        "sum_4|4.0|4.0",
    ]


def test_input_of_mapset_outside_search_path_mapcalc3d(tools):
    tools.t_rast3d_mapcalc(
        inputs="ds3@first",
        output="plus_one3",
        basename="plus3",
        expression="ds3 + 1",
    )

    rows = lines(tools.t_rast3d_list(input="plus_one3", columns="name,min,max"))
    assert rows == ["name|min|max", "plus3_1|2.0|2.0", "plus3_2|3.0|3.0"]


@pytest.mark.parametrize("in_search_path", [False, True])
def test_qualified_name_in_expression_mapcalc(tools, in_search_path):
    """The expression may name the input as ds@first, as before"""
    if in_search_path:
        add_first(tools)

    tools.t_rast_mapcalc(
        inputs="ds@first",
        output="qualified",
        basename="qual",
        expression="ds@first + 1",
        overwrite=True,
    )

    assert listing(tools, "qualified", columns="name,min,max") == [
        "name|min|max",
        "qual_1|2.0|2.0",
        "qual_2|3.0|3.0",
        "qual_3|4.0|4.0",
        "qual_4|5.0|5.0",
    ]


@pytest.mark.parametrize("in_search_path", [False, True])
def test_qualified_name_in_expression_mapcalc3d(tools, in_search_path):
    if in_search_path:
        add_first(tools)

    tools.t_rast3d_mapcalc(
        inputs="ds3@first",
        output="qualified3",
        basename="qual3",
        expression="ds3@first + 1",
        overwrite=True,
    )

    rows = lines(tools.t_rast3d_list(input="qualified3", columns="name,min,max"))
    assert rows == ["name|min|max", "qual3_1|2.0|2.0", "qual3_2|3.0|3.0"]


def test_name_without_mapset_is_not_found_in_a_mapset_added_by_a_qualified_name(
    tools, owner
):
    """The first name adds "first" to the connection; the second must not use it"""
    outcome = refused(
        tools,
        owner,
        lambda: tools.t_rast_aggregate_ds(
            input="ds@first",
            sample="only_first",
            output="aggregated",
            basename="aggr",
            method="sum",
            sampling="equal",
        ),
        "<only_first>",
    )
    # The same message as a tool that searches one name only.
    with pytest.raises(ToolError) as error:
        tools.t_rast_list(input="only_first")
    assert "Space time dataset <only_first> of type <strds> not found" in message(
        error.value
    )
    assert "Space time dataset <only_first> of type <strds> not found" in outcome


def test_vect_what_strds_does_not_find_a_name_in_a_mapset_added_by_a_qualified_name(
    tools, owner
):
    refused(
        tools,
        owner,
        lambda: tools.t_vect_what_strds(
            input="dsv@first", strds="ds", column="what", method="average"
        ),
        "Space time dataset <ds> of type <strds> not found",
    )


def test_name_in_the_search_path_is_found_by_both_tools(tools):
    """With "first" in the search path the same two calls work"""
    add_first(tools)

    tools.t_rast_aggregate_ds(
        input="ds@first",
        sample="only_first",
        output="aggregated",
        basename="aggr",
        method="sum",
        sampling="equal",
        overwrite=True,
    )

    assert len(listing(tools, "aggregated")) == 3


def test_copy_and_merge_without_maps_make_no_map_of_the_owner(tools):
    """t.copy and t.merge without -c insert the maps of the other mapset

    3D raster and vector maps showed up in g.list of "second" before, because
    the time stamp of each map was written into it.
    """
    tools.t_copy(type="str3ds", input="ds3@first", output="copy3")
    tools.t_copy(type="stvds", input="dsv@first", output="copyv")
    tools.t_merge(type="str3ds", inputs="ds3@first", output="merge3")
    tools.t_merge(type="stvds", inputs="dsv@first", output="mergev")

    assert not phantoms(tools)


def test_register_of_map_of_other_mapset_makes_no_map_of_the_owner(tools):
    """An update of a map of another mapset writes no time stamp either"""
    tools.t_copy(type="str3ds", input="ds3@first", output="update_copy3")
    tools.t_create(
        type="str3ds", output="update_target", title="t", description="d", quiet=True
    )

    tools.t_register(
        type="raster_3d",
        input="update_target",
        maps="r3_1@first",
        start="2002-01-01",
        overwrite=True,
    )

    assert not phantoms(tools)


@pytest.fixture(scope="module")
def odd_sessions(tmp_path_factory):
    """Tools in the mapsets "user-1" and "2026", names that r.mapcalc splits

    The mapset "user-1" is the current one and holds the datasets own,
    own3; "2026" holds other, other3. The names of the maps and of the
    mapsets show how a map is written into an r.mapcalc expression.
    """
    project = tmp_path_factory.mktemp("odd_names") / "project"
    with (
        project_session(project, mapset="user-1") as work,
        mapset_session(work, "2026") as other,
    ):
        tools = []
        for session in (work, other):
            tools.append(
                Tools(
                    session=session, consistent_return_value=True, capture_stderr=True
                )
            )
            tools[-1].g_region(n=1, s=0, e=1, w=0, res=1, b=0, t=1, res3=1)
        current, foreign = tools
        create_daily_stds(current, "strds", ["own"], 2, map_prefix="o")
        create_daily_stds(current, "str3ds", ["own3"], 2, map_prefix="o3")
        for place, kind in ((current, "c"), (foreign, "f")):
            for bound, value in (("low", 0), ("high", 100)):
                create_stds(
                    place,
                    "strds",
                    f"{bound}{kind}",
                    [
                        MapSpec(
                            f"{bound}{kind}_{n}",
                            value,
                            D(2001, 1, n),
                            D(2001, 1, n + 1),
                        )
                        for n in (1, 2)
                    ],
                )
        create_daily_stds(foreign, "strds", ["other"], 2, map_prefix="f")
        create_daily_stds(foreign, "str3ds", ["other3"], 2, map_prefix="f3")
        yield current


def values(tools, name, lister="t_rast_list"):
    rows = lines(getattr(tools, lister)(input=name, columns="name,min,max"))[1:]
    return [(row.split("|")[1], row.split("|")[2]) for row in rows]


@pytest.mark.parametrize("source", ["own", "other@2026"])
def test_mapcalc_with_mapsets_that_r_mapcalc_splits(odd_sessions, source):
    name = source.split("@")[0]

    odd_sessions.t_rast_mapcalc(
        inputs=source,
        output=f"calc_{name}",
        basename=f"calc_{name}",
        expression=f"{name} + 1",
    )

    assert values(odd_sessions, f"calc_{name}") == [("2.0", "2.0"), ("3.0", "3.0")]


@pytest.mark.parametrize("source", ["own3", "other3@2026"])
def test_mapcalc3d_with_mapsets_that_r_mapcalc_splits(odd_sessions, source):
    name = source.split("@")[0]

    odd_sessions.t_rast3d_mapcalc(
        inputs=source,
        output=f"calc_{name}",
        basename=f"calc_{name}",
        expression=f"{name} + 1",
    )

    assert values(odd_sessions, f"calc_{name}", "t_rast3d_list") == [
        ("2.0", "2.0"),
        ("3.0", "3.0"),
    ]


@pytest.mark.parametrize("source", ["own@user-1", "other@2026"])
def test_mapcalc_with_qualified_name_in_expression_that_r_mapcalc_splits(
    odd_sessions, source
):
    """The expression names the input with a mapset that r.mapcalc splits"""
    name = source.split("@")[0]

    odd_sessions.t_rast_mapcalc(
        inputs=source,
        output=f"qcalc_{name}",
        basename=f"qcalc_{name}",
        expression=f"{source} + 1",
    )

    assert values(odd_sessions, f"qcalc_{name}") == [("2.0", "2.0"), ("3.0", "3.0")]


@pytest.mark.parametrize("source", ["own3@user-1", "other3@2026"])
def test_mapcalc3d_with_qualified_name_in_expression_that_r_mapcalc_splits(
    odd_sessions, source
):
    name = source.split("@")[0]

    odd_sessions.t_rast3d_mapcalc(
        inputs=source,
        output=f"qcalc_{name}",
        basename=f"qcalc_{name}",
        expression=f"{source} + 1",
    )

    assert values(odd_sessions, f"qcalc_{name}", "t_rast3d_list") == [
        ("2.0", "2.0"),
        ("3.0", "3.0"),
    ]


@pytest.mark.parametrize("source", ["own", "other@2026"])
def test_accdetect_with_mapsets_that_r_mapcalc_splits(odd_sessions, source):
    name = source.split("@")[0]

    odd_sessions.t_rast_accdetect(
        input=source,
        occurrence=f"occ_{name}",
        basename=f"occ_{name}",
        start="2001-01-01",
        cycle="2 days",
        range="0,10",
    )

    assert values(odd_sessions, f"occ_{name}") == [("0.0", "0.0"), ("1.0", "1.0")]


@pytest.mark.parametrize("suffix", ["", "@2026"])
def test_accdetect_thresholds_with_mapsets_that_r_mapcalc_splits(odd_sessions, suffix):
    kind = "f" if suffix else "c"

    odd_sessions.t_rast_accdetect(
        input="own",
        minimum=f"low{kind}{suffix}",
        maximum=f"high{kind}{suffix}",
        occurrence=f"thr_{kind}",
        basename=f"thr_{kind}",
        start="2001-01-01",
        cycle="2 days",
    )

    assert values(odd_sessions, f"thr_{kind}") == [("0.0", "0.0"), ("1.0", "1.0")]


def test_extract_with_expression_in_mapset_that_r_mapcalc_splits(odd_sessions):
    odd_sessions.t_rast_extract(
        input="own", output="ext", expression="own + 1", basename="ext"
    )

    assert values(odd_sessions, "ext") == [("2.0", "2.0"), ("3.0", "3.0")]
