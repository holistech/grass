# SPDX-FileCopyrightText: 2026 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fixtures for the t.support tests

tools and prefix come from temporal/conftest.py.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, relative_intervals


@pytest.fixture
def make_dataset(tools, prefix):
    """Function that creates a dataset <prefix>_ds of three maps

    make(stds_type, temporaltype) returns the name of the dataset and of the
    maps <prefix>_1 to <prefix>_3. Map n lasts one unit, from n-1 to n (days
    from 2001-01-01 for absolute time), and holds the value 10 n; a vector
    map has one point at (n, n) instead, so that its extent differs from the
    others. Title and description are "T0" and "D0", the semantic type is
    mean.
    """

    def make(stds_type="strds", temporaltype="absolute"):
        if temporaltype == "absolute":
            times = [(day(n), day(n + 1)) for n in range(3)]
        else:
            times = relative_intervals(3)
        value = 1 if stds_type == "stvds" else 10
        specs = [
            MapSpec(f"{prefix}_{n}", value * n, start, end)
            for n, (start, end) in enumerate(times, 1)
        ]
        options = {"temporaltype": temporaltype}
        if temporaltype == "relative":
            options["unit"] = "days"
        name = f"{prefix}_ds"
        create_stds(
            tools, stds_type, name, specs, title="T0", description="D0", **options
        )
        return name, [spec.name for spec in specs]

    return make


@pytest.fixture
def info_text(tools):
    """Function that gives t.info of a dataset as one line, the frame left out

    t.info draws a frame and breaks long lines, so a title or a command is
    found only after the frame characters and the breaks are gone.
    """

    def text(stds_type, name):
        return " ".join(
            tools.t_info(type=stds_type, input=name).stdout.replace("|", " ").split()
        )

    return text
