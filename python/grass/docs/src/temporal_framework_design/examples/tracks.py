"""Write the GPS tracks of two field crews that visit the Crabtree Creek gauges

The crews sample the five stream gauges of Crabtree Creek in Raleigh, taken
from usgsgages of the North Carolina sample dataset, on the same morning:
crew A from upstream to downstream, crew B the other way round, starting ten
minutes later. Each crew stays 30 minutes at a gauge and drives at 20 km/h
between two gauges. A position is recorded every 5 minutes.
"""

import csv
import math
from datetime import datetime, timedelta

from grass.tools import Tools

STEP = timedelta(minutes=5)
METERS_PER_STEP = 20000 / 12
STEPS_AT_GAUGE = 6

tools = Tools()
lines = tools.v_out_ascii(
    input="usgsgages",
    columns="SITE_ID",
    where="SITE_NAME LIKE 'Crabtree Creek%'",
    format="point",
).text.splitlines()
# USGS site numbers grow downstream.
rows = [line.split("|") for line in lines]
gauges = [
    (float(east), float(north))
    for east, north, _cat, _site in sorted(rows, key=lambda row: row[3])
]


def track(stops, start):
    """The positions (east, north, time) of a crew that visits the stops"""
    positions = []
    time = start
    for number, (east, north) in enumerate(stops):
        for _step in range(STEPS_AT_GAUGE):
            positions.append((east, north, time))
            time += STEP
        if number + 1 == len(stops):
            break
        next_east, next_north = stops[number + 1]
        distance = math.hypot(next_east - east, next_north - north)
        steps = max(1, round(distance / METERS_PER_STEP))
        for step in range(1, steps):
            fraction = step / steps
            positions.append(
                (
                    east + fraction * (next_east - east),
                    north + fraction * (next_north - north),
                    time,
                )
            )
            time += STEP
    return positions


crews = {
    "crew_a.csv": track(gauges, datetime(2020, 7, 15, 8, 0)),
    "crew_b.csv": track(gauges[::-1], datetime(2020, 7, 15, 8, 10)),
}
for filename, positions in crews.items():
    with open(filename, "w", newline="") as output:
        writer = csv.writer(output)
        for east, north, time in positions:
            writer.writerow(
                ["{:.1f}".format(east), "{:.1f}".format(north), time.isoformat(" ")]
            )
    print(
        "{}: {} positions from {} to {}".format(
            filename, len(positions), positions[0][2], positions[-1][2]
        )
    )
