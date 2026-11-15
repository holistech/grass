"""Helpers for tests of the temporal framework

No module imports pytest when it is imported; ``postgresql`` imports it
inside ``server_or_skip()`` only. The shared fixtures that use them live in
temporal/conftest.py and python/grass/temporal/tests/conftest.py; the test
directories of the tools add their own in their conftest.py.
doc/development/testing.md describes how the tests use them.

Sessions and data:

session
    Create the GRASS sessions that the tests run in: a project for tests
    that run tools, a temporal session for tests that call grass.temporal in
    the test process, a second mapset, a tool run with a time limit.
data
    Build dates, maps and space time datasets as input.
readback
    Read registered maps, t.info output, cell values and the maps and
    datasets of a session back; normalize the messages of a call.
io_cache
    Cache the list of temporal mapsets and the interface descriptions of the
    tools, two slow calls that give the same answer within a test.

The algebra core (grass.temporal.algebra):

outcomes
    Run an expression on the core and read the maps it made.
algebra_cases
    Datasets and checks of the algebra cases of the library tests that came
    from the former gunittest files, with expected values derived by hand.
expressions_data
    The datasets that the algebra tests run expressions on.

Recordings of the library, proof that a refactor changes no result:

recordings
    Record and compare what the extent, granularity, date and topology
    functions compute.
database_image
    Record and compare the temporal database that the library writes and
    what it reads back from it.

Optional services and other versions:

postgresql
    Run temporal tests against a PostgreSQL server that the person who runs
    them starts, and compare the two database backends row by row.
versions
    Turn a current temporal database into one of an older version, for the
    tests of t.upgrade and of the version check.

The manuals and the North Carolina sample dataset:

nc_dataset
    Find the North Carolina sample dataset, make projects that link its
    PERMANENT mapset read-only, and record the mapset to show that a run
    wrote nothing into it.
manual_examples
    Read the examples of a tool manual (the Command line and Python
    (grass.tools) tabs, the shown output, the control comments), run them
    and compare the output with the manual after normalising it.
manual_coverage
    Check that the examples of a manual show every option of the tool and
    that its .md and .html files agree.

Documentation:

contract_trace
    Run an example script and list the public functions of grass.temporal
    that it calls, then name those that the public contract does not cover.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""
