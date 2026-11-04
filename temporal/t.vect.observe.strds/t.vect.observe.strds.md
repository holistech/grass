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
the module warns, naming the granule and the dataset, and uses the first of
them. The datasets must have the same temporal type,
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
overwrite flag. With **--overwrite** it keeps the column, sets it to NULL in
every row of the output map first and then writes the sampled values, so a point
that is not sampled, outside the region or on a cell without a value, gets a
NULL as well. The input map keeps its values.
A name that differs from such a column only in upper and lower case (`Altitude`
for `altitude`) is refused, with and without **--overwrite**, before the output
map is made, with a message that names both spellings.

If a run fails with an error message, the module removes the vector map and the
space time vector dataset that it made, so nothing is left behind. With
**--overwrite** the previous output map and dataset of the same names have
already been replaced when the run fails, so they are gone as well and are not
restored. Without **--overwrite** an existing output is refused before anything
is made and stays as it was. To keep a result, give the new run another name.

If **where** selects no point, the module stops with the message `The where
option selects no point of vector map <name>`. It makes no output vector map and
no space time vector dataset. The second block of the example "Observe a
selection of the points" shows it.

If several datasets are given and no map of the first dataset has a map with
the same time in every other dataset, the module ends with the return code 0
and a warning that no granule has a map in each of the datasets. It writes
nothing: no space time vector dataset and no vector map are made, and an output
of the same names that exists stays as it is. The third block of the example
"Observe several raster datasets" shows it.

