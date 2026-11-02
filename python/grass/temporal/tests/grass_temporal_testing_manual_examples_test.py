# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Tests of the parser for the examples of a temporal tool manual

The input is plain text written to tmp_path, so no GRASS session is needed.
"""

import pytest

from grass.temporal.testing import manual_examples as me


def tab(label, body):
    """Return a tab of the manual layout with its content indented by four"""
    lines = [f'=== "{label}"', ""]
    lines += [("    " + line) if line else "" for line in body.split("\n")]
    return "\n".join(lines) + "\n"


def example(title, shell, python, extra=""):
    """Return one ### section with both tabs"""
    return (
        f"### {title}\n\n{extra}"
        + tab("Command line", "```sh\n" + shell + "\n```")
        + "\n"
        + tab("Python (grass.tools)", "```python\n" + python + "\n```")
        + "\n"
    )


def write(tmp_path, text, tool="t.x"):
    folder = tmp_path / tool
    folder.mkdir()
    path = folder / f"{tool}.md"
    path.write_text(text)
    return path


def manual(*sections, head="", after=""):
    return (
        "## DESCRIPTION\n\nText.\n\n## EXAMPLES\n\n" + head + "".join(sections) + after
    )


def test_each_h3_under_examples_is_an_example(tmp_path):
    text = manual(
        example("First", "t.a", "tools.t_a()"),
        example("Second", "t.b", "tools.t_b()"),
        after="## SEE ALSO\n\n### Not an example\n",
    )
    parsed = me.parse_manual(write(tmp_path, text))
    assert parsed.tool == "t.x"
    got = [(e.title, e.variant, e.blocks[0].code) for e in parsed.examples]
    assert got == [
        ("First", "shell", "t.a\n"),
        ("First", "python", "tools.t_a()\n"),
        ("Second", "shell", "t.b\n"),
        ("Second", "python", "tools.t_b()\n"),
    ]
    assert [b.language for e in parsed.examples for b in e.blocks] == [
        "sh",
        "python",
        "sh",
        "python",
    ]


def test_a_text_block_after_a_code_block_is_its_shown_output(tmp_path):
    shell = "```sh\nt.a\n```\n\n```text\nline 1\nline 2\n```"
    python = "```python\nprint(1)\n```"
    text = manual(
        "### T\n\n"
        + tab("Command line", shell)
        + "\n"
        + tab("Python (grass.tools)", python)
    )
    parsed = me.parse_manual(write(tmp_path, text))
    shell_block = parsed.examples[0].blocks[0]
    assert shell_block.shown_output == "line 1\nline 2\n"
    assert shell_block.code == "t.a\n"
    assert shell_block.line == 11
    assert parsed.examples[1].blocks[0].shown_output is None


def test_a_text_block_without_a_code_block_is_an_error(tmp_path):
    shell = "```text\nlost\n```\n\n```sh\nt.a\n```"
    text = manual(
        "### T\n\n"
        + tab("Command line", shell)
        + "\n"
        + tab("Python (grass.tools)", "```python\nx\n```")
    )
    with pytest.raises(me.ManualFormatError) as excinfo:
        me.parse_manual(write(tmp_path, text))
    assert excinfo.value.line == 11
    assert "t.x" in str(excinfo.value)
    assert ":11:" in str(excinfo.value)


def test_prose_between_a_code_block_and_a_text_block_is_an_error(tmp_path):
    shell = "```sh\nt.a\n```\n\nProse.\n\n```text\nout\n```"
    text = manual(
        "### T\n\n"
        + tab("Command line", shell)
        + "\n"
        + tab("Python (grass.tools)", "```python\nx\n```")
    )
    with pytest.raises(me.ManualFormatError):
        me.parse_manual(write(tmp_path, text))


def test_an_example_without_the_python_tab_is_an_error(tmp_path):
    text = manual("### Lonely\n\n" + tab("Command line", "```sh\nt.a\n```"))
    with pytest.raises(me.ManualFormatError) as excinfo:
        me.parse_manual(write(tmp_path, text))
    message = str(excinfo.value)
    assert "t.x" in message
    assert "Lonely" in message
    assert "Python (grass.tools)" in message
    assert "is missing" in message


def test_a_code_block_of_another_language_is_an_error(tmp_path):
    text = manual(example("T", "t.a", "x").replace("```sh", "```bash"))
    with pytest.raises(me.ManualFormatError):
        me.parse_manual(write(tmp_path, text))


