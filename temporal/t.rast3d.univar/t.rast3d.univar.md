## DESCRIPTION

*t.rast3d.univar* calculates univariate statistics of each 3D raster map
registered in a space time 3D raster dataset and prints one line of statistics
per map, ordered by start time. It runs *[r3.univar](r3.univar.md)* for every
map, so the statistics are those of *r3.univar*: they are taken from the cells
(voxels) of the current 3D computational region and count only cells with a
value (non-null cells). See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. Space time raster datasets have their own tool,
*[t.rast.univar](t.rast.univar.md)*, space time vector datasets
*[t.vect.univar](t.vect.univar.md)*. Its manual page explains the statistics
for 2D maps in the same words; this page differs in the options that
*t.rast3d.univar* does not have, in the 3D region, and in the zones.

The option **input** names the space time 3D raster dataset. Each line of the
output starts with three columns that name the map:

- `id`, the name of the map with its mapset, such as `temperature_profile_2020_01@t_rast3d_univar`;
- `start` and `end`, the start and end time of the map; the end of a map
  registered as a time instance is `None`.

The statistics follow:

- `non_null_cells` and `null_cells`: the number of cells with and without a
  value;
- `min`, `max` and `range`, the smallest and the largest value and their
  difference;
- `mean` and `mean_of_abs`, the mean of the values and the mean of their
  absolute values;
- `stddev` and `variance`: the variance is the sum of the squared deviations
  from the mean divided by the number of non-null cells (the population
  variance), the standard deviation is its square root;
- `coeff_var`, the coefficient of variation in percent, 100 times the
  standard deviation divided by the mean. It grows without bound when the mean
  approaches 0, and it is negative for a negative mean;
- `sum` and `sum_abs`, the sum of the values and of their absolute values.

The flag **-e** adds the extended statistics `first_quartile`, `median`,
`third_quartile` and the 90th percentile `percentile_90`. *r3.univar* finds a
percentile p in the sorted values of the n non-null cells: it takes the value
at position `n * p / 100 - 0.5` with the fractional part dropped, counting
from 0, so the percentile 0 is the minimum. The quartiles follow the same rule
with p = 25 and p = 75. The median is the middle value,
or the mean of the two middle values when n is even, so it can differ from
the 50th percentile. The option **percentile** replaces the 90th percentile by
one or more percentiles from 0 to 100, separated by commas; it requires
**-e**. Each percentile gets a column of its own, named after it, with an
underscore for a decimal point: `percentile=97.5` gives `percentile_97_5`.

Two options select the maps of the dataset, and they can be combined:

- the option **where** takes an SQL condition on the registered maps, for
  instance on `start_time` or `name`;
- the option **region_relation** keeps the maps that have a spatial relation
  with the current 3D computational region: `overlaps` keeps the maps that
  share at least a part of the region, `contains` the maps that cover the
  whole region, and `is_contained` the maps that lie inside the region. A map
  with the extent of the region both contains it and is contained in it. The
  option only selects maps; it does not change the cells the statistics are
  taken from.

The statistics of every map are taken in the current 3D computational region:
cells of the map outside the region are not counted, and cells of the region
outside the map are null cells. Unlike *t.rast.univar*, *t.rast3d.univar* has
no flag to take the statistics in the region of each map instead.

The option **zones** names a 3D raster map whose integer values divide the
region into zones. *t.rast3d.univar* then prints one line per map and zone,
with the columns `zone` (the value) and `label` (the category label of the
zone, empty in the example below, where the zone map has none) after the three
columns of the map. **zones** takes a single 3D raster map, not a space time
dataset; the same zones apply to every map.

The option **nprocs** sets the number of maps that are processed at the same
time. Its default is the variable `NPROCS` of the session, if it is set with
*g.gisenv*, and 0 otherwise. 0 uses all CPU cores, a negative number leaves
that many cores unused. The output is the same, in the same order, for any value.

The option **format** chooses the form of the output:

- `plain` (the default) separates the columns with a vertical bar `|`;
- `csv` separates them with a comma, or with another single character given
  in **separator**;
- `json` prints a list with one object per map, or with **zones** one per
  map and zone. The keys are the column names, except where they follow
  *r3.univar*: `n` instead of `non_null_cells`, `zone_label` instead of
  `label`, the additional key `cells` for the number of all cells, and no
  `sum_abs`. With **-e**, the percentiles are the list `percentiles` of
  objects with the keys `percentile` and `value`, instead of the columns
  `percentile_90` and so on. A value that does not exist is `null`. Every
  object has the key `semantic_label`, which is `null` for 3D maps; the formats
  `plain` and `csv` have no such column.

