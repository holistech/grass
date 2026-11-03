## DESCRIPTION

*t.vect.univar* calculates univariate statistics of an attribute column for
each vector map registered in a space time vector dataset and prints one line
of statistics per map, ordered by start time. It runs *[v.univar](v.univar.md)*
for every map, so the statistics are those of *v.univar*: they are taken from
the values of the column in the attribute table of the map, which are read
through the categories of the features. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. Space time raster datasets have their own tool,
*[t.rast.univar](t.rast.univar.md)*, space time 3D raster datasets
*[t.rast3d.univar](t.rast3d.univar.md)*.

The option **input** names the space time vector dataset, and the option
**column** the numeric attribute column, which has to exist in the table of
every selected map. Each line of the output starts with three columns that name
the map:

- `id`, the name of the map with its mapset, such as `gauges_1@t_vect_univar`;
- `start` and `end`, the start and end time of the map; the end of a map
  registered as a time instance is `None`.

Three columns count the features:

- `n`, the number of values the statistics are taken from;
- `nmissing`, the number of features without a selected row in the attribute
  table. The condition **where** leaves rows out, so the features whose row it
  does not select are counted here;
- `nnull`, the number of features whose value in the column is NULL. A NULL is
  not a value: it takes no part in the statistics and not in `n`.

The statistics follow. They are empty if the map has no value to take them
from (`n` is 0):

- `min`, `max` and `range`, the smallest and the largest value and their
  difference;
- `mean` and `mean_abs`, the mean of the values and the mean of their
  absolute values;
- `population_stddev` and `population_variance`: the variance is the sum of
  the squared deviations from the mean divided by `n` (the population
  variance), the standard deviation is its square root;
- `population_coeff_variation`, the population standard deviation divided by
  the absolute value of the mean, so that it stays positive for a negative
  mean (the values -1 and -3 have the mean -2, the standard deviation 1 and the
  coefficient 0.5). Unlike `coeff_var` of *t.rast.univar* it is not given in
  percent;
- `sample_stddev` and `sample_variance`: the sum of the squared deviations
  divided by `n - 1`, and its square root;
- `kurtosis`, the mean of the fourth powers of the deviations divided by the
  fourth power of `sample_stddev`, minus 3, so that it is 0 for a normal
  distribution;
- `skewness`, the mean of the third powers of the deviations divided by the
  third power of `sample_stddev`. It is 0 for values that are symmetric around
  the mean.

The flag **-e** adds the extended statistics `first_quartile`, `median`,
`third_quartile` and the 90th percentile `percentile_90`; the percentile cannot
be changed. *v.univar* finds a percentile p in the sorted values: it takes the
value at position `n * p / 100 - 0.5` with the fractional part dropped,
counting from 0, so with four values the 90th percentile is the largest. The
quartiles follow the same rule with p = 25 and p = 75. The median is the
middle value, or the mean of the two middle values when `n` is even. The
extended statistics need values: for a map without values they are empty, too.

The option **type** chooses the features that are read: `point` (the default),
`line`, `boundary`, `centroid` or `area`. A feature has to have a category in
the layer, and its category links it to a row of the table. With `point` and
`centroid`, the statistics are all those above. With the other types, the
output has the columns up to `range` and no more, also with **-e** (see
NOTES).
The type `area` reads the categories of the centroids of the areas, which is
the way to get the attribute of an area. A type that the map has no features
of gives a line with `n` 0 and no statistics, as a map of lines does with the
default `point`.

The option **layer** is the layer of the vector map whose table holds the
column. It applies to the maps that are registered without a layer; a map
registered with a layer, as `mast_1:2` for layer 2, is always read from that
layer. The default is layer 1.

Two options select what is counted, and they can be combined:

- the option **twhere** takes an SQL condition on the registered maps of the
  dataset and selects the maps, for instance on `start_time` or `name`;
- the option **where** takes an SQL condition on the table of each map and
  selects the rows whose features are counted.

The option **output** writes the statistics to a file instead of the standard
output; `output=-` is the standard output. An existing file is replaced only
with **--overwrite**. The option **separator** sets the character between the
columns, the vertical bar `|` by default; it takes a single character or a
name such as `comma`. The flag **-u** leaves out the line with the column
names.

## NOTES

A NULL value is counted in `nnull` and is not part of the statistics, neither
of the extended ones. With **where**, a feature whose row the condition does
not select is counted in `nmissing`, a NULL included: the condition
`discharge > 2` is not true for a NULL.

