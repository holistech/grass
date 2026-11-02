## DESCRIPTION

*t.select* selects maps from space time datasets with the temporal algebra
and registers them in a new space time dataset. It only selects and retimes
maps, it computes none: use *[t.rast.algebra](t.rast.algebra.md)*,
*[t.rast3d.algebra](t.rast3d.algebra.md)* or
*[t.vect.algebra](t.vect.algebra.md)* to compute with them. A selection
answers questions such as "which maps of A lie in the time of a map of B?",
"which maps of A have no map of B at the same time?" or "which maps of A
start before a date?". See the [introduction to temporal data processing](temporalintro.md)
for space time datasets and their temporal relations.

### PROGRAM USE

The module expects an **expression** as input parameter in the following
form:

`"result = expression"`

The statement structure is similar to *[r.mapcalc](r.mapcalc.md)*. **result**
is the name of the space time dataset (STDS) that will contain the maps
selected by the **expression** on the right side of the equality sign. The
expression can be any valid or nested combination of the temporal operations
and functions that the temporal algebra provides. The temporal algebra works
with space time datasets of any type (STRDS, STR3DS and STVDS). The algebra
provides methods for map selection from STDS based on their temporal
relations. It is also possible to temporally shift maps, to create temporal
buffers and to snap time instances to create a valid temporal topology.
Furthermore expressions can be nested and evaluated in conditional statements
(if, else statements). Within if-statements the algebra provides temporal
variables like start time, end time, day of year, time differences or number
of maps per time interval to build up conditions. These operations can be
assigned to space time datasets or to the results of operations between
space time datasets.

The result dataset is created in the current mapset, with the temporal type
(absolute or relative) of the datasets in the expression. Maps whose temporal
extent is changed by a temporal operator (for example `{:,during,r}`) cannot
stay the maps of the input dataset. They are copied to new maps that are
named after the result dataset: the dataset `C` in `C = A {:,during,r} B`
contains the maps `C_1`, `C_2` and so on. Existing maps with these names are
only overwritten with the **--overwrite** flag. Maps whose extent is not
changed are registered in the result dataset without being copied; a map of
another mapset keeps its mapset in the result (`a2@PERMANENT`). An expression
that selects no map creates an empty space time dataset.

### Options

The option **expression** takes the statement `result = expression`. It must
be passed as **quoted** expression, for example:

```sh
t.select expression="C = A : B"
```

Here **C** is the new space time raster dataset that will contain the maps
from **A** that are selected by equal temporal relationships to the existing
dataset **B**. An existing dataset **C** is only replaced with the
**--overwrite** flag. Datasets of other mapsets are written as `name@mapset`;
a name without mapset means the current mapset only.

The option **type** gives the type of the datasets named in the expression:
`strds` (default), `stvds` or `str3ds`. The result has this type as a rule.
Maps of a dataset of another type are pulled into a selection with the
functions `strds()`, `str3ds()` and `stvds()`; a result whose maps come from
such a function can have the type of that function, see the NOTES.

As default, topological relationships between space time datasets will be
evaluated only temporal. The **-s** flag additionally activates the
evaluation of the spatial topology of the maps. It applies wherever the
algebra evaluates the topology of maps: in selections, in the hash operator,
in the conditions of if statements and in comparison operators. Two
temporally related maps are then only used together if they are also
spatially related, that is the spatial extents of the maps are equivalent,
one covers or is covered by the other, they overlap, one lies in the other,
one contains the other, or they meet (the spatial relations *equivalent*,
*cover*, *covered*, *overlap*, *in*, *contain* and *meet*).

The **-d** flag performs a dry run. The tool computes the plan and prints it
as a Python dictionary to standard output, and creates no dataset and no map.
The entry `STDS` holds the name, the type and the temporal type of the
result, `processes` the modules that would copy maps, `register` the maps that
would be registered in the result with their start and end time, and `remove`
the removals, which are empty in the plans shown here.

The **-c** flag uses the classic algebra instead of the algebra core, see the
NOTES. The environment variable `GRASS_TEMPORAL_ALGEBRA=classic` selects it
for a whole session; the flag takes precedence over the variable.

## TEMPORAL ALGEBRA

The temporal algebra provides a wide range of temporal operators and
functions that will be presented in the following section. The catalog
under EXAMPLES runs the expressions of this section on small datasets and
shows the maps they select.

### TEMPORAL RELATIONS

Several temporal topology relations between registered maps of space
time datasets are supported:  

```sh
equal             A ------
                  B ------

during            A  ----
                  B ------

contains          A ------
                  B  ----

starts            A ----
                  B ------

started           A ------
                  B ----

finishes          A   ----
                  B ------

finished          A ------
                  B   ----

precedes          A ----
                  B     ----

follows           A     ----
                  B ----

overlapped        A   ------
                  B ------

overlaps          A ------
                  B   ------

over              both overlaps and overlapped
```

The relations must be read as: A is related to B, like - A is equal to B - A
is during B - A contains B

Gebbert, Leppelt and Pebesma (2019) write the relation `equal` as `equals`;
the new algebra and **-c** read both names. The releases before GRASS 8.6
refused `equals` with a syntax error.

Topological relations must be specified in {} parentheses.  

The relations **during** and **contains** are inclusive: **during** also
selects maps that start or finish together with the related map (the
relations **starts** and **finishes**), and **contains** also selects maps
with the relations **started** and **finished**. The relations **precedes**
and **follows** only apply to maps that touch each other, that is the end of
one map is the start of the other. Maps that are separated by a gap have no
relation.

### TEMPORAL OPERATORS

The temporal algebra defines temporal operators that can be combined
with other operators to perform spatio-temporal operations. The temporal
operators process the time instances and intervals of two temporal
related maps and calculate the result temporal extent by five different
possibilities.

```sh
LEFT REFERENCE     l       Use the time stamp of the left space time dataset
INTERSECTION       i       Intersection
DISJOINT UNION     d       Disjoint union
UNION              u       Union
RIGHT REFERENCE    r       Use the time stamp of the right space time dataset
```

Each operator can also be written as a word: `left`, `intersect`, `disjoint`,
`union` and `right`.

### TEMPORAL SELECTION

The temporal selection simply selects parts of a space time dataset
without processing raster or vector data. The algebra provides a
selection operator **:** that selects parts of a space time dataset that
are temporally equal to parts of a second one by default. The following
expression

```sh
C = A : B
```

means: Select all parts of space time dataset A that are equal to B and
store it in space time dataset C. The parts are time stamped maps.

In addition the inverse selection operator **!:** is defined as the
complement of the selection operator, hence the following expression

```sh
C = A !: B
```

means: select all parts of space time time dataset A that are not equal
to B and store it in space time dataset (STDS) C.

To select parts of a STDS by different topological relations to other
STDS, the temporal topology selection operator can be used. The operator
consists of the temporal selection operator, the topological relations,
that must be separated by the logical OR operator **\|** and the
temporal extent operator. All three parts are separated by comma and
surrounded by curly braces:

```sh
{"temporal selection operator", "topological relations", "temporal operator"}
```

Examples:

```sh
C = A {:, equal} B
C = A {!:, equal} B
```

We can now define arbitrary topological relations using the OR operator
"\|" to connect them:

```sh
C = A {:,equal|during|overlaps} B
```

Select all parts of A that are equal to B, during B or overlaps B.  
In addition we can define the temporal extent of the result STDS by
adding the temporal operator.

```sh
C = A {:, during,r} B
```

Select all parts of A that are during B and use the temporal extents
from B for C.  
  
The selection operator is implicitly contained in the temporal topology
selection operator, so that the following statements are exactly the
same:

```sh
C = A : B
C = A {:} B
C = A {:,equal} B
C = A {:,equal,l} B
```

Same for the complementary selection:

```sh
C = A !: B
C = A {!:} B
C = A {!:,equal} B
C = A {!:,equal,l} B
```

### CONDITIONAL STATEMENTS

Selection operations can be evaluated within conditional statements.  

```sh
Note A and B can either be space time datasets or expressions. The temporal
relationship between the conditions and the conclusions can be defined at the
beginning of the if statement. The relationship between then and else conclusion
must be always equal.

if statement                           decision option                        temporal relations
  if(if, then, else)
  if(conditions, A)                    A if conditions are True;              temporal topological relation between if and then is equal.
  if(conditions, A, B)                 A if conditions are True, B otherwise; temporal topological relation between if, then and else is equal.
  if(topologies, conditions, A)        A if conditions are True;              temporal topological relation between if and then is explicit specified by topologies.
  if(topologies, conditions, A, B)     A if conditions are True, B otherwise; temporal topological relation between if, then and else is explicit specified by topologies.
```

