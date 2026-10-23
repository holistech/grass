"""Test the check of floating point options by the parser

The parser checks an option of type double in libgis (check_double()). The
tests run a Python script, which has the options read by g.parser, in a
session.
"""

import subprocess
import sys

import pytest

SCRIPT = """\
#!/usr/bin/env python3

# %module
# % description: Print the floating point options
# %end
# %option
# % key: number
# % description: One floating point number
# % type: double
# % required: no
# %end
# %option
# % key: numbers
# % description: Several floating point numbers
# % type: double
# % multiple: yes
# % required: no
# %end
# %option
# % key: pair
# % description: East and north
# % key_desc: east,north
# % type: double
# % required: no
# %end
# %option
# % key: ranged
# % description: One number from 0 to 1
# % type: double
# % options: 0-1
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
    script = tmp_path / "double_options.py"
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


@pytest.mark.parametrize(
    "value", ["2.5", "+2.5", "-2.5", "007", "0", ".5", "5.", "1e3", "1.5E-3"]
)
def test_a_number_is_accepted(run, value):
    result = run(f"number={value}")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{value}|||"


@pytest.mark.parametrize(
    "value", ["2.5abc", "2.5x", "3 4", "abc", "1e", "2.5.1", "1,5", " "]
)
def test_a_number_with_trailing_characters_is_refused(run, value):
    result = run(f"number={value}")

    assert result.returncode != 0
    assert f"Invalid value <{value}> for parameter <number>" in result.stderr


@pytest.mark.parametrize("value", ["1e400", "-1e400"])
def test_a_number_beyond_the_double_range_is_refused(run, value):
    # strtod() reports ERANGE and returns HUGE_VAL; sscanf("%lf") gave inf
    # without a hint.
    result = run(f"number={value}")

    assert result.returncode != 0
    assert f"Invalid value <{value}> for parameter <number>" in result.stderr


@pytest.mark.parametrize("value", [" 2.5", "2.5 ", " 2.5 "])
def test_spaces_around_a_number_are_accepted(run, value):
    # Same rule as for integers: strtod() skips leading spaces and trailing
    # ones are allowed; spaces between two numbers ("3 4") stay an error.
    result = run(f"number={value}")

    assert result.returncode == 0, result.stderr


def test_spaces_around_the_numbers_of_a_list_are_accepted(run):
    result = run("numbers=1.5, 2 ,3e1")

    assert result.returncode == 0, result.stderr


def test_a_list_of_numbers_is_accepted(run):
    result = run("numbers=1.5,-2,+3e1,.5")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "|1.5,-2,+3e1,.5||"


@pytest.mark.parametrize("value", ["1.5,2x", "1.5,abc"])
def test_a_list_with_a_bad_number_is_refused(run, value):
    result = run(f"numbers={value}")

    assert result.returncode != 0
    assert "for parameter <numbers>" in result.stderr


def test_the_range_is_checked_after_the_syntax(run):
    assert run("ranged=0.5").returncode == 0
    result = run("ranged=1.5")
    assert result.returncode != 0
    assert "Value <1.5> out of range for parameter <ranged>" in result.stderr
    result = run("ranged=0.5x")
    assert result.returncode != 0
    assert "Invalid value <0.5x> for parameter <ranged>" in result.stderr


def test_a_tuple_of_numbers_is_accepted(run):
    # An option with a key_desc of two values is not multiple, but its answer
    # holds two numbers; r.what coordinates=1.5,2.5 is the example.
    result = run("pair=1.5,2.5")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "||1.5,2.5|"


def test_a_tuple_with_a_bad_number_is_refused(run):
    result = run("pair=1.5,2.5x")

    assert result.returncode != 0
    assert "Invalid value <2.5x> for parameter <pair>" in result.stderr
