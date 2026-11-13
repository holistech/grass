"""Test t.rast.list method=gran on a space time dataset with a time zone offset

The three maps of register_three_days last one day each from 2001-01-01 at +01:00, so
the granularity of the dataset is one day and the list has one granule per
map, each one day long and 0, 1 and 2 days from the start of the dataset.
"""


def test_the_granules_of_a_dataset_with_an_offset(tools, register_three_days):
    maps, name = register_three_days("z", stds_type="strds")

    rows = tools.t_rast_list(input=name, method="gran").stdout.splitlines()

    days = ["2001-01-01", "2001-01-02", "2001-01-03", "2001-01-04"]
    assert rows[0] == (
        "id|name|mapset|start_time|end_time|interval_length|distance_from_begin"
    )
    assert rows[1:] == [
        f"{map_}@PERMANENT|{map_}|PERMANENT|{start} 00:00:00+01:00"
        f"|{end} 00:00:00+01:00|1.0|{float(number)}"
        for number, (map_, start, end) in enumerate(
            zip(maps, days[:-1], days[1:], strict=True)
        )
    ]
