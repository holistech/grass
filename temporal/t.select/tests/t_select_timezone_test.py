"""Test t.select on space time datasets with a time zone offset

Each map of register_three_days is equal to itself and to no other map of the dataset,
so "Z : Z" selects all three maps with their times.
"""

import pytest


@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_a_dataset_with_an_offset_selects_itself(tools, register_three_days, stds_type):
    maps, name = register_three_days("z", stds_type=stds_type)

    tools.t_select(type=stds_type, expression=f"{name}_s = {name} : {name}")

    listed = tools.run(
        {"strds": "t.rast.list", "str3ds": "t.rast3d.list", "stvds": "t.vect.list"}[
            stds_type
        ],
        input=f"{name}_s",
        columns="name,start_time,end_time",
    )
    assert listed.stdout.splitlines()[1:] == [
        f"{maps[0]}|2001-01-01 00:00:00+01:00|2001-01-02 00:00:00+01:00",
        f"{maps[1]}|2001-01-02 00:00:00+01:00|2001-01-03 00:00:00+01:00",
        f"{maps[2]}|2001-01-03 00:00:00+01:00|2001-01-04 00:00:00+01:00",
    ]


def test_a_dataset_with_an_offset_and_one_without_are_refused(
    register_three_days, refusal_of, mixed_zones_message
):
    zoned, with_offset = register_three_days("z")
    naive, without = register_three_days("a", offset="")

    text = refusal_of("t.select", expression=f"S = {without} : {with_offset}")

    assert mixed_zones_message(f"{zoned[0]}@PERMANENT", f"{naive[0]}@PERMANENT") in text
