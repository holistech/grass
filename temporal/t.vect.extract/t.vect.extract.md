## DESCRIPTION

*t.vect.extract* selects maps of a space time vector dataset and registers
them in a new space time vector dataset. On the way, it can extract the
features that meet an SQL condition on their attribute table from each
selected map into a new vector map. Use it to cut a time window out of a
dataset, or to keep the features of every map that meet the same condition.
See the [introduction to temporal data processing](temporalintro.md) for
space time datasets. *[t.vect.list](t.vect.list.md)* lists the maps of the
result. The tool works like *[t.rast.extract](t.rast.extract.md)*, on space
time vector datasets (STVDS) and vector maps instead of space time raster
datasets and raster maps, with *[v.extract](v.extract.md)* in place of
*r.mapcalc*.

The option **input** names the space time vector dataset, the option
**output** the new one. The new dataset takes the temporal type and the
semantic type of the input dataset. The output always belongs to the current
mapset. An existing output dataset is refused unless the flag **--overwrite**
is given; then it is replaced.

### Select the maps

The option **where** takes an SQL condition on the columns of the registered
maps, the columns that *[t.vect.list](t.vect.list.md)* offers, such as
`start_time >= '2026-03-03'`, which selects the maps that start on 3 March or
later. Without **where**, all maps are selected.

### Register or extract

Without **expression**, *t.vect.extract* creates no map. It registers the
selected maps themselves in the new dataset, so a map is then part of two
datasets and the data are not duplicated.

With **expression**, the tool runs *v.extract* once for each selected map and
registers the new maps, with the start and end time of the map they come from,
in the new dataset. The expression is an SQL condition without the word
`where`, such as `speed > 22`. It is not a map algebra expression, as in
*t.rast.extract*: *v.extract* applies it to the attribute
table of the map and copies the features that meet it, with their table rows,
into the new map. The new maps belong to the current mapset. The expression
needs the option **basename**.

The options **layer** and **type** tell *v.extract* where to look. The option
**layer** (default `1`) is the layer whose table the expression reads, for the
maps that are registered without a layer. A map registered as `name:2` (`name`
and layer `2`) is extracted from layer 2, as the layer example shows. The
option **type** (default `point,line,boundary,centroid,area`) lists the feature
types that are copied; any other feature of the map is left out.

The new maps are named after **basename**, followed by an underscore and a
suffix that the option **suffix** chooses.

- `gran` (the default) takes the start time of the map, cut to the unit of the
  granularity of the input dataset: year and month for a granularity of three
  months, year, month and day for a granularity of one day (`2026_03_01`). A
  dataset of a single time instant has no granularity; `gran` then takes the
  full start time, as `time` does.
- `time` takes the full start time: `2026_03_01T00_00_00`.
- `num` numbers the selected maps from 1 in the order of their start time and
  map id, with five digits (`00001`); the number counts also the maps that come
  out empty. `num%03` gives three digits (`001`).
- With relative time, a start time is a number without a calendar date. Every
  suffix then gives the number, as `num` does.

Two layers of one vector map, registered as `name:1` and `name:2` for the same
time, get the same name from the suffix. The layer is then appended to both
names: `bx_2026_03_01_1` and `bx_2026_03_01_2`. Two different maps of one time
with the same layer also get the same name. The first of them, in the order of
start time and map id, keeps the name; the second and every further map get the
number `_2`, `_3` and so on after it. A number that another new map has as its
name is skipped.

A new map without any feature is empty, for example when no feature meets the
expression. By default it is not registered in the new dataset and the map is
removed after the run. The flag **-n** registers the empty maps and keeps
them. An expression therefore selects maps by their contents as well.

The option **nprocs** sets the number of *v.extract* processes that run at the
same time. The default is `1`. The parser advises to use more than one only
with a database backend that supports concurrent writing; the default backend
is SQLite.

## NOTES

If **where** selects no map, or the input dataset has none, *t.vect.extract*
warns "Nothing found in the database for space time dataset" and makes no
output dataset; for a **where** that selects nothing, the message adds that
"Dataset is empty or where clause is too constrained or incorrect". A
condition with a syntax error stops with the error "Invalid where condition".

