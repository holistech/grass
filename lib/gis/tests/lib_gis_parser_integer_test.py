"""Test the check of integer options by the parser

The parser checks an option of type integer in libgis (check_int()). The
tests run a Python script, which has the options read by g.parser, in a
session.
"""

import subprocess
import sys

import pytest

SCRIPT = """\
#!/usr/bin/env python3

# %module
# % description: Print the integer options
# %end
# %option
# % key: number
# % description: One integer
# % type: integer
# % required: no
# %end
# %option
# % key: numbers
# % description: Several integers
# % type: integer
# % multiple: yes
# % required: no
# %end
# %option
# % key: pair
# % description: Rows and columns
# % key_desc: rows,columns
# % type: integer
# % required: no
# %end
# %option
# % key: ranged
# % description: One integer from 1 to 10
# % type: integer
# % options: 1-10
# % required: no
# %end

import grass.script as gs

if __name__ == "__main__":
    options, flags = gs.parser()
    print(
        "|".join(
            [options["number"], options["numbers"], options["pair"], options["ranged"]]
        )
    )
"""


@pytest.fixture
def run(xy_session_for_module, tmp_path):
    """Run the script with the arguments and return the finished process"""
    script = tmp_path / "integer_options.py"
    script.write_text(SCRIPT)

    def run_script(*arguments):
        return subprocess.run(
            [sys.executable, str(script), *arguments],
            env=xy_session_for_module.env,
            capture_output=True,
            text=True,
            check=False,
        )

    return run_script


@pytest.mark.parametrize("value", ["3", "+3", "-3", "007", "0", "2147483647"])
def test_an_integer_is_accepted(run, value):
    result = run(f"number={value}")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{value}|||"


@pytest.mark.parametrize(
    "value", ["2.5", "3abc", "3 4", "abc", "1e3", "0x10", "2147483648", "-2147483649"]
)
def test_a_number_with_trailing_characters_is_refused(run, value):
    result = run(f"number={value}")

    assert result.returncode != 0
    assert f"Invalid value <{value}> for parameter <number>" in result.stderr


def test_an_empty_value_counts_as_no_value(run):
    # The parser drops an empty answer before check_int() sees it; a required
    # option is then reported as not set.
    result = run("number=")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "|||"


def test_a_list_of_integers_is_accepted(run):
    result = run("numbers=1,-2,+3,007")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "|1,-2,+3,007||"


@pytest.mark.parametrize("value", ["1,2.5", "1,2x"])
def test_a_list_with_a_bad_integer_is_refused(run, value):
    result = run(f"numbers={value}")

    assert result.returncode != 0
    assert "for parameter <numbers>" in result.stderr


def test_the_range_is_checked_after_the_syntax(run):
    assert run("ranged=5").returncode == 0
    result = run("ranged=11")
    assert result.returncode != 0
    assert "Value <11> out of range for parameter <ranged>" in result.stderr
    result = run("ranged=5x")
    assert result.returncode != 0
    assert "Invalid value <5x> for parameter <ranged>" in result.stderr


def test_a_tuple_of_integers_is_accepted(run):
    # An option with a key_desc of two values is not multiple, but its answer
    # holds two integers; v.mkgrid grid=2,2 is the example.
    result = run("pair=2,3")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "||2,3|"


def test_a_tuple_with_a_bad_integer_is_refused(run):
    result = run("pair=2,3x")

    assert result.returncode != 0
    assert "Invalid value <3x> for parameter <pair>" in result.stderr
