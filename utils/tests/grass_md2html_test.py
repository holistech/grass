# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Tests of the generator of HTML manual pages from Markdown"""

import importlib.util
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

GENERATOR = Path(__file__).parents[1] / "grass_md2html.py"

# utils/ is no package that the tests could import from; the generator is a
# script, so it is loaded from its file.
_spec = importlib.util.spec_from_file_location("grass_md2html", GENERATOR)
md2html = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md2html)


def convert(markdown):
    return md2html.convert(dedent(markdown).lstrip("\n"), "manual.md")


def refusal(markdown):
    with pytest.raises(md2html.UnsupportedMarkdown) as caught:
        convert(markdown)
    return caught.value


def test_headings_become_h2_to_h4():
    html = convert(
        """
        ## DESCRIPTION

        ### An example

        #### A detail
        """
    )
    assert html == (
        "<h2>DESCRIPTION</h2>\n\n<h3>An example</h3>\n\n<h4>A detail</h4>\n"
    )


def test_paragraph_after_heading_is_bare_and_later_ones_open_with_p():
    html = convert(
        """
        ## NOTES

        First paragraph,
        two lines.

        Second paragraph.
        """
    )
    assert html == (
        "<h2>NOTES</h2>\n\nFirst paragraph,\ntwo lines.\n\n<p>\nSecond paragraph.\n"
    )


def test_two_blanks_at_line_end_are_a_line_break_but_not_at_paragraph_end():
    html = convert("First line.  \nSecond line.  \n\nNext.\n")
    assert html == "First line.<br>\nSecond line.\n\n<p>\nNext.\n"


def test_bullet_list():
    html = convert(
        """
        - `strds`, raster
            maps;
        - `stvds`, vector maps.
        """
    )
    assert html == (
        "<ul>\n<li><code>strds</code>, raster\nmaps;</li>\n"
        "<li><code>stvds</code>, vector maps.</li>\n</ul>\n"
    )


def test_ordered_list_with_paragraph_and_code_in_an_item():
    html = convert(
        """
        1. **First.** Text:

            ```sh
            C = A
            ```

        2. **Second.**

            More text.
        """
    )
    assert html == (
        "<ol>\n<li><b>First.</b> Text:\n\n"
        '<div class="code"><pre>\nC = A\n</pre></div>\n</li>\n'
        "<li><b>Second.</b>\n\n<p>\nMore text.</li>\n</ol>\n"
    )


def test_ordered_list_keeps_its_start_number():
    html = convert("3. third\n4. fourth\n")
    assert html == '<ol start="3">\n<li>third</li>\n<li>fourth</li>\n</ol>\n'


def test_nested_list():
    html = convert(
        """
        - outer

            - inner

        - next
        """
    )
    assert html == (
        "<ul>\n<li>outer\n\n<ul>\n<li>inner</li>\n</ul>\n</li>\n<li>next</li>\n</ul>\n"
    )


@pytest.mark.parametrize("marker", ["-", "1."])
@pytest.mark.parametrize("blanks", [1, 2, 3, 5, 6, 7])
def test_list_content_indented_wrongly_is_refused(marker, blanks):
    """Python-Markdown (MkDocs) counts list content from four blanks on"""
    error = refusal(f"{marker} item\n\n{' ' * blanks}more text\n")
    assert (error.path, error.line) == ("manual.md", 3)
    assert "list content must be indented by 4 spaces per level" in str(error)


@pytest.mark.parametrize("marker", ["-", "1."])
@pytest.mark.parametrize("blanks", [2, 3])
def test_list_code_fence_indented_wrongly_is_refused(marker, blanks):
    pad = " " * blanks
    error = refusal(f"{marker} item:\n\n{pad}```sh\n{pad}C = A\n{pad}```\n")
    assert (error.path, error.line) == ("manual.md", 3)
    assert "list content must be indented by 4 spaces per level" in str(error)


def test_list_closing_fence_indented_wrongly_is_refused():
    error = refusal("- item:\n\n    ```sh\n    C = A\n  ```\n")
    assert (error.path, error.line) == ("manual.md", 5)
    assert "list content must be indented by 4 spaces per level" in str(error)


