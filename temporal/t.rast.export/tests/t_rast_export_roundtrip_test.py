"""Test that t.rast.import gives back what t.rast.export wrote

The dataset of conftest.py is exported with every format and compression and
imported again under a new basename. The maps, their times and the value of
every cell must be those of the original; the cells are derived in conftest.py.
-o skips the check of the projection, because the project is unprojected.
"""

import pytest

from grass.temporal.testing.readback import cell_values, list_maps, stds_info

# The cells of the maps, row by row (conftest.py)
VALUES = {
    "ex_a": [10.0] * 6,
    "ex_b": [1.5, 2.5, 2.5, 1.5, 2.5, 2.5],
    "ex_c": [None, None, 7.0, None, None, 7.0],
}
# Every test takes more than a second (measured 18.10.2026 with a serial
# pytest --durations=0).
pytestmark = pytest.mark.slow

FORMATS = [
    ("GTiff", "bzip2"),
    ("GTiff", "gzip"),
    ("GTiff", "no"),
    ("AAIGrid", "no"),
    ("pack", "no"),
    ("pack", "gzip"),
]
TIMES = [
    ("2001-01-01 00:00:00", "2001-02-01 00:00:00"),
    ("2001-02-01 00:00:00", "2001-03-01 00:00:00"),
    ("2001-03-01 00:00:00", "2001-04-01 00:00:00"),
]


def _round_trip(tools, dataset, tmp_path, prefix, **options):
    archive = tmp_path / "out"
    tools.t_rast_export(input=dataset, output=str(archive), **options)
    tools.t_rast_import(
        input=str(archive),
        output=prefix,
        basename=prefix,
        directory=str(tmp_path),
        flags="o",
    )
    return list_maps(tools, "strds", prefix)


@pytest.mark.parametrize(("fmt", "compression"), FORMATS)
def test_the_maps_come_back_with_their_times_and_values(
    tools, absolute, tmp_path, prefix, fmt, compression
):
    rows = _round_trip(
        tools, absolute, tmp_path, prefix, format=fmt, compression=compression
    )

    assert [(row.start, row.end) for row in rows] == TIMES
    assert [cell_values(tools, row.name) for row in rows] == [
        VALUES["ex_a"],
        VALUES["ex_b"],
        VALUES["ex_c"],
    ]


def test_the_value_range_comes_back(tools, absolute, tmp_path, prefix):
    rows = _round_trip(tools, absolute, tmp_path, prefix, compression="no")

    assert [(row.min, row.max) for row in rows] == [(10, 10), (1.5, 2.5), (7, 7)]


# A nodata value outside the range of the type that holds the cells (10 and 7)
@pytest.mark.parametrize(
    ("data_type", "nodata"),
    [
        ("Byte", 255),
        ("Int16", -9),
        ("UInt16", 65535),
        ("Int32", -9),
        ("Float32", -9),
    ],
)
def test_an_integer_map_survives_every_type(
    tools, absolute, tmp_path, prefix, data_type, nodata
):
    rows = _round_trip(
        tools,
        absolute,
        tmp_path,
        prefix,
        type=data_type,
        compression="no",
        nodata=nodata,
        where="start_time < '2001-02-01' or start_time >= '2001-03-01'",
    )

    assert [cell_values(tools, row.name) for row in rows] == [
        VALUES["ex_a"],
        VALUES["ex_c"],
    ]


def test_the_relative_time_comes_back(tools, relative, tmp_path, prefix):
    rows = _round_trip(tools, relative, tmp_path, prefix, compression="no")

    info = stds_info(tools, "strds", prefix)
    assert info["temporal_type"] == "relative"
    assert [(row.start, row.end) for row in rows] == [(1, 2), (2, 3)]
    assert [cell_values(tools, row.name) for row in rows] == [[3.0] * 6, [4.0] * 6]
