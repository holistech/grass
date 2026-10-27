"""Test t.topology -m and -s, which list the relations of each map

-m prints for every map its neighbours in time (next, previous) and its
temporal relations; -s adds the spatial relations to the maps it is related to
in time. where= restricts the maps, and a dataset of such a subset says so.
"""

import re
from io import StringIO

import pytest

from grass.temporal.testing.data import register_file
from grass.tools import ToolError


def _blocks(text):
    """The maps of a -m or -s listing: id to a dict of label to list of ids

    Only the sections "Temporal Topology" and "Spatial Topology" are read.
    """
    result = {}
    for block in text.split("Dataset ---")[1:]:
        map_id = re.search(r"\| Id: \.+ (\S+)", block).group(1)
        labels = {}
        keep = False
        for line in block.splitlines():
            if "-----" in line:
                keep = "Topology" in line
                continue
            match = re.match(r"\s*\|\s*([^:|]+?):[ .]*(\S.*?)\s*$", line)
            if keep and match:
                labels[match.group(1)] = match.group(2).split(",")
        result[map_id] = labels
    return result


@pytest.fixture
def nested(tools, prefix, tmp_path):
    """Maps a, b, c and the dataset that holds them

    Months: a [0,6), b [1,3), c [3,6), all on the region of one cell.
    """
    names = {key: f"{prefix}_{key}" for key in "abc"}
    tools.r_mapcalc(file=StringIO("\n".join(f"{n} = 1" for n in names.values())))
    name = f"{prefix}_ds"
    tools.t_create(output=name, title="t", description="d")
    file = register_file(
        tmp_path / "maps.txt",
        [
            (names["a"], "2001-01-01", "2001-07-01"),
            (names["b"], "2001-02-01", "2001-04-01"),
            (names["c"], "2001-04-01", "2001-07-01"),
        ],
    )
    tools.t_register(input=name, file=file)
    return name, {key: f"{value}@PERMANENT" for key, value in names.items()}


def test_m_lists_the_temporal_relations_of_every_map(tools, nested):
    name, ids = nested

    result = tools.t_topology(input=name, flags="m")

    blocks = _blocks(result.stdout)
    a, b, c = ids["a"], ids["b"], ids["c"]
    assert list(blocks) == [a, b, c]
    # b lies in a, c ends with a (so it also lies in a, and finishes it), and
    # b ends where c starts.
    assert blocks[a] == {
        "Next": [b],
        "Contains": [b, c],
        "Finished": [c],
    }
    assert blocks[b] == {
        "Next": [c],
        "Previous": [a],
        "Precedes": [c],
        "During": [a],
    }
    assert blocks[c] == {
        "Previous": [b],
        "Follows": [b],
        "During": [a],
        "Finishes": [a],
    }


def test_m_prints_no_summary(tools, nested):
    name, _ = nested

    result = tools.t_topology(input=name, flags="m")

    assert "Temporal topology is" not in result.stdout
    assert "Spatial Topology" not in result.stdout


def test_s_adds_the_spatial_relations(tools, nested):
    name, ids = nested

    result = tools.t_topology(input=name, flags="s")

    blocks = _blocks(result.stdout)
    # The maps have the same extent and are related in time: equivalent.
    assert blocks[ids["a"]]["Equivalent"] == [ids["b"], ids["c"]]
    assert blocks[ids["b"]]["Equivalent"] == [ids["a"], ids["c"]]
    assert blocks[ids["c"]]["Equivalent"] == [ids["a"], ids["b"]]
    # The temporal relations are the same as with -m.
    assert blocks[ids["a"]]["Contains"] == [ids["b"], ids["c"]]


def test_m_with_s_is_the_same_as_s(tools, nested):
    name, _ = nested

    assert (
        tools.t_topology(input=name, flags="ms").stdout
        == tools.t_topology(input=name, flags="s").stdout
    )


def test_where_restricts_the_summary(tools, nested):
    name, _ = nested

    result = tools.t_topology(input=name, where="start_time >= '2001-02-01'")

    text = result.stdout
    assert "Is subset of dataset: ...... True" in text
    # b [1,3) and c [3,6): two intervals that touch.
    assert "Number of intervals: ....... 2" in text
    assert "Temporal topology is: ...... valid" in text
    assert "Follows: ................... 1" in text


