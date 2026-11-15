"""Test that t.rast.colors still takes a dataset name with a semantic label

The tool writes colour tables of the maps and not of the dataset, so the label
selects the maps that are coloured.
"""


def _rules(tools, name):
    return tools.r_colors_out(map=name).stdout


def test_colors_still_takes_a_label(tools, labelled):
    before = [_rules(tools, name) for name in labelled.maps]

    tools.t_rast_colors(input=f"{labelled.name}.S2_1", color="ryb")

    after = [_rules(tools, name) for name in labelled.maps]
    assert after[0] != before[0]
    assert after[1] != before[1]
    assert after[2:] == before[2:]
