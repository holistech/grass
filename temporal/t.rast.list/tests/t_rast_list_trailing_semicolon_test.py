"""A trailing semicolon in the where option of t.rast.list is tolerated"""

from grass.temporal.testing.readback import list_maps


def test_where_with_a_trailing_semicolon(tools, make_stds):
    maps, (name,) = make_stds(3)

    result = tools.t_rast_list(
        input=name,
        columns="name",
        where="start_time >= '2001-01-02';",
        format="json",
    )

    assert [row["name"] for row in result.json["data"]] == maps[1:]
    assert [row.name for row in list_maps(tools, "strds", name)] == maps
