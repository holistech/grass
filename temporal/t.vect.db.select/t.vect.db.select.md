## DESCRIPTION

*t.vect.db.select* prints the attribute tables of the vector maps that are
registered in a space time vector dataset. It runs
*[v.db.select](v.db.select.md)* on each map, in the order of the start times of
the maps, and puts the start and end time of the map in front of every row. Use
it to see the attributes of a whole time series at once, or to find the rows of
all maps that meet one condition. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. *[t.vect.list](t.vect.list.md)* lists the maps themselves, and
*[t.vect.univar](t.vect.univar.md)* calculates statistics of their attributes.

The option **input** names the space time vector dataset. A dataset of another
mapset can be named with its mapset, `name@mapset`; a name without a mapset is
searched in the current mapset and then in the mapsets of the search path. The
last example shows both forms. The maps are read from their own mapsets.

### Select maps and rows

The option **t_where** selects maps of the dataset. It takes an SQL condition on
the columns of the registered maps, the columns that *t.vect.list* offers, such
as `start_time >= '2026-02-01'` or `name = 'normals_2026_02'`. Without
**t_where**, all maps are used. The option **where** selects rows. It takes an
SQL condition on the columns of the attribute table, such as
`precipitation > 100`, and is applied to the table of each selected map. Both
options leave out the word `where`, and they can be combined: a row is printed
if its map meets **t_where** and the row meets **where**.

The option **layer** (default `1`) is the layer whose table is printed. A map
that is registered in the dataset with a layer, as `name:2`, always uses that
layer, and the option **layer** applies to the maps registered without one,
unless an earlier map was registered with a layer; see the notes. The layer
example shows both.

### Select columns

The option **columns** takes the names of the table columns to print, separated
by commas, in the order in which they are given. Without **columns**, all
columns of the table are printed in the order of the table. The names are
compared without regard to case, as the database does. Besides plain names,
**columns** takes the star and SQL expressions such as `precipitation * 2`, which
*v.db.select* evaluates for each row.

### Output

Every row starts with two columns, `start_time` and `end_time`, the times of the
map that the row comes from; the other columns are those of the attribute table.
A map registered as a time instant has no end time: the column is empty in the
formats `plain` and `csv` and `null` in `json`. With relative time, the times
are numbers in the unit of the dataset.

The option **format** chooses the form of the output:

- `plain` (the default) prints one header line with the column names and then
  one line per row. The columns are separated by `|`.
- `csv` prints the same lines, separated by a comma. Text values are put in
  double quotes.
- `json` prints a single list that holds one object per row, with the keys
  `start_time` and `end_time` first and then the columns. Numbers stay numbers
  and text values are strings.

The option **separator** replaces the separator of the columns in `plain` and
`csv`. It takes a character or a name such as `comma`, as the example shows.
In `csv` the separator must be a single character. `json` does not take a
separator.

### Several maps

The header line is printed before the rows of the first map. When the next map
has other columns, the header is printed again before its rows, so each block of
lines has the header that belongs to it. Maps with the same columns share one
header. A map without a row that meets **where** adds no line, except a header
if its columns differ. The format `json` has no headers. Its list holds the rows
of all maps.

## NOTES

All maps are checked before the first line is printed, for their attribute
table and for the columns named in **columns**. If a map has no attribute table
in the layer used for it, or lacks such a column, the module ends with an error
that lists the maps and prints nothing. The star and SQL expressions in
**columns** are not checked; *v.db.select* evaluates them in the table of each
map. A column of **where** is not checked in advance. An error in **where** ends
the module with the message of *v.db.select*, for example "incomplete input",
and a column that the table of a later map lacks stops the module at that map,
after the lines of the earlier maps have been printed.

If **t_where** selects no map, the module prints a warning and ends
successfully: the output is empty, or `[]` for the JSON format. An error in
**t_where** ends the module with the message "Invalid t_where condition".

