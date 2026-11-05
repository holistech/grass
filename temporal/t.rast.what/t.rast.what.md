## DESCRIPTION

*t.rast.what* samples the maps of a space time raster dataset at point
locations: it reads the cell value of each selected map at each location and
writes the values, together with the start and end time of each map, as a text
table. A temperature series sampled at a few stations gives one time series per
station, for instance. The tool runs *[r.what](r.what.md)* on the maps, so the
values are those of *r.what*, and it brings the output of *r.what* into one of
three layouts, with the time stamps of the maps instead of their names. It can
run several *r.what* processes in parallel. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets, and *[v.what.strds](v.what.strds.md)* for sampling that stores the
values in the attribute table of a vector map.

### Locations

The locations come from one of three sources. The option **points**
names a vector map; each point of it is a location. The option **coordinates**
lists the locations as `east,north` pairs, for instance `0.5,2.5,2.5,0.5` for
the two locations `0.5,2.5` and `2.5,0.5`; the tool stops with the message
`Option <coordinates> must be provided in multiples of 2` if a coordinate
lacks its partner. The flag **-i** reads the locations from stdin, one location
per line, and ignores **coordinates** and **points**. A line has the east and
the north coordinate, separated by blanks. If the first line has a third
column, it is the name of the location (a site name or an identifier), and the
tool shows it in every layout. The sixth example uses **-i**.

The tool stops with an error message if no source is given, with a request to
give the coordinates, the **points** option or the flag **-i**, and if
**points** and **coordinates** are given together, also with **-i**: "Options
coordinates and points are mutually exclusive". A location outside the current
region is no error; it gets a null value in every map.

The flag **-v** adds the category of each point of the vector map. It needs
**points**; with **coordinates** or with **-i** the tool stops with the message
"Flag 'v' required option 'points'". The third example uses **-v**.

### Selection of maps

The option **strds** names the space time raster dataset. The option **where**
takes an SQL condition on the registered maps and selects the maps to sample;
without it, all maps are sampled. If the condition selects no map, the tool
stops with the message that the space time raster dataset is empty; a condition
with a syntax error stops it with the message "Invalid where condition" and the
error of the database. The option **order** sorts the selected maps by one or
several columns, separated by commas; the output lists the maps in this order.
The columns are `id`, `name`, `creator`, `mapset`, `creation_time`,
`modification_time`, `start_time` (the default), `end_time`, `north`, `south`,
`west`, `east`, `min` and `max`. The fourth example shows both options.

### Layouts

The option **layout** chooses how the table is arranged. With the flag **-n**
the table has a header line. Without **-n** the table has no header line and
the lines of the data are the same.

- `row` (the default) writes one line for each location and map, location
  after location, in the order of the maps. A line holds the coordinates, the
  start time, the end time and the value: `x`, `y`, `start`, `end` and `value`
  in the header. The coordinates have ten decimals.
- `col` writes one line for each map and one column for each location. A line
  holds the start time, the end time and the value of every location. The title
  of a location column in the header is its coordinates, `east` and `north`,
  separated by a comma. If the output separator is a comma, a semicolon
  separates the parts of the title instead, so that the title stays one column.
  Coordinates have ten decimals.
- `timerow` writes one line for each location and one column for each map. A
  line holds the coordinates followed by the values of all maps, and the title
  of a map column is its start and end time, separated by a semicolon. The
  coordinates are written in the shortest form (`0.5`, not `0.5000000000`).
  This is the layout of *r.what* with the time stamps as column titles.

With **-v**, the category of the point comes first in the `row` and `timerow`
layouts (`cat` in the header) and in front of the coordinates in the title of a
location column in the `col` layout, separated from them by the same character
as the coordinates. With a site name from stdin, the name follows the
coordinates: in the column `site` of the `row` and `timerow` layouts, and as a
third part of the title of a location column in the `col` layout.

### Output

The option **output** names a text file for the table; with `-`, the default,
the table goes to stdout. The tool does not overwrite an existing file unless
the flag `--overwrite` is given. The option **separator** sets the character
between the columns of the table: a character, or one of the names `pipe`
(the default), `comma`, `space`, `tab` and `newline`. It also tells *r.what*
which character to write; it does not change how the locations on stdin are
separated. The option **null_value** sets the text that stands for a null
cell; the default is `*`. The fifth example shows these options.

