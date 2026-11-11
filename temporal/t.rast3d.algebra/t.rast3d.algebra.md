## DESCRIPTION

*t.rast3d.algebra* performs temporal and spatial map algebra operations
on space time 3D raster datasets (STR3DS) by using the temporal 3D
raster algebra. It reads an expression of the form `result = expression`,
relates the maps of the datasets in the expression by their time (and,
with **-s**, by their place), computes each result map with
*[r3.mapcalc](r3.mapcalc.md)* and registers the result maps in a new space
time 3D raster dataset in the current mapset. Use it when the maps to
combine are not simply paired by equal time stamps, or when a result
depends on how the time intervals of the maps lie to each other. The 2D
counterpart is *[t.rast.algebra](t.rast.algebra.md)*; to compute with the
maps of the datasets for each time step with a single *r3.mapcalc*
expression, see *[t.rast3d.mapcalc](t.rast3d.mapcalc.md)*. See the
[introduction to temporal data processing](temporalintro.md) for space
time datasets.

### Expression, result and maps

The option **expression** holds the statement `result = expression`. The name
left of the equal sign is the new space time 3D raster dataset; it is created in
the current mapset, and an existing dataset of that name is replaced only with
**--overwrite**. A dataset of another mapset is named `name@mapset` in the
expression. A name without mapset is searched in the current mapset first, then
in the mapsets of the search path. The right side may contain space time 3D
raster datasets, single maps (`map()` and `tmap()`), temporal and raster
operators and functions, as described below and in
*[t.rast.algebra](t.rast.algebra.md)*.

The option **basename** is required. The result maps are named `basename_0`,
`basename_1` and so on, counted from 0 in the order in which the algebra
computes them. This is not always the order of their time. A map that is null
everywhere is not registered unless **-n** is given. The algebra numbers only
the registered maps, so such a map leaves no gap: the next registered map takes
its number (see the example "Spatially related maps and empty maps"). An
expression that leaves no map to register ends with
the warning "The expression produced no map, the result is empty", and the
result is an empty dataset.

The option **nprocs** is the number of *r3.mapcalc* processes that run at
the same time. The default is 1. The result is the same for any number.

### Flags

**-s** also checks the spatial topology of temporally related maps and processes
only maps that are related in space too. **-n** registers maps that are null
everywhere, which are left out by default. **-g** uses the granularity algebra
instead of the temporal topology of the maps, see "Granularity algebra" below.

## NOTES

The module expects an **expression** as input parameter in the following
form:

`"result = expression"`

The statement structure is exact the same as of *t.rast.algebra*, see
[t.rast.algebra](t.rast.algebra.md) but allows four-dimensional
indexing: a neighbourhood modifier with four offsets is written
str3ds\[row,column,depth,time\].

By default, only temporal topological relations are evaluated.
The **-s** flag additionally activates the evaluation of the spatial
topology of the maps. It applies wherever the algebra evaluates the
topology of maps: in selections, in the hash operator, in the conditions
of if statements, in comparison operators and in the spatial operators.
Two temporally related maps are then only used together if they are also
spatially related, that is the spatial extents of the maps are
equivalent, one covers or is covered by the other, they overlap, one
lies in the other, one contains the other, or they meet (the spatial
relations *equivalent*, *cover*, *covered*, *overlap*, *in*, *contain*
and *meet*). The relations *equivalent*, *cover*, *overlap*, *in*,
*contain* and *meet* can also be named in the curly brackets of a
spatial operator, for example `{+,equal|overlap}`; the maps then need
this spatial relation in addition to the temporal one. Such a name builds
the spatial topology for its operator also without **-s**. The relation is
evaluated in three dimensions: two maps with the same depth range are not
related as *overlap*, even if they overlap in the horizontal plane.

Maps that are related in space are computed in the current 3D region:
*r3.mapcalc* cannot compute in the union of the regions of its input maps.

A map that the result takes over unchanged, for example one that a
selection stamps with a new time, is copied in the current 3D region as
well, with or without **-s**. A copy of a map that lies outside the region
has no data. Like any map without data it is not registered unless **-n**
is given, and a warning names it and the map it copies. Set the region with
*g.region* so that it covers the maps.

### Differences from GRASS 8.5

Since GRASS 8.6, *t.rast3d.algebra* computes its expressions with the functions
of the Python package `grass.temporal.algebra`, as *t.rast.algebra* does. The
implementation of the releases up to GRASS 8.5 is no longer part of GRASS; it
is available in those releases and in the history of the source code (tag
`classic-reference-corpus`).

An `if` without else gives 0 where a condition on map values is false, as in
GRASS 8.5, like the `if()` of *r3.mapcalc* with two arguments.

Some expressions give other results than in GRASS 8.5, as the following points
describe; where such an expression also meets one of the cases under "Results
corrected since GRASS 8.5" below, GRASS 8.5 behaved as described there for the
earlier versions. The examples use four daily 3D raster maps in A with the
values 1 to 4, two maps of two days in B that start with A, and time instances
in I.

1. **One result per conclusion map.** If a map of the conclusion of an
    `if` has several related condition maps, their conditions are joined
    with and; written as `{during,|}`, the relation joins them with or.
    GRASS 8.5 gives one result for each pair of condition map and
    conclusion map, so that a conclusion map can occur several times, and
    does not read the form `{during,|}`. The first expression keeps the
    cells of B where both maps of A within the map of B are greater than 1,
    the second where one of them is:

    ```sh
    C = if({during}, A > 1, B, 0)
    C = if({during,|}, A > 1, B, 0)
    ```

2. **Equal time stamps for then and else.** With a condition on map values, the
    then and the else part need equal time stamps; otherwise the algebra stops
    with an error. GRASS 8.5 computes only the maps whose time stamp occurs in
    both parts and leaves out the others without notice. This expression is
    therefore an error, where GRASS 8.5 gives an empty result:

    ```sh
    C = if(A > 2, A, B)
    ```

3. **Precedence.** `&&` binds stronger than `||`, and conditions can be
    grouped with parentheses. GRASS 8.5 evaluates conditions on
    temporal variables from left to right and does not accept parentheses
    around conditions. The first expression takes all maps of A, because
    `td(A) == 1` is true for each of them; GRASS 8.5 reads it as
    the second expression and takes none:

    ```sh
    C = if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)
    C = if((td(A) == 1 || td(A) == 2) && td(A) == 3, A)
    ```

