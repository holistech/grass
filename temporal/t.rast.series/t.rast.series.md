## DESCRIPTION

*t.rast.series* reduces the raster maps of a space time raster dataset to one
raster map for each aggregation method: every cell of a new map holds the
result of the method over the values of that cell in the selected maps. Daily
maps give their average, their maximum, or the slope of their values over
time, for instance. The tool writes the list of the selected maps to a file
and runs *[r.series](r.series.md)* on it, so the methods and the results are
those of *r.series*; it offers a subset of its methods. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets, and *[t.rast.aggregate](t.rast.aggregate.md)* for the same
aggregation over regular periods of time with the results registered in a new
dataset.

The new maps are ordinary raster maps in the current mapset, not the maps of a
space time dataset. Unless the flag **-t** is given, each of them is
registered in the temporal database with a time stamp (see below). To put them
into a dataset, register them with *[t.register](t.register.md)*.

### Selection

The option **input** names the space time raster dataset. The option
**where** takes an SQL condition on the registered maps and selects the input
maps, for instance by their `start_time`; without it, all maps are used. SQLite
functions such as `strftime` are available, which selects a recurring period of
a multi-year series. The fourth and the fifth example use **where**. If the
condition selects no map, the tool warns "Space time raster dataset ... is
empty", creates no map and ends without an error.

The option **order** sorts the selected maps before *r.series* reads them. It
takes the columns `id`, `name`, `creator`, `mapset`, `creation_time`,
`start_time` (the default), `end_time`, `north`, `south`, `west`, `east`,
`min` and `max`, where `min` and `max` are the smallest and the largest cell
value of a map. Several columns are separated by commas. The order changes the
result of the methods that use the position of a map in the series: `slope`,
`offset` and `detcoeff` describe the values of a cell at the positions 0, 1,
2 and so on, and `min_raster` and `max_raster` give the position of the map
with the smallest or the largest value, counted from 0. The fourth example
shows `slope` and `max_raster`. The column `modification_time` is not offered,
because the maps in the temporal database have no such column.

### Methods and outputs

The option **method** lists the aggregation methods: `average` (the default),
`count`, `median`, `mode`, `minimum`, `min_raster`, `maximum`, `max_raster`,
`stddev`, `range`, `sum`, `variance`, `diversity`, `slope`, `offset`,
`detcoeff`, `quart1`, `quart3`, `perc90`, `quantile`, `skewness` and
`kurtosis`; *r.series* defines each of them. The option **output** lists the
names of the new maps, one for each method, in the same order. The tool stops
with the message "Number requested methods and output maps do not match." if
the numbers differ. The second example computes three methods in one run.

The method `quantile` needs a quantile between 0 and 1, which the option
**quantile** gives. The values of **quantile** belong to the methods
`quantile` in the order of the list: a method list with two `quantile` takes
two values, and `quantile` next to another method takes one value for the
`quantile` and none for the other method. The quantile is the type 7 estimate
of *r.series*: the values of a cell are sorted, `n` is their number and the
quantile `q` lies at the position `q * (n - 1)`, counted from 0, between the
two neighbouring values with a linear mix. The median of four values is the
mean of the two in the middle. If the number of values of **quantile** differs
from the number of methods `quantile`, the tool stops with the message given
above for the outputs; this includes a quantile given for no `quantile` method
and a `quantile` method without a quantile. The third example shows
quantiles.

The flag **-n** propagates null cells. By default *r.series* skips them: a cell
is aggregated over the maps that have a value there. With **-n**, a cell that
is null in any selected map is null in the new map. The sixth example shows
both for `average` and `count`.

### Time stamp of the new maps

Unless the flag **-t** is given, every new map gets a time stamp that spans the
selected maps: it starts at the earliest start time and ends at the latest end
time, or at the start of the last map if that map is a time instant. If the
only selected map is a time instant, so is the new map. The stamp does not
depend on **order**, and all new maps of one run get the same stamp. In
relative time, the new maps get numbers in the unit of the input dataset. The
flag **-t** gives the new maps no time stamp and does not register them in the
temporal database. The seventh example shows the stamp with and without **-t**.

