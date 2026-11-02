## DESCRIPTION

*t.rast.mapcalc* computes new raster maps from the maps of one or more space
time raster datasets (STRDS) and registers them in a new STRDS. It runs
*[r.mapcalc](r.mapcalc.md)* once for each time step and adds the temporal
variables `td()`, `start_time()`, `end_time()` and, for absolute time, the
calendar functions `start_doy()`, `end_month()` and others to the expression.
Use it when the result of a time step depends on maps of several datasets, on
the time of the step, or on both. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. *[t.rast3d.mapcalc](t.rast3d.mapcalc.md)* does the same for space
time 3D raster datasets, *[t.rast.algebra](t.rast.algebra.md)* computes with
the temporal algebra, and *[t.rast.list](t.rast.list.md)* lists the maps of the
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

A name with a dot, such as `bands.S2_8`, is a dataset name and a semantic
label. It selects the maps of the dataset that have this label, and the
expression uses the same name. The new maps take the semantic label of the map
of the sampler. The eighth example shows it; see
*[i.band.library](i.band.library.md)* for the concept of semantic labels.

The result dataset is the option **output**. It always belongs to the current
mapset, and so do the new maps. It takes the temporal type and the semantic type
of the first dataset of **inputs**. Each new map has the start and end time of
its granule. An existing dataset **output** is refused unless the flag
**--overwrite** is given; then it is replaced, and the tool warns that it
unregisters all maps of the old dataset. A name with a dot is refused as
**output**.

The option **where** is an SQL condition on the registered maps, for example
`start_time >= '2026-06-11'`. It applies to every dataset in **inputs**, the
sampler too, so only the remaining maps are granules and partners. The new maps
are numbered from 1 among the remaining granules. The eighth example uses it.

The tool computes in the current region, as *r.mapcalc* does. A map that lies
outside the region reads as null.

### The expression

The option **expression** is the right side of an *r.mapcalc* expression,
without the `map =` of a full one. In it, the name of each dataset of **inputs**
stands for the related map of the current granule, so `soil * weight`
multiplies the map of `soil` by the related map of `weight`, and
`weight * soil` does the same. Any other raster map can be used by its name.
The operators and functions of *r.mapcalc* are available.

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
expression goes to *r.mapcalc*. They work with absolute and with relative
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

With relative time, a calendar function stops the tool with an error. The fifth
example shows the variables for both kinds of time.

### Select the related maps

The option **method** is a list of the sampling methods. It names the relation
between the granule and the map of another dataset. The default is `equal`. A
map is related to the granule if it has one of the listed relations. The third
example shows the methods.

- `equal`: the map has the start and the end time of the granule.
- `during`: the granule lies inside the time interval of the map. The map may
  share the start or the end of the granule, but is not equal to it: for a
  granule from 10 to 20 the maps from 5 to 25, from 10 to 25 and from 5 to 20.
- `contain`: the map lies inside the granule. It may share the start or the
  end of the granule, but is not equal to it.
- `overlap`: the map starts inside the granule and ends after it, or starts
  before it and ends inside it.
- `follows`: the map ends when the granule starts.
- `precedes`: the map starts when the granule ends.
- `start`: the maps that lie inside the granule, the maps that start before it
  and end inside it, and the maps that cover it while sharing its start or its
  end. It does not take the equal map, a map that covers the granule strictly
  and a map that starts inside it and ends after it.

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
to the granule only if its extent, from west to east and from south to north,
touches or overlaps that of the granule, so a shared edge counts. A granule
without a related map is skipped. The seventh example shows the difference.

### Parallel processing

The option **nprocs** sets the number of *r.mapcalc* processes that run at the
same time. The default is `1`. The result does not depend on it.

## NOTES

*t.rast.mapcalc* has the same options as *t.rast3d.mapcalc*, plus **where**,
and works on raster maps only. The maps of the datasets are not touched; the
tool makes new maps.

If a map of the base name exists as a registered map and **--overwrite** is not
given, the tool stops before it computes any map, with "Map ... is already in
temporal database, use overwrite flag to overwrite". If the dataset **output**
exists, the tool stops with "Space time raster dataset ... is already in the
database. Use the overwrite flag.".

With **--overwrite**, the maps of the old dataset are unregistered from it, not
removed. A new run with fewer maps leaves the surplus old maps in the mapset;
the tenth example shows it.

