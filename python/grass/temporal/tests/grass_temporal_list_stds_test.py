"""Test which errors list_maps_of_stds() turns into a message"""

import pytest

from grass.temporal import list_stds


def test_an_error_of_the_code_keeps_its_traceback(monkeypatch):
    # Only a combination of columns, method and format that cannot be listed
    # is reported as a message; any other ValueError is a bug in the code.
    def broken(**kwargs):
        msg = "a bug"
        raise ValueError(msg)

    monkeypatch.setattr(list_stds, "_get_list_of_maps_stds", broken)

    with pytest.raises(ValueError, match="a bug"):
        list_stds.list_maps_of_stds(
            type="strds",
            input="a",
            columns=None,
            order=None,
            where=None,
            separator=None,
            method="delta",
        )
