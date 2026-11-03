## DESCRIPTION

*t.register* gives raster, 3D raster and vector maps a time and, if a space
time dataset is named, enters them into that dataset. It is the step after
*[t.create](t.create.md)* in most temporal workflows: the other temporal
tools work on the maps of a dataset. See the
[introduction to temporal data processing](temporalintro.md) for an overview.

The time of a map is stored in the temporal database and in the metadata of
the map itself, so that *[r.timestamp](r.timestamp.md)*,
*[r3.timestamp](r3.timestamp.md)* and *[v.timestamp](v.timestamp.md)* read it.
Those three tools set only the time stamp of the map and do not register the
map in the temporal database; *t.register* can use a time stamp that they
have set (see below).

### Maps and dataset

The option **maps** lists the maps, separated by commas. The option **file**
names a text file with the maps instead (see the input file below); **maps**
and **file** exclude each other, and one of them is required. The option
**type** says what kind of maps they are: `raster` (the default), `raster_3d`
or `vector`. The dataset has to be of the matching kind (`strds`, `str3ds` or
`stvds`), otherwise *t.register* does not find it.

A map is named with or without its mapset (`precipitation_1@t_register` or `precipitation_1`).
Without a mapset, *t.register* looks for the map in the mapsets of the search
path. A map that is not found ends the run before any map is registered. Maps
of other mapsets can be registered in a dataset of the current mapset, but the
dataset itself has to belong to the current mapset: *t.register* refuses a
dataset of another mapset before it writes anything.

The option **input** names the space time dataset. Without it, *t.register*
only gives the maps their time and registers them in the temporal database.
A map that is registered already can be entered into a further dataset by its
name alone: *t.register* then reads its time from the temporal database, and
**start**, **end** and **increment** are not needed.

A vector map can have several layers, and each layer is registered on its own.
The notation `map:layer` selects a layer, such as `stations:2`, and a time step
of a series can be a layer of one map. A name without a layer is a map of its
own next to its layer 1. A layer has to be a number, and a layer that
a vector map with a database link does not have is refused.

### Time of the maps

The temporal type of the maps is absolute or relative, and a dataset holds
only maps of its own type (see the option **temporaltype** of *t.create*).
Absolute time is a date, and the time of the day if you want it, in the form
`yyyy-mm-dd`, `yyyy-mm-dd HH:MM`, `yyyy-mm-dd HH:MM:SS` or
`yyyy-mm-ddTHH:MM:SS`, optionally followed by a time zone offset such as
`+0200` or `+02:00`. Relative time is an integer number of a time unit counted
from an arbitrary start; a **start** that is no date is read as relative time.

- The option **start** is the start of the first map. Without **increment**,
  every map gets this start.
- The option **end** is the end of every map. With it, all maps have the same
  interval from **start** to **end**. **end** needs **start**, and it excludes
  **increment** and the flag **-i**.
- The option **increment** is the time between maps, such as `1 months`,
  `12 hours` or `20 seconds, 5 minutes` in absolute time and `5` in relative
  time. It needs **start**. Map n starts n - 1 increments after **start**,
  counted from **start** and not from the previous map. A list such as
  `20 seconds, 5 minutes` is one increment of 5 minutes and 20 seconds.
- The flag **-i** turns the maps into consecutive intervals: map n starts n - 1
  increments after **start** and ends where map n + 1 starts, n increments
  after **start**. Without **-i**, the maps are time instances. **-i** needs
  **start**, and it excludes **end**.
- The option **unit** gives the unit of relative time: `years`, `months`,
  `days`, `hours`, `minutes` or `seconds`. It is required for relative time
  and refused for absolute time. A relative dataset has one unit: the first
  registration sets it, from **unit** or from the relative time that the maps
  have already, and a map with another unit is refused.

Without **start**, *t.register* takes the time that a map has already: the
time of a map that is registered in the temporal database, or the time stamp
that *r.timestamp*, *r3.timestamp* or *v.timestamp* has set. A map that has no
time then makes *t.register* stop with an error.

A map that is registered in the temporal database already keeps its time
when it is registered again, even if **start** is given. *t.register* warns
that the map is already registered and that the overwrite flag is not set. With
**--overwrite**, the time of the map is replaced by the new one, in the
temporal database and in the metadata of the map.

