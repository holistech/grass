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
condition selects no map, the tool ends without an error, prints no message and
creates no map.

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
The name in **output** may carry the mapset, as in `output=mean@PERMANENT`.

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

<!-- markdownlint-disable MD046 -->

### Aggregate all maps of a dataset

The dataset `reading` holds four daily maps on a region of one row and three
cells, from 1 March 2026. Each map is a time interval of one day. The value of
a cell is its column number, 1 to 3, plus 3, 0, 9 and 1 in the four maps. The
average of a cell is the column number plus (3 + 0 + 9 + 1) / 4 = 3.25, so the
new map `mean` holds 4.25, 5.25 and 6.25. Its time stamp spans the four maps,
from 1 March to 5 March; *[t.list](t.list.md)* shows it.

=== "Command line"

    ```sh
    g.region n=1 s=0 e=3 w=0 res=1
    for map in "reading_1 3" "reading_2 0" "reading_3 9" "reading_4 1"; do
        set -- $map
        r.mapcalc expression="$1 = col() + $2"
    done
    t.create output=reading title="Readings" description="Four daily readings"
    t.register -i input=reading maps=reading_1,reading_2,reading_3,reading_4 \
        start=2026-03-01 increment="1 day"
    t.rast.series input=reading method=average output=mean
    r.stats -1 input=mean | paste -sd' '
    t.list type=raster columns=name,start_time,end_time format=csv separator=pipe \
        where="name = 'mean'"
    ```

    ```text
    4.25 5.25 6.25
    name|start_time|end_time
    mean|2026-03-01 00:00:00|2026-03-05 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()


    def cells(name):
        return " ".join(tools.r_stats(input=name, flags="1").text.split())


    tools.g_region(n=1, s=0, e=3, w=0, res=1)
    for name, offset in (
        ("reading_1", 3),
        ("reading_2", 0),
        ("reading_3", 9),
        ("reading_4", 1),
    ):
        tools.r_mapcalc(expression=f"{name} = col() + {offset}")
    tools.t_create(output="reading", title="Readings", description="Four daily readings")
    tools.t_register(
        input="reading",
        maps="reading_1,reading_2,reading_3,reading_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_series(input="reading", method="average", output="mean")
    print(cells("mean"))
    print(
        tools.t_list(
            type="raster",
            columns="name,start_time,end_time",
            format="csv",
            separator="pipe",
            where="name = 'mean'",
        ).text
    )
    ```

    ```text
    4.25 5.25 6.25
    name|start_time|end_time
    mean|2026-03-01 00:00:00|2026-03-05 00:00:00
    ```

### Compute several methods in one run

One run takes a list of methods and a list of output names of the same length,
and the maps come in the order of the lists. With `minimum`, `maximum` and
`range` the new maps `low`, `high` and `spread` hold the smallest value of
each cell, 0 + 1 = 1, 2 and 3, the largest, 9 + 1 = 10, 11 and 12, and their
difference, 9 in every cell. The dataset `reading` is the one of the previous
example.

=== "Command line"

    ```sh
    t.rast.series input=reading method=minimum,maximum,range \
        output=low,high,spread
    for map in low high spread; do
        echo "$map: $(r.stats -1 input=$map | paste -sd' ')"
    done
    ```

    ```text
    low: 1 2 3
    high: 10 11 12
    spread: 9 9 9
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_series(
        input="reading", method="minimum,maximum,range", output="low,high,spread"
    )
    for name in ("low", "high", "spread"):
        print(f"{name}: {cells(name)}")
    ```

    ```text
    low: 1 2 3
    high: 10 11 12
    spread: 9 9 9
    ```

### Compute quantiles

