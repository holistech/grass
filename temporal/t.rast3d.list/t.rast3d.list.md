## DESCRIPTION

*t.rast3d.list* lists the 3D raster maps that are registered in a space time
3D raster dataset, with the metadata that the temporal database holds for each
map. It reads the temporal database; the maps themselves are not opened. The
listing is the usual step after *[t.info](t.info.md)* has shown the dataset as
a whole and before a tool such as the map algebra works on its maps. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. The tool is the counterpart of *[t.rast.list](t.rast.list.md)* for
3D raster maps, with the same options, formats and methods; the differences are
the columns of the volume (see below), the flag **-s** instead of **-u**, and
the method `cols` instead of `list`. Space time vector datasets have their own
tool, *[t.vect.list](t.vect.list.md)*, and *[t.list](t.list.md)* lists the
datasets themselves.

### Select the maps

The option **input** names the space time 3D raster dataset. The option
**where** takes an SQL condition on the columns of the registered maps, such
as `max > 5`, `name = 'soil_1'` or `start_time >= '2026-03-02'`. Times are
compared as text, so a time with a clock part needs the whole text:
`start_time = '2026-03-02'` selects nothing, because the stored value is
`2026-03-02 00:00:00`. Use `>=` and `<` for a day, or `name` for a single map.
The function `strftime()` of SQLite selects recurring times, such as one day of
the month or one month of the year. With the methods `delta`, `deltagaps` and
`gran`, the condition selects the maps before the lengths and distances are
counted, so the distances start at 0 with the first selected map.

### Columns and order

The option **columns** chooses the columns that are printed for each map,
separated by commas. The columns are:

- `id`, the name of the map with its mapset, such as `soil_1@PERMANENT`;
  `name` and `mapset`, the two parts of it;
- `temporal_type`, `absolute` or `relative`;
- `start_time` and `end_time`, the time of the map. The end time of a map
  registered as a time instant is `None`. With relative time, they are numbers
  in the unit of the dataset, printed without the unit;
- `creator` and `creation_time`, the user who created the entry of the map in
  the temporal database and the time of its creation;
- `north`, `south`, `west` and `east`, the horizontal extent of the map;
  `nsres` and `ewres`, its horizontal cell sizes;
- `tbres`, the vertical resolution, which is the thickness of one layer;
  `depths`, the number of layers; `cols` and `rows`, the number of columns and
  rows of one layer; `number_of_cells`, the number of cells of the whole map,
  which is `cols * rows * depths`. The vertical extent of the map is the
  number of layers times their thickness;
- `min` and `max`, the smallest and the largest value of the map, as stored in
  the temporal database;
- `interval_length` and `distance_from_begin`, the length of the time interval
  of the map and the distance of its start from the start of the first listed
  map. They exist for the methods `delta`, `deltagaps` and `gran` only (see
  below). With absolute time they are numbers of days, with relative time
  numbers of the time unit of the dataset.

The option **order** sorts the maps by one or more columns, separated by
commas; the possible columns are those of the list above up to `max`. The
default is `start_time`. The order is ascending, and the option takes names of
columns only, no sort direction. The option works with the methods `cols` and
`comma` only.

### Methods

The option **method** chooses what is listed. The default is `cols`.

- `cols` prints one line per registered map with the columns of **columns**.
  Without **columns**, these are `name`, `mapset`, `start_time` and
  `end_time`; with `format=line`, the column `id`. It supports all columns
  except `interval_length` and `distance_from_begin`, and **order** applies to
  it.
- `delta` prints the maps ordered by start time with the length of their
  intervals and their distance from the first map. Without **columns**, the
  columns are `id`, `name`, `mapset`, `start_time`, `end_time`,
  `interval_length` and `distance_from_begin`. The length of a time instant is
  `None`. `delta` supports only these columns.
- `deltagaps` is `delta` with a line for every temporal gap between two maps.
  A gap line has `None` as `id`, `name` and `mapset`; its times are the end of
  the map before and the start of the map after the gap, and its length is the
  length of the gap. Maps that follow each other directly leave no gap.
