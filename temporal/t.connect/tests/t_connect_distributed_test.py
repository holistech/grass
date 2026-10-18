"""Test datasets in several mapsets, each with its own temporal database

t.connect gives every mapset its own connection (t.connect -d sets the default
file in the mapset), so a project holds one temporal database per mapset. The
tests build three mapsets with a dataset A each, in the three dataset types,
and read them from a fourth mapset and from the three themselves, with all of
them on the search path.

In mapset number i (1 to 3) the maps a1 to a3 are registered from 2001-01-01
with the step "i months", map k lasting from (k-1) i to k i months. The dataset
runs from 2001-01-01 to 2001-01-01 plus 3 i months and has the granularity
i months. The former tests used six mapsets for rasters and four for the others;
the mapsets do not depend on each other, so three show the same.
"""

import contextlib
from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import make_map
from grass.temporal.testing.readback import list_maps, stds_info
from grass.temporal.testing.session import mapset_session, project_session
from grass.tools import Tools

KINDS = [
    pytest.param(("strds", "raster", "t_rast_list"), id="strds"),
    pytest.param(("str3ds", "raster_3d", "t_rast3d_list"), id="str3ds"),
    pytest.param(("stvds", "vector", "t_vect_list"), id="stvds"),
]
COUNT = 3

# The tests marked slow call a tool once for each of the three mapsets and take
# about 1.2 s; the others call it once (measured 18.10.2026 with a serial
# pytest --durations=0).


def _month(offset):
    """The first day of the month that lies offset months after 2001-01-01"""
    return f"2001-{1 + offset:02d}-01 00:00:00"


@pytest.fixture(scope="module", params=KINDS)
def project(request, tmp_path_factory):
    """Tools of the viewing mapset and of the mapsets d<type>1 to d<type>3"""
    stds_type, map_type, list_tool = request.param
    path = tmp_path_factory.mktemp("distributed") / "project"
    names = [f"d{stds_type}{i}" for i in range(1, COUNT + 1)]
    with contextlib.ExitStack() as stack:
        viewer = stack.enter_context(project_session(path, mapset="viewer"))
        sessions = {
            name: stack.enter_context(mapset_session(viewer, name)) for name in names
        }
        tools = {"viewer": Tools(session=viewer, consistent_return_value=True)}
        for name, session in sessions.items():
            tools[name] = Tools(session=session, consistent_return_value=True)
        for number, name in enumerate(names, 1):
            here = tools[name]
            here.g_region(n=1, s=0, e=1, w=0, res=1, b=0, t=1, res3=1)
            here.t_connect(flags="d")
            maps = []
            for k in (1, 2, 3):
                make_map(here, map_type, f"a{k}", k)
                maps.append(f"a{k}")
            here.t_create(
                type=stds_type,
                temporaltype="absolute",
                output="A",
                title="A test",
                description="A test",
            )
            here.t_register(
                flags="i",
                type=map_type,
                input="A",
                maps=",".join(maps),
                start="2001-01-01",
                increment=f"{number} months",
            )
        for name, here in tools.items():
            others = [other for other in [*names, "viewer"] if other != name]
            here.g_mapsets(operation="add", mapset=",".join(others))
        yield SimpleNamespace(
            stds_type=stds_type,
            map_type=map_type,
            list_tool=list_tool,
            mapsets=names,
            tools=tools,
        )


@pytest.fixture(params=["viewer", 1, 2, 3])
def reader(request, project):
    """Tools of the mapset that a test reads from: the viewer or a data mapset"""
    key = (
        request.param
        if request.param == "viewer"
        else project.mapsets[request.param - 1]
    )
    return project.tools[key]


def test_each_mapset_has_a_connection_of_its_own(project):
    for name in project.mapsets:
        (entry,) = project.tools[name].t_connect(flags="p", format="json", mapset=".")
        assert entry["mapset"] == name
        assert entry["driver"] == "sqlite"
        assert entry["database"] == "$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db"


def test_t_list_reads_the_dataset_of_every_mapset(project, reader):
    result = reader.t_list(
        type=project.stds_type,
        columns="name,mapset,start_time,end_time,number_of_maps",
        where='name = "A"',
    )

    # Mapset i: three maps of i months each, so the dataset ends 3 i months
    # after 2001-01-01.
    lines = [line for line in result.stdout.splitlines() if line]
    assert sorted(lines) == sorted(
        f"A|{name}|{_month(0)}|{_month(3 * number)}|3"
        for number, name in enumerate(project.mapsets, 1)
    )


def test_t_list_writes_the_same_to_a_file(project, reader, tmp_path):
    columns = "name,mapset,start_time,end_time,number_of_maps"
    options = {"type": project.stds_type, "columns": columns, "where": 'name = "A"'}
    expected = reader.t_list(**options).stdout

    reader.t_list(output=tmp_path / "list.txt", **options)

    assert (tmp_path / "list.txt").read_text() == expected


@pytest.mark.slow
def test_the_maps_of_a_dataset_of_another_mapset(project, reader):
    for number, name in enumerate(project.mapsets, 1):
        rows = list_maps(reader, project.stds_type, f"A@{name}")

        # Map k lasts from (k-1) i to k i months.
        assert [(row.name, row.start, row.end) for row in rows] == [
            (f"a{k}", _month((k - 1) * number), _month(k * number)) for k in (1, 2, 3)
        ]


def test_the_maps_list_goes_to_a_file(project, reader, tmp_path):
    name = project.mapsets[1]
    options = {"input": f"A@{name}", "columns": "name,mapset,start_time,end_time"}
    tool = getattr(reader, project.list_tool)
    expected = tool(**options).stdout

    tool(output=tmp_path / "maps.txt", **options)

    # The mapset has the step of 2 months, so map k lasts from 2 (k-1) to 2 k.
    assert expected.splitlines() == [
        "name|mapset|start_time|end_time",
        *(f"a{k}|{name}|{_month(2 * (k - 1))}|{_month(2 * k)}" for k in (1, 2, 3)),
    ]
    assert (tmp_path / "maps.txt").read_text() == expected


@pytest.mark.slow
def test_t_info_of_a_dataset_of_another_mapset(project, reader):
    for number, name in enumerate(project.mapsets, 1):
        info = stds_info(reader, project.stds_type, f"A@{name}")

        assert info["id"] == f"A@{name}"
        assert info["mapset"] == name
        assert info["start_time"] == f"'{_month(0)}'"
        assert info["end_time"] == f"'{_month(3 * number)}'"
        assert info["granularity"] == f"'{number} month{'s' if number > 1 else ''}'"


@pytest.mark.slow
def test_t_info_of_a_map_of_another_mapset(project, reader):
    for number, name in enumerate(project.mapsets, 1):
        info = reader.t_info(
            flags="g", type=project.map_type, input=f"a1@{name}"
        ).keyval

        assert info["id"] == f"a1@{name}"
        assert info["mapset"] == name
        assert info["temporal_type"] == "absolute"
        assert info["start_time"] == f"'{_month(0)}'"
        assert info["end_time"] == f"'{_month(number)}'"
