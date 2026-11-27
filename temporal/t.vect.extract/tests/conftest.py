"""Datasets for the tests of t.vect.extract

The dataset ve_quarterly has six point maps vq_1 to vq_6 of three months from
2001-01-01. Map k has four points at (k, 1) to (k, 4) with the columns
value = 10 k + i (11 to 14, 21 to 24, ...) and height = 1.5 i for point i.

The dataset ve_layers has two maps with two layers each, the four layers
one after the other in quarters. In layer 1 the
column value holds 1 and 2, in layer 2 (table vl_k_2) 101 and 102, so that a
condition on value tells the layers apart.
"""

import pytest

from grass.temporal.testing.data import MapSpec, quarter, register_stds, vector_points


@pytest.fixture(scope="module")
def quarterly(tools):
    """The name of the dataset described above"""
    for k in range(1, 7):
        vector_points(
            tools,
            f"vq_{k}",
            [(k, i) for i in range(1, 5)],
            attributes={
                "value": [10 * k + i for i in range(1, 5)],
                "height": [1.5 * i for i in range(1, 5)],
            },
        )
    register_stds(
        tools,
        "stvds",
        "ve_quarterly",
        [MapSpec(f"vq_{k + 1}", None, quarter(k), quarter(k + 1)) for k in range(6)],
    )
    return "ve_quarterly"


@pytest.fixture(scope="module")
def layered(tools):
    """The name of the dataset ve_layers, registered as vl_k:1 and vl_k:2"""
    names = []
    for k in (1, 2):
        vector_points(
            tools,
            f"vl_{k}",
            [(k, 1), (k, 2)],
            attributes={"value": [1, 2]},
            layers=(1, 2),
        )
        tools.db_execute(sql=f"UPDATE vl_{k}_2 SET value = value + 100")
        names += [f"vl_{k}:1", f"vl_{k}:2"]
    register_stds(
        tools,
        "stvds",
        "ve_layers",
        [
            MapSpec(name, None, quarter(k), quarter(k + 1))
            for k, name in enumerate(names)
        ],
    )
    return "ve_layers"


@pytest.fixture(scope="module")
def plain_layers(tools):
    """Dataset ve_plain: two maps with two layers each, registered without a
    layer (vp_k); layer 1 holds value 1 and 2, layer 2 holds 101 and 102"""
    for k in (1, 2):
        vector_points(
            tools,
            f"vp_{k}",
            [(k, 1), (k, 2)],
            attributes={"value": [1, 2]},
            layers=(1, 2),
        )
        tools.db_execute(sql=f"UPDATE vp_{k}_2 SET value = value + 100")
    register_stds(
        tools,
        "stvds",
        "ve_plain",
        [MapSpec(f"vp_{k + 1}", None, quarter(k), quarter(k + 1)) for k in range(2)],
    )
    return "ve_plain"


@pytest.fixture(scope="module")
def same_time_layers(tools):
    """Dataset ve_same: one map vs_1 with the layers 1 and 2, both registered
    for the first quarter"""
    vector_points(
        tools, "vs_1", [(1, 1), (1, 2)], attributes={"value": [1, 2]}, layers=(1, 2)
    )
    tools.db_execute(sql="UPDATE vs_1_2 SET value = value + 100")
    register_stds(
        tools,
        "stvds",
        "ve_same",
        [MapSpec(f"vs_1:{layer}", None, quarter(0), quarter(1)) for layer in (1, 2)],
    )
    return "ve_same"
