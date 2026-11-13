"""Test t.rast.to.rast3 on a space time dataset with a time zone offset"""


def test_the_cube_of_a_dataset_with_an_offset(tools, register_three_days):
    """The bottom counts the days from 1900-01-01 to the start in the clock
    of the start, as the years and months of the start count without
    offset: 101 years of 365 days and the 25 leap days 1904 to 2000 give
    36890 for 2001-01-01. Three maps of one day put the top at 36893."""
    _maps, name = register_three_days("z")

    tools.t_rast_to_rast3(input=name, output="cube")

    info = tools.r3_info(map="cube", flags="g").keyval
    assert (info["bottom"], info["top"], info["tbres"]) == (36890, 36893, 1)
