"""Test that t.create stores an apostrophe and a question mark in title and description

The text is put into the INSERT statement by the library; the dataset must be
created and the text read back as given.
"""

import re

import pytest

CASES = {
    "apostrophe_title": {"title": "It's", "description": "d"},
    "apostrophe_description": {"title": "t", "description": "it's"},
    "question_mark_title": {"title": "Why?", "description": "d"},
    "question_mark_description": {"title": "t", "description": "what?"},
    "both": {"title": 'it\'s ? "quoted"', "description": "?'?"},
}


def _title_and_description(tools, name):
    text = tools.t_info(type="strds", input=name).stdout
    match = re.search(
        r"\| Title:\n(.*?)\| Description:\n(.*?)\| Command history:", text, re.DOTALL
    )
    return tuple(part.strip(" |\n") for part in match.groups())


@pytest.mark.parametrize("case", CASES)
def test_text_is_stored_as_given(tools, case):
    options = CASES[case]
    name = f"quote_right_{case}"

    tools.t_create(output=name, **options)

    assert _title_and_description(tools, name) == (
        options["title"],
        options["description"],
    )