The conditions are comparison expressions that are used to evaluate
space time datasets. Specific values of temporal variables are compared
by logical operators and evaluated for each map of the STDS.  
**Important:** The conditions are evaluated from left to right.

#### Logical operators

```sh
Symbol  description

  ==    equal
  !=    not equal
  >     greater than
  >=    greater than or equal
  <     less than
  <=    less than or equal
  &&    and
  ||    or
```

#### Temporal functions

The following temporal function are evaluated only for the STDS that
must be given in parenthesis.

```sh
td(A)                    Returns a list of time intervals of STDS A

start_time(A)            Start time as HH:MM:SS
start_date(A)            Start date as yyyy-mm-DD
start_datetime(A)        Start datetime as yyyy-mm-DD HH:MM:SS
end_time(A)              End time as HH:MM:SS
end_date(A)              End date as yyyy-mm-DD
end_datetime(A)          End datetime as yyyy-mm-DD HH:MM:SS

start_doy(A)             Day of year (doy) from the start time [1 - 366]
start_dow(A)             Day of week (dow) from the start time [1 - 7], the start of the week is Monday == 1
start_year(A)            The year of the start time [0 - 9999]
start_month(A)           The month of the start time [1 - 12]
start_week(A)            Week of year of the start time [1 - 54]
start_day(A)             Day of month from the start time [1 - 31]
start_hour(A)            The hour of the start time [0 - 23]
start_minute(A)          The minute of the start time [0 - 59]
start_second(A)          The second of the start time [0 - 59]
end_doy(A)               Day of year (doy) from the end time [1 - 366]
end_dow(A)               Day of week (dow) from the end time [1 - 7], the start of the week is Monday == 1
end_year(A)              The year of the end time [0 - 9999]
end_month(A)             The month of the end time [1 - 12]
end_week(A)              Week of year of the end time [1 - 54]
end_day(A)               Day of month from the end time [1 - 31]
end_hour(A)              The hour of the end time [0 - 23]
end_minute(A)            The minute of the end time [0 - 59]
end_second(A)            The second of the end time [0 - 59]
```

#### Comparison operator

The conditions are comparison expressions that are used to evaluate
space time datasets. Specific values of temporal variables are compared
by logical operators and evaluated for each map of the STDS and the
related maps. For complex relations the comparison operator can be used
to combine conditions:  
The structure is similar to the select operator with the extension of an
aggregation operator: {"comparison operator", "topological relations",
aggregation operator, "temporal operator"}  
This aggregation operator (\| or &) define the behaviour if a map is
related the more than one map, e.g for the topological relations
'contains'. Should all (&) conditions for the related maps be true or is
it sufficient to have any (\|) condition that is true. The resulting
boolean value is then compared to the first condition by the comparison
operator (\|\| or &&). As default the aggregation operator is related to
the comparison operator:  
Comparison operator -\> aggregation operator:

```sh
|| -> | and && -> &
```

Examples:

```sh
Condition 1 {||, equal, r} Condition 2
Condition 1 {&&, equal|during, l} Condition 2
Condition 1 {&&, equal|contains, |, l} Condition 2
Condition 1 {&&, equal|during, l} Condition 2 && Condition 3
Condition 1 {&&, equal|during, l} Condition 2 {&&,contains, |, r} Condition 3
```

#### Hash operator

