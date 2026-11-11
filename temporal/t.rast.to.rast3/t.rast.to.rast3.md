## DESCRIPTION

*t.rast.to.rast3* converts a space time raster dataset (STRDS) into a space
time voxel cube: a 3D raster map whose vertical axis is time. The maps of the
dataset become the layers of the cube, the earliest map at the bottom. The tool
puts the maps on top of each other with *[r.to.rast3](r.to.rast3.md)* and
registers the cube in the temporal database. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets.

The option **input** names the space time raster dataset, the option **output**
the new 3D raster map. Both are required. The tool prints nothing to the
standard output. The cube gets the title "Space time voxel cube" and a
description that says it was made with *t.rast.to.rast3*; *[r3.info](r3.info.md)*
shows both.

**Layers.** The granularity of the dataset, as *[t.info](t.info.md)* reports
it, is the thickness of a layer. For maps with an interval, the tool cuts the
time from the start of the first map to the end of the last map into steps of
this size and makes one layer for each step. A step that a map covers gets that
map. A map that is longer than the granularity covers several steps and is
copied into each of them; the third example shows a map of two days in two
layers. A step in which no map is registered, a gap of the dataset, becomes a
layer without values (null cells). The layers run from the bottom upwards in
the order of time. A time instant has no end; it gets one layer that starts at
its time, so the cube of a dataset of time instants ends one granularity after
the last instant, as the eighth example shows. A monthly series from the last
day of a month (January 31, February 28, March 31) has the granularity of one
month, so its cube has a layer per month. The maps of the dataset must not
overlap, include each other or have the same time: the tool refuses such a
dataset before it writes anything.

**Horizontal extent and resolution.** The cube covers the current
computational region. Its resolution in the horizontal plane is the 3D
resolution of the region, **res3** of *[g.region](g.region.md)*, not the 2D
resolution **res**; the sixth example sets a coarser **res3**. The tool sets the
vertical extent of the cube itself, from the dataset, in a temporary region
and leaves the current region as it is.

**Data type.** All maps of the dataset must have the same data type, `CELL`,
`FCELL` or `DCELL`. The cube has `DCELL` for maps of type `CELL` and for maps
of type `DCELL`, `FCELL` for maps of type `FCELL`. The layers of gaps have the
same type. A dataset with maps of different types is refused, as the ninth
example shows.

**Vertical axis.** The bottom of the cube, its resolution and its vertical
unit depend on the temporal type and the granularity of the dataset:

- Years: the bottom is the year number counted from 1900, `2026 - 1900 = 126`
  for a dataset that starts in 2026. The resolution is the granularity in
  years and the vertical unit is `years`.
- Months: the bottom is the month number counted from January 1900, `(year -
  1900) * 12 + month`, so `1515` for March 2026. The resolution is the
  granularity in months and the vertical unit is `months`.
- Days, hours, minutes and seconds: the bottom is the start of the dataset as
  the number of days since 1900-01-01 00:00:00, a decimal number, `46080` for
  March 1, 2026. The resolution is the granularity converted to days, `0.5`
  for twelve hours. The vertical unit is `days` for all four granularities,
  because bottom and resolution are counted in days.
- Relative time: the start of the dataset, its granularity and its unit are
  taken as they are, so the cube of a dataset in hours has the vertical unit
  `hours`.

The reference time 1900-01-01 00:00:00 is the same for all cubes. This allows
the alignment of cubes with different granularities. Cubes with the unit
`days` and cubes with the unit `months` or `years` do not share an axis.

The cube is registered as a 3D raster map in the temporal database, with the
temporal type of the dataset and the start and end time of the dataset as its
time stamp. For a dataset of time instants, the end is one granularity after
the last instant, where the top of the cube is. *[t.info](t.info.md)* with
`type=raster_3d` shows it. To convert only
some maps, select them into a dataset of their own with
*[t.rast.extract](t.rast.extract.md)*, as the seventh example shows.

## NOTES

