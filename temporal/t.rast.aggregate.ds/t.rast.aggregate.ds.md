## DESCRIPTION

*t.rast.aggregate.ds* aggregates the maps of a space time raster dataset over
the time intervals of a second space time dataset, the sampler. Each map of
the sampler is an interval. For every interval the tool collects the raster
maps of the input dataset that stand in a chosen temporal relation to it,
computes one map from them with an aggregation method, and registers the
result in a new space time raster dataset. The new map has the start and the
end time of the interval. *[t.rast.aggregate](t.rast.aggregate.md)* instead
cuts the time into granules of one given length; here the intervals can differ
in length and leave gaps between them. The maps are computed by
*[r.series](r.series.md)*. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets.

### Datasets

The option **input** names the space time raster dataset to aggregate, the
option **sample** the sampler. The option **type** gives the type of the
sampler: `strds` (the default), `stvds` or `str3ds`. Only the time stamps of
the sampler are used; the aggregated maps are always the raster maps of
**input**. A dataset of another mapset is named with its mapset,
`name@mapset`, and the new dataset is created in the current mapset, as the
last example shows.

The input and the sampler must have the same temporal type, absolute or
relative, and all maps of the sampler must be time intervals, not time
instances. With relative time they must have the same unit. The sampler
intervals can overlap: each interval collects its maps, so a map can go into
several results. The intervals are not required to touch; the time between two
of them is not aggregated. Two intervals with the same start and the same end
are refused, see the NOTES.

The option **output** names the new space time raster dataset. It takes the
temporal type, the unit of relative time and the semantic type of the input,
and the method as its aggregation type, as the first example shows. An
existing dataset is replaced only with **--overwrite**.

### Choosing the maps of an interval

The option **sampling** lists the temporal relations that select the maps of
an interval. It is always formulated from the point of view of the sampler
interval, so the default `contains` takes the maps that lie inside the
interval. The values describe maps that have a start and an end, that is
intervals. The values are:

- `equal`: the map has the start and the end of the interval
- `contains`: the map lies inside the interval; a map that shares the start or
  the end of the interval counts as well, but a map that has both is `equal`
- `started`: the map has the start of the interval and ends inside it
- `finished`: the map has the end of the interval and starts inside it
- `during`: the interval lies inside the map; a map that shares the start or
  the end of the interval counts as well, but a map that has both is `equal`
- `starts`: the map has the start of the interval and reaches over its end
- `finishes`: the map has the end of the interval and starts before it
- `overlaps`: the interval starts before the map and ends inside it
- `overlapped`: the map starts before the interval and ends inside it

Several values are separated by commas. A map that stands in more than one of
the listed relations goes into the result once: `contains,started` selects
what `contains` selects, and `during,starts` what `during` selects. The
selected maps are read in the order of their start times. The third example
runs every value.

The option **where** takes an SQL condition on the registered maps, for
instance on `start_time` or `name`. It applies to the maps of the input and to
the maps of the sampler: a condition on `start_time` removes intervals as well
as input maps.

### Names of the new maps

The option **basename** is required. Each new map is named `basename_suffix`.
The option **suffix** sets the form of the suffix:

- `gran` (the default), for absolute time: the start of the interval, cut to
  the granularity of the sampler, with underscores. For a sampler with a
  granularity of one day this is `2026_06_01`;
- `time`: the full start time, `2026_06_01T00_00_00`;
- `num`: the number of the interval with five digits, `00001`; `num%03` sets
  the number of digits to 3.

With relative time the default `gran` gives the number of the interval with
five digits, as `num` does, as the example with relative time shows.

The intervals are numbered from 1 in the order of their start times, and an
interval that gets no map keeps its number, so the numbers can have gaps. The
option **offset** (default 0) is added to the number in the suffixes `num` and
`num%NN`; the suffixes `gran` and `time` ignore it.

### Computing the maps

The option **method** is one of the aggregates of *r.series*; its default is
`average`. See the manual of *r.series* for their definitions. Cells without a
value are passed over: a result cell is null only if the cell is null in every
map of the interval. An interval without any related map produces no map. If
all maps of an interval are null, the result is a map without a valid cell; by
default it is not registered, and the flag **-n** keeps it. The option
**nprocs** sets how many aggregations run at the same time (default 1); the
result does not depend on it.

*t.rast.aggregate.ds* computes in the current computational region, as
*r.series* does, as the eighth example shows.

## NOTES

The tool checks its input before it computes anything and refuses the
following with an error.

- A dataset that does not exist, or the sampler with another type than
  **type**: `Space time dataset <name> of type <strds> not found`, with the
  name and the type that were looked for.
- An input and a sampler of different temporal types: `Input and aggregation
  dataset must have the same temporal type`.
- With relative time, a sampler with another unit than the input: `The unit
  <years> of the aggregation dataset <sampler> differs from the unit <days> of
  the input dataset <input>`, here for a sampler in years and an input in days.
  Releases before GRASS 8.6 read the numbers of the sampler in the unit of the
  input.
- A sampler with a time instance: `All registered maps of the aggregation
  dataset must have time intervals`.
- An input or a sampler that **where** leaves without a map: `Space time
  raster dataset <name> is empty` for the input, `Space time dataset <name> is
  empty` for the sampler.
- A **where** with an SQL syntax error: `Invalid where condition <condition>`
  followed by the message of the database, without a traceback.
- Two sampler intervals with the same start and end, which would give two
  maps one name: `Several maps would get the same name`.
- A **suffix** other than `gran`, `time`, `num` or `num%NN`: `Invalid suffix
  <name>, use gran, time, num or num%NN`.
- A dot in the name of the new dataset: `<name> is not a valid name for a new
  space time dataset: a dot is not allowed`.
- An existing output dataset without **--overwrite**: one error message that
  names the dataset.

If no map is related to any interval, the tool warns, names the granularity of
the sampler and the sampling, and creates no space time dataset; it ends
without an error. With monthly intervals and maps that do not start on the
first day of a month, for example a series from 31 January, the default
sampling `contains` finds nothing; `sampling=overlaps` relates each map to the
interval in which it starts and which it outlasts.

Since GRASS 8.6 the flag **-n** works as documented and as in
*t.rast.aggregate*: by default an aggregated map without any valid cell is not
registered, and **-n** keeps it. Earlier versions did the opposite. Since GRASS
8.6 a map that stands in several of the listed relations counts once, and the
maps of an interval are read as one list in time order. Earlier versions read
them relation by relation, in the order `equal`, `contains`, `during`,
`starts`, `started`, `finishes`, `finished`, `overlaps`, `overlapped`. This
matters only when **sampling** lists more than one relation and the method
depends on the order of the maps, that is `min_raster`, `max_raster`, `slope`,
`offset` and `detcoeff`; the other methods give the same result.

*r.series* keeps every map of an interval open once per thread and needs two
files per map and thread. The tool therefore runs *r.series* with the flag
**-z**, which reads the maps row by row, when the maps of an interval exceed
1000 (this tool has no **file_limit** option) or when 2 x threads x maps + 64
exceeds the limit of open files of the process (`ulimit -n`). The threads are
counted from `NPROCS` of the GRASS session (see *g.gisenv*), else
`OMP_NUM_THREADS`, else the usable processors. With a raster mask (see
*r.mask*), *r.series* runs one thread, and so does the count. In a GRASS built
without OpenMP, *r.series* runs one thread; the count does not know this and
may set **-z** earlier than needed. The tool warns whenever it sets the flag.
Without a limit on open files, or without the Python module `resource` (for
example on Windows), the limit of 1000 maps counts. The flag does not change
the result but is slower: for 100 maps of 1000 x 1000 cells, *r.series* took
5.2 s with **-z** instead of 0.25 s (measured 31.10.2026 with method sum, three
runs).

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Aggregate by the intervals of another dataset

The dataset `rain` holds the rain of eight days from 1 June 2026 as maps with
constant values 1 to 8. The gauge failed on 4 and 5 June, so `rain_4` and
`rain_5` have no value at all, and `rain_3` has no value in its western
column. The dataset has the semantic type `sum`.

The sampler `periods` has four intervals: 1 to 4 June, 4 to 6 June, 6 to 8
June and 8 to 9 June, one day long. The default `sampling=contains` and the
method `sum` give:

- 1 to 4 June: `rain_1`, `rain_2` and `rain_3` lie in the interval, the sum is
  1 + 2 + 3 = 6 in the eastern columns, and 1 + 2 = 3 in the western column,
  where `rain_3` has no value and is passed over. The map has the minimum 3 and
  the maximum 6;
- 4 to 6 June: both maps have no value, so there is no map with data. Without
  **-n** the tool does not register the result;
- 6 to 8 June: 6 + 7 = 13;
- 8 June: `rain_8` has the start and the end of the interval, so it is `equal`
  and not related by `contains`. The interval gets no map.

