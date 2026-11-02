# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Tests of running, comparing and covering the examples of a temporal manual

Each test writes a small manual to tmp_path. The tests that run examples do
so in a real session in a project of their own under tmp_path.
"""

import re
import struct
import zlib

import pytest

import grass.script as gs
from grass.temporal.testing import manual_coverage as mc
from grass.temporal.testing import manual_examples as me
from grass.temporal.testing.postgresql import SERVER_VARIABLE
from grass.temporal.testing.session import project_session


def tab(label, body):
    """Return a tab of the manual layout with its content indented by four"""
    lines = [f'=== "{label}"', ""]
    lines += [("    " + line) if line else "" for line in body.split("\n")]
    return "\n".join(lines) + "\n"


def blocks(language, *items):
    """Return code blocks, each item a code or a (code, shown output) pair"""
    parts = []
    for item in items:
        code, shown = item if isinstance(item, tuple) else (item, None)
        parts.append(f"```{language}\n{code}```")
        if shown is not None:
            parts.append(f"```text\n{shown}```")
    return "\n\n".join(parts)


def example(title, shell, python, after=""):
    """Return one ### section with both tabs and text after them"""
    return (
        f"### {title}\n\n"
        + tab("Command line", shell)
        + "\n"
        + tab("Python (grass.tools)", python)
        + "\n"
        + after
    )


def write_manual(tmp_path, *sections, tool="t.x"):
    folder = tmp_path / "manual" / tool
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{tool}.md"
    path.write_text(
        "## DESCRIPTION\n\nText.\n\n## EXAMPLES\n\n"
        + "\n".join(sections)
        + "\n## SEE ALSO\n\n*t.info*\n"
    )
    return me.parse_manual(path)


@pytest.fixture
def session(tmp_path):
    """Session in an XY project of its own; the region is 3 rows, 2 columns"""
    with project_session(tmp_path / "grassdata" / "temporal_examples") as session:
        gs.run_command("g.region", n=3, s=0, e=2, w=0, res=1, env=session.env)
        yield session