The tool refuses to run in these cases and writes a message:

- The dataset has no maps: "Space time raster dataset `<name@mapset>` is
  empty".
- The dataset does not exist: "Space time dataset `<name>` of type `<strds>`
  not found".
- The dataset holds a single time instance and so has no granularity to make
  layers of: "Space time dataset `<name@mapset>` has no granularity, for
  example because it holds a single time instance", in absolute and in
  relative time.
- The cube exists and **--overwrite** is not given: "`<name>` exists. To
  overwrite, use the --overwrite flag". With **--overwrite** the tool replaces
  the cube and its entry in the temporal database; the fourth example shows it.
- The maps overlap, include each other or have the same time: "The maps of the
  space time raster dataset `<name@mapset>` overlap, include each other or have
  the same time, so a layer cannot be assigned to one of them. See t.topology."
  The check is that of *[t.topology](t.topology.md)*; a dataset with one map
  passes.
- The maps have different data types: "Input maps have to be from the same
  type. CELL, FCELL or DCELL!", followed by "Unable to create 3D raster map
  `<name>`".
- A map of the dataset is gone from the mapset: "Unable to create 3D raster
  map `<name>`". The cube is not made.

The cube of three daily instants has three layers and spans three days, and
its time stamp in the temporal database ends three days after the start, one
granularity after the last instant. The same holds for a series of instants in
months and for one in relative time.

The gaps are filled with a temporary map of null cells. The tool removes it
when it is done, also when it stops with a message.

Every layer has the thickness of the granularity. A dataset of long maps with
one short map or one short gap has a small granularity and so a cube with many
layers: the layers of the third example are one day thick although one map
is two days long.

A dataset of another mapset (`input=name@mapset`) is read like one of the
current mapset. The 3D raster map is created in the current mapset.

### Displaying the cube

To look at the cube, set the region to it with `g.region raster_3d=<cube>`, as
the first example shows. The 3D view mode of the
*[wxGUI](wxGUI.nviz.md)* shows the cube within this region. The cell
size in the vertical direction is a time span (years, months or days), the
cells in the horizontal direction are in the length unit of the project, often
meters, so the cube looks flat or extremely tall unless the **vertical
exaggeration** of the 3D view is set for the unit of the time axis. Show slices
first, since they show the values of single layers, and try isosurfaces
afterwards.

### Management of open file limits

*r.to.rast3* opens all maps of the dataset at the same time, so the number of
maps that the tool can stack is limited by the per-user limit of open files of
the operating system. With more maps, the tool stops with "Too many open
files" from *r.to.rast3* and "Unable to create 3D raster map" and makes no
cube. The soft limit can be raised with `ulimit -n 4096` (UNIX-based operating
systems) up to the hard limit. If the hard limit is too low, a superuser can
raise it with an entry in `/etc/security/limits.conf`:

```sh
# <domain>      <type>  <item>         <value>
your_username  hard    nofile          4096
```

