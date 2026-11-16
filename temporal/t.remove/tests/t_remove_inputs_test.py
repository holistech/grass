"""Test how t.remove reads its datasets: lists, files, types and refusals

Pinned as they are today: the exclusion message names input= and file= for
the options inputs= and file=, a missing file ends in a traceback, and a
failed call with -r has already unregistered the maps of the datasets it got
to before the error.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def test_several_datasets(tools, make_stds, has_dataset):
    _, (first, second, third) = make_stds(2, datasets=3)

    tools.t_remove(inputs=f"{first},{second}", flags="f")

    assert [has_dataset(name) for name in (first, second, third)] == [
        False,
        False,
        True,
    ]


def test_blanks_around_a_name_are_ignored(tools, make_stds, has_dataset):
    _, (first, second) = make_stds(1, datasets=2)

    tools.t_remove(inputs=f" {first} ,{second}", flags="f")

    assert not has_dataset(first)
    assert not has_dataset(second)


def test_a_name_with_its_mapset(tools, make_stds, has_dataset):
    _, (name,) = make_stds(1)

    tools.t_remove(inputs=f"{name}@PERMANENT", flags="f")

    assert not has_dataset(name)


def test_names_come_from_a_file(tools, make_stds, has_dataset, tmp_path):
    _, (first, second, third) = make_stds(1, datasets=3)
    file = tmp_path / "names.txt"
    file.write_text(f"{first}\n{third}\n")

    tools.t_remove(file=file, flags="f")

    assert [has_dataset(name) for name in (first, second, third)] == [
        False,
        True,
        False,
    ]


def test_a_blank_line_in_the_file_is_skipped(tools, make_stds, has_dataset, tmp_path):
    # The blank line lies before a later valid name, so that a tool which
    # stopped at the blank line would leave the second dataset.
    _, (first, second) = make_stds(1, datasets=2)
    file = tmp_path / "names.txt"
    file.write_text(f"{first}\n\n{second}\n")

    result = tools.t_remove(file=file, flags="f")

    assert result.stderr.strip() == ""
    assert not has_dataset(first)
    assert not has_dataset(second)


def test_inputs_and_file_exclude_each_other(tools, make_stds, has_dataset, tmp_path):
    _, (name,) = make_stds(1)
    file = tmp_path / "names.txt"
    file.write_text(name + "\n")

    with pytest.raises(ToolError, match=r"are\s+mutually\s+exclusive"):
        tools.t_remove(inputs=name, file=file, flags="f")

    assert has_dataset(name)


def test_the_exclusion_names_the_options_inputs_and_file(tools, tmp_path):
    with pytest.raises(
        ToolError, match=r"inputs=\s+and\s+file=\s+are\s+mutually\s+exclusive"
    ):
        tools.t_remove(inputs="a", file=tmp_path / "names.txt")


def test_a_missing_file_is_refused_with_a_message(tools, tmp_path):
    with pytest.raises(ToolError) as error:
        tools.t_remove(file=tmp_path / "missing.txt", flags="f")

    assert "Traceback" not in message(error.value)
    assert "not found" in message(error.value)


def test_an_unknown_dataset_is_refused(tools):
    with pytest.raises(
        ToolError, match=r"Space\s+time\s+dataset\s+<nope>\s+of\s+type\s+<strds>"
    ):
        tools.t_remove(inputs="nope", flags="f")


def test_an_unknown_dataset_after_a_known_one_removes_nothing(
    tools, make_stds, has_dataset, registered
):
    maps, (name,) = make_stds(2)

    with pytest.raises(ToolError, match=r"not\s+found"):
        tools.t_remove(inputs=f"{name},nope", flags="f")

    assert has_dataset(name)
    assert registered(maps) == [True] * 2


def test_a_failed_call_does_not_change_anything(
    tools, make_stds, has_dataset, registered
):
    maps, (name,) = make_stds(2)

    with pytest.raises(ToolError, match=r"not\s+found"):
        tools.t_remove(inputs=f"{name},nope", flags="rf")

    assert has_dataset(name)
    assert registered(maps) == [True] * 2


def test_a_dataset_of_another_type_is_not_found(tools, make_stds, has_dataset):
    _, (name,) = make_stds(1)

    with pytest.raises(ToolError, match=r"of\s+type\s+<stvds>\s+not\s+found"):
        tools.t_remove(inputs=name, type="stvds", flags="f")

    assert has_dataset(name)


def test_the_type_defaults_to_strds(tools, make_stds, has_dataset):
    _, (name,) = make_stds(1)

    tools.t_remove(inputs=name, type="strds", flags="f")

    assert not has_dataset(name)


def test_an_unknown_type_is_refused(tools):
    with pytest.raises(ToolError, match=r"out\s+of\s+range\s+for\s+parameter\s+<type>"):
        tools.t_remove(inputs="a", type="raster", flags="f")