def png(width, height):
    """Return a minimal grey PNG of the given size"""

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    rows = b"".join(b"\0" + b"\0" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def test_one_changed_character_in_a_shown_output_fails(tmp_path, session):
    printed = gs.read_command("g.region", flags="p", env=session.env)
    changed = printed.replace("rows:       3", "rows:       4")
    assert changed != printed
    python = blocks("python", "print(1)\n")

    right = write_manual(
        tmp_path, example("Region", blocks("sh", ("g.region -p\n", printed)), python)
    )
    me.check_manual(right, "shell", session, tmp_path / "right")

    wrong = write_manual(
        tmp_path, example("Region", blocks("sh", ("g.region -p\n", changed)), python)
    )
    with pytest.raises(AssertionError) as excinfo:
        me.check_manual(wrong, "shell", session, tmp_path / "wrong")
    message = str(excinfo.value)
    assert str(wrong.path) in message
    assert "'Region'" in message
    assert "line 11" in message
    assert "-rows:       4\n+rows:       3" in message
    assert "@@" in message


@pytest.mark.parametrize("variant", ["shell", "python"])
def test_a_failing_command_shows_its_stderr(tmp_path, session, variant):
    manual = write_manual(
        tmp_path,
        example(
            "Missing map",
            # Without -e and pipefail, bash would end the block with 0.
            blocks(
                "sh",
                "g.region -p\n",
                "r.info map=missing | cat\necho after\n",
                "g.region -p\n",
            ),
            blocks(
                "python",
                "from grass.tools import Tools\n\ntools = Tools()\n",
                'tools.r_info(map="missing")\n',
                "print(2)\n",
            ),
        ),
    )
    with pytest.raises(AssertionError) as excinfo:
        me.check_manual(manual, variant, session, tmp_path / "work")
    message = str(excinfo.value)
    assert "Raster map <missing> not found" in message
    assert str(manual.path) in message
    assert "'Missing map'" in message
    failing = manual.examples[0 if variant == "shell" else 1].blocks[1]
    assert f"line {failing.line}" in message
    assert variant in message

    results = me.run_manual(manual, variant, session, tmp_path / "again")
    assert [r.returncode for r in results[:2]] == [0, 1]
    assert results[2].skipped
    assert str(failing.line) in results[2].skipped


def test_python_blocks_share_a_namespace(tmp_path, session):
    python = blocks(
        "python",
        (
            "from grass.tools import Tools\n\ntools = Tools()\nprint('ready')\n",
            "ready\n",
        ),
        ('print(tools.g_region(flags="g").keyval["rows"])\n', "3\n"),
    )
    manual = write_manual(tmp_path, example("Shared", blocks("sh", "true\n"), python))
    results = me.run_manual(manual, "python", session, tmp_path / "work")
    assert [(r.stdout, r.returncode, r.skipped) for r in results] == [
        ("ready\n", 0, None),
        ("3\n", 0, None),
    ]
    me.check_manual(manual, "python", session, tmp_path / "work")


def test_a_python_block_that_ends_the_process_fails_the_next(tmp_path, session):
    python = blocks("python", "import sys\n\nsys.exit(0)\n", "print(1)\n")
    manual = write_manual(tmp_path, example("Exit", blocks("sh", "true\n"), python))
    results = me.run_manual(manual, "python", session, tmp_path / "work")
    assert [r.returncode for r in results] == [0, 1]
    assert "ended before this block" in results[1].stderr


@pytest.mark.parametrize("variant", ["shell", "python"])
def test_a_hanging_block_is_stopped(tmp_path, session, monkeypatch, variant):
    monkeypatch.setattr(me, "BLOCK_SECONDS", 1)
    manual = write_manual(
        tmp_path,
        example(
            "Hang",
            blocks("sh", "sleep 60\n"),
            blocks("python", "import time\n\ntime.sleep(60)\n"),
        ),
    )
    results = me.run_manual(manual, variant, session, tmp_path / "work")
    assert results[0].returncode < 0
    assert "Stopped after 1 s" in results[0].stderr


VERSION = (
    "import sqlite3\n"
    "import grass.script as gs\n"
    "\n"
    "env = gs.gisenv()\n"
    "path = f\"{env['GISDBASE']}/{env['LOCATION_NAME']}/{env['MAPSET']}/tgis/sqlite.db\"\n"
    "query = \"SELECT value FROM tgis_metadata WHERE key = 'tgis_db_version'\"\n"
    "print(sqlite3.connect(path).execute(query).fetchone()[0])\n"
)


def test_old_database_turns_the_database_into_version_2(tmp_path):
    shell = (
        blocks("sh", "t.info -d > /dev/null\n")
        + "\n\n<!-- example: requires=old-database -->\n"
        + blocks("sh", ("python3 version.py\n", "2\n"))
    )
    python = (
        blocks(
            "python", ("from grass.tools import Tools\n\nTools().t_info(flags='d')\n")
        )
        + "\n\n<!-- example: requires=old-database -->\n"
        + blocks("python", (VERSION, "2\n"))
    )
    manual = write_manual(tmp_path, example("Old", shell, python))
    for variant in ("shell", "python"):
        workdir = tmp_path / variant
        workdir.mkdir()
        (workdir / "version.py").write_text(VERSION)
        with project_session(tmp_path / variant / "project") as session:
            me.check_manual(manual, variant, session, workdir)


def test_shown_options_counts_names_flags_and_keywords(tmp_path):
    shell = blocks(
        "sh",
        "t.create output=a type=strds \\\n    --overwrite | cat\n",
        "t.info input=a temporaltype=x\nt.create -gs\n",
    )
    shell += '\n\n<!-- example: not-run reason="shown only" -->\n' + blocks(
        "sh", "t.create temporaltype=relative\n"
    )
    python = blocks(
        "python",
        'tools.t_create(semantictype="sum", flags="g", overwrite=True)\n'
        'tools.t_info(title="x")\n',
    )
    manual = write_manual(tmp_path, example("Options", shell, python), tool="t.create")
    assert mc.shown_options(manual) == {"output", "type", "-g", "-s", "semantictype"}


def test_shell_calls_follow_continuations_pipes_and_comments():
    code = (
        "X=1 t.a a=1 \\\n    b=2 | t.a c=3 > t.a\n"
        "echo x  # t.a d=4\n"
        't.a -e; t.a f="x | y"\n'
    )
    assert me.shell_calls(code, "t.a") == [
        ["a=1", "b=2"],
        ["c=3"],
        ["-e"],
        ["f=x | y"],
    ]


def test_shell_calls_take_a_comment_only_where_a_word_starts():
    # An apostrophe in a comment is no quote; a # within a word or within
    # quotes starts no comment.
    code = (
        "# set the region's extent\n"
        "t.a a=1  # the map's name\n"
        "t.a b=x#y c=\"# z\" d='#'\n"
    )
    assert me.shell_calls(code, "t.a") == [["a=1"], ["b=x#y", "c=# z", "d=#"]]


def test_shell_calls_leave_out_the_body_of_a_here_document():
    code = (
        "cat > list.txt <<EOF\n"
        "t.a a=1\n"
        "it's\n"
        "EOF\n"
        "t.a b=1 <<-'END' # it's\n"
        "\tt.a c=1\n"
        "\tEND\n"
        "t.a d=1 <<< 't.a e=1'\n"
        "t.a f=1\n"
    )
    assert me.shell_calls(code, "t.a") == [["b=1"], ["d=1"], ["f=1"]]


def test_shell_calls_find_a_command_after_a_keyword():
    code = (
        "for m in a b; do t.a input=$m; done\n"
        "if t.a -e; then t.a f=1; elif t.a g=1; then :; else t.a h=1; fi\n"
        "while t.a i=1; do :; done; until t.a j=1; do :; done\n"
        "! t.a k=1\n"
        "{ t.a l=1; }\n"
        "time t.a m=1\n"
    )
    assert me.shell_calls(code, "t.a") == [
        ["input=$m"],
        ["-e"],
        ["f=1"],
        ["g=1"],
        ["h=1"],
        ["i=1"],
        ["j=1"],
        ["k=1"],
        ["l=1"],
        ["m=1"],
    ]


def test_a_shell_block_that_cannot_be_read_names_its_line(tmp_path, session):
    # bash takes $'...' with an escaped quote, shlex does not.
    unreadable = "echo $'it\\'s'\n"
    with pytest.raises(ValueError, match="quotation"):
        me.shell_calls(unreadable, "t.create")
    python = blocks("python", 'tools.t_create(output="a")\n')
    manual = write_manual(
        tmp_path,
        example("Quote", blocks("sh", unreadable), python),
        tool="t.create",
    )
    where = f"{manual.path}:{manual.examples[0].blocks[0].line}:"
    with pytest.raises(me.ManualFormatError, match=re.escape(where)):
        mc.shown_options(manual)

    drawing = image_manual(tmp_path, unreadable + DRAW, "unreadable")
    where = f"{drawing.path}:{drawing.examples[0].blocks[0].line}:"
    with pytest.raises(me.ManualFormatError, match=re.escape(where)):
        me.check_manual(drawing, "shell", session, tmp_path / "unreadable" / "work")


def test_a_block_runs_where_its_gdal_driver_exists(tmp_path, session):
    gdal = pytest.importorskip("osgeo.gdal")
    assert gdal.GetDriverByName("GTiff") is not None
    shell = "<!-- example: requires=gdal:GTiff -->\n" + blocks("sh", "echo ran\n")
    manual = write_manual(
        tmp_path, example("GDAL", shell, blocks("python", "print(1)\n"))
    )
    results = me.run_manual(manual, "shell", session, tmp_path / "work")
    assert (results[0].stdout, results[0].skipped) == ("ran\n", None)


def test_a_skipped_block_names_its_condition(tmp_path, session, monkeypatch):
    monkeypatch.delenv(SERVER_VARIABLE, raising=False)
    shell = (
        "<!-- example: requires=postgresql -->\n"
        + blocks("sh", "exit 3\n")
        + "\n\n<!-- example: requires=gdal:NoSuchDriver -->\n"
        + blocks("sh", "exit 4\n")
        + '\n\n<!-- example: not-run reason="needs a network" -->\n'
        + blocks("sh", "exit 5\n")
        + "\n\n"
        + blocks("sh", ("echo ran\n", "ran\n"))
    )
    python = (
        "<!-- example: requires=postgresql -->\n"
        + blocks("python", "raise SystemExit(3)\n")
        + "\n\n"
        + blocks("python", ("print('ran')\n", "ran\n"))
    )
    manual = write_manual(tmp_path, example("Skipped", shell, python))

    results = me.run_manual(manual, "shell", session, tmp_path / "shell")
    assert SERVER_VARIABLE in results[0].skipped
    assert "postgresql" in results[0].skipped
    assert "NoSuchDriver" in results[1].skipped
    assert results[2].skipped == "not-run: needs a network"
    assert (results[3].stdout, results[3].skipped) == ("ran\n", None)

    results = me.run_manual(manual, "python", session, tmp_path / "python")
    assert "postgresql" in results[0].skipped
    assert (results[1].stdout, results[1].returncode) == ("ran\n", 0)
    me.check_manual(manual, "shell", session, tmp_path / "shell")
    me.check_manual(manual, "python", session, tmp_path / "python")


def image_manual(tmp_path, shell, name):
    python = blocks(
        "python",
        "from grass.tools import Tools\n\ntools = Tools()\n"
        'tools.d_mon(start="cairo", output="x.png", width=60, height=40)\n'
        "tools.d_erase()\n"
        'tools.d_mon(stop="cairo")\n',
    )
    figure = "![A figure](x.png)\n\n*Figure: a figure*\n"
    folder = tmp_path / name
    folder.mkdir()
    return write_manual(folder, example("Figure", blocks("sh", shell), python, figure))


DRAW = "d.mon start=cairo output=x.png width=60 height=40\nd.erase\nd.mon stop=cairo\n"


def test_an_image_must_exist_with_the_given_size(tmp_path, session):
    good = image_manual(tmp_path, DRAW, "good")
    me.check_manual(good, "shell", session, tmp_path / "good" / "shell")
    me.check_manual(good, "python", session, tmp_path / "good" / "python")

    undrawn = "d.mon start=cairo output=x.png width=60 height=40\nd.mon stop=cairo\n"
    missing = image_manual(tmp_path, undrawn, "missing")
    with pytest.raises(AssertionError, match=r"x\.png.*does not exist"):
        me.check_manual(missing, "shell", session, tmp_path / "missing" / "work")

    replace = DRAW + "printf 'not a png' > x.png\n"
    broken = image_manual(tmp_path, replace, "broken")
    with pytest.raises(AssertionError, match=r"x\.png.*not a PNG"):
        me.check_manual(broken, "shell", session, tmp_path / "broken" / "work")

    workdir = tmp_path / "small_work"
    workdir.mkdir(parents=True)
    (workdir / "small.png").write_bytes(png(30, 20))
    small = image_manual(tmp_path, DRAW + "cp small.png x.png\n", "small")
    with pytest.raises(AssertionError, match=r"x\.png.*30 x 20.*60 x 40"):
        me.check_manual(small, "shell", session, workdir)

    nowhere = image_manual(tmp_path, "true\n", "nowhere")
    with pytest.raises(AssertionError, match=r"no d\.mon .*x\.png"):
        me.check_manual(nowhere, "shell", session, tmp_path / "nowhere" / "work")


def test_escaped_html_matches_the_markdown_block(tmp_path):
    shell = blocks("sh", ("t.info input=a\n", "ERROR: Dataset <name@mapset> & b\n"))
    python = blocks("python", 'tools.t_info(input="a")\n')
    manual = write_manual(
        tmp_path, example("Escaped", shell, python, "![A figure](t_x_a.png)\n")
    )
    pre = (
        "<pre>\nt.info input=a\n</pre>\n"
        "<pre>\nERROR: Dataset &lt;name@mapset&gt; &amp; b\n</pre>\n"
        '<p>Python (grass.tools):</p>\n<div class="code"><pre>\n'
        'tools.t_info(input="a")\n</pre></div>\n'
    )
    page = (
        "<h2>DESCRIPTION</h2>\n<p>Text.</p>\n<h2>EXAMPLES</h2>\n"
        + pre
        + '<img src="t_x_a.png" alt="A figure">\n<h2>SEE ALSO</h2>\n'
    )
    html_path = manual.path.with_suffix(".html")
    html_path.write_text(page)
    assert mc.check_html_sync(manual, html_path) == []

    # Unescaped, the map name is a tag to an HTML reader, not text.
    html_path.write_text(page.replace("&lt;name@mapset&gt;", "<name@mapset>"))
    missing = mc.check_html_sync(manual, html_path)
    assert len(missing) == 1
    assert "Dataset <name@mapset> & b" in missing[0]

    gaps = page.replace("<pre>\nt.info input=a\n</pre>\n", "")
    gaps = gaps.replace("<h2>SEE ALSO</h2>", "<h3>SEE ALSO</h3>")
    html_path.write_text(gaps.replace('src="t_x_a.png"', 'src="other.png"'))
    missing = mc.check_html_sync(manual, html_path)
    assert len(missing) == 3
    assert any("t.info input=a" in item for item in missing)
    assert any("t_x_a.png" in item for item in missing)
    assert any("SEE ALSO" in item for item in missing)


def test_blanks_at_line_ends_do_not_count_in_the_html(tmp_path):
    shell = blocks("sh", ("t.info input=a\n", " | # 2026-11-01 12:00:00 \n | \n"))
    python = blocks("python", 'tools.t_info(input="a")\n')
    manual = write_manual(tmp_path, example("Blanks", shell, python))
    page = (
        "<h2>DESCRIPTION</h2>\n<h2>EXAMPLES</h2>\n"
        "<pre>\nt.info input=a\n</pre>\n"
        "<pre>\n | # 2026-11-01 12:00:00\n |\n</pre>\n"
        '<pre>\ntools.t_info(input="a")\n</pre>\n<h2>SEE ALSO</h2>\n'
    )
    html_path = manual.path.with_suffix(".html")
    # As the trailing-whitespace hook of pre-commit leaves the .html.
    html_path.write_text(page)
    assert mc.check_html_sync(manual, html_path) == []

    # Blanks that only the .html has do not count either.
    html_path.write_text(page.replace("input=a\n", "input=a  \n"))
    assert mc.check_html_sync(manual, html_path) == []

    html_path.write_text(page.replace("12:00:00\n", "12:00:01\n"))
    missing = mc.check_html_sync(manual, html_path)
    assert len(missing) == 1
    assert "12:00:00" in missing[0]


def test_tool_options_lists_parameters_and_short_flags(session):
    options = mc.tool_options("t.create", session.env)
    assert options == {
        "output",
        "type",
        "temporaltype",
        "semantictype",
        "title",
        "description",
    }
    assert mc.tool_options("t.info", session.env) == {"input", "type", "-g", "-h", "-d"}