In a dataset with relative time, `start` and `end` are numbers of the time
unit of the dataset, printed without the unit: a map registered from 0 to 6
hours shows `0` and `6`, as the first example shows.

*t.vect.univar* only reads, so it works on a dataset of another mapset as
well. The name with the mapset (`input=gauges@t_vect_univar`) selects it. A name
without a mapset means the current mapset: the mapsets of the search path (see
*[g.mapsets](g.mapsets.md)*) are not searched, unlike in *t.rast.univar*, and
the dataset is reported as not found. The last example shows this.

If **twhere** selects no map, or the dataset has no map, *t.vect.univar* stops
with the message that the space time vector dataset is empty. A dataset that
does not exist stops it with the message that it was not found.

If *v.univar* fails on a map, for instance because the column does not exist in
the table of the map, because the layer does not exist, or because **where** is
no valid condition, *t.vect.univar* stops with the message `Error running
v.univar on` followed by the map and the message of *v.univar*. A **twhere**
that the database cannot parse stops the tool with the message `Invalid twhere
condition` followed by the condition and the message of the database.

**-e** is accepted for the types `line`, `boundary` and `area`, and *v.univar*
warns that the extended statistics exist only for points and centroids, as the
example of the type `area` shows.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_vect_univar` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset and
region. *t.vect.univar* reads the attribute tables, so the maps are copies of
the stream gauges `usgsgages` of the dataset with integer columns of generated
values, which the examples set to numbers that can be recomputed by hand.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_vect_univar -->

<!-- markdownlint-disable MD046 -->

### Statistics of each map of a dataset

The points of the maps are stream gauges. Three maps with two integer columns:
`discharge`, a generated discharge in cubic meters per second, and `peak`,
which is `discharge + 1`. The values are plausible for small streams, a few
cubic meters per second, with a flood of 40 in the third map, but they are not
measured.

- `gauges_1` has the discharges 1, 2, 3 and 4, those of the gauges with the
  categories 1 to 4;
- `gauges_2` has 2, 4, 6 and 8, and a fifth gauge without a discharge: its columns
  stay NULL;
- `gauges_3` has 10, 10, 10 and 40.

The maps are registered as daily intervals starting on 1 March 2026. The
statistics follow by hand from the values. For `gauges_1` the mean is
10 / 4 = 2.5, and the deviations from the mean are -1.5, -0.5, 0.5 and 1.5,
whose squares add up to 5. The population variance is 5 / 4 = 1.25, the sample
variance 5 / 3 = 1.6667, and the population coefficient of variation
`sqrt(1.25) / 2.5` = 0.4472. The values are symmetric, so the skewness is 0;
the kurtosis is `10.25 / 4 / (5 / 3)^2 - 3` = -2.0775. `gauges_2` has twice
the values, so four times the variances, and the same coefficient of
variation, skewness and kurtosis; its fifth point is counted in `nnull`, not
in `n`. `gauges_3` is skewed: the mean is 17.5, the deviations are -7.5, -7.5,
-7.5 and 22.5, the sample variance 225, and the skewness
`(10125 / 4) / 15^3` = 0.75.

The second block makes the dataset `steps` with relative time: two maps of 6
hours each. Their `start` and `end` are numbers of hours. It shows the columns
`id`, `n` to `range` only.

The third block makes the region smaller, so that it holds only the first
gauge of each map, and runs the command of the first block again: the numbers
are the same as there. The region does not change the statistics of
*t.vect.univar*. The block sets the region back afterwards.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_univar
    g.region raster=elev_state_500m res=1000 -a
    v.extract input=usgsgages output=gauges_1 where="cat <= 4"
    v.extract input=usgsgages output=gauges_2 where="cat <= 5"
    v.extract input=usgsgages output=gauges_3 where="cat <= 4"
    v.db.addcolumn map=gauges_1 columns="discharge integer, peak integer"
    v.db.addcolumn map=gauges_2 columns="discharge integer, peak integer"
    v.db.addcolumn map=gauges_3 columns="discharge integer, peak integer"
    v.db.update map=gauges_1 column=discharge query_column=cat
    v.db.update map=gauges_2 column=discharge query_column="2 * cat" where="cat <= 4"
    v.db.update map=gauges_3 column=discharge \
        query_column="CASE WHEN cat < 4 THEN 10 ELSE 40 END"
    for map in gauges_1 gauges_2 gauges_3; do
        v.db.update map=$map column=peak query_column="discharge + 1"
    done
    t.create type=stvds output=gauges title="Gauges" \
        description="Discharge at gauges"
    t.register -i type=vector input=gauges \
        maps=gauges_1,gauges_2,gauges_3 start=2026-03-01 increment="1 day"
    t.vect.univar input=gauges column=discharge
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range|mean|mean_abs|population_stddev|population_variance|population_coeff_variation|sample_stddev|sample_variance|kurtosis|skewness
    gauges_1@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|4|0|0|1|4|3|2.5|2.5|1.11803|1.25|0.447214|1.29099|1.66667|-2.0775|0
    gauges_2@t_vect_univar|2026-03-02 00:00:00|2026-03-03 00:00:00|4|0|1|2|8|6|5|5|2.23607|5|0.447214|2.58199|6.66667|-2.0775|0
    gauges_3@t_vect_univar|2026-03-03 00:00:00|2026-03-04 00:00:00|4|0|0|10|40|30|17.5|17.5|12.9904|168.75|0.742307|15|225|-1.6875|0.75
    ```

    ```sh
    v.extract input=usgsgages output=step_1 where="cat <= 2"
    v.extract input=usgsgages output=step_2 where="cat <= 2"
    v.db.addcolumn map=step_1 columns="discharge integer"
    v.db.addcolumn map=step_2 columns="discharge integer"
    v.db.update map=step_1 column=discharge query_column="2 * cat - 1"
    v.db.update map=step_2 column=discharge query_column="2 * cat + 3"
    t.create type=stvds output=steps temporaltype=relative title="Steps" \
        description="Model steps of 6 hours"
    t.register -i type=vector input=steps maps=step_1,step_2 \
        start=0 increment=6 unit=hours
    t.vect.univar input=steps column=discharge | cut -d"|" -f1,4-9
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    step_1@t_vect_univar|2|0|0|1|3|2
    step_2@t_vect_univar|2|0|0|5|7|2
    ```

    ```sh
    g.region n=334000 s=333000 w=868000 e=869000
    t.vect.univar input=gauges column=discharge | cut -d"|" -f1,4-9
    g.region raster=elev_state_500m res=1000 -a
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    gauges_1@t_vect_univar|4|0|0|1|4|3
    gauges_2@t_vect_univar|4|0|1|2|8|6
    gauges_3@t_vect_univar|4|0|0|10|40|30
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(mapset="t_vect_univar", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    gauges = {
        "gauges_1": ("cat <= 4", "cat", None),
        "gauges_2": ("cat <= 5", "2 * cat", "cat <= 4"),
        "gauges_3": ("cat <= 4", "CASE WHEN cat < 4 THEN 10 ELSE 40 END", None),
    }
    for name, (selection, discharge, discharge_where) in gauges.items():
        tools.v_extract(input="usgsgages", output=name, where=selection)
        tools.v_db_addcolumn(map=name, columns="discharge integer, peak integer")
        options = {"where": discharge_where} if discharge_where else {}
        tools.v_db_update(map=name, column="discharge", query_column=discharge, **options)
        tools.v_db_update(map=name, column="peak", query_column="discharge + 1")
    tools.t_create(
        type="stvds", output="gauges", title="Gauges", description="Discharge at gauges"
    )
    tools.t_register(
        type="vector",
        input="gauges",
        maps=",".join(gauges),
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_vect_univar(input="gauges", column="discharge").text)
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range|mean|mean_abs|population_stddev|population_variance|population_coeff_variation|sample_stddev|sample_variance|kurtosis|skewness
    gauges_1@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|4|0|0|1|4|3|2.5|2.5|1.11803|1.25|0.447214|1.29099|1.66667|-2.0775|0
    gauges_2@t_vect_univar|2026-03-02 00:00:00|2026-03-03 00:00:00|4|0|1|2|8|6|5|5|2.23607|5|0.447214|2.58199|6.66667|-2.0775|0
    gauges_3@t_vect_univar|2026-03-03 00:00:00|2026-03-04 00:00:00|4|0|0|10|40|30|17.5|17.5|12.9904|168.75|0.742307|15|225|-1.6875|0.75
    ```

    ```python
    steps = {"step_1": "2 * cat - 1", "step_2": "2 * cat + 3"}
    for name, discharge in steps.items():
        tools.v_extract(input="usgsgages", output=name, where="cat <= 2")
        tools.v_db_addcolumn(map=name, columns="discharge integer")
        tools.v_db_update(map=name, column="discharge", query_column=discharge)
    tools.t_create(
        type="stvds",
        output="steps",
        temporaltype="relative",
        title="Steps",
        description="Model steps of 6 hours",
    )
    tools.t_register(
        type="vector",
        input="steps",
        maps="step_1,step_2",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )


    def print_columns(result):
        for line in result.text.splitlines():
            columns = line.split("|")
            print("|".join(columns[:1] + columns[3:9]))


    print_columns(tools.t_vect_univar(input="steps", column="discharge"))
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    step_1@t_vect_univar|2|0|0|1|3|2
    step_2@t_vect_univar|2|0|0|5|7|2
    ```

    ```python
    tools.g_region(n=334000, s=333000, w=868000, e=869000)
    print_columns(tools.t_vect_univar(input="gauges", column="discharge"))
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    gauges_1@t_vect_univar|4|0|0|1|4|3
    gauges_2@t_vect_univar|4|0|1|2|8|6
    gauges_3@t_vect_univar|4|0|0|10|40|30
    ```