The first block aggregates with **nprocs** 2 and lists the result with
*[t.rast.list](t.rast.list.md)*. The second block runs the same aggregation
with **-n**. The map for 4 to 6 June is then registered, and its minimum and
maximum are `None`. The third block reads the semantic type and the aggregation
type of the new dataset.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 t=1 b=0 res=1 res3=1 tbres=1
    for day in 1 2 6 7 8; do
        r.mapcalc expression="rain_$day = $day"
    done
    r.mapcalc expression="rain_3 = if(col() == 1, null(), 3)"
    r.mapcalc expression="rain_4 = null()"
    r.mapcalc expression="rain_5 = null()"
    t.create output=rain semantictype=sum title="Daily rain" \
        description="Rain on eight days, the gauge failed on days 4 and 5"
    t.register -i input=rain \
        maps=rain_1,rain_2,rain_3,rain_4,rain_5,rain_6,rain_7,rain_8 \
        start=2026-06-01 increment="1 day"
    t.create output=periods title="Periods" \
        description="Four intervals of different length"
    for period in "1 2026-06-01 2026-06-04" "2 2026-06-04 2026-06-06" \
        "3 2026-06-06 2026-06-08" "4 2026-06-08 2026-06-09"; do
        set -- $period
        r.mapcalc expression="period_$1 = $1"
        t.register input=periods maps=period_$1 start=$2 end=$3
    done
    t.rast.aggregate.ds input=rain sample=periods output=rain_periods \
        basename=rain_period method=sum nprocs=2
    t.rast.list input=rain_periods columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    rain_period_2026_06_01|2026-06-01 00:00:00|2026-06-04 00:00:00|3.0|6.0
    rain_period_2026_06_06|2026-06-06 00:00:00|2026-06-08 00:00:00|13.0|13.0
    ```

    ```sh
    t.rast.aggregate.ds -n input=rain sample=periods output=rain_periods_n \
        basename=rain_period_n method=sum
    t.rast.list input=rain_periods_n columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    rain_period_n_2026_06_01|2026-06-01 00:00:00|2026-06-04 00:00:00|3.0|6.0
    rain_period_n_2026_06_04|2026-06-04 00:00:00|2026-06-06 00:00:00|None|None
    rain_period_n_2026_06_06|2026-06-06 00:00:00|2026-06-08 00:00:00|13.0|13.0
    ```

    ```sh
    t.info -g input=rain_periods | grep -E "^(semantic_type|aggregation_type)="
    ```

    ```text
    semantic_type=sum
    aggregation_type=sum
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()

    tools.g_region(n=2, s=0, e=3, w=0, t=1, b=0, res=1, res3=1, tbres=1)
    for day in (1, 2, 6, 7, 8):
        tools.r_mapcalc(expression=f"rain_{day} = {day}")
    tools.r_mapcalc(expression="rain_3 = if(col() == 1, null(), 3)")
    tools.r_mapcalc(expression="rain_4 = null()")
    tools.r_mapcalc(expression="rain_5 = null()")
    tools.t_create(
        output="rain",
        semantictype="sum",
        title="Daily rain",
        description="Rain on eight days, the gauge failed on days 4 and 5",
    )
    tools.t_register(
        input="rain",
        maps="rain_1,rain_2,rain_3,rain_4,rain_5,rain_6,rain_7,rain_8",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    tools.t_create(
        output="periods",
        title="Periods",
        description="Four intervals of different length",
    )
    for number, start, end in (
        (1, "2026-06-01", "2026-06-04"),
        (2, "2026-06-04", "2026-06-06"),
        (3, "2026-06-06", "2026-06-08"),
        (4, "2026-06-08", "2026-06-09"),
    ):
        tools.r_mapcalc(expression=f"period_{number} = {number}")
        tools.t_register(input="periods", maps=f"period_{number}", start=start, end=end)
    tools.t_rast_aggregate_ds(
        input="rain",
        sample="periods",
        output="rain_periods",
        basename="rain_period",
        method="sum",
        nprocs=2,
    )
    print(
        tools.t_rast_list(
            input="rain_periods", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    rain_period_2026_06_01|2026-06-01 00:00:00|2026-06-04 00:00:00|3.0|6.0
    rain_period_2026_06_06|2026-06-06 00:00:00|2026-06-08 00:00:00|13.0|13.0
    ```

    ```python
    tools.t_rast_aggregate_ds(
        input="rain",
        sample="periods",
        output="rain_periods_n",
        basename="rain_period_n",
        method="sum",
        flags="n",
    )
    print(
        tools.t_rast_list(
            input="rain_periods_n", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    rain_period_n_2026_06_01|2026-06-01 00:00:00|2026-06-04 00:00:00|3.0|6.0
    rain_period_n_2026_06_04|2026-06-04 00:00:00|2026-06-06 00:00:00|None|None
    rain_period_n_2026_06_06|2026-06-06 00:00:00|2026-06-08 00:00:00|13.0|13.0
    ```

    ```python
    info = tools.t_info(input="rain_periods", flags="g").keyval
    for key in ("semantic_type", "aggregation_type"):
        print(f"{key}={info[key]}")
    ```

    ```text
    semantic_type=sum
    aggregation_type=sum
    ```

### Name the new maps

The option **suffix** with `num%02` numbers the intervals with two digits, and
**offset** adds 10 to the number. The interval for 4 to 6 June, number 2, has
no map without **-n**, and the interval for 8 June, number 4, has none either,
so the maps carry the numbers 11 and 13 and 12 is missing. The second block
uses `suffix=time` with the same **offset**, which does not change the names.
The default suffix `gran`, the day of the start, was used in the previous
example.

=== "Command line"

    ```sh
    t.rast.aggregate.ds input=rain sample=periods output=rain_num \
        basename=rain_num method=sum suffix=num%02 offset=10
    t.rast.list input=rain_num columns=name,start_time
    ```

    ```text
    name|start_time
    rain_num_11|2026-06-01 00:00:00
    rain_num_13|2026-06-06 00:00:00
    ```

    ```sh
    t.rast.aggregate.ds input=rain sample=periods output=rain_time \
        basename=rain_time method=sum suffix=time offset=10
    t.rast.list input=rain_time columns=name,start_time
    ```

    ```text
    name|start_time
    rain_time_2026_06_01T00_00_00|2026-06-01 00:00:00
    rain_time_2026_06_06T00_00_00|2026-06-06 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_aggregate_ds(
        input="rain",
        sample="periods",
        output="rain_num",
        basename="rain_num",
        method="sum",
        suffix="num%02",
        offset=10,
    )
    print(tools.t_rast_list(input="rain_num", columns="name,start_time").text)
    ```

    ```text
    name|start_time
    rain_num_11|2026-06-01 00:00:00
    rain_num_13|2026-06-06 00:00:00
    ```

    ```python
    tools.t_rast_aggregate_ds(
        input="rain",
        sample="periods",
        output="rain_time",
        basename="rain_time",
        method="sum",
        suffix="time",
        offset=10,
    )
    print(tools.t_rast_list(input="rain_time", columns="name,start_time").text)
    ```

    ```text
    name|start_time
    rain_time_2026_06_01T00_00_00|2026-06-01 00:00:00
    rain_time_2026_06_06T00_00_00|2026-06-06 00:00:00
    ```

### Choose the temporal relation

The sampler `window` has one interval, 10 to 20 June 2026. The dataset `shapes`
has nine maps in different positions to it, with the values 1, 2, 4 and so on,
so the sum of a result shows which maps were selected:

- `wide`, 5 to 25 June, value 1: the interval lies inside it;
- `early`, 8 to 12 June, value 2: it starts before the interval and ends
  inside it;
- `late`, 18 to 25 June, value 4: it starts inside the interval and ends after
  it;
- `inside`, 12 to 15 June, value 8: it lies inside the interval;
- `same`, 10 to 20 June, value 16: it has the start and the end of the
  interval;
- `first_part`, 10 to 15 June, value 32: it has the start of the interval and
  ends inside it;
- `last_part`, 15 to 20 June, value 64: it has the end of the interval and
  starts inside it;
- `long_start`, 10 to 25 June, value 128: it has the start of the interval and
  ends after it;
- `long_end`, 5 to 20 June, value 256: it has the end of the interval and
  starts before it.

The loop runs every value of **sampling** and prints the value with the sum.
`contains` selects `inside` and the two maps that share a border, 8 + 32 + 64 =
104, but not `same`. `during` selects `wide` and the two maps that share a
border, 1 + 128 + 256 = 385. `contains,started` and `during,starts` give the
same sums, as the maps of `started` and `starts` are selected by both. Each run
replaces the previous result with **--overwrite**.

=== "Command line"

    ```sh
    r.mapcalc expression="window = 1"
    t.create output=window title="Window" description="One interval"
    t.register input=window maps=window start=2026-06-10 end=2026-06-20
    t.create output=shapes title="Shapes" \
        description="Maps in different positions to the interval"
    for shape in "wide 1 2026-06-05 2026-06-25" "early 2 2026-06-08 2026-06-12" \
        "late 4 2026-06-18 2026-06-25" "inside 8 2026-06-12 2026-06-15" \
        "same 16 2026-06-10 2026-06-20" "first_part 32 2026-06-10 2026-06-15" \
        "last_part 64 2026-06-15 2026-06-20" \
        "long_start 128 2026-06-10 2026-06-25" \
        "long_end 256 2026-06-05 2026-06-20"; do
        set -- $shape
        r.mapcalc expression="$1 = $2"
        t.register input=shapes maps=$1 start=$3 end=$4
    done
    for relation in equal overlaps overlapped starts started finishes finished \
        during contains contains,started during,starts; do
        t.rast.aggregate.ds --overwrite input=shapes sample=window \
            output=by_relation basename=by_relation method=sum sampling=$relation
        printf "%s " $relation
        t.rast.list -u input=by_relation columns=min
    done
    ```

    ```text
    equal 16.0
    overlaps 4.0
    overlapped 2.0
    starts 128.0
    started 32.0
    finishes 256.0
    finished 64.0
    during 385.0
    contains 104.0
    contains,started 104.0
    during,starts 385.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="window = 1")
    tools.t_create(output="window", title="Window", description="One interval")
    tools.t_register(input="window", maps="window", start="2026-06-10", end="2026-06-20")
    tools.t_create(
        output="shapes",
        title="Shapes",
        description="Maps in different positions to the interval",
    )
    for name, value, start, end in (
        ("wide", 1, "2026-06-05", "2026-06-25"),
        ("early", 2, "2026-06-08", "2026-06-12"),
        ("late", 4, "2026-06-18", "2026-06-25"),
        ("inside", 8, "2026-06-12", "2026-06-15"),
        ("same", 16, "2026-06-10", "2026-06-20"),
        ("first_part", 32, "2026-06-10", "2026-06-15"),
        ("last_part", 64, "2026-06-15", "2026-06-20"),
        ("long_start", 128, "2026-06-10", "2026-06-25"),
        ("long_end", 256, "2026-06-05", "2026-06-20"),
    ):
        tools.r_mapcalc(expression=f"{name} = {value}")
        tools.t_register(input="shapes", maps=name, start=start, end=end)
    for relation in (
        "equal",
        "overlaps",
        "overlapped",
        "starts",
        "started",
        "finishes",
        "finished",
        "during",
        "contains",
        "contains,started",
        "during,starts",
    ):
        tools.t_rast_aggregate_ds(
            input="shapes",
            sample="window",
            output="by_relation",
            basename="by_relation",
            method="sum",
            sampling=relation,
            overwrite=True,
        )
        print(
            relation,
            tools.t_rast_list(input="by_relation", columns="min", flags="u").text,
        )
    ```

    ```text
    equal 16.0
    overlaps 4.0
    overlapped 2.0
    starts 128.0
    started 32.0
    finishes 256.0
    finished 64.0
    during 385.0
    contains 104.0
    contains,started 104.0
    during,starts 385.0
    ```

### Select the relations and the maps

The default `contains` leaves out the map of 8 June, which is `equal` to the
last interval of `periods`. With `sampling=contains,equal` the interval gets
its map, 8. The second block adds a **where** condition: only the maps of
`rain` and the intervals of `periods` that start on 6 June or later remain,
and the result has the two last maps of the first one, 13 and 8. The interval
of 1 to 4 June is removed from the sampler as well as the maps of the first
days from the input.

=== "Command line"

    ```sh
    t.rast.aggregate.ds input=rain sample=periods output=rain_equal \
        basename=rain_equal method=sum sampling=contains,equal
    t.rast.list input=rain_equal columns=name,start_time,min
    ```

    ```text
    name|start_time|min
    rain_equal_2026_06_01|2026-06-01 00:00:00|3.0
    rain_equal_2026_06_06|2026-06-06 00:00:00|13.0
    rain_equal_2026_06_08|2026-06-08 00:00:00|8.0
    ```

    ```sh
    t.rast.aggregate.ds input=rain sample=periods output=rain_late \
        basename=rain_late method=sum sampling=contains,equal \
        where="start_time >= '2026-06-06'"
    t.rast.list input=rain_late columns=name,start_time,min
    ```

    ```text
    name|start_time|min
    rain_late_2026_06_06|2026-06-06 00:00:00|13.0
    rain_late_2026_06_08|2026-06-08 00:00:00|8.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_aggregate_ds(
        input="rain",
        sample="periods",
        output="rain_equal",
        basename="rain_equal",
        method="sum",
        sampling="contains,equal",
    )
    print(tools.t_rast_list(input="rain_equal", columns="name,start_time,min").text)
    ```

    ```text
    name|start_time|min
    rain_equal_2026_06_01|2026-06-01 00:00:00|3.0
    rain_equal_2026_06_06|2026-06-06 00:00:00|13.0
    rain_equal_2026_06_08|2026-06-08 00:00:00|8.0
    ```

    ```python
    tools.t_rast_aggregate_ds(
        input="rain",
        sample="periods",
        output="rain_late",
        basename="rain_late",
        method="sum",
        sampling="contains,equal",
        where="start_time >= '2026-06-06'",
    )
    print(tools.t_rast_list(input="rain_late", columns="name,start_time,min").text)
    ```

    ```text
    name|start_time|min
    rain_late_2026_06_06|2026-06-06 00:00:00|13.0
    rain_late_2026_06_08|2026-06-08 00:00:00|8.0
    ```

### Take the intervals from a vector or 3D raster dataset

The sampler can be a space time vector dataset or a space time 3D raster
dataset; **type** names its type. Only its time stamps count. The vector
dataset `gauges` has two maps, one point each, for 1 to 3 June and 5 to 9 June.
The days between are in no interval, so `rain_3` is not used: the sums are
1 + 2 = 3 and, for the second interval, 6 + 7 + 8 = 21, as `rain_5` has no
value. The 3D raster dataset `slabs` has three intervals, 1 to 3 June, 3 to 6
June and 6 to 9 June; the sums are 3, then 3 for `rain_3` alone, as `rain_4`
and `rain_5` have no value, and 21.

=== "Command line"

    ```sh
    t.create type=stvds output=gauges title="Gauges" \
        description="Two gauge periods with a gap between them"
    t.create type=str3ds output=slabs title="Slabs" \
        description="Three periods without a gap"
    for gauge in "1 2026-06-01 2026-06-03" "2 2026-06-05 2026-06-09"; do
        set -- $gauge
        echo "0.5,0.5" | v.in.ascii input=- output=gauge_$1 separator=comma \
            columns="x double precision, y double precision"
        t.register type=vector input=gauges maps=gauge_$1 start=$2 end=$3
    done
    for slab in "1 2026-06-01 2026-06-03" "2 2026-06-03 2026-06-06" \
        "3 2026-06-06 2026-06-09"; do
        set -- $slab
        r3.mapcalc expression="slab_$1 = $1"
        t.register type=raster_3d input=slabs maps=slab_$1 start=$2 end=$3
    done
    t.rast.aggregate.ds type=stvds input=rain sample=gauges \
        output=rain_gauges basename=rain_gauge method=sum
    t.rast.list input=rain_gauges columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    rain_gauge_2026_06_01|2026-06-01 00:00:00|2026-06-03 00:00:00|3.0
    rain_gauge_2026_06_05|2026-06-05 00:00:00|2026-06-09 00:00:00|21.0
    ```

    ```sh
    t.rast.aggregate.ds type=str3ds input=rain sample=slabs \
        output=rain_slabs basename=rain_slab method=sum
    t.rast.list input=rain_slabs columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    rain_slab_2026_06_01|2026-06-01 00:00:00|2026-06-03 00:00:00|3.0
    rain_slab_2026_06_03|2026-06-03 00:00:00|2026-06-06 00:00:00|3.0
    rain_slab_2026_06_06|2026-06-06 00:00:00|2026-06-09 00:00:00|21.0
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.t_create(
        type="stvds",
        output="gauges",
        title="Gauges",
        description="Two gauge periods with a gap between them",
    )
    tools.t_create(
        type="str3ds",
        output="slabs",
        title="Slabs",
        description="Three periods without a gap",
    )
    for number, start, end in (
        (1, "2026-06-01", "2026-06-03"),
        (2, "2026-06-05", "2026-06-09"),
    ):
        tools.v_in_ascii(
            input=StringIO("0.5,0.5\n"),
            output=f"gauge_{number}",
            separator="comma",
            columns="x double precision, y double precision",
        )
        tools.t_register(
            type="vector", input="gauges", maps=f"gauge_{number}", start=start, end=end
        )
    for number, start, end in (
        (1, "2026-06-01", "2026-06-03"),
        (2, "2026-06-03", "2026-06-06"),
        (3, "2026-06-06", "2026-06-09"),
    ):
        tools.r3_mapcalc(expression=f"slab_{number} = {number}")
        tools.t_register(
            type="raster_3d", input="slabs", maps=f"slab_{number}", start=start, end=end
        )
    tools.t_rast_aggregate_ds(
        type="stvds",
        input="rain",
        sample="gauges",
        output="rain_gauges",
        basename="rain_gauge",
        method="sum",
    )
    print(
        tools.t_rast_list(input="rain_gauges", columns="name,start_time,end_time,min").text
    )
    ```

    ```text
    name|start_time|end_time|min
    rain_gauge_2026_06_01|2026-06-01 00:00:00|2026-06-03 00:00:00|3.0
    rain_gauge_2026_06_05|2026-06-05 00:00:00|2026-06-09 00:00:00|21.0
    ```

    ```python
    tools.t_rast_aggregate_ds(
        type="str3ds",
        input="rain",
        sample="slabs",
        output="rain_slabs",
        basename="rain_slab",
        method="sum",
    )
    print(
        tools.t_rast_list(input="rain_slabs", columns="name,start_time,end_time,min").text
    )
    ```

    ```text
    name|start_time|end_time|min
    rain_slab_2026_06_01|2026-06-01 00:00:00|2026-06-03 00:00:00|3.0
    rain_slab_2026_06_03|2026-06-03 00:00:00|2026-06-06 00:00:00|3.0
    rain_slab_2026_06_06|2026-06-06 00:00:00|2026-06-09 00:00:00|21.0
    ```

### Aggregate a dataset with relative time

A model writes one map per hour for six hours, with the values 1 to 6. The
dataset `model` has relative time in the unit hours, and so has the sampler
`blocks` with the intervals 0 to 3 and 3 to 6. The method `maximum` gives 3 and
6. Start and end of the new maps are numbers of the unit of the input, printed
without it. The sampler needs the same unit as the input. The last two blocks
register a sampler in years and try to aggregate the dataset in hours with it.
The tool refuses and prints the error; the block goes on after it.

=== "Command line"

    ```sh
    for step in 1 2 3 4 5 6; do
        r.mapcalc expression="step_$step = $step"
    done
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per hour"
    t.register -i input=model maps=step_1,step_2,step_3,step_4,step_5,step_6 \
        start=0 increment=1 unit=hours
    t.create output=blocks temporaltype=relative title="Blocks" \
        description="Two blocks of three hours"
    for block in "1 0 3" "2 3 6"; do
        set -- $block
        r.mapcalc expression="block_$1 = $1"
        t.register input=blocks maps=block_$1 start=$2 end=$3 unit=hours
    done
    t.rast.aggregate.ds input=model sample=blocks output=model_blocks \
        basename=model_block method=maximum
    t.rast.list input=model_blocks columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    model_block_00001|0|3|3.0
    model_block_00002|3|6|6.0
    ```

    ```sh
    r.mapcalc expression="block_years = 1"
    t.create output=blocks_years temporaltype=relative title="Blocks in years" \
        description="One block of one year"
    t.register input=blocks_years maps=block_years start=0 end=1 unit=years
    if ! t.rast.aggregate.ds input=model sample=blocks_years \
        output=model_years basename=model_year method=maximum 2>&1; then
        echo "t.rast.aggregate.ds failed"
    fi
    ```

    ```text
    ERROR: The unit <years> of the aggregation dataset <blocks_years> differs
           from the unit <hours> of the input dataset <model>
    t.rast.aggregate.ds failed
    ```

=== "Python (grass.tools)"

    ```python
    for step in range(1, 7):
        tools.r_mapcalc(expression=f"step_{step} = {step}")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per hour",
    )
    tools.t_register(
        input="model",
        maps="step_1,step_2,step_3,step_4,step_5,step_6",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.t_create(
        output="blocks",
        temporaltype="relative",
        title="Blocks",
        description="Two blocks of three hours",
    )
    for number, start, end in ((1, 0, 3), (2, 3, 6)):
        tools.r_mapcalc(expression=f"block_{number} = {number}")
        tools.t_register(
            input="blocks", maps=f"block_{number}", start=start, end=end, unit="hours"
        )
    tools.t_rast_aggregate_ds(
        input="model",
        sample="blocks",
        output="model_blocks",
        basename="model_block",
        method="maximum",
    )
    print(
        tools.t_rast_list(input="model_blocks", columns="name,start_time,end_time,min").text
    )
    ```

    ```text
    name|start_time|end_time|min
    model_block_00001|0|3|3.0
    model_block_00002|3|6|6.0
    ```

    ```python
    from grass.tools import ToolError

    tools.r_mapcalc(expression="block_years = 1")
    tools.t_create(
        output="blocks_years",
        temporaltype="relative",
        title="Blocks in years",
        description="One block of one year",
    )
    tools.t_register(input="blocks_years", maps="block_years", start=0, end=1, unit="years")
    try:
        tools.t_rast_aggregate_ds(
            input="model",
            sample="blocks_years",
            output="model_years",
            basename="model_year",
            method="maximum",
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.aggregate.ds failed")
    ```

    ```text
    ERROR: The unit <years> of the aggregation dataset <blocks_years> differs
           from the unit <hours> of the input dataset <model>
    t.rast.aggregate.ds failed
    ```

### Aggregate to intervals that restart every year

Satellite products such as MODIS cut each year into intervals of equal length
that start again on 1 January, so the last interval of a year is shorter. The
example scales this down: eight daily maps from 28 December 2026 to 4 January
2027 with the values 1 to 8, and a sampler with the intervals 28 to 31
December, the single day of 31 December, 1 to 4 January and 4 to 7 January.
The map of 31 December has the start and the end of the second interval, so
the sampling is `contains,equal`. The sums are 1 + 2 + 3 = 6, 4, 5 + 6 + 7 =
18 and 8. The names carry the start of each interval.

=== "Command line"

    ```sh
    for day in 1 2 3 4 5 6 7 8; do
        r.mapcalc expression="turn_$day = $day"
    done
    t.create output=turn title="Year change" \
        description="Eight daily maps over the end of a year"
    t.register -i input=turn \
        maps=turn_1,turn_2,turn_3,turn_4,turn_5,turn_6,turn_7,turn_8 \
        start=2026-12-28 increment="1 day"
    t.create output=turn_seeds title="Seeds" \
        description="Intervals that restart on 1 January"
    for seed in "1 2026-12-28 2026-12-31" "2 2026-12-31 2027-01-01" \
        "3 2027-01-01 2027-01-04" "4 2027-01-04 2027-01-07"; do
        set -- $seed
        r.mapcalc expression="seed_$1 = $1"
        t.register input=turn_seeds maps=seed_$1 start=$2 end=$3
    done
    t.rast.aggregate.ds input=turn sample=turn_seeds output=turn_sum \
        basename=turn_sum method=sum sampling=contains,equal
    t.rast.list input=turn_sum columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    turn_sum_2026_12_28|2026-12-28 00:00:00|2026-12-31 00:00:00|6.0
    turn_sum_2026_12_31|2026-12-31 00:00:00|2027-01-01 00:00:00|4.0
    turn_sum_2027_01_01|2027-01-01 00:00:00|2027-01-04 00:00:00|18.0
    turn_sum_2027_01_04|2027-01-04 00:00:00|2027-01-07 00:00:00|8.0
    ```

=== "Python (grass.tools)"

    ```python
    for day in range(1, 9):
        tools.r_mapcalc(expression=f"turn_{day} = {day}")
    tools.t_create(
        output="turn",
        title="Year change",
        description="Eight daily maps over the end of a year",
    )
    tools.t_register(
        input="turn",
        maps="turn_1,turn_2,turn_3,turn_4,turn_5,turn_6,turn_7,turn_8",
        start="2026-12-28",
        increment="1 day",
        flags="i",
    )
    tools.t_create(
        output="turn_seeds",
        title="Seeds",
        description="Intervals that restart on 1 January",
    )
    for number, start, end in (
        (1, "2026-12-28", "2026-12-31"),
        (2, "2026-12-31", "2027-01-01"),
        (3, "2027-01-01", "2027-01-04"),
        (4, "2027-01-04", "2027-01-07"),
    ):
        tools.r_mapcalc(expression=f"seed_{number} = {number}")
        tools.t_register(input="turn_seeds", maps=f"seed_{number}", start=start, end=end)
    tools.t_rast_aggregate_ds(
        input="turn",
        sample="turn_seeds",
        output="turn_sum",
        basename="turn_sum",
        method="sum",
        sampling="contains,equal",
    )
    print(tools.t_rast_list(input="turn_sum", columns="name,start_time,end_time,min").text)
    ```

    ```text
    name|start_time|end_time|min
    turn_sum_2026_12_28|2026-12-28 00:00:00|2026-12-31 00:00:00|6.0
    turn_sum_2026_12_31|2026-12-31 00:00:00|2027-01-01 00:00:00|4.0
    turn_sum_2027_01_01|2027-01-01 00:00:00|2027-01-04 00:00:00|18.0
    turn_sum_2027_01_04|2027-01-04 00:00:00|2027-01-07 00:00:00|8.0
    ```

### Aggregate in a smaller region

The new maps cover the current computational region at the time of the run.
The region is reduced to the northern row of the maps, and the aggregation of
the first example is repeated. The map has one row and three columns. The
region is then set back for the next example.

=== "Command line"

    ```sh
    g.region n=1 s=0 e=3 w=0 res=1
    t.rast.aggregate.ds input=rain sample=periods output=rain_small \
        basename=rain_small method=sum
    r.info -g map=rain_small_2026_06_01
    g.region n=2 s=0 e=3 w=0 res=1
    ```

    ```text
    north=1
    south=0
    east=3
    west=0
    nsres=1
    ewres=1
    rows=1
    cols=3
    cells=3
    datatype=DCELL
    ncats=0
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=1, s=0, e=3, w=0, res=1)
    tools.t_rast_aggregate_ds(
        input="rain",
        sample="periods",
        output="rain_small",
        basename="rain_small",
        method="sum",
    )
    print(tools.r_info(map="rain_small_2026_06_01", flags="g").text)
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    ```

    ```text
    north=1
    south=0
    east=3
    west=0
    nsres=1
    ewres=1
    rows=1
    cols=3
    cells=3
    datatype=DCELL
    ncats=0
    ```

### Use datasets of another mapset

The tool reads datasets of other mapsets and creates the new dataset and its
maps in the current mapset. The example creates the mapset `analysis` and
switches to it. The datasets `rain` and `periods` stay in `PERMANENT` and are
named with their mapset. The listing shows the new maps in `analysis`.

=== "Command line"

    ```sh
    g.mapset -c mapset=analysis
    g.region n=2 s=0 e=3 w=0 res=1
    t.rast.aggregate.ds input=rain@PERMANENT sample=periods@PERMANENT \
        output=rain_analysis basename=rain_analysis method=sum
    t.rast.list input=rain_analysis columns=name,mapset,start_time,min
    ```

    ```text
    name|mapset|start_time|min
    rain_analysis_2026_06_01|analysis|2026-06-01 00:00:00|3.0
    rain_analysis_2026_06_06|analysis|2026-06-06 00:00:00|13.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="analysis", flags="c")
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    tools.t_rast_aggregate_ds(
        input="rain@PERMANENT",
        sample="periods@PERMANENT",
        output="rain_analysis",
        basename="rain_analysis",
        method="sum",
    )
    print(
        tools.t_rast_list(input="rain_analysis", columns="name,mapset,start_time,min").text
    )
    ```

    ```text
    name|mapset|start_time|min
    rain_analysis_2026_06_01|analysis|2026-06-01 00:00:00|3.0
    rain_analysis_2026_06_06|analysis|2026-06-06 00:00:00|13.0
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[r.series](r.series.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.aggregate](t.rast.aggregate.md), [t.rast.list](t.rast.list.md),
[t.register](t.register.md), [t.sample](t.sample.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
