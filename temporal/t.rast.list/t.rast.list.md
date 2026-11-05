## DESCRIPTION

*t.rast.list* lists the raster maps that are registered in a space time raster
dataset, with the metadata that the temporal database holds for each map. It
reads the temporal database; the maps themselves are not opened. The
listing is the usual step after *[t.info](t.info.md)* has shown the dataset as
a whole and before a tool such as *[t.rast.univar](t.rast.univar.md)* or the
map algebra works on its maps. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. Space time 3D raster datasets have their own tool,
*[t.rast3d.list](t.rast3d.list.md)*, space time vector datasets
*[t.vect.list](t.vect.list.md)*, and *[t.list](t.list.md)* lists the datasets
themselves.

### Select the maps

The option **input** names the space time raster dataset. A semantic label
after the name, `input=name.label`, keeps only the maps with this label; the
name and the label are separated by a single dot. A dataset whose whole name
is `name.label` is found first, before the text after the dot is read as a
label; this concerns only datasets of earlier releases, which could have a dot
in their name. The mapsets are searched in turn, the current one first, and in
each the whole name is tried before the label: the dataset `name` of the
current mapset wins over a dataset `name.label` of the search path. Labels are
given to maps by
*[r.semantic.label](r.semantic.label.md)* or when the maps are registered
with *[t.register](t.register.md)*.

The option **where** takes an SQL condition on the columns of the registered
maps, such as `max > 5`, `name = 'temperature_2026_03_01'` or
`start_time >= '2026-03-02'`. Times are compared as text, so a time with a
clock part needs the whole text: `start_time = '2026-03-02'` selects nothing,
because the stored value is `2026-03-02 00:00:00`. Use `>=` and `<` for a day,
or `name` for a single map. The function `strftime()` of SQLite selects
recurring times, such as one day of the month or one month of the year. A
condition with a syntax error stops with an error that starts with "Invalid
where condition". With the methods `delta`, `deltagaps` and `gran`, the
condition selects the maps before the lengths and distances are counted, so
the distances start at 0 with the first selected map.

### Columns and order

The option **columns** chooses the columns that are printed for each map,
separated by commas. The columns are:

- `id`, the name of the map with its mapset, such as
  `temperature_2026_03_01@t_rast_list`; `name` and `mapset`, the two parts of it;
- `semantic_label`, the semantic label of the map, `None` for a map without
  one. A temporal database of version 2 has no semantic labels: asking for
  the column stops the run with an error that tells to run
  *[t.upgrade](t.upgrade.md)* first;
- `temporal_type`, `absolute` or `relative`;
- `start_time` and `end_time`, the time of the map. The end time of a map
  registered as a time instant is `None`. With relative time, they are numbers
  in the unit of the dataset, printed without the unit;
- `creator` and `creation_time`, the user who created the entry of the map in
  the temporal database and the time of its creation;
- `north`, `south`, `west` and `east`, the spatial extent of the map;
  `nsres` and `ewres`, its cell sizes; `cols`, `rows` and `number_of_cells`,
  its size in cells;
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
columns only, no sort direction. The option works with the method `list` only.

### Methods

The option **method** chooses what is listed. The default is `list`.

- `list` prints one line per registered map with the columns of **columns**.
  Without **columns**, these are `name`, `mapset`, `start_time` and
  `end_time`; with `format=line`, the column `id`. It supports all columns
  except `interval_length` and `distance_from_begin`, and it is the only
  method that **order** applies to.
- `delta` prints the maps ordered by start time with the length of their
  intervals and their distance from the first map. Without **columns**, the
  columns are `id`, `name`, `mapset`, `start_time`, `end_time`,
  `interval_length` and `distance_from_begin`. The length of a time instant is
  `None`. `delta` supports only these columns.
- `deltagaps` is `delta` with a line for every temporal gap. A gap is time
  that no map covers. A gap line has `None` as `id`, `name` and `mapset`; its
  times are the latest end of the maps before the gap and the start of the map
  after it, and its length is the length of the gap. Maps that follow each
  other directly leave no gap, and neither does a map that ends inside a longer
  one: of maps from 1 to 11 January, 3 to 5 January and 8 to 13 January, the
  first covers 5 to 8 January.
- `gran` samples the maps by a granule and prints one line per granule, with the
  columns of `delta`. The times and the length are those of the granule, not of
  the map, so a map that is longer than the granule is listed once for each
  granule it covers. A granule without a map has `None` as `id`, `name` and
  `mapset`. When more than one map meets a granule, the line names the map with
  the earliest start of the first of these groups that is not empty: maps that
  are equal to the granule, maps that contain it, maps that start inside it and
  end after it, maps that start before it and end inside it, and maps that lie
  inside it. `gran` refuses a dataset without maps.
- `cols` and `comma` are the old names of the formats `plain` and `line`.
  `cols` is the same as `list`, and `comma` is `list` with `format=line`.
  Prefer the option **format**.

