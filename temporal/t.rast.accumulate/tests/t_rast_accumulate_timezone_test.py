"""Test t.rast.accumulate on space time datasets with a time zone offset"""


def test_a_dataset_with_an_offset_is_accumulated(tools, register_three_days):
    """Cycles of two days from 2001-01-01 at +01:00: the first sums map 1 to
    1 and maps 1 and 2 to 3, the second starts again with map 3."""
    _maps, name = register_three_days("z")

    tools.t_rast_accumulate(
        input=name,
        output="AC",
        basename="ac",
        start="2001-01-01 00:00:00+01:00",
        cycle="2 days",
        limits="0,10",
    )

    rows = tools.t_rast_list(input="AC", columns="start_time,end_time,min").stdout
    assert rows.splitlines()[1:] == [
        "2001-01-01 00:00:00+01:00|2001-01-02 00:00:00+01:00|1.0",
        "2001-01-02 00:00:00+01:00|2001-01-03 00:00:00+01:00|3.0",
        "2001-01-03 00:00:00+01:00|2001-01-04 00:00:00+01:00|3.0",
    ]


def test_a_start_without_offset_is_refused(register_three_days, refusal_of):
    _maps, name = register_three_days("z")

    text = refusal_of(
        "t.rast.accumulate",
        input=name,
        output="N",
        basename="n",
        start="2001-01-01",
        cycle="2 days",
        limits="0,10",
    )

    assert (
        f"The time <2001-01-01 00:00:00> and the maps of the space time dataset "
        f"<{name}@PERMANENT> must both have a time zone offset or both have none"
    ) in text


def test_a_lower_dataset_without_offset_is_refused(
    register_three_days, refusal_of, mixed_zones_message
):
    zoned, with_offset = register_three_days("z")
    naive, without = register_three_days("a", offset="")

    text = refusal_of(
        "t.rast.accumulate",
        input=with_offset,
        lower=without,
        output="N",
        basename="n",
        start="2001-01-01 00:00:00+01:00",
        cycle="2 days",
        limits="0,10",
    )

    assert mixed_zones_message(f"{zoned[0]}@PERMANENT", f"{naive[0]}@PERMANENT") in text