@pytest.mark.parametrize("marker", ["-", "1."])
def test_list_content_indented_by_four_spaces_is_accepted(marker):
    html = convert(f"{marker} item:\n\n    ```sh\n    C = A\n    ```\n\n    More.\n")
    assert '<div class="code"><pre>\nC = A\n</pre></div>' in html
    assert html.count("<li>") == 1


def test_code_lines_in_a_list_fence_are_not_checked():
    """A code line may have any indentation; only the fences are checked"""
    html = convert("- item:\n\n    ```sh\n    C = A\n      + B\n   odd\n    ```\n")
    assert "C = A\n  + B\nodd\n" in html


def test_nested_list_content_indented_by_eight_spaces_is_accepted():
    html = convert(
        "- outer\n\n    - inner\n\n        ```sh\n        C = A\n        ```\n"
    )
    assert html.count("<ul>") == 2
    assert '<div class="code"><pre>\nC = A\n</pre></div>' in html


def test_nested_list_content_indented_by_six_spaces_is_refused():
    error = refusal("- outer\n\n    - inner\n\n      text\n")
    assert (error.path, error.line) == ("manual.md", 5)
    assert "list content must be indented by 4 spaces per level" in str(error)


def test_tab_inside_list_item():
    html = convert(
        "1. Run:\n\n"
        '    === "Command line"\n\n'
        "        ```sh\n        t.info input=A\n        ```\n"
    )
    assert html == (
        "<ol>\n<li>Run:\n\n<p>Command line:</p>\n\n"
        '<div class="code"><pre>\nt.info input=A\n</pre></div>\n</li>\n</ol>\n'
    )


@pytest.mark.parametrize("first", ["2", "1900"])
@pytest.mark.parametrize("blanks", [2, 3, 4])
@pytest.mark.parametrize("marker", ["-", "1."])
def test_wrapped_line_starting_with_number_and_dot_is_refused(marker, blanks, first):
    """CommonMark joins it to the paragraph, Python-Markdown makes it a list item"""
    error = refusal(f"{marker} year -\n{' ' * blanks}{first}. x\n")
    assert (error.path, error.line) == ("manual.md", 2)
    assert "must not start with a number and a dot" in str(error)


def test_number_with_dot_in_a_later_paragraph_stays_text():
    """Python-Markdown splits only the first block of an item into items"""
    html = convert("- a\n\n    para\n    2. x\n")
    assert "<p>\npara\n2. x</li>" in html


@pytest.mark.parametrize(
    "markdown",
    [
        "1. a\n\n    text\n2. b\n",
        "1. a:\n\n    ```sh\n    x\n    ```\n2. b\n",
        "- a\n\n    - b\n- c\n",
        '1. a\n\n    === "T"\n\n        ```sh\n        x\n        ```\n2. c\n',
        "- a\n\n    | x |\n    | - |\n    | 1 |\n- c\n",
    ],
)
def test_item_right_after_a_block_of_the_item_above_is_refused(markdown):
    error = refusal(markdown)
    assert error.path == "manual.md"
    assert "needs a blank line before it" in str(error)


def test_item_after_a_block_with_a_blank_line_is_accepted():
    html = convert("1. a\n\n    text\n\n2. b\n")
    assert html == "<ol>\n<li>a\n\n<p>\ntext</li>\n<li>b</li>\n</ol>\n"


def test_tight_items_stay_accepted():
    html = convert("- a\n  wrapped\n- c\n")
    assert html == "<ul>\n<li>a\nwrapped</li>\n<li>c</li>\n</ul>\n"


@pytest.mark.parametrize("marker", ["1.   a", "100. a", "-    a"])
def test_list_marker_wider_than_four_columns_is_refused(marker):
    error = refusal(f"{marker}\n\n        text\n")
    assert (error.path, error.line) == ("manual.md", 1)
    assert "at most 4 columns wide" in str(error)


@pytest.mark.parametrize("marker", ["1. a", "10. a", "- a"])
def test_list_marker_up_to_four_columns_is_accepted(marker):
    assert "<li>a</li>" in convert(f"{marker}\n")


def test_ordered_list_continues_its_numbers_after_a_code_block():
    html = convert(
        """
        1. One:

            ```sh
            A
            ```

        2. Two:

            ```sh
            B
            ```

        3. Three.
        """
    )
    assert html.startswith("<ol>\n")
    assert html.count("<ol") == 1
    assert html.count("<li>") == 3


