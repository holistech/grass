"""The example in the docstring of grass.temporal.algebra runs

The test runs the code block of the package docstring as it stands, so the
two cannot drift apart. The datasets hold four days around the turn of
January 2020 instead of a year: enough for two months, one warm day in each.
"""

import datetime
import re
import textwrap

import grass.temporal.algebra as ta
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import list_maps
from grass.tools import Tools

# (day, precipitation, temperature); warm days have more than 5 degrees.
DAYS = [
    (datetime.datetime(2020, 1, 30), 1, 3),
    (datetime.datetime(2020, 1, 31), 2, 8),
    (datetime.datetime(2020, 2, 1), 4, 10),
    (datetime.datetime(2020, 2, 2), 8, 2),
]
ONE_DAY = datetime.timedelta(days=1)


def example_code():
    """The code block of the package docstring, dedented"""
    match = re.search(
        r"\.\. code-block:: python\n\n(.*?)\n\n(?=\S)", ta.__doc__, re.DOTALL
    )
    assert match is not None, "The package docstring has no code block"
    return textwrap.dedent(match.group(1))


def test_the_package_example_runs(temporal_module_session):
    tools = Tools(session=temporal_module_session)
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    for name, column in (("precipitation_daily", 1), ("temperature_daily", 2)):
        maps = [
            MapSpec(f"{name}_{number}", row[column], row[0], row[0] + ONE_DAY)
            for number, row in enumerate(DAYS, start=1)
        ]
        create_stds(tools, "strds", name, maps)
    # The code is the docstring of the package under test, not outside input.
    exec(example_code(), {})  # noqa: S102
    # January: 0 on the 30th (3 degrees) + 2 on the 31st; February: 4 on the
    # 1st + 0 on the 2nd (2 degrees). The other ten months relate no map.
    rows = list_maps(tools, "strds", "precip_warm_monthly")
    assert [(row.name, row.start, row.end, row.min, row.max) for row in rows] == [
        ("pwm_0", "2020-01-01 00:00:00", "2020-02-01 00:00:00", 2, 2),
        ("pwm_1", "2020-02-01 00:00:00", "2020-03-01 00:00:00", 4, 4),
    ]