The overall limit of the operating system is in `/proc/sys/fs/file-max`; on
modern Linux systems it is several 100,000 files.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_to_rast3`, sets the computational region to
North Carolina with cells of 1 km, also in 3D (**res3**, the resolution the
cube uses), and stacks a series of monthly air temperatures into a cube. The
later examples work in this mapset. They show how the tool builds the time
axis and the layers, which takes small maps: a window of 3 columns and 2 rows
of 1 km cells in North Carolina, so that the cells of a cube fit on the page.
The maps are made with *r.mapcalc*; their values are generated for the
examples and are not measurements.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_to_rast3 -->

<!-- markdownlint-disable MD046 -->

### Stack monthly air temperatures into a cube

The series `temperature_monthly` holds the monthly mean air temperature of 2020
over North Carolina in degrees Celsius, generated from the elevation model:
cooler in the mountains, warmest in July. The first block makes the mapset, the
region and the twelve maps, registers them as monthly intervals, and makes the
cube `temperature_cube`. The second block prints the properties of the 3D map
that *r3.info* reports with **-g**. The cube has the 839 columns and 335 rows
of the region and twelve layers, one for each month. It starts at month 1441
(January 2020, `(2020 - 1900) * 12 + 1`), each layer is one month thick, and
the vertical unit is `months`. The data type is `DCELL` like the maps.

The third block prints the time stamp of the cube from the temporal database.
The fourth block sets the region to the lowest layer of the cube, the month
January, and prints the smallest and the largest value of the cube there with
*r3.univar*, then the same for the layer of July, month 1447. The fifth block
sets the region to the whole cube with **raster_3d** and prints its top,
bottom, vertical resolution and number of layers, which is the region to
display the cube in. The layers lie in the order of time, the earliest at the
bottom. By the formula of the generated series, January is the coldest and
July the warmest month.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_to_rast3
    g.region raster=elev_state_500m res=1000 res3=1000 -a
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
    t.rast.to.rast3 input=temperature_monthly output=temperature_cube
    ```

    ```sh
    r3.info -g temperature_cube | grep -E "^(bottom|top|tbres|rows|cols|depths|datatype|vertical_units)="
    ```

    ```text
    bottom=1441
    top=1453
    tbres=1
    rows=335
    cols=839
    depths=12
    datatype="DCELL"
    vertical_units="months"
    ```

    ```sh
    t.info -g type=raster_3d input=temperature_cube | grep -E "^(temporal_type|start_time|end_time)="
    ```

    ```text
    temporal_type=absolute
    start_time='2020-01-01 00:00:00'
    end_time='2021-01-01 00:00:00'
    ```

    ```sh
    for layer in 1441 1447; do
        g.region raster_3d=temperature_cube b=$layer t=$((layer + 1))
        r3.univar -g map=temperature_cube | grep -E "^(min|max)="
    done
    ```

    ```text
    min=-7
    max=7.5
    min=13.9
    max=28.4
    ```

    ```sh
    g.region raster_3d=temperature_cube
    g.region -3 -g | grep -E "^(b|t|tbres|depths)="
    ```

    ```text
    t=1453
    b=1441
    tbres=1
    depths=12
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()


    def print_keys(result, *keys):
        for key in keys:
            print(f"{key}={result.keyval[key]}")


    tools.g_mapset(flags="c", mapset="t_rast_to_rast3")
    tools.g_region(raster="elev_state_500m", res=1000, res3=1000, flags="a")
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
    tools.t_rast_to_rast3(input="temperature_monthly", output="temperature_cube")
    ```

    ```python
    print_keys(
        tools.r3_info(map="temperature_cube", flags="g"),
        "bottom",
        "top",
        "tbres",
        "rows",
        "cols",
        "depths",
        "datatype",
        "vertical_units",
    )
    ```

    ```text
    bottom=1441
    top=1453
    tbres=1
    rows=335
    cols=839
    depths=12
    datatype="DCELL"
    vertical_units="months"
    ```

    ```python
    result = tools.t_info(type="raster_3d", input="temperature_cube", flags="g")
    print_keys(result, "temporal_type", "start_time", "end_time")
    ```

    ```text
    temporal_type=absolute
    start_time='2020-01-01 00:00:00'
    end_time='2021-01-01 00:00:00'
    ```

    ```python
    for layer in (1441, 1447):
        tools.g_region(raster_3d="temperature_cube", b=layer, t=layer + 1)
        print_keys(tools.r3_univar(map="temperature_cube", flags="g"), "min", "max")
    ```

    ```text
    min=-7
    max=7.5
    min=13.9
    max=28.4
    ```

    ```python
    tools.g_region(raster_3d="temperature_cube")
    print_keys(tools.g_region(flags="3g"), "t", "b", "tbres", "depths")
    ```

    ```text
    t=1453
    b=1441
    tbres=1
    depths=12
    ```

### Stack the maps of a dataset