The option **separator** sets the separator of the formats `plain` and `csv`.
The flag **-s** leaves out the line with the column names; it takes the place
of the flag **-u** of *t.rast.univar*. The format `json` always names the
values and accepts neither **separator** nor **-s**.

The option **output** writes the statistics to a file instead of the standard
output; `output=-` is the standard output. An existing file is replaced only
with **--overwrite**.

## NOTES

The current 3D computational region decides which cells are counted, so it
needs a vertical extent and a 3D resolution (the options **t**, **b** and
**res3** of *g.region*). A map that does not reach into the region has only
null cells there; its `min`, `max` and all further statistics are `nan` in the
formats `plain` and `csv` and `null` in the format `json`. A map that lies
above or below the region counts as outside, too. The region is the same for
all maps, so maps with different extents can have different numbers of
non-null cells, as the example with the cubes below shows.

In a dataset with relative time, `start` and `end` are numbers of the time
unit of the dataset, printed without the unit: a map registered from 0 to 6
hours shows `0` and `6`, as the first example shows.

*t.rast3d.univar* only reads, so it works on a dataset of another mapset as
well. The name with the mapset (`input=temperature_profile@t_rast3d_univar`)
selects it; a name without a mapset is searched in the mapsets of the search
path (see *[g.mapsets](g.mapsets.md)*). The last example shows this.

The 3D raster mask set with *[r3.mask](r3.mask.md)* has no effect on the
statistics: *r3.univar* does not read it and counts the cells that the mask
would exclude. To leave cells out, set them to null in the maps themselves, for
instance with *[r3.mapcalc](r3.mapcalc.md)* and `if(layers == 2, null(), temperature_profile_2020_07)`,
or read the lines of the zones that are wanted (see **zones** and the example
with the layers).

If no map is selected, for instance because the condition in **where**
matches none, *t.rast3d.univar* prints nothing in the formats `plain` and
`csv`, not even the line with the column names. The format `json` prints an
empty list `[]`.

The option **zones** also takes a floating point map. *r3.univar* then rounds
each value to the nearest integer, halves away from zero, instead of
refusing the map, so the zone of the value 2.5 is 3.

