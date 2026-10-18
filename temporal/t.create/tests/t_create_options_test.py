"""Test the options of t.create: types, time types, semantic types, texts

Every test uses its own dataset names, because the module shares one project.
"""

import re

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, stds_info
from grass.tools import ToolError

MAPSET = "work"  # the current mapset of the fixture in conftest.py

CREATE = {"title": "A title", "description": "A description"}


def _texts(tools, stds_type, name):
    """Title, description and command history of a dataset, from t.info

    t.info prints them in a box, the text of a line after "| ". A text of
    several lines continues without the prefix.
    """
    text = tools.t_info(type=stds_type, input=name).stdout
    match = re.search(
        r"\| Title:\n(?P<title>.*?)\| Description:\n(?P<description>.*?)"
        r"\| Command history:\n(?P<history>.*?)\n \+-",
        text,
        re.DOTALL,
    )
    assert match, text
    return {key: value.strip(" |\n") for key, value in match.groupdict().items()}


def _listed(tools, stds_type, name, **options):
    """The rows of t.list for exactly this dataset (name and type columns)"""
    result = tools.t_list(
        type=stds_type,
        where=f"name = '{name}'",
        columns="name,type,semantic_type",
        format="json",
        **options,
    )
    return result.json


@pytest.mark.slow
@pytest.mark.parametrize("temporaltype", ["absolute", "relative"])
@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_type_and_temporal_type_are_recorded(tools, stds_type, temporaltype):
    name = f"ty_{stds_type}_{temporaltype}"

    tools.t_create(
        output=name,
        type=stds_type,
        temporaltype=temporaltype,
        semantictype="sum",
        **CREATE,
    )

    info = stds_info(tools, stds_type, name)
    assert (info["id"], info["name"], info["mapset"]) == (
        f"{name}@{MAPSET}",
        name,
        MAPSET,
    )
    assert info["temporal_type"] == temporaltype
    # Only a relative time dataset has a time unit, still unset when empty.
    assert ("unit" in info) == (temporaltype == "relative")
    other = "relative" if temporaltype == "absolute" else "absolute"
    # t.list filters on the temporal type read from the database, so this
    # tells the stored value from what t.info prints.
    assert _listed(tools, stds_type, name, temporaltype=temporaltype) == [
        {"name": name, "type": stds_type, "semantic_type": "sum"}
    ]
    assert _listed(tools, stds_type, name, temporaltype=other) == []


@pytest.mark.slow
def test_dataset_is_empty_after_creation(tools):
    tools.t_create(output="empty_ds", **CREATE)

    info = stds_info(tools, "strds", "empty_ds")

    # t.info prints "None" for the count of a dataset that never held a map.
    assert info["number_of_maps"] == "None"
    assert list_maps(tools, "strds", "empty_ds") == []


@pytest.mark.slow
def test_type_defaults_to_strds_and_time_to_absolute(tools):
    tools.t_create(output="defaults_ds", **CREATE)

    info = stds_info(tools, "strds", "defaults_ds")

    assert info["temporal_type"] == "absolute"
    assert _listed(tools, "strds", "defaults_ds")[0]["type"] == "strds"
    assert _listed(tools, "stvds", "defaults_ds") == []


@pytest.mark.slow
@pytest.mark.parametrize("semantictype", ["min", "max", "sum", "mean"])
def test_semantictype_is_recorded(tools, semantictype):
    name = f"sem_{semantictype}"

    tools.t_create(output=name, semantictype=semantictype, **CREATE)

    assert stds_info(tools, "strds", name)["semantic_type"] == semantictype
    assert _listed(tools, "strds", name)[0]["semantic_type"] == semantictype


@pytest.mark.parametrize("stds_type", ["str3ds", "stvds"])
def test_semantictype_is_recorded_for_the_other_types(tools, stds_type):
    name = f"sem_max_{stds_type}"

    tools.t_create(output=name, type=stds_type, semantictype="max", **CREATE)

    assert stds_info(tools, stds_type, name)["semantic_type"] == "max"


def test_semantictype_defaults_to_mean(tools):
    # The option is marked as required in the interface but has the answer
    # mean, so leaving it out is accepted.
    tools.t_create(output="sem_default", **CREATE)

    assert stds_info(tools, "strds", "sem_default")["semantic_type"] == "mean"


@pytest.mark.parametrize(
    ("key", "text"),
    [
        ("plain", "Plain words"),
        ("double_quotes", 'with "double quotes"'),
        ("umlauts", "umlauts \u00e4\u00f6\u00fc \u00df"),
        ("sql_characters", "semicolon; and --dashes"),
        ("backslash", "back\\slash"),
        ("newline", "two\nlines"),
    ],
)
def test_title_and_description_are_stored_as_given(tools, key, text):
    name = f"txt_{key}"

    tools.t_create(output=name, title=text, description=f"about {text}")

    texts = _texts(tools, "strds", name)
    assert texts["title"] == text
    assert texts["description"] == f"about {text}"


def test_command_is_recorded_in_the_history(tools):
    tools.t_create(output="hist_ds", semantictype="min", **CREATE)

    history = _texts(tools, "strds", "hist_ds")["history"]

    assert 't.create output="hist_ds"' in history
    assert 'semantictype="min"' in history


