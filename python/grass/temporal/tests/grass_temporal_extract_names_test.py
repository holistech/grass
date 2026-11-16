"""Test the numbering of map names that still clash after extraction"""

from grass.temporal.extract import number_clashing_names


def test_the_first_map_keeps_its_name_and_the_next_ones_are_numbered():
    assert number_clashing_names(["b_01", "b_01", "b_01"]) == [
        "b_01",
        "b_01_2",
        "b_01_3",
    ]


def test_a_number_is_skipped_when_a_later_map_has_that_name_naturally():
    # The second map would become b_01_2, which the third map has already.
    assert number_clashing_names(["b_01", "b_01", "b_01_2"]) == [
        "b_01",
        "b_01_3",
        "b_01_2",
    ]


def test_names_without_a_clash_stay():
    assert number_clashing_names(["a", "b", "c"]) == ["a", "b", "c"]