def test_where_restricts_the_maps_of_m(tools, nested):
    name, ids = nested

    result = tools.t_topology(input=name, flags="m", where="start_time >= '2001-02-01'")

    blocks = _blocks(result.stdout)
    assert list(blocks) == [ids["b"], ids["c"]]
    assert blocks[ids["b"]] == {"Next": [ids["c"]], "Precedes": [ids["c"]]}
    assert blocks[ids["c"]] == {"Previous": [ids["b"]], "Follows": [ids["b"]]}


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_s_relates_maps_of_different_extents(tools, prefix, tmp_path):
    # Extents (west, east, south, north): A (0,120,0,80); B (10,110,20,70)
    # lies strictly inside A; C (10,130,20,80) has B in it and shares its west
    # and south edge; D (10,130,70,90) touches B along the line north = 70.
    # Times in June 1990: A 1-5, B 5-18, C 10-13, D 16-20. Only maps that are
    # related in time are related in space: A/B (follows), B/C (during), B/D
    # (overlaps); A is before C and D, and C before D.
    extents = {
        "A": {"s": 0, "n": 80, "w": 0, "e": 120},
        "B": {"s": 20, "n": 70, "w": 10, "e": 110},
        "C": {"s": 20, "n": 80, "w": 10, "e": 130},
        "D": {"s": 70, "n": 90, "w": 10, "e": 130},
    }
    ids = {}
    for key, extent in extents.items():
        tools.g_region(**extent, res=10)
        ids[key] = f"{prefix}_{key}"
        tools.r_mapcalc(expression=f"{ids[key]} = 1")
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    name = f"{prefix}_ds"
    tools.t_create(output=name, title="t", description="d")
    file = register_file(
        tmp_path / "maps.txt",
        [
            (ids["A"], "1990-06-01", "1990-06-05"),
            (ids["B"], "1990-06-05", "1990-06-18"),
            (ids["C"], "1990-06-10", "1990-06-13"),
            (ids["D"], "1990-06-16", "1990-06-20"),
        ],
    )
    tools.t_register(input=name, file=file)

    result = tools.t_topology(input=name, flags="s")

    listing = _blocks(result.stdout)

    def at(key):
        return f"{ids[key]}@PERMANENT"

    blocks = {
        key: {k: v for k, v in listing[at(key)].items() if k in SPATIAL} for key in ids
    }
    assert blocks == {
        "A": {"Contain": [at("B")]},
        "B": {"In": [at("A")], "Covered": [at("C")], "Meet": [at("D")]},
        "C": {"Cover": [at("B")]},
        "D": {"Meet": [at("B")]},
    }


def _without(blocks, labels):
    return {
        map_id: {k: v for k, v in block.items() if k not in labels}
        for map_id, block in blocks.items()
    }


def test_a_map_stored_with_its_end_before_its_start(tools, nested):
    """Registering refuses such a map, but a database edited by hand holds one

    Reading the dataset reports the map and leaves it without time; it gets
    no relations, and the other maps are related as without it. The summary
    leaves it out of the granularity.
    """
    name, ids = nested
    tools.db_execute(
        driver="sqlite",
        database="$GISDBASE/$LOCATION_NAME/PERMANENT/tgis/sqlite.db",
        sql="UPDATE raster_absolute_time SET end_time = '2001-01-01 00:00:00'"
        f" WHERE id = '{ids['b']}'",
    )

    result = tools.t_topology(input=name, flags="m")

    assert result.returncode == 0
    assert f"<{ids['b']}>" in result.stderr
    assert "Traceback" not in result.stderr
    blocks = _blocks(result.stdout)
    expected = _blocks(
        tools.t_topology(input=name, flags="m", where=f"id != '{ids['b']}'").stdout
    )
    # The map without time comes last in the order of the maps and has no
    # neighbour; the chain of the others runs past it.
    assert all(_without(expected, {"Next", "Previous"}).values())
    assert list(blocks) == [ids["a"], ids["c"], ids["b"]]
    assert blocks == {**expected, ids["b"]: {}}

    summary = tools.t_topology(input=name)

    assert summary.returncode == 0
    assert f"<{ids['b']}>" in summary.stderr
    assert "Traceback" not in summary.stderr


SPATIAL = {"Equivalent", "Cover", "Covered", "Overlap", "In", "Contain", "Meet"}


def test_an_unknown_dataset_is_refused(tools):
    with pytest.raises(
        ToolError, match=r"Space\s+time\s+dataset\s+<nope>\s+of\s+type\s+<strds>"
    ):
        tools.t_topology(input="nope")


def test_the_input_is_required(tools):
    with pytest.raises(ToolError, match=r"Required\s+parameter\s+<input>\s+not\s+set"):
        tools.t_topology()


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_each_dataset_type(tools, make_stds, stds_type):
    # Three one-day maps that touch: two follows and two precedes, no gap.
    _, (name,) = make_stds(3, stds_type=stds_type)

    result = tools.t_topology(type=stds_type, input=name)

    text = result.stdout
    assert "Temporal topology is: ...... valid" in text
    assert "Number of intervals: ....... 3" in text
    assert "Number of gaps: ............ 0" in text
    assert "Granularity: ............... 1 day" in text
    assert "Follows: ................... 2" in text
    assert "Precedes: .................. 2" in text


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("stds_type", ["strds", "str3ds"])
def test_s_for_maps_of_one_extent(tools, make_stds, stds_type):
    # Raster maps and 3D raster maps of the same region are equivalent in 2D
    # (strds) and in 3D (str3ds).
    maps, (name,) = make_stds(3, stds_type=stds_type)

    result = tools.t_topology(type=stds_type, input=name, flags="s")

    blocks = _blocks(result.stdout)
    ids = [f"{m}@PERMANENT" for m in maps]
    assert [blocks[i]["Equivalent"] for i in ids] == [
        [ids[1]],
        [ids[0], ids[2]],
        [ids[1]],
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_s_for_vector_maps_that_do_not_touch(tools, make_stds):
    # The points (1,1), (2,2), (3,3) are disjoint, which is not listed.
    maps, (name,) = make_stds(3, stds_type="stvds")

    result = tools.t_topology(type="stvds", input=name, flags="s")

    blocks = _blocks(result.stdout)
    assert all(not SPATIAL & blocks[f"{m}@PERMANENT"].keys() for m in maps)


def _topology_refused(tools, name, **options):
    with pytest.raises(ToolError) as error:
        tools.t_topology(input=name, **options)
    return error.value.stderr


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, nested):
    text = _topology_refused(tools, nested[0], where="nonsense =")

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
