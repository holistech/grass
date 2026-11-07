# SPDX-FileCopyrightText: 2026 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
"""Test that only the seed option leaves an integer answer to the tool

The parser checks an integer option strictly (check_int()), but an answer of
the standard option G_OPT_M_SEED is checked as a seed instead, which
accepts a wider range and has its own message. The tests run Python scripts,
which have the options read by g.parser, in a session.
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
STRICT = ["2147483648", "12abc"]

SEED_SCRIPT = """\
#!/usr/bin/env python3

# %module
# % description: Print the seed
# %end
# %option G_OPT_M_SEED
# %end

import grass.script as gs

if __name__ == "__main__":
    options, flags = gs.parser()
    print(options["seed"])
"""

# A script has no seed function of its own, so the parser must refuse what is
# no seed.
NOT_SEEDS = ["abc", "12abc", "4294967296", "-2147483649"]
SEEDS = ["-2147483648", "0", "2147483648", "4294967295"]

# An option with the key seed which is no G_OPT_M_SEED: scripts such as
# r.mapcalc.simple have one, and it must stay a strictly checked integer, so
# the exemption cannot be keyed on the name.
NAMED_SEED_SCRIPT = """\
#!/usr/bin/env python3

# %module
# % description: Print an integer option named seed
# %end
# %option
# % key: seed
# % description: An integer which is no G_OPT_M_SEED
# % type: integer
# % required: no
# %end

import grass.script as gs

if __name__ == "__main__":
    options, flags = gs.parser()
    print(options["seed"])
"""


@pytest.fixture
def run_script_text(xy_session_for_module, tmp_path):
    """Return a function running a script text with arguments"""

    def run_text(text, *arguments):
        script = tmp_path / "script.py"
        script.write_text(text)
        return subprocess.run(
            [sys.executable, str(script), *arguments],
            env=xy_session_for_module.env,
            capture_output=True,
            text=True,
            check=False,
        )

    return run_text


@pytest.fixture
def run(run_script_text):
    """Run the script with the arguments and return the finished process"""
    return lambda *arguments: run_script_text(SCRIPT, *arguments)


@pytest.mark.parametrize("value", STRICT)
def test_other_integer_options_stay_strict(run, value):
    for key in ("number", "seed2"):
        result = run(f"{key}={value}")

        assert result.returncode != 0
        assert f"Invalid value <{value}> for parameter <{key}>" in result.stderr


@pytest.mark.parametrize("value", STRICT)
def test_an_option_named_seed_stays_strict(run_script_text, value):
    result = run_script_text(NAMED_SEED_SCRIPT, f"seed={value}")

    assert result.returncode != 0
    assert f"Invalid value <{value}> for parameter <seed>" in result.stderr


@pytest.mark.parametrize("value", NOT_SEEDS)
def test_the_seed_option_refuses_what_is_no_seed(run_script_text, value):
    result = run_script_text(SEED_SCRIPT, f"seed={value}")

    assert result.returncode != 0
    assert f"Invalid random seed <{value}>" in result.stderr


@pytest.mark.parametrize("value", SEEDS)
def test_the_seed_option_accepts_the_range_of_seeds(run_script_text, value):
    # The negative test for the one above: this is what the parser lets
    # through, so the refusals could not come from a blanket rejection. The
    # value 2147483648 is refused by check_int() for any other option.
    result = run_script_text(SEED_SCRIPT, f"seed={value}")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == value
