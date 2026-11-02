## DESCRIPTION

*t.rast3d.mapcalc* computes new 3D raster maps from the maps of one or more
space time 3D raster datasets and registers them in a new space time 3D raster
dataset. It runs *[r3.mapcalc](r3.mapcalc.md)* once for each time step and
adds the temporal variables `td()`, `start_time()`, `end_time()` and, for
absolute time, the calendar functions `start_doy()`, `end_month()` and others
to the expression. Use it when the result of a time step depends on maps of
several datasets, on the time of the step, or on both. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. *[t.rast.mapcalc](t.rast.mapcalc.md)* does the same for space time
raster datasets, *[t.rast3d.algebra](t.rast3d.algebra.md)* computes with the
temporal algebra, and *[t.rast3d.list](t.rast3d.list.md)* lists the maps of the
result.

### Datasets and time steps

The option **inputs** lists the datasets whose maps the **expression** uses.
The first dataset of the list is the sampler: every map of it is one time step,
which this manual calls a granule. Each of the other datasets is sampled by
the granules: for each granule, the tool looks for the map of the dataset that
is related to the granule in time, as the option **method** says. A granule
for which one of the datasets has no related map is skipped. The order of the
datasets in the expression does not matter, only their order in **inputs**. If
the list names only one dataset, every map of it is a granule. The datasets may
be in other mapsets (`soil@PERMANENT`); the expression then still uses the name
without the mapset.

The result dataset is the option **output**. It always belongs to the current
mapset, and so do the new maps. It takes the temporal type and the semantic type
of the first dataset of **inputs**. Each new map has the start and end time of
its granule. An existing dataset **output** is refused unless the flag
**--overwrite** is given; then it is replaced, and the tool warns that it
unregisters all maps of the old dataset.

The tool computes in the current 3D region, as *r3.mapcalc* does. A map that
lies outside the region reads as null.

### The expression

The option **expression** is the right side of an *r3.mapcalc* expression,
without the `map =` of a full one. In it, the name of each dataset of **inputs**
stands for the related map of the current granule, so `soil * weight`
multiplies the map of `soil` by the related map of `weight`, and
`weight * soil` does the same. Any other 3D raster map can be used by its
name. The operators and functions of *r3.mapcalc* are available.

The tool puts the names of the maps into the text of the expression and
numbers the results, so a call with four granules runs four statements such as
`doubled_1=soil_1*2`. Because the replacement works on the text, a dataset
name must not occur anywhere else in the expression, neither in a function name
(a dataset `day` breaks `start_day()`) nor in another dataset name (`soil`
breaks `soil_deep`); see the ninth example.

The option **basename** is required. The new maps are named after it, followed
by an underscore and the number of their granule, counted from 1 in the order
of the sampler. The number has as many digits as the number of granules
needs, filled up with zeros: `doubled_1` for four granules, `doubled_01` for
eleven. A granule that is skipped, or whose result is empty, leaves a gap in
the numbers.

### Temporal variables

The following variables are replaced by a number for each granule before the
expression goes to *r3.mapcalc*. They work with absolute and with relative
time.

- `td()`: the length of the granule, the end minus the start, in days and
  fractions of days for absolute time, in the unit of the dataset for relative
  time; null for a time instant.
- `start_time()`: the start of the granule minus the start of the first
  granule, in days or in the unit.
- `end_time()`: the end of the granule minus the start of the first granule, in
  days or in the unit; null for a time instant, which has no end.

For absolute time, the calendar functions give a part of the start or the end
of the granule as a whole number. Each function exists for the start
(`start_doy()`) and for the end (`end_doy()`) of the granule, and the end
functions are null for a time instant.

- `start_doy()`: the day of the year, 1 to 366.
- `start_dow()`: the day of the week, 1 to 7; Monday is 1.
- `start_year()`: the year.
- `start_month()`: the month, 1 to 12.
- `start_week()`: the ISO week of the year. Weeks start on Monday, and the
  first days of January can belong to week 52 or 53.
- `start_day()`: the day of the month, 1 to 31.
- `start_hour()`: the hour, 0 to 23.
- `start_minute()`: the minute, 0 to 59.
- `start_second()`: the second, 0 to 59.

With relative time, a calendar function stops the tool with an error.

### Select the related maps

The option **method** is a list of the sampling methods. It names the relation
between the granule and the map of another dataset. The default is
`during,overlap,contain,equal`. A map is related to the granule if it has one of
the listed relations. The third example shows the methods.

- `equal`: the map has the start and the end time of the granule.
- `during`: the granule lies inside the time interval of the map. The map may
  share the start or the end of the granule, but is not equal to it: for a
  granule from 10 to 20 the maps from 5 to 25, from 10 to 25 and from 5 to 20.
- `contain`: the map lies inside the granule.
- `overlap`: the map starts inside the granule and ends after it, or starts
  before it and ends inside it.
- `follows`: the map ends when the granule starts.
- `precedes`: the map starts when the granule ends.
- `start`: the maps that lie inside the granule, the maps that start before it
  and end inside it, and the maps that cover it while sharing its start or its
  end. It does not take the equal map, a map that covers the granule strictly
  and a map that starts inside it and ends after it. The temporal topology names
  the relations of this group `overlapped`, `starts`, `started`, `finishes` and
  `contains`.

If more than one map of a dataset is related to a granule, the tool warns on
the standard error and uses only one of them. Which one, follows from the
order in which it tries the relations. First come the methods `equal`,
`during`, `follows` and `precedes`, in the order of the list **method**; then
the group `start`, then `overlap` and then `contain`, if they are in the list.
Within one relation, the map with the earliest start time is taken, and for
equal start times the map with the smaller id. So for the list
`contain,during` a map found by `during` wins over a map found by `contain`.
The fourth example shows this. Choose the first dataset of **inputs** so that
its granules are the time steps you want, and use
*[t.rast.aggregate.ds](t.rast.aggregate.ds.md)* to make datasets with one map
per step.

### Empty results and spatial relation

A new map that has no valid cell, that is, no minimum and no maximum, is empty.
By default it is not registered in **output** and is removed after the run. The
flag **-n** registers the empty maps and keeps them. An expression such as
`if(soil > 15, soil, null())` selects time steps by values in this way. If all
results are empty, **output** exists but holds no map.

The flag **-s** adds a spatial condition to the temporal one: a map is related
to the granule only if its 2D extent, from west to east and from south to north,
touches or overlaps that of the granule, so a shared edge counts. The vertical
extent is not compared. A granule without a related map is skipped. The eighth
example shows the difference.