def test_a_code_block_outside_a_tab_is_an_error(tmp_path):
    text = manual("### T\n\n```sh\nt.a\n```\n\n")
    with pytest.raises(me.ManualFormatError, match="outside a tab"):
        me.parse_manual(write(tmp_path, text))


def test_a_control_comment_at_the_end_of_the_file_is_an_error(tmp_path):
    text = (
        manual(example("T", "a", "b")) + "    <!-- example: requires=postgresql -->\n"
    )
    with pytest.raises(me.ManualFormatError, match="without a code block"):
        me.parse_manual(write(tmp_path, text))


def test_a_heading_inside_a_code_block_does_not_end_the_section(tmp_path):
    shell = "t.a\n## EXAMPLES"
    text = manual(example("T", shell, "x"))
    parsed = me.parse_manual(write(tmp_path, text))
    assert parsed.examples[0].blocks[0].code == "t.a\n## EXAMPLES\n"


def test_control_comments_are_read_and_unknown_keys_rejected(tmp_path):
    good = (
        example("T", "t.a", "x")
        .replace(
            "    ```sh",
            "    <!-- example: requires=postgresql -->\n    ```sh",
        )
        .replace(
            "    ```python",
            '    <!-- example: not-run reason="needs a network, 2 words" -->\n'
            "    ```python",
        )
    )
    parsed = me.parse_manual(write(tmp_path, manual(good)))
    assert parsed.examples[0].blocks[0].control == {"requires": "postgresql"}
    assert parsed.examples[1].blocks[0].control == {
        "not-run": "",
        "reason": "needs a network, 2 words",
    }
    bad = example("T", "t.a", "x").replace(
        "    ```sh", "    <!-- example: frobnicate=1 -->\n    ```sh"
    )
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(me.ManualFormatError) as excinfo:
        me.parse_manual(write(other, manual(bad)))
    assert "frobnicate" in str(excinfo.value)


@pytest.mark.parametrize(
    "comment",
    [
        "requires=mysql",
        "requires=gdal:",
        "not-run",
        'reason="why"',
        "requires=postgresql requires=old-database",
    ],
)
def test_invalid_control_values_are_rejected(tmp_path, comment):
    bad = example("T", "t.a", "x").replace(
        "    ```sh", f"    <!-- example: {comment} -->\n    ```sh"
    )
    with pytest.raises(me.ManualFormatError):
        me.parse_manual(write(tmp_path, manual(bad)))


def test_known_control_values_are_accepted(tmp_path):
    for comment in ("requires=old-database", "requires=gdal:GPKG"):
        folder = tmp_path / comment.replace(":", "_")
        folder.mkdir()
        ok = example("T", "t.a", "x").replace(
            "    ```sh", f"    <!-- example: {comment} -->\n    ```sh"
        )
        parsed = me.parse_manual(write(folder, manual(ok)))
        assert parsed.examples[0].blocks[0].control == {
            "requires": comment.split("=")[1]
        }


def test_a_control_comment_without_a_code_block_is_an_error(tmp_path):
    bad = example("T", "t.a", "x").replace(
        "    ```sh\n    t.a\n    ```",
        "    ```sh\n    t.a\n    ```\n    <!-- example: requires=postgresql -->\n",
    )
    with pytest.raises(me.ManualFormatError):
        me.parse_manual(write(tmp_path, manual(bad)))


def test_images_of_an_example_are_listed(tmp_path):
    first = example("First", "t.a", "x", extra="![a](t_x_a.png)\n\n")
    second = example("Second", "t.b", "y")
    parsed = me.parse_manual(write(tmp_path, manual(first, second)))
    assert parsed.examples[0].images == ("t_x_a.png",)
    assert parsed.examples[1].images == ("t_x_a.png",)
    assert parsed.examples[2].images == ()
    assert parsed.examples[3].images == ()
    assert parsed.images == ("t_x_a.png",)


def test_images_outside_the_examples_belong_to_the_manual_only(tmp_path):
    text = "## DESCRIPTION\n\n![d](t_x_d.png)\n\n" + manual(
        example("First", "t.a", "x", extra="![a](t_x_a.png)\n\n")
    )
    parsed = me.parse_manual(write(tmp_path, text))
    assert parsed.images == ("t_x_d.png", "t_x_a.png")
    assert parsed.examples[0].images == ("t_x_a.png",)


