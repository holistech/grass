## DESCRIPTION

*t.rast.mapcalc* computes new raster maps from the maps of one or more space
time raster datasets (STRDS) and registers them in a new STRDS. It runs
*[r.mapcalc](r.mapcalc.md)* once for each time step and adds the temporal
variables `td()`, `start_time()`, `end_time()` and, for absolute time, the
calendar functions `start_doy()`, `end_month()` and others to the expression.
Use it when the result of a time step depends on maps of several datasets, on
the time of the step, or on both. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. *[t.rast3d.mapcalc](t.rast3d.mapcalc.md)* does the same for space
time 3D raster datasets, *[t.rast.algebra](t.rast.algebra.md)* computes with
the temporal algebra, and *[t.rast.list](t.rast.list.md)* lists the maps of the
result.

### Datasets and time steps

The option **inputs** lists the datasets whose maps the **expression** uses.
The first dataset of the list is the sampler: every map of it is one time step,
which this manual calls a granule. Each of the other datasets is sampled by
the granules: for each granule, the tool looks for the map of the dataset that
is related to the granule in time, as the option **method** says. A granule
for which one of the datasets has no related map is skipped. The order of the
datasets in the expression does not matter, only their order in **inputs**. If
the list names only one dataset, every map of it is a granule. The datasets may
be in other mapsets (`precipitation_monthly@t_rast_mapcalc`); the expression
then uses the name without the mapset or, as in **inputs**, with it, and the
mapset does not have to be in the search path (see [Datasets of other
mapsets](temporalintro.md#datasets-of-other-mapsets)).

A name with a dot, such as `bands.S2_8`, is a dataset name and a semantic
label. It selects the maps of the dataset that have this label, and the
expression uses the same name. The new maps take the semantic label of the map
of the sampler. The eighth example shows it; see
*[i.band.library](i.band.library.md)* for the concept of semantic labels. A
dataset of an earlier release can have a dot in its name. It is found by its
whole name: the mapsets are searched in turn, the current one first, and in
each the whole name is tried before the text after the dot is read as a
semantic label.

The result dataset is the option **output**. It always belongs to the current
mapset, and so do the new maps. It takes the temporal type and the semantic type
of the first dataset of **inputs**. Each new map has the start and end time of
its granule. An existing dataset **output** is refused unless the flag
**--overwrite** is given; then it is replaced, and the tool warns that it
unregisters all maps of the old dataset. A name with a dot is refused as
**output**.

The option **where** is an SQL condition on the registered maps, for example
`start_time >= '2026-06-11'`. It applies to every dataset in **inputs**, the
sampler too, so only the remaining maps are granules and partners. The new maps
are numbered from 1 among the remaining granules. The eighth example uses it.

The tool computes in the current region, as *r.mapcalc* does. A map that lies
outside the region reads as null.

### The expression

The option **expression** is the right side of an *r.mapcalc* expression,
without the `map =` of a full one. In it, the name of each dataset of **inputs**
stands for the related map of the current granule, so
`precipitation_monthly * temperature_monthly` multiplies the map of
`precipitation_monthly` by the related map of `temperature_monthly`, and
`temperature_monthly * precipitation_monthly` does the same. Any other raster
map can be used by its name. The operators and functions of *r.mapcalc* are
available.

The tool puts the names of the maps into the text of the expression and
numbers the results, so with the expression `soil * 2` a call with four
granules runs four statements such as `doubled_1=soil_1 * 2`. A dataset name
is replaced only where it stands as a whole name: not inside a longer name
(`soil` in `soil_deep`), and not before an opening parenthesis, where it is the
name of a function (`day` in `start_day()`); see the ninth example. A modifier
of *r.mapcalc* in front of the name applies to the map of the granule, so
`@soil` reads the category labels of `soil_1`; after a map name, as in
`elevation@soil`, the name is a mapset and stays. The rest of
the expression goes to *r.mapcalc* as written, blanks included. Two inputs with
the same name, such as `soil,soil`, are refused before any map is computed,
because the expression could not tell them apart.

The option **basename** is required. The new maps are named after it, followed
by an underscore and the number of their granule, counted from 1 in the order
of the sampler. The number has as many digits as the number of granules
needs, filled up with zeros: `doubled_1` for four granules, `doubled_01` for
eleven. A granule that is skipped, or whose result is empty, leaves a gap in
the numbers.

### Temporal variables

The following variables are replaced by a number for each granule before the
expression goes to *r.mapcalc*. They work with absolute and with relative
time.

- `td()`: the length of the granule, the end minus the start, in days and
  fractions of days for absolute time, in the unit of the dataset for relative
  time; null for a time instant.
- `start_time()`: the start of the granule minus the start of the first
  granule, in days or in the unit.
- `end_time()`: the end of the granule minus the start of the first granule, in
  days or in the unit; null for a time instant, which has no end.

For absolute time, the calendar functions give a part of the start or the end
of the granule as a whole number. Each function exists for the start
(`start_doy()`) and for the end (`end_doy()`) of the granule, and the end
functions are null for a time instant.

- `start_doy()`: the day of the year, 1 to 366.
- `start_dow()`: the day of the week, 1 to 7; Monday is 1.
- `start_year()`: the year.
- `start_month()`: the month, 1 to 12.
- `start_week()`: the ISO week of the year. Weeks start on Monday, and the
  first days of January can belong to week 52 or 53.
- `start_day()`: the day of the month, 1 to 31.
- `start_hour()`: the hour, 0 to 23.
- `start_minute()`: the minute, 0 to 59.
- `start_second()`: the second, 0 to 59.

With relative time, a calendar function stops the tool with an error. The fifth
example shows the variables for both kinds of time.

### Select the related maps

The option **method** is a list of the sampling methods. It names the relation
between the granule and the map of another dataset. The default is `equal`. A
map is related to the granule if it has one of the listed relations. The third
example shows the methods.

- `equal`: the map has the start and the end time of the granule.
- `during`: the granule lies inside the time interval of the map. The map may
  share the start or the end of the granule, but is not equal to it: for a
  granule from 10 to 20 the maps from 5 to 25, from 10 to 25 and from 5 to 20.
- `contain`: the map lies inside the granule. It may share the start or the
  end of the granule, but is not equal to it.
- `overlap`: the map starts inside the granule and ends after it, or starts
  before it and ends inside it.
- `follows`: the map ends when the granule starts.
- `precedes`: the map starts when the granule ends.
- `start`: the maps that lie inside the granule, the maps that start before it
  and end inside it, the maps that cover it while sharing its start or its
  end, and the equal map. It does not take a map that covers the granule
  strictly and a map that starts inside it and ends after it.

If more than one map of a dataset is related to a granule, the tool warns on
the standard error and uses only one of them. Which one, follows from the
order in which it tries the relations. First come the methods `equal`,
`during`, `follows` and `precedes`, in the order of the list **method**; then
the group `start`, which tries the equal map last, then `overlap` and then
`contain`, if they are in the list.
Within one relation, the map with the earliest start time is taken, and for
equal start times the map with the smaller id. So for the list
`contain,during` a map found by `during` wins over a map found by `contain`.
The fourth example shows this. Choose the first dataset of **inputs** so that
its granules are the time steps you want, and use
*[t.rast.aggregate.ds](t.rast.aggregate.ds.md)* to make datasets with one map
per step.

### Empty results and spatial relation

A new map that has no valid cell, that is, no minimum and no maximum, is empty.
By default it is not registered in **output** and is removed after the run. The
flag **-n** registers the empty maps and keeps them. An expression such as
`if(soil > 15, soil, null())` selects time steps by values in this way. If all
results are empty, **output** exists but holds no map.

The flag **-s** adds a spatial condition to the temporal one: a map is related
to the granule only if its extent, from west to east and from south to north,
touches or overlaps that of the granule, so a shared edge counts. A granule
without a related map is skipped. The seventh example shows the difference.

### Parallel processing

The option **nprocs** sets the number of *r.mapcalc* processes that run at the
same time. The default is `1`. The result does not depend on it.

## NOTES

*t.rast.mapcalc* has the same options as *t.rast3d.mapcalc*, plus **where**,
and works on raster maps only. The maps of the datasets are not touched; the
tool makes new maps.

If a map of the base name exists as a registered map and **--overwrite** is not
given, the tool stops before it computes any map, with "Map ... is already in
temporal database, use overwrite flag to overwrite". If the dataset **output**
exists, the tool stops with "Space time raster dataset ... is already in the
database. Use the overwrite flag.".

With **--overwrite**, the maps of the old dataset are unregistered from it, not
removed. A new run with fewer maps leaves the surplus old maps in the mapset;
the tenth example shows it.

The tool stops with an error if an input dataset does not exist ("Space time
dataset ... of type strds not found"), if **method** names a method that does
not exist ("Value ... out of range for parameter method"), if **where** is not
valid SQL ("Invalid where condition ...") and if *r.mapcalc* does not accept
the expression ("Error while mapcalc computation"). A calendar function with
relative time stops it with
`The temporal operators <start_*> support only absolute time.` (`<end_*>` for
an end function). The tool announces its steps
on the standard error with "Starting temporal sampling..." (with **-s**:
"Starting spatio-temporal sampling...") and "Starting mapcalc
computation...".

If **inputs** names more than one dataset and the sampler has only time
instants, or the datasets have different temporal types, the first dataset
cannot sample the others: the tool stops before it computes any map, with "The
temporal map type of the sample dataset must be interval" or "The space time
datasets must be of the same temporal type". If **where** leaves no map in the
sampler, the tool warns "The where condition selects no map of space time
raster dataset ...". A call with one dataset needs no sampling: time instants
work as in the fifth example; if **where** leaves no map, the tool gives the
same warning, and if the dataset has no maps and no **where** is given, it
warns "No maps registered in input dataset ...". Labels of one dataset, as in
`bands.S2_8,bands.S2_4`, are not sampled either: if a later label has no map,
the tool warns in the same way and names that label. If a sampler without
maps (a label without maps, or a dataset without maps) samples another dataset
of the same temporal type and no **where** is given, the tool warns "No samples
found for map calculation". In these cases it makes no dataset **output**
and ends with status 0. If **where** leaves no map in another dataset that the
sampler samples, no granule has a partner, and the tool makes an **output**
without maps.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_mapcalc` and sets the computational region
to North Carolina with cells of 1 km; the later examples work in this mapset
and region, except the last, which creates a second mapset with the same
region. The first two examples and the sixth compute with generated series of
monthly temperature and precipitation. The examples that show how granules,
sampling and the temporal variables work use maps with small constant values,
so that the results can be checked by hand.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_mapcalc -->

<!-- markdownlint-disable MD046 -->

### Apply an expression to every map

The dataset `temperature_monthly` holds twelve maps of the monthly mean air
temperature in 2020, in degrees Celsius rounded to tenths. They are generated
from the elevation model `elev_state_500m`: 16.5 degrees at sea level and the
northing 160 km, an annual cycle of plus and minus 10.5 degrees with its
maximum in July, 6.5 degrees less for every 1000 m of elevation, and 1 degree
more for every 100 km to the south. Each map is an interval of one month.

The first block makes the mapset, the region and the dataset, and converts the
maps to degrees Fahrenheit. The name `temperature_monthly` in the expression
stands for the map of each month. The new maps are named `fahrenheit_01` to
`fahrenheit_12` after the granules, and each has the time of its source map.
**nprocs** lets two *r.mapcalc* processes run at the same time; the result is
the same as with one. The result is rounded to tenths, as the source maps are.
In July the warmest cell has 28.4 degrees Celsius, which is 83.1 degrees
Fahrenheit, and in January the coldest has -7.0 degrees Celsius, which is
19.4 degrees Fahrenheit. The second block shows what the new dataset takes
from `temperature_monthly`: the temporal type and the semantic type, and the
granularity that follows from the maps it holds.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_mapcalc
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
    t.rast.mapcalc inputs=temperature_monthly output=fahrenheit \
        basename=fahrenheit nprocs=2 \
        expression="round((temperature_monthly * 1.8 + 32) * 10) / 10.0"
    t.rast.list input=fahrenheit columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    fahrenheit_01|2020-01-01 00:00:00|2020-02-01 00:00:00|19.4|45.5
    fahrenheit_02|2020-02-01 00:00:00|2020-03-01 00:00:00|21.0|47.1
    fahrenheit_03|2020-03-01 00:00:00|2020-04-01 00:00:00|27.1|53.2
    fahrenheit_04|2020-04-01 00:00:00|2020-05-01 00:00:00|36.3|62.4
    fahrenheit_05|2020-05-01 00:00:00|2020-06-01 00:00:00|45.9|72.0
    fahrenheit_06|2020-06-01 00:00:00|2020-07-01 00:00:00|53.6|79.7
    fahrenheit_07|2020-07-01 00:00:00|2020-08-01 00:00:00|57.0|83.1
    fahrenheit_08|2020-08-01 00:00:00|2020-09-01 00:00:00|55.6|81.7
    fahrenheit_09|2020-09-01 00:00:00|2020-10-01 00:00:00|49.3|75.6
    fahrenheit_10|2020-10-01 00:00:00|2020-11-01 00:00:00|40.3|66.4
    fahrenheit_11|2020-11-01 00:00:00|2020-12-01 00:00:00|30.6|56.7
    fahrenheit_12|2020-12-01 00:00:00|2021-01-01 00:00:00|23.0|49.1
    ```

    ```sh
    t.info -g input=fahrenheit | grep -E "^(temporal_type|semantic_type|granularity)="
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    granularity='1 month'
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast_mapcalc")
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
    tools.t_rast_mapcalc(
        inputs="temperature_monthly",
        output="fahrenheit",
        basename="fahrenheit",
        expression="round((temperature_monthly * 1.8 + 32) * 10) / 10.0",
        nprocs=2,
    )
    columns = "name,start_time,end_time,min,max"
    print(tools.t_rast_list(input="fahrenheit", columns=columns).text)
    ```

    ```text
    name|start_time|end_time|min|max
    fahrenheit_01|2020-01-01 00:00:00|2020-02-01 00:00:00|19.4|45.5
    fahrenheit_02|2020-02-01 00:00:00|2020-03-01 00:00:00|21.0|47.1
    fahrenheit_03|2020-03-01 00:00:00|2020-04-01 00:00:00|27.1|53.2
    fahrenheit_04|2020-04-01 00:00:00|2020-05-01 00:00:00|36.3|62.4
    fahrenheit_05|2020-05-01 00:00:00|2020-06-01 00:00:00|45.9|72.0
    fahrenheit_06|2020-06-01 00:00:00|2020-07-01 00:00:00|53.6|79.7
    fahrenheit_07|2020-07-01 00:00:00|2020-08-01 00:00:00|57.0|83.1
    fahrenheit_08|2020-08-01 00:00:00|2020-09-01 00:00:00|55.6|81.7
    fahrenheit_09|2020-09-01 00:00:00|2020-10-01 00:00:00|49.3|75.6
    fahrenheit_10|2020-10-01 00:00:00|2020-11-01 00:00:00|40.3|66.4
    fahrenheit_11|2020-11-01 00:00:00|2020-12-01 00:00:00|30.6|56.7
    fahrenheit_12|2020-12-01 00:00:00|2021-01-01 00:00:00|23.0|49.1
    ```

    ```python
    info = tools.t_info(input="fahrenheit", flags="g").keyval
    for key in ("temporal_type", "semantic_type", "granularity"):
        print(f"{key}={info[key]}")
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    granularity='1 month'
    ```

### Combine the maps of several datasets

The dataset `precipitation_monthly` holds twelve maps of the monthly
precipitation sum in 2020, in whole millimeters. They are generated, not
measured: the monthly normals of the climate stations in `precip_30ynormals`
are interpolated for each month with *v.surf.idw* from 12 neighbours and
multiplied by an assumed factor for a wet year, between 0.8 and 1.7. The maps
are null outside North Carolina. The twelve interpolated normals stay in the
mapset as `precipitation_normal_01` to `precipitation_normal_12`.
*t.rast.aggregate* adds the dataset `precipitation_quarterly` with four maps,
the sums of three months each, so each map of it is an interval of one quarter.

The first block calculates the share of a month in the precipitation of its
quarter. The first dataset of **inputs** is the sampler, so the result has
twelve maps of one month each, and each month of `precipitation_monthly` lies
during a map of `precipitation_quarterly`. The expression divides the two and
gives percent rounded to tenths. In January a cell has between 28.0 and 38.6
percent of the precipitation of the first quarter; before the rounding, the
three shares of a cell add up to 100 percent.

The second block swaps the order in **inputs**, so the sampler is
`precipitation_quarterly` and the result has four maps of three months each.
With **method** `contain`, each granule contains three monthly maps; the tool
warns on the standard error and uses the first of them, the map of the first
month of the quarter. The result is the sum of the quarter minus that map, so
the precipitation of the other two months: 222 to 521 mm for February and
March.

The third block leaves out **method**. The default is `equal`, and no month
has the time of a quarter, so every granule is skipped. The tool does not
fail; the new dataset exists and holds no map.

The fourth block names the default **method** `equal` and gives it partners.
The sampler is `temperature_monthly`, and every month has a map of
`precipitation_monthly` with the same time. The expression names
`precipitation_monthly` first, which does not matter. It chooses the
calculation by the time of the granule, a simple climatic water balance: from
April to September it subtracts an assumed evaporation of 4 mm for every
degree Celsius, rounded to whole millimeters, from the precipitation; in the
other months it keeps the precipitation. So the maps from October to March
have the values of `precipitation_monthly`, for example 94 to 249 mm in
January, and in July the balance is between -14 and 136 mm, negative where the
evaporation exceeds the precipitation.

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
    t.rast.aggregate input=precipitation_monthly output=precipitation_quarterly \
        basename=precipitation_quarterly granularity="3 months" method=sum
    t.rast.mapcalc inputs=precipitation_monthly,precipitation_quarterly \
        output=quarter_share basename=quarter_share method=during \
        expression="round(1000.0 * precipitation_monthly / precipitation_quarterly) / 10.0"
    t.rast.list input=quarter_share columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    quarter_share_01|2020-01-01 00:00:00|2020-02-01 00:00:00|28.0|38.6
    quarter_share_02|2020-02-01 00:00:00|2020-03-01 00:00:00|35.9|43.7
    quarter_share_03|2020-03-01 00:00:00|2020-04-01 00:00:00|22.5|30.5
    quarter_share_04|2020-04-01 00:00:00|2020-05-01 00:00:00|24.4|35.7
    quarter_share_05|2020-05-01 00:00:00|2020-06-01 00:00:00|39.6|50.0
    quarter_share_06|2020-06-01 00:00:00|2020-07-01 00:00:00|20.7|33.2
    quarter_share_07|2020-07-01 00:00:00|2020-08-01 00:00:00|27.4|40.6
    quarter_share_08|2020-08-01 00:00:00|2020-09-01 00:00:00|38.3|49.7
    quarter_share_09|2020-09-01 00:00:00|2020-10-01 00:00:00|18.5|27.5
    quarter_share_10|2020-10-01 00:00:00|2020-11-01 00:00:00|20.0|33.9
    quarter_share_11|2020-11-01 00:00:00|2020-12-01 00:00:00|40.1|53.6
    quarter_share_12|2020-12-01 00:00:00|2021-01-01 00:00:00|20.6|31.1
    ```

    ```sh
    t.rast.mapcalc inputs=precipitation_quarterly,precipitation_monthly \
        output=rest_of_quarter basename=rest_of_quarter method=contain \
        expression="precipitation_quarterly - precipitation_monthly"
    t.rast.list input=rest_of_quarter columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    rest_of_quarter_1|2020-01-01 00:00:00|2020-04-01 00:00:00|222.0|521.0
    rest_of_quarter_2|2020-04-01 00:00:00|2020-07-01 00:00:00|217.0|501.0
    rest_of_quarter_3|2020-07-01 00:00:00|2020-10-01 00:00:00|186.0|473.0
    rest_of_quarter_4|2020-10-01 00:00:00|2021-01-01 00:00:00|174.0|518.0
    ```

    ```sh
    t.rast.mapcalc inputs=precipitation_monthly,precipitation_quarterly \
        output=unmatched basename=unmatched \
        expression="precipitation_monthly + precipitation_quarterly"
    t.info -g input=unmatched | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=0
    ```

    ```sh
    t.rast.mapcalc inputs=temperature_monthly,precipitation_monthly \
        output=balance basename=balance method=equal \
        expression="if(start_month() >= 4 && start_month() <= 9, precipitation_monthly - round(4 * temperature_monthly), precipitation_monthly)"
    t.rast.list input=balance columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    balance_01|2020-01-01 00:00:00|94.0|249.0
    balance_02|2020-02-01 00:00:00|133.0|309.0
    balance_03|2020-03-01 00:00:00|88.0|212.0
    balance_04|2020-04-01 00:00:00|30.0|194.0
    balance_05|2020-05-01 00:00:00|50.0|289.0
    balance_06|2020-06-01 00:00:00|-16.0|97.0
    balance_07|2020-07-01 00:00:00|-14.0|136.0
    balance_08|2020-08-01 00:00:00|21.0|215.0
    balance_09|2020-09-01 00:00:00|-15.0|85.0
    balance_10|2020-10-01 00:00:00|55.0|160.0
    balance_11|2020-11-01 00:00:00|104.0|350.0
    balance_12|2020-12-01 00:00:00|59.0|177.0
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
    tools.t_rast_aggregate(
        input="precipitation_monthly",
        output="precipitation_quarterly",
        basename="precipitation_quarterly",
        granularity="3 months",
        method="sum",
    )
    tools.t_rast_mapcalc(
        inputs="precipitation_monthly,precipitation_quarterly",
        output="quarter_share",
        basename="quarter_share",
        method="during",
        expression="round(1000.0 * precipitation_monthly / precipitation_quarterly) / 10.0",
    )
    print(tools.t_rast_list(input="quarter_share", columns=columns).text)
    ```

    ```text
    name|start_time|end_time|min|max
    quarter_share_01|2020-01-01 00:00:00|2020-02-01 00:00:00|28.0|38.6
    quarter_share_02|2020-02-01 00:00:00|2020-03-01 00:00:00|35.9|43.7
    quarter_share_03|2020-03-01 00:00:00|2020-04-01 00:00:00|22.5|30.5
    quarter_share_04|2020-04-01 00:00:00|2020-05-01 00:00:00|24.4|35.7
    quarter_share_05|2020-05-01 00:00:00|2020-06-01 00:00:00|39.6|50.0
    quarter_share_06|2020-06-01 00:00:00|2020-07-01 00:00:00|20.7|33.2
    quarter_share_07|2020-07-01 00:00:00|2020-08-01 00:00:00|27.4|40.6
    quarter_share_08|2020-08-01 00:00:00|2020-09-01 00:00:00|38.3|49.7
    quarter_share_09|2020-09-01 00:00:00|2020-10-01 00:00:00|18.5|27.5
    quarter_share_10|2020-10-01 00:00:00|2020-11-01 00:00:00|20.0|33.9
    quarter_share_11|2020-11-01 00:00:00|2020-12-01 00:00:00|40.1|53.6
    quarter_share_12|2020-12-01 00:00:00|2021-01-01 00:00:00|20.6|31.1
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="precipitation_quarterly,precipitation_monthly",
        output="rest_of_quarter",
        basename="rest_of_quarter",
        method="contain",
        expression="precipitation_quarterly - precipitation_monthly",
    )
    print(tools.t_rast_list(input="rest_of_quarter", columns=columns).text)
    ```

    ```text
    name|start_time|end_time|min|max
    rest_of_quarter_1|2020-01-01 00:00:00|2020-04-01 00:00:00|222.0|521.0
    rest_of_quarter_2|2020-04-01 00:00:00|2020-07-01 00:00:00|217.0|501.0
    rest_of_quarter_3|2020-07-01 00:00:00|2020-10-01 00:00:00|186.0|473.0
    rest_of_quarter_4|2020-10-01 00:00:00|2021-01-01 00:00:00|174.0|518.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="precipitation_monthly,precipitation_quarterly",
        output="unmatched",
        basename="unmatched",
        expression="precipitation_monthly + precipitation_quarterly",
    )
    info = tools.t_info(input="unmatched", flags="g").keyval
    print(f"number_of_maps={info['number_of_maps']}")
    ```

    ```text
    number_of_maps=0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="temperature_monthly,precipitation_monthly",
        output="balance",
        basename="balance",
        method="equal",
        expression=(
            "if(start_month() >= 4 && start_month() <= 9,"
            " precipitation_monthly - round(4 * temperature_monthly),"
            " precipitation_monthly)"
        ),
    )
    print(tools.t_rast_list(input="balance", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    balance_01|2020-01-01 00:00:00|94.0|249.0
    balance_02|2020-02-01 00:00:00|133.0|309.0
    balance_03|2020-03-01 00:00:00|88.0|212.0
    balance_04|2020-04-01 00:00:00|30.0|194.0
    balance_05|2020-05-01 00:00:00|50.0|289.0
    balance_06|2020-06-01 00:00:00|-16.0|97.0
    balance_07|2020-07-01 00:00:00|-14.0|136.0
    balance_08|2020-08-01 00:00:00|21.0|215.0
    balance_09|2020-09-01 00:00:00|-15.0|85.0
    balance_10|2020-10-01 00:00:00|55.0|160.0
    balance_11|2020-11-01 00:00:00|104.0|350.0
    balance_12|2020-12-01 00:00:00|59.0|177.0
    ```

### Choose the sampling method

The dataset `slots` has nine granules of 10 days with relative time, from day
110 to 120, from 210 to 220 and so on up to 910 to 920. Its map `slot_k` has the
value `k`. The dataset `probes` has one map for each granule, `probe_k` with the
value `10 * k`, and each has a different position relative to the granule:

1. `probe_1` has the same times, 110 to 120.
2. `probe_2` lies inside the granule, 214 to 218.
3. `probe_3` covers the granule, 305 to 325.
4. `probe_4` starts inside the granule and ends after it, 415 to 425.
5. `probe_5` starts before the granule and ends inside it, 505 to 515.
6. `probe_6` ends when the granule starts, 600 to 610.
7. `probe_7` starts when the granule ends, 720 to 730.
8. `probe_8` starts with the granule and ends after it, 810 to 825.
9. `probe_9` starts before the granule and ends with it, 905 to 920.

The loop runs the tool once for each method and prints the maps of the result.
The number at the end of a name is the number of the granule that found a
related map: `equal` finds the map of granule 1, `during` the ones of the
granules 3, 8 and 9, `contain` granule 2, `overlap` the granules 4 and 5,
`follows` granule 6 and `precedes` granule 7. The method `start` finds the
granules 1, 2, 5, 8 and 9. The last two blocks show that **method** takes a
list. Without **method** the default `equal` finds only the granule 1. With
the list `during,overlap,contain,equal` the tool collects the granules 1 to 5,
8 and 9, and the listing shows that the maps have the times of the granules.

The time of the datasets is relative, in days, and the result takes it over.
The files for *[t.register](t.register.md)* list one map per line with its
start and end time.

=== "Command line"

    ```sh
    for step in 1 2 3 4 5 6 7 8 9; do
        r.mapcalc expression="slot_$step = $step"
        r.mapcalc expression="probe_$step = 10 * $step"
    done
    cat > slots.txt <<EOF
    slot_1|110|120
    slot_2|210|220
    slot_3|310|320
    slot_4|410|420
    slot_5|510|520
    slot_6|610|620
    slot_7|710|720
    slot_8|810|820
    slot_9|910|920
    EOF
    cat > probes.txt <<EOF
    probe_1|110|120
    probe_2|214|218
    probe_3|305|325
    probe_4|415|425
    probe_5|505|515
    probe_6|600|610
    probe_7|720|730
    probe_8|810|825
    probe_9|905|920
    EOF
    t.create temporaltype=relative output=slots title="Slots" \
        description="Granules of 10 days"
    t.create temporaltype=relative output=probes title="Probes" \
        description="One probe for each granule"
    t.register input=slots unit=days file=slots.txt
    t.register input=probes unit=days file=probes.txt
    for method in equal during contain overlap follows precedes start; do
        t.rast.mapcalc inputs=slots,probes output=by_$method \
            basename=$method expression="slots + probes" method=$method
        names=$(t.rast.list -u input=by_$method columns=name method=comma)
        echo "$method: $names"
    done
    ```

    ```text
    equal: equal_1
    during: during_3,during_8,during_9
    contain: contain_2
    overlap: overlap_4,overlap_5
    follows: follows_6
    precedes: precedes_7
    start: start_1,start_2,start_5,start_8,start_9
    ```

    ```sh
    t.rast.mapcalc inputs=slots,probes output=by_default basename=default \
        expression="slots + probes"
    t.rast.list input=by_default columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    default_1|110|120|11.0|11.0
    ```

    ```sh
    t.rast.mapcalc inputs=slots,probes output=by_list basename=list \
        expression="slots + probes" method=during,overlap,contain,equal
    t.rast.list input=by_list columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    list_1|110|120|11.0|11.0
    list_2|210|220|22.0|22.0
    list_3|310|320|33.0|33.0
    list_4|410|420|44.0|44.0
    list_5|510|520|55.0|55.0
    list_8|810|820|88.0|88.0
    list_9|910|920|99.0|99.0
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    for step in range(1, 10):
        tools.r_mapcalc(expression=f"slot_{step} = {step}")
        tools.r_mapcalc(expression=f"probe_{step} = 10 * {step}")
    Path("slots.txt").write_text(
        "slot_1|110|120\nslot_2|210|220\nslot_3|310|320\nslot_4|410|420\n"
        "slot_5|510|520\nslot_6|610|620\nslot_7|710|720\nslot_8|810|820\n"
        "slot_9|910|920\n"
    )
    Path("probes.txt").write_text(
        "probe_1|110|120\nprobe_2|214|218\nprobe_3|305|325\nprobe_4|415|425\n"
        "probe_5|505|515\nprobe_6|600|610\nprobe_7|720|730\nprobe_8|810|825\n"
        "probe_9|905|920\n"
    )
    tools.t_create(
        temporaltype="relative",
        output="slots",
        title="Slots",
        description="Granules of 10 days",
    )
    tools.t_create(
        temporaltype="relative",
        output="probes",
        title="Probes",
        description="One probe for each granule",
    )
    tools.t_register(input="slots", unit="days", file="slots.txt")
    tools.t_register(input="probes", unit="days", file="probes.txt")
    for method in ("equal", "during", "contain", "overlap", "follows", "precedes", "start"):
        tools.t_rast_mapcalc(
            inputs="slots,probes",
            output=f"by_{method}",
            basename=method,
            expression="slots + probes",
            method=method,
        )
        names = tools.t_rast_list(
            input=f"by_{method}", columns="name", method="comma", flags="u"
        ).text
        print(f"{method}: {names}")
    ```

    ```text
    equal: equal_1
    during: during_3,during_8,during_9
    contain: contain_2
    overlap: overlap_4,overlap_5
    follows: follows_6
    precedes: precedes_7
    start: start_1,start_2,start_5,start_8,start_9
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="slots,probes",
        output="by_default",
        basename="default",
        expression="slots + probes",
    )
    print(
        tools.t_rast_list(
            input="by_default", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    default_1|110|120|11.0|11.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="slots,probes",
        output="by_list",
        basename="list",
        expression="slots + probes",
        method="during,overlap,contain,equal",
    )
    print(
        tools.t_rast_list(input="by_list", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    list_1|110|120|11.0|11.0
    list_2|210|220|22.0|22.0
    list_3|310|320|33.0|33.0
    list_4|410|420|44.0|44.0
    list_5|510|520|55.0|55.0
    list_8|810|820|88.0|88.0
    list_9|910|920|99.0|99.0
    ```

### Several related maps for one granule

The dataset `window` has one map of 10 days, from day 10 to 20, with the
value 1. The dataset `cands` has four maps that are all related to it, in
different ways: `cand_a` from 12 to 18 with the value 100 (inside the granule),
`cand_b` from 5 to 25 with the value 200 (covers it), `cand_c` from 11 to 13
with the value 300 (inside, and starts before `cand_a`) and `cand_d` from 10 to
20 with the value 400 (equal).

The expression is only `cands`, so the result holds the value of the map the
tool took. The loop prints it for five lists of methods. With the list
`during,overlap,contain,equal` it is 200: `during` comes before `contain` and
`equal` and finds `cand_b`. With `contain,during` it is 200 as well, because
the order of the list only counts for `equal`, `during`, `follows` and
`precedes`, and `contain` is tried after them. With `equal,during,contain` it
is 400, because `equal` is first, and with `during,equal` it is 200 again,
because `during` is first now. With `contain` alone it is 300: of the maps
inside the granule, `cand_c` starts first. The tool warns on the standard
error when it chooses between maps.

=== "Command line"

    ```sh
    r.mapcalc expression="window_1 = 1"
    r.mapcalc expression="cand_a = 100"
    r.mapcalc expression="cand_b = 200"
    r.mapcalc expression="cand_c = 300"
    r.mapcalc expression="cand_d = 400"
    cat > window.txt <<EOF
    window_1|10|20
    EOF
    cat > cands.txt <<EOF
    cand_a|12|18
    cand_b|5|25
    cand_c|11|13
    cand_d|10|20
    EOF
    t.create temporaltype=relative output=window title="Window" \
        description="One granule"
    t.create temporaltype=relative output=cands title="Candidates" \
        description="Four maps related to the granule"
    t.register input=window unit=days file=window.txt
    t.register input=cands unit=days file=cands.txt
    number=0
    for methods in during,overlap,contain,equal contain,during \
        equal,during,contain during,equal contain; do
        number=$((number + 1))
        t.rast.mapcalc inputs=window,cands output=taken_$number \
            basename=taken_$number expression="cands" method=$methods
        value=$(t.rast.list -u input=taken_$number columns=min)
        echo "$methods: $value"
    done
    ```

    ```text
    during,overlap,contain,equal: 200.0
    contain,during: 200.0
    equal,during,contain: 400.0
    during,equal: 200.0
    contain: 300.0
    ```

=== "Python (grass.tools)"

    ```python
    for name, value in (("window_1", 1), ("cand_a", 100), ("cand_b", 200)):
        tools.r_mapcalc(expression=f"{name} = {value}")
    tools.r_mapcalc(expression="cand_c = 300")
    tools.r_mapcalc(expression="cand_d = 400")
    Path("window.txt").write_text("window_1|10|20\n")
    Path("cands.txt").write_text("cand_a|12|18\ncand_b|5|25\ncand_c|11|13\ncand_d|10|20\n")
    tools.t_create(
        temporaltype="relative",
        output="window",
        title="Window",
        description="One granule",
    )
    tools.t_create(
        temporaltype="relative",
        output="cands",
        title="Candidates",
        description="Four maps related to the granule",
    )
    tools.t_register(input="window", unit="days", file="window.txt")
    tools.t_register(input="cands", unit="days", file="cands.txt")
    lists = (
        "during,overlap,contain,equal",
        "contain,during",
        "equal,during,contain",
        "during,equal",
        "contain",
    )
    for number, methods in enumerate(lists, start=1):
        tools.t_rast_mapcalc(
            inputs="window,cands",
            output=f"taken_{number}",
            basename=f"taken_{number}",
            expression="cands",
            method=methods,
        )
        value = tools.t_rast_list(input=f"taken_{number}", columns="min", flags="u").text
        print(f"{methods}: {value}")
    ```

    ```text
    during,overlap,contain,equal: 200.0
    contain,during: 200.0
    equal,during,contain: 400.0
    during,equal: 200.0
    contain: 300.0
    ```

### Use the time of the granule

The first block makes the dataset `soil` with four maps for the days from 1 to
4 March 2026. Each map has the same value in every cell: 2, 12, 22 and 32
degrees Celsius. The expressions of the first four blocks need no map, only the
time of the granule, so they name `soil` only in **inputs**. The granules are
the days; 1 March 2026 is a Sunday, the 60th day of the year. Each block prints
the smallest and largest value of every new map; all cells of a map have the
same value.

- Block 1: `start_time()` counts the hundreds, `td()` the tens and
  `end_time()` the ones. The days start 0, 1, 2 and 3 days after the first,
  are 1 day long and end 1, 2, 3 and 4 days after the start of the first, so
  the results are 11, 112, 213 and 314.
- Block 2: the day of the year and the day of the week, tens and ones again:
  60 and 7 (Sunday) for the first day, then 61 and 1 (Monday) and so on, so
  607, 611, 622 and 633.
- Block 3: the month and the end day. The month is 3 and the end day is 2 to
  5, so the results are 302 to 305.
- Block 4: the weeks, which start on Monday. The first day starts in week 9
  and ends on Monday 2 March, in week 10, so 910, and 1010 for the other days.

The next three blocks show time instants and the ISO weeks.

- Block 5: the dataset `gauge` has two time instants, at 06:00 on 1 March and
  at 18:00 on 2 March, and its maps have the values 1 and 2. `start_time()` is
  the offset in days and fractions of days from the first instant, 0 and 1.5,
  and `end_time()` is null, so `isnull()` is true and the result is 100 and
  101.5. The listing shows `None` as the end of the maps.
- Block 6: `td()` of an instant is null as well, so the result is 7.
- Block 7: the dataset `newyear` has one day, 1 January 2027, which is a
  Friday in week 53 of 2026, and `start_week()` gives 53.

The dataset `model` has three steps of 5 hours with relative time.
`start_time()`, `td()` and `end_time()` give numbers in the unit of the dataset,
hours.

- Block 8: the steps start 0, 5 and 10 hours after the first, are 5 hours long
  and end 5, 10 and 15 hours after the start of the first. With the expression
  of the first block, the results are 55, 560 and 1065.
- Block 9: the calendar functions need absolute time. The block calls
  `start_doy()` on `model`; the tool prints its error and stops without a
  result dataset. The block shows the error and then prints
  `t.rast.mapcalc failed`.

=== "Command line"

    ```sh
    for step in 1 2 3 4; do
        r.mapcalc expression="soil_$step = $((2 + 10 * ($step - 1)))"
    done
    t.create output=soil title="Soil" \
        description="Soil temperature in degree Celsius, one map per day"
    t.register -i input=soil \
        maps=soil_1,soil_2,soil_3,soil_4 start=2026-03-01 increment="1 day"
    t.rast.mapcalc inputs=soil output=when basename=when \
        expression="start_time() * 100 + td() * 10 + end_time()"
    t.rast.list input=when columns=name,min,max
    ```

    ```text
    name|min|max
    when_1|11.0|11.0
    when_2|112.0|112.0
    when_3|213.0|213.0
    when_4|314.0|314.0
    ```

    ```sh
    t.rast.mapcalc inputs=soil output=calendar basename=calendar \
        expression="start_doy() * 10 + start_dow()"
    t.rast.list input=calendar columns=name,min,max
    ```

    ```text
    name|min|max
    calendar_1|607.0|607.0
    calendar_2|611.0|611.0
    calendar_3|622.0|622.0
    calendar_4|633.0|633.0
    ```

    ```sh
    t.rast.mapcalc inputs=soil output=month_day basename=month_day \
        expression="start_month() * 100 + end_day()"
    t.rast.list input=month_day columns=name,min,max
    ```

    ```text
    name|min|max
    month_day_1|302.0|302.0
    month_day_2|303.0|303.0
    month_day_3|304.0|304.0
    month_day_4|305.0|305.0
    ```

    ```sh
    t.rast.mapcalc inputs=soil output=weeks basename=weeks \
        expression="start_week() * 100 + end_week()"
    t.rast.list input=weeks columns=name,min,max
    ```

    ```text
    name|min|max
    weeks_1|910.0|910.0
    weeks_2|1010.0|1010.0
    weeks_3|1010.0|1010.0
    weeks_4|1010.0|1010.0
    ```

    ```sh
    r.mapcalc expression="gauge_1 = 1"
    r.mapcalc expression="gauge_2 = 2"
    t.create output=gauge title="Gauge" description="Two instants"
    t.register input=gauge maps=gauge_1 start="2026-03-01 06:00:00"
    t.register input=gauge maps=gauge_2 start="2026-03-02 18:00:00"
    t.rast.mapcalc inputs=gauge output=instants basename=instants \
        expression="start_time() + if(isnull(end_time()), 100, 0)"
    t.rast.list input=instants columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    instants_1|2026-03-01 06:00:00|None|100.0|100.0
    instants_2|2026-03-02 18:00:00|None|101.5|101.5
    ```

    ```sh
    t.rast.mapcalc inputs=gauge output=lengths basename=lengths \
        expression="if(isnull(td()), 7, 0)"
    t.rast.list input=lengths columns=name,min,max
    ```

    ```text
    name|min|max
    lengths_1|7.0|7.0
    lengths_2|7.0|7.0
    ```

    ```sh
    r.mapcalc expression="newyear_1 = 1"
    t.create output=newyear title="New year" description="One day"
    t.register input=newyear maps=newyear_1 \
        start=2027-01-01 end=2027-01-02
    t.rast.mapcalc inputs=newyear output=iso basename=iso \
        expression="start_week()"
    t.rast.list input=iso columns=name,min,max
    ```

    ```text
    name|min|max
    iso_1|53.0|53.0
    ```

    ```sh
    for step in 1 2 3; do
        r.mapcalc expression="model_$step = $step"
    done
    t.create temporaltype=relative output=model title="Model" \
        description="Model output every 5 hours"
    t.register -i input=model maps=model_1,model_2,model_3 \
        start=0 increment=5 unit=hours
    t.rast.mapcalc inputs=model output=elapsed basename=elapsed \
        expression="start_time() * 100 + td() * 10 + end_time()"
    t.rast.list input=elapsed columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    elapsed_1|0|5|55.0|55.0
    elapsed_2|5|10|560.0|560.0
    elapsed_3|10|15|1065.0|1065.0
    ```

    ```sh
    if ! t.rast.mapcalc inputs=model output=bad basename=bad \
        expression="start_doy()" 2>&1; then
        echo "t.rast.mapcalc failed"
    fi
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    ERROR: The temporal operators <start_*> support only absolute time.
    t.rast.mapcalc failed
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    for step in range(1, 5):
        tools.r_mapcalc(expression=f"soil_{step} = {2 + 10 * (step - 1)}")
    tools.t_create(
        output="soil",
        title="Soil",
        description="Soil temperature in degree Celsius, one map per day",
    )
    tools.t_register(
        input="soil",
        maps="soil_1,soil_2,soil_3,soil_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_mapcalc(
        inputs="soil",
        output="when",
        basename="when",
        expression="start_time() * 100 + td() * 10 + end_time()",
    )
    print(tools.t_rast_list(input="when", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    when_1|11.0|11.0
    when_2|112.0|112.0
    when_3|213.0|213.0
    when_4|314.0|314.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="soil",
        output="calendar",
        basename="calendar",
        expression="start_doy() * 10 + start_dow()",
    )
    print(tools.t_rast_list(input="calendar", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    calendar_1|607.0|607.0
    calendar_2|611.0|611.0
    calendar_3|622.0|622.0
    calendar_4|633.0|633.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="soil",
        output="month_day",
        basename="month_day",
        expression="start_month() * 100 + end_day()",
    )
    print(tools.t_rast_list(input="month_day", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    month_day_1|302.0|302.0
    month_day_2|303.0|303.0
    month_day_3|304.0|304.0
    month_day_4|305.0|305.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="soil",
        output="weeks",
        basename="weeks",
        expression="start_week() * 100 + end_week()",
    )
    print(tools.t_rast_list(input="weeks", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    weeks_1|910.0|910.0
    weeks_2|1010.0|1010.0
    weeks_3|1010.0|1010.0
    weeks_4|1010.0|1010.0
    ```

    ```python
    tools.r_mapcalc(expression="gauge_1 = 1")
    tools.r_mapcalc(expression="gauge_2 = 2")
    tools.t_create(output="gauge", title="Gauge", description="Two instants")
    tools.t_register(input="gauge", maps="gauge_1", start="2026-03-01 06:00:00")
    tools.t_register(input="gauge", maps="gauge_2", start="2026-03-02 18:00:00")
    tools.t_rast_mapcalc(
        inputs="gauge",
        output="instants",
        basename="instants",
        expression="start_time() + if(isnull(end_time()), 100, 0)",
    )
    print(
        tools.t_rast_list(input="instants", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    instants_1|2026-03-01 06:00:00|None|100.0|100.0
    instants_2|2026-03-02 18:00:00|None|101.5|101.5
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="gauge",
        output="lengths",
        basename="lengths",
        expression="if(isnull(td()), 7, 0)",
    )
    print(tools.t_rast_list(input="lengths", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    lengths_1|7.0|7.0
    lengths_2|7.0|7.0
    ```

    ```python
    tools.r_mapcalc(expression="newyear_1 = 1")
    tools.t_create(output="newyear", title="New year", description="One day")
    tools.t_register(
        input="newyear",
        maps="newyear_1",
        start="2027-01-01",
        end="2027-01-02",
    )
    tools.t_rast_mapcalc(
        inputs="newyear", output="iso", basename="iso", expression="start_week()"
    )
    print(tools.t_rast_list(input="iso", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    iso_1|53.0|53.0
    ```

    ```python
    for step in range(1, 4):
        tools.r_mapcalc(expression=f"model_{step} = {step}")
    tools.t_create(
        temporaltype="relative",
        output="model",
        title="Model",
        description="Model output every 5 hours",
    )
    tools.t_register(
        input="model",
        maps="model_1,model_2,model_3",
        start=0,
        increment=5,
        unit="hours",
        flags="i",
    )
    tools.t_rast_mapcalc(
        inputs="model",
        output="elapsed",
        basename="elapsed",
        expression="start_time() * 100 + td() * 10 + end_time()",
    )
    print(
        tools.t_rast_list(input="elapsed", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    elapsed_1|0|5|55.0|55.0
    elapsed_2|5|10|560.0|560.0
    elapsed_3|10|15|1065.0|1065.0
    ```

    ```python
    try:
        tools.t_rast_mapcalc(
            inputs="model", output="bad", basename="bad", expression="start_doy()"
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.mapcalc failed")
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    ERROR: The temporal operators <start_*> support only absolute time.
    t.rast.mapcalc failed
    ```

### Keep or drop empty results

An expression that sets cells to null selects time steps by their values.
The first block keeps the cells of `temperature_monthly` warmer than 20 degrees
Celsius. Only the maps from May to September have such cells; the warmest cell
of May has 22.2 degrees. The maps of the other months have no valid cell left.
They are not registered in `warm`, and the second block shows that they are
removed from the mapset. The new maps `warm_05` to `warm_09` keep the numbers
of their granules.

The third block runs the call again with **-n**. The dataset `warm_all`
registers the empty maps as well, with `None` as their smallest and largest
value, and the mapset keeps all twelve maps.

The fourth block mixes a condition on the time with one on the values: in July,
cells of `temperature_monthly` warmer than 25 degrees become null, and the
other months keep their values. The largest value of July drops from 28.4 to
25.0 degrees; the other maps are those of `temperature_monthly`.

=== "Command line"

    ```sh
    t.rast.mapcalc inputs=temperature_monthly output=warm basename=warm \
        expression="if(temperature_monthly > 20, temperature_monthly, null())"
    t.rast.list input=warm columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    warm_05|2020-05-01 00:00:00|20.1|22.2
    warm_06|2020-06-01 00:00:00|20.1|26.5
    warm_07|2020-07-01 00:00:00|20.1|28.4
    warm_08|2020-08-01 00:00:00|20.1|27.6
    warm_09|2020-09-01 00:00:00|20.1|24.2
    ```

    ```sh
    g.list type=raster pattern="warm*" mapset=.
    ```

    ```text
    warm_05
    warm_06
    warm_07
    warm_08
    warm_09
    ```

    ```sh
    t.rast.mapcalc -n inputs=temperature_monthly output=warm_all basename=warm_all \
        expression="if(temperature_monthly > 20, temperature_monthly, null())"
    t.rast.list input=warm_all columns=name,start_time,min,max
    g.list type=raster pattern="warm_all*" mapset=.
    ```

    ```text
    name|start_time|min|max
    warm_all_01|2020-01-01 00:00:00|None|None
    warm_all_02|2020-02-01 00:00:00|None|None
    warm_all_03|2020-03-01 00:00:00|None|None
    warm_all_04|2020-04-01 00:00:00|None|None
    warm_all_05|2020-05-01 00:00:00|20.1|22.2
    warm_all_06|2020-06-01 00:00:00|20.1|26.5
    warm_all_07|2020-07-01 00:00:00|20.1|28.4
    warm_all_08|2020-08-01 00:00:00|20.1|27.6
    warm_all_09|2020-09-01 00:00:00|20.1|24.2
    warm_all_10|2020-10-01 00:00:00|None|None
    warm_all_11|2020-11-01 00:00:00|None|None
    warm_all_12|2020-12-01 00:00:00|None|None
    warm_all_01
    warm_all_02
    warm_all_03
    warm_all_04
    warm_all_05
    warm_all_06
    warm_all_07
    warm_all_08
    warm_all_09
    warm_all_10
    warm_all_11
    warm_all_12
    ```

    ```sh
    t.rast.mapcalc inputs=temperature_monthly output=thinned basename=thinned \
        expression="if(start_month() == 7 && temperature_monthly > 25, null(), temperature_monthly)"
    t.rast.list input=thinned columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    thinned_01|2020-01-01 00:00:00|-7.0|7.5
    thinned_02|2020-02-01 00:00:00|-6.1|8.4
    thinned_03|2020-03-01 00:00:00|-2.7|11.8
    thinned_04|2020-04-01 00:00:00|2.4|16.9
    thinned_05|2020-05-01 00:00:00|7.7|22.2
    thinned_06|2020-06-01 00:00:00|12.0|26.5
    thinned_07|2020-07-01 00:00:00|13.9|25.0
    thinned_08|2020-08-01 00:00:00|13.1|27.6
    thinned_09|2020-09-01 00:00:00|9.6|24.2
    thinned_10|2020-10-01 00:00:00|4.6|19.1
    thinned_11|2020-11-01 00:00:00|-0.8|13.7
    thinned_12|2020-12-01 00:00:00|-5.0|9.5
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_mapcalc(
        inputs="temperature_monthly",
        output="warm",
        basename="warm",
        expression="if(temperature_monthly > 20, temperature_monthly, null())",
    )
    print(tools.t_rast_list(input="warm", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    warm_05|2020-05-01 00:00:00|20.1|22.2
    warm_06|2020-06-01 00:00:00|20.1|26.5
    warm_07|2020-07-01 00:00:00|20.1|28.4
    warm_08|2020-08-01 00:00:00|20.1|27.6
    warm_09|2020-09-01 00:00:00|20.1|24.2
    ```

    ```python
    print(tools.g_list(type="raster", pattern="warm*", mapset=".").text)
    ```

    ```text
    warm_05
    warm_06
    warm_07
    warm_08
    warm_09
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="temperature_monthly",
        output="warm_all",
        basename="warm_all",
        expression="if(temperature_monthly > 20, temperature_monthly, null())",
        flags="n",
    )
    print(tools.t_rast_list(input="warm_all", columns="name,start_time,min,max").text)
    print(tools.g_list(type="raster", pattern="warm_all*", mapset=".").text)
    ```

    ```text
    name|start_time|min|max
    warm_all_01|2020-01-01 00:00:00|None|None
    warm_all_02|2020-02-01 00:00:00|None|None
    warm_all_03|2020-03-01 00:00:00|None|None
    warm_all_04|2020-04-01 00:00:00|None|None
    warm_all_05|2020-05-01 00:00:00|20.1|22.2
    warm_all_06|2020-06-01 00:00:00|20.1|26.5
    warm_all_07|2020-07-01 00:00:00|20.1|28.4
    warm_all_08|2020-08-01 00:00:00|20.1|27.6
    warm_all_09|2020-09-01 00:00:00|20.1|24.2
    warm_all_10|2020-10-01 00:00:00|None|None
    warm_all_11|2020-11-01 00:00:00|None|None
    warm_all_12|2020-12-01 00:00:00|None|None
    warm_all_01
    warm_all_02
    warm_all_03
    warm_all_04
    warm_all_05
    warm_all_06
    warm_all_07
    warm_all_08
    warm_all_09
    warm_all_10
    warm_all_11
    warm_all_12
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="temperature_monthly",
        output="thinned",
        basename="thinned",
        expression=(
            "if(start_month() == 7 && temperature_monthly > 25,"
            " null(), temperature_monthly)"
        ),
    )
    print(tools.t_rast_list(input="thinned", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    thinned_01|2020-01-01 00:00:00|-7.0|7.5
    thinned_02|2020-02-01 00:00:00|-6.1|8.4
    thinned_03|2020-03-01 00:00:00|-2.7|11.8
    thinned_04|2020-04-01 00:00:00|2.4|16.9
    thinned_05|2020-05-01 00:00:00|7.7|22.2
    thinned_06|2020-06-01 00:00:00|12.0|26.5
    thinned_07|2020-07-01 00:00:00|13.9|25.0
    thinned_08|2020-08-01 00:00:00|13.1|27.6
    thinned_09|2020-09-01 00:00:00|9.6|24.2
    thinned_10|2020-10-01 00:00:00|4.6|19.1
    thinned_11|2020-11-01 00:00:00|-0.8|13.7
    thinned_12|2020-12-01 00:00:00|-5.0|9.5
    ```

### Take only the maps in the same place

The dataset `patch` has four maps for the days of `soil`, with the values
1000, 2000, 3000 and 4000. The first block makes them. The second map
`patch_2` lies next to the region of the first example, from 963 km to 1000 km
in the east, so it shares an edge with it. The third map `patch_3` was made far
away, from 1090 km to 1100 km. The other maps cover the region, like `soil`.
The current region is the one of the first example again.

The first call adds `soil` and `patch`, with 100 where `patch` is null. The
maps `patch_2` and `patch_3` are related in time but read in the current region
where they have no data, so the result for the second and third day is the
value of `soil` plus 100: 112 and 122. The result of the other days is `soil`
plus `patch`: 1002 and 4032.

With **-s**, the second call takes only maps whose extent touches or overlaps
that of the granule. `patch_2` touches it and stays, `patch_3` does not, so the
third granule is skipped, and the result has three maps with the numbers 1, 2
and 4.

=== "Command line"

    ```sh
    for step in 1 2 3 4; do
        if [ $step = 2 ]; then
            g.region n=319000 s=-16000 e=1000000 w=963000 res=1000
        elif [ $step = 3 ]; then
            g.region n=319000 s=-16000 e=1100000 w=1090000 res=1000
        fi
        r.mapcalc expression="patch_$step = 1000 * $step"
        g.region raster=elev_state_500m res=1000 -a
    done
    t.create output=patch title="Patch" description="Four patches"
    t.register -i input=patch \
        maps=patch_1,patch_2,patch_3,patch_4 start=2026-03-01 increment="1 day"
    t.rast.mapcalc inputs=soil,patch output=near basename=near \
        expression="soil + if(isnull(patch), 100, patch)"
    t.rast.list input=near columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    near_1|2026-03-01 00:00:00|1002.0|1002.0
    near_2|2026-03-02 00:00:00|112.0|112.0
    near_3|2026-03-03 00:00:00|122.0|122.0
    near_4|2026-03-04 00:00:00|4032.0|4032.0
    ```

    ```sh
    t.rast.mapcalc -s inputs=soil,patch output=near_only basename=near_only \
        expression="soil + if(isnull(patch), 100, patch)"
    t.rast.list input=near_only columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    near_only_1|2026-03-01 00:00:00|1002.0|1002.0
    near_only_2|2026-03-02 00:00:00|112.0|112.0
    near_only_4|2026-03-04 00:00:00|4032.0|4032.0
    ```

=== "Python (grass.tools)"

    ```python
    for step in range(1, 5):
        if step == 2:
            tools.g_region(n=319000, s=-16000, e=1000000, w=963000, res=1000)
        elif step == 3:
            tools.g_region(n=319000, s=-16000, e=1100000, w=1090000, res=1000)
        tools.r_mapcalc(expression=f"patch_{step} = 1000 * {step}")
        tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.t_create(output="patch", title="Patch", description="Four patches")
    tools.t_register(
        input="patch",
        maps="patch_1,patch_2,patch_3,patch_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_mapcalc(
        inputs="soil,patch",
        output="near",
        basename="near",
        expression="soil + if(isnull(patch), 100, patch)",
    )
    print(tools.t_rast_list(input="near", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    near_1|2026-03-01 00:00:00|1002.0|1002.0
    near_2|2026-03-02 00:00:00|112.0|112.0
    near_3|2026-03-03 00:00:00|122.0|122.0
    near_4|2026-03-04 00:00:00|4032.0|4032.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="soil,patch",
        output="near_only",
        basename="near_only",
        expression="soil + if(isnull(patch), 100, patch)",
        flags="s",
    )
    print(tools.t_rast_list(input="near_only", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    near_only_1|2026-03-01 00:00:00|1002.0|1002.0
    near_only_2|2026-03-02 00:00:00|112.0|112.0
    near_only_4|2026-03-04 00:00:00|4032.0|4032.0
    ```

### Select maps by semantic label and by time

The dataset `bands` has two bands for each of two periods: the maps `nir_1`
and `nir_2` have the semantic label `S2_8` and the values 60 and 70, the maps
`red_1` and `red_2` have the label `S2_4` and the values 20 and 10. The first
period is from 1 to 11 June 2026, the second from 11 to 21 June. The maps get
their labels from *[r.support](r.support.md)* before *[t.register](t.register.md)*
stores them.

A name with a dot in **inputs** selects the maps of one dataset by label:
`bands.S2_8` is the dataset `bands` reduced to its maps with the label `S2_8`.
The expression uses the same name, so the first dataset of the list has the two
`S2_8` maps as granules and the maps of `bands.S2_4` are their partners. The
first block computes the normalized difference of the two bands, the
normalized difference vegetation index. The values are (60 - 20) / (60 + 20) =
0.5 and (70 - 10) / (70 + 10) = 0.75. The new maps take the semantic label of
the map of the sampler, `S2_8`, and, as always, its time.

The option **where** is an SQL condition on the registered maps of all
datasets in **inputs**. The second block repeats the call for the maps that
start on or after 11 June. Only the second period is left, and the one new map
has the number 1.

=== "Command line"

    ```sh
    r.mapcalc expression="nir_1 = 60"
    r.mapcalc expression="red_1 = 20"
    r.mapcalc expression="nir_2 = 70"
    r.mapcalc expression="red_2 = 10"
    r.support map=nir_1 semantic_label=S2_8
    r.support map=red_1 semantic_label=S2_4
    r.support map=nir_2 semantic_label=S2_8
    r.support map=red_2 semantic_label=S2_4
    t.create output=bands title="Bands" description="Near infrared and red"
    t.register input=bands maps=nir_1,red_1 start=2026-06-01 end=2026-06-11
    t.register input=bands maps=nir_2,red_2 start=2026-06-11 end=2026-06-21
    t.rast.list input=bands columns=name,start_time,semantic_label
    ```

    ```text
    name|start_time|semantic_label
    nir_1|2026-06-01 00:00:00|S2_8
    red_1|2026-06-01 00:00:00|S2_4
    nir_2|2026-06-11 00:00:00|S2_8
    red_2|2026-06-11 00:00:00|S2_4
    ```

    ```sh
    t.rast.mapcalc inputs=bands.S2_8,bands.S2_4 output=ndvi basename=ndvi \
        expression="float(bands.S2_8 - bands.S2_4) / (bands.S2_8 + bands.S2_4)"
    t.rast.list input=ndvi columns=name,start_time,semantic_label,min,max
    ```

    ```text
    name|start_time|semantic_label|min|max
    ndvi_1|2026-06-01 00:00:00|S2_8|0.5|0.5
    ndvi_2|2026-06-11 00:00:00|S2_8|0.75|0.75
    ```

    ```sh
    t.rast.mapcalc inputs=bands.S2_8,bands.S2_4 output=ndvi_late basename=late \
        expression="float(bands.S2_8 - bands.S2_4) / (bands.S2_8 + bands.S2_4)" \
        where="start_time >= '2026-06-11'"
    t.rast.list input=ndvi_late columns=name,start_time,semantic_label,min,max
    ```

    ```text
    name|start_time|semantic_label|min|max
    late_1|2026-06-11 00:00:00|S2_8|0.75|0.75
    ```

=== "Python (grass.tools)"

    ```python
    for name, value, label in (
        ("nir_1", 60, "S2_8"),
        ("red_1", 20, "S2_4"),
        ("nir_2", 70, "S2_8"),
        ("red_2", 10, "S2_4"),
    ):
        tools.r_mapcalc(expression=f"{name} = {value}")
        tools.r_support(map=name, semantic_label=label)
    tools.t_create(output="bands", title="Bands", description="Near infrared and red")
    tools.t_register(
        input="bands", maps="nir_1,red_1", start="2026-06-01", end="2026-06-11"
    )
    tools.t_register(
        input="bands", maps="nir_2,red_2", start="2026-06-11", end="2026-06-21"
    )
    print(tools.t_rast_list(input="bands", columns="name,start_time,semantic_label").text)
    ```

    ```text
    name|start_time|semantic_label
    nir_1|2026-06-01 00:00:00|S2_8
    red_1|2026-06-01 00:00:00|S2_4
    nir_2|2026-06-11 00:00:00|S2_8
    red_2|2026-06-11 00:00:00|S2_4
    ```

    ```python
    ndvi = "float(bands.S2_8 - bands.S2_4) / (bands.S2_8 + bands.S2_4)"
    tools.t_rast_mapcalc(
        inputs="bands.S2_8,bands.S2_4",
        output="ndvi",
        basename="ndvi",
        expression=ndvi,
    )
    print(
        tools.t_rast_list(
            input="ndvi", columns="name,start_time,semantic_label,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|semantic_label|min|max
    ndvi_1|2026-06-01 00:00:00|S2_8|0.5|0.5
    ndvi_2|2026-06-11 00:00:00|S2_8|0.75|0.75
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="bands.S2_8,bands.S2_4",
        output="ndvi_late",
        basename="late",
        expression=ndvi,
        where="start_time >= '2026-06-11'",
    )
    print(
        tools.t_rast_list(
            input="ndvi_late", columns="name,start_time,semantic_label,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|semantic_label|min|max
    late_1|2026-06-11 00:00:00|S2_8|0.75|0.75
    ```

### Names of datasets in the expression

A dataset name in the expression is replaced only where it stands as a whole
name. The dataset `day` has one map with the value 4 on March 1. In
`day * start_day()` the name `day` inside `start_day()` stays, so the result is
4 times the day of the month, 1. The dataset `soil_deep` has one map with the
value 3 on March 1. In `soil + soil_deep` the name `soil` inside `soil_deep`
stays, so the first granule of `soil`, whose map holds 2, gets 5; the other
three granules of `soil` have no map of `soil_deep` and are skipped.

Two inputs with the same name cannot be told apart in the expression. The
third block names `day` twice, and the tool stops before it computes anything.

=== "Command line"

    ```sh
    r.mapcalc expression="day_1 = 4"
    t.create output=day title="Day" description="One map"
    t.register input=day maps=day_1 \
        start=2026-03-01 end=2026-03-02
    t.rast.mapcalc inputs=day output=day_of_month basename=day_of_month \
        expression="day * start_day()"
    t.rast.list input=day_of_month columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    day_of_month_1|2026-03-01 00:00:00|4.0|4.0
    ```

    ```sh
    r.mapcalc expression="soil_deep_1 = 3"
    t.create output=soil_deep title="Deep soil" \
        description="One map"
    t.register input=soil_deep maps=soil_deep_1 \
        start=2026-03-01 end=2026-03-02
    t.rast.mapcalc inputs=soil,soil_deep output=layers basename=layers \
        expression="soil + soil_deep"
    t.rast.list input=layers columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    layers_1|2026-03-01 00:00:00|5.0|5.0
    ```

    ```sh
    if ! t.rast.mapcalc inputs=day,day output=twice basename=twice \
        expression="day + 1" 2>&1; then
        echo "t.rast.mapcalc failed"
    fi
    ```

    ```text
    ERROR: The name <day> stands more than once in inputs, so the expression
    cannot tell the inputs apart
    t.rast.mapcalc failed
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="day_1 = 4")
    tools.t_create(output="day", title="Day", description="One map")
    tools.t_register(input="day", maps="day_1", start="2026-03-01", end="2026-03-02")
    tools.t_rast_mapcalc(
        inputs="day",
        output="day_of_month",
        basename="day_of_month",
        expression="day * start_day()",
    )
    print(tools.t_rast_list(input="day_of_month", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    day_of_month_1|2026-03-01 00:00:00|4.0|4.0
    ```

    ```python
    tools.r_mapcalc(expression="soil_deep_1 = 3")
    tools.t_create(output="soil_deep", title="Deep soil", description="One map")
    tools.t_register(
        input="soil_deep",
        maps="soil_deep_1",
        start="2026-03-01",
        end="2026-03-02",
    )
    tools.t_rast_mapcalc(
        inputs="soil,soil_deep",
        output="layers",
        basename="layers",
        expression="soil + soil_deep",
    )
    print(tools.t_rast_list(input="layers", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    layers_1|2026-03-01 00:00:00|5.0|5.0
    ```

    ```python
    try:
        tools.t_rast_mapcalc(
            inputs="day,day", output="twice", basename="twice", expression="day + 1"
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.mapcalc failed")
    ```

    ```text
    ERROR: The name <day> stands more than once in inputs, so the expression
    cannot tell the inputs apart
    t.rast.mapcalc failed
    ```

### Use a dataset of another mapset and replace a result

The mapset `t_rast_mapcalc_2` is new and empty. A new mapset starts with the
default region of the dataset, cells of 500 m, so the first block sets the
region of the first example again. It converts
`precipitation_monthly@t_rast_mapcalc` from millimeters to centimeters. The
expression still uses the name `precipitation_monthly`, and the mapset of the
input does not have to be in the search path. See [Datasets of other
mapsets](temporalintro.md#datasets-of-other-mapsets). The dataset
`precipitation_cm` and its maps belong to the current mapset; the listing shows
the mapset of the maps.

The second block repeats the call without **--overwrite**. The tool stops
because the dataset `precipitation_cm` exists. The third block adds
**--overwrite** and makes the dataset again, with the same twelve maps; the tool
warns on the standard error that it unregisters all maps of the old dataset.

The fourth block replaces `precipitation_cm` once more, now with a **where**
condition that leaves the ten months from January to October. The new dataset
holds ten maps. The maps `precipitation_cm_11` and `precipitation_cm_12` of the
earlier run are no longer registered in it, but the tool does not remove them:
`g.list` still finds them.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_mapcalc_2
    g.region raster=elev_state_500m res=1000 -a
    t.rast.mapcalc inputs=precipitation_monthly@t_rast_mapcalc \
        output=precipitation_cm basename=precipitation_cm \
        expression="precipitation_monthly / 10.0"
    t.rast.list input=precipitation_cm columns=name,mapset,min,max
    ```

    ```text
    name|mapset|min|max
    precipitation_cm_01|t_rast_mapcalc_2|9.4|24.9
    precipitation_cm_02|t_rast_mapcalc_2|13.3|30.9
    precipitation_cm_03|t_rast_mapcalc_2|8.8|21.2
    precipitation_cm_04|t_rast_mapcalc_2|9.2|23.1
    precipitation_cm_05|t_rast_mapcalc_2|13.3|34.7
    precipitation_cm_06|t_rast_mapcalc_2|7.1|16.3
    precipitation_cm_07|t_rast_mapcalc_2|8.3|22.3
    precipitation_cm_08|t_rast_mapcalc_2|11.9|29.5
    precipitation_cm_09|t_rast_mapcalc_2|6.0|18.1
    precipitation_cm_10|t_rast_mapcalc_2|5.5|16.0
    precipitation_cm_11|t_rast_mapcalc_2|10.4|35.0
    precipitation_cm_12|t_rast_mapcalc_2|5.9|17.7
    ```

    ```sh
    if ! t.rast.mapcalc inputs=precipitation_monthly@t_rast_mapcalc \
        output=precipitation_cm basename=precipitation_cm \
        expression="precipitation_monthly / 10.0" 2>&1; then
        echo "t.rast.mapcalc failed"
    fi
    ```

    ```text
    ERROR: Space time raster dataset <precipitation_cm> is already in the
    database. Use the overwrite flag.
    t.rast.mapcalc failed
    ```

    ```sh
    t.rast.mapcalc --overwrite inputs=precipitation_monthly@t_rast_mapcalc \
        output=precipitation_cm basename=precipitation_cm \
        expression="precipitation_monthly / 10.0"
    t.rast.list input=precipitation_cm columns=name,mapset,min,max
    ```

    ```text
    name|mapset|min|max
    precipitation_cm_01|t_rast_mapcalc_2|9.4|24.9
    precipitation_cm_02|t_rast_mapcalc_2|13.3|30.9
    precipitation_cm_03|t_rast_mapcalc_2|8.8|21.2
    precipitation_cm_04|t_rast_mapcalc_2|9.2|23.1
    precipitation_cm_05|t_rast_mapcalc_2|13.3|34.7
    precipitation_cm_06|t_rast_mapcalc_2|7.1|16.3
    precipitation_cm_07|t_rast_mapcalc_2|8.3|22.3
    precipitation_cm_08|t_rast_mapcalc_2|11.9|29.5
    precipitation_cm_09|t_rast_mapcalc_2|6.0|18.1
    precipitation_cm_10|t_rast_mapcalc_2|5.5|16.0
    precipitation_cm_11|t_rast_mapcalc_2|10.4|35.0
    precipitation_cm_12|t_rast_mapcalc_2|5.9|17.7
    ```

    ```sh
    t.rast.mapcalc --overwrite inputs=precipitation_monthly@t_rast_mapcalc \
        output=precipitation_cm basename=precipitation_cm \
        expression="precipitation_monthly / 10.0" \
        where="start_time < '2020-11-01'"
    t.info -g input=precipitation_cm | grep "^number_of_maps="
    g.list type=raster pattern="precipitation_cm_1*" mapset=.
    ```

    ```text
    number_of_maps=10
    precipitation_cm_10
    precipitation_cm_11
    precipitation_cm_12
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_rast_mapcalc_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.t_rast_mapcalc(
        inputs="precipitation_monthly@t_rast_mapcalc",
        output="precipitation_cm",
        basename="precipitation_cm",
        expression="precipitation_monthly / 10.0",
    )
    print(tools.t_rast_list(input="precipitation_cm", columns="name,mapset,min,max").text)
    ```

    ```text
    name|mapset|min|max
    precipitation_cm_01|t_rast_mapcalc_2|9.4|24.9
    precipitation_cm_02|t_rast_mapcalc_2|13.3|30.9
    precipitation_cm_03|t_rast_mapcalc_2|8.8|21.2
    precipitation_cm_04|t_rast_mapcalc_2|9.2|23.1
    precipitation_cm_05|t_rast_mapcalc_2|13.3|34.7
    precipitation_cm_06|t_rast_mapcalc_2|7.1|16.3
    precipitation_cm_07|t_rast_mapcalc_2|8.3|22.3
    precipitation_cm_08|t_rast_mapcalc_2|11.9|29.5
    precipitation_cm_09|t_rast_mapcalc_2|6.0|18.1
    precipitation_cm_10|t_rast_mapcalc_2|5.5|16.0
    precipitation_cm_11|t_rast_mapcalc_2|10.4|35.0
    precipitation_cm_12|t_rast_mapcalc_2|5.9|17.7
    ```

    ```python
    try:
        tools.t_rast_mapcalc(
            inputs="precipitation_monthly@t_rast_mapcalc",
            output="precipitation_cm",
            basename="precipitation_cm",
            expression="precipitation_monthly / 10.0",
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.mapcalc failed")
    ```

    ```text
    ERROR: Space time raster dataset <precipitation_cm> is already in the
    database. Use the overwrite flag.
    t.rast.mapcalc failed
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="precipitation_monthly@t_rast_mapcalc",
        output="precipitation_cm",
        basename="precipitation_cm",
        expression="precipitation_monthly / 10.0",
        overwrite=True,
    )
    print(tools.t_rast_list(input="precipitation_cm", columns="name,mapset,min,max").text)
    ```

    ```text
    name|mapset|min|max
    precipitation_cm_01|t_rast_mapcalc_2|9.4|24.9
    precipitation_cm_02|t_rast_mapcalc_2|13.3|30.9
    precipitation_cm_03|t_rast_mapcalc_2|8.8|21.2
    precipitation_cm_04|t_rast_mapcalc_2|9.2|23.1
    precipitation_cm_05|t_rast_mapcalc_2|13.3|34.7
    precipitation_cm_06|t_rast_mapcalc_2|7.1|16.3
    precipitation_cm_07|t_rast_mapcalc_2|8.3|22.3
    precipitation_cm_08|t_rast_mapcalc_2|11.9|29.5
    precipitation_cm_09|t_rast_mapcalc_2|6.0|18.1
    precipitation_cm_10|t_rast_mapcalc_2|5.5|16.0
    precipitation_cm_11|t_rast_mapcalc_2|10.4|35.0
    precipitation_cm_12|t_rast_mapcalc_2|5.9|17.7
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="precipitation_monthly@t_rast_mapcalc",
        output="precipitation_cm",
        basename="precipitation_cm",
        expression="precipitation_monthly / 10.0",
        where="start_time < '2020-11-01'",
        overwrite=True,
    )
    info = tools.t_info(input="precipitation_cm", flags="g").keyval
    print(f"number_of_maps={info['number_of_maps']}")
    print(tools.g_list(type="raster", pattern="precipitation_cm_1*", mapset=".").text)
    ```

    ```text
    number_of_maps=10
    precipitation_cm_10
    precipitation_cm_11
    precipitation_cm_12
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapset](g.mapset.md),
[i.band.library](i.band.library.md), [r.mapcalc](r.mapcalc.md),
[r.support](r.support.md), [t.info](t.info.md),
[t.rast.aggregate.ds](t.rast.aggregate.ds.md),
[t.rast.algebra](t.rast.algebra.md), [t.rast.list](t.rast.list.md),
[t.rast3d.mapcalc](t.rast3d.mapcalc.md), [t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