The dataset `daily` holds three daily maps of 2 rows and 3 columns, from March
1, 2026. The value of a cell is `10 * row() + col()` plus 100 for the second
and 200 for the third map, so the north row of the first map is 11, 12, 13.
The first block makes the cube and prints the properties of the 3D map that
*r3.info* reports with **-g**. The cube starts at day 46080 since 1900-01-01
(March 1, 2026), is three layers thick, has the resolution 1 and the vertical
unit `days`. The data type is `DCELL` although the maps have integer values.

The second block prints the time stamp of the cube from the temporal database:
the start of the first and the end of the last map. The third block prints the
cells of the cube with *r3.out.ascii* (**-h** leaves out its header). The
region is set to the cube first. The output holds the rows of the bottom layer
first, north row first, then those of the second layer and the third.

=== "Command line"

    ```sh
    g.region n=202000 s=200000 e=603000 w=600000 res=1000 res3=1000
    r.mapcalc expression="day_1 = 10 * row() + col()"
    r.mapcalc expression="day_2 = 100 + 10 * row() + col()"
    r.mapcalc expression="day_3 = 200 + 10 * row() + col()"
    t.create output=daily title="Daily" description="Three daily maps"
    t.register -i input=daily maps=day_1,day_2,day_3 start=2026-03-01 increment="1 day"
    t.rast.to.rast3 input=daily output=daily_cube
    r3.info -g daily_cube | grep -E "^(bottom|top|tbres|depths|datatype|vertical_units)="
    ```

    ```text
    bottom=46080
    top=46083
    tbres=1
    depths=3
    datatype="DCELL"
    vertical_units="days"
    ```

    ```sh
    t.info -g type=raster_3d input=daily_cube | grep -E "^(temporal_type|start_time|end_time)="
    ```

    ```text
    temporal_type=absolute
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-04 00:00:00'
    ```

    ```sh
    g.region raster_3d=daily_cube
    r3.out.ascii input=daily_cube precision=0 -h | sed 's/ *$//'
    ```

    ```text
    11 12 13
    21 22 23
    111 112 113
    121 122 123
    211 212 213
    221 222 223
    ```

=== "Python (grass.tools)"

    ```python
    def print_layers(result):
        print("\n".join(line.rstrip() for line in result.text.splitlines()))


    tools.g_region(n=202000, s=200000, e=603000, w=600000, res=1000, res3=1000)
    for step in range(3):
        tools.r_mapcalc(expression=f"day_{step + 1} = {100 * step} + 10 * row() + col()")
    tools.t_create(output="daily", title="Daily", description="Three daily maps")
    tools.t_register(
        input="daily",
        maps="day_1,day_2,day_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_to_rast3(input="daily", output="daily_cube")
    print_keys(
        tools.r3_info(map="daily_cube", flags="g"),
        "bottom",
        "top",
        "tbres",
        "depths",
        "datatype",
        "vertical_units",
    )
    ```

    ```text
    bottom=46080
    top=46083
    tbres=1
    depths=3
    datatype="DCELL"
    vertical_units="days"
    ```

    ```python
    result = tools.t_info(type="raster_3d", input="daily_cube", flags="g")
    print_keys(result, "temporal_type", "start_time", "end_time")
    ```

    ```text
    temporal_type=absolute
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-04 00:00:00'
    ```

    ```python
    tools.g_region(raster_3d="daily_cube")
    print_layers(tools.r3_out_ascii(input="daily_cube", precision=0, flags="h"))
    ```

    ```text
    11 12 13
    21 22 23
    111 112 113
    121 122 123
    211 212 213
    221 222 223
    ```

### Gaps, long maps and the data type

The dataset `cover` holds a map of one day (March 1) and a map of two days
(March 3 and 4) with the data type `FCELL`; March 2 has no map. Its granularity
is one day, so the cube has four layers. The first layer is the first map. The
second, the gap, has no values, the cells show as `*`. The map of two days is
in the third and the fourth layer. The cube has the type `FCELL` of the maps.
The last block lists the raster maps of the mapset except the temperatures of
the first example: besides the maps of the examples there is no temporary map,
the tool removed the one it made for the gap.