A month or year increment that ends behind the last day of a month ends on
that last day: with `start="2001-01-31"` and `increment="1 months"` the maps
start on January 31, February 28, March 31 and April 30. With the **-i** flag
each map of such an increment ends where the next one starts, so the map of
February 28 ends on March 31. Years and months of an increment such as `20
years, 3 months` form one step of `12 * years + months` months. The **-i**
flag creates consecutive intervals also for a list such as `1 months, 15
days`: there is no gap and no overlap between two maps.

The granularity of a space-time dataset (see *[t.info](t.info.md)*) counts
months and years only if the start and the end of every interval lie on the
first day of a month. A monthly series that starts on another day has the
granularity in days: with `start="2001-01-31"` and `increment="1 months"` the
intervals last 28, 31 and 30 days and the granularity is `1 day`, while the
same series from `2001-01-01` has the granularity `1 month`.

### Input file

The input file has one map per line, and a line can carry the time of its map.
The columns of a line are separated by the character of the option
**separator**, which is the pipe `|` by default. It takes a character or one of
the names `comma`, `pipe` and `tab`. Empty lines are skipped. The forms of a
line are:

- `name`: a map without a time of its own, which gets its time from **start**,
  **end** and **increment**; the position of the line in the file counts, also
  for lines before it that have a time of their own;
- `name|start`: a time instance, which ends at **end** if that option is given;
- `name|start|end`: an interval;
- `name|start|label` and `name|start|end|label`: the same with a semantic label
  of the map.

The name can have a mapset, `name@mapset`. The third column is the end time if
it can be read as one, a date for absolute time and an integer for relative
time, and a semantic label if it cannot. A line with a time keeps it; it needs
no **start**. If every line has a time, **start**, **increment** and the flag
**-i** have no effect, and *t.register* warns about **increment** and **-i**.
The lines of a file with names only get their times in the same way as the
maps of the option **maps**.

A semantic label from the file is registered with the map. Without a label in
the file, the label that the map has, set for instance with
*[r.support](r.support.md)*, is registered with it. Raster maps with a semantic
label can only be registered in a temporal database of version 3 or higher. A
database of version 2 stops the run with an error that says to run
*[t.upgrade](t.upgrade.md)* first; *[t.connect](t.connect.md)* shows the
version.

## NOTES

The timestamps of registered maps are stored in the temporal database and in
the metadata of the maps in the spatial database. This assures that timestamps
can always be accessed with *(r\|r3\|v).timestamp* and the temporal tools.
Timestamps should only be modified with *t.register*, because the
*(r\|r3\|v).timestamp* tools have no access to the temporal database.

If maps are registered without **start** and a map carries a timestamp from
*(r\|r3\|v).timestamp* that is no valid date or relative time, such as `5`,
*t.register* stops with an error that names the map and the stored text
(`The timestamp of raster map <broken@PERMANENT> is not a valid date or time: <5>`)
before any map is registered.

The temporal database stores absolute time stamps in whole seconds: a
fraction of a second is cut off, not rounded, and a time zone offset is
kept. A map whose start and end time fall into the same second is
therefore registered as a time instance, as when start and end time are
equal.

A temporal database on PostgreSQL stores times without a time zone. A
start or end time with a time zone offset, including `+00:00` and `Z`,
is refused before the first map is registered; remove the offset or use
SQLite.

*t.register* checks all maps before it writes the first one. A map that is
refused, for instance because its time has another temporal type or another
relative unit than the dataset, stops the run and leaves the maps before it
as they were. The checks end with these errors, among others:

- `maps and file are mutually exclusive`;
- `end and increment are mutually exclusive`;
- `end and the interval flag are mutually exclusive`;
- `The increment option requires the start option` and, with the flag **-i**,
  `The interval flag requires the start option`;
- `Please specify maps or file`;
- `The map has no timestamp and the start time is not set`;
- `unit can only be set for relative time` for **unit** with absolute time and
  `unit must be set in case of relative time stamps` for relative time without
  it;
- `Space time dataset <name> of type <raster> not found`, also for a dataset
  of another kind than **type**.

A dataset holds maps with a time zone offset or maps without one, not both: a
map of the other kind is refused, and the error says which of the two has a
time zone offset.

