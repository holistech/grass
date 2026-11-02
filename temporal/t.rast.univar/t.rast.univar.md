## DESCRIPTION

*t.rast.univar* calculates univariate statistics of each raster map
registered in a space time raster dataset and prints one line of statistics
per map, ordered by start time. It runs *[r.univar](r.univar.md)* for every
map, so the statistics are those of *r.univar*: they are taken from the cells
of the current computational region and count only cells with a value
(non-null cells). See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. Space time 3D raster datasets have their own tool,
*[t.rast3d.univar](t.rast3d.univar.md)*, space time vector datasets
*[t.vect.univar](t.vect.univar.md)*.

The option **input** names the space time raster dataset. Each line of the
output starts with four columns that name the map:

- `id`, the name of the map with its mapset, such as
  `temperature_1@PERMANENT`;
- `semantic_label`, the semantic label of the map, empty if it has none;
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
`third_quartile` and the 90th percentile `percentile_90`. *r.univar* finds a
percentile p in the sorted values of the n non-null cells: it takes the value
at position `n * p / 100 - 0.5` with the fractional part dropped, counting
from 0, so the percentile 0 is the minimum. The quartiles follow the same rule
with p = 25 and p = 75. The median is the middle value,
or the mean of the two middle values when n is even, so it can differ from
the 50th percentile. The option **percentile** replaces the 90th percentile by
one or more percentiles from 0 to 100, separated by commas; it requires
**-e**. Each percentile gets a column of its own, named after it, with an
underscore for a decimal point: `percentile=97.5` gives `percentile_97_5`.

Three ways select the maps of the dataset, and they can be combined:

- the option **where** takes an SQL condition on the registered maps, for
  instance on `start_time` or `name`;
- a semantic label after the name of the dataset, `input=name.label`, keeps
  only the maps with this label;
- the option **region_relation** keeps the maps that have a spatial relation
  with the current computational region: `overlaps` keeps the maps that share
  at least a part of the region, `contains` the maps that cover the whole
  region, and `is_contained` the maps that lie inside the region. A map with
  the extent of the region both contains it and is contained in it. The
  option only selects maps; it does not change the cells the statistics are
  taken from.

Without the flag **-r**, the statistics of every map are taken in the current
computational region: cells of the map outside the region are not counted,
and cells of the region outside the map are null cells. With **-r**, the
statistics of each map are taken in the region of that map, so every cell of
the map is counted, whatever the current region. In this version, **-r** has
no effect together with **zones**: the statistics per zone are taken in the
current region.

The option **zones** names an integer (CELL) raster map whose categories
divide the region into zones. *t.rast.univar* then prints one line per map
and zone, with the columns `zone` (the category) and `label` (the category
label) after the four columns of the map. **zones** takes a single raster
map, not a space time dataset; the same zones apply to every map.

The option **nprocs** sets the number of maps that are processed at the same
time. Its default is the variable `NPROCS` of the session, if it is set with
*g.gisenv*, and 0 otherwise. 0 uses all CPU cores, a negative number leaves
that many cores unused. The output is the same, in the same order, for any value.

The option **format** chooses the form of the output:

- `plain` (the default) separates the columns with a vertical bar `|`;
- `csv` separates them with a comma, or with another single character given
  in **separator**;
- `json` prints a list with one object per map, or with **zones** one per
  map and zone, the category label under the name `zone_label`. The objects
  use the names of *r.univar*: `n` for the number of non-null cells, `cells`
  for the number of all cells, and the list `percentiles` for the
  percentiles. They have no
  `sum_abs`. A value that does not exist, such as the semantic label of a map
  without one, is `null`.

The option **separator** sets the separator of the formats `plain` and `csv`.
The flag **-u** leaves out the line with the column names. The format `json`
always names the values and accepts neither **separator** nor **-u**.

The option **output** writes the statistics to a file instead of the standard
output; `output=-` is the standard output. An existing file is replaced only
with **--overwrite**.