The format `csv` refuses a separator of more than one character, the format
`json` refuses **separator** and **-s**. **percentile** without **-e** is
refused by the parser.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast3d_univar` and sets the 3D computational
region to North Carolina with cells of 1 km and three layers of 1000 m, from 0
to 3000 m; the later examples work in this mapset and region, except the cubes,
which set a region of their own, and the last, which creates a second mapset. The
horizontal resolution `res` alone leaves the 3D resolution at the 500 m of the
elevation model, so the region sets **res3** as well.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast3d_univar -->

<!-- markdownlint-disable MD046 -->

### Statistics of each map of a dataset

The dataset `temperature_profile` holds twelve 3D maps of the monthly mean air
temperature in 2020 in whole degrees Celsius. They are generated, not
measured: the temperature follows a yearly cycle with its maximum in July,
falls by 0.0065 degrees per meter of height (`z()` is the height of the centre
of a layer: 500, 1500 and 2500 m) and by 0.01 degrees per kilometer to the
north. `round()` in *r3.mapcalc* rounds the values to whole degrees, which
keeps the mean, the variance and the sums the same on every platform. Each map
covers all 839 \* 335 \* 3 = 843,195 cells of the region, so no cell is null.
The maps are registered as intervals of one month, starting on 1 January 2020.
*t.rast3d.univar* processes two maps at the same time here (**nprocs**); the
output does not depend on it. The condition in **where** keeps the first three
months.

The second block makes the dataset `model` with relative time: two model
steps of 6 hours each, with the constant values 1 and 2. Their `start` and
`end` are numbers of hours, printed without the unit.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast3d_univar
    g.region raster=elev_state_500m res=1000 res3=1000 t=3000 b=0 tbres=1000 -a
    for month in $(seq 12); do
        echo "temperature_profile_2020_$(printf %02d $month) = round(16.5" \
            "+ 10.5 * cos(30 * ($month - 7.2)) - 0.0065 * z()" \
            "- 0.00001 * (y() - 160000))"
    done | r3.mapcalc file=-
    t.create type=str3ds output=temperature_profile title="Air temperature" \
        description="Monthly mean air temperature 2020 in degree Celsius, 0 to 3000 m"
    t.register -i type=raster_3d input=temperature_profile \
        maps=$(g.list type=raster_3d pattern="temperature_profile_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    t.rast3d.univar input=temperature_profile nprocs=2 \
        where="start_time < '2020-04-01'"
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_profile_2020_01@t_rast3d_univar|2020-01-01 00:00:00|2020-02-01 00:00:00|843195|0|-12|5|17|-3.61492537313433|5.53134328358209|5.4020427423754|29.1820657904507|-149.437185689163|-3048087|4664001
    temperature_profile_2020_02@t_rast3d_univar|2020-02-01 00:00:00|2020-03-01 00:00:00|843195|0|-11|5|16|-2.76318407960199|5.24278606965174|5.40127475380717|29.1737689661147|-195.472852991581|-2329903|4420691
    temperature_profile_2020_03@t_rast3d_univar|2020-03-01 00:00:00|2020-04-01 00:00:00|843195|0|-8|9|17|0.680597014925373|4.65074626865672|5.40024613791268|29.1626583500408|793.457217631907|573876|3921486
    ```

    ```sh
    r3.mapcalc expression="model_step_1 = 1"
    r3.mapcalc expression="model_step_2 = 2"
    t.create type=str3ds output=model temporaltype=relative title="Model" \
        description="Model output per step of 6 hours"
    t.register -i type=raster_3d input=model maps=model_step_1,model_step_2 \
        start=0 increment=6 unit=hours
    t.rast3d.univar input=model
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    model_step_1@t_rast3d_univar|0|6|843195|0|1|1|0|1|1|0|0|0|843195|843195
    model_step_2@t_rast3d_univar|6|12|843195|0|2|2|0|2|2|0|0|0|1686390|1686390
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast3d_univar")
    tools.g_region(
        raster="elev_state_500m",
        res=1000,
        res3=1000,
        t=3000,
        b=0,
        tbres=1000,
        flags="a",
    )
    months = range(1, 13)
    tools.r3_mapcalc(
        expression="\n".join(
            f"temperature_profile_2020_{month:02d} = round(16.5"
            f" + 10.5 * cos(30 * ({month} - 7.2)) - 0.0065 * z()"
            " - 0.00001 * (y() - 160000))"
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
    result = tools.t_rast3d_univar(
        input="temperature_profile", nprocs=2, where="start_time < '2020-04-01'"
    )
    print(result.text)
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_profile_2020_01@t_rast3d_univar|2020-01-01 00:00:00|2020-02-01 00:00:00|843195|0|-12|5|17|-3.61492537313433|5.53134328358209|5.4020427423754|29.1820657904507|-149.437185689163|-3048087|4664001
    temperature_profile_2020_02@t_rast3d_univar|2020-02-01 00:00:00|2020-03-01 00:00:00|843195|0|-11|5|16|-2.76318407960199|5.24278606965174|5.40127475380717|29.1737689661147|-195.472852991581|-2329903|4420691
    temperature_profile_2020_03@t_rast3d_univar|2020-03-01 00:00:00|2020-04-01 00:00:00|843195|0|-8|9|17|0.680597014925373|4.65074626865672|5.40024613791268|29.1626583500408|793.457217631907|573876|3921486
    ```

    ```python
    tools.r3_mapcalc(expression="model_step_1 = 1")
    tools.r3_mapcalc(expression="model_step_2 = 2")
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
        maps="model_step_1,model_step_2",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    print(tools.t_rast3d_univar(input="model").text)
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    model_step_1@t_rast3d_univar|0|6|843195|0|1|1|0|1|1|0|0|0|843195|843195
    model_step_2@t_rast3d_univar|6|12|843195|0|2|2|0|2|2|0|0|0|1686390|1686390
    ```

### Calculate extended statistics and percentiles

The flag **-e** adds the quartiles, the median and the 90th percentile. The
first command takes the July map of `temperature_profile`, which has an odd
number of cells. The first quartile is at position
`843195 * 25 / 100 - 0.5` = 210798.25, which becomes 210798 (the value 12), the
third quartile at position 632395.75, which becomes 632395 (the value 23). The
option **percentile** replaces the 90th percentile by the listed ones: the
10th percentile is at position 84319 (the value 10), the 95th at position
801034.75, which becomes 801034 (the value 25). The 50th percentile and the
median are both the middle value 17, at position 421597: with an odd number of
cells, the median is a value of the map, too.

