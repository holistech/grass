"""Sample the monthly mean temperature of 2020 at three climate stations

Needs the dataset temperature_monthly of aggregate.py in the current mapset.
The stations are copied from precip_30ynormals of the North Carolina sample
dataset; the raster cells are read directly with pygrass.
"""

import grass.temporal as tgis
from grass.pygrass.gis.region import Region
from grass.pygrass.raster import RasterRow
from grass.pygrass.utils import coor2pixel
from grass.pygrass.vector import VectorTopo
from grass.tools import Tools

tools = Tools()
tools.g_region(raster="elev_state_500m", res=1000, flags="a")
# On the coast, in the Piedmont and in the mountains
tools.v_extract(
    input="precip_30ynormals",
    output="stations",
    where="station IN (311606, 317924, 313565)",
)

stations = VectorTopo("stations")
stations.open("r")
points = []
for point in stations.viter("points"):
    station = int(point.attrs["station"])
    print(
        "Station {} at {:.0f} m: east {:.0f}, north {:.0f}".format(
            station, point.attrs["elev"], point.x, point.y
        )
    )
    points.append((station, point))
stations.close()

tgis.init()
monthly = tgis.open_old_stds("temperature_monthly", "strds")
region = Region()
for layer in monthly.get_registered_maps_as_objects(order="start_time"):
    start, end = layer.get_absolute_time()
    raster = RasterRow(layer.get_name())
    raster.open("r")
    for station, point in points:
        row, col = coor2pixel(point.coords(), region)
        value = raster[int(row)][int(col)]
        print("{:%Y-%m} {} {:.2f}".format(start, station, value))
    raster.close()