The four values of a cell, sorted, are 0, 1, 3 and 9 plus the column number.
The quantile 0.25 lies at the position `0.25 * 3 = 0.75`, so it is
`0 + 0.75 * (1 - 0) = 0.75` plus the column number: 1.75, 2.75 and 3.75. The
quantile 0.75 lies at the position 2.25, `3 + 0.25 * (9 - 3) = 4.5` plus the
column number: 5.5, 6.5 and 7.5. The first block asks for both quantiles with
two methods `quantile`. In the second block `quantile` stands next to
`maximum`, which takes no quantile: the median lies at the position 1.5, the
mean of 1 and 3, which is 2 plus the column number, so 3, 4 and 5, and the
maximum is 10, 11 and 12.

=== "Command line"

    ```sh
    t.rast.series input=reading method=quantile,quantile quantile=0.25,0.75 \
        output=lower,upper
    for map in lower upper; do
        echo "$map: $(r.stats -1 input=$map | paste -sd' ')"
    done
    ```

    ```text
    lower: 1.75 2.75 3.75
    upper: 5.5 6.5 7.5
    ```

    ```sh
    t.rast.series input=reading method=quantile,maximum quantile=0.5 \
        output=median,top
    for map in median top; do
        echo "$map: $(r.stats -1 input=$map | paste -sd' ')"
    done
    ```

    ```text
    median: 3 4 5
    top: 10 11 12
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_series(
        input="reading",
        method="quantile,quantile",
        quantile="0.25,0.75",
        output="lower,upper",
    )
    for name in ("lower", "upper"):
        print(f"{name}: {cells(name)}")
    ```

    ```text
    lower: 1.75 2.75 3.75
    upper: 5.5 6.5 7.5
    ```

    ```python
    tools.t_rast_series(
        input="reading", method="quantile,maximum", quantile=0.5, output="median,top"
    )
    for name in ("median", "top"):
        print(f"{name}: {cells(name)}")
    ```

    ```text
    median: 3 4 5
    top: 10 11 12
    ```

### Select the maps and set their order

The first block aggregates only the maps that start on or after 3 March, the
third and the fourth, with `sum`: 9 + 1 = 10 plus twice the column number, so
12, 14 and 16. The new map `late` starts on 3 March, where the third map
starts, and ends on 5 March, where the fourth map ends.

The other blocks compute `slope` and `max_raster` for two orders. In the time
order the values of the first cell are 4, 1, 10 and 2. The slope is the slope
of a line fitted to these values at the positions 0 to 3, and it is 0.3; the
largest value, 10, is at the position 2, so `max_raster` is 2. With **order**
`max` the maps are sorted by their largest cell value, which is 6, 3, 12 and 4
in the time order; the values of the first cell then are 1, 2, 4 and 10, the
slope is 2.9 and the largest value is at the position 3.

=== "Command line"

    ```sh
    t.rast.series input=reading method=sum output=late \
        where="start_time >= '2026-03-03'"
    r.stats -1 input=late | paste -sd' '
    t.list type=raster columns=name,start_time,end_time format=csv separator=pipe \
        where="name = 'late'"
    ```

    ```text
    12 14 16
    name|start_time|end_time
    late|2026-03-03 00:00:00|2026-03-05 00:00:00
    ```

    ```sh
    t.rast.series input=reading method=slope,max_raster \
        output=slope_by_time,max_by_time
    t.rast.series input=reading method=slope,max_raster order=max \
        output=slope_by_max,max_by_max
    for map in slope_by_time max_by_time slope_by_max max_by_max; do
        echo "$map: $(r.stats -1 input=$map | paste -sd' ')"
    done
    ```

    ```text
    slope_by_time: 0.3 0.3 0.3
    max_by_time: 2 2 2
    slope_by_max: 2.9 2.9 2.9
    max_by_max: 3 3 3
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_series(
        input="reading",
        method="sum",
        output="late",
        where="start_time >= '2026-03-03'",
    )
    print(cells("late"))
    print(
        tools.t_list(
            type="raster",
            columns="name,start_time,end_time",
            format="csv",
            separator="pipe",
            where="name = 'late'",
        ).text
    )
    ```

    ```text
    12 14 16
    name|start_time|end_time
    late|2026-03-03 00:00:00|2026-03-05 00:00:00
    ```

    ```python
    tools.t_rast_series(
        input="reading",
        method="slope,max_raster",
        output="slope_by_time,max_by_time",
    )
    tools.t_rast_series(
        input="reading",
        method="slope,max_raster",
        order="max",
        output="slope_by_max,max_by_max",
    )
    for name in ("slope_by_time", "max_by_time", "slope_by_max", "max_by_max"):
        print(f"{name}: {cells(name)}")
    ```

    ```text
    slope_by_time: 0.3 0.3 0.3
    max_by_time: 2 2 2
    slope_by_max: 2.9 2.9 2.9
    max_by_max: 3 3 3
    ```

