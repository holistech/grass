## DESCRIPTION

*t.sample* shows how the maps of one or more space time datasets lie in time
to the maps of another space time dataset, the sampler. It reads the temporal
topology of the datasets and prints one row for each map of the sampler and for
each gap between two maps of the sampler. A row lists the maps of every input
dataset that stand in the chosen temporal relations to that sampler map. The
types of the datasets can differ: a vector dataset can be sampled by a raster
dataset, and a raster dataset by a 3D raster dataset. See the
[introduction to temporal data processing](temporalintro.md) for an overview,
*[t.topology](t.topology.md)* for the temporal topology of one dataset and
*[t.rast.list](t.rast.list.md)* for the method `deltagaps`, which lists the
gaps of a dataset in the same way.

### Datasets

The option **inputs** names the datasets to be sampled, separated by commas, and
is required. The option **sample** names the sampler and is required. All inputs
are of the type given by **intype**, the sampler is of the type given by
**samtype**: `strds` (the default of both), `str3ds` or `stvds`. A name without
`@mapset` means the current mapset. The temporal type, absolute or relative,
must be the same for the sampler and for each input, and the maps of the sampler
must be intervals. If they are not, the dataset is not sampled, see the NOTES.

The sampler divides the time into granules: each of its maps is a granule, and
a hole between two maps is a granule of its own, a gap. A gap is time that no
sampler map covers. Two maps that touch, where the end of one is the start of
the next, leave no gap, and neither does a map that ends inside a longer one.
A granule includes its start and excludes its end. The sampler should have a
valid topology: the tool does not check it, and if sampler maps start at the
same time, the rows follow the order of their start and end times.

### Relations

The option **method** selects the temporal relations between a granule and the
maps of an input. The default is `during,overlap,contain,equal`. It takes the
following values:

- `during`: the map is longer than the granule and the granule lies inside it;
  the two may share the start or the end
- `overlap`: the map reaches over one border of the granule
- `contain`: the map lies inside the granule, also a time instance; a map that
  shares the start or the end of the granule counts as well
- `equal`: the map has the start and the end of the granule
- `start`: the maps of `contain`, the maps that begin before the granule and
  end inside it or at its end, and the maps longer than the granule that begin
  with it; the maps equal to the granule are never listed
- `follows`: the map ends where the granule starts
- `precedes`: the map starts where the granule ends, also a time instance

Other values are rejected by the parser, among them the inverse relations
`overlaps` and `overlapped`. Several values are separated by commas. The maps
of a cell are listed relation by relation: first those of `during`, `equal`,
`follows` and `precedes`, in the order in which the list names them, then
those of the groups `start`, `overlap` and `contain` in this order, whatever
the order of the list. A map that stands in two selected relations is listed
once. The maps of one of the plain relations follow their start times, and
maps that start together follow their ids. A group is made of several
relations, which follow one another, so a map need not be listed by its start
time: in the call with `start` of the third example, `wide_s` stands before
`wide_e`, although it starts later.

### Output

*t.sample* prints a table to standard output. The columns are separated by the
character of the option **separator**, which is the pipe `|` by default; the
names `space` and `tab` are accepted as well. A comma cannot be
used, as it separates the map ids inside a cell: with a comma the columns are
separated by ` | `, a pipe with a space on each side. The flag **-c** prints the
names of the columns as first row, with the ids of the datasets for the first
columns. The columns are:

- the sampler map of the granule, as `name@mapset`; a gap has no map, and the
  cell shows `None`
- one column for each input dataset, in the order of **inputs**: the ids of the
  maps related to the granule, separated by commas, or `None` if there are none;
  a map of a vector dataset registered with a layer shows as `name:layer@mapset`
- `start_time` and `end_time`: the start and the end of the granule; relative
  time is printed as the stored numbers, without a unit
- `interval_length`: the length of the granule, `end_time` minus `start_time`;
  absolute time gives days, as a fraction if the granule is shorter than a
  day (`0.25` for six hours), relative time gives a number of the unit of the
  datasets
- `distance_from_begin`: the distance of the start of the granule from the
  start of the first granule, in the same unit as `interval_length`

The flag **-s** adds a spatial check: a map stays in a cell only if its spatial
extent touches the extent of the granule, where a shared edge or corner counts.
For 3D datasets only the north-south and east-west extent is compared, not
bottom and top. A gap has no extent of its own and is given the extent
`(0, 0, 0, 0)`: with **-s** it relates only to maps whose extent touches the
origin. Without **-s** the spatial extent plays no role.

## NOTES

The tool checks every dataset before it prints anything. A dataset that is not
found, an unknown name or a name of another type than **intype** or **samtype**,
ends the tool with the error `Dataset <name@mapset> not found in temporal
database` and return code 1; the name in the message always has the mapset.

The two other refusals print an error and no failure code. If the sampler has
time instances instead of intervals, the tool prints `The temporal map type of
the sample dataset must be interval`, nothing else, and returns 0. If an input
has another temporal type than the sampler, absolute or relative, the tool
prints `The space time datasets must be of the same temporal type`, leaves that
input out of the rows and samples the others. With **-c** the header still
names the left-out input, so the header has one column more than the rows.

