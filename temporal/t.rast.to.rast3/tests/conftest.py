"""Datasets for the tests of t.rast.to.rast3

The region has two rows and three columns of size 1. Most tests use maps with
a constant value; the dataset tr_cells (see below) has maps with different cells.
"""

import pytest

from grass.temporal.testing.data import small_region


@pytest.fixture(autouse=True)
def _region(tools):
    small_region(tools, 2, 3)
