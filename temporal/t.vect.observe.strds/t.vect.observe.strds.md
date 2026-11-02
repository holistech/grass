## DESCRIPTION

*t.vect.observe.strds* observes the values of one or several space time raster
datasets (STRDS) at the positions of the points of a vector map. For every
raster map of the dataset it reads the value under each point and stores it in
a column. The result is a new space time vector dataset (STVDS) with one
vector map and as many layers as the raster dataset has maps: layer 1 holds the
values of the first map, layer 2 those of the second map, and so on. Every
layer is registered in the new dataset with the time of its raster map. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. *[t.vect.what.strds](t.vect.what.strds.md)* does the opposite: it
samples at the positions of the maps of a vector dataset and writes the values
into the table of each vector map. *[t.rast.what](t.rast.what.md)* prints the
values at points instead of storing them. The values are read with
*[v.what.rast](v.what.rast.md)*.

The option **input** is the vector map with the points; it can be in another
mapset. The option **strds** names one or several space time raster datasets,
separated by commas. The option **columns** names the columns that get the
sampled values, one name for each dataset in the order of **strds**; the numbers
of names and datasets must be equal. A column of a CELL (integer) raster map is
of type INTEGER, the column of any other raster map of type DOUBLE PRECISION.

The output is made of two parts, both in the current mapset:

- the option **vector_output** names the new vector map. It is a copy of the
  input in which every point has the same category in each layer. Layer 1 is
  linked to a copy of the table of the input, which gets the new columns in
  addition to the columns that it has; it keeps the layer name of the input.
  Every further layer has a new table `<vector_output>_<layer>` with the
  columns `cat` and the new columns;
- the option **output** names the new space time vector dataset. It takes the
  temporal type (absolute or relative time, with its unit) and the semantic
  type of the first dataset of **strds**. Its maps are the layers
  `<vector_output>:<layer>`, each with the start and end time of its granule.

With one dataset, a granule is a map of the dataset. With several datasets, the
granules are the maps of the first dataset, and the run observes a granule only
if every other dataset has a map with the same time; a granule for which one
dataset has no map is left out. If a dataset has several maps with that time,
only one of them is used. The datasets must have the same temporal type,
and the first dataset needs maps with intervals. All datasets are sampled
as they are, over their whole temporal extent.

Points are sampled in the current computational region (see
*[g.region](g.region.md)*): a point outside the region, or on a cell without a
value, gets a NULL in the column.

The option **where** takes an SQL condition on the table of layer 1 of the
input and selects the points to observe. The points that it does not select are
not in the output map, in none of its layers.

Use *[t.vect.db.select](t.vect.db.select.md)* or *[v.db.select](v.db.select.md)*
to print the values of the new layers.

## NOTES

The condition **where** works on the table of layer 1, so the module stops with
an error before it writes anything if the input map has other layers besides
layer 1, with categories or with a table. A condition that *[v.extract](v.extract.md)*
refuses stops the module with the message `Unable to select the points of <name>
with where`, again before anything is written.

If a column named in **columns** exists in the table of a layer of the input
map, the module stops with an error that names the column and advises the
overwrite flag. With **--overwrite** it keeps the column and replaces its values
with the sampled ones, but a point that is not sampled (a point outside the
region) keeps its old value; a point on a cell without a value gets a NULL.
A name that differs from such a column only in upper and lower case (`Altitude`
for `altitude`) is refused, with and without **--overwrite**, before the output
map is made, with a message that names both spellings.

If a run fails with an error message, the module removes the vector map and the
space time vector dataset that it made, so nothing is left behind. The
exception is a **where** that selects no point, see below. With
**--overwrite** the previous output map and dataset of the same names have
already been replaced when the run fails, so they are gone as well and are not
restored. Without
**--overwrite** an existing output is refused before anything is made and stays
as it was. To keep a result, give the new run another name.

If **where** selects no point, the module ends with a Python error
(`KeyError: 1`) and leaves the empty output vector map behind; it makes no
space time vector dataset. Remove the map with *[g.remove](g.remove.md)*, or
check the condition on the table of the input with
*[v.db.select](v.db.select.md)* first. The second block of the example
"Observe a selection of the points" shows it.

If several datasets are given and no map of the first dataset has a map with
the same time in every other dataset, the module ends without a message and
with the return code 0. It makes an empty space time vector dataset and a vector
map that has only layer 1. Check the result with *[t.info](t.info.md)* if the
datasets may not share a granule. The third block of the example "Observe
several raster datasets" shows it.

The module stops with an error, among others, for these reasons:

- the numbers of **columns** and datasets differ: `The number of columns must be
  equal to the number of space time raster datasets`;
- a dataset has no maps: `Space time raster dataset <name@mapset> is empty`;
- the datasets have different temporal types: `Temporal type of space time
  raster datasets must be equal`;
- with several datasets, the first dataset has maps that are time instances:
  `The temporal map type of the sample dataset must be interval`;
- a raster map of a dataset does not exist any more.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Observe a raster dataset at points

The region has 3 by 3 cells. The raster map `temperature_k` (k from 1 to 3, one
map for each day from 1 March 2026) holds `10 * k` plus the number of the cell,
counted from 1 in the upper left corner row by row: 11 to 19 in the first map,
21 to 29 in the second, 31 to 39 in the third. The input map `stations` has five
points; the column `altitude` is their only attribute, and their categories are
1 to 5. The first four lie in the middle of the cells 1, 3, 5 and 7, the fifth
outside the region.

The run observes the dataset `temperature`, so the output has three layers
with one day each. The first block runs the module and shows the temporal
properties of the new dataset, which holds 15 points (five in each of the three
layers), and its maps. The layers have the column `temp`
and, in layer 1, the columns of `stations` in addition: the points in the cells
1, 3, 5 and 7 read 11, 13, 15 and 17 in the first layer, 21, 23, 25 and 27 in
the second, 31, 33, 35 and 37 in the third. The fifth point has no value. The
second block shows the tables of the layers. The third block shows how the
layers are linked to their tables: layer 1 keeps the layer name `stations` of
the input and uses the table `obs_points`, the others have the table
`obs_points_<layer>`.