The names in **columns** must differ, whatever the case of the letters. A name
that is given twice stops the module with the message `The column names must be
different` before anything is written.

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

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_vect_observe_strds` and sets the computational
region to North Carolina with cells of 1 km; the later examples work in this
mapset and region. The raster series are generated, they are not measurements.
The points are the places of real climate stations of the dataset, rounded to
the meter, but the values at them come from a formula and say nothing about
the climate there. The datasets `shifted`, `twin` and `runoff` hold maps with
small constant values.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_vect_observe_strds -->

<!-- markdownlint-disable MD046 -->

### Observe a raster dataset at points

The dataset `temperature_monthly` holds the three maps of the monthly mean air
temperature from January to March 2020, in degrees Celsius rounded to tenths.
They are generated from the elevation model `elev_state_500m`: 16.5 degrees at
sea level and the northing 160 km, an annual cycle of plus and minus 10.5
degrees with its maximum in July, 6.5 degrees less for every 1000 m of
elevation, and 1 degree more for every 100 km to the south. Each map is an
interval of one month.

The input map `stations` has five points; the column `altitude` is their only
attribute besides the coordinates, and their categories are 1 to 5. The first
three lie at the climate stations 310090, 310184 and 310241, the fourth at the
station 311458 on the Outer Banks, whose cell has no value in the elevation
model, and the fifth west of the computational region. The altitudes are those
of the stations in meters, rounded, the altitude of the fifth point is chosen.

The run observes the dataset `temperature_monthly`, so the output has three
layers with one month each. The first block runs the module and shows the
temporal properties of the new dataset, which holds 15 points (five in each of
the three layers), and its maps. The layers have the column `temp` and, in
layer 1, the columns of `stations` in addition. The fourth and the fifth point
have no value. The second block shows the tables of the layers. The third block
shows how the layers are linked to their tables: layer 1 keeps the layer name
`stations` of the input and uses the table `obs_points`, the others have the
table `obs_points_<layer>`.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_observe_strds
    g.region raster=elev_state_500m res=1000 -a
    for month in $(seq 3); do
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
    v.in.ascii input=- output=stations separator=comma \
        columns="x double precision, y double precision, altitude double precision" <<EOF
    500657,183601,186
    169208,171737,533
    701031,282371,101
    917005,169684,3
    100000,170000,50
    EOF
    ```

    ```sh
    t.vect.observe.strds input=stations strds=temperature_monthly output=obs \
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
    obs_points|1|2020-01-01 00:00:00|2020-02-01 00:00:00
    obs_points|2|2020-02-01 00:00:00|2020-03-01 00:00:00
    obs_points|3|2020-03-01 00:00:00|2020-04-01 00:00:00
    ```

    ```sh
    for layer in 1 2 3; do
        v.db.select map=obs_points layer=$layer
    done
    ```

    ```text
    cat|x|y|altitude|temp
    1|500657|183601|186|4.7
    2|169208|171737|533|2.4
    3|701031|282371|101|4.2
    4|917005|169684|3|
    5|100000|170000|50|
    cat|temp
    1|5.6
    2|3.2
    3|5.1
    4|
    5|
    cat|temp
    1|9
    2|6.7
    3|8.5
    4|
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
    tools.g_mapset(flags="c", mapset="t_vect_observe_strds")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    months = range(1, 4)
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
    tools.v_in_ascii(
        input=StringIO(
            "500657,183601,186\n169208,171737,533\n701031,282371,101\n"
            "917005,169684,3\n100000,170000,50\n"
        ),
        output="stations",
        separator="comma",
        columns="x double precision, y double precision, altitude double precision",
    )
    ```

    ```python
    tools.t_vect_observe_strds(
        input="stations",
        strds="temperature_monthly",
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
    obs_points|1|2020-01-01 00:00:00|2020-02-01 00:00:00
    obs_points|2|2020-02-01 00:00:00|2020-03-01 00:00:00
    obs_points|3|2020-03-01 00:00:00|2020-04-01 00:00:00
    ```

    ```python
    for layer in (1, 2, 3):
        print(tools.v_db_select(map="obs_points", layer=layer).text)
    ```

    ```text
    cat|x|y|altitude|temp
    1|500657|183601|186|4.7
    2|169208|171737|533|2.4
    3|701031|282371|101|4.2
    4|917005|169684|3|
    5|100000|170000|50|
    cat|temp
    1|5.6
    2|3.2
    3|5.1
    4|
    5|
    cat|temp
    1|9
    2|6.7
    3|8.5
    4|
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

The second input is the dataset `precipitation_monthly` with the maps of
February and March 2020, in whole millimeters. They are generated too: the
monthly normal of the climate stations (the columns `feb` and `mar` of
`precip_30ynormals`) is interpolated with *[v.surf.idw](v.surf.idw.md)* and
multiplied by an assumed factor for a wet year, 1.7 for February and 0.9 for
March. The run needs one column for each dataset, so `columns=temp,precip`
gives the values of `temperature_monthly` to `temp` and those of
`precipitation_monthly` to `precip`. The granules are the maps of
`temperature_monthly` for which `precipitation_monthly` has a map with the same
time: January has no precipitation, so it is left out and the output has two
layers, February and March. The fourth and the fifth point read NULL in both
columns: the cell of the fourth point has no value in either series, and the
fifth point lies outside the region. The second block shows the column types:
`temp` follows the floating point maps of `temperature_monthly`, `precip` the
integer maps of `precipitation_monthly`.

The third block adds the dataset `shifted` with one map from noon of 15
January to noon of 15 February 2020. No map of `shifted` has the time of a map
of `temperature_monthly`, so no granule is left: the module warns and writes
nothing, neither the dataset `none` nor the vector map `none_points`. The
fourth block adds the dataset `twin` with the two maps `twin_a` (the value 1)
and `twin_b` (the value 2) for January. The module warns that `twin` has two
maps for the granule and uses the first one, `twin_a`. The column `two` gets
its value 1 for the points in the region, also for the fourth point on the Outer
Banks, where the temperature is null: the constant maps have a value in every
cell of the region.

=== "Command line"

    ```sh
    month=2
    for entry in feb:1.7 mar:0.9; do
        name=$(printf %02d $month)
        v.surf.idw input=precip_30ynormals column=${entry%:*} \
            output=precipitation_normal_$name npoints=12 power=2
        r.mapcalc expression="precipitation_monthly_2020_$name = if(isnull(elev_state_500m), null(), round(${entry#*:} * precipitation_normal_$name))"
        month=$((month + 1))
    done
    t.create output=precipitation_monthly title="Precipitation" \
        description="Monthly precipitation sum 2020 in mm"
    t.register -i input=precipitation_monthly \
        maps=$(g.list type=raster pattern="precipitation_monthly_*" mapset=. separator=comma) \
        start=2020-02-01 increment="1 month"
    t.vect.observe.strds input=stations strds=temperature_monthly,precipitation_monthly \
        output=obs_both vector_output=obs_both_points columns=temp,precip
    t.vect.list input=obs_both columns=name,layer,start_time
    for layer in 1 2; do
        v.db.select map=obs_both_points layer=$layer
    done
    ```

    ```text
    name|layer|start_time
    obs_both_points|1|2020-02-01 00:00:00
    obs_both_points|2|2020-03-01 00:00:00
    cat|x|y|altitude|temp|precip
    1|500657|183601|186|5.6|157
    2|169208|171737|533|3.2|263
    3|701031|282371|101|5.1|149
    4|917005|169684|3||
    5|100000|170000|50||
    cat|temp|precip
    1|9|110
    2|6.7|159
    3|8.5|102
    4||
    5||
    ```

    ```sh
    db.describe -c table=obs_both_points_2
    ```

    ```text
    ncols: 3
    nrows: 5
    Column 1: cat:INTEGER:20
    Column 2: temp:DOUBLE PRECISION:20
    Column 3: precip:INTEGER:20
    ```

    ```sh
    r.mapcalc expression="shifted_1 = 1"
    t.create output=shifted title="Shifted" description="Noon to noon"
    t.register input=shifted maps=shifted_1 \
        start="2020-01-15 12:00:00" end="2020-02-15 12:00:00"
    t.vect.observe.strds input=stations strds=temperature_monthly,shifted \
        output=none vector_output=none_points columns=temp,shifted 2>&1 |
        sed -n '/^WARNING/,$p'
    g.list type=vector pattern=none_points
    ```

    ```text
    WARNING: No granule of space time raster dataset
             <temperature_monthly@t_vect_observe_strds> has a map in each of
             the datasets, nothing is written
    ```

    ```sh
    r.mapcalc expression="twin_a = 1"
    r.mapcalc expression="twin_b = 2"
    t.create output=twin title="Twin" description="Two maps for one month"
    t.register input=twin maps=twin_a,twin_b start=2020-01-01 end=2020-02-01
    t.vect.observe.strds input=stations strds=temperature_monthly,twin \
        output=obs_twin vector_output=obs_twin_points columns=temp,two 2>&1 |
        sed -n '/^WARNING: Granule/,/is used$/p'
    v.db.select map=obs_twin_points layer=1
    ```

    ```text
    WARNING: Granule 2020-01-01 00:00:00 - 2020-02-01 00:00:00: space time
             raster dataset <twin> has 2 maps, only
             <twin_a@t_vect_observe_strds> is used
    cat|x|y|altitude|temp|two
    1|500657|183601|186|4.7|1
    2|169208|171737|533|2.4|1
    3|701031|282371|101|4.2|1
    4|917005|169684|3||1
    5|100000|170000|50||
    ```

=== "Python (grass.tools)"

    ```python
    factors = {"feb": 1.7, "mar": 0.9}
    for month, (column, factor) in enumerate(factors.items(), start=2):
        normal = f"precipitation_normal_{month:02d}"
        tools.v_surf_idw(
            input="precip_30ynormals", column=column, output=normal, npoints=12, power=2
        )
        tools.r_mapcalc(
            expression=f"precipitation_monthly_2020_{month:02d} ="
            f" if(isnull(elev_state_500m), null(), round({factor} * {normal}))"
        )
    tools.t_create(
        output="precipitation_monthly",
        title="Precipitation",
        description="Monthly precipitation sum 2020 in mm",
    )
    tools.t_register(
        input="precipitation_monthly",
        maps="precipitation_monthly_2020_02,precipitation_monthly_2020_03",
        start="2020-02-01",
        increment="1 month",
        flags="i",
    )
    tools.t_vect_observe_strds(
        input="stations",
        strds="temperature_monthly,precipitation_monthly",
        output="obs_both",
        vector_output="obs_both_points",
        columns="temp,precip",
    )
    print(tools.t_vect_list(input="obs_both", columns="name,layer,start_time").text)
    for layer in (1, 2):
        print(tools.v_db_select(map="obs_both_points", layer=layer).text)
    ```

    ```text
    name|layer|start_time
    obs_both_points|1|2020-02-01 00:00:00
    obs_both_points|2|2020-03-01 00:00:00
    cat|x|y|altitude|temp|precip
    1|500657|183601|186|5.6|157
    2|169208|171737|533|3.2|263
    3|701031|282371|101|5.1|149
    4|917005|169684|3||
    5|100000|170000|50||
    cat|temp|precip
    1|9|110
    2|6.7|159
    3|8.5|102
    4||
    5||
    ```

    ```python
    print(tools.db_describe(table="obs_both_points_2", flags="c").text)
    ```

    ```text
    ncols: 3
    nrows: 5
    Column 1: cat:INTEGER:20
    Column 2: temp:DOUBLE PRECISION:20
    Column 3: precip:INTEGER:20
    ```

    ```python
    tools.r_mapcalc(expression="shifted_1 = 1")
    tools.t_create(output="shifted", title="Shifted", description="Noon to noon")
    tools.t_register(
        input="shifted",
        maps="shifted_1",
        start="2020-01-15 12:00:00",
        end="2020-02-15 12:00:00",
    )
    import re

    from grass.tools import Tools

    # A tool without output returns None, unless the result object is requested.
    with_result = Tools(consistent_return_value=True)
    result = with_result.t_vect_observe_strds(
        input="stations",
        strds="temperature_monthly,shifted",
        output="none",
        vector_output="none_points",
        columns="temp,shifted",
    )
    print(result.stderr.strip())
    print(with_result.g_list(type="vector", pattern="none_points").stdout.split())
    ```

    ```text
    WARNING: No granule of space time raster dataset
             <temperature_monthly@t_vect_observe_strds> has a map in each of
             the datasets, nothing is written
    []
    ```

    ```python
    tools.r_mapcalc(expression="twin_a = 1")
    tools.r_mapcalc(expression="twin_b = 2")
    tools.t_create(output="twin", title="Twin", description="Two maps for one month")
    tools.t_register(
        input="twin", maps="twin_a,twin_b", start="2020-01-01", end="2020-02-01"
    )
    result = with_result.t_vect_observe_strds(
        input="stations",
        strds="temperature_monthly,twin",
        output="obs_twin",
        vector_output="obs_twin_points",
        columns="temp,two",
    )
    print(re.search(r"WARNING: Granule.*?is used", result.stderr, re.DOTALL).group())
    print(tools.v_db_select(map="obs_twin_points", layer=1).text)
    ```

    ```text
    WARNING: Granule 2020-01-01 00:00:00 - 2020-02-01 00:00:00: space time
             raster dataset <twin> has 2 maps, only
             <twin_a@t_vect_observe_strds> is used
    cat|x|y|altitude|temp|two
    1|500657|183601|186|4.7|1
    2|169208|171737|533|2.4|1
    3|701031|282371|101|4.2|1
    4|917005|169684|3||1
    5|100000|170000|50||
    ```

### Observe a selection of the points

**where** selects points of `stations` by their attributes: `altitude < 150`
keeps the points with the categories 3, 4 and 5. The output map has only these
points, in every layer, with the categories they have in the input. The values
are those of the first example. The layer 1 of the output keeps the layer name
`stations`.

The second block uses a condition that selects no point. The module stops with
an error and makes neither the vector map `nowhere_points` nor a dataset.

=== "Command line"

    ```sh
    t.vect.observe.strds input=stations strds=temperature_monthly output=obs_low \
        vector_output=obs_low_points columns=temp where="altitude < 150"
    for layer in 1 3; do
        v.db.select map=obs_low_points layer=$layer
    done
    v.db.connect -g map=obs_low_points | cut -d"|" -f1,2
    ```

    ```text
    cat|x|y|altitude|temp
    3|701031|282371|101|4.2
    4|917005|169684|3|
    5|100000|170000|50|
    cat|temp
    3|8.5
    4|
    5|
    1/stations|obs_low_points
    2/obs_low_points_2|obs_low_points_2
    3/obs_low_points_3|obs_low_points_3
    ```

    ```sh
    if ! (t.vect.observe.strds input=stations strds=temperature_monthly \
        output=nowhere vector_output=nowhere_points columns=temp \
        where="altitude > 900" 2>&1 | sed -n '/^ERROR/,$p'); then
        echo "t.vect.observe.strds failed"
    fi
    g.list type=vector pattern=nowhere_points
    ```

    ```text
    ERROR: The where option selects no point of vector map <stations>
    t.vect.observe.strds failed
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools, ToolError

    tools.t_vect_observe_strds(
        input="stations",
        strds="temperature_monthly",
        output="obs_low",
        vector_output="obs_low_points",
        columns="temp",
        where="altitude < 150",
    )
    for layer in (1, 3):
        print(tools.v_db_select(map="obs_low_points", layer=layer).text)
    for line in tools.v_db_connect(map="obs_low_points", flags="g").text.splitlines():
        print("|".join(line.split("|")[:2]))
    ```

    ```text
    cat|x|y|altitude|temp
    3|701031|282371|101|4.2
    4|917005|169684|3|
    5|100000|170000|50|
    cat|temp
    3|8.5
    4|
    5|
    1/stations|obs_low_points
    2/obs_low_points_2|obs_low_points_2
    3/obs_low_points_3|obs_low_points_3
    ```

    ```python
    try:
        tools.t_vect_observe_strds(
            input="stations",
            strds="temperature_monthly",
            output="nowhere",
            vector_output="nowhere_points",
            columns="temp",
            where="altitude > 900",
        )
    except ToolError as error:
        lines = error.stderr.strip().splitlines()
        first = [line.startswith("ERROR") for line in lines].index(True)
        print("\n".join(lines[first:]))
        print("t.vect.observe.strds failed")
    with_result = Tools(consistent_return_value=True)
    print(with_result.g_list(type="vector", pattern="nowhere_points").stdout.split())
    ```

    ```text
    ERROR: The where option selects no point of vector map <stations>
    t.vect.observe.strds failed
    []
    ```

### Use the name of a column that the input has

The column `altitude` exists in the table of `stations`. The first block shows
that the module refuses it and prints the error. With **--overwrite** (second
block) the module writes the sampled values into the existing column of layer 1
and the layers 2 and 3 get a column with that name. The fifth point lies
outside the region, and the fourth point lies on a cell without a value: both
get a NULL, because the column is emptied before the values are written. The
third block shows that `Altitude` is refused, with **--overwrite** too, because
it differs from `altitude` only in the case of a letter.

=== "Command line"

    ```sh
    if ! (t.vect.observe.strds input=stations strds=temperature_monthly \
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
    t.vect.observe.strds --overwrite input=stations strds=temperature_monthly \
        output=check vector_output=check_points columns=altitude
    for layer in 1 3; do
        v.db.select map=check_points layer=$layer
    done
    ```

    ```text
    cat|x|y|altitude
    1|500657|183601|4.7
    2|169208|171737|2.4
    3|701031|282371|4.2
    4|917005|169684|
    5|100000|170000|
    cat|altitude
    1|9
    2|6.7
    3|8.5
    4|
    5|
    ```

    ```sh
    if ! (t.vect.observe.strds --overwrite input=stations strds=temperature_monthly \
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
            strds="temperature_monthly",
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
        strds="temperature_monthly",
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
    1|500657|183601|4.7
    2|169208|171737|2.4
    3|701031|282371|4.2
    4|917005|169684|
    5|100000|170000|
    cat|altitude
    1|9
    2|6.7
    3|8.5
    4|
    5|
    ```

    ```python
    try:
        tools.t_vect_observe_strds(
            input="stations",
            strds="temperature_monthly",
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

The dataset `runoff` has relative time with the unit hours: `runoff_1` from 0
to 1 and `runoff_2` from 1 to 2, with the constant values 100 and 200. In
layer 2 the points 1 to 4 read 200, the fifth point outside the region has no
value. The output dataset has relative time with the same unit, and its
layers have the times of the maps as numbers.

=== "Command line"

    ```sh
    for step in 1 2; do
        r.mapcalc expression="runoff_$step = 100 * $step"
    done
    t.create output=runoff temporaltype=relative title="Runoff" \
        description="Simulated runoff in mm per model hour"
    t.register -i input=runoff maps=runoff_1,runoff_2 start=0 increment=1 unit=hours
    t.vect.observe.strds input=stations strds=runoff output=obs_runoff \
        vector_output=obs_runoff_points columns=runoff_mm
    t.vect.list input=obs_runoff columns=name,layer,start_time,end_time
    t.info -g type=stvds input=obs_runoff | grep -E "^(temporal_type|unit)="
    v.db.select map=obs_runoff_points layer=2
    ```

    ```text
    name|layer|start_time|end_time
    obs_runoff_points|1|0|1
    obs_runoff_points|2|1|2
    temporal_type=relative
    unit=hours
    cat|runoff_mm
    1|200
    2|200
    3|200
    4|200
    5|
    ```

=== "Python (grass.tools)"

    ```python
    for step in (1, 2):
        tools.r_mapcalc(expression=f"runoff_{step} = 100 * {step}")
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
    tools.t_vect_observe_strds(
        input="stations",
        strds="runoff",
        output="obs_runoff",
        vector_output="obs_runoff_points",
        columns="runoff_mm",
    )
    print(
        tools.t_vect_list(input="obs_runoff", columns="name,layer,start_time,end_time").text
    )
    info = tools.t_info(type="stvds", input="obs_runoff", flags="g").keyval
    for key in ("temporal_type", "unit"):
        print(f"{key}={info[key]}")
    print(tools.v_db_select(map="obs_runoff_points", layer=2).text)
    ```

    ```text
    name|layer|start_time|end_time
    obs_runoff_points|1|0|1
    obs_runoff_points|2|1|2
    temporal_type=relative
    unit=hours
    cat|runoff_mm
    1|200
    2|200
    3|200
    4|200
    5|
    ```

### Observe data of another mapset

The input map and the raster dataset may be in another mapset: the names with
the mapset, `stations@t_vect_observe_strds` and
`temperature_monthly@t_vect_observe_strds`, select them. The output map and
dataset are made in the current mapset, here the new mapset
`t_vect_observe_strds_2`. A new mapset has its own region, so the example sets
the region again before the points are sampled. The mapset
`t_vect_observe_strds` does not have to be in the search path.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_observe_strds_2
    g.region raster=elev_state_500m res=1000 -a
    t.vect.observe.strds input=stations@t_vect_observe_strds \
        strds=temperature_monthly@t_vect_observe_strds output=remote \
        vector_output=remote_points columns=temp
    t.vect.list input=remote columns=name,layer,mapset
    v.db.select map=remote_points layer=1 columns=cat,temp
    ```

    ```text
    name|layer|mapset
    remote_points|1|t_vect_observe_strds_2
    remote_points|2|t_vect_observe_strds_2
    remote_points|3|t_vect_observe_strds_2
    cat|temp
    1|4.7
    2|2.4
    3|4.2
    4|
    5|
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_vect_observe_strds_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.t_vect_observe_strds(
        input="stations@t_vect_observe_strds",
        strds="temperature_monthly@t_vect_observe_strds",
        output="remote",
        vector_output="remote_points",
        columns="temp",
    )
    print(tools.t_vect_list(input="remote", columns="name,layer,mapset").text)
    print(tools.v_db_select(map="remote_points", layer=1, columns="cat,temp").text)
    ```

    ```text
    name|layer|mapset
    remote_points|1|t_vect_observe_strds_2
    remote_points|2|t_vect_observe_strds_2
    remote_points|3|t_vect_observe_strds_2
    cat|temp
    1|4.7
    2|2.4
    3|4.2
    4|
    5|
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.mapset](g.mapset.md), [g.mapsets](g.mapsets.md),
[g.region](g.region.md), [t.create](t.create.md),
[t.info](t.info.md), [t.rast.what](t.rast.what.md),
[t.register](t.register.md), [t.vect.db.select](t.vect.db.select.md),
[t.vect.list](t.vect.list.md), [t.vect.what.strds](t.vect.what.strds.md),
[v.db.select](v.db.select.md), [v.extract](v.extract.md),
[v.surf.idw](v.surf.idw.md), [v.what.rast](v.what.rast.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
