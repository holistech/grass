"""Test t.rast.accdetect on space time datasets with a time zone offset"""


def test_a_dataset_with_an_offset_is_detected(tools, register_three_days):
    """All values 1 to 3 lie in the range 0 to 10. A cycle of two days from
    2001-01-01 at +01:00 counts the days since the start of the event in it:
    0 for January 1, 1 for January 2; January 3 starts the next cycle, 0."""
    _maps, name = register_three_days("z")

    tools.t_rast_accdetect(
        input=name,
        occurrence="OC",
        basename="oc",
        start="2001-01-01 00:00:00+01:00",
        cycle="2 days",
        range="0,10",
    )

    rows = tools.t_rast_list(input="OC", columns="start_time,end_time,min").stdout
    assert rows.splitlines()[1:] == [
        "2001-01-01 00:00:00+01:00|2001-01-02 00:00:00+01:00|0.0",
        "2001-01-02 00:00:00+01:00|2001-01-03 00:00:00+01:00|1.0",
        "2001-01-03 00:00:00+01:00|2001-01-04 00:00:00+01:00|0.0",
    ]


def test_a_minimum_dataset_without_offset_is_refused(
    register_three_days, refusal_of, mixed_zones_message
):
    zoned, with_offset = register_three_days("z")
    naive, without = register_three_days("a", offset="")

    text = refusal_of(
        "t.rast.accdetect",
        input=with_offset,
        minimum=without,
        occurrence="N",
        basename="n",
        start="2001-01-01 00:00:00+01:00",
        cycle="2 days",
        range="0,10",
    )

    assert mixed_zones_message(f"{zoned[0]}@PERMANENT", f"{naive[0]}@PERMANENT") in text
