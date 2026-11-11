## DESCRIPTION

*t.rast.algebra* performs temporal and spatial map algebra operations on
space time raster datasets (STRDS) by using the temporal raster algebra. It
reads an expression of the form `result = expression`, relates the maps of the
datasets in the expression by their time (and, with **-s**, by their place),
computes each result map with *[r.mapcalc](r.mapcalc.md)* and registers the
result maps in a new space time raster dataset in the current mapset. Use it
when the maps to combine are not simply paired by equal time stamps, or when a
result depends on how the time intervals of the maps lie to each other. To
compute with the maps of the datasets for each time step with a single
*r.mapcalc* expression, see *[t.rast.mapcalc](t.rast.mapcalc.md)*. The
counterparts for 3D raster and vector datasets are
*[t.rast3d.algebra](t.rast3d.algebra.md)* and
*[t.vect.algebra](t.vect.algebra.md)*, and *[t.select](t.select.md)* selects
maps without computing. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets.

The algebra provides methods for map selection based on their temporal
relations. It is also possible to temporally shift maps, to create temporal
buffer and to snap time instances to create a valid temporal topology.
Furthermore, expressions can be nested and evaluated in conditional statements
(if, else statements). Within if-statements, the algebra provides temporal
variables like start time, end time, day of year, time differences or number of
maps per time interval to build up conditions. In addition the algebra provides
a subset of the spatial operations from *[r.mapcalc](r.mapcalc.md)*. All these
operations can be assigned to STRDS or to the map lists resulting of operations
between STRDS.

### Expression, result and maps

The statement structure of the option **expression** is similar to that of
*[r.mapcalc](r.mapcalc.md)*:

```sh
"result = expression"
```

The name left of the equal sign is the new STRDS that will contain the result
of the calculation on the right side. The expression can be any valid or nested
combination of temporal operations and spatial overlay or buffer functions
that are provided by the temporal algebra, as described below. The option must
be passed as **quoted** expression, for example:

```sh
t.rast.algebra expression="C = A + B" basename=result
```

Here **C** is the new space time raster dataset that will contain maps with
the basename "result" and a numerical suffix separated by an underscore that
represent the sum of maps from the STRDS **A** and temporally equal maps (i.e.,
maps with equal temporal topology relation) from the STRDS **B**.

The result dataset is created in the current mapset, and an existing dataset
of that name is replaced only with **--overwrite**; without it the tool stops
with the error
`Space time dataset <C@t_rast_algebra> exists. Use the overwrite flag.` The
name of the result must not contain a dot or a mapset. The parser
stops at the dot: the new algebra with the error "Unexpected character '.'",
the classic algebra (**-c**) with a syntax error. No dataset is created. A
dataset of another mapset is named `name@mapset` in the expression. A name
without mapset is searched in the current mapset first, then in the mapsets
of the search path; the classic algebra (**-c**) searches only the current
mapset (see the example "Use datasets of another mapset").

The option **basename** is required. The result maps are named `basename_0`,
`basename_1` and so on, numbered in the order in which the algebra computes
them. This is not always the order of their time. The number is padded with
zeros to the digits of the count of computed maps: ten maps are named
`basename_00` to `basename_09` (see the example "Catalog: merge, single maps
and the neighbourhood modifier"). A map that is null everywhere is not
registered unless **-n** is given. The new algebra numbers only the registered
maps, so such a map leaves no gap: the next registered map takes its number
(see the example "Spatially related maps and empty maps"). A neighbourhood
modifier that reaches before the first map makes such a map in the new
algebra, see the last example of "Catalog: the expressions of the original
manual". The dry run with **-d** shows the names of a run that registers every
computed map. The classic algebra keeps the number of a map that it computes
and does not register, so its numbers can have a gap. An expression that
leaves no map to register ends with the warning "The expression produced no
map, the result is empty", and the result is an empty dataset.

The option **suffix** changes the part of the names after the basename. `num`,
the default, is the number described above. For absolute time, `gran` takes the
start time of the map cut to the granularity of the result and `time` the full
start time, see the example "Name the result maps and plan a run". A monthly
result from the last day of a month (January 31, February 28) has the
granularity of one month, so `gran` gives year and month (`2026_01`); the
classic algebra (**-c**) computes the granularity by the rules of the releases
before GRASS 8.6 with the correction of item 18 under "Corrections to the
classic algebra", one day here, and gives `2026_01_31` (see the
[introduction](temporalintro.md)). `num%NN` pads the number with zeros to NN
digits: `suffix=num%03` names the maps `basename_000`, `basename_001` and so on,
as in *t.rast.extract*. The classic algebra takes `num%NN` as `num`.

The option **nprocs** is the number of *r.mapcalc* processes that run at the
same time. The default is 1. The result is the same for any number.

### Flags

