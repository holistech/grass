"""Test t.register with vector maps: time options and layers

The maps come from vector_points(): two points with one attribute column.
Layer maps have the same categories in layers 1 to 3, each with its own table,
and are registered as name:layer.
"""

import pytest

from grass.temporal.testing.data import register_file, vector_points
from grass.temporal.testing.readback import list_maps, stds_info
from grass.tools import ToolError

# Almost every test of the module runs longer than one second (measured
# 18.10.2026 with pytest --durations).
pytestmark = pytest.mark.slow


def _make(tools, prefix, count, layers=(1,)):
    names = []
    for number in range(1, count + 1):
        name = f"{prefix}_{number}"
        vector_points(
            tools,
            name,
            [(number, number), (number + 1, number)],
            attributes={"height": [number, number * 10]},
            layers=layers,
        )
        names.append(name)
    return names


def _layers(tools, name):
    """(name, layer, start, end) of the registered maps of the dataset"""
    result = tools.t_vect_list(
        input=name, columns="name,layer,start_time,end_time", format="json"
    )
    return [
        (row["name"], row["layer"], row["start_time"], row["end_time"])
        for row in result.json["data"]
    ]


@pytest.mark.parametrize(
    ("increment", "interval", "times", "granularity"),
    [
        # Intervals of 1 second.
        (
            "1 seconds",
            True,
            [
                ("2001-01-01 00:00:00", "2001-01-01 00:00:01"),
                ("2001-01-01 00:00:01", "2001-01-01 00:00:02"),
                ("2001-01-01 00:00:02", "2001-01-01 00:00:03"),
            ],
            "1 second",
        ),
        # Time points every 3 days: Jan 1, 4, 7.
        (
            "3 days",
            False,
            [
                ("2001-01-01 00:00:00", None),
                ("2001-01-04 00:00:00", None),
                ("2001-01-07 00:00:00", None),
            ],
            "3 days",
        ),
        # Intervals of 2 months: Jan 1 to Mar 1, Mar 1 to May 1, May 1 to Jul 1.
        (
            "2 months",
            True,
            [
                ("2001-01-01 00:00:00", "2001-03-01 00:00:00"),
                ("2001-03-01 00:00:00", "2001-05-01 00:00:00"),
                ("2001-05-01 00:00:00", "2001-07-01 00:00:00"),
            ],
            "2 months",
        ),
    ],
    ids=["seconds", "days_as_points", "months_as_intervals"],
)
def test_start_and_increment(
    tools, prefix, dataset, increment, interval, times, granularity
):
    maps = _make(tools, prefix, 3)
    name = dataset(stds_type="stvds")

    tools.t_register(
        type="vector",
        input=name,
        maps=",".join(maps),
        start="2001-01-01",
        increment=increment,
        flags="i" if interval else "",
    )

    rows = list_maps(tools, "stvds", name)
    assert [(row.name, row.start, row.end) for row in rows] == [
        (map_name, *time) for map_name, time in zip(maps, times, strict=True)
    ]
    info = stds_info(tools, "stvds", name)
    assert info["number_of_maps"] == 3
    assert info["granularity"] == f"'{granularity}'"


def test_vector_time_is_written_to_the_map(tools, prefix, dataset):
    maps = _make(tools, prefix, 1)
    name = dataset(stds_type="stvds")

    tools.t_register(
        type="vector",
        input=name,
        maps=maps[0],
        start="2001-01-01 10:00:00",
        end="2001-01-02",
    )

    assert tools.v_timestamp(map=maps[0]).stdout.strip() == (
        "1 Jan 2001 10:00:00 / 2 Jan 2001 00:00:00"
    )


def test_relative_time(tools, prefix, dataset):
    maps = _make(tools, prefix, 2)
    name = dataset(stds_type="stvds", temporaltype="relative")

    tools.t_register(
        type="vector",
        input=name,
        maps=",".join(maps),
        start=0,
        increment=7,
        unit="days",
        flags="i",
    )

    assert [(row.start, row.end) for row in list_maps(tools, "stvds", name)] == [
        (0, 7),
        (7, 14),
    ]


def test_layers_with_start_and_increment(tools, prefix, dataset):
    # Layers of one map are registered one by one, each with its own time.
    (map_name,) = _make(tools, prefix, 1, layers=(1, 2, 3))
    name = dataset(stds_type="stvds")

    tools.t_register(
        type="vector",
        input=name,
        maps=",".join(f"{map_name}:{layer}" for layer in (1, 2, 3)),
        start="2001-01-01",
        increment="1 months",
        flags="i",
    )

    assert _layers(tools, name) == [
        (map_name, "1", "2001-01-01 00:00:00", "2001-02-01 00:00:00"),
        (map_name, "2", "2001-02-01 00:00:00", "2001-03-01 00:00:00"),
        (map_name, "3", "2001-03-01 00:00:00", "2001-04-01 00:00:00"),
    ]
    assert stds_info(tools, "stvds", name)["number_of_maps"] == 3