A separator longer than one character with the format `csv`, and any separator
with the format `json`, are refused.

A map is read with the layer it is registered with. A map that is registered
without a layer takes the layer of the last selected map before it, in the order
of the start times, that is registered with one, and the option **layer** only
if there is none. The order of registration does not matter, and a map that
**t_where** leaves out passes on nothing. The layer example
shows the case, which is easy to miss: register such maps with the layer they
need, as `name:1`, or keep them in a dataset of their own.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_vect_db_select` and sets the computational region
to North Carolina with cells of 1 km; the later examples work in this mapset
and region. *t.vect.db.select* reads attribute tables, so the maps are copies of
the climate stations `precip_30ynormals` or of small sketches in the coordinate
system of the dataset, and the datasets carry times of 2026.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_vect_db_select -->

<!-- markdownlint-disable MD046 -->

### Print the attributes of the maps of a dataset

The dataset `normals` has three point maps for the months from January to March
2026. Map `normals_2026_k` is a copy of the first three climate stations of
`precip_30ynormals`, the stations 310090, 310184 and 310241, with the 30-year
normal of the month `k` as the column `precipitation` in mm: the column `jan`
of the stations for January, `feb` for February and `mar` for March, rounded to
whole millimeters. The values are normals of the stations, not measurements of
2026; the dates only place the maps on the time axis. The column `terrain` is
`upland` for a station above 300 m and `lowland` for the others. The copy keeps
the columns `cat`, `station` and `elev` of the stations, so the table of each
map has the columns `cat`, `station`, `elev`, `precipitation` and `terrain`.

The first block prints the whole table of the three maps, nine rows. Each row
starts with the start and end time of its map. The second block prints the two
columns `precipitation` and `cat` only; the columns come in the order of
**columns**.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_db_select
    g.region raster=elev_state_500m res=1000 -a
    for month in 01:jan 02:feb 03:mar; do
        map=normals_2026_${month%:*}
        v.extract input=precip_30ynormals output=$map where="cat <= 3"
        v.db.addcolumn map=$map columns="precipitation integer, terrain text"
        v.db.update map=$map column=precipitation query_column="round(${month#*:})"
        v.db.update map=$map column=terrain \
            query_column="CASE WHEN elev > 300 THEN 'upland' ELSE 'lowland' END"
        v.db.dropcolumn map=$map \
            columns=lat,long,jan,feb,mar,apr,may,jun,jul,aug,sep,oct,nov,dec,annual
    done
    t.create type=stvds output=normals title="Precipitation normals" \
        description="30-year normals in mm at three stations"
    t.register -i type=vector input=normals \
        maps=normals_2026_01,normals_2026_02,normals_2026_03 \
        start=2026-01-01 increment="1 month"
    t.vect.db.select input=normals
    ```

    ```text
    start_time|end_time|cat|station|elev|precipitation|terrain
    2026-01-01 00:00:00|2026-02-01 00:00:00|1|310090|185.928|111|lowland
    2026-01-01 00:00:00|2026-02-01 00:00:00|2|310184|533.0952|182|upland
    2026-01-01 00:00:00|2026-02-01 00:00:00|3|310241|100.584|100|lowland
    2026-02-01 00:00:00|2026-03-01 00:00:00|1|310090|185.928|92|lowland
    2026-02-01 00:00:00|2026-03-01 00:00:00|2|310184|533.0952|155|upland
    2026-02-01 00:00:00|2026-03-01 00:00:00|3|310241|100.584|88|lowland
    2026-03-01 00:00:00|2026-04-01 00:00:00|1|310090|185.928|123|lowland
    2026-03-01 00:00:00|2026-04-01 00:00:00|2|310184|533.0952|177|upland
    2026-03-01 00:00:00|2026-04-01 00:00:00|3|310241|100.584|113|lowland
    ```

    ```sh
    t.vect.db.select input=normals columns=precipitation,cat
    ```

    ```text
    start_time|end_time|precipitation|cat
    2026-01-01 00:00:00|2026-02-01 00:00:00|111|1
    2026-01-01 00:00:00|2026-02-01 00:00:00|182|2
    2026-01-01 00:00:00|2026-02-01 00:00:00|100|3
    2026-02-01 00:00:00|2026-03-01 00:00:00|92|1
    2026-02-01 00:00:00|2026-03-01 00:00:00|155|2
    2026-02-01 00:00:00|2026-03-01 00:00:00|88|3
    2026-03-01 00:00:00|2026-04-01 00:00:00|123|1
    2026-03-01 00:00:00|2026-04-01 00:00:00|177|2
    2026-03-01 00:00:00|2026-04-01 00:00:00|113|3
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_vect_db_select")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    unused = "lat,long,jan,feb,mar,apr,may,jun,jul,aug,sep,oct,nov,dec,annual"
    for number, column in (("01", "jan"), ("02", "feb"), ("03", "mar")):
        name = f"normals_2026_{number}"
        tools.v_extract(input="precip_30ynormals", output=name, where="cat <= 3")
        tools.v_db_addcolumn(map=name, columns="precipitation integer, terrain text")
        tools.v_db_update(map=name, column="precipitation", query_column=f"round({column})")
        tools.v_db_update(
            map=name,
            column="terrain",
            query_column="CASE WHEN elev > 300 THEN 'upland' ELSE 'lowland' END",
        )
        tools.v_db_dropcolumn(map=name, columns=unused)
    tools.t_create(
        type="stvds",
        output="normals",
        title="Precipitation normals",
        description="30-year normals in mm at three stations",
    )
    tools.t_register(
        type="vector",
        input="normals",
        maps="normals_2026_01,normals_2026_02,normals_2026_03",
        start="2026-01-01",
        increment="1 month",
        flags="i",
    )
    print(tools.t_vect_db_select(input="normals").text)
    ```

    ```text
    start_time|end_time|cat|station|elev|precipitation|terrain
    2026-01-01 00:00:00|2026-02-01 00:00:00|1|310090|185.928|111|lowland
    2026-01-01 00:00:00|2026-02-01 00:00:00|2|310184|533.0952|182|upland
    2026-01-01 00:00:00|2026-02-01 00:00:00|3|310241|100.584|100|lowland
    2026-02-01 00:00:00|2026-03-01 00:00:00|1|310090|185.928|92|lowland
    2026-02-01 00:00:00|2026-03-01 00:00:00|2|310184|533.0952|155|upland
    2026-02-01 00:00:00|2026-03-01 00:00:00|3|310241|100.584|88|lowland
    2026-03-01 00:00:00|2026-04-01 00:00:00|1|310090|185.928|123|lowland
    2026-03-01 00:00:00|2026-04-01 00:00:00|2|310184|533.0952|177|upland
    2026-03-01 00:00:00|2026-04-01 00:00:00|3|310241|100.584|113|lowland
    ```

    ```python
    print(tools.t_vect_db_select(input="normals", columns="precipitation,cat").text)
    ```

    ```text
    start_time|end_time|precipitation|cat
    2026-01-01 00:00:00|2026-02-01 00:00:00|111|1
    2026-01-01 00:00:00|2026-02-01 00:00:00|182|2
    2026-01-01 00:00:00|2026-02-01 00:00:00|100|3
    2026-02-01 00:00:00|2026-03-01 00:00:00|92|1
    2026-02-01 00:00:00|2026-03-01 00:00:00|155|2
    2026-02-01 00:00:00|2026-03-01 00:00:00|88|3
    2026-03-01 00:00:00|2026-04-01 00:00:00|123|1
    2026-03-01 00:00:00|2026-04-01 00:00:00|177|2
    2026-03-01 00:00:00|2026-04-01 00:00:00|113|3
    ```