### Choose the attribute and calculate extended statistics

The option **column** chooses the attribute. `peak` is `discharge + 1`, so every
value is 1 larger: the minimum, the maximum, the mean and the quartiles move
by 1, while the range, the variances, the kurtosis and the skewness stay the
same; the coefficient of variation falls, because the mean grows. The flag
**-e** adds the quartiles and the 90th percentile. For `gauges_1` the sorted
values are 2, 3, 4 and 5. The first quartile is at position
`4 * 25 / 100 - 0.5` = 0.5, which becomes 0 (the value 2), the third quartile
at position 2.5, which becomes 2 (the value 4), and the 90th percentile at
position 3.1, which becomes 3 (the value 5). The median is the mean of the
two middle values 3 and 4. The NULL of `gauges_2` is left out: its sorted
values are 3, 5, 7 and 9.

=== "Command line"

    ```sh
    t.vect.univar -e input=gauges column=peak
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range|mean|mean_abs|population_stddev|population_variance|population_coeff_variation|sample_stddev|sample_variance|kurtosis|skewness|first_quartile|median|third_quartile|percentile_90
    gauges_1@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|4|0|0|2|5|3|3.5|3.5|1.11803|1.25|0.319438|1.29099|1.66667|-2.0775|0|2|3.5|4|5
    gauges_2@t_vect_univar|2026-03-02 00:00:00|2026-03-03 00:00:00|4|0|1|3|9|6|6|6|2.23607|5|0.372678|2.58199|6.66667|-2.0775|0|3|6|7|9
    gauges_3@t_vect_univar|2026-03-03 00:00:00|2026-03-04 00:00:00|4|0|0|11|41|30|18.5|18.5|12.9904|168.75|0.702183|15|225|-1.6875|0.75|11|11|11|41
    ```

