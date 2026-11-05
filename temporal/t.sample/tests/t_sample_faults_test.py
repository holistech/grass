"""Test the gap rows, the refusals, the method start and the separator of t.sample

A gap is time that no sampler map covers: a map that ends inside a longer one
leaves no gap behind it. Of g_1 1 to 11 January, g_2 3 to 5 January, g_3 8 to
13 January and g_4 15 to 16 January only 13 to 15 January is a gap.

A sampler that cannot sample ends the run with an error, the method start
selects a map of the same time as the granule, and the description of the
separator says what the tool does with it.
"""

import xml.etree.ElementTree as ET
from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, message
from grass.tools import ToolError

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


def refused(tools, **options):
    """The message of a refused run, after checking that it left nothing"""
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_sample(**options)
    assert inventory(tools) == before
    return message(error.value)


def test_sampler_of_instants_fails(tools, prefix):
    """A sampler of time instants has no granules: an error, not a message"""
    create_stds(
        tools,
        "strds",
        f"{prefix}_inst",
        [MapSpec(f"{prefix}_i{k}", k, D(2026, 1, k)) for k in (1, 2, 3)],
    )
    text = refused(tools, inputs=f"{prefix}_inst", sample=f"{prefix}_inst", flags="c")
    assert "The temporal map type of the sample dataset must be interval" in text
    assert text.count("ERROR") == 1
    assert "No samples found" not in text


def test_sampler_of_another_temporal_type_fails(tools, prefix):
    """An input of relative time cannot be sampled by absolute time"""
    create_stds(
        tools,
        "strds",
        f"{prefix}_samp",
        [MapSpec(f"{prefix}_s1", 1, D(2026, 1, 1), D(2026, 1, 3))],
    )
    create_stds(
        tools,
        "strds",
        f"{prefix}_rel",
        [MapSpec(f"{prefix}_r1", 1, 0, 2)],
        temporaltype="relative",
        unit="days",
    )
    text = refused(tools, inputs=f"{prefix}_rel", sample=f"{prefix}_samp")
    assert "The space time datasets must be of the same temporal type" in text
    assert text.count("ERROR") == 1


def test_method_start_keeps_equal_maps(tools, prefix):
    """The input map with the time of the granule is listed, as by equal"""
    create_stds(
        tools,
        "strds",
        f"{prefix}_samp",
        [MapSpec(f"{prefix}_s1", 1, D(2026, 1, 1), D(2026, 1, 3))],
    )
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_e1", 1, D(2026, 1, 1), D(2026, 1, 3))],
    )
    rows = {
        method: tools.t_sample(
            inputs=f"{prefix}_in", sample=f"{prefix}_samp", method=method
        ).stdout.split("|")[:2]
        for method in ("start", "equal")
    }
    assert rows["start"] == [f"{prefix}_s1@PERMANENT", f"{prefix}_e1@PERMANENT"]
    assert rows["start"] == rows["equal"]


def option_description(tools, tool, key):
    """The label and the description of an option in --interface-description"""
    root = ET.fromstring(tools.call_cmd([tool, "--interface-description"]).stdout)
    parameter = root.find(f"parameter[@name='{key}']")
    return " ".join(
        (parameter.findtext(tag) or "").strip() for tag in ("label", "description")
    )


def test_option_descriptions_match_behaviour(tools, prefix):
    """The default pipe prints "|", and a comma is replaced by a padded pipe"""
    text = option_description(tools, "t.sample", "separator")
    assert "default" not in text
    assert 'a separator with a comma is replaced by " | "' in text
    create_stds(
        tools,
        "strds",
        f"{prefix}_samp",
        [MapSpec(f"{prefix}_s1", 1, D(2026, 1, 1), D(2026, 1, 3))],
    )
    run = {
        separator: tools.t_sample(
            inputs=f"{prefix}_samp", sample=f"{prefix}_samp", separator=separator
        ).stdout
        for separator in ("pipe", "comma")
    }
    assert run["pipe"].startswith(f"{prefix}_s1@PERMANENT|{prefix}_s1@PERMANENT|")
    assert run["comma"].startswith(f"{prefix}_s1@PERMANENT | {prefix}_s1@PERMANENT | ")
