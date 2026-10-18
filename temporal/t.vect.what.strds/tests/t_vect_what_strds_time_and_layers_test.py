"""Test t.vect.what.strds with relative time and with layers

The data are described in conftest.py. The old script of the layer case
(test.t.vect.what.strds.layer.sh) gave a vector map six layers and registered
the layers as soils:1 to soils:6, one month each from 2001-03-01, and sampled a
dataset with one map of a whole year and another with six monthly maps.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    register_stds,
    vector_points,
)
from grass.temporal.testing.readback import stds_info

# Most tests take more than a second (measured 19.10.2026 with a serial
# pytest --durations=0): every test makes its own vector maps.
pytestmark = pytest.mark.slow

CELLS = [11, 12, 21, 22]
CENTRES = [(0.5, 1.5), (1.5, 1.5), (0.5, 0.5), (1.5, 0.5)]


def _column(tools, vector, column, layer=1):
    text = tools.v_db_select(map=vector, layer=layer, columns=column, flags="c").stdout
    return text.splitlines()


def _columns(tools, table):
    names = tools.db_columns(table=table).stdout.split()
    return [name for name in names if name not in {"x", "y", "cat", "h", "sand"}]


def test_relative_time_samples_the_maps_that_start_in_the_interval(
    tools, rasters, vectors
):
    # Intervals in minutes: 0 to 10, 12 to 17 and 20 to 30. The raster maps
    # wrr_k last five minutes from 5 (k - 1): wrr_1 and wrr_2 start in the
    # first interval, wrr_4 (starts at 15) in the second, wrr_5 and wrr_6
    # (20, 25) in the third.
    data = vectors(
        [(0, 10), (12, 17), (20, 30)], temporaltype="relative", unit="minutes"
    )

    tools.t_vect_what_strds(input=data.dataset, strds="wh_rel")

    names = [tools.db_columns(table=name).stdout.split()[4:] for name in data.maps]
    assert names == [["wrr_1", "wrr_2"], ["wrr_4"], ["wrr_5", "wrr_6"]]
    assert _column(tools, data.maps[1], "wrr_4") == [str(400 + cell) for cell in CELLS]


def test_relative_time_with_a_column_and_the_maximum(tools, rasters, vectors):
    data = vectors(
        [(0, 10), (12, 17), (20, 30)], temporaltype="relative", unit="minutes"
    )

    tools.t_vect_what_strds(
        input=data.dataset,
        strds="wh_rel",
        sampling="start,during",
        column="m",
        method="maximum",
    )

    # Interval 1: wrr_1 and wrr_2, the larger is wrr_2 (200 + cell). Interval 2:
    # wrr_4 alone. Interval 3: wrr_5 and wrr_6 -> wrr_6.
    assert [_column(tools, name, "m")[0] for name in data.maps] == ["211", "411", "611"]


def test_relative_time_with_the_average_during_the_interval(tools, rasters, vectors):
    data = vectors(
        [(0, 10), (12, 17), (20, 30)], temporaltype="relative", unit="minutes"
    )

    tools.t_vect_what_strds(
        input=data.dataset,
        strds="wh_rel",
        sampling="during",
        column="m",
        method="average",
    )

    # During 0 to 10: wrr_1 and wrr_2, mean 150 + cell. During 12 to 17: no
    # map (wrr_4 ends at 20), so the table gets no column. During 20 to 30:
    # wrr_5 and wrr_6, mean 550 + cell.
    assert _column(tools, data.maps[0], "m") == [str(150 + cell) for cell in CELLS]
    assert _columns(tools, data.maps[1]) == []
    assert _column(tools, data.maps[2], "m") == [str(550 + cell) for cell in CELLS]


def test_the_datasets_must_have_the_same_temporal_type(tools, rasters, vectors):
    from grass.temporal.testing.readback import message
    from grass.tools import ToolError

    data = vectors([(0, 10)], temporaltype="relative", unit="minutes")

    with pytest.raises(ToolError) as error:
        tools.t_vect_what_strds(input=data.dataset, strds="wh_a")

    assert "Input and aggregation dataset must have the same temporal type" in message(
        error.value
    )


def test_a_registered_layer_gets_the_column(tools, rasters, prefix):
    vector_points(
        tools, f"{prefix}_m", CENTRES, attributes={"h": [1, 2, 3, 4]}, layers=(1, 2)
    )
    register_stds(
        tools,
        "stvds",
        f"{prefix}_ds",
        [MapSpec(f"{prefix}_m:2", None, datetime(2001, 1, 1), datetime(2001, 4, 1))],
    )

    tools.t_vect_what_strds(input=f"{prefix}_ds", strds="wh_a", column="m")

    # The layer 2 table gets the column; the table of layer 1 is unchanged.
    assert _column(tools, f"{prefix}_m", "m", layer=2) == ["111", "112", "121", "122"]
    assert _columns(tools, f"{prefix}_m") == []


def test_the_layer_script_case(tools, prefix):
    # The case of test.t.vect.what.strds.layer.sh: a map with the layers 1 to 6
    # (the script took 100 random points; here four points at the centres of
    # the cells of a 2 x 2 region), registered as soils:1 to soils:6, one month
    # each from 2001-03-01.
    name = f"{prefix}_soils"
    vector_points(
        tools,
        name,
        CENTRES,
        attributes={"sand": [1, 2, 3, 4]},
        layers=(1, 2, 3, 4, 5, 6),
    )
    register_stds(
        tools,
        "stvds",
        f"{prefix}_soil_abs",
        [
            MapSpec(
                f"{name}:{k}", None, datetime(2001, k + 2, 1), datetime(2001, k + 3, 1)
            )
            for k in range(1, 7)
        ],
    )
    # One map of a whole year (value 50.0)
    create_stds(
        tools,
        "strds",
        f"{prefix}_year",
        [
            MapSpec(
                f"{prefix}_sand_frac",
                "50.0",
                datetime(2001, 1, 1),
                datetime(2002, 1, 1),
            )
        ],
    )
    # Six monthly maps with 25.0, 35.0 ... 75.0 (15 + 10 k for k = 1 to 6)
    create_stds(
        tools,
        "strds",
        f"{prefix}_months",
        [
            MapSpec(
                f"{prefix}_sand_frac_{k}",
                f"{15 + 10 * k}.0",
                datetime(2001, k + 2, 1),
                datetime(2001, k + 3, 1),
            )
            for k in range(1, 7)
        ],
    )

    tools.t_vect_what_strds(
        input=f"{prefix}_soil_abs",
        strds=f"{prefix}_year",
        sampling="overlap,during,contain",
        column="sand_frac",
    )

    # The year contains every month: each layer reads 50.0 in every point.
    for layer in range(1, 7):
        table = name if layer == 1 else f"{name}_{layer}"
        assert _columns(tools, table) == ["sand_frac"], layer
        assert _column(tools, name, "sand_frac", layer=layer) == ["50"] * 4, layer

    tools.t_vect_what_strds(
        input=f"{prefix}_soil_abs", strds=f"{prefix}_months", sampling="equal"
    )

    # The monthly map k equals the interval of layer k: only that layer gets the
    # column, with the value 15 + 10 k.
    for layer in range(1, 7):
        table = name if layer == 1 else f"{name}_{layer}"
        assert _columns(tools, table) == ["sand_frac", f"{prefix}_sand_frac_{layer}"], (
            layer
        )
        assert (
            _column(tools, name, f"{prefix}_sand_frac_{layer}", layer=layer)
            == [str(15 + 10 * layer)] * 4
        ), layer
    assert stds_info(tools, "stvds", f"{prefix}_soil_abs")["number_of_maps"] == 6


def test_where_applies_to_the_table_of_a_registered_layer(tools, rasters, prefix):
    vector_points(
        tools, f"{prefix}_m", CENTRES, attributes={"h": [1, 2, 3, 4]}, layers=(1, 2)
    )
    register_stds(
        tools,
        "stvds",
        f"{prefix}_ds",
        [MapSpec(f"{prefix}_m:2", None, datetime(2001, 1, 1), datetime(2001, 4, 1))],
    )

    tools.t_vect_what_strds(
        input=f"{prefix}_ds", strds="wh_a", column="m", where="cat > 2"
    )

    # The layer 2 table has the categories 1 to 4 as well: only p3 and p4 are read.
    assert _column(tools, f"{prefix}_m", "m", layer=2) == ["", "", "121", "122"]