### Parallel processing

The option **nprocs** sets the number of *r3.mapcalc* processes that run at
the same time. The default is `1`. The result does not depend on it.

## NOTES

*t.rast3d.mapcalc* has the same options as *t.rast.mapcalc*, except for
**where**, and works on 3D rasters only. The maps of the datasets are not
touched; the tool makes new maps.

If a map of the base name exists as a registered map and **--overwrite** is not
given, the tool stops before it computes any map, with "Map ... is already in
temporal database, use overwrite flag to overwrite". If the dataset **output**
exists, the tool stops with "Space time raster3d dataset ... is already in the
database. Use the overwrite flag.".

With **--overwrite**, the maps of the old dataset are unregistered from it, not
removed. A new run with fewer maps leaves the surplus old maps in the mapset;
the tenth example shows it.

The tool stops with an error if an input dataset does not exist ("Space time
dataset ... of type str3ds not found"), if **method** names a method that does
not exist ("Value ... out of range for parameter method"), and if *r3.mapcalc*
does not accept the expression ("Error while mapcalc computation"). A
calendar function with relative time stops it with
`The temporal operators <start_*> support only absolute time.` (`<end_*>` for
an end function). The tool announces its steps
on the standard error with "Starting temporal sampling..." (with **-s**:
"Starting spatio-temporal sampling...") and "Starting mapcalc
computation...".

Because the tool replaces the names as text, two datasets whose names share a
start, such as `soil` and `soil_deep`, cannot be used together in one call, in
whatever order they are listed. Copy one of them with *[t.copy](t.copy.md)*
under another name, as the ninth example shows.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Apply an expression to every map

The dataset `soil` has four maps for the days from 1 to 4 March 2026. The
region from `g.region` is two by two cells wide and, with `t=2`, `b=0` and
`tbres=1`, two layers high, and `depth()` counts the layers from 1. So the
maps have two layers of two by two voxels, and their values are the layer
number (1 and 2) plus 0, 10, 20 and 30, so the smallest and largest values
are 1 and 2, 11 and 12, 21 and 22, and 31 and 32.

The first block doubles the maps. The name `soil` in the expression stands for
the map of each day. The new maps are named `doubled_1` to `doubled_4` after
the granules, and each has the time of its source map. **nprocs** lets two
*r3.mapcalc* processes run at the same time; the result is the same as with
one. The values are twice those of the source maps. The second block shows
what the new dataset takes from `soil`: the temporal type and the semantic
type, and the granularity that follows from the maps it holds.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=2 w=0 t=2 b=0 res=1 res3=1 tbres=1
    for step in 1 2 3 4; do
        r3.mapcalc expression="soil_$step = depth() + 10 * ($step - 1)"
    done
    t.create type=str3ds output=soil title="Soil" \
        description="Soil temperature in two layers"
    t.register -i type=raster_3d input=soil \
        maps=soil_1,soil_2,soil_3,soil_4 start=2026-03-01 increment="1 day"
    t.rast3d.mapcalc inputs=soil output=doubled basename=doubled \
        expression="soil * 2" nprocs=2
    t.rast3d.list input=doubled columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    doubled_1|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|4.0
    doubled_2|2026-03-02 00:00:00|2026-03-03 00:00:00|22.0|24.0
    doubled_3|2026-03-03 00:00:00|2026-03-04 00:00:00|42.0|44.0
    doubled_4|2026-03-04 00:00:00|2026-03-05 00:00:00|62.0|64.0
    ```

    ```sh
    t.info -g type=str3ds input=doubled | grep -E "^(temporal_type|semantic_type|granularity)="
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    granularity='1 day'
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=2, w=0, t=2, b=0, res=1, res3=1, tbres=1)
    for step in range(1, 5):
        tools.r3_mapcalc(expression=f"soil_{step} = depth() + 10 * ({step} - 1)")
    tools.t_create(
        type="str3ds",
        output="soil",
        title="Soil",
        description="Soil temperature in two layers",
    )
    tools.t_register(
        type="raster_3d",
        input="soil",
        maps="soil_1,soil_2,soil_3,soil_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast3d_mapcalc(
        inputs="soil", output="doubled", basename="doubled", expression="soil * 2", nprocs=2
    )
    print(
        tools.t_rast3d_list(
            input="doubled", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    doubled_1|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|4.0
    doubled_2|2026-03-02 00:00:00|2026-03-03 00:00:00|22.0|24.0
    doubled_3|2026-03-03 00:00:00|2026-03-04 00:00:00|42.0|44.0
    doubled_4|2026-03-04 00:00:00|2026-03-05 00:00:00|62.0|64.0
    ```

    ```python
    info = tools.t_info(type="str3ds", input="doubled", flags="g").keyval
    for key in ("temporal_type", "semantic_type", "granularity"):
        print(f"{key}={info[key]}")
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    granularity='1 day'
    ```

### Combine the maps of several datasets

The dataset `weight` has two maps, each for two days: `weight_1` with the value
2 for 1 and 2 March, `weight_2` with the value 3 for 3 and 4 March. The first
block multiplies `soil` by `weight`; the expression names `weight` first, which
does not matter. The first dataset of **inputs** is the
sampler, so the result has four maps of one day each, and each day of `soil`
lies during a map of `weight`. The values are twice those of `soil` for the
first two days and three times for the last two: 2 and 4, 22 and 24, 63 and
66, 93 and 96.

The second block swaps the order in **inputs**, so the sampler is `weight` and
the result has two maps of two days each. Each granule of `weight` contains two
maps of `soil`; the tool warns on the standard error and uses the first of
them. The result is the value of `weight` plus the first map of `soil`: 3 and 4
for the first two days (2 plus 1 and 2), 24 and 25 for the last two (3 plus 21
and 22).

=== "Command line"

    ```sh
    r3.mapcalc expression="weight_1 = 2"
    r3.mapcalc expression="weight_2 = 3"
    t.create type=str3ds output=weight title="Weight" \
        description="Factor for two days each"
    t.register -i type=raster_3d input=weight maps=weight_1,weight_2 \
        start=2026-03-01 increment="2 days"
    t.rast3d.mapcalc inputs=soil,weight output=weighted basename=weighted \
        expression="weight * soil"
    t.rast3d.list input=weighted columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    weighted_1|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|4.0
    weighted_2|2026-03-02 00:00:00|2026-03-03 00:00:00|22.0|24.0
    weighted_3|2026-03-03 00:00:00|2026-03-04 00:00:00|63.0|66.0
    weighted_4|2026-03-04 00:00:00|2026-03-05 00:00:00|93.0|96.0
    ```

    ```sh
    t.rast3d.mapcalc inputs=weight,soil output=summed basename=summed \
        expression="weight + soil"
    t.rast3d.list input=summed columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    summed_1|2026-03-01 00:00:00|2026-03-03 00:00:00|3.0|4.0
    summed_2|2026-03-03 00:00:00|2026-03-05 00:00:00|24.0|25.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(expression="weight_1 = 2")
    tools.r3_mapcalc(expression="weight_2 = 3")
    tools.t_create(
        type="str3ds",
        output="weight",
        title="Weight",
        description="Factor for two days each",
    )
    tools.t_register(
        type="raster_3d",
        input="weight",
        maps="weight_1,weight_2",
        start="2026-03-01",
        increment="2 days",
        flags="i",
    )
    tools.t_rast3d_mapcalc(
        inputs="soil,weight",
        output="weighted",
        basename="weighted",
        expression="weight * soil",
    )
    print(
        tools.t_rast3d_list(
            input="weighted", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    weighted_1|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|4.0
    weighted_2|2026-03-02 00:00:00|2026-03-03 00:00:00|22.0|24.0
    weighted_3|2026-03-03 00:00:00|2026-03-04 00:00:00|63.0|66.0
    weighted_4|2026-03-04 00:00:00|2026-03-05 00:00:00|93.0|96.0
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="weight,soil",
        output="summed",
        basename="summed",
        expression="weight + soil",
    )
    print(
        tools.t_rast3d_list(input="summed", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    summed_1|2026-03-01 00:00:00|2026-03-03 00:00:00|3.0|4.0
    summed_2|2026-03-03 00:00:00|2026-03-05 00:00:00|24.0|25.0
    ```

### Choose the sampling method

The dataset `slots` has nine granules of 10 days with relative time, from day
110 to 120, from 210 to 220 and so on up to 910 to 920. Its map `slot_k` has the
value `k`. The dataset `probes` has one map for each granule, `probe_k` with the
value `10 * k`, and each has a different position relative to the granule:

1. `probe_1` has the same times, 110 to 120.
2. `probe_2` lies inside the granule, 214 to 218.
3. `probe_3` covers the granule, 305 to 325.
4. `probe_4` starts inside the granule and ends after it, 415 to 425.
5. `probe_5` starts before the granule and ends inside it, 505 to 515.
6. `probe_6` ends when the granule starts, 600 to 610.
7. `probe_7` starts when the granule ends, 720 to 730.
8. `probe_8` starts with the granule and ends after it, 810 to 825.
9. `probe_9` starts before the granule and ends with it, 905 to 920.

The loop runs the tool once for each method and prints the maps of the result.
The number at the end of a name is the number of the granule that found a
related map: `equal` finds the map of granule 1, `during` the ones of the
granules 3, 8 and 9, `contain` granule 2, `overlap` the granules 4 and 5,
`follows` granule 6 and `precedes` granule 7. The method `start` finds the
granules 2, 5, 8 and 9. The last block uses no **method**, so the default
`during,overlap,contain,equal` finds the granules 1 to 5, 8 and 9, and the
listing shows that the maps have the times of the granules.

The time of the datasets is relative, in days, and the result takes it over.
The files for *[t.register](t.register.md)* list one map per line with its
start and end time.

=== "Command line"

    ```sh
    for step in 1 2 3 4 5 6 7 8 9; do
        r3.mapcalc expression="slot_$step = $step"
        r3.mapcalc expression="probe_$step = 10 * $step"
    done
    cat > slots.txt <<EOF
    slot_1|110|120
    slot_2|210|220
    slot_3|310|320
    slot_4|410|420
    slot_5|510|520
    slot_6|610|620
    slot_7|710|720
    slot_8|810|820
    slot_9|910|920
    EOF
    cat > probes.txt <<EOF
    probe_1|110|120
    probe_2|214|218
    probe_3|305|325
    probe_4|415|425
    probe_5|505|515
    probe_6|600|610
    probe_7|720|730
    probe_8|810|825
    probe_9|905|920
    EOF
    t.create type=str3ds temporaltype=relative output=slots title="Slots" \
        description="Granules of 10 days"
    t.create type=str3ds temporaltype=relative output=probes title="Probes" \
        description="One probe for each granule"
    t.register type=raster_3d input=slots unit=days file=slots.txt
    t.register type=raster_3d input=probes unit=days file=probes.txt
    for method in equal during contain overlap follows precedes start; do
        t.rast3d.mapcalc inputs=slots,probes output=by_$method \
            basename=$method expression="slots + probes" method=$method
        names=$(t.rast3d.list -s input=by_$method columns=name method=comma)
        echo "$method: $names"
    done
    ```

    ```text
    equal: equal_1
    during: during_3,during_8,during_9
    contain: contain_2
    overlap: overlap_4,overlap_5
    follows: follows_6
    precedes: precedes_7
    start: start_2,start_5,start_8,start_9
    ```

    ```sh
    t.rast3d.mapcalc inputs=slots,probes output=by_default basename=default \
        expression="slots + probes"
    t.rast3d.list input=by_default columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    default_1|110|120|11.0|11.0
    default_2|210|220|22.0|22.0
    default_3|310|320|33.0|33.0
    default_4|410|420|44.0|44.0
    default_5|510|520|55.0|55.0
    default_8|810|820|88.0|88.0
    default_9|910|920|99.0|99.0
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    for step in range(1, 10):
        tools.r3_mapcalc(expression=f"slot_{step} = {step}")
        tools.r3_mapcalc(expression=f"probe_{step} = 10 * {step}")
    Path("slots.txt").write_text(
        "slot_1|110|120\nslot_2|210|220\nslot_3|310|320\nslot_4|410|420\n"
        "slot_5|510|520\nslot_6|610|620\nslot_7|710|720\nslot_8|810|820\n"
        "slot_9|910|920\n"
    )
    Path("probes.txt").write_text(
        "probe_1|110|120\nprobe_2|214|218\nprobe_3|305|325\nprobe_4|415|425\n"
        "probe_5|505|515\nprobe_6|600|610\nprobe_7|720|730\nprobe_8|810|825\n"
        "probe_9|905|920\n"
    )
    tools.t_create(
        type="str3ds",
        temporaltype="relative",
        output="slots",
        title="Slots",
        description="Granules of 10 days",
    )
    tools.t_create(
        type="str3ds",
        temporaltype="relative",
        output="probes",
        title="Probes",
        description="One probe for each granule",
    )
    tools.t_register(type="raster_3d", input="slots", unit="days", file="slots.txt")
    tools.t_register(type="raster_3d", input="probes", unit="days", file="probes.txt")
    for method in ("equal", "during", "contain", "overlap", "follows", "precedes", "start"):
        tools.t_rast3d_mapcalc(
            inputs="slots,probes",
            output=f"by_{method}",
            basename=method,
            expression="slots + probes",
            method=method,
        )
        names = tools.t_rast3d_list(
            input=f"by_{method}", columns="name", method="comma", flags="s"
        ).text
        print(f"{method}: {names}")
    ```

    ```text
    equal: equal_1
    during: during_3,during_8,during_9
    contain: contain_2
    overlap: overlap_4,overlap_5
    follows: follows_6
    precedes: precedes_7
    start: start_2,start_5,start_8,start_9
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="slots,probes",
        output="by_default",
        basename="default",
        expression="slots + probes",
    )
    print(
        tools.t_rast3d_list(
            input="by_default", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    default_1|110|120|11.0|11.0
    default_2|210|220|22.0|22.0
    default_3|310|320|33.0|33.0
    default_4|410|420|44.0|44.0
    default_5|510|520|55.0|55.0
    default_8|810|820|88.0|88.0
    default_9|910|920|99.0|99.0
    ```

### Several related maps for one granule

The dataset `window` has one map of 10 days, from day 10 to 20, with the
value 1. The dataset `cands` has four maps that are all related to it, in
different ways: `cand_a` from 12 to 18 with the value 100 (inside the granule),
`cand_b` from 5 to 25 with the value 200 (covers it), `cand_c` from 11 to 13
with the value 300 (inside, and starts before `cand_a`) and `cand_d` from 10 to
20 with the value 400 (equal).

The expression is only `cands`, so the result holds the value of the map the
tool took. The loop prints it for four lists of methods. With the default
`during,overlap,contain,equal` it is 200: `during` comes before `contain` and
`equal` and finds `cand_b`. With `contain,during` it is 200 as well, because
the order of the list only counts for `equal`, `during`, `follows` and
`precedes`, and `contain` is tried after them. With `equal,during,contain` it
is 400, because `equal` is first. With `contain` alone it is 300: of the maps
inside the granule, `cand_c` starts first. The tool warns on the standard
error when it chooses between maps.

=== "Command line"

    ```sh
    r3.mapcalc expression="window_1 = 1"
    r3.mapcalc expression="cand_a = 100"
    r3.mapcalc expression="cand_b = 200"
    r3.mapcalc expression="cand_c = 300"
    r3.mapcalc expression="cand_d = 400"
    cat > window.txt <<EOF
    window_1|10|20
    EOF
    cat > cands.txt <<EOF
    cand_a|12|18
    cand_b|5|25
    cand_c|11|13
    cand_d|10|20
    EOF
    t.create type=str3ds temporaltype=relative output=window title="Window" \
        description="One granule"
    t.create type=str3ds temporaltype=relative output=cands title="Candidates" \
        description="Four maps related to the granule"
    t.register type=raster_3d input=window unit=days file=window.txt
    t.register type=raster_3d input=cands unit=days file=cands.txt
    number=0
    for methods in during,overlap,contain,equal contain,during \
        equal,during,contain contain; do
        number=$((number + 1))
        t.rast3d.mapcalc inputs=window,cands output=taken_$number \
            basename=taken_$number expression="cands" method=$methods
        value=$(t.rast3d.list -s input=taken_$number columns=min)
        echo "$methods: $value"
    done
    ```

    ```text
    during,overlap,contain,equal: 200.0
    contain,during: 200.0
    equal,during,contain: 400.0
    contain: 300.0
    ```

=== "Python (grass.tools)"

    ```python
    for name, value in (("window_1", 1), ("cand_a", 100), ("cand_b", 200)):
        tools.r3_mapcalc(expression=f"{name} = {value}")
    tools.r3_mapcalc(expression="cand_c = 300")
    tools.r3_mapcalc(expression="cand_d = 400")
    Path("window.txt").write_text("window_1|10|20\n")
    Path("cands.txt").write_text("cand_a|12|18\ncand_b|5|25\ncand_c|11|13\ncand_d|10|20\n")
    tools.t_create(
        type="str3ds",
        temporaltype="relative",
        output="window",
        title="Window",
        description="One granule",
    )
    tools.t_create(
        type="str3ds",
        temporaltype="relative",
        output="cands",
        title="Candidates",
        description="Four maps related to the granule",
    )
    tools.t_register(type="raster_3d", input="window", unit="days", file="window.txt")
    tools.t_register(type="raster_3d", input="cands", unit="days", file="cands.txt")
    lists = (
        "during,overlap,contain,equal",
        "contain,during",
        "equal,during,contain",
        "contain",
    )
    for number, methods in enumerate(lists, start=1):
        tools.t_rast3d_mapcalc(
            inputs="window,cands",
            output=f"taken_{number}",
            basename=f"taken_{number}",
            expression="cands",
            method=methods,
        )
        value = tools.t_rast3d_list(input=f"taken_{number}", columns="min", flags="s").text
        print(f"{methods}: {value}")
    ```

    ```text
    during,overlap,contain,equal: 200.0
    contain,during: 200.0
    equal,during,contain: 400.0
    contain: 300.0
    ```

### Use the time of the granule

Back to `soil`. The expressions of the first four blocks need no map, only the
time of the granule, so they name `soil` only in **inputs**. The granules are
the days from 1 to 4 March 2026; 1 March 2026 is a Sunday, the 60th day of the
year.

The first block puts three variables into one number: `start_time()` counts the
hundreds, `td()` the tens and `end_time()` the ones. The days start 0, 1, 2 and
3 days after the first, are 1 day long and end 1, 2, 3 and 4 days after the
start of the first, so the results are 11, 112, 213 and 314. The second block
combines the day of the year and the day of the week, tens and ones again: 60
and 7 (Sunday) for the first day, then 61 and 1 (Monday) and so on, so 607, 611,
622 and 633. The third block gives the month and the day at the end: the month
is 3 and the end day is 2 to 5, so the results are 302 to 305. The fourth block
uses the weeks, which start on Monday: the first day starts in week 9 and ends
on Monday 2 March, in week 10, so 910, and 1010 for the other days.

The dataset `gauge` has two time instants, at 06:00 on 1 March and at 18:00 on 2
March, and its maps have the values 1 and 2. The last block shows what an
instant gets: `start_time()` is the offset in days and fractions of days from
the first instant, 0 and 1.5, and `end_time()` is null, so `isnull()` is true
and the result is 100 and 101.5. The next block shows that `td()` of an
instant is null as well: the result is 7.

The weeks are ISO weeks. The dataset `newyear` has one day, 1 January 2027,
which is a Friday in week 53 of 2026, and the last block gives `start_week()`
53.

=== "Command line"

    ```sh
    t.rast3d.mapcalc inputs=soil output=when basename=when \
        expression="start_time() * 100 + td() * 10 + end_time()"
    t.rast3d.list input=when columns=name,min,max
    ```

    ```text
    name|min|max
    when_1|11.0|11.0
    when_2|112.0|112.0
    when_3|213.0|213.0
    when_4|314.0|314.0
    ```

    ```sh
    t.rast3d.mapcalc inputs=soil output=calendar basename=calendar \
        expression="start_doy() * 10 + start_dow()"
    t.rast3d.list input=calendar columns=name,min,max
    ```

    ```text
    name|min|max
    calendar_1|607.0|607.0
    calendar_2|611.0|611.0
    calendar_3|622.0|622.0
    calendar_4|633.0|633.0
    ```

    ```sh
    t.rast3d.mapcalc inputs=soil output=month_day basename=month_day \
        expression="start_month() * 100 + end_day()"
    t.rast3d.list input=month_day columns=name,min,max
    ```

    ```text
    name|min|max
    month_day_1|302.0|302.0
    month_day_2|303.0|303.0
    month_day_3|304.0|304.0
    month_day_4|305.0|305.0
    ```

    ```sh
    t.rast3d.mapcalc inputs=soil output=weeks basename=weeks \
        expression="start_week() * 100 + end_week()"
    t.rast3d.list input=weeks columns=name,min,max
    ```

    ```text
    name|min|max
    weeks_1|910.0|910.0
    weeks_2|1010.0|1010.0
    weeks_3|1010.0|1010.0
    weeks_4|1010.0|1010.0
    ```

    ```sh
    r3.mapcalc expression="gauge_1 = 1"
    r3.mapcalc expression="gauge_2 = 2"
    t.create type=str3ds output=gauge title="Gauge" description="Two instants"
    t.register type=raster_3d input=gauge maps=gauge_1 start="2026-03-01 06:00:00"
    t.register type=raster_3d input=gauge maps=gauge_2 start="2026-03-02 18:00:00"
    t.rast3d.mapcalc inputs=gauge output=instants basename=instants \
        expression="start_time() + if(isnull(end_time()), 100, 0)"
    t.rast3d.list input=instants columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    instants_1|2026-03-01 06:00:00|None|100.0|100.0
    instants_2|2026-03-02 18:00:00|None|101.5|101.5
    ```

    ```sh
    t.rast3d.mapcalc inputs=gauge output=lengths basename=lengths \
        expression="if(isnull(td()), 7, 0)"
    t.rast3d.list input=lengths columns=name,min,max
    ```

    ```text
    name|min|max
    lengths_1|7.0|7.0
    lengths_2|7.0|7.0
    ```

    ```sh
    r3.mapcalc expression="newyear_1 = 1"
    t.create type=str3ds output=newyear title="New year" description="One day"
    t.register type=raster_3d input=newyear maps=newyear_1 \
        start=2027-01-01 end=2027-01-02
    t.rast3d.mapcalc inputs=newyear output=iso basename=iso \
        expression="start_week()"
    t.rast3d.list input=iso columns=name,min,max
    ```

    ```text
    name|min|max
    iso_1|53.0|53.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast3d_mapcalc(
        inputs="soil",
        output="when",
        basename="when",
        expression="start_time() * 100 + td() * 10 + end_time()",
    )
    print(tools.t_rast3d_list(input="when", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    when_1|11.0|11.0
    when_2|112.0|112.0
    when_3|213.0|213.0
    when_4|314.0|314.0
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="soil",
        output="calendar",
        basename="calendar",
        expression="start_doy() * 10 + start_dow()",
    )
    print(tools.t_rast3d_list(input="calendar", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    calendar_1|607.0|607.0
    calendar_2|611.0|611.0
    calendar_3|622.0|622.0
    calendar_4|633.0|633.0
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="soil",
        output="month_day",
        basename="month_day",
        expression="start_month() * 100 + end_day()",
    )
    print(tools.t_rast3d_list(input="month_day", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    month_day_1|302.0|302.0
    month_day_2|303.0|303.0
    month_day_3|304.0|304.0
    month_day_4|305.0|305.0
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="soil",
        output="weeks",
        basename="weeks",
        expression="start_week() * 100 + end_week()",
    )
    print(tools.t_rast3d_list(input="weeks", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    weeks_1|910.0|910.0
    weeks_2|1010.0|1010.0
    weeks_3|1010.0|1010.0
    weeks_4|1010.0|1010.0
    ```

    ```python
    tools.r3_mapcalc(expression="gauge_1 = 1")
    tools.r3_mapcalc(expression="gauge_2 = 2")
    tools.t_create(type="str3ds", output="gauge", title="Gauge", description="Two instants")
    tools.t_register(
        type="raster_3d", input="gauge", maps="gauge_1", start="2026-03-01 06:00:00"
    )
    tools.t_register(
        type="raster_3d", input="gauge", maps="gauge_2", start="2026-03-02 18:00:00"
    )
    tools.t_rast3d_mapcalc(
        inputs="gauge",
        output="instants",
        basename="instants",
        expression="start_time() + if(isnull(end_time()), 100, 0)",
    )
    print(
        tools.t_rast3d_list(
            input="instants", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    instants_1|2026-03-01 06:00:00|None|100.0|100.0
    instants_2|2026-03-02 18:00:00|None|101.5|101.5
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="gauge",
        output="lengths",
        basename="lengths",
        expression="if(isnull(td()), 7, 0)",
    )
    print(tools.t_rast3d_list(input="lengths", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    lengths_1|7.0|7.0
    lengths_2|7.0|7.0
    ```

    ```python
    tools.r3_mapcalc(expression="newyear_1 = 1")
    tools.t_create(type="str3ds", output="newyear", title="New year", description="One day")
    tools.t_register(
        type="raster_3d",
        input="newyear",
        maps="newyear_1",
        start="2027-01-01",
        end="2027-01-02",
    )
    tools.t_rast3d_mapcalc(
        inputs="newyear", output="iso", basename="iso", expression="start_week()"
    )
    print(tools.t_rast3d_list(input="iso", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    iso_1|53.0|53.0
    ```

### Use the time of a dataset with relative time

The dataset `model` has three steps of 5 hours with relative time. `start_time()`,
`td()` and `end_time()` give numbers in the unit of the dataset, hours: the
steps start 0, 5 and 10 hours after the first, are 5 hours long and end 5, 10
and 15 hours after the start of the first. With the expression of the first
example of the previous section, the results are 55, 560 and 1065.

The calendar functions need absolute time. The second block calls
`start_doy()` on `model`; the tool prints its error and stops without a result
dataset. The block shows the error and then prints `t.rast3d.mapcalc failed`.

=== "Command line"

    ```sh
    for step in 1 2 3; do
        r3.mapcalc expression="step_$step = depth() + 10 * ($step - 1)"
    done
    t.create type=str3ds temporaltype=relative output=model title="Model" \
        description="Model output every 5 hours"
    t.register -i type=raster_3d input=model maps=step_1,step_2,step_3 \
        start=0 increment=5 unit=hours
    t.rast3d.mapcalc inputs=model output=elapsed basename=elapsed \
        expression="start_time() * 100 + td() * 10 + end_time()"
    t.rast3d.list input=elapsed columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    elapsed_1|0|5|55.0|55.0
    elapsed_2|5|10|560.0|560.0
    elapsed_3|10|15|1065.0|1065.0
    ```

    ```sh
    if ! t.rast3d.mapcalc inputs=model output=bad basename=bad \
        expression="start_doy()" 2>&1; then
        echo "t.rast3d.mapcalc failed"
    fi
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    ERROR: The temporal operators <start_*> support only absolute time.
    t.rast3d.mapcalc failed
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    for step in range(1, 4):
        tools.r3_mapcalc(expression=f"step_{step} = depth() + 10 * ({step} - 1)")
    tools.t_create(
        type="str3ds",
        temporaltype="relative",
        output="model",
        title="Model",
        description="Model output every 5 hours",
    )
    tools.t_register(
        type="raster_3d",
        input="model",
        maps="step_1,step_2,step_3",
        start=0,
        increment=5,
        unit="hours",
        flags="i",
    )
    tools.t_rast3d_mapcalc(
        inputs="model",
        output="elapsed",
        basename="elapsed",
        expression="start_time() * 100 + td() * 10 + end_time()",
    )
    print(
        tools.t_rast3d_list(
            input="elapsed", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    elapsed_1|0|5|55.0|55.0
    elapsed_2|5|10|560.0|560.0
    elapsed_3|10|15|1065.0|1065.0
    ```

    ```python
    try:
        tools.t_rast3d_mapcalc(
            inputs="model", output="bad", basename="bad", expression="start_doy()"
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast3d.mapcalc failed")
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    ERROR: The temporal operators <start_*> support only absolute time.
    t.rast3d.mapcalc failed
    ```

### Keep or drop empty results

An expression that sets voxels to null selects time steps by their values.
The first block keeps the values of `soil` above 15, so the maps of the
first two days (with the largest values 2 and 12) have no valid voxel left. They
are not registered in `warm`, and the second block shows that they are removed
from the mapset. The new maps `warm_3` and `warm_4` keep the numbers of their
granules.

The third block runs the call again with **-n**. The dataset `warm_all`
registers the empty maps as well, with `None` as their smallest and largest
value, and the mapset keeps all four maps.

=== "Command line"

    ```sh
    t.rast3d.mapcalc inputs=soil output=warm basename=warm \
        expression="if(soil > 15, soil, null())"
    t.rast3d.list input=warm columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    warm_3|2026-03-03 00:00:00|21.0|22.0
    warm_4|2026-03-04 00:00:00|31.0|32.0
    ```

    ```sh
    g.list type=raster_3d pattern="warm*"
    ```

    ```text
    warm_3
    warm_4
    ```

    ```sh
    t.rast3d.mapcalc -n inputs=soil output=warm_all basename=warm_all \
        expression="if(soil > 15, soil, null())"
    t.rast3d.list input=warm_all columns=name,start_time,min,max
    g.list type=raster_3d pattern="warm_all*"
    ```

    ```text
    name|start_time|min|max
    warm_all_1|2026-03-01 00:00:00|None|None
    warm_all_2|2026-03-02 00:00:00|None|None
    warm_all_3|2026-03-03 00:00:00|21.0|22.0
    warm_all_4|2026-03-04 00:00:00|31.0|32.0
    warm_all_1
    warm_all_2
    warm_all_3
    warm_all_4
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast3d_mapcalc(
        inputs="soil",
        output="warm",
        basename="warm",
        expression="if(soil > 15, soil, null())",
    )
    print(tools.t_rast3d_list(input="warm", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    warm_3|2026-03-03 00:00:00|21.0|22.0
    warm_4|2026-03-04 00:00:00|31.0|32.0
    ```

    ```python
    print(tools.g_list(type="raster_3d", pattern="warm*").text)
    ```

    ```text
    warm_3
    warm_4
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="soil",
        output="warm_all",
        basename="warm_all",
        expression="if(soil > 15, soil, null())",
        flags="n",
    )
    print(tools.t_rast3d_list(input="warm_all", columns="name,start_time,min,max").text)
    print(tools.g_list(type="raster_3d", pattern="warm_all*").text)
    ```

    ```text
    name|start_time|min|max
    warm_all_1|2026-03-01 00:00:00|None|None
    warm_all_2|2026-03-02 00:00:00|None|None
    warm_all_3|2026-03-03 00:00:00|21.0|22.0
    warm_all_4|2026-03-04 00:00:00|31.0|32.0
    warm_all_1
    warm_all_2
    warm_all_3
    warm_all_4
    ```

### Take only the maps in the same place

The dataset `patch` has four maps for the days of `soil`, with the values
1000, 2000, 3000 and 4000. The second map `patch_2` lies next to the squares
of `soil`, from 2 to 4 in the east, so it shares an edge with them. The third
map `patch_3` was made far away, for the squares from 10 to 12. The other maps
lie in the squares from 0 to 2, like `soil`. The current region is the one from
0 to 2 again.

The first block adds `soil` and `patch`, with 100 where `patch` is null. The
maps `patch_2` and `patch_3` are related in time but read in the current region
where they have no data, so the result for the second and third day is the
value of `soil` plus 100: 111 and 112, and 121 and 122. The result of the other
days is `soil` plus `patch`: 1001 and 1002, and 4031 and 4032.

With **-s**, the second block takes only maps whose 2D extent touches or
overlaps that of the granule. `patch_2` touches it and stays, `patch_3` does
not, so the third granule is skipped, and the result has three maps with the
numbers 1, 2 and 4.

=== "Command line"

    ```sh
    for step in 1 2 3 4; do
        if [ $step = 2 ]; then
            g.region n=2 s=0 e=4 w=2 t=2 b=0 res=1 res3=1 tbres=1
        elif [ $step = 3 ]; then
            g.region n=12 s=10 e=12 w=10 t=2 b=0 res=1 res3=1 tbres=1
        fi
        r3.mapcalc expression="patch_$step = 1000 * $step"
        g.region n=2 s=0 e=2 w=0 t=2 b=0 res=1 res3=1 tbres=1
    done
    t.create type=str3ds output=patch title="Patch" description="Four patches"
    t.register -i type=raster_3d input=patch \
        maps=patch_1,patch_2,patch_3,patch_4 start=2026-03-01 increment="1 day"
    t.rast3d.mapcalc inputs=soil,patch output=near basename=near \
        expression="soil + if(isnull(patch), 100, patch)"
    t.rast3d.list input=near columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    near_1|2026-03-01 00:00:00|1001.0|1002.0
    near_2|2026-03-02 00:00:00|111.0|112.0
    near_3|2026-03-03 00:00:00|121.0|122.0
    near_4|2026-03-04 00:00:00|4031.0|4032.0
    ```

    ```sh
    t.rast3d.mapcalc -s inputs=soil,patch output=near_only basename=near_only \
        expression="soil + if(isnull(patch), 100, patch)"
    t.rast3d.list input=near_only columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    near_only_1|2026-03-01 00:00:00|1001.0|1002.0
    near_only_2|2026-03-02 00:00:00|111.0|112.0
    near_only_4|2026-03-04 00:00:00|4031.0|4032.0
    ```

=== "Python (grass.tools)"

    ```python
    for step in range(1, 5):
        if step == 2:
            tools.g_region(n=2, s=0, e=4, w=2, t=2, b=0, res=1, res3=1, tbres=1)
        elif step == 3:
            tools.g_region(n=12, s=10, e=12, w=10, t=2, b=0, res=1, res3=1, tbres=1)
        tools.r3_mapcalc(expression=f"patch_{step} = 1000 * {step}")
        tools.g_region(n=2, s=0, e=2, w=0, t=2, b=0, res=1, res3=1, tbres=1)
    tools.t_create(type="str3ds", output="patch", title="Patch", description="Four patches")
    tools.t_register(
        type="raster_3d",
        input="patch",
        maps="patch_1,patch_2,patch_3,patch_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast3d_mapcalc(
        inputs="soil,patch",
        output="near",
        basename="near",
        expression="soil + if(isnull(patch), 100, patch)",
    )
    print(tools.t_rast3d_list(input="near", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    near_1|2026-03-01 00:00:00|1001.0|1002.0
    near_2|2026-03-02 00:00:00|111.0|112.0
    near_3|2026-03-03 00:00:00|121.0|122.0
    near_4|2026-03-04 00:00:00|4031.0|4032.0
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="soil,patch",
        output="near_only",
        basename="near_only",
        expression="soil + if(isnull(patch), 100, patch)",
        flags="s",
    )
    print(tools.t_rast3d_list(input="near_only", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    near_only_1|2026-03-01 00:00:00|1001.0|1002.0
    near_only_2|2026-03-02 00:00:00|111.0|112.0
    near_only_4|2026-03-04 00:00:00|4031.0|4032.0
    ```

### Names of datasets in the expression

The tool replaces the name of a dataset in the text of the expression, so the
name must not appear elsewhere in it. The dataset `day` has one map. In
`day * start_day()` the replacement also changes `start_day()`, and
*r3.mapcalc* stops with the message that the function `start_day_1` is not
defined.

Two datasets whose names share a start have the same problem. The dataset
`soil_deep` has one map; `soil + soil_deep` becomes `soil_1+soil_1_deep`, and
*r3.mapcalc* does not know the map `soil_1_deep`.

Copy a dataset under another name with *t.copy*, and use the new name. The copy
holds the same maps, and the third block computes with it.

=== "Command line"

    ```sh
    r3.mapcalc expression="day_1 = 4"
    t.create type=str3ds output=day title="Day" description="One map"
    t.register type=raster_3d input=day maps=day_1 \
        start=2026-03-01 end=2026-03-02
    if ! t.rast3d.mapcalc inputs=day output=bad basename=bad \
        expression="day * start_day()" 2>&1; then
        echo "t.rast3d.mapcalc failed"
    fi
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    Undefined function 'start_day_1'
    Parse error
    ERROR: parse error
    ERROR: Error while mapcalc computation
    t.rast3d.mapcalc failed
    ```

    ```sh
    r3.mapcalc expression="soil_deep_1 = 3"
    t.create type=str3ds output=soil_deep title="Deep soil" \
        description="One map"
    t.register type=raster_3d input=soil_deep maps=soil_deep_1 \
        start=2026-03-01 end=2026-03-02
    if ! t.rast3d.mapcalc inputs=soil,soil_deep output=bad basename=bad \
        expression="soil + soil_deep" 2>&1; then
        echo "t.rast3d.mapcalc failed"
    fi
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    Invalid map <soil_1_deep>
    Parse error
    ERROR: parse error
    ERROR: Error while mapcalc computation
    t.rast3d.mapcalc failed
    ```

    ```sh
    t.copy type=str3ds input=day output=sunshine
    t.rast3d.mapcalc inputs=sunshine output=sunny basename=sunny \
        expression="sunshine * start_day()"
    t.rast3d.list input=sunny columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    sunny_1|2026-03-01 00:00:00|4.0|4.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(expression="day_1 = 4")
    tools.t_create(type="str3ds", output="day", title="Day", description="One map")
    tools.t_register(
        type="raster_3d", input="day", maps="day_1", start="2026-03-01", end="2026-03-02"
    )
    try:
        tools.t_rast3d_mapcalc(
            inputs="day", output="bad", basename="bad", expression="day * start_day()"
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast3d.mapcalc failed")
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    Undefined function 'start_day_1'
    Parse error
    ERROR: parse error
    ERROR: Error while mapcalc computation
    t.rast3d.mapcalc failed
    ```

    ```python
    tools.r3_mapcalc(expression="soil_deep_1 = 3")
    tools.t_create(
        type="str3ds", output="soil_deep", title="Deep soil", description="One map"
    )
    tools.t_register(
        type="raster_3d",
        input="soil_deep",
        maps="soil_deep_1",
        start="2026-03-01",
        end="2026-03-02",
    )
    try:
        tools.t_rast3d_mapcalc(
            inputs="soil,soil_deep",
            output="bad",
            basename="bad",
            expression="soil + soil_deep",
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast3d.mapcalc failed")
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    Invalid map <soil_1_deep>
    Parse error
    ERROR: parse error
    ERROR: Error while mapcalc computation
    t.rast3d.mapcalc failed
    ```

    ```python
    tools.t_copy(type="str3ds", input="day", output="sunshine")
    tools.t_rast3d_mapcalc(
        inputs="sunshine",
        output="sunny",
        basename="sunny",
        expression="sunshine * start_day()",
    )
    print(tools.t_rast3d_list(input="sunny", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    sunny_1|2026-03-01 00:00:00|4.0|4.0
    ```

### Use a dataset of another mapset and replace a result

The mapset `analysis` is new and empty. The first block makes it the current
mapset, sets the region there, and halves `soil@PERMANENT`. The expression still
uses the name `soil`. The dataset `halved` and its maps belong to the current
mapset; the listing shows the mapset of the maps.

The second block repeats the call without **--overwrite**. The tool stops
because the dataset `halved` exists. The third block adds **--overwrite** and
makes the dataset again, with the same four maps; the tool warns on the standard
error that it unregisters all maps of the old dataset.

The fourth block replaces `halved` once more, now from the dataset `weight`,
which has two maps. The new dataset holds two maps, with the values 1 and 1.5.
The maps `halved_3` and `halved_4` of the earlier run are no longer registered
in it, but the tool does not remove them: `g.list` still finds all four.

=== "Command line"

    ```sh
    g.mapset -c mapset=analysis
    g.region n=2 s=0 e=2 w=0 t=2 b=0 res=1 res3=1 tbres=1
    t.rast3d.mapcalc inputs=soil@PERMANENT output=halved basename=halved \
        expression="soil / 2"
    t.rast3d.list input=halved columns=name,mapset,min,max
    ```

    ```text
    name|mapset|min|max
    halved_1|analysis|0.5|1.0
    halved_2|analysis|5.5|6.0
    halved_3|analysis|10.5|11.0
    halved_4|analysis|15.5|16.0
    ```

    ```sh
    if ! t.rast3d.mapcalc inputs=soil@PERMANENT output=halved basename=halved \
        expression="soil / 2" 2>&1; then
        echo "t.rast3d.mapcalc failed"
    fi
    ```

    ```text
    ERROR: Space time raster3d dataset <halved> is already in the database. Use
    the overwrite flag.
    t.rast3d.mapcalc failed
    ```

    ```sh
    t.rast3d.mapcalc --overwrite inputs=soil@PERMANENT output=halved \
        basename=halved expression="soil / 2"
    t.rast3d.list input=halved columns=name,mapset,min,max
    ```

    ```text
    name|mapset|min|max
    halved_1|analysis|0.5|1.0
    halved_2|analysis|5.5|6.0
    halved_3|analysis|10.5|11.0
    halved_4|analysis|15.5|16.0
    ```

    ```sh
    t.rast3d.mapcalc --overwrite inputs=weight@PERMANENT output=halved \
        basename=halved expression="weight / 2"
    t.rast3d.list input=halved columns=name,min,max
    g.list type=raster_3d pattern="halved*"
    ```

    ```text
    name|min|max
    halved_1|1.0|1.0
    halved_2|1.5|1.5
    halved_1
    halved_2
    halved_3
    halved_4
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="analysis", flags="c")
    tools.g_region(n=2, s=0, e=2, w=0, t=2, b=0, res=1, res3=1, tbres=1)
    tools.t_rast3d_mapcalc(
        inputs="soil@PERMANENT",
        output="halved",
        basename="halved",
        expression="soil / 2",
    )
    print(tools.t_rast3d_list(input="halved", columns="name,mapset,min,max").text)
    ```

    ```text
    name|mapset|min|max
    halved_1|analysis|0.5|1.0
    halved_2|analysis|5.5|6.0
    halved_3|analysis|10.5|11.0
    halved_4|analysis|15.5|16.0
    ```

    ```python
    try:
        tools.t_rast3d_mapcalc(
            inputs="soil@PERMANENT",
            output="halved",
            basename="halved",
            expression="soil / 2",
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast3d.mapcalc failed")
    ```

    ```text
    ERROR: Space time raster3d dataset <halved> is already in the database. Use
    the overwrite flag.
    t.rast3d.mapcalc failed
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="soil@PERMANENT",
        output="halved",
        basename="halved",
        expression="soil / 2",
        overwrite=True,
    )
    print(tools.t_rast3d_list(input="halved", columns="name,mapset,min,max").text)
    ```

    ```text
    name|mapset|min|max
    halved_1|analysis|0.5|1.0
    halved_2|analysis|5.5|6.0
    halved_3|analysis|10.5|11.0
    halved_4|analysis|15.5|16.0
    ```

    ```python
    tools.t_rast3d_mapcalc(
        inputs="weight@PERMANENT",
        output="halved",
        basename="halved",
        expression="weight / 2",
        overwrite=True,
    )
    print(tools.t_rast3d_list(input="halved", columns="name,min,max").text)
    print(tools.g_list(type="raster_3d", pattern="halved*").text)
    ```

    ```text
    name|min|max
    halved_1|1.0|1.0
    halved_2|1.5|1.5
    halved_1
    halved_2
    halved_3
    halved_4
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapset](g.mapset.md), [r3.mapcalc](r3.mapcalc.md),
[t.copy](t.copy.md), [t.info](t.info.md),
[t.rast.aggregate.ds](t.rast.aggregate.ds.md),
[t.rast.mapcalc](t.rast.mapcalc.md), [t.rast3d.algebra](t.rast3d.algebra.md),
[t.rast3d.list](t.rast3d.list.md), [t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
