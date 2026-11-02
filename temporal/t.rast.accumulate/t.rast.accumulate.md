## DESCRIPTION

*t.rast.accumulate* adds up the maps of a space time raster dataset over time,
cell by cell, in cycles: a running sum of temperature above a threshold
(growing degree days), of a mean, or of the other indices described below. The
sum restarts at the beginning of every cycle, for example every year. The
result is a new space time raster dataset with one accumulated map per
granule. The accumulation of one granule is done by
*[r.series.accumulate](r.series.accumulate.md)*, which gets the maps of the
granule as input and the result of the granule before as its **basemap**. The
result can be examined with *[t.rast.accdetect](t.rast.accdetect.md)*, which
detects accumulation patterns in it. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets.

### Time, cycles and granules

The accumulation runs over the time from **start** to **stop**. This time is
cut into cycles of the length **cycle**, and every cycle into granules of the
length **granularity**. The first cycle begins at **start**. At the beginning
of every cycle the sum starts from zero again.

- **start** is the beginning of the first cycle and is required. With absolute
  time it is a date such as `2026-03-01`; with relative time it is an integer
  in the unit of the dataset.
- **stop** ends the accumulation. A cycle that reaches beyond **stop** ends at
  **stop**, and a map that starts at **stop** or later is not used. Without
  **stop**, the run ends with the input dataset; a map that is a time instant
  at the end of the dataset is processed as well.
- **cycle** is the length of a cycle, such as `12 months` or `3 days`, and is
  required. With relative time it is an integer.
- **offset** is a time that is skipped between the end of a cycle and the
  beginning of the next one. Maps that start in the skipped time are not
  used. Without **offset**, a cycle begins where the cycle before ended.
- **granularity** is the length of a granule. In every granule, the maps that
  belong to it are accumulated into one result map. The default is `1 day`
  with absolute time. With relative time there is no usable default: give
  **granularity** as an integer, such as `granularity=1`.

Cycles and offsets in months or years are counted from **start**, and a month
step that ends behind the last day of a shorter month ends on that day. Monthly
cycles from 2001-01-31 therefore start on 2001-02-28 and 2001-03-31; the
granules of a cycle are counted from its start in the same way. If only one of
**cycle** and **offset** is in months or years, such as a cycle in months with
an offset in days, each cycle starts one offset after the end of the cycle
before.

With absolute time, a **start** that does not lie on the beginning of the
**granularity** is moved to it: with `granularity="1 months"`, the start
`2026-03-02` becomes `2026-03-01`. The tool warns and names both times. The
cycles count from the moved start. *[t.rast.accdetect](t.rast.accdetect.md)*
does not move its start; for the same cycles, give it the moved start.

The maps of a granule are found by their temporal relation to the granule. The
maps that have the time of the granule are used. If there are none, the maps
that lie inside the granule are used; otherwise the maps that overlap the
granule at its start or at its end, and last the maps that cover the whole
granule. A map is used for the first of these relations that has any map, so
the maps of different relations are never mixed. A granule without a map gets
no result map; the next granule with maps goes on from the last result of the
cycle.

The option **-r** reverses the direction of the accumulation within every
cycle: the granules are accumulated from the last to the first, so the map of
the last granule holds the result of one step and the map of the first granule
the sum of all.

### Method and limits

The option **method** selects the index that is added up. The input maps of a
granule are reduced to their mean `avg` and their largest value `max`; with
one map per granule both are the value of the map. With the limits `lower`
and `upper` of the granule, which are described below, the methods compute the
increment of a granule:

- `mean` (the default) adds `avg`. The limits do not enter the sum, but a
  lower limit that is not below the upper limit stops the run for every
  method.
- `gdd`, growing degree days, adds `avg - lower`, but not less than 0.
- `bedd`, biologically effective degree days, adds `min(avg, upper) - lower`,
  but not less than 0. This is the only method that uses the upper limit.
- `huglin`, the Huglin heliothermal index, adds `(avg + max) / 2 - lower`, but
  not less than 0.

The lower limit and the upper limit of a granule come from the options
**lower** and **upper**, which name space time raster datasets, or from
**limits**. The option **limits** takes two numbers, `lower,upper`, such as
`limits=10,30`. It is required, also for the method `mean`, and is used for all
cells in every granule for which no map of **lower** or **upper** is found. The
upper limit must be above the lower limit; *t.rast.accumulate* refuses
**limits** that do not rise before any map is made. The option **upper** works
only together with **lower**, and both datasets must have the same temporal
type as the input dataset.

The map of **lower** or **upper** for a granule is looked up by the relation of
the granule to the maps of the dataset: first a map with the time of the
granule (`equals`), then a map that covers the granule (`during`), then a map
that overlaps the beginning of the granule (`overlaps`) or its end
(`overlapped`), and last a map inside the granule (`contains`). The first map
of the first relation that has any map is used. A granule without such a map
takes the number from **limits**.

The options **scale** and **shift** transform the values of the input maps
before they are accumulated, `new = old * scale + shift`; they are passed to
*r.series.accumulate*. Without them, the values are used as they are.

A cell without a value (NULL) in the first granule of a cycle stays NULL in
every later granule of that cycle, because there is no earlier sum to add the
later values to. A NULL cell in a later granule keeps the sum of the granules
before it.

### Output

The option **output** names the new space time raster dataset. It is created
in the current mapset. The option **basename** is the beginning of the names
of the result maps and is required. The tool appends a suffix, which the
option **suffix** selects:

- `gran` (the default) appends the start of the granule, with the resolution of
  the granularity of the input dataset, such as `_2026_03_01` or
  `_2026_06_01_12`. With relative time it appends a number.
- `time` appends the start of the granule with the whole time of the day, such
  as `_2026_06_01T00_00_00`.
- `num` appends a number of five digits, such as `_00001`. The numbers count
  the result maps in the order of the computation, over all cycles.

Every result map has the time of its granule. A result map that has no cell
with a value is empty. The flag **-n** registers the empty maps in the output
dataset; without it, they are removed.

## NOTES

*t.rast.accumulate* reads datasets of other mapsets: **input**, **lower** and
**upper** can be given with a mapset, `input=ones@PERMANENT`, or without one,
when the mapset is in the search path (see *[g.mapsets](g.mapsets.md)*). The
output dataset and its maps are always created in the current mapset. The last
example shows this.

An existing output dataset stops the run before any computation, unless
**--overwrite** is set.
A name with a dot is refused for a new dataset before any map is made.