### Select rows and maps

The first block prints the stations with a precipitation above 100 mm from every
map. The condition **where** is applied to each table: the first map has two
such stations, the second one and the third all three. The second block selects
the maps that start on 1 February or later and prints all their rows. The third
block combines both: the station with the category 2 of the maps that start on
1 February or later.

=== "Command line"

    ```sh
    t.vect.db.select input=normals columns=cat,precipitation \
        where="precipitation > 100"
    ```

    ```text
    start_time|end_time|cat|precipitation
    2026-01-01 00:00:00|2026-02-01 00:00:00|1|111
    2026-01-01 00:00:00|2026-02-01 00:00:00|2|182
    2026-02-01 00:00:00|2026-03-01 00:00:00|2|155
    2026-03-01 00:00:00|2026-04-01 00:00:00|1|123
    2026-03-01 00:00:00|2026-04-01 00:00:00|2|177
    2026-03-01 00:00:00|2026-04-01 00:00:00|3|113
    ```

    ```sh
    t.vect.db.select input=normals columns=cat,precipitation \
        t_where="start_time >= '2026-02-01'"
    ```

    ```text
    start_time|end_time|cat|precipitation
    2026-02-01 00:00:00|2026-03-01 00:00:00|1|92
    2026-02-01 00:00:00|2026-03-01 00:00:00|2|155
    2026-02-01 00:00:00|2026-03-01 00:00:00|3|88
    2026-03-01 00:00:00|2026-04-01 00:00:00|1|123
    2026-03-01 00:00:00|2026-04-01 00:00:00|2|177
    2026-03-01 00:00:00|2026-04-01 00:00:00|3|113
    ```

    ```sh
    t.vect.db.select input=normals columns=cat,precipitation \
        where="cat = 2" t_where="start_time >= '2026-02-01'"
    ```

    ```text
    start_time|end_time|cat|precipitation
    2026-02-01 00:00:00|2026-03-01 00:00:00|2|155
    2026-03-01 00:00:00|2026-04-01 00:00:00|2|177
    ```