The option **granule** is the granule of the method `gran`. For absolute time it
is a text with a number and a time unit, such as `"2 months"`. For relative time
it is a whole number of at least 1 in the time unit of the dataset, also
followed by this unit: `12`, `"12 hours"` and `"12 hour"` are the same granule
of a dataset in hours. Another unit, such as `"1 day"` for a dataset in hours,
is refused with the error "Invalid granule". Without **granule**, the
granularity of the dataset is used. The first granule starts with the first map,
and the granules reach the latest end of the maps, also when a shorter map
starts last. Each later start is counted in whole granules from the start of the
dataset when the first selected map lies whole granules after it, otherwise from
the first selected map; this matters when **where** selects later maps only. A
step of months or years that ends behind the last day of a shorter month ends on
that day: with a granule of one month and a first map from 31 January, the
granules start on 31 January, 28 February, 31 March and 30 April. Such a series
has the granularity one month (see *[t.info](t.info.md)*), so `gran` without
**granule** samples it by months as well. The other methods ignore **granule**.

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

The flag **-u** suppresses the line with the column names in the formats
`plain` and `csv`. The formats `json` and `yaml` always name the columns and
refuse **-u**.

The option **separator** replaces the separator of the formats `plain`, `csv`
and `line`. It is a single character or a name such as `pipe`, `comma` or
`tab`. The format `csv` accepts one character only, and `json` and `yaml`
refuse **separator**. The option **output** writes the listing to a file
instead of the standard output.

## NOTES

If no map is listed, the result depends on the method and the format. With the
method `list` and the formats `plain` and `line`, *t.rast.list* stops with the
error "Nothing found in the database for space time dataset `<name@mapset>`
(type: strds)", followed by "Dataset is empty" for a dataset without maps and by
"Dataset is empty or where clause is too constrained or incorrect" when
**where** is given. With the format `json`, `data` is an empty list. The methods
`delta` and `deltagaps` print the line with the column names only, both for a
dataset without maps and when **where** selects nothing. The method `gran` does
the same when **where** selects nothing in a dataset that has a granularity, but
stops for a dataset without maps with the error "Dataset is empty". A dataset
with a single map that is a time instant has no granularity, and `gran` without
**granule** stops for it with the error that the dataset has no granularity,
whatever **where** selects. Give a **granule**, such as `"1 day"`, or use
`delta`.

A map without a start time is listed by `delta` and `deltagaps` with `None`
in all time columns, and *t.rast.list* warns about it. The distances count from
the first map that has a start time.

The first example shows the format of a dataset with absolute time, the
dataset `model` in the fifth example the format of one with relative time:
the times are numbers of the time unit of the dataset, printed without the
unit. The method `gran` works with relative time with and without
**granule**, as the example "Sample the maps by a granule" shows.

The option **output** takes the name of a file; the name `-` is the standard
output, as the last block of the "Choose the output format" example shows.

*t.rast.list* only reads, so it works on a dataset of another mapset as well.
The name with the mapset (`input=temperature@t_rast_list`) selects it; a name
without a mapset is searched in the mapsets of the search path (see
*[g.mapsets](g.mapsets.md)*). The last example shows this.