If no map with values is computed, the tool warns and ends without creating the
output dataset. This happens when the cycles lie before or after the data or
in a gap, when a **stop** is not after the **start** (such as a relative stop of
0), and when every computed map is empty and **-n** is not set. With
**--overwrite**, an output dataset that exists is removed in this case, and the
tool warns again that it did so. The maps of the removed dataset stay as maps,
except for maps that have the name of a new result map, which the computation
replaces and then removes. This also holds for a map that another dataset
holds: with **--overwrite** and an empty result, such a map is replaced by an
empty map and removed, and the other dataset loses it. The seventh example
shows an empty result.

A cycle in which no map starts is skipped. An empty input dataset ends with a
warning and creates no output.

With relative time, the unit of the dataset is the unit of **start**, **stop**,
**cycle**, **offset** and **granularity**; they are integers without a unit.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Accumulate the daily temperature

The dataset `temperature` has six daily maps from 1 to 6 March 2026 on a region
of three cells in one row. The map of day `n` holds the value of the day plus
the column number minus one, so the cells of a map differ by one. The values
of the first cell are 4, 12, 14, 8, 16 and 20, those of the last cell two more.

The first block accumulates growing degree days above 10 with one cycle of six
days. The increment of a day is its value minus 10, but not below 0, so the
first cell adds 0, 2, 4, 0, 6 and 10: its sums are 0, 2, 6, 6, 12 and 22. The
last cell adds 0, 4, 6, 0, 8 and 12 and ends with 30. The listing shows the
smallest and the largest value of each result map, the values of the first
and the last cell. The names of the maps end with the date of the granule. The
upper limit 30 is required but not used by the method `gdd`.

The second block leaves out **method**. The default is `mean`, which adds the
values themselves: the sums of the first cell are 4, 16, 30, 38, 54 and 74.

=== "Command line"

    ```sh
    g.region n=1 s=0 e=3 w=0 res=1
    r.mapcalc expression="temperature_1 = 4 + col() - 1"
    r.mapcalc expression="temperature_2 = 12 + col() - 1"
    r.mapcalc expression="temperature_3 = 14 + col() - 1"
    r.mapcalc expression="temperature_4 = 8 + col() - 1"
    r.mapcalc expression="temperature_5 = 16 + col() - 1"
    r.mapcalc expression="temperature_6 = 20 + col() - 1"
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature"
    t.register -i input=temperature \
        maps=temperature_1,temperature_2,temperature_3,temperature_4,temperature_5,temperature_6 \
        start=2026-03-01 increment="1 day"
    t.rast.accumulate input=temperature output=temperature_gdd basename=gdd \
        start=2026-03-01 cycle="6 days" limits=10,30 method=gdd
    t.rast.list input=temperature_gdd columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    gdd_2026_03_01|2026-03-01 00:00:00|2026-03-02 00:00:00|0.0|0.0
    gdd_2026_03_02|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|4.0
    gdd_2026_03_03|2026-03-03 00:00:00|2026-03-04 00:00:00|6.0|10.0
    gdd_2026_03_04|2026-03-04 00:00:00|2026-03-05 00:00:00|6.0|10.0
    gdd_2026_03_05|2026-03-05 00:00:00|2026-03-06 00:00:00|12.0|18.0
    gdd_2026_03_06|2026-03-06 00:00:00|2026-03-07 00:00:00|22.0|30.0
    ```

    ```sh
    t.rast.accumulate input=temperature output=temperature_mean basename=mean \
        start=2026-03-01 cycle="6 days" limits=10,30
    t.rast.list input=temperature_mean columns=name,min,max
    ```

    ```text
    name|min|max
    mean_2026_03_01|4.0|6.0
    mean_2026_03_02|16.0|20.0
    mean_2026_03_03|30.0|36.0
    mean_2026_03_04|38.0|46.0
    mean_2026_03_05|54.0|64.0
    mean_2026_03_06|74.0|86.0
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=1, s=0, e=3, w=0, res=1)
    for number, value in enumerate((4, 12, 14, 8, 16, 20), start=1):
        tools.r_mapcalc(expression=f"temperature_{number} = {value} + col() - 1")
    tools.t_create(
        output="temperature",
        title="Air temperature",
        description="Daily mean air temperature",
    )
    tools.t_register(
        input="temperature",
        maps=",".join(f"temperature_{number}" for number in range(1, 7)),
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_accumulate(
        input="temperature",
        output="temperature_gdd",
        basename="gdd",
        start="2026-03-01",
        cycle="6 days",
        limits="10,30",
        method="gdd",
    )
    result = tools.t_rast_list(
        input="temperature_gdd", columns="name,start_time,end_time,min,max"
    )
    print(result.text)
    ```

    ```text
    name|start_time|end_time|min|max
    gdd_2026_03_01|2026-03-01 00:00:00|2026-03-02 00:00:00|0.0|0.0
    gdd_2026_03_02|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|4.0
    gdd_2026_03_03|2026-03-03 00:00:00|2026-03-04 00:00:00|6.0|10.0
    gdd_2026_03_04|2026-03-04 00:00:00|2026-03-05 00:00:00|6.0|10.0
    gdd_2026_03_05|2026-03-05 00:00:00|2026-03-06 00:00:00|12.0|18.0
    gdd_2026_03_06|2026-03-06 00:00:00|2026-03-07 00:00:00|22.0|30.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="temperature",
        output="temperature_mean",
        basename="mean",
        start="2026-03-01",
        cycle="6 days",
        limits="10,30",
    )
    print(tools.t_rast_list(input="temperature_mean", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    mean_2026_03_01|4.0|6.0
    mean_2026_03_02|16.0|20.0
    mean_2026_03_03|30.0|36.0
    mean_2026_03_04|38.0|46.0
    mean_2026_03_05|54.0|64.0
    mean_2026_03_06|74.0|86.0
    ```

### Choose the method

The dataset `readings` has two maps per day for three days from 1 June 2026,
registered at an interval of 12 hours: a value by day and one by night. Each
map has the same value in all cells. The values of the days are 24 and 8, 30
and 14, 50 and 20. With the granularity of one day, every granule holds the
two maps of its day, inside it, and their mean is used: 16, 22 and 35. The
largest values are 24, 30 and 50.

Each block uses another method with the limits 10 and 30 and one cycle of
three days. The method `mean` adds the means: 16, 38 and 73. The method `gdd`
adds the mean minus 10: 6, 12 and 25, so the sums are 6, 18 and 43. The method
`bedd` caps the mean at the upper limit 30 first, so the third day adds only
20 and the sum is 38; this is the one method that uses the upper limit. The
method `huglin` takes the mean of `avg` and `max`, minus 10: 10,
16 and 32.5, so the sums are 10, 26 and 58.5.

