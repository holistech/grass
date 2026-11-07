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
as `max > 5`, `name = 'temperature_profile_2020_01'` or
`start_time >= '2020-03-01'`. Times are
compared as text, so a time with a clock part needs the whole text:
`start_time = '2020-03-01'` selects nothing, because the stored value is
`2020-03-01 00:00:00`. Use `>=` and `<` for a day, or `name` for a single map.
The function `strftime()` of SQLite selects recurring times, such as one day of
the month or one month of the year. With the methods `delta`, `deltagaps` and
`gran`, the condition selects the maps before the lengths and distances are
counted, so the distances start at 0 with the first selected map.

### Columns and order

The option **columns** chooses the columns that are printed for each map,
separated by commas. The columns are:

- `id`, the name of the map with its mapset, such as
  `temperature_profile_2020_01@t_rast3d_list`; `name` and `mapset`, the two
  parts of it;
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
- `deltagaps` is `delta` with a line for every temporal gap. A gap is time
  that no map covers. A gap line has `None` as `id`, `name` and `mapset`; its
  times are the latest end of the maps before the gap and the start of the map
  after it, and its length is the length of the gap. Maps that follow each
  other directly leave no gap, and neither does a map that ends inside a longer
  one.
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

The option **granule** is the granule of the method `gran`. For absolute time it
is a text with a number and a time unit, such as `"2 months"`. For relative time
it is a whole number of at least 1 in the time unit of the dataset, also
followed by this unit: `12`, `"12 hours"` and `"12 hour"` are the same granule
of a dataset in hours. Another unit, such as `"1 day"` for a dataset in hours,
is refused with the error "Invalid granule". An absolute granule whose number is
below 1, such as `"0 days"`, is refused with the error "The granularity '0 days'
must be positive". Without **granule**, the granularity of the dataset is used.
The first granule starts with the first map, and the granules reach the latest
end of the maps, also when a shorter map starts last. Each later start is
counted in whole granules from the start of the dataset when the first selected
map lies whole granules after it, otherwise from the first selected map; this
matters when **where** selects later maps only. A step of months or years that
ends behind the last day of a shorter month ends on that day: with a granule of
one month and a first map from 31 January, the granules start on 31 January, 28
February, 31 March and 30 April. Such a series has the granularity one month
(see *[t.info](t.info.md)*), so `gran` without **granule** samples it by months
as well. The other methods ignore **granule**.

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
without **granule** stops for it with the error that the dataset has no
granularity, whatever **where** selects. Give a **granule**, such as `"1 day"`,
or use `delta`.

With relative time, the times are numbers of the time unit of the dataset,
printed without the unit, as the dataset `runoff` in the fourth example
shows. The method `gran` works with relative time with and without
**granule**, as the example "Sample the maps by a granule" shows.

The option **output** takes the name of a file; the name `-` is the standard
output, as the last block of the "Choose the output format" example shows.

