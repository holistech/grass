"""The classic temporal algebra engine

The original implementation of the temporal algebra: PLY lexers and parsers
that compute while they parse. Scientific publications cite its results, so it
is kept as it is and is never replaced. The algebra core in
``grass.temporal.algebra`` reproduces it in its classic profile and is tested
against it.

The public parser classes (``grass.temporal.TemporalRasterAlgebraParser`` and
the others) are in ``grass.temporal.algebra.parser.facade``; they choose the
core or its classic profile and build an object of this engine only for the
granularity mode.

SPDX-License-Identifier: GPL-2.0-or-later
"""
