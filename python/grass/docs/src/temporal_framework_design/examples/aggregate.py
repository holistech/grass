"""Aggregate the daily temperature of 2020 to monthly means in degree Celsius

Needs the dataset temperature_daily of register.py in the current mapset.
"""

from datetime import datetime

import grass.temporal as tgis
from grass.tools import Tools

tools = Tools()
tools.g_region(raster="elev_state_500m", res=1000, flags="a")

tgis.init()
daily = tgis.open_old_stds("temperature_daily", "strds")
monthly = tgis.open_new_stds(
    name="temperature_monthly",
    type="strds",
    temporaltype="absolute",
    title="Monthly mean air temperature",
    descr="Monthly mean air temperature 2020 in degree Celsius",
    semantic="mean",
    overwrite=True,
)

dbif = tgis.SQLDatabaseInterfaceConnection()
dbif.connect()

# A granule is a map object without a map: it has only a time stamp.
granules = []
start = datetime(2020, 1, 1)
for _month in range(12):
    end = tgis.increment_datetime_by_string(start, "1 month")
    granule = tgis.RasterDataset(None)
    granule.set_absolute_time(start, end)
    granules.append(granule)
    start = end

daily_maps = daily.get_registered_maps_as_objects(dbif=dbif)
builder = tgis.SpatioTemporalTopologyBuilder()
builder.build(mapsA=granules, mapsB=daily_maps)

mapset = tgis.get_current_mapset()
for granule in granules:
    start, end = granule.get_absolute_time()
    name = "temperature_monthly_{:%Y_%m}".format(start)
    days = [layer.get_id() for layer in granule.get_contains()]
    print("{}: {} days".format(name, len(days)))
    tools.r_series(input=days, output="daily_average", method="average", overwrite=True)
    tools.r_mapcalc(
        expression="{} = daily_average / 100.0".format(name), overwrite=True
    )

    layer = tgis.RasterDataset("{}@{}".format(name, mapset))
    layer.load()
    layer.set_temporal_extent(granule.get_temporal_extent())
    if layer.is_in_db(dbif=dbif):
        layer.update(dbif=dbif)
    else:
        layer.insert(dbif=dbif)
    monthly.register_map(layer, dbif=dbif)

monthly.update_from_registered_maps(dbif=dbif)
for layer in monthly.get_registered_maps_as_objects(dbif=dbif):
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