=== "Python (grass.tools)"

    ```python
    print(
        tools.t_vect_db_select(
            input="normals", columns="cat,precipitation", where="precipitation > 100"
        ).text
    )
    ```

    ```text
    start_time|end_time|cat|precipitation
    2026-01-01 00:00:00|2026-02-01 00:00:00|1|111
    2026-01-01 00:00:00|2026-02-01 00:00:00|2|182
    2026-02-01 00:00:00|2026-03-01 00:00:00|2|155
    2026-03-01 00:00:00|2026-04-01 00:00:00|1|123
    2026-03-01 00:00:00|2026-04-01 00:00:00|2|177
    2026-03-01 00:00:00|2026-04-01 00:00:00|3|113
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="normals",
            columns="cat,precipitation",
            t_where="start_time >= '2026-02-01'",
        ).text
    )
    ```

    ```text
    start_time|end_time|cat|precipitation
    2026-02-01 00:00:00|2026-03-01 00:00:00|1|92
    2026-02-01 00:00:00|2026-03-01 00:00:00|2|155
    2026-02-01 00:00:00|2026-03-01 00:00:00|3|88
    2026-03-01 00:00:00|2026-04-01 00:00:00|1|123
    2026-03-01 00:00:00|2026-04-01 00:00:00|2|177
    2026-03-01 00:00:00|2026-04-01 00:00:00|3|113
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="normals",
            columns="cat,precipitation",
            where="cat = 2",
            t_where="start_time >= '2026-02-01'",
        ).text
    )
    ```

    ```text
    start_time|end_time|cat|precipitation
    2026-02-01 00:00:00|2026-03-01 00:00:00|2|155
    2026-03-01 00:00:00|2026-04-01 00:00:00|2|177
    ```

### Choose the output format