=== "Command line"

    ```sh
    g.region n=202000 s=200000 e=603000 w=600000 res=1000 res3=1000
    r.mapcalc expression="cover_1 = float(10 * row() + col())"
    r.mapcalc expression="cover_2 = float(120 + 10 * row() + col())"
    t.create output=cover title="Cover" description="A gap and a long map"
    t.register input=cover maps=cover_1 start=2026-03-01 end=2026-03-02
    t.register input=cover maps=cover_2 start=2026-03-03 end=2026-03-05
    t.rast.to.rast3 input=cover output=cover_cube
    r3.info -g cover_cube | grep -E "^(bottom|top|tbres|depths|datatype)="
    g.region raster_3d=cover_cube
    r3.out.ascii input=cover_cube precision=0 -h | sed 's/ *$//'
    ```

    ```text
    bottom=46080
    top=46084
    tbres=1
    depths=4
    datatype="FCELL"
    11 12 13
    21 22 23
    * * *
    * * *
    131 132 133
    141 142 143
    131 132 133
    141 142 143
    ```

    ```sh
    g.list type=raster exclude="temperature_*" mapset=.
    ```

    ```text
    cover_1
    cover_2
    day_1
    day_2
    day_3
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=202000, s=200000, e=603000, w=600000, res=1000, res3=1000)
    tools.r_mapcalc(expression="cover_1 = float(10 * row() + col())")
    tools.r_mapcalc(expression="cover_2 = float(120 + 10 * row() + col())")
    tools.t_create(output="cover", title="Cover", description="A gap and a long map")
    tools.t_register(input="cover", maps="cover_1", start="2026-03-01", end="2026-03-02")
    tools.t_register(input="cover", maps="cover_2", start="2026-03-03", end="2026-03-05")
    tools.t_rast_to_rast3(input="cover", output="cover_cube")
    print_keys(
        tools.r3_info(map="cover_cube", flags="g"),
        "bottom",
        "top",
        "tbres",
        "depths",
        "datatype",
    )
    tools.g_region(raster_3d="cover_cube")
    print_layers(tools.r3_out_ascii(input="cover_cube", precision=0, flags="h"))
    ```

    ```text
    bottom=46080
    top=46084
    tbres=1
    depths=4
    datatype="FCELL"
    11 12 13
    21 22 23
    * * *
    * * *
    131 132 133
    141 142 143
    131 132 133
    141 142 143
    ```

    ```python
    print(tools.g_list(type="raster", exclude="temperature_*", mapset=".").text)
    ```

    ```text
    cover_1
    cover_2
    day_1
    day_2
    day_3
    ```

### Replace a cube after the dataset changed

The map `cover_gap` has the values 61, 62, 63 and 71, 72, 73. It is registered
for March 2, the gap of the dataset `cover`. The cube `cover_cube` exists
already, so the tool needs **--overwrite** (`overwrite=True` in Python) to
replace it. The new cube has no gap: its second layer is the new map.

=== "Command line"

    ```sh
    g.region n=202000 s=200000 e=603000 w=600000 res=1000 res3=1000
    r.mapcalc expression="cover_gap = float(50 + 10 * row() + col())"
    t.register input=cover maps=cover_gap start=2026-03-02 end=2026-03-03
    t.rast.to.rast3 input=cover output=cover_cube --overwrite
    g.region raster_3d=cover_cube
    r3.out.ascii input=cover_cube precision=0 -h | sed 's/ *$//'
    ```

    ```text
    11 12 13
    21 22 23
    61 62 63
    71 72 73
    131 132 133
    141 142 143
    131 132 133
    141 142 143
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=202000, s=200000, e=603000, w=600000, res=1000, res3=1000)
    tools.r_mapcalc(expression="cover_gap = float(50 + 10 * row() + col())")
    tools.t_register(input="cover", maps="cover_gap", start="2026-03-02", end="2026-03-03")
    tools.t_rast_to_rast3(input="cover", output="cover_cube", overwrite=True)
    tools.g_region(raster_3d="cover_cube")
    print_layers(tools.r3_out_ascii(input="cover_cube", precision=0, flags="h"))
    ```

    ```text
    11 12 13
    21 22 23
    61 62 63
    71 72 73
    131 132 133
    141 142 143
    131 132 133
    141 142 143
    ```