*t.rast3d.list* only reads, so it works on a dataset of another mapset as well.
The name with the mapset (`input=temperature_profile@t_rast3d_list`) selects
it; a name without a mapset is searched in the mapsets of the search path (see
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

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast3d_list` and sets the computational region
to North Carolina with cells of 1 km, in the plane and in the vertical (the
option **res3**), and three layers of 1000 m from 0 to 3000 m; the later
examples work in this mapset and region, except the last, which creates a
second mapset with the same region. The examples about times, gaps and
granules use 3D maps with small constant values, so that the results can be
checked by hand.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast3d_list -->

<!-- markdownlint-disable MD046 -->

### List the maps of a dataset

The dataset `temperature_profile` has twelve 3D raster maps of the monthly
mean air temperature in 2020, in degrees Celsius rounded to tenths. They are
generated from the height `z()` of the cell: 16.5 degrees at sea level and the
northing 160 km, an annual cycle of plus and minus 10.5 degrees with its
maximum in July, 6.5 degrees less for every 1000 m of height, and 1 degree
more for every 100 km to the south. Each map is an interval of one month. The
region has 839 columns, 335 rows and 3 layers of a thickness of 1000 m, so
each map has 843,195 cells. A space time 3D raster dataset has the type
`str3ds`, and its maps are registered with the type `raster_3d`.

The first block lists the maps with the default columns. The second block adds
the flag **-s**, which suppresses the line with the column names, and names the
default method `cols`. The third block names the columns, among them the
smallest and largest value of each map: January is the coldest month, July the
warmest. The fourth block lists the columns of the volume of the first map: the
extent in the plane, the cell sizes, the thickness `tbres` of a layer and the
number of layers `depths`.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast3d_list
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
    t.rast3d.list input=temperature_profile
    ```

    ```text
    name|mapset|start_time|end_time
    temperature_profile_2020_01|t_rast3d_list|2020-01-01 00:00:00|2020-02-01 00:00:00
    temperature_profile_2020_02|t_rast3d_list|2020-02-01 00:00:00|2020-03-01 00:00:00
    temperature_profile_2020_03|t_rast3d_list|2020-03-01 00:00:00|2020-04-01 00:00:00
    temperature_profile_2020_04|t_rast3d_list|2020-04-01 00:00:00|2020-05-01 00:00:00
    temperature_profile_2020_05|t_rast3d_list|2020-05-01 00:00:00|2020-06-01 00:00:00
    temperature_profile_2020_06|t_rast3d_list|2020-06-01 00:00:00|2020-07-01 00:00:00
    temperature_profile_2020_07|t_rast3d_list|2020-07-01 00:00:00|2020-08-01 00:00:00
    temperature_profile_2020_08|t_rast3d_list|2020-08-01 00:00:00|2020-09-01 00:00:00
    temperature_profile_2020_09|t_rast3d_list|2020-09-01 00:00:00|2020-10-01 00:00:00
    temperature_profile_2020_10|t_rast3d_list|2020-10-01 00:00:00|2020-11-01 00:00:00
    temperature_profile_2020_11|t_rast3d_list|2020-11-01 00:00:00|2020-12-01 00:00:00
    temperature_profile_2020_12|t_rast3d_list|2020-12-01 00:00:00|2021-01-01 00:00:00
    ```

    ```sh
    t.rast3d.list -s input=temperature_profile method=cols
    ```

    ```text
    temperature_profile_2020_01|t_rast3d_list|2020-01-01 00:00:00|2020-02-01 00:00:00
    temperature_profile_2020_02|t_rast3d_list|2020-02-01 00:00:00|2020-03-01 00:00:00
    temperature_profile_2020_03|t_rast3d_list|2020-03-01 00:00:00|2020-04-01 00:00:00
    temperature_profile_2020_04|t_rast3d_list|2020-04-01 00:00:00|2020-05-01 00:00:00
    temperature_profile_2020_05|t_rast3d_list|2020-05-01 00:00:00|2020-06-01 00:00:00
    temperature_profile_2020_06|t_rast3d_list|2020-06-01 00:00:00|2020-07-01 00:00:00
    temperature_profile_2020_07|t_rast3d_list|2020-07-01 00:00:00|2020-08-01 00:00:00
    temperature_profile_2020_08|t_rast3d_list|2020-08-01 00:00:00|2020-09-01 00:00:00
    temperature_profile_2020_09|t_rast3d_list|2020-09-01 00:00:00|2020-10-01 00:00:00
    temperature_profile_2020_10|t_rast3d_list|2020-10-01 00:00:00|2020-11-01 00:00:00
    temperature_profile_2020_11|t_rast3d_list|2020-11-01 00:00:00|2020-12-01 00:00:00
    temperature_profile_2020_12|t_rast3d_list|2020-12-01 00:00:00|2021-01-01 00:00:00
    ```

    ```sh
    t.rast3d.list input=temperature_profile columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    temperature_profile_2020_01|2020-01-01 00:00:00|-11.8|4.6
    temperature_profile_2020_02|2020-02-01 00:00:00|-10.9|5.4
    temperature_profile_2020_03|2020-03-01 00:00:00|-7.5|8.8
    temperature_profile_2020_04|2020-04-01 00:00:00|-2.4|13.9
    temperature_profile_2020_05|2020-05-01 00:00:00|2.9|19.3
    temperature_profile_2020_06|2020-06-01 00:00:00|7.2|23.5
    temperature_profile_2020_07|2020-07-01 00:00:00|9.1|25.4
    temperature_profile_2020_08|2020-08-01 00:00:00|8.3|24.6
    temperature_profile_2020_09|2020-09-01 00:00:00|4.8|21.2
    temperature_profile_2020_10|2020-10-01 00:00:00|-0.2|16.1
    temperature_profile_2020_11|2020-11-01 00:00:00|-5.6|10.7
    temperature_profile_2020_12|2020-12-01 00:00:00|-9.8|6.5
    ```

    ```sh
    t.rast3d.list input=temperature_profile \
        where="name = 'temperature_profile_2020_01'" \
        columns=id,name,mapset,temporal_type,start_time,end_time,north,south,west,east,nsres,ewres,tbres,cols,rows,depths,number_of_cells,min,max
    ```

    ```text
    id|name|mapset|temporal_type|start_time|end_time|north|south|west|east|nsres|ewres|tbres|cols|rows|depths|number_of_cells|min|max
    temperature_profile_2020_01@t_rast3d_list|temperature_profile_2020_01|t_rast3d_list|absolute|2020-01-01 00:00:00|2020-02-01 00:00:00|319000.0|-16000.0|124000.0|963000.0|1000.0|1000.0|1000.0|839|335|3|843195|-11.8|4.6
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast3d_list")
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
    print(tools.t_rast3d_list(input="temperature_profile").text)
    ```

    ```text
    name|mapset|start_time|end_time
    temperature_profile_2020_01|t_rast3d_list|2020-01-01 00:00:00|2020-02-01 00:00:00
    temperature_profile_2020_02|t_rast3d_list|2020-02-01 00:00:00|2020-03-01 00:00:00
    temperature_profile_2020_03|t_rast3d_list|2020-03-01 00:00:00|2020-04-01 00:00:00
    temperature_profile_2020_04|t_rast3d_list|2020-04-01 00:00:00|2020-05-01 00:00:00
    temperature_profile_2020_05|t_rast3d_list|2020-05-01 00:00:00|2020-06-01 00:00:00
    temperature_profile_2020_06|t_rast3d_list|2020-06-01 00:00:00|2020-07-01 00:00:00
    temperature_profile_2020_07|t_rast3d_list|2020-07-01 00:00:00|2020-08-01 00:00:00
    temperature_profile_2020_08|t_rast3d_list|2020-08-01 00:00:00|2020-09-01 00:00:00
    temperature_profile_2020_09|t_rast3d_list|2020-09-01 00:00:00|2020-10-01 00:00:00
    temperature_profile_2020_10|t_rast3d_list|2020-10-01 00:00:00|2020-11-01 00:00:00
    temperature_profile_2020_11|t_rast3d_list|2020-11-01 00:00:00|2020-12-01 00:00:00
    temperature_profile_2020_12|t_rast3d_list|2020-12-01 00:00:00|2021-01-01 00:00:00
    ```

    ```python
    result = tools.t_rast3d_list(input="temperature_profile", method="cols", flags="s")
    print(result.text)
    ```

    ```text
    temperature_profile_2020_01|t_rast3d_list|2020-01-01 00:00:00|2020-02-01 00:00:00
    temperature_profile_2020_02|t_rast3d_list|2020-02-01 00:00:00|2020-03-01 00:00:00
    temperature_profile_2020_03|t_rast3d_list|2020-03-01 00:00:00|2020-04-01 00:00:00
    temperature_profile_2020_04|t_rast3d_list|2020-04-01 00:00:00|2020-05-01 00:00:00
    temperature_profile_2020_05|t_rast3d_list|2020-05-01 00:00:00|2020-06-01 00:00:00
    temperature_profile_2020_06|t_rast3d_list|2020-06-01 00:00:00|2020-07-01 00:00:00
    temperature_profile_2020_07|t_rast3d_list|2020-07-01 00:00:00|2020-08-01 00:00:00
    temperature_profile_2020_08|t_rast3d_list|2020-08-01 00:00:00|2020-09-01 00:00:00
    temperature_profile_2020_09|t_rast3d_list|2020-09-01 00:00:00|2020-10-01 00:00:00
    temperature_profile_2020_10|t_rast3d_list|2020-10-01 00:00:00|2020-11-01 00:00:00
    temperature_profile_2020_11|t_rast3d_list|2020-11-01 00:00:00|2020-12-01 00:00:00
    temperature_profile_2020_12|t_rast3d_list|2020-12-01 00:00:00|2021-01-01 00:00:00
    ```

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile", columns="name,start_time,min,max"
    )
    print(result.text)
    ```

    ```text
    name|start_time|min|max
    temperature_profile_2020_01|2020-01-01 00:00:00|-11.8|4.6
    temperature_profile_2020_02|2020-02-01 00:00:00|-10.9|5.4
    temperature_profile_2020_03|2020-03-01 00:00:00|-7.5|8.8
    temperature_profile_2020_04|2020-04-01 00:00:00|-2.4|13.9
    temperature_profile_2020_05|2020-05-01 00:00:00|2.9|19.3
    temperature_profile_2020_06|2020-06-01 00:00:00|7.2|23.5
    temperature_profile_2020_07|2020-07-01 00:00:00|9.1|25.4
    temperature_profile_2020_08|2020-08-01 00:00:00|8.3|24.6
    temperature_profile_2020_09|2020-09-01 00:00:00|4.8|21.2
    temperature_profile_2020_10|2020-10-01 00:00:00|-0.2|16.1
    temperature_profile_2020_11|2020-11-01 00:00:00|-5.6|10.7
    temperature_profile_2020_12|2020-12-01 00:00:00|-9.8|6.5
    ```

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile",
        where="name = 'temperature_profile_2020_01'",
        columns=(
            "id,name,mapset,temporal_type,start_time,end_time,north,south,west,east,"
            "nsres,ewres,tbres,cols,rows,depths,number_of_cells,min,max"
        ),
    )
    print(result.text)
    ```

    ```text
    id|name|mapset|temporal_type|start_time|end_time|north|south|west|east|nsres|ewres|tbres|cols|rows|depths|number_of_cells|min|max
    temperature_profile_2020_01@t_rast3d_list|temperature_profile_2020_01|t_rast3d_list|absolute|2020-01-01 00:00:00|2020-02-01 00:00:00|319000.0|-16000.0|124000.0|963000.0|1000.0|1000.0|1000.0|839|335|3|843195|-11.8|4.6
    ```