All blocks print the station with the category 2 of each map and the columns
`cat` and `terrain`. The first block uses `csv`: the separator is a comma and
the text values are in double quotes. The second block sets **separator** to a
semicolon for `csv`. The third block shows `plain` with the separator `comma`,
which differs from `csv` by the missing quotes. The fourth block uses `json`: a
list with one object for each row, the times first.

=== "Command line"

    ```sh
    t.vect.db.select input=normals columns=cat,terrain where="cat = 2" format=csv
    ```

    ```text
    start_time,end_time,cat,terrain
    2026-01-01 00:00:00,2026-02-01 00:00:00,2,"upland"
    2026-02-01 00:00:00,2026-03-01 00:00:00,2,"upland"
    2026-03-01 00:00:00,2026-04-01 00:00:00,2,"upland"
    ```

    ```sh
    t.vect.db.select input=normals columns=cat,terrain where="cat = 2" \
        format=csv separator=";"
    ```

    ```text
    start_time;end_time;cat;terrain
    2026-01-01 00:00:00;2026-02-01 00:00:00;2;"upland"
    2026-02-01 00:00:00;2026-03-01 00:00:00;2;"upland"
    2026-03-01 00:00:00;2026-04-01 00:00:00;2;"upland"
    ```

    ```sh
    t.vect.db.select input=normals columns=cat,terrain where="cat = 2" \
        separator=comma
    ```

    ```text
    start_time,end_time,cat,terrain
    2026-01-01 00:00:00,2026-02-01 00:00:00,2,upland
    2026-02-01 00:00:00,2026-03-01 00:00:00,2,upland
    2026-03-01 00:00:00,2026-04-01 00:00:00,2,upland
    ```

    ```sh
    t.vect.db.select input=normals columns=cat,terrain where="cat = 2" format=json
    ```

    ```text
    [
        {
            "start_time": "2026-01-01 00:00:00",
            "end_time": "2026-02-01 00:00:00",
            "cat": 2,
            "terrain": "upland"
        },
        {
            "start_time": "2026-02-01 00:00:00",
            "end_time": "2026-03-01 00:00:00",
            "cat": 2,
            "terrain": "upland"
        },
        {
            "start_time": "2026-03-01 00:00:00",
            "end_time": "2026-04-01 00:00:00",
            "cat": 2,
            "terrain": "upland"
        }
    ]
    ```

=== "Python (grass.tools)"

    ```python
    print(
        tools.t_vect_db_select(
            input="normals", columns="cat,terrain", where="cat = 2", format="csv"
        ).text
    )
    ```

    ```text
    start_time,end_time,cat,terrain
    2026-01-01 00:00:00,2026-02-01 00:00:00,2,"upland"
    2026-02-01 00:00:00,2026-03-01 00:00:00,2,"upland"
    2026-03-01 00:00:00,2026-04-01 00:00:00,2,"upland"
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="normals",
            columns="cat,terrain",
            where="cat = 2",
            format="csv",
            separator=";",
        ).text
    )
    ```

    ```text
    start_time;end_time;cat;terrain
    2026-01-01 00:00:00;2026-02-01 00:00:00;2;"upland"
    2026-02-01 00:00:00;2026-03-01 00:00:00;2;"upland"
    2026-03-01 00:00:00;2026-04-01 00:00:00;2;"upland"
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="normals", columns="cat,terrain", where="cat = 2", separator="comma"
        ).text
    )
    ```

    ```text
    start_time,end_time,cat,terrain
    2026-01-01 00:00:00,2026-02-01 00:00:00,2,upland
    2026-02-01 00:00:00,2026-03-01 00:00:00,2,upland
    2026-03-01 00:00:00,2026-04-01 00:00:00,2,upland
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="normals", columns="cat,terrain", where="cat = 2", format="json"
        ).text
    )
    ```

    ```text
    [
        {
            "start_time": "2026-01-01 00:00:00",
            "end_time": "2026-02-01 00:00:00",
            "cat": 2,
            "terrain": "upland"
        },
        {
            "start_time": "2026-02-01 00:00:00",
            "end_time": "2026-03-01 00:00:00",
            "cat": 2,
            "terrain": "upland"
        },
        {
            "start_time": "2026-03-01 00:00:00",
            "end_time": "2026-04-01 00:00:00",
            "cat": 2,
            "terrain": "upland"
        }
    ]
    ```