=== "Command line"

    ```sh
    i=0
    for value in 24 8 30 14 50 20; do
        i=$((i + 1))
        r.mapcalc expression="reading_$i = $value"
    done
    t.create output=readings title="Readings" \
        description="Air temperature by day and by night"
    t.register -i input=readings \
        maps=reading_1,reading_2,reading_3,reading_4,reading_5,reading_6 \
        start="2026-06-01 00:00:00" increment="12 hours"
    t.rast.accumulate input=readings output=readings_mean basename=mean \
        start=2026-06-01 cycle="3 days" limits=10,30 method=mean
    t.rast.list input=readings_mean columns=name,start_time,max
    ```

    ```text
    name|start_time|max
    mean_2026_06_01_00|2026-06-01 00:00:00|16.0
    mean_2026_06_02_00|2026-06-02 00:00:00|38.0
    mean_2026_06_03_00|2026-06-03 00:00:00|73.0
    ```

    ```sh
    t.rast.accumulate input=readings output=readings_gdd basename=gdd \
        start=2026-06-01 cycle="3 days" limits=10,30 method=gdd
    t.rast.list input=readings_gdd columns=name,start_time,max
    ```

    ```text
    name|start_time|max
    gdd_2026_06_01_00|2026-06-01 00:00:00|6.0
    gdd_2026_06_02_00|2026-06-02 00:00:00|18.0
    gdd_2026_06_03_00|2026-06-03 00:00:00|43.0
    ```

    ```sh
    t.rast.accumulate input=readings output=readings_bedd basename=bedd \
        start=2026-06-01 cycle="3 days" limits=10,30 method=bedd
    t.rast.list input=readings_bedd columns=name,start_time,max
    ```

    ```text
    name|start_time|max
    bedd_2026_06_01_00|2026-06-01 00:00:00|6.0
    bedd_2026_06_02_00|2026-06-02 00:00:00|18.0
    bedd_2026_06_03_00|2026-06-03 00:00:00|38.0
    ```

    ```sh
    t.rast.accumulate input=readings output=readings_huglin basename=huglin \
        start=2026-06-01 cycle="3 days" limits=10,30 method=huglin
    t.rast.list input=readings_huglin columns=name,start_time,max
    ```

    ```text
    name|start_time|max
    huglin_2026_06_01_00|2026-06-01 00:00:00|10.0
    huglin_2026_06_02_00|2026-06-02 00:00:00|26.0
    huglin_2026_06_03_00|2026-06-03 00:00:00|58.5
    ```

=== "Python (grass.tools)"

    ```python
    for number, value in enumerate((24, 8, 30, 14, 50, 20), start=1):
        tools.r_mapcalc(expression=f"reading_{number} = {value}")
    tools.t_create(
        output="readings",
        title="Readings",
        description="Air temperature by day and by night",
    )
    tools.t_register(
        input="readings",
        maps=",".join(f"reading_{number}" for number in range(1, 7)),
        start="2026-06-01 00:00:00",
        increment="12 hours",
        flags="i",
    )
    tools.t_rast_accumulate(
        input="readings",
        output="readings_mean",
        basename="mean",
        start="2026-06-01",
        cycle="3 days",
        limits="10,30",
        method="mean",
    )
    print(tools.t_rast_list(input="readings_mean", columns="name,start_time,max").text)
    ```

    ```text
    name|start_time|max
    mean_2026_06_01_00|2026-06-01 00:00:00|16.0
    mean_2026_06_02_00|2026-06-02 00:00:00|38.0
    mean_2026_06_03_00|2026-06-03 00:00:00|73.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="readings",
        output="readings_gdd",
        basename="gdd",
        start="2026-06-01",
        cycle="3 days",
        limits="10,30",
        method="gdd",
    )
    print(tools.t_rast_list(input="readings_gdd", columns="name,start_time,max").text)
    ```

    ```text
    name|start_time|max
    gdd_2026_06_01_00|2026-06-01 00:00:00|6.0
    gdd_2026_06_02_00|2026-06-02 00:00:00|18.0
    gdd_2026_06_03_00|2026-06-03 00:00:00|43.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="readings",
        output="readings_bedd",
        basename="bedd",
        start="2026-06-01",
        cycle="3 days",
        limits="10,30",
        method="bedd",
    )
    print(tools.t_rast_list(input="readings_bedd", columns="name,start_time,max").text)
    ```

    ```text
    name|start_time|max
    bedd_2026_06_01_00|2026-06-01 00:00:00|6.0
    bedd_2026_06_02_00|2026-06-02 00:00:00|18.0
    bedd_2026_06_03_00|2026-06-03 00:00:00|38.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="readings",
        output="readings_huglin",
        basename="huglin",
        start="2026-06-01",
        cycle="3 days",
        limits="10,30",
        method="huglin",
    )
    print(tools.t_rast_list(input="readings_huglin", columns="name,start_time,max").text)
    ```

    ```text
    name|start_time|max
    huglin_2026_06_01_00|2026-06-01 00:00:00|10.0
    huglin_2026_06_02_00|2026-06-02 00:00:00|26.0
    huglin_2026_06_03_00|2026-06-03 00:00:00|58.5
    ```

### Restart the accumulation in cycles

The dataset `ones` has eight daily maps from 1 to 8 March 2026 with the value 1
in all cells. With the method `mean`, the sum counts the days of a cycle, so
the cycles are easy to see.

The first block uses cycles of three days: the sum counts 1, 2, 3 and starts
again on 4 March and on 7 March; the last cycle holds two days. The second
block adds **offset** of one day. The cycle from 1 to 3 March is followed by a
skipped day, 4 March, which has no result map; the second cycle runs from 5 to
7 March, and 8 March falls into the offset after the second cycle. The third
block sets **stop** to 6 March: the second cycle ends at the stop and holds
the days 4 and 5, because the map of 6 March starts at the stop. The fourth
block uses the flag **-r** with cycles of four days. The sums run backwards in
time: the first day of a cycle has the largest sum, 4, and the last day has 1.