The second command takes the statistics in the lower two layers only, by
setting the top of the region to 2000 m: the 281,065 cells of the upper layer
are not counted, `non_null_cells` is 562,130, and the number of cells is even.
The lower layer holds the values 22 to 25 and the middle layer 16 to 19, as the
zones below show. The two middle values, at the positions 281064 and 281065,
are 19 and 22, so the median is their mean 20.5, while the 50th percentile is
the value 19 at position 281064. The median is not even a value that occurs in
the map. The third command resets the region and takes the December map, with
the default percentile.

=== "Command line"

    ```sh
    t.rast3d.univar -e input=temperature_profile percentile=10,50,95 \
        where="name = 'temperature_profile_2020_07'"
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_10|percentile_50|percentile_95
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|843195|0|9|25|16|17.2636815920398|17.2636815920398|5.40085900465552|29.1692779881686|31.284514695555|14556650|14556650|12|17|23|10|17|25
    ```

    ```sh
    g.region t=2000
    t.rast3d.univar -e input=temperature_profile percentile=10,50,95 \
        where="name = 'temperature_profile_2020_07'"
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_10|percentile_50|percentile_95
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|562130|0|16|25|9|20.5223880597015|20.5223880597015|3.37620386027356|11.3987525061261|16.4513206282421|11536250|11536250|17|20.5|24|16|19|25
    ```

    ```sh
    g.region t=3000
    t.rast3d.univar -e input=temperature_profile where="start_time >= '2020-12-01'"
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_90
    temperature_profile_2020_12@t_rast3d_univar|2020-12-01 00:00:00|2021-01-01 00:00:00|843195|0|-10|7|17|-1.66965174129353|4.87960199004975|5.40060107011404|29.1664919185169|-323.456738704684|-1407842|4114456|-7|-2|4|6
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast3d_univar(
        input="temperature_profile",
        percentile=[10, 50, 95],
        where="name = 'temperature_profile_2020_07'",
        flags="e",
    )
    print(result.text)
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_10|percentile_50|percentile_95
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|843195|0|9|25|16|17.2636815920398|17.2636815920398|5.40085900465552|29.1692779881686|31.284514695555|14556650|14556650|12|17|23|10|17|25
    ```

    ```python
    tools.g_region(t=2000)
    result = tools.t_rast3d_univar(
        input="temperature_profile",
        percentile=[10, 50, 95],
        where="name = 'temperature_profile_2020_07'",
        flags="e",
    )
    print(result.text)
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_10|percentile_50|percentile_95
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|562130|0|16|25|9|20.5223880597015|20.5223880597015|3.37620386027356|11.3987525061261|16.4513206282421|11536250|11536250|17|20.5|24|16|19|25
    ```

    ```python
    tools.g_region(t=3000)
    result = tools.t_rast3d_univar(
        input="temperature_profile", where="start_time >= '2020-12-01'", flags="e"
    )
    print(result.text)
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_90
    temperature_profile_2020_12@t_rast3d_univar|2020-12-01 00:00:00|2021-01-01 00:00:00|843195|0|-10|7|17|-1.66965174129353|4.87960199004975|5.40060107011404|29.1664919185169|-323.456738704684|-1407842|4114456|-7|-2|4|6
    ```

### Statistics per zone

The 3D map `layers` holds the number of the layer: 1 in the lower layer
(0 to 1000 m), 2 in the middle and 3 in the upper layer. With **zones**, each
map gets one line per zone. Every zone has 839 \* 335 = 281,065 cells. In July,
the mean falls by about 6.5 degrees from layer to layer, as the assumed
0.0065 degrees per meter say, and the layers do not overlap: the lower layer
holds 22 to 25, the middle layer 16 to 19 and the upper layer 9 to 12. The zone
map has no category labels, so `label` is empty. With **format** `json`, each
zone is an object of its own, and the category label has the name
`zone_label`; it is the empty text here, not `null`.