- `gran` samples the maps by a granule and prints one line per granule, with the
  columns of `delta`. The times and the length are those of the granule, not of
  the map, so a map that is longer than the granule is listed once for each
  granule it covers. A granule without a map has `None` as `id`, `name` and
  `mapset`. When more than one map meets a granule, the line names the map with
  the earliest start of the first of these groups that is not empty: maps that
  are equal to the granule, maps that contain it, maps that start inside it and
  end after it, maps that start before it and end inside it, and maps that lie
  inside it.
- `comma` is the old name of `cols` with `format=line`: it prints the values of
  the chosen column in one line, the ids without **columns**. Prefer the option
  **format**.

The option **granule** is the granule of the method `gran`. For absolute
time it is a text with a number and a time unit, such as `"2 months"`. For
relative time, leave it out (see the notes). Without it, the granularity of the
dataset is used. The first granule starts with the first map; each later start
is counted in whole granules from this start. A step of months or years that
ends behind the last day of a shorter month ends on that day: with a granule of
one month and a first map from 31 January, the granules start on 31 January, 28
February, 31 March and 30 April. The other methods ignore **granule**.

### Output

The option **format** chooses the form of the output:

- `plain` (the default) prints one line per map with the columns separated by
  a vertical bar `|`, and the column names as the first line;
- `line` prints the values of one column in one line, separated by commas. It
  takes one column only; the default column is `id`, so the line is a list of
  maps that other tools accept as input;
- `csv` prints comma separated values, with the column names as the first
  line. Text is enclosed in double quotes and numbers are not. A missing value
  (`None`) is an empty text;
- `json` prints an object with the key `data`, a list with one object per
  map, and the key `metadata` with the list `column_names`. A missing value is
  `null`, numbers are numbers, and times with absolute time are text;
- `yaml` prints the same structure as YAML. It needs the PyYAML package.

The flag **-s** suppresses the line with the column names in the formats
`plain` and `csv`. The formats `json` and `yaml` always name the columns and
refuse **-s**.

The option **separator** replaces the separator of the formats `plain`, `csv`
and `line`. It is a single character or a name such as `pipe`, `comma` or
`tab`. The format `csv` accepts one character only, and `json` and `yaml`
refuse **separator**. The option **output** writes the listing to a file
instead of the standard output.

## NOTES

A column name that is not in the list above is refused by the parser, which
names the column.

If no map is listed, the result depends on the method and the format. The
methods `cols` and `comma` stop with the error "Nothing found in the database
for space time dataset `<name@mapset>` (type: str3ds)", followed by "Dataset is
empty" for a dataset without maps and by "Dataset is empty or where clause is
too constrained or incorrect" when **where** selects nothing. With the format
`json`, `data` is an empty list. The methods `delta` and `deltagaps` print the
line with the column names only, both for a dataset without maps and when
**where** selects nothing. The method `gran` does the same when **where**
selects nothing in a dataset that has a granularity, but stops for a dataset
without maps with the error "Nothing found in the database for space time
dataset `<name@mapset>` (type: str3ds)", followed by "Dataset is empty". A
dataset with a single map that is a time instant has no granularity, and `gran`
without **granule** stops for it with the error "Wrong granularity: "None"",
whatever **where** selects. Give a **granule**, such as `"1 day"`, or use
`delta`.

With relative time, the times are numbers of the time unit of the dataset,
printed without the unit, as the model in the fourth example shows. The method
`gran` works with relative time without **granule**. Given a **granule** for a
dataset with relative time, it fails: a number ends with a Python error
(`TypeError`) and a text with a unit such as `"6 hours"` with the error "Wrong
granularity". Leave **granule** out; the granularity of the dataset is used.

The option **output** takes the name of a file. The name `-` is not the
standard output here: it writes a file with this name, as the last block of
the "Choose the output format" example shows. To print the listing, leave out
**output**; to keep it in a file, give a file name other than `-`.

*t.rast3d.list* only reads, so it works on a dataset of another mapset as well.
The name with the mapset (`input=soil@PERMANENT`) selects it; a name without a
mapset is searched in the mapsets of the search path (see
*[g.mapsets](g.mapsets.md)*). The last example shows this.