### Time instants and relative time

The dataset `snapshots` has two maps that are registered as time instants, for 1
and 2 January 2026. Each has one point: map `snapshot_k` is a copy of the
station with the category `k` of `precip_30ynormals`. The end time is empty: the
first block shows the two separators `||` next to each other in the plain
format, and the second block shows `null` in `json`. The dataset `cycles` has
two maps of relative time in days, from 0 to 1 and from 1 to 2, with the same
two stations. Its times are numbers.

=== "Command line"

    ```sh
    for k in 1 2; do
        v.extract input=precip_30ynormals output=snapshot_$k where="cat = $k"
        v.extract input=precip_30ynormals output=cycle_$k where="cat = $k"
    done
    t.create type=stvds output=snapshots title="Snapshots" \
        description="Stations as time instants"
    t.register type=vector input=snapshots maps=snapshot_1,snapshot_2 \
        start=2026-01-01 increment="1 day"
    t.create type=stvds temporaltype=relative output=cycles title="Cycles" \
        description="Stations per cycle"
    t.register -i type=vector input=cycles maps=cycle_1,cycle_2 \
        start=0 increment=1 unit=days
    t.vect.db.select input=snapshots columns=cat,station,elev
    ```

    ```text
    start_time|end_time|cat|station|elev
    2026-01-01 00:00:00||1|310090|185.928
    2026-01-02 00:00:00||2|310184|533.0952
    ```

    ```sh
    t.vect.db.select input=snapshots columns=cat,station,elev \
        where="elev > 300" format=json
    ```

    ```text
    [
        {
            "start_time": "2026-01-02 00:00:00",
            "end_time": null,
            "cat": 2,
            "station": 310184,
            "elev": 533.0952
        }
    ]
    ```

    ```sh
    t.vect.db.select input=cycles columns=cat,station,elev
    ```

    ```text
    start_time|end_time|cat|station|elev
    0|1|1|310090|185.928
    1|2|2|310184|533.0952
    ```

=== "Python (grass.tools)"

    ```python
    for k in (1, 2):
        tools.v_extract(
            input="precip_30ynormals", output=f"snapshot_{k}", where=f"cat = {k}"
        )
        tools.v_extract(input="precip_30ynormals", output=f"cycle_{k}", where=f"cat = {k}")
    tools.t_create(
        type="stvds",
        output="snapshots",
        title="Snapshots",
        description="Stations as time instants",
    )
    tools.t_register(
        type="vector",
        input="snapshots",
        maps="snapshot_1,snapshot_2",
        start="2026-01-01",
        increment="1 day",
    )
    tools.t_create(
        type="stvds",
        temporaltype="relative",
        output="cycles",
        title="Cycles",
        description="Stations per cycle",
    )
    tools.t_register(
        type="vector",
        input="cycles",
        maps="cycle_1,cycle_2",
        start=0,
        increment=1,
        unit="days",
        flags="i",
    )
    print(tools.t_vect_db_select(input="snapshots", columns="cat,station,elev").text)
    ```

    ```text
    start_time|end_time|cat|station|elev
    2026-01-01 00:00:00||1|310090|185.928
    2026-01-02 00:00:00||2|310184|533.0952
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="snapshots", columns="cat,station,elev", where="elev > 300", format="json"
        ).text
    )
    ```

    ```text
    [
        {
            "start_time": "2026-01-02 00:00:00",
            "end_time": null,
            "cat": 2,
            "station": 310184,
            "elev": 533.0952
        }
    ]
    ```

    ```python
    print(tools.t_vect_db_select(input="cycles", columns="cat,station,elev").text)
    ```

    ```text
    start_time|end_time|cat|station|elev
    0|1|1|310090|185.928
    1|2|2|310184|533.0952
    ```