def test_wrapped_item_text_is_not_checked():
    """A line that continues a paragraph is joined to it by both parsers"""
    html = convert("- first line\n  second line\n   third line\n- next\n")
    assert "<li>first line\nsecond line\nthird line</li>" in html


def test_wrapped_item_text_starting_with_a_number_is_not_checked():
    html = convert("- the year (year -\n  1900) * 12\n")
    assert "<li>the year (year -\n1900) * 12</li>" in html


def test_wrapped_number_with_dot_stays_text():
    """A line such as "0. The first ..." inside a paragraph starts no list,
    as an ordered list may only interrupt a paragraph with the number 1"""
    html = convert("cells are\n0. The first block\n")
    assert html == "cells are\n0. The first block\n"


def test_table():
    html = convert(
        """
        | Dataset | Maps |
        | --- | --- |
        | `A` | `a1` 1 to 6 |
        | `B` | `x \\| y` |
        """
    )
    assert html == (
        "<table>\n<tr><th>Dataset</th><th>Maps</th></tr>\n"
        "<tr><td><code>A</code></td><td><code>a1</code> 1 to 6</td></tr>\n"
        "<tr><td><code>B</code></td><td><code>x | y</code></td></tr>\n</table>\n"
    )


def test_tabs_become_labelled_blocks():
    html = convert(
        """
        === "Command line"

            ```sh
            t.info input=A
            ```

            ```text
            A
            ```

        === "Python (grass.tools)"

            ```python
            tools.t_info(input="A")
            ```
        """
    )
    assert html == (
        "<p>Command line:</p>\n\n"
        '<div class="code"><pre>\nt.info input=A\n</pre></div>\n\n'
        '<div class="code"><pre>\nA\n</pre></div>\n\n'
        "<p>Python (grass.tools):</p>\n\n"
        '<div class="code"><pre>\ntools.t_info(input="A")\n</pre></div>\n'
    )


def test_fence_indented_like_its_list_item_text():
    """CommonMark removes the indentation of the fence from its lines"""
    html = convert(
        """
        7. Text that
            goes on:

            ```sh
            C = A
              + B
            ```
        """
    )
    assert '<div class="code"><pre>\nC = A\n  + B\n</pre></div>' in html


def test_entities_in_pre():
    html = convert(
        """
        ```sh
        r.mapcalc "C = if(A < 2 && B > 1)"
        ```
        """
    )
    assert html == (
        '<div class="code"><pre>\n'
        'r.mapcalc "C = if(A &lt; 2 &amp;&amp; B &gt; 1)"\n'
        "</pre></div>\n"
    )


def test_blanks_at_line_end_are_dropped_in_pre():
    """The trailing-whitespace hook of pre-commit would drop them"""
    html = convert("```text\n| # 2026-11-01 \n```\n")
    assert html == '<div class="code"><pre>\n| # 2026-11-01\n</pre></div>\n'


def test_control_comments_are_dropped():
    html = convert(
        """
        ## EXAMPLES

        <!-- markdownlint-disable MD046 -->

        <!-- example: requires=gdal:GTiff -->

        Text.

        <!-- -->

        - item
        """
    )
    assert html == "<h2>EXAMPLES</h2>\n\nText.\n\n<ul>\n<li>item</li>\n</ul>\n"


def test_image():
    html = convert("![Maps of air temperature](t_rast_a.png)\n")
    assert html == '<img src="t_rast_a.png" alt="Maps of air temperature">\n'


def test_links_to_manuals_point_to_html_pages():
    html = convert(
        "*[t.info](t.info.md)*, [intro](temporalintro.md#concepts),\n"
        "[GRASS](https://grass.osgeo.org/a.md) and <https://doi.org/10.3390/x>\n"
    )
    assert html == (
        '<em><a href="t.info.html">t.info</a></em>, '
        '<a href="temporalintro.html#concepts">intro</a>,\n'
        '<a href="https://grass.osgeo.org/a.md">GRASS</a> and '
        '<a href="https://doi.org/10.3390/x">https://doi.org/10.3390/x</a>\n'
    )


