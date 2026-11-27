"""Test t.vect.list on maps with layers and on the columns of a vector map

The map lay has three points at (1, 1), (3, 4) and (2, 2) and three layers
with the same categories. It is registered as lay:3 (January), lay:2
(February) and lay:1 (March), so the order of the layers differs from the order
of time, and the plain map lp (one point, no layer) follows in April. The map
lg has six layers and is registered as lg:1 to lg:6 at six intervals with gaps.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, make_map, register_stds, vector_points

D = datetime
GAPS = [
    (D(2001, 1, 1), D(2001, 4, 1)),
    (D(2001, 5, 1), D(2001, 7, 1)),
    (D(2001, 8, 1), D(2001, 10, 1)),
    (D(2001, 11, 1), D(2002, 1, 1)),
    (D(2002, 2, 1), D(2002, 4, 1)),
    (D(2002, 5, 1), D(2002, 7, 1)),
]


@pytest.fixture(scope="module")
def stds(tools):
    vector_points(
        tools,
        "lay",
        [(1, 1), (3, 4), (2, 2)],
        attributes={"value": [1, 2, 3]},
        layers=(1, 2, 3),
    )
    make_map(tools, "vector", "lp", 1)
    month = [D(2001, number, 1) for number in range(1, 6)]
    register_stds(
        tools,
        "stvds",
        "layered",
        [
            MapSpec("lay:3", None, month[0], month[1]),
            MapSpec("lay:2", None, month[1], month[2]),
            MapSpec("lay:1", None, month[2], month[3]),
            MapSpec("lp", None, month[3], month[4]),
        ],
    )
    vector_points(
        tools, "lg", [(1, 1)], attributes={"value": [1]}, layers=(1, 2, 3, 4, 5, 6)
    )
    register_stds(
        tools,
        "stvds",
        "layered_gaps",
        [MapSpec(f"lg:{number}", None, *GAPS[number - 1]) for number in range(1, 7)],
    )


def _lines(tools, **options):
    return tools.t_vect_list(**options).stdout.splitlines()


def test_the_layer_is_listed_with_the_name_of_the_map(tools, stds):
    assert _lines(tools, input="layered") == [
        "name|layer|mapset|start_time|end_time",
        "lay|3|PERMANENT|2001-01-01 00:00:00|2001-02-01 00:00:00",
        "lay|2|PERMANENT|2001-02-01 00:00:00|2001-03-01 00:00:00",
        "lay|1|PERMANENT|2001-03-01 00:00:00|2001-04-01 00:00:00",
        "lp|None|PERMANENT|2001-04-01 00:00:00|2001-05-01 00:00:00",
    ]


def test_the_id_holds_the_layer_of_a_layered_map_only(tools, stds):
    assert _lines(tools, input="layered", columns="id", flags="u") == [
        "lay:3@PERMANENT",
        "lay:2@PERMANENT",
        "lay:1@PERMANENT",
        "lp@PERMANENT",
    ]


def test_order_by_layer(tools, stds):
    lines = _lines(
        tools, input="layered", columns="name,layer", order="layer", flags="u"
    )

    # A text sorts a missing layer (stored as NULL) first or last depending on
    # the database; the layers 1 to 3 keep their order either way.
    assert [line for line in lines if line != "lp|None"] == [
        "lay|1",
        "lay|2",
        "lay|3",
    ]


def test_where_selects_a_layer(tools, stds):
    assert _lines(
        tools, input="layered", where="layer = 2", columns="id", flags="u"
    ) == ["lay:2@PERMANENT"]


def test_json_holds_the_layer_as_text(tools, stds):
    data = tools.t_vect_list(input="layered", format="json", columns="name,layer").json[
        "data"
    ]

    assert [(row["name"], row["layer"]) for row in data] == [
        ("lay", "3"),
        ("lay", "2"),
        ("lay", "1"),
        ("lp", None),
    ]


def test_csv_leaves_the_layer_of_a_plain_map_empty(tools, stds):
    lines = _lines(
        tools, input="layered", format="csv", columns="name,layer", flags="u"
    )

    assert lines[-1] == '"lp",""'


def test_deltagaps_lists_the_gaps_between_the_layers(tools, stds):
    lines = _lines(
        tools, input="layered_gaps", method="deltagaps", columns="name,layer,start_time"
    )

    # Six layers at the intervals with gaps: five gap rows between them.
    names = [line.split("|")[:2] for line in lines[1:]]
    assert names == [
        ["lg", "1"],
        ["None", "None"],
        ["lg", "2"],
        ["None", "None"],
        ["lg", "3"],
        ["None", "None"],
        ["lg", "4"],
        ["None", "None"],
        ["lg", "5"],
        ["None", "None"],
        ["lg", "6"],
    ]


def test_gran_repeats_a_layer_for_every_month(tools, stds):
    lines = _lines(tools, input="layered_gaps", method="gran", columns="name,layer")

    # The first interval covers three months, the others two.
    assert lines[1:4] == ["lg|1"] * 3
    assert lines[4] == "None|None"
    assert lines[5:7] == ["lg|2"] * 2


def test_the_vector_columns_describe_the_map(tools, stds):
    columns = (
        "id,name,layer,mapset,temporal_type,north,south,west,east,points,lines,"
        "boundaries,centroids,faces,kernels,primitives,nodes,areas,islands,holes,"
        "volumes"
    )

    lines = _lines(tools, input="layered", columns=columns, where="layer = 2")

    # The points lie at x = 1, 3 and 2 and y = 1, 4 and 2: west 1, east 3,
    # south 1, north 4. Three points are three primitives.
    assert lines == [
        columns.replace(",", "|"),
        "lay:2@PERMANENT|lay|2|PERMANENT|absolute|4.0|1.0|1.0|3.0|3|0|0|0|0|0|3|0|0|0|0|0",
    ]


def test_a_map_of_one_point_has_a_degenerate_extent(tools, stds):
    lines = _lines(
        tools,
        input="layered",
        columns="north,south,west,east,points",
        where="name = 'lp'",
        flags="u",
    )

    # make_map() puts the point at (1, 1).
    assert lines == ["1.0|1.0|1.0|1.0|1"]


def test_creator_and_creation_time_are_set(tools, stds):
    lines = _lines(
        tools,
        input="layered",
        columns="creator,creation_time",
        where="name = 'lp'",
        flags="u",
    )

    creator, creation_time = lines[0].split("|")
    assert creator
    assert datetime.strptime(creation_time[:19], "%Y-%m-%d %H:%M:%S")