### Choose the layer

The dataset `plots` has two maps for 1 and 2 March 2026. Each has two points
with the categories 1 and 2 in layer 1 and in layer 2. The points lie in the
computational region south of the state: the points of `plots_k` are `k` km east
of the position (300000, 100000) and 1 and 2 km north of it. The table of layer
1 has the column `count` with the values 1 and 2, the table of layer 2 the
values 101 and 102. The maps are registered without a layer, so the first block
prints layer 1 and the second block, with **layer** set to 2, prints layer 2.

The dataset `both` registers the two layers of `plots_1` as `plots_1:1` and
`plots_1:2`. The third block prints both, and a **layer** option does not change
this: the registered layer wins.

The dataset `mixed` shows the case that the notes warn about. It registers
`plots_1:2` for 1 March and `plots_2` without a layer for 2 March. The fourth
block prints layer 2 for both maps: the second map takes the layer of the
first and shows 101 and 102, not the values 1 and 2 of its layer 1.

=== "Command line"

    ```sh
    for k in 1 2; do
        v.edit map=plots_$k tool=create
        v.edit map=plots_$k tool=add input=- <<EOF
    VERTI:
    P 1 2
     $((300000 + 1000 * k)) 101000
     1 1
     2 1
    P 1 2
     $((300000 + 1000 * k)) 102000
     1 2
     2 2
    EOF
        v.db.addtable map=plots_$k columns="count integer"
        v.db.addtable map=plots_$k layer=2 table=plots_${k}_b columns="count integer"
        db.execute input=- <<EOF
    UPDATE plots_$k SET count = cat;
    UPDATE plots_${k}_b SET count = 100 + cat;
    EOF
    done
    t.create type=stvds output=plots title="Plots" \
        description="Two layers per map"
    t.register -i type=vector input=plots maps=plots_1,plots_2 \
        start=2026-03-01 increment="1 day"
    t.vect.db.select input=plots
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|1
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|2
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|1
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|2
    ```

    ```sh
    t.vect.db.select input=plots layer=2
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|101
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|102
    ```

    ```sh
    t.create type=stvds output=both title="Both layers" \
        description="Two layers of one map"
    t.register type=vector input=both maps=plots_1:1,plots_1:2 \
        start=2026-03-01 end=2026-03-02
    t.vect.db.select input=both layer=2
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|1
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|2
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    ```

    ```sh
    t.create type=stvds output=mixed title="Mixed layers" \
        description="A map with a layer, then one without"
    t.register type=vector input=mixed maps=plots_1:2 \
        start=2026-03-01 end=2026-03-02
    t.register type=vector input=mixed maps=plots_2 \
        start=2026-03-02 end=2026-03-03
    t.vect.db.select input=mixed
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|101
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|102
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    features = "VERTI:\nP 1 2\n {x} 101000\n 1 1\n 2 1\nP 1 2\n {x} 102000\n 1 2\n 2 2\n"
    for k in (1, 2):
        tools.v_edit(map=f"plots_{k}", tool="create")
        tools.v_edit(
            map=f"plots_{k}",
            tool="add",
            input=StringIO(features.format(x=300000 + 1000 * k)),
        )
        tools.v_db_addtable(map=f"plots_{k}", columns="count integer")
        tools.v_db_addtable(
            map=f"plots_{k}", layer=2, table=f"plots_{k}_b", columns="count integer"
        )
        sql = f"UPDATE plots_{k} SET count = cat;\n"
        sql += f"UPDATE plots_{k}_b SET count = 100 + cat;\n"
        tools.db_execute(input=StringIO(sql))
    tools.t_create(
        type="stvds", output="plots", title="Plots", description="Two layers per map"
    )
    tools.t_register(
        type="vector",
        input="plots",
        maps="plots_1,plots_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_vect_db_select(input="plots").text)
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|1
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|2
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|1
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|2
    ```

    ```python
    print(tools.t_vect_db_select(input="plots", layer=2).text)
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|101
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|102
    ```

    ```python
    tools.t_create(
        type="stvds",
        output="both",
        title="Both layers",
        description="Two layers of one map",
    )
    tools.t_register(
        type="vector",
        input="both",
        maps="plots_1:1,plots_1:2",
        start="2026-03-01",
        end="2026-03-02",
    )
    print(tools.t_vect_db_select(input="both", layer=2).text)
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|1
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|2
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    ```

    ```python
    tools.t_create(
        type="stvds",
        output="mixed",
        title="Mixed layers",
        description="A map with a layer, then one without",
    )
    tools.t_register(
        type="vector",
        input="mixed",
        maps="plots_1:2",
        start="2026-03-01",
        end="2026-03-02",
    )
    tools.t_register(
        type="vector",
        input="mixed",
        maps="plots_2",
        start="2026-03-02",
        end="2026-03-03",
    )
    print(tools.t_vect_db_select(input="mixed").text)
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|101
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|102
    ```

