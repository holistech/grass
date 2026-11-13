"""Test t.rast.aggregate.ds on space time datasets with a time zone offset"""


def test_a_dataset_with_an_offset_is_aggregated_by_itself(tools, register_three_days):
    """Each map of register_three_days is the only map equal to its own granule, so the
    averages are the values 1, 2 and 3 with the times of the maps."""
    _maps, name = register_three_days("z")

    tools.t_rast_aggregate_ds(
        input=name,
        sample=name,
        output="G",
        basename="g",
        method="average",
        sampling="equal",
    )

    rows = tools.t_rast_list(input="G", columns="start_time,end_time,min").stdout
    assert rows.splitlines()[1:] == [
        "2001-01-01 00:00:00+01:00|2001-01-02 00:00:00+01:00|1.0",
        "2001-01-02 00:00:00+01:00|2001-01-03 00:00:00+01:00|2.0",
        "2001-01-03 00:00:00+01:00|2001-01-04 00:00:00+01:00|3.0",
    ]


def test_a_sampler_without_offset_is_refused(
    register_three_days, refusal_of, mixed_zones_message
):
    """The granules come from the sampler but are computed, so the message
    names the first by its start."""
    zoned, with_offset = register_three_days("z")
    _naive, without = register_three_days("a", offset="")

    text = refusal_of(
        "t.rast.aggregate.ds",
        input=with_offset,
        sample=without,
        output="N",
        basename="n",
        method="average",
    )

    assert mixed_zones_message(f"{zoned[0]}@PERMANENT", "2001-01-01 00:00:00") in text
