## DESCRIPTION

*t.rast.algebra* performs temporal and spatial map algebra operations on
space time raster datasets (STRDS) using the temporal raster algebra.

The module expects an **expression** as input parameter in the following
form:

```sh
"result = expression"
```

The statement structure is similar to that of [r.mapcalc](r.mapcalc.md).
In this statement, **result** represents the name of the space time
raster dataset (STRDS) that will contain the result of the calculation
that is given as **expression** on the right side of the equality sign.
These expressions can be any valid or nested combination of temporal
operations and spatial overlay or buffer functions that are provided by
the temporal algebra.

The temporal raster algebra works only with space time raster datasets
(STRDS). The algebra provides methods for map selection based on their
temporal relations. It is also possible to temporally shift maps, to
create temporal buffer and to snap time instances to create a valid
temporal topology. Furthermore, expressions can be nested and evaluated
in conditional statements (if, else statements). Within if-statements,
the algebra provides temporal variables like start time, end time, day
of year, time differences or number of maps per time interval to build
up conditions.  
In addition the algebra provides a subset of the spatial operations from
[r.mapcalc](r.mapcalc.md). All these operations can be assigned to STRDS
or to the map lists resulting of operations between STRDS.

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
this spatial relation in addition to the temporal one.

The expression option must be passed as **quoted** expression, for
example:

```sh
t.rast.algebra expression="C = A + B" basename=result
```

Where **C** is the new space time raster dataset that will contain maps
with the basename "result" and a numerical suffix separated by an
underscore that represent the sum of maps from the STRDS **A** and
temporally equal maps (i.e., maps with equal temporal topology relation)
from the STRDS **B**.

The map **basename** for the result STRDS must always be specified.

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
the new algebra and **-c** read both names. The previous implementation
refuses `equals` with a syntax error.

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

start_time(A)            Start time as HH::MM:SS
start_date(A)            Start date as yyyy-mm-DD
start_datetime(A)        Start datetime as yyyy-mm-DD HH:MM:SS
end_time(A)              End time as HH:MM:SS
end_date(A)              End date as yyyy-mm-DD
end_datetime(A)          End datetime as  yyyy-mm-DD HH:MM

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
end_day(A)               Day of month from the start time [1 - 31]
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

### Core and classic algebra

Since GRASS 8.6, *t.rast.algebra* computes its expressions with the
functions of the Python package `grass.temporal.algebra`. The previous
implementation stays available as the classic algebra, so that published
results remain reproducible. The classic algebra is a set of rules of the
same functions: it reads the syntax of the previous implementation and
applies its rules for relations, order and results. The flag **-c** selects
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

5. **if without else.** An `if` without else gives null where a condition
   on map values is false; the classic algebra gives 0 there, like the
   `if()` of *r.mapcalc* with two arguments. A map that is false everywhere
   is not registered unless **-n** is set. This expression registers the
   maps of value 3 and 4, with **-n** also the first two maps as null maps;
   the classic algebra registers four maps, the first two with the value 0:

   ```sh
   C = if(A > 2, A)
   ```

6. **td() of a time instance** is null instead of an error, so a condition
   on it is neither true nor false. This expression gives no map; the
   classic algebra stops with an error:

   ```sh
   C = if(td(I) > 0, I)
   ```

   A temporal variable that a map does not have, such as `end_doy()` of a
   time instance or the calendar values of relative time, is an error in
   both algebras.

7. **Spatial relations need -s.** A spatial relation in an operator, such
   as `{+,equal|overlap}`, needs the flag **-s**; without it, the algebra
   stops with an error. The classic algebra gives an empty result.

8. **More syntax.** Comparisons, temporal functions and the minus sign may
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

9. **Maps without time stamp in arithmetic.** An expression of maps
   without time stamp, such as `map(L) + 1`, can be combined with space
   time datasets. The soil-adjusted vegetation index of Gebbert, Leppelt
   and Pebesma (2019) is a syntax error in the classic algebra:

   ```sh
   C = ((NIR - RED) * (map(L) + 1)) / (NIR + RED + map(L))
   ```

10. **Intersection with several related maps.** With the temporal
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

11. **Negative buffer.** A negative size in `buff_t()` shrinks the maps
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

12. **merge() of maps read at an offset.** The new algebra takes two maps
    with equal content and time stamps as one map. The classic algebra, as
    the previous implementation, makes a new map for each map read with a
    temporal neighbourhood modifier and for each value of a temporal
    function with an offset, and `merge()` keeps such a map next to an
    equal one. The first two expressions give four maps in the new algebra
    and eight in the classic algebra, the third three and six:

    ```sh
    C = merge(A[0], A[0])
    C = merge(A + 1, A[0] + 1)
    C = merge(start_day(A, 1), start_day(A, 1))
    ```

In Python, both algebras raise `SyntaxError` for an expression they cannot
read. For one they cannot compute, the new algebra raises `ValueError` or
`TypeError`, where the classic algebra raises `FatalError`. Both raise
`FatalError` for a missing dataset or map and, without overwrite, for an
existing result dataset or map; a dry run of the classic algebra stops only
at an existing result map. The tool stops with the error message in both
algebras.