### Computation

The option **nprocs** sets the number of *r.what* processes that run at the
same time (default 1). Each process samples a share of the maps and writes a
temporary file; the tool puts the files together in the order of the maps. The
table does not depend on the number of processes. The first example uses
**nprocs**.

## NOTES

If *r.what* reads none of the locations, for example because a line of the
locations on stdin has the coordinates separated by `|` or `,` instead of
blanks, the tool ends with the message "No location was sampled: r.what
returned no line. Check the locations and the separator." and writes no
output. It leaves an existing output file as it is. The same happens with an
empty vector map in **points**.

A map that is registered in the dataset but no longer exists stops the tool
with the message "Error running r.what".

A dataset with relative time works in the same way; the tables show the start
and end time of a map as the numbers stored in the temporal database, without
the unit. The seventh example shows it.

A dataset of another mapset (`strds=name@mapset`) is queried like one of the
current mapset; the tool reads its maps from their own mapset.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_what` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset and
region. The series are generated from the elevation model, they are not
measurements: the locations are real climate stations of the dataset, but the
values at them come from a formula and say nothing about the climate there.
The last example uses maps with small constant values.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_what -->

<!-- markdownlint-disable MD046 -->

### Sample a dataset at coordinates

The dataset `temperature_monthly` holds twelve maps of the monthly mean air
temperature in 2020, in degrees Celsius rounded to tenths. They are generated
from the elevation model `elev_state_500m`: 16.5 degrees at sea level and the
northing 160 km, an annual cycle of plus and minus 10.5 degrees with its
maximum in July, 6.5 degrees less for every 1000 m of elevation, and 1 degree
more for every 100 km to the south. Each map is an interval of one month.

The tool samples it at two locations given as **coordinates**, in the
coordinates of the dataset (meters): `500657,183601` is the position of the
climate station 310090, rounded to the meter, and `169208,171737` that of the
station 310184. The formula uses the elevation of the 1 km cell, about 170 m
at the first and 547 m at the second location. The option **where** keeps the
table short, it selects the first three months. The tool writes the default
layout `row`, a line for each location and map, with a header from **-n**. The
option **nprocs** lets two processes sample the maps; the table is the same as
with one. In these months the second location is colder than the first one,
because the formula lowers the temperature with the elevation.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_what
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
    t.rast.what strds=temperature_monthly coordinates=500657,183601,169208,171737 \
        where="start_time < '2020-04-01'" -n nprocs=2
    ```

    ```text
    x|y|start|end|value
    500657.0000000000|183601.0000000000|2020-01-01 00:00:00|2020-02-01 00:00:00|4.7
    500657.0000000000|183601.0000000000|2020-02-01 00:00:00|2020-03-01 00:00:00|5.6
    500657.0000000000|183601.0000000000|2020-03-01 00:00:00|2020-04-01 00:00:00|9
    169208.0000000000|171737.0000000000|2020-01-01 00:00:00|2020-02-01 00:00:00|2.4
    169208.0000000000|171737.0000000000|2020-02-01 00:00:00|2020-03-01 00:00:00|3.2
    169208.0000000000|171737.0000000000|2020-03-01 00:00:00|2020-04-01 00:00:00|6.7
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast_what")
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
    result = tools.t_rast_what(
        strds="temperature_monthly",
        coordinates="500657,183601,169208,171737",
        where="start_time < '2020-04-01'",
        flags="n",
        nprocs=2,
    )
    print(result.text)
    ```

    ```text
    x|y|start|end|value
    500657.0000000000|183601.0000000000|2020-01-01 00:00:00|2020-02-01 00:00:00|4.7
    500657.0000000000|183601.0000000000|2020-02-01 00:00:00|2020-03-01 00:00:00|5.6
    500657.0000000000|183601.0000000000|2020-03-01 00:00:00|2020-04-01 00:00:00|9
    169208.0000000000|171737.0000000000|2020-01-01 00:00:00|2020-02-01 00:00:00|2.4
    169208.0000000000|171737.0000000000|2020-02-01 00:00:00|2020-03-01 00:00:00|3.2
    169208.0000000000|171737.0000000000|2020-03-01 00:00:00|2020-04-01 00:00:00|6.7
    ```

