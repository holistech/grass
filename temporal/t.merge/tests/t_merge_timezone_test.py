"""Test t.merge with space time datasets with a time zone offset

t.register keeps the times of a dataset to one kind, with or without an
offset, because times of both kinds cannot be ordered against each other;
t.merge keeps the merged dataset to one kind as well.
"""

import pytest


def test_datasets_with_an_offset_are_merged(tools, register_three_days):
    maps, first = register_three_days("z")
    _other_maps, second = register_three_days("y")

    tools.t_merge(inputs=f"{first},{second}", output="M")

    assert tools.t_info(input="M", flags="g").keyval["number_of_maps"] == 6
    assert maps[0] in tools.t_rast_list(input="M", columns="name").stdout


@pytest.mark.parametrize("order", ["with first", "without first"])
def test_a_dataset_with_an_offset_and_one_without_are_refused(
    register_three_days, refusal_of, order
):
    _zoned, with_offset = register_three_days("z")
    _naive, without = register_three_days("a", offset="")
    inputs = [with_offset, without]
    if order == "without first":
        inputs.reverse()

    text = refusal_of("t.merge", inputs=",".join(inputs), output="N")

    assert (
        "Space time datasets to merge must all have a time zone offset or all "
        f"have none: <{with_offset}@PERMANENT> has one, <{without}@PERMANENT> "
        "has none"
    ) in text


def test_an_existing_output_without_offset_is_refused(
    tools, register_three_days, refusal_of
):
    """The maps already in the output count like those of an input."""
    _zoned, with_offset = register_three_days("z")
    _naive, without = register_three_days("a", offset="")
    tools.t_copy(input=without, output="Old")
    before = tools.t_rast_list(input="Old", columns="name").stdout

    text = refusal_of("t.merge", inputs=with_offset, output="Old", overwrite=True)

    assert "Space time datasets to merge must all have a time zone offset" in text
    assert tools.t_rast_list(input="Old", columns="name").stdout == before