=== "Command line"

    ```sh
    for number in 1 2 3 4 5 6 7 8; do
        r.mapcalc expression="one_$number = 1"
    done
    t.create output=ones title="Ones" description="The value 1 on each day"
    t.register -i input=ones \
        maps=one_1,one_2,one_3,one_4,one_5,one_6,one_7,one_8 \
        start=2026-03-01 increment="1 day"
    t.rast.accumulate input=ones output=ones_cycles basename=cycles \
        start=2026-03-01 cycle="3 days" limits=10,30
    t.rast.list input=ones_cycles columns=name,max
    ```

    ```text
    name|max
    cycles_2026_03_01|1.0
    cycles_2026_03_02|2.0
    cycles_2026_03_03|3.0
    cycles_2026_03_04|1.0
    cycles_2026_03_05|2.0
    cycles_2026_03_06|3.0
    cycles_2026_03_07|1.0
    cycles_2026_03_08|2.0
    ```

    ```sh
    t.rast.accumulate input=ones output=ones_offset basename=offset \
        start=2026-03-01 cycle="3 days" offset="1 day" limits=10,30
    t.rast.list input=ones_offset columns=name,max
    ```

    ```text
    name|max
    offset_2026_03_01|1.0
    offset_2026_03_02|2.0
    offset_2026_03_03|3.0
    offset_2026_03_05|1.0
    offset_2026_03_06|2.0
    offset_2026_03_07|3.0
    ```

    ```sh
    t.rast.accumulate input=ones output=ones_stopped basename=stopped \
        start=2026-03-01 stop=2026-03-06 cycle="3 days" limits=10,30
    t.rast.list input=ones_stopped columns=name,max
    ```

    ```text
    name|max
    stopped_2026_03_01|1.0
    stopped_2026_03_02|2.0
    stopped_2026_03_03|3.0
    stopped_2026_03_04|1.0
    stopped_2026_03_05|2.0
    ```

    ```sh
    t.rast.accumulate -r input=ones output=ones_reverse basename=reverse \
        start=2026-03-01 cycle="4 days" limits=10,30
    t.rast.list input=ones_reverse columns=name,max
    ```

    ```text
    name|max
    reverse_2026_03_01|4.0
    reverse_2026_03_02|3.0
    reverse_2026_03_03|2.0
    reverse_2026_03_04|1.0
    reverse_2026_03_05|4.0
    reverse_2026_03_06|3.0
    reverse_2026_03_07|2.0
    reverse_2026_03_08|1.0
    ```

=== "Python (grass.tools)"

    ```python
    for number in range(1, 9):
        tools.r_mapcalc(expression=f"one_{number} = 1")
    tools.t_create(output="ones", title="Ones", description="The value 1 on each day")
    tools.t_register(
        input="ones",
        maps=",".join(f"one_{number}" for number in range(1, 9)),
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_accumulate(
        input="ones",
        output="ones_cycles",
        basename="cycles",
        start="2026-03-01",
        cycle="3 days",
        limits="10,30",
    )
    print(tools.t_rast_list(input="ones_cycles", columns="name,max").text)
    ```

    ```text
    name|max
    cycles_2026_03_01|1.0
    cycles_2026_03_02|2.0
    cycles_2026_03_03|3.0
    cycles_2026_03_04|1.0
    cycles_2026_03_05|2.0
    cycles_2026_03_06|3.0
    cycles_2026_03_07|1.0
    cycles_2026_03_08|2.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="ones",
        output="ones_offset",
        basename="offset",
        start="2026-03-01",
        cycle="3 days",
        offset="1 day",
        limits="10,30",
    )
    print(tools.t_rast_list(input="ones_offset", columns="name,max").text)
    ```

    ```text
    name|max
    offset_2026_03_01|1.0
    offset_2026_03_02|2.0
    offset_2026_03_03|3.0
    offset_2026_03_05|1.0
    offset_2026_03_06|2.0
    offset_2026_03_07|3.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="ones",
        output="ones_stopped",
        basename="stopped",
        start="2026-03-01",
        stop="2026-03-06",
        cycle="3 days",
        limits="10,30",
    )
    print(tools.t_rast_list(input="ones_stopped", columns="name,max").text)
    ```

    ```text
    name|max
    stopped_2026_03_01|1.0
    stopped_2026_03_02|2.0
    stopped_2026_03_03|3.0
    stopped_2026_03_04|1.0
    stopped_2026_03_05|2.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="ones",
        output="ones_reverse",
        basename="reverse",
        start="2026-03-01",
        cycle="4 days",
        limits="10,30",
        flags="r",
    )
    print(tools.t_rast_list(input="ones_reverse", columns="name,max").text)
    ```

    ```text
    name|max
    reverse_2026_03_01|4.0
    reverse_2026_03_02|3.0
    reverse_2026_03_03|2.0
    reverse_2026_03_04|1.0
    reverse_2026_03_05|4.0
    reverse_2026_03_06|3.0
    reverse_2026_03_07|2.0
    reverse_2026_03_08|1.0
    ```

### Scale and shift the input values

**scale** and **shift** transform the values of the input maps before they are
accumulated, `new = old * scale + shift`. The input is the dataset `ones` from
the previous example. With `scale=2` and `shift=0.5`, every day adds 2.5, so the
sums of a cycle of four days are 2.5, 5, 7.5 and 10, and the cycle starts again
at 2.5.

=== "Command line"

    ```sh
    t.rast.accumulate input=ones output=ones_scaled basename=scaled \
        start=2026-03-01 cycle="4 days" limits=10,30 scale=2 shift=0.5
    t.rast.list input=ones_scaled columns=name,max
    ```

    ```text
    name|max
    scaled_2026_03_01|2.5
    scaled_2026_03_02|5.0
    scaled_2026_03_03|7.5
    scaled_2026_03_04|10.0
    scaled_2026_03_05|2.5
    scaled_2026_03_06|5.0
    scaled_2026_03_07|7.5
    scaled_2026_03_08|10.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_accumulate(
        input="ones",
        output="ones_scaled",
        basename="scaled",
        start="2026-03-01",
        cycle="4 days",
        limits="10,30",
        scale=2,
        shift=0.5,
    )
    print(tools.t_rast_list(input="ones_scaled", columns="name,max").text)
    ```

    ```text
    name|max
    scaled_2026_03_01|2.5
    scaled_2026_03_02|5.0
    scaled_2026_03_03|7.5
    scaled_2026_03_04|10.0
    scaled_2026_03_05|2.5
    scaled_2026_03_06|5.0
    scaled_2026_03_07|7.5
    scaled_2026_03_08|10.0
    ```

### Take the limits from datasets

The dataset `warm` has six daily maps from 1 to 6 March 2026 with the values
14, 20, 26, 32, 22 and 12. The datasets `low` and `high` hold the lower and
the upper limit for the first three days only: 10, 12 and 14 for the lower,
30, 25 and 20 for the upper limit. The first block uses both datasets with the
method `bedd`. For the first three days the limits come from the datasets, so
the increments are 14 - 10 = 4, 20 - 12 = 8 and 26 capped at 20, minus 14 = 6;
the sums are 4, 12 and 18. For the last three days there are no maps in the
datasets, so **limits** applies: 32 is capped at 30 and gives 20, 22 gives 12,
12 gives 2; the sums are 38, 50 and 52.