### The granularity sets the vertical unit

Three datasets of two maps each, with different granularities. `hourly` has
maps of twelve hours from March 1, 2026, 12:00. Its cube starts at day 46080.5
and has the resolution 0.5, both in days, the vertical unit is `days`.
`monthly` has two maps of one month from March 2026; its cube starts at month
1515 and has the unit `months`. `yearly` has two maps of one year from 2026; its
cube starts at year 126 and has the unit `years`.

=== "Command line"

    ```sh
    g.region n=202000 s=200000 e=603000 w=600000 res=1000 res3=1000
    for name in hourly monthly yearly; do
        r.mapcalc expression="${name}_1 = 1"
        r.mapcalc expression="${name}_2 = 2"
        t.create output=$name title="$name" description="Two maps"
    done
    t.register -i input=hourly maps=hourly_1,hourly_2 start="2026-03-01 12:00:00" increment="12 hours"
    t.register -i input=monthly maps=monthly_1,monthly_2 start=2026-03-01 increment="1 month"
    t.register -i input=yearly maps=yearly_1,yearly_2 start=2026-01-01 increment="1 year"
    for name in hourly monthly yearly; do
        t.rast.to.rast3 input=$name output=${name}_cube
        echo "$name"
        r3.info -g ${name}_cube | grep -E "^(bottom|top|tbres|depths|vertical_units)="
    done
    ```

    ```text
    hourly
    bottom=46080.5
    top=46081.5
    tbres=0.5
    depths=2
    vertical_units="days"
    monthly
    bottom=1515
    top=1517
    tbres=1
    depths=2
    vertical_units="months"
    yearly
    bottom=126
    top=128
    tbres=1
    depths=2
    vertical_units="years"
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=202000, s=200000, e=603000, w=600000, res=1000, res3=1000)
    starts = {
        "hourly": ("2026-03-01 12:00:00", "12 hours"),
        "monthly": ("2026-03-01", "1 month"),
        "yearly": ("2026-01-01", "1 year"),
    }
    for name, (start, increment) in starts.items():
        tools.r_mapcalc(expression=f"{name}_1 = 1")
        tools.r_mapcalc(expression=f"{name}_2 = 2")
        tools.t_create(output=name, title=name, description="Two maps")
        tools.t_register(
            input=name,
            maps=f"{name}_1,{name}_2",
            start=start,
            increment=increment,
            flags="i",
        )
    for name in starts:
        tools.t_rast_to_rast3(input=name, output=f"{name}_cube")
        print(name)
        print_keys(
            tools.r3_info(map=f"{name}_cube", flags="g"),
            "bottom",
            "top",
            "tbres",
            "depths",
            "vertical_units",
        )
    ```

    ```text
    hourly
    bottom=46080.5
    top=46081.5
    tbres=0.5
    depths=2
    vertical_units="days"
    monthly
    bottom=1515
    top=1517
    tbres=1
    depths=2
    vertical_units="months"
    yearly
    bottom=126
    top=128
    tbres=1
    depths=2
    vertical_units="years"
    ```

### Relative time and a coarser horizontal resolution

The dataset `model` has relative time. Its two maps cover the hours 10 to 15
and 15 to 20 on a region of 4 rows and 4 columns. The cube takes start,
granularity and unit as they are: it starts at 10, its resolution is 5 and the
unit is `hours`. The 3D resolution of the region is 2, so the cube has 2 rows
and 2 columns, although the maps have 4 each. The block after the cube shows
the time stamp of the cube in the temporal database.