### Choose the layout

The same two locations and months in the layouts `col` and `timerow`. In the
layout `col` each line is a map and each column a location, whose title is its
coordinates. In the layout `timerow` each line is a location and each column a
map, whose title is its start and end time.

=== "Command line"

    ```sh
    t.rast.what strds=temperature_monthly coordinates=500657,183601,169208,171737 \
        where="start_time < '2020-04-01'" layout=col -n
    ```

    ```text
    start|end|500657.0000000000,183601.0000000000|169208.0000000000,171737.0000000000
    2020-01-01 00:00:00|2020-02-01 00:00:00|4.7|2.4
    2020-02-01 00:00:00|2020-03-01 00:00:00|5.6|3.2
    2020-03-01 00:00:00|2020-04-01 00:00:00|9|6.7
    ```

    ```sh
    t.rast.what strds=temperature_monthly coordinates=500657,183601,169208,171737 \
        where="start_time < '2020-04-01'" layout=timerow -n
    ```

    ```text
    x|y|2020-01-01 00:00:00;2020-02-01 00:00:00|2020-02-01 00:00:00;2020-03-01 00:00:00|2020-03-01 00:00:00;2020-04-01 00:00:00
    500657|183601|4.7|5.6|9
    169208|171737|2.4|3.2|6.7
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_what(
        strds="temperature_monthly",
        coordinates="500657,183601,169208,171737",
        where="start_time < '2020-04-01'",
        layout="col",
        flags="n",
    )
    print(result.text)
    ```

    ```text
    start|end|500657.0000000000,183601.0000000000|169208.0000000000,171737.0000000000
    2020-01-01 00:00:00|2020-02-01 00:00:00|4.7|2.4
    2020-02-01 00:00:00|2020-03-01 00:00:00|5.6|3.2
    2020-03-01 00:00:00|2020-04-01 00:00:00|9|6.7
    ```

    ```python
    result = tools.t_rast_what(
        strds="temperature_monthly",
        coordinates="500657,183601,169208,171737",
        where="start_time < '2020-04-01'",
        layout="timerow",
        flags="n",
    )
    print(result.text)
    ```

    ```text
    x|y|2020-01-01 00:00:00;2020-02-01 00:00:00|2020-02-01 00:00:00;2020-03-01 00:00:00|2020-03-01 00:00:00;2020-04-01 00:00:00
    500657|183601|4.7|5.6|9
    169208|171737|2.4|3.2|6.7
    ```

### Sample the points of a vector map

The option **points** takes the locations from a vector map. The flag **-v**
adds the category of each point. The map `stations` holds the places of three
climate stations of `precip_30ynormals`, rounded to whole meters, with the
categories 1, 2 and 18. The station with the category 18 lies on the Outer
Banks, on a cell where the elevation model has no value in this region, so the
generated series has no value there either: the table shows the default `*` in
every month. The first block uses the layout `row`, the second the layout `col`,
where the category is the first part of the title of a column.

