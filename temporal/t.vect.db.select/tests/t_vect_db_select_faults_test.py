"""Test the layer rules of t.vect.db.select for maps registered with and without one

The dataset dbs_lay of conftest.py registers dl:2 in January and du without a
layer in February.
"""


def test_layer_option_applies_to_maps_without_layer(tools, layers):
    # The layer of dl:2 belongs to that map only; du has its own layer 1 table
    # (a = 1, 2) and is read with the layer option, which defaults to 1.
    lines = tools.t_vect_db_select(input=layers, columns="a").stdout.splitlines()

    assert lines == [
        "start_time|end_time|a",
        "2001-01-01 00:00:00|2001-02-01 00:00:00|101",
        "2001-01-01 00:00:00|2001-02-01 00:00:00|102",
        "2001-02-01 00:00:00|2001-03-01 00:00:00|1",
        "2001-02-01 00:00:00|2001-03-01 00:00:00|2",
    ]


def test_layer_option_two_reaches_the_map_after_a_registered_layer(tools, layers):
    lines = tools.t_vect_db_select(
        input=layers, columns="a", layer=2
    ).stdout.splitlines()

    assert lines[3:] == [
        "2001-02-01 00:00:00|2001-03-01 00:00:00|101",
        "2001-02-01 00:00:00|2001-03-01 00:00:00|102",
    ]