=== "Python (grass.tools)"

    ```python
    print(tools.t_vect_univar(input="gauges", column="peak", flags="e").text)
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range|mean|mean_abs|population_stddev|population_variance|population_coeff_variation|sample_stddev|sample_variance|kurtosis|skewness|first_quartile|median|third_quartile|percentile_90
    gauges_1@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|4|0|0|2|5|3|3.5|3.5|1.11803|1.25|0.319438|1.29099|1.66667|-2.0775|0|2|3.5|4|5
    gauges_2@t_vect_univar|2026-03-02 00:00:00|2026-03-03 00:00:00|4|0|1|3|9|6|6|6|2.23607|5|0.372678|2.58199|6.66667|-2.0775|0|3|6|7|9
    gauges_3@t_vect_univar|2026-03-03 00:00:00|2026-03-04 00:00:00|4|0|0|11|41|30|18.5|18.5|12.9904|168.75|0.702183|15|225|-1.6875|0.75|11|11|11|41
    ```

### Select maps and features

The option **twhere** selects maps by their registered times, and the option
**where** the features of each map by their attributes. The columns `id`, `n`
to `range` are shown.

1. `where="discharge > 2"` counts only the points with a discharge above 2 in every
   map. In `gauges_1` these are 3 and 4, so `n` is 2 and the 2 other points are
   counted in `nmissing`. `gauges_2` keeps 4, 6 and 8; the points with the
   discharges 2 and NULL are missing, because the row of a NULL is not selected
   by the condition, so `nnull` is 0 here. `gauges_3` keeps all of its points.