Maps outside the time of the sampler get no row of their own. With the default
method a map before the first granule, or starting at or after the end of the
last one, appears in no cell.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_sample` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset and
region. Most examples are about time, not about maps: their maps hold small
constant values, and the dates are the point. The last two examples sample
series of maps over North Carolina and use the extents of the maps.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_sample -->

<!-- markdownlint-disable MD046 -->

### Sample time instances with intervals

Six maps are time instances on June 1 to 6, 2026. The sampler `periods` has
three intervals: June 1 to 3, June 5 to 7 and June 7 to 9. With the flag
**-c** the first row names the columns. The first period holds the readings of
June 1 and 2. The reading of June 3 is not in it, as the end of a granule is
excluded: it belongs to the gap from June 3 to 5, a row without a sampler map,
with the reading of June 4. The second period holds the readings of June 5 and
6. The third period starts where the second one ends, so there is no gap row
between them, and it holds no reading: its cell shows `None`. The length of
each granule is 2.0 days, and the distance from the start of the first granule
grows by 2.0 days from row to row.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_sample
    g.region raster=elev_state_500m res=1000 -a
    for step in 1 2 3 4 5 6; do
        r.mapcalc expression="reading_$step = $step"
    done
    t.create output=readings title="Daily readings" \
        description="One reading on each day"
    t.register input=readings \
        maps=reading_1,reading_2,reading_3,reading_4,reading_5,reading_6 \
        start=2026-06-01 increment="1 day"
    for step in 1 2 3; do
        r.mapcalc expression="period_$step = $step"
    done
    t.create output=periods title="Sampling periods" \
        description="Two days, a hole of two days, two and two days"
    t.register input=periods maps=period_1 start=2026-06-01 end=2026-06-03
    t.register input=periods maps=period_2 start=2026-06-05 end=2026-06-07
    t.register input=periods maps=period_3 start=2026-06-07 end=2026-06-09
    t.sample -c inputs=readings sample=periods
    ```

    ```text
    periods@t_sample|readings@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|reading_1@t_sample,reading_2@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|reading_3@t_sample,reading_4@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|reading_5@t_sample,reading_6@t_sample|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|None|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()

    tools.g_mapset(flags="c", mapset="t_sample")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for step in range(1, 7):
        tools.r_mapcalc(expression=f"reading_{step} = {step}")
    tools.t_create(
        output="readings",
        title="Daily readings",
        description="One reading on each day",
    )
    tools.t_register(
        input="readings",
        maps="reading_1,reading_2,reading_3,reading_4,reading_5,reading_6",
        start="2026-06-01",
        increment="1 day",
    )
    for step in range(1, 4):
        tools.r_mapcalc(expression=f"period_{step} = {step}")
    tools.t_create(
        output="periods",
        title="Sampling periods",
        description="Two days, a hole of two days, two and two days",
    )
    for step, start, end in (
        (1, "2026-06-01", "2026-06-03"),
        (2, "2026-06-05", "2026-06-07"),
        (3, "2026-06-07", "2026-06-09"),
    ):
        tools.t_register(input="periods", maps=f"period_{step}", start=start, end=end)
    print(tools.t_sample(inputs="readings", sample="periods", flags="c").text)
    ```

    ```text
    periods@t_sample|readings@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|reading_1@t_sample,reading_2@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|reading_3@t_sample,reading_4@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|reading_5@t_sample,reading_6@t_sample|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|None|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

### Several datasets and the field separator

The dataset `spans` has three intervals of two days: June 1 to 3, June 3 to 5
and June 5 to 7. The first and the last are equal to the granules `period_1` and
`period_2`, the middle one fills the gap of `periods`. Naming it after the
readings in **inputs** adds a column in this order. The default method lists
each span in the row it is equal to, and the last granule has no span. The
second call uses **separator** `space`. The third asks for a comma: it cannot
separate the columns, as the cells list several map ids with commas, so ` | ` is
printed.

=== "Command line"

    ```sh
    for step in 1 2 3; do
        r.mapcalc expression="span_$step = $step"
    done
    t.create output=spans title="Two-day spans" \
        description="Three spans of two days without a gap"
    t.register -i input=spans maps=span_1,span_2,span_3 \
        start=2026-06-01 increment="2 days"
    t.sample -c inputs=readings,spans sample=periods
    ```

    ```text
    periods@t_sample|readings@t_sample|spans@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|reading_1@t_sample,reading_2@t_sample|span_1@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|reading_3@t_sample,reading_4@t_sample|span_2@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|reading_5@t_sample,reading_6@t_sample|span_3@t_sample|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|None|None|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

    ```sh
    t.sample -c inputs=readings,spans sample=periods separator=space
    ```

    ```text
    periods@t_sample readings@t_sample spans@t_sample start_time end_time interval_length distance_from_begin
    period_1@t_sample reading_1@t_sample,reading_2@t_sample span_1@t_sample 2026-06-01 00:00:00 2026-06-03 00:00:00 2.0 0.0
    None reading_3@t_sample,reading_4@t_sample span_2@t_sample 2026-06-03 00:00:00 2026-06-05 00:00:00 2.0 2.0
    period_2@t_sample reading_5@t_sample,reading_6@t_sample span_3@t_sample 2026-06-05 00:00:00 2026-06-07 00:00:00 2.0 4.0
    period_3@t_sample None None 2026-06-07 00:00:00 2026-06-09 00:00:00 2.0 6.0
    ```

    ```sh
    t.sample -c inputs=readings,spans sample=periods separator=comma
    ```

    ```text
    periods@t_sample | readings@t_sample | spans@t_sample | start_time | end_time | interval_length | distance_from_begin
    period_1@t_sample | reading_1@t_sample,reading_2@t_sample | span_1@t_sample | 2026-06-01 00:00:00 | 2026-06-03 00:00:00 | 2.0 | 0.0
    None | reading_3@t_sample,reading_4@t_sample | span_2@t_sample | 2026-06-03 00:00:00 | 2026-06-05 00:00:00 | 2.0 | 2.0
    period_2@t_sample | reading_5@t_sample,reading_6@t_sample | span_3@t_sample | 2026-06-05 00:00:00 | 2026-06-07 00:00:00 | 2.0 | 4.0
    period_3@t_sample | None | None | 2026-06-07 00:00:00 | 2026-06-09 00:00:00 | 2.0 | 6.0
    ```