def test_name_may_carry_the_current_mapset(tools):
    tools.t_create(output=f"qualified@{MAPSET}", **CREATE)

    assert stds_info(tools, "strds", "qualified")["id"] == f"qualified@{MAPSET}"


@pytest.mark.parametrize("mapset", ["other", "PERMANENT", "nowhere"])
def test_name_in_another_mapset_is_refused(tools, mapset):
    name = f"foreign_{mapset}"

    with pytest.raises(ToolError, match="only be created in the current mapset"):
        tools.t_create(output=f"{name}@{mapset}", **CREATE)

    assert _listed(tools, "strds", name) == []


@pytest.mark.slow
def test_existing_dataset_is_refused_without_overwrite(tools):
    tools.t_create(output="exists_ds", semantictype="sum", **CREATE)

    with pytest.raises(ToolError, match="already in the database") as raised:
        tools.t_create(
            output="exists_ds", semantictype="min", title="New", description="New"
        )

    assert "overwrite" in str(raised.value)
    # Nothing of the refused call is stored.
    assert stds_info(tools, "strds", "exists_ds")["semantic_type"] == "sum"
    assert _texts(tools, "strds", "exists_ds")["title"] == "A title"


@pytest.mark.slow
def test_overwrite_replaces_the_dataset(tools):
    tools.t_create(output="over_ds", semantictype="sum", **CREATE)

    result = tools.t_create(
        output="over_ds",
        temporaltype="relative",
        semantictype="max",
        title="New title",
        description="New description",
        overwrite=True,
    )

    assert "Overwriting space time raster dataset <over_ds>" in result.stderr
    info = stds_info(tools, "strds", "over_ds")
    assert (info["temporal_type"], info["semantic_type"]) == ("relative", "max")
    texts = _texts(tools, "strds", "over_ds")
    assert (texts["title"], texts["description"]) == ("New title", "New description")


@pytest.mark.slow
def test_overwrite_unregisters_the_maps_but_keeps_them(tools):
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    create_stds(
        tools,
        "strds",
        "over_maps",
        [MapSpec(f"over_m{i}", i, day(i - 1), day(i)) for i in (1, 2)],
    )

    result = tools.t_create(output="over_maps", overwrite=True, **CREATE)

    assert "unregistering all maps" in result.stderr.replace("\n", " ")
    assert list_maps(tools, "strds", "over_maps") == []
    existing = tools.g_list(type="raster", pattern="over_m*").stdout.split()
    assert existing == ["over_m1", "over_m2"]


def test_overwrite_of_a_new_name_just_creates(tools):
    result = tools.t_create(output="over_new", overwrite=True, **CREATE)

    assert "Overwriting" not in result.stderr
    assert _listed(tools, "strds", "over_new")


@pytest.mark.parametrize(
    ("option", "value"),
    [("type", "raster"), ("temporaltype", "bogus"), ("semantictype", "median")],
)
def test_value_outside_the_options_is_refused(tools, option, value):
    name = f"bad_{option}"

    with pytest.raises(ToolError) as raised:
        tools.t_create(output=name, **{**CREATE, option: value})

    assert f"Value <{value}> out of range for parameter <{option}>" in str(raised.value)
    assert _listed(tools, "strds", name) == []


@pytest.mark.parametrize("missing", ["output", "title", "description"])
def test_required_option_is_checked(tools, missing):
    options = {"output": "req_ds", **CREATE}
    del options[missing]

    with pytest.raises(ToolError, match=f"Required parameter <{missing}> not set"):
        tools.t_create(**options)

    assert _listed(tools, "strds", "req_ds") == []


# G_legal_filename() (lib/gis/legal_name.c) refuses a map name that starts
# with "." or contains a character up to " ", one of / " ' @ , = * or a byte
# above 0176. A semicolon and a leading digit are legal there.
LEGAL_NAMES = {"leading_digit": "1digit", "semicolon": "semi;colon"}
# The value says whether t.create warns today; the comma passes silently.
ILLEGAL_NAMES = {
    "space": ("a b", True),
    "slash": ("sl/ash", True),
    "equals": ("eq=ual", True),
    "star": ("st*ar", True),
    "comma": ("com,ma", False),
}


@pytest.mark.parametrize("case", LEGAL_NAMES)
def test_odd_but_legal_names_are_accepted(tools, case):
    name = LEGAL_NAMES[case]

    result = tools.t_create(output=name, **CREATE)

    assert "Illegal filename" not in result.stderr
    assert _listed(tools, "strds", name) == [
        {"name": name, "type": "strds", "semantic_type": "mean"}
    ]


@pytest.mark.parametrize("case", ILLEGAL_NAMES)
def test_today_an_illegal_name_is_accepted(tools, case):
    name, warns = ILLEGAL_NAMES[case]
    name = f"today_{name}"

    result = tools.t_create(output=name, **CREATE)

    assert ("Illegal filename" in result.stderr) == warns
    assert _listed(tools, "strds", name) == [
        {"name": name, "type": "strds", "semantic_type": "mean"}
    ]


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
@pytest.mark.parametrize("case", ILLEGAL_NAMES)
def test_an_illegal_name_is_refused(tools, case):
    name, _ = ILLEGAL_NAMES[case]
    name = f"right_{name}"

    with pytest.raises(ToolError):
        tools.t_create(output=name, **CREATE)

    assert _listed(tools, "strds", name) == []