def test_link_text_may_span_lines():
    html = convert("[Spatio-temporal data in GRASS\nGIS](https://example.org/)\n")
    assert (
        html
        == '<a href="https://example.org/">Spatio-temporal data in GRASS\nGIS</a>\n'
    )


def test_asterisk_in_code_stays_literal():
    html = convert("`C = A * 2` and `*` and `a*b*c`\n")
    assert html == (
        "<code>C = A * 2</code> and <code>*</code> and <code>a*b*c</code>\n"
    )


def test_code_span_with_angle_brackets_and_ampersand():
    html = convert("`Option <mapset> requires <-p>` and `&&`\n")
    assert html == (
        "<code>Option &lt;mapset&gt; requires &lt;-p&gt;</code> and "
        "<code>&amp;&amp;</code>\n"
    )


def test_code_span_may_span_lines():
    html = convert("refused with `Option <database> must not be\nempty`.\n")
    assert html == (
        "refused with <code>Option &lt;database&gt; must not be\nempty</code>.\n"
    )


def test_emphasis_and_bold():
    html = convert("*t.create* with **-p** and **--overwrite**, *(r\\|r3).x*\n")
    assert html == (
        "<em>t.create</em> with <b>-p</b> and <b>--overwrite</b>, <em>(r|r3).x</em>\n"
    )


def test_emphasis_spans_lines():
    html = convert("*[a](a.md),\n[b](b.md)*\n")
    assert html == '<em><a href="a.html">a</a>,\n<a href="b.html">b</a></em>\n'


def test_asterisk_between_blanks_stays_literal():
    html = convert("A * 2 and 3 * 4\n")
    assert html == "A * 2 and 3 * 4\n"


def test_backslash_escapes():
    html = convert("operator \\| and -\\> and strds\\[r,c,t\\] and \\*.timestamp\n")
    assert html == "operator | and -&gt; and strds[r,c,t] and *.timestamp\n"


def test_prose_ampersand_and_angle_brackets_are_escaped():
    html = convert("(\\| or &) and a < b, c > d\n")
    assert html == "(| or &amp;) and a &lt; b, c &gt; d\n"


def test_underscore_inside_a_word_stays_literal():
    html = convert("the mapset t_rast_aggregate\n")
    assert html == "the mapset t_rast_aggregate\n"


def test_characters_beyond_ascii_become_entities():
    html = convert(
        "S\u00f6ren, Th\u00fcnen, 5 \u00b0C, \u2264 1\n\n```text\n\u00e4\n```\n"
    )
    assert html == (
        "S&ouml;ren, Th&uuml;nen, 5 &deg;C, &le; 1\n\n"
        '<div class="code"><pre>\n&auml;\n</pre></div>\n'
    )


def test_front_matter_becomes_meta_comments_and_the_title_is_dropped():
    html = convert(
        """
        ---
        description: Temporal data processing in GRASS
        index: temporal
        ---

        # Temporal data processing in GRASS

        The temporal framework.

        ## Concepts
        """
    )
    assert html == (
        "<!-- meta page description: Temporal data processing in GRASS -->\n"
        "<!-- meta page index: temporal -->\n\n"
        "The temporal framework.\n\n<h2>Concepts</h2>\n"
    )


def test_title_other_than_the_description_is_refused():
    error = refusal(
        """
        ---
        description: Temporal data processing
        ---

        # Another title
        """
    )
    assert error.line == 5


