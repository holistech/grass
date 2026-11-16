"""Test t.topology on space time datasets with a time zone offset

The three maps of register_three_days last one day each at +01:00, so each ends where
the next begins, as without offset: the topology is valid, with two maps that
follow and two that precede.
"""

import re

import pytest


@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_a_dataset_with_an_offset_has_a_valid_topology(
    tools, register_three_days, stds_type
):
    _maps, name = register_three_days("z", stds_type=stds_type)

    text = tools.t_topology(type=stds_type, input=name).stdout

    assert re.search(r"Temporal topology is: \.+ valid$", text, re.MULTILINE)
    assert re.search(r"Follows: \.+ 2$", text, re.MULTILINE)
    assert re.search(r"Precedes: \.+ 2$", text, re.MULTILINE)