=== "Command line"

    ```sh
    v.in.ascii input=- output=stations separator=pipe x=1 y=2 cat=3 <<EOF
    500657|183601|1
    169208|171737|2
    917005|169684|18
    EOF
    ```

    ```sh
    t.rast.what strds=temperature_monthly points=stations \
        where="start_time < '2020-03-01'" -n -v
    ```

    ```text
    cat|x|y|start|end|value
    1|500657.0000000000|183601.0000000000|2020-01-01 00:00:00|2020-02-01 00:00:00|4.7
    1|500657.0000000000|183601.0000000000|2020-02-01 00:00:00|2020-03-01 00:00:00|5.6
    2|169208.0000000000|171737.0000000000|2020-01-01 00:00:00|2020-02-01 00:00:00|2.4
    2|169208.0000000000|171737.0000000000|2020-02-01 00:00:00|2020-03-01 00:00:00|3.2
    18|917005.0000000000|169684.0000000000|2020-01-01 00:00:00|2020-02-01 00:00:00|*
    18|917005.0000000000|169684.0000000000|2020-02-01 00:00:00|2020-03-01 00:00:00|*
    ```

    ```sh
    t.rast.what strds=temperature_monthly points=stations \
        where="start_time < '2020-03-01'" layout=col -n -v
    ```

    ```text
    start|end|1,500657.0000000000,183601.0000000000|2,169208.0000000000,171737.0000000000|18,917005.0000000000,169684.0000000000
    2020-01-01 00:00:00|2020-02-01 00:00:00|4.7|2.4|*
    2020-02-01 00:00:00|2020-03-01 00:00:00|5.6|3.2|*
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.v_in_ascii(
        input=StringIO("500657|183601|1\n169208|171737|2\n917005|169684|18\n"),
        output="stations",
        separator="pipe",
        x=1,
        y=2,
        cat=3,
    )
    ```

    ```python
    result = tools.t_rast_what(
        strds="temperature_monthly",
        points="stations",
        where="start_time < '2020-03-01'",
        flags="nv",
    )
    print(result.text)
    ```

    ```text
    cat|x|y|start|end|value
    1|500657.0000000000|183601.0000000000|2020-01-01 00:00:00|2020-02-01 00:00:00|4.7
    1|500657.0000000000|183601.0000000000|2020-02-01 00:00:00|2020-03-01 00:00:00|5.6
    2|169208.0000000000|171737.0000000000|2020-01-01 00:00:00|2020-02-01 00:00:00|2.4
    2|169208.0000000000|171737.0000000000|2020-02-01 00:00:00|2020-03-01 00:00:00|3.2
    18|917005.0000000000|169684.0000000000|2020-01-01 00:00:00|2020-02-01 00:00:00|*
    18|917005.0000000000|169684.0000000000|2020-02-01 00:00:00|2020-03-01 00:00:00|*
    ```

    ```python
    result = tools.t_rast_what(
        strds="temperature_monthly",
        points="stations",
        where="start_time < '2020-03-01'",
        layout="col",
        flags="nv",
    )
    print(result.text)
    ```

    ```text
    start|end|1,500657.0000000000,183601.0000000000|2,169208.0000000000,171737.0000000000|18,917005.0000000000,169684.0000000000
    2020-01-01 00:00:00|2020-02-01 00:00:00|4.7|2.4|*
    2020-02-01 00:00:00|2020-03-01 00:00:00|5.6|3.2|*
    ```

### Select and order the maps

The option **where** samples only the maps that match a condition: the maps
from November on. The option **order** sorts the maps; the summer maps, sorted
by `max`, the largest value of each map, come in the order of their largest
value, June, August and July, instead of the order of their start times, and so
do the columns of the layout `timerow`, whose titles show the start and end
time of each map.

=== "Command line"

    ```sh
    t.rast.what strds=temperature_monthly coordinates=500657,183601 \
        where="start_time >= '2020-11-01'" -n
    ```

    ```text
    x|y|start|end|value
    500657.0000000000|183601.0000000000|2020-11-01 00:00:00|2020-12-01 00:00:00|10.9
    500657.0000000000|183601.0000000000|2020-12-01 00:00:00|2021-01-01 00:00:00|6.7
    ```

    ```sh
    t.rast.what strds=temperature_monthly coordinates=500657,183601 \
        where="start_time >= '2020-06-01' and start_time < '2020-09-01'" \
        order=max layout=timerow -n
    ```

    ```text
    x|y|2020-06-01 00:00:00;2020-07-01 00:00:00|2020-08-01 00:00:00;2020-09-01 00:00:00|2020-07-01 00:00:00;2020-08-01 00:00:00
    500657|183601|23.7|24.8|25.6
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_what(
        strds="temperature_monthly",
        coordinates="500657,183601",
        where="start_time >= '2020-11-01'",
        flags="n",
    )
    print(result.text)
    ```

    ```text
    x|y|start|end|value
    500657.0000000000|183601.0000000000|2020-11-01 00:00:00|2020-12-01 00:00:00|10.9
    500657.0000000000|183601.0000000000|2020-12-01 00:00:00|2021-01-01 00:00:00|6.7
    ```

    ```python
    result = tools.t_rast_what(
        strds="temperature_monthly",
        coordinates="500657,183601",
        where="start_time >= '2020-06-01' and start_time < '2020-09-01'",
        order="max",
        layout="timerow",
        flags="n",
    )
    print(result.text)
    ```

    ```text
    x|y|2020-06-01 00:00:00;2020-07-01 00:00:00|2020-08-01 00:00:00;2020-09-01 00:00:00|2020-07-01 00:00:00;2020-08-01 00:00:00
    500657|183601|23.7|24.8|25.6
    ```

### Write a file with another separator and null value

Of the three locations the first is the station 310090 of the first example,
the second is the station on the Outer Banks of the third example, and the third,
`100,100`, lies outside the region. The last two give null values in every
map. The option **null_value** writes `NA` instead of `*`, the option
**separator** makes the table comma separated, and the option **output** writes
it to a file instead of stdout, so that the call prints nothing. In the layout
`col`, a semicolon separates the coordinates in the title of a location
column, because the comma separates the columns.

=== "Command line"

    ```sh
    t.rast.what strds=temperature_monthly \
        coordinates=500657,183601,917005,169684,100,100 \
        where="start_time < '2020-03-01'" \
        separator=comma null_value=NA output=result.csv -n
    cat result.csv
    ```

    ```text
    x,y,start,end,value
    500657.0000000000,183601.0000000000,2020-01-01 00:00:00,2020-02-01 00:00:00,4.7
    500657.0000000000,183601.0000000000,2020-02-01 00:00:00,2020-03-01 00:00:00,5.6
    917005.0000000000,169684.0000000000,2020-01-01 00:00:00,2020-02-01 00:00:00,NA
    917005.0000000000,169684.0000000000,2020-02-01 00:00:00,2020-03-01 00:00:00,NA
    100.0000000000,100.0000000000,2020-01-01 00:00:00,2020-02-01 00:00:00,NA
    100.0000000000,100.0000000000,2020-02-01 00:00:00,2020-03-01 00:00:00,NA
    ```

    ```sh
    t.rast.what strds=temperature_monthly \
        coordinates=500657,183601,917005,169684,100,100 \
        where="start_time < '2020-03-01'" \
        separator=comma null_value=NA layout=col -n
    ```

    ```text
    start,end,500657.0000000000;183601.0000000000,917005.0000000000;169684.0000000000,100.0000000000;100.0000000000
    2020-01-01 00:00:00,2020-02-01 00:00:00,4.7,NA,NA
    2020-02-01 00:00:00,2020-03-01 00:00:00,5.6,NA,NA
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    tools.t_rast_what(
        strds="temperature_monthly",
        coordinates="500657,183601,917005,169684,100,100",
        where="start_time < '2020-03-01'",
        separator="comma",
        null_value="NA",
        output="result.csv",
        flags="n",
    )
    print(Path("result.csv").read_text(), end="")
    ```

    ```text
    x,y,start,end,value
    500657.0000000000,183601.0000000000,2020-01-01 00:00:00,2020-02-01 00:00:00,4.7
    500657.0000000000,183601.0000000000,2020-02-01 00:00:00,2020-03-01 00:00:00,5.6
    917005.0000000000,169684.0000000000,2020-01-01 00:00:00,2020-02-01 00:00:00,NA
    917005.0000000000,169684.0000000000,2020-02-01 00:00:00,2020-03-01 00:00:00,NA
    100.0000000000,100.0000000000,2020-01-01 00:00:00,2020-02-01 00:00:00,NA
    100.0000000000,100.0000000000,2020-02-01 00:00:00,2020-03-01 00:00:00,NA
    ```

    ```python
    result = tools.t_rast_what(
        strds="temperature_monthly",
        coordinates="500657,183601,917005,169684,100,100",
        where="start_time < '2020-03-01'",
        separator="comma",
        null_value="NA",
        layout="col",
        flags="n",
    )
    print(result.text)
    ```

    ```text
    start,end,500657.0000000000;183601.0000000000,917005.0000000000;169684.0000000000,100.0000000000;100.0000000000
    2020-01-01 00:00:00,2020-02-01 00:00:00,4.7,NA,NA
    2020-02-01 00:00:00,2020-03-01 00:00:00,5.6,NA,NA
    ```

