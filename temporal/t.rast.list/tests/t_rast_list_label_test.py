"""Test that reading tools still select maps by the semantic label"""

from grass.temporal.testing.readback import list_maps


def test_reading_tools_filter_by_label(tools, labelled):
    selected = f"{labelled.name}.S2_1"

    listed = [row.name for row in list_maps(tools, "strds", selected)]
    univar = tools.t_rast_univar(input=selected, format="json").json

    assert listed == labelled.maps[:2]
    assert [record["id"].split("@")[0] for record in univar] == labelled.maps[:2]