## NOTES

The current computational region decides which cells are counted, unless
**-r** is given. A map that does not reach into the region has only null
cells there; its `min` and `max` are `nan` in the formats `plain` and `csv`
and `null` in the format `json`. The raster mask is respected: cells outside
the mask are null cells. Region and mask are the same for all maps, so maps
with different extents can have different numbers of non-null cells, as the
example with the scenes below shows.

In a dataset with relative time, `start` and `end` are numbers of the time
unit of the dataset, printed without the unit: a map registered from 0 to 6
hours shows `0` and `6`, as the first example shows.

*t.rast.univar* only reads, so it works on a dataset of another mapset as
well. The name with the mapset (`input=temperature@PERMANENT`) selects it;
a name without a mapset is searched in the mapsets of the search path (see
*[g.mapsets](g.mapsets.md)*). The example at the end shows this.

If no map is selected, for instance because the condition in **where**
matches none, *t.rast.univar* prints nothing, not even the line with the
column names, in all formats. With the format `json`, the output is then
empty, not an empty list `[]`.

The option **zones** takes a map of type CELL; *t.rast.univar* stops with the
error "Zoning raster must be of type CELL" for a floating point map.

The format `csv` refuses a separator of more than one character, the format
`json` refuses **separator** and **-u**. **percentile** without **-e** is
refused by the parser.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Statistics of each map of a dataset

Three maps of daily mean air temperature on a small region of two rows and
three columns make up the dataset `temperature`. The helper map `cell_number`
numbers the cells from 1 to 6, row by row, so each map is simple to follow:

- `temperature_1` holds -2, -1, 0 in the northern row and 1, 2, 3 in the
  southern row;
- `temperature_2` holds 1, 2, 3 and 4, 5, 6;
- `temperature_3` holds 4, 5 and 7, 8, and nothing in the eastern column, as
  if a sensor had failed there.

The maps are registered as daily intervals starting on 1 March 2026.
*t.rast.univar* processes two maps at the same time here (**nprocs**); the
output does not depend on it.

