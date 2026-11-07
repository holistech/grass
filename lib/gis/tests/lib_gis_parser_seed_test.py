# SPDX-FileCopyrightText: 2026 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
"""Test that only the seed option leaves an integer answer to the tool

The parser checks an integer option strictly (check_int()), but an answer of
the standard option G_OPT_M_SEED is read by the tool with
G_random_seed_from_option(), which accepts a wider range and has its own
message. The tests run a Python script, which has the options read by
g.parser, in a session.
"""

import subprocess
import sys

import pytest

SCRIPT = """\
#!/usr/bin/env python3

# %module
# % description: Print the seed and another integer option
# %end
# %option G_OPT_M_SEED
# %end
# %option
# % key: number
# % description: Another integer, like the seed
# % type: integer
# % required: no
# %end
# %option
# % key: seed2
# % description: An option with the key of the seed which is no G_OPT_M_SEED
# % type: integer
# % required: no
# %end

import grass.script as gs

if __name__ == "__main__":
    options, flags = gs.parser()
    print("|".join([options["seed"], options["number"], options["seed2"]]))
"""

# Both are refused by check_int(): the first is out of the range of int, the
# second has trailing characters.
UNCHECKED = ["2147483648", "12abc"]


@pytest.fixture
def run(xy_session_for_module, tmp_path):
    """Run the script with the arguments and return the finished process"""
    script = tmp_path / "seed_options.py"
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


@pytest.mark.parametrize("value", UNCHECKED)
def test_other_integer_options_stay_strict(run, value):
    for key in ("number", "seed2"):
        result = run(f"{key}={value}")

        assert result.returncode != 0
        assert f"Invalid value <{value}> for parameter <{key}>" in result.stderr


@pytest.mark.parametrize("value", UNCHECKED)
def test_the_seed_option_is_left_to_the_tool(run, value):
    # The negative test for the one above: this is what the parser lets
    # through, so the strict refusals above could not come from anywhere else.
    result = run(f"seed={value}")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{value}||"
