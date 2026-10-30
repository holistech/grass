"""Helpers for tests of the temporal framework

The modules do not import pytest. The shared fixtures that use them live in
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

The algebras (the core grass.temporal.algebra, its classic profile and the
reference implementation grass.temporal.classic):

reference
    Run the reference directly, whatever GRASS_TEMPORAL_ALGEBRA says.
corpus
    The outcomes of the reference for each case of the test suite (the gold
    corpus in the directory corpus), which the tests read in place of a run.
corpus_orphans
    List the entries of the gold corpus that no test reads.
differential
    Run an expression on the reference, the classic profile or the core and
    compare two outcomes.
algebra_cases
    Datasets and checks of the algebra cases of the library tests that came
    from the former gunittest files, with expected values derived by hand.
expressions
    Seeded random expressions in the syntax of the classic algebra, run by
    two runners of differential and compared, in pytest and from the
    command line.
expressions_generator
    The generator of these expressions.
expressions_data
    The datasets these expressions run on.

Recordings of the library, proof that a refactor changes no result:

recordings
    Record and compare what the extent, granularity, date and topology
    functions compute.
database_image
    Record and compare the temporal database that the library writes and
    what it reads back from it.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""