@pytest.mark.parametrize(
    ("markdown", "line"),
    [
        pytest.param("Text\n\nA <div>raw</div> tag.\n", 3, id="raw-html"),
        pytest.param("Text\n\n    indented code\n", 3, id="indented-code"),
        pytest.param("Text\n\nan _emphasis_ here\n", 3, id="underscore-emphasis"),
        pytest.param("| a |\n| :-- |\n| b |\n", 1, id="table-alignment"),
        pytest.param("| a |\n| --- |\n| `x|y` |\n", 3, id="pipe-in-cell-code"),
        pytest.param("##### Deep\n", 1, id="heading-level-5"),
        pytest.param("- item\ncontinued\n", 2, id="lazy-line"),
        pytest.param("Text\n- item\n", 2, id="list-in-paragraph"),
        pytest.param("Text\n\n```sh\nC = A\n", 3, id="unclosed-fence"),
        pytest.param("Text with `code\n", 1, id="unclosed-code-span"),
        pytest.param("A &ouml; entity\n", 1, id="entity"),
        pytest.param('[a](a.md "title")\n', 1, id="link-title"),
        pytest.param("Line\\\nbreak\n", 1, id="backslash-break"),
        pytest.param('=== "Tab"\n\nnot indented\n', 1, id="empty-tab"),
        pytest.param("Text\n\n<!-- open\ncomment -->\n", 3, id="multi-line-comment"),
        pytest.param("---\ntitle: x\n---\n", 2, id="front-matter-key"),
        pytest.param("Text\n\n---\n", 3, id="thematic-break"),
        pytest.param("Title\n---\n", 2, id="setext-heading"),
        pytest.param("Text\n\n> quoted\n", 3, id="block-quote"),
        pytest.param("[a]: https://example.org/\n", 1, id="reference-definition"),
        pytest.param("!!! note\n    Text.\n", 1, id="admonition"),
        pytest.param("![a *b*](x.png)\n", 1, id="markup-in-image-text"),
        pytest.param("Text.\n\n~~~\nC = A*2*B\n~~~\n", 3, id="tilde-fence"),
        pytest.param("Text\n~~~\nC = A*2*B\n~~~\n", 2, id="tilde-fence-in-paragraph"),
        pytest.param("Text.\n\n````sh\nC = A\n````\n", 3, id="four-backtick-fence"),
        pytest.param("a | b\n--- | ---\nc | d\n", 2, id="table-without-outer-pipes"),
        pytest.param(
            "| a | b |\n| --- | --- |\n| c | d |\ne | f\n", 4, id="line-after-table"
        ),
        pytest.param("# Title\n\nText.\n", 1, id="title-without-front-matter"),
        pytest.param(
            "---\ndescription: T\n---\n\n# T\n\n# Second\n", 7, id="second-title"
        ),
    ],
)
def test_unknown_construct_names_file_and_line(markdown, line):
    with pytest.raises(md2html.UnsupportedMarkdown) as caught:
        md2html.convert(markdown, "temporal/t.x/t.x.md")
    assert caught.value.path == "temporal/t.x/t.x.md"
    assert caught.value.line == line
    assert str(caught.value).startswith(f"temporal/t.x/t.x.md:{line}: ")


def test_second_run_changes_nothing(tmp_path):
    manual = tmp_path / "t.x.md"
    manual.write_text("## DESCRIPTION\n\n*t.x* does `a * b`.\n", encoding="utf-8")
    first = run(manual)
    assert first.returncode == 0, first.stderr
    page = manual.with_suffix(".html")
    written = page.read_bytes()
    second = run(manual)
    assert second.returncode == 0, second.stderr
    assert page.read_bytes() == written
    assert written == convert(manual.read_text()).encode()
    check = run("--check", manual)
    assert (check.returncode, check.stdout) == (0, "")


def test_check_names_a_differing_page_and_writes_nothing(tmp_path):
    manual = tmp_path / "t.x.md"
    manual.write_text("## DESCRIPTION\n\nText.\n", encoding="utf-8")
    page = manual.with_suffix(".html")
    page.write_text("<h2>DESCRIPTION</h2>\n\nOther text.\n", encoding="utf-8")
    check = run("--check", manual)
    assert check.returncode == 1
    assert check.stdout == f"{page}\n"
    assert page.read_text(encoding="utf-8") == "<h2>DESCRIPTION</h2>\n\nOther text.\n"


def test_check_names_a_missing_page(tmp_path):
    manual = tmp_path / "t.x.md"
    manual.write_text("Text.\n", encoding="utf-8")
    check = run("--check", manual)
    assert (check.returncode, check.stdout) == (1, f"{manual.with_suffix('.html')}\n")


def test_unsupported_markdown_ends_the_script_with_file_and_line(tmp_path):
    manual = tmp_path / "t.x.md"
    manual.write_text("Text\n\n##### Deep\n", encoding="utf-8")
    result = run(manual)
    assert result.returncode == 2
    assert result.stderr.startswith(f"{manual}:3: ")
    assert not manual.with_suffix(".html").exists()


def run(*args):
    return subprocess.run(
        [sys.executable, str(GENERATOR), *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )
