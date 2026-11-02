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

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Sample a dataset at coordinates

The first example creates a space time raster dataset `temperature` with three
daily maps on a region of 3 by 3 cells of size 1, and samples it at two
locations given as **coordinates**. The map `thu` holds `10 * row + col` in
each cell, counted from the north-west corner, so the cell in the first row
and the first column holds 11 and the cell in the third row and the third
column holds 33. The map `fri` adds 100 and has no value in the middle column,
and `sat` adds 200. The location `0.5,2.5` lies in the cell with the value 11
and `2.5,0.5` in the cell with the value 33. The tool writes the default
layout `row`, a line for each location and map, with a header from **-n**. The
option **nprocs** lets two processes sample the maps; the table is the same as
with one.

=== "Command line"

    ```sh
    g.region n=3 s=0 e=3 w=0 res=1
    r.mapcalc expression="thu = row() * 10 + col()"
    r.mapcalc expression="fri = if(col() == 2, null(), row() * 10 + col() + 100)"
    r.mapcalc expression="sat = row() * 10 + col() + 200"
    t.create output=temperature title="Temperature" \
        description="Daily temperature"
    t.register -i input=temperature maps=thu,fri,sat \
        start=2026-03-05 increment="1 day"
    ```

    ```sh
    t.rast.what strds=temperature coordinates=0.5,2.5,2.5,0.5 -n nprocs=2
    ```

    ```text
    x|y|start|end|value
    0.5000000000|2.5000000000|2026-03-05 00:00:00|2026-03-06 00:00:00|11
    0.5000000000|2.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|111
    0.5000000000|2.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|211
    2.5000000000|0.5000000000|2026-03-05 00:00:00|2026-03-06 00:00:00|33
    2.5000000000|0.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|133
    2.5000000000|0.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|233
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    tools.r_mapcalc(expression="thu = row() * 10 + col()")
    tools.r_mapcalc(expression="fri = if(col() == 2, null(), row() * 10 + col() + 100)")
    tools.r_mapcalc(expression="sat = row() * 10 + col() + 200")
    tools.t_create(
        output="temperature", title="Temperature", description="Daily temperature"
    )
    tools.t_register(
        input="temperature",
        maps="thu,fri,sat",
        start="2026-03-05",
        increment="1 day",
        flags="i",
    )
    ```

    ```python
    result = tools.t_rast_what(
        strds="temperature", coordinates="0.5,2.5,2.5,0.5", flags="n", nprocs=2
    )
    print(result.text)
    ```

    ```text
    x|y|start|end|value
    0.5000000000|2.5000000000|2026-03-05 00:00:00|2026-03-06 00:00:00|11
    0.5000000000|2.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|111
    0.5000000000|2.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|211
    2.5000000000|0.5000000000|2026-03-05 00:00:00|2026-03-06 00:00:00|33
    2.5000000000|0.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|133
    2.5000000000|0.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|233
    ```

### Choose the layout

The same two locations in the layouts `col` and `timerow`. In the layout `col`
each line is a map and each column a location, whose title is its coordinates.
In the layout `timerow` each line is a location and each column a map, whose
title is its start and end time.

=== "Command line"

    ```sh
    t.rast.what strds=temperature coordinates=0.5,2.5,2.5,0.5 layout=col -n
    ```

    ```text
    start|end|0.5000000000,2.5000000000|2.5000000000,0.5000000000
    2026-03-05 00:00:00|2026-03-06 00:00:00|11|33
    2026-03-06 00:00:00|2026-03-07 00:00:00|111|133
    2026-03-07 00:00:00|2026-03-08 00:00:00|211|233
    ```

    ```sh
    t.rast.what strds=temperature coordinates=0.5,2.5,2.5,0.5 layout=timerow -n
    ```

    ```text
    x|y|2026-03-05 00:00:00;2026-03-06 00:00:00|2026-03-06 00:00:00;2026-03-07 00:00:00|2026-03-07 00:00:00;2026-03-08 00:00:00
    0.5|2.5|11|111|211
    2.5|0.5|33|133|233
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_what(
        strds="temperature", coordinates="0.5,2.5,2.5,0.5", layout="col", flags="n"
    )
    print(result.text)
    ```

    ```text
    start|end|0.5000000000,2.5000000000|2.5000000000,0.5000000000
    2026-03-05 00:00:00|2026-03-06 00:00:00|11|33
    2026-03-06 00:00:00|2026-03-07 00:00:00|111|133
    2026-03-07 00:00:00|2026-03-08 00:00:00|211|233
    ```

    ```python
    result = tools.t_rast_what(
        strds="temperature",
        coordinates="0.5,2.5,2.5,0.5",
        layout="timerow",
        flags="n",
    )
    print(result.text)
    ```

    ```text
    x|y|2026-03-05 00:00:00;2026-03-06 00:00:00|2026-03-06 00:00:00;2026-03-07 00:00:00|2026-03-07 00:00:00;2026-03-08 00:00:00
    0.5|2.5|11|111|211
    2.5|0.5|33|133|233
    ```

### Sample the points of a vector map

The option **points** takes the locations from a vector map. The flag **-v**
adds the category of each point. The map `stations` has three points with the
categories 7, 8 and 9, in the cells with the values 11, 33 and 22. The cell
at the third point has no value in the map `fri`; the table shows the default
`*`. The first block uses the layout `row`, the second the layout `col`, where
the category is the first part of the title of a column.

=== "Command line"

    ```sh
    v.in.ascii input=- output=stations separator=pipe x=1 y=2 cat=3 <<EOF
    0.5|2.5|7
    2.5|0.5|8
    1.5|1.5|9
    EOF
    ```

    ```sh
    t.rast.what strds=temperature points=stations -n -v
    ```

    ```text
    cat|x|y|start|end|value
    7|0.5000000000|2.5000000000|2026-03-05 00:00:00|2026-03-06 00:00:00|11
    7|0.5000000000|2.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|111
    7|0.5000000000|2.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|211
    8|2.5000000000|0.5000000000|2026-03-05 00:00:00|2026-03-06 00:00:00|33
    8|2.5000000000|0.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|133
    8|2.5000000000|0.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|233
    9|1.5000000000|1.5000000000|2026-03-05 00:00:00|2026-03-06 00:00:00|22
    9|1.5000000000|1.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|*
    9|1.5000000000|1.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|222
    ```

    ```sh
    t.rast.what strds=temperature points=stations layout=col -n -v
    ```

    ```text
    start|end|7,0.5000000000,2.5000000000|8,2.5000000000,0.5000000000|9,1.5000000000,1.5000000000
    2026-03-05 00:00:00|2026-03-06 00:00:00|11|33|22
    2026-03-06 00:00:00|2026-03-07 00:00:00|111|133|*
    2026-03-07 00:00:00|2026-03-08 00:00:00|211|233|222
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.v_in_ascii(
        input=StringIO("0.5|2.5|7\n2.5|0.5|8\n1.5|1.5|9\n"),
        output="stations",
        separator="pipe",
        x=1,
        y=2,
        cat=3,
    )
    ```

    ```python
    result = tools.t_rast_what(strds="temperature", points="stations", flags="nv")
    print(result.text)
    ```

    ```text
    cat|x|y|start|end|value
    7|0.5000000000|2.5000000000|2026-03-05 00:00:00|2026-03-06 00:00:00|11
    7|0.5000000000|2.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|111
    7|0.5000000000|2.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|211
    8|2.5000000000|0.5000000000|2026-03-05 00:00:00|2026-03-06 00:00:00|33
    8|2.5000000000|0.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|133
    8|2.5000000000|0.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|233
    9|1.5000000000|1.5000000000|2026-03-05 00:00:00|2026-03-06 00:00:00|22
    9|1.5000000000|1.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|*
    9|1.5000000000|1.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|222
    ```

    ```python
    result = tools.t_rast_what(
        strds="temperature", points="stations", layout="col", flags="nv"
    )
    print(result.text)
    ```

    ```text
    start|end|7,0.5000000000,2.5000000000|8,2.5000000000,0.5000000000|9,1.5000000000,1.5000000000
    2026-03-05 00:00:00|2026-03-06 00:00:00|11|33|22
    2026-03-06 00:00:00|2026-03-07 00:00:00|111|133|*
    2026-03-07 00:00:00|2026-03-08 00:00:00|211|233|222
    ```

### Select and order the maps

The option **where** samples only the maps that match a condition: the maps
`fri` and `sat` start on or after 2026-03-06. The option **order** sorts the
maps; sorted by `name`, they come in the alphabetical order `fri`, `sat`,
`thu` instead of the order of their start times, and so do the columns of the
layout `timerow`, whose titles show the start and end time of each map.

=== "Command line"

    ```sh
    t.rast.what strds=temperature coordinates=1.5,1.5 \
        where="start_time >= '2026-03-06'" -n
    ```

    ```text
    x|y|start|end|value
    1.5000000000|1.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|*
    1.5000000000|1.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|222
    ```

    ```sh
    t.rast.what strds=temperature coordinates=1.5,1.5 order=name \
        layout=timerow -n
    ```

    ```text
    x|y|2026-03-06 00:00:00;2026-03-07 00:00:00|2026-03-07 00:00:00;2026-03-08 00:00:00|2026-03-05 00:00:00;2026-03-06 00:00:00
    1.5|1.5|*|222|22
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_what(
        strds="temperature",
        coordinates="1.5,1.5",
        where="start_time >= '2026-03-06'",
        flags="n",
    )
    print(result.text)
    ```

    ```text
    x|y|start|end|value
    1.5000000000|1.5000000000|2026-03-06 00:00:00|2026-03-07 00:00:00|*
    1.5000000000|1.5000000000|2026-03-07 00:00:00|2026-03-08 00:00:00|222
    ```

    ```python
    result = tools.t_rast_what(
        strds="temperature",
        coordinates="1.5,1.5",
        order="name",
        layout="timerow",
        flags="n",
    )
    print(result.text)
    ```

    ```text
    x|y|2026-03-06 00:00:00;2026-03-07 00:00:00|2026-03-07 00:00:00;2026-03-08 00:00:00|2026-03-05 00:00:00;2026-03-06 00:00:00
    1.5|1.5|*|222|22
    ```

### Write a file with another separator and null value

The locations `1.5,1.5` and `100,100` give null values: the middle cell of the
map `fri` has no value, and the second location lies outside the region. The
option **null_value** writes `NA` instead of `*`, the option **separator**
makes the table comma separated, and the option **output** writes it to a file
instead of stdout, so that the call prints nothing. In the layout `col`, a
semicolon separates the coordinates in the title of a location column,
because the comma separates the columns.

=== "Command line"

    ```sh
    t.rast.what strds=temperature coordinates=1.5,1.5,100,100 \
        separator=comma null_value=NA output=result.csv -n
    cat result.csv
    ```

    ```text
    x,y,start,end,value
    1.5000000000,1.5000000000,2026-03-05 00:00:00,2026-03-06 00:00:00,22
    1.5000000000,1.5000000000,2026-03-06 00:00:00,2026-03-07 00:00:00,NA
    1.5000000000,1.5000000000,2026-03-07 00:00:00,2026-03-08 00:00:00,222
    100.0000000000,100.0000000000,2026-03-05 00:00:00,2026-03-06 00:00:00,NA
    100.0000000000,100.0000000000,2026-03-06 00:00:00,2026-03-07 00:00:00,NA
    100.0000000000,100.0000000000,2026-03-07 00:00:00,2026-03-08 00:00:00,NA
    ```

    ```sh
    t.rast.what strds=temperature coordinates=1.5,1.5,100,100 \
        separator=comma null_value=NA layout=col -n
    ```

    ```text
    start,end,1.5000000000;1.5000000000,100.0000000000;100.0000000000
    2026-03-05 00:00:00,2026-03-06 00:00:00,22,NA
    2026-03-06 00:00:00,2026-03-07 00:00:00,NA,NA
    2026-03-07 00:00:00,2026-03-08 00:00:00,222,NA
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    tools.t_rast_what(
        strds="temperature",
        coordinates="1.5,1.5,100,100",
        separator="comma",
        null_value="NA",
        output="result.csv",
        flags="n",
    )
    print(Path("result.csv").read_text(), end="")
    ```

    ```text
    x,y,start,end,value
    1.5000000000,1.5000000000,2026-03-05 00:00:00,2026-03-06 00:00:00,22
    1.5000000000,1.5000000000,2026-03-06 00:00:00,2026-03-07 00:00:00,NA
    1.5000000000,1.5000000000,2026-03-07 00:00:00,2026-03-08 00:00:00,222
    100.0000000000,100.0000000000,2026-03-05 00:00:00,2026-03-06 00:00:00,NA
    100.0000000000,100.0000000000,2026-03-06 00:00:00,2026-03-07 00:00:00,NA
    100.0000000000,100.0000000000,2026-03-07 00:00:00,2026-03-08 00:00:00,NA
    ```

    ```python
    result = tools.t_rast_what(
        strds="temperature",
        coordinates="1.5,1.5,100,100",
        separator="comma",
        null_value="NA",
        layout="col",
        flags="n",
    )
    print(result.text)
    ```

    ```text
    start,end,1.5000000000;1.5000000000,100.0000000000;100.0000000000
    2026-03-05 00:00:00,2026-03-06 00:00:00,22,NA
    2026-03-06 00:00:00,2026-03-07 00:00:00,NA,NA
    2026-03-07 00:00:00,2026-03-08 00:00:00,222,NA
    ```

### Read the locations from stdin

The flag **-i** reads the locations from stdin: a line has the east and the
north coordinate and optionally a name, separated by blanks. The name of the
location appears in the column `site` of the layout `row`. The call gives
no **coordinates** and no **points**.

=== "Command line"

    ```sh
    printf '0.5 2.5 north\n2.5 0.5 south\n' | t.rast.what -i strds=temperature -n
    ```

    ```text
    x|y|site|start|end|value
    0.5000000000|2.5000000000|north|2026-03-05 00:00:00|2026-03-06 00:00:00|11
    0.5000000000|2.5000000000|north|2026-03-06 00:00:00|2026-03-07 00:00:00|111
    0.5000000000|2.5000000000|north|2026-03-07 00:00:00|2026-03-08 00:00:00|211
    2.5000000000|0.5000000000|south|2026-03-05 00:00:00|2026-03-06 00:00:00|33
    2.5000000000|0.5000000000|south|2026-03-06 00:00:00|2026-03-07 00:00:00|133
    2.5000000000|0.5000000000|south|2026-03-07 00:00:00|2026-03-08 00:00:00|233
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_what(
        strds="temperature",
        flags="in",
        stdin=StringIO("0.5 2.5 north\n2.5 0.5 south\n"),
    )
    print(result.text)
    ```

    ```text
    x|y|site|start|end|value
    0.5000000000|2.5000000000|north|2026-03-05 00:00:00|2026-03-06 00:00:00|11
    0.5000000000|2.5000000000|north|2026-03-06 00:00:00|2026-03-07 00:00:00|111
    0.5000000000|2.5000000000|north|2026-03-07 00:00:00|2026-03-08 00:00:00|211
    2.5000000000|0.5000000000|south|2026-03-05 00:00:00|2026-03-06 00:00:00|33
    2.5000000000|0.5000000000|south|2026-03-06 00:00:00|2026-03-07 00:00:00|133
    2.5000000000|0.5000000000|south|2026-03-07 00:00:00|2026-03-08 00:00:00|233
    ```

### Sample a dataset with relative time

A dataset with relative time shows the start and end of a map as numbers. The
dataset `model` has two maps of one hour each, starting at 0; the maps hold the
values 1 and 2.

=== "Command line"

    ```sh
    r.mapcalc expression="step_1 = 1"
    r.mapcalc expression="step_2 = 2"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i input=model maps=step_1,step_2 start=0 increment=1 unit=hours
    ```

    ```sh
    t.rast.what strds=model coordinates=0.5,0.5 -n
    ```

    ```text
    x|y|start|end|value
    0.5000000000|0.5000000000|0|1|1
    0.5000000000|0.5000000000|1|2|2
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="step_1 = 1")
    tools.r_mapcalc(expression="step_2 = 2")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        input="model", maps="step_1,step_2", start=0, increment=1, unit="hours", flags="i"
    )
    ```

    ```python
    result = tools.t_rast_what(strds="model", coordinates="0.5,0.5", flags="n")
    print(result.text)
    ```

    ```text
    x|y|start|end|value
    0.5000000000|0.5000000000|0|1|1
    0.5000000000|0.5000000000|1|2|2
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