### Read the locations from stdin

The flag **-i** reads the locations from stdin: a line has the east and the
north coordinate and optionally a name, separated by blanks. Here the name is
the number of the climate station. It appears in the column `site` of the layout
`row`. The call gives no **coordinates** and no **points**.

=== "Command line"

    ```sh
    printf '500657 183601 310090\n169208 171737 310184\n' |
        t.rast.what -i strds=temperature_monthly \
        where="start_time < '2020-03-01'" -n
    ```

    ```text
    x|y|site|start|end|value
    500657.0000000000|183601.0000000000|310090|2020-01-01 00:00:00|2020-02-01 00:00:00|4.7
    500657.0000000000|183601.0000000000|310090|2020-02-01 00:00:00|2020-03-01 00:00:00|5.6
    169208.0000000000|171737.0000000000|310184|2020-01-01 00:00:00|2020-02-01 00:00:00|2.4
    169208.0000000000|171737.0000000000|310184|2020-02-01 00:00:00|2020-03-01 00:00:00|3.2
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_what(
        strds="temperature_monthly",
        flags="in",
        where="start_time < '2020-03-01'",
        stdin=StringIO("500657 183601 310090\n169208 171737 310184\n"),
    )
    print(result.text)
    ```

    ```text
    x|y|site|start|end|value
    500657.0000000000|183601.0000000000|310090|2020-01-01 00:00:00|2020-02-01 00:00:00|4.7
    500657.0000000000|183601.0000000000|310090|2020-02-01 00:00:00|2020-03-01 00:00:00|5.6
    169208.0000000000|171737.0000000000|310184|2020-01-01 00:00:00|2020-02-01 00:00:00|2.4
    169208.0000000000|171737.0000000000|310184|2020-02-01 00:00:00|2020-03-01 00:00:00|3.2
    ```

### Sample a dataset with relative time

A dataset with relative time shows the start and end of a map as numbers. The
dataset `runoff` has two maps of one hour each, starting at 0; the maps hold the
constant values 1 and 2, in millimeters of simulated runoff, over the whole
region.

=== "Command line"

    ```sh
    for step in 1 2; do
        r.mapcalc expression="runoff_$step = $step"
    done
    t.create output=runoff temporaltype=relative title="Runoff" \
        description="Simulated runoff in mm per model hour"
    t.register -i input=runoff maps=runoff_1,runoff_2 start=0 increment=1 unit=hours
    ```

    ```sh
    t.rast.what strds=runoff coordinates=500657,183601 -n
    ```

    ```text
    x|y|start|end|value
    500657.0000000000|183601.0000000000|0|1|1
    500657.0000000000|183601.0000000000|1|2|2
    ```

=== "Python (grass.tools)"

    ```python
    for step in (1, 2):
        tools.r_mapcalc(expression=f"runoff_{step} = {step}")
    tools.t_create(
        output="runoff",
        temporaltype="relative",
        title="Runoff",
        description="Simulated runoff in mm per model hour",
    )
    tools.t_register(
        input="runoff",
        maps="runoff_1,runoff_2",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    ```

    ```python
    result = tools.t_rast_what(strds="runoff", coordinates="500657,183601", flags="n")
    print(result.text)
    ```

    ```text
    x|y|start|end|value
    500657.0000000000|183601.0000000000|0|1|1
    500657.0000000000|183601.0000000000|1|2|2
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.region](g.region.md), [r.mask](r.mask.md), [r.neighbors](r.neighbors.md),
[r.what](r.what.md), [t.info](t.info.md),
[t.rast.aggregate.ds](t.rast.aggregate.ds.md),
[t.rast.extract](t.rast.extract.md), [v.what.strds](v.what.strds.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