### Print from a dataset of another mapset

The dataset `normals` stays in the mapset `t_vect_db_select`. The example
creates the mapset `t_vect_db_select_2` and switches to it, with the region of
the first example. The first block adds the mapset `t_vect_db_select` to the
search path of the new mapset with *g.mapsets* and prints the dataset by its
name alone, which is found in the search path. The mapset is added only for
this block, because it names the dataset without its mapset; the second block
names the mapset and works without it (see
[Datasets of other mapsets](temporalintro.md#datasets-of-other-mapsets)). Both
print the same rows.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_db_select_2
    g.region raster=elev_state_500m res=1000 -a
    g.mapsets mapset=t_vect_db_select operation=add
    t.vect.db.select input=normals columns=cat,precipitation where="cat = 1"
    ```

    ```text
    start_time|end_time|cat|precipitation
    2026-01-01 00:00:00|2026-02-01 00:00:00|1|111
    2026-02-01 00:00:00|2026-03-01 00:00:00|1|92
    2026-03-01 00:00:00|2026-04-01 00:00:00|1|123
    ```

    ```sh
    t.vect.db.select input=normals@t_vect_db_select columns=cat,precipitation \
        where="cat = 1"
    ```

    ```text
    start_time|end_time|cat|precipitation
    2026-01-01 00:00:00|2026-02-01 00:00:00|1|111
    2026-02-01 00:00:00|2026-03-01 00:00:00|1|92
    2026-03-01 00:00:00|2026-04-01 00:00:00|1|123
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_vect_db_select_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.g_mapsets(mapset="t_vect_db_select", operation="add")
    print(
        tools.t_vect_db_select(
            input="normals", columns="cat,precipitation", where="cat = 1"
        ).text
    )
    ```

    ```text
    start_time|end_time|cat|precipitation
    2026-01-01 00:00:00|2026-02-01 00:00:00|1|111
    2026-02-01 00:00:00|2026-03-01 00:00:00|1|92
    2026-03-01 00:00:00|2026-04-01 00:00:00|1|123
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="normals@t_vect_db_select",
            columns="cat,precipitation",
            where="cat = 1",
        ).text
    )
    ```

    ```text
    start_time|end_time|cat|precipitation
    2026-01-01 00:00:00|2026-02-01 00:00:00|1|111
    2026-02-01 00:00:00|2026-03-01 00:00:00|1|92
    2026-03-01 00:00:00|2026-04-01 00:00:00|1|123
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[t.create](t.create.md), [t.info](t.info.md),
[t.vect.list](t.vect.list.md), [t.vect.univar](t.vect.univar.md),
[v.db.select](v.db.select.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