A wrong **separator** is not an error of its own: the whole line is read as the
name of a map, and the map is not found.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_register` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset and
region. *t.register* changes times only, so the maps hold small constant
values.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_register -->

<!-- markdownlint-disable MD046 -->

### Register maps as consecutive intervals

Three maps of monthly precipitation sums over North Carolina,
`precipitation_1` to `precipitation_3` with the values 100, 200 and 300
millimetres in every cell, become the intervals January, February and March
2001 of the dataset `precipitation`. The flag **-i** makes each map end where
the next one starts. The type of the maps is `raster`, the default.
*t.rast.list* shows the times in the dataset, and *r.timestamp* shows that the
first map carries its time itself.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_register
    g.region raster=elev_state_500m res=1000 -a
    for number in 1 2 3; do
        r.mapcalc expression="precipitation_$number = 100 * $number"
    done
    t.create output=precipitation title="Precipitation" \
        description="Monthly precipitation sums"
    t.register -i input=precipitation \
        maps=precipitation_1,precipitation_2,precipitation_3 \
        start=2001-01-01 increment="1 months"
    ```

    ```sh
    t.rast.list input=precipitation
    ```

    ```text
    name|mapset|start_time|end_time
    precipitation_1|t_register|2001-01-01 00:00:00|2001-02-01 00:00:00
    precipitation_2|t_register|2001-02-01 00:00:00|2001-03-01 00:00:00
    precipitation_3|t_register|2001-03-01 00:00:00|2001-04-01 00:00:00
    ```

    ```sh
    r.timestamp map=precipitation_1
    ```

    ```text
    1 Jan 2001 00:00:00 / 1 Feb 2001 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_register")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for number in range(1, 4):
        tools.r_mapcalc(expression=f"precipitation_{number} = 100 * {number}")
    tools.t_create(
        output="precipitation",
        title="Precipitation",
        description="Monthly precipitation sums",
    )
    tools.t_register(
        input="precipitation",
        maps="precipitation_1,precipitation_2,precipitation_3",
        start="2001-01-01",
        increment="1 months",
        flags="i",
    )
    ```

    ```python
    print(tools.t_rast_list(input="precipitation").text)
    ```

    ```text
    name|mapset|start_time|end_time
    precipitation_1|t_register|2001-01-01 00:00:00|2001-02-01 00:00:00
    precipitation_2|t_register|2001-02-01 00:00:00|2001-03-01 00:00:00
    precipitation_3|t_register|2001-03-01 00:00:00|2001-04-01 00:00:00
    ```

    ```python
    print(tools.r_timestamp(map="precipitation_1").text)
    ```

    ```text
    1 Jan 2001 00:00:00 / 1 Feb 2001 00:00:00
    ```

### Register time instances and one interval for all maps

Without the flag **-i**, **start** and **increment** make time instances: the
maps `gauge_1` and `gauge_2` are at May 1 and May 2, 2001. The maps `season_1`
and `season_2` get the same interval from **start** to **end**, June 1 to
September 1. Both maps have the same time, so *t.info* with the flag **-g**
shows the time of the dataset as a whole, not one line per map: the maps are
intervals (`map_time=interval`), and the dataset starts and ends with them.

=== "Command line"

    ```sh
    for number in 1 2; do
        r.mapcalc expression="gauge_$number = $number"
        r.mapcalc expression="season_$number = 10 * $number"
    done
    t.create output=gauges title="Gauges" description="Gauge readings"
    t.register input=gauges maps=gauge_1,gauge_2 start=2001-05-01 \
        increment="1 days"
    t.rast.list input=gauges
    ```

    ```text
    name|mapset|start_time|end_time
    gauge_1|t_register|2001-05-01 00:00:00|None
    gauge_2|t_register|2001-05-02 00:00:00|None
    ```

    ```sh
    t.create output=season title="Season" description="One interval"
    t.register input=season maps=season_1,season_2 start=2001-06-01 \
        end=2001-09-01
    t.info -g input=season | grep -E "^(start_time|end_time|map_time)="
    ```

    ```text
    start_time='2001-06-01 00:00:00'
    end_time='2001-09-01 00:00:00'
    map_time=interval
    ```