=== "Command line"

    ```sh
    g.region n=3 s=0 e=3 w=0 res=1
    for k in 1 2 3; do
        r.mapcalc expression="temperature_$k = 10 * $k + 3 * (row() - 1) + col()"
    done
    t.create output=temperature title="Temperature" \
        description="Daily temperature"
    t.register -i input=temperature \
        maps=temperature_1,temperature_2,temperature_3 \
        start=2026-03-01 increment="1 day"
    v.in.ascii input=- output=stations separator=comma \
        columns="x double precision, y double precision, altitude double precision" <<EOF
    0.5,2.5,100
    2.5,2.5,200
    1.5,1.5,300
    0.5,0.5,400
    5.5,0.5,500
    EOF
    t.vect.observe.strds input=stations strds=temperature output=obs \
        vector_output=obs_points columns=temp
    t.info -g type=stvds input=obs | \
        grep -E "^(temporal_type|semantic_type|number_of_maps|points)="
    t.vect.list input=obs columns=name,layer,start_time,end_time
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    points=15
    number_of_maps=3
    name|layer|start_time|end_time
    obs_points|1|2026-03-01 00:00:00|2026-03-02 00:00:00
    obs_points|2|2026-03-02 00:00:00|2026-03-03 00:00:00
    obs_points|3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    for layer in 1 2 3; do
        v.db.select map=obs_points layer=$layer
    done
    ```

    ```text
    cat|x|y|altitude|temp
    1|0.5|2.5|100|11
    2|2.5|2.5|200|13
    3|1.5|1.5|300|15
    4|0.5|0.5|400|17
    5|5.5|0.5|500|
    cat|temp
    1|21
    2|23
    3|25
    4|27
    5|
    cat|temp
    1|31
    2|33
    3|35
    4|37
    5|
    ```

    ```sh
    v.db.connect -g map=obs_points | cut -d"|" -f1,2
    ```

    ```text
    1/stations|obs_points
    2/obs_points_2|obs_points_2
    3/obs_points_3|obs_points_3
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    for k in (1, 2, 3):
        tools.r_mapcalc(expression=f"temperature_{k} = 10 * {k} + 3 * (row() - 1) + col()")
    tools.t_create(
        output="temperature", title="Temperature", description="Daily temperature"
    )
    tools.t_register(
        input="temperature",
        maps="temperature_1,temperature_2,temperature_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.v_in_ascii(
        input=StringIO("0.5,2.5,100\n2.5,2.5,200\n1.5,1.5,300\n0.5,0.5,400\n5.5,0.5,500\n"),
        output="stations",
        separator="comma",
        columns="x double precision, y double precision, altitude double precision",
    )
    tools.t_vect_observe_strds(
        input="stations",
        strds="temperature",
        output="obs",
        vector_output="obs_points",
        columns="temp",
    )
    info = tools.t_info(type="stvds", input="obs", flags="g").keyval
    for key in ("temporal_type", "semantic_type", "points", "number_of_maps"):
        print(f"{key}={info[key]}")
    print(tools.t_vect_list(input="obs", columns="name,layer,start_time,end_time").text)
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    points=15
    number_of_maps=3
    name|layer|start_time|end_time
    obs_points|1|2026-03-01 00:00:00|2026-03-02 00:00:00
    obs_points|2|2026-03-02 00:00:00|2026-03-03 00:00:00
    obs_points|3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```python
    for layer in (1, 2, 3):
        print(tools.v_db_select(map="obs_points", layer=layer).text)
    ```

    ```text
    cat|x|y|altitude|temp
    1|0.5|2.5|100|11
    2|2.5|2.5|200|13
    3|1.5|1.5|300|15
    4|0.5|0.5|400|17
    5|5.5|0.5|500|
    cat|temp
    1|21
    2|23
    3|25
    4|27
    5|
    cat|temp
    1|31
    2|33
    3|35
    4|37
    5|
    ```

    ```python
    for line in tools.v_db_connect(map="obs_points", flags="g").text.splitlines():
        print("|".join(line.split("|")[:2]))
    ```

    ```text
    1/stations|obs_points
    2/obs_points_2|obs_points_2
    3/obs_points_3|obs_points_3
    ```

### Observe several raster datasets

The second input is the dataset `humidity` from the maps `humidity_2` and
`humidity_3`, which are valid on the second and the third day. Their values are
`k + 0.5 * n` for `humidity_k` and the cell number `n`, except that the cell
number 7 is NULL. The run needs one column for each dataset, so `columns=temp,hum`
gives the values of `temperature` to `temp` and those of `humidity` to `hum`.
The granules are the maps of `temperature` for which `humidity` has a map with
the same time: the first day has no humidity, so it is left out and the output
has two layers, the second and the third day. The point in the cell 7 reads a
NULL in `hum`, and the fifth point outside the region a NULL in both columns.
The second block shows the column types: `temp` follows the integer maps of
`temperature`, `hum` the floating point maps of `humidity`.

The third block adds the dataset `late` with one map from noon of the first day
to noon of the second day. No map of `late` has the time of a map of
`temperature`, so no granule is left: the module ends without a message and
the new dataset `none` has no map (`number_of_maps=0`); the vector map
`none_points` exists, with layer 1 only. The fourth block adds the dataset
`twice` with the two maps `twice_a` (the value 1) and `twice_b` (the value 2)
for the first day. The column `two` gets the value of one of them, here 1, for
the points in the region; the other map is not used.

=== "Command line"

    ```sh
    for k in 2 3; do
        r.mapcalc expression="humidity_$k = if(row() == 3 && col() == 1, null(), $k + 0.5 * (3 * (row() - 1) + col()))"
    done
    t.create output=humidity title="Humidity" description="Daily humidity"
    t.register -i input=humidity maps=humidity_2,humidity_3 \
        start=2026-03-02 increment="1 day"
    t.vect.observe.strds input=stations strds=temperature,humidity \
        output=obs_both vector_output=obs_both_points columns=temp,hum
    t.vect.list input=obs_both columns=name,layer,start_time
    for layer in 1 2; do
        v.db.select map=obs_both_points layer=$layer
    done
    ```

    ```text
    name|layer|start_time
    obs_both_points|1|2026-03-02 00:00:00
    obs_both_points|2|2026-03-03 00:00:00
    cat|x|y|altitude|temp|hum
    1|0.5|2.5|100|21|2.5
    2|2.5|2.5|200|23|3.5
    3|1.5|1.5|300|25|4.5
    4|0.5|0.5|400|27|
    5|5.5|0.5|500||
    cat|temp|hum
    1|31|3.5
    2|33|4.5
    3|35|5.5
    4|37|
    5||
    ```

    ```sh
    db.describe -c table=obs_both_points_2
    ```

    ```text
    ncols: 3
    nrows: 5
    Column 1: cat:INTEGER:20
    Column 2: temp:INTEGER:20
    Column 3: hum:DOUBLE PRECISION:20
    ```

    ```sh
    r.mapcalc expression="late_1 = 1"
    t.create output=late title="Late" description="Noon to noon"
    t.register input=late maps=late_1 \
        start="2026-03-01 12:00:00" end="2026-03-02 12:00:00"
    t.vect.observe.strds input=stations strds=temperature,late \
        output=none vector_output=none_points columns=temp,late
    t.info -g type=stvds input=none | grep -E "^number_of_maps="
    g.list type=vector pattern=none_points
    ```

    ```text
    number_of_maps=0
    none_points
    ```

    ```sh
    r.mapcalc expression="twice_a = 1"
    r.mapcalc expression="twice_b = 2"
    t.create output=twice title="Twice" description="Two maps for one day"
    t.register input=twice maps=twice_a,twice_b start=2026-03-01 end=2026-03-02
    t.vect.observe.strds input=stations strds=temperature,twice \
        output=both vector_output=both_points columns=temp,two
    v.db.select map=both_points layer=1
    ```

    ```text
    cat|x|y|altitude|temp|two
    1|0.5|2.5|100|11|1
    2|2.5|2.5|200|13|1
    3|1.5|1.5|300|15|1
    4|0.5|0.5|400|17|1
    5|5.5|0.5|500||
    ```

=== "Python (grass.tools)"

    ```python
    for k in (2, 3):
        tools.r_mapcalc(
            expression=(
                f"humidity_{k} = if(row() == 3 && col() == 1, null(), "
                f"{k} + 0.5 * (3 * (row() - 1) + col()))"
            )
        )
    tools.t_create(output="humidity", title="Humidity", description="Daily humidity")
    tools.t_register(
        input="humidity",
        maps="humidity_2,humidity_3",
        start="2026-03-02",
        increment="1 day",
        flags="i",
    )
    tools.t_vect_observe_strds(
        input="stations",
        strds="temperature,humidity",
        output="obs_both",
        vector_output="obs_both_points",
        columns="temp,hum",
    )
    print(tools.t_vect_list(input="obs_both", columns="name,layer,start_time").text)
    for layer in (1, 2):
        print(tools.v_db_select(map="obs_both_points", layer=layer).text)
    ```

    ```text
    name|layer|start_time
    obs_both_points|1|2026-03-02 00:00:00
    obs_both_points|2|2026-03-03 00:00:00
    cat|x|y|altitude|temp|hum
    1|0.5|2.5|100|21|2.5
    2|2.5|2.5|200|23|3.5
    3|1.5|1.5|300|25|4.5
    4|0.5|0.5|400|27|
    5|5.5|0.5|500||
    cat|temp|hum
    1|31|3.5
    2|33|4.5
    3|35|5.5
    4|37|
    5||
    ```

    ```python
    print(tools.db_describe(table="obs_both_points_2", flags="c").text)
    ```

    ```text
    ncols: 3
    nrows: 5
    Column 1: cat:INTEGER:20
    Column 2: temp:INTEGER:20
    Column 3: hum:DOUBLE PRECISION:20
    ```

    ```python
    tools.r_mapcalc(expression="late_1 = 1")
    tools.t_create(output="late", title="Late", description="Noon to noon")
    tools.t_register(
        input="late",
        maps="late_1",
        start="2026-03-01 12:00:00",
        end="2026-03-02 12:00:00",
    )
    tools.t_vect_observe_strds(
        input="stations",
        strds="temperature,late",
        output="none",
        vector_output="none_points",
        columns="temp,late",
    )
    info = tools.t_info(type="stvds", input="none", flags="g").keyval
    print(f"number_of_maps={info['number_of_maps']}")
    print(tools.g_list(type="vector", pattern="none_points").text)
    ```

    ```text
    number_of_maps=0
    none_points
    ```

    ```python
    tools.r_mapcalc(expression="twice_a = 1")
    tools.r_mapcalc(expression="twice_b = 2")
    tools.t_create(output="twice", title="Twice", description="Two maps for one day")
    tools.t_register(
        input="twice", maps="twice_a,twice_b", start="2026-03-01", end="2026-03-02"
    )
    tools.t_vect_observe_strds(
        input="stations",
        strds="temperature,twice",
        output="both",
        vector_output="both_points",
        columns="temp,two",
    )
    print(tools.v_db_select(map="both_points", layer=1).text)
    ```

    ```text
    cat|x|y|altitude|temp|two
    1|0.5|2.5|100|11|1
    2|2.5|2.5|200|13|1
    3|1.5|1.5|300|15|1
    4|0.5|0.5|400|17|1
    5|5.5|0.5|500||
    ```

### Observe a selection of the points

**where** selects points of `stations` by their attributes: `altitude >= 300`
keeps the points with the categories 3, 4 and 5. The output map has only these
points, in every layer, with the categories they have in the input. The values
are those of the example above. The layer 1 of the output keeps the layer name
`stations`.

The second block uses a condition that selects no point. The module ends with a
Python error, `KeyError: 1`, and the empty vector map `nowhere_points` stays.

=== "Command line"

    ```sh
    t.vect.observe.strds input=stations strds=temperature output=obs_high \
        vector_output=obs_high_points columns=temp where="altitude >= 300"
    for layer in 1 3; do
        v.db.select map=obs_high_points layer=$layer
    done
    v.db.connect -g map=obs_high_points | cut -d"|" -f1,2
    ```

    ```text
    cat|x|y|altitude|temp
    3|1.5|1.5|300|15
    4|0.5|0.5|400|17
    5|5.5|0.5|500|
    cat|temp
    3|35
    4|37
    5|
    1/stations|obs_high_points
    2/obs_high_points_2|obs_high_points_2
    3/obs_high_points_3|obs_high_points_3
    ```

    ```sh
    if ! (t.vect.observe.strds input=stations strds=temperature \
        output=nowhere vector_output=nowhere_points columns=temp \
        where="altitude > 900" 2>&1 | grep -E "^KeyError"); then
        echo "t.vect.observe.strds failed"
    fi
    g.list type=vector pattern=nowhere_points
    ```

    ```text
    KeyError: 1
    t.vect.observe.strds failed
    nowhere_points
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    tools.t_vect_observe_strds(
        input="stations",
        strds="temperature",
        output="obs_high",
        vector_output="obs_high_points",
        columns="temp",
        where="altitude >= 300",
    )
    for layer in (1, 3):
        print(tools.v_db_select(map="obs_high_points", layer=layer).text)
    for line in tools.v_db_connect(map="obs_high_points", flags="g").text.splitlines():
        print("|".join(line.split("|")[:2]))
    ```

    ```text
    cat|x|y|altitude|temp
    3|1.5|1.5|300|15
    4|0.5|0.5|400|17
    5|5.5|0.5|500|
    cat|temp
    3|35
    4|37
    5|
    1/stations|obs_high_points
    2/obs_high_points_2|obs_high_points_2
    3/obs_high_points_3|obs_high_points_3
    ```

    ```python
    try:
        tools.t_vect_observe_strds(
            input="stations",
            strds="temperature",
            output="nowhere",
            vector_output="nowhere_points",
            columns="temp",
            where="altitude > 900",
        )
    except ToolError as error:
        print(error.stderr.strip().splitlines()[-1])
        print("t.vect.observe.strds failed")
    print(tools.g_list(type="vector", pattern="nowhere_points").text)
    ```

    ```text
    KeyError: 1
    t.vect.observe.strds failed
    nowhere_points
    ```

### Use the name of a column that the input has

The column `altitude` exists in the table of `stations`. The first block shows
that the module refuses it and prints the error. With **--overwrite** (second
block) the module writes the sampled values into the existing column of layer 1
and the layers 2 and 3 get a column with that name. The fifth point lies outside
the region, is not sampled and keeps the altitude 500. The third block shows
that `Altitude` is refused, with **--overwrite** too, because it differs from
`altitude` only in the case of a letter.

=== "Command line"

    ```sh
    if ! (t.vect.observe.strds input=stations strds=temperature \
        output=check vector_output=check_points columns=altitude 2>&1 |
        sed -n '/^ERROR/,$p'); then
        echo "t.vect.observe.strds failed"
    fi
    ```

    ```text
    ERROR: Unable to add column altitude to vector map <check_points> with
           layer 1: the column exists, use the overwrite flag to replace its
           values
    t.vect.observe.strds failed
    ```

    ```sh
    t.vect.observe.strds --overwrite input=stations strds=temperature \
        output=check vector_output=check_points columns=altitude
    for layer in 1 3; do
        v.db.select map=check_points layer=$layer
    done
    ```

    ```text
    cat|x|y|altitude
    1|0.5|2.5|11
    2|2.5|2.5|13
    3|1.5|1.5|15
    4|0.5|0.5|17
    5|5.5|0.5|500
    cat|altitude
    1|31
    2|33
    3|35
    4|37
    5|
    ```

    ```sh
    if ! (t.vect.observe.strds --overwrite input=stations strds=temperature \
        output=check vector_output=check_points columns=Altitude 2>&1 |
        sed -n '/^ERROR/,$p'); then
        echo "t.vect.observe.strds failed"
    fi
    ```

    ```text
    ERROR: Column <Altitude> differs only in case from the column <altitude> of
           the table of vector map <stations> layer 1
    t.vect.observe.strds failed
    ```

=== "Python (grass.tools)"

    ```python
    try:
        tools.t_vect_observe_strds(
            input="stations",
            strds="temperature",
            output="check",
            vector_output="check_points",
            columns="altitude",
        )
    except ToolError as error:
        lines = error.stderr.strip().splitlines()
        first = [line.startswith("ERROR") for line in lines].index(True)
        print("\n".join(lines[first:]))
        print("t.vect.observe.strds failed")
    ```

    ```text
    ERROR: Unable to add column altitude to vector map <check_points> with
           layer 1: the column exists, use the overwrite flag to replace its
           values
    t.vect.observe.strds failed
    ```

    ```python
    tools.t_vect_observe_strds(
        input="stations",
        strds="temperature",
        output="check",
        vector_output="check_points",
        columns="altitude",
        overwrite=True,
    )
    for layer in (1, 3):
        print(tools.v_db_select(map="check_points", layer=layer).text)
    ```

    ```text
    cat|x|y|altitude
    1|0.5|2.5|11
    2|2.5|2.5|13
    3|1.5|1.5|15
    4|0.5|0.5|17
    5|5.5|0.5|500
    cat|altitude
    1|31
    2|33
    3|35
    4|37
    5|
    ```

    ```python
    try:
        tools.t_vect_observe_strds(
            input="stations",
            strds="temperature",
            output="check",
            vector_output="check_points",
            columns="Altitude",
            overwrite=True,
        )
    except ToolError as error:
        lines = error.stderr.strip().splitlines()
        first = [line.startswith("ERROR") for line in lines].index(True)
        print("\n".join(lines[first:]))
        print("t.vect.observe.strds failed")
    ```

    ```text
    ERROR: Column <Altitude> differs only in case from the column <altitude> of
           the table of vector map <stations> layer 1
    t.vect.observe.strds failed
    ```

### Observe a dataset with relative time

The dataset `model` has relative time with the unit hours: `step_1` from 0 to 1
and `step_2` from 1 to 2, with the values `100 * k + col()` for `step_k`. The
points in the columns 1, 3, 2 and 1 read 201, 203, 202 and 201 in layer 2. The
output dataset has relative time with the same unit, and its layers have the
times of the maps as numbers.

=== "Command line"

    ```sh
    for k in 1 2; do
        r.mapcalc expression="step_$k = 100 * $k + col()"
    done
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i input=model maps=step_1,step_2 start=0 increment=1 unit=hours
    t.vect.observe.strds input=stations strds=model output=obs_model \
        vector_output=obs_model_points columns=step
    t.vect.list input=obs_model columns=name,layer,start_time,end_time
    t.info -g type=stvds input=obs_model | grep -E "^(temporal_type|unit)="
    v.db.select map=obs_model_points layer=2
    ```

    ```text
    name|layer|start_time|end_time
    obs_model_points|1|0|1
    obs_model_points|2|1|2
    temporal_type=relative
    unit=hours
    cat|step
    1|201
    2|203
    3|202
    4|201
    5|
    ```

=== "Python (grass.tools)"

    ```python
    for k in (1, 2):
        tools.r_mapcalc(expression=f"step_{k} = 100 * {k} + col()")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        input="model", maps="step_1,step_2", start=0, increment=1, unit="hours", flags="i"
    )
    tools.t_vect_observe_strds(
        input="stations",
        strds="model",
        output="obs_model",
        vector_output="obs_model_points",
        columns="step",
    )
    print(
        tools.t_vect_list(input="obs_model", columns="name,layer,start_time,end_time").text
    )
    info = tools.t_info(type="stvds", input="obs_model", flags="g").keyval
    for key in ("temporal_type", "unit"):
        print(f"{key}={info[key]}")
    print(tools.v_db_select(map="obs_model_points", layer=2).text)
    ```

    ```text
    name|layer|start_time|end_time
    obs_model_points|1|0|1
    obs_model_points|2|1|2
    temporal_type=relative
    unit=hours
    cat|step
    1|201
    2|203
    3|202
    4|201
    5|
    ```

### Observe data of another mapset

The input map and the raster dataset may be in another mapset: the names with
the mapset, `stations@PERMANENT` and `temperature@PERMANENT`, select them. The
output map and dataset are made in the current mapset, here the new mapset
`analysis`. A new mapset has its own region, so the example sets the region
again before the points are sampled.

=== "Command line"

    ```sh
    g.mapset -c mapset=analysis
    g.region n=3 s=0 e=3 w=0 res=1
    t.vect.observe.strds input=stations@PERMANENT \
        strds=temperature@PERMANENT output=remote \
        vector_output=remote_points columns=temp
    t.vect.list input=remote columns=name,layer,mapset
    v.db.select map=remote_points layer=1 columns=cat,temp
    ```

    ```text
    name|layer|mapset
    remote_points|1|analysis
    remote_points|2|analysis
    remote_points|3|analysis
    cat|temp
    1|11
    2|13
    3|15
    4|17
    5|
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="analysis", flags="c")
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    tools.t_vect_observe_strds(
        input="stations@PERMANENT",
        strds="temperature@PERMANENT",
        output="remote",
        vector_output="remote_points",
        columns="temp",
    )
    print(tools.t_vect_list(input="remote", columns="name,layer,mapset").text)
    print(tools.v_db_select(map="remote_points", layer=1, columns="cat,temp").text)
    ```

    ```text
    name|layer|mapset
    remote_points|1|analysis
    remote_points|2|analysis
    remote_points|3|analysis
    cat|temp
    1|11
    2|13
    3|15
    4|17
    5|
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.mapset](g.mapset.md), [g.region](g.region.md), [t.create](t.create.md),
[t.info](t.info.md), [t.rast.what](t.rast.what.md),
[t.register](t.register.md), [t.vect.db.select](t.vect.db.select.md),
[t.vect.list](t.vect.list.md), [t.vect.what.strds](t.vect.what.strds.md),
[v.db.select](v.db.select.md), [v.extract](v.extract.md),
[v.what.rast](v.what.rast.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