### Select and sort the maps

The maps of `temperature_profile` are sorted by start time. The option
**order** sorts by another column; the first block sorts by `max`, so the
coldest months come first: January, February and December.

The option **where** selects the maps. The second block selects the maps that
start from 1 March on and before 1 May, so March and April. The third block
combines a condition on the smallest value with **order**: it keeps the months
in which no cell is colder than 3 degrees: June to September, sorted by `max`,
so September comes first. The fourth block uses `strftime()`
to select the maps that start in January or July, a recurring selection that
works the same way for every year.

The last block shows a trap: a time compared with `=` must be the whole text
`2020-03-01 00:00:00`, and the short form selects no map. The format `json`
shows the empty result, `data` is an empty list; the formats `plain` and
`line` stop with an error here.

=== "Command line"

    ```sh
    t.rast3d.list input=temperature_profile columns=name,max order=max
    ```

    ```text
    name|max
    temperature_profile_2020_01|4.6
    temperature_profile_2020_02|5.4
    temperature_profile_2020_12|6.5
    temperature_profile_2020_03|8.8
    temperature_profile_2020_11|10.7
    temperature_profile_2020_04|13.9
    temperature_profile_2020_10|16.1
    temperature_profile_2020_05|19.3
    temperature_profile_2020_09|21.2
    temperature_profile_2020_06|23.5
    temperature_profile_2020_08|24.6
    temperature_profile_2020_07|25.4
    ```

    ```sh
    t.rast3d.list input=temperature_profile columns=name,start_time \
        where="start_time >= '2020-03-01' and start_time < '2020-05-01'"
    ```

    ```text
    name|start_time
    temperature_profile_2020_03|2020-03-01 00:00:00
    temperature_profile_2020_04|2020-04-01 00:00:00
    ```

    ```sh
    t.rast3d.list input=temperature_profile columns=name,min,max order=max \
        where="min > 3"
    ```

    ```text
    name|min|max
    temperature_profile_2020_09|4.8|21.2
    temperature_profile_2020_06|7.2|23.5
    temperature_profile_2020_08|8.3|24.6
    temperature_profile_2020_07|9.1|25.4
    ```

    ```sh
    t.rast3d.list input=temperature_profile columns=name,start_time \
        where="strftime('%m', start_time) in ('01', '07')"
    ```

    ```text
    name|start_time
    temperature_profile_2020_01|2020-01-01 00:00:00
    temperature_profile_2020_07|2020-07-01 00:00:00
    ```

    ```sh
    t.rast3d.list input=temperature_profile columns=name format=json \
        where="start_time = '2020-03-01'"
    echo
    ```

    ```text
    {"data": [], "metadata": {"column_names": ["name"]}}
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile", columns="name,max", order="max"
    )
    print(result.text)
    ```

    ```text
    name|max
    temperature_profile_2020_01|4.6
    temperature_profile_2020_02|5.4
    temperature_profile_2020_12|6.5
    temperature_profile_2020_03|8.8
    temperature_profile_2020_11|10.7
    temperature_profile_2020_04|13.9
    temperature_profile_2020_10|16.1
    temperature_profile_2020_05|19.3
    temperature_profile_2020_09|21.2
    temperature_profile_2020_06|23.5
    temperature_profile_2020_08|24.6
    temperature_profile_2020_07|25.4
    ```

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile",
        columns="name,start_time",
        where="start_time >= '2020-03-01' and start_time < '2020-05-01'",
    )
    print(result.text)
    ```

    ```text
    name|start_time
    temperature_profile_2020_03|2020-03-01 00:00:00
    temperature_profile_2020_04|2020-04-01 00:00:00
    ```

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile",
        columns="name,min,max",
        order="max",
        where="min > 3",
    )
    print(result.text)
    ```

    ```text
    name|min|max
    temperature_profile_2020_09|4.8|21.2
    temperature_profile_2020_06|7.2|23.5
    temperature_profile_2020_08|8.3|24.6
    temperature_profile_2020_07|9.1|25.4
    ```

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile",
        columns="name,start_time",
        where="strftime('%m', start_time) in ('01', '07')",
    )
    print(result.text)
    ```

    ```text
    name|start_time
    temperature_profile_2020_01|2020-01-01 00:00:00
    temperature_profile_2020_07|2020-07-01 00:00:00
    ```

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile",
        columns="name",
        format="json",
        where="start_time = '2020-03-01'",
    )
    print(result.text)
    ```

    ```text
    {"data": [], "metadata": {"column_names": ["name"]}}
    ```

