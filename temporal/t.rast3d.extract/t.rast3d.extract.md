## DESCRIPTION

*t.rast3d.extract* selects maps of a space time 3D raster dataset and
registers them in a new space time 3D raster dataset. On the way, it can
compute a new 3D raster map from each selected map with an
*[r3.mapcalc](r3.mapcalc.md)* expression. Use it to cut a time window out of a
dataset, to drop the maps whose values do not matter, or to derive a dataset by
map algebra when the same expression applies to every map. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. *[t.rast3d.mapcalc](t.rast3d.mapcalc.md)* computes from more than one
dataset, and *[t.rast3d.list](t.rast3d.list.md)* lists the maps of the result.
The tool works like *[t.rast.extract](t.rast.extract.md)*, on space time 3D
raster datasets (STR3DS) and 3D raster maps instead of space time raster
datasets and raster maps.

The option **input** names the space time 3D raster dataset, the option
**output** the new one. The new dataset takes the temporal type and the
semantic type of the input dataset. The output always belongs to the current
mapset. An existing output dataset is refused unless the flag **--overwrite**
is given; then it is replaced.

### Select the maps

The option **where** takes an SQL condition on the columns of the registered
maps, such as `start_time >= '2026-03-03'`, which selects the maps that start
on 3 March or later. Without **where**, all maps are selected.

### Register or compute

Without **expression**, *t.rast3d.extract* creates no map. It registers the
selected maps themselves in the new dataset, so a map is then part of two
datasets and the data are not duplicated.

With **expression**, the tool runs *r3.mapcalc* once for each selected map and
registers the new maps, with the start and end time of the map they come from,
in the new dataset. The expression is the right side of an *r3.mapcalc*
expression, without the `map =` of a full one. The name of the input dataset
stands for the selected map of each step, so `2 * soil` doubles the map of every
step of the dataset `soil`. Any other 3D raster map can be used in the
expression by name. The new maps belong to the current mapset. The expression
needs the option **basename**.

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

Two different maps of one time, such as two maps of January 2001, get the same
name from the suffix. The first of them, in the order of start time and map id,
keeps the name; the second and every further map get the number `_2`, `_3` and
so on after it. A number that another new map has as its name is skipped.

A new map that has no valid cell, that is, no minimum and no maximum, is
empty. By default it is not registered in the new dataset and the map is
removed after the run. The flag **-n** registers the empty maps and keeps
them. An expression such as `if(soil > 6, soil, null())` therefore selects
maps by their values as well.

The option **nprocs** sets the number of *r3.mapcalc* processes that run at the
same time. The default is `1`. The result does not depend on it.

## NOTES

If **where** selects no map, or the input dataset has none, *t.rast3d.extract*
warns "Nothing found in the database for space time dataset" and makes no
output dataset; for a **where** that selects nothing, the message adds that
"Dataset is empty or where clause is too constrained or incorrect". A condition
with a syntax error stops with the error "Invalid where condition".

