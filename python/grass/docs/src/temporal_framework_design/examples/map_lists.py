"""Register three maps with gaps and list them in the three ways of the document"""

from datetime import datetime

import grass.temporal as tgis
from grass.tools import Tools

tools = Tools()
tools.g_region(raster="elev_state_500m", res=1000, flags="a")
tools.r_mapcalc(expression="A = 1\nB = 2\nC = 3")

tgis.init()
dataset = tgis.open_new_stds(
    name="abc",
    type="strds",
    temporaltype="absolute",
    title="Three maps",
    descr="Three maps with gaps between them",
    semantic="mean",
    overwrite=True,
)
mapset = tgis.get_current_mapset()
times = {
    "A": (datetime(2010, 1, 20), datetime(2010, 1, 22)),
    "B": (datetime(2010, 1, 24), datetime(2010, 1, 27)),
    "C": (datetime(2010, 1, 28), datetime(2010, 1, 29)),
}
for name, (start, end) in times.items():
    layer = tgis.RasterDataset("{}@{}".format(name, mapset))
    layer.load()
    layer.set_absolute_time(start, end)
    layer.insert()
    dataset.register_map(layer)
dataset.update_from_registered_maps()
print("Granularity:", dataset.get_granularity())


def describe(layer):
    """The name, or "gap" for a gap, and the time of a map object"""
    start, end = layer.get_absolute_time()
    name = layer.get_name() if layer.get_id() else "gap"
    return "{} {:%m-%d}..{:%m-%d}".format(name, start, end)


print("get_registered_maps_as_objects():")
print(", ".join(describe(layer) for layer in dataset.get_registered_maps_as_objects()))
print("get_registered_maps_as_objects_with_gaps():")
print(
    ", ".join(
        describe(layer) for layer in dataset.get_registered_maps_as_objects_with_gaps()
    )
)
print("get_registered_maps_as_objects_by_granularity():")
for granule in dataset.get_registered_maps_as_objects_by_granularity():
    print("[{}]".format(", ".join(describe(layer) for layer in granule)))