Combinations that cannot work are refused with a message that names the
options. **order** is refused with `delta`, `deltagaps` and `gran`. These
three methods list only the columns of `delta`, so a column of the temporal
database is refused with them, and `interval_length` and `distance_from_begin`
are refused with `cols`. More than one column is refused with `format=line`,
**-s** and **separator** with `json` and `yaml`, and a separator of more than
one character with `csv`. A granule of absolute time without a time unit
(`"2"`) or with an unknown unit (`"3 foo"`) is refused with the error "Wrong
granularity".

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### List the maps of a dataset

The dataset `soil` has four 3D raster maps of the soil temperature on the days
from 1 to 4 March 2026. The region of the maps has 3 columns, 2 rows and 4
layers of a thickness of 2, from the bottom 0 to the top 8, so each map has 24
cells. The value of a cell is
the number of its layer plus an offset, so the smallest and largest value of
`soil_1` are 1 and 4. The offsets 0, 6, 3 and 9 make the third map colder than
the second one. A space time 3D raster dataset has the type `str3ds`, and its
maps are registered with the type `raster_3d`.

The first block lists the maps with the default columns. The second block adds
the flag **-s**, which suppresses the line with the column names, and names the
default method `cols`. The third block names the columns, among them the
smallest and largest value of each map. The fourth block lists the columns of
the volume of the first map: the extent in the plane, the cell sizes, the
thickness `tbres` of a layer and the number of layers `depths`.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 t=8 b=0 res=1 res3=1 tbres=2
    r3.mapcalc expression="soil_1 = depth()"
    r3.mapcalc expression="soil_2 = depth() + 6"
    r3.mapcalc expression="soil_3 = depth() + 3"
    r3.mapcalc expression="soil_4 = depth() + 9"
    t.create type=str3ds output=soil title="Soil temperature" \
        description="Soil temperature in four layers"
    t.register -i type=raster_3d input=soil \
        maps=soil_1,soil_2,soil_3,soil_4 \
        start=2026-03-01 increment="1 day"
    t.rast3d.list input=soil
    ```

    ```text
    name|mapset|start_time|end_time
    soil_1|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    soil_2|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    soil_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    soil_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```sh
    t.rast3d.list -s input=soil method=cols
    ```

    ```text
    soil_1|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    soil_2|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    soil_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    soil_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```sh
    t.rast3d.list input=soil columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    soil_1|2026-03-01 00:00:00|1.0|4.0
    soil_2|2026-03-02 00:00:00|7.0|10.0
    soil_3|2026-03-03 00:00:00|4.0|7.0
    soil_4|2026-03-04 00:00:00|10.0|13.0
    ```

    ```sh
    t.rast3d.list input=soil where="name = 'soil_1'" \
        columns=id,name,mapset,temporal_type,start_time,end_time,north,south,west,east,nsres,ewres,tbres,cols,rows,depths,number_of_cells,min,max
    ```

    ```text
    id|name|mapset|temporal_type|start_time|end_time|north|south|west|east|nsres|ewres|tbres|cols|rows|depths|number_of_cells|min|max
    soil_1@PERMANENT|soil_1|PERMANENT|absolute|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|0.0|0.0|3.0|1.0|1.0|2.0|3|2|4|24|1.0|4.0
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=3, w=0, t=8, b=0, res=1, res3=1, tbres=2)
    for number, offset in enumerate((0, 6, 3, 9), start=1):
        tools.r3_mapcalc(expression=f"soil_{number} = depth() + {offset}")
    tools.t_create(
        type="str3ds",
        output="soil",
        title="Soil temperature",
        description="Soil temperature in four layers",
    )
    tools.t_register(
        type="raster_3d",
        input="soil",
        maps="soil_1,soil_2,soil_3,soil_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_rast3d_list(input="soil").text)
    ```

    ```text
    name|mapset|start_time|end_time
    soil_1|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    soil_2|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    soil_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    soil_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```python
    print(tools.t_rast3d_list(input="soil", method="cols", flags="s").text)
    ```

    ```text
    soil_1|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    soil_2|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    soil_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    soil_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```python
    print(tools.t_rast3d_list(input="soil", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    soil_1|2026-03-01 00:00:00|1.0|4.0
    soil_2|2026-03-02 00:00:00|7.0|10.0
    soil_3|2026-03-03 00:00:00|4.0|7.0
    soil_4|2026-03-04 00:00:00|10.0|13.0
    ```

    ```python
    result = tools.t_rast3d_list(
        input="soil",
        where="name = 'soil_1'",
        columns=(
            "id,name,mapset,temporal_type,start_time,end_time,north,south,west,east,"
            "nsres,ewres,tbres,cols,rows,depths,number_of_cells,min,max"
        ),
    )
    print(result.text)
    ```

    ```text
    id|name|mapset|temporal_type|start_time|end_time|north|south|west|east|nsres|ewres|tbres|cols|rows|depths|number_of_cells|min|max
    soil_1@PERMANENT|soil_1|PERMANENT|absolute|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|0.0|0.0|3.0|1.0|1.0|2.0|3|2|4|24|1.0|4.0
    ```

### Select and sort the maps

The maps of `soil` are sorted by start time. The option **order** sorts by
another column; the first block sorts by `max`, so the colder third map comes
before the second one.

The option **where** selects the maps. The second block selects the maps that
start from 2 March on and before 4 March, so the second and the third map. The
third block combines a condition on the smallest value with **order**. The
fourth block uses `strftime()` to select the maps that start on the 1st or the
4th day of the month, a recurring selection that works the same way for one
month of every year.

The last block shows a trap: a time compared with `=` must be the whole text
`2026-03-02 00:00:00`, and the short form selects no map. The format `json`
shows the empty result, `data` is an empty list; the formats `plain` and
`line` stop with an error here.

=== "Command line"

    ```sh
    t.rast3d.list input=soil columns=name,max order=max
    ```

    ```text
    name|max
    soil_1|4.0
    soil_3|7.0
    soil_2|10.0
    soil_4|13.0
    ```

    ```sh
    t.rast3d.list input=soil columns=name,start_time \
        where="start_time >= '2026-03-02' and start_time < '2026-03-04'"
    ```

    ```text
    name|start_time
    soil_2|2026-03-02 00:00:00
    soil_3|2026-03-03 00:00:00
    ```

    ```sh
    t.rast3d.list input=soil columns=name,min,max order=max where="min > 3"
    ```

    ```text
    name|min|max
    soil_3|4.0|7.0
    soil_2|7.0|10.0
    soil_4|10.0|13.0
    ```

    ```sh
    t.rast3d.list input=soil columns=name,start_time \
        where="strftime('%d', start_time) in ('01', '04')"
    ```

    ```text
    name|start_time
    soil_1|2026-03-01 00:00:00
    soil_4|2026-03-04 00:00:00
    ```

    ```sh
    t.rast3d.list input=soil columns=name format=json \
        where="start_time = '2026-03-02'"
    echo
    ```

    ```text
    {"data": [], "metadata": {"column_names": ["name"]}}
    ```

=== "Python (grass.tools)"

    ```python
    print(tools.t_rast3d_list(input="soil", columns="name,max", order="max").text)
    ```

    ```text
    name|max
    soil_1|4.0
    soil_3|7.0
    soil_2|10.0
    soil_4|13.0
    ```

    ```python
    result = tools.t_rast3d_list(
        input="soil",
        columns="name,start_time",
        where="start_time >= '2026-03-02' and start_time < '2026-03-04'",
    )
    print(result.text)
    ```

    ```text
    name|start_time
    soil_2|2026-03-02 00:00:00
    soil_3|2026-03-03 00:00:00
    ```

    ```python
    result = tools.t_rast3d_list(
        input="soil", columns="name,min,max", order="max", where="min > 3"
    )
    print(result.text)
    ```

    ```text
    name|min|max
    soil_3|4.0|7.0
    soil_2|7.0|10.0
    soil_4|10.0|13.0
    ```

    ```python
    result = tools.t_rast3d_list(
        input="soil",
        columns="name,start_time",
        where="strftime('%d', start_time) in ('01', '04')",
    )
    print(result.text)
    ```

    ```text
    name|start_time
    soil_1|2026-03-01 00:00:00
    soil_4|2026-03-04 00:00:00
    ```

    ```python
    result = tools.t_rast3d_list(
        input="soil",
        columns="name",
        format="json",
        where="start_time = '2026-03-02'",
    )
    print(result.text)
    ```

    ```text
    {"data": [], "metadata": {"column_names": ["name"]}}
    ```

### Choose the output format

All blocks list the dataset `soil`. The first block prints the maps as a list
of ids in one line, the form that other tools accept as input; the second
block does the same with the old method name `comma`; the third block prints
the names only, with another separator. The fourth and fifth block print CSV
with and without the line of column names; text is quoted and numbers are not.
The sixth block replaces the separator of the plain format. The seventh block
prints JSON, which the Python tab reads from `result.json` and prints name and
`max` of each map. The eighth block writes the listing to a file and prints the
file. The ninth block shows that `output=-` writes a file named `-`.

=== "Command line"

    ```sh
    t.rast3d.list input=soil format=line
    ```

    ```text
    soil_1@PERMANENT,soil_2@PERMANENT,soil_3@PERMANENT,soil_4@PERMANENT
    ```

    ```sh
    t.rast3d.list input=soil method=comma
    ```

    ```text
    soil_1@PERMANENT,soil_2@PERMANENT,soil_3@PERMANENT,soil_4@PERMANENT
    ```

    ```sh
    t.rast3d.list input=soil format=line columns=name separator=" | "
    ```

    ```text
    soil_1 | soil_2 | soil_3 | soil_4
    ```

    ```sh
    t.rast3d.list input=soil format=csv columns=name,min,max
    ```

    ```text
    "name","min","max"
    "soil_1",1.0,4.0
    "soil_2",7.0,10.0
    "soil_3",4.0,7.0
    "soil_4",10.0,13.0
    ```

    ```sh
    t.rast3d.list -s input=soil format=csv columns=name,min,max
    ```

    ```text
    "soil_1",1.0,4.0
    "soil_2",7.0,10.0
    "soil_3",4.0,7.0
    "soil_4",10.0,13.0
    ```

    ```sh
    t.rast3d.list input=soil columns=name,min,max separator=";"
    ```

    ```text
    name;min;max
    soil_1;1.0;4.0
    soil_2;7.0;10.0
    soil_3;4.0;7.0
    soil_4;10.0;13.0
    ```

    ```sh
    t.rast3d.list input=soil columns=name,max format=json
    echo
    ```

    ```text
    {"data": [{"name": "soil_1", "max": 4.0}, {"name": "soil_2", "max": 10.0}, {"name": "soil_3", "max": 7.0}, {"name": "soil_4", "max": 13.0}], "metadata": {"column_names": ["name", "max"]}}
    ```

    ```sh
    t.rast3d.list input=soil columns=name,max output=maxima.txt
    cat maxima.txt
    ```

    ```text
    name|max
    soil_1|4.0
    soil_2|10.0
    soil_3|7.0
    soil_4|13.0
    ```

    ```sh
    t.rast3d.list input=soil columns=name output=-
    cat ./-
    ```

    ```text
    name
    soil_1
    soil_2
    soil_3
    soil_4
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    print(tools.t_rast3d_list(input="soil", format="line").text)
    ```

    ```text
    soil_1@PERMANENT,soil_2@PERMANENT,soil_3@PERMANENT,soil_4@PERMANENT
    ```

    ```python
    print(tools.t_rast3d_list(input="soil", method="comma").text)
    ```

    ```text
    soil_1@PERMANENT,soil_2@PERMANENT,soil_3@PERMANENT,soil_4@PERMANENT
    ```

    ```python
    result = tools.t_rast3d_list(
        input="soil", format="line", columns="name", separator=" | "
    )
    print(result.text)
    ```

    ```text
    soil_1 | soil_2 | soil_3 | soil_4
    ```

    ```python
    result = tools.t_rast3d_list(input="soil", format="csv", columns="name,min,max")
    print(result.text)
    ```

    ```text
    "name","min","max"
    "soil_1",1.0,4.0
    "soil_2",7.0,10.0
    "soil_3",4.0,7.0
    "soil_4",10.0,13.0
    ```

    ```python
    result = tools.t_rast3d_list(
        input="soil", format="csv", columns="name,min,max", flags="s"
    )
    print(result.text)
    ```

    ```text
    "soil_1",1.0,4.0
    "soil_2",7.0,10.0
    "soil_3",4.0,7.0
    "soil_4",10.0,13.0
    ```

    ```python
    result = tools.t_rast3d_list(input="soil", columns="name,min,max", separator=";")
    print(result.text)
    ```

    ```text
    name;min;max
    soil_1;1.0;4.0
    soil_2;7.0;10.0
    soil_3;4.0;7.0
    soil_4;10.0;13.0
    ```

    ```python
    result = tools.t_rast3d_list(input="soil", columns="name,max", format="json")
    for item in result.json["data"]:
        print(item["name"], item["max"])
    ```

    ```text
    soil_1 4.0
    soil_2 10.0
    soil_3 7.0
    soil_4 13.0
    ```

    ```python
    tools.t_rast3d_list(input="soil", columns="name,max", output="maxima.txt")
    print(Path("maxima.txt").read_text(), end="")
    ```

    ```text
    name|max
    soil_1|4.0
    soil_2|10.0
    soil_3|7.0
    soil_4|13.0
    ```

    ```python
    tools.t_rast3d_list(input="soil", columns="name", output="-")
    print(Path("-").read_text(), end="")
    ```

    ```text
    name
    soil_1
    soil_2
    soil_3
    soil_4
    ```

### Intervals, distances and gaps

The dataset `rain` has two daily maps, registered with a start and an end:
`rain_1` for 1 June 2026 and `rain_3` for 3 June, so 2 June is a gap. The
method `delta` prints the length of each map and its distance from the first
map in days; it skips the gap. The method `deltagaps` adds a line for the gap
with `None` as `id`, `name` and `mapset`, and its length. The CSV form of this
table shows `None` as an empty text.

The dataset `model` has relative time: three model steps of 6 hours. Its times,
lengths and distances are numbers of hours, printed without the unit.

=== "Command line"

    ```sh
    r3.mapcalc expression="rain_1 = 4"
    r3.mapcalc expression="rain_3 = 2"
    t.create type=str3ds output=rain title="Rain" \
        description="Daily rain with a gap"
    t.register type=raster_3d input=rain maps=rain_1 \
        start=2026-06-01 end=2026-06-02
    t.register type=raster_3d input=rain maps=rain_3 \
        start=2026-06-03 end=2026-06-04
    t.rast3d.list input=rain method=delta
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    rain_1@PERMANENT|rain_1|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    rain_3@PERMANENT|rain_3|PERMANENT|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```sh
    t.rast3d.list input=rain method=deltagaps
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    rain_1@PERMANENT|rain_1|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    None|None|None|2026-06-02 00:00:00|2026-06-03 00:00:00|1.0|1.0
    rain_3@PERMANENT|rain_3|PERMANENT|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```sh
    t.rast3d.list input=rain method=deltagaps format=csv columns=id,interval_length
    ```

    ```text
    "id","interval_length"
    "rain_1@PERMANENT",1.0
    "",1.0
    "rain_3@PERMANENT",1.0
    ```

    ```sh
    for step in 1 2 3; do
        r3.mapcalc expression="step_$step = $step"
    done
    t.create type=str3ds output=model temporaltype=relative title="Model" \
        description="Model output per step of 6 hours"
    t.register -i type=raster_3d input=model maps=step_1,step_2,step_3 \
        start=0 increment=6 unit=hours
    t.rast3d.list input=model method=delta
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    step_1@PERMANENT|step_1|PERMANENT|0|6|6|0
    step_2@PERMANENT|step_2|PERMANENT|6|12|6|6
    step_3@PERMANENT|step_3|PERMANENT|12|18|6|12
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(expression="rain_1 = 4")
    tools.r3_mapcalc(expression="rain_3 = 2")
    tools.t_create(
        type="str3ds", output="rain", title="Rain", description="Daily rain with a gap"
    )
    tools.t_register(
        type="raster_3d",
        input="rain",
        maps="rain_1",
        start="2026-06-01",
        end="2026-06-02",
    )
    tools.t_register(
        type="raster_3d",
        input="rain",
        maps="rain_3",
        start="2026-06-03",
        end="2026-06-04",
    )
    print(tools.t_rast3d_list(input="rain", method="delta").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    rain_1@PERMANENT|rain_1|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    rain_3@PERMANENT|rain_3|PERMANENT|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```python
    print(tools.t_rast3d_list(input="rain", method="deltagaps").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    rain_1@PERMANENT|rain_1|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    None|None|None|2026-06-02 00:00:00|2026-06-03 00:00:00|1.0|1.0
    rain_3@PERMANENT|rain_3|PERMANENT|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```python
    result = tools.t_rast3d_list(
        input="rain", method="deltagaps", format="csv", columns="id,interval_length"
    )
    print(result.text)
    ```

    ```text
    "id","interval_length"
    "rain_1@PERMANENT",1.0
    "",1.0
    "rain_3@PERMANENT",1.0
    ```

    ```python
    for step in (1, 2, 3):
        tools.r3_mapcalc(expression=f"step_{step} = {step}")
    tools.t_create(
        type="str3ds",
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step of 6 hours",
    )
    tools.t_register(
        type="raster_3d",
        input="model",
        maps="step_1,step_2,step_3",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    print(tools.t_rast3d_list(input="model", method="delta").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    step_1@PERMANENT|step_1|PERMANENT|0|6|6|0
    step_2@PERMANENT|step_2|PERMANENT|6|12|6|6
    step_3@PERMANENT|step_3|PERMANENT|12|18|6|12
    ```

### Sample the maps by a granule

The dataset `monthly` has four maps that start on the last day of a month
and end on the last day of the next one, from 31 January. The first block
lists them. The method `gran` with a granule of one month prints one line per
month granule: the granules start on 31 January, 28 February, 31 March and 30
April, as each start is counted in months from 31 January and cut to the last
day of a shorter month. With a granule of two months, each line covers two
maps and names the first of them. The last block samples the relative dataset
`model` of the previous example without a granule, so it uses the granularity
of the dataset, 6 hours.

=== "Command line"

    ```sh
    for month in 1 2 3 4; do
        r3.mapcalc expression="month_$month = $month"
    done
    t.create type=str3ds output=monthly title="Monthly" \
        description="Monthly maps"
    t.register -i type=raster_3d input=monthly \
        maps=month_1,month_2,month_3,month_4 \
        start=2026-01-31 increment="1 month"
    t.rast3d.list input=monthly
    ```

    ```text
    name|mapset|start_time|end_time
    month_1|PERMANENT|2026-01-31 00:00:00|2026-02-28 00:00:00
    month_2|PERMANENT|2026-02-28 00:00:00|2026-03-31 00:00:00
    month_3|PERMANENT|2026-03-31 00:00:00|2026-04-30 00:00:00
    month_4|PERMANENT|2026-04-30 00:00:00|2026-05-31 00:00:00
    ```

    ```sh
    t.rast3d.list input=monthly method=gran granule="1 month"
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    month_1@PERMANENT|month_1|PERMANENT|2026-01-31 00:00:00|2026-02-28 00:00:00|28.0|0.0
    month_2@PERMANENT|month_2|PERMANENT|2026-02-28 00:00:00|2026-03-31 00:00:00|31.0|28.0
    month_3@PERMANENT|month_3|PERMANENT|2026-03-31 00:00:00|2026-04-30 00:00:00|30.0|59.0
    month_4@PERMANENT|month_4|PERMANENT|2026-04-30 00:00:00|2026-05-31 00:00:00|31.0|89.0
    ```

    ```sh
    t.rast3d.list input=monthly method=gran granule="2 months"
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    month_1@PERMANENT|month_1|PERMANENT|2026-01-31 00:00:00|2026-03-31 00:00:00|59.0|0.0
    month_3@PERMANENT|month_3|PERMANENT|2026-03-31 00:00:00|2026-05-31 00:00:00|61.0|59.0
    ```

    ```sh
    t.rast3d.list input=model method=gran
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    step_1@PERMANENT|step_1|PERMANENT|0|6|6|0
    step_2@PERMANENT|step_2|PERMANENT|6|12|6|6
    step_3@PERMANENT|step_3|PERMANENT|12|18|6|12
    ```

=== "Python (grass.tools)"

    ```python
    for month in (1, 2, 3, 4):
        tools.r3_mapcalc(expression=f"month_{month} = {month}")
    tools.t_create(
        type="str3ds", output="monthly", title="Monthly", description="Monthly maps"
    )
    tools.t_register(
        type="raster_3d",
        input="monthly",
        maps="month_1,month_2,month_3,month_4",
        start="2026-01-31",
        increment="1 month",
        flags="i",
    )
    print(tools.t_rast3d_list(input="monthly").text)
    ```

    ```text
    name|mapset|start_time|end_time
    month_1|PERMANENT|2026-01-31 00:00:00|2026-02-28 00:00:00
    month_2|PERMANENT|2026-02-28 00:00:00|2026-03-31 00:00:00
    month_3|PERMANENT|2026-03-31 00:00:00|2026-04-30 00:00:00
    month_4|PERMANENT|2026-04-30 00:00:00|2026-05-31 00:00:00
    ```

    ```python
    result = tools.t_rast3d_list(input="monthly", method="gran", granule="1 month")
    print(result.text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    month_1@PERMANENT|month_1|PERMANENT|2026-01-31 00:00:00|2026-02-28 00:00:00|28.0|0.0
    month_2@PERMANENT|month_2|PERMANENT|2026-02-28 00:00:00|2026-03-31 00:00:00|31.0|28.0
    month_3@PERMANENT|month_3|PERMANENT|2026-03-31 00:00:00|2026-04-30 00:00:00|30.0|59.0
    month_4@PERMANENT|month_4|PERMANENT|2026-04-30 00:00:00|2026-05-31 00:00:00|31.0|89.0
    ```

    ```python
    result = tools.t_rast3d_list(input="monthly", method="gran", granule="2 months")
    print(result.text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    month_1@PERMANENT|month_1|PERMANENT|2026-01-31 00:00:00|2026-03-31 00:00:00|59.0|0.0
    month_3@PERMANENT|month_3|PERMANENT|2026-03-31 00:00:00|2026-05-31 00:00:00|61.0|59.0
    ```

    ```python
    print(tools.t_rast3d_list(input="model", method="gran").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    step_1@PERMANENT|step_1|PERMANENT|0|6|6|0
    step_2@PERMANENT|step_2|PERMANENT|6|12|6|6
    step_3@PERMANENT|step_3|PERMANENT|12|18|6|12
    ```

### Use a dataset of another mapset

*t.rast3d.list* reads a dataset of another mapset. The example creates the
mapset `other` and switches to it; the dataset `soil` stays in the mapset
`PERMANENT` and is named with its mapset. In the second block, *g.mapsets*
shows that `PERMANENT` is in the search path of the new mapset, so the name
`soil` without a mapset finds the same dataset.

=== "Command line"

    ```sh
    g.mapset -c mapset=other
    t.rast3d.list input=soil@PERMANENT columns=id,start_time
    ```

    ```text
    id|start_time
    soil_1@PERMANENT|2026-03-01 00:00:00
    soil_2@PERMANENT|2026-03-02 00:00:00
    soil_3@PERMANENT|2026-03-03 00:00:00
    soil_4@PERMANENT|2026-03-04 00:00:00
    ```

    ```sh
    g.mapsets -p
    t.rast3d.list input=soil columns=id,start_time
    ```

    ```text
    other PERMANENT
    id|start_time
    soil_1@PERMANENT|2026-03-01 00:00:00
    soil_2@PERMANENT|2026-03-02 00:00:00
    soil_3@PERMANENT|2026-03-03 00:00:00
    soil_4@PERMANENT|2026-03-04 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="other", flags="c")
    result = tools.t_rast3d_list(input="soil@PERMANENT", columns="id,start_time")
    print(result.text)
    ```

    ```text
    id|start_time
    soil_1@PERMANENT|2026-03-01 00:00:00
    soil_2@PERMANENT|2026-03-02 00:00:00
    soil_3@PERMANENT|2026-03-03 00:00:00
    soil_4@PERMANENT|2026-03-04 00:00:00
    ```

    ```python
    print(tools.g_mapsets(flags="p").text)
    print(tools.t_rast3d_list(input="soil", columns="id,start_time").text)
    ```

    ```text
    other PERMANENT
    id|start_time
    soil_1@PERMANENT|2026-03-01 00:00:00
    soil_2@PERMANENT|2026-03-02 00:00:00
    soil_3@PERMANENT|2026-03-03 00:00:00
    soil_4@PERMANENT|2026-03-04 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapsets](g.mapsets.md), [t.create](t.create.md),
[t.info](t.info.md), [t.list](t.list.md), [t.rast.list](t.rast.list.md),
[t.register](t.register.md), [t.vect.list](t.vect.list.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
