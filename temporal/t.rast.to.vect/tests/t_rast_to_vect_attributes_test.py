"""Test the attribute tables and the topology of the maps of t.rast.to.vect

The first map of the dataset holds 10 in its first column and 20 in the other
six cells, so its nine points carry three times 10 and six times 20.
"""

from pathlib import Path

import pytest

from grass.temporal.testing.readback import list_maps
from grass.tools import ToolError

FIRST_DAY = "start_time < '2001-01-02'"


def _first(tools, name):
    return list_maps(tools, "stvds", name)[0].name


def _rows(tools, name, **options):
    lines = tools.v_db_select(map=name, **options).stdout.splitlines()
    return lines[0], [line.split("|") for line in lines[1:]]


def _convert(tools, shapes, prefix, **options):
    tools.t_rast_to_vect(
        input=shapes,
        output=prefix,
        basename=prefix,
        type="point",
        where=FIRST_DAY,
        **options,
    )
    return _first(tools, prefix)


def test_the_table_holds_a_sequence_and_the_raster_value(tools, shapes, prefix):
    name = _convert(tools, shapes, prefix)

    header, rows = _rows(tools, name)
    assert header == "cat|value|label"
    assert sorted(int(row[0]) for row in rows) == list(range(1, 10))
    assert sorted(int(row[1]) for row in rows) == [10] * 3 + [20] * 6


def test_column_names_the_value_column(tools, shapes, prefix):
    name = _convert(tools, shapes, prefix, column="height")

    header, rows = _rows(tools, name)
    assert header == "cat|height|label"
    assert sorted(int(row[1]) for row in rows) == [10] * 3 + [20] * 6


def test_the_v_flag_uses_the_raster_values_as_categories(tools, shapes, prefix):
    name = _convert(tools, shapes, prefix, flags="v")

    header, rows = _rows(tools, name)
    # One category per value instead of one per point, and no value column
    assert header == "cat|label"
    assert sorted(int(row[0]) for row in rows) == [10, 20]


def test_the_z_flag_makes_no_table(tools, shapes, prefix):
    name = _convert(tools, shapes, prefix, flags="z")

    assert tools.v_db_connect(map=name, flags="p").stdout.strip() == ""


def test_the_t_flag_makes_no_table(tools, shapes, prefix):
    name = _convert(tools, shapes, prefix, flags="t")

    assert tools.v_db_connect(map=name, flags="p").stdout.strip() == ""


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_b_flag_leaves_out_the_topology_but_keeps_the_table(tools, shapes, prefix):
    with_topology = _convert(tools, shapes, f"{prefix}_a")
    without_topology = _convert(tools, shapes, f"{prefix}_b", flags="b")

    def files(name):
        path = tools.g_findfile(element="vector", file=name).keyval["file"]
        return {item.name for item in Path(path.strip("'")).iterdir()}

    assert {"topo", "sidx", "cidx"} <= files(with_topology)
    assert files(without_topology).isdisjoint({"topo", "sidx", "cidx"})
    assert len(_rows(tools, without_topology)[1]) == 9


def test_today_a_column_that_is_no_sql_name_ends_with_a_traceback(
    tools, shapes, prefix
):
    with pytest.raises(ToolError) as error:
        _convert(tools, shapes, prefix, column="1x")

    assert "Traceback" in str(error.value)