=== "Command line"

    ```sh
    r3.mapcalc expression="layers = depth()"
    t.rast3d.univar input=temperature_profile zones=layers \
        where="name = 'temperature_profile_2020_07'"
    ```

    ```text
    id|start|end|zone|label|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|1||281065|0|22|25|3|23.7462686567164|23.7462686567164|0.997658206989149|0.995321897972803|4.20132620165135|6674245|6674245
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|2||281065|0|16|19|3|17.2985074626866|17.2985074626866|1.00765614505185|1.01537090666075|5.82510454861724|4862005|4862005
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|3||281065|0|9|12|3|10.7462686567164|10.7462686567164|0.997658206989156|0.995321897972817|9.28376387059353|3020400|3020400
    ```

    ```sh
    t.rast3d.univar input=temperature_profile zones=layers format=json \
        where="name = 'temperature_profile_2020_07'" | grep -E '"(zone|zone_label|mean)"'
    ```

    ```text
            "zone": 1,
            "zone_label": "",
            "mean": 23.746268656716417,
            "zone": 2,
            "zone_label": "",
            "mean": 17.29850746268657,
            "zone": 3,
            "zone_label": "",
            "mean": 10.746268656716419,
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(expression="layers = depth()")
    result = tools.t_rast3d_univar(
        input="temperature_profile",
        zones="layers",
        where="name = 'temperature_profile_2020_07'",
    )
    print(result.text)
    ```

    ```text
    id|start|end|zone|label|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|1||281065|0|22|25|3|23.7462686567164|23.7462686567164|0.997658206989149|0.995321897972803|4.20132620165135|6674245|6674245
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|2||281065|0|16|19|3|17.2985074626866|17.2985074626866|1.00765614505185|1.01537090666075|5.82510454861724|4862005|4862005
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|3||281065|0|9|12|3|10.7462686567164|10.7462686567164|0.997658206989156|0.995321897972817|9.28376387059353|3020400|3020400
    ```

    ```python
    result = tools.t_rast3d_univar(
        input="temperature_profile",
        zones="layers",
        format="json",
        where="name = 'temperature_profile_2020_07'",
    )
    for stats in result.json:
        print(f"zone {stats['zone']} ({stats['zone_label']!r}): mean {stats['mean']}")
    ```

    ```text
    zone 1 (''): mean 23.746268656716417
    zone 2 (''): mean 17.29850746268657
    zone 3 (''): mean 10.746268656716419
    ```

### Choose the output format

The option **separator** sets another separator, and the flag **-s** leaves
out the line with the column names, for instance to append the lines to a
table that has them already. With **format** `csv`, the columns are separated
by commas, and the option **output** writes the statistics to a file. These
commands show the first two months. With **format** `json`,
*t.rast3d.univar* prints a list with one object per map; here for the July
map with the extended statistics and two percentiles. The key `semantic_label`
is `null`. In Python, the attribute `json` of the result holds this list, and
the example prints the mean, the median and the percentiles from it.

