## DESCRIPTION

*t.rast.accdetect* finds, in a space time raster dataset of accumulated values,
the maps and cells in which the accumulated value lies in a given range. The
input is the result of a run of
*[t.rast.accumulate](t.rast.accumulate.md)*, for instance the growing degree
days of a crop, and the range is, for instance, the sum at which the crop
germinates and the sum at which it is harvested. The tool writes two space
time raster datasets. The **occurrence** dataset tells when the sum was in the
range, and the optional **indicator** dataset marks the start, the course and
the end of every stretch of time in which it was. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets.

### Cycles

The tool works through the input dataset in cycles, as *t.rast.accumulate*
does, and restarts at the beginning of every cycle.

- **start** is the beginning of the first cycle and is required. With absolute
  time it is a date such as `2026-03-01`; with relative time it is an integer
  in the unit of the dataset.
- **cycle** is the length of a cycle, such as `12 months` or `4 days`, and is
  required. With relative time it is an integer.
- **offset** is a time that is skipped between the end of a cycle and the
  beginning of the next one. Maps that start in the skipped time are not used.
  Without **offset**, a cycle begins where the cycle before ended.
- **stop** ends the last cycle. A cycle that reaches beyond **stop** ends at
  **stop**, and a map that starts at **stop** or later is not used. Without
  **stop**, the run ends with the input dataset; a map that is a time instant
  at the end of the dataset is processed as well.

A map belongs to the cycle in which it starts. A cycle in which no map starts
is skipped. The **cycle** and the **offset** must be the ones that
*t.rast.accumulate* used for the input dataset; **start** and **stop** need not
be the same. Cycles and offsets in months or years are counted from **start**,
as in *t.rast.accumulate*, and a month step that ends behind the last day of a
month ends on that day, so monthly cycles from 2001-01-31 start on 2001-02-28
and 2001-03-31. If only one of **cycle** and **offset** is in months or years,
such as a cycle in months with an offset in days, each cycle starts one offset
after the end of the cycle before.

*t.rast.accumulate* moves its **start** to the beginning of its
**granularity**, a month to its first day, and *t.rast.accdetect* does not.
For the same cycles, give *t.rast.accdetect* the moved start.

### The range

A cell is in the range when its value is above the minimum and below the
maximum; the two bounds themselves are not in the range. The bounds come from
the options **minimum**, **maximum** and **range**:

- **range** takes two numbers, `min,max`, such as `range=480,730`. They are
  used for all cells and all maps for which no map of **minimum** or of
  **maximum** is found. A range with the bounds the wrong way round, such as
  `45,15`, finds nothing.
- **minimum** and **maximum** name space time raster datasets, which allow a
  different bound for each cell and each time. For example, to detect the
  germination (minimum) and the harvest (maximum) of different crops in
  Germany with growing degree days, the cells of the crops differ, and so do
  the bounds of one cell when the crops rotate. Both datasets must have the
  same temporal type as the input dataset.

The bound for a map of the input dataset is looked up by the temporal relation
of the map to the maps of the dataset **minimum** or **maximum**. First the
maps that have the time of the map are used. If there are none, the maps that
cover the time of the map are used, then the maps that overlap it at its start
or at its end, and last the maps that lie within it. The first map of the
first relation that has any map gives the bound; the maps of different
relations are never mixed. If no map is found, or the dataset is not given,
the bound comes from **range**. The tool refuses to start without **range**
unless both **minimum** and **maximum** are given, and it ends with a message
when a map of the input dataset has no bound at all.

### Output

The option **occurrence** names the new dataset and is required. For every
input map it has a map that has the time of the input map and holds, in each
cell in the range, the time from the beginning of the cycle to the start of
the input map, and null elsewhere. With absolute time the unit is days; with
relative time it is the unit of the dataset.

The option **indicator** names a second new dataset with the same maps. Its
cells hold one of three integers: `1` where a stretch of time in the range
starts, `2` while it goes on and `3` where it ends. The option **staend**
changes the three values, for instance `staend=10,20,30`; the default is
`1,2,3`. A cell that is null in the occurrence map is null in the indicator.
A stretch that is still going on at the last map of a cycle ends there, so
that map gets the end value. A stretch of a single map has no map to end it
after its start: it gets the start value only, never the end value. The same
holds for a map that is alone in its cycle.

The flag **-r** works through every cycle from its last map back, for an input
dataset that *t.rast.accumulate* made with its flag **-r**. The indicator then
starts a stretch at its last map in time and ends it at an earlier map; a
stretch that is still going on at the first map of the cycle ends there, so the
first map gets the end value. The occurrence still counts the time from the
beginning of the cycle, whatever the direction.

The maps in which no cell is in the range are empty. The flag **-n**
registers the empty maps in the output datasets; without it, they are removed.

The option **basename** is the beginning of the names of the new maps and is
required. The name of an occurrence map is the **basename**, an underscore
and the suffix, such as `occ_2026_03_02`. An indicator map has the word
`indicator` behind the **basename**, such as `occ_indicator_2026_03_02`.
The option **suffix** selects the suffix:

- `gran` (the default) takes, with absolute time, the start of the input map
  cut to the granularity of the input dataset, such as `2026_03_02`. An input
  dataset that has only a time instant has no granularity, and `gran` then
  gives the full start time like `time`. This description is for absolute
  time only.
- `time` takes the full start time, such as `2026_03_02T00_00_00`.
- `num` takes a number of five digits, from 1; `num%NN` takes NN digits, so
  `num%02` gives `01`. The numbers count the maps of each dataset in the order
  of the computation, over all cycles.

## NOTES

