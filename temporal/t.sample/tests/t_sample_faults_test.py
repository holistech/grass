"""Test the gap rows that t.sample lists for a sampler of overlapping maps

A gap is time that no sampler map covers: a map that ends inside a longer one
leaves no gap behind it. Of g_1 1 to 11 January, g_2 3 to 5 January, g_3 8 to
13 January and g_4 15 to 16 January only 13 to 15 January is a gap.
"""

from datetime import datetime

from grass.temporal.testing.data import MapSpec, create_stds

D = datetime


def test_gap_inside_longer_sampler_map_is_not_a_gap(tools):
    create_stds(
        tools,
        "strds",
        "sampler",
        [
            MapSpec("g_1", 1, D(2026, 1, 1), D(2026, 1, 11)),
            MapSpec("g_2", 2, D(2026, 1, 3), D(2026, 1, 5)),
            MapSpec("g_3", 3, D(2026, 1, 8), D(2026, 1, 13)),
            MapSpec("g_4", 4, D(2026, 1, 15), D(2026, 1, 16)),
        ],
    )
    create_stds(
        tools,
        "strds",
        "observed",
        [
            MapSpec("x_1", 1, D(2026, 1, 6), D(2026, 1, 7)),
            MapSpec("x_2", 2, D(2026, 1, 13), D(2026, 1, 14)),
        ],
    )
    result = tools.t_sample(
        inputs="observed", sample="sampler", method="contain,during,overlap,equal"
    )
    rows = [line.split("|")[:4] for line in result.stdout.splitlines()]
    assert rows == [
        [
            "g_1@PERMANENT",
            "x_1@PERMANENT",
            "2026-01-01 00:00:00",
            "2026-01-11 00:00:00",
        ],
        ["g_2@PERMANENT", "None", "2026-01-03 00:00:00", "2026-01-05 00:00:00"],
        ["g_3@PERMANENT", "None", "2026-01-08 00:00:00", "2026-01-13 00:00:00"],
        ["None", "x_2@PERMANENT", "2026-01-13 00:00:00", "2026-01-15 00:00:00"],
        ["g_4@PERMANENT", "None", "2026-01-15 00:00:00", "2026-01-16 00:00:00"],
    ]