### Choose the output format

All blocks list the dataset `temperature_profile`; the blocks that print the
values of all twelve maps name the columns, so that the lines stay short. The
first block prints the maps as a list of ids in one line, the form that other
tools accept as input; the second block does the same with the old method name
`comma`; the third block prints the names only, with another separator. The
fourth and fifth block print CSV with and without the line of column names;
text is quoted and numbers are not. The sixth block replaces the separator of
the plain format. The seventh block prints JSON, which the Python tab reads
from `result.json` and prints name and `max` of each map. The eighth block
writes the listing to a file and prints the file. The ninth block prints the
listing with `output=-`, the standard output.

=== "Command line"

    ```sh
    t.rast3d.list input=temperature_profile format=line
    ```

    ```text
    temperature_profile_2020_01@t_rast3d_list,temperature_profile_2020_02@t_rast3d_list,temperature_profile_2020_03@t_rast3d_list,temperature_profile_2020_04@t_rast3d_list,temperature_profile_2020_05@t_rast3d_list,temperature_profile_2020_06@t_rast3d_list,temperature_profile_2020_07@t_rast3d_list,temperature_profile_2020_08@t_rast3d_list,temperature_profile_2020_09@t_rast3d_list,temperature_profile_2020_10@t_rast3d_list,temperature_profile_2020_11@t_rast3d_list,temperature_profile_2020_12@t_rast3d_list
    ```

    ```sh
    t.rast3d.list input=temperature_profile method=comma
    ```

    ```text
    temperature_profile_2020_01@t_rast3d_list,temperature_profile_2020_02@t_rast3d_list,temperature_profile_2020_03@t_rast3d_list,temperature_profile_2020_04@t_rast3d_list,temperature_profile_2020_05@t_rast3d_list,temperature_profile_2020_06@t_rast3d_list,temperature_profile_2020_07@t_rast3d_list,temperature_profile_2020_08@t_rast3d_list,temperature_profile_2020_09@t_rast3d_list,temperature_profile_2020_10@t_rast3d_list,temperature_profile_2020_11@t_rast3d_list,temperature_profile_2020_12@t_rast3d_list
    ```

    ```sh
    t.rast3d.list input=temperature_profile format=line columns=name separator=" | "
    ```

    ```text
    temperature_profile_2020_01 | temperature_profile_2020_02 | temperature_profile_2020_03 | temperature_profile_2020_04 | temperature_profile_2020_05 | temperature_profile_2020_06 | temperature_profile_2020_07 | temperature_profile_2020_08 | temperature_profile_2020_09 | temperature_profile_2020_10 | temperature_profile_2020_11 | temperature_profile_2020_12
    ```

    ```sh
    t.rast3d.list input=temperature_profile format=csv columns=name,min,max
    ```

    ```text
    "name","min","max"
    "temperature_profile_2020_01",-11.8,4.6
    "temperature_profile_2020_02",-10.9,5.4
    "temperature_profile_2020_03",-7.5,8.8
    "temperature_profile_2020_04",-2.4,13.9
    "temperature_profile_2020_05",2.9,19.3
    "temperature_profile_2020_06",7.2,23.5
    "temperature_profile_2020_07",9.1,25.4
    "temperature_profile_2020_08",8.3,24.6
    "temperature_profile_2020_09",4.8,21.2
    "temperature_profile_2020_10",-0.2,16.1
    "temperature_profile_2020_11",-5.6,10.7
    "temperature_profile_2020_12",-9.8,6.5
    ```

    ```sh
    t.rast3d.list -s input=temperature_profile format=csv columns=name,min,max
    ```

    ```text
    "temperature_profile_2020_01",-11.8,4.6
    "temperature_profile_2020_02",-10.9,5.4
    "temperature_profile_2020_03",-7.5,8.8
    "temperature_profile_2020_04",-2.4,13.9
    "temperature_profile_2020_05",2.9,19.3
    "temperature_profile_2020_06",7.2,23.5
    "temperature_profile_2020_07",9.1,25.4
    "temperature_profile_2020_08",8.3,24.6
    "temperature_profile_2020_09",4.8,21.2
    "temperature_profile_2020_10",-0.2,16.1
    "temperature_profile_2020_11",-5.6,10.7
    "temperature_profile_2020_12",-9.8,6.5
    ```

    ```sh
    t.rast3d.list input=temperature_profile columns=name,min,max separator=";"
    ```

    ```text
    name;min;max
    temperature_profile_2020_01;-11.8;4.6
    temperature_profile_2020_02;-10.9;5.4
    temperature_profile_2020_03;-7.5;8.8
    temperature_profile_2020_04;-2.4;13.9
    temperature_profile_2020_05;2.9;19.3
    temperature_profile_2020_06;7.2;23.5
    temperature_profile_2020_07;9.1;25.4
    temperature_profile_2020_08;8.3;24.6
    temperature_profile_2020_09;4.8;21.2
    temperature_profile_2020_10;-0.2;16.1
    temperature_profile_2020_11;-5.6;10.7
    temperature_profile_2020_12;-9.8;6.5
    ```

    ```sh
    t.rast3d.list input=temperature_profile columns=name,max format=json
    echo
    ```

    ```text
    {"data": [{"name": "temperature_profile_2020_01", "max": 4.6}, {"name": "temperature_profile_2020_02", "max": 5.4}, {"name": "temperature_profile_2020_03", "max": 8.8}, {"name": "temperature_profile_2020_04", "max": 13.9}, {"name": "temperature_profile_2020_05", "max": 19.3}, {"name": "temperature_profile_2020_06", "max": 23.5}, {"name": "temperature_profile_2020_07", "max": 25.4}, {"name": "temperature_profile_2020_08", "max": 24.6}, {"name": "temperature_profile_2020_09", "max": 21.2}, {"name": "temperature_profile_2020_10", "max": 16.1}, {"name": "temperature_profile_2020_11", "max": 10.7}, {"name": "temperature_profile_2020_12", "max": 6.5}], "metadata": {"column_names": ["name", "max"]}}
    ```

    ```sh
    t.rast3d.list input=temperature_profile columns=name,max output=maxima.txt
    cat maxima.txt
    ```

    ```text
    name|max
    temperature_profile_2020_01|4.6
    temperature_profile_2020_02|5.4
    temperature_profile_2020_03|8.8
    temperature_profile_2020_04|13.9
    temperature_profile_2020_05|19.3
    temperature_profile_2020_06|23.5
    temperature_profile_2020_07|25.4
    temperature_profile_2020_08|24.6
    temperature_profile_2020_09|21.2
    temperature_profile_2020_10|16.1
    temperature_profile_2020_11|10.7
    temperature_profile_2020_12|6.5
    ```

    ```sh
    t.rast3d.list input=temperature_profile columns=name output=-
    ```

    ```text
    name
    temperature_profile_2020_01
    temperature_profile_2020_02
    temperature_profile_2020_03
    temperature_profile_2020_04
    temperature_profile_2020_05
    temperature_profile_2020_06
    temperature_profile_2020_07
    temperature_profile_2020_08
    temperature_profile_2020_09
    temperature_profile_2020_10
    temperature_profile_2020_11
    temperature_profile_2020_12
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    print(tools.t_rast3d_list(input="temperature_profile", format="line").text)
    ```

    ```text
    temperature_profile_2020_01@t_rast3d_list,temperature_profile_2020_02@t_rast3d_list,temperature_profile_2020_03@t_rast3d_list,temperature_profile_2020_04@t_rast3d_list,temperature_profile_2020_05@t_rast3d_list,temperature_profile_2020_06@t_rast3d_list,temperature_profile_2020_07@t_rast3d_list,temperature_profile_2020_08@t_rast3d_list,temperature_profile_2020_09@t_rast3d_list,temperature_profile_2020_10@t_rast3d_list,temperature_profile_2020_11@t_rast3d_list,temperature_profile_2020_12@t_rast3d_list
    ```

    ```python
    print(tools.t_rast3d_list(input="temperature_profile", method="comma").text)
    ```

    ```text
    temperature_profile_2020_01@t_rast3d_list,temperature_profile_2020_02@t_rast3d_list,temperature_profile_2020_03@t_rast3d_list,temperature_profile_2020_04@t_rast3d_list,temperature_profile_2020_05@t_rast3d_list,temperature_profile_2020_06@t_rast3d_list,temperature_profile_2020_07@t_rast3d_list,temperature_profile_2020_08@t_rast3d_list,temperature_profile_2020_09@t_rast3d_list,temperature_profile_2020_10@t_rast3d_list,temperature_profile_2020_11@t_rast3d_list,temperature_profile_2020_12@t_rast3d_list
    ```

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile", format="line", columns="name", separator=" | "
    )
    print(result.text)
    ```

    ```text
    temperature_profile_2020_01 | temperature_profile_2020_02 | temperature_profile_2020_03 | temperature_profile_2020_04 | temperature_profile_2020_05 | temperature_profile_2020_06 | temperature_profile_2020_07 | temperature_profile_2020_08 | temperature_profile_2020_09 | temperature_profile_2020_10 | temperature_profile_2020_11 | temperature_profile_2020_12
    ```

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile", format="csv", columns="name,min,max"
    )
    print(result.text)
    ```

    ```text
    "name","min","max"
    "temperature_profile_2020_01",-11.8,4.6
    "temperature_profile_2020_02",-10.9,5.4
    "temperature_profile_2020_03",-7.5,8.8
    "temperature_profile_2020_04",-2.4,13.9
    "temperature_profile_2020_05",2.9,19.3
    "temperature_profile_2020_06",7.2,23.5
    "temperature_profile_2020_07",9.1,25.4
    "temperature_profile_2020_08",8.3,24.6
    "temperature_profile_2020_09",4.8,21.2
    "temperature_profile_2020_10",-0.2,16.1
    "temperature_profile_2020_11",-5.6,10.7
    "temperature_profile_2020_12",-9.8,6.5
    ```

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile", format="csv", columns="name,min,max", flags="s"
    )
    print(result.text)
    ```

    ```text
    "temperature_profile_2020_01",-11.8,4.6
    "temperature_profile_2020_02",-10.9,5.4
    "temperature_profile_2020_03",-7.5,8.8
    "temperature_profile_2020_04",-2.4,13.9
    "temperature_profile_2020_05",2.9,19.3
    "temperature_profile_2020_06",7.2,23.5
    "temperature_profile_2020_07",9.1,25.4
    "temperature_profile_2020_08",8.3,24.6
    "temperature_profile_2020_09",4.8,21.2
    "temperature_profile_2020_10",-0.2,16.1
    "temperature_profile_2020_11",-5.6,10.7
    "temperature_profile_2020_12",-9.8,6.5
    ```

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile", columns="name,min,max", separator=";"
    )
    print(result.text)
    ```

    ```text
    name;min;max
    temperature_profile_2020_01;-11.8;4.6
    temperature_profile_2020_02;-10.9;5.4
    temperature_profile_2020_03;-7.5;8.8
    temperature_profile_2020_04;-2.4;13.9
    temperature_profile_2020_05;2.9;19.3
    temperature_profile_2020_06;7.2;23.5
    temperature_profile_2020_07;9.1;25.4
    temperature_profile_2020_08;8.3;24.6
    temperature_profile_2020_09;4.8;21.2
    temperature_profile_2020_10;-0.2;16.1
    temperature_profile_2020_11;-5.6;10.7
    temperature_profile_2020_12;-9.8;6.5
    ```

    ```python
    result = tools.t_rast3d_list(
        input="temperature_profile", columns="name,max", format="json"
    )
    for item in result.json["data"]:
        print(item["name"], item["max"])
    ```

    ```text
    temperature_profile_2020_01 4.6
    temperature_profile_2020_02 5.4
    temperature_profile_2020_03 8.8
    temperature_profile_2020_04 13.9
    temperature_profile_2020_05 19.3
    temperature_profile_2020_06 23.5
    temperature_profile_2020_07 25.4
    temperature_profile_2020_08 24.6
    temperature_profile_2020_09 21.2
    temperature_profile_2020_10 16.1
    temperature_profile_2020_11 10.7
    temperature_profile_2020_12 6.5
    ```

    ```python
    tools.t_rast3d_list(
        input="temperature_profile", columns="name,max", output="maxima.txt"
    )
    print(Path("maxima.txt").read_text(), end="")
    ```

    ```text
    name|max
    temperature_profile_2020_01|4.6
    temperature_profile_2020_02|5.4
    temperature_profile_2020_03|8.8
    temperature_profile_2020_04|13.9
    temperature_profile_2020_05|19.3
    temperature_profile_2020_06|23.5
    temperature_profile_2020_07|25.4
    temperature_profile_2020_08|24.6
    temperature_profile_2020_09|21.2
    temperature_profile_2020_10|16.1
    temperature_profile_2020_11|10.7
    temperature_profile_2020_12|6.5
    ```

    ```python
    result = tools.t_rast3d_list(input="temperature_profile", columns="name", output="-")
    print(result.text)
    ```

    ```text
    name
    temperature_profile_2020_01
    temperature_profile_2020_02
    temperature_profile_2020_03
    temperature_profile_2020_04
    temperature_profile_2020_05
    temperature_profile_2020_06
    temperature_profile_2020_07
    temperature_profile_2020_08
    temperature_profile_2020_09
    temperature_profile_2020_10
    temperature_profile_2020_11
    temperature_profile_2020_12
    ```