4. **Right reference.** `A {:,R,r} B` and `A {op,R,r} B` give one map per
    related pair, with the time stamp of the right map and, for an operator, the
    value of this pair. GRASS 8.5 keeps only the last pair of a selection, and
    an operator combines the left map with all of its related right maps in
    every result. The first expression gives four maps, the time stamps of A
    with the values of B; GRASS 8.5 gives one map per map of B. If a map b1
    contains the maps a1 and a2, the second expression gives `b1 + a1` and
    `b1 + a2`, GRASS 8.5 `b1 + a1 + a2` for both:

    ```sh
    C = B {:,contains,r} A
    C = B {+,contains,r} A
    ```

    The inverse selection `A {!:,R,t} B` takes only the temporal operator `l`,
    because its maps have no related map to combine with; GRASS 8.5 accepts the
    other operators.

5. **td() of a time instance** is null instead of an error, so a condition
    on it is neither true nor false. This expression gives no map;
    GRASS 8.5 stops with an error:

    ```sh
    C = if(td(I) > 0, I)
    ```

    A temporal variable that a map does not have, such as `end_doy()` of a
    time instance or the calendar values of relative time, is an error in
    GRASS 8.5 and 8.6.

6. **More syntax.** Comparisons, temporal functions and the minus sign may
    stand anywhere in an expression, and a dataset may have the name of a
    function. GRASS 8.5 reports a syntax error for each of these
    expressions; the last one adds 1 to a dataset named `td`:

    ```sh
    C = A
    C = -A + 10
    C = A > 2
    C = A + start_doy(A)
    C = isnull(A)
    C = td + 1
    ```

7. **Intersection with several related maps.** With the temporal
    operator `i`, a map whose related maps have no common intersection is
    left out. GRASS 8.5 intersects the map with its related maps
    until the first one that has no common time with the result so far,
    so that its result depends on the order of the related maps. If a
    dataset H has a map from day 2 to day 4, this map follows the map of A
    of day 1 and precedes the one of day 4; the intersections are the time
    instances of day 2 and day 4, and the map is left out:

    ```sh
    C = H {:,follows|precedes,i} A
    ```

8. **Negative buffer.** A negative size in `buff_t()` shrinks the maps by that
    size at both ends. GRASS 8.6 stops with an error if a map would keep no
    time, that is if its end would fall on or before its start, and for a time
    instance, which has no duration to shrink. GRASS 8.5 goes on instead: for a
    map whose end would fall before its start it prints an error message and
    keeps the old time stamp, and it makes a time instance of a map whose end
    equals its start. For maps of two days, the first expression shrinks them to
    one day and the second is an error:

    ```sh
    C = buff_t(B, "-12 hours")
    C = buff_t(B, "-1 day")
    ```

9. **merge() of maps read at an offset.** Two maps with equal content and
    time stamps are one map. GRASS 8.5 made a new map for each map read with
    a temporal neighbourhood modifier, and `merge()` kept such a map next to
    an equal one. For four maps in A, this expression gives four maps, where
    GRASS 8.5 gave eight:

    ```sh
    C = merge(A[0], A[0])
    ```

10. **Integers beyond 32 bits.** GRASS 8.6 keeps an integer
    constant beyond 32 bits and writes it as a floating point number, so the
    result map is of type DCELL. GRASS 8.5 reads it as *r3.mapcalc*
    does, which keeps only its lower 32 bits: 3000000000 becomes
    -1294967296, and 2147483648 becomes null. Each map of A lasts one day,
    so this expression gives 3000000001 in GRASS 8.6 and -1294967295
    in GRASS 8.5:

    ```sh
    C = if(td(A) <= 0.5, A, 3000000000) + td(A)
    ```

    GRASS 8.5 also computes arithmetic on time function values as *r3.mapcalc*
    does, in 32 bits, also in a condition; GRASS 8.6 computes with all digits.
    If the two maps of RS last 3000000000 seconds each, `td(RS) * td(RS)` wraps
    around to -494665728 in GRASS 8.5, so this expression gives the value 1 for
    both maps there and the maps of RS in GRASS 8.6. A time function on its own,
    as in `if(td(RS) > 2000000000, RS, 1)`, keeps all its digits in GRASS 8.5
    and 8.6.

    ```sh
    C = if(td(RS) * td(RS) > 5, RS, 1)
    ```

11. **Maps that touch under -s.** Under **-s**, a selection with the temporal
    operator `r` or `u` takes the time of the maps that are related in time
    and in space. GRASS 8.5 chose the maps with the spatial test but took the
    time from the maps related in time, also from one whose box only touches
    the map at a corner, which is no spatial relation.

In Python, the algebra raises `SyntaxError` for an expression it cannot read.
For one it cannot compute, such as `if(end_doy(I) > 0, I)`, it raises
`ValueError` or `TypeError`, where GRASS 8.5 raises `FatalError`. It raises
`FatalError` for a missing dataset and, without overwrite, for an existing
result. The tool stops with the error message.

Two more differences concern conditions on temporal variables, in
*t.rast.algebra*, *t.select* and *t.vect.algebra* as well. First,
`if({R}, condition, conclusion)` reads "condition R conclusion":
`if({contains}, start_doy(A) > 0, B)` gives the maps of B that lie within
a map of A, where earlier versions gave the maps of B that contain a map of
A. Second, with a temporal relation beyond `equal`, the else part of a
condition on temporal variables also takes the maps that no condition map
is related to. Figure A3 of Gebbert, Leppelt and Pebesma (2019) needs both:
A has maps from day 1 to 3, 3 to 5 and 5 to 7 of January 2001, B has daily
maps from day 1 to 10, and this expression gives the first two maps of A
and the maps of B from day 5 on, as the figure shows (see the example
"Figure A3 of the publication"):

```sh
C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)
```

Results that rely on the previous reading direction or else rule need the
GRASS version they were computed with. The section "Differences from
GRASS 8.5" in the NOTES of [t.rast.algebra](t.rast.algebra.md) describes
both.

#### Results corrected since GRASS 8.5

In the following cases GRASS 8.5 computed wrongly, ended in an error that had
no reason, or reported the wrong error; GRASS 8.6 gives the result described
here. Results of earlier GRASS versions that used one of these forms need a
new run. The examples use the datasets of the list above and, in addition, N
with daily maps.

1. **td() of an expression** on the right of an operator used the value of
    the expression instead of the duration of its maps. With daily maps in N
    and A, the expression gave `N - A * 2` where it now gives `N - 1`:

    ```sh
    C = N - td(A * 2)
    ```

2. **tsnap() and tshift() of no maps.** If the expression inside has no
    maps, the result is an empty dataset, and an enclosing expression goes on
    with no maps. Earlier versions ended in an error. No map of A is equal to
    a map of B, so both expressions give an empty dataset:

    ```sh
    C = tsnap(A {:,equal} B)
    C = A + tshift(A {:,equal} B, "1 day")
    ```

3. **Increments that the library refuses.** An increment of `tshift()` or
    `buff_t()` that does not fit the temporal type, such as a text that is
    not a time step or a number without unit on absolute time, is an error and
    leaves no result dataset:

    ```sh
    C = tshift(A, "1 DAY")
    C = buff_t(A, 3)
    ```

4. **merge() with a single map.** The releases before GRASS 8.6 refused
    `merge()` of a dataset with a single map from `tmap()` with the error
    "Space time datasets to merge must have the same temporal type", also
    when both had the same temporal type. The data types of the maps are not
    compared, so a dataset may hold integer and floating point maps. The
    expression below gives the maps of A and the floating point maps
    computed from them; it ran in those releases as well. `merge()` with
    `map()`, as in `merge(A, map(a1))`, is refused, because a map without time
    stamp forms a series of its own:

    ```sh
    C = merge(A, A * 1.5)
    ```

5. **Time constants with offset.** A temporal function with an offset needs a
    map with the time value it returns. On a map without it, such as
    `end_month()` of a time instance or `start_month()` of relative time, the
    expression stops with an error that says the function requires absolute
    time, as the same function in a condition does. The releases before
    GRASS 8.6 ended with a Python traceback (`AttributeError`) while they read
    the expression:

    ```sh
    C = A + end_month(I, 0)
    ```

6. **Intersection with a time instance.** With the temporal operator `i`,
    the time stamp of the result is the time instance, for a selection and
    for an operator, on absolute and on relative time. Earlier versions kept
    the time stamp of the left map for an operator and failed with a
    `TypeError` for a selection on relative time. Both expressions give maps
    with the instances of I as time:

    ```sh
    C = A {:,contains,i} I
    C = A {+,contains,i} I
    ```

7. **td() of a counted map.** `td()` of a map counted by the hash operator gave
    the count instead of the duration, as an operand and in a comparison. The
    datasets A and N have daily maps and `A # merge(A, N)` counts 2 for each map
    of A. The expression added 2 to the maps of N where it now adds the one day
    of their duration; a condition such as `td(A # merge(A, N)) > 1.5` was true
    and is false now. The duration of a map that is not counted did not change:

    ```sh
    C = N + td(A # merge(A, N))
    ```

8. **Chains that start with a number or map().** A chain of operators whose
    first operand is a number or a map without time stamp, such as
    `map(L) - 1 - A`, was grouped from the right, as `map(L) - (1 - A)`. It is
    grouped from the left now, as in mathematics. With
    0.5 in L and the values 1 to 4 in A, the expression gave 0.5, 1.5, 2.5 and
    3.5 and now gives -1.5, -2.5, -3.5 and -4.5, the result of
    `(map(L) - 1) - A`. Chains after a dataset, such as `A + (map(L) - 1 - 1)`,
    which ended in a syntax error, are read now:

    ```sh
    C = map(L) - 1 - A
    ```

9. **td() as left operand of a stronger operator.** An expression such as
    `A + td(A) / A` was computed as `(A + td(A)) / A`, because `td()` could only
    stand right of an operator. The operators `*`, `/` and `%`, also with a
    temporal operator in braces, bind stronger than `+` and `-` now, as in
    mathematics. With daily maps and the values 1 to 4 in
    A, `td(A)` is one day. The expression gave 2, 1.5, 1.3333 and 1.25 and now
    gives 2, 2.5, 3.3333 and 4.25. A `td()` at the start of a product, such as
    `td(A) * 2`, was a syntax error and is read now:

    ```sh
    C = A + td(A) / A
    ```

10. **A spatial relation without a temporal one.** An operator with spatial
    relation names only, such as `A {+,equivalent,l} N`, related no map, because
    maps are related by their temporal relations, and gave an empty result
    without a message. It stops now with the error "equivalent is a spatial
    relation and needs a temporal one, as in equal|overlap". Write a temporal
    relation beside the spatial one:

    ```sh
    C = A {+,equal|equivalent,l} N
    ```

11. **Month and year steps from the end of a month.** `tshift()` and `buff_t()`
    by months or years ended in an error ("day is out of range for month") when
    a time stamp moved to a day that the target month lacks. Such a step now
    ends on the last day of that month. With a dataset M whose map lasts from
    31 January to 31 March 2001, the first expression gives a map from
    28 February to 30 April 2001, the second one a map from 31 December 2000 to
    30 April 2001. A year step from 29 February 2004 ends on 28 February 2005:

    ```sh
    C = tshift(M, "1 months")
    C = buff_t(M, "1 months")
    ```

    A month step back that ends in December of the year before last or earlier,
    for example `buff_t(A, "24 months")` on a map that starts on 1 December or
    `tshift(A, "-13 months")` on one that starts in January, ended in the error
    "bad month number 0" and now gives a result. Years and months of one step
    count as one step of 12 * years + months months, so `"1 years, 11 months"`
    and `"23 months"` end on the same day.

12. **A date beyond the year 9999.** A step that ends behind the year 9999 or
    before the year 1, for example `buff_t(A, "365 days")` on a map that ends on
    1 December 9999, ended with a traceback ("date value out of range"). It now
    ends with the error "... is beyond the year 9999" or "...
    is before the year 1"; no map and no dataset is created.

13. **A failed module.** If a module fails while the maps are computed, for
    example *r3.mapcalc* on a floating point map as an operand of `&&`, the
    tool ended with a Python traceback. It now ends with the error
    `Module <r3.mapcalc> failed with return code 1, see the error output above`;
    the cause is in the error output of the module above it. No dataset is
    created.

14. **The relation equals.** The relation `equal` may be written `equals` here
    too, as in *t.rast.algebra*; the releases before GRASS 8.6 refused that
    spelling with a syntax error.

15. **Comparison of related maps.** The comparison of related maps inside
    `if()`, such as `C = if(A {>=, contains, |} B, A, 0)` or
    `C = if(A >= B, A, B)`, described in [t.rast.algebra](t.rast.algebra.md),
    works for 3D raster maps in the same way. The releases before GRASS 8.6
    refused it with a syntax error.

16. **The granularity of steps over a year and of a time of the day.** The
    granularity of a dataset, which the time suffix `gran`, `tsnap()` and the
    granularity mode **-g** use, counted a step between the first days of two
    months more than a year apart by the difference of the months only: 1
    January 2024 to 1 March 2025 gave 2 months and now gives 14 months. A step
    whose two ends lie at the same time of the day other than midnight counted
    in hours or minutes: time instances at 10:30 ten days apart had the
    granularity `14400 minutes` and now have `10 days`. A time of the day that
    differs between the two ends still counts: from 10:30 to 11:30 ten days
    later the granularity is `241 hours`.

