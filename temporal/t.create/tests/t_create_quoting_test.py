"""Pin how t.create treats an apostrophe and a question mark in title and description

The apostrophe ends the SQL string of the INSERT statement, and the question
mark is taken for a placeholder by the library's mogrify_sql_statement(), so
the call fails with a Python traceback instead of storing the text. Each case has a test for today's behaviour and a strict xfail test for
the behaviour a user expects: the dataset is created and the text is read back
as given.
"""

import re

import pytest

from grass.temporal.testing.readback import stds_info
from grass.tools import ToolError

CASES = {
    "apostrophe_title": ({"title": "It's", "description": "d"}, "syntax error"),
    "apostrophe_description": ({"title": "t", "description": "it's"}, "syntax error"),
    "question_mark_title": ({"title": "Why?", "description": "d"}, "IndexError"),
    "question_mark_description": ({"title": "t", "description": "what?"}, "IndexError"),
}


def _exists(tools, name):
    result = tools.t_list(type="strds", where=f"name = '{name}'", format="json")
    return bool(result.json)


def _title_and_description(tools, name):
    text = tools.t_info(type="strds", input=name).stdout
    match = re.search(
        r"\| Title:\n(.*?)\| Description:\n(.*?)\| Command history:", text, re.DOTALL
    )
    return tuple(part.strip(" |\n") for part in match.groups())


@pytest.mark.parametrize("case", CASES)
def test_today_the_call_fails_and_leaves_no_dataset(tools, case):
    options, reason = CASES[case]
    name = f"quote_today_{case}"

    with pytest.raises(ToolError) as raised:
        tools.t_create(output=name, **options)

    assert reason in str(raised.value)
    assert not _exists(tools, name)
    # The failed call leaves nothing behind that blocks the name.
    tools.t_create(output=name, title="plain", description="plain")
    assert stds_info(tools, "strds", name)["name"] == name


@pytest.mark.xfail(strict=True, raises=ToolError, reason="see OFFENE_PUNKTE")
@pytest.mark.parametrize("case", CASES)
def test_text_is_stored_as_given(tools, case):
    options, _ = CASES[case]
    name = f"quote_right_{case}"

    tools.t_create(output=name, **options)

    assert _title_and_description(tools, name) == (
        options["title"],
        options["description"],
    )