=== "Command line"

    ```sh
    g.region n=204000 s=200000 e=604000 w=600000 res=1000 res3=2000
    r.mapcalc expression="model_1 = 1"
    r.mapcalc expression="model_2 = 2"
    t.create output=model temporaltype=relative title="Model" description="Two steps"
    t.register -i input=model maps=model_1,model_2 start=10 increment=5 unit=hours
    t.rast.to.rast3 input=model output=model_cube
    r3.info -g model_cube | grep -E "^(bottom|top|tbres|depths|rows|cols|nsres|ewres|vertical_units)="
    ```

    ```text
    bottom=10
    top=20
    nsres=2000
    ewres=2000
    tbres=5
    rows=2
    cols=2
    depths=2
    vertical_units="hours"
    ```

    ```sh
    t.info -g type=raster_3d input=model_cube | grep -E "^(temporal_type|start_time|end_time|unit)="
    ```

    ```text
    temporal_type=relative
    start_time='10'
    end_time='20'
    unit=hours
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=204000, s=200000, e=604000, w=600000, res=1000, res3=2000)
    tools.r_mapcalc(expression="model_1 = 1")
    tools.r_mapcalc(expression="model_2 = 2")
    tools.t_create(
        output="model", temporaltype="relative", title="Model", description="Two steps"
    )
    tools.t_register(
        input="model",
        maps="model_1,model_2",
        start=10,
        increment=5,
        unit="hours",
        flags="i",
    )
    tools.t_rast_to_rast3(input="model", output="model_cube")
    print_keys(
        tools.r3_info(map="model_cube", flags="g"),
        "bottom",
        "top",
        "tbres",
        "depths",
        "rows",
        "cols",
        "nsres",
        "ewres",
        "vertical_units",
    )
    ```

    ```text
    bottom=10
    top=20
    tbres=5
    depths=2
    rows=2
    cols=2
    nsres=2000
    ewres=2000
    vertical_units="hours"
    ```

    ```python
    result = tools.t_info(type="raster_3d", input="model_cube", flags="g")
    print_keys(result, "temporal_type", "start_time", "end_time", "unit")
    ```

    ```text
    temporal_type=relative
    start_time='10'
    end_time='20'
    unit=hours
    ```

### Convert a subset of a dataset

*t.rast.extract* selects the maps of `daily` that start on or after March 2
into the dataset `daily_late`. The cube of the subset starts at day 46081 and
has two layers, the maps of March 2 and March 3, and its time stamp starts on
March 2. This example continues with the dataset `daily` of the second example.

=== "Command line"

    ```sh
    g.region n=202000 s=200000 e=603000 w=600000 res=1000 res3=1000
    t.rast.extract input=daily output=daily_late where="start_time >= '2026-03-02'"
    t.rast.to.rast3 input=daily_late output=late_cube
    r3.info -g late_cube | grep -E "^(bottom|top|depths)="
    t.info -g type=raster_3d input=late_cube | grep -E "^(start_time|end_time)="
    ```

    ```text
    bottom=46081
    top=46083
    depths=2
    start_time='2026-03-02 00:00:00'
    end_time='2026-03-04 00:00:00'
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=202000, s=200000, e=603000, w=600000, res=1000, res3=1000)
    tools.t_rast_extract(
        input="daily", output="daily_late", where="start_time >= '2026-03-02'"
    )
    tools.t_rast_to_rast3(input="daily_late", output="late_cube")
    print_keys(tools.r3_info(map="late_cube", flags="g"), "bottom", "top", "depths")
    print_keys(
        tools.t_info(type="raster_3d", input="late_cube", flags="g"),
        "start_time",
        "end_time",
    )
    ```

    ```text
    bottom=46081
    top=46083
    depths=2
    start_time='2026-03-02 00:00:00'
    end_time='2026-03-04 00:00:00'
    ```

### Time instants