Combinations that cannot work are refused with a message that names the
options: **order** with `delta`, `deltagaps` or `gran`; a column of the
temporal database with these methods and `interval_length` or
`distance_from_begin` with `list`; more than one column with `format=line`;
**-u** or **separator** with `json` or `yaml`; a separator of more than one
character with `csv`. A granule of absolute time without a time unit (`"2"`)
or with an unknown unit (`"3 foo"`) is refused with the error "Wrong
granularity".

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_list` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset and
region. *t.rast.list* reads the temporal database only, so the maps hold small
integer values in two halves: the first 167 rows, counted from the north, hold
the low value of the map, the remaining rows the high value, and the smallest
and the largest value of a map are these two values.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_list -->

<!-- markdownlint-disable MD046 -->

### List the maps of a dataset

The dataset `temperature` has four maps of daily mean air temperature over
North Carolina for the days from 1 to 4 March 2026. The northern half of each
map holds the low value and the southern half the high value, in degrees
Celsius: 1 and 3, 7 and 9, 4 and 6, 10 and 12. The smallest and largest value
of `temperature_2026_03_01` are therefore 1 and 3, and the third map is colder
than the second one.

The first block lists the maps with the default columns. The second block adds
the flag **-u**, which suppresses the line with the column names. The third
block names the columns, among them the smallest and largest value of each
map. The fourth block lists all columns of the first map except `creator` and
`creation_time`, which differ from user to user and from day to day. The map
has no semantic label, and its extent is the computational region of 839 by
335 cells of 1000 m.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_list
    g.region raster=elev_state_500m res=1000 -a
    r.mapcalc expression="temperature_2026_03_01 = if(row() <= 167, 1, 3)"
    r.mapcalc expression="temperature_2026_03_02 = if(row() <= 167, 7, 9)"
    r.mapcalc expression="temperature_2026_03_03 = if(row() <= 167, 4, 6)"
    r.mapcalc expression="temperature_2026_03_04 = if(row() <= 167, 10, 12)"
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature in degree Celsius"
    t.register -i input=temperature \
        maps=temperature_2026_03_01,temperature_2026_03_02,temperature_2026_03_03,temperature_2026_03_04 \
        start=2026-03-01 increment="1 day"
    t.rast.list input=temperature
    ```

    ```text
    name|mapset|start_time|end_time
    temperature_2026_03_01|t_rast_list|2026-03-01 00:00:00|2026-03-02 00:00:00
    temperature_2026_03_02|t_rast_list|2026-03-02 00:00:00|2026-03-03 00:00:00
    temperature_2026_03_03|t_rast_list|2026-03-03 00:00:00|2026-03-04 00:00:00
    temperature_2026_03_04|t_rast_list|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```sh
    t.rast.list -u input=temperature
    ```

    ```text
    temperature_2026_03_01|t_rast_list|2026-03-01 00:00:00|2026-03-02 00:00:00
    temperature_2026_03_02|t_rast_list|2026-03-02 00:00:00|2026-03-03 00:00:00
    temperature_2026_03_03|t_rast_list|2026-03-03 00:00:00|2026-03-04 00:00:00
    temperature_2026_03_04|t_rast_list|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```sh
    t.rast.list input=temperature columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    temperature_2026_03_01|2026-03-01 00:00:00|1.0|3.0
    temperature_2026_03_02|2026-03-02 00:00:00|7.0|9.0
    temperature_2026_03_03|2026-03-03 00:00:00|4.0|6.0
    temperature_2026_03_04|2026-03-04 00:00:00|10.0|12.0
    ```

    ```sh
    t.rast.list input=temperature where="name = 'temperature_2026_03_01'" \
        columns=id,name,semantic_label,mapset,temporal_type,start_time,end_time,north,south,west,east,nsres,ewres,cols,rows,number_of_cells,min,max
    ```

    ```text
    id|name|semantic_label|mapset|temporal_type|start_time|end_time|north|south|west|east|nsres|ewres|cols|rows|number_of_cells|min|max
    temperature_2026_03_01@t_rast_list|temperature_2026_03_01|None|t_rast_list|absolute|2026-03-01 00:00:00|2026-03-02 00:00:00|319000.0|-16000.0|124000.0|963000.0|1000.0|1000.0|839|335|281065|1.0|3.0
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast_list")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for day, (low, high) in enumerate(((1, 3), (7, 9), (4, 6), (10, 12)), start=1):
        expression = f"temperature_2026_03_0{day} = if(row() <= 167, {low}, {high})"
        tools.r_mapcalc(expression=expression)
    tools.t_create(
        output="temperature",
        title="Air temperature",
        description="Daily mean air temperature in degree Celsius",
    )
    tools.t_register(
        input="temperature",
        maps="temperature_2026_03_01,temperature_2026_03_02,temperature_2026_03_03,temperature_2026_03_04",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_rast_list(input="temperature").text)
    ```

    ```text
    name|mapset|start_time|end_time
    temperature_2026_03_01|t_rast_list|2026-03-01 00:00:00|2026-03-02 00:00:00
    temperature_2026_03_02|t_rast_list|2026-03-02 00:00:00|2026-03-03 00:00:00
    temperature_2026_03_03|t_rast_list|2026-03-03 00:00:00|2026-03-04 00:00:00
    temperature_2026_03_04|t_rast_list|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```python
    print(tools.t_rast_list(input="temperature", flags="u").text)
    ```

    ```text
    temperature_2026_03_01|t_rast_list|2026-03-01 00:00:00|2026-03-02 00:00:00
    temperature_2026_03_02|t_rast_list|2026-03-02 00:00:00|2026-03-03 00:00:00
    temperature_2026_03_03|t_rast_list|2026-03-03 00:00:00|2026-03-04 00:00:00
    temperature_2026_03_04|t_rast_list|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```python
    print(tools.t_rast_list(input="temperature", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    temperature_2026_03_01|2026-03-01 00:00:00|1.0|3.0
    temperature_2026_03_02|2026-03-02 00:00:00|7.0|9.0
    temperature_2026_03_03|2026-03-03 00:00:00|4.0|6.0
    temperature_2026_03_04|2026-03-04 00:00:00|10.0|12.0
    ```

    ```python
    result = tools.t_rast_list(
        input="temperature",
        where="name = 'temperature_2026_03_01'",
        columns=(
            "id,name,semantic_label,mapset,temporal_type,start_time,end_time,"
            "north,south,west,east,nsres,ewres,cols,rows,number_of_cells,min,max"
        ),
    )
    print(result.text)
    ```

    ```text
    id|name|semantic_label|mapset|temporal_type|start_time|end_time|north|south|west|east|nsres|ewres|cols|rows|number_of_cells|min|max
    temperature_2026_03_01@t_rast_list|temperature_2026_03_01|None|t_rast_list|absolute|2026-03-01 00:00:00|2026-03-02 00:00:00|319000.0|-16000.0|124000.0|963000.0|1000.0|1000.0|839|335|281065|1.0|3.0
    ```

### Select and sort the maps

