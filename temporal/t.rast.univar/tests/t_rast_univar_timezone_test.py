"""Test t.rast.univar granularity on a dataset with a time zone offset"""


def test_granules_of_a_dataset_with_an_offset(tools, register_three_days):
    """Granules of two days from the start of the data at +01:00: January 1
    to 3 holds the maps 1 and 2 (mean 1.5), January 3 to 5 map 3 (mean 3)."""
    maps, name = register_three_days("z")

    rows = tools.t_rast_univar(input=name, granularity="2 days").stdout.splitlines()

    head = rows[0].split("|")
    picked = [
        [
            row.split("|")[head.index(column)]
            for column in ("id", "start", "end", "mean")
        ]
        for row in rows[1:]
    ]
    assert picked == [
        [
            f"{maps[0]}@PERMANENT,{maps[1]}@PERMANENT",
            "2001-01-01 00:00:00+01:00",
            "2001-01-03 00:00:00+01:00",
            "1.5",
        ],
        [
            f"{maps[2]}@PERMANENT",
            "2001-01-03 00:00:00+01:00",
            "2001-01-05 00:00:00+01:00",
            "3",
        ],
    ]
