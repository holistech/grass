"""Test t.rast.algebra on space time datasets with a time zone offset

The maps of register_three_days hold 1, 2 and 3 and last one day each at +01:00.
In "Z + Z" each map is equal only to itself, so the result has three maps
with the times of Z and the values 2, 4 and 6.
"""


def test_a_dataset_with_an_offset_is_added_to_itself(tools, register_three_days):
    _maps, name = register_three_days("z", stds_type="strds")

    tools.t_rast_algebra(expression=f"R = {name} + {name}", basename="r")

    rows = tools.t_rast_list(input="R", columns="start_time,end_time,min").stdout
    assert rows.splitlines()[1:] == [
        "2001-01-01 00:00:00+01:00|2001-01-02 00:00:00+01:00|2.0",
        "2001-01-02 00:00:00+01:00|2001-01-03 00:00:00+01:00|4.0",
        "2001-01-03 00:00:00+01:00|2001-01-04 00:00:00+01:00|6.0",
    ]


def test_a_dataset_with_an_offset_and_one_without_are_refused(
    register_three_days, refusal_of, mixed_zones_message
):
    zoned, with_offset = register_three_days("z", stds_type="strds")
    naive, without = register_three_days("a", stds_type="strds", offset="")

    text = refusal_of(
        "t.rast.algebra", expression=f"S = {without} : {with_offset}", basename="s"
    )

    assert mixed_zones_message(f"{zoned[0]}@PERMANENT", f"{naive[0]}@PERMANENT") in text