=== "Python (grass.tools)"

    ```python
    for step in range(1, 4):
        tools.r_mapcalc(expression=f"span_{step} = {step}")
    tools.t_create(
        output="spans",
        title="Two-day spans",
        description="Three spans of two days without a gap",
    )
    tools.t_register(
        input="spans",
        maps="span_1,span_2,span_3",
        start="2026-06-01",
        increment="2 days",
        flags="i",
    )
    print(tools.t_sample(inputs="readings,spans", sample="periods", flags="c").text)
    ```

    ```text
    periods@t_sample|readings@t_sample|spans@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|reading_1@t_sample,reading_2@t_sample|span_1@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|reading_3@t_sample,reading_4@t_sample|span_2@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|reading_5@t_sample,reading_6@t_sample|span_3@t_sample|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|None|None|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

    ```python
    print(
        tools.t_sample(
            inputs="readings,spans", sample="periods", separator="space", flags="c"
        ).text
    )
    ```

    ```text
    periods@t_sample readings@t_sample spans@t_sample start_time end_time interval_length distance_from_begin
    period_1@t_sample reading_1@t_sample,reading_2@t_sample span_1@t_sample 2026-06-01 00:00:00 2026-06-03 00:00:00 2.0 0.0
    None reading_3@t_sample,reading_4@t_sample span_2@t_sample 2026-06-03 00:00:00 2026-06-05 00:00:00 2.0 2.0
    period_2@t_sample reading_5@t_sample,reading_6@t_sample span_3@t_sample 2026-06-05 00:00:00 2026-06-07 00:00:00 2.0 4.0
    period_3@t_sample None None 2026-06-07 00:00:00 2026-06-09 00:00:00 2.0 6.0
    ```

    ```python
    print(
        tools.t_sample(
            inputs="readings,spans", sample="periods", separator="comma", flags="c"
        ).text
    )
    ```

    ```text
    periods@t_sample | readings@t_sample | spans@t_sample | start_time | end_time | interval_length | distance_from_begin
    period_1@t_sample | reading_1@t_sample,reading_2@t_sample | span_1@t_sample | 2026-06-01 00:00:00 | 2026-06-03 00:00:00 | 2.0 | 0.0
    None | reading_3@t_sample,reading_4@t_sample | span_2@t_sample | 2026-06-03 00:00:00 | 2026-06-05 00:00:00 | 2.0 | 2.0
    period_2@t_sample | reading_5@t_sample,reading_6@t_sample | span_3@t_sample | 2026-06-05 00:00:00 | 2026-06-07 00:00:00 | 2.0 | 4.0
    period_3@t_sample | None | None | 2026-06-07 00:00:00 | 2026-06-09 00:00:00 | 2.0 | 6.0
    ```

### Choose the temporal relations of intervals

A granule from June 10 to June 20, in the dataset `windows_june`, is sampled
with the dataset `shapes`. The maps `wide`, `wide_s` and `wide_e` are longer
than the granule, `wide_s` shares its start and `wide_e` its end, `early` and
`late` reach over its start and its end, `inside` lies in it, `same` has its
start and end and `before` ends long before it. The first call uses the default
method: the plain values `during` and `equal` come first, then the groups
`overlap` and `contain`, so the maps come in the order `wide`, `wide_e`,
`wide_s`, `same`, `early`, `late`, `inside`; the maps of `during` follow their
start times. The other calls select one relation each. `before` is related by
none of them. `start` lists `early`, which begins before the granule and ends
inside it, `wide_e`, which begins before it and ends with it, `wide_s`, which is
longer and begins with it, and `inside`. It does not list `wide`, `late` and
`same`: the value `start` never lists a map equal to the granule. The last call
names `overlap` before `start`, yet the maps of `start` come first and `late`,
which only `overlap` selects, comes last.

=== "Command line"

    ```sh
    for name in window wide wide_s wide_e early late inside same before; do
        r.mapcalc expression="$name = 1"
    done
    t.create output=windows_june title="One granule" \
        description="The granule from June 10 to June 20"
    t.register input=windows_june maps=window start=2026-06-10 end=2026-06-20
    t.create output=shapes title="Shapes" \
        description="Intervals in different positions to the granule"
    t.register input=shapes maps=wide start=2026-06-05 end=2026-06-25
    t.register input=shapes maps=wide_s start=2026-06-10 end=2026-06-25
    t.register input=shapes maps=wide_e start=2026-06-05 end=2026-06-20
    t.register input=shapes maps=early start=2026-06-08 end=2026-06-12
    t.register input=shapes maps=late start=2026-06-18 end=2026-06-25
    t.register input=shapes maps=inside start=2026-06-12 end=2026-06-15
    t.register input=shapes maps=same start=2026-06-10 end=2026-06-20
    t.register input=shapes maps=before start=2026-06-01 end=2026-06-05
    t.sample -c inputs=shapes sample=windows_june
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|wide@t_sample,wide_e@t_sample,wide_s@t_sample,same@t_sample,early@t_sample,late@t_sample,inside@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```sh
    t.sample -c inputs=shapes sample=windows_june method=during
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|wide@t_sample,wide_e@t_sample,wide_s@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```sh
    t.sample -c inputs=shapes sample=windows_june method=overlap
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|early@t_sample,late@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```sh
    t.sample -c inputs=shapes sample=windows_june method=contain
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|inside@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```sh
    t.sample -c inputs=shapes sample=windows_june method=equal
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|same@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```sh
    t.sample -c inputs=shapes sample=windows_june method=start
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|early@t_sample,wide_s@t_sample,wide_e@t_sample,inside@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```sh
    t.sample -c inputs=shapes sample=windows_june method=overlap,start
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|early@t_sample,wide_s@t_sample,wide_e@t_sample,inside@t_sample,late@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

=== "Python (grass.tools)"

    ```python
    for name in (
        "window",
        "wide",
        "wide_s",
        "wide_e",
        "early",
        "late",
        "inside",
        "same",
        "before",
    ):
        tools.r_mapcalc(expression=f"{name} = 1")
    tools.t_create(
        output="windows_june",
        title="One granule",
        description="The granule from June 10 to June 20",
    )
    tools.t_register(
        input="windows_june", maps="window", start="2026-06-10", end="2026-06-20"
    )
    tools.t_create(
        output="shapes",
        title="Shapes",
        description="Intervals in different positions to the granule",
    )
    for name, start, end in (
        ("wide", "2026-06-05", "2026-06-25"),
        ("wide_s", "2026-06-10", "2026-06-25"),
        ("wide_e", "2026-06-05", "2026-06-20"),
        ("early", "2026-06-08", "2026-06-12"),
        ("late", "2026-06-18", "2026-06-25"),
        ("inside", "2026-06-12", "2026-06-15"),
        ("same", "2026-06-10", "2026-06-20"),
        ("before", "2026-06-01", "2026-06-05"),
    ):
        tools.t_register(input="shapes", maps=name, start=start, end=end)
    print(tools.t_sample(inputs="shapes", sample="windows_june", flags="c").text)
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|wide@t_sample,wide_e@t_sample,wide_s@t_sample,same@t_sample,early@t_sample,late@t_sample,inside@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```python
    print(
        tools.t_sample(
            inputs="shapes", sample="windows_june", method="during", flags="c"
        ).text
    )
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|wide@t_sample,wide_e@t_sample,wide_s@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```python
    print(
        tools.t_sample(
            inputs="shapes", sample="windows_june", method="overlap", flags="c"
        ).text
    )
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|early@t_sample,late@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```python
    print(
        tools.t_sample(
            inputs="shapes", sample="windows_june", method="contain", flags="c"
        ).text
    )
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|inside@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```python
    print(
        tools.t_sample(
            inputs="shapes", sample="windows_june", method="equal", flags="c"
        ).text
    )
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|same@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```python
    print(
        tools.t_sample(
            inputs="shapes", sample="windows_june", method="start", flags="c"
        ).text
    )
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|early@t_sample,wide_s@t_sample,wide_e@t_sample,inside@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

    ```python
    print(
        tools.t_sample(
            inputs="shapes", sample="windows_june", method="overlap,start", flags="c"
        ).text
    )
    ```

    ```text
    windows_june@t_sample|shapes@t_sample|start_time|end_time|interval_length|distance_from_begin
    window@t_sample|early@t_sample,wide_s@t_sample,wide_e@t_sample,inside@t_sample,late@t_sample|2026-06-10 00:00:00|2026-06-20 00:00:00|10.0|0.0
    ```

### Maps next to the granule

The relations `follows` and `precedes` select the neighbours of a granule in
time. The dataset `spans` from the previous example has maps June 1 to 3, June 3
to 5 and June 5 to 7, and the sampler is `periods` again. With `follows` a cell
lists the span that ends where the granule starts: `span_1` ends on June 3 where
the gap starts, `span_2` where `period_2` starts and `span_3` where `period_3`
starts. With `precedes` it lists the span that starts where the granule ends:
`span_2` for `period_1` and `span_3` for the gap. The third call names both
values. The gap now lists `span_3` before `span_1`, as `precedes` stands first
in the list; with `follows,precedes` the two would swap.