The second block gives only **lower**. The upper limit comes from **limits**
for all days, here 28: the sums are 4, 12, 24 (the third day adds 26 - 14),
and then 42, 54 and 56, because 32 is capped at 28. The third block uses no
dataset; **limits** applies to all days and the sums are 4, 14, 30, 50, 62
and 64.

=== "Command line"

    ```sh
    i=0
    for value in 14 20 26 32 22 12; do
        i=$((i + 1))
        r.mapcalc expression="warm_$i = $value"
    done
    for i in 1 2 3; do
        r.mapcalc expression="low_$i = 8 + 2 * $i"
        r.mapcalc expression="high_$i = 35 - 5 * $i"
    done
    t.create output=warm title="Warm" description="Daily mean air temperature"
    t.create output=low title="Lower" description="Lower limit of the accumulation"
    t.create output=high title="Upper" description="Upper limit of the accumulation"
    t.register -i input=warm \
        maps=warm_1,warm_2,warm_3,warm_4,warm_5,warm_6 \
        start=2026-03-01 increment="1 day"
    t.register -i input=low maps=low_1,low_2,low_3 \
        start=2026-03-01 increment="1 day"
    t.register -i input=high maps=high_1,high_2,high_3 \
        start=2026-03-01 increment="1 day"
    t.rast.accumulate input=warm output=warm_both basename=both \
        lower=low upper=high start=2026-03-01 cycle="6 days" \
        limits=10,30 method=bedd
    t.rast.list input=warm_both columns=name,max
    ```

    ```text
    name|max
    both_2026_03_01|4.0
    both_2026_03_02|12.0
    both_2026_03_03|18.0
    both_2026_03_04|38.0
    both_2026_03_05|50.0
    both_2026_03_06|52.0
    ```

    ```sh
    t.rast.accumulate input=warm output=warm_lower basename=lower \
        lower=low start=2026-03-01 cycle="6 days" limits=10,28 method=bedd
    t.rast.list input=warm_lower columns=name,max
    ```

    ```text
    name|max
    lower_2026_03_01|4.0
    lower_2026_03_02|12.0
    lower_2026_03_03|24.0
    lower_2026_03_04|42.0
    lower_2026_03_05|54.0
    lower_2026_03_06|56.0
    ```

    ```sh
    t.rast.accumulate input=warm output=warm_limits basename=limits \
        start=2026-03-01 cycle="6 days" limits=10,30 method=bedd
    t.rast.list input=warm_limits columns=name,max
    ```

    ```text
    name|max
    limits_2026_03_01|4.0
    limits_2026_03_02|14.0
    limits_2026_03_03|30.0
    limits_2026_03_04|50.0
    limits_2026_03_05|62.0
    limits_2026_03_06|64.0
    ```

=== "Python (grass.tools)"

    ```python
    for number, value in enumerate((14, 20, 26, 32, 22, 12), start=1):
        tools.r_mapcalc(expression=f"warm_{number} = {value}")
    for number in (1, 2, 3):
        tools.r_mapcalc(expression=f"low_{number} = {8 + 2 * number}")
        tools.r_mapcalc(expression=f"high_{number} = {35 - 5 * number}")
    tools.t_create(output="warm", title="Warm", description="Daily mean air temperature")
    tools.t_create(
        output="low", title="Lower", description="Lower limit of the accumulation"
    )
    tools.t_create(
        output="high", title="Upper", description="Upper limit of the accumulation"
    )
    tools.t_register(
        input="warm",
        maps=",".join(f"warm_{number}" for number in range(1, 7)),
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_register(
        input="low",
        maps="low_1,low_2,low_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_register(
        input="high",
        maps="high_1,high_2,high_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_accumulate(
        input="warm",
        output="warm_both",
        basename="both",
        lower="low",
        upper="high",
        start="2026-03-01",
        cycle="6 days",
        limits="10,30",
        method="bedd",
    )
    print(tools.t_rast_list(input="warm_both", columns="name,max").text)
    ```

    ```text
    name|max
    both_2026_03_01|4.0
    both_2026_03_02|12.0
    both_2026_03_03|18.0
    both_2026_03_04|38.0
    both_2026_03_05|50.0
    both_2026_03_06|52.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="warm",
        output="warm_lower",
        basename="lower",
        lower="low",
        start="2026-03-01",
        cycle="6 days",
        limits="10,28",
        method="bedd",
    )
    print(tools.t_rast_list(input="warm_lower", columns="name,max").text)
    ```

    ```text
    name|max
    lower_2026_03_01|4.0
    lower_2026_03_02|12.0
    lower_2026_03_03|24.0
    lower_2026_03_04|42.0
    lower_2026_03_05|54.0
    lower_2026_03_06|56.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="warm",
        output="warm_limits",
        basename="limits",
        start="2026-03-01",
        cycle="6 days",
        limits="10,30",
        method="bedd",
    )
    print(tools.t_rast_list(input="warm_limits", columns="name,max").text)
    ```

    ```text
    name|max
    limits_2026_03_01|4.0
    limits_2026_03_02|14.0
    limits_2026_03_03|30.0
    limits_2026_03_04|50.0
    limits_2026_03_05|62.0
    limits_2026_03_06|64.0
    ```

### Choose the granularity and the names of the maps

The granularity sets the length of the granules. On the dataset `ones`, the
granularity of two days puts two maps into each granule. Their mean is 1, so
one cycle of eight days gives four result maps with the sums 1, 2, 3 and 4,
each with the time of two days.

On the dataset `readings`, the granularity of 12 hours gives one granule for
each map. The default suffix `gran` follows the resolution of the input
dataset, which has intervals of 12 hours, so the names end with the date and the
hour. The option **suffix** selects another form: `time` adds the whole time of
the day, and `num` adds a number of five digits that counts the maps in the
order of the computation.

