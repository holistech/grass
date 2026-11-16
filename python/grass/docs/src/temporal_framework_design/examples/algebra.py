"""Compute the monthly mean temperature of 2020 with the algebra core

Needs the dataset temperature_daily of register.py in the current mapset.
The result equals the one of aggregate.py.
"""

import grass.temporal as tgis
from grass.temporal import algebra as ta
from grass.tools import Tools

tools = Tools()
tools.g_region(raster="elev_state_500m", res=1000, flags="a")

tgis.init()
daily = ta.source("temperature_daily")
months = ta.granules("2020-01-01", "2021-01-01", "1 month")
averages = ta.gather(months, ta.contains, daily, reduce=ta.series_method("average"))
monthly = averages / 100.0

# Only materialize() computes maps: it runs r.series and r.mapcalc for each
# month and registers the results in a new space time raster dataset.
ta.materialize(
    monthly, "temperature_core", basename="temperature_core", time_suffix="gran"
)
core = tgis.open_old_stds("temperature_core", "strds")
dbif = tgis.SQLDatabaseInterfaceConnection()
dbif.connect()
for layer in core.get_registered_maps_as_objects(dbif=dbif):
    # The list holds the identifier and the extents; select() reads the rest.
    layer.select(dbif=dbif)
    start, end = layer.get_absolute_time()
    print(
        "{} {:%Y-%m-%d} {:%Y-%m-%d} {} {}".format(
            layer.get_name(),
            start,
            end,
            layer.metadata.get_min(),
            layer.metadata.get_max(),
        )
    )
dbif.close()