**-s** also checks the spatial topology of temporally related maps and processes
only maps that are related in space too. **-n** registers maps that are null
everywhere, which are left out by default; this concerns the new algebra, see
above for **-c**. **-g** uses the granularity algebra instead of the temporal
topology of the maps, see "Granularity algebra" below. **-d** performs a dry
run: it plans the maps and prints the process chain, but computes no map and
creates no dataset. **-c** selects the classic algebra, which gives the results
of the releases before GRASS 8.6 with the exceptions that the page
[changes in GRASS 8.6](temporalchanges.md#classic-algebra) lists; see "Core and
classic algebra" below. The environment variable `GRASS_TEMPORAL_ALGEBRA`
selects it for a whole session.

## TEMPORAL RASTER ALGEBRA

The temporal algebra provides a wide range of temporal operators and
functions that will be presented in the following section.

### TEMPORAL RELATIONS

Several temporal topology relations are supported between maps
registered in space time datasets:

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
is during B - A contains B.

Gebbert, Leppelt and Pebesma (2019) write the relation `equal` as `equals`;
the new algebra and **-c** read both names. The releases before GRASS 8.6
refused `equals` with a syntax error.

Topological relations must be specified with curly brackets {}.

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
operators process the time instances and intervals of two temporally
related maps and calculate the resulting temporal extent in five
possible different ways.

```sh
LEFT REFERENCE     l       Use the time stamp of the left space time dataset
INTERSECTION       i       Intersection
DISJOINT UNION     d       Disjoint union
UNION              u       Union
RIGHT REFERENCE    r       Use the time stamp of the right space time dataset
```

### TEMPORAL SELECTION

The temporal selection simply selects parts of a space time dataset
without processing any raster or vector data. The algebra provides a
selection operator **:** that by default selects parts of a space time
dataset that are temporally equal to parts of a second space time
dataset. The following expression

```sh
C = A : B
```

means: select all parts of space time dataset A that are equal to B and
store them in space time dataset C. These parts are time stamped maps.

In addition, the inverse selection operator **!:** is defined as the
complement of the selection operator, hence the following expression

```sh
C = A !: B
```

means: select all parts of space time time dataset A that are not equal
to B and store them in space time dataset C.

To select parts of a STRDS using different topological relations
regarding to other STRDS, the temporal topology selection operator can
be used. This operator consists of the temporal selection operator, the
topological relations that must be separated by the logical OR operator
**\|** and, the temporal extent operator. All three parts are separated
by comma and surrounded by curly brackets as follows: {"temporal
selection operator", "topological relations", "temporal operator"}.

**Examples:**

```sh
C = A {:,equal} B
C = A {!:,equal} B
```

We can now define arbitrary topological relations using the OR operator
"\|" to connect them:

```sh
C = A {:,equal|during|overlaps} B
```

Select all parts of A that are equal to B, during B or overlaps B.  
In addition, we can define the temporal extent of the resulting STRDS by
adding the temporal operator.

```sh
C = A {:,during,r} B
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

Selection operations can be evaluated within conditional statements as
showed below. Note that A and B can be either space time datasets or
expressions. The temporal relationship between the conditions and the
conclusions can be defined at the beginning of the if statement (third
and fourth examples below). The relationship between then and else
conclusion must be always equal.

```sh
if statement                        decision option                        temporal relations
  if(if, then, else)
  if(conditions, A)                   A if conditions are True;              temporal topological relation between if and then is equal.
  if(conditions, A, B)                A if conditions are True, B otherwise; temporal topological relation between if, then and else is equal.
  if(topologies, conditions, A)       A if conditions are True;              temporal topological relation between if and then is explicitly specified by topologies.
  if(topologies, conditions, A, B)    A if conditions are True, B otherwise; temporal topological relation between if, then and else is explicitly specified by topologies.
```

An `if` without else gives 0 where a condition on map values is false, like
the `if()` of *r.mapcalc* with two arguments, so a map that is false
everywhere is registered with the value 0.

The conditions are comparison expressions that are used to evaluate
space time datasets. Specific values of temporal variables are compared
by logical operators and evaluated for each map of the STRDS.  
**Important:** `&&` binds stronger than `||`, as in *r.mapcalc*, and
conditions can be grouped with parentheses. The classic algebra (**-c**)
evaluates conditions on temporal variables from left to right instead (see
NOTES).

The relation reads from the condition to the conclusion:
`if({contains}, condition, A)` takes the maps of A that lie within a map
of the condition. A map of the then part gets a result only if it has a
condition map in the given temporal relation. For a condition on
temporal variables and a temporal relation beyond `equal`, the else part
is also taken for the maps that no condition map is related to, while the
then part leaves them out. `if({equal}, ...)` and `if(...)` take no such
maps, because the condition speaks of maps with equal time only, and
neither does a condition on map values. In this expression each map of B
that contains two maps of A becomes the sum of these three maps, and the
maps of A outside of B are kept unchanged by the else part:

```sh
C = merge(if({equal|contains}, B {#,contains} A == 2, B {+,contains,l} A, A), A {!:,during} B)
```

The result stays the same without the `merge()` and the inverse select
operator, because the else part takes the maps without condition map.

Several maps with equal time stamps cannot be told apart by their time.
An arithmetic operator aggregates them (`E + E` adds all maps of a time
to each map of E), a conditional pairs them: a single condition map
applies to all conclusion maps of its time, n condition maps of a time
are paired with n conclusion maps of that time in the order of the
datasets. Different numbers of several maps of one time are an error.

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

The following temporal functions are evaluated only for the STDS that
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

In order to use the numbers returned by the functions in the last block
above, an offset value needs to be added. For example, start_doy(A, 0)
would return the DOY of the current map in STDS A. end_hour(A, -1) would
return the end hour of the previous map in STDS A.

#### Comparison operator

As mentioned above, the conditions are comparison expressions that are
used to evaluate space time datasets. Specific values of temporal
variables are compared by logical operators and evaluated for each map
of the STDS and (optionally) related maps. For complex relations, the
comparison operator can be used to combine conditions.  
The structure is similar to the select operator with the addition of an
aggregation operator: {"comparison operator", "topological relations",
aggregation operator, "temporal operator"}  
This aggregation operator (\| or &) defines the behaviour when a map is
related to more than one map, e.g. for the topological relation
'contains'. Should all (&) conditions for the related maps be true or is
it sufficient to have any (\|) condition that is true. The resulting
boolean value is then compared to the first condition by the comparison
operator (\|\| or &&). By default, the aggregation operator is related
to the comparison operator:  
comparison operator -\> aggregation operator:

```sh
|| -> | and && -> &
```

**Examples:**

```sh
Condition 1 {||, equal, r} Condition 2
Condition 1 {&&, equal|during, l} Condition 2
Condition 1 {&&, equal|contains, |, l} Condition 2
Condition 1 {&&, equal|during, l} Condition 2 && Condition 3
Condition 1 {&&, equal|during, l} Condition 2 {&&,contains, |, r} Condition 3
```

#### Comparison of related maps

Inside `if()`, the values of two space time datasets can be compared with
the comparison operators `==`, `!=`, `>`, `>=`, `<` and `<=`. Each map of
the first dataset is compared with every map of the second dataset that has
one of the given topological relations to it. The result for a map is true
if all comparisons are true (aggregation `&`) or if any is true
(aggregation `|`). The operator in braces has the form
{"comparison operator", "topological relations", aggregation operator,
"temporal operator"}; the aggregation operator and the temporal operator
are optional, the aggregation operator is `&` and the temporal operator `l`
by default, and the relations default to `equal` if the braces are left
out. The short form `A >= F` is the operator `{>=, equal, &, l}`. A map of
the first dataset without a related map gives no map in the classic
algebra and a null map in the new algebra:

```sh
if(A {>=, contains, |} E, A, 0)
if(A {<, equal|during, &, r} F, F, 0)
if(A >= F, A, F)
```

The first expression is true for a map of A if it is greater than or equal
to any related map of E; the last one gives, for each map of A, the value
of A where it is not smaller than the map of F with the same time, and the
value of F otherwise. In the new algebra the short form compares maps of
equal time stamps cell by cell, as `A + F` does, and stops with an error if
the time stamps differ. With the temporal reference `r`, the new algebra
compares each pair on its own, as it does for `&&` and `||`, where the
classic algebra gives every related map the whole condition of its left
map. Earlier GRASS releases did not read the comparison of two datasets,
neither in braces nor as `A >= F`; both algebras do now. The granularity
mode (**-g**) reads the short form; it refuses the operator in braces, as
it refuses every operator in braces.

#### Hash operator

Additionally, the number of maps in intervals can be computed and used
in conditional statements with the hash (#) operator.

```sh
A {#, contains} B
```

The hash operator is mostly used in the condition of an if statement, but
it can also stand alone or in arithmetic, where it has the precedence of
`+` and `-`: `B {#,contains} A + B` adds the count to each map of B.

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

This expression selects all maps from A that temporally contain more than
2 maps from B and stores them in space time dataset C. The leading equal
statement in the if condition specifies the temporal relation between
the if and then part of the if expression. This is very important, so we
do not need to specify a global time reference (a space time dataset)
for temporal processing.

Furthermore, the temporal algebra allows temporal buffering, shifting
and snapping with the functions buff_t(), tshift() and tsnap(),
respectively.

```sh
buff_t(A, size)         Buffer STDS A with granule ("1 month" or 5)
tshift(A, size)         Shift STDS A with granule ("1 month" or 5)
tsnap(A)                Snap time instances and intervals of STDS A
```

A negative size shrinks the maps; the new algebra stops with an error where
a map would keep no time, see "Core and classic algebra".

`tsnap()` ends a last map that is a time instance one granularity of the maps
after its start. A granularity of months counts from the first map, with the cut
to the end of a shorter month: the time instances January 31, February 28 and
March 31 have the granularity of one month, and the last one ends on April 30;
after an instance on April 30 in the same series it ends on May 31. The classic
algebra (**-c**) computes the granularity by the rules of the releases before
GRASS 8.6 with the correction of item 18 under "Corrections to the classic
algebra", one day here, and ends the instance of March 31 on April 1.

#### Merge function

The function `merge()` returns the union of the maps of two space time
datasets or of two expressions. The datatype of both operands must be
the same.

```sh
C = merge(A, B)
```

A map that occurs in both operands identically, that is with the same
map name, the same time stamps and the same computation, is kept once
in the result and the algebra prints a warning. This happens, for
example, if two selections of one dataset overlap. Maps of equal time
stamps that were computed differently are both kept:

```sh
C = merge(A + 1, A + 2)
```

#### Single map with temporal extent

The temporal algebra can also handle single maps with time stamps in the
tmap() function.

```sh
tmap()
```

For example:

```sh
C = A {:, during} tmap(event)
```

This statement selects all maps from space time data set A that are
during the temporal extent of the single map 'event'

### Spatial raster operators

The module supports the following raster operations:

```sh
Symbol  description     precedence

  %     modulus         1
  /     division        1
  *     multiplication  1
  +     addition        2
  -     subtraction     2
```

A division of two integers is an integer division, as in *r.mapcalc*, and
the result is truncated towards zero: `7 / 2` is 3, `-7 / 2` is -3 and
`7.0 / 2` is 3.5. In `7 / 2 / 2 * A` the numbers are divided first, so the
chain multiplies A by 1. Both algebras compute it so.

And raster functions:

```sh
abs(x)                  return absolute value of x
double(x)               convert x to double-precision floating point
float(x)                convert x to floating point
int(x)                  convert x to integer [ truncates ]
exp(x)                  exponential function of x
log(x)                  natural log of x
sqrt(x)                 square root of x
tan(x)                  tangent of x (x is in degrees)
sin(x)                  sine of x (x is in degrees)
cos(x)                  cosine of x (x is in degrees)
asin(x)                 inverse sine of x (result is in degrees)
acos(x)                 inverse cosine of x (result is in degrees)
isnull(x)               check if x = NULL
isntnull(x)             check if x is not NULL
null                    set null value
exist(x)                use the values of x as condition (non-zero is true)
```

#### Single raster map

The temporal raster algebra features also a function to integrate single
raster maps without time stamps into the expressions.

```sh
map()
```

For example:

```sh
C = A * map(constant_value)
```

This statement multiplies all raster maps from space time raster data
set A with the raster map 'constant_value'

### Combinations of temporal, raster and select operators

The user can combine the temporal topology relations, the temporal
operators and the spatial/select operators to create spatio-temporal
operators as follows:

```sh
{"spatial or select operator", "list of temporal relations", "temporal operator"}
```

For multiple topological relations or several related maps the
spatio-temporal operators feature implicit aggregation. The algebra
evaluates the stated STDS by their temporal topologies and apply the
given spatio-temporal operators in a aggregated form. If we have two
STDS A and B, B has three maps: b1, b2, b3 that are all during the
temporal extent of the single map a1 of A, then the following arithmetic
calculations would implicitly aggregate all maps of B into one result
map for a1 of A:

```code
 C = A {+, contains} B --> c1 = a1 + b1 + b2 + b3
```

**Important**: the aggregation behaviour is not symmetric

```code
 C = B {+, during} A --> c1 = b1 + a1
                         c2 = b2 + a1
                         c3 = b3 + a1
```

### Temporal neighbourhood modifier

The neighbourhood modifier of *r.mapcalc* is extended for the temporal
raster algebra with the temporal dimension. The format is
strds\[r,c,t\], where r is the row offset, c is the column offset and
t is the temporal offset. A single neighborhood modifier is interpreted as
temporal offset \[t\], while two neighborhood modifiers are interpreted
as row and column offsets \[r,c\].

```code
strds[2]
```

refers to the second successor of the current map.

```code
strds[1,2]
```

refers to the cell one row below and two columns to the right of the
current cell in the current map.

```code
strds[-2,-1,1]
```

refers to the cell two rows above and one column to the left of the
current cell of the first successor map.

```code
strds[0,1,-2]
```

refers to the cell one column to the right of the current cell in the
second predecessor map.

## NOTES

By default, only temporal topological relations among space time
datasets (STDS) are evaluated.
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
the spatial topology for its operator also without **-s**, as in the
classic algebra.

Maps are computed in the current region. A map that the result takes over
unchanged, for example one that a selection stamps with a new time, is
copied there as well; with **-s**, *r.mapcalc* computes such a copy in the
union of the regions of its input maps instead. A copy of a map that lies
outside the region has no data. Like any map without data it is not
registered unless **-n** is given, and a warning names it and the map it
copies. Set the region with *g.region* so that it covers
the maps.

Datasets of absolute and of relative time work in the same way, and the
result has the temporal type of the datasets in the expression. The steps of
`tshift()` and `buff_t()` are numbers in the unit of a dataset of relative
time and texts such as `"1 day"` for absolute time. Datasets of both temporal
types cannot be related in one expression: the tool stops with an error and
creates no dataset (see the example "Catalog: select and combine maps by
temporal relations").

An existing result dataset without **--overwrite** stops a dry run with
**-d** as it stops a real run.

### Core and classic algebra

Since GRASS 8.6, *t.rast.algebra* computes its expressions with the
functions of the Python package `grass.temporal.algebra`. The implementation
that computed them before, the reference implementation in
`grass.temporal.classic`, stays in the source code, and its rules stay
available as the classic algebra, so that published results remain
reproducible. The classic algebra is a set of rules of the same functions: it
reads the syntax of the reference implementation and applies its rules for
relations, order and results. The flag **-c** selects
it for one call, the environment variable `GRASS_TEMPORAL_ALGEBRA=classic`
for a whole session or script; `GRASS_TEMPORAL_ALGEBRA=core` or an unset or
empty variable selects the new algebra, and the flag takes precedence over the
variable. In Python, `TemporalRasterAlgebraParser` takes the keyword
`classic=True` for the same purpose. Both algebras compute the granularity
mode (**-g**), see below.

The two algebras differ in the following points. The examples use four
daily maps in A with the values 1 to 4, two maps of two days in B that
start with A, and time instances in I.

1. **One result per conclusion map.** If a map of the conclusion of an
    `if` has several related condition maps, their conditions are joined
    with and; written as `{during,|}`, the relation joins them with or. The
    classic algebra gives one result for each pair of condition map and
    conclusion map, so that a conclusion map can occur several times. The
    first expression keeps the cells of B where both maps of A within the
    map of B are greater than 1, the second where one of them is:

    ```sh
    C = if({during}, A > 1, B, 0)
    C = if({during,|}, A > 1, B, 0)
    ```

2. **Equal time stamps for then and else.** With a condition on map
    values, the then and the else part need equal time stamps; otherwise the
    algebra stops with an error. The classic algebra computes only the maps
    whose time stamp occurs in both parts and leaves out the others without
    notice. This expression is therefore an error, where the classic
    algebra gives an empty result:

    ```sh
    C = if(A > 2, A, B)
    ```

3. **Precedence.** `&&` binds stronger than `||`, and conditions can be
    grouped with parentheses. The classic algebra evaluates conditions on
    temporal variables from left to right and does not accept parentheses
    around conditions. The first expression takes all maps of A, because
    `td(A) == 1` is true for each of them; the classic algebra reads it as
    the second expression and takes none:

    ```sh
    C = if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)
    C = if((td(A) == 1 || td(A) == 2) && td(A) == 3, A)
    ```

4. **Right reference.** `A {:,R,r} B` and `A {op,R,r} B` give one map
    per related pair, with the time stamp of the right map and, for an
    operator, the value of this pair. The classic algebra keeps only the
    last pair of a selection, and an operator combines the left map with
    all of its related right maps in every result. The first expression gives
    four maps, the time stamps of A with the values of B; the classic
    algebra gives one map per map of B. If a map b1 contains the maps a1 and
    a2, the second expression gives `b1 + a1` and `b1 + a2`, the classic
    algebra `b1 + a1 + a2` for both:

    ```sh
    C = B {:,contains,r} A
    C = B {+,contains,r} A
    ```

    The inverse selection `A {!:,R,t} B` takes only the temporal operator
    `l`, because its maps have no related map to combine with; the classic
    algebra accepts the other operators.

5. **td() of a time instance** is null instead of an error, so a condition
    on it is neither true nor false. This expression gives no map; the
    classic algebra stops with an error:

    ```sh
    C = if(td(I) > 0, I)
    ```

    A temporal variable that a map does not have, such as `end_doy()` of a
    time instance or the calendar values of relative time, is an error in
    both algebras.

6. **More syntax.** Comparisons, temporal functions and the minus sign may
    stand anywhere in an expression, and a dataset may have the name of a
    function. The classic algebra reports a syntax error for each of these
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
    left out. The classic algebra intersects the map with its related maps
    until the first one that has no common time with the result so far,
    so that its result depends on the order of the related maps. If a
    dataset H has a map from day 2 to day 4, this map follows the map of A
    of day 1 and precedes the one of day 4; the intersections are the time
    instances of day 2 and day 4, and the map is left out:

    ```sh
    C = H {:,follows|precedes,i} A
    ```

8. **Negative buffer.** A negative size in `buff_t()` shrinks the maps
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

9. **merge() of maps read at an offset.** The new algebra takes two maps
    with equal content and time stamps as one map. The classic algebra, as
    the reference implementation, makes a new map for each map read with a
    temporal neighbourhood modifier and for each value of a temporal
    function with an offset, and `merge()` keeps such a map next to an
    equal one. The first two expressions give four maps in the new algebra
    and eight in the classic algebra, the third three and six:

    ```sh
    C = merge(A[0], A[0])
    C = merge(A + 1, A[0] + 1)
    C = merge(start_day(A, 1), start_day(A, 1))
    ```

10. **tsnap() of maps that start together.** Of maps with the same start,
    `tsnap()` snaps only one to the start of the next later map; the others
    keep their own ends. The new algebra takes the map that ends last, so
    its result does not depend on the order of the maps. The classic
    algebra takes the map listed last, so that the order of the arguments
    of `merge()` matters. If C has a map from day 2 to day 4, it starts
    with the map of A on days 2 to 3. The new algebra gives both
    expressions the same maps, the map of C ends on day 3. The classic
    algebra gives this result for the first expression only; in the second
    the map of C keeps its end on day 4 and the map of A ends on day 3:

    ```sh
    D = tsnap(merge(A, C))
    D = tsnap(merge(C, A))
    ```

11. **Integers beyond 32 bits.** The new algebra keeps an integer
    constant beyond 32 bits and writes it as a floating point number, so the
    result map is of type DCELL. The classic algebra reads it as *r.mapcalc*
    does, which keeps only its lower 32 bits: 3000000000 becomes
    -1294967296, and 2147483648 becomes null. Each map of A lasts one day,
    so this expression gives 3000000001 in the new algebra and -1294967295
    in the classic algebra:

    ```sh
    C = if(td(A) <= 0.5, A, 3000000000) + td(A)
    ```

    The classic algebra also computes arithmetic on time function values
    as *r.mapcalc* does, in 32 bits, also in a condition; the new algebra
    computes with all digits. If the two maps of RS last 3000000000 seconds
    each, `td(RS) * td(RS)` wraps around to -494665728 in the classic
    algebra, so this expression gives the value 1 for both maps there and
    the maps of RS in the new algebra. A time function on its own, as in
    `if(td(RS) > 2000000000, RS, 1)`, keeps all its digits in both
    algebras.

    ```sh
    C = if(td(RS) * td(RS) > 5, RS, 1)
    ```

12. **A number beside a temporal operator.** An operator in braces or the
    hash operator `#` needs a space time dataset on both sides. The
    classic algebra reads the number with the expression behind it as the
    right operand, so that the first expression is the second; the new
    algebra reports a syntax error for the first and computes the second:

    ```sh
    C = A {*,equal} 2 - B
    C = A {*,equal} (2 - B)
    C = A # 2 - B
    C = A # (2 - B)
    ```

    With an operator in braces, the same holds for a number with an
    expression in front of it as the left operand. The classic algebra reads
    this expression, the new algebra reports a syntax error:

    ```sh
    C = A - 1.5 {%,starts} A
    ```

13. **Maps without a related map under -n.** With **-n**, the new algebra
    registers a null map for each map of the left side of `{&&,...}` that
    has no related map; the classic algebra never registers one. In this
    expression the maps of A that contain no map of E give a null map each
    in the new algebra and no map in the classic algebra:

    ```sh
    C = if(A > 1 {&&,contains,&,l} E > 1, A)
    ```

In Python, both algebras raise `SyntaxError` for an expression they cannot
read. For one they cannot compute, the new algebra raises `ValueError` or
`TypeError`, where the classic algebra raises `FatalError`. Both raise
`FatalError` for a missing dataset or map and, without overwrite, for an
existing result dataset or map; a dry run of the classic algebra stops only
at an existing result map. The tool stops with the error message in both
algebras.

Two corrections apply to both algebras, so **-c** gives the rules of the
classic algebra, not the results of a particular release. First,
`if({R}, condition, conclusion)` reads "condition R conclusion" also for
conditions on temporal variables, as it always did for conditions on map
values. Second, with a temporal relation beyond `equal`, the else part of
a condition on temporal variables also takes the maps that no condition
map is related to (see CONDITIONAL STATEMENTS). Figure A3 of Gebbert,
Leppelt and Pebesma (2019) needs both: A has maps from day 1 to 3, 3 to 5
and 5 to 7 of January 2001, B has daily maps from day 1 to 10, and this
expression gives the first two maps of A and the maps of B from day 5 on,
as the figure shows, while GRASS 8.4 gives only the two maps of A:

```sh
C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)
```

Results that rely on the previous reading direction or else rule need the
GRASS version they were computed with.

#### Corrections to the classic algebra

The classic algebra gives the results of the releases before GRASS 8.6, except
where those releases were corrected; the page
[changes in GRASS 8.6](temporalchanges.md#classic-algebra) lists all
corrections. The items below describe some of them with examples. In them those
releases computed wrongly, ended in an error that had no reason, or reported the
wrong error. **-c** now gives the result described here. The reference
implementation was corrected in the same way, except in item 15: it still raises
the `CalledModuleError` of a failed module. The new algebra never computed these
cases wrongly; only the items on infinite values, on month steps, on dates
beyond the year 9999, on a map that starts with the next map in tsnap(), on a
failed module and on the granularity concerned the library and with it both
algebras. Results of earlier GRASS versions that used one of these forms need a
new run. The examples use the datasets of the list above and, in addition, N
with daily maps of the values 11 to 14 and RT with maps of relative time.

1. **td() of an expression** on the right of an operator used the value of
    the expression instead of the duration of its maps. With daily maps in N
    and A, the expression gave `N - A * 2` where it now gives `N - 1`:

    ```sh
    C = N - td(A * 2)
    ```

2. **tsnap() and tshift() of no maps.** If the expression inside has no
    maps, the result is empty, like any other empty result: an empty dataset
    is created, and an enclosing expression goes on with no maps. Earlier
    versions ended in an error. No map of A is equal to a map of B, so both
    expressions give an empty dataset:

    ```sh
    C = tsnap(A {:,equal} B)
    C = A + tshift(A {:,equal} B, "1 day")
    ```

3. **Increments that the library refuses.** An increment of `tshift()` or
    `buff_t()` that does not fit the temporal type is a syntax error and
    leaves no result dataset: a text with a time unit on relative time, a
    number without unit on absolute time, or a text that is not a time step.
    Earlier versions raised a `TypeError` for `buff_t()` on relative time,
    and for `tshift()` they did not report the increment as the cause: the
    result was missing, or an enclosing operator complained about its input.
    Each of these expressions is a syntax error. The new algebra refuses the
    same increments with a `ValueError`. A number with a fraction, such as
    `buff_t(RT, 1.5)`, stays valid on relative time in the classic algebra;
    the new algebra reads whole numbers only and reports a syntax error:

    ```sh
    C = tshift(A, "1 DAY")
    C = tshift(RT, "1 month")
    C = buff_t(RT, "3 hours")
    C = buff_t(A, 3)
    ```

4. **merge() with a single map.** The releases before GRASS 8.6 refused
    `merge()` of a dataset with a single map from `tmap()` with the error
    "Space time datasets to merge must have the same temporal type", also
    when both had the same temporal type. The data types of the maps are not
    compared, so a dataset may hold integer and floating point maps. The
    first expression gives the four maps of A and the single map. The second
    gives the maps of A and the floating point maps computed from them; it
    ran in those releases as well. Both algebras refuse `merge()` with
    `map()`, as in `merge(A, map(a1))`: the classic algebra reports a syntax
    error, the new algebra that a map without time stamp forms a series of
    its own.

    ```sh
    C = merge(A, tmap(singletmap))
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
    C = A + start_month(RT, 1)
    ```

6. **Intersection with a time instance.** With the temporal operator `i`, the
    time stamp of the result is the time instance, for a selection and for
    an operator, on absolute and on relative time. Earlier versions kept the
    time stamp of the left map for an operator and failed with a `TypeError`
    for a selection on relative time. If `sinst` is an instance on day 1,
    both expressions give one map with the instance as time:

    ```sh
    C = A {:,contains,i} tmap(sinst)
    C = A {+,contains,i} tmap(sinst)
    ```

7. **Infinite values.** A map with infinite values, such as the result of
    `exp(A * 1000)`, is registered with null as its minimum and maximum.
    Earlier versions failed when they wrote the map statistics ("no such
    column: inf") and could leave the temporal database locked.

    ```sh
    C = exp(A * 1000)
    ```

8. **td() of a counted map.** `td()` of a map counted by the hash operator gave
    the count instead of the duration, as an operand and in a comparison. The
    datasets A and N have daily maps and `A # merge(A, N)` counts 2 for each map
    of A. The expression added 2 to the maps of N where it now adds the one day
    of their duration; a condition such as `td(A # merge(A, N)) > 1.5` was true
    and is false now. The duration of a map that is not counted did not change:

    ```sh
    C = N + td(A # merge(A, N))
    ```

9. **Chains that start with a number or map().** A chain of operators whose
    first operand is a number or a map without time stamp, such as
    `map(L) - 1 - A`, was grouped from the right, as `map(L) - (1 - A)`. It is
    grouped from the left now, as in mathematics and in the new algebra. With
    0.5 in L and the values 1 to 4 in A, the expression gave 0.5, 1.5, 2.5 and
    3.5 and now gives -1.5, -2.5, -3.5 and -4.5, the result of
    `(map(L) - 1) - A`. The same holds for `2 * map(L) + A`, `1 - 2 - 3 - A` and
    chains inside `if()`. Chains after a dataset, such as
    `A + (map(L) - 1 - 1)`, which ended in a syntax error, are read now. A chain
    of numbers or maps alone, as in `map(L) - 1 - 1`, has no dataset to compute
    and stays a syntax error:

    ```sh
    C = map(L) - 1 - A
    ```

10. **td() as left operand of a stronger operator.** An expression such as
    `A + td(A) / A` was computed as `(A + td(A)) / A`, because `td()` could only
    stand right of an operator. The operators `*`, `/` and `%`, also with a
    temporal operator in braces, bind stronger than `+` and `-` now, as in
    mathematics and in the new algebra. With daily maps and the values 1 to 4 in
    A, `td(A)` is one day. The expression gave 2, 1.5, 1.3333 and 1.25 and now
    gives 2, 2.5, 3.3333 and 4.25. A `td()` at the start of a product, such as
    `td(A) * 2`, was a syntax error and is read now:

    ```sh
    C = A + td(A) / A
    ```

11. **A spatial relation without a temporal one.** An operator with spatial
    relation names only, such as `A {+,equivalent,l} N`, related no map, because
    maps are related by their temporal relations, and gave an empty result
    without a message. It stops now with the error "equivalent is a spatial
    relation and needs a temporal one, as in equal|overlap", as in the new
    algebra. Write a temporal relation beside the spatial one:

    ```sh
    C = A {+,equal|equivalent,l} N
    ```

12. **A map that starts with the next map in tsnap().** `tsnap()` sets the end
    of each map to the start of the next map. A map that starts at the same time
    as the next map keeps its own end instead. Earlier versions gave it the end
    of the next map, so the two maps swapped their ends. In the datasets above,
    the map of A on days 2 to 3 and the map of C on days 2 to 4 start together.
    In the classic algebra (**-c**, `GRASS_TEMPORAL_ALGEBRA=classic` and the
    reference implementation) the map listed first keeps its end. The new
    algebra orders such maps by their end instead, see item 10 of the
    differences above:

    ```sh
    D = tsnap(merge(A, C))
    ```

13. **Month and year steps from the end of a month.** `tshift()` and `buff_t()`
    by months or years ended in an error ("day is out of range for month") when
    a time stamp moved to a day that the target month lacks, in both algebras.
    Such a step now ends on the last day of that month. With a dataset M whose
    map lasts from 31 January to 31 March 2001, the first expression gives a map
    from 28 February to 30 April 2001, the second one a map from 31 December
    2000 to 30 April 2001. A year step from 29 February 2004 ends on 28 February
    2005:

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

14. **A date beyond the year 9999.** A step that ends behind the year 9999 or
    before the year 1, for example `buff_t(A, "365 days")` on a map that ends on
    1 December 9999, ended with a traceback ("date value out of range") in both
    algebras. It now ends with the error "... is beyond the year 9999" or "...
    is before the year 1"; no map and no dataset is created.

15. **A failed module.** If a module fails while the maps are computed, for
    example *r.mapcalc* on a floating point map as an operand of `&&`, both
    algebras ended with a Python traceback. They now end with the error
    `Module <r.mapcalc> failed with return code 1, see the error output above`;
    the cause is in the error output of the module above it. No dataset is
    created.

16. **The relation equals.** The releases before GRASS 8.6 refused the spelling
    `equals` of the paper with a syntax error. The classic algebra reads it as
    `equal`, so this expression gives the same maps as `C = A {+,equal,l} B`:

    ```sh
    C = A {+,equals,l} B
    ```

17. **Comparison of related maps.** The releases before GRASS 8.6 refused the
    comparison of two space time datasets, in braces and as `A >= F`, with a
    syntax error. **-c** reads it as described in the comparison of related maps
    above:

    ```sh
    C = if(A {<, contains, |, r} B, B, 0)
    ```

18. **The granularity of steps over a year and of a time of the day.** The
    granularity of a dataset, which the time suffix `gran`, `tsnap()` and the
    granularity mode **-g** use, counted a step between the first days of two
    months more than a year apart by the difference of the months only: 1
    January 2024 to 1 March 2025 gave 2 months and now gives 14 months. A step
    whose two ends lie at the same time of the day other than midnight counted
    in hours or minutes: time instances at 10:30 ten days apart had the
    granularity `14400 minutes` and now have `10 days`. A time of the day that
    differs between the two ends still counts: from 10:30 to 11:30 ten days
    later the granularity is `241 hours`.

#### Differences from the reference implementation

Besides the corrections, **-c** differs from the reference implementation in the
following points. Three of them change the outcome of an expression, the items
on lists of absolute and relative time, on a relative time instance in a
selection and on boxes that touch at a corner under **-s**; the others concern
messages, output and the class of an error.

- **Message texts.** The texts of warnings and errors are those of the
    new algebra. A `merge()` that meets maps identical in content and time
    warns "merge() dropped 4 duplicate map(s)" for `C = merge(A, A)` instead
    of "merge() keeps 4 maps of both operands only once". A refused increment
    of `tshift()` reports that the text cannot be read as a time step, for
    `tshift(A, "1 DAY")` instead of "cannot shift absolute time by".
- **Debug output.** In Python, with `debug=True`, the classic algebra
    prints each module call as a command line like the new algebra, for
    example `r.mapcalc expression=q_0=(a1@t_rast_algebra + 1) nprocs=1`. The
    reference implementation printed the *r.mapcalc* commands and the
    resulting statement.
- **Order of the errors.** Both implementations reject an invalid
    expression, but they can report another class of error. The classic
    algebra reads the whole expression before it computes. An expression with
    a syntax error is therefore a syntax error, where the reference
    implementation could stop with the error of a computation before it
    reached the syntax error. The classic algebra also reads a dataset that is
    an argument of a function before the arguments after it. A dataset of
    another temporal type stops it there (`FatalError`), where the reference
    implementation reads such a dataset last and can stop with an error of a
    later argument, for example a `SyntaxError` of `buff_t()` in
    `if(end_year(A) > 3, RT, buff_t(A, 2))`. In this expression the dataset
    `nosuch` does not exist and a bracket is too many; the reference
    implementation reported the missing dataset (`FatalError`):

    ```sh
    C = nosuch + A )
    ```

- **Existing result.** In Python, without `tgis.init(raise_fatal_error=True)`,
    the reference implementation exits the process with `SystemExit` for an
    existing result map. The classic algebra raises `FatalError`, as the new
    algebra does. The tools are not affected, because they initialise the
    library with `raise_fatal_error=True`.
- **Lists of absolute and relative time.** A relation over a list that
    mixes maps of absolute and of relative time, made with `merge()` and
    `tmap()`, stopped the reference implementation with a `TypeError` while it
    related the maps. The classic algebra does not reproduce this crash: maps
    of the two types relate to nothing, so this expression selects the maps
    of `RT` as `RT : RT` does:

    ```sh
    C = merge(tmap(sinst), RT) : RT
    ```

- **A relative time instance in a selection.** A selection on relative time with
    a time instance on the right and the temporal operator `r`, such as
    `RT {:,contains,r} tmap(rinst)`, stops the reference implementation with a
    `TypeError`, as it stopped the releases before GRASS 8.6. The classic
    algebra selects the map with the time of the instance, as the new algebra
    does; the last block of the
    [catalog](#catalog-where-the-classic-algebra-differs) where the classic
    algebra differs shows it.
- **Boxes that touch at a corner under -s.** With **-s** two maps are related
    when they are related in time and in space. Boxes with a common edge meet
    and are related in both implementations. Boxes that touch at a corner only
    are related by the reference implementation, but not by **-c**, as in the
    new algebra. A selection such as `A {:,precedes,r} B` gives no map for such
    maps in both, but an inverse selection such as `A {!:,precedes,r} B`
    differs: for a map of A from 1 to 2 January and a map of B from 2 to 3
    January whose box meets that of A at a corner, **-c** keeps the map with its
    own time 1 to 2 January, where the reference implementation takes the time
    of the partner, 2 to 3 January. Without **-s** only the time relates the
    maps.

### Granularity algebra

With the flag **-g**, each space time dataset of the expression is first sampled
with the common granularity of all datasets of the expression. A monthly series
from the last day of a month (January 31, February 28 and March 31) has the
granularity of one month and gets a granule per month; the classic algebra
(**-c**) computes the granularity from the maps by the rules of the releases
before GRASS 8.6 with the correction of item 18 under "Corrections to the
classic algebra", one day here, and gets a granule per day. If the start times
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
warning. The differences between the two algebras listed under "Core and
classic algebra" apply with **-g** as well, for example item 4, the right
reference.

See the example "Sample the maps with a common granularity" below.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_algebra` and sets the computational region
to North Carolina with cells of 1 km; the later examples work in this mapset
and region unless they say otherwise. Most examples show how the algebra
relates maps by their time, so their maps hold small constant values; the
example with satellite scenes and the hydrothermal coefficient in the catalog
of the publication compute with generated maps that vary in space.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_algebra -->

<!-- markdownlint-disable MD046 -->

### Compute with every map of a dataset

The dataset `A` has four daily maps for 1 to 4 March 2026. Each map has the
same value in all cells: 1, 2, 3 and 4, so the smallest and the largest value
of a map are equal.

The expression `C = A * 2` creates the dataset `C` and doubles each map of
`A`. The new maps are named `c_0` to `c_3` after **basename**, and each has
the time of its source map. **nprocs** lets two *r.mapcalc* processes run at
the same time; the result is the same as with one. The values are 2, 4, 6 and
8.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_algebra
    g.region raster=elev_state_500m res=1000 -a
    for step in 1 2 3 4; do
        r.mapcalc expression="a_$step = $step"
    done
    t.create output=A title="Daily maps" \
        description="Four daily maps with the values 1 to 4"
    t.register -i input=A maps=a_1,a_2,a_3,a_4 \
        start=2026-03-01 increment="1 day"
    t.rast.list input=A columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    a_1|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    a_2|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    a_3|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    a_4|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra expression="C = A * 2" basename=c nprocs=2
    t.rast.list input=C columns=name,start_time,end_time,min,max
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
    tools.g_mapset(flags="c", mapset="t_rast_algebra")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for step in range(1, 5):
        tools.r_mapcalc(expression=f"a_{step} = {step}")
    tools.t_create(
        output="A",
        title="Daily maps",
        description="Four daily maps with the values 1 to 4",
    )
    tools.t_register(
        input="A",
        maps="a_1,a_2,a_3,a_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_rast_list(input="A", columns="name,start_time,end_time,min,max").text)
    ```

    ```text
    name|start_time|end_time|min|max
    a_1|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    a_2|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    a_3|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    a_4|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```python
    tools.t_rast_algebra(expression="C = A * 2", basename="c", nprocs=2)
    print(tools.t_rast_list(input="C", columns="name,start_time,end_time,min,max").text)
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
    r.mapcalc expression="b_1 = 10"
    r.mapcalc expression="b_2 = 20"
    t.create output=B title="Two-day maps" \
        description="Two maps of two days each"
    t.register -i input=B maps=b_1,b_2 \
        start=2026-03-01 increment="2 days"
    t.rast.algebra expression="D = B {+,contains} A" basename=d
    t.rast.list input=D columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    d_0|2026-03-01 00:00:00|2026-03-03 00:00:00|13.0|13.0
    d_1|2026-03-03 00:00:00|2026-03-05 00:00:00|27.0|27.0
    ```

    ```sh
    t.rast.algebra expression="E = A {+,during} B" basename=e
    t.rast.list input=E columns=name,start_time,end_time,min,max
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
    tools.r_mapcalc(expression="b_1 = 10")
    tools.r_mapcalc(expression="b_2 = 20")
    tools.t_create(
        output="B",
        title="Two-day maps",
        description="Two maps of two days each",
    )
    tools.t_register(
        input="B",
        maps="b_1,b_2",
        start="2026-03-01",
        increment="2 days",
        flags="i",
    )
    tools.t_rast_algebra(expression="D = B {+,contains} A", basename="d")
    print(tools.t_rast_list(input="D", columns="name,start_time,end_time,min,max").text)
    ```

    ```text
    name|start_time|end_time|min|max
    d_0|2026-03-01 00:00:00|2026-03-03 00:00:00|13.0|13.0
    d_1|2026-03-03 00:00:00|2026-03-05 00:00:00|27.0|27.0
    ```

    ```python
    tools.t_rast_algebra(expression="E = A {+,during} B", basename="e")
    print(tools.t_rast_list(input="E", columns="name,start_time,end_time,min,max").text)
    ```

    ```text
    name|start_time|end_time|min|max
    e_0|2026-03-01 00:00:00|2026-03-02 00:00:00|11.0|11.0
    e_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|12.0
    e_2|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|23.0
    e_3|2026-03-04 00:00:00|2026-03-05 00:00:00|24.0|24.0
    ```

### Name the result maps and plan a run

The option **suffix** decides how the names of the result maps continue after
the **basename**. `num`, the default, counts the maps from 0, as in the first
example. For a dataset of absolute time, `gran` names a map after its start
time cut to the granularity of the dataset, here one day, and `time` after its
full start time, written as `2026_03_01T00_00_00`. `num%03` counts from 0
with three digits.

The flag **-d** plans the run and computes nothing. It prints the process
chain as a Python dictionary: the result dataset (`STDS`), the calls of
*r.mapcalc* (`processes`), the maps to register with their start and end time
(`register`) and the temporary maps to remove (`remove`). Neither the dataset
`dry` nor its maps exist afterwards, so *t.list* shows only the datasets of the
earlier examples.

=== "Command line"

    ```sh
    t.rast.algebra expression="by_gran = A * 2" basename=by_gran suffix=gran
    t.rast.list input=by_gran columns=name
    t.rast.algebra expression="by_time = A * 2" basename=by_time suffix=time
    t.rast.list input=by_time columns=name
    t.rast.algebra expression="by_num = A * 2" basename=by_num suffix=num%03
    t.rast.list input=by_num columns=name
    ```

    ```text
    name
    by_gran_2026_03_01
    by_gran_2026_03_02
    by_gran_2026_03_03
    by_gran_2026_03_04
    name
    by_time_2026_03_01T00_00_00
    by_time_2026_03_02T00_00_00
    by_time_2026_03_03T00_00_00
    by_time_2026_03_04T00_00_00
    name
    by_num_000
    by_num_001
    by_num_002
    by_num_003
    ```

    ```sh
    t.rast.algebra -d expression="dry = B * 2" basename=dry
    t.list type=strds columns=name mapset=.
    ```

    ```text
    {'STDS': {'name': 'dry', 'stdstype': 'strds', 'temporal_type': 'absolute'},
     'processes': [{'flags': [],
                    'inputs': [('expression', '"dry_0"=("b_1@t_rast_algebra" * 2)'),
                               ('nprocs', 1)],
                    'name': 'r.mapcalc',
                    'outputs': []},
                   {'flags': [],
                    'inputs': [('expression', '"dry_1"=("b_2@t_rast_algebra" * 2)'),
                               ('nprocs', 1)],
                    'name': 'r.mapcalc',
                    'outputs': []}],
     'register': [('dry_0', '2026-03-01 00:00:00', '2026-03-03 00:00:00'),
                  ('dry_1', '2026-03-03 00:00:00', '2026-03-05 00:00:00')],
     'remove': []}
    A
    B
    C
    D
    E
    by_gran
    by_num
    by_time
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_algebra(expression="by_gran = A * 2", basename="by_gran", suffix="gran")
    print(tools.t_rast_list(input="by_gran", columns="name").text)
    tools.t_rast_algebra(expression="by_time = A * 2", basename="by_time", suffix="time")
    print(tools.t_rast_list(input="by_time", columns="name").text)
    tools.t_rast_algebra(expression="by_num = A * 2", basename="by_num", suffix="num%03")
    print(tools.t_rast_list(input="by_num", columns="name").text)
    ```

    ```text
    name
    by_gran_2026_03_01
    by_gran_2026_03_02
    by_gran_2026_03_03
    by_gran_2026_03_04
    name
    by_time_2026_03_01T00_00_00
    by_time_2026_03_02T00_00_00
    by_time_2026_03_03T00_00_00
    by_time_2026_03_04T00_00_00
    name
    by_num_000
    by_num_001
    by_num_002
    by_num_003
    ```

    ```python
    print(tools.t_rast_algebra(expression="dry = B * 2", basename="dry", flags="d").text)
    print(tools.t_list(type="strds", columns="name", mapset=".").text)
    ```

    ```text
    {'STDS': {'name': 'dry', 'stdstype': 'strds', 'temporal_type': 'absolute'},
     'processes': [{'flags': [],
                    'inputs': [('expression', '"dry_0"=("b_1@t_rast_algebra" * 2)'),
                               ('nprocs', 1)],
                    'name': 'r.mapcalc',
                    'outputs': []},
                   {'flags': [],
                    'inputs': [('expression', '"dry_1"=("b_2@t_rast_algebra" * 2)'),
                               ('nprocs', 1)],
                    'name': 'r.mapcalc',
                    'outputs': []}],
     'register': [('dry_0', '2026-03-01 00:00:00', '2026-03-03 00:00:00'),
                  ('dry_1', '2026-03-03 00:00:00', '2026-03-05 00:00:00')],
     'remove': []}
    A
    B
    C
    D
    E
    by_gran
    by_num
    by_time
    ```

### Use the classic algebra

With the temporal operator `r`, the result takes the time of the right
dataset. The expression `B {+,contains,r} A` gives one map for each map of
`A`: the new algebra adds to each map of `A` the map of `B` that contains it,
so the results are 11, 12, 23 and 24 with the times of `A`. The flag **-c**
selects the classic algebra, which adds to each of them all maps of `A` that
the map of `B` contains: 13, 13, 27 and 27, with the same times. This is item
4 in the NOTES; the other differences are listed there.

=== "Command line"

    ```sh
    t.rast.algebra expression="core_sum = B {+,contains,r} A" basename=core_sum
    t.rast.list input=core_sum columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    core_sum_0|2026-03-01 00:00:00|2026-03-02 00:00:00|11.0|11.0
    core_sum_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|12.0
    core_sum_2|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|23.0
    core_sum_3|2026-03-04 00:00:00|2026-03-05 00:00:00|24.0|24.0
    ```

    ```sh
    t.rast.algebra -c expression="classic_sum = B {+,contains,r} A" \
        basename=classic_sum
    t.rast.list input=classic_sum columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    classic_sum_0|2026-03-01 00:00:00|2026-03-02 00:00:00|13.0|13.0
    classic_sum_1|2026-03-02 00:00:00|2026-03-03 00:00:00|13.0|13.0
    classic_sum_2|2026-03-03 00:00:00|2026-03-04 00:00:00|27.0|27.0
    classic_sum_3|2026-03-04 00:00:00|2026-03-05 00:00:00|27.0|27.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_algebra(expression="core_sum = B {+,contains,r} A", basename="core_sum")
    print(
        tools.t_rast_list(input="core_sum", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    core_sum_0|2026-03-01 00:00:00|2026-03-02 00:00:00|11.0|11.0
    core_sum_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|12.0
    core_sum_2|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|23.0
    core_sum_3|2026-03-04 00:00:00|2026-03-05 00:00:00|24.0|24.0
    ```

    ```python
    tools.t_rast_algebra(
        expression="classic_sum = B {+,contains,r} A",
        basename="classic_sum",
        flags="c",
    )
    print(
        tools.t_rast_list(
            input="classic_sum", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    classic_sum_0|2026-03-01 00:00:00|2026-03-02 00:00:00|13.0|13.0
    classic_sum_1|2026-03-02 00:00:00|2026-03-03 00:00:00|13.0|13.0
    classic_sum_2|2026-03-03 00:00:00|2026-03-04 00:00:00|27.0|27.0
    classic_sum_3|2026-03-04 00:00:00|2026-03-05 00:00:00|27.0|27.0
    ```

### Spatially related maps and empty maps

The dataset `patches` has three daily maps with the values 100, 200 and 300
for 1 to 3 March. The map `patch_2` is created in a window of 10 by 10 cells
that lies east of the region and has no cell in common with it; the region is
set back afterwards.

The expression `A + patches` is computed in the current region. The maps of the
second day do not overlap in space, so the result for that day has no data in
the region. By default a map without data is not registered, and the numbers
count the registered maps only: the first block gives the maps `plain_0`
(1 + 100 = 101) and `plain_1` (3 + 300 = 303). **-n** registers the empty map
as well: `with_null_1` has no minimum or maximum, which the list shows as
`None`. With **-s** the maps of the second day are not related in space, so
the algebra does not compute that pair, and with **-n** there is no empty map
either: `spatial_0` and `spatial_1` hold 101 and 303. The classic algebra
(**-c**) registers no empty map even with **-n**: `classic_0` and `classic_1`
hold 101 and 303.

=== "Command line"

    ```sh
    r.mapcalc expression="patch_1 = 100"
    g.region n=319000 s=309000 e=1010000 w=1000000 res=1000
    r.mapcalc expression="patch_2 = 200"
    g.region raster=elev_state_500m res=1000 -a
    r.mapcalc expression="patch_3 = 300"
    t.create output=patches title="Patches" \
        description="Three daily maps, the second one far away"
    t.register -i input=patches maps=patch_1,patch_2,patch_3 \
        start=2026-03-01 increment="1 day"
    t.rast.algebra expression="plain = A + patches" basename=plain
    t.rast.list input=plain columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    plain_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    plain_1|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

    ```sh
    t.rast.algebra -n expression="with_null = A + patches" basename=with_null
    t.rast.list input=with_null columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    with_null_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    with_null_1|2026-03-02 00:00:00|2026-03-03 00:00:00|None|None
    with_null_2|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

    ```sh
    t.rast.algebra -n -s expression="spatial = A + patches" basename=spatial
    t.rast.list input=spatial columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    spatial_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    spatial_1|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

    ```sh
    t.rast.algebra -n -c expression="classic = A + patches" basename=classic
    t.rast.list input=classic columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    classic_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    classic_1|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="patch_1 = 100")
    tools.g_region(n=319000, s=309000, e=1010000, w=1000000, res=1000)
    tools.r_mapcalc(expression="patch_2 = 200")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.r_mapcalc(expression="patch_3 = 300")
    tools.t_create(
        output="patches",
        title="Patches",
        description="Three daily maps, the second one far away",
    )
    tools.t_register(
        input="patches",
        maps="patch_1,patch_2,patch_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_algebra(expression="plain = A + patches", basename="plain")
    print(tools.t_rast_list(input="plain", columns="name,start_time,end_time,min,max").text)
    ```

    ```text
    name|start_time|end_time|min|max
    plain_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    plain_1|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

    ```python
    tools.t_rast_algebra(
        expression="with_null = A + patches", basename="with_null", flags="n"
    )
    print(
        tools.t_rast_list(
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
    tools.t_rast_algebra(expression="spatial = A + patches", basename="spatial", flags="ns")
    print(
        tools.t_rast_list(input="spatial", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    spatial_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    spatial_1|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
    ```

    ```python
    tools.t_rast_algebra(expression="classic = A + patches", basename="classic", flags="nc")
    print(
        tools.t_rast_list(input="classic", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    classic_0|2026-03-01 00:00:00|2026-03-02 00:00:00|101.0|101.0
    classic_1|2026-03-03 00:00:00|2026-03-04 00:00:00|303.0|303.0
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
    t.rast.algebra expression="unsampled = A + B" basename=unsampled
    t.info -g type=strds input=unsampled | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=0
    ```

    ```sh
    t.rast.algebra -g expression="sampled = A + B" basename=sampled
    t.rast.list input=sampled columns=name,start_time,end_time,min,max
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
    tools.t_rast_algebra(expression="unsampled = A + B", basename="unsampled")
    info = tools.t_info(type="strds", input="unsampled", flags="g").keyval
    print(f"number_of_maps={info['number_of_maps']}")
    ```

    ```text
    number_of_maps=0
    ```

    ```python
    tools.t_rast_algebra(expression="sampled = A + B", basename="sampled", flags="g")
    print(
        tools.t_rast_list(input="sampled", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    sampled_0|2026-03-01 00:00:00|2026-03-02 00:00:00|11.0|11.0
    sampled_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|12.0
    sampled_2|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|23.0
    sampled_3|2026-03-04 00:00:00|2026-03-05 00:00:00|24.0|24.0
    ```

### Compute the NDVI of satellite scenes

The red and the near infrared band of three scenes are stored in two
datasets, `S2_b4` and `S2_b8`, as time instances five days apart. The bands
are generated, not measured: integer reflectances scaled by 10000, as in
Sentinel-2 products, over North Carolina. From scene to scene the red band
decreases by 150 and the near infrared band increases by 400, and with the
elevation the red band rises and the near infrared band falls. The scenes of
the two datasets have equal time, so the expression pairs them and computes
the NDVI `(nir - red) / (nir + red)` of each scene; its smallest and largest
values grow from scene to scene. *float()* turns the integer maps into
floating point maps before the division, because the division of two
integers is an integer division. *t.rast.colors* sets the color table `ndvi`
for the maps of the result.

=== "Command line"

    ```sh
    for scene in 1 2 3; do
        r.mapcalc expression="red_$scene = round(900 - 150 * $scene + 0.2 * elev_state_500m)"
        r.mapcalc expression="nir_$scene = round(2400 + 400 * $scene - 0.5 * elev_state_500m)"
    done
    t.create output=S2_b4 title="Red band" description="Sentinel-2 band 4"
    t.create output=S2_b8 title="Near infrared band" \
        description="Sentinel-2 band 8"
    t.register input=S2_b4 maps=red_1,red_2,red_3 \
        start=2026-06-01 increment="5 days"
    t.register input=S2_b8 maps=nir_1,nir_2,nir_3 \
        start=2026-06-01 increment="5 days"
    t.rast.list input=S2_b4 columns=name,start_time,min,max
    t.rast.list input=S2_b8 columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    red_1|2026-06-01 00:00:00|749.0|1130.0
    red_2|2026-06-06 00:00:00|599.0|980.0
    red_3|2026-06-11 00:00:00|449.0|830.0
    name|start_time|min|max
    nir_1|2026-06-01 00:00:00|1850.0|2803.0
    nir_2|2026-06-06 00:00:00|2250.0|3203.0
    nir_3|2026-06-11 00:00:00|2650.0|3603.0
    ```

    ```sh
    t.rast.algebra basename=ndvi \
        expression="ndvi = float(S2_b8 - S2_b4) / ( S2_b8 + S2_b4 )"
    t.rast.colors input=ndvi color=ndvi
    t.rast.list input=ndvi columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    ndvi_0|2026-06-01 00:00:00|0.24161073565483093|0.5782657861709595
    ndvi_1|2026-06-06 00:00:00|0.39318886399269104|0.6849026679992676
    ndvi_2|2026-06-11 00:00:00|0.522988498210907|0.7783810496330261
    ```

=== "Python (grass.tools)"

    ```python
    for scene in range(1, 4):
        tools.r_mapcalc(
            expression=f"red_{scene} = round(900 - 150 * {scene} + 0.2 * elev_state_500m)"
        )
        tools.r_mapcalc(
            expression=f"nir_{scene} = round(2400 + 400 * {scene} - 0.5 * elev_state_500m)"
        )
    tools.t_create(output="S2_b4", title="Red band", description="Sentinel-2 band 4")
    tools.t_create(
        output="S2_b8",
        title="Near infrared band",
        description="Sentinel-2 band 8",
    )
    tools.t_register(
        input="S2_b4",
        maps="red_1,red_2,red_3",
        start="2026-06-01",
        increment="5 days",
    )
    tools.t_register(
        input="S2_b8",
        maps="nir_1,nir_2,nir_3",
        start="2026-06-01",
        increment="5 days",
    )
    print(tools.t_rast_list(input="S2_b4", columns="name,start_time,min,max").text)
    print(tools.t_rast_list(input="S2_b8", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    red_1|2026-06-01 00:00:00|749.0|1130.0
    red_2|2026-06-06 00:00:00|599.0|980.0
    red_3|2026-06-11 00:00:00|449.0|830.0
    name|start_time|min|max
    nir_1|2026-06-01 00:00:00|1850.0|2803.0
    nir_2|2026-06-06 00:00:00|2250.0|3203.0
    nir_3|2026-06-11 00:00:00|2650.0|3603.0
    ```

    ```python
    tools.t_rast_algebra(
        basename="ndvi",
        expression="ndvi = float(S2_b8 - S2_b4) / ( S2_b8 + S2_b4 )",
    )
    tools.t_rast_colors(input="ndvi", color="ndvi")
    print(tools.t_rast_list(input="ndvi", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    ndvi_0|2026-06-01 00:00:00|0.24161073565483093|0.5782657861709595
    ndvi_1|2026-06-06 00:00:00|0.39318886399269104|0.6849026679992676
    ndvi_2|2026-06-11 00:00:00|0.522988498210907|0.7783810496330261
    ```

### Use datasets of another mapset

A dataset of another mapset is named `name@mapset` in the expression. A name
without mapset is searched in the current mapset first, then in the mapsets of
the search path. The example creates the mapset `t_rast_algebra_2`, switches to
it and sets the region of the first example. The first call names `A` without
mapset and fails: `t_rast_algebra_2` has no dataset `A`, and `t_rast_algebra`,
where `A` exists, is not in its search path. The second call names
`A@t_rast_algebra`. The result dataset `halved` is always created in the
current mapset: its maps are new maps in `t_rast_algebra_2`, as the column
`mapset` shows, and the maps of `A` stay as they were.

The second block adds `t_rast_algebra` to the search path with
*[g.mapsets](g.mapsets.md)*, and `A` without mapset is found there. The
classic algebra (**-c**) searches only the current mapset and still fails.
The last command returns to `t_rast_algebra` for the following examples.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_algebra_2
    g.region raster=elev_state_500m res=1000 -a
    if ! t.rast.algebra expression="halved = A * 0.5" basename=halved 2>&1; then
        echo "t.rast.algebra failed"
    fi
    t.rast.algebra expression="halved = A@t_rast_algebra * 0.5" basename=halved
    t.rast.list input=halved columns=name,mapset,min,max
    ```

    ```text
    ERROR: Space time raster dataset <A@t_rast_algebra_2> not found
    t.rast.algebra failed
    name|mapset|min|max
    halved_0|t_rast_algebra_2|0.5|0.5
    halved_1|t_rast_algebra_2|1.0|1.0
    halved_2|t_rast_algebra_2|1.5|1.5
    halved_3|t_rast_algebra_2|2.0|2.0
    ```

    ```sh
    g.mapsets operation=add mapset=t_rast_algebra
    t.rast.algebra expression="doubled = A * 2" basename=doubled
    t.rast.list input=doubled columns=name,mapset,min,max
    if ! t.rast.algebra -c expression="doubled_c = A * 2" basename=doubled_c 2>&1; then
        echo "t.rast.algebra -c failed"
    fi
    g.mapset mapset=t_rast_algebra
    ```

    ```text
    name|mapset|min|max
    doubled_0|t_rast_algebra_2|2.0|2.0
    doubled_1|t_rast_algebra_2|4.0|4.0
    doubled_2|t_rast_algebra_2|6.0|6.0
    doubled_3|t_rast_algebra_2|8.0|8.0
    ERROR: Space time raster dataset <A@t_rast_algebra_2> not found
    t.rast.algebra -c failed
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    tools.g_mapset(mapset="t_rast_algebra_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    try:
        tools.t_rast_algebra(expression="halved = A * 0.5", basename="halved")
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.algebra failed")
    tools.t_rast_algebra(expression="halved = A@t_rast_algebra * 0.5", basename="halved")
    print(tools.t_rast_list(input="halved", columns="name,mapset,min,max").text)
    ```

    ```text
    ERROR: Space time raster dataset <A@t_rast_algebra_2> not found
    t.rast.algebra failed
    name|mapset|min|max
    halved_0|t_rast_algebra_2|0.5|0.5
    halved_1|t_rast_algebra_2|1.0|1.0
    halved_2|t_rast_algebra_2|1.5|1.5
    halved_3|t_rast_algebra_2|2.0|2.0
    ```

    ```python
    tools.g_mapsets(operation="add", mapset="t_rast_algebra")
    tools.t_rast_algebra(expression="doubled = A * 2", basename="doubled")
    print(tools.t_rast_list(input="doubled", columns="name,mapset,min,max").text)
    try:
        tools.t_rast_algebra(
            expression="doubled_c = A * 2", basename="doubled_c", flags="c"
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.algebra -c failed")
    tools.g_mapset(mapset="t_rast_algebra")
    ```

    ```text
    name|mapset|min|max
    doubled_0|t_rast_algebra_2|2.0|2.0
    doubled_1|t_rast_algebra_2|4.0|4.0
    doubled_2|t_rast_algebra_2|6.0|6.0
    doubled_3|t_rast_algebra_2|8.0|8.0
    ERROR: Space time raster dataset <A@t_rast_algebra_2> not found
    t.rast.algebra -c failed
    ```

### Catalog: select and combine maps by temporal relations

<!-- example: shell-only -->

The expressions of this and the following sections are shown for the shell
only; they use the datasets of the earlier examples and a few more, which the
first block creates: `I` has two time instances (2 and 4 March 2026, values
100 and 200), `H` one map from 2 to 4 March (value 5), `N` four daily maps
with the values 11 to 14, `F` four daily maps with the value 3, `M` one map
from 31 January to 31 March 2001 (value 7), `runoff` two maps of simulated
runoff in relative time (hours 0 to 1 and 1 to 2, values 1 and 2), `columns`
two daily maps whose cells hold their column number (1 to 839, plus 10 for
the second map), and the plain map `factor` with the value 0.5. Every block
replaces the dataset `C` of the block before (**--overwrite**) and lists it.

=== "Command line"

    ```sh
    r.mapcalc expression="i_1 = 100"
    r.mapcalc expression="i_2 = 200"
    t.create output=I title="Instants" description="Two instants"
    t.register input=I maps=i_1,i_2 start=2026-03-02 increment="2 days"
    r.mapcalc expression="h_1 = 5"
    t.create output=H title="Interval" description="One interval"
    t.register input=H maps=h_1 start=2026-03-02 end=2026-03-04
    for step in 1 2 3 4; do
        r.mapcalc expression="n_$step = 10 + $step"
        r.mapcalc expression="f_$step = 3"
    done
    t.create output=N title="Daily maps" description="Values 11 to 14"
    t.register -i input=N maps=n_1,n_2,n_3,n_4 \
        start=2026-03-01 increment="1 day"
    t.create output=F title="Daily maps" description="The value 3"
    t.register -i input=F maps=f_1,f_2,f_3,f_4 \
        start=2026-03-01 increment="1 day"
    r.mapcalc expression="m_1 = 7"
    t.create output=M title="Long interval" \
        description="From January to March 2001"
    t.register input=M maps=m_1 start=2001-01-31 end=2001-03-31
    r.mapcalc expression="runoff_1 = 1"
    r.mapcalc expression="runoff_2 = 2"
    t.create output=runoff temporaltype=relative title="Runoff" \
        description="Simulated runoff in mm per model hour"
    t.register -i input=runoff maps=runoff_1,runoff_2 start=0 increment=1 \
        unit=hours
    r.mapcalc expression="columns_1 = col()"
    r.mapcalc expression="columns_2 = col() + 10"
    t.create output=columns title="Columns" description="Column numbers"
    t.register -i input=columns maps=columns_1,columns_2 start=2026-03-01 \
        increment="1 day"
    r.mapcalc expression="factor = 0.5"
    ```

    The selection `:` takes the maps of the left dataset that are in the given
    relation to a map of the right one and does not compute any cell. Without a
    relation it takes the maps of equal time: the first block gives the four
    maps of `A`, each with the time of the map of `N`. In the second block, each
    map of `A` lies during a map of `B`, so all four maps are selected, and in
    the third the temporal operator `r` gives each of them the time of the map
    of `B` it lies in, so two maps share a time.

    ```sh
    t.rast.algebra --overwrite expression="C = A : N" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = A {:,during} B" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = A {:,during,r} B" basename=c
    t.rast.list input=C order=start_time,name \
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
    Several relations are joined with `|`: every map of `A` is during a map of
    `B`, and the relations `equal` and `overlaps` add no other map.

    ```sh
    t.rast.algebra --overwrite expression="C = A {!:,during} H" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = A {:,during} tmap(h_1)" \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_1|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = A {:,equal|during|overlaps} B" \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    The map of `H` starts before the second map of `B` and ends within it, so
    it overlaps that map; the first map of `B` is not in this relation to it.
    The sum is 25 for either operator. The temporal operator decides the time
    of the sum: `i` is the intersection of the two times, 3 and 4 March, and
    `u` the union, 2 to 5 March.

    ```sh
    t.rast.algebra --overwrite expression="C = H {+,overlaps,i} B" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-03 00:00:00|2026-03-04 00:00:00|25.0|25.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = H {+,overlaps,u} B" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-02 00:00:00|2026-03-05 00:00:00|25.0|25.0
    ```

    The hash operator `#` counts the related maps: each map of `B` contains
    two maps of `A`. In a condition, the count selects the maps of `B` that
    contain more than one map.

    ```sh
    t.rast.algebra --overwrite expression="C = B {#,contains} A" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|2.0|2.0
    ```

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if(B {#,contains} A > 1, B)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|10.0|10.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|20.0|20.0
    ```

    Datasets of absolute and of relative time cannot be related. The dataset
    `runoff` has relative time, so the sum with `A` stops with an error and
    creates no dataset:

    ```sh
    if ! t.rast.algebra expression="mixed = A + runoff" basename=mixed 2>&1; then
        echo "t.rast.algebra failed"
    fi
    ```

    ```text
    ERROR: Series of different temporal types or units cannot be related
    t.rast.algebra failed
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
    t.rast.algebra --overwrite expression="C = if(A > 2, A)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|0.0|0.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|0.0|0.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if(start_day(A) <= 2, A, 0)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|0.0|0.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|0.0|0.0
    ```

    Conditions on values and on time are joined with `&&` and `||`, and `&&`
    binds stronger. The map of the first day fails `A > 1` and gives 0; the
    others pass both parts.

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if(A > 1 && td(A) == 1, A)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|0.0|0.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    With a temporal relation at the start, `if({during}, A > 1, B, 0)` takes
    the maps of `B` that lie during a map of the condition. A map of `B`
    contains two maps of `A`, and the conditions of the related maps are
    joined with and: the first map of `B` has a map of `A` with the value 1,
    so the result is 0, and the second gives 20. Written as `{during,|}` the
    relation joins them with or, so both maps of `B` are kept: 10 and 20.

    ```sh
    t.rast.algebra --overwrite expression="C = if({during}, A > 1, B, 0)" \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|0.0|0.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|20.0|20.0
    ```

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if({during,|}, A > 1, B, 0)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|10.0|10.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|20.0|20.0
    ```

    Inside `if()`, two datasets are compared cell by cell. `A >= F` compares
    the maps of equal time, and the `if` gives the larger of the two: the
    values of `A` are 1 to 4 and those of `F` are 3, so the result is 3, 3, 3
    and 4. A comparison with a temporal relation in curly brackets is true for
    a map of `A` if the comparison holds for any (`|`) or all (`&`) of the
    related maps: `A {<,during,|} B` is true for every map of `A`, since all
    values are below 10.

    ```sh
    t.rast.algebra --overwrite expression="C = if(A >= F, A, F)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|3.0|3.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|3.0|3.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if(A {<,during,|} B, A, 0)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
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

=== "Command line"

    ```sh
    t.rast.algebra --overwrite expression="C = A + start_day(A)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|2.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|4.0|4.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|6.0|6.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|8.0|8.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = A * td(A)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
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
    t.rast.algebra --overwrite expression='C = tshift(A, "1 day")' basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-02 00:00:00|2026-03-03 00:00:00|1.0|1.0
    c_1|2026-03-03 00:00:00|2026-03-04 00:00:00|2.0|2.0
    c_2|2026-03-04 00:00:00|2026-03-05 00:00:00|3.0|3.0
    c_3|2026-03-05 00:00:00|2026-03-06 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = tsnap(I)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-02 00:00:00|2026-03-04 00:00:00|100.0|100.0
    c_1|2026-03-04 00:00:00|2026-03-06 00:00:00|200.0|200.0
    ```

    ```sh
    t.rast.algebra --overwrite expression='C = buff_t(I, "1 day")' basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|100.0|100.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|200.0|200.0
    ```

    ```sh
    t.rast.algebra --overwrite expression='C = buff_t(B, "-12 hours")' \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
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
    t.rast.algebra --overwrite expression='C = tshift(M, "1 months")' \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2001-02-28 00:00:00|2001-04-30 00:00:00|7.0|7.0
    ```

    ```sh
    t.rast.algebra --overwrite expression='C = buff_t(M, "1 months")' \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2000-12-31 00:00:00|2001-04-30 00:00:00|7.0|7.0
    ```

    Datasets with relative time work in the same way, and a step is a number
    in the unit of the dataset: `runoff * 2` doubles the values 1 and 2, and
    shifting by 1 moves the maps by one hour.

    ```sh
    t.rast.algebra --overwrite expression="C = runoff * 2" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|0|1|2.0|2.0
    c_1|1|2|4.0|4.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = tshift(runoff, 1)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
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
enters through `map()`: `A * map(factor)` multiplies each map of `A` with 0.5,
giving 0.5, 1, 1.5 and 2.

=== "Command line"

    ```sh
    t.rast.algebra --overwrite expression="C = merge(A, B)" basename=c
    t.rast.list input=C order=start_time,name \
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

    Merging three datasets gives ten maps, and the numbers in their names
    have two digits.

    ```sh
    t.rast.algebra --overwrite expression="C = merge(merge(A, N), B)" basename=c
    t.rast.list input=C order=name columns=name
    ```

    ```text
    name
    c_00
    c_01
    c_02
    c_03
    c_04
    c_05
    c_06
    c_07
    c_08
    c_09
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = A * map(factor)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|0.5|0.5
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|1.0|1.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|1.5|1.5
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|2.0|2.0
    ```

    A single offset in the neighbourhood modifier reads another map in time.
    `A[1]` has the cells of the next map with the time of the current one, so
    the last map of `A` has no successor and the result has three maps with the
    values 2, 3 and 4. `A[-1] + A` adds the previous map, which leaves out the
    first map.

    ```sh
    t.rast.algebra --overwrite expression="C = A[1]" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|2.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|3.0|3.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = A[-1] + A" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-02 00:00:00|2026-03-03 00:00:00|3.0|3.0
    c_1|2026-03-03 00:00:00|2026-03-04 00:00:00|5.0|5.0
    c_2|2026-03-04 00:00:00|2026-03-05 00:00:00|7.0|7.0
    ```

    Two offsets are a row and a column offset in the cells of the map. The
    cells of the maps of `columns` hold their column number, 1 to 839 (plus 10
    for the second map). `columns[0,1]` reads the cell to the right, so each
    column sees the value of the next one, and the last column has no right
    neighbour and is null: the result ranges from 2 to 839 for the first day
    and from 12 to 849 for the second. `columns[0,-1]` reads the cell to the
    left, so the first column is null and the result ranges from 1 to 838 and
    from 11 to 848. Three offsets add the temporal one: `columns[0,1,1]` reads
    the cell to the right in the next map, 12 to 849, which leaves out the
    last day.

    ```sh
    t.rast.algebra --overwrite expression="C = columns[0,1]" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|2.0|839.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|12.0|849.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = columns[0,-1]" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|838.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|11.0|848.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = columns[0,1,1]" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|12.0|849.0
    ```

### Catalog: where the classic algebra differs

<!-- example: shell-only -->

Each pair of blocks computes one expression of the list "Core and classic
algebra" in the NOTES, first with the new algebra and then with **-c**; the last
block shows a form that the releases before GRASS 8.6 refused with a
`TypeError`, which the classic algebra now computes and the reference
implementation still refuses. The first pair is item 1: the conditions of the
two maps of `A` within a map of `B` are joined with and, so the new algebra
gives 0 and 20; the classic algebra gives one result for each pair of a
condition map and a conclusion map, and four maps in total.

=== "Command line"

    ```sh
    t.rast.algebra --overwrite expression="C = if({during}, A > 1, B, 0)" \
        basename=c
    t.rast.list input=C order=start_time,name \
        columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|0.0|0.0
    c_1|2026-03-03 00:00:00|2026-03-05 00:00:00|20.0|20.0
    ```

    ```sh
    t.rast.algebra -c --overwrite \
        expression="C = if({during}, A > 1, B, 0)" basename=c
    t.rast.list input=C order=start_time,name \
        columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-03 00:00:00|0.0|0.0
    c_1|2026-03-01 00:00:00|2026-03-03 00:00:00|10.0|10.0
    c_2|2026-03-03 00:00:00|2026-03-05 00:00:00|20.0|20.0
    c_3|2026-03-03 00:00:00|2026-03-05 00:00:00|20.0|20.0
    ```

    Item 2, equal time stamps: the then part `A` and the else part `B` have
    different time stamps. The new algebra stops with an error and creates no
    dataset; the classic algebra computes only the maps whose time stamp occurs
    in both parts, which are none, and the result is an empty dataset.

    ```sh
    if ! t.rast.algebra expression="E1 = if(A > 2, A, B)" basename=e1 2>&1; then
        echo "t.rast.algebra failed"
    fi
    ```

    ```text
    ERROR: where() needs series with equal time stamps; they differ at slot 0:
           2026-03-01 00:00:00 .. 2026-03-02 00:00:00 and 2026-03-01 00:00:00
           .. 2026-03-03 00:00:00. Relate the series with gather() or pairs()
           first.
    t.rast.algebra failed
    ```

    ```sh
    t.rast.algebra -c expression="E2 = if(A > 2, A, B)" basename=e2
    t.info -g type=strds input=E2 | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=0
    ```

    Item 3, precedence: `&&` binds stronger than `||` in the new algebra, so
    each map of `A` is taken because `td(A) == 1` is true. The classic algebra
    reads the condition from left to right and takes no map; the tool warns
    and the result dataset is empty.

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)" \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra -c expression="E3 = if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)" \
        basename=e3
    t.info -g type=strds input=E3 | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=0
    ```

    Item 5, `td()` of a time instance: the new algebra gives null, so the
    condition is neither true nor false and no map remains. The classic
    algebra stops with an error.

    ```sh
    t.rast.algebra expression="E4 = if(td(I) > 0, I)" basename=e4
    t.info -g type=strds input=E4 | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=0
    ```

    ```sh
    if ! t.rast.algebra -c expression="E5 = if(td(I) > 0, I)" basename=e5 2>&1; then
        echo "t.rast.algebra failed"
    fi
    ```

    ```text
    ERROR: Function td() requires a time interval, but map <i_1@t_rast_algebra>
           is a time instance.
    t.rast.algebra failed
    ```

    Item 6, more syntax: the minus sign may stand at the start of an
    expression in the new algebra, which gives 9, 8, 7 and 6. The classic
    algebra reports a syntax error.

    ```sh
    t.rast.algebra --overwrite expression="C = -A + 10" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|9.0|9.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|8.0|8.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|7.0|7.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|6.0|6.0
    ```

    ```sh
    if ! t.rast.algebra -c expression="E6 = -A + 10" basename=e6 2>&1; then
        echo "t.rast.algebra failed"
    fi
    ```

    ```text
    ERROR: syntax error on line 1, position 5 token SUB near '-' expression 'E6
           = -A + 10'
    t.rast.algebra failed
    ```

    Item 7, intersection: the map of `H` follows the map of `A` of the first
    day and precedes the one of the fourth day. The new algebra leaves it out,
    because the two intersections are not the same time; the classic algebra
    gives one time instance.

    ```sh
    t.rast.algebra expression="E7 = H {:,follows|precedes,i} A" basename=e7
    t.info -g type=strds input=E7 | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=0
    ```

    ```sh
    t.rast.algebra -c expression="E8 = H {:,follows|precedes,i} A" basename=e8
    t.rast.list input=E8 columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    e8_0|2026-03-02 00:00:00|None|5.0|5.0
    ```

    Item 8, negative buffer: the maps of `B` last two days, so a buffer of -1
    day on both sides leaves no time. The new algebra stops with an error. The
    classic algebra goes on and makes a time instance of each map, at the
    middle of its interval: 2 and 4 March.

    ```sh
    if ! t.rast.algebra expression='E9 = buff_t(B, "-1 day")' basename=e9 2>&1; then
        echo "t.rast.algebra failed"
    fi
    ```

    ```text
    ERROR: Buffering map <b_1@t_rast_algebra> [2026-03-01 00:00:00, 2026-03-03
           00:00:00] by -1 day leaves no time
    t.rast.algebra failed
    ```

    ```sh
    t.rast.algebra -c expression='E10 = buff_t(B, "-1 day")' basename=e10
    t.rast.list input=E10 columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    e10_0|2026-03-02 00:00:00|None|10.0|10.0
    e10_1|2026-03-04 00:00:00|None|20.0|20.0
    ```

    Item 9: `merge()` of two equal maps read at an offset gives four maps in the
    new algebra and eight in the classic one.

    ```sh
    t.rast.algebra expression="E11 = merge(A[0], A[0])" basename=e11
    t.info -g type=strds input=E11 | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=4
    ```

    ```sh
    t.rast.algebra -c expression="E12 = merge(A[0], A[0])" basename=e12
    t.info -g type=strds input=E12 | grep "^number_of_maps="
    ```

    ```text
    number_of_maps=8
    ```

    Item 10, `tsnap()` of maps that start together: the map of `H` and the second
    map of `A` both start on 2 March, and `H` ends on 4 March. The new algebra
    snaps the map of `H` to 3 March in both expressions. The classic algebra
    does so for the first expression only; in the second it takes the map
    listed last and lets `H` keep its end on 4 March.

    ```sh
    t.rast.algebra --overwrite expression="C = tsnap(merge(A, H))" basename=c
    t.rast.list input=C order=start_time,name \
        columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-02 00:00:00|2026-03-03 00:00:00|5.0|5.0
    c_3|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_4|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = tsnap(merge(H, A))" basename=c
    t.rast.list input=C order=start_time,name \
        columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_2|2026-03-02 00:00:00|2026-03-03 00:00:00|5.0|5.0
    c_3|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_4|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra -c --overwrite expression="C = tsnap(merge(H, A))" basename=c
    t.rast.list input=C order=start_time,name \
        columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|1.0
    c_1|2026-03-02 00:00:00|2026-03-04 00:00:00|5.0|5.0
    c_2|2026-03-02 00:00:00|2026-03-03 00:00:00|2.0|2.0
    c_3|2026-03-03 00:00:00|2026-03-04 00:00:00|3.0|3.0
    c_4|2026-03-04 00:00:00|2026-03-05 00:00:00|4.0|4.0
    ```

    Item 11, integers beyond 32 bits: the new algebra keeps the constant
    3000000000 and adds the one day of each map to it. The classic algebra
    reads it as *r.mapcalc* does, with its lower 32 bits only, which is
    -1294967296.

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if(td(A) <= 0.5, A, 3000000000) + td(A)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|3000000001.0|3000000001.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|3000000001.0|3000000001.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3000000001.0|3000000001.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|3000000001.0|3000000001.0
    ```

    ```sh
    t.rast.algebra -c --overwrite \
        expression="C = if(td(A) <= 0.5, A, 3000000000) + td(A)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2026-03-01 00:00:00|2026-03-02 00:00:00|-1294967295.0|-1294967295.0
    c_1|2026-03-02 00:00:00|2026-03-03 00:00:00|-1294967295.0|-1294967295.0
    c_2|2026-03-03 00:00:00|2026-03-04 00:00:00|-1294967295.0|-1294967295.0
    c_3|2026-03-04 00:00:00|2026-03-05 00:00:00|-1294967295.0|-1294967295.0
    ```

    A selection on relative time with a time instance on the right and the
    temporal operator `r` ended with a `TypeError` in the releases before
    GRASS 8.6. The classic algebra now computes it as the new algebra does,
    while the reference implementation still ends with the `TypeError`: of the
    two maps of `flow` (hours 0 to 2 and 2 to 4, values 6 and 8), the second
    contains the time instance `pulse` at hour 3 and is selected with the time
    of the instance.

    ```sh
    r.mapcalc expression="flow_1 = 6"
    r.mapcalc expression="flow_2 = 8"
    t.create output=flow temporaltype=relative title="Flow" \
        description="Two intervals of two hours"
    t.register -i input=flow maps=flow_1,flow_2 start=0 increment=2 unit=hours
    r.mapcalc expression="pulse = 9"
    t.create output=pulses temporaltype=relative title="Pulses" \
        description="One time instance"
    t.register input=pulses maps=pulse start=3 unit=hours
    t.rast.algebra -c --overwrite \
        expression="C = flow {:,contains,r} tmap(pulse)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|3|None|8.0|8.0
    ```

### Catalog: the expressions of the original manual

<!-- example: shell-only -->

The following expressions come from the first manual of the algebra and from
the publication cited under REFERENCES. They name the datasets `A` and `B`
for other data than the examples above, so the first block creates them anew
with **--overwrite**: `A` has five monthly maps for January to May 2001 with
the values 500, 700, 1800, 900 and 1200, and `B` five monthly maps with the
values 1 to 5. The sum of `A` and `B` pairs the maps of equal time: 501, 702,
1803, 904 and 1205. The condition on the start date is true for every map, so
the first expression gives the same sums. The second form of the sum names the
relation, the temporal operator and the operator `+` in curly brackets
explicitly; it gives the same maps.

=== "Command line"

    ```sh
    i=0
    for value in 500 700 1800 900 1200; do
        i=$((i + 1))
        r.mapcalc expression="am_$i = $value"
        r.mapcalc expression="bm_$i = $i"
    done
    t.create --overwrite output=A title="Monthly maps" \
        description="Five monthly maps of 2001"
    t.register -i input=A maps=am_1,am_2,am_3,am_4,am_5 \
        start=2001-01-01 increment="1 months"
    t.create --overwrite output=B title="Monthly maps" \
        description="Five monthly maps of 2001, values 1 to 5"
    t.register -i input=B maps=bm_1,bm_2,bm_3,bm_4,bm_5 \
        start=2001-01-01 increment="1 months"
    ```

    ```sh
    t.rast.algebra --overwrite \
        expression='D = if(start_date(A) < "2005-01-01", A + B)' basename=d
    t.rast.list input=D columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    d_0|2001-01-01 00:00:00|2001-02-01 00:00:00|501.0|501.0
    d_1|2001-02-01 00:00:00|2001-03-01 00:00:00|702.0|702.0
    d_2|2001-03-01 00:00:00|2001-04-01 00:00:00|1803.0|1803.0
    d_3|2001-04-01 00:00:00|2001-05-01 00:00:00|904.0|904.0
    d_4|2001-05-01 00:00:00|2001-06-01 00:00:00|1205.0|1205.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = A + B" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2001-01-01 00:00:00|2001-02-01 00:00:00|501.0|501.0
    c_1|2001-02-01 00:00:00|2001-03-01 00:00:00|702.0|702.0
    c_2|2001-03-01 00:00:00|2001-04-01 00:00:00|1803.0|1803.0
    c_3|2001-04-01 00:00:00|2001-05-01 00:00:00|904.0|904.0
    c_4|2001-05-01 00:00:00|2001-06-01 00:00:00|1205.0|1205.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="C = A {+,equal,l} B" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2001-01-01 00:00:00|2001-02-01 00:00:00|501.0|501.0
    c_1|2001-02-01 00:00:00|2001-03-01 00:00:00|702.0|702.0
    c_2|2001-03-01 00:00:00|2001-04-01 00:00:00|1803.0|1803.0
    c_3|2001-04-01 00:00:00|2001-05-01 00:00:00|904.0|904.0
    c_4|2001-05-01 00:00:00|2001-06-01 00:00:00|1205.0|1205.0
    ```

    The next expression selects the cells of `B` where the map of `A` is
    greater than 100 and less than 1600 and lasts more than 30 days. January
    and May pass (31 days), February has 28 days, April 30 days and March a
    value above 1600, so these three maps are 0 and the others keep the values
    1 and 5. The second form names the relation between the condition and the
    then part.

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if(A > 100 && A < 1600 && td(A) > 30, B)" basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2001-01-01 00:00:00|2001-02-01 00:00:00|1.0|1.0
    c_1|2001-02-01 00:00:00|2001-03-01 00:00:00|0.0|0.0
    c_2|2001-03-01 00:00:00|2001-04-01 00:00:00|0.0|0.0
    c_3|2001-04-01 00:00:00|2001-05-01 00:00:00|0.0|0.0
    c_4|2001-05-01 00:00:00|2001-06-01 00:00:00|5.0|5.0
    ```

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if({equal}, A > 100 && A < 1600 && td(A) > 30, B)" \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2001-01-01 00:00:00|2001-02-01 00:00:00|1.0|1.0
    c_1|2001-02-01 00:00:00|2001-03-01 00:00:00|0.0|0.0
    c_2|2001-03-01 00:00:00|2001-04-01 00:00:00|0.0|0.0
    c_3|2001-04-01 00:00:00|2001-05-01 00:00:00|0.0|0.0
    c_4|2001-05-01 00:00:00|2001-06-01 00:00:00|5.0|5.0
    ```

    The recharge of the next expression needs a temperature and a
    precipitation. The datasets `Temp` and `Prec` have four monthly maps; the
    temperatures are 5, 12, 8 and 15 degrees, and the precipitation is chosen so
    that the division gives the numbers 1 to 4: the values are the number of
    seconds of the month times 1, 2, 3 and 4. Only the months with more than 10
    degrees compute the quotient (2 and 4); the others are 0. The second form
    names the relation of the condition and the temporal operator of the
    division.

    ```sh
    i=0
    for pair in "5 2678400" "12 4838400" "8 8035200" "15 10368000"; do
        i=$((i + 1))
        set -- $pair
        r.mapcalc expression="temp_$i = $1"
        r.mapcalc expression="prec_$i = $2"
    done
    t.create output=Temp title="Temperature" \
        description="Mean temperature of four months"
    t.register -i input=Temp maps=temp_1,temp_2,temp_3,temp_4 \
        start=2001-01-01 increment="1 months"
    t.create output=Prec title="Precipitation" \
        description="Precipitation of four months"
    t.register -i input=Prec maps=prec_1,prec_2,prec_3,prec_4 \
        start=2001-01-01 increment="1 months"
    ```

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if(Temp > 10.0, Prec / 3600.0 / 24.0 / td(Prec))" \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2001-01-01 00:00:00|2001-02-01 00:00:00|0.0|0.0
    c_1|2001-02-01 00:00:00|2001-03-01 00:00:00|2.0|2.0
    c_2|2001-03-01 00:00:00|2001-04-01 00:00:00|0.0|0.0
    c_3|2001-04-01 00:00:00|2001-05-01 00:00:00|4.0|4.0
    ```

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if({equal}, Temp > 10.0, Prec / 3600.0 / 24.0 {/,equal,l} td(Prec))" \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2001-01-01 00:00:00|2001-02-01 00:00:00|0.0|0.0
    c_1|2001-02-01 00:00:00|2001-03-01 00:00:00|2.0|2.0
    c_2|2001-03-01 00:00:00|2001-04-01 00:00:00|0.0|0.0
    c_3|2001-04-01 00:00:00|2001-05-01 00:00:00|4.0|4.0
    ```

    The mean of the maps of `A` within a longer interval needs a dataset `B`
    with such intervals. The block replaces `B` by two maps of three months
    each, with the values 100 and 200: the first lasts from January to March
    and contains three maps of `A` (500, 700 and 1800, mean 1000), the second
    lasts from April to June and contains two maps (900 and 1200, mean 1050).
    The sum of the contained maps minus the map of `B` is divided by their
    number, and the result has the times of `B`. The value of `B` cancels out.

    ```sh
    r.mapcalc expression="q_1 = 100"
    r.mapcalc expression="q_2 = 200"
    t.create --overwrite output=B title="Quarters" \
        description="Two maps of three months"
    t.register -i input=B maps=q_1,q_2 start=2001-01-01 increment="3 months"
    ```

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if(B {#,contains} A > 1, (B {+,contains,l} A - B) / (B {#,contains} A), A)" \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2001-01-01 00:00:00|2001-04-01 00:00:00|1000.0|1000.0
    c_1|2001-04-01 00:00:00|2001-07-01 00:00:00|1050.0|1050.0
    ```

    ```sh
    t.rast.algebra --overwrite \
        expression="C = if({equal}, B {#,contains} A > 1, (B {+,contains,l} A {-,equal,l} B) {/,equal,l} (B {#,contains} A), A)" \
        basename=c
    t.rast.list input=C columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2001-01-01 00:00:00|2001-04-01 00:00:00|1000.0|1000.0
    c_1|2001-04-01 00:00:00|2001-07-01 00:00:00|1050.0|1050.0
    ```

    The last expression computes the day of the year for the maps where three
    consecutive months are above 0: the condition reads the map, its
    predecessor and the one before it, and `start_doy(A, -1)` gives the day of
    the year of the start of the predecessor. The first two maps have no
    complete neighbourhood and are left out, so the result has three maps, for
    March to May, with the values 32, 60 and 91, the start days of February,
    March and April. The new algebra also computes a map for February, but
    `A[-2]` has no map there, so it is null everywhere and not registered; the
    registered maps take the numbers from 0, `doy_0` to `doy_2`. With **-n**
    the second block registers it as `doyn_0`, without minimum and maximum, and
    the others follow as `doyn_1` to `doyn_3`. The classic algebra computes no
    map for February and numbers the three maps `doyc_0` to `doyc_2`. The
    result is named `B`, which replaces the dataset of the block before.

    ```sh
    t.rast.algebra --overwrite \
        expression="B = if(A > 0.0 && A[-1] > 0.0 && A[-2] > 0.0, start_doy(A, -1), 0)" \
        basename=doy
    t.rast.list input=B columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    doy_0|2001-03-01 00:00:00|2001-04-01 00:00:00|32.0|32.0
    doy_1|2001-04-01 00:00:00|2001-05-01 00:00:00|60.0|60.0
    doy_2|2001-05-01 00:00:00|2001-06-01 00:00:00|91.0|91.0
    ```

    ```sh
    t.rast.algebra -n --overwrite \
        expression="B = if(A > 0.0 && A[-1] > 0.0 && A[-2] > 0.0, start_doy(A, -1), 0)" \
        basename=doyn
    t.rast.list input=B columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    doyn_0|2001-02-01 00:00:00|2001-03-01 00:00:00|None|None
    doyn_1|2001-03-01 00:00:00|2001-04-01 00:00:00|32.0|32.0
    doyn_2|2001-04-01 00:00:00|2001-05-01 00:00:00|60.0|60.0
    doyn_3|2001-05-01 00:00:00|2001-06-01 00:00:00|91.0|91.0
    ```

    ```sh
    t.rast.algebra -c --overwrite \
        expression="B = if(A > 0.0 && A[-1] > 0.0 && A[-2] > 0.0, start_doy(A, -1), 0)" \
        basename=doyc
    t.rast.list input=B columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    doyc_0|2001-03-01 00:00:00|2001-04-01 00:00:00|32.0|32.0
    doyc_1|2001-04-01 00:00:00|2001-05-01 00:00:00|60.0|60.0
    doyc_2|2001-05-01 00:00:00|2001-06-01 00:00:00|91.0|91.0
    ```

    Figure A3 of the publication needs the else rule described in the NOTES: `A`
    has maps from day 1 to 3, 3 to 5 and 5 to 7 of January 2001, and `B` has
    daily maps from day 1 to 10. The expression gives the first two maps of `A`
    and the maps of `B` from day 5 on.

    ```sh
    r.mapcalc expression="fa_1 = 1"
    r.mapcalc expression="fa_2 = 2"
    r.mapcalc expression="fa_3 = 3"
    t.create --overwrite output=A title="Figure A3" \
        description="Maps of two days"
    t.register -i input=A maps=fa_1,fa_2,fa_3 start=2001-01-01 \
        increment="2 days"
    for day in 1 2 3 4 5 6 7 8 9 10; do
        r.mapcalc expression="fb_$day = 10 + $day"
    done
    t.create --overwrite output=B title="Figure A3" \
        description="Ten daily maps"
    t.register -i input=B maps=fb_1,fb_2,fb_3,fb_4,fb_5,fb_6,fb_7,fb_8,fb_9,fb_10 \
        start=2001-01-01 increment="1 day"
    ```

    ```sh
    t.rast.algebra --overwrite \
        expression='C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)' \
        basename=c
    t.rast.list input=C order=start_time,name \
        columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    c_0|2001-01-01 00:00:00|2001-01-03 00:00:00|1.0|1.0
    c_1|2001-01-03 00:00:00|2001-01-05 00:00:00|2.0|2.0
    c_2|2001-01-05 00:00:00|2001-01-06 00:00:00|15.0|15.0
    c_3|2001-01-06 00:00:00|2001-01-07 00:00:00|16.0|16.0
    c_4|2001-01-07 00:00:00|2001-01-08 00:00:00|17.0|17.0
    c_5|2001-01-08 00:00:00|2001-01-09 00:00:00|18.0|18.0
    c_6|2001-01-09 00:00:00|2001-01-10 00:00:00|19.0|19.0
    c_7|2001-01-10 00:00:00|2001-01-11 00:00:00|20.0|20.0
    ```

### Catalog: expressions of the publication

<!-- example: shell-only -->

The expressions of the publication cited under REFERENCES (Gebbert, Leppelt
and Pebesma, 2019) follow as they are printed there, on small data that the
first block creates anew, replacing the datasets with the same names above.
`A` and `F` have four monthly maps from January to April 2001 (the values 1.5,
2.5, 3.5, 4.5 and 5, 6, 7, 8), `G` three from February (10, 20, 30), `B` two
maps of a month that start on the 15th of January and February (10 and 20),
`E` three daily maps from 5 January (1.5, 2.5, 3.5), `NIR` and `RED` three
daily maps from 1 January (8.5, 9.5, 10.5 and 2.5, 3.5, 4.5), `H` six daily
maps from 10 January (1.5 to 6.5), and the plain map `L` has the value 0.5.
The values are floating point numbers, because *r.mapcalc* divides whole
numbers as whole numbers. The hydrothermal coefficient computes with
generated monthly maps of 2020, which a block of their own creates. Every
block names its result `PUB`, which replaces the one before.

=== "Command line"

    ```sh
    series() {
        name=$1; start=$2; step=$3; shift 3
        maps=""; i=0
        for value in "$@"; do
            i=$((i + 1))
            r.mapcalc --overwrite expression="pub${name}_$i = $value"
            maps="$maps,pub${name}_$i"
        done
        t.create --overwrite output=$name title="Publication $name" \
            description="Data for the expressions of the publication"
        t.register -i input=$name maps=${maps#,} start=$start increment="$step"
    }
    series A 2001-01-01 "1 months" 1.5 2.5 3.5 4.5
    series F 2001-01-01 "1 months" 5 6 7 8
    series G 2001-02-01 "1 months" 10 20 30
    series B 2001-01-15 "1 months" 10 20
    series E 2001-01-05 "1 days" 1.5 2.5 3.5
    series NIR 2001-01-01 "1 days" 8.5 9.5 10.5
    series RED 2001-01-01 "1 days" 2.5 3.5 4.5
    series H 2001-01-10 "1 days" 1.5 2.5 3.5 4.5 5.5 6.5
    r.mapcalc --overwrite expression="L = 0.5"
    ```

    The first expression is the NDVI of Landsat scenes, written with the
    names of the bands: the maps of equal time are paired, and the first day
    gives `(8.5 - 2.5) / (8.5 + 2.5)`, which is 6 / 11.

    ```sh
    t.rast.algebra --overwrite expression="PUB = (NIR - RED) / (NIR + RED)" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-01-02 00:00:00|0.5454545454545454|0.5454545454545454
    pub_1|2001-01-02 00:00:00|2001-01-03 00:00:00|0.46153846153846156|0.46153846153846156
    pub_2|2001-01-03 00:00:00|2001-01-04 00:00:00|0.4|0.4
    ```

    The Sentinel-2 form names the relations `equal|equivalent` in every
    operator and needs **-s** in the publication; the maps have the same extent,
    so the result is the same as before.

    ```sh
    t.rast.algebra -s --overwrite expression="PUB = (NIR {-,equal|equivalent,l} RED) {/,equal|equivalent,l} (NIR {+,equal|equivalent,l} RED)" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-01-02 00:00:00|0.5454545454545454|0.5454545454545454
    pub_1|2001-01-02 00:00:00|2001-01-03 00:00:00|0.46153846153846156|0.46153846153846156
    pub_2|2001-01-03 00:00:00|2001-01-04 00:00:00|0.4|0.4
    ```

    The hydrothermal coefficient divides the precipitation of the warm days of
    a period by a tenth of the sum of their temperatures; the publication
    sums daily maps. Here the maps are generated monthly maps of 2020 in North
    Carolina, not measurements. `T` has the monthly mean air temperature in
    degrees Celsius, rounded to 0.1. `precipitation_monthly` has monthly
    precipitation sums in mm, interpolated from the climate normals of the
    stations in `precip_30ynormals` and multiplied with an assumed factor for
    each month. `P` is the mean daily precipitation of each month in mm per
    day, the monthly sum divided by the days of the month, `td()`: like `T`,
    which stands for the mean of every day of its month, it stands for a day,
    so that the ratio keeps the scale of daily sums. The list shows the first
    quarter, where January has 94 to 249 mm in 31 days. `DM` has the
    four quarters of 2020 with the value 0, so that only the maps they contain
    make up the sums.

    ```sh
    for month in $(seq 12); do
        echo "temperature_monthly_2020_$(printf %02d $month) = round((16.5" \
            "+ 10.5 * cos(30 * ($month - 7.2)) - 0.0065 * elev_state_500m" \
            "- 0.00001 * (y() - 160000)) * 10) / 10.0"
    done | r.mapcalc file=-
    t.create output=T title="Air temperature" \
        description="Monthly mean air temperature 2020 in degree Celsius"
    t.register -i input=T \
        maps=$(g.list type=raster pattern="temperature_monthly_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    month=1
    for entry in jan:1.2 feb:1.7 mar:0.9 apr:1.3 may:1.6 jun:0.9 \
        jul:1.1 aug:1.5 sep:0.8 oct:1.0 nov:1.6 dec:0.9; do
        name=$(printf %02d $month)
        v.surf.idw input=precip_30ynormals column=${entry%:*} \
            output=precipitation_normal_$name npoints=12 power=2
        r.mapcalc expression="precipitation_monthly_2020_$name = if(isnull(elev_state_500m), null(), round(${entry#*:} * precipitation_normal_$name))"
        month=$((month + 1))
    done
    t.create output=precipitation_monthly title="Precipitation" \
        description="Monthly precipitation sum 2020 in mm"
    t.register -i input=precipitation_monthly \
        maps=$(g.list type=raster pattern="precipitation_monthly_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    t.rast.algebra --overwrite \
        expression="P = precipitation_monthly * 1.0 / td(precipitation_monthly)" \
        basename=precipitation_rate suffix=gran
    for quarter in 1 2 3 4; do
        r.mapcalc expression="quarter_2020_$quarter = 0"
    done
    t.create output=DM title="Quarters" \
        description="The four quarters of 2020"
    t.register -i input=DM \
        maps=quarter_2020_1,quarter_2020_2,quarter_2020_3,quarter_2020_4 \
        start=2020-01-01 increment="3 months"
    t.rast.list input=P columns=name,start_time,min,max where="start_time < '2020-04-01'"
    ```

    ```text
    name|start_time|min|max
    precipitation_rate_2020_01|2020-01-01 00:00:00|3.032258064516129|8.03225806451613
    precipitation_rate_2020_02|2020-02-01 00:00:00|4.586206896551724|10.655172413793103
    precipitation_rate_2020_03|2020-03-01 00:00:00|2.838709677419355|6.838709677419355
    ```

    The sums run over the three months of each quarter, and a month counts
    only where its mean temperature reaches 10 degrees. Where no month of a
    quarter does, both sums are 0, and the quotient 0 / 0 leaves the cell
    null.

    ```sh
    t.rast.algebra --overwrite expression="PUB = (DM {+,contains,l} if(T >= 10.0, P, 0.0)) / (DM {+,contains,l} if(T >= 10.0, T / 10.0, 0.0))" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2020-01-01 00:00:00|2020-04-01 00:00:00|2.619244554728426|3.577131906739061
    pub_1|2020-04-01 00:00:00|2020-07-01 00:00:00|1.7792887764424767|5.5561933187923325
    pub_2|2020-07-01 00:00:00|2020-10-01 00:00:00|1.3690615128456503|4.122812780588222
    pub_3|2020-10-01 00:00:00|2021-01-01 00:00:00|1.2582932967284375|5.750350631136045
    ```

    The hash operator with the spelling `equals`: the sum of the three maps of
    `E` that lie in the first map of `A` and the map of `A`, divided by their
    number. The result is `(1.5 + 1.5 + 2.5 + 3.5) / 3`.

    ```sh
    t.rast.algebra --overwrite expression="PUB = (A {+,contains,l} E) {/,equals,l} (A {#,contains,l} E)" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-02-01 00:00:00|3.0|3.0
    ```

    A list of relations. `E` lies during the first map of `A`, so each map of
    `E` is added to that map: 3, 4 and 5.

    ```sh
    t.rast.algebra --overwrite expression="PUB = E {+,equals|during|equivalent,l} A" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-05 00:00:00|2001-01-06 00:00:00|3.0|3.0
    pub_1|2001-01-06 00:00:00|2001-01-07 00:00:00|4.0|4.0
    pub_2|2001-01-07 00:00:00|2001-01-08 00:00:00|5.0|5.0
    ```

    The selection of the maps of `E` that lie during `A` keeps the values of
    `E`.

    ```sh
    t.rast.algebra --overwrite expression="PUB = E {:,during,l} A" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-05 00:00:00|2001-01-06 00:00:00|1.5|1.5
    pub_1|2001-01-06 00:00:00|2001-01-07 00:00:00|2.5|2.5
    pub_2|2001-01-07 00:00:00|2001-01-08 00:00:00|3.5|3.5
    ```

    The inverse selection and the selection with `contains` are read from
    left to right: `A !: B` leaves all four maps of `A`, because none is equal
    to a map of `B`, and the maps that contain a map of `E` remain, which is the
    first map only.

    ```sh
    t.rast.algebra --overwrite expression="PUB = A !: B {:,contains,l} E" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-02-01 00:00:00|1.5|1.5
    ```

    `A` contains `E` and the other way round: `1.5 + 1.5 + 2.5 + 3.5` is 9 for
    the first map of `A`, and each map of `E` plus the map of `A` is 3, 4 and 5.

    ```sh
    t.rast.algebra --overwrite expression="PUB = A {+,contains,l} E" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-02-01 00:00:00|9.0|9.0
    ```

    ```sh
    t.rast.algebra --overwrite expression="PUB = E {+,during,l} A" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-05 00:00:00|2001-01-06 00:00:00|3.0|3.0
    pub_1|2001-01-06 00:00:00|2001-01-07 00:00:00|4.0|4.0
    pub_2|2001-01-07 00:00:00|2001-01-08 00:00:00|5.0|5.0
    ```

    The disjoint union relates each map of `A` to the maps of `G` that touch
    it: the map before and after it. The time of a result is the union of the
    times without the gap between them.

    ```sh
    t.rast.algebra --overwrite expression="PUB = A {+,follows|precedes,d} G" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-03-01 00:00:00|11.5|11.5
    pub_1|2001-02-01 00:00:00|2001-04-01 00:00:00|22.5|22.5
    pub_2|2001-02-01 00:00:00|2001-05-01 00:00:00|43.5|43.5
    pub_3|2001-03-01 00:00:00|2001-05-01 00:00:00|24.5|24.5
    ```

    The intersection as temporal operator: the first map of `B` overlaps the
    first map of `A` from 15 to 31 January, so the result is `1.5 - 10` for
    that time, and `2.5 - 20` from 15 to 28 February.

    ```sh
    t.rast.algebra --overwrite expression="PUB = A {-,overlaps,i} B" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-15 00:00:00|2001-02-01 00:00:00|-8.5|-8.5
    pub_1|2001-02-15 00:00:00|2001-03-01 00:00:00|-17.5|-17.5
    ```

    The spatial name `equivalent` beside `equals` needs no **-s**; the maps of
    `A` and `F` have the same extent, so each pair is added: 6.5, 8.5, 10.5 and
    12.5.

    ```sh
    t.rast.algebra --overwrite expression="PUB = A {+,equals|equivalent,l} F" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-02-01 00:00:00|6.5|6.5
    pub_1|2001-02-01 00:00:00|2001-03-01 00:00:00|8.5|8.5
    pub_2|2001-03-01 00:00:00|2001-04-01 00:00:00|10.5|10.5
    pub_3|2001-04-01 00:00:00|2001-05-01 00:00:00|12.5|12.5
    ```

    The temporal buffer widens the maps by one month at both ends before they
    are related; the union of two related maps gives the time of the result.

    ```sh
    t.rast.algebra --overwrite expression='PUB = buff_t(A, "1 month") {+,equals|overlaps|overlapped,u} buff_t(B, "1 month")' basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2000-12-01 00:00:00|2001-04-15 00:00:00|31.5|31.5
    pub_1|2000-12-15 00:00:00|2001-04-15 00:00:00|32.5|32.5
    pub_2|2000-12-15 00:00:00|2001-05-01 00:00:00|33.5|33.5
    pub_3|2000-12-15 00:00:00|2001-06-01 00:00:00|34.5|34.5
    ```

    The moving average over five maps uses the neighbourhood modifier. Only
    the third and the fourth of the six daily maps of `H` have two neighbours on
    each side, so the result has two maps, with the means 3.5 and 4.5.

    ```sh
    t.rast.algebra --overwrite expression="PUB = (H[-2] + H[-1] + H + H[1] + H[2]) / 5.0" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-12 00:00:00|2001-01-13 00:00:00|3.5|3.5
    pub_1|2001-01-13 00:00:00|2001-01-14 00:00:00|4.5|4.5
    ```

    The gradient divides the sum of a map and its predecessor by the duration
    of the map in days: `(1.5 + 2.5) / 28` for February, which has 28 days.

    ```sh
    t.rast.algebra --overwrite expression="PUB = (A[-1] + A) / td(A)" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-02-01 00:00:00|2001-03-01 00:00:00|0.14285714285714285|0.14285714285714285
    pub_1|2001-03-01 00:00:00|2001-04-01 00:00:00|0.1935483870967742|0.1935483870967742
    pub_2|2001-04-01 00:00:00|2001-05-01 00:00:00|0.26666666666666666|0.26666666666666666
    ```

    A logical operator with the relation `equals`: the map of `A` is kept where
    it is greater than 1 and the map of `F` of equal time is greater than 6, so
    the first two maps are 0 and the others keep their values.

    ```sh
    t.rast.algebra --overwrite expression="PUB = if(A > 1 {&&,equals,&,l} F > 6, A)" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-02-01 00:00:00|0.0|0.0
    pub_1|2001-02-01 00:00:00|2001-03-01 00:00:00|0.0|0.0
    pub_2|2001-03-01 00:00:00|2001-04-01 00:00:00|3.5|3.5
    pub_3|2001-04-01 00:00:00|2001-05-01 00:00:00|4.5|4.5
    ```

    The SAVI uses a plain map without time stamp, `map(L)`, with the value 0.5:
    `((8.5 - 2.5) * (0.5 + 1)) / (8.5 + 2.5 + 0.5)` is 9 / 11.5.

    ```sh
    t.rast.algebra --overwrite expression="PUB = ((NIR - RED) * (map(L) + 1)) / (NIR + RED + map(L))" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-01-02 00:00:00|0.782608695652174|0.782608695652174
    pub_1|2001-01-02 00:00:00|2001-01-03 00:00:00|0.6666666666666666|0.6666666666666666
    pub_2|2001-01-03 00:00:00|2001-01-04 00:00:00|0.5806451612903226|0.5806451612903226
    ```

    A logical operator with the relation `contains`: only the first map of
    `A` contains maps of `E`, and all are greater than 1, so the result is the
    first map of `A`.

    ```sh
    t.rast.algebra --overwrite expression="PUB = if(A > 1 {&&,contains,&,l} E > 1, A)" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-02-01 00:00:00|1.5|1.5
    ```

    Some printed forms are misprints. Typed as printed, they are refused or
    compute something other than the figure shows; the readable forms follow.

    The caption of Figure A7 writes `preceedes`, which is a syntax error; the
    drawing and the algebra name the relation `precedes`, as in
    `A {+,follows|precedes,d} G` above. The publication writes the relation
    `equal` as `equals`; the algebra reads `equals` as another name of
    `equal`.

    Figure A8 writes `{-,overlaps,i}`, but its left map, 4 to 9 January,
    starts inside the right map, 1 to 6 January: the left map is overlapped
    by the right one. With the maps of the figure the printed `overlaps`
    relates no map, and the expression produces no map. The relation
    `overlapped` gives the drawn result: the intersection, 4 to 6 January,
    with the value `1 - 1`.

    ```sh
    r.mapcalc --overwrite expression="puba8a = 1"
    r.mapcalc --overwrite expression="puba8b = 1"
    t.create --overwrite output=A8A title="Figure A8, A" \
        description="The left dataset of Figure A8 of the publication"
    t.register input=A8A maps=puba8a start=2001-01-04 end=2001-01-09
    t.create --overwrite output=A8B title="Figure A8, B" \
        description="The right dataset of Figure A8 of the publication"
    t.register input=A8B maps=puba8b start=2001-01-01 end=2001-01-06
    t.rast.algebra --overwrite expression="PUB = A8A {-,overlapped,i} A8B" basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-04 00:00:00|2001-01-06 00:00:00|0.0|0.0
    ```

    Figures A2 and A3 compare `start_time()` with a date and set the date in
    typographic quotes, as Appendix C.3 sets the size of the temporal buffer.
    Copied from the publication, these quotes are a syntax error; the algebra
    reads a text in plain double or single quotes. The releases before GRASS
    8.6 read single quotes around the size of `buff_t()`, but not around a
    date. `start_time()` is the time of day, and a date compared with it
    counts as midnight, so it does not select by the date: for maps that
    start at midnight, `start_time(A) >= "2001-03-01"` holds for every map,
    and the result is `A` throughout.

    ```sh
    t.rast.algebra --overwrite expression='PUB = if(start_time(A) >= "2001-03-01", A, F)' basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-02-01 00:00:00|1.5|1.5
    pub_1|2001-02-01 00:00:00|2001-03-01 00:00:00|2.5|2.5
    pub_2|2001-03-01 00:00:00|2001-04-01 00:00:00|3.5|3.5
    pub_3|2001-04-01 00:00:00|2001-05-01 00:00:00|4.5|4.5
    ```

    The comparison of the figures needs `start_date()`: the maps of `A` from
    March on, and the maps of `F` before.

    ```sh
    t.rast.algebra --overwrite expression='PUB = if(start_date(A) >= "2001-03-01", A, F)' basename=pub
    t.rast.list input=PUB columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    pub_0|2001-01-01 00:00:00|2001-02-01 00:00:00|5.0|5.0
    pub_1|2001-02-01 00:00:00|2001-03-01 00:00:00|6.0|6.0
    pub_2|2001-03-01 00:00:00|2001-04-01 00:00:00|3.5|3.5
    pub_3|2001-04-01 00:00:00|2001-05-01 00:00:00|4.5|4.5
    ```

    The tables of Appendix B have three more misprints. `start_time()` gives
    the time as `HH:MM:SS`, not `HH::MM:SS`; `end_day()` is the day of month
    of the end time, not of the start time; and `round()`, listed among the
    spatial functions, is no function of the algebra in any release.

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.mapset](g.mapset.md), [g.mapsets](g.mapsets.md), [g.region](g.region.md),
[r.mapcalc](r.mapcalc.md), [t.create](t.create.md), [t.info](t.info.md),
[t.list](t.list.md), [t.rast.colors](t.rast.colors.md),
[t.rast.list](t.rast.list.md), [t.rast.mapcalc](t.rast.mapcalc.md),
[t.rast3d.algebra](t.rast3d.algebra.md), [t.register](t.register.md),
[t.select](t.select.md), [t.vect.algebra](t.vect.algebra.md),
[changes in GRASS 8.6](temporalchanges.md),
[temporal data processing](temporalintro.md)*

[Temporal data processing
Wiki](https://grasswiki.osgeo.org/wiki/Temporal_data_processing)

## REFERENCES

The use of this module requires the following software to be installed:
[PLY(Python-Lex-Yacc)](https://www.dabeaz.com/ply/)

```sh
# Ubuntu/Debian
sudo apt-get install python3-ply

# Fedora
sudo dnf install python3-ply

# MS-Windows (OSGeo4W: requires "python3-pip" package to be installed)
python3-pip install ply
```

Related publications:

- Gebbert, S., Pebesma, E. 2014. *TGRASS: A temporal GIS for field based
    environmental modeling*. Environmental Modelling & Software 53, 1-12
    ([DOI](https://doi.org/10.1016/j.envsoft.2013.11.001)) - [preprint
    PDF](http://ifgi.uni-muenster.de/~epebe_01/tgrass.pdf)
- Gebbert, S., Pebesma, E. 2017. *The GRASS GIS temporal framework*.
    International Journal of Geographical Information Science 31,
    1273-1292 ([DOI](https://doi.org/10.1080/13658816.2017.1306862))
- Gebbert, S., Leppelt, T., Pebesma, E., 2019. *A topology based
    spatio-temporal map algebra for big data analysis*. Data 4, 86.
    ([DOI](https://doi.org/10.3390/data4020086))

## AUTHORS

Thomas Leppelt, Sören Gebbert, Thünen Institute of Climate-Smart
Agriculture