### Granularity algebra

With the flag **-g**, each space time dataset of the expression is first sampled
with the common granularity of all datasets of the expression. A monthly series
from the last day of a month (January 31, February 28 and March 31) has the
granularity of one month and gets a granule per month; GRASS 8.5 computed
one day here and got a granule per day. If the start times
of the datasets differ in a finer unit than their common granularity, the
granules are one unit long, in the finest unit in which the start times differ,
so that the maps of every dataset start with a granule: a monthly series from
the first of a month and one from the fifteenth are sampled per day, a daily
series from midnight and one from noon per hour. The granules of a dataset
follow each other from the start of its first map until they cover the end of
its last map, so the last granule may reach past it, for example a granule of
two days over a map of three days. If the dataset has time instances, one more
granule follows. Each granule takes one map of the dataset, with the time stamp
of the granule:

1. the first map that is equal to the granule;
2. otherwise the first map that contains the granule;
3. otherwise the first map that starts within the granule and ends after
    it;
4. otherwise the first map that starts before the granule and ends within
    it;
5. otherwise the first map that lies within the granule.

A granule without such a map is left out. Then the expression is computed
as without the flag, so that maps of equal time are combined. Operators
with temporal relations in curly brackets cannot be used in this mode, and
all datasets need a valid temporal topology and the same temporal type.

Single maps given with `map()` or `tmap()` are not sampled; an expression
without any space time dataset is computed as without the flag, with a
warning. The differences listed under "Differences from GRASS 8.5" apply
with **-g** as well, for example item 4, the right reference.

