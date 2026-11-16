"""Create daily temperature maps of 2020 and register them in a new STRDS

The maps are generated from the elevation model of the North Carolina sample
dataset and stored in hundredths of a degree Celsius, as integers.
"""

from datetime import datetime, timedelta

import grass.temporal as tgis
from grass.tools import Tools

tools = Tools()
tools.g_region(raster="elev_state_500m", res=1000, flags="a")

# Daily mean air temperature: 16.5 degree Celsius at sea level, an annual
# cycle of 10.5 degree with its maximum in mid July, a weather term of 3
# degree, -6.5 degree per 1000 m and +1 degree per 100 km to the south.
first_day = datetime(2020, 1, 1)
days = [first_day + timedelta(days=number) for number in range(366)]
names = ["temperature_daily_{:%Y_%m_%d}".format(day) for day in days]
expressions = [
    "{} = round(100 * (16.5 + 10.5 * cos(360 * ({} - 196) / 366.0)"
    " + 3 * sin(47 * {}) - 0.0065 * elev_state_500m"
    " - 0.00001 * (y() - 160000)))".format(name, number, number)
    for number, name in enumerate(names)
]
tools.r_mapcalc(expression="\n".join(expressions))

tgis.init()
dbif = tgis.SQLDatabaseInterfaceConnection()
dbif.connect()

temperature = tgis.open_new_stds(
    name="temperature_daily",
    type="strds",
    temporaltype="absolute",
    title="Daily mean air temperature",
    descr="Daily mean air temperature 2020 in 1/100 degree Celsius",
    semantic="mean",
    overwrite=True,
    dbif=dbif,
)

mapset = tgis.get_current_mapset()
for day, name in zip(days, names, strict=True):
    layer = tgis.RasterDataset("{}@{}".format(name, mapset))
    layer.load()
    layer.set_absolute_time(day, day + timedelta(days=1))
    if layer.is_in_db(dbif=dbif):
        layer.update(dbif=dbif)
    else:
        layer.insert(dbif=dbif)
    temperature.register_map(layer, dbif=dbif)

temperature.update_from_registered_maps(dbif=dbif)
start, end = temperature.get_absolute_time()
print("Dataset:", temperature.get_id())
print("Maps:", temperature.metadata.get_number_of_maps())
print("Time:", start, "to", end)
print("Granularity:", temperature.get_granularity())
print("Smallest minimum:", temperature.metadata.get_min_min())
print("Largest maximum:", temperature.metadata.get_max_max())
dbif.close()