=== "Command line"

    ```sh
    t.rast3d.univar -s input=temperature_profile separator=";" \
        where="start_time < '2020-03-01'"
    ```

    ```text
    temperature_profile_2020_01@t_rast3d_univar;2020-01-01 00:00:00;2020-02-01 00:00:00;843195;0;-12;5;17;-3.61492537313433;5.53134328358209;5.4020427423754;29.1820657904507;-149.437185689163;-3048087;4664001
    temperature_profile_2020_02@t_rast3d_univar;2020-02-01 00:00:00;2020-03-01 00:00:00;843195;0;-11;5;16;-2.76318407960199;5.24278606965174;5.40127475380717;29.1737689661147;-195.472852991581;-2329903;4420691
    ```

    ```sh
    t.rast3d.univar input=temperature_profile format=csv output=profile.csv \
        where="start_time < '2020-03-01'"
    cat profile.csv
    ```

    ```text
    id,start,end,non_null_cells,null_cells,min,max,range,mean,mean_of_abs,stddev,variance,coeff_var,sum,sum_abs
    temperature_profile_2020_01@t_rast3d_univar,2020-01-01 00:00:00,2020-02-01 00:00:00,843195,0,-12,5,17,-3.61492537313433,5.53134328358209,5.4020427423754,29.1820657904507,-149.437185689163,-3048087,4664001
    temperature_profile_2020_02@t_rast3d_univar,2020-02-01 00:00:00,2020-03-01 00:00:00,843195,0,-11,5,16,-2.76318407960199,5.24278606965174,5.40127475380717,29.1737689661147,-195.472852991581,-2329903,4420691
    ```

    ```sh
    t.rast3d.univar -e input=temperature_profile format=json percentile=50,90 \
        where="name = 'temperature_profile_2020_07'"
    ```

    ```text
    [
        {
            "id": "temperature_profile_2020_07@t_rast3d_univar",
            "semantic_label": null,
            "start": "2020-07-01 00:00:00",
            "end": "2020-08-01 00:00:00",
            "n": 843195,
            "null_cells": 0,
            "cells": 843195,
            "min": 9,
            "max": 25,
            "range": 16,
            "mean": 17.263681592039802,
            "mean_of_abs": 17.263681592039802,
            "stddev": 5.400859004655521,
            "variance": 29.169277988168627,
            "coeff_var": 31.284514695555032,
            "sum": 14556650,
            "first_quartile": 12,
            "median": 17,
            "third_quartile": 23,
            "percentiles": [
                {
                    "percentile": 50,
                    "value": 17
                },
                {
                    "percentile": 90,
                    "value": 24
                }
            ]
        }
    ]
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast3d_univar(
        input="temperature_profile",
        separator=";",
        where="start_time < '2020-03-01'",
        flags="s",
    )
    print(result.text)
    ```

    ```text
    temperature_profile_2020_01@t_rast3d_univar;2020-01-01 00:00:00;2020-02-01 00:00:00;843195;0;-12;5;17;-3.61492537313433;5.53134328358209;5.4020427423754;29.1820657904507;-149.437185689163;-3048087;4664001
    temperature_profile_2020_02@t_rast3d_univar;2020-02-01 00:00:00;2020-03-01 00:00:00;843195;0;-11;5;16;-2.76318407960199;5.24278606965174;5.40127475380717;29.1737689661147;-195.472852991581;-2329903;4420691
    ```

    ```python
    from pathlib import Path

    tools.t_rast3d_univar(
        input="temperature_profile",
        format="csv",
        output="profile.csv",
        where="start_time < '2020-03-01'",
    )
    print(Path("profile.csv").read_text(), end="")
    ```

    ```text
    id,start,end,non_null_cells,null_cells,min,max,range,mean,mean_of_abs,stddev,variance,coeff_var,sum,sum_abs
    temperature_profile_2020_01@t_rast3d_univar,2020-01-01 00:00:00,2020-02-01 00:00:00,843195,0,-12,5,17,-3.61492537313433,5.53134328358209,5.4020427423754,29.1820657904507,-149.437185689163,-3048087,4664001
    temperature_profile_2020_02@t_rast3d_univar,2020-02-01 00:00:00,2020-03-01 00:00:00,843195,0,-11,5,16,-2.76318407960199,5.24278606965174,5.40127475380717,29.1737689661147,-195.472852991581,-2329903,4420691
    ```

    ```python
    result = tools.t_rast3d_univar(
        input="temperature_profile",
        format="json",
        percentile=[50, 90],
        where="name = 'temperature_profile_2020_07'",
        flags="e",
    )
    for stats in result.json:
        percentiles = {item["percentile"]: item["value"] for item in stats["percentiles"]}
        print(
            f"{stats['id']}: mean {stats['mean']}, median {stats['median']},"
            f" percentiles {percentiles}"
        )
    ```

    ```text
    temperature_profile_2020_07@t_rast3d_univar: mean 17.263681592039802, median 17, percentiles {50: 17, 90: 24}
    ```

### Maps with extents of their own

The dataset `cubes` holds four maps with constant values on cubes of their
own. The current region is the cube with 64 cells from (200000, 100000, 0) to
(204000, 104000, 4000), with cells of 1000 m. Each cube is set with *g.region*,
in kilometers from the corner of this region, the same in all three directions:

- `cube_1` covers the cube from (-1, -1, -1) to (5, 5, 5) and so the whole
  region;
- `cube_2` lies inside the region, from (1, 1, 1) to (3, 3, 3);
- `cube_3` reaches from (2, 2, 2) to (6, 6, 6) and shares 8 cells with the
  region;
- `cube_4` lies outside, from (10, 10, 10) to (12, 12, 12).

The commands print the columns `id`, `non_null_cells`, `null_cells` and `min`
only: on the command line, *cut* keeps the first, fourth, fifth and sixth
column; in Python, the function `print_columns()` picks them from the plain
text.

1. By default, the cells are counted in the current region: `cube_1` has 64
   non-null cells there, `cube_2` and `cube_3` have 8, and `cube_4` none. As
   `cube_4` has no value in the region, its `min` is `nan`.