2. `twhere="start_time >= '2026-03-02'"` selects the maps `gauges_2` and
   `gauges_3` and counts all their points.
3. Both options work together: of the maps that start on 2 March or later,
   only the points above 2 are counted.

=== "Command line"

    ```sh
    t.vect.univar input=gauges column=discharge where="discharge > 2" |
        cut -d"|" -f1,4-9
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    gauges_1@t_vect_univar|2|2|0|3|4|1
    gauges_2@t_vect_univar|3|2|0|4|8|4
    gauges_3@t_vect_univar|4|0|0|10|40|30
    ```

    ```sh
    t.vect.univar input=gauges column=discharge \
        twhere="start_time >= '2026-03-02'" | cut -d"|" -f1,4-9
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    gauges_2@t_vect_univar|4|0|1|2|8|6
    gauges_3@t_vect_univar|4|0|0|10|40|30
    ```

    ```sh
    t.vect.univar input=gauges column=discharge where="discharge > 2" \
        twhere="start_time >= '2026-03-02'" | cut -d"|" -f1,4-9
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    gauges_2@t_vect_univar|3|2|0|4|8|4
    gauges_3@t_vect_univar|4|0|0|10|40|30
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_vect_univar(input="gauges", column="discharge", where="discharge > 2")
    print_columns(result)
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    gauges_1@t_vect_univar|2|2|0|3|4|1
    gauges_2@t_vect_univar|3|2|0|4|8|4
    gauges_3@t_vect_univar|4|0|0|10|40|30
    ```

    ```python
    result = tools.t_vect_univar(
        input="gauges", column="discharge", twhere="start_time >= '2026-03-02'"
    )
    print_columns(result)
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    gauges_2@t_vect_univar|4|0|1|2|8|6
    gauges_3@t_vect_univar|4|0|0|10|40|30
    ```

    ```python
    result = tools.t_vect_univar(
        input="gauges",
        column="discharge",
        where="discharge > 2",
        twhere="start_time >= '2026-03-02'",
    )
    print_columns(result)
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    gauges_2@t_vect_univar|3|2|0|4|8|4
    gauges_3@t_vect_univar|4|0|0|10|40|30
    ```

### Statistics of lines and areas

The map `plots` is a small generated sketch that *v.in.ascii* reads. It has two
lines with the categories 1 and 2, two squares of 20 km by 20 km and the
centroids of the squares with the categories 3 and 4; they lie inside the
region. Its table has the integer column `value`, 10 times the category: 10, 20,
30 and 40. It is registered as one map of the dataset `plotset`. The option
**type** decides which features are read:

1. `line` reads the two lines: the values 10 and 20.
2. `area` reads the categories of the centroids of the areas: 30 and 40. The
   output ends with `range` for both types, also with the flag **-e**; the
   second block shows the warning of *v.univar* on the error output.
3. `centroid` reads the same centroids, and prints all statistics: with the
   values 30 and 40 the mean is 35, the deviations are -5 and 5, so the
   population variance is 25 and the sample variance 50.
4. `boundary` finds no feature with a category: a line without statistics.
5. The default `point` finds no point: the same.

