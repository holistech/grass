"""Test the encoding that grass.script uses for the bytes of tool output"""

import os
import subprocess
import sys

from grass.tools import Tools

DESCRIPTION = "Précipitation totale mensuelle NC"


def run_python(*args):
    """Run the interpreter under LC_ALL=C and return the decoded stdout"""
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "LC_ALL": "C"},
    ).stdout.strip()


def test_get_encoding_is_utf8_in_the_utf8_mode():
    # sys.flags is read-only, so the mode is switched on for a fresh
    # interpreter. locale.getencoding() reports ASCII under LC_ALL=C even in
    # this mode.
    code = "from grass.script.utils import _get_encoding; print(_get_encoding())"
    assert run_python("-X", "utf8", "-c", code) == "UTF-8"


def test_get_encoding_follows_the_locale_outside_the_utf8_mode():
    # Only the mode may change the answer: a program that runs in a real
    # non-UTF-8 locale without the mode keeps decoding with that locale.
    code = (
        "import locale;"
        "from grass.script.utils import _get_encoding;"
        "print(_get_encoding() == locale.getencoding())"
    )
    assert run_python("-X", "utf8=0", "-c", code) == "True"


def test_decode_and_encode_use_utf8_in_the_utf8_mode():
    code = (
        "from grass.script.utils import decode, encode;"
        "print(decode(encode('S\\u00fcdtirol')))"
    )
    assert run_python("-X", "utf8", "-c", code) == "Südtirol"


def test_python_tool_with_non_ascii_argument_under_lc_all_c(empty_session):
    # With LC_ALL=C Python switches to its UTF-8 mode (PEP 540) but
    # locale.getencoding() still reports ASCII, so g.parser output with the
    # argument could not be decoded and every Python tool failed.
    empty_session.env["LC_ALL"] = "C"
    tools = Tools(
        session=empty_session, consistent_return_value=True, capture_stderr=True
    )
    tools.t_create(output="pluies", title="t", description=DESCRIPTION)
    assert DESCRIPTION in tools.t_info(type="strds", input="pluies").stdout