Two corrections apply to both algebras, so **-c** gives the rules of the
previous algebra, not the results of a particular release. First,
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

The classic algebra gives the results of the previous implementation, with
the exceptions below. In these cases the previous implementation
computed wrongly, ended in an error that had no reason, or reported the
wrong error. **-c** now gives the result described here. The new algebra
never computed these cases wrongly; only the item on infinite values
concerned the library and with it both algebras. Results of earlier GRASS
versions that used one of these forms need a new run. The examples use the
datasets of the list above and, in addition, N with daily maps of the values
11 to 14 and RT with maps of relative time.

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

4. **merge() and the data type.** The data types of the maps are not
   compared, so a dataset may hold integer and floating point maps. Earlier
   versions refused `merge()` of a dataset with a single map from `map()` or
   `tmap()` with the error that the datasets must have the same data type.
   The first expression gives the four maps of A and the single map, the
   second the maps of A and the floating point maps computed from them:

   ```sh
   C = merge(A, tmap(singletmap))
   C = merge(A, A * 1.5)
   ```

5. **Time constants with offset.** A temporal function with an offset
   needs a map with the time value it returns. On a map without it, such as
   `end_month()` of a time instance or `start_month()` of relative time, the
   expression stops with an error that says the function requires absolute
   time, as the same function in a condition does. Earlier versions wrote
   `None` into the *r.mapcalc* expression, which failed when the maps were
   computed:

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

8. **td() of a counted map.** `td()` of a map counted by the hash operator
   gave the count instead of the duration, as an operand and in a
   comparison (corrected 17 October 2026). The datasets A and N have daily
   maps and `A # merge(A, N)` counts 2 for each map of A. The expression
   added 2 to the maps of N where it now adds the one day of their
   duration; a condition such as `td(A # merge(A, N)) > 1.5` was true and
   is false now. The duration of a map that is not counted did not change:

   ```sh
   C = N + td(A # merge(A, N))
   ```

9. **A map read at an offset as a truth value.** A time function of a
   map read at an offset in time or in cells, such as `end_year(A[1])`,
   joined with `&&` or `||` to a condition on cells is a truth value, like
   the time function of any map (corrected 17 October 2026). The previous
   implementation wrote the map itself as the operand, so that a map with
   a value other than 0 counted as true whatever the time function said.
   With the values 1 to 4 in A, the expression gave 1, 2 and 3 and now
   gives 0, 0 and 3, because `end_year(A[1]) == 1` is false. The cell
   value of a map read at an offset, as in `A[1] > 1 && A`, did not
   change:

   ```sh
   C = if(end_year(A[1]) == 1 || A > 2, A)
   ```

#### Differences from the previous implementation

Besides the corrections, **-c** differs from the previous implementation
in the following points. Only the items on lists of absolute and relative
time and on the relation `equals` change the outcome of an expression; the
others concern messages, output and the class of an error.

- **Message texts.** The texts of warnings and errors are those of the
  new algebra. A `merge()` that meets maps identical in content and time
  warns "merge() dropped 4 duplicate map(s)" for `C = merge(A, A)` instead
  of "merge() keeps 4 maps of both operands only once". A refused increment
  of `tshift()` reports that the text cannot be read as a time step, for
  `tshift(A, "1 DAY")` instead of "cannot shift absolute time by".
- **Debug output.** In Python, with `debug=True`, the classic algebra
  prints each module call as a command line like the new algebra, for
  example `r.mapcalc expression=q_0=(a1@PERMANENT + 1) nprocs=1`. The
  previous implementation printed the *r.mapcalc* commands and the
  resulting statement.
- **Order of the errors.** Both implementations reject an invalid
  expression, but they can report another class of error. The classic
  algebra reads the whole expression before it computes. An expression with
  a syntax error is therefore a syntax error, where the previous
  implementation could stop with the error of a computation before it
  reached the syntax error. The classic algebra also reads a dataset that is
  an argument of a function before the arguments after it. A dataset of
  another temporal type stops it there (`FatalError`), where the previous
  implementation reads such a dataset last and can stop with an error of a
  later argument, for example a `SyntaxError` of `buff_t()` in
  `if(end_year(A) > 3, RT, buff_t(A, 2))`. In this expression the dataset
  `nosuch` does not exist and a bracket is too many; the previous
  implementation reported the missing dataset (`FatalError`):

  ```sh
  C = nosuch + A )
  ```

- **Existing result.** In Python, without `tgis.init(raise_fatal_error=True)`,
  the previous implementation exits the process with `SystemExit` for an
  existing result map. The classic algebra raises `FatalError`, as the new
  algebra does. The tools are not affected, because they initialise the
  library with `raise_fatal_error=True`.