=== "Command line"

    ```sh
    v.in.ascii input=- output=plots format=standard <<EOF
    VERTI:
    L 2 1
     400000 100000
     440000 100000
     1 1
    L 2 1
     400000 120000
     440000 120000
     1 2
    B 5
     460000 100000
     480000 100000
     480000 120000
     460000 120000
     460000 100000
    B 5
     500000 100000
     520000 100000
     520000 120000
     500000 120000
     500000 100000
    C 1 1
     470000 110000
     1 3
    C 1 1
     510000 110000
     1 4
    EOF
    v.db.addtable map=plots columns="value integer"
    v.db.update map=plots column=value query_column="cat * 10"
    t.create type=stvds output=plotset title="Plots" \
        description="Lines and areas"
    t.register type=vector input=plotset maps=plots \
        start=2026-03-01 end=2026-03-02
    t.vect.univar input=plotset column=value type=line
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range
    plots@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|2|0|0|10|20|10
    ```

    ```sh
    t.vect.univar -e input=plotset column=value type=area
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range
    plots@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|2|0|0|30|40|10
    ```

    ```sh
    t.vect.univar -e input=plotset column=value type=area 2>&1 >/dev/null |
        grep -A1 WARNING
    ```

    ```text
    WARNING: Extended statistics is currently supported only for
             points/centroids
    ```

    ```sh
    t.vect.univar input=plotset column=value type=centroid
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range|mean|mean_abs|population_stddev|population_variance|population_coeff_variation|sample_stddev|sample_variance|kurtosis|skewness
    plots@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|2|0|0|30|40|10|35|35|5|25|0.142857|7.07107|50|-2.75|0
    ```

    ```sh
    t.vect.univar input=plotset column=value type=boundary
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range
    plots@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|0|0|0|||
    ```

    ```sh
    t.vect.univar input=plotset column=value | cut -d"|" -f1,4-9
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    plots@t_vect_univar|0|0|0|||
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    features = """VERTI:
    L 2 1
     400000 100000
     440000 100000
     1 1
    L 2 1
     400000 120000
     440000 120000
     1 2
    B 5
     460000 100000
     480000 100000
     480000 120000
     460000 120000
     460000 100000
    B 5
     500000 100000
     520000 100000
     520000 120000
     500000 120000
     500000 100000
    C 1 1
     470000 110000
     1 3
    C 1 1
     510000 110000
     1 4
    """
    tools.v_in_ascii(input=StringIO(features), output="plots", format="standard")
    tools.v_db_addtable(map="plots", columns="value integer")
    tools.v_db_update(map="plots", column="value", query_column="cat * 10")
    tools.t_create(
        type="stvds", output="plotset", title="Plots", description="Lines and areas"
    )
    tools.t_register(
        type="vector",
        input="plotset",
        maps="plots",
        start="2026-03-01",
        end="2026-03-02",
    )
    print(tools.t_vect_univar(input="plotset", column="value", type="line").text)
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range
    plots@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|2|0|0|10|20|10
    ```

    ```python
    result = tools.t_vect_univar(input="plotset", column="value", type="area", flags="e")
    print(result.text)
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range
    plots@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|2|0|0|30|40|10
    ```

    ```python
    print(result.stderr, end="")
    ```

    ```text
    WARNING: Extended statistics is currently supported only for
             points/centroids
    ```

    ```python
    print(tools.t_vect_univar(input="plotset", column="value", type="centroid").text)
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range|mean|mean_abs|population_stddev|population_variance|population_coeff_variation|sample_stddev|sample_variance|kurtosis|skewness
    plots@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|2|0|0|30|40|10|35|35|5|25|0.142857|7.07107|50|-2.75|0
    ```

    ```python
    print(tools.t_vect_univar(input="plotset", column="value", type="boundary").text)
    ```

    ```text
    id|start|end|n|nmissing|nnull|min|max|range
    plots@t_vect_univar|2026-03-01 00:00:00|2026-03-02 00:00:00|0|0|0|||
    ```

    ```python
    print_columns(tools.t_vect_univar(input="plotset", column="value"))
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    plots@t_vect_univar|0|0|0|||
    ```

### Read the table of another layer

A vector map can have several layers, each with its own table. The maps
`mast_1` and `mast_2` are copies of the first three stream gauges with the
categories 1 to 3 in the layers 1 and 2. The column `speed` of the layer 1
holds 1, 2 and 3, the column of the layer 2 (the wind speed higher up) 11, 12
and 13. The dataset `masts` registers `mast_1` as `mast_1:2`, for layer 2, and
`mast_2` without a layer.

1. With the default layer 1, `mast_1` is read from its registered layer 2
   (11 to 13), and `mast_2` from layer 1 (1 to 3).
2. With `layer=2`, both maps are read from layer 2.
3. With `layer=1`, the registered layer of `mast_1` still wins.