2. **region_relation** selects maps by their relation to the current region:
   `overlaps` keeps all but `cube_4`, `contains` only `cube_1`, which covers
   the region, and `is_contained` only `cube_2`, which lies inside it.
3. **region_relation** and **where** work together: of the maps that overlap
   the region, the condition keeps those that start on 2 July 2026 or later.
4. With **format** `json`, the statistics of `cube_4` that do not exist are
   `null`.

=== "Command line"

    ```sh
    for cube in "cube_1 -1 5 10" "cube_2 1 3 20" \
        "cube_3 2 6 30" "cube_4 10 12 40"; do
        set -- $cube
        g.region w=$((200000 + $2 * 1000)) e=$((200000 + $3 * 1000)) \
            s=$((100000 + $2 * 1000)) n=$((100000 + $3 * 1000)) \
            b=$(($2 * 1000)) t=$(($3 * 1000)) res=1000 res3=1000
        r3.mapcalc expression="$1 = $4"
    done
    t.create type=str3ds output=cubes title="Cubes" \
        description="Cubes with extents of their own"
    t.register -i type=raster_3d input=cubes \
        maps=cube_1,cube_2,cube_3,cube_4 start=2026-07-01 increment="1 day"
    g.region w=200000 e=204000 s=100000 n=104000 b=0 t=4000 res=1000 res3=1000
    t.rast3d.univar input=cubes | cut -d"|" -f1,4-6
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@t_rast3d_univar|64|0|10
    cube_2@t_rast3d_univar|8|56|20
    cube_3@t_rast3d_univar|8|56|30
    cube_4@t_rast3d_univar|0|64|nan
    ```

    ```sh
    t.rast3d.univar input=cubes region_relation=overlaps | cut -d"|" -f1,4-6
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@t_rast3d_univar|64|0|10
    cube_2@t_rast3d_univar|8|56|20
    cube_3@t_rast3d_univar|8|56|30
    ```

    ```sh
    t.rast3d.univar input=cubes region_relation=contains | cut -d"|" -f1,4-6
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@t_rast3d_univar|64|0|10
    ```

    ```sh
    t.rast3d.univar input=cubes region_relation=is_contained | cut -d"|" -f1,4-6
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_2@t_rast3d_univar|8|56|20
    ```

    ```sh
    t.rast3d.univar input=cubes region_relation=overlaps \
        where="start_time >= '2026-07-02'" | cut -d"|" -f1,4-6
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_2@t_rast3d_univar|8|56|20
    cube_3@t_rast3d_univar|8|56|30
    ```

    ```sh
    t.rast3d.univar input=cubes format=json where="name = 'cube_4'" |
        grep -E '"(n|null_cells|min|mean)"'
    ```

    ```text
            "n": 0,
            "null_cells": 64,
            "min": null,
            "mean": null,
    ```

=== "Python (grass.tools)"

    ```python
    for name, low, high, value in (
        ("cube_1", -1, 5, 10),
        ("cube_2", 1, 3, 20),
        ("cube_3", 2, 6, 30),
        ("cube_4", 10, 12, 40),
    ):
        tools.g_region(
            w=200000 + low * 1000,
            e=200000 + high * 1000,
            s=100000 + low * 1000,
            n=100000 + high * 1000,
            b=low * 1000,
            t=high * 1000,
            res=1000,
            res3=1000,
        )
        tools.r3_mapcalc(expression=f"{name} = {value}")
    tools.t_create(
        type="str3ds",
        output="cubes",
        title="Cubes",
        description="Cubes with extents of their own",
    )
    tools.t_register(
        type="raster_3d",
        input="cubes",
        maps="cube_1,cube_2,cube_3,cube_4",
        start="2026-07-01",
        increment="1 day",
        flags="i",
    )
    tools.g_region(w=200000, e=204000, s=100000, n=104000, b=0, t=4000, res=1000, res3=1000)


    def print_columns(result):
        for line in result.text.splitlines():
            columns = line.split("|")
            print("|".join(columns[index] for index in (0, 3, 4, 5)))


    print_columns(tools.t_rast3d_univar(input="cubes"))
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@t_rast3d_univar|64|0|10
    cube_2@t_rast3d_univar|8|56|20
    cube_3@t_rast3d_univar|8|56|30
    cube_4@t_rast3d_univar|0|64|nan
    ```

    ```python
    print_columns(tools.t_rast3d_univar(input="cubes", region_relation="overlaps"))
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@t_rast3d_univar|64|0|10
    cube_2@t_rast3d_univar|8|56|20
    cube_3@t_rast3d_univar|8|56|30
    ```

    ```python
    print_columns(tools.t_rast3d_univar(input="cubes", region_relation="contains"))
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@t_rast3d_univar|64|0|10
    ```

    ```python
    print_columns(tools.t_rast3d_univar(input="cubes", region_relation="is_contained"))
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_2@t_rast3d_univar|8|56|20
    ```

    ```python
    result = tools.t_rast3d_univar(
        input="cubes", region_relation="overlaps", where="start_time >= '2026-07-02'"
    )
    print_columns(result)
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_2@t_rast3d_univar|8|56|20
    cube_3@t_rast3d_univar|8|56|30
    ```

    ```python
    result = tools.t_rast3d_univar(input="cubes", format="json", where="name = 'cube_4'")
    for stats in result.json:
        print(
            f"n: {stats['n']}, null_cells: {stats['null_cells']},"
            f" min: {stats['min']}, mean: {stats['mean']}"
        )
    ```

    ```text
    n: 0, null_cells: 64, min: None, mean: None
    ```