=== "Python (grass.tools)"

    ```python
    for number in range(1, 3):
        tools.r_mapcalc(expression=f"gauge_{number} = {number}")
        tools.r_mapcalc(expression=f"season_{number} = {10 * number}")
    tools.t_create(output="gauges", title="Gauges", description="Gauge readings")
    tools.t_register(
        input="gauges",
        maps="gauge_1,gauge_2",
        start="2001-05-01",
        increment="1 days",
    )
    print(tools.t_rast_list(input="gauges").text)
    ```

    ```text
    name|mapset|start_time|end_time
    gauge_1|t_register|2001-05-01 00:00:00|None
    gauge_2|t_register|2001-05-02 00:00:00|None
    ```

    ```python
    tools.t_create(output="season", title="Season", description="One interval")
    tools.t_register(
        input="season",
        maps="season_1,season_2",
        start="2001-06-01",
        end="2001-09-01",
    )
    info = tools.t_info(input="season", flags="g").keyval
    for key in ("start_time", "end_time", "map_time"):
        print(f"{key}={info[key]}")
    ```

    ```text
    start_time='2001-06-01 00:00:00'
    end_time='2001-09-01 00:00:00'
    map_time=interval
    ```

### Use a registered map in a second dataset, or change its time

A map that is registered already is entered into another dataset by its name
alone: `first_half` takes `precipitation_1` and `precipitation_2` with the
times they have in the temporal database. A second registration with **start**
does not change the time of `gauge_2`: *t.register* warns and keeps May 2. Only
with **--overwrite** (the argument `overwrite=True` in Python) does the map get
the new time, May 10.

=== "Command line"

    ```sh
    t.create output=first_half title="First half" description="Two months"
    t.register input=first_half maps=precipitation_1,precipitation_2
    t.rast.list input=first_half
    ```

    ```text
    name|mapset|start_time|end_time
    precipitation_1|t_register|2001-01-01 00:00:00|2001-02-01 00:00:00
    precipitation_2|t_register|2001-02-01 00:00:00|2001-03-01 00:00:00
    ```

    ```sh
    t.register input=gauges maps=gauge_2 start=2001-05-10
    t.rast.list input=gauges
    ```

    ```text
    name|mapset|start_time|end_time
    gauge_1|t_register|2001-05-01 00:00:00|None
    gauge_2|t_register|2001-05-02 00:00:00|None
    ```

    ```sh
    t.register --overwrite input=gauges maps=gauge_2 start=2001-05-10
    t.rast.list input=gauges
    ```

    ```text
    name|mapset|start_time|end_time
    gauge_1|t_register|2001-05-01 00:00:00|None
    gauge_2|t_register|2001-05-10 00:00:00|None
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_create(output="first_half", title="First half", description="Two months")
    tools.t_register(input="first_half", maps="precipitation_1,precipitation_2")
    print(tools.t_rast_list(input="first_half").text)
    ```

    ```text
    name|mapset|start_time|end_time
    precipitation_1|t_register|2001-01-01 00:00:00|2001-02-01 00:00:00
    precipitation_2|t_register|2001-02-01 00:00:00|2001-03-01 00:00:00
    ```

    ```python
    tools.t_register(input="gauges", maps="gauge_2", start="2001-05-10")
    print(tools.t_rast_list(input="gauges").text)
    ```

    ```text
    name|mapset|start_time|end_time
    gauge_1|t_register|2001-05-01 00:00:00|None
    gauge_2|t_register|2001-05-02 00:00:00|None
    ```

    ```python
    tools.t_register(input="gauges", maps="gauge_2", start="2001-05-10", overwrite=True)
    print(tools.t_rast_list(input="gauges").text)
    ```

    ```text
    name|mapset|start_time|end_time
    gauge_1|t_register|2001-05-01 00:00:00|None
    gauge_2|t_register|2001-05-10 00:00:00|None
    ```

### Monthly series that start at the end of a month

Eight maps, `month_1` to `month_8`, are registered as monthly intervals. The
first four start on January 31. Each start is a month after the previous one,
counted from January 31, and a month that is too short ends on its last day:
February 28, March 31 and April 30. The intervals are 28, 31, 30 and 31 days
long, so the granularity of `jan31` is `1 day`. The maps `month_5` to
`month_8` start on January 1 and form the dataset `jan01` with the granularity
`1 month`.

=== "Command line"

    ```sh
    for number in 1 2 3 4 5 6 7 8; do
        r.mapcalc expression="month_$number = $number"
    done
    t.create output=jan31 title="Month ends" description="From January 31"
    t.register -i input=jan31 maps=month_1,month_2,month_3,month_4 \
        start=2001-01-31 increment="1 months"
    t.rast.list input=jan31
    ```

    ```text
    name|mapset|start_time|end_time
    month_1|t_register|2001-01-31 00:00:00|2001-02-28 00:00:00
    month_2|t_register|2001-02-28 00:00:00|2001-03-31 00:00:00
    month_3|t_register|2001-03-31 00:00:00|2001-04-30 00:00:00
    month_4|t_register|2001-04-30 00:00:00|2001-05-31 00:00:00
    ```

    ```sh
    t.info -g input=jan31 | grep "^granularity="
    ```

    ```text
    granularity='1 day'
    ```

    ```sh
    t.create output=jan01 title="Month starts" description="From January 1"
    t.register -i input=jan01 maps=month_5,month_6,month_7,month_8 \
        start=2001-01-01 increment="1 months"
    t.info -g input=jan01 | grep "^granularity="
    ```

    ```text
    granularity='1 month'
    ```