=== "Command line"

    ```sh
    for mast in mast_1 mast_2; do
        v.extract input=usgsgages output=${mast}_points where="cat <= 3"
        v.db.addcolumn map=${mast}_points columns="speed integer"
        v.db.update map=${mast}_points column=speed query_column=cat
        v.category input=${mast}_points output=$mast option=transfer layer=1,2
        db.copy from_table=$mast to_table=${mast}_2
        v.db.connect map=$mast table=${mast}_2 layer=2 key=cat
        db.execute sql="UPDATE ${mast}_2 SET speed = speed + 10"
    done
    t.create type=stvds output=masts title="Masts" \
        description="Wind speed in two layers"
    t.register -i type=vector input=masts maps=mast_1:2 \
        start=2026-03-01 increment="1 day"
    t.register -i type=vector input=masts maps=mast_2 \
        start=2026-03-02 increment="1 day"
    t.vect.list input=masts columns=name,layer,start_time
    t.vect.univar input=masts column=speed | cut -d"|" -f1,4-9
    ```

    ```text
    name|layer|start_time
    mast_1|2|2026-03-01 00:00:00
    mast_2|None|2026-03-02 00:00:00
    id|n|nmissing|nnull|min|max|range
    mast_1@t_vect_univar|3|0|0|11|13|2
    mast_2@t_vect_univar|3|0|0|1|3|2
    ```

    ```sh
    t.vect.univar input=masts column=speed layer=2 | cut -d"|" -f1,4-9
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    mast_1@t_vect_univar|3|0|0|11|13|2
    mast_2@t_vect_univar|3|0|0|11|13|2
    ```

    ```sh
    t.vect.univar input=masts column=speed layer=1 | cut -d"|" -f1,4-9
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    mast_1@t_vect_univar|3|0|0|11|13|2
    mast_2@t_vect_univar|3|0|0|1|3|2
    ```

=== "Python (grass.tools)"

    ```python
    for mast in ("mast_1", "mast_2"):
        tools.v_extract(input="usgsgages", output=f"{mast}_points", where="cat <= 3")
        tools.v_db_addcolumn(map=f"{mast}_points", columns="speed integer")
        tools.v_db_update(map=f"{mast}_points", column="speed", query_column="cat")
        tools.v_category(
            input=f"{mast}_points", output=mast, option="transfer", layer="1,2"
        )
        tools.db_copy(from_table=mast, to_table=f"{mast}_2")
        tools.v_db_connect(map=mast, table=f"{mast}_2", layer=2, key="cat")
        tools.db_execute(sql=f"UPDATE {mast}_2 SET speed = speed + 10")
    tools.t_create(
        type="stvds",
        output="masts",
        title="Masts",
        description="Wind speed in two layers",
    )
    for mast, start in (("mast_1:2", "2026-03-01"), ("mast_2", "2026-03-02")):
        tools.t_register(
            type="vector",
            input="masts",
            maps=mast,
            start=start,
            increment="1 day",
            flags="i",
        )
    print(tools.t_vect_list(input="masts", columns="name,layer,start_time").text)
    print_columns(tools.t_vect_univar(input="masts", column="speed"))
    ```

    ```text
    name|layer|start_time
    mast_1|2|2026-03-01 00:00:00
    mast_2|None|2026-03-02 00:00:00
    id|n|nmissing|nnull|min|max|range
    mast_1@t_vect_univar|3|0|0|11|13|2
    mast_2@t_vect_univar|3|0|0|1|3|2
    ```

    ```python
    print_columns(tools.t_vect_univar(input="masts", column="speed", layer=2))
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    mast_1@t_vect_univar|3|0|0|11|13|2
    mast_2@t_vect_univar|3|0|0|11|13|2
    ```

    ```python
    print_columns(tools.t_vect_univar(input="masts", column="speed", layer=1))
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    mast_1@t_vect_univar|3|0|0|11|13|2
    mast_2@t_vect_univar|3|0|0|1|3|2
    ```

### Choose the output format

The option **separator** sets another separator between the columns, and the
flag **-u** leaves out the line with the column names, for instance to append
the lines to a table that has them already. With `separator=comma` and the
option **output**, the statistics go to a file instead of the standard output;
the second block of each tab prints the file.