=== "Command line"

    ```sh
    t.rast.accumulate input=ones output=ones_two_days basename=two_days \
        start=2026-03-01 cycle="8 days" granularity="2 days" limits=10,30
    t.rast.list input=ones_two_days columns=name,start_time,end_time,max
    ```

    ```text
    name|start_time|end_time|max
    two_days_2026_03_01|2026-03-01 00:00:00|2026-03-03 00:00:00|1.0
    two_days_2026_03_03|2026-03-03 00:00:00|2026-03-05 00:00:00|2.0
    two_days_2026_03_05|2026-03-05 00:00:00|2026-03-07 00:00:00|3.0
    two_days_2026_03_07|2026-03-07 00:00:00|2026-03-09 00:00:00|4.0
    ```

    ```sh
    t.rast.accumulate input=readings output=readings_halves basename=half \
        start=2026-06-01 cycle="3 days" granularity="12 hours" limits=10,30
    t.rast.list input=readings_halves columns=name,start_time
    ```

    ```text
    name|start_time
    half_2026_06_01_00|2026-06-01 00:00:00
    half_2026_06_01_12|2026-06-01 12:00:00
    half_2026_06_02_00|2026-06-02 00:00:00
    half_2026_06_02_12|2026-06-02 12:00:00
    half_2026_06_03_00|2026-06-03 00:00:00
    half_2026_06_03_12|2026-06-03 12:00:00
    ```

    ```sh
    t.rast.accumulate input=readings output=readings_time basename=half \
        start=2026-06-01 cycle="3 days" granularity="12 hours" limits=10,30 \
        suffix=time
    t.rast.list input=readings_time columns=name
    ```

    ```text
    name
    half_2026_06_01T00_00_00
    half_2026_06_01T12_00_00
    half_2026_06_02T00_00_00
    half_2026_06_02T12_00_00
    half_2026_06_03T00_00_00
    half_2026_06_03T12_00_00
    ```

    ```sh
    t.rast.accumulate input=readings output=readings_num basename=half \
        start=2026-06-01 cycle="3 days" granularity="12 hours" limits=10,30 \
        suffix=num
    t.rast.list input=readings_num columns=name
    ```

    ```text
    name
    half_00001
    half_00002
    half_00003
    half_00004
    half_00005
    half_00006
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_accumulate(
        input="ones",
        output="ones_two_days",
        basename="two_days",
        start="2026-03-01",
        cycle="8 days",
        granularity="2 days",
        limits="10,30",
    )
    result = tools.t_rast_list(
        input="ones_two_days", columns="name,start_time,end_time,max"
    )
    print(result.text)
    ```

    ```text
    name|start_time|end_time|max
    two_days_2026_03_01|2026-03-01 00:00:00|2026-03-03 00:00:00|1.0
    two_days_2026_03_03|2026-03-03 00:00:00|2026-03-05 00:00:00|2.0
    two_days_2026_03_05|2026-03-05 00:00:00|2026-03-07 00:00:00|3.0
    two_days_2026_03_07|2026-03-07 00:00:00|2026-03-09 00:00:00|4.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="readings",
        output="readings_halves",
        basename="half",
        start="2026-06-01",
        cycle="3 days",
        granularity="12 hours",
        limits="10,30",
    )
    print(tools.t_rast_list(input="readings_halves", columns="name,start_time").text)
    ```

    ```text
    name|start_time
    half_2026_06_01_00|2026-06-01 00:00:00
    half_2026_06_01_12|2026-06-01 12:00:00
    half_2026_06_02_00|2026-06-02 00:00:00
    half_2026_06_02_12|2026-06-02 12:00:00
    half_2026_06_03_00|2026-06-03 00:00:00
    half_2026_06_03_12|2026-06-03 12:00:00
    ```

    ```python
    tools.t_rast_accumulate(
        input="readings",
        output="readings_time",
        basename="half",
        start="2026-06-01",
        cycle="3 days",
        granularity="12 hours",
        limits="10,30",
        suffix="time",
    )
    print(tools.t_rast_list(input="readings_time", columns="name").text)
    ```

    ```text
    name
    half_2026_06_01T00_00_00
    half_2026_06_01T12_00_00
    half_2026_06_02T00_00_00
    half_2026_06_02T12_00_00
    half_2026_06_03T00_00_00
    half_2026_06_03T12_00_00
    ```

    ```python
    tools.t_rast_accumulate(
        input="readings",
        output="readings_num",
        basename="half",
        start="2026-06-01",
        cycle="3 days",
        granularity="12 hours",
        limits="10,30",
        suffix="num",
    )
    print(tools.t_rast_list(input="readings_num", columns="name").text)
    ```

    ```text
    name
    half_00001
    half_00002
    half_00003
    half_00004
    half_00005
    half_00006
    ```

### Keep or remove empty maps

The dataset `gappy` has four daily maps. The first one has no value in any cell,
the second the value 3 everywhere. The third has no value in the first cell,
the fourth none in the second cell; the other cells hold 3. Cycles of two days
start on 1 and 3 March.

In the first cycle the first map is empty, so every cell is NULL in the first
step and stays NULL in the second one. Both result maps of the cycle are
empty. Without **-n** they are removed; the dataset `gaps_dropped` has two
maps. With **-n**, the dataset `gaps_kept` registers all four maps, the empty
ones with `None` as smallest and largest value.

In the second cycle the first cell is NULL in the first step and stays NULL in
the second one. The second cell is NULL in the second step and keeps the sum of
the first step, 3. The last cell holds 3 and 6. The `r.stats` blocks list the
cells of the two maps of the second cycle.

An empty result is warned about and creates no dataset. The last block runs
the same computation once more with **--overwrite** and the **stop** 3 March,
which leaves only the empty first cycle. The tool warns that no map with
values was computed and removes the existing dataset `gaps_dropped`; the
listing of the datasets whose names start with `gaps` shows that
`gaps_dropped` is gone and `gaps_kept` is still there.