The maps of `temperature` are sorted by start time. The option **order**
sorts by another column; the first block sorts by `max`, so the colder third
map comes before the second one.

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
    t.rast.list input=temperature columns=name,max order=max
    ```

    ```text
    name|max
    temperature_2026_03_01|3.0
    temperature_2026_03_03|6.0
    temperature_2026_03_02|9.0
    temperature_2026_03_04|12.0
    ```

    ```sh
    t.rast.list input=temperature columns=name,start_time \
        where="start_time >= '2026-03-02' and start_time < '2026-03-04'"
    ```

    ```text
    name|start_time
    temperature_2026_03_02|2026-03-02 00:00:00
    temperature_2026_03_03|2026-03-03 00:00:00
    ```

    ```sh
    t.rast.list input=temperature columns=name,min,max order=max where="min > 3"
    ```

    ```text
    name|min|max
    temperature_2026_03_03|4.0|6.0
    temperature_2026_03_02|7.0|9.0
    temperature_2026_03_04|10.0|12.0
    ```

    ```sh
    t.rast.list input=temperature columns=name,start_time \
        where="strftime('%d', start_time) in ('01', '04')"
    ```

    ```text
    name|start_time
    temperature_2026_03_01|2026-03-01 00:00:00
    temperature_2026_03_04|2026-03-04 00:00:00
    ```

    ```sh
    t.rast.list input=temperature columns=name format=json \
        where="start_time = '2026-03-02'"
    echo
    ```

    ```text
    {"data": [], "metadata": {"column_names": ["name"]}}
    ```

=== "Python (grass.tools)"

    ```python
    print(tools.t_rast_list(input="temperature", columns="name,max", order="max").text)
    ```

    ```text
    name|max
    temperature_2026_03_01|3.0
    temperature_2026_03_03|6.0
    temperature_2026_03_02|9.0
    temperature_2026_03_04|12.0
    ```

    ```python
    result = tools.t_rast_list(
        input="temperature",
        columns="name,start_time",
        where="start_time >= '2026-03-02' and start_time < '2026-03-04'",
    )
    print(result.text)
    ```

    ```text
    name|start_time
    temperature_2026_03_02|2026-03-02 00:00:00
    temperature_2026_03_03|2026-03-03 00:00:00
    ```

    ```python
    result = tools.t_rast_list(
        input="temperature", columns="name,min,max", order="max", where="min > 3"
    )
    print(result.text)
    ```

    ```text
    name|min|max
    temperature_2026_03_03|4.0|6.0
    temperature_2026_03_02|7.0|9.0
    temperature_2026_03_04|10.0|12.0
    ```

    ```python
    result = tools.t_rast_list(
        input="temperature",
        columns="name,start_time",
        where="strftime('%d', start_time) in ('01', '04')",
    )
    print(result.text)
    ```

    ```text
    name|start_time
    temperature_2026_03_01|2026-03-01 00:00:00
    temperature_2026_03_04|2026-03-04 00:00:00
    ```

    ```python
    result = tools.t_rast_list(
        input="temperature",
        columns="name",
        format="json",
        where="start_time = '2026-03-02'",
    )
    print(result.text)
    ```

    ```text
    {"data": [], "metadata": {"column_names": ["name"]}}
    ```

### Select maps by semantic label

The dataset `sentinel` has two scenes, on 1 and 11 June 2026, each with a red
band (`S2_B4`) and a near infrared band (`S2_B8`) of constant reflectance. The
maps are registered at an instant, without an end, so their `end_time` is
`None`. The name of the dataset followed by a dot and a label,
`sentinel.S2_B8`, lists the maps with this label. The second block adds
**where** to the selection by label.

=== "Command line"

    ```sh
    r.mapcalc expression="red_2026_06_01 = 0.05"
    r.mapcalc expression="red_2026_06_11 = 0.06"
    r.mapcalc expression="nir_2026_06_01 = 0.35"
    r.mapcalc expression="nir_2026_06_11 = 0.45"
    for date in 2026_06_01 2026_06_11; do
        r.support map=red_$date semantic_label=S2_B4
        r.support map=nir_$date semantic_label=S2_B8
    done
    t.create output=sentinel title="Reflectance" \
        description="Red and near infrared"
    t.register input=sentinel maps=red_2026_06_01,nir_2026_06_01 \
        start="2026-06-01 10:30:00"
    t.register input=sentinel maps=red_2026_06_11,nir_2026_06_11 \
        start="2026-06-11 10:30:00"
    t.rast.list input=sentinel.S2_B8
    ```

    ```text
    name|mapset|start_time|end_time
    nir_2026_06_01|t_rast_list|2026-06-01 10:30:00|None
    nir_2026_06_11|t_rast_list|2026-06-11 10:30:00|None
    ```

    ```sh
    t.rast.list input=sentinel.S2_B4 columns=name,semantic_label,start_time \
        where="start_time >= '2026-06-10'"
    ```

    ```text
    name|semantic_label|start_time
    red_2026_06_11|S2_B4|2026-06-11 10:30:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="red_2026_06_01 = 0.05")
    tools.r_mapcalc(expression="red_2026_06_11 = 0.06")
    tools.r_mapcalc(expression="nir_2026_06_01 = 0.35")
    tools.r_mapcalc(expression="nir_2026_06_11 = 0.45")
    for date in ("2026_06_01", "2026_06_11"):
        tools.r_support(map=f"red_{date}", semantic_label="S2_B4")
        tools.r_support(map=f"nir_{date}", semantic_label="S2_B8")
    tools.t_create(
        output="sentinel", title="Reflectance", description="Red and near infrared"
    )
    tools.t_register(
        input="sentinel",
        maps="red_2026_06_01,nir_2026_06_01",
        start="2026-06-01 10:30:00",
    )
    tools.t_register(
        input="sentinel",
        maps="red_2026_06_11,nir_2026_06_11",
        start="2026-06-11 10:30:00",
    )
    print(tools.t_rast_list(input="sentinel.S2_B8").text)
    ```

    ```text
    name|mapset|start_time|end_time
    nir_2026_06_01|t_rast_list|2026-06-01 10:30:00|None
    nir_2026_06_11|t_rast_list|2026-06-11 10:30:00|None
    ```

    ```python
    result = tools.t_rast_list(
        input="sentinel.S2_B4",
        columns="name,semantic_label,start_time",
        where="start_time >= '2026-06-10'",
    )
    print(result.text)
    ```

    ```text
    name|semantic_label|start_time
    red_2026_06_11|S2_B4|2026-06-11 10:30:00
    ```

### Choose the output format

All blocks list the dataset `temperature`. The first block prints the maps as
a list of ids in one line, the form that other tools accept as input; the
second block does the same with the names only and with another separator.
The third and fourth block print CSV with and without the line of column
names; text is quoted and numbers are not. The fifth block replaces the
separator of the plain format. The sixth block prints JSON, which the Python
tab reads from `result.json` and prints name and `max` of each map. The
seventh block writes the listing to a file and prints the file. The eighth
block prints the listing with `output=-`, the standard output.

=== "Command line"

    ```sh
    t.rast.list input=temperature format=line
    ```

    ```text
    temperature_2026_03_01@t_rast_list,temperature_2026_03_02@t_rast_list,temperature_2026_03_03@t_rast_list,temperature_2026_03_04@t_rast_list
    ```

    ```sh
    t.rast.list input=temperature format=line columns=name separator=" | "
    ```

    ```text
    temperature_2026_03_01 | temperature_2026_03_02 | temperature_2026_03_03 | temperature_2026_03_04
    ```

    ```sh
    t.rast.list input=temperature format=csv columns=name,min,max
    ```

    ```text
    "name","min","max"
    "temperature_2026_03_01",1.0,3.0
    "temperature_2026_03_02",7.0,9.0
    "temperature_2026_03_03",4.0,6.0
    "temperature_2026_03_04",10.0,12.0
    ```

    ```sh
    t.rast.list -u input=temperature format=csv columns=name,min,max
    ```

    ```text
    "temperature_2026_03_01",1.0,3.0
    "temperature_2026_03_02",7.0,9.0
    "temperature_2026_03_03",4.0,6.0
    "temperature_2026_03_04",10.0,12.0
    ```

    ```sh
    t.rast.list input=temperature columns=name,min,max separator=";"
    ```

    ```text
    name;min;max
    temperature_2026_03_01;1.0;3.0
    temperature_2026_03_02;7.0;9.0
    temperature_2026_03_03;4.0;6.0
    temperature_2026_03_04;10.0;12.0
    ```

    ```sh
    t.rast.list input=temperature columns=name,max format=json
    echo
    ```

    ```text
    {"data": [{"name": "temperature_2026_03_01", "max": 3.0}, {"name": "temperature_2026_03_02", "max": 9.0}, {"name": "temperature_2026_03_03", "max": 6.0}, {"name": "temperature_2026_03_04", "max": 12.0}], "metadata": {"column_names": ["name", "max"]}}
    ```

    ```sh
    t.rast.list input=temperature columns=name,max output=maxima.txt
    cat maxima.txt
    ```

    ```text
    name|max
    temperature_2026_03_01|3.0
    temperature_2026_03_02|9.0
    temperature_2026_03_03|6.0
    temperature_2026_03_04|12.0
    ```

    ```sh
    t.rast.list input=temperature columns=name output=-
    ```

    ```text
    name
    temperature_2026_03_01
    temperature_2026_03_02
    temperature_2026_03_03
    temperature_2026_03_04
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    print(tools.t_rast_list(input="temperature", format="line").text)
    ```

    ```text
    temperature_2026_03_01@t_rast_list,temperature_2026_03_02@t_rast_list,temperature_2026_03_03@t_rast_list,temperature_2026_03_04@t_rast_list
    ```

    ```python
    result = tools.t_rast_list(
        input="temperature", format="line", columns="name", separator=" | "
    )
    print(result.text)
    ```

    ```text
    temperature_2026_03_01 | temperature_2026_03_02 | temperature_2026_03_03 | temperature_2026_03_04
    ```

    ```python
    result = tools.t_rast_list(input="temperature", format="csv", columns="name,min,max")
    print(result.text)
    ```

    ```text
    "name","min","max"
    "temperature_2026_03_01",1.0,3.0
    "temperature_2026_03_02",7.0,9.0
    "temperature_2026_03_03",4.0,6.0
    "temperature_2026_03_04",10.0,12.0
    ```

    ```python
    result = tools.t_rast_list(
        input="temperature", format="csv", columns="name,min,max", flags="u"
    )
    print(result.text)
    ```

    ```text
    "temperature_2026_03_01",1.0,3.0
    "temperature_2026_03_02",7.0,9.0
    "temperature_2026_03_03",4.0,6.0
    "temperature_2026_03_04",10.0,12.0
    ```

    ```python
    result = tools.t_rast_list(input="temperature", columns="name,min,max", separator=";")
    print(result.text)
    ```

    ```text
    name;min;max
    temperature_2026_03_01;1.0;3.0
    temperature_2026_03_02;7.0;9.0
    temperature_2026_03_03;4.0;6.0
    temperature_2026_03_04;10.0;12.0
    ```

    ```python
    result = tools.t_rast_list(input="temperature", columns="name,max", format="json")
    for item in result.json["data"]:
        print(item["name"], item["max"])
    ```

    ```text
    temperature_2026_03_01 3.0
    temperature_2026_03_02 9.0
    temperature_2026_03_03 6.0
    temperature_2026_03_04 12.0
    ```

    ```python
    tools.t_rast_list(input="temperature", columns="name,max", output="maxima.txt")
    print(Path("maxima.txt").read_text(), end="")
    ```

    ```text
    name|max
    temperature_2026_03_01|3.0
    temperature_2026_03_02|9.0
    temperature_2026_03_03|6.0
    temperature_2026_03_04|12.0
    ```

    ```python
    print(tools.t_rast_list(input="temperature", columns="name", output="-").text)
    ```

    ```text
    name
    temperature_2026_03_01
    temperature_2026_03_02
    temperature_2026_03_03
    temperature_2026_03_04
    ```

### Intervals, distances and gaps

The dataset `rain` has two daily maps, registered with a start and an end:
`rain_2026_06_01` for 1 June 2026 and `rain_2026_06_03` for 3 June, so 2 June
is a gap. The method `delta` prints the length of each map and its distance
from the first map in days; it skips the gap. The method `deltagaps` adds a
line for the gap with `None` as `id`, `name` and `mapset`, and its length.
The CSV form of this table shows `None` as an empty text.

The dataset `model` has relative time: three model steps of 6 hours. Its times,
lengths and distances are numbers of hours, printed without the unit.

=== "Command line"

    ```sh
    r.mapcalc expression="rain_2026_06_01 = 4"
    r.mapcalc expression="rain_2026_06_03 = 2"
    t.create output=rain title="Rain" \
        description="Daily rain in mm with a gap"
    t.register input=rain maps=rain_2026_06_01 start=2026-06-01 end=2026-06-02
    t.register input=rain maps=rain_2026_06_03 start=2026-06-03 end=2026-06-04
    t.rast.list input=rain method=delta
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    rain_2026_06_01@t_rast_list|rain_2026_06_01|t_rast_list|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    rain_2026_06_03@t_rast_list|rain_2026_06_03|t_rast_list|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```sh
    t.rast.list input=rain method=deltagaps
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    rain_2026_06_01@t_rast_list|rain_2026_06_01|t_rast_list|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    None|None|None|2026-06-02 00:00:00|2026-06-03 00:00:00|1.0|1.0
    rain_2026_06_03@t_rast_list|rain_2026_06_03|t_rast_list|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```sh
    t.rast.list input=rain method=deltagaps format=csv columns=id,interval_length
    ```

    ```text
    "id","interval_length"
    "rain_2026_06_01@t_rast_list",1.0
    "",1.0
    "rain_2026_06_03@t_rast_list",1.0
    ```

    ```sh
    for step in 1 2 3; do
        r.mapcalc expression="runoff_$step = $step"
    done
    t.create output=model temporaltype=relative title="Model" \
        description="Simulated runoff in mm per model step of 6 hours"
    t.register -i input=model maps=runoff_1,runoff_2,runoff_3 \
        start=0 increment=6 unit=hours
    t.rast.list input=model method=delta
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast_list|runoff_1|t_rast_list|0|6|6|0
    runoff_2@t_rast_list|runoff_2|t_rast_list|6|12|6|6
    runoff_3@t_rast_list|runoff_3|t_rast_list|12|18|6|12
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="rain_2026_06_01 = 4")
    tools.r_mapcalc(expression="rain_2026_06_03 = 2")
    tools.t_create(output="rain", title="Rain", description="Daily rain in mm with a gap")
    tools.t_register(
        input="rain", maps="rain_2026_06_01", start="2026-06-01", end="2026-06-02"
    )
    tools.t_register(
        input="rain", maps="rain_2026_06_03", start="2026-06-03", end="2026-06-04"
    )
    print(tools.t_rast_list(input="rain", method="delta").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    rain_2026_06_01@t_rast_list|rain_2026_06_01|t_rast_list|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    rain_2026_06_03@t_rast_list|rain_2026_06_03|t_rast_list|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```python
    print(tools.t_rast_list(input="rain", method="deltagaps").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    rain_2026_06_01@t_rast_list|rain_2026_06_01|t_rast_list|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    None|None|None|2026-06-02 00:00:00|2026-06-03 00:00:00|1.0|1.0
    rain_2026_06_03@t_rast_list|rain_2026_06_03|t_rast_list|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```python
    result = tools.t_rast_list(
        input="rain", method="deltagaps", format="csv", columns="id,interval_length"
    )
    print(result.text)
    ```

    ```text
    "id","interval_length"
    "rain_2026_06_01@t_rast_list",1.0
    "",1.0
    "rain_2026_06_03@t_rast_list",1.0
    ```

    ```python
    for step in (1, 2, 3):
        tools.r_mapcalc(expression=f"runoff_{step} = {step}")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Simulated runoff in mm per model step of 6 hours",
    )
    tools.t_register(
        input="model",
        maps="runoff_1,runoff_2,runoff_3",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    print(tools.t_rast_list(input="model", method="delta").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast_list|runoff_1|t_rast_list|0|6|6|0
    runoff_2@t_rast_list|runoff_2|t_rast_list|6|12|6|6
    runoff_3@t_rast_list|runoff_3|t_rast_list|12|18|6|12
    ```

### Sample the maps by a granule

The dataset `monthly` has four maps that start on the last day of a month
and end on the last day of the next one, from 31 January. The first block
lists them. The method `gran` with a granule of one month prints one line per
month granule: the granules start on 31 January, 28 February, 31 March and 30
April, as each start is counted in months from 31 January and cut to the last
day of a shorter month. With a granule of two months, each line covers two
maps and names the first of them. Without a granule, `gran` takes the
granularity of the dataset, one month, and prints the same lines as with
`"1 month"`. The last blocks sample the relative dataset `model` of the
previous example: without a granule by the granularity of the dataset, 6
hours, and with the granule `12`, a number of hours; `"12 hours"` is the same
granule.

=== "Command line"

    ```sh
    r.mapcalc expression="precipitation_month_1 = 80"
    r.mapcalc expression="precipitation_month_2 = 95"
    r.mapcalc expression="precipitation_month_3 = 110"
    r.mapcalc expression="precipitation_month_4 = 90"
    t.create output=monthly title="Monthly" \
        description="Monthly precipitation in mm"
    t.register -i input=monthly \
        maps=precipitation_month_1,precipitation_month_2,precipitation_month_3,precipitation_month_4 \
        start=2026-01-31 increment="1 month"
    t.rast.list input=monthly
    ```

    ```text
    name|mapset|start_time|end_time
    precipitation_month_1|t_rast_list|2026-01-31 00:00:00|2026-02-28 00:00:00
    precipitation_month_2|t_rast_list|2026-02-28 00:00:00|2026-03-31 00:00:00
    precipitation_month_3|t_rast_list|2026-03-31 00:00:00|2026-04-30 00:00:00
    precipitation_month_4|t_rast_list|2026-04-30 00:00:00|2026-05-31 00:00:00
    ```

    ```sh
    t.rast.list input=monthly method=gran granule="1 month"
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    precipitation_month_1@t_rast_list|precipitation_month_1|t_rast_list|2026-01-31 00:00:00|2026-02-28 00:00:00|28.0|0.0
    precipitation_month_2@t_rast_list|precipitation_month_2|t_rast_list|2026-02-28 00:00:00|2026-03-31 00:00:00|31.0|28.0
    precipitation_month_3@t_rast_list|precipitation_month_3|t_rast_list|2026-03-31 00:00:00|2026-04-30 00:00:00|30.0|59.0
    precipitation_month_4@t_rast_list|precipitation_month_4|t_rast_list|2026-04-30 00:00:00|2026-05-31 00:00:00|31.0|89.0
    ```

    ```sh
    t.rast.list input=monthly method=gran granule="2 months"
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    precipitation_month_1@t_rast_list|precipitation_month_1|t_rast_list|2026-01-31 00:00:00|2026-03-31 00:00:00|59.0|0.0
    precipitation_month_3@t_rast_list|precipitation_month_3|t_rast_list|2026-03-31 00:00:00|2026-05-31 00:00:00|61.0|59.0
    ```

    ```sh
    t.rast.list input=monthly method=gran
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    precipitation_month_1@t_rast_list|precipitation_month_1|t_rast_list|2026-01-31 00:00:00|2026-02-28 00:00:00|28.0|0.0
    precipitation_month_2@t_rast_list|precipitation_month_2|t_rast_list|2026-02-28 00:00:00|2026-03-31 00:00:00|31.0|28.0
    precipitation_month_3@t_rast_list|precipitation_month_3|t_rast_list|2026-03-31 00:00:00|2026-04-30 00:00:00|30.0|59.0
    precipitation_month_4@t_rast_list|precipitation_month_4|t_rast_list|2026-04-30 00:00:00|2026-05-31 00:00:00|31.0|89.0
    ```

    ```sh
    t.rast.list input=model method=gran
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast_list|runoff_1|t_rast_list|0|6|6|0
    runoff_2@t_rast_list|runoff_2|t_rast_list|6|12|6|6
    runoff_3@t_rast_list|runoff_3|t_rast_list|12|18|6|12
    ```

    ```sh
    t.rast.list input=model method=gran granule=12
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast_list|runoff_1|t_rast_list|0|12|12|0
    runoff_3@t_rast_list|runoff_3|t_rast_list|12|24|12|12
    ```

=== "Python (grass.tools)"

    ```python
    for month, value in enumerate((80, 95, 110, 90), start=1):
        tools.r_mapcalc(expression=f"precipitation_month_{month} = {value}")
    tools.t_create(
        output="monthly", title="Monthly", description="Monthly precipitation in mm"
    )
    tools.t_register(
        input="monthly",
        maps=(
            "precipitation_month_1,precipitation_month_2,"
            "precipitation_month_3,precipitation_month_4"
        ),
        start="2026-01-31",
        increment="1 month",
        flags="i",
    )
    print(tools.t_rast_list(input="monthly").text)
    ```

    ```text
    name|mapset|start_time|end_time
    precipitation_month_1|t_rast_list|2026-01-31 00:00:00|2026-02-28 00:00:00
    precipitation_month_2|t_rast_list|2026-02-28 00:00:00|2026-03-31 00:00:00
    precipitation_month_3|t_rast_list|2026-03-31 00:00:00|2026-04-30 00:00:00
    precipitation_month_4|t_rast_list|2026-04-30 00:00:00|2026-05-31 00:00:00
    ```

    ```python
    print(tools.t_rast_list(input="monthly", method="gran", granule="1 month").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    precipitation_month_1@t_rast_list|precipitation_month_1|t_rast_list|2026-01-31 00:00:00|2026-02-28 00:00:00|28.0|0.0
    precipitation_month_2@t_rast_list|precipitation_month_2|t_rast_list|2026-02-28 00:00:00|2026-03-31 00:00:00|31.0|28.0
    precipitation_month_3@t_rast_list|precipitation_month_3|t_rast_list|2026-03-31 00:00:00|2026-04-30 00:00:00|30.0|59.0
    precipitation_month_4@t_rast_list|precipitation_month_4|t_rast_list|2026-04-30 00:00:00|2026-05-31 00:00:00|31.0|89.0
    ```

    ```python
    print(tools.t_rast_list(input="monthly", method="gran", granule="2 months").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    precipitation_month_1@t_rast_list|precipitation_month_1|t_rast_list|2026-01-31 00:00:00|2026-03-31 00:00:00|59.0|0.0
    precipitation_month_3@t_rast_list|precipitation_month_3|t_rast_list|2026-03-31 00:00:00|2026-05-31 00:00:00|61.0|59.0
    ```

    ```python
    print(tools.t_rast_list(input="monthly", method="gran").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    precipitation_month_1@t_rast_list|precipitation_month_1|t_rast_list|2026-01-31 00:00:00|2026-02-28 00:00:00|28.0|0.0
    precipitation_month_2@t_rast_list|precipitation_month_2|t_rast_list|2026-02-28 00:00:00|2026-03-31 00:00:00|31.0|28.0
    precipitation_month_3@t_rast_list|precipitation_month_3|t_rast_list|2026-03-31 00:00:00|2026-04-30 00:00:00|30.0|59.0
    precipitation_month_4@t_rast_list|precipitation_month_4|t_rast_list|2026-04-30 00:00:00|2026-05-31 00:00:00|31.0|89.0
    ```

    ```python
    print(tools.t_rast_list(input="model", method="gran").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast_list|runoff_1|t_rast_list|0|6|6|0
    runoff_2@t_rast_list|runoff_2|t_rast_list|6|12|6|6
    runoff_3@t_rast_list|runoff_3|t_rast_list|12|18|6|12
    ```

    ```python
    print(tools.t_rast_list(input="model", method="gran", granule="12 hours").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast_list|runoff_1|t_rast_list|0|12|12|0
    runoff_3@t_rast_list|runoff_3|t_rast_list|12|24|12|12
    ```

### Use a dataset of another mapset

*t.rast.list* reads a dataset of another mapset. The example creates the
mapset `t_rast_list_2` and switches to it; the dataset `temperature` stays in
the mapset `t_rast_list`, which is not in the search path of the new mapset,
and is named with its mapset. In the second block, *g.mapsets* adds
`t_rast_list` to the search path of the new mapset and prints the search path,
because a name without a mapset is searched only there (see
[Datasets of other mapsets](temporalintro.md#datasets-of-other-mapsets)); the name
`temperature` then finds the same dataset.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_list_2
    g.region raster=elev_state_500m res=1000 -a
    t.rast.list input=temperature@t_rast_list columns=id,start_time
    ```

    ```text
    id|start_time
    temperature_2026_03_01@t_rast_list|2026-03-01 00:00:00
    temperature_2026_03_02@t_rast_list|2026-03-02 00:00:00
    temperature_2026_03_03@t_rast_list|2026-03-03 00:00:00
    temperature_2026_03_04@t_rast_list|2026-03-04 00:00:00
    ```

    ```sh
    g.mapsets mapset=t_rast_list operation=add
    g.mapsets -p
    t.rast.list input=temperature columns=id,start_time
    ```

    ```text
    t_rast_list_2 PERMANENT t_rast_list
    id|start_time
    temperature_2026_03_01@t_rast_list|2026-03-01 00:00:00
    temperature_2026_03_02@t_rast_list|2026-03-02 00:00:00
    temperature_2026_03_03@t_rast_list|2026-03-03 00:00:00
    temperature_2026_03_04@t_rast_list|2026-03-04 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_rast_list_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    result = tools.t_rast_list(input="temperature@t_rast_list", columns="id,start_time")
    print(result.text)
    ```

    ```text
    id|start_time
    temperature_2026_03_01@t_rast_list|2026-03-01 00:00:00
    temperature_2026_03_02@t_rast_list|2026-03-02 00:00:00
    temperature_2026_03_03@t_rast_list|2026-03-03 00:00:00
    temperature_2026_03_04@t_rast_list|2026-03-04 00:00:00
    ```

    ```python
    tools.g_mapsets(mapset="t_rast_list", operation="add")
    print(tools.g_mapsets(flags="p").text)
    print(tools.t_rast_list(input="temperature", columns="id,start_time").text)
    ```

    ```text
    t_rast_list_2 PERMANENT t_rast_list
    id|start_time
    temperature_2026_03_01@t_rast_list|2026-03-01 00:00:00
    temperature_2026_03_02@t_rast_list|2026-03-02 00:00:00
    temperature_2026_03_03@t_rast_list|2026-03-03 00:00:00
    temperature_2026_03_04@t_rast_list|2026-03-04 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapsets](g.mapsets.md),
[r.semantic.label](r.semantic.label.md), [t.create](t.create.md),
[t.info](t.info.md), [t.list](t.list.md), [t.rast.univar](t.rast.univar.md),
[t.rast3d.list](t.rast3d.list.md), [t.register](t.register.md),
[t.upgrade](t.upgrade.md), [t.vect.list](t.vect.list.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