### Intervals, distances and gaps

The dataset `rain` has two daily maps, registered with a start and an end:
`rain_1` for 1 June 2026 and `rain_3` for 3 June, so 2 June is a gap. The maps
hold the constants 4 and 2 mm in every cell. The method `delta` prints the
length of each map and its distance from the first map in days; it skips the
gap. The method `deltagaps` adds a line for the gap with `None` as `id`,
`name` and `mapset`, and its length. The CSV form of this table shows `None` as
an empty text.

The dataset `runoff` has relative time: three model steps of 6 hours, with the
constants 1, 2 and 3 mm of runoff. Its times, lengths and distances are
numbers of hours, printed without the unit.

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
    rain_1@t_rast3d_list|rain_1|t_rast3d_list|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    rain_3@t_rast3d_list|rain_3|t_rast3d_list|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```sh
    t.rast3d.list input=rain method=deltagaps
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    rain_1@t_rast3d_list|rain_1|t_rast3d_list|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    None|None|None|2026-06-02 00:00:00|2026-06-03 00:00:00|1.0|1.0
    rain_3@t_rast3d_list|rain_3|t_rast3d_list|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```sh
    t.rast3d.list input=rain method=deltagaps format=csv columns=id,interval_length
    ```

    ```text
    "id","interval_length"
    "rain_1@t_rast3d_list",1.0
    "",1.0
    "rain_3@t_rast3d_list",1.0
    ```

    ```sh
    for step in 1 2 3; do
        r3.mapcalc expression="runoff_$step = $step"
    done
    t.create type=str3ds output=runoff temporaltype=relative title="Runoff" \
        description="Simulated runoff in mm per model step of 6 hours"
    t.register -i type=raster_3d input=runoff maps=runoff_1,runoff_2,runoff_3 \
        start=0 increment=6 unit=hours
    t.rast3d.list input=runoff method=delta
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast3d_list|runoff_1|t_rast3d_list|0|6|6|0
    runoff_2@t_rast3d_list|runoff_2|t_rast3d_list|6|12|6|6
    runoff_3@t_rast3d_list|runoff_3|t_rast3d_list|12|18|6|12
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
    rain_1@t_rast3d_list|rain_1|t_rast3d_list|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    rain_3@t_rast3d_list|rain_3|t_rast3d_list|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```python
    print(tools.t_rast3d_list(input="rain", method="deltagaps").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    rain_1@t_rast3d_list|rain_1|t_rast3d_list|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    None|None|None|2026-06-02 00:00:00|2026-06-03 00:00:00|1.0|1.0
    rain_3@t_rast3d_list|rain_3|t_rast3d_list|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```python
    result = tools.t_rast3d_list(
        input="rain", method="deltagaps", format="csv", columns="id,interval_length"
    )
    print(result.text)
    ```

    ```text
    "id","interval_length"
    "rain_1@t_rast3d_list",1.0
    "",1.0
    "rain_3@t_rast3d_list",1.0
    ```

    ```python
    for step in (1, 2, 3):
        tools.r3_mapcalc(expression=f"runoff_{step} = {step}")
    tools.t_create(
        type="str3ds",
        output="runoff",
        temporaltype="relative",
        title="Runoff",
        description="Simulated runoff in mm per model step of 6 hours",
    )
    tools.t_register(
        type="raster_3d",
        input="runoff",
        maps="runoff_1,runoff_2,runoff_3",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    print(tools.t_rast3d_list(input="runoff", method="delta").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast3d_list|runoff_1|t_rast3d_list|0|6|6|0
    runoff_2@t_rast3d_list|runoff_2|t_rast3d_list|6|12|6|6
    runoff_3@t_rast3d_list|runoff_3|t_rast3d_list|12|18|6|12
    ```

### Sample the maps by a granule

The dataset `moisture` has four maps that start on the last day of a month
and end on the last day of the next one, from 31 January; they hold the
constants 1 to 4 as the soil moisture in percent. The first block lists them.
The method `gran` with a granule of one month prints one line per month
granule: the granules start on 31 January, 28 February, 31 March and 30 April,
as each start is counted in months from 31 January and cut to the last day of
a shorter month. With a granule of two months, each line covers two maps and
names the first of them. Without a granule, `gran` takes the granularity of the
dataset, one month, and prints the same lines as with `"1 month"`. The last
blocks sample the relative dataset `runoff` of the previous example: without a
granule by the granularity of the dataset, 6 hours, and with the granule `12`,
a number of hours; `"12 hours"` is the same granule.

=== "Command line"

    ```sh
    for month in 1 2 3 4; do
        r3.mapcalc expression="moisture_$month = $month"
    done
    t.create type=str3ds output=moisture title="Soil moisture" \
        description="Monthly soil moisture in percent"
    t.register -i type=raster_3d input=moisture \
        maps=moisture_1,moisture_2,moisture_3,moisture_4 \
        start=2026-01-31 increment="1 month"
    t.rast3d.list input=moisture
    ```

    ```text
    name|mapset|start_time|end_time
    moisture_1|t_rast3d_list|2026-01-31 00:00:00|2026-02-28 00:00:00
    moisture_2|t_rast3d_list|2026-02-28 00:00:00|2026-03-31 00:00:00
    moisture_3|t_rast3d_list|2026-03-31 00:00:00|2026-04-30 00:00:00
    moisture_4|t_rast3d_list|2026-04-30 00:00:00|2026-05-31 00:00:00
    ```

    ```sh
    t.rast3d.list input=moisture method=gran granule="1 month"
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    moisture_1@t_rast3d_list|moisture_1|t_rast3d_list|2026-01-31 00:00:00|2026-02-28 00:00:00|28.0|0.0
    moisture_2@t_rast3d_list|moisture_2|t_rast3d_list|2026-02-28 00:00:00|2026-03-31 00:00:00|31.0|28.0
    moisture_3@t_rast3d_list|moisture_3|t_rast3d_list|2026-03-31 00:00:00|2026-04-30 00:00:00|30.0|59.0
    moisture_4@t_rast3d_list|moisture_4|t_rast3d_list|2026-04-30 00:00:00|2026-05-31 00:00:00|31.0|89.0
    ```

    ```sh
    t.rast3d.list input=moisture method=gran granule="2 months"
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    moisture_1@t_rast3d_list|moisture_1|t_rast3d_list|2026-01-31 00:00:00|2026-03-31 00:00:00|59.0|0.0
    moisture_3@t_rast3d_list|moisture_3|t_rast3d_list|2026-03-31 00:00:00|2026-05-31 00:00:00|61.0|59.0
    ```

    ```sh
    t.rast3d.list input=moisture method=gran
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    moisture_1@t_rast3d_list|moisture_1|t_rast3d_list|2026-01-31 00:00:00|2026-02-28 00:00:00|28.0|0.0
    moisture_2@t_rast3d_list|moisture_2|t_rast3d_list|2026-02-28 00:00:00|2026-03-31 00:00:00|31.0|28.0
    moisture_3@t_rast3d_list|moisture_3|t_rast3d_list|2026-03-31 00:00:00|2026-04-30 00:00:00|30.0|59.0
    moisture_4@t_rast3d_list|moisture_4|t_rast3d_list|2026-04-30 00:00:00|2026-05-31 00:00:00|31.0|89.0
    ```

    ```sh
    t.rast3d.list input=runoff method=gran
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast3d_list|runoff_1|t_rast3d_list|0|6|6|0
    runoff_2@t_rast3d_list|runoff_2|t_rast3d_list|6|12|6|6
    runoff_3@t_rast3d_list|runoff_3|t_rast3d_list|12|18|6|12
    ```

    ```sh
    t.rast3d.list input=runoff method=gran granule=12
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast3d_list|runoff_1|t_rast3d_list|0|12|12|0
    runoff_3@t_rast3d_list|runoff_3|t_rast3d_list|12|24|12|12
    ```

=== "Python (grass.tools)"

    ```python
    for month in (1, 2, 3, 4):
        tools.r3_mapcalc(expression=f"moisture_{month} = {month}")
    tools.t_create(
        type="str3ds",
        output="moisture",
        title="Soil moisture",
        description="Monthly soil moisture in percent",
    )
    tools.t_register(
        type="raster_3d",
        input="moisture",
        maps="moisture_1,moisture_2,moisture_3,moisture_4",
        start="2026-01-31",
        increment="1 month",
        flags="i",
    )
    print(tools.t_rast3d_list(input="moisture").text)
    ```

    ```text
    name|mapset|start_time|end_time
    moisture_1|t_rast3d_list|2026-01-31 00:00:00|2026-02-28 00:00:00
    moisture_2|t_rast3d_list|2026-02-28 00:00:00|2026-03-31 00:00:00
    moisture_3|t_rast3d_list|2026-03-31 00:00:00|2026-04-30 00:00:00
    moisture_4|t_rast3d_list|2026-04-30 00:00:00|2026-05-31 00:00:00
    ```

    ```python
    result = tools.t_rast3d_list(input="moisture", method="gran", granule="1 month")
    print(result.text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    moisture_1@t_rast3d_list|moisture_1|t_rast3d_list|2026-01-31 00:00:00|2026-02-28 00:00:00|28.0|0.0
    moisture_2@t_rast3d_list|moisture_2|t_rast3d_list|2026-02-28 00:00:00|2026-03-31 00:00:00|31.0|28.0
    moisture_3@t_rast3d_list|moisture_3|t_rast3d_list|2026-03-31 00:00:00|2026-04-30 00:00:00|30.0|59.0
    moisture_4@t_rast3d_list|moisture_4|t_rast3d_list|2026-04-30 00:00:00|2026-05-31 00:00:00|31.0|89.0
    ```

    ```python
    result = tools.t_rast3d_list(input="moisture", method="gran", granule="2 months")
    print(result.text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    moisture_1@t_rast3d_list|moisture_1|t_rast3d_list|2026-01-31 00:00:00|2026-03-31 00:00:00|59.0|0.0
    moisture_3@t_rast3d_list|moisture_3|t_rast3d_list|2026-03-31 00:00:00|2026-05-31 00:00:00|61.0|59.0
    ```

    ```python
    print(tools.t_rast3d_list(input="moisture", method="gran").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    moisture_1@t_rast3d_list|moisture_1|t_rast3d_list|2026-01-31 00:00:00|2026-02-28 00:00:00|28.0|0.0
    moisture_2@t_rast3d_list|moisture_2|t_rast3d_list|2026-02-28 00:00:00|2026-03-31 00:00:00|31.0|28.0
    moisture_3@t_rast3d_list|moisture_3|t_rast3d_list|2026-03-31 00:00:00|2026-04-30 00:00:00|30.0|59.0
    moisture_4@t_rast3d_list|moisture_4|t_rast3d_list|2026-04-30 00:00:00|2026-05-31 00:00:00|31.0|89.0
    ```

    ```python
    print(tools.t_rast3d_list(input="runoff", method="gran").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast3d_list|runoff_1|t_rast3d_list|0|6|6|0
    runoff_2@t_rast3d_list|runoff_2|t_rast3d_list|6|12|6|6
    runoff_3@t_rast3d_list|runoff_3|t_rast3d_list|12|18|6|12
    ```

    ```python
    print(tools.t_rast3d_list(input="runoff", method="gran", granule="12 hours").text)
    ```

    ```text
    id|name|mapset|start_time|end_time|interval_length|distance_from_begin
    runoff_1@t_rast3d_list|runoff_1|t_rast3d_list|0|12|12|0
    runoff_3@t_rast3d_list|runoff_3|t_rast3d_list|12|24|12|12
    ```

### Use a dataset of another mapset

*t.rast3d.list* reads a dataset of another mapset. The new mapset
`t_rast3d_list_2` starts with the default region of the dataset, cells of
500 m, so the example sets the region of the first example again. The mapset
`t_rast3d_list` holds the dataset `temperature_profile`; it is not in the search
path of the new mapset, and the dataset is named with its mapset. In the second
block, *g.mapsets* adds `t_rast3d_list` to the search path and shows it, because
a name without a mapset is searched only there (see
[Datasets of other mapsets](temporalintro.md#datasets-of-other-mapsets)); the name
`temperature_profile` then finds the same dataset.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast3d_list_2
    g.region raster=elev_state_500m res=1000 res3=1000 t=3000 b=0 tbres=1000 -a
    t.rast3d.list input=temperature_profile@t_rast3d_list \
        columns=id,start_time where="start_time < '2020-03-01'"
    ```

    ```text
    id|start_time
    temperature_profile_2020_01@t_rast3d_list|2020-01-01 00:00:00
    temperature_profile_2020_02@t_rast3d_list|2020-02-01 00:00:00
    ```

    ```sh
    g.mapsets mapset=t_rast3d_list operation=add
    g.mapsets -p
    t.rast3d.list input=temperature_profile columns=id,start_time \
        where="start_time < '2020-03-01'"
    ```

    ```text
    t_rast3d_list_2 PERMANENT t_rast3d_list
    id|start_time
    temperature_profile_2020_01@t_rast3d_list|2020-01-01 00:00:00
    temperature_profile_2020_02@t_rast3d_list|2020-02-01 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(flags="c", mapset="t_rast3d_list_2")
    tools.g_region(
        raster="elev_state_500m", res=1000, res3=1000, t=3000, b=0, tbres=1000, flags="a"
    )
    result = tools.t_rast3d_list(
        input="temperature_profile@t_rast3d_list",
        columns="id,start_time",
        where="start_time < '2020-03-01'",
    )
    print(result.text)
    ```

    ```text
    id|start_time
    temperature_profile_2020_01@t_rast3d_list|2020-01-01 00:00:00
    temperature_profile_2020_02@t_rast3d_list|2020-02-01 00:00:00
    ```

    ```python
    tools.g_mapsets(mapset="t_rast3d_list", operation="add")
    print(tools.g_mapsets(flags="p").text)
    result = tools.t_rast3d_list(
        input="temperature_profile",
        columns="id,start_time",
        where="start_time < '2020-03-01'",
    )
    print(result.text)
    ```

    ```text
    t_rast3d_list_2 PERMANENT t_rast3d_list
    id|start_time
    temperature_profile_2020_01@t_rast3d_list|2020-01-01 00:00:00
    temperature_profile_2020_02@t_rast3d_list|2020-02-01 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapsets](g.mapsets.md), [t.create](t.create.md),
[t.info](t.info.md), [t.list](t.list.md), [t.rast.list](t.rast.list.md),
[t.register](t.register.md), [t.vect.list](t.vect.list.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
