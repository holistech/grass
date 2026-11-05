## DESCRIPTION

*t.rast3d.mapcalc* computes new 3D raster maps from the maps of one or more
space time 3D raster datasets and registers them in a new space time 3D raster
dataset. It runs *[r3.mapcalc](r3.mapcalc.md)* once for each time step and
adds the temporal variables `td()`, `start_time()`, `end_time()` and, for
absolute time, the calendar functions `start_doy()`, `end_month()` and others
to the expression. Use it when the result of a time step depends on maps of
several datasets, on the time of the step, or on both. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. *[t.rast.mapcalc](t.rast.mapcalc.md)* does the same for space time
raster datasets, *[t.rast3d.algebra](t.rast3d.algebra.md)* computes with the
temporal algebra, and *[t.rast3d.list](t.rast3d.list.md)* lists the maps of the
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
be in other mapsets (`moisture@t_rast3d_mapcalc`); the expression then uses
the name without the mapset or, as in **inputs**, with it, and the mapset does
not have to be in the search path (see [Datasets of other
mapsets](temporalintro.md#datasets-of-other-mapsets)).

The result dataset is the option **output**. It always belongs to the current
mapset, and so do the new maps. It takes the temporal type and the semantic type
of the first dataset of **inputs**. Each new map has the start and end time of
its granule. An existing dataset **output** is refused unless the flag
**--overwrite** is given; then it is replaced, and the tool warns that it
unregisters all maps of the old dataset.

The tool computes in the current 3D region, as *r3.mapcalc* does. A map that
lies outside the region reads as null.

### The expression

The option **expression** is the right side of an *r3.mapcalc* expression,
without the `map =` of a full one. In it, the name of each dataset of **inputs**
stands for the related map of the current granule, so `moisture * bias`
multiplies the map of `moisture` by the related map of `bias`, and
`bias * moisture` does the same. Any other 3D raster map can be used by its
name. The operators and functions of *r3.mapcalc* are available.

The tool puts the names of the maps into the text of the expression and
numbers the results, so with the expression `moisture / 2` a call with four
granules runs four statements such as `halved_1=moisture_1 / 2`. A dataset
name is replaced only where it stands as a whole name: not inside a longer name
(`moisture` in `moisture_deep`), and not before an opening parenthesis, where
it is the name of a function (`day` in `start_day()`); see the ninth example.
After a map name, as in `volume@moisture`, the name is a mapset and stays.
The rest of the expression goes to *r3.mapcalc* as written, blanks included.
Two inputs with the same name, such as `moisture,moisture`, are refused before
any map is computed, because the expression could not tell them apart.

The option **basename** is required. The new maps are named after it, followed
by an underscore and the number of their granule, counted from 1 in the order
of the sampler. The number has as many digits as the number of granules
needs, filled up with zeros: `halved_1` for four granules, `halved_01` for
eleven. A granule that is skipped, or whose result is empty, leaves a gap in
the numbers.

### Temporal variables

The following variables are replaced by a number for each granule before the
expression goes to *r3.mapcalc*. They work with absolute and with relative
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

With relative time, a calendar function stops the tool with an error.

### Select the related maps

The option **method** is a list of the sampling methods. It names the relation
between the granule and the map of another dataset. The default is
`during,overlap,contain,equal`. A map is related to the granule if it has one of
the listed relations. The third example shows the methods.

- `equal`: the map has the start and the end time of the granule.
- `during`: the granule lies inside the time interval of the map. The map may
  share the start or the end of the granule, but is not equal to it: for a
  granule from 10 to 20 the maps from 5 to 25, from 10 to 25 and from 5 to 20.
- `contain`: the map lies inside the granule.
- `overlap`: the map starts inside the granule and ends after it, or starts
  before it and ends inside it.
- `follows`: the map ends when the granule starts.
- `precedes`: the map starts when the granule ends.
- `start`: the maps that lie inside the granule, the maps that start before it
  and end inside it, the maps that cover it while sharing its start or its
  end, and the equal map. It does not take a map that covers the granule
  strictly and a map that starts inside it and ends after it. The temporal
  topology names the relations of this group `overlapped`, `starts`, `started`,
  `finishes`, `contains` and `equal`.

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
`if(moisture > 15, moisture, null())` selects time steps by values in this
way. If all results are empty, **output** exists but holds no map.

The flag **-s** adds a spatial condition to the temporal one: a map is related
to the granule only if its 2D extent, from west to east and from south to north,
touches or overlaps that of the granule, so a shared edge counts. The vertical
extent is not compared. A granule without a related map is skipped. The eighth
example shows the difference.

### Parallel processing

The option **nprocs** sets the number of *r3.mapcalc* processes that run at
the same time. The default is `1`. The result does not depend on it.

## NOTES

*t.rast3d.mapcalc* has the same options as *t.rast.mapcalc*, except for
**where**, and works on 3D rasters only. The maps of the datasets are not
touched; the tool makes new maps.

If **inputs** names one dataset and it has no maps, the tool warns "No maps
registered in input dataset ...", makes no dataset **output** and ends with
status 0.

If a map of the base name exists as a registered map and **--overwrite** is not
given, the tool stops before it computes any map, with "Map ... is already in
temporal database, use overwrite flag to overwrite". If the dataset **output**
exists, the tool stops with "Space time raster3d dataset ... is already in the
database. Use the overwrite flag.".

With **--overwrite**, the maps of the old dataset are unregistered from it, not
removed. A new run with fewer maps leaves the surplus old maps in the mapset;
the tenth example shows it.

The tool stops with an error if an input dataset does not exist ("Space time
dataset ... of type str3ds not found"), if **method** names a method that does
not exist ("Value ... out of range for parameter method"), and if *r3.mapcalc*
does not accept the expression ("Error while mapcalc computation"). A
calendar function with relative time stops it with
`The temporal operators <start_*> support only absolute time.` (`<end_*>` for
an end function). The tool announces its steps
on the standard error with "Starting temporal sampling..." (with **-s**:
"Starting spatio-temporal sampling...") and "Starting mapcalc
computation...".

If **inputs** names more than one dataset and the sampler has only time
instants, or the datasets have different temporal types, the first dataset
cannot sample the others: the tool stops before it computes any map, with "The
temporal map type of the sample dataset must be interval" or "The space time
datasets must be of the same temporal type". A call with one dataset needs no
sampling, so time instants work there.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast3d_mapcalc` and sets the computational
region to North Carolina with cells of 1 km and three layers of 1000 m. The
3D resolution stays at the 500 m of the elevation model unless `res3` is set,
so the examples set it. The third example narrows the region to a square of
two by two cells, where the maps of the later examples hold small constant
values, so that the results can be checked by hand; the last example creates a
second mapset with the full region again.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast3d_mapcalc -->

<!-- markdownlint-disable MD046 -->

### Apply an expression to every map

The dataset `temperature_profile` holds twelve 3D maps of the monthly mean air
temperature in 2020, in degrees Celsius rounded to tenths. They are generated
like the monthly maps of the other temporal manuals, but from the height of
the layer instead of the elevation model: 16.5 degrees at sea level and the
northing 160 km, an annual cycle of plus and minus 10.5 degrees with its
maximum in July, 6.5 degrees less for every 1000 m of height, and 1 degree
more for every 100 km to the south. The maps have three layers of 1000 m,
from 0 to 3000 m, and each is an interval of one month.

The first block converts the maps to degrees Fahrenheit. The name
`temperature_profile` in the expression stands for the map of each month. The
new maps are named `fahrenheit_01` to `fahrenheit_12` after the granules, and
each has the time of its source map. **nprocs** lets two *r3.mapcalc*
processes run at the same time; the result is the same as with one. The
result is rounded to tenths, as the source maps are. In July the warmest
voxel has 25.4 degrees Celsius, which is 77.7 degrees Fahrenheit, and in
January the coldest has -11.8 degrees Celsius, which is 10.8 degrees
Fahrenheit. The second block shows what the new dataset takes from
`temperature_profile`: the temporal type and the semantic type, and the
granularity that follows from the maps it holds.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast3d_mapcalc
    g.region raster=elev_state_500m res=1000 res3=1000 t=3000 b=0 tbres=1000 -a
    for month in $(seq 12); do
        echo "temperature_profile_2020_$(printf %02d $month) = round((16.5" \
            "+ 10.5 * cos(30 * ($month - 7.2)) - 0.0065 * z()" \
            "- 0.00001 * (y() - 160000)) * 10) / 10.0"
    done | r3.mapcalc file=-
    t.create type=str3ds output=temperature_profile title="Air temperature" \
        description="Monthly mean air temperature 2020 in degree Celsius, 0 to 3000 m"
    t.register -i type=raster_3d input=temperature_profile \
        maps=$(g.list type=raster_3d pattern="temperature_profile_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    t.rast3d.mapcalc inputs=temperature_profile output=fahrenheit basename=fahrenheit \
        expression="round((temperature_profile * 1.8 + 32) * 10) / 10.0" nprocs=2
    t.rast3d.list input=fahrenheit columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    fahrenheit_01|2020-01-01 00:00:00|10.8|40.3
    fahrenheit_02|2020-02-01 00:00:00|12.4|41.7
    fahrenheit_03|2020-03-01 00:00:00|18.5|47.8
    fahrenheit_04|2020-04-01 00:00:00|27.7|57.0
    fahrenheit_05|2020-05-01 00:00:00|37.2|66.7
    fahrenheit_06|2020-06-01 00:00:00|45.0|74.3
    fahrenheit_07|2020-07-01 00:00:00|48.4|77.7
    fahrenheit_08|2020-08-01 00:00:00|46.9|76.3
    fahrenheit_09|2020-09-01 00:00:00|40.6|70.2
    fahrenheit_10|2020-10-01 00:00:00|31.6|61.0
    fahrenheit_11|2020-11-01 00:00:00|21.9|51.3
    fahrenheit_12|2020-12-01 00:00:00|14.4|43.7
    ```

    ```sh
    t.info -g type=str3ds input=fahrenheit | grep -E "^(temporal_type|semantic_type|granularity)="
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
    tools.g_mapset(flags="c", mapset="t_rast3d_mapcalc")
    tools.g_region(
        raster="elev_state_500m", res=1000, res3=1000, t=3000, b=0, tbres=1000, flags="a"
    )
    months = range(1, 13)
    tools.r3_mapcalc(
        expression="\n".join(
            f"temperature_profile_2020_{month:02d} = round((16.5"
            f" + 10.5 * cos(30 * ({month} - 7.2)) - 0.0065 * z()"
            " - 0.00001 * (y() - 160000)) * 10) / 10.0"
            for month in months
        )
    )
    tools.t_create(
        type="str3ds",
        output="temperature_profile",
        title="Air temperature",
        description="Monthly mean air temperature 2020 in degree Celsius, 0 to 3000 m",
    )
    tools.t_register(
        type="raster_3d",
        input="temperature_profile",
        maps=",".join(f"temperature_profile_2020_{month:02d}" for month in months),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    tools.t_rast3d_mapcalc(
        inputs="temperature_profile",
        output="fahrenheit",
        basename="fahrenheit",
        expression="round((temperature_profile * 1.8 + 32) * 10) / 10.0",
        nprocs=2,
    )
    print(tools.t_rast3d_list(input="fahrenheit", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    fahrenheit_01|2020-01-01 00:00:00|10.8|40.3
    fahrenheit_02|2020-02-01 00:00:00|12.4|41.7
    fahrenheit_03|2020-03-01 00:00:00|18.5|47.8
    fahrenheit_04|2020-04-01 00:00:00|27.7|57.0
    fahrenheit_05|2020-05-01 00:00:00|37.2|66.7
    fahrenheit_06|2020-06-01 00:00:00|45.0|74.3
    fahrenheit_07|2020-07-01 00:00:00|48.4|77.7
    fahrenheit_08|2020-08-01 00:00:00|46.9|76.3
    fahrenheit_09|2020-09-01 00:00:00|40.6|70.2
    fahrenheit_10|2020-10-01 00:00:00|31.6|61.0
    fahrenheit_11|2020-11-01 00:00:00|21.9|51.3
    fahrenheit_12|2020-12-01 00:00:00|14.4|43.7
    ```

    ```python
    info = tools.t_info(type="str3ds", input="fahrenheit", flags="g").keyval
    for key in ("temporal_type", "semantic_type", "granularity"):
        print(f"{key}={info[key]}")
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    granularity='1 month'
    ```

### Combine the maps of several datasets

The dataset `bias` has four maps, each for a quarter of 2020: `bias_2020_q1`
with the value 0.5, `bias_2020_q2` with -0.5, `bias_2020_q3` with 1 and
`bias_2020_q4` with -1, a correction in degrees Celsius that is the same in
every voxel. The first block adds the correction to `temperature_profile`; the
expression names `bias` second, which does not matter. The first dataset of
**inputs** is the sampler, so the result has twelve maps of one month each, and
each month of `temperature_profile` lies during a map of `bias`. The sum is
rounded to tenths. The listing shows March, which is in the first quarter, and
April and May, which are in the second: the values of March are 0.5 above those
of the source map (the largest is 8.8 degrees there and 9.3 here), those of
April and May are 0.5 below (the largest of April is 13.9 degrees and 13.4
here).

The second block swaps the order in **inputs**, so the sampler is `bias` and
the result has four maps of three months each. Each granule of `bias` contains
three maps of `temperature_profile`; the tool warns on the standard error and
uses the first of them, the map of the first month of the quarter. The result
is the value of `bias` plus that map, so the maps hold the temperature of
January, April, July and October with the correction of their quarter: the
largest value of July is 25.4 plus 1, which is 26.4 degrees.

=== "Command line"

    ```sh
    cat <<EOF | r3.mapcalc file=-
    bias_2020_q1 = 0.5
    bias_2020_q2 = -0.5
    bias_2020_q3 = 1
    bias_2020_q4 = -1
    EOF
    t.create type=str3ds output=bias title="Bias" \
        description="Correction in degree Celsius for each quarter"
    t.register -i type=raster_3d input=bias \
        maps=bias_2020_q1,bias_2020_q2,bias_2020_q3,bias_2020_q4 \
        start=2020-01-01 increment="3 months"
    t.rast3d.mapcalc inputs=temperature_profile,bias output=corrected \
        basename=corrected \
        expression="round((bias + temperature_profile) * 10) / 10.0"
    t.rast3d.list input=corrected columns=name,start_time,min,max \
        where="start_time >= '2020-03-01' and start_time < '2020-06-01'"
    ```

    ```text
    name|start_time|min|max
    corrected_03|2020-03-01 00:00:00|-7.0|9.3
    corrected_04|2020-04-01 00:00:00|-2.9|13.4
    corrected_05|2020-05-01 00:00:00|2.4|18.8
    ```

    ```sh
    t.rast3d.mapcalc inputs=bias,temperature_profile output=quarter_start \
        basename=quarter_start \
        expression="round((bias + temperature_profile) * 10) / 10.0"
    t.rast3d.list input=quarter_start columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    quarter_start_1|2020-01-01 00:00:00|2020-04-01 00:00:00|-11.3|5.1
    quarter_start_2|2020-04-01 00:00:00|2020-07-01 00:00:00|-2.9|13.4
    quarter_start_3|2020-07-01 00:00:00|2020-10-01 00:00:00|10.1|26.4
    quarter_start_4|2020-10-01 00:00:00|2021-01-01 00:00:00|-1.2|15.1
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(
        expression="\n".join(
            (
                "bias_2020_q1 = 0.5",
                "bias_2020_q2 = -0.5",
                "bias_2020_q3 = 1",
                "bias_2020_q4 = -1",
            )
        )
    )
    tools.t_create(
        type="str3ds",
        output="bias",
        title="Bias",
        description="Correction in degree Celsius for each quarter",
    )
    tools.t_register(
        type="raster_3d",
        input="bias",
        maps="bias_2020_q1,bias_2020_q2,bias_2020_q3,bias_2020_q4",
        start="2020-01-01",
        increment="3 months",
        flags="i",
    )
    tools.t_rast3d_mapcalc(
        inputs="temperature_profile,bias",
        output="corrected",
        basename="corrected",
        expression="round((bias + temperature_profile) * 10) / 10.0",
    )
    print(
        tools.t_rast3d_list(
            input="corrected",
            columns="name,start_time,min,max",
            where="start_time >= '2020-03-01' and start_time < '2020-06-01'",
        ).text
    )
    ```

    ```text
    name|start_time|min|max
    corrected_03|2020-03-01 00:00:00|-7.0|9.3
    corrected_04|2020-04-01 00:00:00|-2.9|13.4
    corrected_05|2020-05-01 00:00:00|2.4|18.8
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="bias,temperature_profile",
        output="quarter_start",
        basename="quarter_start",
        expression="round((bias + temperature_profile) * 10) / 10.0",
    )
    print(
        tools.t_rast3d_list(
            input="quarter_start", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    quarter_start_1|2020-01-01 00:00:00|2020-04-01 00:00:00|-11.3|5.1
    quarter_start_2|2020-04-01 00:00:00|2020-07-01 00:00:00|-2.9|13.4
    quarter_start_3|2020-07-01 00:00:00|2020-10-01 00:00:00|10.1|26.4
    quarter_start_4|2020-10-01 00:00:00|2021-01-01 00:00:00|-1.2|15.1
    ```

### Choose the sampling method

The next examples work on a small region: a square of two by two cells of
1 km with three layers of 1000 m. The maps of these examples hold constant
values, and the time of the maps is the point.

The dataset `dekads` has nine granules of 10 days with relative time, from day
110 to 120, from 210 to 220 and so on up to 910 to 920. Its map `dekad_k` has
the value `k`. The dataset `probes` has one map for each granule, `probe_k` with
the value `10 * k`, and each has a different position relative to the granule:

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
granules 1, 2, 5, 8 and 9. The last block uses no **method**, so the default
`during,overlap,contain,equal` finds the granules 1 to 5, 8 and 9, and the
listing shows that the maps have the times of the granules.

The time of the datasets is relative, in days, and the result takes it over.
The files for *[t.register](t.register.md)* list one map per line with its
start and end time.

=== "Command line"

    ```sh
    g.region n=100000 s=98000 e=202000 w=200000 res=1000 res3=1000 t=3000 b=0 tbres=1000
    for step in 1 2 3 4 5 6 7 8 9; do
        echo "dekad_$step = $step"
        echo "probe_$step = 10 * $step"
    done | r3.mapcalc file=-
    cat > dekads.txt <<EOF
    dekad_1|110|120
    dekad_2|210|220
    dekad_3|310|320
    dekad_4|410|420
    dekad_5|510|520
    dekad_6|610|620
    dekad_7|710|720
    dekad_8|810|820
    dekad_9|910|920
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
    t.create type=str3ds temporaltype=relative output=dekads title="Dekads" \
        description="Granules of 10 days"
    t.create type=str3ds temporaltype=relative output=probes title="Probes" \
        description="One probe for each granule"
    t.register type=raster_3d input=dekads unit=days file=dekads.txt
    t.register type=raster_3d input=probes unit=days file=probes.txt
    for method in equal during contain overlap follows precedes start; do
        t.rast3d.mapcalc inputs=dekads,probes output=by_$method \
            basename=$method expression="dekads + probes" method=$method
        names=$(t.rast3d.list -s input=by_$method columns=name method=comma)
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
    t.rast3d.mapcalc inputs=dekads,probes output=by_default basename=default \
        expression="dekads + probes"
    t.rast3d.list input=by_default columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    default_1|110|120|11.0|11.0
    default_2|210|220|22.0|22.0
    default_3|310|320|33.0|33.0
    default_4|410|420|44.0|44.0
    default_5|510|520|55.0|55.0
    default_8|810|820|88.0|88.0
    default_9|910|920|99.0|99.0
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    tools.g_region(
        n=100000, s=98000, e=202000, w=200000, res=1000, res3=1000, t=3000, b=0, tbres=1000
    )
    tools.r3_mapcalc(
        expression="\n".join(
            f"dekad_{step} = {step}\nprobe_{step} = 10 * {step}" for step in range(1, 10)
        )
    )
    Path("dekads.txt").write_text(
        "dekad_1|110|120\ndekad_2|210|220\ndekad_3|310|320\ndekad_4|410|420\n"
        "dekad_5|510|520\ndekad_6|610|620\ndekad_7|710|720\ndekad_8|810|820\n"
        "dekad_9|910|920\n"
    )
    Path("probes.txt").write_text(
        "probe_1|110|120\nprobe_2|214|218\nprobe_3|305|325\nprobe_4|415|425\n"
        "probe_5|505|515\nprobe_6|600|610\nprobe_7|720|730\nprobe_8|810|825\n"
        "probe_9|905|920\n"
    )
    tools.t_create(
        type="str3ds",
        temporaltype="relative",
        output="dekads",
        title="Dekads",
        description="Granules of 10 days",
    )
    tools.t_create(
        type="str3ds",
        temporaltype="relative",
        output="probes",
        title="Probes",
        description="One probe for each granule",
    )
    tools.t_register(type="raster_3d", input="dekads", unit="days", file="dekads.txt")
    tools.t_register(type="raster_3d", input="probes", unit="days", file="probes.txt")
    for method in ("equal", "during", "contain", "overlap", "follows", "precedes", "start"):
        tools.t_rast3d_mapcalc(
            inputs="dekads,probes",
            output=f"by_{method}",
            basename=method,
            expression="dekads + probes",
            method=method,
        )
        names = tools.t_rast3d_list(
            input=f"by_{method}", columns="name", method="comma", flags="s"
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
    tools.t_rast3d_mapcalc(
        inputs="dekads,probes",
        output="by_default",
        basename="default",
        expression="dekads + probes",
    )
    print(
        tools.t_rast3d_list(
            input="by_default", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    default_1|110|120|11.0|11.0
    default_2|210|220|22.0|22.0
    default_3|310|320|33.0|33.0
    default_4|410|420|44.0|44.0
    default_5|510|520|55.0|55.0
    default_8|810|820|88.0|88.0
    default_9|910|920|99.0|99.0
    ```

### Several related maps for one granule

The dataset `window` has one map of 10 days, from day 10 to 20, with the
value 1. The dataset `cands` has four maps that are all related to it, in
different ways: `cand_a` from 12 to 18 with the value 100 (inside the granule),
`cand_b` from 5 to 25 with the value 200 (covers it), `cand_c` from 11 to 13
with the value 300 (inside, and starts before `cand_a`) and `cand_d` from 10 to
20 with the value 400 (equal).

The expression is only `cands`, so the result holds the value of the map the
tool took. The loop prints it for four lists of methods. With the default
`during,overlap,contain,equal` it is 200: `during` comes before `contain` and
`equal` and finds `cand_b`. With `contain,during` it is 200 as well, because
the order of the list only counts for `equal`, `during`, `follows` and
`precedes`, and `contain` is tried after them. With `equal,during,contain` it
is 400, because `equal` is first. With `contain` alone it is 300: of the maps
inside the granule, `cand_c` starts first. The tool warns on the standard
error when it chooses between maps.

=== "Command line"

    ```sh
    cat <<EOF | r3.mapcalc file=-
    window_1 = 1
    cand_a = 100
    cand_b = 200
    cand_c = 300
    cand_d = 400
    EOF
    cat > window.txt <<EOF
    window_1|10|20
    EOF
    cat > cands.txt <<EOF
    cand_a|12|18
    cand_b|5|25
    cand_c|11|13
    cand_d|10|20
    EOF
    t.create type=str3ds temporaltype=relative output=window title="Window" \
        description="One granule"
    t.create type=str3ds temporaltype=relative output=cands title="Candidates" \
        description="Four maps related to the granule"
    t.register type=raster_3d input=window unit=days file=window.txt
    t.register type=raster_3d input=cands unit=days file=cands.txt
    number=0
    for methods in during,overlap,contain,equal contain,during \
        equal,during,contain contain; do
        number=$((number + 1))
        t.rast3d.mapcalc inputs=window,cands output=taken_$number \
            basename=taken_$number expression="cands" method=$methods
        value=$(t.rast3d.list -s input=taken_$number columns=min)
        echo "$methods: $value"
    done
    ```

    ```text
    during,overlap,contain,equal: 200.0
    contain,during: 200.0
    equal,during,contain: 400.0
    contain: 300.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(
        expression="\n".join(
            (
                "window_1 = 1",
                "cand_a = 100",
                "cand_b = 200",
                "cand_c = 300",
                "cand_d = 400",
            )
        )
    )
    Path("window.txt").write_text("window_1|10|20\n")
    Path("cands.txt").write_text("cand_a|12|18\ncand_b|5|25\ncand_c|11|13\ncand_d|10|20\n")
    tools.t_create(
        type="str3ds",
        temporaltype="relative",
        output="window",
        title="Window",
        description="One granule",
    )
    tools.t_create(
        type="str3ds",
        temporaltype="relative",
        output="cands",
        title="Candidates",
        description="Four maps related to the granule",
    )
    tools.t_register(type="raster_3d", input="window", unit="days", file="window.txt")
    tools.t_register(type="raster_3d", input="cands", unit="days", file="cands.txt")
    lists = (
        "during,overlap,contain,equal",
        "contain,during",
        "equal,during,contain",
        "contain",
    )
    for number, methods in enumerate(lists, start=1):
        tools.t_rast3d_mapcalc(
            inputs="window,cands",
            output=f"taken_{number}",
            basename=f"taken_{number}",
            expression="cands",
            method=methods,
        )
        value = tools.t_rast3d_list(input=f"taken_{number}", columns="min", flags="s").text
        print(f"{methods}: {value}")
    ```

    ```text
    during,overlap,contain,equal: 200.0
    contain,during: 200.0
    equal,during,contain: 400.0
    contain: 300.0
    ```

### Use the time of the granule

The dataset `moisture` has four maps for the days from 1 to 4 March 2026. The
maps have three layers of two by two voxels, and their values are the layer
number (1, 2 and 3) plus 0, 10, 20 and 30, so the smallest and largest values
are 1 and 3, 11 and 13, 21 and 23, and 31 and 33. `depth()` counts the layers
from 1. The expressions of the first four blocks need no map, only the time of
the granule, so they name `moisture` only in **inputs**. The granules are the
days from 1 to 4 March 2026; 1 March 2026 is a Sunday, the 60th day of the
year.

The first block puts three variables into one number: `start_time()` counts the
hundreds, `td()` the tens and `end_time()` the ones. The days start 0, 1, 2 and
3 days after the first, are 1 day long and end 1, 2, 3 and 4 days after the
start of the first, so the results are 11, 112, 213 and 314. The second block
combines the day of the year and the day of the week, tens and ones again: 60
and 7 (Sunday) for the first day, then 61 and 1 (Monday) and so on, so 607, 611,
622 and 633. The third block gives the month and the day at the end: the month
is 3 and the end day is 2 to 5, so the results are 302 to 305. The fourth block
uses the weeks, which start on Monday: the first day starts in week 9 and ends
on Monday 2 March, in week 10, so 910, and 1010 for the other days.

The dataset `gauge` has two time instants, at 06:00 on 1 March and at 18:00 on 2
March, and its maps have the values 1 and 2. The last block shows what an
instant gets: `start_time()` is the offset in days and fractions of days from
the first instant, 0 and 1.5, and `end_time()` is null, so `isnull()` is true
and the result is 100 and 101.5. The next block shows that `td()` of an
instant is null as well: the result is 7.

The weeks are ISO weeks. The dataset `newyear` has one day, 1 January 2027,
which is a Friday in week 53 of 2026, and the last block gives `start_week()`
53.

=== "Command line"

    ```sh
    for step in 1 2 3 4; do
        echo "moisture_$step = depth() + 10 * ($step - 1)"
    done | r3.mapcalc file=-
    t.create type=str3ds output=moisture title="Moisture" \
        description="Test values by layer and day"
    t.register -i type=raster_3d input=moisture \
        maps=moisture_1,moisture_2,moisture_3,moisture_4 \
        start=2026-03-01 increment="1 day"
    t.rast3d.mapcalc inputs=moisture output=when basename=when \
        expression="start_time() * 100 + td() * 10 + end_time()"
    t.rast3d.list input=when columns=name,min,max
    ```

    ```text
    name|min|max
    when_1|11.0|11.0
    when_2|112.0|112.0
    when_3|213.0|213.0
    when_4|314.0|314.0
    ```

    ```sh
    t.rast3d.mapcalc inputs=moisture output=calendar basename=calendar \
        expression="start_doy() * 10 + start_dow()"
    t.rast3d.list input=calendar columns=name,min,max
    ```

    ```text
    name|min|max
    calendar_1|607.0|607.0
    calendar_2|611.0|611.0
    calendar_3|622.0|622.0
    calendar_4|633.0|633.0
    ```

    ```sh
    t.rast3d.mapcalc inputs=moisture output=month_day basename=month_day \
        expression="start_month() * 100 + end_day()"
    t.rast3d.list input=month_day columns=name,min,max
    ```

    ```text
    name|min|max
    month_day_1|302.0|302.0
    month_day_2|303.0|303.0
    month_day_3|304.0|304.0
    month_day_4|305.0|305.0
    ```

    ```sh
    t.rast3d.mapcalc inputs=moisture output=weeks basename=weeks \
        expression="start_week() * 100 + end_week()"
    t.rast3d.list input=weeks columns=name,min,max
    ```

    ```text
    name|min|max
    weeks_1|910.0|910.0
    weeks_2|1010.0|1010.0
    weeks_3|1010.0|1010.0
    weeks_4|1010.0|1010.0
    ```

    ```sh
    r3.mapcalc expression="gauge_1 = 1"
    r3.mapcalc expression="gauge_2 = 2"
    t.create type=str3ds output=gauge title="Gauge" description="Two instants"
    t.register type=raster_3d input=gauge maps=gauge_1 start="2026-03-01 06:00:00"
    t.register type=raster_3d input=gauge maps=gauge_2 start="2026-03-02 18:00:00"
    t.rast3d.mapcalc inputs=gauge output=instants basename=instants \
        expression="start_time() + if(isnull(end_time()), 100, 0)"
    t.rast3d.list input=instants columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    instants_1|2026-03-01 06:00:00|None|100.0|100.0
    instants_2|2026-03-02 18:00:00|None|101.5|101.5
    ```

    ```sh
    t.rast3d.mapcalc inputs=gauge output=lengths basename=lengths \
        expression="if(isnull(td()), 7, 0)"
    t.rast3d.list input=lengths columns=name,min,max
    ```

    ```text
    name|min|max
    lengths_1|7.0|7.0
    lengths_2|7.0|7.0
    ```

    ```sh
    r3.mapcalc expression="newyear_1 = 1"
    t.create type=str3ds output=newyear title="New year" description="One day"
    t.register type=raster_3d input=newyear maps=newyear_1 \
        start=2027-01-01 end=2027-01-02
    t.rast3d.mapcalc inputs=newyear output=iso basename=iso \
        expression="start_week()"
    t.rast3d.list input=iso columns=name,min,max
    ```

    ```text
    name|min|max
    iso_1|53.0|53.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(
        expression="\n".join(
            f"moisture_{step} = depth() + 10 * ({step} - 1)" for step in range(1, 5)
        )
    )
    tools.t_create(
        type="str3ds",
        output="moisture",
        title="Moisture",
        description="Test values by layer and day",
    )
    tools.t_register(
        type="raster_3d",
        input="moisture",
        maps="moisture_1,moisture_2,moisture_3,moisture_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast3d_mapcalc(
        inputs="moisture",
        output="when",
        basename="when",
        expression="start_time() * 100 + td() * 10 + end_time()",
    )
    print(tools.t_rast3d_list(input="when", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    when_1|11.0|11.0
    when_2|112.0|112.0
    when_3|213.0|213.0
    when_4|314.0|314.0
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="moisture",
        output="calendar",
        basename="calendar",
        expression="start_doy() * 10 + start_dow()",
    )
    print(tools.t_rast3d_list(input="calendar", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    calendar_1|607.0|607.0
    calendar_2|611.0|611.0
    calendar_3|622.0|622.0
    calendar_4|633.0|633.0
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="moisture",
        output="month_day",
        basename="month_day",
        expression="start_month() * 100 + end_day()",
    )
    print(tools.t_rast3d_list(input="month_day", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    month_day_1|302.0|302.0
    month_day_2|303.0|303.0
    month_day_3|304.0|304.0
    month_day_4|305.0|305.0
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="moisture",
        output="weeks",
        basename="weeks",
        expression="start_week() * 100 + end_week()",
    )
    print(tools.t_rast3d_list(input="weeks", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    weeks_1|910.0|910.0
    weeks_2|1010.0|1010.0
    weeks_3|1010.0|1010.0
    weeks_4|1010.0|1010.0
    ```

    ```python
    tools.r3_mapcalc(expression="gauge_1 = 1")
    tools.r3_mapcalc(expression="gauge_2 = 2")
    tools.t_create(type="str3ds", output="gauge", title="Gauge", description="Two instants")
    tools.t_register(
        type="raster_3d", input="gauge", maps="gauge_1", start="2026-03-01 06:00:00"
    )
    tools.t_register(
        type="raster_3d", input="gauge", maps="gauge_2", start="2026-03-02 18:00:00"
    )
    tools.t_rast3d_mapcalc(
        inputs="gauge",
        output="instants",
        basename="instants",
        expression="start_time() + if(isnull(end_time()), 100, 0)",
    )
    print(
        tools.t_rast3d_list(
            input="instants", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    instants_1|2026-03-01 06:00:00|None|100.0|100.0
    instants_2|2026-03-02 18:00:00|None|101.5|101.5
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="gauge",
        output="lengths",
        basename="lengths",
        expression="if(isnull(td()), 7, 0)",
    )
    print(tools.t_rast3d_list(input="lengths", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    lengths_1|7.0|7.0
    lengths_2|7.0|7.0
    ```

    ```python
    tools.r3_mapcalc(expression="newyear_1 = 1")
    tools.t_create(type="str3ds", output="newyear", title="New year", description="One day")
    tools.t_register(
        type="raster_3d",
        input="newyear",
        maps="newyear_1",
        start="2027-01-01",
        end="2027-01-02",
    )
    tools.t_rast3d_mapcalc(
        inputs="newyear", output="iso", basename="iso", expression="start_week()"
    )
    print(tools.t_rast3d_list(input="iso", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    iso_1|53.0|53.0
    ```

### Use the time of a dataset with relative time

The dataset `runoff` has three steps of 5 hours with relative time. Its maps
`runoff_1` to `runoff_3` hold the values 1 to 3. `start_time()`, `td()` and
`end_time()` give numbers in the unit of the dataset, hours: the steps start 0,
5 and 10 hours after the first, are 5 hours long and end 5, 10 and 15 hours
after the start of the first. With the expression of the first example of the
previous section, the results are 55, 560 and 1065.

The calendar functions need absolute time. The second block calls
`start_doy()` on `runoff`; the tool prints its error and stops without a result
dataset. The block shows the error and then prints `t.rast3d.mapcalc failed`.

=== "Command line"

    ```sh
    for step in 1 2 3; do
        echo "runoff_$step = $step"
    done | r3.mapcalc file=-
    t.create type=str3ds temporaltype=relative output=runoff title="Runoff" \
        description="Simulated runoff in mm per model hour"
    t.register -i type=raster_3d input=runoff maps=runoff_1,runoff_2,runoff_3 \
        start=0 increment=5 unit=hours
    t.rast3d.mapcalc inputs=runoff output=elapsed basename=elapsed \
        expression="start_time() * 100 + td() * 10 + end_time()"
    t.rast3d.list input=elapsed columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    elapsed_1|0|5|55.0|55.0
    elapsed_2|5|10|560.0|560.0
    elapsed_3|10|15|1065.0|1065.0
    ```

    ```sh
    if ! t.rast3d.mapcalc inputs=runoff output=bad basename=bad \
        expression="start_doy()" 2>&1; then
        echo "t.rast3d.mapcalc failed"
    fi
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    ERROR: The temporal operators <start_*> support only absolute time.
    t.rast3d.mapcalc failed
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    tools.r3_mapcalc(
        expression="\n".join(f"runoff_{step} = {step}" for step in range(1, 4))
    )
    tools.t_create(
        type="str3ds",
        temporaltype="relative",
        output="runoff",
        title="Runoff",
        description="Simulated runoff in mm per model hour",
    )
    tools.t_register(
        type="raster_3d",
        input="runoff",
        maps="runoff_1,runoff_2,runoff_3",
        start=0,
        increment=5,
        unit="hours",
        flags="i",
    )
    tools.t_rast3d_mapcalc(
        inputs="runoff",
        output="elapsed",
        basename="elapsed",
        expression="start_time() * 100 + td() * 10 + end_time()",
    )
    print(
        tools.t_rast3d_list(
            input="elapsed", columns="name,start_time,end_time,min,max"
        ).text
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
        tools.t_rast3d_mapcalc(
            inputs="runoff", output="bad", basename="bad", expression="start_doy()"
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast3d.mapcalc failed")
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    ERROR: The temporal operators <start_*> support only absolute time.
    t.rast3d.mapcalc failed
    ```

### Keep or drop empty results

An expression that sets voxels to null selects time steps by their values.
The first block keeps the values of `moisture` above 15, so the maps of the
first two days (with the largest values 3 and 13) have no valid voxel left. They
are not registered in `warm`, and the second block shows that they are removed
from the mapset. The new maps `warm_3` and `warm_4` keep the numbers of their
granules.

The third block runs the call again with **-n**. The dataset `warm_all`
registers the empty maps as well, with `None` as their smallest and largest
value, and the mapset keeps all four maps.

=== "Command line"

    ```sh
    t.rast3d.mapcalc inputs=moisture output=warm basename=warm \
        expression="if(moisture > 15, moisture, null())"
    t.rast3d.list input=warm columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    warm_3|2026-03-03 00:00:00|21.0|23.0
    warm_4|2026-03-04 00:00:00|31.0|33.0
    ```

    ```sh
    g.list type=raster_3d pattern="warm*" mapset=.
    ```

    ```text
    warm_3
    warm_4
    ```

    ```sh
    t.rast3d.mapcalc -n inputs=moisture output=warm_all basename=warm_all \
        expression="if(moisture > 15, moisture, null())"
    t.rast3d.list input=warm_all columns=name,start_time,min,max
    g.list type=raster_3d pattern="warm_all*" mapset=.
    ```

    ```text
    name|start_time|min|max
    warm_all_1|2026-03-01 00:00:00|None|None
    warm_all_2|2026-03-02 00:00:00|None|None
    warm_all_3|2026-03-03 00:00:00|21.0|23.0
    warm_all_4|2026-03-04 00:00:00|31.0|33.0
    warm_all_1
    warm_all_2
    warm_all_3
    warm_all_4
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast3d_mapcalc(
        inputs="moisture",
        output="warm",
        basename="warm",
        expression="if(moisture > 15, moisture, null())",
    )
    print(tools.t_rast3d_list(input="warm", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    warm_3|2026-03-03 00:00:00|21.0|23.0
    warm_4|2026-03-04 00:00:00|31.0|33.0
    ```

    ```python
    print(tools.g_list(type="raster_3d", pattern="warm*", mapset=".").text)
    ```

    ```text
    warm_3
    warm_4
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="moisture",
        output="warm_all",
        basename="warm_all",
        expression="if(moisture > 15, moisture, null())",
        flags="n",
    )
    print(tools.t_rast3d_list(input="warm_all", columns="name,start_time,min,max").text)
    print(tools.g_list(type="raster_3d", pattern="warm_all*", mapset=".").text)
    ```

    ```text
    name|start_time|min|max
    warm_all_1|2026-03-01 00:00:00|None|None
    warm_all_2|2026-03-02 00:00:00|None|None
    warm_all_3|2026-03-03 00:00:00|21.0|23.0
    warm_all_4|2026-03-04 00:00:00|31.0|33.0
    warm_all_1
    warm_all_2
    warm_all_3
    warm_all_4
    ```

### Take only the maps in the same place

The dataset `patch` has four maps for the days of `moisture`, with the values
1000, 2000, 3000 and 4000. The second map `patch_2` lies next to the squares
of `moisture`, from 202 km to 204 km in the east, so it shares an edge with
them. The third map `patch_3` was made far away, for the squares from 210 km to
212 km in the east and from 108 km to 110 km in the north. The other maps lie
in the squares from 200 km to 202 km, like `moisture`. The current region is
the one from 200 km to 202 km again.

The first block adds `moisture` and `patch`, with 100 where `patch` is null.
The maps `patch_2` and `patch_3` are related in time but read in the current
region where they have no data, so the result for the second and third day is
the value of `moisture` plus 100: 111 to 113, and 121 to 123. The result of the
other days is `moisture` plus `patch`: 1001 to 1003, and 4031 to 4033.

With **-s**, the second block takes only maps whose 2D extent touches or
overlaps that of the granule. `patch_2` touches it and stays, `patch_3` does
not, so the third granule is skipped, and the result has three maps with the
numbers 1, 2 and 4.

=== "Command line"

    ```sh
    for step in 1 2 3 4; do
        if [ $step = 2 ]; then
            g.region n=100000 s=98000 e=204000 w=202000 res=1000 res3=1000 t=3000 b=0 tbres=1000
        elif [ $step = 3 ]; then
            g.region n=110000 s=108000 e=212000 w=210000 res=1000 res3=1000 t=3000 b=0 tbres=1000
        fi
        r3.mapcalc expression="patch_$step = 1000 * $step"
        g.region n=100000 s=98000 e=202000 w=200000 res=1000 res3=1000 t=3000 b=0 tbres=1000
    done
    t.create type=str3ds output=patch title="Patch" description="Four patches"
    t.register -i type=raster_3d input=patch \
        maps=patch_1,patch_2,patch_3,patch_4 start=2026-03-01 increment="1 day"
    t.rast3d.mapcalc inputs=moisture,patch output=near basename=near \
        expression="moisture + if(isnull(patch), 100, patch)"
    t.rast3d.list input=near columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    near_1|2026-03-01 00:00:00|1001.0|1003.0
    near_2|2026-03-02 00:00:00|111.0|113.0
    near_3|2026-03-03 00:00:00|121.0|123.0
    near_4|2026-03-04 00:00:00|4031.0|4033.0
    ```

    ```sh
    t.rast3d.mapcalc -s inputs=moisture,patch output=near_only basename=near_only \
        expression="moisture + if(isnull(patch), 100, patch)"
    t.rast3d.list input=near_only columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    near_only_1|2026-03-01 00:00:00|1001.0|1003.0
    near_only_2|2026-03-02 00:00:00|111.0|113.0
    near_only_4|2026-03-04 00:00:00|4031.0|4033.0
    ```

=== "Python (grass.tools)"

    ```python
    square = {"res": 1000, "res3": 1000, "t": 3000, "b": 0, "tbres": 1000}
    for step in range(1, 5):
        if step == 2:
            tools.g_region(n=100000, s=98000, e=204000, w=202000, **square)
        elif step == 3:
            tools.g_region(n=110000, s=108000, e=212000, w=210000, **square)
        tools.r3_mapcalc(expression=f"patch_{step} = 1000 * {step}")
        tools.g_region(n=100000, s=98000, e=202000, w=200000, **square)
    tools.t_create(type="str3ds", output="patch", title="Patch", description="Four patches")
    tools.t_register(
        type="raster_3d",
        input="patch",
        maps="patch_1,patch_2,patch_3,patch_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast3d_mapcalc(
        inputs="moisture,patch",
        output="near",
        basename="near",
        expression="moisture + if(isnull(patch), 100, patch)",
    )
    print(tools.t_rast3d_list(input="near", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    near_1|2026-03-01 00:00:00|1001.0|1003.0
    near_2|2026-03-02 00:00:00|111.0|113.0
    near_3|2026-03-03 00:00:00|121.0|123.0
    near_4|2026-03-04 00:00:00|4031.0|4033.0
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="moisture,patch",
        output="near_only",
        basename="near_only",
        expression="moisture + if(isnull(patch), 100, patch)",
        flags="s",
    )
    print(tools.t_rast3d_list(input="near_only", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    near_only_1|2026-03-01 00:00:00|1001.0|1003.0
    near_only_2|2026-03-02 00:00:00|111.0|113.0
    near_only_4|2026-03-04 00:00:00|4031.0|4033.0
    ```

### Names of datasets in the expression

A dataset name in the expression is replaced only where it stands as a whole
name. The dataset `day` has one map with the value 4 on March 1. In
`day * start_day()` the name `day` inside `start_day()` stays, so the result is
4 times the day of the month, 1. The dataset `moisture_deep` has one map with
the value 3 on March 1. In `moisture + moisture_deep` the name `moisture`
inside `moisture_deep` stays, so the first granule of `moisture`, whose map
holds the layer number 1 to 3, gets 4 to 6; the other three granules of
`moisture` have no map of `moisture_deep` and are skipped.

Two inputs with the same name cannot be told apart in the expression. The
third block names `day` twice, and the tool stops before it computes anything.

=== "Command line"

    ```sh
    r3.mapcalc expression="day_1 = 4"
    t.create type=str3ds output=day title="Day" description="One map"
    t.register type=raster_3d input=day maps=day_1 \
        start=2026-03-01 end=2026-03-02
    t.rast3d.mapcalc inputs=day output=day_of_month basename=day_of_month \
        expression="day * start_day()"
    t.rast3d.list input=day_of_month columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    day_of_month_1|2026-03-01 00:00:00|4.0|4.0
    ```

    ```sh
    r3.mapcalc expression="moisture_deep_1 = 3"
    t.create type=str3ds output=moisture_deep title="Deep moisture" \
        description="One map"
    t.register type=raster_3d input=moisture_deep maps=moisture_deep_1 \
        start=2026-03-01 end=2026-03-02
    t.rast3d.mapcalc inputs=moisture,moisture_deep output=layers basename=layers \
        expression="moisture + moisture_deep"
    t.rast3d.list input=layers columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    layers_1|2026-03-01 00:00:00|4.0|6.0
    ```

    ```sh
    if ! t.rast3d.mapcalc inputs=day,day output=twice basename=twice \
        expression="day + 1" 2>&1; then
        echo "t.rast3d.mapcalc failed"
    fi
    ```

    ```text
    ERROR: The name <day> stands more than once in inputs, so the expression
    cannot tell the inputs apart
    t.rast3d.mapcalc failed
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(expression="day_1 = 4")
    tools.t_create(type="str3ds", output="day", title="Day", description="One map")
    tools.t_register(
        type="raster_3d", input="day", maps="day_1", start="2026-03-01", end="2026-03-02"
    )
    tools.t_rast3d_mapcalc(
        inputs="day",
        output="day_of_month",
        basename="day_of_month",
        expression="day * start_day()",
    )
    print(
        tools.t_rast3d_list(
            input="day_of_month", columns="name,start_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|min|max
    day_of_month_1|2026-03-01 00:00:00|4.0|4.0
    ```

    ```python
    tools.r3_mapcalc(expression="moisture_deep_1 = 3")
    tools.t_create(
        type="str3ds", output="moisture_deep", title="Deep moisture", description="One map"
    )
    tools.t_register(
        type="raster_3d",
        input="moisture_deep",
        maps="moisture_deep_1",
        start="2026-03-01",
        end="2026-03-02",
    )
    tools.t_rast3d_mapcalc(
        inputs="moisture,moisture_deep",
        output="layers",
        basename="layers",
        expression="moisture + moisture_deep",
    )
    print(tools.t_rast3d_list(input="layers", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    layers_1|2026-03-01 00:00:00|4.0|6.0
    ```

    ```python
    try:
        tools.t_rast3d_mapcalc(
            inputs="day,day", output="twice", basename="twice", expression="day + 1"
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast3d.mapcalc failed")
    ```

    ```text
    ERROR: The name <day> stands more than once in inputs, so the expression
    cannot tell the inputs apart
    t.rast3d.mapcalc failed
    ```

### Use a dataset of another mapset and replace a result

The mapset `t_rast3d_mapcalc_2` is new and empty. The first block makes it the
current mapset, sets the region of the first example there, and halves
`moisture@t_rast3d_mapcalc`. The expression still uses the name `moisture`,
and the mapset of the input does not have to be in the search path. See
[Datasets of other mapsets](temporalintro.md#datasets-of-other-mapsets). The
maps of `moisture` hold values only in the square where they were made, so the
new maps read null in the rest of the region. The dataset `halved` and its maps
belong to the current mapset; the listing shows the mapset of the maps.

The second block repeats the call without **--overwrite**. The tool stops
because the dataset `halved` exists. The third block adds **--overwrite** and
makes the dataset again, with the same four maps; the tool warns on the standard
error that it unregisters all maps of the old dataset.

The fourth block replaces `halved` once more, now from the dataset `gauge`,
which has two maps. The new dataset holds two maps, with the values 0.5 and 1.
The maps `halved_3` and `halved_4` of the earlier run are no longer registered
in it, but the tool does not remove them: `g.list` still finds all four.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast3d_mapcalc_2
    g.region raster=elev_state_500m res=1000 res3=1000 t=3000 b=0 tbres=1000 -a
    t.rast3d.mapcalc inputs=moisture@t_rast3d_mapcalc output=halved basename=halved \
        expression="moisture / 2"
    t.rast3d.list input=halved columns=name,mapset,min,max
    ```

    ```text
    name|mapset|min|max
    halved_1|t_rast3d_mapcalc_2|0.5|1.5
    halved_2|t_rast3d_mapcalc_2|5.5|6.5
    halved_3|t_rast3d_mapcalc_2|10.5|11.5
    halved_4|t_rast3d_mapcalc_2|15.5|16.5
    ```

    ```sh
    if ! t.rast3d.mapcalc inputs=moisture@t_rast3d_mapcalc output=halved basename=halved \
        expression="moisture / 2" 2>&1; then
        echo "t.rast3d.mapcalc failed"
    fi
    ```

    ```text
    ERROR: Space time raster3d dataset <halved> is already in the database. Use
    the overwrite flag.
    t.rast3d.mapcalc failed
    ```

    ```sh
    t.rast3d.mapcalc --overwrite inputs=moisture@t_rast3d_mapcalc output=halved \
        basename=halved expression="moisture / 2"
    t.rast3d.list input=halved columns=name,mapset,min,max
    ```

    ```text
    name|mapset|min|max
    halved_1|t_rast3d_mapcalc_2|0.5|1.5
    halved_2|t_rast3d_mapcalc_2|5.5|6.5
    halved_3|t_rast3d_mapcalc_2|10.5|11.5
    halved_4|t_rast3d_mapcalc_2|15.5|16.5
    ```

    ```sh
    t.rast3d.mapcalc --overwrite inputs=gauge@t_rast3d_mapcalc output=halved \
        basename=halved expression="gauge / 2"
    t.rast3d.list input=halved columns=name,min,max
    g.list type=raster_3d pattern="halved*" mapset=.
    ```

    ```text
    name|min|max
    halved_1|0.5|0.5
    halved_2|1.0|1.0
    halved_1
    halved_2
    halved_3
    halved_4
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_rast3d_mapcalc_2", flags="c")
    tools.g_region(
        raster="elev_state_500m", res=1000, res3=1000, t=3000, b=0, tbres=1000, flags="a"
    )
    tools.t_rast3d_mapcalc(
        inputs="moisture@t_rast3d_mapcalc",
        output="halved",
        basename="halved",
        expression="moisture / 2",
    )
    print(tools.t_rast3d_list(input="halved", columns="name,mapset,min,max").text)
    ```

    ```text
    name|mapset|min|max
    halved_1|t_rast3d_mapcalc_2|0.5|1.5
    halved_2|t_rast3d_mapcalc_2|5.5|6.5
    halved_3|t_rast3d_mapcalc_2|10.5|11.5
    halved_4|t_rast3d_mapcalc_2|15.5|16.5
    ```

    ```python
    try:
        tools.t_rast3d_mapcalc(
            inputs="moisture@t_rast3d_mapcalc",
            output="halved",
            basename="halved",
            expression="moisture / 2",
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast3d.mapcalc failed")
    ```

    ```text
    ERROR: Space time raster3d dataset <halved> is already in the database. Use
    the overwrite flag.
    t.rast3d.mapcalc failed
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="moisture@t_rast3d_mapcalc",
        output="halved",
        basename="halved",
        expression="moisture / 2",
        overwrite=True,
    )
    print(tools.t_rast3d_list(input="halved", columns="name,mapset,min,max").text)
    ```

    ```text
    name|mapset|min|max
    halved_1|t_rast3d_mapcalc_2|0.5|1.5
    halved_2|t_rast3d_mapcalc_2|5.5|6.5
    halved_3|t_rast3d_mapcalc_2|10.5|11.5
    halved_4|t_rast3d_mapcalc_2|15.5|16.5
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="gauge@t_rast3d_mapcalc",
        output="halved",
        basename="halved",
        expression="gauge / 2",
        overwrite=True,
    )
    print(tools.t_rast3d_list(input="halved", columns="name,min,max").text)
    print(tools.g_list(type="raster_3d", pattern="halved*", mapset=".").text)
    ```

    ```text
    name|min|max
    halved_1|0.5|0.5
    halved_2|1.0|1.0
    halved_1
    halved_2
    halved_3
    halved_4
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapset](g.mapset.md), [r3.mapcalc](r3.mapcalc.md),
[t.info](t.info.md),
[t.rast.aggregate.ds](t.rast.aggregate.ds.md),
[t.rast.mapcalc](t.rast.mapcalc.md), [t.rast3d.algebra](t.rast3d.algebra.md),
[t.rast3d.list](t.rast3d.list.md), [t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
