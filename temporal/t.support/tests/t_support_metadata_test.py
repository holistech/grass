"""Test the metadata options of t.support: title, description, semantic type

The dataset has three maps (see the make_dataset fixture), the title "T0", the
description "D0" and the semantic type mean. Title and description are read
back from t.info, the semantic type and the aggregation type from t.info -g.

The option semantictype has no default, so a call without it keeps the
semantic type; for a vector dataset an aggr_type is warned about and the other
options are applied.
"""

import pytest

from grass.temporal.testing.readback import message, stds_info
from grass.tools import ToolError

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

TYPES = ["strds", "str3ds", "stvds"]


def _title(text):
    return text.split("Title:")[1].split("Description:")[0].strip()


def _description(text):
    return text.split("Description:")[1].split("Command history:")[0].strip()


@pytest.mark.parametrize("stds_type", TYPES)
def test_title_description_and_semantic_type(tools, make_dataset, info_text, stds_type):
    name, _ = make_dataset(stds_type)

    tools.t_support(
        type=stds_type,
        input=name,
        title="A new title",
        description="A new description",
        semantictype="sum",
    )

    text = info_text(stds_type, name)
    assert _title(text) == "A new title"
    assert _description(text) == "A new description"
    assert stds_info(tools, stds_type, name)["semantic_type"] == "sum"


@pytest.mark.parametrize("stds_type", ["strds", "str3ds"])
def test_aggregation_type(tools, make_dataset, stds_type):
    name, _ = make_dataset(stds_type)
    assert stds_info(tools, stds_type, name)["aggregation_type"] == "None"

    tools.t_support(type=stds_type, input=name, aggr_type="average")

    assert stds_info(tools, stds_type, name)["aggregation_type"] == "average"


@pytest.mark.parametrize("semantic_type", ["min", "max", "sum", "mean"])
def test_each_semantic_type(tools, make_dataset, semantic_type):
    name, _ = make_dataset()

    tools.t_support(input=name, semantictype=semantic_type)

    assert stds_info(tools, "strds", name)["semantic_type"] == semantic_type


def test_the_title_alone_leaves_the_description(tools, make_dataset, info_text):
    name, _ = make_dataset()

    tools.t_support(input=name, title="Only the title")

    text = info_text("strds", name)
    assert (_title(text), _description(text)) == ("Only the title", "D0")


def test_the_description_alone_leaves_the_title(tools, make_dataset, info_text):
    name, _ = make_dataset()

    tools.t_support(input=name, description="Only the description")

    text = info_text("strds", name)
    assert (_title(text), _description(text)) == ("T0", "Only the description")


def test_an_empty_title_changes_nothing(tools, make_dataset, info_text):
    name, _ = make_dataset()

    tools.t_support(input=name, title="")

    assert _title(info_text("strds", name)) == "T0"


def test_a_dataset_of_relative_time(tools, make_dataset, info_text):
    name, _ = make_dataset(temporaltype="relative")

    tools.t_support(
        input=name, title="Test support", description="Relative", semantictype="max"
    )

    text = info_text("strds", name)
    assert (_title(text), _description(text)) == ("Test support", "Relative")
    assert stds_info(tools, "strds", name)["semantic_type"] == "max"


def test_the_command_history_names_t_support(tools, make_dataset, info_text):
    name, _ = make_dataset()

    tools.t_support(input=name, title="Logged")

    history = info_text("strds", name).split("Command history:")[1]
    assert f't.support input="{name}" title="Logged"' in history


def test_the_maps_are_not_touched(tools, make_dataset):
    name, maps = make_dataset()
    before = stds_info(tools, "strds", name)

    tools.t_support(input=name, title="New", semantictype="mean")

    after = stds_info(tools, "strds", name)
    for key in ("number_of_maps", "start_time", "end_time", "granularity", "max_max"):
        assert after[key] == before[key]


def test_today_aggr_type_takes_any_text(tools, make_dataset):
    name, _ = make_dataset()

    tools.t_support(input=name, aggr_type="not an aggregation")

    assert stds_info(tools, "strds", name)["aggregation_type"] == ("not an aggregation")


def test_a_call_without_semantictype_keeps_it(tools, make_dataset):
    name, _ = make_dataset()
    tools.t_support(input=name, semantictype="sum")

    tools.t_support(input=name, title="Another title")

    assert stds_info(tools, "strds", name)["semantic_type"] == "sum"


def test_aggr_type_on_a_vector_dataset_does_not_stop_the_other_options(
    tools, make_dataset, info_text
):
    name, _ = make_dataset("stvds")

    tools.t_support(type="stvds", input=name, aggr_type="average", title="Applied")

    assert _title(info_text("stvds", name)) == "Applied"


def test_aggr_type_on_a_vector_dataset_is_warned_about(tools, make_dataset):
    name, _ = make_dataset("stvds")

    result = tools.t_support(type="stvds", input=name, aggr_type="average")

    assert "has no aggregation type" in message(result)


def test_a_vector_dataset_has_no_aggregation_type(tools, make_dataset):
    name, _ = make_dataset("stvds")

    tools.t_support(type="stvds", input=name, aggr_type="average")

    assert "aggregation_type" not in stds_info(tools, "stvds", name)


def test_an_unknown_dataset_is_refused(tools):
    with pytest.raises(ToolError) as error:
        tools.t_support(input="nope", title="x")

    assert "Space time dataset <nope> of type <strds> not found" in message(error.value)


def test_a_dataset_of_another_type_is_not_found(tools, make_dataset):
    name, _ = make_dataset()

    with pytest.raises(ToolError) as error:
        tools.t_support(type="stvds", input=name, title="x")

    assert f"Space time dataset <{name}> of type <stvds> not found" in message(
        error.value
    )


def test_an_unknown_semantic_type_is_refused(tools):
    with pytest.raises(
        ToolError, match=r"out\s+of\s+range\s+for\s+parameter\s+<semantictype>"
    ):
        tools.t_support(input="a", semantictype="median")


def test_an_unknown_type_is_refused(tools):
    with pytest.raises(ToolError, match=r"out\s+of\s+range\s+for\s+parameter\s+<type>"):
        tools.t_support(type="raster", input="a")


def test_the_input_is_required(tools):
    with pytest.raises(ToolError, match=r"Required\s+parameter\s+<input>\s+not\s+set"):
        tools.t_support(title="x")