=== "Command line"

    ```sh
    t.sample -c inputs=spans sample=periods method=follows
    ```

    ```text
    periods@t_sample|spans@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|None|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|span_1@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|span_2@t_sample|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|span_3@t_sample|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

    ```sh
    t.sample -c inputs=spans sample=periods method=precedes
    ```

    ```text
    periods@t_sample|spans@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|span_2@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|span_3@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|None|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|None|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

    ```sh
    t.sample -c inputs=spans sample=periods method=precedes,follows
    ```

    ```text
    periods@t_sample|spans@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|span_2@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|span_3@t_sample,span_1@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|span_2@t_sample|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|span_3@t_sample|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

=== "Python (grass.tools)"

    ```python
    print(
        tools.t_sample(inputs="spans", sample="periods", method="follows", flags="c").text
    )
    ```

    ```text
    periods@t_sample|spans@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|None|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|span_1@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|span_2@t_sample|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|span_3@t_sample|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

    ```python
    print(
        tools.t_sample(inputs="spans", sample="periods", method="precedes", flags="c").text
    )
    ```

    ```text
    periods@t_sample|spans@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|span_2@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|span_3@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|None|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|None|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

    ```python
    print(
        tools.t_sample(
            inputs="spans", sample="periods", method="precedes,follows", flags="c"
        ).text
    )
    ```

    ```text
    periods@t_sample|spans@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|span_2@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|span_3@t_sample,span_1@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|span_2@t_sample|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|span_3@t_sample|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

### Relative time

Relative time is sampled in the same way, with the stored numbers and no unit.
The model output `output_1` to `output_4` is at the hours 0 to 3, the sampler
has the windows 0 to 2 and 4 to 6. The first window holds the outputs at the
hours 0 and 1, the gap from 2 to 4 those at the hours 2 and 3. The length of
the granules is 2, 2 and 2, and the distance from the first start 0, 2 and 4.

=== "Command line"

    ```sh
    for step in 1 2 3 4; do
        r.mapcalc expression="output_$step = $step"
    done
    t.create output=model temporaltype=relative title="Model output" \
        description="Output at the hours 0, 1, 2 and 3"
    t.register input=model maps=output_1,output_2,output_3,output_4 \
        start=0 increment=1 unit=hours
    for step in 1 2; do
        r.mapcalc expression="window_$step = $step"
    done
    t.create output=windows temporaltype=relative title="Windows" \
        description="Two windows of two hours with a hole between them"
    t.register input=windows maps=window_1 start=0 end=2 unit=hours
    t.register input=windows maps=window_2 start=4 end=6 unit=hours
    t.sample -c inputs=model sample=windows
    ```

    ```text
    windows@t_sample|model@t_sample|start_time|end_time|interval_length|distance_from_begin
    window_1@t_sample|output_1@t_sample,output_2@t_sample|0|2|2|0
    None|output_3@t_sample,output_4@t_sample|2|4|2|2
    window_2@t_sample|None|4|6|2|4
    ```

=== "Python (grass.tools)"

    ```python
    for step in range(1, 5):
        tools.r_mapcalc(expression=f"output_{step} = {step}")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model output",
        description="Output at the hours 0, 1, 2 and 3",
    )
    tools.t_register(
        input="model",
        maps="output_1,output_2,output_3,output_4",
        start=0,
        increment=1,
        unit="hours",
    )
    for step in range(1, 3):
        tools.r_mapcalc(expression=f"window_{step} = {step}")
    tools.t_create(
        output="windows",
        temporaltype="relative",
        title="Windows",
        description="Two windows of two hours with a hole between them",
    )
    tools.t_register(input="windows", maps="window_1", start=0, end=2, unit="hours")
    tools.t_register(input="windows", maps="window_2", start=4, end=6, unit="hours")
    print(tools.t_sample(inputs="model", sample="windows", flags="c").text)
    ```

    ```text
    windows@t_sample|model@t_sample|start_time|end_time|interval_length|distance_from_begin
    window_1@t_sample|output_1@t_sample,output_2@t_sample|0|2|2|0
    None|output_3@t_sample,output_4@t_sample|2|4|2|2
    window_2@t_sample|None|4|6|2|4
    ```

### Granules that are not whole days

With absolute time, `interval_length` and `distance_from_begin` are given in
days, as fractions if needed. The sampler `slots` has a slot of six hours, a
slot of twelve hours starting at 06:00 and a slot of the month July. The first
two granules are 0.25 and 0.5 days long, and the second starts 0.25 days after
the first.
The gap from June 1, 18:00 to July 1 is 29.25 days long and starts 0.75 days
after the first start, and the month of July starts 30.0 days after it.

=== "Command line"

    ```sh
    for step in 1 2 3; do
        r.mapcalc expression="slot_$step = $step"
        r.mapcalc expression="probe_$step = $step"
    done
    t.create output=slots title="Slots" \
        description="A quarter day, half a day and a month"
    t.register input=slots maps=slot_1 \
        start="2026-06-01 00:00:00" end="2026-06-01 06:00:00"
    t.register input=slots maps=slot_2 \
        start="2026-06-01 06:00:00" end="2026-06-01 18:00:00"
    t.register input=slots maps=slot_3 start=2026-07-01 end=2026-08-01
    t.create output=probes title="Probes" description="Three time instances"
    t.register input=probes maps=probe_1 start="2026-06-01 03:00:00"
    t.register input=probes maps=probe_2 start="2026-06-01 12:00:00"
    t.register input=probes maps=probe_3 start="2026-07-15 00:00:00"
    t.sample -c inputs=probes sample=slots
    ```

    ```text
    slots@t_sample|probes@t_sample|start_time|end_time|interval_length|distance_from_begin
    slot_1@t_sample|probe_1@t_sample|2026-06-01 00:00:00|2026-06-01 06:00:00|0.25|0.0
    slot_2@t_sample|probe_2@t_sample|2026-06-01 06:00:00|2026-06-01 18:00:00|0.5|0.25
    None|None|2026-06-01 18:00:00|2026-07-01 00:00:00|29.25|0.75
    slot_3@t_sample|probe_3@t_sample|2026-07-01 00:00:00|2026-08-01 00:00:00|31.0|30.0
    ```

