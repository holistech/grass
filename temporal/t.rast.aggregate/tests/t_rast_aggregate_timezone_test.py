"""Test t.rast.aggregate on a space time dataset with a time zone offset"""


def test_a_dataset_with_an_offset_is_aggregated(tools, register_three_days):
    """Granules of two days from the start of the data at +01:00: January 1
    to 3 averages the maps 1 and 2 to 1.5, January 3 to 5 holds map 3 only."""
    _maps, name = register_three_days("z")

    tools.t_rast_aggregate(input=name, output="G", basename="g", granularity="2 days")

    rows = tools.t_rast_list(input="G", columns="start_time,end_time,min").stdout
    assert rows.splitlines()[1:] == [
        "2001-01-01 00:00:00+01:00|2001-01-03 00:00:00+01:00|1.5",
        "2001-01-03 00:00:00+01:00|2001-01-05 00:00:00+01:00|3.0",
    ]
