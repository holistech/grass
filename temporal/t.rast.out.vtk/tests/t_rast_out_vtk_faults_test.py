"""Test the files that t.rast.out.vtk -g writes for a month series from a month end

The series from 31 January has the granularity "1 month", so -g writes a file
per month, not per day.
"""

from datetime import datetime
from itertools import pairwise

from grass.temporal.testing.data import MapSpec, create_stds

D = datetime


def test_month_end_series_gives_a_file_per_month(tools, tmp_path):
    ends = [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)]
    create_stds(
        tools,
        "strds",
        "month_ends",
        [
            MapSpec(f"month_end_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ends), start=1)
        ],
    )
    tools.t_rast_out_vtk(input="month_ends", directory=str(tmp_path), flags="g")
    assert len(list(tmp_path.glob("*.vtk"))) == 3
