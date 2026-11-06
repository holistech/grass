"""Measure typical operations of the temporal framework on many maps

Usage: python3 benchmark.py [number of maps]

The number of maps defaults to 50. The counts go to standard output, the
times to standard error, so that the output of two runs can be compared.
"""

import sys
import time

import grass.temporal as tgis
from grass.tools import Tools


def measure(label, function):
    """Run function and write its run time with label to standard error"""
    start = time.perf_counter()
    result = function()
    print(
        "{}: {:.3f} s".format(label, time.perf_counter() - start),
        file=sys.stderr,
    )
    return result


number_of_maps = int(sys.argv[1]) if len(sys.argv) > 1 else 50

# The benchmark measures the temporal framework, so the maps are small.
tools = Tools()
tools.g_region(raster="elev_state_500m", res=50000, flags="a")
names = ["benchmark_{}".format(number) for number in range(number_of_maps)]
tools.r_mapcalc(
    expression="\n".join(
        "{} = {}".format(name, number) for number, name in enumerate(names)
    )
)
with open("benchmark_maps.txt", "w") as file_of_names:
    file_of_names.write("\n".join(names) + "\n")

tgis.init()
dataset = tgis.open_new_stds(
    name="benchmark",
    type="strds",
    temporaltype="absolute",
    title="Benchmark",
    descr="Benchmark with {} maps".format(number_of_maps),
    semantic="mean",
    overwrite=True,
)


measure(
    "Registration",
    lambda: tgis.register_maps_in_space_time_dataset(
        type="raster",
        name="benchmark",
        file="benchmark_maps.txt",
        start="2000-01-01",
        increment="1 second",
        interval=True,
    ),
)
where = "start_time >= '2000-01-01 00:00:00'"
rows = measure("SQL selection", lambda: dataset.get_registered_maps(where=where))
print("Selected rows:", len(rows))
maps = measure(
    "Selection as objects",
    lambda: dataset.get_registered_maps_as_objects(where=where),
)
print("Selected map objects:", len(maps))
relations = measure(
    "Topology and counting", lambda: dataset.count_temporal_relations(maps)
)
print("Follows:", relations["follows"])
print("Precedes:", relations["precedes"])