### Use a dataset of another mapset

*t.rast3d.univar* reads a dataset of another mapset. The example creates the
mapset `t_rast3d_univar_2` and switches to it; the dataset `temperature_profile`
stays in the mapset `t_rast3d_univar` and is named with its mapset. The region
of the new mapset is set like the one of the first example, and *g.mapsets* adds
`t_rast3d_univar` to the search path. In the second block, *g.mapsets* shows
the search path, and the name `temperature_profile` without a mapset finds the
same dataset. The mapset is added only for the second block, which names the
dataset without its mapset; the first block works without it (see
[Datasets of other mapsets](temporalintro.md#datasets-of-other-mapsets)).

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast3d_univar_2
    g.region raster=elev_state_500m res=1000 res3=1000 t=3000 b=0 tbres=1000 -a
    g.mapsets mapset=t_rast3d_univar operation=add
    t.rast3d.univar input=temperature_profile@t_rast3d_univar \
        where="name = 'temperature_profile_2020_07'"
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|843195|0|9|25|16|17.2636815920398|17.2636815920398|5.40085900465552|29.1692779881686|31.284514695555|14556650|14556650
    ```

    ```sh
    g.mapsets -p
    t.rast3d.univar input=temperature_profile \
        where="name = 'temperature_profile_2020_07'"
    ```

    ```text
    t_rast3d_univar_2 PERMANENT t_rast3d_univar
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|843195|0|9|25|16|17.2636815920398|17.2636815920398|5.40085900465552|29.1692779881686|31.284514695555|14556650|14556650
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(flags="c", mapset="t_rast3d_univar_2")
    tools.g_region(
        raster="elev_state_500m",
        res=1000,
        res3=1000,
        t=3000,
        b=0,
        tbres=1000,
        flags="a",
    )
    tools.g_mapsets(mapset="t_rast3d_univar", operation="add")
    result = tools.t_rast3d_univar(
        input="temperature_profile@t_rast3d_univar",
        where="name = 'temperature_profile_2020_07'",
    )
    print(result.text)
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|843195|0|9|25|16|17.2636815920398|17.2636815920398|5.40085900465552|29.1692779881686|31.284514695555|14556650|14556650
    ```

    ```python
    print(tools.g_mapsets(flags="p").text)
    result = tools.t_rast3d_univar(
        input="temperature_profile", where="name = 'temperature_profile_2020_07'"
    )
    print(result.text)
    ```

    ```text
    t_rast3d_univar_2 PERMANENT t_rast3d_univar
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_profile_2020_07@t_rast3d_univar|2020-07-01 00:00:00|2020-08-01 00:00:00|843195|0|9|25|16|17.2636815920398|17.2636815920398|5.40085900465552|29.1692779881686|31.284514695555|14556650|14556650
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.gisenv](g.gisenv.md), [g.mapsets](g.mapsets.md), [g.region](g.region.md),
[r3.mapcalc](r3.mapcalc.md), [r3.mask](r3.mask.md),
[r3.univar](r3.univar.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.univar](t.rast.univar.md), [t.register](t.register.md),
[t.vect.univar](t.vect.univar.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture  
Stefan Blumentrath (support for zones)
