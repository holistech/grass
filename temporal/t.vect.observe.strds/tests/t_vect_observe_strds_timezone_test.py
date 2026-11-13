"""Test t.vect.observe.strds on space time datasets with a time zone offset"""

from grass.temporal.testing.data import make_map


def test_datasets_with_an_offset_and_without_are_refused(
    tools, prefix, register_three_days, refusal_of, mixed_zones_message
):
    zoned, with_offset = register_three_days("z")
    naive, without = register_three_days("a", offset="")
    make_map(tools, "vector", f"{prefix}_points", 1)

    text = refusal_of(
        "t.vect.observe.strds",
        input=f"{prefix}_points",
        strds=f"{with_offset},{without}",
        output=f"{prefix}_out",
        vector_output=f"{prefix}_out",
        columns="v,w",
    )

    assert mixed_zones_message(f"{zoned[0]}@PERMANENT", f"{naive[0]}@PERMANENT") in text