def test_the_project_comment_is_read(tmp_path):
    head = "<!-- example-project: crs=EPSG:3358 -->\n\n"
    parsed = me.parse_manual(write(tmp_path, manual(example("T", "a", "b"), head=head)))
    assert parsed.project == {"crs": "EPSG:3358"}
    other = tmp_path / "o"
    other.mkdir()
    plain = me.parse_manual(write(other, manual(example("T", "a", "b"))))
    assert plain.project == {}


def test_a_manual_without_examples_has_none(tmp_path):
    parsed = me.parse_manual(write(tmp_path, "## DESCRIPTION\n\nText.\n"))
    assert parsed.examples == ()


SHELL_ONLY = "<!-- example: shell-only -->\n\n"


def shell_only(title, shell):
    """Return one ### section of a catalog: the comment and a shell tab only"""
    return f"### {title}\n\n{SHELL_ONLY}" + tab("Command line", shell) + "\n"


def test_shell_only_example_has_no_python_tab(tmp_path):
    text = manual(
        example("Full", "t.a", "tools.t_a()"),
        shell_only("Catalog", "```sh\nt.b\n```\n\n```text\nout\n```"),
    )
    parsed = me.parse_manual(write(tmp_path, text))
    got = [(e.title, e.variant, e.shell_only) for e in parsed.examples]
    assert got == [
        ("Full", "shell", False),
        ("Full", "python", False),
        ("Catalog", "shell", True),
    ]
    assert parsed.examples[2].blocks[0].code == "t.b\n"
    assert parsed.examples[2].blocks[0].shown_output == "out\n"


@pytest.mark.parametrize(
    "place",
    ["after prose", "indented", "inside the tab", "before the heading", "with a key"],
)
def test_shell_only_must_follow_the_heading(tmp_path, place):
    body = tab("Command line", "```sh\nt.b\n```")
    sections = {
        "after prose": f"### Catalog\n\nProse.\n\n{SHELL_ONLY}{body}",
        "indented": f"### Catalog\n\n    {SHELL_ONLY}{body}",
        "inside the tab": f"### Catalog\n\n{body}\n    {SHELL_ONLY}",
        "before the heading": f"{SHELL_ONLY}### Catalog\n\n{body}",
        "with a key": (
            "### Catalog\n\n<!-- example: shell-only requires=postgresql -->\n\n" + body
        ),
    }
    text = manual(example("Full", "t.a", "x"), sections[place])
    path = write(tmp_path, text)
    with pytest.raises(me.ManualFormatError) as excinfo:
        me.parse_manual(path)
    line = next(
        number for number, row in enumerate(text.split("\n"), 1) if "shell-only" in row
    )
    assert excinfo.value.path == path
    assert excinfo.value.line == line
    assert f"{path}:{line}:" in str(excinfo.value)
    assert "shell-only" in str(excinfo.value)


def test_an_example_without_python_tab_is_still_refused(tmp_path):
    # The comment of one example does not carry over to the next.
    text = manual(
        shell_only("Catalog", "```sh\nt.b\n```"),
        "### Lonely\n\n" + tab("Command line", "```sh\nt.a\n```"),
    )
    with pytest.raises(me.ManualFormatError) as excinfo:
        me.parse_manual(write(tmp_path, text))
    message = str(excinfo.value)
    assert "Lonely" in message
    assert "'Python (grass.tools)' is missing" in message


def test_a_shell_only_example_with_a_python_tab_is_an_error(tmp_path):
    text = manual(example("Both", "t.a", "x").replace("\n\n", f"\n\n{SHELL_ONLY}", 1))
    with pytest.raises(me.ManualFormatError, match=r"shell-only.*Python"):
        me.parse_manual(write(tmp_path, text))


CONTEXT = me.NormalizeContext(database="/tmp/work/db", user="soeren")


