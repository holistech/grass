---
description: Changes of the temporal framework in GRASS 8.6
index: temporal
---

# Changes of the temporal framework in GRASS 8.6

## DESCRIPTION

This page lists what changed in the temporal framework since GRASS 8.5: in
the results and the output of the temporal tools, in the options they take
and the errors they report, and in the Python library `grass.temporal`. It
is written for users who move from GRASS 8.5 or an earlier release, for
authors of scripts and addons, and for reviewers. Each entry says what
happened before, what happens now and, where a user has to act, what to do.
It links the section of a manual that describes the behavior of today.

Most entries come from a rework of the temporal framework for GRASS 8.6: a
new implementation of the temporal algebra, a review of every temporal tool
with new tests and new manuals, and the errors that this review found and
fixed. Entries marked *(upstream)* come from the development of GRASS
after the creation of the release branch of GRASS 8.5, both before the
start of the rework and, where the rework took them over later, after it;
GRASS 8.5 does not have them either. Where the rework later
changed such an entry, the entry describes the behavior of GRASS 8.6.

The algebra tools compute with a new implementation by default. The flag
**-c** selects the classic algebra, which gives the results of the releases
before GRASS 8.6 with the exceptions in [Classic algebra](#classic-algebra);
use it to repeat a published result. Errors that were fixed without a change
of the result of a valid call are only grouped, in
[Fixed errors](#fixed-errors). The [EXAMPLES](#examples) show two of the
changes in the North Carolina sample dataset.

## Temporal algebra

Since GRASS 8.6, *[t.rast.algebra](t.rast.algebra.md)*,
*[t.rast3d.algebra](t.rast3d.algebra.md)*,
*[t.vect.algebra](t.vect.algebra.md)* and *[t.select](t.select.md)*
compute their expressions with a new implementation, the Python package
`grass.temporal.algebra`. The algebra of the releases before stays available
as the classic algebra: the flag **-c** selects it for one call, the
environment variable `GRASS_TEMPORAL_ALGEBRA=classic` for a whole session or
script. `GRASS_TEMPORAL_ALGEBRA=core`, an empty or an unset variable selects
the new algebra, the flag takes precedence over the variable, and a value of
blanks only is refused. In Python, the parser classes take `classic=True`.
To repeat the results of a publication, set **-c** or the variable. The
section [Core and classic algebra](t.rast.algebra.md#core-and-classic-algebra)
of *t.rast.algebra* describes both algebras.

The new algebra differs from the releases before GRASS 8.6 in the points
below; **-c** keeps the behavior of those releases in each of them. The
example [Compare the new and the classic
algebra](#compare-the-new-and-the-classic-algebra) shows the first point on
precedence.

- **One result per conclusion map.** An `if()` whose conclusion map had
    several related condition maps gave one result for each pair, so a
    conclusion map could occur several times. Now there is one result per
    conclusion map: the conditions are joined with and, and a relation
    written as `{during,|}` joins them with or. Use **-c** for the old
    results ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **Equal time stamps for then and else.** With a condition on map values,
    only the maps whose time stamp occurred in both the then and the else
    part were computed, and the others were left out without notice; the
    result could be empty. Now the then and the else part need equal time
    stamps, or the tool stops with an error. Write both parts with equal
    times, or use **-c**
    ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **Precedence of `&&` and `||`.** Conditions on temporal variables were
    read from left to right, and parentheses around conditions were not
    accepted. Now `&&` binds stronger than `||`, and conditions can be
    grouped with parentheses. Use **-c** for the old results
    ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **Selection with the time of the right map.** `A {:,R,r} B` kept only
    the last pair of a selection, an operator with `r` joined the left map
    with all related right maps in each result, and `!:` took every temporal
    operator. Now there is one map for each related pair, with the time of
    the right map and the value of the pair, and `!:` takes only the
    temporal operator `l`. Use **-c** for the old results
    ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **td() of a time instance.** `td()` of a time instance stopped the tool
    with an error. Now it is null, and a condition on it is neither true nor
    false ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **More forms of expressions.** Comparisons, temporal functions and minus
    signs were syntax errors outside a few places, and a dataset could not
    have the name of a function, so that `C = A`, `C = -A + 10`,
    `C = A > 2`, `C = isnull(A)` and `C = td + 1` were syntax errors. Now
    these forms are read
    ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **Intersection with several related maps.** The temporal operator `i`
    with several related maps intersected them up to the first map without
    common time, so the result depended on their order. Now a map whose
    related maps have no common intersection is left out. Use **-c** for
    the old results
    ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **Negative buffers.** `buff_t()` with a negative buffer reported an error
    when the end came before the start but kept the old time, and an end
    equal to the start gave a time instance. Now the tool stops with an
    error if a map would keep no time, and for time instances
    ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **merge() of equal maps.** `merge()` kept a map read with the
    neighbourhood modifier or a temporal function with an offset next to an
    equal map, so `merge(A[0], A[0])` gave eight maps instead of four. Now
    two maps with equal content and time are one map. Use **-c** for the old
    results ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **tsnap() of maps that start together.** The times that `tsnap()` gave
    two maps with the same start depended on the order of the arguments of
    `merge()`. Now they do not: of a map from 2 to 3 January and a map from
    2 to 4 January, both end on 3 January in either order. Use **-c** for
    the old results
    ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **Integers beyond 32 bits.** An integer constant beyond 32 bits was read
    by *r.mapcalc* with its lower 32 bits only (3000000000 became
    -1294967296, 2147483648 became null), and the values of temporal
    functions were computed with 32 bits. Now the new algebra keeps the
    constant and writes it as a floating point value, and the values of
    temporal functions keep all digits. Use **-c** for the old results
    ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **A number next to an operator in brackets.** A number next to an
    operator in curly brackets or the hash operator was read together with
    the expression behind it: `A {*,equal} 2 - B` meant
    `A {*,equal} (2 - B)`. Now such an operator needs a dataset on both
    sides, and the form without parentheses is a syntax error. Add the
    parentheses, or use **-c**
    ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **Null maps with -n.** With **-n**, no null map was registered for a map
    on the left of `{&&,...}` without a related map. Now **-n** registers a
    null map for each such map
    ([t.rast.algebra](t.rast.algebra.md#core-and-classic-algebra)).
- **Errors in Python and dry runs.** In Python, an expression that cannot
    be computed raised `FatalError`, and a dry run checked existing results
    only at the maps. Now the new algebra raises `ValueError` or
    `TypeError` (an expression that cannot be read stays a `SyntaxError`),
    and a dry run with **-d** without **--overwrite** stops at an existing
    result dataset as the real run does. Python code that catches
    `FatalError` has to catch `ValueError` and `TypeError` too
    ([t.rast.algebra](t.rast.algebra.md#notes)).
- **Errors without traceback.** The algebra tools printed a Python
    traceback with an error. Now they report the error with a message only
    ([t.rast.algebra](t.rast.algebra.md#notes)).
- **Copies outside the region.** A map that the result takes over
    unchanged, for example with a new time, was copied only where needed,
    and a copy outside the region came out empty without notice. Now such
    copies are computed in the current region, with **-s** in the union of
    the regions of the input maps; an empty copy is registered only with
    **-n**, and a warning names it and the map it copies. Set the region
    with *g.region* so that it covers the maps
    ([t.rast.algebra](t.rast.algebra.md#notes)).
- **Datasets in the search path.** *t.rast.algebra* and
    *t.rast3d.algebra* looked for a dataset name without mapset in the
    current mapset only. Now the new algebra looks in the current mapset and
    then in the search path; **-c** keeps looking in the current mapset only
    ([t.rast.algebra](t.rast.algebra.md#use-datasets-of-another-mapset)).
- **Digits of the map numbers.** With `suffix=num%NN`, *t.rast.algebra*
    ignored `NN` and took the number of digits from the number of maps. Now
    `NN` sets the number of digits as in *t.rast.extract*; **-c** keeps the
    digits from the number of maps
    ([t.rast.algebra](t.rast.algebra.md#name-the-result-maps-and-plan-a-run)).

## Classic algebra

The classic algebra, selected with **-c** or `GRASS_TEMPORAL_ALGEBRA=classic`,
gives the results of the releases before GRASS 8.6 with the exceptions below. In
most of them, those releases computed a wrong result, refused an expression that
they should compute, or computed one that they should refuse. The implementation
of those releases, which stays in the source code as `grass.temporal.classic`,
was corrected in the same way, except in the last two entries, on `merge()` of
absolute and relative time and on the selection of a relative time instance,
and under **-s** for maps whose boxes touch at a corner (see
[t.rast.algebra](t.rast.algebra.md#differences-from-the-reference-implementation)):
only the classic algebra computes the first two, and `grass.temporal.classic`
still ends with a `TypeError` and still relates maps whose boxes touch at a
corner. Results of an earlier release that used one of these forms
need a new run. All other results of the classic algebra are those of the
releases before GRASS 8.6: the tests compare it with recorded results of that
implementation. The manuals of the algebra tools describe many of these
corrections with examples, in their sections "Corrections to the classic
algebra".

Besides, the classic algebra reports errors with the messages of the new
algebra, prints its debug output as module calls, reads the syntax of the
whole expression before it computes, raises `FatalError` instead of
`SystemExit` in Python for an existing result, and ends the expressions that
it refuses with a message instead of a Python traceback. No result changes by
this ([t.rast.algebra](t.rast.algebra.md#differences-from-the-reference-implementation)).

- **Unknown relations.** Unknown relations, such as `{:,bogus}` or
    `{+,nonsense}`, and operators of the wrong type gave no result without
    notice. Now they are a syntax error with a message. Correct the
    expression ([t.rast.algebra](t.rast.algebra.md#temporal-relations)).
- **The default relation of a selection.** `{:}` and `{!:}` gave no
    result, and the default relation included the spatial relation
    `equivalent`. Now the default relation is `equal`, `{:}` selects the
    maps of equal time and `{!:}` gives an empty result
    ([t.rast.algebra](t.rast.algebra.md#temporal-selection)).
- **The simple operator + with maps of equal time.** Of several maps of
    equal time, the simple operator `+` aggregated only the last. Now it
    aggregates all of them. Results that rely on this need a new run
    ([t.rast.algebra](t.rast.algebra.md#conditional-statements)).
- **Hash operator with several relations.** The hash operator with several
    relations counted the maps of the last relation only. Now it counts the
    maps of all relations. Results that rely on this need a new run
    ([t.rast.algebra](t.rast.algebra.md#hash-operator)).
- **Relative time.** Result datasets always had absolute time, and inputs
    with relative time failed, also in `td()`, `buff_t()` and `tshift()`.
    Now the result dataset has the temporal type of the inputs, and
    relative time is computed ([t.rast.algebra](t.rast.algebra.md#notes)).
- **Temporal functions in conditions.** Conditions with
    `start_datetime()` or `end_datetime()` failed for every literal,
    `start_time()` and `end_time()` raised a `TypeError` or selected
    nothing, and all temporal functions raised an `AttributeError` for time
    instances and relative time. Now the literal is converted into the type
    of the value of the function, and a function that a map does not have
    stops the tool with an error that names the map
    ([t.rast.algebra](t.rast.algebra.md#temporal-functions)).
- **Vector overlays.** *t.vect.algebra* removed the results of an overlay
    from the mapset after it had registered them, `if()` crashed, the
    operators `|`, `^`, `~` and `+` dropped pairs with separate extents, the
    overlay operator `+` could not be read and `merge()` always failed. Now
    the results stay, `if()` computes, all pairs are overlaid, `+` is read
    and `merge()` joins vector datasets
    ([t.vect.algebra](t.vect.algebra.md#description)).
- **Spatial topology with -s.** The flag **-s** had no effect, and the
    relation `covered` was missing from the spatial relations. Now **-s**
    evaluates the spatial topology (`equivalent`, `cover`, `covered`,
    `overlap`, `in`, `contain`, `meet`) in selections, the hash operator,
    conditions and comparisons. Results computed with **-s** need a new run
    ([t.rast.algebra](t.rast.algebra.md#notes)).
- **Blanks in overlay operators.** In *t.vect.algebra*, a blank after the
    second comma of an overlay operator, as in `aa {&,equal, l} ab`, was a
    syntax error. Now it is read; in the operators of the raster algebras
    it stays a syntax error
    ([t.vect.algebra](t.vect.algebra.md#temporal-operators)).
- **Null maps of 3D rasters.** *t.rast3d.algebra* could not remove its null
    maps, and in Python, `run=False` crashed in the raster algebras. Now
    null maps are removed, and `run=False` only checks the syntax.
- **Conditions over maps of equal time.** With several maps of equal time,
    `if()` combined every condition map with every conclusion map of that
    time and gave one result for each pair. Now maps of equal time are
    paired like the arrays
    of numpy: a single map goes with all maps of its time, n maps with n
    maps in their order, and unequal numbers are an error. Results that rely
    on this need a new run
    ([t.rast.algebra](t.rast.algebra.md#conditional-statements)).
- **Selected maps of another mapset.** *t.select* could not register a
    selected map of another mapset. Now the map is registered in the
    temporal database of the current mapset; the map itself is not copied
    ([t.select](t.select.md#results-empty-selections-and-mapsets)).
- **Result maps of the other temporal type.** Result maps that were
    registered with the other temporal type lost their time when they were
    overwritten, so the result was empty or incomplete. Now they are
    replaced completely ([t.rast.algebra](t.rast.algebra.md#notes)).
- **Temporal operators at the hash operator.** The hash operator took the
    temporal operators `r`, `u`, `i` and `d` and ignored them, so that
    `{#,contains,r}` meant `{#,contains}`. Now they are a syntax error, and
    the result keeps the time of the left maps. Change `{#,R,r}` and the
    like into `{#,R}`, which gives the same result
    ([t.rast.algebra](t.rast.algebra.md#hash-operator)).
- **merge() is a union.** `merge()` appended its operands to each other, so
    a map in both operands was there twice and was counted twice later:
    `N {+,equal} merge(A {:,during} B, A {:,during} C)` gave 12, 16, 19
    and 18. Now `merge()` keeps a map with equal identifier, time and command
    once and warns about it; the expression gives 12, 14, 16 and 18. Results
    of `merge()` with overlapping operands need a new run
    ([t.rast.algebra](t.rast.algebra.md#merge-function)).
- **Reading direction and else in conditions.** In `if({R}, condition,
    conclusion)`, the relation R was read from the conclusion to the
    condition for conditions on temporal variables, and the else part took
    no map without a related condition map. Now R goes from the condition to
    the conclusion, also for temporal variables, and with a relation beyond
    `equal` the else part also takes the maps without a related condition
    map; figure A3 of Gebbert, Leppelt and Pebesma (2019) comes out as
    published. Results that rely on the old reading direction or else rule
    need the GRASS version they were computed with
    ([t.rast.algebra](t.rast.algebra.md#conditional-statements)).
- **td() of an expression.** `td()` of an expression on the right of an
    operator gave the value of the expression instead of the duration of its
    maps: `N - td(A * 2)` was `N - A * 2`. Now it is `N - 1` for daily maps.
    Results with this form need a new run
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra)).
- **tsnap() and tshift() of no maps.** `tshift()` of an expression without
    maps ended with an `IndexError`, and `tsnap()` of such an expression
    created no dataset. Now the result is empty like any other empty result:
    an empty dataset, and an enclosing expression goes on without maps
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra)).
- **Increments of tshift() and buff_t().** `tshift()` with a number on
    absolute time ended without result and with exit code 0, and `buff_t()`
    on relative time ended with a `TypeError`, also with a number such as
    1.5. Now an increment that does not fit the temporal type is an error,
    and no dataset is created; `buff_t(RT, 1.5)` computes on relative time
    with the whole number 1. Correct the increment
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra)).
- **merge() with a single map.** `merge()` of a dataset with a single map
    from `tmap()` ended with the error "Space time datasets to merge must
    have the same temporal type", also when both had the same temporal
    type. Now the map is taken
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra)).
- **Intersection with a time instance.** An operator with `i` and a time
    instance, such as `A {+,contains,i} I`, kept the time of the left map,
    and such a selection on relative time ended with a `TypeError`. Now the
    time of the result is the time instance, for selections and operators,
    in absolute and in relative time. Results with this form need a new run
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra)).
- **Infinite values.** A map with infinite values, as made by
    `exp(A * 1000)`, could not be registered, because writing its range
    failed, and the temporal database could stay locked. Now its minimum and
    maximum are stored as NULL, and a failed transaction is rolled back. This
    concerned the library and with it both algebras
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra)).
- **td() of a counted map.** `td()` of a map counted by the hash operator
    gave the count instead of the duration, as an operand and in a
    comparison. Now it gives the duration. Results with this form need a
    new run
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra)).
- **Chains that start with a number.** A chain that starts with a number or
    `map()`, such as `map(L) - 1 - A`, was grouped from the right, as
    `map(L) - (1 - A)`, and `A + (map(L) - 1 - 1)` was a syntax error. Now
    chains are grouped from the left, and chains after a dataset are read; a
    chain of numbers and `map()` only stays a syntax error. Results with such
    chains need a new run
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra)).
- **Precedence of td().** `A + td(A) / A` was computed as
    `(A + td(A)) / A`, because `td()` could only stand on the right of an
    operator, and `td(A) * 2` was a syntax error. Now `*`, `/` and `%`, also
    with a temporal operator, bind stronger than `+` and `-`, and `td()` at
    the start of a product is read. Results with this form need a new run
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra)).
- **A spatial relation without a temporal one.** An operator with spatial
    relation names only, such as `A {+,equivalent,l} N`, related no map and
    gave an empty result without notice, and in *t.select* `{:,equivalent}`
    selected nothing. Now this is an error that says that `equivalent` is a
    spatial relation and needs a temporal one. Write a temporal relation
    next to it, as in `equal|equivalent`
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra)).
- **tsnap() of a map that starts with the next map.** `tsnap()` gave a map
    that starts at the same time as the next map the end of that map, so
    the two maps exchanged their ends; *t.snap* did the same. Now such a map
    keeps its own end; in the classic algebra the map listed first keeps its
    end ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra),
    [t.snap](t.snap.md#notes)).
- **Steps of months and years.** `tshift()` and `buff_t()` by months or
    years ended with the error "day is out of range for month" when the
    target month is too short for the day, and a step of 24 months back from
    December ended with "month must be in 1..12"; years and months of a
    step were added one after the other. Now such a step ends on the last
    day of the target month, and years and months are one step of
    12 times the years plus the months
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra)).
- **equals and dataset functions in capitals.** The name `equals`, which
    the publication of the algebra uses, gave no result without notice, and
    *t.select* refused `STRDS(A)`, `STR3DS(A)` and `STVDS(A)` as syntax
    errors. Now `equals` is another name of `equal`, and *t.select* reads
    the dataset functions in capitals in front of a parenthesis
    ([t.rast.algebra](t.rast.algebra.md#corrections-to-the-classic-algebra),
    [t.select](t.select.md#corrections-to-the-classic-algebra)).
- **Comparison of two datasets.** A comparison of two datasets in curly
    brackets, such as `{<,equal,|,r}`, and a comparison of two datasets in
    `if()`, such as `if(A >= B, A, 0)`, were syntax errors. Now both are
    read ([t.rast.algebra](t.rast.algebra.md#comparison-of-related-maps)).
- **Granularity in calendar steps.** The granularity counted a step between
    the first days of two months more than a year apart by the difference of
    the months only (from 1 January 2024 to 1 March 2025: 2 months), and
    maps at the same time of day other than midnight in hours or minutes
    (ten days at 10:30: 14400 minutes). Now these are 14 months and 10 days;
    a time of day that differs still counts (10:30 to 11:30 ten days later:
    241 hours). This holds for the suffix `gran`, for `tsnap()` and for the
    granularity mode **-g**, and it is one of two cases where the classic
    algebra was changed on purpose in a point that was no error (the other:
    datasets of a mapset outside the search path). Results
    with **-g**, `gran` or `tsnap()` over such series need a new run;
    *t.support* **-m** computes the stored granularity of a dataset again
    ([t.rast.algebra](t.rast.algebra.md#granularity-algebra)).
- **Dry run of a selection of mixed types.** The dry run (**-d**) of
    *t.select* with an expression of mixed types planned the type given
    with **type**, while the real run created another one, a str3ds. Now
    the dry run plans the type that the run creates
    ([t.select](t.select.md#corrections-to-the-classic-algebra)).
- **Empty buffers in overlays.** In *t.vect.algebra*, an intermediate map
    that `buff_p()` leaves empty went to *v.overlay*, which failed. Now it
    counts as a map without areas: *v.overlay* does not run, a warning is
    printed, and the result is left out
    ([t.vect.algebra](t.vect.algebra.md#corrections-to-the-classic-algebra)).
- **Datasets of a mapset outside the search path.** A dataset
    `name@mapset` of a mapset outside the search path was refused. Now it is
    read if the mapset has a temporal database, so the classic algebra
    computes an expression that it refused before; see [Datasets of other
    mapsets](#datasets-of-other-mapsets)
    ([temporal data processing](temporalintro.md#datasets-of-other-mapsets)).
- **Range of maps in full.** The temporal database stored the minimum and
    the maximum of a map in SQLite with six decimals, so a value such as
    1.5e-8 became 0. Now the full value is stored. Values printed with fewer
    digits can differ in the last digit, such as 3.31662 instead of 3.31663
    ([t.info](t.info.md#the-report-of-a-map)).
- **merge() of absolute and relative time.** `merge()` of a map of
    absolute time from `tmap()` with a dataset of relative time ended with
    the error "Space time datasets to merge must have the same temporal
    type", so a relation over such a list never computed. Now maps of the
    two temporal types are not related to each other:
    `C = merge(tmap(sinst), RT) : RT` selects the maps of `RT` as `RT : RT`
    does
    ([t.rast.algebra](t.rast.algebra.md#differences-from-the-reference-implementation)).
- **Selection of a relative time instance.** A selection on relative time
    with a time instance on the right and the temporal operator `r`, such as
    `RT {:,contains,r} tmap(rinst)`, ended with a `TypeError`. Now it gives
    the selected map with the time of the instance, as the new algebra does
    ([t.rast.algebra](t.rast.algebra.md#catalog-where-the-classic-algebra-differs)).

## Granularity, gaps and lists

- **Monthly series that do not start on the first day.** A series of
    months that starts on another day, such as 31 January, the last day of
    February, 31 March and 30 April, or the 15th of each month, had the
    granularity 1 day. Now steps of whole months, also those that end on the
    last day of a shorter month, count as months, and the granularity is
    1 month. The
    granularity mode **-g** of the new algebra makes one granule per month,
    and *t.rast.to.rast3* one layer per month; the classic algebra keeps
    counting such series in days. Compute the stored granularity of older
    datasets again with *t.support* **-m**; use **-c** for the old results
    of **-g**. The example [Register a series of month
    ends](#register-a-series-of-month-ends) shows such a series
    ([t.register](t.register.md#monthly-series-that-start-at-the-end-of-a-month),
    [temporal data processing](temporalintro.md#granularity)).
- **Gaps under longer maps.** A gap between two maps counted also when a
    longer map covered it. Now a gap is only time that no map covers; this
    holds for the gaps of *t.rast.list* **method=deltagaps**, *t.info*,
    *t.topology*, *t.sample*, *t.rast.mapcalc* and *t.rast3d.mapcalc*.
    *t.rast.gapfill* fills no covered gap and counts the granules of a gap
    from the start of the dataset. The classic algebra keeps the old rule
    ([temporal data processing](temporalintro.md#granularity),
    [t.rast.list](t.rast.list.md#notes)).
- **Granularity over a year and at a time of day.** Between the first days
    of two months more than a year apart, the granularity counted the
    difference of the months only (2 months instead of 14), and maps at the
    same time of day other than midnight counted in hours or minutes (ten
    days at 10:30: 14400 minutes instead of 10 days). Now the steps are
    counted in the calendar, and the names of maps with `suffix=gran` follow
    (names of days instead of names of minutes). Daily maps that overlap at
    different times of day have the granularity 1 day and get the same name
    with `suffix=gran`: *t.rast.accdetect* refuses this, *t.rast.extract*
    numbers the maps. Compute the stored granularity again with *t.support*
    **-m**, and use `suffix=num` for daily maps that overlap
    ([temporal data processing](temporalintro.md#granularity),
    [t.support](t.support.md#updating-the-metadata-computed-from-the-maps)).
- **Month steps from the end of a month.** A step of a month from the 29th,
    30th or 31st ended with the error "day is out of range for month", and
    series were built step by step from the previous time. Now a step of
    months or years ends on the last day of the target month, and a series
    counts from its first time: 31 January, the last day of February,
    31 March. Steps
    that combine units are still added one after the other. This holds for
    *t.register* **-i**, *t.shift*, *t.rast.accumulate*,
    *t.rast.accdetect*, the granules of the new algebra and the list of gaps
    ([t.register](t.register.md#monthly-series-that-start-at-the-end-of-a-month),
    [t.shift](t.shift.md#notes)).
- **Years and months as one step.** Years and months of a step were added
    one after the other: 31 March 2003 plus "1 years, 11 months" ended with
    "day is out of range for month", 1 February 2003 plus "1 years,
    1 months" gave 29 February 2004, and a step of 24 months back from
    December ended with "month must be in 1..12". Now years and months are
    one step of 12 times the years plus the months, which ends on the last
    day of a shorter month: 28 February 2005, 1 March 2004, and the step back
    is computed. This holds for **increment** of *t.register*, for *t.shift*
    and for the library ([t.shift](t.shift.md#notes)).
- **Weeks start on Monday.** A granule of a week in *t.rast.aggregate*
    began at the first map, on its day of the week, and so did the weekly
    cycles of *t.rast.accumulate*. Now weeks begin on the Monday on or
    before the first map. The classic algebra keeps the old rule
    ([t.rast.aggregate](t.rast.aggregate.md#notes)).
- **Granules of the list tools.** In *t.rast.list*, *t.rast3d.list* and
    *t.vect.list*, **method=gran** with a **granule** on relative time ended
    with a `TypeError`, and a granule of 0 or less, such as `0 days`, never
    ended. Now a number, or a number with the unit of the dataset, counts in
    the unit of the dataset, another unit is refused, and a granule smaller
    than 1 is refused before the query, with the message of
    *t.rast.aggregate* ([t.rast.list](t.rast.list.md#notes)).
- **output=- of the list tools.** `output=-` of *t.rast.list*,
    *t.rast3d.list* and *t.vect.list* wrote a file named `-` into the
    working directory. Now it is the standard output
    ([t.rast.list](t.rast.list.md#notes)).
- **Granules of *t.vect.list*.** *t.vect.list* had no option **granule**,
    and **method=gran** ended at the end of the map sorted last. Now it has
    the option **granule** with the rules of *t.rast.list*, and the granules
    reach the end of the dataset ([t.vect.list](t.vect.list.md#notes)).
- **format=line with every method.** **format=line** printed the
    identifiers with some methods only, and **method=delta** with
    **format=line** ended with a traceback. Now every method prints the
    identifiers with **format=line** ([t.rast.list](t.rast.list.md#notes)).
- **method=comma of *t.rast.list*.** **method=comma** printed the table of
    **method=list** with commas instead of the identifiers in one line. Now
    it prints the identifiers in one line, separated by **separator**
    ([t.rast.list](t.rast.list.md#methods)).
- **Delta methods of *t.vect.list*.** The delta methods of *t.vect.list*
    printed no lengths, ignored **order** without notice, **method=comma**
    changed nothing, and **format=line** required **columns**. Now the
    delta columns are there, **order** with a delta method is refused, and
    **method=comma** prints the identifiers ([t.vect.list](t.vect.list.md#notes)).
- **where with method=gran of *t.rast3d.list*.** *t.rast3d.list* refused
    **where** with **method=gran**. Now it takes it, as *t.rast.list* does
    ([t.rast3d.list](t.rast3d.list.md#notes)).
- **method=gran without granularity.** **method=gran** on an empty dataset
    or on a single time instance reported "Wrong granularity: None" or, on
    relative time with a single time instance, printed the header only and
    ended with exit code 0. Now the message says that the dataset is empty,
    or that the granularity is missing and a granule or another method is
    needed
    ([t.rast.list](t.rast.list.md#notes)).
- **Maps without start time in *t.rast.list*.** A map without start time
    ended **method=delta** and **method=deltagaps** of *t.rast.list* with a
    `TypeError`. Now it is listed with `None` in the time columns and a
    warning, and the distances count from the first map with a start time
    ([t.rast.list](t.rast.list.md#notes)).

## Sampling and topology

- **method=start keeps maps of equal time.** The sampling method `start`
    lost the maps of equal time, so a sampler map with a map of the same
    time got none. Now `start` includes `equal`; this holds for *t.sample*,
    *t.rast.mapcalc* and *t.rast3d.mapcalc*. The classic algebra keeps the
    old rule ([t.sample](t.sample.md#notes),
    [temporal data processing](temporalintro.md#sampling)).
- **Samplers of time instances.** A sampler of time instances or of the
    other temporal type made *t.sample*, *t.rast.mapcalc* and
    *t.rast3d.mapcalc* print an error and end with exit code 0. Now they
    end with an error and a non-zero exit code. Scripts that check the exit
    code see the difference ([t.sample](t.sample.md#notes)).
- **Samplers without maps and labels in *t.sample*.** A sampler without
    registered maps made *t.sample* report that the sampler must have
    intervals and end with exit code 0, a dataset with a semantic label in
    **inputs**, such as `ds.B4`, was not found, and a name without mapset
    was looked for in the current mapset only. Now a sampler without maps
    prints nothing, also with **-c** no header, and ends with exit code 0; a
    label selects its maps only, and the header names `ds.B4@mapset`; the
    search path is searched. Samplers of the other temporal type and of
    time instances are still refused ([t.sample](t.sample.md#notes)).
- **Sampling and aggregation on the new algebra.** *t.sample*,
    *t.rast.mapcalc*, *t.rast3d.mapcalc*, *t.rast.aggregate* and
    *t.rast.aggregate.ds* computed sampling and aggregation with code of
    their own. Now they use the functions of the new algebra; their results
    are those of before, and tests that record them keep them
    ([t.rast.mapcalc](t.rast.mapcalc.md#notes)).
- **Samplers and empty maps in *t.rast.aggregate.ds*.** A sampler in another
    relative unit gave no result and exit code 0, and **-n** worked the
    wrong way round: without **-n** empty maps were registered, with **-n**
    they were not. Now a sampler in another relative unit is refused, and
    **-n** registers the empty maps, which are left out without it
    ([t.rast.aggregate.ds](t.rast.aggregate.ds.md#notes)).
- **Maps without start time or with a reversed interval.** A map without
    start time, or with its end before its start, crashed the topology, the
    count of gaps and the granularity, or came into the chain of next and
    previous maps. Now such maps stand outside the chain and are left out
    with a warning, and *t.topology* ends with exit code 0
    ([t.topology](t.topology.md#notes)).
- **Empty selections in *t.topology*.** An empty selection on absolute time
    ended *t.topology* with a traceback, and an empty selection counted as
    an invalid topology. Now an empty selection is a valid topology without
    granularity ([t.topology](t.topology.md#notes)).
- **Spatial relations of 3D datasets.** A space time 3D raster dataset
    computed overlap and relations with a 3D raster map in 2D, but
    intersection and union in 3D. Now space time 3D raster datasets compute
    all spatial relations in 3D; this concerns **-s** of *t.select* and
    *t.rast3d.algebra* ([t.rast3d.algebra](t.rast3d.algebra.md#notes)).

## Registration and time stamps

- **A label after the dataset name** *(upstream)*. *t.rast.extract* and the
    other tools that open a dataset together with its map type did not
    find a dataset given as `name.label`, such as `input=sat.S2_1`: the
    run stopped with "not found". Now the label selects the maps with this
    semantic label in these tools too, as in the others. *t.register* and
    *t.unregister* with `input=name.label` work on the dataset `name`, and
    the label does not filter the maps
    ([temporal data processing](temporalintro.md#semantic-labels)).

- **Intervals with -i.** With an increment of several units, such as
    `1 months, 15 days`, and with monthly intervals from the 31st, each map
    of *t.register* **-i** ended one step after its start, which left gaps
    or overlaps. Now each map ends at the start of the next map, also for
    lists of units and for the ends of months
    ([t.register](t.register.md#notes)).
- **Times in whole seconds.** Time stamps were stored with microseconds,
    and an interval within one second stayed an interval. Now times are
    stored in whole seconds, with their time zone, and an interval within
    one second becomes a time instance ([t.register](t.register.md#notes)).
- **Relative intervals within one unit.** Relative times were cut to whole
    numbers before they were compared: an interval within one unit, such as
    1.2 to 1.7 days, was stored as the interval of length 0 from 1 to 1, and
    an end before the start within one unit was not seen. Now start and end
    are compared exactly before they are cut; an interval within one unit
    becomes a time instance, and an end before the start is refused
    ([t.register](t.register.md#notes)).
- **Reversed intervals.** An interval with its end before its start, and a
    start and an end that cannot be compared, were taken or raised an error
    without a message of their own. Now they raise a `ValueError` with a
    message, and a reversed interval that is already stored reads as a map
    without time ([t.register](t.register.md#notes)).
- **Time zone in the time stamp of a map.** The time zone offset in the
    GRASS time stamp that *t.register* writes into a map was given in
    minutes where GRASS reads hours and minutes: `+02:00` became `+0120`.
    Now it is written as hours and minutes, `+0200`
    ([t.register](t.register.md#notes)).
- **Time zones.** A time without offset in a dataset with an offset stopped
    *t.register* only after it had registered the map and changed its time.
    Now the time is refused before the registration. On PostgreSQL, a time
    with a time zone is refused ([t.register](t.register.md#notes)).
- **Layers of vector maps.** *t.register* registered a layer that the
    vector map does not have, such as `name:7`, did not check a layer without
    database link, refused a layer with categories but without table, and
    ended with a traceback for a layer that is not an integer. Now a layer
    is checked against the table or the categories of the map, a layer with
    categories but without table is registered, and a layer that is not an
    integer is refused with a message ([t.register](t.register.md#notes)).
- **Blank lines in input files.** A blank line in the file of *t.register*
    ended the list of maps without notice, and in the files of
    *t.unregister* and *t.remove* it was a map or a dataset without name.
    Now blank lines are skipped by all three
    ([t.register](t.register.md#notes)).
- **file=- and warnings of *t.register*.** `file=-` looked for a file named
    `-`, and the warnings about files with and without times came also when
    not all lines had a time and for registered maps without **start**. Now
    `file=-` reads the standard input, and the warnings come only when all
    lines have a time, or with **start** ([t.register](t.register.md#notes)).
- **Checks before the first map.** Errors of a later map, such as another
    temporal type, another unit, an invalid time or the unit of an empty
    dataset with relative time, were found only after earlier maps had been
    written. Now *t.register* checks all maps before it writes the first,
    and an empty dataset with relative time takes the unit of the first map
    of the run ([t.register](t.register.md#notes)).
- **The time of each line.** A map of a file with time columns did not
    always get the time of its own line. Now each map gets the time of its
    line ([t.register](t.register.md#input-file)).
- **End times of relative maps in a file** *(upstream)*. In a line
    `name|start|end` of a file with relative time, *t.register* read the
    third column as a semantic label, registered the map as a time instance
    and stored the end time as its label. Now an integer in the third column
    is the end time, and everything else stays a label. Register maps that
    got a wrong label again ([t.register](t.register.md#input-file)).
- **Rows and columns of maps** *(upstream)*. The temporal database held the
    numbers of rows and columns of raster and 3D raster maps exchanged, so
    *t.info* showed other values than *r.info* and *r3.info*; the number of
    cells was right. Now they are right; maps registered before keep the
    exchanged values until they are registered again with *t.register*
    ([t.info](t.info.md#the-report-of-a-map)).
- **Invalid time stamps of maps.** An invalid stored time stamp of a map, or
    a time stamp file that cannot be read, gave a traceback or an empty
    time. Now every tool that reads it stops with a message that names the
    map and the text; *t.register* stops before it writes anything
    ([t.register](t.register.md#notes)).
- **A dot in the name of a new dataset.** A new dataset could have a dot in
    its name, which was then read as the separator of a semantic label, and
    *t.create* made names that GRASS refuses as file names. Now a dot in the
    name of a new dataset is refused by every tool that creates one, the
    imports before they create a project, and names follow the rules of
    GRASS for file names. Datasets of older releases with a dot stay
    readable. Name new datasets without a dot
    ([t.create](t.create.md#notes), [t.rename](t.rename.md#notes)).
- **Datasets of older releases with a dot.** A dataset of an older release
    with a dot in its name could not be opened or removed, because the part
    after the dot was taken for a semantic label. Now each mapset, the
    current one first and then those of the search path, is searched for the
    whole name first and then for the name with label; the classic algebra
    still takes the label off first
    ([temporal data processing](temporalintro.md#semantic-labels)).

## Datasets of other mapsets

- **Datasets name@mapset of every mapset** *(partly upstream)*. In GRASS
    8.5, the temporal tools refused a dataset `name@mapset` of a mapset
    outside the search path. Upstream, the tools that open a dataset with
    `open_old_stds()` began to read it. Now every temporal tool reads
    `name@mapset` of another mapset of the same project if that mapset has a
    temporal database; an unknown mapset and a mapset without temporal
    database are refused, without the list of mapsets. A name without
    mapset is looked for in the current mapset and then in the search path.
    *t.rast.mapcalc*, *t.rast3d.mapcalc* and *t.rast.accdetect* also read
    the maps of such a dataset; their expressions name the maps with their
    mapset. `g.mapsets operation=add` is no longer needed for `name@mapset`
    ([temporal data processing](temporalintro.md#datasets-of-other-mapsets)).
- **Names without mapset stay in the search path.** In
    *t.rast.aggregate.ds*, *t.vect.what.strds*, *t.vect.observe.strds*,
    *t.rast.accumulate*, *t.remove* and *t.unregister*, a name without
    mapset found a dataset of a mapset outside the search path once that
    mapset had been read with `name@mapset`. Now a name without mapset is
    looked for in the current mapset and the search path only
    ([temporal data processing](temporalintro.md#datasets-of-other-mapsets)).
- **The search path in more tools.** *t.vect.univar*, *t.rast.accdetect*,
    *t.info* and *t.sample* looked for a dataset name without mapset in the
    current mapset only. Now they look in the current mapset and then in
    the search path, as the other tools do
    ([temporal data processing](temporalintro.md#datasets-of-other-mapsets)).
- **Extracts from another mapset.** An extract without **expression** from
    a dataset of another mapset with *t.rast.extract*, *t.rast3d.extract*
    or *t.vect.extract* stopped and left an empty dataset behind. Now the
    maps of the other mapset are registered as by *t.copy* without **-c**,
    with their times ([t.rast.extract](t.rast.extract.md#notes)).
- **Datasets of another mapset refused early.** *t.rast.gapfill*,
    *t.unregister*, *t.support*, *t.remove*, *t.rast.accumulate* (for
    **output**), *t.register*, *t.shift*, *t.snap* and *t.rast.accdetect*
    refused a dataset of another mapset only late, after output, an
    interpolation, a computation or the registration of a map. Now they
    refuse it before they read or write anything
    ([temporal data processing](temporalintro.md#datasets-of-other-mapsets)).
- **Maps and datasets shared with other mapsets.** *t.info* did not find a
    map of another mapset that is registered only in a dataset of the
    current mapset, *t.merge* could not merge datasets of other mapsets,
    *t.support* **-m** read no map of another mapset, *t.rast.colors* **-w**
    did not find the color tables of such maps, and *t.remove* did not find
    the datasets that share a map of another mapset. Now all these cases
    work ([t.merge](t.merge.md#notes)).

- **No files written for maps of other mapsets** *(upstream)*. The time
    stamp and the semantic label of a map are files in the current mapset,
    whatever mapset the map is named after. Registering or copying a map of
    another mapset wrote such a file into the current mapset for a map that
    is not there (a file `cell_misc/<name>/semantic_label` for a label), or
    removed a file that was not the map's own. Now no tool writes or
    removes the time stamp file or the semantic label file of a map of
    another mapset; the temporal database of the current mapset still
    records the time and the label of the map
    ([temporal data processing](temporalintro.md#datasets-of-other-mapsets)).

## Tools

### Options of several tools

- **suffix.** An unknown value of **suffix** counted as `num`, and a
    dataset with exactly one time instance and `suffix=gran` ended with an
    `AttributeError`. Now an unknown suffix is refused before the first map
    is written, and a single time instance is named after its time; this
    holds for every tool with **suffix**. Correct the value of **suffix**
    ([t.rast.extract](t.rast.extract.md#notes)).

### t.connect

- **Formats and mapsets** *(upstream)*. *t.connect* printed with **-p** and
    **-g** as text only. Now **-p** takes **format** (`plain`, `shell` or
    `json`, always an array), **-g** is deprecated and equals
    `format=shell`, **-g** with `format=json` and **format** without **-p**
    are refused, and **mapset** (only with **-p** and `format=json`) prints
    the connections of other mapsets. Replace **-g** by `format=shell` and
    read the JSON as an array ([t.connect](t.connect.md#description)).
- **Empty values and -p.** An empty **driver** or **database** was set,
    and **-p** could be combined with **-c**, **-d** or **-g**. Now empty
    values, and **-p** or **-g** together with **-c** or **-d**, are refused;
    one option given alone still sets the other to its default
    ([t.connect](t.connect.md#notes)).

### t.copy

- **Copies of maps with -c.** **-c** with **--overwrite** in the same
    mapset took the maps from the source dataset, **-c** failed for str3ds
    and stvds after the first copy, and **-c** with **--overwrite** did not
    replace maps of the same name. Now **-c** copies all types, checks
    everything before the first copy, replaces maps of the same name in the
    current mapset with **--overwrite** and refuses a map that is registered
    in another dataset ([t.copy](t.copy.md#notes)).

### t.info

- **Report.** The semantic label of a map was never shown, **-h** put a
    backslash before the comment line of the history, **-d** with **-h**
    and without **input** looked for a dataset in PERMANENT, and the line
    `East` had a shorter row of dots. Now the label is shown, the last line
    of a command has no backslash, **-d** with **-h** asks for **input**, and
    the line `East` has the full row of dots
    ([t.info](t.info.md#the-report-of-a-space-time-dataset)).

### t.list

- **Output formats** *(upstream)*. *t.list* printed text with
    **separator** only. Now **format** is `plain`, `line`, `json` or `csv`;
    **columns** defaults to `id` (with `json` all metadata); `csv` has a
    comma as separator and the column names in the first line; a missing
    value is empty in `csv`, `None` in `plain` and `line`, `null` in `json`;
    **separator** or **-c** with `json`, and more than one column with
    `line`, are refused ([t.list](t.list.md#description)).
- **Mapsets** *(upstream)*. *t.list* listed the mapsets of the search path.
    Now **mapset** takes `.`, `*` or a list of mapsets, also outside the
    search path, and an unknown mapset ends *t.list* with an error. Set
    **mapset** for mapsets outside the search path
    ([t.list](t.list.md#description)).
- **Several types** *(upstream)*. **type** took one type of dataset. Now it
    takes a list, such as `strds,stvds`; the columns must exist for all
    types, `csv` and `json` add the column `type`, and `line` with several
    types is refused ([t.list](t.list.md#description)).
- **No temporal database** *(upstream)*. *t.list* created a temporal
    database in a mapset without one. Now it creates none and prints that
    there are no datasets to list (in `plain`; `json` prints `[]`), with exit
    code 0 ([t.list](t.list.md#notes)).
- **Errors and empty results.** `type=raster_3d` failed with an SQL error,
    an unknown column in **order** gave a message about the where
    condition, an unknown mapset ended with exit code 0, `csv` printed
    nothing without matches, and the output file was opened before the
    queries. Now `type=raster_3d` lists, **order** has a message of its own,
    an unknown mapset is an error, without matches `csv` prints the header
    (and `plain` with **-c**), the file is written after the queries, and
    **columns** knows `number_of_semantic_labels` ([t.list](t.list.md#notes)).

### t.merge

- **Output and failures.** `output=name@mapset` ended with an
    `UnboundLocalError`, a failure left the empty output dataset behind, and
    after a stop the message "Needed to restart the messenger server"
    appeared. Now an output with the current mapset works, a failure leaves
    no output dataset, and the message is gone ([t.merge](t.merge.md#notes)).

### t.rast.accdetect

- **Thresholds, cycles and results.** *t.rast.accdetect* had the errors of
    the thresholds of *t.rast.accumulate*, **minimum** and **maximum**
    without **range** ended with an `IndexError`, refusals came with a
    traceback, the last map of a cycle was never its end, a time instance at
    the end without **stop** was left out, an empty result created datasets,
    and conflicts of names showed only late. Now these are fixed: a run ends
    at the end of its cycle, an empty result warns and creates no dataset
    (with **--overwrite** it removes existing ones), all new maps are
    checked before the first, and a run of one map gets the indicator 1
    ([t.rast.accdetect](t.rast.accdetect.md#notes)).

### t.rast.accumulate

- **Thresholds, cycles and results.** Threshold maps of the same time were
    never found, **-r** read the threshold of another day, relative time
    ended with a traceback, a cycle without maps stopped the tool, **start**
    was moved to the granularity without notice, a time instance at the end
    without **stop** was left out, an empty result created a dataset,
    `suffix=gran` followed the granularity of the input, conflicts of names
    showed only after earlier granules, and **--overwrite** removed a map of
    another dataset. Now thresholds of the same time are found, **-r** reads
    the right day, relative time works, empty cycles are skipped, a moved
    **start** is warned about, the time instance at the end is processed,
    an empty or all null result warns without dataset and with
    **--overwrite** removes an existing one, `suffix=gran` follows the
    option **granularity**, all names are checked before the first granule,
    and only maps of the old output dataset are replaced
    ([t.rast.accumulate](t.rast.accumulate.md#notes)).
- **Cycles and stop.** In *t.rast.accumulate* and *t.rast.accdetect*, a
    relative `stop=0` and an end of the data at 0 were not taken as the end,
    and cycles with a negative **offset** ran beyond **stop** or backwards.
    Now cycles end at **stop**, whose default is the end of the data, also
    at 0, and cycles that run backwards are refused
    ([t.rast.accumulate](t.rast.accumulate.md#notes)).

### t.rast.aggregate

- **Names, granularity and empty results.** A result name equal to an
    input map was overwritten with **--overwrite** while *r.series* read it,
    a granularity without unit ended with an `IndexError`, mixed
    granularities were not described, and granules without maps gave no
    notice. Now the tool stops before any computation for an equal name,
    reports an invalid granularity, refuses mixed granularities, and warns
    about an empty result, with exit code 0 and no dataset
    ([t.rast.aggregate](t.rast.aggregate.md#notes)).
- **Many maps in a granule.** *r.series* opened all maps of a granule, so
    an aggregation of more maps than open files allows failed, for example
    30 maps with a limit of 1024 open files on 24 cores. Now *r.series*
    runs with **-z** when two times the threads times the maps plus 64
    exceeds the soft limit of open files, with the threads counted as
    *r.series* counts them and a raster mask as one thread; **file_limit**
    stays an upper limit, and each such run warns. This holds for
    *t.rast.aggregate*, *t.rast.aggregate.ds* and
    `aggregate_raster_maps()` ([t.rast.aggregate](t.rast.aggregate.md#notes),
    [t.rast.aggregate.ds](t.rast.aggregate.ds.md#notes)).

### t.rast.colors

- **Color tables with -w.** **-w** wrote no table to any map once one map
    of the dataset had one, because *r.colors* stopped, and **-l** could not
    be used. Now **-w** leaves out the maps with a table and writes the
    others, also maps of other mapsets, and **-l** lists the rules
    ([t.rast.colors](t.rast.colors.md#notes)).

### t.rast.contour

- **Empty results and names.** Without **-n**, a run with empty maps only
    created an empty dataset, and two maps of equal time with `suffix=gran`
    got the same name. Now the run warns and creates no dataset (with
    **--overwrite** it removes the old one), and equal names are refused
    before the first map ([t.rast.contour](t.rast.contour.md#notes)).

### t.rast.export and t.vect.export

- **Types, nodata and empty selections.** A CELL map with **nodata** and
    GTiff ended with a `TypeError`, AAIGrid with `nodata=-77` stopped, a map
    without values ended with a traceback, `init.txt` held the extent of the
    whole dataset, an empty archive came without notice, and **createopt**,
    **metaopt** and **nodata** were ignored for `pack` and AAIGrid without
    notice. Now **nodata** is passed once, with the smallest type that holds
    the values and the nodata value; `init.txt` has the extent of the
    selected maps; an empty selection warns and the archive stays; ignored
    options are warned about ([t.rast.export](t.rast.export.md#notes)).
- **Maps of several mapsets.** The export passed map names without mapset,
    so the search path could give a map of the same name of the current
    mapset, and maps of the same name from several mapsets could not be told
    apart. Now the export passes `name@mapset`, and maps of the same name
    come into the archive as `name@mapset`; archives without shared names
    are the same character for character
    ([t.rast.export](t.rast.export.md#notes)).
- **Layers in GML and GPKG.** *t.vect.export* exported a map with several
    layers, or one map selected twice with the same layer, into a wrong
    archive. Now this is refused before anything is written
    ([t.vect.export](t.vect.export.md#notes)).

### t.rast.extract, t.rast3d.extract and t.vect.extract

- **Existing and equal names.** Existing map names gave an error, but the
    run ended with exit code 0, and two maps of the same time, also two
    layers, got the same name and the run failed. Now existing maps are
    refused before the first map, with a non-zero exit code, and a running
    number is appended to names that stay equal
    ([t.rast.extract](t.rast.extract.md#notes)).

### t.rast.gapfill

- **The flag -t.** The flag **-t** was in the interface but never had an
    effect. Now it is removed, and a call with **-t** is refused. Remove
    **-t** from scripts ([t.rast.gapfill](t.rast.gapfill.md#description)).
- **Gaps after time instances.** In a dataset of time instances, the tool
    found the gap but no predecessor and ended with exit code 1, and a gap
    after a time instance at the end of an interval was not filled. Now a
    dataset of time instances only and a gap after a time instance are
    refused before anything is written, a gap after a time instance that
    ends an interval is filled, and mixed datasets work as before
    ([t.rast.gapfill](t.rast.gapfill.md#notes)).

### t.rast.import and t.vect.import

- **Names from several mapsets.** Maps of one name from several mapsets in
    an archive are imported as `name_mapset` without **basename**; equal
    import names and an archive that lists a map twice are refused before
    the first map ([t.rast.import](t.rast.import.md#notes)).
- **Numbers, projects and formats.** The numbers of new maps began at 2, an
    archive without projection could not be imported into a new project, GPKG
    archives could not be read, **-e** had no effect for `pack`, the layer
    got lost, *t.vect.import* did not stop for another coordinate system and
    required **directory**, and a second import into a project created by the
    tool failed. Now numbers begin at 1, an archive without projection gets
    an XY project, GPKG archives are read, **-e** and **project** extend the
    region for `pack`, the layer stays, a vector archive of another
    coordinate system stops the import as for rasters (**-o** overrides),
    **directory** is optional, and the region of a new project is set. Set
    **-o** for vector archives of another coordinate system where wanted
    ([t.vect.import](t.vect.import.md#notes),
    [t.rast.import](t.rast.import.md#notes)).
- **Temporary directory and Python** *(upstream)*. The default of
    **directory** was `/tmp`, and a new project was entered with *g.mapset*.
    Now the default is a directory in the current mapset, a new project is
    entered with a temporary session file, and the import needs Python 3.11.4
    or newer: without the data filter of `tarfile` it stops with "Extracting
    may be unsafe; upgrade Python to 3.11.4 or newer". GML with **link** uses
    *v.external*. Update older Python versions; scripts for *t.vect.import*
    with another coordinate system need **-o**
    ([t.rast.import](t.rast.import.md#notes)).

### t.rast.list

- **CSV** *(upstream)*. In *t.rast.list* and *t.vect.list*, `format=csv`
    with `separator=|` was set to a comma without notice. Now `csv` has a
    comma as default separator and takes `separator=|`; `json` and `yaml`
    refuse **separator** ([t.rast.list](t.rast.list.md#output)).
- **method=gran with where** *(upstream)*. **method=gran** refused
    **where**. Now it takes it, with start and end from the selected maps
    instead of the dataset ([t.rast.list](t.rast.list.md#methods)).
- **Old temporal databases.** On a temporal database of version 2,
    columns with `semantic_label` ended with "Invalid where condition", and
    a semantic label was refused without a hint. Now the message points to
    *t.upgrade*; this holds for *t.rast.list* and *t.list*. Run *t.upgrade*
    ([t.rast.list](t.rast.list.md#notes)).

### t.rast.mapcalc and t.rast3d.mapcalc

- **Names, inputs and empty selections.** Existing maps of the basename
    gave an error with exit code 0, dataset names were replaced as text
    (`start_day_1`), `inputs=x,x` and blanks in the expression got lost, and
    an empty sampler, an empty **where** selection or an empty dataset ended
    with a message and exit code 0 or with an error. Now existing maps are
    refused before the first map, names are replaced as whole words and not
    before `(`, a repeated input is refused, blanks stay, and the empty cases
    warn ("No samples found for map calculation", "The where condition
    selects no map ...") and end with exit code 0 and no dataset
    ([t.rast.mapcalc](t.rast.mapcalc.md#notes),
    [t.rast3d.mapcalc](t.rast3d.mapcalc.md#notes)).
- **Semantic labels of 3D rasters.** In *t.rast3d.mapcalc*, a semantic
    label of a 3D raster map stopped the run, and the label operator `@`
    gave null. Now the run goes through, and `@map` gives the number of the
    label as in *r.mapcalc*
    ([t.rast3d.mapcalc](t.rast3d.mapcalc.md#notes)).

### t.rast.neighbors

- **Quantiles, -e and names.** Further quantiles were ignored without
    notice, **-e** required **--overwrite**, and equal result names in one
    run failed after the first map was written. Now **quantile** takes one
    value (a list is refused), **-e** adds maps without **--overwrite**, and
    equal names and existing rasters are refused before the first map
    ([t.rast.neighbors](t.rast.neighbors.md#notes)).

### t.rast.series

- **Order, quantiles and empty selections.** `order=modification_time`
    ended with an SQL error, several quantiles could not be computed, the
    time of the output map followed **order**, and an empty **where**
    selection ended without notice. Now `modification_time` is no order (the
    parser refuses it), several quantiles are computed, one for each method
    `quantile`, the output
    map has the time span of the selected maps, and an empty selection or
    dataset warns. Remove `order=modification_time` from scripts
    ([t.rast.series](t.rast.series.md#notes)).

### t.rast.to.rast3

- **Output, units and overlaps.** Each run printed "Gran from stds" to the
    standard output, an empty dataset reported "Wrong granularity: None",
    hours, minutes and seconds gave another vertical unit, a cube of time
    instances reached beyond the end, and overlapping maps were written
    without notice. Now the granularity is a verbose message, the message
    says that the dataset is empty, the vertical unit is days, a cube of time
    instances ends at the last instance plus the granularity, and
    overlapping maps are refused before anything is written
    ([t.rast.to.rast3](t.rast.to.rast3.md#notes)).

### t.rast.to.vect

- **Empty maps and errors.** With **-b**, empty maps were registered also
    without **-n**, and a failing *r.to.vect* ended without a message. Now
    empty maps are registered only with **-n**, and an error of
    *r.to.vect* is reported ([t.rast.to.vect](t.rast.to.vect.md#notes)).

### t.rast.univar and t.rast3d.univar

- **Formats and columns** *(upstream)*. *t.rast.univar* printed the columns
    `...|mean|min|max|mean_of_abs|stddev|variance|coeff_var|sum|null_cells|cells|non_null_cells`,
    where `cells` and `non_null_cells` were both the number of valid cells,
    and set `nprocs=0` and negative values to 1 without notice. Now
    **format** is `plain`, `csv` or `json`, and the columns come in a new
    order that is not compatible:
    `...|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs`,
    with `zone|label` in front with zones, and with **-e** the quartiles and
    `percentile_90` by default; `nprocs=0` uses all cores and a negative
    value the cores plus that value. Scripts that read columns by their
    position have to read them by the names of the header
    ([t.rast.univar](t.rast.univar.md#description)).
- **Inputs, percentiles and formats of *t.rast3d.univar*** *(upstream)*.
    **input** was declared as a raster map, and there was no **percentile**,
    no **region_relation** and only plain text. Now **input** and **zones**
    are 3D raster maps, **percentile** (with **-e**), **region_relation**
    and **format** (`plain`, `json`, `csv`) are there
    ([t.rast3d.univar](t.rast3d.univar.md#description)).
- **Regions, empty selections and zones.** **-r** with **zones** did not
    use the region of each map, `format=json` with an empty selection
    printed nothing, the parser did not check **region_relation**, and
    *t.rast3d.univar* rounded floating point zones without notice. Now **-r**
    holds with **zones**, an empty selection prints `[]`, the parser checks
    **region_relation**, and floating point zones are refused as in 2D
    ([t.rast.univar](t.rast.univar.md#notes)).

### t.rast.what

- **Order, coordinates and empty results.** The order of the lines depended
    on **nprocs**, **-i** did not pass **coordinates**, with more than 400
    maps the last map could get lost, a file was left in the directory,
    coordinates were padded to ten decimals, and a run in which *r.what*
    wrote no line ended without notice. Now the order of the points is
    fixed, the last map is there, the directory stays clean, coordinates
    have the precision of *r.what*, and a run in which *r.what* samples no
    location ends with a message ([t.rast.what](t.rast.what.md#notes)).

### t.rast3d.list

- **Formats, granules and checks** *(upstream)*. *t.rast3d.list* printed
    plain text only and checked few options. Now **format** is `plain`,
    `line`, `json`, `yaml` or `csv`, there is the option **granule** and the
    columns `interval_length` and `distance_from_begin`, **order** with the
    methods `delta`, `deltagaps` and `gran` is refused, columns that do not
    fit the method are refused, **where** works with **method=gran**, and a
    granule smaller than 1 is refused ([t.rast3d.list](t.rast3d.list.md#output)).

### t.remove

- **Shared maps and failures.** **-rf** did not update the metadata of other
    datasets that shared maps, a failed call with **-r** had already removed
    maps, and **-f** without **inputs** and **file** did nothing. Now the
    other datasets are updated, all datasets are opened first, a call
    without **inputs** and **file** is an error, and maps of other mapsets
    are named with a warning ([t.remove](t.remove.md#notes)).

### t.shift

- **Lists of units and empty datasets.** **granularity** took one step of
    one unit, an empty dataset was skipped without notice, and a shift to a
    day that does not exist ended with a traceback. Now **granularity**
    takes a list such as `1 years, 1 months`, which is added as one step, a
    unit named twice is refused, an empty dataset is reported with exit code
    0, and steps of months end on the last day of the month
    ([t.shift](t.shift.md#notes)).

### t.snap

- **Empty datasets.** *t.snap* ended with a traceback for an empty dataset.
    Now it leaves an empty dataset as it is and refuses an empty dataset of
    another mapset ([t.snap](t.snap.md#notes)).

### t.support

- **Semantic type, -u and -m.** Each call set the semantic type to `mean`
    and wrote the dataset again, **-u** was read and overwritten at once,
    **aggr_type** for an stvds ended the tool without notice, and **-m**
    updated only the given dataset. Now the semantic type stays without the
    option, **aggr_type** for an stvds warns and the other options work, and
    **-m** updates every dataset that holds a changed map and reads maps of
    other mapsets
    ([t.support](t.support.md#updating-the-metadata-computed-from-the-maps)).

### t.unregister

- **Messages and files.** The messages named **input** instead of **maps**,
    a missing file ended with a traceback, and the progress ended before
    100 %. Now the messages name **maps**, a missing file is reported, and
    the progress reaches 100 % ([t.unregister](t.unregister.md#notes)).

### t.upgrade

- **Indices, transaction and views.** The upgrade from version 2 to 3 did
    not create four indices, did not run in one transaction, and did not
    renew the views on version 3. Now the indices of the new schema are
    created, the upgrade is one transaction, and the views are renewed also
    on version 3 ([t.upgrade](t.upgrade.md#notes)).

### t.vect.db.select

- **Formats** *(upstream)*. *t.vect.db.select* printed plain text only. Now
    **format** is `plain`, `csv` or `json`; the separator of `csv` is one
    character, **separator** is refused with `json`, and `json` gives the
    time first and `[]` for a map without matches
    ([t.vect.db.select](t.vect.db.select.md#description)).
- **Columns, empty selections and layers.** A column that only some maps
    have gave half an output, a **t_where** without matches ended without
    notice, and the layer of a map carried over to later maps without layer.
    Now all maps are checked first and every missing column is named in one
    message, an empty **t_where** warns (exit code 0), and **layer** holds
    for each map without a layer of its own
    ([t.vect.db.select](t.vect.db.select.md#notes)).

### t.vect.list

- **Formats** *(upstream)*. As for *t.rast.list*, `format=csv` takes
    `separator=|`, and `json` and `yaml` refuse **separator**; see also the
    granules and delta methods in [Granularity, gaps and
    lists](#granularity-gaps-and-lists) ([t.vect.list](t.vect.list.md#output)).

### t.vect.observe.strds

- **where, columns and empty results.** **where** worked on layer 1 only, a
    column of the input was overwritten, **where** without matches gave a
    `KeyError`, no common granule ended with an empty dataset without
    notice, **--overwrite** kept old values of points that were not sampled,
    `columns=a,a` failed after writing, and column names were compared with
    their case. Now **where** selects the points once before the copy and is
    refused for input with several layers, existing columns and columns that
    differ only in case are refused, **where** without points is reported,
    no common granule warns without dataset, values not sampled are NULL,
    and repeated columns are refused before writing
    ([t.vect.observe.strds](t.vect.observe.strds.md#notes)).

### t.vect.univar

- **Null values and errors.** NULL counted as 0 in the extended statistics,
    because *v.univar* counted it so, and errors of *v.univar* ended with a
    traceback. Now NULL is left out, the quartiles come from the features,
    as *v.univar* computes them today, and errors
    are reported with a message ([t.vect.univar](t.vect.univar.md#notes)).

### t.vect.what.strds

- **Columns, units and quantiles.** A second run with the same column wrote
    without a check, the aggregate column was named after a removed
    temporary map, another relative unit ran without notice, `quantile` had
    no option, time instances forced `start` without notice, a column that
    differs only in case was taken, and one layer under two identifiers
    wrote a column twice. Now all target columns are checked first and
    refused without **--overwrite**, the aggregate column has a fixed name,
    another unit is refused, **quantile** is an option (default 0.5), time
    instances without `start` warn, columns that differ only in case are
    refused also without **--overwrite**, and a layer given twice is refused
    ([t.vect.what.strds](t.vect.what.strds.md#notes)).

## Other tools and libraries

- ***r.contour*.** Levels of **step** had no anchor in the step grid, regions
    with one or two rows or columns hung the tool, lines ran over null
    cells, levels on the minimum or maximum gave no line, rings through
    border cells and lines through saddle cells at the border were lost,
    `minlevel > maxlevel` gave an empty map, **cut** worked before snapping,
    lines of one point crashed the tool, and **step** on a map without
    values crashed it. Now levels come from the step grid (anchored at
    **minlevel**, else at 0) within the limits and the range of the map,
    `step <= 0` and more levels than an integer holds are errors, lines end
    open at null cells, extreme levels, border rings and saddles are traced,
    `minlevel > maxlevel` is an error, **cut** works after snapping, no
    line has one point, and a map without values gives an empty map
    ([r.contour](r.contour.md)).
- ***r.univar* and *r3.univar*.** Without a valid cell, *r.univar* printed
    `-1.79769e+308` as maximum and `-nan`; *r3.univar* counted cells masked
    by the 3D mask and rounded floating point zones without notice. Now
    `nan` is printed without sign, and *r3.univar* respects the 3D mask and
    refuses zones that are not integers ([r.univar](r.univar.md),
    [r3.univar](r3.univar.md)).
- ***r3.support*.** `raster=` ended with "Raster map `<layers>` not found", so
    categories could not be set. Now the categories are taken from the
    raster map ([r3.support](r3.support.md)).
- ***r3.mapcalc* and the 3D mask.** *r3.mapcalc* did not respect the 3D mask,
    `@map` gave null, the mask of tiles hid wrong cells with another region,
    and a mask on another grid was applied differently by each tool. Now
    the 3D mask applies when existing maps are read (a constant stays
    unmasked, a 2D mask has no effect), `@map` gives the number of the
    label, and a value is masked exactly when the mask is null at its
    location; with the region of the map the result is the same byte for
    byte ([r3.mask](r3.mask.md#notes)).
- **3D rasters of reduced precision.** A 3D mask, and any 3D raster map of
    reduced precision with tiles that compress, could not be read, and on
    little-endian machines every 3D raster map of reduced precision stored
    wrong values since 2012; only 0 and null were right. Now these maps are
    read, writing and reading exchange the bytes around the packing on
    little-endian machines, and new maps are written as version 3, whose
    bytes are exchanged when they are read. Old maps read as before, with
    their wrong values; *r3.null* on an old map writes 0; older releases
    read new maps of reduced precision wrongly, with values near 0. Make
    maps of reduced precision of older releases again where the values are
    needed ([3D raster data](raster3dintro.md#3d-raster-data-types)).
- ***v.unpack*.** In a project without projection information (XY),
    *v.unpack* ended with a `FileNotFoundError`. Now the missing file counts
    as another coordinate system, and **-o** allows the import
    ([v.unpack](v.unpack.md)).
- ***v.univar*.** **-e** sorted NULL rows as 0 and took the quartiles from
    the rows of the table instead of the features. Now NULL is left out, and
    the values come from the features; a category of two features counts
    twice ([v.univar](v.univar.md)).
- **Integer and floating point options.** An integer or floating point
    option took text behind the number, such as `5abc` or `2.5abc`. Now such
    text is refused (blanks are allowed, an underflow is valid, an overflow
    refused), and each value of a tuple is checked. Correct such values
    ([g.parser](g.parser.md)).
- **The temporal database.** The PostgreSQL back end did not work
    throughout, new SQLite databases had 27 indices that repeat the primary
    key, and the C library set up a new environment in each call. Now
    PostgreSQL works and is tested, new databases have no repeated indices
    (8,859,648 instead of 10,215,424 bytes for 20,000 maps; the index of
    the register stays), and the C library reads the variables of the
    mapset without a new environment (about 70 kB instead of 48,444 kB of
    memory over 40,000 calls). The schema is unchanged
    ([t.connect](t.connect.md#notes)).
- **SQLite 3.33 or newer** *(upstream)*. The templates for SQLite before
    3.33 were removed; with an older SQLite, the update of a dataset ends
    with a message to update SQLite or to use PostgreSQL with *t.connect*
    ([t.connect](t.connect.md#notes)).
- **The region of *r.mapcalc*.** With `region=union` or `region=intersect`,
    *r.mapcalc* wrote the computed region into the region file of the
    mapset, so after *t.rast.algebra* **-s** the region of the session was
    that of the last maps. Now that region holds for the process only
    ([r.mapcalc](r.mapcalc.md)).

## Python API and addons

The public interface of `grass.temporal` that the repository and the addons of
grass-addons use is recorded in a contract of the tests
(`python/grass/temporal/tests/data/public_contract.json`), and a test keeps it.
Every name of the contract that the addons use was there before GRASS 8.6 and is
kept: the package names such as `open_old_stds`, `open_new_stds`, `init`,
`SpaceTimeRasterDataset` and `register_maps_in_space_time_dataset`, the modules
`core`, `datetime_math`, `list_stds` and `space_time_datasets`, and the methods
and members of the dataset classes, such as
`SpaceTimeRasterDataset.metadata.get_number_of_maps()` and
`RasterDataset.absolute_time.start_time`. Code that uses only these names needs
no change. Names of the contract that only the repository uses can be new in
GRASS 8.6, such as the steps that the temporal tools share, and code that has to
run with GRASS 8.5 cannot use them. The reference documentation of the temporal
framework
([temporal framework](https://grass.osgeo.org/grass-devel/manuals/libpython/temporal_framework.html))
describes every module.

- **The names of the package.** `grass.temporal` imported all names of its
    modules with star imports. Now it exports the names that the
    repository and the addons use, among them all package names of the
    contract, and the steps that the temporal tools share. Code that
    imports another name from `grass.temporal` has
    to import it from the module that defines it today; the table below
    names this module for each name that `grass.temporal` exported in
    GRASS 8.5 and no longer exports.
- **New modules.** The package `grass.temporal.algebra` holds the new
    implementation of the temporal algebra, with series, relations,
    operations, the back ends for raster, 3D raster and vector maps, the plan
    of a computation and its parser; a reduction with `nulls="skip"` passes
    the maps to *r.series* in a file and uses **-z** above the limit of open
    files. The module `grass.temporal.tool_steps` holds the steps that the
    temporal tools share, and `grass.temporal.testing` the helpers of their
    tests ([writing a temporal
    tool](https://grass.osgeo.org/grass-devel/manuals/libpython/temporal_framework_tools.html),
    [extending the algebra
    core](https://grass.osgeo.org/grass-devel/manuals/libpython/temporal_framework_algebra.html)).
- **The classic algebra moved.** The modules of the algebra of the releases
    before, `temporal_algebra`, `temporal_raster_base_algebra`,
    `temporal_operator` and their siblings, moved to
    `grass.temporal.classic`. The parser classes that `grass.temporal`
    exports, such as `TemporalRasterAlgebraParser`, now select the new or
    the classic algebra.
- **Comparisons without eval** *(upstream)*. The algebra of the releases
    before compared values with `eval` of strings. Now it uses
    `compare_values()`, `eval_datetime_str()` is deprecated, and a value in
    a list of conditions that is not a Boolean raises a `TypeError`; both
    methods are in `grass.temporal.classic.temporal_algebra` only. The
    results are the same.
- **Parser tables.** The classic parser built its tables in each call of
    `parse()`. Now they are built once for each parser class.
- **Directory of the SQL templates** *(upstream)*. `get_sql_template_path()`
    took the directory of the SQL files that create and update the temporal
    database from `GISBASE`, below which it assumed `etc`. Now it takes
    `GRASS_ETCDIR`, which `grass` sets, so an installation that keeps `etc`
    elsewhere works. Outside a GRASS session without this variable, the
    function raises a `KeyError`.
- **Maps of other mapsets** *(upstream)*. `BaseRow.get_readonly()`, the
    property `readonly` and `AbstractMapDataset.get_readonly()` are new. They
    tell whether a map belongs to another mapset than the current one, and
    the library writes the time stamp and label files only for maps that are
    not read-only. There is no `set_readonly()`: the answer is computed at
    each call, so it cannot become wrong when the current mapset changes.
- **Initialization** *(upstream)*. `init()` always created the temporal
    database. Now `init(skip_db_init=True)` creates none and checks no
    version, dataset objects work without a temporal database, the default
    back end is SQLite before the initialization, the message and C library
    servers start again after a change of the session, and SQLite waits up
    to 30 s for a locked database. Mapsets with a connection but without a
    database file are skipped, and "Creating temporal database" is a verbose
    message: scripts that read it have to set **--verbose**.
- **Switches and sessions of init().** The switches `TGIS_DISABLE_*` had no
    effect, and a second session in one process kept the error mode and the
    servers of the first. Now the switches work, and `init()` sets the error
    mode and the servers in each call.
- **Connections to mapsets** *(upstream)*. `SQLDatabaseInterfaceConnection`
    and `get_available_temporal_mapsets()` take the argument `mapsets`, and
    `get_dataset_list()` takes the mapsets of the connection; with a list of
    types, it returns a dictionary for each row with the key `type`. Read
    the rows as dictionaries when you pass a list.
- **Registering maps** *(upstream)*. `register_maps_in_space_time_dataset()`
    took `dbif` as a positional argument and used it. Now it opens its own
    connection to the current mapset, `dbif` is a keyword argument only,
    deprecated and ignored with a warning, and `name` is optional. Remove
    `dbif` from calls; a transaction of the caller is not used.
- **Identifiers in SQL.** Identifiers went into SQL statements unbound, so
    SQL could be injected, `set_id()` with a layer split the identifier
    wrongly, and a **where** with OR together with a label or an extent was
    not put into parentheses. Now identifiers are bound or checked,
    `set_id()` splits name, layer and mapset, and conditions are put into
    parentheses.
- **Granules with where** *(upstream)*.
    `get_registered_maps_as_objects_by_granularity()` takes **where** before
    `dbif`. Calls that pass `dbif` as the third positional argument have to
    change.
- **nprocs of aggregate_raster_maps()** *(upstream)*.
    `aggregate_raster_maps()` passes the keyword argument `nprocs` to
    *r.series* (0 for all cores).
- **Dates beyond the year 9999.** A step of days beyond the year 9999
    raised an `OverflowError`. Now it raises a `ValueError` with a message,
    as steps of months and years did already.
- **Relations of no maps.** `count_temporal_relations()` of an empty list of
    maps returned `None`. Now it returns a dictionary with zeros;
    `check_temporal_topology([])` stays `False`.
- **ctime and mtime.** `BaseRow.set_ctime()` and `set_mtime()` kept
    microseconds in memory, while the database held whole seconds. Now they
    keep whole seconds too, with their time zone.
- **Intersections of relative extents.** `RelativeTemporalExtent.intersect()`
    of two extents in different units gave a result, also for separate
    numbers. Now it returns `None` when both units are set and differ.
- **Failed SQL statements on PostgreSQL.** A failed PostgreSQL statement in
    `DBConnection.mogrify_sql_statement()` was printed to the standard
    output. Now nothing is printed.
- **Invalid spatial relations** *(upstream)*. The selection by an invalid
    spatial relation reported an error and then raised a `RuntimeError`.
    Now it raises a `ValueError` with the message.
- **shift()** *(upstream)*. `AbstractSpaceTimeDataset.shift()` returned
    `None`. Now it returns `True`, and `False` for a dataset without maps.
- **Messages** *(upstream)*. The fatal messages of `shift()` and `snap()`
    raised a `TypeError` instead of the message, and the messages for a
    failed removal of a time stamp showed `<%s>` or spoke of a raster map
    for a 3D raster map. Now they name the map.
- **Catalog of the GUI** *(upstream)*. `registered_maps_grouped()` returns
    the registered maps by type and dataset, ordered by start time, and is
    exported by `grass.temporal`; `tlist()` takes the mapsets of the
    connection; the data catalog of the GUI shows the space time datasets.
- **Python 3.14** *(upstream)*. From Python 3.14 on, the servers of the
    library started without a GRASS session. Now they start with the method
    `fork`, also in *t.rast.extract* and *t.rast.mapcalc*, and stopping
    them no longer releases a lock twice.
- **unit_tests** *(upstream)*. The module `grass.temporal.unit_tests` was
    removed; its tests are pytest tests. Remove imports of it.
- **pygrass modules.** `MultiModule` could hang on a failing module, the
    child process printed tracebacks, `ParallelModuleQueue.wait()` did not
    wait for all processes, and `Messenger` warned about a restart after
    `fatal()`. Now the parent process checks the child, `wait()` waits for
    all processes and reports the first error with a note, and the warning
    is gone.
- **grass.script under LC_ALL=C.** Every Python tool failed for an argument
    with a non-ASCII character under `LC_ALL=C`. Now UTF-8 holds in the
    UTF-8 mode of Python.
- **Pack archives in grass.tools.** `tools.v_unpack(input="a.pack")` called
    *r.unpack*, and *v.pack* got the name of the map instead of the path of
    the archive. Now *r.pack*, *r.unpack*, *v.pack* and *v.unpack* get their
    archive argument as it is.

### Names that grass.temporal no longer exports

Each name below was exported by `grass.temporal` in GRASS 8.5 and is not
exported by it in GRASS 8.6. The second column names where it is now; a
module name without package means a module of `grass.temporal`. `kind` is a
value of `grass.temporal.kinds.KINDS`, such as `KINDS["raster"]`.

| Name | In GRASS 8.6 |
| --- | --- |
| `AbstractDataset` | `abstract_dataset.AbstractDataset` |
| `AbstractDatasetComparisonKeyEndTime` | `abstract_dataset.AbstractDatasetComparisonKeyEndTime` |
| `AbstractDatasetComparisonKeyStartTime` | `abstract_dataset.AbstractDatasetComparisonKeyStartTime` |
| `AbstractMapDataset` | `abstract_map_dataset.AbstractMapDataset` |
| `AbstractSTDSRegister` | `base.RegisterRow(kind)` |
| `CLibrariesInterface` | `c_libraries_interface.CLibrariesInterface` |
| `DBConnection` | `db.DBConnection` |
| `DatasetBase` | `base.BaseRow(kind)` |
| `DictSQLSerializer` | `rows.DictSQLSerializer` |
| `GlobalTemporalVar` | `classic.temporal_algebra.GlobalTemporalVar` |
| `RPCDefs` | removed; the functions of the server of the C libraries are called with `c_libraries_interface.CLibrariesInterface.call()` |
| `Raster3DAbsoluteTime` | `temporal_extent.AbsoluteTimeRow(kind)` |
| `Raster3DBase` | `base.BaseRow(kind)` |
| `Raster3DMetadata` | `metadata.MetadataRow(kind)` |
| `Raster3DRelativeTime` | `temporal_extent.RelativeTimeRow(kind)` |
| `Raster3DSTDSRegister` | `base.RegisterRow(kind)` |
| `Raster3DSpatialExtent` | `spatial_extent.SpatialExtentRow(kind)` |
| `RasterAbsoluteTime` | `temporal_extent.AbsoluteTimeRow(kind)` |
| `RasterBase` | `base.BaseRow(kind)` |
| `RasterMetadata` | `metadata.MetadataRow(kind)` |
| `RasterMetadataBase` | `metadata.MetadataRow(kind)` |
| `RasterRelativeTime` | `temporal_extent.RelativeTimeRow(kind)` |
| `RasterSTDSRegister` | `base.RegisterRow(kind)` |
| `RasterSpatialExtent` | `spatial_extent.SpatialExtentRow(kind)` |
| `SQLDatabaseInterface` | `rows.SQLDatabaseInterface` |
| `STDSAbsoluteTime` | `temporal_extent.AbsoluteTimeRow(kind)` |
| `STDSBase` | `base.BaseRow(kind)` |
| `STDSMetadataBase` | `metadata.MetadataRow(kind)` |
| `STDSRasterMetadataBase` | `metadata.MetadataRow(kind)` |
| `STDSRelativeTime` | `temporal_extent.RelativeTimeRow(kind)` |
| `STR3DSAbsoluteTime` | `temporal_extent.AbsoluteTimeRow(kind)` |
| `STR3DSBase` | `base.BaseRow(kind)` |
| `STR3DSMetadata` | `metadata.MetadataRow(kind)` |
| `STR3DSRelativeTime` | `temporal_extent.RelativeTimeRow(kind)` |
| `STR3DSSpatialExtent` | `spatial_extent.SpatialExtentRow(kind)` |
| `STRDSAbsoluteTime` | `temporal_extent.AbsoluteTimeRow(kind)` |
| `STRDSBase` | `base.BaseRow(kind)` |
| `STRDSMetadata` | `metadata.MetadataRow(kind)` |
| `STRDSRelativeTime` | `temporal_extent.RelativeTimeRow(kind)` |
| `STRDSSpatialExtent` | `spatial_extent.SpatialExtentRow(kind)` |
| `STVDSAbsoluteTime` | `temporal_extent.AbsoluteTimeRow(kind)` |
| `STVDSBase` | `base.BaseRow(kind)` |
| `STVDSMetadata` | `metadata.MetadataRow(kind)` |
| `STVDSRelativeTime` | `temporal_extent.RelativeTimeRow(kind)` |
| `STVDSSpatialExtent` | `spatial_extent.SpatialExtentRow(kind)` |
| `SpatialExtent` | `spatial_extent.SpatialExtent` |
| `SpatialTopologyDatasetConnector` | removed; `topology.TopologyLinks` holds the relations, which `get_temporal_relations()` and the like read |
| `TemporalAlgebraLexer` | `classic.temporal_algebra.TemporalAlgebraLexer` |
| `TemporalAlgebraParser` | `classic.temporal_algebra.TemporalAlgebraParser` |
| `TemporalExtent` | `temporal_extent.TemporalExtent` |
| `TemporalOperatorLexer` | `classic.temporal_operator.TemporalOperatorLexer` |
| `TemporalOperatorParser` | `classic.temporal_operator.TemporalOperatorParser` |
| `TemporalRasterBaseAlgebraParser` | `classic.temporal_raster_base_algebra.TemporalRasterBaseAlgebraParser` |
| `TemporalTopologyDatasetConnector` | removed; `topology.TopologyLinks` |
| `TemporalVectorAlgebraLexer` | `classic.temporal_vector_algebra.TemporalVectorAlgebraLexer` |
| `VectorAbsoluteTime` | `temporal_extent.AbsoluteTimeRow(kind)` |
| `VectorBase` | `base.BaseRow(kind)` |
| `VectorMetadata` | `metadata.MetadataRow(kind)` |
| `VectorRelativeTime` | `temporal_extent.RelativeTimeRow(kind)` |
| `VectorSTDSRegister` | `base.RegisterRow(kind)` |
| `VectorSpatialExtent` | `spatial_extent.SpatialExtentRow(kind)` |
| `aggregate_by_topology` | removed; `aggregation_core.aggregate_series` and the temporal algebra aggregate |
| `assign_valid_time_to_map` | `register.assign_valid_time_to_map` |
| `c_library_server` | `c_libraries_interface.c_library_server` |
| `check_datetime_string` | `datetime_math.check_datetime_string` |
| `compute_common_absolute_time_granularity` | `temporal_granularity.compute_common_absolute_time_granularity`; the classic algebra keeps a copy in `classic.granularity` |
| `compute_common_absolute_time_granularity_simple` | `temporal_granularity.compute_common_absolute_time_granularity_simple`; the classic algebra keeps a copy in `classic.granularity` |
| `compute_common_relative_time_granularity` | `temporal_granularity.compute_common_relative_time_granularity` |
| `compute_datetime_delta` | `datetime_math.compute_datetime_delta`; the classic algebra keeps a copy in `classic.granularity` |
| `compute_univar_stats` | `univar_statistics.compute_univar_stats` |
| `count_temporal_topology_relationships` | `topology.count_temporal_topology_relationships` |
| `create_suffix_from_datetime` | `datetime_math.create_suffix_from_datetime` |
| `create_temporal_database` | `schema.create_temporal_database` |
| `create_temporal_relation_sql_where_statement` | `topology.create_temporal_relation_sql_where_statement` |
| `create_time_suffix` | `datetime_math.create_time_suffix` |
| `decrement_datetime_by_string` | `datetime_math.decrement_datetime_by_string` |
| `gcd` | `temporal_granularity.gcd` |
| `gcd_list` | `temporal_granularity.gcd_list` |
| `get_available_temporal_mapsets` | `db.get_available_temporal_mapsets` |
| `get_current_gisdbase` | removed; `gs.gisenv()["GISDBASE"]` |
| `get_current_location` | removed; `gs.gisenv()["LOCATION_NAME"]` |
| `get_database_info_string` | `schema.get_database_info_string` |
| `get_enable_mapset_check` | `state.get_enable_mapset_check` |
| `get_enable_timestamp_write` | `state.get_enable_timestamp_write` |
| `get_raise_on_error` | `state.get_raise_on_error` |
| `get_tgis_backend` | removed; `state.get_tgis_dbmi_paramstyle()` and `get_tgis_database_string()` tell the back end |
| `get_tgis_database` | removed; `get_tgis_database_string()` |
| `get_tgis_db_version` | `state.get_tgis_db_version` |
| `get_tgis_dbmi_paramstyle` | `state.get_tgis_dbmi_paramstyle` |
| `get_tgis_version` | `state.get_tgis_version` |
| `get_time_tuple_function` | `temporal_granularity.get_time_tuple_function` |
| `gran_plural_unit` | removed; `gran_singular_unit` stays |
| `modify_datetime` | `datetime_math.modify_datetime` |
| `modify_datetime_by_string` | `datetime_math.modify_datetime_by_string` |
| `print_spatio_temporal_topology_relationships` | `topology.print_spatio_temporal_topology_relationships` |
| `print_temporal_topology_relationships` | removed; `topology.print_spatio_temporal_topology_relationships` |
| `relative_time_to_time_delta` | removed; the inverse `time_delta_to_relative_time` stays |
| `relative_time_to_time_delta_seconds` | removed; the inverse `datetime_math.time_delta_to_relative_time_seconds` stays |
| `run_mapcalc2d` | `batches.run_mapcalc("r.mapcalc", expression, nprocs=...)` |
| `run_mapcalc3d` | `batches.run_mapcalc("r3.mapcalc", expression, nprocs=...)` |
| `run_vector_extraction` | `extract.run_vector_extraction` |
| `set_raise_on_error` | `state.set_raise_on_error` |
| `set_spatial_relationship` | `topology.set_spatial_relationship` |
| `set_temporal_relationship` | `topology.set_temporal_relationship` |
| `time_delta_to_relative_time_seconds` | `datetime_math.time_delta_to_relative_time_seconds` |

### Names of the modules

Besides the names of the package, the modules of `grass.temporal` lost
names that the package did not export and the contract does not hold. The
table counts them for each module of GRASS 8.5 that lost names; the other
modules keep all their names. Methods that GRASS 8.6 makes from the column
tables when a module is imported count as kept.

| Module of GRASS 8.5 | Names lost | In GRASS 8.6 |
| --- | --- | --- |
| `metadata` | 72 | the classes of the metadata rows are one class `MetadataRow(kind)`; the methods of each column are made from the column tables when the module is imported |
| `temporal_algebra` | 98 | moved to `classic.temporal_algebra` |
| `temporal_raster_base_algebra` | 55 | moved to `classic.temporal_raster_base_algebra` |
| `temporal_operator` | 51 | moved to `classic.temporal_operator` |
| `base` | 49 | the classes of the base rows and registers are `BaseRow(kind)` and `RegisterRow(kind)` |
| `c_libraries_interface` | 47 | the typed methods of the client, such as `read_raster_info()` and `write_raster_timestamp()`, are `CLibrariesInterface.call()` with the name of the function; `RPCDefs`, `get_location()`, `get_gisdbase()`, `fatal_error()`, the `read_*_full_info()` methods and `remove_raster_semantic_label()` are removed |
| `temporal_topology_dataset_connector` | 46 | module removed; `topology.TopologyLinks` and `topology.SpatioTemporalTopologyBuilder` |
| `temporal_extent` | 31 | the classes of the time rows are `AbsoluteTimeRow(kind)` and `RelativeTimeRow(kind)`; `TemporalExtent.adjacent()` is removed |
| `spatial_topology_dataset_connector` | 30 | module removed; `topology.TopologyLinks` |
| `spatial_extent` | 10 | the classes of the extent rows are `SpatialExtentRow(kind)`; `set_spatial_extent_2d()`, `get_spatial_extent_as_tuple_2d()`, `get_volume()` and `set_spatial_extent_from_values_2d()` are removed |
| `temporal_vector_algebra` | 22 | moved to `classic.temporal_vector_algebra`; `TemporalVectorAlgebraParser` stays in `grass.temporal` |
| `core` | 18 | split into `db` (connections), `schema` (creation, checks and upgrade of the database) and `state` (the state of the session and `init()`); `core` forwards to them; the module variables such as `tgis_backend` and `current_mapset` are removed and read with the `get_*()` functions |
| `spatio_temporal_relationships` | 9 | module removed; `topology.SpatioTemporalTopologyBuilder` |
| `abstract_space_time_dataset` | 5 | `create_map_register_name()`, `is_map_registered()`, `sample_by_dataset()`, `sample_by_dataset_sql()` and `get_registered_maps_as_objects_with_temporal_topology()` are removed |
| `temporal_raster3d_algebra` | 4 | moved to `classic.temporal_raster3d_algebra`; `TemporalRaster3DAlgebraParser` stays in `grass.temporal` |
| `temporal_raster_algebra` | 4 | moved to `classic.temporal_raster_algebra`; `TemporalRasterAlgebraParser` stays in `grass.temporal` |
| `space_time_datasets` | 3 | `GRASS_TIMESTAMP_FMT` and `get_np_array()` of raster and 3D raster maps are removed |
| `datetime_math` | 2 | `relative_time_to_time_delta()` and `relative_time_to_time_delta_seconds()` are removed |
| `extract` | 2 | `run_mapcalc2d()` and `run_mapcalc3d()` are `batches.run_mapcalc()` |
| `abstract_map_dataset` | 1 | `check_resolution_with_current_region()`, which always raised an error, is removed |
| `aggregation` | 1 | `aggregate_by_topology()` is removed |
| `stds_export` | 1 | the module variable `exported_maps` is removed |
| `stds_import` | 1 | the module variable `imported_maps` is removed |
| `temporal_granularity` | 1 | `gran_plural_unit()` is removed |

## Fixed errors

Besides the changes above, the rework fixed errors that ended a valid call
with a traceback, left files or maps behind, or reported the wrong thing,
without a change of the result of a valid call. They are grouped here. The
37 errors in the tools below were found when the tests of the tools were
rewritten and when their code was reviewed; errors that the later rewrite
of the manuals found are fixed as well, but they are not counted.

- **A where condition with a syntax error** ended with a traceback in
    *t.list*, *t.topology*, *t.rast.out.vtk*, *t.rast.neighbors*,
    *t.rast.aggregate*, *t.rast.aggregate.ds*, *t.rast.contour*,
    *t.rast.to.vect*, *t.rast.gapfill*, *t.rast.what* and, for **t_where**,
    *t.vect.what.strds*. Now it is reported with a message.
- ***t.create*:** an apostrophe or a question mark in **title** or
    **description** ended with a traceback.
- ***t.rast.accumulate*:** a threshold dataset of the other temporal type was
    not refused, errors ended with a traceback, and with **--overwrite** the
    count of maps of the other dataset was not updated.
- ***t.rast.accumulate*** and ***t.rast.accdetect*:** an empty input dataset
    crashed the tool; now it warns and ends with exit code 0.
- ***t.rast.contour*:** the refusal without **levels** and **step** ended
    with a traceback.
- ***t.rast.export*:** a failed export left its working directory behind.
- ***t.rast.gapfill*:** the message for an existing map named the basename,
    and after **--overwrite** the first dataset kept its count of maps.
- ***t.rast.import*:** every refusal ended with a traceback.
- ***t.rast.mapcalc*:** a decimal number in **nprocs** ended with a traceback.
- ***t.rast.neighbors*:** with **--overwrite** or **-e**, the command was
    written into the history of the output dataset twice in one run. Now it
    is written once: the history of an overwritten dataset holds the
    command of the last run, and with **-e** each run adds its command.
- ***t.rast.neighbors*:** a failing *r.neighbors* ended with a traceback, and
    the parser did not check **region_relation**.
- ***t.rast.out.vtk*:** a refused export left the copy of the map behind.
- ***t.rast.to.rast3*:** a null map was left behind.
- ***t.shift*:** the message of a refused shift named
    `<built-in function id>` instead of the map.
- ***t.vect.db.select*:** an error of *v.db.select* ended with a traceback.
- ***t.vect.export*:** a missing or not writable **directory** ended with a
    traceback, and `readme.txt` described a GPKG archive as packed files.
- ***t.vect.observe.strds*:** a message named the wrong identifier, time
    instances ended with a traceback, and errors of the tools it runs ended
    with a traceback.
- ***t.vect.what.strds*:** an invalid **where** gave no error, and an empty
    vector dataset reported that the maps must be intervals.
- **The Python library:** 18 further errors that only Python code meets,
    among them a rollback and a close of connections on the paths of
    errors, a closed connection of the caller, labels and relative time
    stamps in SQL, and the locale in the format of time stamps.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7`
from the [GRASS sample data](https://grass.osgeo.org/download/data/). The
first example creates the mapset `temporalchanges` and sets the
computational region to North Carolina with cells of 1 km; the second
example works in this mapset and region and uses the dataset of the first.
The maps hold constant values, which make the times easy to follow.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=temporalchanges -->

<!-- markdownlint-disable MD046 -->

### Register a series of month ends

The dataset `inflow` holds four maps of the inflow into a reservoir, one for
each period from the end of a month to the end of the next month; the
values 1 to 4 number the periods. *[t.register](t.register.md)* with the
flag **-i**, `start=2020-01-31` and `increment="1 month"` registers them as
consecutive intervals. Each step of a month ends on the last day of the
month: 29 February, 31 March, 30 April and 31 May. The releases before
GRASS 8.6 could not add one month to 31 January and ended with the error
"day is out of range for month". *[t.info](t.info.md)* with **-g** shows the
granularity of the dataset, 1 month, where the releases before GRASS 8.6
gave a series of month ends the granularity 1 day.

=== "Command line"

    ```sh
    g.mapset -c mapset=temporalchanges
    g.region raster=elev_state_500m res=1000 -a
    for period in 1 2 3 4; do
        r.mapcalc expression="inflow_2020_0$period = $period"
    done
    t.create output=inflow title="Inflow" \
        description="Inflow of periods that start at the end of a month"
    t.register -i input=inflow \
        maps=inflow_2020_01,inflow_2020_02,inflow_2020_03,inflow_2020_04 \
        start=2020-01-31 increment="1 month"
    t.rast.list input=inflow columns=name,start_time,end_time
    t.info -g input=inflow | grep "^granularity="
    ```

    ```text
    name|start_time|end_time
    inflow_2020_01|2020-01-31 00:00:00|2020-02-29 00:00:00
    inflow_2020_02|2020-02-29 00:00:00|2020-03-31 00:00:00
    inflow_2020_03|2020-03-31 00:00:00|2020-04-30 00:00:00
    inflow_2020_04|2020-04-30 00:00:00|2020-05-31 00:00:00
    granularity='1 month'
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="temporalchanges")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    periods = range(1, 5)
    tools.r_mapcalc(
        expression="\n".join(f"inflow_2020_{period:02d} = {period}" for period in periods)
    )
    tools.t_create(
        output="inflow",
        title="Inflow",
        description="Inflow of periods that start at the end of a month",
    )
    tools.t_register(
        input="inflow",
        maps=",".join(f"inflow_2020_{period:02d}" for period in periods),
        start="2020-01-31",
        increment="1 month",
        flags="i",
    )
    print(tools.t_rast_list(input="inflow", columns="name,start_time,end_time").text)
    info = tools.t_info(input="inflow", flags="g").keyval
    print(f"granularity={info['granularity']}")
    ```

    ```text
    name|start_time|end_time
    inflow_2020_01|2020-01-31 00:00:00|2020-02-29 00:00:00
    inflow_2020_02|2020-02-29 00:00:00|2020-03-31 00:00:00
    inflow_2020_03|2020-03-31 00:00:00|2020-04-30 00:00:00
    inflow_2020_04|2020-04-30 00:00:00|2020-05-31 00:00:00
    granularity='1 month'
    ```

### Compare the new and the classic algebra

*[t.rast.algebra](t.rast.algebra.md)* selects maps of `inflow` by a
condition on the month and the day of their start. The new algebra reads
`&&` before `||`: it selects the period that starts in April and, of the
periods that start in January or February, the one that starts on day 31,
which is the period of January. The flag **-c** selects the classic
algebra, which reads conditions on temporal variables from left to right,
as the releases before GRASS 8.6 did:
`(start_month(inflow) == 4 || start_month(inflow) <= 2) &&
start_day(inflow) == 31`. It selects the period of January only.

=== "Command line"

    ```sh
    t.rast.algebra basename=selected expression="selected = if(start_month(inflow) == 4 || start_month(inflow) <= 2 && start_day(inflow) == 31, inflow)"
    t.rast.list input=selected columns=name,start_time,min
    t.rast.algebra -c basename=classic expression="selected_classic = if(start_month(inflow) == 4 || start_month(inflow) <= 2 && start_day(inflow) == 31, inflow)"
    t.rast.list input=selected_classic columns=name,start_time,min
    ```

    ```text
    name|start_time|min
    selected_0|2020-01-31 00:00:00|1.0
    selected_1|2020-04-30 00:00:00|4.0
    name|start_time|min
    classic_0|2020-01-31 00:00:00|1.0
    ```

=== "Python (grass.tools)"

    ```python
    condition = (
        "start_month(inflow) == 4 || start_month(inflow) <= 2 && start_day(inflow) == 31"
    )
    tools.t_rast_algebra(
        expression=f"selected = if({condition}, inflow)", basename="selected"
    )
    print(tools.t_rast_list(input="selected", columns="name,start_time,min").text)
    tools.t_rast_algebra(
        expression=f"selected_classic = if({condition}, inflow)",
        basename="classic",
        flags="c",
    )
    print(tools.t_rast_list(input="selected_classic", columns="name,start_time,min").text)
    ```

    ```text
    name|start_time|min
    selected_0|2020-01-31 00:00:00|1.0
    selected_1|2020-04-30 00:00:00|4.0
    name|start_time|min
    classic_0|2020-01-31 00:00:00|1.0
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[t.rast.algebra](t.rast.algebra.md), [t.rast3d.algebra](t.rast3d.algebra.md),
[t.select](t.select.md), [t.vect.algebra](t.vect.algebra.md),
[temporal data processing](temporalintro.md)*

- Gebbert, S., Leppelt, T., Pebesma, E., 2019. *A topology based
  spatio-temporal map algebra for big data analysis*. Data 4, 86.
  ([DOI](https://doi.org/10.3390/data4020086))

## AUTHORS

Soeren Gebbert
