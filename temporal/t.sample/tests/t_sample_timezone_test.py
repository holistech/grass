"""Test t.sample on space time datasets with a time zone offset

Sampled by itself, each map of register_three_days is equal to one granule only, the
one of its own time: the matrix pairs every map with itself.
"""


def test_a_dataset_with_an_offset_samples_itself(tools, register_three_days):
    maps, name = register_three_days("z")

    rows = tools.t_sample(input=name, sample=name).stdout.splitlines()

    days = ["2001-01-01", "2001-01-02", "2001-01-03", "2001-01-04"]
    assert rows == [
        f"{map_}@PERMANENT|{map_}@PERMANENT|{start} 00:00:00+01:00"
        f"|{end} 00:00:00+01:00|1.0|{float(number)}"
        for number, (map_, start, end) in enumerate(
            zip(maps, days[:-1], days[1:], strict=True)
        )
    ]


def test_a_dataset_with_an_offset_and_one_without_are_refused(
    register_three_days, refusal_of, mixed_zones_message
):
    zoned, with_offset = register_three_days("z")
    naive, without = register_three_days("a", offset="")

    text = refusal_of("t.sample", input=without, sample=with_offset)

    assert mixed_zones_message(f"{zoned[0]}@PERMANENT", f"{naive[0]}@PERMANENT") in text