def test_normalize_replaces_the_database_user_and_creation_times():
    shown = (
        " | Creator: ................... soeren\n"
        " | Creation time: ............. 2026-11-01 23:14:05\n"
        " | Modification time:.......... 2026-11-01 23:14:06\n"
        "creator=soeren\n"
        "creation_time='2026-11-01 23:14:05'\n"
        "modification_time='2026-11-01 23:14:06'\n"
        "database:/tmp/work/db/temporal_examples/PERMANENT\n"
    )
    assert me.normalize(shown, CONTEXT) == (
        " | Creator: ................... user\n"
        " | Creation time: ............. 2026-11-01 12:00:00\n"
        " | Modification time:.......... 2026-11-01 12:00:00\n"
        "creator=user\n"
        "creation_time='2026-11-01 12:00:00'\n"
        "modification_time='2026-11-01 12:00:00'\n"
        "database:/home/user/grassdata/temporal_examples/PERMANENT\n"
    )


def test_normalize_keeps_a_user_name_outside_the_creator_fields():
    context = me.NormalizeContext(database="/db", user="a")
    shown = "Creator: ... a\nName: banana\nmapset a\n"
    assert me.normalize(shown, context) == (
        "Creator: ... user\nName: banana\nmapset a\n"
    )


def test_normalize_replaces_the_time_of_the_command_history():
    shown = " | Command history:\n | # 2026-11-01 23:14:05 \n | t.create\n"
    assert me.normalize(shown, CONTEXT) == (
        " | Command history:\n | # 2026-11-01 12:00:00 \n | t.create\n"
    )


def test_normalize_keeps_values_next_to_a_replaced_time():
    shown = "| Creation time: ... 2026-11-01 23:14:05 | min: 3 |\n"
    got = me.normalize(shown, CONTEXT)
    assert got == "| Creation time: ... 2026-11-01 12:00:00 | min: 3 |\n"
    changed = shown.replace("min: 3", "min: 4")
    assert me.normalize(changed, CONTEXT) != got


def test_normalize_keeps_a_time_outside_the_labelled_fields():
    shown = "Start time: 2020-01-01 00:00:00\n"
    assert me.normalize(shown, CONTEXT) == shown


def test_normalize_replaces_the_hex_of_the_register_table_name():
    one = " | Raster register table:...... raster_map_register_" + "a" * 32 + "\n"
    two = one.replace("a" * 32, "b" * 32)
    assert me.normalize(one, CONTEXT) == me.normalize(two, CONTEXT)
    assert me.normalize(one, CONTEXT).startswith(" | Raster register table:")
    vector = one.replace("raster_map", "vector_map")
    assert me.normalize(vector, CONTEXT) != me.normalize(one, CONTEXT)
    assert "raster_map_register_" + "a" * 32 not in me.normalize(one, CONTEXT)
    other = "register=raster_map_register_" + "a" * 32 + " | min: 3\n"
    assert me.normalize(other, CONTEXT).endswith(" | min: 3\n")


def test_normalize_keeps_a_comment_line_that_starts_with_a_time():
    shown = "# 2020-01-01 00:00:00 start\n"
    assert me.normalize(shown, CONTEXT) == shown


def test_a_closing_fence_with_trailing_spaces_closes_the_block(tmp_path):
    shell = "```sh\nt.a\n```  \n\n```text\nout\n```"
    text = manual(
        "### T\n\n"
        + tab("Command line", shell)
        + "\n"
        + tab("Python (grass.tools)", "```python\nx\n```")
    )
    parsed = me.parse_manual(write(tmp_path, text))
    assert parsed.examples[0].blocks[0].shown_output == "out\n"


def test_timeout_grows_with_the_blocks(tmp_path):
    def catalog(count, not_run=0):
        code = "\n\n".join(["```sh\nt.a\n```"] * count)
        skipped = '<!-- example: not-run reason="x" -->\n```sh\nt.b\n```'
        code += "".join(f"\n\n{skipped}" for _ in range(not_run))
        return example("Full", "t.a", "x") + "\n" + shell_only("Catalog", code)

    folder = tmp_path / "small"
    folder.mkdir()
    small = me.parse_manual(write(folder, manual(catalog(3))))
    # Below the floor, both tabs get the 300 s of the repository.
    assert me.timeout_for(small, "shell") == 300
    assert me.timeout_for(small, "python") == 300
    blocks = 300 // me.SECONDS_PER_BLOCK + 10
    folder = tmp_path / "large"
    folder.mkdir()
    large = me.parse_manual(write(folder, manual(catalog(blocks - 1, not_run=7))))
    # The full example adds one block; the blocks marked not-run do not count.
    assert me.timeout_for(large, "shell") == me.SECONDS_PER_BLOCK * blocks
    assert me.timeout_for(large, "python") == 300