### Select the same month of several years

The dataset `temp` holds six monthly maps on a region of one row and two
cells, January to March of 2025 and of 2026. The maps are numbered 1 to 6 in
time order, and the value of a cell is its column number, 1 or 2, plus 10 times
the number of the map. The condition `strftime('%m', start_time) = '01'`
selects the January maps, 1 and 4, in both years: the average of a cell is the
column number plus (10 + 40) / 2 = 25, so 26 and 27. The loop in the second
block computes the climatology of each month for two methods. The maps of a
month are numbered 1 + k and 4 + k for k = 0, 1 and 2, so the average is the
column number plus 25, 35 and 45, and the maximum is the column number plus 40,
50 and 60.

=== "Command line"

    ```sh
    g.region n=1 s=0 e=2 w=0 res=1
    for number in 1 2 3 4 5 6; do
        r.mapcalc expression="temp_$number = col() + 10 * $number"
    done
    t.create output=temp title="Temperature" \
        description="Three months of two years"
    t.register -i input=temp maps=temp_1,temp_2,temp_3 \
        start=2025-01-01 increment="1 month"
    t.register -i input=temp maps=temp_4,temp_5,temp_6 \
        start=2026-01-01 increment="1 month"
    t.rast.series input=temp method=average output=january \
        where="strftime('%m', start_time) = '01'"
    r.stats -1 input=january | paste -sd' '
    ```

    ```text
    26 27
    ```

    ```sh
    for month in 01 02 03; do
        for method in average maximum; do
            t.rast.series input=temp method=$method output=${method}_$month \
                where="strftime('%m', start_time) = '$month'"
            echo "${method}_$month: $(r.stats -1 input=${method}_$month | paste -sd' ')"
        done
    done
    ```

    ```text
    average_01: 26 27
    maximum_01: 41 42
    average_02: 36 37
    maximum_02: 51 52
    average_03: 46 47
    maximum_03: 61 62
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=1, s=0, e=2, w=0, res=1)
    for number in range(1, 7):
        tools.r_mapcalc(expression=f"temp_{number} = col() + 10 * {number}")
    tools.t_create(
        output="temp", title="Temperature", description="Three months of two years"
    )
    for maps, start in (
        ("temp_1,temp_2,temp_3", "2025-01-01"),
        ("temp_4,temp_5,temp_6", "2026-01-01"),
    ):
        tools.t_register(
            input="temp", maps=maps, start=start, increment="1 month", flags="i"
        )
    tools.t_rast_series(
        input="temp",
        method="average",
        output="january",
        where="strftime('%m', start_time) = '01'",
    )
    print(cells("january"))
    ```

    ```text
    26 27
    ```

    ```python
    for month in ("01", "02", "03"):
        for method in ("average", "maximum"):
            tools.t_rast_series(
                input="temp",
                method=method,
                output=f"{method}_{month}",
                where=f"strftime('%m', start_time) = '{month}'",
            )
            print(f"{method}_{month}: {cells(f'{method}_{month}')}")
    ```

    ```text
    average_01: 26 27
    maximum_01: 41 42
    average_02: 36 37
    maximum_02: 51 52
    average_03: 46 47
    maximum_03: 61 62
    ```

### Handle null cells