=== "Command line"

    ```sh
    t.vect.univar -u input=gauges column=discharge separator=";" |
        cut -d";" -f1,4-9
    ```

    ```text
    gauges_1@t_vect_univar;4;0;0;1;4;3
    gauges_2@t_vect_univar;4;0;1;2;8;6
    gauges_3@t_vect_univar;4;0;0;10;40;30
    ```

    ```sh
    t.vect.univar input=gauges column=discharge separator=comma \
        output=gauges.csv
    cat gauges.csv
    ```

    ```text
    id,start,end,n,nmissing,nnull,min,max,range,mean,mean_abs,population_stddev,population_variance,population_coeff_variation,sample_stddev,sample_variance,kurtosis,skewness
    gauges_1@t_vect_univar,2026-03-01 00:00:00,2026-03-02 00:00:00,4,0,0,1,4,3,2.5,2.5,1.11803,1.25,0.447214,1.29099,1.66667,-2.0775,0
    gauges_2@t_vect_univar,2026-03-02 00:00:00,2026-03-03 00:00:00,4,0,1,2,8,6,5,5,2.23607,5,0.447214,2.58199,6.66667,-2.0775,0
    gauges_3@t_vect_univar,2026-03-03 00:00:00,2026-03-04 00:00:00,4,0,0,10,40,30,17.5,17.5,12.9904,168.75,0.742307,15,225,-1.6875,0.75
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_vect_univar(input="gauges", column="discharge", separator=";", flags="u")
    for line in result.text.splitlines():
        columns = line.split(";")
        print(";".join(columns[:1] + columns[3:9]))
    ```

    ```text
    gauges_1@t_vect_univar;4;0;0;1;4;3
    gauges_2@t_vect_univar;4;0;1;2;8;6
    gauges_3@t_vect_univar;4;0;0;10;40;30
    ```

    ```python
    from pathlib import Path

    tools.t_vect_univar(
        input="gauges", column="discharge", separator="comma", output="gauges.csv"
    )
    print(Path("gauges.csv").read_text(), end="")
    ```

    ```text
    id,start,end,n,nmissing,nnull,min,max,range,mean,mean_abs,population_stddev,population_variance,population_coeff_variation,sample_stddev,sample_variance,kurtosis,skewness
    gauges_1@t_vect_univar,2026-03-01 00:00:00,2026-03-02 00:00:00,4,0,0,1,4,3,2.5,2.5,1.11803,1.25,0.447214,1.29099,1.66667,-2.0775,0
    gauges_2@t_vect_univar,2026-03-02 00:00:00,2026-03-03 00:00:00,4,0,1,2,8,6,5,5,2.23607,5,0.447214,2.58199,6.66667,-2.0775,0
    gauges_3@t_vect_univar,2026-03-03 00:00:00,2026-03-04 00:00:00,4,0,0,10,40,30,17.5,17.5,12.9904,168.75,0.742307,15,225,-1.6875,0.75
    ```

### Use a dataset of another mapset

*t.vect.univar* reads a dataset of another mapset. The example creates the
mapset `t_vect_univar_2`, switches to it, sets the region and adds the mapset
`t_vect_univar` to the search path with *g.mapsets*. The dataset `gauges` stays
in the mapset `t_vect_univar` and is named with its mapset. A name without a
mapset means the current mapset, whatever the search path of *g.mapsets*
holds: in the second block, `t_vect_univar` is in the search path of
`t_vect_univar_2`, but `input=gauges` is refused. The second block prints the
line of the error message.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_univar_2
    g.region raster=elev_state_500m res=1000 -a
    g.mapsets mapset=t_vect_univar operation=add
    t.vect.univar input=gauges@t_vect_univar column=discharge \
        twhere="start_time < '2026-03-02'" | cut -d"|" -f1,4-9
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    gauges_1@t_vect_univar|4|0|0|1|4|3
    ```

    ```sh
    g.mapsets -p
    t.vect.univar input=gauges column=discharge 2>&1 | grep ERROR || true
    ```

    ```text
    t_vect_univar_2 PERMANENT t_vect_univar
    ERROR: Space time vector dataset <gauges@t_vect_univar_2> not found
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    tools.g_mapset(mapset="t_vect_univar_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.g_mapsets(mapset="t_vect_univar", operation="add")
    result = tools.t_vect_univar(
        input="gauges@t_vect_univar", column="discharge", twhere="start_time < '2026-03-02'"
    )
    print_columns(result)
    ```

    ```text
    id|n|nmissing|nnull|min|max|range
    gauges_1@t_vect_univar|4|0|0|1|4|3
    ```

    ```python
    print(tools.g_mapsets(flags="p").text)
    try:
        tools.t_vect_univar(input="gauges", column="discharge")
    except ToolError as error:
        print([line for line in error.stderr.splitlines() if "ERROR" in line][0])
    ```

    ```text
    t_vect_univar_2 PERMANENT t_vect_univar
    ERROR: Space time vector dataset <gauges@t_vect_univar_2> not found
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.mapsets](g.mapsets.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.univar](t.rast.univar.md), [t.rast3d.univar](t.rast3d.univar.md),
[t.register](t.register.md), [t.vect.list](t.vect.list.md),
[v.univar](v.univar.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