Additionally the number of maps in intervals can be computed and used in
conditional statements with the hash (#) operator.  

```sh
A{#, contains}B
```

The hash operator can only be used in the condition of an if statement.

This expression computes the number of maps from space time dataset B
which are during the time intervals of maps from space time dataset A.  
A list of integers (scalars) corresponding to the maps of A that contain
maps from B will be returned.

The result keeps the time stamps of the maps of A. The temporal operators
`r`, `u`, `i` and `d` have no meaning for the count and are rejected with
a syntax error; `l` is the default.

```sh
C = if({equal}, A {#, contains} B > 2, A {:, contains} B)
```

This expression selects all maps from A that temporally contains more than
2 maps from B and stores them in space time dataset C. The leading
equal statement in the if condition specifies the temporal relation
between the if and then part of the if expression. This is very
important, so we do not need to specify a global time reference (a space
time dataset) for temporal processing.

Furthermore the temporal algebra allows temporal buffering, shifting and
snapping with the functions buff_t(), tshift() and tsnap() respectively.

```sh
buff_t(A, size)         Buffer STDS A with granule ("1 month" or 5)
tshift(A, size)         Shift STDS A with granule ("1 month" or 5)
tsnap(A)                Snap time instances and intervals of STDS A
```

A negative size shrinks the maps; the new algebra stops with an error where
a map would keep no time, see "Core and classic algebra".

#### Single map with temporal extent

The temporal algebra can also handle single maps with time stamps in the
map function.

```sh
tmap()
```

For example:

```sh
 C = A {:,during} tmap(event)
```

This statement select all maps from space time data set A that are
during the temporal extent of single map 'event'  

## NOTES

### Results, empty selections and mapsets

The result dataset and the copies of retimed maps are always created in the
current mapset. A selected map that keeps its time is registered as it is,
also when it belongs to another mapset: the result of the example with the
mapset `paper` holds `a2@PERMANENT`, and no map of that name exists in
`paper`. A name without a mapset in the expression refers to the current
mapset only, so `X` does not find a dataset `X` of another mapset; write
`X@mapset`.

An expression that selects no map creates an empty space time dataset, for
vector maps also, with **-c** and without. The empty dataset has the map count
0 in *[t.info](t.info.md)*, as the example with the mapset `paper` shows.

Datasets of relative time are selected like those of absolute time, with the
same relations and operators. The result has the temporal type of the input
(see the example on relative time).

### Core and classic algebra

Since GRASS 8.6, *t.select* selects with the functions of the Python package
`grass.temporal.algebra`, as *t.rast.algebra* and *t.vect.algebra* do. The
implementation used before, the reference implementation in
`grass.temporal.classic`, stays in the source code, and its rules stay
available as the classic algebra, so that published results remain
reproducible. The classic algebra is a set of rules of the same functions: it
reads the syntax of the reference implementation and applies its rules for
relations and order. The flag **-c** selects it for one call, the environment
variable `GRASS_TEMPORAL_ALGEBRA=classic` for a whole session or script;
`GRASS_TEMPORAL_ALGEBRA=core` or an unset or empty variable selects the new
algebra, and the flag takes precedence over the variable.

Both algebras pull maps of another dataset type into a selection with the
functions `strds()`, `str3ds()` and `stvds()`; the type of the function need
not equal the parameter **type**, which gives the type of the result (since
17 October 2026 the new algebra reads them as well; before, only the classic
algebra did). Since 21 October 2026 the new algebra also relates a vector
dataset on the left to a raster or 3D raster dataset, as in
`if({contains}, stvds(B) {#,contains} A == 2, A)`; before, it stopped with an
error. Besides the lower case spelling, `str3ds(A)`, both read the
capitals of the paper, `STRDS(A)`, `STR3DS(A)` and `STVDS(A)`. A capital name
is a function only before an opening parenthesis, so that a dataset may be
named `STRDS`. Other spellings, such as `Str3ds(A)`, are a syntax error.

*t.select* only selects and retimes maps, it computes none, so most
differences between the two algebras do not reach it. An expression that
selects no map creates an empty space time dataset in both algebras. These
points differ:

1. **Spatial relations.** A spatial relation in an operator, such as
   `{:,equal|overlap}`, is read only by the new algebra, with and without
   the flag **-s**, and needs a temporal relation to go with it. The
   classic algebra reports a syntax error for the name of a spatial
   relation, with and without **-s**.

2. **Right reference.** `A {:,R,r} B` gives one map per related pair, with
   the time stamp of the right map: a map of A that contains two maps of B
   gives two maps. The classic algebra keeps only the last pair of each map
   of A. `A {!:,R,t} B` with a temporal reference other than `l` is a
   syntax error, because the inverse selection has no related map to
   combine with; the classic algebra accepts it.

3. **More syntax.** The neighbourhood modifier `A[1]` and `A[-1]`, and
   comparisons and temporal functions anywhere in a condition (also with
   the number on the left, as in `20 < start_doy(A)`, and in arithmetic, as
   in `start_doy(A) - 1 > 20`), and the hash operator in arithmetic within
   a condition are read by the new algebra. So is an expression that is only
   a dataset, `C = A`. The classic algebra reports a syntax error for each.

4. **Arithmetic on datasets.** An expression such as `A + B` is read by the
   new algebra, which stops with a message that names the tools that
   compute maps, because it is no selection. The classic algebra cannot
   read it and reports a syntax error.

5. **Copy names in a mixed result.** When a result mixes maps registered
   unchanged with retimed maps, the copied maps are named `<result>_1`,
   `<result>_2`, ... in the time order of the result. The classic algebra
   numbers them by their position among all result maps, so the suffixes can
   differ; the maps and their time stamps are the same. If three maps are
   registered unchanged before three copies, the copies are `C_1` to `C_3`
   in the new algebra and `C_4` to `C_6` in the classic one:

   ```sh
   C = merge(A {:,during,l} D, A {:,during,r} D)
   ```

6. **Negative buffer.** A negative size in `buff_t()` shrinks the maps
   by that size at both ends. The new algebra stops with an error if a map
   would keep no time, that is if its end would fall on or before its start,
   and for a time instance, which has no duration to shrink. The classic
   algebra goes on instead: for a map whose end would fall before its
   start it prints an error message and keeps the old time stamp, and it
   makes a time instance of a map whose end equals its start. For maps
   of two days, the first expression shrinks them to one day and the
   second is an error:

   ```sh
   C = buff_t(B, "-12 hours")
   C = buff_t(B, "-1 day")
   ```

7. **tsnap() of maps that start together.** Of maps with the same start,
   `tsnap()` snaps only one to the start of the next later map; the others
   keep their own ends. The new algebra takes the map that ends last, so its
   result does not depend on the order of the maps. The classic algebra
   takes the map listed last, so that the order of the arguments of
   `merge()` matters. If a map from day 2 to day 4 is in C and a map from
   day 2 to day 3 in A, the new algebra gives both expressions the same
   maps; the classic algebra lets the map of C keep its end in the second:

   ```sh
   D = tsnap(merge(A, C))
   D = tsnap(merge(C, A))
   ```

8. **Time functions as the conclusion of if().** A time function such as
   `start_doy()` gives numbers, not maps, so the new algebra stops with the
   error "A time function such as start_doy() cannot be the result of a
   selection" whenever it is the conclusion of `if()` beside maps. A time
   function belongs in the condition. The classic algebra stops with this
   error only where a value of the time function would be among the
   selected maps (see the corrections below). If the first map of A starts
   on 1 January, only that map meets the condition, and it has no
   predecessor: the classic algebra selects the other maps of A with the
   first expression and stops with the second:

   ```sh
   C = if(start_doy(A) < 3, start_doy(A, -1), A)
   C = if(start_doy(A) < 3, start_doy(A, 1), A)
   ```

In Python, both algebras raise `SyntaxError` for an expression they cannot
read, and `FatalError` for a missing dataset and, without overwrite, for an
existing result. The new algebra raises `ValueError` for an expression it
reads but cannot select, such as `A + B`, where the classic algebra raises
`SyntaxError`. The tool stops with the error message in both algebras.

Two corrections apply to both algebras, and to *t.rast.algebra*,
*t.rast3d.algebra* and *t.vect.algebra* as well, so **-c** gives the rules of
the classic algebra, not the results of a particular release. First,
`if({R}, condition, conclusion)` reads "condition R conclusion":
`if({contains}, start_doy(A) > 0, B)` gives the maps of B that lie within a
map of A. Second, with a temporal relation beyond `equal`, the else part of a
condition on temporal variables also takes the maps that no condition map is
related to. Figure A3 of Gebbert, Leppelt and Pebesma (2019) needs both: A
has maps from day 1 to 3, 3 to 5 and 5 to 7 of January 2001, B has daily maps
from day 1 to 10, and this expression gives the first two maps of A and the
maps of B from day 5 on, as the figure shows:

```sh
C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)
```

Results that rely on the previous reading direction or else rule need the
GRASS version they were computed with. The section "Core and classic
algebra" in the NOTES of [t.rast.algebra](t.rast.algebra.md) describes both
corrections.

#### Corrections to the classic algebra

The classic algebra gives the results of the releases before GRASS 8.6, with the
exceptions below. In these cases those releases ended in an error that had no
reason, reported the wrong error, or did not do what this manual describes.
**-c** now gives the result described here. The reference implementation was
corrected in the same way, except in items 5, 6, 9, 11 and 12: items 5, 6 and 9
say what it does, it still takes the time of a partner whose box only touches,
and it still raises the `CalledModuleError` of a failed module. The new algebra
never had these errors; only the items on month steps, on dates beyond the year
9999, on a map that starts with the next map in tsnap() and on a failed module
concerned the library and with it both algebras. Results of earlier GRASS
versions that used one of these forms need a new run.

1. **tsnap() and tshift() of no maps.** If the expression inside selects
   no map, the result is an empty dataset, like any other selection of no
   map, and an enclosing expression goes on with no maps. Earlier versions
   ended in an error. No map of A is equal to a map of D, so both
   expressions give an empty dataset:

   ```sh
   C = tsnap(A {:,equal} D)
   C = tshift(A {:,equal} D, "1 day")
   ```

2. **Increments that the library refuses.** An increment of `tshift()` or
   `buff_t()` that does not fit the temporal type, such as a text that is
   not a time step or a number without unit on absolute time, is a syntax
   error and leaves no result dataset. The new algebra refuses the same
   increments with a `ValueError`:

   ```sh
   C = tshift(A, "1 DAY")
   C = buff_t(A, 3)
   ```

3. **Selection with a time instance on relative time.** With the temporal
   operator `i`, the time stamp of the result is the time instance. Earlier
   versions failed with a `TypeError` for a selection on relative time. If A
   has maps of relative time that contain the time instances of I, this
   expression gives maps with the instances as time:

   ```sh
   C = A {:,contains,i} I
   ```

4. **Spatial relation names alone.** A selection in braces refuses spatial
   relation names with a syntax error. With spatial names only, such as
   `A {:,equivalent} B`, it stops now with the error "equivalent is a spatial
   relation and needs a temporal one, as in equal|overlap", as every operator
   of the algebras and the new algebra do (17 October 2026). Selections read
   temporal relations only:

   ```sh
   C = A {:,equal} B
   ```

5. **Empty selection of vector maps.** An expression that selects no map
   creates an empty space time vector dataset, as it does for raster maps
   and in the new algebra (19 October 2026). The reference implementation
   created no dataset for vector maps and gave no warning. With
   **type=stvds**, if no map of A is equal to a map of D, this expression
   gives an empty dataset:

   ```sh
   C = A {:,equal} D
   ```

6. **Planned type of a mixed selection.** The dry run (**-d**) plans the
   type of the dataset that the run creates (19 October 2026). If the maps
   of the result come from a function of another type, the run creates a
   dataset of that type: with **type=strds**, this expression creates a
   space time 3D raster dataset, and the dry run plans one. The reference
   implementation planned the type given by **type** and created the other:

   ```sh
   C = if({contains}, (stvds(B) {#,contains} str3ds(A)) == 2, str3ds(A))
   ```

7. **A map that starts with the next map in tsnap().** `tsnap()` sets the end
   of each map to the start of the next map. A map that starts at the same
   time as the next map keeps its own end instead (corrected 21 October 2026).
   Earlier versions gave it the end of the next map, so the two maps swapped
   their ends. If a map on days 2 to 3 and a map on days 2 to 4 start together,
   the one listed first keeps its end in the classic algebra (**-c**,
   `GRASS_TEMPORAL_ALGEBRA=classic` and the reference implementation). The new
   algebra orders such maps by their end instead, see item 7 of the
   differences above:

   ```sh
   D = tsnap(merge(A, C))
   ```

8. **Month and year steps from the end of a month.** `tshift()` and
   `buff_t()` by months or years ended in an error ("day is out of range for
   month") when a time stamp moved to a day that the target month lacks, in
   both algebras. Such a step now ends on the last day of that month
   (corrected 23 October 2026). With a dataset M whose map lasts from 31
   January to 31 March 2001, the first expression gives a map from 28
   February to 30 April 2001, the second one a map from 31 December 2000 to
   30 April 2001. A year step from 29 February 2004 ends on 28 February 2005:

   ```sh
   C = tshift(M, "1 months")
   C = buff_t(M, "1 months")
   ```

   A month step back that ends in December of the year before last or
   earlier, for example `buff_t(A, "24 months")` on a map that starts on 1
   December or `tshift(A, "-13 months")` on one that starts in January,
   ended in the error "bad month number 0" and now gives a result
   (corrected 23 October 2026). Years and months of one step count as one
   step of 12 * years + months months, so `"1 years, 11 months"` and
   `"23 months"` end on the same day.

9. **Time functions as the selected maps.** In a selection, a time function
   at an offset such as `start_doy(A, 1)` stands for the map it reads, whose
   value the reference implementation never computed. Where such a value was
   among the selected maps, a dry run listed it and the real run failed when
   it copied that map. The classic algebra now stops with the error "A time
   function such as start_doy() cannot be the result of a selection" before
   it creates a dataset or a map (corrected 23 October 2026); where no value
   of the time function is selected, the result is the same as before. A
   time function belongs in the condition:

   ```sh
   C = if(start_doy(A) < 3, start_doy(A, 1), A)
   C = tshift(start_doy(A, 1), "1 day")
   ```

10. **A date beyond the year 9999.** A step that ends behind the year 9999
    or before the year 1, for example `buff_t(A, "365 days")` on a map that ends
    on 1 December 9999, ended with a traceback ("date value out of range")
    in both algebras. It now ends with the error "... is beyond the year
    9999" or "... is before the year 1" (corrected 23 October 2026); no map
    and no dataset is created.

11. **A selection with r or u under -s and maps whose boxes only touch.**
    With **-s** two maps are related when they are related in time and in
    space; boxes that meet at an edge or a corner only are not related in
    space. A selection such as `A {:,precedes,r} B` took the time of every
    map that was related in time, also of one whose box only touches the box
    of the map of A, and the last such map won. An inverse selection such as
    `A {!:,precedes,r} B` kept a map without a related partner, as it
    should, but gave it the time of a partner that only touches it. The time
    is now taken only from maps that are related in time and in space, and
    `!:` keeps a map without such a partner with its own time (corrected 23
    October 2026). For example, a map of A from 1 to 2 January whose box
    meets at a corner the box of a map of B from 2 to 3 January keeps the
    time 1 to 2 January in the inverse selection above, where it took 2 to 3
    January. Without **-s** nothing changes.

12. **A failed module.** If a module fails while the maps are computed or
    copied, both algebras ended with a Python traceback. They now end with an
    error that names the module and its return code, such as
    `Module <g.copy> failed with return code 1, see the error output above`
    (corrected 24 October 2026); the cause is in the error output of the module
    above it. No dataset is created.

13. **The relation equals and capital function names.** The releases before
    GRASS 8.6 refused the relation name `equals` and the capital function
    names `STRDS(A)`, `STR3DS(A)` and `STVDS(A)` of the paper with a syntax
    error (corrected 17 October 2026). Both algebras read them as `equal` and
    as the functions in lower case.

#### Differences from the reference implementation

The differences in message texts, in the debug output of the Python
parser, in the order of errors and in the error for an existing result that
[t.rast.algebra](t.rast.algebra.md) lists apply here likewise. One point
changes the outcome of an expression: a relation over a list that mixes maps
of absolute and of relative time, which stopped the reference implementation
with a `TypeError`, selects maps here, as in *t.rast.algebra*: maps of the two
types relate to nothing.

## EXAMPLES

The examples run in the order of this section in one project, and each one
builds on the datasets of the first. The first five show the options of the
tool with both interfaces; the ones after them are a catalog of expressions,
which run on the command line only and show the maps each expression selects.

<!-- markdownlint-disable MD046 -->

### Select the maps of a dataset by their time

The first example creates four datasets of constant maps in a small region.
Every time below is a day of January 2001: a map from day 6 to 11 starts at
00:00 of 6 January and ends at 00:00 of 11 January, so `a1` from day 1 to 6
ends where `a2` starts. The value of each map is the number in its name.

| Dataset | Maps from day to day |
| --- | --- |
| `A` | `a1` 1 to 6, `a2` 6 to 11, `a3` 11 to 16, `a4` 16 to 21 |
| `B` | `b1` 1 to 11, `b2` 6 to 11, `b3` 11 to 13, `b4` 12 to 14, `b5` 14 to 18, `b6` 18 to 21, `b7` 21 to 24 |
| `C` | `c1` 6 to 11, `c2` 16 to 21 |
| `W` | `w1` 3 to 19 |

The operator `:` selects the maps of `A` that are equal in time to a map of
`B`; the operator `!:` selects the ones that are not. Only `a2` and `b2` have
the same time, so the first selection holds `a2` and the second the other
three maps. The maps are registered in the result datasets, not copied.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=2 w=0 res=1
    for dataset in A B C W; do
        t.create output=$dataset title="Dataset $dataset" \
            description="Maps of dataset $dataset"
    done
    while read -r dataset map first last; do
        r.mapcalc expression="$map = ${map#?}"
        t.register input=$dataset maps=$map \
            start=2001-01-$first end=2001-01-$last
    done <<EOF
    A a1 01 06
    A a2 06 11
    A a3 11 16
    A a4 16 21
    B b1 01 11
    B b2 06 11
    B b3 11 13
    B b4 12 14
    B b5 14 18
    B b6 18 21
    B b7 21 24
    C c1 06 11
    C c2 16 21
    W w1 03 19
    EOF
    ```

    ```sh
    t.rast.list input=A columns=name,start_time,end_time
    t.rast.list input=B columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00
    name|start_time|end_time
    b1|2001-01-01 00:00:00|2001-01-11 00:00:00
    b2|2001-01-06 00:00:00|2001-01-11 00:00:00
    b3|2001-01-11 00:00:00|2001-01-13 00:00:00
    b4|2001-01-12 00:00:00|2001-01-14 00:00:00
    b5|2001-01-14 00:00:00|2001-01-18 00:00:00
    b6|2001-01-18 00:00:00|2001-01-21 00:00:00
    b7|2001-01-21 00:00:00|2001-01-24 00:00:00
    ```

    ```sh
    t.select expression="same_time = A : B"
    t.rast.list input=same_time columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00
    ```

    ```sh
    t.select expression="other_time = A !: B"
    t.rast.list input=other_time columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    datasets = {
        "A": [("a1", 1, 6), ("a2", 6, 11), ("a3", 11, 16), ("a4", 16, 21)],
        "B": [
            ("b1", 1, 11),
            ("b2", 6, 11),
            ("b3", 11, 13),
            ("b4", 12, 14),
            ("b5", 14, 18),
            ("b6", 18, 21),
            ("b7", 21, 24),
        ],
        "C": [("c1", 6, 11), ("c2", 16, 21)],
        "W": [("w1", 3, 19)],
    }
    for dataset, maps in datasets.items():
        tools.t_create(
            output=dataset,
            title=f"Dataset {dataset}",
            description=f"Maps of dataset {dataset}",
        )
        for name, first, last in maps:
            tools.r_mapcalc(expression=f"{name} = {name[1:]}")
            tools.t_register(
                input=dataset,
                maps=name,
                start=f"2001-01-{first:02d}",
                end=f"2001-01-{last:02d}",
            )
    ```

    ```python
    for dataset in ("A", "B"):
        print(tools.t_rast_list(input=dataset, columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00
    name|start_time|end_time
    b1|2001-01-01 00:00:00|2001-01-11 00:00:00
    b2|2001-01-06 00:00:00|2001-01-11 00:00:00
    b3|2001-01-11 00:00:00|2001-01-13 00:00:00
    b4|2001-01-12 00:00:00|2001-01-14 00:00:00
    b5|2001-01-14 00:00:00|2001-01-18 00:00:00
    b6|2001-01-18 00:00:00|2001-01-21 00:00:00
    b7|2001-01-21 00:00:00|2001-01-24 00:00:00
    ```

    ```python
    tools.t_select(expression="same_time = A : B")
    print(tools.t_rast_list(input="same_time", columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00
    ```

    ```python
    tools.t_select(expression="other_time = A !: B")
    print(tools.t_rast_list(input="other_time", columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00
    ```

### Plan a selection without running it

With **-d** the tool prints what it would do and creates nothing. The
selection `A {:,during,r} W` gives the two maps of `A` inside `w1` the time of
`w1`. A map with a new time is a copy, so the plan has one `g.copy` for each
and registers the copies, named after the result `plan`, with the time of
`w1`. The listing of the datasets after the dry run does not show `plan`. A
run without **-d** then creates it. A second dry run with **--overwrite**
plans the same copies, now with the flag `overwrite`, because the result
exists.

=== "Command line"

    ```sh
    t.select -d expression="plan = A {:,during,r} W"
    ```

    ```text
    {'STDS': {'name': 'plan', 'stdstype': 'strds', 'temporal_type': 'absolute'},
     'processes': [{'flags': [],
                    'inputs': [('raster', ('a2@PERMANENT', 'plan_1'))],
                    'name': 'g.copy',
                    'outputs': []},
                   {'flags': [],
                    'inputs': [('raster', ('a3@PERMANENT', 'plan_2'))],
                    'name': 'g.copy',
                    'outputs': []}],
     'register': [('plan_1', '2001-01-03 00:00:00', '2001-01-19 00:00:00'),
                  ('plan_2', '2001-01-03 00:00:00', '2001-01-19 00:00:00')],
     'remove': []}
    ```

    ```sh
    t.list type=strds
    ```

    ```text
    A@PERMANENT
    B@PERMANENT
    C@PERMANENT
    W@PERMANENT
    other_time@PERMANENT
    same_time@PERMANENT
    ```

    ```sh
    t.select expression="plan = A {:,during,r} W"
    t.rast.list input=plan columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    plan_1|2001-01-03 00:00:00|2001-01-19 00:00:00|2.0
    plan_2|2001-01-03 00:00:00|2001-01-19 00:00:00|3.0
    ```

    ```sh
    t.select --overwrite -d expression="plan = A {:,during,r} W"
    ```

    ```text
    {'STDS': {'name': 'plan', 'stdstype': 'strds', 'temporal_type': 'absolute'},
     'processes': [{'flags': ['overwrite'],
                    'inputs': [('raster', ('a2@PERMANENT', 'plan_1'))],
                    'name': 'g.copy',
                    'outputs': []},
                   {'flags': ['overwrite'],
                    'inputs': [('raster', ('a3@PERMANENT', 'plan_2'))],
                    'name': 'g.copy',
                    'outputs': []}],
     'register': [('plan_1', '2001-01-03 00:00:00', '2001-01-19 00:00:00'),
                  ('plan_2', '2001-01-03 00:00:00', '2001-01-19 00:00:00')],
     'remove': []}
    ```

=== "Python (grass.tools)"

    ```python
    print(tools.t_select(expression="plan = A {:,during,r} W", flags="d").text)
    ```

    ```text
    {'STDS': {'name': 'plan', 'stdstype': 'strds', 'temporal_type': 'absolute'},
     'processes': [{'flags': [],
                    'inputs': [('raster', ('a2@PERMANENT', 'plan_1'))],
                    'name': 'g.copy',
                    'outputs': []},
                   {'flags': [],
                    'inputs': [('raster', ('a3@PERMANENT', 'plan_2'))],
                    'name': 'g.copy',
                    'outputs': []}],
     'register': [('plan_1', '2001-01-03 00:00:00', '2001-01-19 00:00:00'),
                  ('plan_2', '2001-01-03 00:00:00', '2001-01-19 00:00:00')],
     'remove': []}
    ```

    ```python
    print(tools.t_list(type="strds").text)
    ```

    ```text
    A@PERMANENT
    B@PERMANENT
    C@PERMANENT
    W@PERMANENT
    other_time@PERMANENT
    same_time@PERMANENT
    ```

    ```python
    tools.t_select(expression="plan = A {:,during,r} W")
    print(tools.t_rast_list(input="plan", columns="name,start_time,end_time,min").text)
    ```

    ```text
    name|start_time|end_time|min
    plan_1|2001-01-03 00:00:00|2001-01-19 00:00:00|2.0
    plan_2|2001-01-03 00:00:00|2001-01-19 00:00:00|3.0
    ```

    ```python
    print(
        tools.t_select(expression="plan = A {:,during,r} W", flags="d", overwrite=True).text
    )
    ```

    ```text
    {'STDS': {'name': 'plan', 'stdstype': 'strds', 'temporal_type': 'absolute'},
     'processes': [{'flags': ['overwrite'],
                    'inputs': [('raster', ('a2@PERMANENT', 'plan_1'))],
                    'name': 'g.copy',
                    'outputs': []},
                   {'flags': ['overwrite'],
                    'inputs': [('raster', ('a3@PERMANENT', 'plan_2'))],
                    'name': 'g.copy',
                    'outputs': []}],
     'register': [('plan_1', '2001-01-03 00:00:00', '2001-01-19 00:00:00'),
                  ('plan_2', '2001-01-03 00:00:00', '2001-01-19 00:00:00')],
     'remove': []}
    ```

### Read an expression with the classic algebra

The flag **-c** selects the classic algebra, which gives the results of the
releases before GRASS 8.6 for the forms they read. The two algebras differ
in some cases, which the NOTES list. One of them is the temporal operator `r`:
the algebra core gives one map per related pair, so `a3`, which contains `b3`
and `b4`, gives two maps, with the times of both. The classic algebra keeps
only the last pair of each map of `A`, so `a3` gives one map, with the time
of `b4`. The map of `a4` with the time of `b6` is in both results.

=== "Command line"

    ```sh
    t.select expression="pairs = A {:,contains,r} B"
    t.rast.list input=pairs columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    pairs_1|2001-01-11 00:00:00|2001-01-13 00:00:00|3.0
    pairs_2|2001-01-12 00:00:00|2001-01-14 00:00:00|3.0
    pairs_3|2001-01-18 00:00:00|2001-01-21 00:00:00|4.0
    ```

    ```sh
    t.select -c expression="pairs_classic = A {:,contains,r} B"
    t.rast.list input=pairs_classic columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    pairs_classic_1|2001-01-12 00:00:00|2001-01-14 00:00:00|3.0
    pairs_classic_2|2001-01-18 00:00:00|2001-01-21 00:00:00|4.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_select(expression="pairs = A {:,contains,r} B")
    print(tools.t_rast_list(input="pairs", columns="name,start_time,end_time,min").text)
    ```

    ```text
    name|start_time|end_time|min
    pairs_1|2001-01-11 00:00:00|2001-01-13 00:00:00|3.0
    pairs_2|2001-01-12 00:00:00|2001-01-14 00:00:00|3.0
    pairs_3|2001-01-18 00:00:00|2001-01-21 00:00:00|4.0
    ```

    ```python
    tools.t_select(expression="pairs_classic = A {:,contains,r} B", flags="c")
    print(
        tools.t_rast_list(
            input="pairs_classic", columns="name,start_time,end_time,min"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min
    pairs_classic_1|2001-01-12 00:00:00|2001-01-14 00:00:00|3.0
    pairs_classic_2|2001-01-18 00:00:00|2001-01-21 00:00:00|4.0
    ```

### Select only maps that are also related in space

Without **-s** only the time decides. The dataset `tiles` has two maps with
the time of `a2`, the day 6 to 11. The map `west` has the extent of the maps
of `A` (0 to 2 in both directions), the map `east` covers the columns from 3
to 5, so it has no point in common with them. Both maps are selected by time;
with **-s** only `west` is. The listings are ordered by name because both
maps have the same start time.

=== "Command line"

    ```sh
    g.region n=2 s=0 w=0 e=2 res=1
    r.mapcalc expression="west = 1"
    g.region n=2 s=0 w=3 e=5 res=1
    r.mapcalc expression="east = 2"
    g.region n=2 s=0 w=0 e=2 res=1
    t.create output=tiles title="Tiles" description="Two tiles at the time of a2"
    t.register input=tiles maps=west,east start=2001-01-06 end=2001-01-11
    ```

    ```sh
    t.select expression="by_time = tiles : A"
    t.rast.list input=by_time columns=name,start_time,end_time,east,west order=name
    ```

    ```text
    name|start_time|end_time|east|west
    east|2001-01-06 00:00:00|2001-01-11 00:00:00|5.0|3.0
    west|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0|0.0
    ```

    ```sh
    t.select -s expression="by_space = tiles : A"
    t.rast.list input=by_space columns=name,start_time,end_time,east,west order=name
    ```

    ```text
    name|start_time|end_time|east|west
    west|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0|0.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=2, s=0, w=0, e=2, res=1)
    tools.r_mapcalc(expression="west = 1")
    tools.g_region(n=2, s=0, w=3, e=5, res=1)
    tools.r_mapcalc(expression="east = 2")
    tools.g_region(n=2, s=0, w=0, e=2, res=1)
    tools.t_create(output="tiles", title="Tiles", description="Two tiles at the time of a2")
    tools.t_register(input="tiles", maps="west,east", start="2001-01-06", end="2001-01-11")
    ```

    ```python
    tools.t_select(expression="by_time = tiles : A")
    print(
        tools.t_rast_list(
            input="by_time", columns="name,start_time,end_time,east,west", order="name"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|east|west
    east|2001-01-06 00:00:00|2001-01-11 00:00:00|5.0|3.0
    west|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0|0.0
    ```

    ```python
    tools.t_select(expression="by_space = tiles : A", flags="s")
    print(
        tools.t_rast_list(
            input="by_space", columns="name,start_time,end_time,east,west", order="name"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|east|west
    west|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0|0.0
    ```

### Select 3D raster and vector maps and use other mapsets

The option **type** names the type of the datasets. The new mapset `paper`
has a dataset `A` of 3D raster maps and a dataset `B` of vector maps, so the
names differ from the raster datasets in `PERMANENT`. `soil_1`, `soil_2` and
`soil_3` last from 2 to 5, 5 to 8 and 8 to 11 January, the vector maps `g_1`
and `g_2` from 1 to 6 and 6 to 11 January.

The first selection is the one of the paper by Gebbert, Leppelt and Pebesma
(2019): the 3D raster maps that are during a vector map, written with the
functions `STR3DS()` and `STVDS()`. `soil_1` is inside `g_1`, `soil_3` ends
with `g_2`, and `soil_2` lies across both vector maps. The second selects
vector maps with **type=stvds**: `g_1` ends where `g_2` starts, so it precedes
it. No vector map contains another, so the third selection is empty, and still
creates an empty dataset with no map, with **-c** and without. The last one
selects in the raster datasets of `PERMANENT`, named with their mapset; the
result is in the current mapset and registers the map of `PERMANENT` itself,
not a copy.

=== "Command line"

    ```sh
    g.mapset -c mapset=paper
    g.region n=2 s=0 e=2 w=0 t=3 b=0 res=1 res3=1 tbres=1
    for i in 1 2 3; do
        r3.mapcalc expression="soil_$i = $i"
    done
    for i in 1 2; do
        v.random output=g_$i npoints=1 seed=$i
    done
    t.create type=str3ds output=A title="Soil" description="Soil in three steps"
    t.register -i type=raster_3d input=A maps=soil_1,soil_2,soil_3 \
        start=2001-01-02 increment="3 days"
    t.create type=stvds output=B title="Gauges" description="Two gauges"
    t.register -i type=vector input=B maps=g_1,g_2 \
        start=2001-01-01 increment="5 days"
    ```

    ```sh
    t.select type=str3ds expression="inside = STR3DS(A) {:,during,l} STVDS(B)"
    t.rast3d.list input=inside columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    soil_1|2001-01-02 00:00:00|2001-01-05 00:00:00
    soil_3|2001-01-08 00:00:00|2001-01-11 00:00:00
    ```

    ```sh
    t.select type=stvds expression="first = B {:,precedes} B"
    t.vect.list input=first columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    g_1|2001-01-01 00:00:00|2001-01-06 00:00:00
    ```

    ```sh
    t.select -c type=stvds expression="empty_classic = B {:,contains} B"
    t.info -g type=stvds input=empty_classic | grep number_of_maps
    t.select type=stvds expression="empty_core = B {:,contains} B"
    t.info -g type=stvds input=empty_core | grep number_of_maps
    ```

    ```text
    number_of_maps=0
    number_of_maps=0
    ```

    ```sh
    t.select expression="main = A@PERMANENT : B@PERMANENT"
    t.rast.list input=main columns=id,start_time,end_time
    ```

    ```text
    id|start_time|end_time
    a2@PERMANENT|2001-01-06 00:00:00|2001-01-11 00:00:00
    ```

    ```sh
    g.mapset mapset=PERMANENT
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="paper", flags="c")
    tools.g_region(n=2, s=0, e=2, w=0, t=3, b=0, res=1, res3=1, tbres=1)
    for i in (1, 2, 3):
        tools.r3_mapcalc(expression=f"soil_{i} = {i}")
    for i in (1, 2):
        tools.v_random(output=f"g_{i}", npoints=1, seed=i)
    tools.t_create(
        type="str3ds", output="A", title="Soil", description="Soil in three steps"
    )
    tools.t_register(
        type="raster_3d",
        input="A",
        maps="soil_1,soil_2,soil_3",
        start="2001-01-02",
        increment="3 days",
        flags="i",
    )
    tools.t_create(type="stvds", output="B", title="Gauges", description="Two gauges")
    tools.t_register(
        type="vector",
        input="B",
        maps="g_1,g_2",
        start="2001-01-01",
        increment="5 days",
        flags="i",
    )
    ```

    ```python
    tools.t_select(type="str3ds", expression="inside = STR3DS(A) {:,during,l} STVDS(B)")
    print(tools.t_rast3d_list(input="inside", columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    soil_1|2001-01-02 00:00:00|2001-01-05 00:00:00
    soil_3|2001-01-08 00:00:00|2001-01-11 00:00:00
    ```

    ```python
    tools.t_select(type="stvds", expression="first = B {:,precedes} B")
    print(tools.t_vect_list(input="first", columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    g_1|2001-01-01 00:00:00|2001-01-06 00:00:00
    ```

    ```python
    tools.t_select(type="stvds", expression="empty_classic = B {:,contains} B", flags="c")
    info = tools.t_info(type="stvds", input="empty_classic", flags="g").keyval
    print(f"number_of_maps={info['number_of_maps']}")
    tools.t_select(type="stvds", expression="empty_core = B {:,contains} B")
    info = tools.t_info(type="stvds", input="empty_core", flags="g").keyval
    print(f"number_of_maps={info['number_of_maps']}")
    ```

    ```text
    number_of_maps=0
    number_of_maps=0
    ```

    ```python
    tools.t_select(expression="main = A@PERMANENT : B@PERMANENT")
    print(tools.t_rast_list(input="main", columns="id,start_time,end_time").text)
    ```

    ```text
    id|start_time|end_time
    a2@PERMANENT|2001-01-06 00:00:00|2001-01-11 00:00:00
    ```

    ```python
    tools.g_mapset(mapset="PERMANENT")
    ```

### Select by one temporal relation

<!-- example: shell-only -->

Every block selects maps of `A` that are in one temporal relation to a
map of `B`. The maps of `A` stand in these relations to the maps of `B`:

| Map of A | Relation to the maps of B |
| --- | --- |
| `a1` | starts `b1`, precedes `b2` |
| `a2` | finishes `b1`, equal `b2`, precedes `b3` |
| `a3` | follows `b1` and `b2`, started by `b3`, contains `b4`, overlaps `b5` |
| `a4` | overlapped by `b5`, finished by `b6`, precedes `b7` |

The last column of each listing is the value of the map, which is the
number in its name, so the listing also tells which map of `A` was
selected when its name changed.

=== "Command line"

    ```sh
    # A map of A with the time of a map of B: a2 and b2.
    t.select expression="rel_equal = A {:,equal} B"
    t.rast.list input=rel_equal columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

    ```sh
    # The paper writes equal as equals: the same maps.
    t.select expression="rel_equals = A {:,equals} B"
    t.rast.list input=rel_equals columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

    ```sh
    # During also takes maps that start or finish with the map of B: a1
    # starts b1 and a2 finishes b1.
    t.select expression="rel_during = A {:,during} B"
    t.rast.list input=rel_during columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00|1.0
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

    ```sh
    # a1 starts b1: same start, a1 is shorter.
    t.select expression="rel_starts = A {:,starts} B"
    t.rast.list input=rel_starts columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00|1.0
    ```

    ```sh
    # a2 finishes b1: same end, a2 is shorter.
    t.select expression="rel_finishes = A {:,finishes} B"
    t.rast.list input=rel_finishes columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

    ```sh
    # Contains also takes maps that start or finish with the map of B: a3
    # contains b3 and b4, a4 contains b6.
    t.select expression="rel_contains = A {:,contains} B"
    t.rast.list input=rel_contains columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00|4.0
    ```

    ```sh
    # a3 is started by b3: same start, a3 is longer.
    t.select expression="rel_started = A {:,started} B"
    t.rast.list input=rel_started columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    ```

    ```sh
    # a4 is finished by b6: same end, a4 is longer.
    t.select expression="rel_finished = A {:,finished} B"
    t.rast.list input=rel_finished columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00|4.0
    ```

    ```sh
    # The end of a1 is the start of b2, a2 of b3, a4 of b7.
    t.select expression="rel_precedes = A {:,precedes} B"
    t.rast.list input=rel_precedes columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00|1.0
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00|4.0
    ```

    ```sh
    # a3 starts where b1 and b2 end.
    t.select expression="rel_follows = A {:,follows} B"
    t.rast.list input=rel_follows columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    ```

    ```sh
    # a3 starts first and ends inside b5.
    t.select expression="rel_overlaps = A {:,overlaps} B"
    t.rast.list input=rel_overlaps columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    ```

    ```sh
    # a4 starts inside b5 and ends later.
    t.select expression="rel_overlapped = A {:,overlapped} B"
    t.rast.list input=rel_overlapped columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00|4.0
    ```

    ```sh
    # over is overlaps or overlapped: a3 and a4.
    t.select expression="rel_over = A {:,over} B"
    t.rast.list input=rel_over columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00|4.0
    ```

### Select by several relations or by the complement

<!-- example: shell-only -->

The operator `:` selects the maps that are equal in time to a map of the
second dataset, `!:` the maps that are not. Relations in braces are
joined with `|`. `W` has one long map, `w1`, from 3 to 19 January, so
that `a2` and `a3` lie strictly inside it. A chain of selections is read
from left to right.

=== "Command line"

    ```sh
    # Maps of A equal in time to a map of B.
    t.select expression="sel_equal = A : B"
    t.rast.list input=sel_equal columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

    ```sh
    # Maps of A that are not.
    t.select expression="sel_not_equal = A !: B"
    t.rast.list input=sel_not_equal columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00|1.0
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00|4.0
    ```

    ```sh
    # Equal, during or overlaps.
    t.select expression="sel_three = A {:,equal|during|overlaps} B"
    t.rast.list input=sel_three columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00|1.0
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    ```

    ```sh
    # Neither equal nor during: the complement of two relations.
    t.select expression="sel_not_two = A {!:,equal|during} B"
    t.rast.list input=sel_not_two columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00|4.0
    ```

    ```sh
    # Strictly inside the one map of W.
    t.select expression="sel_inside = A {:,during} W"
    t.rast.list input=sel_inside columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    ```

    ```sh
    # The same pair from the other side selects the map of W.
    t.select expression="sel_wide = W {:,contains} A"
    t.rast.list input=sel_wide columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    w1|2001-01-03 00:00:00|2001-01-19 00:00:00|1.0
    ```

    ```sh
    # Equal to a map of B and of C: only a2.
    t.select expression="sel_chain = A : B : C"
    t.rast.list input=sel_chain columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

    ```sh
    # A precedes B first, then during W: of a1, a2 and a4 only a2.
    t.select expression="sel_chain_two = A {:,precedes} B {:,during} W"
    t.rast.list input=sel_chain_two columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

### Choose the temporal extent of the result

<!-- example: shell-only -->

The last part of the braces says which time the selected maps get: `l`
the time of the left map (the default), `r` of the right map, `i` the
intersection, `u` the union and `d` the disjoint union. A map whose
time differs from its own becomes a copy named after the result, here
`ext_i_1`, `ext_r_1` and so on. `a3` [11, 16) overlaps `b5` [14, 18).

=== "Command line"

    ```sh
    # l keeps 11 to 16 and the map a3 itself.
    t.select expression="ext_l = A {:,overlaps,l} B"
    t.rast.list input=ext_l columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    ```

    ```sh
    # i: 14 to 16.
    t.select expression="ext_i = A {:,overlaps,i} B"
    t.rast.list input=ext_i columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    ext_i_1|2001-01-14 00:00:00|2001-01-16 00:00:00|3.0
    ```

    ```sh
    # r: 14 to 18.
    t.select expression="ext_r = A {:,overlaps,r} B"
    t.rast.list input=ext_r columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    ext_r_1|2001-01-14 00:00:00|2001-01-18 00:00:00|3.0
    ```

    ```sh
    # u: 11 to 18.
    t.select expression="ext_u = A {:,overlaps,u} B"
    t.rast.list input=ext_u columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    ext_u_1|2001-01-11 00:00:00|2001-01-18 00:00:00|3.0
    ```

    ```sh
    # d: 11 to 18 as well, the two maps overlap.
    t.select expression="ext_d = A {:,overlaps,d} B"
    t.rast.list input=ext_d columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    ext_d_1|2001-01-11 00:00:00|2001-01-18 00:00:00|3.0
    ```

    ```sh
    # The word intersect is i.
    t.select expression="ext_word = A {:,overlaps,intersect} B"
    t.rast.list input=ext_word columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    ext_word_1|2001-01-14 00:00:00|2001-01-16 00:00:00|3.0
    ```

    ```sh
    # r gives one map per related pair: a3 with the times of b3 and b4,
    # a4 with the time of b6.
    t.select expression="ext_pairs = A {:,contains,r} B"
    t.rast.list input=ext_pairs columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    ext_pairs_1|2001-01-11 00:00:00|2001-01-13 00:00:00|3.0
    ext_pairs_2|2001-01-12 00:00:00|2001-01-14 00:00:00|3.0
    ext_pairs_3|2001-01-18 00:00:00|2001-01-21 00:00:00|4.0
    ```

    ```sh
    # The inverse selection keeps the maps with the time of A.
    t.select expression="ext_inverse = A {!:,contains,l} B"
    t.rast.list input=ext_inverse columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00|1.0
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

### Select with conditions on time

<!-- example: shell-only -->

An `if` selects the maps for which a condition on temporal variables
holds. Without an else part, the other maps are dropped; with one, each
map for which the condition is false is replaced by the map of the else
dataset that is equal to it in time. The first block is the chain of
relations from above, the second takes the else maps `c2` for `a4`.

=== "Command line"

    ```sh
    # a2 is the only map before 12 January that is equal to maps of
    # B and C.
    t.select expression='cond_chain = if(start_date(A) < "2001-01-12", A : B : C)'
    t.rast.list input=cond_chain columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

    ```sh
    # Written as in the older manual. Every map of A starts before 2005,
    # so the result is the same as for A : B : C, here a2.
    t.select expression='F = if(start_date(A) < "2005-01-01", A : B : C)'
    t.rast.list input=F columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

    ```sh
    # a1 to a3 start before 12 January; for a4, c2 has the same time.
    t.select expression='cond_else = if(start_date(A) < "2001-01-12", A, C)'
    t.rast.list input=cond_else columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00|1.0
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    c2|2001-01-16 00:00:00|2001-01-21 00:00:00|2.0
    ```

    ```sh
    # && needs both conditions: a start between day 6 and day 11.
    t.select expression="cond_doy = if(start_doy(A) >= 6 && start_doy(A) <= 11, A)"
    t.rast.list input=cond_doy columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    ```

    ```sh
    # || needs one of them: a start before day 3 or after day 10.
    t.select expression="cond_or = if(start_doy(A) < 3 || start_doy(A) > 10, A)"
    t.rast.list input=cond_or columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00|1.0
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    a4|2001-01-16 00:00:00|2001-01-21 00:00:00|4.0
    ```

    ```sh
    # The end date of a3 is 16 January.
    t.select expression='cond_end = if(end_date(A) == "2001-01-16", A)'
    t.rast.list input=cond_end columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    ```

    ```sh
    # The start of the week is Monday == 1; 1 January 2001 was one.
    t.select expression="cond_dow = if(start_dow(A) == 1, A)"
    t.rast.list input=cond_dow columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00|1.0
    ```

    ```sh
    # td() is the length of a map in days: B maps longer than 3 days.
    t.select expression="cond_td = if(td(B) > 3, B)"
    t.rast.list input=cond_td columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    b1|2001-01-01 00:00:00|2001-01-11 00:00:00|1.0
    b2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    b5|2001-01-14 00:00:00|2001-01-18 00:00:00|5.0
    ```

    ```sh
    # The relation in braces reads condition, relation, conclusion:
    # the maps of B that lie within a map of A.
    t.select expression="cond_relation = if({contains}, start_doy(A) > 0, B)"
    t.rast.list input=cond_relation columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    b3|2001-01-11 00:00:00|2001-01-13 00:00:00|3.0
    b4|2001-01-12 00:00:00|2001-01-14 00:00:00|4.0
    b6|2001-01-18 00:00:00|2001-01-21 00:00:00|6.0
    ```

### Count related maps and compare them

<!-- example: shell-only -->

The hash operator `#` counts, for each map of the left dataset, the maps
of the right dataset in the given relation. A map without any related
map has no count: it is neither selected nor used for the else part.
`a1` and `a2` contain no map of `B`, `a3` contains `b3` and `b4`, `a4`
contains `b6`. A comparison operator in braces combines the conditions
on two datasets.

=== "Command line"

    ```sh
    # The leading {equal} relates the count to the maps of A.
    t.select expression="count_a3 = if({equal}, A {#, contains} B > 1, A {:, contains} B)"
    t.rast.list input=count_a3 columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    ```

    ```sh
    # a3 has two maps; a4 has one, so c2 comes from the else part.
    t.select expression="count_else = if(A {#, contains} B > 1, A {:, contains} B, C)"
    t.rast.list input=count_else columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    c2|2001-01-16 00:00:00|2001-01-21 00:00:00|2.0
    ```

    ```sh
    # Written as in the older manual. Only a3 (two maps of B) and a4 (one)
    # have a count, and neither has more than three, so the else part holds
    # for both: c2 has the time of a4, and no map of C has the time of a3.
    t.select expression="D = if(A {#, contains} B > 3, A {:, contains} B, C)"
    t.rast.list input=D columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    c2|2001-01-16 00:00:00|2001-01-21 00:00:00|2.0
    ```

    ```sh
    # During counts starts and finishes: a1 and a2 each have b1.
    t.select expression="count_during = if(A {#, during} B >= 1, A)"
    t.rast.list input=count_during columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a1|2001-01-01 00:00:00|2001-01-06 00:00:00|1.0
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

    ```sh
    # A map of A that contains no map of B has no count, so no map has
    # count 0 and the result is empty.
    t.select expression="count_zero = if(A {#, contains} B == 0, A)"
    t.info -g input=count_zero | grep number_of_maps
    ```

    ```text
    number_of_maps=0
    ```

    ```sh
    # A map of A must start after day 5, and the B maps equal or
    # during it must start before day 9: only a2.
    t.select expression="cond_compare = if(start_doy(A) > 5 {&&, equal|during, l} start_doy(B) < 9, A)"
    t.rast.list input=cond_compare columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    ```

### Buffer, shift and snap

<!-- example: shell-only -->

`buff_t()` widens every map by the given time at both ends (a negative
size shrinks it), `tshift()` moves the maps and `tsnap()` sets the end
of each map to the start of the next. Maps with a new time are copies
named after the result. `C` has a gap from 11 to 16 January.

=== "Command line"

    ```sh
    # One day at both ends.
    t.select expression='buffered = buff_t(A, "1 days")'
    t.rast.list input=buffered columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    buffered_1|2000-12-31 00:00:00|2001-01-07 00:00:00|1.0
    buffered_2|2001-01-05 00:00:00|2001-01-12 00:00:00|2.0
    buffered_3|2001-01-10 00:00:00|2001-01-17 00:00:00|3.0
    buffered_4|2001-01-15 00:00:00|2001-01-22 00:00:00|4.0
    ```

    ```sh
    # One day less at both ends.
    t.select expression='shrunk = buff_t(A, "-1 days")'
    t.rast.list input=shrunk columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    shrunk_1|2001-01-02 00:00:00|2001-01-05 00:00:00|1.0
    shrunk_2|2001-01-07 00:00:00|2001-01-10 00:00:00|2.0
    shrunk_3|2001-01-12 00:00:00|2001-01-15 00:00:00|3.0
    shrunk_4|2001-01-17 00:00:00|2001-01-20 00:00:00|4.0
    ```

    ```sh
    # Two days later.
    t.select expression='shifted = tshift(A, "2 days")'
    t.rast.list input=shifted columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    shifted_1|2001-01-03 00:00:00|2001-01-08 00:00:00|1.0
    shifted_2|2001-01-08 00:00:00|2001-01-13 00:00:00|2.0
    shifted_3|2001-01-13 00:00:00|2001-01-18 00:00:00|3.0
    shifted_4|2001-01-18 00:00:00|2001-01-23 00:00:00|4.0
    ```

    ```sh
    # c1 grows to the start of c2; c2 has no successor and stays.
    t.select expression="snapped = tsnap(C)"
    t.rast.list input=snapped columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    snapped_1|2001-01-06 00:00:00|2001-01-16 00:00:00|1.0
    c2|2001-01-16 00:00:00|2001-01-21 00:00:00|2.0
    ```

    ```sh
    # B maps within the buffered A maps, which are 7 days long.
    # The else maps of C are not used: the condition holds everywhere.
    t.select expression='cond_buffered = if({contains}, td(buff_t(A, "1 days")) == 7, B, C)'
    t.rast.list input=cond_buffered columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    b2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    b3|2001-01-11 00:00:00|2001-01-13 00:00:00|3.0
    b4|2001-01-12 00:00:00|2001-01-14 00:00:00|4.0
    b6|2001-01-18 00:00:00|2001-01-21 00:00:00|6.0
    ```

    ```sh
    # Written as in the older manual. The buffered maps are 7 days long,
    # not 3, so the condition never holds and the else part gives the
    # maps of C within the buffered maps of A: c1 and c2.
    t.select expression='E = if({contains}, td(buff_t(A, "1 days")) == 3, B, C)'
    t.rast.list input=E columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    c1|2001-01-06 00:00:00|2001-01-11 00:00:00|1.0
    c2|2001-01-16 00:00:00|2001-01-21 00:00:00|2.0
    ```

### Select with the time of a single map

<!-- example: shell-only -->

`tmap()` takes the time stamp of one single map, here `w1` of `W`.

=== "Command line"

    ```sh
    # The same maps as `A {:,during} W`.
    t.select expression="single_map = A {:,during} tmap(w1)"
    t.rast.list input=single_map columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    a2|2001-01-06 00:00:00|2001-01-11 00:00:00|2.0
    a3|2001-01-11 00:00:00|2001-01-16 00:00:00|3.0
    ```

### Select on relative time

<!-- example: shell-only -->

Datasets of relative time work with the same relations and with
`buff_t()` and `tshift()`, whose size is a number, not a text, and
the result has relative time. `P` has four maps of two days, `Q`
two maps, 2 to 4 and 3 to 9.

=== "Command line"

    ```sh
    # Four maps of P with a length of two and two maps of Q, in days.
    r.mapcalc expression="p1 = 1"
    r.mapcalc expression="p2 = 2"
    r.mapcalc expression="p3 = 3"
    r.mapcalc expression="p4 = 4"
    r.mapcalc expression="q1 = 1"
    r.mapcalc expression="q2 = 2"
    t.create temporaltype=relative output=P title="P" description="Relative P"
    t.create temporaltype=relative output=Q title="Q" description="Relative Q"
    t.register -i input=P maps=p1,p2,p3,p4 start=0 increment=2 unit=days
    t.register input=Q maps=q1 start=2 end=4 unit=days
    t.register input=Q maps=q2 start=3 end=9 unit=days
    t.rast.list input=P columns=name,start_time,end_time,min
    t.rast.list input=Q columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    p1|0|2|1.0
    p2|2|4|2.0
    p3|4|6|3.0
    p4|6|8|4.0
    name|start_time|end_time|min
    q1|2|4|1.0
    q2|3|9|2.0
    ```

    ```sh
    # Equal in time: p2.
    t.select expression="rel_equal_q = P : Q"
    t.rast.list input=rel_equal_q columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    p2|2|4|2.0
    ```

    ```sh
    # p2 [2, 4) overlaps q2 [3, 9): the union is 2 to 9.
    t.select expression="rel_union = P {:,overlaps,u} Q"
    t.rast.list input=rel_union columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    rel_union_1|2|9|2.0
    ```

    ```sh
    # One step at both ends.
    t.select expression="rel_buffered = buff_t(P, 1)"
    t.rast.list input=rel_buffered columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    rel_buffered_1|-1|3|1.0
    rel_buffered_2|1|5|2.0
    rel_buffered_3|3|7|3.0
    rel_buffered_4|5|9|4.0
    ```

    ```sh
    # Ten steps later.
    t.select expression="rel_shifted_list = tshift(P, 10)"
    t.rast.list input=rel_shifted_list columns=name,start_time,end_time,min
    ```

    ```text
    name|start_time|end_time|min
    rel_shifted_list_1|10|12|1.0
    rel_shifted_list_2|12|14|2.0
    rel_shifted_list_3|14|16|3.0
    rel_shifted_list_4|16|18|4.0
    ```

    ```sh
    # The result has the temporal type of its input.
    t.select expression="rel_shifted = tshift(P, 10)"
    t.info -g input=rel_shifted | grep temporal_type
    ```

    ```text
    temporal_type=relative
    ```

<!-- markdownlint-enable MD046 -->

## REFERENCES

[PLY(Python-Lex-Yacc)](https://www.dabeaz.com/ply/)

Gebbert, S., Leppelt, T., Pebesma, E., 2019. A topology based
spatio-temporal map algebra for big data analysis. Data 4, 86.
<https://doi.org/10.3390/data4020086>

## SEE ALSO

*[r.mapcalc](r.mapcalc.md)*

## AUTHORS

Thomas Leppelt, Sören Gebbert, Thünen Institute of Climate-Smart
Agriculture