- **Lists of absolute and relative time.** A relation over a list that
  mixes maps of absolute and of relative time, made with `merge()` and
  `tmap()`, stopped the previous implementation with a `TypeError` while it
  related the maps. The classic algebra does not reproduce this crash: maps
  of the two types relate to nothing, so this expression selects the maps
  of `RT` as `RT : RT` does:

  ```sh
  C = merge(tmap(sinst), RT) : RT
  ```

- **The relation equals.** The previous implementation refuses the
  spelling `equals` of the paper with a syntax error. The classic algebra
  reads it as `equal`, so this expression gives the same maps as
  `C = A {+,equal,l} B`:

  ```sh
  C = A {+,equals,l} B
  ```

### Granularity algebra

With the flag **-g**, each space time dataset of the expression is first
sampled with the common granularity of all datasets of the expression. The
granules of a dataset follow each other from the start of its first map
until they cover the end of its last map, so the last granule may reach
past it, for example a granule of two days over a map of three days. If the
dataset has time instances, one more granule follows. Each granule takes
one map of the dataset, with the time stamp of the granule:

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

Single maps given with `map()` or `tmap()` are not sampled. The differences
between the two algebras listed under "Core and classic algebra" apply with
**-g** as well, for example item 5, an `if` without else.

With four daily maps in A with the values 1 to 4 and two maps of two days
in B with the values 5 and 6, both starting on the same day,
`C = A + B` gives no map without **-g** and four daily maps with the
values 6, 7, 9 and 10 with **-g**.

## EXAMPLES

### Computation of NDVI

```sh
# Sentinel-2 bands are stored separately in two STDRS "S2_b4" and "S2_b8"
g.region raster=sentinel2_B04_10m -p
t.rast.list S2_b4
t.rast.list S2_b8
t.rast.algebra basename=ndvi expression="ndvi = float(S2_b8 - S2_b4) / ( S2_b8 + S2_b4 )"
t.rast.colors input=ndvi color=ndvi
```

### Sum of space-time raster datasets

Sum maps from STRDS A with maps from STRDS B which have equal time
stamps and are temporally before Jan. 1. 2005 and store them in STRDS D:

```sh
D = if(start_date(A) < "2005-01-01", A + B)
```

Create the sum of all maps from STRDS A and B that have equal time
stamps and store the new maps in STRDS C:

```sh
C = A + B
```

### Sum of space-time raster datasets with temporal topology relation

Same expression with explicit definition of the temporal topology
relation and temporal operators:

```sh
C = A {+,equal,l} B
```

### Selection of raster cells

Select all cells from STRDS B with equal temporal relations to STRDS A,
if the cells of A are in the range \[100.0, 1600\] of time intervals
that have more than 30 days (Jan, Mar, May, Jul, Aug, Oct, Dec):

```sh
C = if(A > 100 && A < 1600 && td(A) > 30, B)
```

### Selection of raster cells with temporal topology relation

Same expression with explicit definition of the temporal topology
relation between the condition and the then part:

```sh
C = if({equal}, A > 100 && A < 1600 && td(A) > 30, B)
```

### Conditional computation

Compute the recharge in meters per second for all cells of precipitation
STRDS "Prec" if the mean temperature specified in STRDS "Temp" is higher
than 10 degrees. Computation is performed if STRDS "Prec" and "Temp"
have equal time stamps. The number of days or fraction of days per
interval is computed using the td() function that has as argument the
STRDS "Prec":

```sh
C = if(Temp > 10.0, Prec / 3600.0 / 24.0 / td(Prec))
```

### Conditional computation with temporal topology relation

Same expression with explicit definition of the temporal topology
relation and temporal operators:

```sh
C = if({equal}, Temp > 10.0, Prec / 3600.0 / 24.0 {/,equal,l} td(Prec))
```

### Computation with time intervals

Compute the mean value of all maps from STRDS A that are located during
time intervals of STRDS B if more than one map of A is contained in an
interval of B, use A otherwise. The resulting time intervals are either
from B or A:

```sh
C = if(B {#,contains} A > 1, (B {+,contains,l} A - B) / (B {#,contains} A), A)
```

### Computation with time intervals with temporal topology relation

Same expression with explicit definition of the temporal topology
relation and temporal operators:

```sh
C = if({equal}, B {#,contains} A > 1, (B {+,contains,l} A {-,equal,l} B) {/,equal,l} (B {#,contains} A), A)
```

### Compute DOY for spatio-temporal conditions

Compute the DOY for all maps from STRDS A where conditions are met at
three consecutive time intervals (e.g. temperature \> 0):

```sh
B = if(A > 0.0 && A[-1] > 0.0 && A[-2] > 0.0, start_doy(A, -1), 0)
```

## SEE ALSO

*[r.mapcalc](r.mapcalc.md), [t.vect.algebra](t.vect.algebra.md),
[t.rast3d.algebra](t.rast3d.algebra.md), [t.select](t.select.md),
[t.rast3d.mapcalc](t.rast3d.mapcalc.md),
[t.rast.mapcalc](t.rast.mapcalc.md)*

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