=== "Python (grass.tools)"

    ```python
    for number in range(1, 9):
        tools.r_mapcalc(expression=f"month_{number} = {number}")
    tools.t_create(output="jan31", title="Month ends", description="From January 31")
    tools.t_register(
        input="jan31",
        maps="month_1,month_2,month_3,month_4",
        start="2001-01-31",
        increment="1 months",
        flags="i",
    )
    print(tools.t_rast_list(input="jan31").text)
    ```

    ```text
    name|mapset|start_time|end_time
    month_1|t_register|2001-01-31 00:00:00|2001-02-28 00:00:00
    month_2|t_register|2001-02-28 00:00:00|2001-03-31 00:00:00
    month_3|t_register|2001-03-31 00:00:00|2001-04-30 00:00:00
    month_4|t_register|2001-04-30 00:00:00|2001-05-31 00:00:00
    ```

    ```python
    info = tools.t_info(input="jan31", flags="g").keyval
    print(f"granularity={info['granularity']}")
    ```

    ```text
    granularity='1 day'
    ```

    ```python
    tools.t_create(output="jan01", title="Month starts", description="From January 1")
    tools.t_register(
        input="jan01",
        maps="month_5,month_6,month_7,month_8",
        start="2001-01-01",
        increment="1 months",
        flags="i",
    )
    info = tools.t_info(input="jan01", flags="g").keyval
    print(f"granularity={info['granularity']}")
    ```

    ```text
    granularity='1 month'
    ```

### Register maps from a file

The dataset `scenes` takes eight maps, `scene_1` to `scene_8`, from three
files. The first file gives each line its own form: `scene_1` has a start and
an end, `scene_2` only a start, and `scene_3` a start and the semantic label
`S2_8`, because `S2_8` cannot be read as an end time. The second file uses
commas as the separator, which the option **separator** sets, and names the
maps with their mapset. The third file lists only names, made by
*[g.list](g.list.md)*, so **start** and **increment** place the maps, here as
consecutive intervals of 12 hours. The last block shows that the dataset holds
a mix of intervals and instances.