The tool stops with an error if **expression** is given without **basename**
("You need to specify the base name of new created maps"), if the input dataset
does not exist, if the output dataset exists and **--overwrite** is not given,
and if **suffix** is not `gran`, `time`, `num` or `num%NN` ("Invalid
suffix"). A dot in the name of the output dataset is refused: "a dot is not
allowed". An **expression** that *r3.mapcalc* does not accept stops with
"Error in computation process". If a new map is already in the temporal
database and **--overwrite** is not given, the tool stops before it computes
anything, with "Map ... is already in temporal database, use overwrite flag to
overwrite", and makes no dataset.

The last example shows that a dataset of another mapset works as input when an
**expression** is given. Without an **expression**, such a dataset is refused,
and the empty output dataset that the refusal leaves behind has to be removed
with *[t.remove](t.remove.md)*. Add an **expression** such as the name of the
input dataset to copy the maps instead.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Select maps by time

The dataset `soil` has four 3D raster maps of daily mean soil temperature for
the days from 1 to 4 March 2026. The region has two rows, two columns and three
layers. The values of a map are the layer number plus the offset 0, 6, 3 and 9,
so the smallest and largest values of the maps are 1 to 3, 7 to 9, 4 to 6 and
10 to 12.

The first block extracts the maps from 3 March on into the dataset `later`.
There is no **expression**, so no map is made: the second block lists the 3D
raster maps of the mapset, and they are still the four maps of `soil`. The
dataset `later` lists two of them. The third block shows what the new dataset
takes from the input: the temporal type and the semantic type, and the start
and end time that follow from the maps it holds.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=2 w=0 t=3 b=0 res=1 res3=1 tbres=1
    r3.mapcalc expression="soil_1 = depth()"
    r3.mapcalc expression="soil_2 = depth() + 6"
    r3.mapcalc expression="soil_3 = depth() + 3"
    r3.mapcalc expression="soil_4 = depth() + 9"
    t.create type=str3ds output=soil title="Soil temperature" \
        description="Daily mean soil temperature"
    t.register -i type=raster_3d input=soil \
        maps=soil_1,soil_2,soil_3,soil_4 start=2026-03-01 increment="1 day"
    t.rast3d.extract input=soil output=later \
        where="start_time >= '2026-03-03'"
    t.rast3d.list input=later
    ```

    ```text
    name|mapset|start_time|end_time
    soil_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    soil_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```sh
    g.list type=raster_3d
    ```

    ```text
    soil_1
    soil_2
    soil_3
    soil_4
    ```

    ```sh
    t.info -g type=str3ds input=later | grep -E "^(temporal_type|semantic_type|start_time|end_time)="
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    start_time='2026-03-03 00:00:00'
    end_time='2026-03-05 00:00:00'
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=2, w=0, t=3, b=0, res=1, res3=1, tbres=1)
    for number, offset in enumerate((0, 6, 3, 9), start=1):
        tools.r3_mapcalc(expression=f"soil_{number} = depth() + {offset}")
    tools.t_create(
        type="str3ds",
        output="soil",
        title="Soil temperature",
        description="Daily mean soil temperature",
    )
    tools.t_register(
        type="raster_3d",
        input="soil",
        maps="soil_1,soil_2,soil_3,soil_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast3d_extract(input="soil", output="later", where="start_time >= '2026-03-03'")
    print(tools.t_rast3d_list(input="later").text)
    ```

    ```text
    name|mapset|start_time|end_time
    soil_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    soil_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```python
    print(tools.g_list(type="raster_3d").text)
    ```

    ```text
    soil_1
    soil_2
    soil_3
    soil_4
    ```

    ```python
    info = tools.t_info(type="str3ds", input="later", flags="g").keyval
    for key in ("temporal_type", "semantic_type", "start_time", "end_time"):
        print(f"{key}={info[key]}")
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    start_time='2026-03-03 00:00:00'
    end_time='2026-03-05 00:00:00'
    ```

### Compute new maps from the selected maps

The first block doubles the maps of `soil`. The expression `2 * soil` names the
dataset, which stands for the map of each step. The new maps are named
`doubled`, an underscore and the day of the map (the granularity of `soil` is
one day), and each has the time of its source map. **nprocs** lets two
*r3.mapcalc* processes run at the same time; the result is the same as with one
process. The values are twice those of the source maps: 2 to 6 for the first
day, 14 to 18 for the second.

The second block shows that the expression may use any 3D raster map. The map
`bias` is 10 everywhere; **where** selects the first two days, and the new maps
hold the values of their source maps plus 10.

=== "Command line"

    ```sh
    t.rast3d.extract input=soil output=doubled basename=doubled \
        expression="2 * soil" nprocs=2
    t.rast3d.list input=doubled columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    doubled_2026_03_01|2026-03-01 00:00:00|2.0|6.0
    doubled_2026_03_02|2026-03-02 00:00:00|14.0|18.0
    doubled_2026_03_03|2026-03-03 00:00:00|8.0|12.0
    doubled_2026_03_04|2026-03-04 00:00:00|20.0|24.0
    ```

    ```sh
    r3.mapcalc expression="bias = 10"
    t.rast3d.extract input=soil output=biased basename=biased \
        where="start_time < '2026-03-03'" expression="soil + bias"
    t.rast3d.list input=biased columns=name,min,max
    ```

    ```text
    name|min|max
    biased_2026_03_01|11.0|13.0
    biased_2026_03_02|17.0|19.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast3d_extract(
        input="soil",
        output="doubled",
        basename="doubled",
        expression="2 * soil",
        nprocs=2,
    )
    print(tools.t_rast3d_list(input="doubled", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    doubled_2026_03_01|2026-03-01 00:00:00|2.0|6.0
    doubled_2026_03_02|2026-03-02 00:00:00|14.0|18.0
    doubled_2026_03_03|2026-03-03 00:00:00|8.0|12.0
    doubled_2026_03_04|2026-03-04 00:00:00|20.0|24.0
    ```

    ```python
    tools.r3_mapcalc(expression="bias = 10")
    tools.t_rast3d_extract(
        input="soil",
        output="biased",
        basename="biased",
        where="start_time < '2026-03-03'",
        expression="soil + bias",
    )
    print(tools.t_rast3d_list(input="biased", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    biased_2026_03_01|11.0|13.0
    biased_2026_03_02|17.0|19.0
    ```

### Select maps by their values

An expression that sets cells to null selects maps. The first block takes the
maps from 2 March on, three maps, and keeps the values above 6. Of the three,
only the maps with values from 7 to 9 and from 10 to 12 keep cells; the map
with the values 4 to 6 has none left, so it is empty. The empty map is not
registered in `warm`, and the second block shows that it is removed: only two
maps are left in the mapset.

The third block runs the same call with the flag **-n**. The dataset `warm_all`
registers the empty map as well, with `None` as its smallest and largest value,
and the mapset keeps all three maps.

=== "Command line"

    ```sh
    t.rast3d.extract input=soil output=warm basename=warm \
        where="start_time >= '2026-03-02'" \
        expression="if(soil > 6, soil, null())"
    t.rast3d.list input=warm columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    warm_2026_03_02|2026-03-02 00:00:00|7.0|9.0
    warm_2026_03_04|2026-03-04 00:00:00|10.0|12.0
    ```

    ```sh
    g.list type=raster_3d pattern="warm*"
    ```

    ```text
    warm_2026_03_02
    warm_2026_03_04
    ```

    ```sh
    t.rast3d.extract -n input=soil output=warm_all basename=warm_all \
        where="start_time >= '2026-03-02'" \
        expression="if(soil > 6, soil, null())"
    t.rast3d.list input=warm_all columns=name,start_time,min,max
    g.list type=raster_3d pattern="warm_all*"
    ```

    ```text
    name|start_time|min|max
    warm_all_2026_03_02|2026-03-02 00:00:00|7.0|9.0
    warm_all_2026_03_03|2026-03-03 00:00:00|None|None
    warm_all_2026_03_04|2026-03-04 00:00:00|10.0|12.0
    warm_all_2026_03_02
    warm_all_2026_03_03
    warm_all_2026_03_04
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast3d_extract(
        input="soil",
        output="warm",
        basename="warm",
        where="start_time >= '2026-03-02'",
        expression="if(soil > 6, soil, null())",
    )
    print(tools.t_rast3d_list(input="warm", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    warm_2026_03_02|2026-03-02 00:00:00|7.0|9.0
    warm_2026_03_04|2026-03-04 00:00:00|10.0|12.0
    ```

    ```python
    print(tools.g_list(type="raster_3d", pattern="warm*").text)
    ```

    ```text
    warm_2026_03_02
    warm_2026_03_04
    ```

    ```python
    tools.t_rast3d_extract(
        input="soil",
        output="warm_all",
        basename="warm_all",
        where="start_time >= '2026-03-02'",
        expression="if(soil > 6, soil, null())",
        flags="n",
    )
    columns = "name,start_time,min,max"
    print(tools.t_rast3d_list(input="warm_all", columns=columns).text)
    print(tools.g_list(type="raster_3d", pattern="warm_all*").text)
    ```

    ```text
    name|start_time|min|max
    warm_all_2026_03_02|2026-03-02 00:00:00|7.0|9.0
    warm_all_2026_03_03|2026-03-03 00:00:00|None|None
    warm_all_2026_03_04|2026-03-04 00:00:00|10.0|12.0
    warm_all_2026_03_02
    warm_all_2026_03_03
    warm_all_2026_03_04
    ```

### Name the new maps

The option **suffix** chooses the end of the names. Each of the first three
blocks copies the four maps of `soil` with the expression `soil` and lists the
names: `time` gives the full start time, `num` a number of five digits and
`num%03` a number of three digits.

The dataset `pair` in the fourth block has two maps of the same day, `pair_a`
with the value 1 and `pair_b` with the value 2. Their names from the default
suffix would be the same. The first map in the order of start time and map id,
`pair_a`, keeps `ten_2026_06_01`; the second one becomes `ten_2026_06_01_2`.
The values are 10 and 20.

=== "Command line"

    ```sh
    t.rast3d.extract input=soil output=by_time basename=by_time \
        expression="soil" suffix=time
    t.rast3d.list input=by_time columns=name
    ```

    ```text
    name
    by_time_2026_03_01T00_00_00
    by_time_2026_03_02T00_00_00
    by_time_2026_03_03T00_00_00
    by_time_2026_03_04T00_00_00
    ```

    ```sh
    t.rast3d.extract input=soil output=by_number basename=by_number \
        expression="soil" suffix=num
    t.rast3d.list input=by_number columns=name
    ```

    ```text
    name
    by_number_00001
    by_number_00002
    by_number_00003
    by_number_00004
    ```

    ```sh
    t.rast3d.extract input=soil output=by_width basename=by_width \
        expression="soil" suffix=num%03
    t.rast3d.list input=by_width columns=name
    ```

    ```text
    name
    by_width_001
    by_width_002
    by_width_003
    by_width_004
    ```

    ```sh
    r3.mapcalc expression="pair_a = 1"
    r3.mapcalc expression="pair_b = 2"
    t.create type=str3ds output=pair title="Two maps of one day" \
        description="Two maps with the same time"
    t.register type=raster_3d input=pair maps=pair_a,pair_b \
        start=2026-06-01 end=2026-06-02
    t.rast3d.extract input=pair output=pair_ten basename=ten \
        expression="pair * 10"
    t.rast3d.list input=pair_ten columns=name,start_time,min order=name
    ```

    ```text
    name|start_time|min
    ten_2026_06_01|2026-06-01 00:00:00|10.0
    ten_2026_06_01_2|2026-06-01 00:00:00|20.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast3d_extract(
        input="soil",
        output="by_time",
        basename="by_time",
        expression="soil",
        suffix="time",
    )
    print(tools.t_rast3d_list(input="by_time", columns="name").text)
    ```

    ```text
    name
    by_time_2026_03_01T00_00_00
    by_time_2026_03_02T00_00_00
    by_time_2026_03_03T00_00_00
    by_time_2026_03_04T00_00_00
    ```

    ```python
    tools.t_rast3d_extract(
        input="soil",
        output="by_number",
        basename="by_number",
        expression="soil",
        suffix="num",
    )
    print(tools.t_rast3d_list(input="by_number", columns="name").text)
    ```

    ```text
    name
    by_number_00001
    by_number_00002
    by_number_00003
    by_number_00004
    ```

    ```python
    tools.t_rast3d_extract(
        input="soil",
        output="by_width",
        basename="by_width",
        expression="soil",
        suffix="num%03",
    )
    print(tools.t_rast3d_list(input="by_width", columns="name").text)
    ```

    ```text
    name
    by_width_001
    by_width_002
    by_width_003
    by_width_004
    ```

    ```python
    tools.r3_mapcalc(expression="pair_a = 1")
    tools.r3_mapcalc(expression="pair_b = 2")
    tools.t_create(
        type="str3ds",
        output="pair",
        title="Two maps of one day",
        description="Two maps with the same time",
    )
    tools.t_register(
        type="raster_3d",
        input="pair",
        maps="pair_a,pair_b",
        start="2026-06-01",
        end="2026-06-02",
    )
    tools.t_rast3d_extract(
        input="pair", output="pair_ten", basename="ten", expression="pair * 10"
    )
    result = tools.t_rast3d_list(
        input="pair_ten", columns="name,start_time,min", order="name"
    )
    print(result.text)
    ```

    ```text
    name|start_time|min
    ten_2026_06_01|2026-06-01 00:00:00|10.0
    ten_2026_06_01_2|2026-06-01 00:00:00|20.0
    ```

### Extract from a dataset with relative time

The dataset `model` has two maps of six hours each, from 0 to 6 and from 6 to
12 hours, with the values 1 and 2. In a dataset with relative time a start time
is a number, so the names of the new maps carry the number of the map instead of
a date. The first block keeps the values above 1. The number counts all selected
maps, also the empty one: the first map is empty and left out, so the remaining
map is `m_00002`. The new dataset has the times and the unit of the input. The
second block takes `time` as the suffix; with relative time it gives the number
as well.

=== "Command line"

    ```sh
    r3.mapcalc expression="step_1 = 1"
    r3.mapcalc expression="step_2 = 2"
    t.create type=str3ds output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i type=raster_3d input=model maps=step_1,step_2 start=0 \
        increment=6 unit=hours
    t.rast3d.extract input=model output=model_high basename=m \
        expression="if(model > 1, model, null())"
    t.rast3d.list input=model_high columns=name,start_time,end_time,min
    t.info -g type=str3ds input=model_high | grep -E "^(temporal_type|unit)="
    ```

    ```text
    name|start_time|end_time|min
    m_00002|6|12|2.0
    temporal_type=relative
    unit=hours
    ```

    ```sh
    t.rast3d.extract input=model output=model_time basename=t \
        expression="model" suffix=time
    t.rast3d.list input=model_time columns=name
    ```

    ```text
    name
    t_00001
    t_00002
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(expression="step_1 = 1")
    tools.r3_mapcalc(expression="step_2 = 2")
    tools.t_create(
        type="str3ds",
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        type="raster_3d",
        input="model",
        maps="step_1,step_2",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    tools.t_rast3d_extract(
        input="model",
        output="model_high",
        basename="m",
        expression="if(model > 1, model, null())",
    )
    columns = "name,start_time,end_time,min"
    print(tools.t_rast3d_list(input="model_high", columns=columns).text)
    info = tools.t_info(type="str3ds", input="model_high", flags="g").keyval
    for key in ("temporal_type", "unit"):
        print(f"{key}={info[key]}")
    ```

    ```text
    name|start_time|end_time|min
    m_00002|6|12|2.0
    temporal_type=relative
    unit=hours
    ```

    ```python
    tools.t_rast3d_extract(
        input="model",
        output="model_time",
        basename="t",
        expression="model",
        suffix="time",
    )
    print(tools.t_rast3d_list(input="model_time", columns="name").text)
    ```

    ```text
    name
    t_00001
    t_00002
    ```

### Extract from a dataset of another mapset

The dataset `model` stays in the mapset `PERMANENT`. The first block creates
the mapset `other`, switches to it and extracts with an expression. The name
`model` in the expression stands for the maps of the dataset, though it has no
mapset, and the output dataset `model_copy` and its maps `copy_00001` and
`copy_00002` belong to `other`. The `id` column shows the mapset.

The second block shows what happens without an expression. The call is
refused, so the block prints `refused`. The refusal leaves the empty dataset
`model_copy_empty` behind. `number_of_maps=None` shows that it has no maps, and
*t.remove* removes it.

=== "Command line"

    ```sh
    g.mapset -c mapset=other
    t.rast3d.extract input=model@PERMANENT output=model_copy basename=copy \
        expression="model" suffix=num
    t.rast3d.list input=model_copy columns=id,start_time,min
    ```

    ```text
    id|start_time|min
    copy_00001@other|0|1.0
    copy_00002@other|6|2.0
    ```

    ```sh
    if t.rast3d.extract input=model@PERMANENT output=model_copy_empty \
        2>/dev/null; then echo extracted; else echo refused; fi
    t.info -g type=str3ds input=model_copy_empty | grep -E "^(id|number_of_maps)="
    t.remove -f type=str3ds inputs=model_copy_empty
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
    tools.t_rast3d_extract(
        input="model@PERMANENT",
        output="model_copy",
        basename="copy",
        expression="model",
        suffix="num",
    )
    print(tools.t_rast3d_list(input="model_copy", columns="id,start_time,min").text)
    ```

    ```text
    id|start_time|min
    copy_00001@other|0|1.0
    copy_00002@other|6|2.0
    ```

    ```python
    try:
        tools.t_rast3d_extract(input="model@PERMANENT", output="model_copy_empty")
    except ToolError:
        print("refused")
    else:
        print("extracted")
    info = tools.t_info(type="str3ds", input="model_copy_empty", flags="g").keyval
    for key in ("id", "number_of_maps"):
        print(f"{key}={info[key]}")
    tools.t_remove(type="str3ds", inputs="model_copy_empty", flags="f")
    ```

    ```text
    refused
    id=model_copy_empty@other
    number_of_maps=None
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapset](g.mapset.md), [r3.mapcalc](r3.mapcalc.md),
[t.create](t.create.md), [t.info](t.info.md),
[t.rast.extract](t.rast.extract.md), [t.rast3d.list](t.rast3d.list.md),
[t.rast3d.mapcalc](t.rast3d.mapcalc.md), [t.register](t.register.md),
[t.remove](t.remove.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