The dataset `gappy` holds two daily maps. The first holds 10, 20 and 30, the
second holds the same values but is null in the first cell. By default the
average of the first cell is the value of the first map alone, 10, and the
count is 1 there and 2 in the other cells. With **-n** a cell that is null in
one map is null in the result, so the first cell is `*`, the symbol of
*r.stats* for a null cell.

=== "Command line"

    ```sh
    r.mapcalc expression="gappy_1 = col() * 10"
    r.mapcalc expression="gappy_2 = if(col() == 1, null(), col() * 10)"
    t.create output=gappy title="Gaps" description="One null cell in the second map"
    t.register -i input=gappy maps=gappy_1,gappy_2 start=2026-03-01 \
        increment="1 day"
    t.rast.series input=gappy method=average,count output=skip_average,skip_count
    t.rast.series -n input=gappy method=average,count \
        output=keep_average,keep_count
    for map in skip_average skip_count keep_average keep_count; do
        echo "$map: $(r.stats -1 input=$map | paste -sd' ')"
    done
    ```

    ```text
    skip_average: 10 20
    skip_count: 1 2
    keep_average: * 20
    keep_count: * 2
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="gappy_1 = col() * 10")
    tools.r_mapcalc(expression="gappy_2 = if(col() == 1, null(), col() * 10)")
    tools.t_create(
        output="gappy", title="Gaps", description="One null cell in the second map"
    )
    tools.t_register(
        input="gappy",
        maps="gappy_1,gappy_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_series(
        input="gappy", method="average,count", output="skip_average,skip_count"
    )
    tools.t_rast_series(
        input="gappy",
        method="average,count",
        output="keep_average,keep_count",
        flags="n",
    )
    for name in ("skip_average", "skip_count", "keep_average", "keep_count"):
        print(f"{name}: {cells(name)}")
    ```

    ```text
    skip_average: 10 20
    skip_count: 1 2
    keep_average: * 20
    keep_count: * 2
    ```

### Give the new map no time stamp

With the flag **-t** the new map `plain` is computed as before but gets no time
stamp and is not registered. *[t.list](t.list.md)* lists the maps registered in
the temporal database with their time: `mean` from the first example and `late`
from the fourth example are there, `plain` is not.

=== "Command line"

    ```sh
    t.rast.series -t input=reading method=average output=plain
    r.stats -1 input=plain | paste -sd' '
    t.list type=raster columns=name,start_time,end_time format=csv separator=pipe \
        where="name in ('mean', 'late', 'plain')"
    ```

    ```text
    4.25 5.25
    name|start_time|end_time
    late|2026-03-03 00:00:00|2026-03-05 00:00:00
    mean|2026-03-01 00:00:00|2026-03-05 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_series(input="reading", method="average", output="plain", flags="t")
    print(cells("plain"))
    print(
        tools.t_list(
            type="raster",
            columns="name,start_time,end_time",
            format="csv",
            separator="pipe",
            where="name in ('mean', 'late', 'plain')",
        ).text
    )
    ```

    ```text
    4.25 5.25
    name|start_time|end_time
    late|2026-03-03 00:00:00|2026-03-05 00:00:00
    mean|2026-03-01 00:00:00|2026-03-05 00:00:00
    ```

### Limit the open files and set the threads

A **file_limit** of 2 is below the four maps of `reading`, so the tool runs
*r.series* with its flag **-z** and warns on the standard error. The result is
the same as without the flag: the sum of a cell is four times the column number
plus 13, so 17, 21 and 25. The options **nprocs** and **memory** are passed to
*r.series* and do not change the result either.

=== "Command line"

    ```sh
    t.rast.series input=reading method=sum output=total file_limit=2 nprocs=2 \
        memory=100
    r.stats -1 input=total | paste -sd' '
    ```

    ```text
    17 21
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_series(
        input="reading",
        method="sum",
        output="total",
        file_limit=2,
        nprocs=2,
        memory=100,
    )
    print(cells("total"))
    ```

    ```text
    17 21
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