=== "Command line"

    ```sh
    for number in 1 2 3 4 5 6 7 8; do
        r.mapcalc expression="scene_$number = $number"
    done
    t.create output=scenes title="Scenes" description="Scenes from files"
    cat > scenes_a.txt <<EOF
    scene_1|2001-01-01|2001-04-01
    scene_2|2001-04-01
    scene_3|2001-07-01|S2_8
    EOF
    t.register input=scenes file=scenes_a.txt
    t.rast.list input=scenes columns=name,start_time,end_time,semantic_label
    ```

    ```text
    name|start_time|end_time|semantic_label
    scene_1|2001-01-01 00:00:00|2001-04-01 00:00:00|None
    scene_2|2001-04-01 00:00:00|None|None
    scene_3|2001-07-01 00:00:00|None|S2_8
    ```

    ```sh
    cat > scenes_b.txt <<EOF
    scene_4@t_register,2002-01-01,2002-02-01
    scene_5@t_register,2002-02-01,2002-03-01
    EOF
    t.register input=scenes file=scenes_b.txt separator=comma
    t.rast.list input=scenes columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    scene_1|2001-01-01 00:00:00|2001-04-01 00:00:00
    scene_2|2001-04-01 00:00:00|None
    scene_3|2001-07-01 00:00:00|None
    scene_4|2002-01-01 00:00:00|2002-02-01 00:00:00
    scene_5|2002-02-01 00:00:00|2002-03-01 00:00:00
    ```

    ```sh
    g.list type=raster pattern="scene_[678]" mapset=. > scenes_c.txt
    t.register -i input=scenes file=scenes_c.txt start="2003-01-01 06:00" \
        increment="12 hours"
    t.rast.list input=scenes columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    scene_1|2001-01-01 00:00:00|2001-04-01 00:00:00
    scene_2|2001-04-01 00:00:00|None
    scene_3|2001-07-01 00:00:00|None
    scene_4|2002-01-01 00:00:00|2002-02-01 00:00:00
    scene_5|2002-02-01 00:00:00|2002-03-01 00:00:00
    scene_6|2003-01-01 06:00:00|2003-01-01 18:00:00
    scene_7|2003-01-01 18:00:00|2003-01-02 06:00:00
    scene_8|2003-01-02 06:00:00|2003-01-02 18:00:00
    ```

    ```sh
    t.info -g input=scenes | grep -E "^(map_time|number_of_maps)="
    ```

    ```text
    map_time=mixed
    number_of_maps=8
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    for number in range(1, 9):
        tools.r_mapcalc(expression=f"scene_{number} = {number}")
    tools.t_create(output="scenes", title="Scenes", description="Scenes from files")
    Path("scenes_a.txt").write_text(
        "scene_1|2001-01-01|2001-04-01\nscene_2|2001-04-01\nscene_3|2001-07-01|S2_8\n"
    )
    tools.t_register(input="scenes", file="scenes_a.txt")
    print(
        tools.t_rast_list(
            input="scenes", columns="name,start_time,end_time,semantic_label"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|semantic_label
    scene_1|2001-01-01 00:00:00|2001-04-01 00:00:00|None
    scene_2|2001-04-01 00:00:00|None|None
    scene_3|2001-07-01 00:00:00|None|S2_8
    ```

    ```python
    Path("scenes_b.txt").write_text(
        "scene_4@t_register,2002-01-01,2002-02-01\nscene_5@t_register,2002-02-01,2002-03-01\n"
    )
    tools.t_register(input="scenes", file="scenes_b.txt", separator="comma")
    print(tools.t_rast_list(input="scenes", columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    scene_1|2001-01-01 00:00:00|2001-04-01 00:00:00
    scene_2|2001-04-01 00:00:00|None
    scene_3|2001-07-01 00:00:00|None
    scene_4|2002-01-01 00:00:00|2002-02-01 00:00:00
    scene_5|2002-02-01 00:00:00|2002-03-01 00:00:00
    ```

    ```python
    names = tools.g_list(type="raster", pattern="scene_[678]", mapset=".").stdout
    Path("scenes_c.txt").write_text(names)
    tools.t_register(
        input="scenes",
        file="scenes_c.txt",
        start="2003-01-01 06:00",
        increment="12 hours",
        flags="i",
    )
    print(tools.t_rast_list(input="scenes", columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    scene_1|2001-01-01 00:00:00|2001-04-01 00:00:00
    scene_2|2001-04-01 00:00:00|None
    scene_3|2001-07-01 00:00:00|None
    scene_4|2002-01-01 00:00:00|2002-02-01 00:00:00
    scene_5|2002-02-01 00:00:00|2002-03-01 00:00:00
    scene_6|2003-01-01 06:00:00|2003-01-01 18:00:00
    scene_7|2003-01-01 18:00:00|2003-01-02 06:00:00
    scene_8|2003-01-02 06:00:00|2003-01-02 18:00:00
    ```

    ```python
    info = tools.t_info(input="scenes", flags="g").keyval
    for key in ("map_time", "number_of_maps"):
        print(f"{key}={info[key]}")
    ```

    ```text
    map_time=mixed
    number_of_maps=8
    ```

### Register maps with relative time

A dataset with relative time counts in a unit, which **unit** names. The maps
`runoff_1` to `runoff_3` are the intervals 0 to 1, 1 to 2 and 2 to 3 hours. Two
more maps come from a file whose times are integers in the same unit; the third
column of a line is an integer, so it is an end time. The unit has to be the one
of the dataset.

=== "Command line"

    ```sh
    for number in 1 2 3 4 5; do
        r.mapcalc expression="runoff_$number = $number"
    done
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i input=model maps=runoff_1,runoff_2,runoff_3 start=0 increment=1 \
        unit=hours
    t.rast.list input=model
    ```

    ```text
    name|mapset|start_time|end_time
    runoff_1|t_register|0|1
    runoff_2|t_register|1|2
    runoff_3|t_register|2|3
    ```

    ```sh
    cat > steps.txt <<EOF
    runoff_4|10|12
    runoff_5|12|15
    EOF
    t.register input=model file=steps.txt unit=hours
    t.rast.list input=model
    ```

    ```text
    name|mapset|start_time|end_time
    runoff_1|t_register|0|1
    runoff_2|t_register|1|2
    runoff_3|t_register|2|3
    runoff_4|t_register|10|12
    runoff_5|t_register|12|15
    ```

