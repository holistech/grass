"""Test t.vect.algebra on space time datasets with a time zone offset

Each map of register_three_days lasts one day at +01:00 and is equal only to itself,
so "Z : Z" gives three maps with the times of Z.
"""


def test_a_dataset_with_an_offset_selects_itself(tools, register_three_days):
    _maps, name = register_three_days("z", stds_type="stvds")

    tools.t_vect_algebra(expression=f"W = {name} : {name}", basename="w")

    rows = tools.t_vect_list(input="W", columns="start_time,end_time").stdout
    assert rows.splitlines()[1:] == [
        "2001-01-01 00:00:00+01:00|2001-01-02 00:00:00+01:00",
        "2001-01-02 00:00:00+01:00|2001-01-03 00:00:00+01:00",
        "2001-01-03 00:00:00+01:00|2001-01-04 00:00:00+01:00",
    ]


def test_a_dataset_with_an_offset_and_one_without_are_refused(
    register_three_days, refusal_of, mixed_zones_message
):
    zoned, with_offset = register_three_days("z", stds_type="stvds")
    naive, without = register_three_days("a", stds_type="stvds", offset="")

    text = refusal_of(
        "t.vect.algebra", expression=f"S = {without} : {with_offset}", basename="s"
    )

    assert mixed_zones_message(f"{zoned[0]}@PERMANENT", f"{naive[0]}@PERMANENT") in text