### Computation

The option **nprocs** is the number of threads of *r.series*: `0` uses the
default of OpenMP, a positive number uses that many threads, and a negative
number uses all but that many threads. Its default is `0`, or the value of
`NPROCS` of the GRASS session if that is set (see *g.gisenv*). The option
**memory** is the size of the row cache of *r.series* in MB, `300` by default.
Both are passed on to *r.series*, and threads need a GRASS built with OpenMP.
The result does not depend on them.

*r.series* keeps every input map open, which can exceed the number of files
that the operating system allows. If the number of selected maps is greater
than **file_limit** (`1000` by default), the tool runs *r.series* with its
flag **-z**, which reads the maps row by row, and warns "Processing over N
maps: activating -z flag of r.series which slows down processing", with the
value of **file_limit** for N. A number of maps equal to **file_limit** gives
no warning. The flag does not change the result but makes the computation
slower. A higher **file_limit** avoids it, but should not exceed the limit of
open files of the operating system (see the
[Wiki](https://grasswiki.osgeo.org/wiki/Large_raster_data_processing#Number_of_open_files_limitation)).
The eighth example sets a low **file_limit**.

## NOTES

The tool computes in the current computational region, because *r.series*
does; see *g.region*.

An existing map of the name given in **output** is replaced only with
**--overwrite**; without it the tool stops with a message that the map
exists. With **--overwrite** the time stamp of the map is replaced as well.
The name in **output** may carry the mapset, as in `output=temperature_mean@t_rast_series`.

Wrong input stops the tool with a message before anything is written:

- An **input** dataset that does not exist: "Space time dataset `<name>` of
  type `<strds>` not found".
- An SQL error in **where**: two messages, "Unable to get map ids from
  register table" with the name of the register table, and "Invalid where
  condition" with the condition and the text of the SQL error.
- A value that is not offered for **method** or **order**, or a **quantile**
  outside 0 to 1: the parser stops with "Value `<value>` out of range for
  parameter" and the name of the option.

If *r.series* fails, the tool ends with "r.series failed. Check above error
messages."

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_series` and sets the computational region
to North Carolina with cells of 1 km; the later examples work in this mapset
and region. The maps of the first two examples are generated series of the year
2020, not measurements. The later examples use maps with constant values
or two constant parts, so that the result can be calculated by hand. The
results are read with *[r.what](r.what.md)* at two places, whose easting is
shown in the first column: 640000 east of Raleigh at about 104 m above sea
level and 300000 in the mountains at about 1168 m.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_series -->

<!-- markdownlint-disable MD046 -->

### Aggregate all maps of a dataset

The dataset `temperature_monthly` holds twelve monthly maps of the mean air
temperature in degree Celsius for 2020, generated from the elevation and not
measured: 16.5 degrees at sea level and the northing 160 km, plus a seasonal
cycle of 10.5 degrees with its maximum in July, minus 6.5 degrees per 1000 m of
height, and 1 degree more for every 100 km to the south, rounded to 0.1.
Outside North Carolina the maps are null. The average of the twelve maps is
the annual mean. At 640000 it is 15.225 degrees, the sum 182.7 divided by 12,
and in the mountains at 300000 it is 8.30833 degrees, 99.7 divided by 12. The
time stamp of `temperature_mean` spans the twelve maps, from 1 January 2020 to
1 January 2021, the end of the December map; *[t.list](t.list.md)* shows it.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_series
    g.region raster=elev_state_500m res=1000 -a
    for month in $(seq 12); do
        echo "temperature_monthly_2020_$(printf %02d $month) = round((16.5" \
            "+ 10.5 * cos(30 * ($month - 7.2)) - 0.0065 * elev_state_500m" \
            "- 0.00001 * (y() - 160000)) * 10) / 10.0"
    done | r.mapcalc file=-
    t.create output=temperature_monthly title="Air temperature" \
        description="Monthly mean air temperature 2020 in degree Celsius"
    t.register -i input=temperature_monthly \
        maps=$(g.list type=raster pattern="temperature_monthly_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    t.rast.series input=temperature_monthly method=average output=temperature_mean
    r.what -n map=temperature_mean coordinates=640000,220000,300000,220000 \
        | cut -d"|" -f1,4-
    t.list type=raster columns=name,start_time,end_time format=csv separator=pipe \
        mapset=. where="name = 'temperature_mean'"
    ```

    ```text
    easting|temperature_mean
    640000|15.225
    300000|8.30833333333333
    name|start_time|end_time
    temperature_mean|2020-01-01 00:00:00|2021-01-01 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()


    def what(maps, coordinates="640000,220000"):
        text = tools.r_what(map=maps, coordinates=coordinates, flags="n").text
        for line in text.splitlines():
            fields = line.split("|")
            print("|".join(fields[:1] + fields[3:]))


    tools.g_mapset(flags="c", mapset="t_rast_series")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    months = range(1, 13)
    tools.r_mapcalc(
        expression="\n".join(
            f"temperature_monthly_2020_{month:02d} = round((16.5"
            f" + 10.5 * cos(30 * ({month} - 7.2)) - 0.0065 * elev_state_500m"
            " - 0.00001 * (y() - 160000)) * 10) / 10.0"
            for month in months
        )
    )
    tools.t_create(
        output="temperature_monthly",
        title="Air temperature",
        description="Monthly mean air temperature 2020 in degree Celsius",
    )
    tools.t_register(
        input="temperature_monthly",
        maps=",".join(f"temperature_monthly_2020_{month:02d}" for month in months),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    tools.t_rast_series(
        input="temperature_monthly", method="average", output="temperature_mean"
    )
    what("temperature_mean", "640000,220000,300000,220000")
    print(
        tools.t_list(
            type="raster",
            columns="name,start_time,end_time",
            format="csv",
            separator="pipe",
            mapset=".",
            where="name = 'temperature_mean'",
        ).text
    )
    ```

    ```text
    easting|temperature_mean
    640000|15.225
    300000|8.30833333333333
    name|start_time|end_time
    temperature_mean|2020-01-01 00:00:00|2021-01-01 00:00:00
    ```

### Compute several methods in one run

The dataset `precipitation_monthly` holds twelve monthly precipitation sums of
2020 in whole millimeters. They are generated, not measured: the monthly
normals of the 136 climate stations of the dataset are interpolated for each
month with *[v.surf.idw](v.surf.idw.md)* and multiplied by an assumed factor
for a wet year. One run takes a list of methods and a list of output names of
the same length, and the maps come in the order of the lists. With `minimum`,
`maximum` and `range` the new maps hold the smallest monthly sum of each cell,
the largest, and their difference. At 640000 these are 73 and 162 millimeters
and the difference 89, at 300000 they are 77, 193 and 116.

=== "Command line"

    ```sh
    month=1
    for entry in jan:1.2 feb:1.7 mar:0.9 apr:1.3 may:1.6 jun:0.9 \
        jul:1.1 aug:1.5 sep:0.8 oct:1.0 nov:1.6 dec:0.9; do
        name=$(printf %02d $month)
        v.surf.idw input=precip_30ynormals column=${entry%:*} \
            output=precipitation_normal_$name npoints=12 power=2
        r.mapcalc expression="precipitation_monthly_2020_$name = if(isnull(elev_state_500m), null(), round(${entry#*:} * precipitation_normal_$name))"
        month=$((month + 1))
    done
    t.create output=precipitation_monthly title="Precipitation" \
        description="Monthly precipitation sum 2020 in mm"
    t.register -i input=precipitation_monthly \
        maps=$(g.list type=raster pattern="precipitation_monthly_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    t.rast.series input=precipitation_monthly method=minimum,maximum,range \
        output=precipitation_low,precipitation_high,precipitation_spread
    r.what -n map=precipitation_low,precipitation_high,precipitation_spread \
        coordinates=640000,220000,300000,220000 | cut -d"|" -f1,4-
    ```

    ```text
    easting|precipitation_low|precipitation_high|precipitation_spread
    640000|73|162|89
    300000|77|193|116
    ```

=== "Python (grass.tools)"

    ```python
    factors = {"jan": 1.2, "feb": 1.7, "mar": 0.9, "apr": 1.3, "may": 1.6, "jun": 0.9}
    factors |= {"jul": 1.1, "aug": 1.5, "sep": 0.8, "oct": 1.0, "nov": 1.6, "dec": 0.9}
    for month, (column, factor) in enumerate(factors.items(), start=1):
        normal = f"precipitation_normal_{month:02d}"
        tools.v_surf_idw(
            input="precip_30ynormals", column=column, output=normal, npoints=12, power=2
        )
        tools.r_mapcalc(
            expression=f"precipitation_monthly_2020_{month:02d} ="
            f" if(isnull(elev_state_500m), null(), round({factor} * {normal}))"
        )
    tools.t_create(
        output="precipitation_monthly",
        title="Precipitation",
        description="Monthly precipitation sum 2020 in mm",
    )
    tools.t_register(
        input="precipitation_monthly",
        maps=",".join(f"precipitation_monthly_2020_{month:02d}" for month in months),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    tools.t_rast_series(
        input="precipitation_monthly",
        method="minimum,maximum,range",
        output="precipitation_low,precipitation_high,precipitation_spread",
    )
    what(
        "precipitation_low,precipitation_high,precipitation_spread",
        "640000,220000,300000,220000",
    )
    ```

    ```text
    easting|precipitation_low|precipitation_high|precipitation_spread
    640000|73|162|89
    300000|77|193|116
    ```

### Compute quantiles

The dataset `discharge` holds four daily maps from 1 March 2026, each a time
interval of one day with the same value in every cell: 4, 1, 10 and 2 cubic
meters per second. The sorted values are 1, 2, 4 and 10. The quantile 0.25 lies
at the position `0.25 * 3 = 0.75`, so it is `1 + 0.75 * (2 - 1) = 1.75`. The
quantile 0.75 lies at the position 2.25, `4 + 0.25 * (10 - 4) = 5.5`. The first
block asks for both quantiles with two methods `quantile`. In the second block
`quantile` stands next to `maximum`, which takes no quantile: the median lies at
the position 1.5, the mean of 2 and 4, which is 3, and the maximum is 10.

=== "Command line"

    ```sh
    for day in 1 2 3 4; do
        value=$(echo 4 1 10 2 | cut -d" " -f$day)
        r.mapcalc expression="discharge_2026_03_0$day = $value"
    done
    t.create output=discharge title="Discharge" \
        description="Daily river discharge in cubic metres per second"
    t.register -i input=discharge \
        maps=discharge_2026_03_01,discharge_2026_03_02,discharge_2026_03_03,discharge_2026_03_04 \
        start=2026-03-01 increment="1 day"
    t.rast.series input=discharge method=quantile,quantile quantile=0.25,0.75 \
        output=discharge_lower,discharge_upper
    r.what -n map=discharge_lower,discharge_upper coordinates=640000,220000 \
        | cut -d"|" -f1,4-
    ```

    ```text
    easting|discharge_lower|discharge_upper
    640000|1.75|5.5
    ```

    ```sh
    t.rast.series input=discharge method=quantile,maximum quantile=0.5 \
        output=discharge_median,discharge_top
    r.what -n map=discharge_median,discharge_top coordinates=640000,220000 \
        | cut -d"|" -f1,4-
    ```

    ```text
    easting|discharge_median|discharge_top
    640000|3|10
    ```

=== "Python (grass.tools)"

    ```python
    values = (4, 1, 10, 2)
    for day, value in enumerate(values, start=1):
        tools.r_mapcalc(expression=f"discharge_2026_03_{day:02d} = {value}")
    tools.t_create(
        output="discharge",
        title="Discharge",
        description="Daily river discharge in cubic metres per second",
    )
    tools.t_register(
        input="discharge",
        maps=",".join(f"discharge_2026_03_{day:02d}" for day in range(1, 5)),
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_series(
        input="discharge",
        method="quantile,quantile",
        quantile="0.25,0.75",
        output="discharge_lower,discharge_upper",
    )
    what("discharge_lower,discharge_upper")
    ```

    ```text
    easting|discharge_lower|discharge_upper
    640000|1.75|5.5
    ```

    ```python
    tools.t_rast_series(
        input="discharge",
        method="quantile,maximum",
        quantile=0.5,
        output="discharge_median,discharge_top",
    )
    what("discharge_median,discharge_top")
    ```

    ```text
    easting|discharge_median|discharge_top
    640000|3|10
    ```

### Select the maps and set their order

The first block aggregates the maps of June, July and August 2020 with `sum`;
the condition selects the maps that start from 1 June up to, but not including,
1 September. The sum is 379 millimeters at 640000 and 362 at 300000. The new
map `precipitation_summer` starts on 1 June and ends on 1 September, where the
August map ends.

The other blocks compute `slope` and `max_raster` of `discharge` for two orders.
In the time order the values are 4, 1, 10 and 2. The slope is the slope of a
line fitted to these values at the positions 0 to 3, and it is 0.3; the largest
value, 10, is at the position 2, so `max_raster` is 2. With **order** `max` the
maps are sorted by their largest cell value, which is the value of the map; the
values then are 1, 2, 4 and 10, the slope is 2.9 and the largest value is at the
position 3.

=== "Command line"

    ```sh
    t.rast.series input=precipitation_monthly method=sum \
        output=precipitation_summer \
        where="start_time >= '2020-06-01' and start_time < '2020-09-01'"
    r.what -n map=precipitation_summer coordinates=640000,220000,300000,220000 \
        | cut -d"|" -f1,4-
    t.list type=raster columns=name,start_time,end_time format=csv separator=pipe \
        mapset=. where="name = 'precipitation_summer'"
    ```

    ```text
    easting|precipitation_summer
    640000|379
    300000|362
    name|start_time|end_time
    precipitation_summer|2020-06-01 00:00:00|2020-09-01 00:00:00
    ```

    ```sh
    t.rast.series input=discharge method=slope,max_raster \
        output=slope_by_time,max_by_time
    t.rast.series input=discharge method=slope,max_raster order=max \
        output=slope_by_max,max_by_max
    r.what -n map=slope_by_time,max_by_time,slope_by_max,max_by_max \
        coordinates=640000,220000 | cut -d"|" -f1,4-
    ```

    ```text
    easting|slope_by_time|max_by_time|slope_by_max|max_by_max
    640000|0.3|2|2.9|3
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_series(
        input="precipitation_monthly",
        method="sum",
        output="precipitation_summer",
        where="start_time >= '2020-06-01' and start_time < '2020-09-01'",
    )
    what("precipitation_summer", "640000,220000,300000,220000")
    print(
        tools.t_list(
            type="raster",
            columns="name,start_time,end_time",
            format="csv",
            separator="pipe",
            mapset=".",
            where="name = 'precipitation_summer'",
        ).text
    )
    ```

    ```text
    easting|precipitation_summer
    640000|379
    300000|362
    name|start_time|end_time
    precipitation_summer|2020-06-01 00:00:00|2020-09-01 00:00:00
    ```

    ```python
    tools.t_rast_series(
        input="discharge",
        method="slope,max_raster",
        output="slope_by_time,max_by_time",
    )
    tools.t_rast_series(
        input="discharge",
        method="slope,max_raster",
        order="max",
        output="slope_by_max,max_by_max",
    )
    what("slope_by_time,max_by_time,slope_by_max,max_by_max")
    ```

    ```text
    easting|slope_by_time|max_by_time|slope_by_max|max_by_max
    640000|0.3|2|2.9|3
    ```

### Select the same month of several years

The dataset `signal` holds six monthly maps, January to March of 2025 and of
2026, with the same value in every cell of a map. The maps are numbered 1 to 6
in time order, and the value is 10 times the number plus 1, so 11 to 61. The
condition `strftime('%m', start_time) = '01'` selects the January maps, 1 and 4
with the values 11 and 41, in both years: the average is (11 + 41) / 2 = 26. The
loop in the second block computes the climatology of each month for two methods.
The maps of a month are numbered 1 + k and 4 + k for k = 0, 1 and 2, so the
average is 26, 36 and 46, and the maximum is 41, 51 and 61.

=== "Command line"

    ```sh
    for number in 1 2 3 4 5 6; do
        year=$((2025 + (number - 1) / 3))
        month=$(printf %02d $(((number - 1) % 3 + 1)))
        r.mapcalc expression="signal_${year}_$month = 10 * $number + 1"
    done
    t.create output=signal title="Signal" \
        description="Three months of two years"
    t.register -i input=signal maps=signal_2025_01,signal_2025_02,signal_2025_03 \
        start=2025-01-01 increment="1 month"
    t.register -i input=signal maps=signal_2026_01,signal_2026_02,signal_2026_03 \
        start=2026-01-01 increment="1 month"
    t.rast.series input=signal method=average output=signal_january \
        where="strftime('%m', start_time) = '01'"
    r.what -n map=signal_january coordinates=640000,220000 | cut -d"|" -f1,4-
    ```

    ```text
    easting|signal_january
    640000|26
    ```

    ```sh
    for month in 01 02 03; do
        for method in average maximum; do
            t.rast.series input=signal method=$method output=${method}_$month \
                where="strftime('%m', start_time) = '$month'"
        done
    done
    r.what -n map=average_01,maximum_01,average_02,maximum_02,average_03,maximum_03 \
        coordinates=640000,220000 | cut -d"|" -f1,4-
    ```

    ```text
    easting|average_01|maximum_01|average_02|maximum_02|average_03|maximum_03
    640000|26|41|36|51|46|61
    ```

=== "Python (grass.tools)"

    ```python
    for number in range(1, 7):
        year = 2025 + (number - 1) // 3
        month = (number - 1) % 3 + 1
        tools.r_mapcalc(expression=f"signal_{year}_{month:02d} = 10 * {number} + 1")
    tools.t_create(output="signal", title="Signal", description="Three months of two years")
    for maps, start in (
        ("signal_2025_01,signal_2025_02,signal_2025_03", "2025-01-01"),
        ("signal_2026_01,signal_2026_02,signal_2026_03", "2026-01-01"),
    ):
        tools.t_register(
            input="signal", maps=maps, start=start, increment="1 month", flags="i"
        )
    tools.t_rast_series(
        input="signal",
        method="average",
        output="signal_january",
        where="strftime('%m', start_time) = '01'",
    )
    what("signal_january")
    ```

    ```text
    easting|signal_january
    640000|26
    ```

    ```python
    for month in ("01", "02", "03"):
        for method in ("average", "maximum"):
            tools.t_rast_series(
                input="signal",
                method=method,
                output=f"{method}_{month}",
                where=f"strftime('%m', start_time) = '{month}'",
            )
    what("average_01,maximum_01,average_02,maximum_02,average_03,maximum_03")
    ```

    ```text
    easting|average_01|maximum_01|average_02|maximum_02|average_03|maximum_03
    640000|26|41|36|51|46|61
    ```

### Handle null cells

The dataset `snow_depth` holds two daily maps from 1 March 2026. The first
holds 10 centimeters in every cell. The second holds 20 centimeters east of the
easting 500000 and is null west of it, as if a gauge had not reported. By
default the cells of the east are aggregated over both maps, so the average is
(10 + 20) / 2 = 15 and the count 2; in the west the first map is the only one
with a value, so the average is 10 and the count 1. With **-n** a cell that is
null in one map is null in the result, so both results are `*` in the west,
the symbol of *r.what* for a null cell, while the east does not change.

=== "Command line"

    ```sh
    r.mapcalc expression="snow_depth_1 = 10"
    r.mapcalc expression="snow_depth_2 = if(x() < 500000, null(), 20)"
    t.create output=snow_depth title="Snow depth" \
        description="Snow depth in cm, not measured in the west on the second day"
    t.register -i input=snow_depth maps=snow_depth_1,snow_depth_2 \
        start=2026-03-01 increment="1 day"
    t.rast.series input=snow_depth method=average,count \
        output=skip_average,skip_count
    t.rast.series -n input=snow_depth method=average,count \
        output=keep_average,keep_count
    r.what -n map=skip_average,skip_count,keep_average,keep_count \
        coordinates=640000,220000,300000,220000 | cut -d"|" -f1,4-
    ```

    ```text
    easting|skip_average|skip_count|keep_average|keep_count
    640000|15|2|15|2
    300000|10|1|*|*
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="snow_depth_1 = 10")
    tools.r_mapcalc(expression="snow_depth_2 = if(x() < 500000, null(), 20)")
    tools.t_create(
        output="snow_depth",
        title="Snow depth",
        description="Snow depth in cm, not measured in the west on the second day",
    )
    tools.t_register(
        input="snow_depth",
        maps="snow_depth_1,snow_depth_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_series(
        input="snow_depth", method="average,count", output="skip_average,skip_count"
    )
    tools.t_rast_series(
        input="snow_depth",
        method="average,count",
        output="keep_average,keep_count",
        flags="n",
    )
    what(
        "skip_average,skip_count,keep_average,keep_count",
        "640000,220000,300000,220000",
    )
    ```

    ```text
    easting|skip_average|skip_count|keep_average|keep_count
    640000|15|2|15|2
    300000|10|1|*|*
    ```

### Give the new map no time stamp

With the flag **-t** the new map `discharge_plain` is computed as before, its
value is (4 + 1 + 10 + 2) / 4 = 4.25, but it gets no time stamp and is not
registered. *[t.list](t.list.md)* lists the maps registered in the temporal
database with their time: `temperature_mean` from the first example and
`precipitation_summer` from the fourth example are there, `discharge_plain` is
not.

=== "Command line"

    ```sh
    t.rast.series -t input=discharge method=average output=discharge_plain
    r.what -n map=discharge_plain coordinates=640000,220000 | cut -d"|" -f1,4-
    t.list type=raster columns=name,start_time,end_time format=csv separator=pipe \
        mapset=. \
        where="name in ('temperature_mean', 'precipitation_summer', 'discharge_plain')"
    ```

    ```text
    easting|discharge_plain
    640000|4.25
    name|start_time|end_time
    precipitation_summer|2020-06-01 00:00:00|2020-09-01 00:00:00
    temperature_mean|2020-01-01 00:00:00|2021-01-01 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_series(
        input="discharge", method="average", output="discharge_plain", flags="t"
    )
    what("discharge_plain")
    print(
        tools.t_list(
            type="raster",
            columns="name,start_time,end_time",
            format="csv",
            separator="pipe",
            mapset=".",
            where="name in ('temperature_mean', 'precipitation_summer', 'discharge_plain')",
        ).text
    )
    ```

    ```text
    easting|discharge_plain
    640000|4.25
    name|start_time|end_time
    precipitation_summer|2020-06-01 00:00:00|2020-09-01 00:00:00
    temperature_mean|2020-01-01 00:00:00|2021-01-01 00:00:00
    ```

### Limit the open files and set the threads

A **file_limit** of 2 is below the four maps of `discharge`, so the tool runs
*r.series* with its flag **-z** and warns on the standard error. The result is
the same as without the flag: 4 + 1 + 10 + 2 = 17. The options **nprocs** and
**memory** are passed to *r.series* and do not change the result either.

=== "Command line"

    ```sh
    t.rast.series input=discharge method=sum output=discharge_total file_limit=2 \
        nprocs=2 memory=100
    r.what -n map=discharge_total coordinates=640000,220000 | cut -d"|" -f1,4-
    ```

    ```text
    easting|discharge_total
    640000|17
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_series(
        input="discharge",
        method="sum",
        output="discharge_total",
        file_limit=2,
        nprocs=2,
        memory=100,
    )
    what("discharge_total")
    ```

    ```text
    easting|discharge_total
    640000|17
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.region](g.region.md), [r.series](r.series.md), [r.stats](r.stats.md),
[t.create](t.create.md), [t.info](t.info.md), [t.list](t.list.md),
[t.rast.aggregate](t.rast.aggregate.md), [t.register](t.register.md),
[temporal data processing](temporalintro.md)*

[Temporal data processing
Wiki](https://grasswiki.osgeo.org/wiki/Temporal_data_processing)

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