=== "Python (grass.tools)"

    ```python
    for number in range(1, 6):
        tools.r_mapcalc(expression=f"runoff_{number} = {number}")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        input="model",
        maps="runoff_1,runoff_2,runoff_3",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    print(tools.t_rast_list(input="model").text)
    ```

    ```text
    name|mapset|start_time|end_time
    runoff_1|t_register|0|1
    runoff_2|t_register|1|2
    runoff_3|t_register|2|3
    ```

    ```python
    Path("steps.txt").write_text("runoff_4|10|12\nrunoff_5|12|15\n")
    tools.t_register(input="model", file="steps.txt", unit="hours")
    print(tools.t_rast_list(input="model").text)
    ```

    ```text
    name|mapset|start_time|end_time
    runoff_1|t_register|0|1
    runoff_2|t_register|1|2
    runoff_3|t_register|2|3
    runoff_4|t_register|10|12
    runoff_5|t_register|12|15
    ```

### Register maps without a dataset, or with a time stamp of the map

Without **input**, the maps only get their time and are registered in the
temporal database: `free_1` and `free_2` are the days August 1 and 2, 2001.
*t.list* lists them. The second part sets the time of `stamped_1` and
`stamped_2` with *r.timestamp* first; *t.register* needs no **start**, because
it takes the time from the maps.

=== "Command line"

    ```sh
    for number in 1 2; do
        r.mapcalc expression="free_$number = $number"
        r.mapcalc expression="stamped_$number = $number"
    done
    t.register -i maps=free_1,free_2 start=2001-08-01 increment="1 days"
    t.list type=raster columns=name,start_time,end_time \
        where="name IN ('free_1', 'free_2')" order=start_time format=csv
    ```

    ```text
    name,start_time,end_time
    free_1,2001-08-01 00:00:00,2001-08-02 00:00:00
    free_2,2001-08-02 00:00:00,2001-08-03 00:00:00
    ```

    ```sh
    r.timestamp map=stamped_1 date="1 Sep 2001 / 1 Oct 2001"
    r.timestamp map=stamped_2 date="1 Oct 2001 / 1 Nov 2001"
    t.create output=stamped title="Stamped" description="Time from the maps"
    t.register input=stamped maps=stamped_1,stamped_2
    t.rast.list input=stamped
    ```

    ```text
    name|mapset|start_time|end_time
    stamped_1|t_register|2001-09-01 00:00:00|2001-10-01 00:00:00
    stamped_2|t_register|2001-10-01 00:00:00|2001-11-01 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    for number in range(1, 3):
        tools.r_mapcalc(expression=f"free_{number} = {number}")
        tools.r_mapcalc(expression=f"stamped_{number} = {number}")
    tools.t_register(
        maps="free_1,free_2", start="2001-08-01", increment="1 days", flags="i"
    )
    print(
        tools.t_list(
            type="raster",
            columns="name,start_time,end_time",
            where="name IN ('free_1', 'free_2')",
            order="start_time",
            format="csv",
        ).text
    )
    ```

    ```text
    name,start_time,end_time
    free_1,2001-08-01 00:00:00,2001-08-02 00:00:00
    free_2,2001-08-02 00:00:00,2001-08-03 00:00:00
    ```

    ```python
    tools.r_timestamp(map="stamped_1", date="1 Sep 2001 / 1 Oct 2001")
    tools.r_timestamp(map="stamped_2", date="1 Oct 2001 / 1 Nov 2001")
    tools.t_create(output="stamped", title="Stamped", description="Time from the maps")
    tools.t_register(input="stamped", maps="stamped_1,stamped_2")
    print(tools.t_rast_list(input="stamped").text)
    ```

    ```text
    name|mapset|start_time|end_time
    stamped_1|t_register|2001-09-01 00:00:00|2001-10-01 00:00:00
    stamped_2|t_register|2001-10-01 00:00:00|2001-11-01 00:00:00
    ```

### Register layers of a vector map

A vector map can stand for a series if each time step is a layer. The map
`wind_stations` has two points in North Carolina, with a wind speed in metres per
second, and the layers 1 to 3 with the same categories. With
`type=vector` and the notation `map:layer`, each layer is registered as a day of
the dataset `daily`.

