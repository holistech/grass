"""Test the units, the sampling of instants and the quantile of t.vect.what.strds

The data are described in conftest.py.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import message
from grass.tools import ToolError

# Most tests take more than a second (measured 19.10.2026 with a serial
# pytest --durations=0): every test makes its own vector maps.
pytestmark = pytest.mark.slow

# The cells of the points in the raster maps: 10 row + col
CELLS = [11, 12, 21, 22]


def _column(tools, vector, column):
    text = tools.v_db_select(map=vector, columns=column, flags="c").stdout
    return text.splitlines()


def test_different_relative_units_are_refused(tools, rasters, vectors, prefix):
    # The numbers of the raster maps are minutes, those of the vector maps
    # hours: read as the same unit they select other maps.
    data = vectors([(0, 2)], temporaltype="relative", unit="hours")

    with pytest.raises(ToolError) as error:
        tools.t_vect_what_strds(input=data.dataset, strds="wh_rel")

    text = message(error.value)
    assert (
        "The unit <minutes> of the space time raster dataset <wh_rel"
        f"@PERMANENT> differs from the unit <hours> of the space time vector "
        f"dataset <{data.dataset}"
    ) in text
    assert tools.db_columns(table=data.maps[0]).stdout.split() == [
        "x",
        "y",
        "cat",
        "h",
    ]


def test_the_same_relative_unit_is_accepted(tools, rasters, vectors):
    data = vectors([(0, 10)], temporaltype="relative", unit="minutes")

    result = tools.t_vect_what_strds(input=data.dataset, strds="wh_rel")

    assert "differs from the unit" not in message(result)


@pytest.mark.parametrize(
    ("quantile", "offset"), [(None, 50), (0.5, 50), (0.25, 25), (0, 0), (1, 100)]
)
def test_quantile_option(tools, rasters, vectors, quantile, offset):
    # The maps wr_3 and wr_4 lie in the second interval and hold 300 + cell
    # and 400 + cell. The quantile of two values by the rule of Hyndman and
    # Fan, type 7, lies q of the way from the first to the second.
    data = vectors()
    options = {} if quantile is None else {"quantile": quantile}

    tools.t_vect_what_strds(
        input=data.dataset,
        strds="wh_a",
        sampling="during",
        column="m",
        method="quantile",
        **options,
    )

    assert [float(value) for value in _column(tools, data.maps[1], "m")] == (
        pytest.approx([300 + cell + offset for cell in CELLS], abs=1e-5)
    )


@pytest.mark.parametrize("quantile", [-0.1, 1.5])
def test_the_quantile_must_lie_between_0_and_1(tools, rasters, vectors, quantile):
    data = vectors()

    with pytest.raises(ToolError) as error:
        tools.t_vect_what_strds(
            input=data.dataset, strds="wh_a", method="quantile", quantile=quantile
        )

    assert "<quantile>" in message(error.value)
    assert "out of range" in message(error.value)
    assert tools.db_columns(table=data.maps[1]).stdout.split() == [
        "x",
        "y",
        "cat",
        "h",
    ]


def test_instants_force_start_with_warning(tools, rasters, vectors, prefix):
    create_stds(
        tools,
        "strds",
        f"{prefix}_inst",
        [MapSpec(f"{prefix}_i{k}", 10 * k, datetime(2001, 5, 10 * k)) for k in (1, 2)],
    )
    data = vectors()

    result = tools.t_vect_what_strds(
        input=data.dataset, strds=f"{prefix}_inst", sampling="during,overlap"
    )

    text = message(result)
    assert (
        f"The maps of the space time raster dataset <{prefix}_inst@PERMANENT> are "
        "not all time intervals, so the sampling <during,overlap> is ignored and "
        "<start> is used"
    ) in text
    # The instants of May lie in the interval of the second map.
    assert tools.db_columns(table=data.maps[1]).stdout.split()[4:] == [
        f"{prefix}_i1",
        f"{prefix}_i2",
    ]


def test_instants_with_the_default_sampling_give_no_warning(
    tools, rasters, vectors, prefix
):
    create_stds(
        tools,
        "strds",
        f"{prefix}_inst",
        [MapSpec(f"{prefix}_i1", 10, datetime(2001, 5, 10))],
    )
    data = vectors()

    result = tools.t_vect_what_strds(input=data.dataset, strds=f"{prefix}_inst")

    assert "is ignored" not in message(result)