=== "Command line"

    ```sh
    r.mapcalc expression="gap_1 = null()"
    r.mapcalc expression="gap_2 = 3"
    r.mapcalc expression="gap_3 = if(col() == 1, null(), 3)"
    r.mapcalc expression="gap_4 = if(col() == 2, null(), 3)"
    t.create output=gappy title="Gappy" description="Maps with NULL cells"
    t.register -i input=gappy maps=gap_1,gap_2,gap_3,gap_4 \
        start=2026-03-01 increment="1 day"
    t.rast.accumulate input=gappy output=gaps_dropped basename=dropped \
        start=2026-03-01 cycle="2 days" limits=10,30
    t.rast.list input=gaps_dropped columns=name,min,max
    ```

    ```text
    name|min|max
    dropped_2026_03_03|3.0|3.0
    dropped_2026_03_04|3.0|6.0
    ```

    ```sh
    t.rast.accumulate -n input=gappy output=gaps_kept basename=kept \
        start=2026-03-01 cycle="2 days" limits=10,30
    t.rast.list input=gaps_kept columns=name,min,max
    ```

    ```text
    name|min|max
    kept_2026_03_01|None|None
    kept_2026_03_02|None|None
    kept_2026_03_03|3.0|3.0
    kept_2026_03_04|3.0|6.0
    ```

    ```sh
    r.stats -1 input=dropped_2026_03_03 null_value=NULL
    r.stats -1 input=dropped_2026_03_04 null_value=NULL
    ```

    ```text
    NULL
    3
    3
    NULL
    3
    6
    ```

    ```sh
    t.rast.accumulate --overwrite input=gappy output=gaps_dropped \
        basename=dropped start=2026-03-01 stop=2026-03-03 cycle="2 days" \
        limits=10,30
    t.list type=strds columns=name where="name like 'gaps%'"
    ```

    ```text
    gaps_kept
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="gap_1 = null()")
    tools.r_mapcalc(expression="gap_2 = 3")
    tools.r_mapcalc(expression="gap_3 = if(col() == 1, null(), 3)")
    tools.r_mapcalc(expression="gap_4 = if(col() == 2, null(), 3)")
    tools.t_create(output="gappy", title="Gappy", description="Maps with NULL cells")
    tools.t_register(
        input="gappy",
        maps="gap_1,gap_2,gap_3,gap_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_accumulate(
        input="gappy",
        output="gaps_dropped",
        basename="dropped",
        start="2026-03-01",
        cycle="2 days",
        limits="10,30",
    )
    print(tools.t_rast_list(input="gaps_dropped", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    dropped_2026_03_03|3.0|3.0
    dropped_2026_03_04|3.0|6.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="gappy",
        output="gaps_kept",
        basename="kept",
        start="2026-03-01",
        cycle="2 days",
        limits="10,30",
        flags="n",
    )
    print(tools.t_rast_list(input="gaps_kept", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    kept_2026_03_01|None|None
    kept_2026_03_02|None|None
    kept_2026_03_03|3.0|3.0
    kept_2026_03_04|3.0|6.0
    ```

    ```python
    for name in ("dropped_2026_03_03", "dropped_2026_03_04"):
        print(tools.r_stats(input=name, flags="1", null_value="NULL").text)
    ```

    ```text
    NULL
    3
    3
    NULL
    3
    6
    ```

    ```python
    tools.t_rast_accumulate(
        input="gappy",
        output="gaps_dropped",
        basename="dropped",
        start="2026-03-01",
        stop="2026-03-03",
        cycle="2 days",
        limits="10,30",
        overwrite=True,
    )
    print(tools.t_list(type="strds", columns="name", where="name like 'gaps%'").text)
    ```

    ```text
    gaps_kept
    ```

### Accumulate with relative time

The dataset `model` has four steps of one hour with the values 2, 3, 4 and 5. With
relative time, **start**, **stop**, **cycle**, **offset** and **granularity**
are integers in the unit of the dataset, here hours. The first block uses
cycles of two steps with the method `gdd` and the lower limit 0, so the
increments are the values themselves: the sums are 2 and 5, then 4 and 9 after
the restart. The names of the maps end with a number.

The second block adds **offset** of one step. The first cycle holds the steps
from 0 to 2, the step from 2 to 3 is skipped, and the second cycle starts at 3:
the maps are `2`, `5` and `5`.

=== "Command line"

    ```sh
    for number in 1 2 3 4; do
        r.mapcalc expression="step_$number = $number + 1"
    done
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per hour"
    t.register -i input=model maps=step_1,step_2,step_3,step_4 \
        start=0 increment=1 unit=hours
    t.rast.accumulate input=model output=model_sum basename=sum start=0 \
        cycle=2 granularity=1 limits=0,10 method=gdd
    t.rast.list input=model_sum columns=name,start_time,end_time,max
    ```

    ```text
    name|start_time|end_time|max
    sum_00001|0|1|2.0
    sum_00002|1|2|5.0
    sum_00003|2|3|4.0
    sum_00004|3|4|9.0
    ```

    ```sh
    t.rast.accumulate input=model output=model_offset basename=offset \
        start=0 cycle=2 offset=1 granularity=1 limits=0,10 method=gdd
    t.rast.list input=model_offset columns=name,start_time,end_time,max
    ```

    ```text
    name|start_time|end_time|max
    offset_00001|0|1|2.0
    offset_00002|1|2|5.0
    offset_00003|3|4|5.0
    ```

=== "Python (grass.tools)"

    ```python
    for number in range(1, 5):
        tools.r_mapcalc(expression=f"step_{number} = {number} + 1")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per hour",
    )
    tools.t_register(
        input="model",
        maps="step_1,step_2,step_3,step_4",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.t_rast_accumulate(
        input="model",
        output="model_sum",
        basename="sum",
        start=0,
        cycle=2,
        granularity=1,
        limits="0,10",
        method="gdd",
    )
    result = tools.t_rast_list(input="model_sum", columns="name,start_time,end_time,max")
    print(result.text)
    ```

    ```text
    name|start_time|end_time|max
    sum_00001|0|1|2.0
    sum_00002|1|2|5.0
    sum_00003|2|3|4.0
    sum_00004|3|4|9.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="model",
        output="model_offset",
        basename="offset",
        start=0,
        cycle=2,
        offset=1,
        granularity=1,
        limits="0,10",
        method="gdd",
    )
    result = tools.t_rast_list(input="model_offset", columns="name,start_time,end_time,max")
    print(result.text)
    ```

    ```text
    name|start_time|end_time|max
    offset_00001|0|1|2.0
    offset_00002|1|2|5.0
    offset_00003|3|4|5.0
    ```

### Cycles of months

The dataset `pulses` has six time instants with the value 1 near the ends of
months in 2001: on 31 January, 27 and 28 February, 30 and 31 March and 1 April.
With the method `mean` the sum counts the maps of a cycle.

The first block uses monthly cycles from 31 January with the granularity of
one day. A month step that ends behind the last day of a shorter month ends on
that day, so the second cycle starts on 28 February and the third on 31
March. The sums are 1, 2 for each cycle. The granules without a map between
the instants have no result map.

The second block uses cycles of two months with the granularity of one month,
from 31 January. A start inside a month is moved to the first day of the
granularity, here 1 January, and the tool warns. The first cycle holds January
and February: the January granule holds one map, the February granule two, and
the mean of each is 1, so the sums are 1 and 2. The second cycle begins on
1 March and has the sums 1 and 2.