=== "Python (grass.tools)"

    ```python
    for step in range(1, 4):
        tools.r_mapcalc(expression=f"slot_{step} = {step}")
        tools.r_mapcalc(expression=f"probe_{step} = {step}")
    tools.t_create(
        output="slots",
        title="Slots",
        description="A quarter day, half a day and a month",
    )
    for step, start, end in (
        (1, "2026-06-01 00:00:00", "2026-06-01 06:00:00"),
        (2, "2026-06-01 06:00:00", "2026-06-01 18:00:00"),
        (3, "2026-07-01", "2026-08-01"),
    ):
        tools.t_register(input="slots", maps=f"slot_{step}", start=start, end=end)
    tools.t_create(output="probes", title="Probes", description="Three time instances")
    for step, start in (
        (1, "2026-06-01 03:00:00"),
        (2, "2026-06-01 12:00:00"),
        (3, "2026-07-15 00:00:00"),
    ):
        tools.t_register(input="probes", maps=f"probe_{step}", start=start)
    print(tools.t_sample(inputs="probes", sample="slots", flags="c").text)
    ```

    ```text
    slots@t_sample|probes@t_sample|start_time|end_time|interval_length|distance_from_begin
    slot_1@t_sample|probe_1@t_sample|2026-06-01 00:00:00|2026-06-01 06:00:00|0.25|0.0
    slot_2@t_sample|probe_2@t_sample|2026-06-01 06:00:00|2026-06-01 18:00:00|0.5|0.25
    None|None|2026-06-01 18:00:00|2026-07-01 00:00:00|29.25|0.75
    slot_3@t_sample|probe_3@t_sample|2026-07-01 00:00:00|2026-08-01 00:00:00|31.0|30.0
    ```

### Datasets of different types

The dataset type of the inputs and of the sampler are selected with **intype**
and **samtype**, independent of each other. The first call samples the vector
dataset `gauges` with the raster dataset `periods` of the first example; each of
its three maps holds the stream gauges of Crabtree Creek in Raleigh, taken from
`usgsgages`. The second call samples the raster dataset `readings` with the 3D
raster dataset `soil`, which has two maps of two days. The region of this
example includes the 3D settings (**t**, **b**, **res3** and **tbres**) that 3D
maps need.