The tool stops with an error if an input dataset does not exist ("Space time
dataset ... of type strds not found"), if **method** names a method that does
not exist ("Value ... out of range for parameter method"), if **where** is not
valid SQL ("Invalid where condition ...") and if *r.mapcalc* does not accept
the expression ("Error while mapcalc computation"). A calendar function with
relative time stops it with
`The temporal operators <start_*> support only absolute time.` (`<end_*>` for
an end function). The tool announces its steps
on the standard error with "Starting temporal sampling..." (with **-s**:
"Starting spatio-temporal sampling...") and "Starting mapcalc
computation...".

Some inputs give no samples. If **inputs** names more than one dataset and the
sampler has only time instants, or the datasets have different temporal types,
the tool prints a message that names the reason and "No samples found for map
calculation". It also prints that last message if **where** leaves no map in
the sampler. A call with one dataset needs no sampling: time instants work as
in the fifth example, and if **where** leaves no map, the tool prints "No maps
registered in input dataset ...". In all these cases it makes no dataset
**output** and ends with status 0. If **where** leaves no map in another
dataset, no granule has a partner, and the tool makes an **output** without
maps.

Because the tool replaces the names as text, two datasets whose names share a
start, such as `soil` and `soil_deep`, cannot be used together in one call, in
whatever order they are listed. Copy one of them with *[t.copy](t.copy.md)*
under another name, as the ninth example shows.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Apply an expression to every map

The dataset `soil` has four maps for the days from 1 to 4 March 2026. The
region from `g.region` is two by two cells wide, and `col()` counts the columns
from 1. So the maps have two columns of two cells each, and their values are the
column number (1 and 2) plus 0, 10, 20 and 30, so the smallest and largest
values are 1 and 2, 11 and 12, 21 and 22, and 31 and 32.

The first block doubles the maps. The name `soil` in the expression stands for
the map of each day. The new maps are named `doubled_1` to `doubled_4` after
the granules, and each has the time of its source map. **nprocs** lets two
*r.mapcalc* processes run at the same time; the result is the same as with
one. The values are twice those of the source maps. The second block shows
what the new dataset takes from `soil`: the temporal type and the semantic
type, and the granularity that follows from the maps it holds.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=2 w=0 res=1
    for step in 1 2 3 4; do
        r.mapcalc expression="soil_$step = col() + 10 * ($step - 1)"
    done
    t.create output=soil title="Soil" \
        description="Soil temperature, one map per day"
    t.register -i input=soil \
        maps=soil_1,soil_2,soil_3,soil_4 start=2026-03-01 increment="1 day"
    t.rast.mapcalc inputs=soil output=doubled basename=doubled \
        expression="soil * 2" nprocs=2
    t.rast.list input=doubled columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    doubled_1|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|4.0
    doubled_2|2026-03-02 00:00:00|2026-03-03 00:00:00|22.0|24.0
    doubled_3|2026-03-03 00:00:00|2026-03-04 00:00:00|42.0|44.0
    doubled_4|2026-03-04 00:00:00|2026-03-05 00:00:00|62.0|64.0
    ```

    ```sh
    t.info -g input=doubled | grep -E "^(temporal_type|semantic_type|granularity)="
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
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    for step in range(1, 5):
        tools.r_mapcalc(expression=f"soil_{step} = col() + 10 * ({step} - 1)")
    tools.t_create(
        output="soil",
        title="Soil",
        description="Soil temperature, one map per day",
    )
    tools.t_register(
        input="soil",
        maps="soil_1,soil_2,soil_3,soil_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_mapcalc(
        inputs="soil", output="doubled", basename="doubled", expression="soil * 2", nprocs=2
    )
    print(
        tools.t_rast_list(input="doubled", columns="name,start_time,end_time,min,max").text
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
    info = tools.t_info(input="doubled", flags="g").keyval
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
block multiplies `soil` by `weight` with **method** `during`. The expression
names `weight` first, which does not matter. The first dataset of **inputs** is
the sampler, so the result has four maps of one day each, and each day of `soil`
lies during a map of `weight`. The values are twice those of `soil` for the
first two days and three times for the last two: 2 and 4, 22 and 24, 63 and
66, 93 and 96.

The second block swaps the order in **inputs**, so the sampler is `weight` and
the result has two maps of two days each. With **method** `contain`, each
granule of `weight` contains two maps of `soil`; the tool warns on the standard
error and uses the first of them. The result is the value of `weight` plus the
first map of `soil`: 3 and 4 for the first two days (2 plus 1 and 2), 24 and 25
for the last two (3 plus 21 and 22).

The third block leaves out **method**. The default is `equal`, and no map of
`weight` has the time of a day of `soil`, so every granule is skipped. The
tool does not fail; the new dataset exists and holds no map.

The fourth block names the default **method** `equal` and gives it partners.
The dataset `offset` has one map for each day of `soil`, `offset_k` with the
value `k`, so every day has a map with the same time. The expression chooses
the calculation by the time of the granule: on the 2nd and 3rd of the month it
adds the maps, on the other days it multiplies them. The results are 1 and 2
(1 times 1 and 2), 13 and 14 (11 plus 2 and 12 plus 2), 24 and 25 (21 plus 3
and 22 plus 3), and 124 and 128 (31 and 32 times 4).

=== "Command line"

    ```sh
    r.mapcalc expression="weight_1 = 2"
    r.mapcalc expression="weight_2 = 3"
    t.create output=weight title="Weight" \
        description="Factor for two days each"
    t.register -i input=weight maps=weight_1,weight_2 \
        start=2026-03-01 increment="2 days"
    t.rast.mapcalc inputs=soil,weight output=weighted basename=weighted \
        expression="weight * soil" method=during
    t.rast.list input=weighted columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    weighted_1|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|4.0
    weighted_2|2026-03-02 00:00:00|2026-03-03 00:00:00|22.0|24.0
    weighted_3|2026-03-03 00:00:00|2026-03-04 00:00:00|63.0|66.0
    weighted_4|2026-03-04 00:00:00|2026-03-05 00:00:00|93.0|96.0
    ```

    ```sh
    t.rast.mapcalc inputs=weight,soil output=summed basename=summed \
        expression="weight + soil" method=contain
    t.rast.list input=summed columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    summed_1|2026-03-01 00:00:00|2026-03-03 00:00:00|3.0|4.0
    summed_2|2026-03-03 00:00:00|2026-03-05 00:00:00|24.0|25.0
    ```

    ```sh
    t.rast.mapcalc inputs=soil,weight output=unmatched basename=unmatched \
        expression="soil * weight"
    t.info -g input=unmatched | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=0
    ```

    ```sh
    for step in 1 2 3 4; do
        r.mapcalc expression="offset_$step = $step"
    done
    t.create output=offset title="Offset" description="One factor per day"
    t.register -i input=offset maps=offset_1,offset_2,offset_3,offset_4 \
        start=2026-03-01 increment="1 day"
    t.rast.mapcalc inputs=soil,offset output=chosen basename=chosen method=equal \
        expression="if(start_day() == 2 || start_day() == 3, soil + offset, soil * offset)"
    t.rast.list input=chosen columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    chosen_1|2026-03-01 00:00:00|1.0|2.0
    chosen_2|2026-03-02 00:00:00|13.0|14.0
    chosen_3|2026-03-03 00:00:00|24.0|25.0
    chosen_4|2026-03-04 00:00:00|124.0|128.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="weight_1 = 2")
    tools.r_mapcalc(expression="weight_2 = 3")
    tools.t_create(
        output="weight",
        title="Weight",
        description="Factor for two days each",
    )
    tools.t_register(
        input="weight",
        maps="weight_1,weight_2",
        start="2026-03-01",
        increment="2 days",
        flags="i",
    )
    tools.t_rast_mapcalc(
        inputs="soil,weight",
        output="weighted",
        basename="weighted",
        expression="weight * soil",
        method="during",
    )
    print(
        tools.t_rast_list(input="weighted", columns="name,start_time,end_time,min,max").text
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
    tools.t_rast_mapcalc(
        inputs="weight,soil",
        output="summed",
        basename="summed",
        expression="weight + soil",
        method="contain",
    )
    print(
        tools.t_rast_list(input="summed", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    summed_1|2026-03-01 00:00:00|2026-03-03 00:00:00|3.0|4.0
    summed_2|2026-03-03 00:00:00|2026-03-05 00:00:00|24.0|25.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="soil,weight",
        output="unmatched",
        basename="unmatched",
        expression="soil * weight",
    )
    info = tools.t_info(input="unmatched", flags="g").keyval
    print(f"number_of_maps={info['number_of_maps']}")
    ```

    ```text
    number_of_maps=0
    ```

    ```python
    for step in range(1, 5):
        tools.r_mapcalc(expression=f"offset_{step} = {step}")
    tools.t_create(output="offset", title="Offset", description="One factor per day")
    tools.t_register(
        input="offset",
        maps="offset_1,offset_2,offset_3,offset_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_mapcalc(
        inputs="soil,offset",
        output="chosen",
        basename="chosen",
        expression=(
            "if(start_day() == 2 || start_day() == 3, soil + offset, soil * offset)"
        ),
        method="equal",
    )
    print(tools.t_rast_list(input="chosen", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    chosen_1|2026-03-01 00:00:00|1.0|2.0
    chosen_2|2026-03-02 00:00:00|13.0|14.0
    chosen_3|2026-03-03 00:00:00|24.0|25.0
    chosen_4|2026-03-04 00:00:00|124.0|128.0
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
granules 2, 5, 8 and 9. The last two blocks show that **method** takes a
list. Without **method** the default `equal` finds only the granule 1. With
the list `during,overlap,contain,equal` the tool collects the granules 1 to 5,
8 and 9, and the listing shows that the maps have the times of the granules.

The time of the datasets is relative, in days, and the result takes it over.
The files for *[t.register](t.register.md)* list one map per line with its
start and end time.

=== "Command line"

    ```sh
    for step in 1 2 3 4 5 6 7 8 9; do
        r.mapcalc expression="slot_$step = $step"
        r.mapcalc expression="probe_$step = 10 * $step"
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
    t.create temporaltype=relative output=slots title="Slots" \
        description="Granules of 10 days"
    t.create temporaltype=relative output=probes title="Probes" \
        description="One probe for each granule"
    t.register input=slots unit=days file=slots.txt
    t.register input=probes unit=days file=probes.txt
    for method in equal during contain overlap follows precedes start; do
        t.rast.mapcalc inputs=slots,probes output=by_$method \
            basename=$method expression="slots + probes" method=$method
        names=$(t.rast.list -u input=by_$method columns=name method=comma)
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
    t.rast.mapcalc inputs=slots,probes output=by_default basename=default \
        expression="slots + probes"
    t.rast.list input=by_default columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    default_1|110|120|11.0|11.0
    ```

    ```sh
    t.rast.mapcalc inputs=slots,probes output=by_list basename=list \
        expression="slots + probes" method=during,overlap,contain,equal
    t.rast.list input=by_list columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    list_1|110|120|11.0|11.0
    list_2|210|220|22.0|22.0
    list_3|310|320|33.0|33.0
    list_4|410|420|44.0|44.0
    list_5|510|520|55.0|55.0
    list_8|810|820|88.0|88.0
    list_9|910|920|99.0|99.0
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    for step in range(1, 10):
        tools.r_mapcalc(expression=f"slot_{step} = {step}")
        tools.r_mapcalc(expression=f"probe_{step} = 10 * {step}")
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
        temporaltype="relative",
        output="slots",
        title="Slots",
        description="Granules of 10 days",
    )
    tools.t_create(
        temporaltype="relative",
        output="probes",
        title="Probes",
        description="One probe for each granule",
    )
    tools.t_register(input="slots", unit="days", file="slots.txt")
    tools.t_register(input="probes", unit="days", file="probes.txt")
    for method in ("equal", "during", "contain", "overlap", "follows", "precedes", "start"):
        tools.t_rast_mapcalc(
            inputs="slots,probes",
            output=f"by_{method}",
            basename=method,
            expression="slots + probes",
            method=method,
        )
        names = tools.t_rast_list(
            input=f"by_{method}", columns="name", method="comma", flags="u"
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
    tools.t_rast_mapcalc(
        inputs="slots,probes",
        output="by_default",
        basename="default",
        expression="slots + probes",
    )
    print(
        tools.t_rast_list(
            input="by_default", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    default_1|110|120|11.0|11.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="slots,probes",
        output="by_list",
        basename="list",
        expression="slots + probes",
        method="during,overlap,contain,equal",
    )
    print(
        tools.t_rast_list(input="by_list", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    list_1|110|120|11.0|11.0
    list_2|210|220|22.0|22.0
    list_3|310|320|33.0|33.0
    list_4|410|420|44.0|44.0
    list_5|510|520|55.0|55.0
    list_8|810|820|88.0|88.0
    list_9|910|920|99.0|99.0
    ```

### Several related maps for one granule

The dataset `window` has one map of 10 days, from day 10 to 20, with the
value 1. The dataset `cands` has four maps that are all related to it, in
different ways: `cand_a` from 12 to 18 with the value 100 (inside the granule),
`cand_b` from 5 to 25 with the value 200 (covers it), `cand_c` from 11 to 13
with the value 300 (inside, and starts before `cand_a`) and `cand_d` from 10 to
20 with the value 400 (equal).

The expression is only `cands`, so the result holds the value of the map the
tool took. The loop prints it for five lists of methods. With the list
`during,overlap,contain,equal` it is 200: `during` comes before `contain` and
`equal` and finds `cand_b`. With `contain,during` it is 200 as well, because
the order of the list only counts for `equal`, `during`, `follows` and
`precedes`, and `contain` is tried after them. With `equal,during,contain` it
is 400, because `equal` is first, and with `during,equal` it is 200 again,
because `during` is first now. With `contain` alone it is 300: of the maps
inside the granule, `cand_c` starts first. The tool warns on the standard
error when it chooses between maps.

=== "Command line"

    ```sh
    r.mapcalc expression="window_1 = 1"
    r.mapcalc expression="cand_a = 100"
    r.mapcalc expression="cand_b = 200"
    r.mapcalc expression="cand_c = 300"
    r.mapcalc expression="cand_d = 400"
    cat > window.txt <<EOF
    window_1|10|20
    EOF
    cat > cands.txt <<EOF
    cand_a|12|18
    cand_b|5|25
    cand_c|11|13
    cand_d|10|20
    EOF
    t.create temporaltype=relative output=window title="Window" \
        description="One granule"
    t.create temporaltype=relative output=cands title="Candidates" \
        description="Four maps related to the granule"
    t.register input=window unit=days file=window.txt
    t.register input=cands unit=days file=cands.txt
    number=0
    for methods in during,overlap,contain,equal contain,during \
        equal,during,contain during,equal contain; do
        number=$((number + 1))
        t.rast.mapcalc inputs=window,cands output=taken_$number \
            basename=taken_$number expression="cands" method=$methods
        value=$(t.rast.list -u input=taken_$number columns=min)
        echo "$methods: $value"
    done
    ```

    ```text
    during,overlap,contain,equal: 200.0
    contain,during: 200.0
    equal,during,contain: 400.0
    during,equal: 200.0
    contain: 300.0
    ```

=== "Python (grass.tools)"

    ```python
    for name, value in (("window_1", 1), ("cand_a", 100), ("cand_b", 200)):
        tools.r_mapcalc(expression=f"{name} = {value}")
    tools.r_mapcalc(expression="cand_c = 300")
    tools.r_mapcalc(expression="cand_d = 400")
    Path("window.txt").write_text("window_1|10|20\n")
    Path("cands.txt").write_text("cand_a|12|18\ncand_b|5|25\ncand_c|11|13\ncand_d|10|20\n")
    tools.t_create(
        temporaltype="relative",
        output="window",
        title="Window",
        description="One granule",
    )
    tools.t_create(
        temporaltype="relative",
        output="cands",
        title="Candidates",
        description="Four maps related to the granule",
    )
    tools.t_register(input="window", unit="days", file="window.txt")
    tools.t_register(input="cands", unit="days", file="cands.txt")
    lists = (
        "during,overlap,contain,equal",
        "contain,during",
        "equal,during,contain",
        "during,equal",
        "contain",
    )
    for number, methods in enumerate(lists, start=1):
        tools.t_rast_mapcalc(
            inputs="window,cands",
            output=f"taken_{number}",
            basename=f"taken_{number}",
            expression="cands",
            method=methods,
        )
        value = tools.t_rast_list(input=f"taken_{number}", columns="min", flags="u").text
        print(f"{methods}: {value}")
    ```

    ```text
    during,overlap,contain,equal: 200.0
    contain,during: 200.0
    equal,during,contain: 400.0
    during,equal: 200.0
    contain: 300.0
    ```

### Use the time of the granule

Back to `soil`. The expressions of the first four blocks need no map, only the
time of the granule, so they name `soil` only in **inputs**. The granules are
the days from 1 to 4 March 2026; 1 March 2026 is a Sunday, the 60th day of the
year. Each block prints the smallest and largest value of every new map; all
cells of a map have the same value.

- Block 1: `start_time()` counts the hundreds, `td()` the tens and
  `end_time()` the ones. The days start 0, 1, 2 and 3 days after the first,
  are 1 day long and end 1, 2, 3 and 4 days after the start of the first, so
  the results are 11, 112, 213 and 314.
- Block 2: the day of the year and the day of the week, tens and ones again:
  60 and 7 (Sunday) for the first day, then 61 and 1 (Monday) and so on, so
  607, 611, 622 and 633.
- Block 3: the month and the end day. The month is 3 and the end day is 2 to
  5, so the results are 302 to 305.
- Block 4: the weeks, which start on Monday. The first day starts in week 9
  and ends on Monday 2 March, in week 10, so 910, and 1010 for the other days.

The next three blocks show time instants and the ISO weeks.

- Block 5: the dataset `gauge` has two time instants, at 06:00 on 1 March and
  at 18:00 on 2 March, and its maps have the values 1 and 2. `start_time()` is
  the offset in days and fractions of days from the first instant, 0 and 1.5,
  and `end_time()` is null, so `isnull()` is true and the result is 100 and
  101.5. The listing shows `None` as the end of the maps.
- Block 6: `td()` of an instant is null as well, so the result is 7.
- Block 7: the dataset `newyear` has one day, 1 January 2027, which is a
  Friday in week 53 of 2026, and `start_week()` gives 53.

The dataset `model` has three steps of 5 hours with relative time.
`start_time()`, `td()` and `end_time()` give numbers in the unit of the dataset,
hours.

- Block 8: the steps start 0, 5 and 10 hours after the first, are 5 hours long
  and end 5, 10 and 15 hours after the start of the first. With the expression
  of the first block, the results are 55, 560 and 1065.
- Block 9: the calendar functions need absolute time. The block calls
  `start_doy()` on `model`; the tool prints its error and stops without a
  result dataset. The block shows the error and then prints
  `t.rast.mapcalc failed`.

=== "Command line"

    ```sh
    t.rast.mapcalc inputs=soil output=when basename=when \
        expression="start_time() * 100 + td() * 10 + end_time()"
    t.rast.list input=when columns=name,min,max
    ```

    ```text
    name|min|max
    when_1|11.0|11.0
    when_2|112.0|112.0
    when_3|213.0|213.0
    when_4|314.0|314.0
    ```

    ```sh
    t.rast.mapcalc inputs=soil output=calendar basename=calendar \
        expression="start_doy() * 10 + start_dow()"
    t.rast.list input=calendar columns=name,min,max
    ```

    ```text
    name|min|max
    calendar_1|607.0|607.0
    calendar_2|611.0|611.0
    calendar_3|622.0|622.0
    calendar_4|633.0|633.0
    ```

    ```sh
    t.rast.mapcalc inputs=soil output=month_day basename=month_day \
        expression="start_month() * 100 + end_day()"
    t.rast.list input=month_day columns=name,min,max
    ```

    ```text
    name|min|max
    month_day_1|302.0|302.0
    month_day_2|303.0|303.0
    month_day_3|304.0|304.0
    month_day_4|305.0|305.0
    ```

    ```sh
    t.rast.mapcalc inputs=soil output=weeks basename=weeks \
        expression="start_week() * 100 + end_week()"
    t.rast.list input=weeks columns=name,min,max
    ```

    ```text
    name|min|max
    weeks_1|910.0|910.0
    weeks_2|1010.0|1010.0
    weeks_3|1010.0|1010.0
    weeks_4|1010.0|1010.0
    ```

    ```sh
    r.mapcalc expression="gauge_1 = 1"
    r.mapcalc expression="gauge_2 = 2"
    t.create output=gauge title="Gauge" description="Two instants"
    t.register input=gauge maps=gauge_1 start="2026-03-01 06:00:00"
    t.register input=gauge maps=gauge_2 start="2026-03-02 18:00:00"
    t.rast.mapcalc inputs=gauge output=instants basename=instants \
        expression="start_time() + if(isnull(end_time()), 100, 0)"
    t.rast.list input=instants columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    instants_1|2026-03-01 06:00:00|None|100.0|100.0
    instants_2|2026-03-02 18:00:00|None|101.5|101.5
    ```

    ```sh
    t.rast.mapcalc inputs=gauge output=lengths basename=lengths \
        expression="if(isnull(td()), 7, 0)"
    t.rast.list input=lengths columns=name,min,max
    ```

    ```text
    name|min|max
    lengths_1|7.0|7.0
    lengths_2|7.0|7.0
    ```

    ```sh
    r.mapcalc expression="newyear_1 = 1"
    t.create output=newyear title="New year" description="One day"
    t.register input=newyear maps=newyear_1 \
        start=2027-01-01 end=2027-01-02
    t.rast.mapcalc inputs=newyear output=iso basename=iso \
        expression="start_week()"
    t.rast.list input=iso columns=name,min,max
    ```

    ```text
    name|min|max
    iso_1|53.0|53.0
    ```


    ```sh
    for step in 1 2 3; do
        r.mapcalc expression="step_$step = col() + 10 * ($step - 1)"
    done
    t.create temporaltype=relative output=model title="Model" \
        description="Model output every 5 hours"
    t.register -i input=model maps=step_1,step_2,step_3 \
        start=0 increment=5 unit=hours
    t.rast.mapcalc inputs=model output=elapsed basename=elapsed \
        expression="start_time() * 100 + td() * 10 + end_time()"
    t.rast.list input=elapsed columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    elapsed_1|0|5|55.0|55.0
    elapsed_2|5|10|560.0|560.0
    elapsed_3|10|15|1065.0|1065.0
    ```

    ```sh
    if ! t.rast.mapcalc inputs=model output=bad basename=bad \
        expression="start_doy()" 2>&1; then
        echo "t.rast.mapcalc failed"
    fi
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    ERROR: The temporal operators <start_*> support only absolute time.
    t.rast.mapcalc failed
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_mapcalc(
        inputs="soil",
        output="when",
        basename="when",
        expression="start_time() * 100 + td() * 10 + end_time()",
    )
    print(tools.t_rast_list(input="when", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    when_1|11.0|11.0
    when_2|112.0|112.0
    when_3|213.0|213.0
    when_4|314.0|314.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="soil",
        output="calendar",
        basename="calendar",
        expression="start_doy() * 10 + start_dow()",
    )
    print(tools.t_rast_list(input="calendar", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    calendar_1|607.0|607.0
    calendar_2|611.0|611.0
    calendar_3|622.0|622.0
    calendar_4|633.0|633.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="soil",
        output="month_day",
        basename="month_day",
        expression="start_month() * 100 + end_day()",
    )
    print(tools.t_rast_list(input="month_day", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    month_day_1|302.0|302.0
    month_day_2|303.0|303.0
    month_day_3|304.0|304.0
    month_day_4|305.0|305.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="soil",
        output="weeks",
        basename="weeks",
        expression="start_week() * 100 + end_week()",
    )
    print(tools.t_rast_list(input="weeks", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    weeks_1|910.0|910.0
    weeks_2|1010.0|1010.0
    weeks_3|1010.0|1010.0
    weeks_4|1010.0|1010.0
    ```

    ```python
    tools.r_mapcalc(expression="gauge_1 = 1")
    tools.r_mapcalc(expression="gauge_2 = 2")
    tools.t_create(output="gauge", title="Gauge", description="Two instants")
    tools.t_register(input="gauge", maps="gauge_1", start="2026-03-01 06:00:00")
    tools.t_register(input="gauge", maps="gauge_2", start="2026-03-02 18:00:00")
    tools.t_rast_mapcalc(
        inputs="gauge",
        output="instants",
        basename="instants",
        expression="start_time() + if(isnull(end_time()), 100, 0)",
    )
    print(
        tools.t_rast_list(input="instants", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    instants_1|2026-03-01 06:00:00|None|100.0|100.0
    instants_2|2026-03-02 18:00:00|None|101.5|101.5
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="gauge",
        output="lengths",
        basename="lengths",
        expression="if(isnull(td()), 7, 0)",
    )
    print(tools.t_rast_list(input="lengths", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    lengths_1|7.0|7.0
    lengths_2|7.0|7.0
    ```

    ```python
    tools.r_mapcalc(expression="newyear_1 = 1")
    tools.t_create(output="newyear", title="New year", description="One day")
    tools.t_register(
        input="newyear",
        maps="newyear_1",
        start="2027-01-01",
        end="2027-01-02",
    )
    tools.t_rast_mapcalc(
        inputs="newyear", output="iso", basename="iso", expression="start_week()"
    )
    print(tools.t_rast_list(input="iso", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    iso_1|53.0|53.0
    ```


    ```python
    from grass.tools import ToolError

    for step in range(1, 4):
        tools.r_mapcalc(expression=f"step_{step} = col() + 10 * ({step} - 1)")
    tools.t_create(
        temporaltype="relative",
        output="model",
        title="Model",
        description="Model output every 5 hours",
    )
    tools.t_register(
        input="model",
        maps="step_1,step_2,step_3",
        start=0,
        increment=5,
        unit="hours",
        flags="i",
    )
    tools.t_rast_mapcalc(
        inputs="model",
        output="elapsed",
        basename="elapsed",
        expression="start_time() * 100 + td() * 10 + end_time()",
    )
    print(
        tools.t_rast_list(input="elapsed", columns="name,start_time,end_time,min,max").text
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
        tools.t_rast_mapcalc(
            inputs="model", output="bad", basename="bad", expression="start_doy()"
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.mapcalc failed")
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    ERROR: The temporal operators <start_*> support only absolute time.
    t.rast.mapcalc failed
    ```

### Keep or drop empty results

An expression that sets cells to null selects time steps by their values.
The first block keeps the values of `soil` above 15, so the maps of the
first two days (with the largest values 2 and 12) have no valid cell left. They
are not registered in `warm`, and the second block shows that they are removed
from the mapset. The new maps `warm_3` and `warm_4` keep the numbers of their
granules.

The third block runs the call again with **-n**. The dataset `warm_all`
registers the empty maps as well, with `None` as their smallest and largest
value, and the mapset keeps all four maps.

The fourth block mixes a condition on the time with one on the values: on the
2nd of the month, cells of `soil` above 11 become null, and the other days keep
their values. The map of the second day keeps the smallest value 11 and loses
12, so its largest value drops to 11; the other maps are those of `soil`.

=== "Command line"

    ```sh
    t.rast.mapcalc inputs=soil output=warm basename=warm \
        expression="if(soil > 15, soil, null())"
    t.rast.list input=warm columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    warm_3|2026-03-03 00:00:00|21.0|22.0
    warm_4|2026-03-04 00:00:00|31.0|32.0
    ```

    ```sh
    g.list type=raster pattern="warm*"
    ```

    ```text
    warm_3
    warm_4
    ```

    ```sh
    t.rast.mapcalc -n inputs=soil output=warm_all basename=warm_all \
        expression="if(soil > 15, soil, null())"
    t.rast.list input=warm_all columns=name,start_time,min,max
    g.list type=raster pattern="warm_all*"
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

    ```sh
    t.rast.mapcalc inputs=soil output=thinned basename=thinned \
        expression="if(start_day() == 2 && soil > 11, null(), soil)"
    t.rast.list input=thinned columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    thinned_1|2026-03-01 00:00:00|1.0|2.0
    thinned_2|2026-03-02 00:00:00|11.0|11.0
    thinned_3|2026-03-03 00:00:00|21.0|22.0
    thinned_4|2026-03-04 00:00:00|31.0|32.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_mapcalc(
        inputs="soil",
        output="warm",
        basename="warm",
        expression="if(soil > 15, soil, null())",
    )
    print(tools.t_rast_list(input="warm", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    warm_3|2026-03-03 00:00:00|21.0|22.0
    warm_4|2026-03-04 00:00:00|31.0|32.0
    ```

    ```python
    print(tools.g_list(type="raster", pattern="warm*").text)
    ```

    ```text
    warm_3
    warm_4
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="soil",
        output="warm_all",
        basename="warm_all",
        expression="if(soil > 15, soil, null())",
        flags="n",
    )
    print(tools.t_rast_list(input="warm_all", columns="name,start_time,min,max").text)
    print(tools.g_list(type="raster", pattern="warm_all*").text)
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

    ```python
    tools.t_rast_mapcalc(
        inputs="soil",
        output="thinned",
        basename="thinned",
        expression="if(start_day() == 2 && soil > 11, null(), soil)",
    )
    print(tools.t_rast_list(input="thinned", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    thinned_1|2026-03-01 00:00:00|1.0|2.0
    thinned_2|2026-03-02 00:00:00|11.0|11.0
    thinned_3|2026-03-03 00:00:00|21.0|22.0
    thinned_4|2026-03-04 00:00:00|31.0|32.0
    ```

### Take only the maps in the same place

The dataset `patch` has four maps for the days of `soil`, with the values
1000, 2000, 3000 and 4000. The second map `patch_2` lies next to the region
of `soil`, from 2 to 4 in the east, so it shares an edge with it. The third map
`patch_3` was made far away, in the region from 10 to 12. The other maps lie in
the region from 0 to 2, like `soil`. The current region is the one from 0 to 2
again.

The first block adds `soil` and `patch`, with 100 where `patch` is null. The
maps `patch_2` and `patch_3` are related in time but read in the current region
where they have no data, so the result for the second and third day is the
value of `soil` plus 100: 111 and 112, and 121 and 122. The result of the other
days is `soil` plus `patch`: 1001 and 1002, and 4031 and 4032.

With **-s**, the second block takes only maps whose extent touches or
overlaps that of the granule. `patch_2` touches it and stays, `patch_3` does
not, so the third granule is skipped, and the result has three maps with the
numbers 1, 2 and 4.

=== "Command line"

    ```sh
    for step in 1 2 3 4; do
        if [ $step = 2 ]; then
            g.region n=2 s=0 e=4 w=2 res=1
        elif [ $step = 3 ]; then
            g.region n=12 s=10 e=12 w=10 res=1
        fi
        r.mapcalc expression="patch_$step = 1000 * $step"
        g.region n=2 s=0 e=2 w=0 res=1
    done
    t.create output=patch title="Patch" description="Four patches"
    t.register -i input=patch \
        maps=patch_1,patch_2,patch_3,patch_4 start=2026-03-01 increment="1 day"
    t.rast.mapcalc inputs=soil,patch output=near basename=near \
        expression="soil + if(isnull(patch), 100, patch)"
    t.rast.list input=near columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    near_1|2026-03-01 00:00:00|1001.0|1002.0
    near_2|2026-03-02 00:00:00|111.0|112.0
    near_3|2026-03-03 00:00:00|121.0|122.0
    near_4|2026-03-04 00:00:00|4031.0|4032.0
    ```

    ```sh
    t.rast.mapcalc -s inputs=soil,patch output=near_only basename=near_only \
        expression="soil + if(isnull(patch), 100, patch)"
    t.rast.list input=near_only columns=name,start_time,min,max
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
            tools.g_region(n=2, s=0, e=4, w=2, res=1)
        elif step == 3:
            tools.g_region(n=12, s=10, e=12, w=10, res=1)
        tools.r_mapcalc(expression=f"patch_{step} = 1000 * {step}")
        tools.g_region(n=2, s=0, e=2, w=0, res=1)
    tools.t_create(output="patch", title="Patch", description="Four patches")
    tools.t_register(
        input="patch",
        maps="patch_1,patch_2,patch_3,patch_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_mapcalc(
        inputs="soil,patch",
        output="near",
        basename="near",
        expression="soil + if(isnull(patch), 100, patch)",
    )
    print(tools.t_rast_list(input="near", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    near_1|2026-03-01 00:00:00|1001.0|1002.0
    near_2|2026-03-02 00:00:00|111.0|112.0
    near_3|2026-03-03 00:00:00|121.0|122.0
    near_4|2026-03-04 00:00:00|4031.0|4032.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="soil,patch",
        output="near_only",
        basename="near_only",
        expression="soil + if(isnull(patch), 100, patch)",
        flags="s",
    )
    print(tools.t_rast_list(input="near_only", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    near_only_1|2026-03-01 00:00:00|1001.0|1002.0
    near_only_2|2026-03-02 00:00:00|111.0|112.0
    near_only_4|2026-03-04 00:00:00|4031.0|4032.0
    ```

### Select maps by semantic label and by time

The dataset `bands` has two bands for each of two periods: the maps `nir_1`
and `nir_2` have the semantic label `S2_8` and the values 60 and 70, the maps
`red_1` and `red_2` have the label `S2_4` and the values 20 and 10. The first
period is from 1 to 11 June 2026, the second from 11 to 21 June. The maps get
their labels from *[r.support](r.support.md)* before *[t.register](t.register.md)*
stores them.

A name with a dot in **inputs** selects the maps of one dataset by label:
`bands.S2_8` is the dataset `bands` reduced to its maps with the label `S2_8`.
The expression uses the same name, so the first dataset of the list has the two
`S2_8` maps as granules and the maps of `bands.S2_4` are their partners. The
first block computes the normalized difference of the two bands, the
normalized difference vegetation index. The values are (60 - 20) / (60 + 20) =
0.5 and (70 - 10) / (70 + 10) = 0.75. The new maps take the semantic label of
the map of the sampler, `S2_8`, and, as always, its time.

The option **where** is an SQL condition on the registered maps of all
datasets in **inputs**. The second block repeats the call for the maps that
start on or after 11 June. Only the second period is left, and the one new map
has the number 1.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=2 w=0 res=1
    r.mapcalc expression="nir_1 = 60"
    r.mapcalc expression="red_1 = 20"
    r.mapcalc expression="nir_2 = 70"
    r.mapcalc expression="red_2 = 10"
    r.support map=nir_1 semantic_label=S2_8
    r.support map=red_1 semantic_label=S2_4
    r.support map=nir_2 semantic_label=S2_8
    r.support map=red_2 semantic_label=S2_4
    t.create output=bands title="Bands" description="Near infrared and red"
    t.register input=bands maps=nir_1,red_1 start=2026-06-01 end=2026-06-11
    t.register input=bands maps=nir_2,red_2 start=2026-06-11 end=2026-06-21
    t.rast.list input=bands columns=name,start_time,semantic_label
    ```

    ```text
    name|start_time|semantic_label
    nir_1|2026-06-01 00:00:00|S2_8
    red_1|2026-06-01 00:00:00|S2_4
    nir_2|2026-06-11 00:00:00|S2_8
    red_2|2026-06-11 00:00:00|S2_4
    ```

    ```sh
    t.rast.mapcalc inputs=bands.S2_8,bands.S2_4 output=ndvi basename=ndvi \
        expression="float(bands.S2_8 - bands.S2_4) / (bands.S2_8 + bands.S2_4)"
    t.rast.list input=ndvi columns=name,start_time,semantic_label,min,max
    ```

    ```text
    name|start_time|semantic_label|min|max
    ndvi_1|2026-06-01 00:00:00|S2_8|0.5|0.5
    ndvi_2|2026-06-11 00:00:00|S2_8|0.75|0.75
    ```

    ```sh
    t.rast.mapcalc inputs=bands.S2_8,bands.S2_4 output=ndvi_late basename=late \
        expression="float(bands.S2_8 - bands.S2_4) / (bands.S2_8 + bands.S2_4)" \
        where="start_time >= '2026-06-11'"
    t.rast.list input=ndvi_late columns=name,start_time,semantic_label,min,max
    ```

    ```text
    name|start_time|semantic_label|min|max
    late_1|2026-06-11 00:00:00|S2_8|0.75|0.75
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    for name, value, label in (
        ("nir_1", 60, "S2_8"),
        ("red_1", 20, "S2_4"),
        ("nir_2", 70, "S2_8"),
        ("red_2", 10, "S2_4"),
    ):
        tools.r_mapcalc(expression=f"{name} = {value}")
        tools.r_support(map=name, semantic_label=label)
    tools.t_create(output="bands", title="Bands", description="Near infrared and red")
    tools.t_register(
        input="bands", maps="nir_1,red_1", start="2026-06-01", end="2026-06-11"
    )
    tools.t_register(
        input="bands", maps="nir_2,red_2", start="2026-06-11", end="2026-06-21"
    )
    print(tools.t_rast_list(input="bands", columns="name,start_time,semantic_label").text)
    ```

    ```text
    name|start_time|semantic_label
    nir_1|2026-06-01 00:00:00|S2_8
    red_1|2026-06-01 00:00:00|S2_4
    nir_2|2026-06-11 00:00:00|S2_8
    red_2|2026-06-11 00:00:00|S2_4
    ```

    ```python
    ndvi = "float(bands.S2_8 - bands.S2_4) / (bands.S2_8 + bands.S2_4)"
    tools.t_rast_mapcalc(
        inputs="bands.S2_8,bands.S2_4",
        output="ndvi",
        basename="ndvi",
        expression=ndvi,
    )
    print(
        tools.t_rast_list(
            input="ndvi", columns="name,start_time,semantic_label,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|semantic_label|min|max
    ndvi_1|2026-06-01 00:00:00|S2_8|0.5|0.5
    ndvi_2|2026-06-11 00:00:00|S2_8|0.75|0.75
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="bands.S2_8,bands.S2_4",
        output="ndvi_late",
        basename="late",
        expression=ndvi,
        where="start_time >= '2026-06-11'",
    )
    print(
        tools.t_rast_list(
            input="ndvi_late", columns="name,start_time,semantic_label,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|semantic_label|min|max
    late_1|2026-06-11 00:00:00|S2_8|0.75|0.75
    ```

### Names of datasets in the expression

The tool replaces the name of a dataset in the text of the expression, so the
name must not appear elsewhere in it. The dataset `day` has one map. In
`day * start_day()` the replacement also changes `start_day()`, and
*r.mapcalc* stops with the message that the function `start_day_1` is not
defined.

Two datasets whose names share a start have the same problem. The dataset
`soil_deep` has one map; `soil + soil_deep` becomes `soil_1+soil_1_deep`, and
*r.mapcalc* does not know the map `soil_1_deep`.

Copy a dataset under another name with *t.copy*, and use the new name. The copy
holds the same maps, and the third block computes with it.

=== "Command line"

    ```sh
    r.mapcalc expression="day_1 = 4"
    t.create output=day title="Day" description="One map"
    t.register input=day maps=day_1 \
        start=2026-03-01 end=2026-03-02
    if ! t.rast.mapcalc inputs=day output=bad basename=bad \
        expression="day * start_day()" 2>&1; then
        echo "t.rast.mapcalc failed"
    fi
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    Undefined function 'start_day_1'
    Parse error
    ERROR: parse error
    ERROR: Error while mapcalc computation
    t.rast.mapcalc failed
    ```

    ```sh
    r.mapcalc expression="soil_deep_1 = 3"
    t.create output=soil_deep title="Deep soil" \
        description="One map"
    t.register input=soil_deep maps=soil_deep_1 \
        start=2026-03-01 end=2026-03-02
    if ! t.rast.mapcalc inputs=soil,soil_deep output=bad basename=bad \
        expression="soil + soil_deep" 2>&1; then
        echo "t.rast.mapcalc failed"
    fi
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    Invalid map <soil_1_deep>
    Parse error
    ERROR: parse error
    ERROR: Error while mapcalc computation
    t.rast.mapcalc failed
    ```

    ```sh
    t.copy input=day output=sunshine
    t.rast.mapcalc inputs=sunshine output=sunny basename=sunny \
        expression="sunshine * start_day()"
    t.rast.list input=sunny columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    sunny_1|2026-03-01 00:00:00|4.0|4.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="day_1 = 4")
    tools.t_create(output="day", title="Day", description="One map")
    tools.t_register(input="day", maps="day_1", start="2026-03-01", end="2026-03-02")
    try:
        tools.t_rast_mapcalc(
            inputs="day", output="bad", basename="bad", expression="day * start_day()"
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.mapcalc failed")
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    Undefined function 'start_day_1'
    Parse error
    ERROR: parse error
    ERROR: Error while mapcalc computation
    t.rast.mapcalc failed
    ```

    ```python
    tools.r_mapcalc(expression="soil_deep_1 = 3")
    tools.t_create(output="soil_deep", title="Deep soil", description="One map")
    tools.t_register(
        input="soil_deep",
        maps="soil_deep_1",
        start="2026-03-01",
        end="2026-03-02",
    )
    try:
        tools.t_rast_mapcalc(
            inputs="soil,soil_deep",
            output="bad",
            basename="bad",
            expression="soil + soil_deep",
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.mapcalc failed")
    ```

    ```text
    Starting temporal sampling...
    Starting mapcalc computation...
    Invalid map <soil_1_deep>
    Parse error
    ERROR: parse error
    ERROR: Error while mapcalc computation
    t.rast.mapcalc failed
    ```

    ```python
    tools.t_copy(input="day", output="sunshine")
    tools.t_rast_mapcalc(
        inputs="sunshine",
        output="sunny",
        basename="sunny",
        expression="sunshine * start_day()",
    )
    print(tools.t_rast_list(input="sunny", columns="name,start_time,min,max").text)
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
    g.region n=2 s=0 e=2 w=0 res=1
    t.rast.mapcalc inputs=soil@PERMANENT output=halved basename=halved \
        expression="soil / 2.0"
    t.rast.list input=halved columns=name,mapset,min,max
    ```

    ```text
    name|mapset|min|max
    halved_1|analysis|0.5|1.0
    halved_2|analysis|5.5|6.0
    halved_3|analysis|10.5|11.0
    halved_4|analysis|15.5|16.0
    ```

    ```sh
    if ! t.rast.mapcalc inputs=soil@PERMANENT output=halved basename=halved \
        expression="soil / 2.0" 2>&1; then
        echo "t.rast.mapcalc failed"
    fi
    ```

    ```text
    ERROR: Space time raster dataset <halved> is already in the database. Use
    the overwrite flag.
    t.rast.mapcalc failed
    ```

    ```sh
    t.rast.mapcalc --overwrite inputs=soil@PERMANENT output=halved \
        basename=halved expression="soil / 2.0"
    t.rast.list input=halved columns=name,mapset,min,max
    ```

    ```text
    name|mapset|min|max
    halved_1|analysis|0.5|1.0
    halved_2|analysis|5.5|6.0
    halved_3|analysis|10.5|11.0
    halved_4|analysis|15.5|16.0
    ```

    ```sh
    t.rast.mapcalc --overwrite inputs=weight@PERMANENT output=halved \
        basename=halved expression="weight / 2.0"
    t.rast.list input=halved columns=name,min,max
    g.list type=raster pattern="halved*"
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
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    tools.t_rast_mapcalc(
        inputs="soil@PERMANENT",
        output="halved",
        basename="halved",
        expression="soil / 2.0",
    )
    print(tools.t_rast_list(input="halved", columns="name,mapset,min,max").text)
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
        tools.t_rast_mapcalc(
            inputs="soil@PERMANENT",
            output="halved",
            basename="halved",
            expression="soil / 2.0",
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.mapcalc failed")
    ```

    ```text
    ERROR: Space time raster dataset <halved> is already in the database. Use
    the overwrite flag.
    t.rast.mapcalc failed
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="soil@PERMANENT",
        output="halved",
        basename="halved",
        expression="soil / 2.0",
        overwrite=True,
    )
    print(tools.t_rast_list(input="halved", columns="name,mapset,min,max").text)
    ```

    ```text
    name|mapset|min|max
    halved_1|analysis|0.5|1.0
    halved_2|analysis|5.5|6.0
    halved_3|analysis|10.5|11.0
    halved_4|analysis|15.5|16.0
    ```

    ```python
    tools.t_rast_mapcalc(
        inputs="weight@PERMANENT",
        output="halved",
        basename="halved",
        expression="weight / 2.0",
        overwrite=True,
    )
    print(tools.t_rast_list(input="halved", columns="name,min,max").text)
    print(tools.g_list(type="raster", pattern="halved*").text)
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

*[g.list](g.list.md), [g.mapset](g.mapset.md),
[i.band.library](i.band.library.md), [r.mapcalc](r.mapcalc.md),
[r.support](r.support.md), [t.copy](t.copy.md), [t.info](t.info.md),
[t.rast.aggregate.ds](t.rast.aggregate.ds.md),
[t.rast.algebra](t.rast.algebra.md), [t.rast.list](t.rast.list.md),
[t.rast3d.mapcalc](t.rast3d.mapcalc.md), [t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
