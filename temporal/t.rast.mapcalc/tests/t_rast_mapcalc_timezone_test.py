"""Test t.rast.mapcalc on space time datasets with a time zone offset"""


def test_a_dataset_with_an_offset_and_one_without_are_refused(
    register_three_days, refusal_of, mixed_zones_message
):
    zoned, with_offset = register_three_days("z")
    naive, without = register_three_days("a", offset="")

    text = refusal_of(
        "t.rast.mapcalc",
        inputs=f"{with_offset},{without}",
        expression=f"N = {with_offset} + {without}",
        output="N",
        basename="n",
    )

    assert mixed_zones_message(f"{zoned[0]}@PERMANENT", f"{naive[0]}@PERMANENT") in text