The dataset `instants` holds three maps registered as time instants, March 1,
2, and 3, without an end. Its granularity is one day. Each instant gets one
layer, so the cube has three layers and spans the days from 46080 to 46083,
three days. The time stamp of the cube ends one granularity after the last
instant, on March 4, where the top of the cube is.

=== "Command line"

    ```sh
    g.region n=202000 s=200000 e=603000 w=600000 res=1000 res3=1000
    for step in 1 2 3; do
        r.mapcalc expression="instant_$step = $step"
    done
    t.create output=instants title="Instants" description="Three time instants"
    t.register input=instants maps=instant_1,instant_2,instant_3 start=2026-03-01 increment="1 day"
    t.rast.to.rast3 input=instants output=instants_cube
    r3.info -g instants_cube | grep -E "^(bottom|top|depths)="
    t.info -g type=raster_3d input=instants_cube | grep -E "^(start_time|end_time)="
    ```

    ```text
    bottom=46080
    top=46083
    depths=3
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-04 00:00:00'
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=202000, s=200000, e=603000, w=600000, res=1000, res3=1000)
    for step in range(1, 4):
        tools.r_mapcalc(expression=f"instant_{step} = {step}")
    tools.t_create(output="instants", title="Instants", description="Three time instants")
    tools.t_register(
        input="instants",
        maps="instant_1,instant_2,instant_3",
        start="2026-03-01",
        increment="1 day",
    )
    tools.t_rast_to_rast3(input="instants", output="instants_cube")
    print_keys(tools.r3_info(map="instants_cube", flags="g"), "bottom", "top", "depths")
    print_keys(
        tools.t_info(type="raster_3d", input="instants_cube", flags="g"),
        "start_time",
        "end_time",
    )
    ```

    ```text
    bottom=46080
    top=46083
    depths=3
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-04 00:00:00'
    ```

### Maps of different data types are refused

The dataset `mixed` holds a map of type `FCELL` and a map of type `DCELL`. The
tool stops with the message of *r.to.rast3*; the first block prints the error
lines of the call.

=== "Command line"

    ```sh
    g.region n=202000 s=200000 e=603000 w=600000 res=1000 res3=1000
    r.mapcalc expression="mixed_1 = float(1)"
    r.mapcalc expression="mixed_2 = double(2)"
    t.create output=mixed title="Mixed" description="Two data types"
    t.register -i input=mixed maps=mixed_1,mixed_2 start=2026-03-01 increment="1 day"
    if ! t.rast.to.rast3 input=mixed output=mixed_cube 2> errors.txt; then
        grep ERROR errors.txt
        echo "t.rast.to.rast3 failed"
    fi
    ```

    ```text
    ERROR: Input maps have to be from the same type. CELL, FCELL or DCELL!
    ERROR: Unable to create 3D raster map <mixed_cube>
    t.rast.to.rast3 failed
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    tools.g_region(n=202000, s=200000, e=603000, w=600000, res=1000, res3=1000)
    tools.r_mapcalc(expression="mixed_1 = float(1)")
    tools.r_mapcalc(expression="mixed_2 = double(2)")
    tools.t_create(output="mixed", title="Mixed", description="Two data types")
    tools.t_register(
        input="mixed",
        maps="mixed_1,mixed_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    try:
        tools.t_rast_to_rast3(input="mixed", output="mixed_cube")
    except ToolError as error:
        for line in error.stderr.splitlines():
            if "ERROR" in line:
                print(line)
        print("t.rast.to.rast3 failed")
    ```

    ```text
    ERROR: Input maps have to be from the same type. CELL, FCELL or DCELL!
    ERROR: Unable to create 3D raster map <mixed_cube>
    t.rast.to.rast3 failed
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.region](g.region.md), [r.to.rast3](r.to.rast3.md),
[r3.info](r3.info.md), [r3.out.ascii](r3.out.ascii.md),
[t.create](t.create.md), [t.info](t.info.md),
[t.rast.extract](t.rast.extract.md), [t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