See the example "Sample the maps with a common granularity" below and the
manual of [t.rast.algebra](t.rast.algebra.md).

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast3d_algebra` and sets the computational
region to North Carolina with cells of 1 km and, with `res3=1000`, `t=2000`,
`b=0` and `tbres=1000`, two layers of 1000 m, so that every 3D raster map has
two layers. The later examples work in this mapset and region unless they
say otherwise. The temporal algebra works with the times of the maps, so the
maps hold small constant values in all voxels.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast3d_algebra -->

<!-- markdownlint-disable MD046 -->

### Compute with every map of a dataset

The dataset `A` has four daily maps for 1 to 4 March 2026. Each map has the
same value in all voxels: 1, 2, 3 and 4, so the smallest and the largest value
of a map are equal.

The expression `C = A * 2` creates the dataset `C` and doubles each map of
`A`. The new maps are named `c_0` to `c_3` after **basename**, counted from 0,
and each has the time of its source map. **nprocs** lets two *r3.mapcalc*
processes run at the same time; the result is the same as with one. The values
are 2, 4, 6 and 8.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast3d_algebra
    g.region raster=elev_state_500m res=1000 res3=1000 t=2000 b=0 tbres=1000 -a
    for step in 1 2 3 4; do
        r3.mapcalc expression="a_$step = $step"
    done
    t.create type=str3ds output=A title="Daily maps" \
        description="Four daily maps with the values 1 to 4"
    t.register -i type=raster_3d input=A maps=a_1,a_2,a_3,a_4 \
        start=2026-03-01 increment="1 day"
    t.rast3d.list input=A columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    a_1|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    a_2|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    a_3|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    a_4|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast3d.algebra expression="C = A * 2" basename=c nprocs=2
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|2.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|4.0|4.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|6.0|6.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|8.0|8.0
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast3d_algebra")
    tools.g_region(
        raster="elev_state_500m",
        res=1000,
        res3=1000,
        t=2000,
        b=0,
        tbres=1000,
        flags="a",
    )
    for step in range(1, 5):
        tools.r3_mapcalc(expression=f"a_{step} = {step}")
    tools.t_create(
        type="str3ds",
        output="A",
        title="Daily maps",
        description="Four daily maps with the values 1 to 4",
    )
    tools.t_register(
        type="raster_3d",
        input="A",
        maps="a_1,a_2,a_3,a_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_rast3d_list(input="A", columns="name,start_time,end_time,min,max").text)
    ```

    ```text
    name|start_time|end_time|min|max
    a_1|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    a_2|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    a_3|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    a_4|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```python
    tools.t_rast3d_algebra(expression="C = A * 2", basename="c", nprocs=2)
    print(tools.t_rast3d_list(input="C", columns="name,start_time,end_time,min,max").text)
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|2.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|4.0|4.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|6.0|6.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|8.0|8.0
    ```

### Relate the maps of two datasets by their time

The dataset `B` has two maps of two days each: `b_1` with the value 10 for 1
and 2 March and `b_2` with the value 20 for 3 and 4 March. Each map of `B`
contains two maps of `A`, and each map of `A` lies during a map of `B`. The
relation is written in curly brackets after the operator.

The first block adds to each map of `B` all the maps of `A` that it contains:
`b_1 + a_1 + a_2` is 13 and `b_2 + a_3 + a_4` is 27. The result has two maps
and takes the time of `B`. The second block adds to each map of `A` the map of
`B` that it lies in: 11, 12, 23 and 24, with the times of `A`. The two
expressions differ because the operator combines a map with all of its related
maps of the right dataset, and does so for each map of the left one.

=== "Command line"

    ```sh
    r3.mapcalc expression="b_1 = 10"
    r3.mapcalc expression="b_2 = 20"
    t.create type=str3ds output=B title="Two-day maps" \
        description="Two maps of two days each"
    t.register -i type=raster_3d input=B maps=b_1,b_2 \
        start=2026-03-01 increment="2 days"
    t.rast3d.algebra expression="D = B {+,contains} A" basename=d
    t.rast3d.list input=D columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    d_0|2026-03-01 00:00:00|2026-03-03 00:00:00|13.0|13.0
    d_1|2026-03-03 00:00:00|2026-03-05 00:00:00|27.0|27.0
    ```

    ```sh
    t.rast3d.algebra expression="E = A {+,during} B" basename=e
    t.rast3d.list input=E columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    e_0|2026-03-01 00:00:00|2026-03-02 00:00:00|11.0|11.0
    e_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|12.0
    e_2|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|23.0
    e_3|2026-03-04 00:00:00|2026-03-05 00:00:00|24.0|24.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(expression="b_1 = 10")
    tools.r3_mapcalc(expression="b_2 = 20")
    tools.t_create(
        type="str3ds",
        output="B",
        title="Two-day maps",
        description="Two maps of two days each",
    )
    tools.t_register(
        type="raster_3d",
        input="B",
        maps="b_1,b_2",
        start="2026-03-01",
        increment="2 days",
        flags="i",
    )
    tools.t_rast3d_algebra(expression="D = B {+,contains} A", basename="d")
    print(tools.t_rast3d_list(input="D", columns="name,start_time,end_time,min,max").text)
    ```

    ```text
    name|start_time|end_time|min|max
    d_0|2026-03-01 00:00:00|2026-03-03 00:00:00|13.0|13.0
    d_1|2026-03-03 00:00:00|2026-03-05 00:00:00|27.0|27.0
    ```

    ```python
    tools.t_rast3d_algebra(expression="E = A {+,during} B", basename="e")
    print(tools.t_rast3d_list(input="E", columns="name,start_time,end_time,min,max").text)
    ```

    ```text
    name|start_time|end_time|min|max
    e_0|2026-03-01 00:00:00|2026-03-02 00:00:00|11.0|11.0
    e_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|12.0
    e_2|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|23.0
    e_3|2026-03-04 00:00:00|2026-03-05 00:00:00|24.0|24.0
    ```

### Combine each map with its related map

With the temporal operator `r`, the result takes the time of the right
dataset. The expression `B {+,contains,r} A` gives one map for each map of
`A`: the algebra adds to each map of `A` the map of `B` that contains it, so
the results are 11, 12, 23 and 24 with the times of `A`. GRASS 8.5 added to
each of them all maps of `A` that the map of `B` contains: 13, 13, 27 and 27,
with the same times. This is item 4 of the differences from GRASS 8.5 in the
NOTES.

=== "Command line"

    ```sh
    t.rast3d.algebra expression="core_sum = B {+,contains,r} A" basename=core_sum
    t.rast3d.list input=core_sum columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    core_sum_0|2026-03-01 00:00:00|2026-03-02 00:00:00|11.0|11.0
    core_sum_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|12.0
    core_sum_2|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|23.0
    core_sum_3|2026-03-04 00:00:00|2026-03-05 00:00:00|24.0|24.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast3d_algebra(expression="core_sum = B {+,contains,r} A", basename="core_sum")
    print(
        tools.t_rast3d_list(
            input="core_sum", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    core_sum_0|2026-03-01 00:00:00|2026-03-02 00:00:00|11.0|11.0
    core_sum_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|12.0
    core_sum_2|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|23.0
    core_sum_3|2026-03-04 00:00:00|2026-03-05 00:00:00|24.0|24.0
    ```

### Spatially related maps and empty maps

The dataset `P` has three daily maps with the values 100, 200 and 300 for 1 to
3 March. The map `p_2` is created in a window of 10 by 10 cells that lies
east of the region and has no cell in common with it; the region is set back
afterwards.

The expression `A + P` is computed in the current region. The maps of the
second day do not overlap in space, so the result for that day has no data in
the region. By default a map without data is not registered, and the numbers
count the registered maps only: the first block gives the maps `plain_0`
(1 + 100 = 101) and `plain_1` (3 + 300 = 303). **-n** registers the empty map
as well: `with_null_1` has no minimum or maximum, which the list shows as
`None`. With **-s** the maps of the second day are not related in space, so
the algebra does not compute that pair, and with **-n** there is no empty map
either: `spatial_0` and `spatial_1` hold 101 and 303.

=== "Command line"

    ```sh
    r3.mapcalc expression="p_1 = 100"
    g.region n=319000 s=309000 e=1010000 w=1000000 res=1000 res3=1000 \
        t=2000 b=0 tbres=1000
    r3.mapcalc expression="p_2 = 200"
    g.region raster=elev_state_500m res=1000 res3=1000 t=2000 b=0 tbres=1000 -a
    r3.mapcalc expression="p_3 = 300"
    t.create type=str3ds output=P title="Patches" \
        description="Three daily maps, the second one far away"
    t.register -i type=raster_3d input=P maps=p_1,p_2,p_3 \
        start=2026-03-01 increment="1 day"
    t.rast3d.algebra expression="plain = A + P" basename=plain
    t.rast3d.list input=plain columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    plain_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    plain_1|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

    ```sh
    t.rast3d.algebra -n expression="with_null = A + P" basename=with_null
    t.rast3d.list input=with_null columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    with_null_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    with_null_1|2026-03-02 00:00:00|2026-03-03 00:00:00|None|None
    with_null_2|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

    ```sh
    t.rast3d.algebra -n -s expression="spatial = A + P" basename=spatial
    t.rast3d.list input=spatial columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    spatial_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    spatial_1|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(expression="p_1 = 100")
    tools.g_region(
        n=319000,
        s=309000,
        e=1010000,
        w=1000000,
        res=1000,
        res3=1000,
        t=2000,
        b=0,
        tbres=1000,
    )
    tools.r3_mapcalc(expression="p_2 = 200")
    tools.g_region(
        raster="elev_state_500m",
        res=1000,
        res3=1000,
        t=2000,
        b=0,
        tbres=1000,
        flags="a",
    )
    tools.r3_mapcalc(expression="p_3 = 300")
    tools.t_create(
        type="str3ds",
        output="P",
        title="Patches",
        description="Three daily maps, the second one far away",
    )
    tools.t_register(
        type="raster_3d",
        input="P",
        maps="p_1,p_2,p_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast3d_algebra(expression="plain = A + P", basename="plain")
    print(
        tools.t_rast3d_list(input="plain", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    plain_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    plain_1|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

    ```python
    tools.t_rast3d_algebra(expression="with_null = A + P", basename="with_null", flags="n")
    print(
        tools.t_rast3d_list(
            input="with_null", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    with_null_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    with_null_1|2026-03-02 00:00:00|2026-03-03 00:00:00|None|None
    with_null_2|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

    ```python
    tools.t_rast3d_algebra(expression="spatial = A + P", basename="spatial", flags="ns")
    print(
        tools.t_rast3d_list(
            input="spatial", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    spatial_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    spatial_1|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

### Sample the maps with a common granularity

`A` has daily maps and `B` maps of two days. The expression `A + B` relates
maps of equal time by default, and no map of `A` has the time of a map of `B`,
so the first block gives a result dataset without maps (the tool warns that
the expression produced no map). With **-g** the datasets are first sampled
with their common granularity of one day: each day takes the map of `B` that
contains it, and the sum is computed for every day: 11, 12, 23 and 24.

=== "Command line"

    ```sh
    t.rast3d.algebra expression="unsampled = A + B" basename=unsampled
    t.info -g type=str3ds input=unsampled | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=0
    ```

    ```sh
    t.rast3d.algebra -g expression="sampled = A + B" basename=sampled
    t.rast3d.list input=sampled columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    sampled_0|2026-03-01 00:00:00|2026-03-02 00:00:00|11.0|11.0
    sampled_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|12.0
    sampled_2|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|23.0
    sampled_3|2026-03-04 00:00:00|2026-03-05 00:00:00|24.0|24.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast3d_algebra(expression="unsampled = A + B", basename="unsampled")
    info = tools.t_info(type="str3ds", input="unsampled", flags="g").keyval
    print(f"number_of_maps={info['number_of_maps']}")
    ```

    ```text
    number_of_maps=0
    ```

    ```python
    tools.t_rast3d_algebra(expression="sampled = A + B", basename="sampled", flags="g")
    print(
        tools.t_rast3d_list(
            input="sampled", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    sampled_0|2026-03-01 00:00:00|2026-03-02 00:00:00|11.0|11.0
    sampled_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|12.0
    sampled_2|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|23.0
    sampled_3|2026-03-04 00:00:00|2026-03-05 00:00:00|24.0|24.0
    ```

### Catalog: select and combine maps by temporal relations

<!-- example: shell-only -->

The expressions of this and the following sections are shown for the
shell only; they use the datasets of the earlier examples and a few more,
which the first block creates: `I` has two time instances (2 and 4 March 2026,
values 100 and 200), `H` one map from 2 to 4 March (value 5), `N` four daily
maps with the values 4, 3, 2 and 1, `M` one map from 31 January to 31 March
2001 (value 7), `Z` four daily maps with two layers each (the value is the
layer number, 1 or 2, plus 0, 10, 20 and 30), `R` two maps in relative time
(hours 0 to 1 and 1 to 2, values 1 and 2), and the plain map `k_1` with the
value 0.5. Every block replaces the dataset `C` of the block before
(**--overwrite**) and lists it.

=== "Command line"

    ```sh
    r3.mapcalc expression="i_1 = 100"
    r3.mapcalc expression="i_2 = 200"
    t.create type=str3ds output=I title="Instants" description="Two instants"
    t.register type=raster_3d input=I maps=i_1,i_2 \
        start=2026-03-02 increment="2 days"
    r3.mapcalc expression="h_1 = 5"
    t.create type=str3ds output=H title="Interval" description="One interval"
    t.register type=raster_3d input=H maps=h_1 start=2026-03-02 end=2026-03-04
    for step in 1 2 3 4; do
        r3.mapcalc expression="n_$step = 5 - $step"
        r3.mapcalc expression="z_$step = depth() + 10 * ($step - 1)"
    done
    t.create type=str3ds output=N title="Daily maps" description="Values 4 to 1"
    t.register -i type=raster_3d input=N maps=n_1,n_2,n_3,n_4 \
        start=2026-03-01 increment="1 day"
    t.create type=str3ds output=Z title="Layers" description="Two layers"
    t.register -i type=raster_3d input=Z maps=z_1,z_2,z_3,z_4 \
        start=2026-03-01 increment="1 day"
    r3.mapcalc expression="m_1 = 7"
    t.create type=str3ds output=M title="Long interval" \
        description="From January to March 2001"
    t.register type=raster_3d input=M maps=m_1 start=2001-01-31 end=2001-03-31
    r3.mapcalc expression="s_1 = 1"
    r3.mapcalc expression="s_2 = 2"
    t.create type=str3ds output=R temporaltype=relative title="Relative time" \
        description="Two maps of one hour"
    t.register -i type=raster_3d input=R maps=s_1,s_2 start=0 increment=1 \
        unit=hours
    r3.mapcalc expression="k_1 = 0.5"
    ```

    The selection `:` takes the maps of the left dataset that are in the given
    relation to a map of the right one and does not compute any cell. The
    first block gives all four maps of `A`, because each lies during a map of
    `B`. The temporal operator `r` gives each of them the time of the map of `B`
    it lies in, so two maps share a time.

    ```sh
    t.rast3d.algebra --overwrite expression="C = A {:,during} B" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression="C = A {:,during,r} B" basename=c
    t.rast3d.list input=C order=start_time,name \
        columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|1.0|1.0
    c_1|2026-03-01 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-05 00:00:00|3.0|3.0
    c_3|2026-03-03 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    The inverse selection `!:` takes the maps that have no map in the relation.
    Of the four maps of `A`, two lie during `H`, so the maps of the first and
    the last day remain. A single map with a time stamp, `tmap()`, can stand
    on the right side: the selection with it gives the two maps during `H`.

    ```sh
    t.rast3d.algebra --overwrite expression="C = A {!:,during} H" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression="C = A {:,during} tmap(h_1)" \
        basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_1|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    ```

    The map of `H` starts before the second map of `B` and ends within it, so
    it overlaps that map; the first map of `B` is not in this relation to it.
    The sum is 25 for either operator. The temporal operator decides the time
    of the sum: `i` is the intersection of the two times, 3 and 4 March, and
    `u` the union, 2 to 5 March.

    ```sh
    t.rast3d.algebra --overwrite expression="C = H {+,overlaps,i} B" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-03 00:00:00|2026-03-04 00:00:00|25.0|25.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression="C = H {+,overlaps,u} B" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-02 00:00:00|2026-03-05 00:00:00|25.0|25.0
    ```

    The hash operator `#` counts the related maps: each map of `B` contains
    two maps of `A`. In a condition, the count selects the maps of `B` that
    contain more than one map.

    ```sh
    t.rast3d.algebra --overwrite expression="C = B {#,contains} A" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|2.0|2.0
    ```

    ```sh
    t.rast3d.algebra --overwrite \
        expression="C = if(B {#,contains} A > 1, B)" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|10.0|10.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|20.0|20.0
    ```

### Catalog: conditions and comparisons

<!-- example: shell-only -->

An `if` statement keeps the cells of the then part where the condition is true.
Without an else part, the cells where a condition on map values is false are
0. The first block gives 0, 0, 3 and 4; the second tests the start day of the
map instead, so it keeps the first two maps (1 and 2) and gives 0 for the
other two.

=== "Command line"

    ```sh
    t.rast3d.algebra --overwrite expression="C = if(A > 2, A)" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|0.0|0.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|0.0|0.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast3d.algebra --overwrite \
        expression="C = if(start_day(A) <= 2, A, 0)" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|0.0|0.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|0.0|0.0
    ```

    With a temporal relation at the start, `if({during}, A > 1, B, 0)` takes
    the maps of `B` that lie during a map of the condition. A map of `B`
    contains two maps of `A`, and the conditions of the related maps are
    joined with and: the first map of `B` has a map of `A` with the value 1,
    so the result is 0, and the second gives 20. Written as `{during,|}` the
    relation joins them with or, so both maps of `B` are kept: 10 and 20.

    ```sh
    t.rast3d.algebra --overwrite expression="C = if({during}, A > 1, B, 0)" \
        basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|0.0|0.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|20.0|20.0
    ```

    ```sh
    t.rast3d.algebra --overwrite \
        expression="C = if({during,|}, A > 1, B, 0)" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|10.0|10.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|20.0|20.0
    ```

    Inside `if()`, two datasets are compared cell by cell. `A >= N` compares
    the maps of equal time, and the `if` gives the larger of the two: the
    values of `A` are 1 to 4 and those of `N` 4 to 1, so the result is 4, 3, 3
    and 4. A comparison with a temporal relation in curly brackets is true for
    a map of `A` if the comparison holds for any (`|`) or all (`&`) of the
    related maps: `A {<,during,|} B` is true for every map of `A`, since all
    values are below 10.

    ```sh
    t.rast3d.algebra --overwrite expression="C = if(A >= N, A, N)" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|4.0|4.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|3.0|3.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast3d.algebra --overwrite \
        expression="C = if(A {<,during,|} B, A, 0)" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

### Catalog: temporal functions, shifts and buffers

<!-- example: shell-only -->

The temporal functions give the duration or a part of the date of each map
as a number. `start_day(A)` is the day of the month, 1 to 4, so the sum is 2,
4, 6 and 8. `td(A)` is the duration of a map in days, here 1. The functions
`tshift()`, `tsnap()` and `buff_t()` change the time of the maps and leave
the cell values alone.

`tsnap()` ends a last map that is a time instance one granularity of the maps
after its start. A granularity of months counts from the first map, with the cut
to the end of a shorter month: the time instances January 31, February 28 and
March 31 have the granularity of one month, and the last one ends on April 30;
after an instance on April 30 in the same series it ends on May 31. GRASS 8.5
computed a granularity of one day here and ended the instance of March 31 on
April 1.

=== "Command line"

    ```sh
    t.rast3d.algebra --overwrite expression="C = A + start_day(A)" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|2.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|4.0|4.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|6.0|6.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|8.0|8.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression="C = A * td(A)" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    `tshift()` moves the maps by one day. `tsnap()` turns the two time
    instances of `I` into intervals of two days, the granularity of `I`.
    `buff_t()` widens the time of the instances by one day on both sides; with
    a negative size it shrinks the maps of `B` by half a day at both ends,
    from two days to one.

    ```sh
    t.rast3d.algebra --overwrite expression='C = tshift(A, "1 day")' basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-02 00:00:00|2026-03-03 00:00:00|1.0|1.0
    c_1|2026-03-03 00:00:00|2026-03-04 00:00:00|2.0|2.0
    c_2|2026-03-04 00:00:00|2026-03-05 00:00:00|3.0|3.0
    c_3|2026-03-05 00:00:00|2026-03-06 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression="C = tsnap(I)" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-02 00:00:00|2026-03-04 00:00:00|100.0|100.0
    c_1|2026-03-04 00:00:00|2026-03-06 00:00:00|200.0|200.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression='C = buff_t(I, "1 day")' basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|100.0|100.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|200.0|200.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression='C = buff_t(B, "-12 hours")' \
        basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 12:00:00|2026-03-02 12:00:00|10.0|10.0
    c_1|2026-03-03 12:00:00|2026-03-04 12:00:00|20.0|20.0
    ```

    A step in months or years is a calendar step: the map of `M` lasts from 31
    January to 31 March 2001. Shifted by one month it starts on 28 February,
    the last day of February, and ends on 30 April, the last day of April.
    Buffered by a month it starts on 31 December 2000 and ends on 30 April
    2001.

    ```sh
    t.rast3d.algebra --overwrite expression='C = tshift(M, "1 months")' \
        basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2001-02-28 00:00:00|2001-04-30 00:00:00|7.0|7.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression='C = buff_t(M, "1 months")' \
        basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2000-12-31 00:00:00|2001-04-30 00:00:00|7.0|7.0
    ```

    Datasets with relative time work in the same way, and a step is a number
    in the unit of the dataset: `R * 2` doubles the values 1 and 2, and
    shifting by 1 moves the maps by one hour.

    ```sh
    t.rast3d.algebra --overwrite expression="C = R * 2" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|0|1|2.0|2.0
    c_1|1|2|4.0|4.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression="C = tshift(R, 1)" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|1|2|1.0|1.0
    c_1|2|3|2.0|2.0
    ```

### Catalog: merge, single maps and the neighbourhood modifier

<!-- example: shell-only -->

`merge()` joins the maps of two datasets into one dataset; here the result
has the four maps of `A` and the two of `B`. A plain map without time stamp
enters through `map()`: `A * map(k_1)` multiplies each map of `A` with 0.5,
giving 0.5, 1, 1.5 and 2.

=== "Command line"

    ```sh
    t.rast3d.algebra --overwrite expression="C = merge(A, B)" basename=c
    t.rast3d.list input=C order=start_time,name \
        columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-01 00:00:00|2026-03-03 00:00:00|10.0|10.0
    c_2|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_3|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_4|2026-03-03 00:00:00|2026-03-05 00:00:00|20.0|20.0
    c_5|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression="C = A * map(k_1)" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|0.5|0.5
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|1.0|1.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|1.5|1.5
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|2.0|2.0
    ```

    The neighbourhood modifier has four offsets for a 3D raster dataset:
    `Z[row,column,depth,time]`. The maps of `Z` have the values 1 and 2 in
    their two layers (plus 0, 10, 20 and 30 for the four days). The offset 1 in
    depth reads the next layer: the first layer sees the value of the second
    one, and the second layer has no next layer, so it is null. The only value
    of the result is 2 for the first day, 12 for the second, and so on. The
    fourth offset reads another map in time: `Z[0,0,0,1]` has the cells of the
    next map with the time of the current one, and the last map has no
    successor, so the result has three maps. The offsets combine:
    `Z[0,0,1,-1]` reads the next layer of the previous map, which leaves out
    the first map.

    ```sh
    t.rast3d.algebra --overwrite expression="C = Z[0,0,1,0]" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|2.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|12.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|22.0|22.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|32.0|32.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression="C = Z[0,0,0,1]" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|11.0|12.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|21.0|22.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|31.0|32.0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression="C = Z[0,0,1,-1]" basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_1|2026-03-03 00:00:00|2026-03-04 00:00:00|12.0|12.0
    c_2|2026-03-04 00:00:00|2026-03-05 00:00:00|22.0|22.0
    ```

### Catalog: differences from GRASS 8.5

<!-- example: shell-only -->

Each block computes one expression of the list "Differences from GRASS 8.5"
in the NOTES. The first block is item 1: the conditions of the two maps of `A`
within a map of `B` are joined with and, so the algebra gives 0 and 20;
GRASS 8.5 gave one result for each pair of a condition map and a conclusion
map, and four maps in total.

=== "Command line"

    ```sh
    t.rast3d.algebra --overwrite expression="C = if({during}, A > 1, B, 0)" \
        basename=c
    t.rast3d.list input=C order=start_time,name \
        columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|0.0|0.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|20.0|20.0
    ```

    Item 3, precedence: `&&` binds stronger than `||`, so each map of `A` is
    taken because `td(A) == 1` is true. GRASS 8.5 read the condition from left
    to right and took no map.

    ```sh
    t.rast3d.algebra --overwrite \
        expression="C = if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)" \
        basename=c
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    Item 7, intersection: the map of `H` follows the map of `A` of the first
    day and precedes the one of the fourth day. The algebra leaves it out,
    because the two intersections are not the same time; GRASS 8.5 gave one
    time instance. Item 9: `merge()` of two equal maps read at an offset gives
    four maps; GRASS 8.5 gave eight.

    ```sh
    t.rast3d.algebra --overwrite \
        expression="C = H {:,follows|precedes,i} A" basename=c
    t.info -g type=str3ds input=C | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=0
    ```

    ```sh
    t.rast3d.algebra --overwrite expression="C = merge(A[0], A[0])" basename=c
    t.info -g type=str3ds input=C | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=4
    ```

### Figure A3 of the publication

Figure A3 of Gebbert, Leppelt and Pebesma (2019) shows the expression of the
NOTES (section "Differences from GRASS 8.5") on datasets of January 2001. The
example creates the mapset `t_rast3d_algebra_2`, sets the region of the first
example and creates new datasets `A` and `B` there, so that the expression can
be written as it is printed: `A` has three maps of two days from 1 to 7
January 2001 with the values 1 to 3, `B` ten daily maps from 1 to 10 January
with the values 11 to 20. The result `C` holds the first two maps of `A`,
whose start is not after 3 January, and the maps of `B` from day 5 on, which
no such map of `A` contains or equals: the values 1, 2 and 15 to 20.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast3d_algebra_2
    g.region raster=elev_state_500m res=1000 res3=1000 t=2000 b=0 tbres=1000 -a
    for i in 1 2 3; do
        r3.mapcalc expression="fig_a_$i = $i"
    done
    for i in $(seq 1 10); do
        r3.mapcalc expression="fig_b_$i = 10 + $i"
    done
    t.create type=str3ds output=A title="Figure A3, A" \
        description="Three maps of two days in January 2001"
    t.register -i type=raster_3d input=A maps=fig_a_1,fig_a_2,fig_a_3 \
        start=2001-01-01 increment="2 days"
    t.create type=str3ds output=B title="Figure A3, B" \
        description="Ten daily maps in January 2001"
    t.register -i type=raster_3d input=B \
        maps=$(seq -s, -f "fig_b_%g" 1 10) start=2001-01-01 increment="1 day"
    t.rast3d.algebra \
        expression='C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)' \
        basename=fig
    t.rast3d.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    fig_0|2001-01-01 00:00:00|2001-01-03 00:00:00|1.0|1.0
    fig_1|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
    fig_2|2001-01-05 00:00:00|2001-01-06 00:00:00|15.0|15.0
    fig_3|2001-01-06 00:00:00|2001-01-07 00:00:00|16.0|16.0
    fig_4|2001-01-07 00:00:00|2001-01-08 00:00:00|17.0|17.0
    fig_5|2001-01-08 00:00:00|2001-01-09 00:00:00|18.0|18.0
    fig_6|2001-01-09 00:00:00|2001-01-10 00:00:00|19.0|19.0
    fig_7|2001-01-10 00:00:00|2001-01-11 00:00:00|20.0|20.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_rast3d_algebra_2", flags="c")
    tools.g_region(
        raster="elev_state_500m",
        res=1000,
        res3=1000,
        t=2000,
        b=0,
        tbres=1000,
        flags="a",
    )
    for i in range(1, 4):
        tools.r3_mapcalc(expression=f"fig_a_{i} = {i}")
    for i in range(1, 11):
        tools.r3_mapcalc(expression=f"fig_b_{i} = {10 + i}")
    tools.t_create(
        type="str3ds",
        output="A",
        title="Figure A3, A",
        description="Three maps of two days in January 2001",
    )
    tools.t_register(
        type="raster_3d",
        input="A",
        maps="fig_a_1,fig_a_2,fig_a_3",
        start="2001-01-01",
        increment="2 days",
        flags="i",
    )
    tools.t_create(
        type="str3ds",
        output="B",
        title="Figure A3, B",
        description="Ten daily maps in January 2001",
    )
    tools.t_register(
        type="raster_3d",
        input="B",
        maps=",".join(f"fig_b_{i}" for i in range(1, 11)),
        start="2001-01-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast3d_algebra(
        expression='C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)',
        basename="fig",
    )
    print(tools.t_rast3d_list(input="C", columns="name,start_time,end_time,min,max").text)
    ```

    ```text
    name|start_time|end_time|min|max
    fig_0|2001-01-01 00:00:00|2001-01-03 00:00:00|1.0|1.0
    fig_1|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
    fig_2|2001-01-05 00:00:00|2001-01-06 00:00:00|15.0|15.0
    fig_3|2001-01-06 00:00:00|2001-01-07 00:00:00|16.0|16.0
    fig_4|2001-01-07 00:00:00|2001-01-08 00:00:00|17.0|17.0
    fig_5|2001-01-08 00:00:00|2001-01-09 00:00:00|18.0|18.0
    fig_6|2001-01-09 00:00:00|2001-01-10 00:00:00|19.0|19.0
    fig_7|2001-01-10 00:00:00|2001-01-11 00:00:00|20.0|20.0
    ```

<!-- markdownlint-enable MD046 -->

## REFERENCES

[PLY(Python-Lex-Yacc)](https://www.dabeaz.com/ply/)

Gebbert, S., Leppelt, T., Pebesma, E., 2019. A topology based
spatio-temporal map algebra for big data analysis. Data 4, 86.
<https://doi.org/10.3390/data4020086>

## SEE ALSO

*[t.rast.algebra](t.rast.algebra.md),
[t.rast3d.mapcalc](t.rast3d.mapcalc.md), [r.mapcalc](r.mapcalc.md),
[t.vect.algebra](t.vect.algebra.md), [t.select](t.select.md),
[changes in GRASS 8.6](temporalchanges.md)*

## AUTHORS

Thomas Leppelt, Sören Gebbert, Thünen Institute of Climate-Smart
Agriculture