=== "Command line"

    ```sh
    v.in.ascii input=- output=wind_stations_import separator=comma \
        columns="x double precision, y double precision, wind_speed double precision" \
        <<EOF
    640000,220000,3.0
    780000,150000,5.0
    EOF
    v.category input=wind_stations_import output=wind_stations \
        option=transfer layer=1,2,3
    t.create type=stvds output=daily title="Daily" description="Layers as days"
    t.register -i type=vector input=daily \
        maps=wind_stations:1,wind_stations:2,wind_stations:3 \
        start=2001-03-01 increment="1 days"
    t.vect.list input=daily columns=name,layer,start_time,end_time
    ```

    ```text
    name|layer|start_time|end_time
    wind_stations|1|2001-03-01 00:00:00|2001-03-02 00:00:00
    wind_stations|2|2001-03-02 00:00:00|2001-03-03 00:00:00
    wind_stations|3|2001-03-03 00:00:00|2001-03-04 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.v_in_ascii(
        input=StringIO("640000,220000,3.0\n780000,150000,5.0\n"),
        output="wind_stations_import",
        separator="comma",
        columns="x double precision, y double precision, wind_speed double precision",
    )
    tools.v_category(
        input="wind_stations_import",
        output="wind_stations",
        option="transfer",
        layer="1,2,3",
    )
    tools.t_create(
        type="stvds", output="daily", title="Daily", description="Layers as days"
    )
    tools.t_register(
        type="vector",
        input="daily",
        maps="wind_stations:1,wind_stations:2,wind_stations:3",
        start="2001-03-01",
        increment="1 days",
        flags="i",
    )
    print(tools.t_vect_list(input="daily", columns="name,layer,start_time,end_time").text)
    ```

    ```text
    name|layer|start_time|end_time
    wind_stations|1|2001-03-01 00:00:00|2001-03-02 00:00:00
    wind_stations|2|2001-03-02 00:00:00|2001-03-03 00:00:00
    wind_stations|3|2001-03-03 00:00:00|2001-03-04 00:00:00
    ```

### Register 3D raster maps

The 3D raster maps `soil_1` and `soil_2` are registered with `type=raster_3d`
in a space time 3D raster dataset. The region needs a top, a bottom and the 3D
resolutions; the call adds them to the region of the first example.

=== "Command line"

    ```sh
    g.region t=3 b=0 res3=1000 tbres=1
    r3.mapcalc expression="soil_1 = depth()"
    r3.mapcalc expression="soil_2 = depth() + 10"
    t.create type=str3ds output=soil title="Soil" \
        description="Soil temperature in three layers"
    t.register -i type=raster_3d input=soil maps=soil_1,soil_2 \
        start=2001-03-01 increment="1 days"
    t.rast3d.list input=soil columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    soil_1|2001-03-01 00:00:00|2001-03-02 00:00:00
    soil_2|2001-03-02 00:00:00|2001-03-03 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(t=3, b=0, res3=1000, tbres=1)
    tools.r3_mapcalc(expression="soil_1 = depth()")
    tools.r3_mapcalc(expression="soil_2 = depth() + 10")
    tools.t_create(
        type="str3ds",
        output="soil",
        title="Soil",
        description="Soil temperature in three layers",
    )
    tools.t_register(
        type="raster_3d",
        input="soil",
        maps="soil_1,soil_2",
        start="2001-03-01",
        increment="1 days",
        flags="i",
    )
    print(tools.t_rast3d_list(input="soil", columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    soil_1|2001-03-01 00:00:00|2001-03-02 00:00:00
    soil_2|2001-03-02 00:00:00|2001-03-03 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [r.support](r.support.md), [r.timestamp](r.timestamp.md),
[r3.timestamp](r3.timestamp.md), [t.connect](t.connect.md),
[t.create](t.create.md), [t.info](t.info.md), [t.list](t.list.md),
[t.rast.list](t.rast.list.md), [t.rast3d.list](t.rast3d.list.md),
[t.upgrade](t.upgrade.md), [t.vect.list](t.vect.list.md),
[v.timestamp](v.timestamp.md),
[temporal data processing](temporalintro.md)*

[Maps registration examples in Temporal data processing
Wiki](https://grasswiki.osgeo.org/wiki/Temporal_data_processing/maps_registration)

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