=== "Command line"

    ```sh
    g.region raster=elev_state_500m res=1000 res3=1000 t=3000 b=0 tbres=1000 -a
    for step in 1 2 3; do
        v.extract input=usgsgages output=gauge_$step \
            where="SITE_NAME LIKE 'Crabtree Creek%'"
    done
    t.create type=stvds output=gauges title="Gauges" \
        description="Stream gauges on three days"
    t.register type=vector input=gauges maps=gauge_1,gauge_2,gauge_3 \
        start=2026-06-01 increment="1 day"
    r3.mapcalc expression="soil_1 = depth()"
    r3.mapcalc expression="soil_2 = depth() + 10"
    t.create type=str3ds output=soil title="Soil" \
        description="Soil temperature in two layers"
    t.register -i type=raster_3d input=soil maps=soil_1,soil_2 \
        start=2026-06-01 increment="2 days"
    t.sample -c inputs=gauges intype=stvds sample=periods
    ```

    ```text
    periods@t_sample|gauges@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|gauge_1@t_sample,gauge_2@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|gauge_3@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|None|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|None|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

    ```sh
    t.sample -c inputs=readings sample=soil samtype=str3ds
    ```

    ```text
    soil@t_sample|readings@t_sample|start_time|end_time|interval_length|distance_from_begin
    soil_1@t_sample|reading_1@t_sample,reading_2@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    soil_2@t_sample|reading_3@t_sample,reading_4@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(
        raster="elev_state_500m", res=1000, res3=1000, t=3000, b=0, tbres=1000, flags="a"
    )
    for step in range(1, 4):
        tools.v_extract(
            input="usgsgages",
            output=f"gauge_{step}",
            where="SITE_NAME LIKE 'Crabtree Creek%'",
        )
    tools.t_create(
        type="stvds",
        output="gauges",
        title="Gauges",
        description="Stream gauges on three days",
    )
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauge_1,gauge_2,gauge_3",
        start="2026-06-01",
        increment="1 day",
    )
    tools.r3_mapcalc(expression="soil_1 = depth()")
    tools.r3_mapcalc(expression="soil_2 = depth() + 10")
    tools.t_create(
        type="str3ds",
        output="soil",
        title="Soil",
        description="Soil temperature in two layers",
    )
    tools.t_register(
        type="raster_3d",
        input="soil",
        maps="soil_1,soil_2",
        start="2026-06-01",
        increment="2 days",
        flags="i",
    )
    print(tools.t_sample(inputs="gauges", intype="stvds", sample="periods", flags="c").text)
    ```

    ```text
    periods@t_sample|gauges@t_sample|start_time|end_time|interval_length|distance_from_begin
    period_1@t_sample|gauge_1@t_sample,gauge_2@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    None|gauge_3@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    period_2@t_sample|None|2026-06-05 00:00:00|2026-06-07 00:00:00|2.0|4.0
    period_3@t_sample|None|2026-06-07 00:00:00|2026-06-09 00:00:00|2.0|6.0
    ```

    ```python
    print(
        tools.t_sample(inputs="readings", sample="soil", samtype="str3ds", flags="c").text
    )
    ```

    ```text
    soil@t_sample|readings@t_sample|start_time|end_time|interval_length|distance_from_begin
    soil_1@t_sample|reading_1@t_sample,reading_2@t_sample|2026-06-01 00:00:00|2026-06-03 00:00:00|2.0|0.0
    soil_2@t_sample|reading_3@t_sample,reading_4@t_sample|2026-06-03 00:00:00|2026-06-05 00:00:00|2.0|2.0
    ```

### Daily precipitation in the months of a temperature series

A common use of the tool is to find out which maps of a fine series fall into
each granule of a coarse one. The sampler `temperature_monthly` has the monthly
mean air temperature of June, July and August 2020 in degree Celsius, one map
for each month. The input `precipitation_daily` has five daily precipitation
sums in mm, from July 30 to August 3, 2020. The table has one row for each
month. June has no daily map and shows `None`; July lists its two days and
August its three, so the series is split at the month boundary. Both series
are generated: the temperature falls with the height from `elev_state_500m`,
and the precipitation is the height factor `1 + elev_state_500m / 1000`
times a fixed amount for each day (8, 0, 14, 21 and 3 mm at sea level), not a
measurement. The last two columns give the length of each month in days and
the distance of its start from June 1.

=== "Command line"

    ```sh
    for month in 6 7 8; do
        echo "temperature_monthly_2020_$(printf %02d $month) = round((16.5" \
            "+ 10.5 * cos(30 * ($month - 7.2)) - 0.0065 * elev_state_500m" \
            "- 0.00001 * (y() - 160000)) * 10) / 10.0"
    done | r.mapcalc file=-
    t.create output=temperature_monthly title="Air temperature" \
        description="Monthly mean air temperature June to August 2020 in degree Celsius"
    t.register -i input=temperature_monthly \
        maps=temperature_monthly_2020_06,temperature_monthly_2020_07,temperature_monthly_2020_08 \
        start=2020-06-01 increment="1 month"
    for entry in 07_30:8 07_31:0 08_01:14 08_02:21 08_03:3; do
        r.mapcalc expression="precipitation_daily_2020_${entry%:*} = round(${entry#*:} * (1 + elev_state_500m / 1000.0))"
    done
    t.create output=precipitation_daily title="Precipitation" \
        description="Daily precipitation sum July 30 to August 3, 2020 in mm"
    t.register -i input=precipitation_daily \
        maps=precipitation_daily_2020_07_30,precipitation_daily_2020_07_31,precipitation_daily_2020_08_01,precipitation_daily_2020_08_02,precipitation_daily_2020_08_03 \
        start=2020-07-30 increment="1 day"
    t.sample -c inputs=precipitation_daily sample=temperature_monthly
    ```

    ```text
    temperature_monthly@t_sample|precipitation_daily@t_sample|start_time|end_time|interval_length|distance_from_begin
    temperature_monthly_2020_06@t_sample|None|2020-06-01 00:00:00|2020-07-01 00:00:00|30.0|0.0
    temperature_monthly_2020_07@t_sample|precipitation_daily_2020_07_30@t_sample,precipitation_daily_2020_07_31@t_sample|2020-07-01 00:00:00|2020-08-01 00:00:00|31.0|30.0
    temperature_monthly_2020_08@t_sample|precipitation_daily_2020_08_01@t_sample,precipitation_daily_2020_08_02@t_sample,precipitation_daily_2020_08_03@t_sample|2020-08-01 00:00:00|2020-09-01 00:00:00|31.0|61.0
    ```

=== "Python (grass.tools)"

    ```python
    months = ("06", "07", "08")
    tools.r_mapcalc(
        expression="\n".join(
            f"temperature_monthly_2020_{month} = round((16.5"
            f" + 10.5 * cos(30 * ({int(month)} - 7.2)) - 0.0065 * elev_state_500m"
            " - 0.00001 * (y() - 160000)) * 10) / 10.0"
            for month in months
        )
    )
    tools.t_create(
        output="temperature_monthly",
        title="Air temperature",
        description="Monthly mean air temperature June to August 2020 in degree Celsius",
    )
    tools.t_register(
        input="temperature_monthly",
        maps=",".join(f"temperature_monthly_2020_{month}" for month in months),
        start="2020-06-01",
        increment="1 month",
        flags="i",
    )
    daily = {"07_30": 8, "07_31": 0, "08_01": 14, "08_02": 21, "08_03": 3}
    tools.r_mapcalc(
        expression="\n".join(
            f"precipitation_daily_2020_{day} = round({amount} * (1 + elev_state_500m / 1000.0))"
            for day, amount in daily.items()
        )
    )
    tools.t_create(
        output="precipitation_daily",
        title="Precipitation",
        description="Daily precipitation sum July 30 to August 3, 2020 in mm",
    )
    tools.t_register(
        input="precipitation_daily",
        maps=",".join(f"precipitation_daily_2020_{day}" for day in daily),
        start="2020-07-30",
        increment="1 day",
        flags="i",
    )
    print(
        tools.t_sample(
            inputs="precipitation_daily", sample="temperature_monthly", flags="c"
        ).text
    )
    ```

    ```text
    temperature_monthly@t_sample|precipitation_daily@t_sample|start_time|end_time|interval_length|distance_from_begin
    temperature_monthly_2020_06@t_sample|None|2020-06-01 00:00:00|2020-07-01 00:00:00|30.0|0.0
    temperature_monthly_2020_07@t_sample|precipitation_daily_2020_07_30@t_sample,precipitation_daily_2020_07_31@t_sample|2020-07-01 00:00:00|2020-08-01 00:00:00|31.0|30.0
    temperature_monthly_2020_08@t_sample|precipitation_daily_2020_08_01@t_sample,precipitation_daily_2020_08_02@t_sample,precipitation_daily_2020_08_03@t_sample|2020-08-01 00:00:00|2020-09-01 00:00:00|31.0|61.0
    ```

### Keep only maps that touch the granule in space

The flag **-s** drops maps whose spatial extent is apart from the extent of the
granule. The sampler `plots` has one granule of eight days with the map `plot`,
which covers a square of 4 km by 4 km, from 200000 to 204000 in both directions
(meters). The scenes are time instances inside this granule: `scene_1` covers
the area from 199000 to 205000, `scene_2` lies inside it, from 201000 to 203000,
`scene_3` from 204000 to 206000 touches the granule in the corner (204000,
204000) and `scene_4` from 210000 to 212000 is far away. Without **-s** the cell
lists all four scenes. With **-s** the scene `scene_4` is dropped and the scene
that touches the corner stays.

=== "Command line"

    ```sh
    g.region s=200000 n=204000 w=200000 e=204000 res=1000
    r.mapcalc expression="plot = 1"
    for scene in "scene_1 199000 205000 10" "scene_2 201000 203000 20" \
        "scene_3 204000 206000 30" "scene_4 210000 212000 40"; do
        set -- $scene
        g.region s=$2 n=$3 w=$2 e=$3 res=1
        r.mapcalc expression="$1 = $4"
    done
    g.region raster=elev_state_500m res=1000 -a
    t.create output=plots title="Plot" description="One granule of eight days"
    t.register input=plots maps=plot start=2026-06-01 end=2026-06-09
    t.create output=scenes title="Scenes" \
        description="Four scenes of different extents"
    t.register input=scenes maps=scene_1,scene_2,scene_3,scene_4 \
        start=2026-06-02 increment="1 day"
    t.sample -c inputs=scenes sample=plots
    ```

    ```text
    plots@t_sample|scenes@t_sample|start_time|end_time|interval_length|distance_from_begin
    plot@t_sample|scene_1@t_sample,scene_2@t_sample,scene_3@t_sample,scene_4@t_sample|2026-06-01 00:00:00|2026-06-09 00:00:00|8.0|0.0
    ```

    ```sh
    t.sample -cs inputs=scenes sample=plots
    ```

    ```text
    plots@t_sample|scenes@t_sample|start_time|end_time|interval_length|distance_from_begin
    plot@t_sample|scene_1@t_sample,scene_2@t_sample,scene_3@t_sample|2026-06-01 00:00:00|2026-06-09 00:00:00|8.0|0.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(s=200000, n=204000, w=200000, e=204000, res=1000)
    tools.r_mapcalc(expression="plot = 1")
    for name, low, high, value in (
        ("scene_1", 199000, 205000, 10),
        ("scene_2", 201000, 203000, 20),
        ("scene_3", 204000, 206000, 30),
        ("scene_4", 210000, 212000, 40),
    ):
        tools.g_region(s=low, n=high, w=low, e=high, res=1000)
        tools.r_mapcalc(expression=f"{name} = {value}")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.t_create(output="plots", title="Plot", description="One granule of eight days")
    tools.t_register(input="plots", maps="plot", start="2026-06-01", end="2026-06-09")
    tools.t_create(
        output="scenes", title="Scenes", description="Four scenes of different extents"
    )
    tools.t_register(
        input="scenes",
        maps="scene_1,scene_2,scene_3,scene_4",
        start="2026-06-02",
        increment="1 day",
    )
    print(tools.t_sample(inputs="scenes", sample="plots", flags="c").text)
    ```

    ```text
    plots@t_sample|scenes@t_sample|start_time|end_time|interval_length|distance_from_begin
    plot@t_sample|scene_1@t_sample,scene_2@t_sample,scene_3@t_sample,scene_4@t_sample|2026-06-01 00:00:00|2026-06-09 00:00:00|8.0|0.0
    ```

    ```python
    print(tools.t_sample(inputs="scenes", sample="plots", flags="cs").text)
    ```

    ```text
    plots@t_sample|scenes@t_sample|start_time|end_time|interval_length|distance_from_begin
    plot@t_sample|scene_1@t_sample,scene_2@t_sample,scene_3@t_sample|2026-06-01 00:00:00|2026-06-09 00:00:00|8.0|0.0
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[t.rast.list](t.rast.list.md), [t.topology](t.topology.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
