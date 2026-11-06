"""Test t.remove and t.info on a dataset with a dot in its name

A dataset of an older release can have a dot in its name; the tools that
create datasets refuse such a name now. The dataset is made here with the
dataset class, as the older release did.
"""

import pytest

from grass.temporal.testing.data import insert_old_stds
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools


@pytest.fixture
def dotted(tmp_path):
    """Tools in a project with the empty datasets a.b and plain"""
    with temporal_session(tmp_path / "project") as session:
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        for name in ("a.b", "plain"):
            insert_old_stds(name)
        yield tools


def names(tools):
    return tools.t_list(type="strds", columns="name").stdout.split()


def test_dataset_with_dot_in_name(dotted):
    assert dotted.t_info(type="strds", input="a.b", flags="g").keyval["name"] == "a.b"
    assert (
        dotted.t_info(type="strds", input="a.b@PERMANENT", flags="g").keyval["id"]
        == "a.b@PERMANENT"
    )

    dotted.t_remove(type="strds", inputs="a.b", flags="f")

    assert names(dotted) == ["plain"]