The new datasets and maps are created in the current mapset. The last example
reads an input dataset of another mapset, `input=gdd@t_rast_accdetect`. The
input and the datasets of **minimum** and **maximum** are read from any mapset
of the project that has a temporal database; a name without a mapset is searched
in the current mapset first, then in the search path (see
[Datasets of other mapsets](temporalintro.md#datasets-of-other-mapsets)).

An existing **occurrence** or **indicator** dataset stops the run before any
computation, unless **--overwrite** is set. A name with a dot is refused for a
new dataset before any map is made. A new map whose name is that of a map
that is registered elsewhere is refused with the message "Map `<name@mapset>`
is already registered in the temporal database, use overwrite flag to
overwrite"; with **--overwrite** the new map replaces it and leaves the other
dataset.

If no map with values is computed for an output, the tool warns, for example
"No map with values was computed in any cycle. No space time dataset `<name>`
was created.", and does not create that dataset. This happens when the cycles
lie before or after the data or in a gap, when a **stop** is not after the
**start** (such as a relative stop of 0), and when every map of the output is
empty and **-n** is not set. With **--overwrite**, an output dataset that
exists is removed in this case, and the tool warns again that it did so. The
maps of the removed dataset stay as maps, except for maps that have the name
of a new map, which the computation replaces and then removes. The first
two examples leave out the empty maps and the third one registers them. An empty
input dataset ends with a warning and creates no output.

Wrong input stops the tool with a message before anything is written:

- An **input**, **minimum** or **maximum** dataset that does not exist: "Space
  time raster dataset `<name@mapset>` not found".
- A **minimum** or **maximum** dataset of another temporal type than the
  input: "Temporal type of input strds and minimum strds must be equal".
- No **range** and a missing **minimum** or **maximum**: "You need to set the
  range to compute the occurrence space time raster dataset". A map of the
  input dataset that has no bound from the datasets and no **range** gives "No
  minimum map found for `<map>` and no range given", or the same for
  maximum.
- A **start** or **stop** that is not a date, such as "Invalid date `<garbage>`
  of the option `<start>`"; with relative time "The options start and stop must
  be integers". A **cycle** or **offset** that cannot be read: "Invalid cycle"
  or "Invalid offset".
- A **cycle** that does not move time forward: "The cycle must be longer than
  zero". An **offset** that moves the next cycle back to or before the start of
  the cycle: "The offset must not move the next cycle back to or before the
  start of this one".
- An unknown **suffix**: "Invalid suffix `<gram>`, use gran, time, num or
  num%NN".

With relative time, the unit of the dataset is the unit of **start**, **stop**,
**cycle** and **offset**; they are integers without a unit.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_accdetect` and sets the computational region
to North Carolina with cells of 1 km; the later examples work in this mapset
and region, and the last one in a second mapset. The first example applies the
tool to a heat sum; the others use small constant values, so that the sums and
the stretches of time can be recomputed by hand.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_accdetect -->

<!-- markdownlint-disable MD046 -->

### Find the development stage of a crop

A crop or an insect develops through a stage while the heat sum lies between two
values. The first block builds the monthly mean air temperature of 2020 in
degree Celsius over North Carolina, 12 maps with a computed pattern: warmer in
summer, colder with height and a little colder towards the north. The dataset
is generated, not measured. The block then accumulates the heat sum above
10 degrees Celsius with *[t.rast.accumulate](t.rast.accumulate.md)*, with one
cycle of 12 months. Its default granularity is one day, so the granularity of
one month is given; every month then adds its mean minus 10, when that is
positive, and the unit of the sum is degree months (about 30 degree days).
The tool *[t.rast.what](t.rast.what.md)* prints the temperature and the sum of
every month for three cells: in the Mountains (1407 m), in the Piedmont near
Raleigh (115 m) and on the coast (0 m), from left to right.

The second block detects the stage between 20 and 60 degree months, which is
about 600 to 1800 degree days. The bounds themselves are not in the range. The
maps of the **occurrence** dataset hold, in the cells in the range, the days
from 1 January to the start of the map, such as 152 for 1 June; the maps of
January to April have no cell in the range and are left out. The listing shows
that every map has one value. The **indicator** marks the first month of the
stage with 1, the months in between with 2 and the last month with 3. The
Piedmont cell is in the range from June to August (27.1, 42.7 and 57.4 degree
months) and has 1, 2 and 3. The coast cell passes the range in two months (33.9
and 51.4), has 1 and 3, and the cell in the Mountains never reaches 20.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_accdetect
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
    ```

    ```sh
    t.rast.accumulate input=temperature_monthly output=heat_sum \
        basename=heat_sum start=2020-01-01 cycle="12 months" \
        granularity="1 month" limits=10,30 method=gdd
    t.rast.what strds=temperature_monthly \
        coordinates=371500,317500,638500,220500,777500,100500 layout=col
    t.rast.what strds=heat_sum \
        coordinates=371500,317500,638500,220500,777500,100500 layout=col
    ```

    ```text
    2020-01-01 00:00:00|2020-02-01 00:00:00|-4.7|4.7|6.7
    2020-02-01 00:00:00|2020-03-01 00:00:00|-3.8|5.6|7.5
    2020-03-01 00:00:00|2020-04-01 00:00:00|-0.4|9|10.9
    2020-04-01 00:00:00|2020-05-01 00:00:00|4.7|14.1|16
    2020-05-01 00:00:00|2020-06-01 00:00:00|10|19.4|21.4
    2020-06-01 00:00:00|2020-07-01 00:00:00|14.3|23.6|25.6
    2020-07-01 00:00:00|2020-08-01 00:00:00|16.2|25.6|27.5
    2020-08-01 00:00:00|2020-09-01 00:00:00|15.4|24.7|26.7
    2020-09-01 00:00:00|2020-10-01 00:00:00|11.9|21.3|23.3
    2020-10-01 00:00:00|2020-11-01 00:00:00|6.9|16.2|18.2
    2020-11-01 00:00:00|2020-12-01 00:00:00|1.5|10.9|12.8
    2020-12-01 00:00:00|2021-01-01 00:00:00|-2.7|6.7|8.6
    2020-01-01 00:00:00|2020-02-01 00:00:00|0|0|0
    2020-02-01 00:00:00|2020-03-01 00:00:00|0|0|0
    2020-03-01 00:00:00|2020-04-01 00:00:00|0|0|0.9
    2020-04-01 00:00:00|2020-05-01 00:00:00|0|4.1|6.9
    2020-05-01 00:00:00|2020-06-01 00:00:00|0|13.5|18.3
    2020-06-01 00:00:00|2020-07-01 00:00:00|4.3|27.1|33.9
    2020-07-01 00:00:00|2020-08-01 00:00:00|10.5|42.7|51.4
    2020-08-01 00:00:00|2020-09-01 00:00:00|15.9|57.4|68.1
    2020-09-01 00:00:00|2020-10-01 00:00:00|17.8|68.7|81.4
    2020-10-01 00:00:00|2020-11-01 00:00:00|17.8|74.9|89.6
    2020-11-01 00:00:00|2020-12-01 00:00:00|17.8|75.8|92.4
    2020-12-01 00:00:00|2021-01-01 00:00:00|17.8|75.8|92.4
    ```

    ```sh
    t.rast.accdetect input=heat_sum occurrence=stage indicator=stage_ind \
        basename=stage start=2020-01-01 cycle="12 months" range=20,60
    t.rast.list input=stage columns=name,start_time,min,max
    t.rast.what strds=stage_ind \
        coordinates=371500,317500,638500,220500,777500,100500 layout=col
    ```

    ```text
    name|start_time|min|max
    stage_2020_05|2020-05-01 00:00:00|121.0|121.0
    stage_2020_06|2020-06-01 00:00:00|152.0|152.0
    stage_2020_07|2020-07-01 00:00:00|182.0|182.0
    stage_2020_08|2020-08-01 00:00:00|213.0|213.0
    stage_2020_09|2020-09-01 00:00:00|244.0|244.0
    stage_2020_10|2020-10-01 00:00:00|274.0|274.0
    stage_2020_11|2020-11-01 00:00:00|305.0|305.0
    stage_2020_12|2020-12-01 00:00:00|335.0|335.0
    2020-05-01 00:00:00|2020-06-01 00:00:00|*|*|*
    2020-06-01 00:00:00|2020-07-01 00:00:00|*|1|1
    2020-07-01 00:00:00|2020-08-01 00:00:00|*|2|3
    2020-08-01 00:00:00|2020-09-01 00:00:00|*|3|*
    2020-09-01 00:00:00|2020-10-01 00:00:00|*|*|*
    2020-10-01 00:00:00|2020-11-01 00:00:00|*|*|*
    2020-11-01 00:00:00|2020-12-01 00:00:00|*|*|*
    2020-12-01 00:00:00|2021-01-01 00:00:00|*|*|*
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    sites = [371500, 317500, 638500, 220500, 777500, 100500]
    tools.g_mapset(flags="c", mapset="t_rast_accdetect")
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
    ```

    ```python
    tools.t_rast_accumulate(
        input="temperature_monthly",
        output="heat_sum",
        basename="heat_sum",
        start="2020-01-01",
        cycle="12 months",
        granularity="1 month",
        limits=[10, 30],
        method="gdd",
    )
    print(
        tools.t_rast_what(strds="temperature_monthly", coordinates=sites, layout="col").text
    )
    print(tools.t_rast_what(strds="heat_sum", coordinates=sites, layout="col").text)
    ```

    ```text
    2020-01-01 00:00:00|2020-02-01 00:00:00|-4.7|4.7|6.7
    2020-02-01 00:00:00|2020-03-01 00:00:00|-3.8|5.6|7.5
    2020-03-01 00:00:00|2020-04-01 00:00:00|-0.4|9|10.9
    2020-04-01 00:00:00|2020-05-01 00:00:00|4.7|14.1|16
    2020-05-01 00:00:00|2020-06-01 00:00:00|10|19.4|21.4
    2020-06-01 00:00:00|2020-07-01 00:00:00|14.3|23.6|25.6
    2020-07-01 00:00:00|2020-08-01 00:00:00|16.2|25.6|27.5
    2020-08-01 00:00:00|2020-09-01 00:00:00|15.4|24.7|26.7
    2020-09-01 00:00:00|2020-10-01 00:00:00|11.9|21.3|23.3
    2020-10-01 00:00:00|2020-11-01 00:00:00|6.9|16.2|18.2
    2020-11-01 00:00:00|2020-12-01 00:00:00|1.5|10.9|12.8
    2020-12-01 00:00:00|2021-01-01 00:00:00|-2.7|6.7|8.6
    2020-01-01 00:00:00|2020-02-01 00:00:00|0|0|0
    2020-02-01 00:00:00|2020-03-01 00:00:00|0|0|0
    2020-03-01 00:00:00|2020-04-01 00:00:00|0|0|0.9
    2020-04-01 00:00:00|2020-05-01 00:00:00|0|4.1|6.9
    2020-05-01 00:00:00|2020-06-01 00:00:00|0|13.5|18.3
    2020-06-01 00:00:00|2020-07-01 00:00:00|4.3|27.1|33.9
    2020-07-01 00:00:00|2020-08-01 00:00:00|10.5|42.7|51.4
    2020-08-01 00:00:00|2020-09-01 00:00:00|15.9|57.4|68.1
    2020-09-01 00:00:00|2020-10-01 00:00:00|17.8|68.7|81.4
    2020-10-01 00:00:00|2020-11-01 00:00:00|17.8|74.9|89.6
    2020-11-01 00:00:00|2020-12-01 00:00:00|17.8|75.8|92.4
    2020-12-01 00:00:00|2021-01-01 00:00:00|17.8|75.8|92.4
    ```

    ```python
    tools.t_rast_accdetect(
        input="heat_sum",
        occurrence="stage",
        indicator="stage_ind",
        basename="stage",
        start="2020-01-01",
        cycle="12 months",
        range=[20, 60],
    )
    print(tools.t_rast_list(input="stage", columns="name,start_time,min,max").text)
    print(tools.t_rast_what(strds="stage_ind", coordinates=sites, layout="col").text)
    ```

    ```text
    name|start_time|min|max
    stage_2020_05|2020-05-01 00:00:00|121.0|121.0
    stage_2020_06|2020-06-01 00:00:00|152.0|152.0
    stage_2020_07|2020-07-01 00:00:00|182.0|182.0
    stage_2020_08|2020-08-01 00:00:00|213.0|213.0
    stage_2020_09|2020-09-01 00:00:00|244.0|244.0
    stage_2020_10|2020-10-01 00:00:00|274.0|274.0
    stage_2020_11|2020-11-01 00:00:00|305.0|305.0
    stage_2020_12|2020-12-01 00:00:00|335.0|335.0
    2020-05-01 00:00:00|2020-06-01 00:00:00|*|*|*
    2020-06-01 00:00:00|2020-07-01 00:00:00|*|1|1
    2020-07-01 00:00:00|2020-08-01 00:00:00|*|2|3
    2020-08-01 00:00:00|2020-09-01 00:00:00|*|3|*
    2020-09-01 00:00:00|2020-10-01 00:00:00|*|*|*
    2020-10-01 00:00:00|2020-11-01 00:00:00|*|*|*
    2020-11-01 00:00:00|2020-12-01 00:00:00|*|*|*
    2020-12-01 00:00:00|2021-01-01 00:00:00|*|*|*
    ```

### Follow the sums cell by cell

The next examples are time logic. The dataset `temperature_daily` has eight
daily maps from 1 to 8 March 2026 in degree Celsius. Each map holds the value
`base + 2 * (min(column, 3) - 1)` in a cell, so the first three cells of the
northern row, the ones that the listings show, differ by two, and all cells
further east have the value of the third. The base is 12, 14, 16 and 18 on the
days 1 to 4, and the same again on the days 5 to 8, so the data hold two cycles
of four days.

The first block accumulates growing degree days above 10 with
*[t.rast.accumulate](t.rast.accumulate.md)*, with one cycle of four days. The
increment of a day is its value minus 10, so the sums of the first cell are 2,
6, 12 and 20, those of the second cell 4, 10, 18 and 28, and those of the third
cell 6, 14, 24 and 36, in each cycle. The tool
*[t.rast.what](t.rast.what.md)* prints, for each map, the values of the three
cells from west to east, given by the coordinates of their centers.

The second block detects the sums in the range from 8 to 25 with the same
cycle. The **occurrence** dataset holds the days since the beginning of the
cycle. The first cell reaches 12 on the third day, which is day 2 counted from
0, and 20 on the day 3, so it has 2 and 3. The second cell has 10 and 18 on the
days 1 and 2, and the third cell 14 and 24. The sums 2, 4 and 6 of the first
day, and the cells above 25, are not in the range. The map of the first day of
each cycle is empty and not registered. The **indicator** marks the start with
1, the course with 2 and the end with 3: the second cell starts on day 1 and
ends on day 2, because its sum 28 on day 3 is above the range; the first cell
starts on day 2 and is still in the range on day 3, the last map of the cycle,
so this map gets the end value 3.

=== "Command line"

    ```sh
    for step in 1 2 3 4 5 6 7 8; do
        base=$(( 12 + 2 * ((step - 1) % 4) ))
        r.mapcalc expression="temperature_daily_2026_03_0$step = $base + 2 * (min(col(), 3) - 1)"
    done
    t.create output=temperature_daily title="Air temperature" \
        description="Daily mean air temperature in degree Celsius"
    t.register -i input=temperature_daily \
        maps=$(g.list type=raster pattern="temperature_daily_*" mapset=. separator=comma) \
        start=2026-03-01 increment="1 day"
    t.rast.accumulate input=temperature_daily output=gdd basename=gdd \
        start=2026-03-01 cycle="4 days" limits=10,30 method=gdd
    t.rast.what strds=gdd coordinates=124500,318500,125500,318500,126500,318500 layout=col
    ```

    ```text
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|4|6
    2026-03-02 00:00:00|2026-03-03 00:00:00|6|10|14
    2026-03-03 00:00:00|2026-03-04 00:00:00|12|18|24
    2026-03-04 00:00:00|2026-03-05 00:00:00|20|28|36
    2026-03-05 00:00:00|2026-03-06 00:00:00|2|4|6
    2026-03-06 00:00:00|2026-03-07 00:00:00|6|10|14
    2026-03-07 00:00:00|2026-03-08 00:00:00|12|18|24
    2026-03-08 00:00:00|2026-03-09 00:00:00|20|28|36
    ```

    ```sh
    t.rast.accdetect input=gdd occurrence=occ indicator=ind basename=occ \
        start=2026-03-01 cycle="4 days" range=8,25
    t.rast.what strds=occ coordinates=124500,318500,125500,318500,126500,318500 layout=col
    t.rast.what strds=ind coordinates=124500,318500,125500,318500,126500,318500 layout=col
    ```

    ```text
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|1|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|2|2
    2026-03-04 00:00:00|2026-03-05 00:00:00|3|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|*|1|1
    2026-03-07 00:00:00|2026-03-08 00:00:00|2|2|2
    2026-03-08 00:00:00|2026-03-09 00:00:00|3|*|*
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|1|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|3|3
    2026-03-04 00:00:00|2026-03-05 00:00:00|3|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|*|1|1
    2026-03-07 00:00:00|2026-03-08 00:00:00|1|3|3
    2026-03-08 00:00:00|2026-03-09 00:00:00|3|*|*
    ```

=== "Python (grass.tools)"

    ```python
    points = [124500, 318500, 125500, 318500, 126500, 318500]
    maps = []
    for step in range(1, 9):
        base = 12 + 2 * ((step - 1) % 4)
        tools.r_mapcalc(
            expression=f"temperature_daily_2026_03_{step:02d}"
            f" = {base} + 2 * (min(col(), 3) - 1)"
        )
        maps.append(f"temperature_daily_2026_03_{step:02d}")
    tools.t_create(
        output="temperature_daily",
        title="Air temperature",
        description="Daily mean air temperature in degree Celsius",
    )
    tools.t_register(
        input="temperature_daily",
        maps=",".join(maps),
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_accumulate(
        input="temperature_daily",
        output="gdd",
        basename="gdd",
        start="2026-03-01",
        cycle="4 days",
        limits=[10, 30],
        method="gdd",
    )
    print(tools.t_rast_what(strds="gdd", coordinates=points, layout="col").text)
    ```

    ```text
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|4|6
    2026-03-02 00:00:00|2026-03-03 00:00:00|6|10|14
    2026-03-03 00:00:00|2026-03-04 00:00:00|12|18|24
    2026-03-04 00:00:00|2026-03-05 00:00:00|20|28|36
    2026-03-05 00:00:00|2026-03-06 00:00:00|2|4|6
    2026-03-06 00:00:00|2026-03-07 00:00:00|6|10|14
    2026-03-07 00:00:00|2026-03-08 00:00:00|12|18|24
    2026-03-08 00:00:00|2026-03-09 00:00:00|20|28|36
    ```

    ```python
    tools.t_rast_accdetect(
        input="gdd",
        occurrence="occ",
        indicator="ind",
        basename="occ",
        start="2026-03-01",
        cycle="4 days",
        range=[8, 25],
    )
    print(tools.t_rast_what(strds="occ", coordinates=points, layout="col").text)
    print(tools.t_rast_what(strds="ind", coordinates=points, layout="col").text)
    ```

    ```text
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|1|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|2|2
    2026-03-04 00:00:00|2026-03-05 00:00:00|3|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|*|1|1
    2026-03-07 00:00:00|2026-03-08 00:00:00|2|2|2
    2026-03-08 00:00:00|2026-03-09 00:00:00|3|*|*
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|1|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|3|3
    2026-03-04 00:00:00|2026-03-05 00:00:00|3|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|*|1|1
    2026-03-07 00:00:00|2026-03-08 00:00:00|1|3|3
    2026-03-08 00:00:00|2026-03-09 00:00:00|3|*|*
    ```

### Choose the values of the indicator and keep the empty maps

The same detection with **staend** `10,20,30`, so the indicator holds 10 for
the start, 20 for the course and 30 for the end of a stretch. The flag **-n**
registers the maps in which no cell is in the range, the maps of 1 and 5 March,
in both datasets. The option **suffix** `num%02` numbers the maps from 01 to 08
instead of naming them after the date. The list shows the empty maps, which
have no smallest and no largest value, and the table the indicator, which is
the one of the previous example with the new values.

=== "Command line"

    ```sh
    t.rast.accdetect -n input=gdd occurrence=occ_all indicator=ind_all \
        basename=occ_all start=2026-03-01 cycle="4 days" range=8,25 \
        staend=10,20,30 suffix=num%02
    t.rast.list input=occ_all columns=name,start_time,min,max
    t.rast.what strds=ind_all coordinates=124500,318500,125500,318500,126500,318500 layout=col
    ```

    ```text
    name|start_time|min|max
    occ_all_01|2026-03-01 00:00:00|None|None
    occ_all_02|2026-03-02 00:00:00|1.0|1.0
    occ_all_03|2026-03-03 00:00:00|2.0|2.0
    occ_all_04|2026-03-04 00:00:00|3.0|3.0
    occ_all_05|2026-03-05 00:00:00|None|None
    occ_all_06|2026-03-06 00:00:00|1.0|1.0
    occ_all_07|2026-03-07 00:00:00|2.0|2.0
    occ_all_08|2026-03-08 00:00:00|3.0|3.0
    2026-03-01 00:00:00|2026-03-02 00:00:00|*|*|*
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|10|10
    2026-03-03 00:00:00|2026-03-04 00:00:00|10|30|30
    2026-03-04 00:00:00|2026-03-05 00:00:00|30|*|*
    2026-03-05 00:00:00|2026-03-06 00:00:00|*|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|*|10|10
    2026-03-07 00:00:00|2026-03-08 00:00:00|10|30|30
    2026-03-08 00:00:00|2026-03-09 00:00:00|30|*|*
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_accdetect(
        input="gdd",
        occurrence="occ_all",
        indicator="ind_all",
        basename="occ_all",
        start="2026-03-01",
        cycle="4 days",
        range=[8, 25],
        staend=[10, 20, 30],
        suffix="num%02",
        flags="n",
    )
    print(tools.t_rast_list(input="occ_all", columns="name,start_time,min,max").text)
    print(tools.t_rast_what(strds="ind_all", coordinates=points, layout="col").text)
    ```

    ```text
    name|start_time|min|max
    occ_all_01|2026-03-01 00:00:00|None|None
    occ_all_02|2026-03-02 00:00:00|1.0|1.0
    occ_all_03|2026-03-03 00:00:00|2.0|2.0
    occ_all_04|2026-03-04 00:00:00|3.0|3.0
    occ_all_05|2026-03-05 00:00:00|None|None
    occ_all_06|2026-03-06 00:00:00|1.0|1.0
    occ_all_07|2026-03-07 00:00:00|2.0|2.0
    occ_all_08|2026-03-08 00:00:00|3.0|3.0
    2026-03-01 00:00:00|2026-03-02 00:00:00|*|*|*
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|10|10
    2026-03-03 00:00:00|2026-03-04 00:00:00|10|30|30
    2026-03-04 00:00:00|2026-03-05 00:00:00|30|*|*
    2026-03-05 00:00:00|2026-03-06 00:00:00|*|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|*|10|10
    2026-03-07 00:00:00|2026-03-08 00:00:00|10|30|30
    2026-03-08 00:00:00|2026-03-09 00:00:00|30|*|*
    ```

### Detect backwards in time

*t.rast.accumulate* with its flag **-r** accumulates every cycle from the last
day to the first: the map of the last day holds the increment of one day and
the map of the first day the sum of all. The first cell has 20 on the first
day, 18 on the second, 14 on the third and 8 on the last. With the same range
from 8 to 25 and the flag **-r**, *t.rast.accdetect* works through the cycle
from the last map back. The first cell is not in the range on the last day
(8 is not above 8), starts on the third day (14), goes on the second day (18)
and ends on the first day (20), so its indicator is 1, 2 and 3 from the third
to the first day. The third cell starts on the last day (12), and ends on the
third day (22). The occurrence still counts the days from the beginning of the
cycle: 0 for the first day of the cycle.

=== "Command line"

    ```sh
    t.rast.accumulate -r input=temperature_daily output=gdd_back basename=gdd_back \
        start=2026-03-01 cycle="4 days" limits=10,30 method=gdd
    t.rast.what strds=gdd_back coordinates=124500,318500,125500,318500,126500,318500 layout=col
    ```

    ```text
    2026-03-01 00:00:00|2026-03-02 00:00:00|20|28|36
    2026-03-02 00:00:00|2026-03-03 00:00:00|18|24|30
    2026-03-03 00:00:00|2026-03-04 00:00:00|14|18|22
    2026-03-04 00:00:00|2026-03-05 00:00:00|8|10|12
    2026-03-05 00:00:00|2026-03-06 00:00:00|20|28|36
    2026-03-06 00:00:00|2026-03-07 00:00:00|18|24|30
    2026-03-07 00:00:00|2026-03-08 00:00:00|14|18|22
    2026-03-08 00:00:00|2026-03-09 00:00:00|8|10|12
    ```

    ```sh
    t.rast.accdetect -r input=gdd_back occurrence=occ_back \
        indicator=ind_back basename=occ_back start=2026-03-01 \
        cycle="4 days" range=8,25
    t.rast.what strds=occ_back coordinates=124500,318500,125500,318500,126500,318500 layout=col
    t.rast.what strds=ind_back coordinates=124500,318500,125500,318500,126500,318500 layout=col
    ```

    ```text
    2026-03-01 00:00:00|2026-03-02 00:00:00|0|*|*
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|1|*
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|2|2
    2026-03-04 00:00:00|2026-03-05 00:00:00|*|3|3
    2026-03-05 00:00:00|2026-03-06 00:00:00|0|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|1|1|*
    2026-03-07 00:00:00|2026-03-08 00:00:00|2|2|2
    2026-03-08 00:00:00|2026-03-09 00:00:00|*|3|3
    2026-03-01 00:00:00|2026-03-02 00:00:00|3|*|*
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|3|*
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|2|3
    2026-03-04 00:00:00|2026-03-05 00:00:00|*|1|1
    2026-03-05 00:00:00|2026-03-06 00:00:00|3|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|2|3|*
    2026-03-07 00:00:00|2026-03-08 00:00:00|1|2|3
    2026-03-08 00:00:00|2026-03-09 00:00:00|*|1|1
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_accumulate(
        input="temperature_daily",
        output="gdd_back",
        basename="gdd_back",
        start="2026-03-01",
        cycle="4 days",
        limits=[10, 30],
        method="gdd",
        flags="r",
    )
    print(tools.t_rast_what(strds="gdd_back", coordinates=points, layout="col").text)
    ```

    ```text
    2026-03-01 00:00:00|2026-03-02 00:00:00|20|28|36
    2026-03-02 00:00:00|2026-03-03 00:00:00|18|24|30
    2026-03-03 00:00:00|2026-03-04 00:00:00|14|18|22
    2026-03-04 00:00:00|2026-03-05 00:00:00|8|10|12
    2026-03-05 00:00:00|2026-03-06 00:00:00|20|28|36
    2026-03-06 00:00:00|2026-03-07 00:00:00|18|24|30
    2026-03-07 00:00:00|2026-03-08 00:00:00|14|18|22
    2026-03-08 00:00:00|2026-03-09 00:00:00|8|10|12
    ```

    ```python
    tools.t_rast_accdetect(
        input="gdd_back",
        occurrence="occ_back",
        indicator="ind_back",
        basename="occ_back",
        start="2026-03-01",
        cycle="4 days",
        range=[8, 25],
        flags="r",
    )
    print(tools.t_rast_what(strds="occ_back", coordinates=points, layout="col").text)
    print(tools.t_rast_what(strds="ind_back", coordinates=points, layout="col").text)
    ```

    ```text
    2026-03-01 00:00:00|2026-03-02 00:00:00|0|*|*
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|1|*
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|2|2
    2026-03-04 00:00:00|2026-03-05 00:00:00|*|3|3
    2026-03-05 00:00:00|2026-03-06 00:00:00|0|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|1|1|*
    2026-03-07 00:00:00|2026-03-08 00:00:00|2|2|2
    2026-03-08 00:00:00|2026-03-09 00:00:00|*|3|3
    2026-03-01 00:00:00|2026-03-02 00:00:00|3|*|*
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|3|*
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|2|3
    2026-03-04 00:00:00|2026-03-05 00:00:00|*|1|1
    2026-03-05 00:00:00|2026-03-06 00:00:00|3|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|2|3|*
    2026-03-07 00:00:00|2026-03-08 00:00:00|1|2|3
    2026-03-08 00:00:00|2026-03-09 00:00:00|*|1|1
    ```

### Skip time between the cycles and stop early

Cycles of three days with an **offset** of one day, and a **stop** at 7 March.
The first cycle covers 1 to 3 March, the offset skips 4 March, and the second
cycle begins on 5 March and ends at the **stop**, so it holds 5 and 6 March.
The accumulation uses the same **cycle** and **offset**. The occurrence of the
second cycle counts from 5 March, so the 6th is day 1. The maps of 1 and 5
March are empty. There is no map for 4 March, which the offset skipped, and
none from 7 March on.

=== "Command line"

    ```sh
    t.rast.accumulate input=temperature_daily output=gdd_skip basename=gdd_skip \
        start=2026-03-01 stop=2026-03-07 cycle="3 days" offset="1 day" \
        limits=10,30 method=gdd
    t.rast.accdetect input=gdd_skip occurrence=occ_skip basename=occ_skip \
        start=2026-03-01 stop=2026-03-07 cycle="3 days" offset="1 day" \
        range=8,25
    t.rast.what strds=occ_skip coordinates=124500,318500,125500,318500,126500,318500 layout=col
    ```

    ```text
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|1|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|2|2
    2026-03-06 00:00:00|2026-03-07 00:00:00|*|1|1
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_accumulate(
        input="temperature_daily",
        output="gdd_skip",
        basename="gdd_skip",
        start="2026-03-01",
        stop="2026-03-07",
        cycle="3 days",
        offset="1 day",
        limits=[10, 30],
        method="gdd",
    )
    tools.t_rast_accdetect(
        input="gdd_skip",
        occurrence="occ_skip",
        basename="occ_skip",
        start="2026-03-01",
        stop="2026-03-07",
        cycle="3 days",
        offset="1 day",
        range=[8, 25],
    )
    print(tools.t_rast_what(strds="occ_skip", coordinates=points, layout="col").text)
    ```

    ```text
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|1|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|2|2
    2026-03-06 00:00:00|2026-03-07 00:00:00|*|1|1
    ```

### Take the bounds from datasets

The dataset `lower` has one map with the value 15 from 5 to 9 March, and the
dataset `upper` one map with the value 20 from 1 to 9 March. Used as
**minimum** and **maximum**, they replace the range where a map is found: every
map of the input lies within the map of `upper`, so the upper bound is 20 for
all of them, and the maps of the second cycle lie within the map of `lower`,
so the lower bound is 15 there. The maps of the first cycle have no map of
`lower`, and take the lower bound 8 from **range**; the upper bound 25 of
**range** is not used. The bounds are not part of the range: the sum 20 of the
first cell is not below 20 and does not count. Compared with the detection of
the range from 8 to 25, the first cycle loses the sums 20 and 24, and the
second cycle all sums but 18, which is above 15: only the second cell on 7
March is left there.

The second block shows a map within the time of an input map. The dataset
`upper_noon` has one map with the value 20 from 6:00 to 18:00 on 3 March. It
lies within the granule of 3 March and gives the upper bound there; all other
maps take the upper bound 25 from **range**. The sum 24 of the third cell on
3 March is not below 20, but it is below 25 on 7 March.

=== "Command line"

    ```sh
    r.mapcalc expression="lower_second = 15"
    r.mapcalc expression="upper_all = 20"
    t.create output=lower title="Lower bound" \
        description="Lower bound of the second cycle"
    t.create output=upper title="Upper bound" \
        description="Upper bound of all cycles"
    t.register input=lower maps=lower_second start=2026-03-05 end=2026-03-09
    t.register input=upper maps=upper_all start=2026-03-01 end=2026-03-09
    t.rast.accdetect input=gdd minimum=lower maximum=upper \
        occurrence=occ_bounds basename=occ_bounds start=2026-03-01 \
        cycle="4 days" range=8,25
    t.rast.what strds=occ_bounds coordinates=124500,318500,125500,318500,126500,318500 layout=col
    ```

    ```text
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|1|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|2|*
    2026-03-07 00:00:00|2026-03-08 00:00:00|*|2|*
    ```

    ```sh
    r.mapcalc expression="upper_noon = 20"
    t.create output=upper_short title="Upper bound" \
        description="Upper bound within a day"
    t.register input=upper_short maps=upper_noon \
        start="2026-03-03 06:00:00" end="2026-03-03 18:00:00"
    t.rast.accdetect input=gdd maximum=upper_short occurrence=occ_noon \
        basename=occ_noon start=2026-03-01 cycle="4 days" range=8,25
    t.rast.what strds=occ_noon coordinates=124500,318500,125500,318500,126500,318500 layout=col
    ```

    ```text
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|1|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|2|*
    2026-03-04 00:00:00|2026-03-05 00:00:00|3|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|*|1|1
    2026-03-07 00:00:00|2026-03-08 00:00:00|2|2|2
    2026-03-08 00:00:00|2026-03-09 00:00:00|3|*|*
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="lower_second = 15")
    tools.r_mapcalc(expression="upper_all = 20")
    tools.t_create(
        output="lower",
        title="Lower bound",
        description="Lower bound of the second cycle",
    )
    tools.t_create(
        output="upper",
        title="Upper bound",
        description="Upper bound of all cycles",
    )
    tools.t_register(
        input="lower", maps="lower_second", start="2026-03-05", end="2026-03-09"
    )
    tools.t_register(input="upper", maps="upper_all", start="2026-03-01", end="2026-03-09")
    tools.t_rast_accdetect(
        input="gdd",
        minimum="lower",
        maximum="upper",
        occurrence="occ_bounds",
        basename="occ_bounds",
        start="2026-03-01",
        cycle="4 days",
        range=[8, 25],
    )
    print(tools.t_rast_what(strds="occ_bounds", coordinates=points, layout="col").text)
    ```

    ```text
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|1|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|2|*
    2026-03-07 00:00:00|2026-03-08 00:00:00|*|2|*
    ```

    ```python
    tools.r_mapcalc(expression="upper_noon = 20")
    tools.t_create(
        output="upper_short",
        title="Upper bound",
        description="Upper bound within a day",
    )
    tools.t_register(
        input="upper_short",
        maps="upper_noon",
        start="2026-03-03 06:00:00",
        end="2026-03-03 18:00:00",
    )
    tools.t_rast_accdetect(
        input="gdd",
        maximum="upper_short",
        occurrence="occ_noon",
        basename="occ_noon",
        start="2026-03-01",
        cycle="4 days",
        range=[8, 25],
    )
    print(tools.t_rast_what(strds="occ_noon", coordinates=points, layout="col").text)
    ```

    ```text
    2026-03-02 00:00:00|2026-03-03 00:00:00|*|1|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|2|*
    2026-03-04 00:00:00|2026-03-05 00:00:00|3|*|*
    2026-03-06 00:00:00|2026-03-07 00:00:00|*|1|1
    2026-03-07 00:00:00|2026-03-08 00:00:00|2|2|2
    2026-03-08 00:00:00|2026-03-09 00:00:00|3|*|*
    ```

### Detect in a dataset of another mapset

The new mapset `t_rast_accdetect_2` has no dataset of its own and starts with
the default region of the sample dataset, so the second command sets the region
as before. The input is named `gdd@t_rast_accdetect`, which needs no entry in the
search path; the new maps and the new dataset are created in
`t_rast_accdetect_2`, as the column `mapset` shows.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_accdetect_2
    g.region raster=elev_state_500m res=1000 -a
    t.rast.accdetect input=gdd@t_rast_accdetect occurrence=occ_copy \
        basename=occ_copy start=2026-03-01 cycle="4 days" range=8,25
    t.rast.list input=occ_copy columns=name,mapset,start_time
    ```

    ```text
    name|mapset|start_time
    occ_copy_2026_03_02|t_rast_accdetect_2|2026-03-02 00:00:00
    occ_copy_2026_03_03|t_rast_accdetect_2|2026-03-03 00:00:00
    occ_copy_2026_03_04|t_rast_accdetect_2|2026-03-04 00:00:00
    occ_copy_2026_03_06|t_rast_accdetect_2|2026-03-06 00:00:00
    occ_copy_2026_03_07|t_rast_accdetect_2|2026-03-07 00:00:00
    occ_copy_2026_03_08|t_rast_accdetect_2|2026-03-08 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(flags="c", mapset="t_rast_accdetect_2")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.t_rast_accdetect(
        input="gdd@t_rast_accdetect",
        occurrence="occ_copy",
        basename="occ_copy",
        start="2026-03-01",
        cycle="4 days",
        range=[8, 25],
    )
    print(tools.t_rast_list(input="occ_copy", columns="name,mapset,start_time").text)
    ```

    ```text
    name|mapset|start_time
    occ_copy_2026_03_02|t_rast_accdetect_2|2026-03-02 00:00:00
    occ_copy_2026_03_03|t_rast_accdetect_2|2026-03-03 00:00:00
    occ_copy_2026_03_04|t_rast_accdetect_2|2026-03-04 00:00:00
    occ_copy_2026_03_06|t_rast_accdetect_2|2026-03-06 00:00:00
    occ_copy_2026_03_07|t_rast_accdetect_2|2026-03-07 00:00:00
    occ_copy_2026_03_08|t_rast_accdetect_2|2026-03-08 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.region](g.region.md), [r.series.accumulate](r.series.accumulate.md),
[t.info](t.info.md), [t.rast.accumulate](t.rast.accumulate.md),
[t.rast.aggregate](t.rast.aggregate.md), [t.rast.list](t.rast.list.md),
[t.rast.mapcalc](t.rast.mapcalc.md), [t.rast.what](t.rast.what.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