=== "Command line"

    ```sh
    t.create output=pulses title="Pulses" \
        description="Time instants near the ends of months"
    i=0
    for day in 2001-01-31 2001-02-27 2001-02-28 2001-03-30 2001-03-31 2001-04-01; do
        i=$((i + 1))
        r.mapcalc expression="pulse_$i = 1"
        t.register input=pulses maps=pulse_$i start=$day
    done
    t.rast.accumulate input=pulses output=pulses_days basename=days \
        start=2001-01-31 cycle="1 months" granularity="1 day" limits=10,30
    t.rast.list input=pulses_days columns=name,start_time,max
    ```

    ```text
    name|start_time|max
    days_2001_01_31|2001-01-31 00:00:00|1.0
    days_2001_02_27|2001-02-27 00:00:00|2.0
    days_2001_02_28|2001-02-28 00:00:00|1.0
    days_2001_03_30|2001-03-30 00:00:00|2.0
    days_2001_03_31|2001-03-31 00:00:00|1.0
    days_2001_04_01|2001-04-01 00:00:00|2.0
    ```

    ```sh
    t.rast.accumulate input=pulses output=pulses_months basename=months \
        start=2001-01-31 cycle="2 months" granularity="1 months" limits=10,30
    t.rast.list input=pulses_months columns=name,start_time,end_time,max
    ```

    ```text
    name|start_time|end_time|max
    months_2001_01_01|2001-01-01 00:00:00|2001-02-01 00:00:00|1.0
    months_2001_02_01|2001-02-01 00:00:00|2001-03-01 00:00:00|2.0
    months_2001_03_01|2001-03-01 00:00:00|2001-04-01 00:00:00|1.0
    months_2001_04_01|2001-04-01 00:00:00|2001-05-01 00:00:00|2.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_create(
        output="pulses",
        title="Pulses",
        description="Time instants near the ends of months",
    )
    days = ("2001-01-31", "2001-02-27", "2001-02-28", "2001-03-30", "2001-03-31")
    for number, day in enumerate((*days, "2001-04-01"), start=1):
        tools.r_mapcalc(expression=f"pulse_{number} = 1")
        tools.t_register(input="pulses", maps=f"pulse_{number}", start=day)
    tools.t_rast_accumulate(
        input="pulses",
        output="pulses_days",
        basename="days",
        start="2001-01-31",
        cycle="1 months",
        granularity="1 day",
        limits="10,30",
    )
    print(tools.t_rast_list(input="pulses_days", columns="name,start_time,max").text)
    ```

    ```text
    name|start_time|max
    days_2001_01_31|2001-01-31 00:00:00|1.0
    days_2001_02_27|2001-02-27 00:00:00|2.0
    days_2001_02_28|2001-02-28 00:00:00|1.0
    days_2001_03_30|2001-03-30 00:00:00|2.0
    days_2001_03_31|2001-03-31 00:00:00|1.0
    days_2001_04_01|2001-04-01 00:00:00|2.0
    ```

    ```python
    tools.t_rast_accumulate(
        input="pulses",
        output="pulses_months",
        basename="months",
        start="2001-01-31",
        cycle="2 months",
        granularity="1 months",
        limits="10,30",
    )
    result = tools.t_rast_list(
        input="pulses_months", columns="name,start_time,end_time,max"
    )
    print(result.text)
    ```

    ```text
    name|start_time|end_time|max
    months_2001_01_01|2001-01-01 00:00:00|2001-02-01 00:00:00|1.0
    months_2001_02_01|2001-02-01 00:00:00|2001-03-01 00:00:00|2.0
    months_2001_03_01|2001-03-01 00:00:00|2001-04-01 00:00:00|1.0
    months_2001_04_01|2001-04-01 00:00:00|2001-05-01 00:00:00|2.0
    ```

### Use datasets of another mapset

The input and the limit datasets can lie in another mapset, but the output is
created in the current one. The example creates the mapset `other` and
switches to it; the datasets `warm`, `low` and `high` stay in `PERMANENT` and
are named with their mapset. A new mapset takes its region from the default
region, so the example sets the region first. The result is the same as in the
fifth example with both limit datasets: the sums 4, 12, 18, 38, 50 and 52. The
first block shows that the maps are in `other`, the second that the dataset is.

=== "Command line"

    ```sh
    g.mapset -c mapset=other
    g.region n=1 s=0 e=3 w=0 res=1
    t.rast.accumulate input=warm@PERMANENT output=warm_other basename=other \
        lower=low@PERMANENT upper=high@PERMANENT start=2026-03-01 \
        cycle="6 days" limits=10,30 method=bedd
    t.rast.list input=warm_other columns=name,mapset,max
    ```

    ```text
    name|mapset|max
    other_2026_03_01|other|4.0
    other_2026_03_02|other|12.0
    other_2026_03_03|other|18.0
    other_2026_03_04|other|38.0
    other_2026_03_05|other|50.0
    other_2026_03_06|other|52.0
    ```

    ```sh
    t.list type=strds columns=name,mapset where="name = 'warm_other'"
    ```

    ```text
    warm_other|other
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="other", flags="c")
    tools.g_region(n=1, s=0, e=3, w=0, res=1)
    tools.t_rast_accumulate(
        input="warm@PERMANENT",
        output="warm_other",
        basename="other",
        lower="low@PERMANENT",
        upper="high@PERMANENT",
        start="2026-03-01",
        cycle="6 days",
        limits="10,30",
        method="bedd",
    )
    print(tools.t_rast_list(input="warm_other", columns="name,mapset,max").text)
    ```

    ```text
    name|mapset|max
    other_2026_03_01|other|4.0
    other_2026_03_02|other|12.0
    other_2026_03_03|other|18.0
    other_2026_03_04|other|38.0
    other_2026_03_05|other|50.0
    other_2026_03_06|other|52.0
    ```

    ```python
    result = tools.t_list(type="strds", columns="name,mapset", where="name = 'warm_other'")
    print(result.text)
    ```

    ```text
    warm_other|other
    ```

<!-- markdownlint-enable MD046 -->

## REFERENCES

- Jones, G.V., Duff, A.A., Hall, A., Myers, J.W., 2010. Spatial Analysis
  of Climate in Winegrape Growing Regions in the Western United States.
  Am. J. Enol. Vitic. 61, 313-326.

## SEE ALSO

*[g.mapsets](g.mapsets.md), [r.series.accumulate](r.series.accumulate.md),
[r.stats](r.stats.md), [t.list](t.list.md),
[t.rast.accdetect](t.rast.accdetect.md),
[t.rast.aggregate](t.rast.aggregate.md), [t.rast.list](t.rast.list.md),
[t.rast.mapcalc](t.rast.mapcalc.md), [t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