The second block makes the dataset `model` with relative time: two model
steps of 6 hours each, with the constant values 1 and 2. Their `start` and
`end` are numbers of hours, printed without the unit.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    r.mapcalc expression="cell_number = 3 * (row() - 1) + col()"
    r.mapcalc expression="temperature_1 = cell_number - 3"
    r.mapcalc expression="temperature_2 = cell_number"
    r.mapcalc expression="temperature_3 = if(col() == 3, null(), cell_number + 3)"
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature in degrees Celsius"
    t.register -i input=temperature \
        maps=temperature_1,temperature_2,temperature_3 \
        start=2026-03-01 increment="1 day"
    t.rast.univar input=temperature nprocs=2
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_1@PERMANENT||2026-03-01 00:00:00|2026-03-02 00:00:00|6|0|-2|3|5|0.5|1.5|1.70782512765993|2.91666666666667|341.565025531987|3|9
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21
    temperature_3@PERMANENT||2026-03-03 00:00:00|2026-03-04 00:00:00|4|2|4|8|4|6|6|1.58113883008419|2.5|26.3523138347365|24|24
    ```

    ```sh
    r.mapcalc expression="step_1 = 1"
    r.mapcalc expression="step_2 = 2"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step of 6 hours"
    t.register -i input=model maps=step_1,step_2 start=0 increment=6 unit=hours
    t.rast.univar input=model
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    step_1@PERMANENT||0|6|6|0|1|1|0|1|1|0|0|0|6|6
    step_2@PERMANENT||6|12|6|0|2|2|0|2|2|0|0|0|12|12
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    tools.r_mapcalc(expression="cell_number = 3 * (row() - 1) + col()")
    tools.r_mapcalc(expression="temperature_1 = cell_number - 3")
    tools.r_mapcalc(expression="temperature_2 = cell_number")
    tools.r_mapcalc(expression="temperature_3 = if(col() == 3, null(), cell_number + 3)")
    tools.t_create(
        output="temperature",
        title="Air temperature",
        description="Daily mean air temperature in degrees Celsius",
    )
    tools.t_register(
        input="temperature",
        maps="temperature_1,temperature_2,temperature_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_rast_univar(input="temperature", nprocs=2).text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_1@PERMANENT||2026-03-01 00:00:00|2026-03-02 00:00:00|6|0|-2|3|5|0.5|1.5|1.70782512765993|2.91666666666667|341.565025531987|3|9
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21
    temperature_3@PERMANENT||2026-03-03 00:00:00|2026-03-04 00:00:00|4|2|4|8|4|6|6|1.58113883008419|2.5|26.3523138347365|24|24
    ```

    ```python
    tools.r_mapcalc(expression="step_1 = 1")
    tools.r_mapcalc(expression="step_2 = 2")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step of 6 hours",
    )
    tools.t_register(
        input="model",
        maps="step_1,step_2",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    print(tools.t_rast_univar(input="model").text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    step_1@PERMANENT||0|6|6|0|1|1|0|1|1|0|0|0|6|6
    step_2@PERMANENT||6|12|6|0|2|2|0|2|2|0|0|0|12|12
    ```

The output reads line by line:

- `temperature_2` has six values, 1 to 6: the mean is 21 / 6 = 3.5, the
  range 6 - 1 = 5. The squared deviations from the mean add up to 17.5, so
  the variance is 17.5 / 6 = 2.9166..., the standard deviation its square root
  1.7078..., and the coefficient of variation `100 * 1.7078 / 3.5` = 48.79...
- `temperature_1` holds the same values minus 3, so range, variance and
  standard deviation are those of `temperature_2`. Its values -2 to 3 add up to
  3 and give the mean 0.5, while their absolute values add up to 9 and give
  `mean_of_abs` 1.5. With a mean close to 0, the coefficient of variation
  becomes 341.6 and says little.
- `temperature_3` has four non-null cells and two null cells; its mean is
  (4 + 5 + 7 + 8) / 4 = 6.

The semantic label is empty, because the maps have none.

### Select maps by start time or semantic label

The option **where** takes an SQL condition on the registered maps. The first
command keeps the maps that start on 2 March 2026 or later.

The second command uses a dataset of satellite bands. A satellite takes the
bands of a scene at the same moment. The dataset `sentinel` holds the red band
(semantic label `S2_B4`) and the near infrared band (`S2_B8`) of two scenes as
maps with constant reflectance, registered as time instances, so their end
time is `None`. The name `sentinel.S2_B8` selects the near infrared band;
without the label, all four maps would be processed.

=== "Command line"

    ```sh
    t.rast.univar input=temperature where="start_time >= '2026-03-02'"
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21
    temperature_3@PERMANENT||2026-03-03 00:00:00|2026-03-04 00:00:00|4|2|4|8|4|6|6|1.58113883008419|2.5|26.3523138347365|24|24
    ```

    ```sh
    r.mapcalc expression="red_1 = 0.05"
    r.mapcalc expression="nir_1 = 0.30"
    r.mapcalc expression="red_2 = 0.07"
    r.mapcalc expression="nir_2 = 0.40"
    r.support map=red_1 semantic_label=S2_B4
    r.support map=red_2 semantic_label=S2_B4
    r.support map=nir_1 semantic_label=S2_B8
    r.support map=nir_2 semantic_label=S2_B8
    t.create output=sentinel title="Reflectance" \
        description="Red and near infrared reflectance of two scenes"
    t.register input=sentinel maps=red_1,nir_1 start="2026-06-01 10:30:00"
    t.register input=sentinel maps=red_2,nir_2 start="2026-06-11 10:30:00"
    t.rast.univar input=sentinel.S2_B8
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    nir_1@PERMANENT|S2_B8|2026-06-01 10:30:00|None|6|0|0.3|0.3|0|0.3|0.3|0|0|0|1.8|1.8
    nir_2@PERMANENT|S2_B8|2026-06-11 10:30:00|None|6|0|0.4|0.4|0|0.4|0.4|0|0|0|2.4|2.4
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_univar(input="temperature", where="start_time >= '2026-03-02'")
    print(result.text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21
    temperature_3@PERMANENT||2026-03-03 00:00:00|2026-03-04 00:00:00|4|2|4|8|4|6|6|1.58113883008419|2.5|26.3523138347365|24|24
    ```

    ```python
    for name, value, label in (
        ("red_1", 0.05, "S2_B4"),
        ("nir_1", 0.30, "S2_B8"),
        ("red_2", 0.07, "S2_B4"),
        ("nir_2", 0.40, "S2_B8"),
    ):
        tools.r_mapcalc(expression=f"{name} = {value:.2f}")
        tools.r_support(map=name, semantic_label=label)
    tools.t_create(
        output="sentinel",
        title="Reflectance",
        description="Red and near infrared reflectance of two scenes",
    )
    tools.t_register(input="sentinel", maps="red_1,nir_1", start="2026-06-01 10:30:00")
    tools.t_register(input="sentinel", maps="red_2,nir_2", start="2026-06-11 10:30:00")
    print(tools.t_rast_univar(input="sentinel.S2_B8").text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    nir_1@PERMANENT|S2_B8|2026-06-01 10:30:00|None|6|0|0.3|0.3|0|0.3|0.3|0|0|0|1.8|1.8
    nir_2@PERMANENT|S2_B8|2026-06-11 10:30:00|None|6|0|0.4|0.4|0|0.4|0.4|0|0|0|2.4|2.4
    ```

### Calculate extended statistics and percentiles

The flag **-e** adds the quartiles, the median and the 90th percentile. The
six values 1 to 6 of `temperature_2` give the first quartile at position
`6 * 25 / 100 - 0.5` = 1 (the value 2), the third quartile at position 4 (the
value 5), and the 90th percentile at position 4.9, which becomes 4 (the value
5). The median is the mean of the two middle values 3 and 4.

The option **percentile** replaces the 90th percentile by the listed ones.
For `temperature_2`, the 10th percentile is at position 0.1 (the value 1), the
50th at position 2.5 (the value 3) and the 95th at position 5.2 (the value 6).
The 50th percentile 3 is not the median 3.5: the median takes the mean of the
two middle values, the percentile one value.

=== "Command line"

    ```sh
    t.rast.univar -e input=temperature
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_90
    temperature_1@PERMANENT||2026-03-01 00:00:00|2026-03-02 00:00:00|6|0|-2|3|5|0.5|1.5|1.70782512765993|2.91666666666667|341.565025531987|3|9|-1|0.5|2|2
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21|2|3.5|5|5
    temperature_3@PERMANENT||2026-03-03 00:00:00|2026-03-04 00:00:00|4|2|4|8|4|6|6|1.58113883008419|2.5|26.3523138347365|24|24|4|6|7|8
    ```

    ```sh
    t.rast.univar -e input=temperature percentile=10,50,95 \
        where="name = 'temperature_2'"
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_10|percentile_50|percentile_95
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21|2|3.5|5|1|3|6
    ```

=== "Python (grass.tools)"

    ```python
    print(tools.t_rast_univar(input="temperature", flags="e").text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_90
    temperature_1@PERMANENT||2026-03-01 00:00:00|2026-03-02 00:00:00|6|0|-2|3|5|0.5|1.5|1.70782512765993|2.91666666666667|341.565025531987|3|9|-1|0.5|2|2
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21|2|3.5|5|5
    temperature_3@PERMANENT||2026-03-03 00:00:00|2026-03-04 00:00:00|4|2|4|8|4|6|6|1.58113883008419|2.5|26.3523138347365|24|24|4|6|7|8
    ```

    ```python
    result = tools.t_rast_univar(
        input="temperature",
        percentile=[10, 50, 95],
        where="name = 'temperature_2'",
        flags="e",
    )
    print(result.text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_10|percentile_50|percentile_95
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21|2|3.5|5|1|3|6
    ```

### Statistics per zone

The map `zones` divides the region into the northern row (category 1, label
`north`) and the southern row (category 2, label `south`). With **zones**,
each map gets one line per zone. In the northern row, `temperature_2` holds
1, 2 and 3 with the mean 2, in the southern row 4, 5 and 6 with the mean 5.
With **format** `json`, each zone is an object of its own, and the category
label has the name `zone_label`.

=== "Command line"

    ```sh
    r.mapcalc expression="zones = row()"
    r.category map=zones separator=":" rules=- <<EOF
    1:north
    2:south
    EOF
    t.rast.univar input=temperature zones=zones \
        where="name = 'temperature_2'"
    ```

    ```text
    id|semantic_label|start|end|zone|label|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|1|north|3|0|1|3|2|2|2|0.816496580927726|0.666666666666667|40.8248290463863|6|6
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|2|south|3|0|4|6|2|5|5|0.816496580927726|0.666666666666667|16.3299316185545|15|15
    ```

    ```sh
    t.rast.univar input=temperature zones=zones format=json \
        where="name = 'temperature_2'" | grep -E '"(zone|zone_label|mean)"'
    ```

    ```text
            "zone": 1,
            "zone_label": "north",
            "mean": 2,
            "zone": 2,
            "zone_label": "south",
            "mean": 5,
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.r_mapcalc(expression="zones = row()")
    tools.r_category(map="zones", separator=":", rules=StringIO("1:north\n2:south\n"))
    result = tools.t_rast_univar(
        input="temperature", zones="zones", where="name = 'temperature_2'"
    )
    print(result.text)
    ```

    ```text
    id|semantic_label|start|end|zone|label|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|1|north|3|0|1|3|2|2|2|0.816496580927726|0.666666666666667|40.8248290463863|6|6
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|2|south|3|0|4|6|2|5|5|0.816496580927726|0.666666666666667|16.3299316185545|15|15
    ```

    ```python
    result = tools.t_rast_univar(
        input="temperature",
        zones="zones",
        format="json",
        where="name = 'temperature_2'",
    )
    for stats in result.json:
        print(f"zone {stats['zone']} ({stats['zone_label']}): mean {stats['mean']}")
    ```

    ```text
    zone 1 (north): mean 2
    zone 2 (south): mean 5
    ```

### Restrict the statistics with a raster mask

A raster mask restricts the statistics in the same way as for *r.univar*.
With the mask on the northern row (category 1 of `zones`), three cells of
`temperature_2` remain, 1, 2 and 3, and the other three count as null cells.
`r.mask -r` removes the mask again.

=== "Command line"

    ```sh
    r.mask raster=zones maskcats=1
    t.rast.univar input=temperature where="name = 'temperature_2'"
    r.mask -r
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|3|3|1|3|2|2|2|0.816496580927726|0.666666666666667|40.8248290463863|6|6
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mask(raster="zones", maskcats="1")
    result = tools.t_rast_univar(input="temperature", where="name = 'temperature_2'")
    print(result.text)
    tools.r_mask(flags="r")
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|3|3|1|3|2|2|2|0.816496580927726|0.666666666666667|40.8248290463863|6|6
    ```

### Choose the output format

The option **separator** sets another separator, and the flag **-u** leaves
out the line with the column names, for instance to append the lines to a
table that has them already. With **format** `csv`, the columns are separated
by commas, and the option **output** writes the statistics to a file. With
**format** `json`, *t.rast.univar* prints a list with one object per map;
here for `temperature_2` with the extended statistics and two percentiles. In
Python, the attribute `json` of the result holds this list, and the example
prints the mean, the median and the percentiles from it.

=== "Command line"

    ```sh
    t.rast.univar -u input=temperature separator=";"
    ```

    ```text
    temperature_1@PERMANENT;;2026-03-01 00:00:00;2026-03-02 00:00:00;6;0;-2;3;5;0.5;1.5;1.70782512765993;2.91666666666667;341.565025531987;3;9
    temperature_2@PERMANENT;;2026-03-02 00:00:00;2026-03-03 00:00:00;6;0;1;6;5;3.5;3.5;1.70782512765993;2.91666666666667;48.7950036474267;21;21
    temperature_3@PERMANENT;;2026-03-03 00:00:00;2026-03-04 00:00:00;4;2;4;8;4;6;6;1.58113883008419;2.5;26.3523138347365;24;24
    ```

    ```sh
    t.rast.univar input=temperature format=csv output=temperature.csv
    cat temperature.csv
    ```

    ```text
    id,semantic_label,start,end,non_null_cells,null_cells,min,max,range,mean,mean_of_abs,stddev,variance,coeff_var,sum,sum_abs
    temperature_1@PERMANENT,,2026-03-01 00:00:00,2026-03-02 00:00:00,6,0,-2,3,5,0.5,1.5,1.70782512765993,2.91666666666667,341.565025531987,3,9
    temperature_2@PERMANENT,,2026-03-02 00:00:00,2026-03-03 00:00:00,6,0,1,6,5,3.5,3.5,1.70782512765993,2.91666666666667,48.7950036474267,21,21
    temperature_3@PERMANENT,,2026-03-03 00:00:00,2026-03-04 00:00:00,4,2,4,8,4,6,6,1.58113883008419,2.5,26.3523138347365,24,24
    ```

    ```sh
    t.rast.univar -e input=temperature format=json percentile=50,90 \
        where="name = 'temperature_2'"
    ```

    ```text
    [
        {
            "id": "temperature_2@PERMANENT",
            "semantic_label": null,
            "start": "2026-03-02 00:00:00",
            "end": "2026-03-03 00:00:00",
            "n": 6,
            "null_cells": 0,
            "cells": 6,
            "min": 1,
            "max": 6,
            "range": 5,
            "mean": 3.5,
            "mean_of_abs": 3.5,
            "stddev": 1.707825127659933,
            "variance": 2.9166666666666665,
            "coeff_var": 48.795003647426654,
            "sum": 21,
            "first_quartile": 2,
            "median": 3.5,
            "third_quartile": 5,
            "percentiles": [
                {
                    "percentile": 50,
                    "value": 3
                },
                {
                    "percentile": 90,
                    "value": 5
                }
            ]
        }
    ]
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_univar(input="temperature", separator=";", flags="u")
    print(result.text)
    ```

    ```text
    temperature_1@PERMANENT;;2026-03-01 00:00:00;2026-03-02 00:00:00;6;0;-2;3;5;0.5;1.5;1.70782512765993;2.91666666666667;341.565025531987;3;9
    temperature_2@PERMANENT;;2026-03-02 00:00:00;2026-03-03 00:00:00;6;0;1;6;5;3.5;3.5;1.70782512765993;2.91666666666667;48.7950036474267;21;21
    temperature_3@PERMANENT;;2026-03-03 00:00:00;2026-03-04 00:00:00;4;2;4;8;4;6;6;1.58113883008419;2.5;26.3523138347365;24;24
    ```

    ```python
    from pathlib import Path

    tools.t_rast_univar(input="temperature", format="csv", output="temperature.csv")
    print(Path("temperature.csv").read_text(), end="")
    ```

    ```text
    id,semantic_label,start,end,non_null_cells,null_cells,min,max,range,mean,mean_of_abs,stddev,variance,coeff_var,sum,sum_abs
    temperature_1@PERMANENT,,2026-03-01 00:00:00,2026-03-02 00:00:00,6,0,-2,3,5,0.5,1.5,1.70782512765993,2.91666666666667,341.565025531987,3,9
    temperature_2@PERMANENT,,2026-03-02 00:00:00,2026-03-03 00:00:00,6,0,1,6,5,3.5,3.5,1.70782512765993,2.91666666666667,48.7950036474267,21,21
    temperature_3@PERMANENT,,2026-03-03 00:00:00,2026-03-04 00:00:00,4,2,4,8,4,6,6,1.58113883008419,2.5,26.3523138347365,24,24
    ```

    ```python
    result = tools.t_rast_univar(
        input="temperature",
        format="json",
        percentile=[50, 90],
        where="name = 'temperature_2'",
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
    temperature_2@PERMANENT: mean 3.5, median 3.5, percentiles {50: 3, 90: 5}
    ```

### Maps with extents of their own

Satellite scenes rarely share one extent. The dataset `scenes` holds four
maps with constant values on extents of their own; the current region is the
square from (0, 0) to (4, 4) with 16 cells:

- `scene_1` covers the square from (-1, -1) to (5, 5) and so the whole
  region;
- `scene_2` lies inside the region, from (1, 1) to (3, 3);
- `scene_3` reaches from (2, 2) to (6, 6) and shares 4 cells with the region;
- `scene_4` lies outside, from (10, 10) to (12, 12).

The commands print the columns `id`, `non_null_cells` and `null_cells` only:
on the command line, *cut* keeps the first, fifth and sixth column; in Python,
the function `print_cells()` reads them from the JSON output, where `n` is the
number of non-null cells.

1. By default, the cells are counted in the current region: `scene_1` has 16
   non-null cells there, `scene_2` and `scene_3` have 4, and `scene_4` none.
2. With **-r**, each map is counted in its own region: `scene_1` has 36
   cells, `scene_3` 16, and `scene_4`, outside the current region, 4.
3. **region_relation** selects maps by their relation to the current region:
   `overlaps` keeps all but `scene_4`, `contains` only `scene_1`, which covers
   the region, and `is_contained` only `scene_2`, which lies inside it.
   Combined with **-r**, the selected maps are counted in their own regions.

=== "Command line"

    ```sh
    for scene in "scene_1 -1 5 10" "scene_2 1 3 20" \
        "scene_3 2 6 30" "scene_4 10 12 40"; do
        set -- $scene
        g.region s=$2 n=$3 w=$2 e=$3 res=1
        r.mapcalc expression="$1 = $4"
    done
    t.create output=scenes title="Scenes" \
        description="Scenes with extents of their own"
    t.register -i input=scenes maps=scene_1,scene_2,scene_3,scene_4 \
        start=2026-07-01 increment="1 day"
    g.region s=0 n=4 w=0 e=4 res=1
    t.rast.univar input=scenes | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@PERMANENT|16|0
    scene_2@PERMANENT|4|12
    scene_3@PERMANENT|4|12
    scene_4@PERMANENT|0|16
    ```

    ```sh
    t.rast.univar -r input=scenes | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@PERMANENT|36|0
    scene_2@PERMANENT|4|0
    scene_3@PERMANENT|16|0
    scene_4@PERMANENT|4|0
    ```

    ```sh
    t.rast.univar input=scenes region_relation=overlaps | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@PERMANENT|16|0
    scene_2@PERMANENT|4|12
    scene_3@PERMANENT|4|12
    ```

    ```sh
    t.rast.univar input=scenes region_relation=contains | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@PERMANENT|16|0
    ```

    ```sh
    t.rast.univar input=scenes region_relation=is_contained | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_2@PERMANENT|4|12
    ```

    ```sh
    t.rast.univar -r input=scenes region_relation=overlaps | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@PERMANENT|36|0
    scene_2@PERMANENT|4|0
    scene_3@PERMANENT|16|0
    ```

=== "Python (grass.tools)"

    ```python
    for name, low, high, value in (
        ("scene_1", -1, 5, 10),
        ("scene_2", 1, 3, 20),
        ("scene_3", 2, 6, 30),
        ("scene_4", 10, 12, 40),
    ):
        tools.g_region(s=low, n=high, w=low, e=high, res=1)
        tools.r_mapcalc(expression=f"{name} = {value}")
    tools.t_create(
        output="scenes",
        title="Scenes",
        description="Scenes with extents of their own",
    )
    tools.t_register(
        input="scenes",
        maps="scene_1,scene_2,scene_3,scene_4",
        start="2026-07-01",
        increment="1 day",
        flags="i",
    )
    tools.g_region(s=0, n=4, w=0, e=4, res=1)


    def print_cells(result):
        print("id|non_null_cells|null_cells")
        for stats in result.json:
            print(f"{stats['id']}|{stats['n']}|{stats['null_cells']}")


    print_cells(tools.t_rast_univar(input="scenes", format="json"))
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@PERMANENT|16|0
    scene_2@PERMANENT|4|12
    scene_3@PERMANENT|4|12
    scene_4@PERMANENT|0|16
    ```

    ```python
    print_cells(tools.t_rast_univar(input="scenes", format="json", flags="r"))
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@PERMANENT|36|0
    scene_2@PERMANENT|4|0
    scene_3@PERMANENT|16|0
    scene_4@PERMANENT|4|0
    ```

    ```python
    result = tools.t_rast_univar(input="scenes", format="json", region_relation="overlaps")
    print_cells(result)
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@PERMANENT|16|0
    scene_2@PERMANENT|4|12
    scene_3@PERMANENT|4|12
    ```

    ```python
    result = tools.t_rast_univar(input="scenes", format="json", region_relation="contains")
    print_cells(result)
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@PERMANENT|16|0
    ```

    ```python
    result = tools.t_rast_univar(
        input="scenes", format="json", region_relation="is_contained"
    )
    print_cells(result)
    ```

    ```text
    id|non_null_cells|null_cells
    scene_2@PERMANENT|4|12
    ```

    ```python
    result = tools.t_rast_univar(
        input="scenes", format="json", region_relation="overlaps", flags="r"
    )
    print_cells(result)
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@PERMANENT|36|0
    scene_2@PERMANENT|4|0
    scene_3@PERMANENT|16|0
    ```

### Use a dataset of another mapset

*t.rast.univar* reads a dataset of another mapset. The example creates the
mapset `analysis` and switches to it; the dataset `temperature` stays in the
mapset `PERMANENT` and is named with its mapset. The region of the new
mapset is set to the one of the maps. In the second block, *g.mapsets* shows
that `PERMANENT` is in the search path of the new mapset, so the name
`temperature` without a mapset finds the same dataset.

=== "Command line"

    ```sh
    g.mapset -c mapset=analysis
    g.region n=2 s=0 e=3 w=0 res=1
    t.rast.univar input=temperature@PERMANENT where="name = 'temperature_2'"
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21
    ```

    ```sh
    g.mapsets -p
    t.rast.univar input=temperature where="name = 'temperature_2'"
    ```

    ```text
    analysis PERMANENT
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="analysis", flags="c")
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    result = tools.t_rast_univar(
        input="temperature@PERMANENT", where="name = 'temperature_2'"
    )
    print(result.text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21
    ```

    ```python
    print(tools.g_mapsets(flags="p").text)
    result = tools.t_rast_univar(input="temperature", where="name = 'temperature_2'")
    print(result.text)
    ```

    ```text
    analysis PERMANENT
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    temperature_2@PERMANENT||2026-03-02 00:00:00|2026-03-03 00:00:00|6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.gisenv](g.gisenv.md), [g.mapsets](g.mapsets.md), [g.region](g.region.md),
[r.mask](r.mask.md), [r.univar](r.univar.md),
[t.create](t.create.md), [t.info](t.info.md),
[t.rast3d.univar](t.rast3d.univar.md), [t.register](t.register.md),
[t.vect.univar](t.vect.univar.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture  
Stefan Blumentrath (support for zones, parallel processing, and spatial
relations)