def test_map_without_layer_is_not_a_layer(tools, prefix, dataset):
    # A map named without a layer is registered without one, next to its layer 1.
    (map_name,) = _make(tools, prefix, 1)
    name = dataset(stds_type="stvds")

    tools.t_register(
        type="vector",
        input=name,
        maps=f"{map_name}:1,{map_name}",
        start="2001-01-01",
        increment="1 days",
    )

    assert _layers(tools, name) == [
        (map_name, "1", "2001-01-01 00:00:00", None),
        (map_name, None, "2001-01-02 00:00:00", None),
    ]


def test_layers_in_a_file(tools, prefix, dataset, tmp_path):
    # Names only (with the start of the command line), then names with a
    # start, then names with start and end. The time belongs to the map, so
    # each dataset is read before the next registration changes it.
    (map_name,) = _make(tools, prefix, 1, layers=(1, 2, 3))
    layers = [f"{map_name}:{layer}" for layer in (1, 2, 3)]
    common = {"type": "vector", "overwrite": True}

    names_only = dataset(stds_type="stvds", suffix="_names")
    tools.t_register(
        input=names_only,
        file=register_file(tmp_path / "names.txt", layers),
        start="2001-01-01",
        increment="1 months",
        **common,
    )
    names_only_result = _layers(tools, names_only)
    starts = dataset(stds_type="stvds", suffix="_starts")
    tools.t_register(
        input=starts,
        file=register_file(
            tmp_path / "starts.txt",
            [
                (layers[0], "2002-01-01"),
                (layers[1], "2002-02-01"),
                (layers[2], "2002-03-01"),
            ],
        ),
        **common,
    )
    starts_result = _layers(tools, starts)
    intervals = dataset(stds_type="stvds", suffix="_intervals")
    tools.t_register(
        input=intervals,
        file=register_file(
            tmp_path / "intervals.txt",
            [
                (layers[0], "2001-01-01", "2001-04-01"),
                (layers[1], "2001-04-01", "2001-07-01"),
                (layers[2], "2001-07-01", "2001-10-01"),
            ],
        ),
        **common,
    )

    assert names_only_result == [
        (map_name, "1", "2001-01-01 00:00:00", None),
        (map_name, "2", "2001-02-01 00:00:00", None),
        (map_name, "3", "2001-03-01 00:00:00", None),
    ]
    # Other times than the first round, so a file whose times were ignored
    # would show.
    assert starts_result == [
        (map_name, "1", "2002-01-01 00:00:00", None),
        (map_name, "2", "2002-02-01 00:00:00", None),
        (map_name, "3", "2002-03-01 00:00:00", None),
    ]
    assert _layers(tools, intervals) == [
        (map_name, "1", "2001-01-01 00:00:00", "2001-04-01 00:00:00"),
        (map_name, "2", "2001-04-01 00:00:00", "2001-07-01 00:00:00"),
        (map_name, "3", "2001-07-01 00:00:00", "2001-10-01 00:00:00"),
    ]


def test_a_layer_the_map_does_not_have_is_refused(tools, prefix, dataset):
    (map_name,) = _make(tools, prefix, 1)
    name = dataset(stds_type="stvds")

    with pytest.raises(ToolError, match="layer"):
        tools.t_register(
            type="vector", input=name, maps=f"{map_name}:7", start="2001-01-01"
        )


def test_a_layer_that_is_no_number_is_refused_with_a_message(tools, prefix, dataset):
    (map_name,) = _make(tools, prefix, 1)
    name = dataset(stds_type="stvds")

    with pytest.raises(ToolError) as error:
        tools.t_register(
            type="vector", input=name, maps=f"{map_name}:abc", start="2001-01-01"
        )

    # The messenger wraps long lines.
    text = " ".join(str(error.value).split())
    assert "The layer <abc> is no integer." in text
    assert "Traceback" not in text


def test_a_layer_with_categories_but_no_table_is_registered(tools, prefix, dataset):
    # v.category adds categories in layer 2 without a database link for it.
    (map_name,) = _make(tools, prefix, 1)
    tools.v_category(input=map_name, output=f"{map_name}_l2", option="add", layer=2)
    name = dataset(stds_type="stvds")

    tools.t_register(
        type="vector", input=name, maps=f"{map_name}_l2:2", start="2001-01-01"
    )

    assert [row[:2] for row in _layers(tools, name)] == [(f"{map_name}_l2", "2")]


def test_vector_without_time_needs_a_start(tools, prefix, dataset):
    (map_name,) = _make(tools, prefix, 1)
    name = dataset(stds_type="stvds")

    with pytest.raises(ToolError, match=r"has\s+no\s+timestamp"):
        tools.t_register(type="vector", input=name, maps=map_name)