The tool stops with an error if **expression** is given without **basename**
("You need to specify the base name of new created maps"), if the input dataset
does not exist, if the output dataset exists and **--overwrite** is not given,
and if **suffix** is not `gran`, `time`, `num` or `num%NN` ("Invalid
suffix"). A dot in the name of the output dataset is refused: "a dot
is not allowed". An **expression** that *v.extract* does not accept stops with
"Error in computation process"; the maps that the run has made are removed.
If a new map is already in the temporal database and **--overwrite** is not
given, the tool stops before it extracts anything, with "Map ... is already in
temporal database, use overwrite flag to overwrite", and makes no dataset.

The last example shows that a dataset of another mapset works as input when an
**expression** is given. Without an **expression**, such a dataset is refused,
and the empty output dataset that the refusal leaves behind has to be removed
with *[t.remove](t.remove.md)*. Add an **expression** that every feature
meets, such as `level > 0` there, to copy the maps instead.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Select maps by time

The dataset `gauges` has four point maps of wind speed for the days from 1 to
4 March 2026. Map `gauges_k` has three points at `(k, 1)`, `(k, 2)` and
`(k, 3)` with the speeds `10 * k + 1`, `10 * k + 2` and `10 * k + 3`, so the
speeds are 11 to 13, 21 to 23, 31 to 33 and 41 to 43.

The first block extracts the maps from 3 March on into the dataset `later`.
There is no **expression**, so no map is made: the second block lists the
vector maps of the mapset, and they are still the four maps of `gauges`. The
dataset `later` lists two of them, with three points each. The third block
shows what the new dataset takes from the input: the temporal type and the
semantic type, the start and end time and the number of maps and points that
follow from the maps it holds.

=== "Command line"

    ```sh
    for k in 1 2 3 4; do
        v.in.ascii input=- output=gauges_$k separator=comma \
            columns="x double precision, y double precision, speed double precision" <<EOF
    $k,1,$((10 * k + 1))
    $k,2,$((10 * k + 2))
    $k,3,$((10 * k + 3))
    EOF
    done
    t.create type=stvds output=gauges title="Wind speed" \
        description="Wind speed at three gauges"
    t.register -i type=vector input=gauges \
        maps=gauges_1,gauges_2,gauges_3,gauges_4 \
        start=2026-03-01 increment="1 day"
    t.vect.extract input=gauges output=later \
        where="start_time >= '2026-03-03'"
    t.vect.list input=later columns=name,start_time,points
    ```

    ```text
    name|start_time|points
    gauges_3|2026-03-03 00:00:00|3
    gauges_4|2026-03-04 00:00:00|3
    ```

    ```sh
    g.list type=vector
    ```

    ```text
    gauges_1
    gauges_2
    gauges_3
    gauges_4
    ```

    ```sh
    t.info -g type=stvds input=later | grep -E "^(temporal_type|semantic_type|start_time|end_time|number_of_maps|points)="
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    start_time='2026-03-03 00:00:00'
    end_time='2026-03-05 00:00:00'
    points=6
    number_of_maps=2
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    from grass.tools import Tools

    tools = Tools()
    for k in range(1, 5):
        rows = "".join(f"{k},{i},{10 * k + i}\n" for i in (1, 2, 3))
        tools.v_in_ascii(
            input=StringIO(rows),
            output=f"gauges_{k}",
            separator="comma",
            columns="x double precision, y double precision, speed double precision",
        )
    tools.t_create(
        type="stvds",
        output="gauges",
        title="Wind speed",
        description="Wind speed at three gauges",
    )
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauges_1,gauges_2,gauges_3,gauges_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_vect_extract(input="gauges", output="later", where="start_time >= '2026-03-03'")
    print(tools.t_vect_list(input="later", columns="name,start_time,points").text)
    ```

    ```text
    name|start_time|points
    gauges_3|2026-03-03 00:00:00|3
    gauges_4|2026-03-04 00:00:00|3
    ```

    ```python
    print(tools.g_list(type="vector").text)
    ```

    ```text
    gauges_1
    gauges_2
    gauges_3
    gauges_4
    ```

    ```python
    info = tools.t_info(type="stvds", input="later", flags="g").keyval
    keys = (
        "temporal_type",
        "semantic_type",
        "start_time",
        "end_time",
        "points",
        "number_of_maps",
    )
    for key in keys:
        print(f"{key}={info[key]}")
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    start_time='2026-03-03 00:00:00'
    end_time='2026-03-05 00:00:00'
    points=6
    number_of_maps=2
    ```

### Keep the features that meet a condition

The expression `speed > 22` keeps the points with a speed above 22: none of
the first map, the point with 23 of the second, and all points of the third
and fourth map. The new maps are named `fast`, an underscore and the day of
the map (the granularity of `gauges` is one day). **nprocs** lets two
*v.extract* processes run at the same time.

The first map comes out empty. It is not registered in `fast`, and the second
block shows that it is removed: the mapset has three maps `fast_...`. The third
block shows that the new map keeps the table rows of the features: the point
with the speed 23 has the category 3. The fourth block runs the same call with
the flag **-n**. The dataset `fast_all` registers the empty map as well, with 0
points, and the mapset keeps all four maps.

=== "Command line"

    ```sh
    t.vect.extract input=gauges output=fast basename=fast \
        expression="speed > 22" nprocs=2
    t.vect.list input=fast columns=name,start_time,points
    ```

    ```text
    name|start_time|points
    fast_2026_03_02|2026-03-02 00:00:00|1
    fast_2026_03_03|2026-03-03 00:00:00|3
    fast_2026_03_04|2026-03-04 00:00:00|3
    ```

    ```sh
    g.list type=vector pattern="fast*"
    ```

    ```text
    fast_2026_03_02
    fast_2026_03_03
    fast_2026_03_04
    ```

    ```sh
    v.db.select map=fast_2026_03_02
    ```

    ```text
    cat|x|y|speed
    3|2|3|23
    ```

    ```sh
    t.vect.extract -n input=gauges output=fast_all basename=fast_all \
        expression="speed > 22"
    t.vect.list input=fast_all columns=name,start_time,points
    g.list type=vector pattern="fast_all*"
    ```

    ```text
    name|start_time|points
    fast_all_2026_03_01|2026-03-01 00:00:00|0
    fast_all_2026_03_02|2026-03-02 00:00:00|1
    fast_all_2026_03_03|2026-03-03 00:00:00|3
    fast_all_2026_03_04|2026-03-04 00:00:00|3
    fast_all_2026_03_01
    fast_all_2026_03_02
    fast_all_2026_03_03
    fast_all_2026_03_04
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_vect_extract(
        input="gauges",
        output="fast",
        basename="fast",
        expression="speed > 22",
        nprocs=2,
    )
    print(tools.t_vect_list(input="fast", columns="name,start_time,points").text)
    ```

    ```text
    name|start_time|points
    fast_2026_03_02|2026-03-02 00:00:00|1
    fast_2026_03_03|2026-03-03 00:00:00|3
    fast_2026_03_04|2026-03-04 00:00:00|3
    ```

    ```python
    print(tools.g_list(type="vector", pattern="fast*").text)
    ```

    ```text
    fast_2026_03_02
    fast_2026_03_03
    fast_2026_03_04
    ```

    ```python
    print(tools.v_db_select(map="fast_2026_03_02").text)
    ```

    ```text
    cat|x|y|speed
    3|2|3|23
    ```

    ```python
    tools.t_vect_extract(
        input="gauges",
        output="fast_all",
        basename="fast_all",
        expression="speed > 22",
        flags="n",
    )
    columns = "name,start_time,points"
    print(tools.t_vect_list(input="fast_all", columns=columns).text)
    print(tools.g_list(type="vector", pattern="fast_all*").text)
    ```

    ```text
    name|start_time|points
    fast_all_2026_03_01|2026-03-01 00:00:00|0
    fast_all_2026_03_02|2026-03-02 00:00:00|1
    fast_all_2026_03_03|2026-03-03 00:00:00|3
    fast_all_2026_03_04|2026-03-04 00:00:00|3
    fast_all_2026_03_01
    fast_all_2026_03_02
    fast_all_2026_03_03
    fast_all_2026_03_04
    ```

### Choose the feature types

The dataset `tracks` has two maps for 1 and 2 March 2026. Each holds one point
and one line, both with a category in layer 1 and a row in the table. The
condition `cat > 0` is met by every feature, so only **type** decides what is
copied. `type=point` keeps the point of every map, `type=line` the line, and
without **type** both are copied. The columns `points` and `lines` of
*t.vect.list* count the features of each new map.

=== "Command line"

    ```sh
    for k in 1 2; do
        v.edit map=track_$k tool=create
        v.edit map=track_$k tool=add input=- <<EOF
    VERTI:
    P 1 1
     $k 1
     1 1
    L 2 1
     $k 2
     $k 3
     1 2
    EOF
        v.db.addtable map=track_$k
    done
    t.create type=stvds output=tracks title="Tracks" \
        description="One point and one line per day"
    t.register -i type=vector input=tracks maps=track_1,track_2 \
        start=2026-03-01 increment="1 day"
    t.vect.extract input=tracks output=track_points basename=tp \
        expression="cat > 0" type=point
    t.vect.list input=track_points columns=name,points,lines
    ```

    ```text
    name|points|lines
    tp_2026_03_01|1|0
    tp_2026_03_02|1|0
    ```

    ```sh
    t.vect.extract input=tracks output=track_lines basename=tl \
        expression="cat > 0" type=line
    t.vect.list input=track_lines columns=name,points,lines
    ```

    ```text
    name|points|lines
    tl_2026_03_01|0|1
    tl_2026_03_02|0|1
    ```

    ```sh
    t.vect.extract input=tracks output=track_both basename=tb \
        expression="cat > 0"
    t.vect.list input=track_both columns=name,points,lines
    ```

    ```text
    name|points|lines
    tb_2026_03_01|1|1
    tb_2026_03_02|1|1
    ```

=== "Python (grass.tools)"

    ```python
    features = "VERTI:\nP 1 1\n {k} 1\n 1 1\nL 2 1\n {k} 2\n {k} 3\n 1 2\n"
    for k in (1, 2):
        tools.v_edit(map=f"track_{k}", tool="create")
        tools.v_edit(map=f"track_{k}", tool="add", input=StringIO(features.format(k=k)))
        tools.v_db_addtable(map=f"track_{k}")
    tools.t_create(
        type="stvds",
        output="tracks",
        title="Tracks",
        description="One point and one line per day",
    )
    tools.t_register(
        type="vector",
        input="tracks",
        maps="track_1,track_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_vect_extract(
        input="tracks",
        output="track_points",
        basename="tp",
        expression="cat > 0",
        type="point",
    )
    columns = "name,points,lines"
    print(tools.t_vect_list(input="track_points", columns=columns).text)
    ```

    ```text
    name|points|lines
    tp_2026_03_01|1|0
    tp_2026_03_02|1|0
    ```

    ```python
    tools.t_vect_extract(
        input="tracks",
        output="track_lines",
        basename="tl",
        expression="cat > 0",
        type="line",
    )
    print(tools.t_vect_list(input="track_lines", columns=columns).text)
    ```

    ```text
    name|points|lines
    tl_2026_03_01|0|1
    tl_2026_03_02|0|1
    ```

    ```python
    tools.t_vect_extract(
        input="tracks", output="track_both", basename="tb", expression="cat > 0"
    )
    print(tools.t_vect_list(input="track_both", columns=columns).text)
    ```

    ```text
    name|points|lines
    tb_2026_03_01|1|1
    tb_2026_03_02|1|1
    ```

### Choose the layer

The dataset `plots` has two maps for 1 and 2 March 2026. Each has two points
with the categories 1 and 2 in layer 1 and in layer 2. The table of layer 1 has
the column `count` with the values 1 and 2, the table of layer 2 the values 101
and 102. The maps are registered without a layer.

The first block runs the condition `count > 100` with the default layer 1,
which finds nothing; the flag **-n** keeps the empty maps, so that the result
can be listed. The second block sets **layer** to 2: each new map has the two
points whose count is above 100.

The third block registers the two layers of `plots_1` as `plots_1:1` and
`plots_1:2` in the dataset `both`, both for 1 March. Each registered map reads
the layer it is registered with, so the condition `count > 0` is met by the
points of both layers. The two new maps would get the same name from the time;
the layer is appended to tell them apart. The mapset has the two maps
`bx_2026_03_01_1` and `bx_2026_03_01_2`.

=== "Command line"

    ```sh
    for k in 1 2; do
        v.edit map=plots_$k tool=create
        v.edit map=plots_$k tool=add input=- <<EOF
    VERTI:
    P 1 2
     $k 1
     1 1
     2 1
    P 1 2
     $k 2
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
    t.vect.extract -n input=plots output=plots_l1 basename=l1 \
        expression="count > 100"
    t.vect.list input=plots_l1 columns=name,points
    ```

    ```text
    name|points
    l1_2026_03_01|0
    l1_2026_03_02|0
    ```

    ```sh
    t.vect.extract input=plots output=plots_l2 basename=l2 \
        expression="count > 100" layer=2
    t.vect.list input=plots_l2 columns=name,points
    ```

    ```text
    name|points
    l2_2026_03_01|2
    l2_2026_03_02|2
    ```

    ```sh
    t.create type=stvds output=both title="Both layers" \
        description="Two layers of one map"
    t.register type=vector input=both maps=plots_1:1,plots_1:2 \
        start=2026-03-01 end=2026-03-02
    t.vect.extract input=both output=both_x basename=bx expression="count > 0"
    t.vect.list input=both_x columns=name,layer,points
    ```

    ```text
    name|layer|points
    bx_2026_03_01_1|1|2
    bx_2026_03_01_2|2|2
    ```

=== "Python (grass.tools)"

    ```python
    features = "VERTI:\nP 1 2\n {k} 1\n 1 1\n 2 1\nP 1 2\n {k} 2\n 1 2\n 2 2\n"
    for k in (1, 2):
        tools.v_edit(map=f"plots_{k}", tool="create")
        tools.v_edit(map=f"plots_{k}", tool="add", input=StringIO(features.format(k=k)))
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
    tools.t_vect_extract(
        input="plots",
        output="plots_l1",
        basename="l1",
        expression="count > 100",
        flags="n",
    )
    print(tools.t_vect_list(input="plots_l1", columns="name,points").text)
    ```

    ```text
    name|points
    l1_2026_03_01|0
    l1_2026_03_02|0
    ```

    ```python
    tools.t_vect_extract(
        input="plots",
        output="plots_l2",
        basename="l2",
        expression="count > 100",
        layer=2,
    )
    print(tools.t_vect_list(input="plots_l2", columns="name,points").text)
    ```

    ```text
    name|points
    l2_2026_03_01|2
    l2_2026_03_02|2
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
    tools.t_vect_extract(
        input="both", output="both_x", basename="bx", expression="count > 0"
    )
    print(tools.t_vect_list(input="both_x", columns="name,layer,points").text)
    ```

    ```text
    name|layer|points
    bx_2026_03_01_1|1|2
    bx_2026_03_01_2|2|2
    ```

### Name the new maps

The option **suffix** chooses the end of the names. Each of the first three
blocks extracts the four maps of `gauges` with the condition `speed > 0` and
lists the names: `time` gives the full start time, `num` a number of five
digits and `num%03` a number of three digits.

The dataset `pair` in the fourth block has two maps of the same day, `pair_a`
with one point and `pair_b` with two points. Their names from the default
suffix would be the same. The first map in the order of start time and map id,
`pair_a`, keeps `ten_2026_06_01`; the second one becomes `ten_2026_06_01_2`.
Maps of one time have no fixed order in a listing, so the two listings pick
the map by its number of points; the flag **-u** of *t.vect.list* leaves out
the column names of the second.

=== "Command line"

    ```sh
    t.vect.extract input=gauges output=by_time basename=by_time \
        expression="speed > 0" suffix=time
    t.vect.list input=by_time columns=name
    ```

    ```text
    name
    by_time_2026_03_01T00_00_00
    by_time_2026_03_02T00_00_00
    by_time_2026_03_03T00_00_00
    by_time_2026_03_04T00_00_00
    ```

    ```sh
    t.vect.extract input=gauges output=by_number basename=by_number \
        expression="speed > 0" suffix=num
    t.vect.list input=by_number columns=name
    ```

    ```text
    name
    by_number_00001
    by_number_00002
    by_number_00003
    by_number_00004
    ```

    ```sh
    t.vect.extract input=gauges output=by_width basename=by_width \
        expression="speed > 0" suffix=num%03
    t.vect.list input=by_width columns=name
    ```

    ```text
    name
    by_width_001
    by_width_002
    by_width_003
    by_width_004
    ```

    ```sh
    v.in.ascii input=- output=pair_a separator=comma \
        columns="x double precision, y double precision, speed double precision" <<EOF
    1,1,1
    EOF
    v.in.ascii input=- output=pair_b separator=comma \
        columns="x double precision, y double precision, speed double precision" <<EOF
    2,1,2
    2,2,3
    EOF
    t.create type=stvds output=pair title="Two maps of one day" \
        description="Two maps with the same time"
    t.register type=vector input=pair maps=pair_a,pair_b \
        start=2026-06-01 end=2026-06-02
    t.vect.extract input=pair output=pair_ten basename=ten \
        expression="speed > 0"
    t.vect.list input=pair_ten columns=name,start_time,points \
        where="points = 1"
    t.vect.list -u input=pair_ten columns=name,start_time,points \
        where="points = 2"
    ```

    ```text
    name|start_time|points
    ten_2026_06_01|2026-06-01 00:00:00|1
    ten_2026_06_01_2|2026-06-01 00:00:00|2
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_vect_extract(
        input="gauges",
        output="by_time",
        basename="by_time",
        expression="speed > 0",
        suffix="time",
    )
    print(tools.t_vect_list(input="by_time", columns="name").text)
    ```

    ```text
    name
    by_time_2026_03_01T00_00_00
    by_time_2026_03_02T00_00_00
    by_time_2026_03_03T00_00_00
    by_time_2026_03_04T00_00_00
    ```

    ```python
    tools.t_vect_extract(
        input="gauges",
        output="by_number",
        basename="by_number",
        expression="speed > 0",
        suffix="num",
    )
    print(tools.t_vect_list(input="by_number", columns="name").text)
    ```

    ```text
    name
    by_number_00001
    by_number_00002
    by_number_00003
    by_number_00004
    ```

    ```python
    tools.t_vect_extract(
        input="gauges",
        output="by_width",
        basename="by_width",
        expression="speed > 0",
        suffix="num%03",
    )
    print(tools.t_vect_list(input="by_width", columns="name").text)
    ```

    ```text
    name
    by_width_001
    by_width_002
    by_width_003
    by_width_004
    ```

    ```python
    columns = "x double precision, y double precision, speed double precision"
    tools.v_in_ascii(
        input=StringIO("1,1,1\n"), output="pair_a", separator="comma", columns=columns
    )
    tools.v_in_ascii(
        input=StringIO("2,1,2\n2,2,3\n"),
        output="pair_b",
        separator="comma",
        columns=columns,
    )
    tools.t_create(
        type="stvds",
        output="pair",
        title="Two maps of one day",
        description="Two maps with the same time",
    )
    tools.t_register(
        type="vector",
        input="pair",
        maps="pair_a,pair_b",
        start="2026-06-01",
        end="2026-06-02",
    )
    tools.t_vect_extract(
        input="pair", output="pair_ten", basename="ten", expression="speed > 0"
    )
    columns = "name,start_time,points"
    first = tools.t_vect_list(input="pair_ten", columns=columns, where="points = 1")
    print(first.text)
    second = tools.t_vect_list(
        input="pair_ten", columns=columns, where="points = 2", flags="u"
    )
    print(second.text)
    ```

    ```text
    name|start_time|points
    ten_2026_06_01|2026-06-01 00:00:00|1
    ten_2026_06_01_2|2026-06-01 00:00:00|2
    ```

### Extract from a dataset with relative time

The dataset `model` has two maps of six hours each, from 0 to 6 and from 6 to
12 hours. Map `run_1` has two points with the levels 1 and 3, map `run_2` the
levels 2 and 4. In a dataset with relative time a start time is a number, so
the names of the new maps carry the number of the map instead of a date. The
first block keeps the levels above 3. The number counts all selected maps, also
the empty one: the first map has no such point and is left out, so the remaining
map is `m_00002`. The new dataset has the times and the unit of the input. The
second block takes `time` as the suffix; with relative time it gives the number
as well.

=== "Command line"

    ```sh
    v.in.ascii input=- output=run_1 separator=comma \
        columns="x double precision, y double precision, level double precision" <<EOF
    1,1,1
    1,2,3
    EOF
    v.in.ascii input=- output=run_2 separator=comma \
        columns="x double precision, y double precision, level double precision" <<EOF
    2,1,2
    2,2,4
    EOF
    t.create type=stvds output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i type=vector input=model maps=run_1,run_2 start=0 \
        increment=6 unit=hours
    t.vect.extract input=model output=model_high basename=m \
        expression="level > 3"
    t.vect.list input=model_high columns=name,start_time,end_time,points
    t.info -g type=stvds input=model_high | grep -E "^(temporal_type|unit)="
    ```

    ```text
    name|start_time|end_time|points
    m_00002|6|12|1
    temporal_type=relative
    unit=hours
    ```

    ```sh
    t.vect.extract input=model output=model_time basename=t \
        expression="level > 0" suffix=time
    t.vect.list input=model_time columns=name
    ```

    ```text
    name
    t_00001
    t_00002
    ```

=== "Python (grass.tools)"

    ```python
    columns = "x double precision, y double precision, level double precision"
    tools.v_in_ascii(
        input=StringIO("1,1,1\n1,2,3\n"),
        output="run_1",
        separator="comma",
        columns=columns,
    )
    tools.v_in_ascii(
        input=StringIO("2,1,2\n2,2,4\n"),
        output="run_2",
        separator="comma",
        columns=columns,
    )
    tools.t_create(
        type="stvds",
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        type="vector",
        input="model",
        maps="run_1,run_2",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    tools.t_vect_extract(
        input="model", output="model_high", basename="m", expression="level > 3"
    )
    columns = "name,start_time,end_time,points"
    print(tools.t_vect_list(input="model_high", columns=columns).text)
    info = tools.t_info(type="stvds", input="model_high", flags="g").keyval
    for key in ("temporal_type", "unit"):
        print(f"{key}={info[key]}")
    ```

    ```text
    name|start_time|end_time|points
    m_00002|6|12|1
    temporal_type=relative
    unit=hours
    ```

    ```python
    tools.t_vect_extract(
        input="model",
        output="model_time",
        basename="t",
        expression="level > 0",
        suffix="time",
    )
    print(tools.t_vect_list(input="model_time", columns="name").text)
    ```

    ```text
    name
    t_00001
    t_00002
    ```

### Extract from a dataset of another mapset

The dataset `model` stays in the mapset `PERMANENT`. The first block creates
the mapset `other`, switches to it and extracts with an expression. The new
dataset `model_copy` and its maps `copy_00001` and `copy_00002` belong to
`other`. The `id` column shows the mapset.

The second block shows what happens without an expression. The call is
refused, so the block prints `refused`. The refusal leaves the empty dataset
`model_copy_empty` behind. `number_of_maps=None` shows that it has no maps, and
*t.remove* removes it.

=== "Command line"

    ```sh
    g.mapset -c mapset=other
    t.vect.extract input=model@PERMANENT output=model_copy basename=copy \
        expression="level > 0" suffix=num
    t.vect.list input=model_copy columns=id,start_time,points
    ```

    ```text
    id|start_time|points
    copy_00001@other|0|2
    copy_00002@other|6|2
    ```

    ```sh
    if t.vect.extract input=model@PERMANENT output=model_copy_empty \
        2>/dev/null; then echo extracted; else echo refused; fi
    t.info -g type=stvds input=model_copy_empty | grep -E "^(id|number_of_maps)="
    t.remove -f type=stvds inputs=model_copy_empty
    ```

    ```text
    refused
    id=model_copy_empty@other
    number_of_maps=None
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    tools.g_mapset(mapset="other", flags="c")
    tools.t_vect_extract(
        input="model@PERMANENT",
        output="model_copy",
        basename="copy",
        expression="level > 0",
        suffix="num",
    )
    print(tools.t_vect_list(input="model_copy", columns="id,start_time,points").text)
    ```

    ```text
    id|start_time|points
    copy_00001@other|0|2
    copy_00002@other|6|2
    ```

    ```python
    try:
        tools.t_vect_extract(input="model@PERMANENT", output="model_copy_empty")
    except ToolError:
        print("refused")
    else:
        print("extracted")
    info = tools.t_info(type="stvds", input="model_copy_empty", flags="g").keyval
    for key in ("id", "number_of_maps"):
        print(f"{key}={info[key]}")
    tools.t_remove(type="stvds", inputs="model_copy_empty", flags="f")
    ```

    ```text
    refused
    id=model_copy_empty@other
    number_of_maps=None
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapset](g.mapset.md), [t.create](t.create.md),
[t.info](t.info.md), [t.rast.extract](t.rast.extract.md),
[t.register](t.register.md), [t.remove](t.remove.md),
[t.vect.list](t.vect.list.md), [v.extract](v.extract.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
