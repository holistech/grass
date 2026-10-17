## DESCRIPTION

*t.vect.algebra* performs temporal and spatial overlay and buffer
functions on space time vector datasets (STVDS) by using the temporal
vector algebra. New STVDS can be created, which are expressions of
existing STVDS.

The module expects an **expression** as input parameter in the following
form:

```sh
"result = expression"
```

The statement structure is similar to r.mapcalc, see
[r.mapcalc](r.mapcalc.md). Where **result** represents the name of a
space time dataset (STVDS) that will contain the result of the
calculation that is given as **expression** on the right side of the
equality sign. These expression can be any valid or nested combination
of temporal operations and functions that are provided by the temporal
vector algebra.  
The algebra provides methods for map selection from STDS based on their
temporal relations. It is also possible to temporally shift maps, to
create temporal buffer and to snap time instances to create a valid
temporal topology. Furthermore expressions can be nested and evaluated
in conditional statements (if, else statements). Within if-statements
the algebra provides temporal variables like start time, end time, day
of year, time differences or number of maps per time interval to build
up conditions. These operations can be assigned to space time datasets
or to the results of operations between space time datasets.

As default, topological relationships between space time datasets will
be evaluated only temporal.
The **-s** flag additionally activates the evaluation of the spatial
topology of the maps. It applies wherever the algebra evaluates the
topology of maps: in selections, in the hash operator, in the conditions
of if statements and in comparison operators. Two temporally related
maps are then only used together if they are also spatially related,
that is the spatial extents of the maps are equivalent, one covers or is
covered by the other, they overlap, one lies in the other, one contains
the other, or they meet (the spatial relations *equivalent*, *cover*,
*covered*, *overlap*, *in*, *contain* and *meet*).

The expression option must be passed as **quoted** expression, for
example:  

```sh
t.select expression="C = A : B"
```

Where **C** is the new space time raster dataset that will contain maps
from **A** that are selected by equal temporal relationships to the
existing dataset **B** in this case.

## TEMPORAL VECTOR ALGEBRA

The temporal algebra provides a wide range of temporal operators and
functions that will be presented in the following section.

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
the new algebra and **-c** read both names. The previous implementation
refuses `equals` with a syntax error.

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
Note A and B can either be space time datasets or expressions. The
temporal relationship between the conditions and the conclusions can be
defined at the beginning of the if statement. The relationship between
then and else conclusion must be always equal.

```sh
if statement                           decision option                        temporal relations
  if(if, then, else)
  if(conditions, A)                    A if conditions are True;              temporal topological relation between if and then is equal.
  if(conditions, A, B)                 A if conditions are True, B otherwise; temporal topological relation between if, then and else is equal.
  if(topologies, conditions, A)        A if conditions are True;              temporal topological relation between if and then is explicit specified by topologies.
  if(topologies, conditions, A, B)     A if conditions are True, B otherwise; temporal topological relation between if, then and else is explicit specified by topologies.
```

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

#### Comparison operator

The conditions are comparison expressions that are used to evaluate
space time datasets. Specific values of temporal variables are compared
by logical operators and evaluated for each map of the STDS and the
related maps. For complex relations the comparison operator can be used
to combine conditions:  
The structure is similar to the select operator with the extension of an
aggregation operator:

```sh
{"comparison operator", "topological relations", aggregation operator, "temporal operator"}
```

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
tmap function.

```sh
tmap()
```

For example:

```sh
 C = A {:,during} tmap(event)
```

This statement select all maps from space time data set A that are
during the temporal extent of single map 'event'

### Spatial vector operators

The module supports the following boolean vector operations:  

```sh
 Boolean Name   Operator Meaning         Precedence   Correspondent function
----------------------------------------------------------------------------------
 AND            &        Intersection          1      (v.overlay operator=and)
 OR             |        Union                 1      (v.overlay operator=or)
 DISJOINT OR    +        Disjoint union        1      (v.patch)
 XOR            ^        Symmetric difference  1      (v.overlay operator=xor)
 NOT            ~        Complement            1      (v.overlay operator=not)
```

And vector functions:

```sh
 buff_p(A, size)          Buffer the points of vector map layer A with size
 buff_l(A, size)          Buffer the lines of vector map layer A with size
 buff_a(A, size)          Buffer the areas of vector map layer A with size
```

### Combinations of temporal, vector and select operators

We combine the temporal topology relations, the temporal operators and
the spatial/select operators to create spatio-temporal vector operators:

```code
{"spatial or select operator" , "list of temporal relations", "temporal operator" }
```

For multiple topological relations or several related maps the
spatio-temporal operators feature implicit aggregation. The algebra
evaluates the stated STDS by their temporal topologies and apply the
given spatio temporal operators in a aggregated form. If we have two
STDS A and B, B has three maps: b1, b2, b3 that are all during the
temporal extent of the single map a1 of A, then the following overlay
calculations would implicitly aggregate all maps of B into one result
map for a1 of A:

```sh
C = A {&, contains} B --> c1 = a1 & b1 & b2 & b3
```

Keep attention that the aggregation behaviour is not symmetric:

```sh
C = B {&, during} A --> c1 = b1 & a1
                        c2 = b2 & a1
                        c3 = b3 & a1
```

### Examples

Spatio-temporal intersect all maps from space time dataset A with all
maps from space time dataset B which have equal time stamps and are
temporary before Jan. 1. 2005 and store them in space time dataset D.

```sh
D = if(start_date(A) < "2005-01-01", A & B)
```

Buffer all vector points from space time vector dataset A and B with a
distance of one and intersect the results with overlapping, containing,
during and equal temporal relations to store the result in space time
vector dataset D with intersected time stamps.

```sh
D = buff_p(A, 1) {&,overlaps|overlapped|equal|during|contains,i} buff_p(B, 1)
```

Select all maps from space time dataset B which are during the temporal
buffered space time dataset A with a map interval of three days, else
select maps from C and store them in space time dataset D.

```sh
D = if({contains}, td(buff_t(A, "1 days")) == 3, B, C)
```

## NOTES

Maps that an expression leaves unchanged, such as the maps of A in
`C = A : B`, are registered in the result dataset as they are, not copied.
*t.remove* with the flags **-rf** on the result dataset therefore also
unregisters them from A, and with **-df** deletes them. Maps of another
mapset cannot be deleted; for them *t.remove* **-df** stops with an error
and leaves the maps as they are.

The same holds for a time function that leaves the time of a map unchanged:
`C = tsnap(A)` registers the maps of A themselves if they have no gaps, and
copies only the maps whose time changes. This holds for both algebras.

### Core and classic algebra

Since GRASS 8.6, *t.vect.algebra* computes its expressions with the
functions of the Python package `grass.temporal.algebra`, as
*t.rast.algebra* does. The previous implementation stays available as the
classic algebra, so that published results remain reproducible. The classic
algebra is a set of rules of the same functions: it reads the syntax of the
previous implementation and applies its rules for relations, order and
results. The flag **-c** selects it for one call, the environment variable
`GRASS_TEMPORAL_ALGEBRA=classic` for a whole session or script;
`GRASS_TEMPORAL_ALGEBRA=core` or an unset or empty variable selects the
new algebra, and the flag takes precedence over the variable. In Python,
`TemporalVectorAlgebraParser` takes the keyword `classic=True` for the
same purpose.

The two algebras differ in the following points. The examples use four
daily maps in A with one area each, and two maps of two days in B that
start with A, each with one area that contains the areas of the two maps
of A in its time, and time instances in I.

1. **Right reference.** `A {:,R,r} B` and `A {op,R,r} B` give one map
   per related pair, with the time stamp of the right map and, for an
   overlay, the overlay of this pair. The classic algebra keeps only the
   last pair of a selection, and an overlay combines the left map with
   all of its related right maps into one map, with the time stamp of the
   last of them. The first expression gives four maps, the maps of B with
   the time stamps of A; the classic algebra gives one map per map of B.
   If a map b1 contains the maps a1 and a2, the second expression gives
   `b1 & a1` with the time stamp of a1 and `b1 & a2` with that of a2, the
   classic algebra `b1 & a1 & a2` with the time stamp of a2:

   ```sh
   C = B {:,contains,r} A
   C = B {&,contains,r} A
   ```

   The inverse selection `A {!:,R,t} B` takes only the temporal operator
   `l`, because its maps have no related map to combine with; the classic
   algebra accepts the other operators.

2. **Spatial relations need -s.** A spatial relation in an operator, such
   as `{&,equal|overlap}`, needs the flag **-s**; without it, the algebra
   stops with an error. The classic algebra gives an empty result.

3. **Empty results.** An expression that gives no map creates an empty
   space time dataset; the classic algebra creates none. No daily map of A
   contains a map of B of two days, so this expression gives an empty
   dataset:

   ```sh
   C = A {:,contains} B
   ```

4. **Maps without primitives.** A computed map without primitives, such
   as the intersection of two maps without common area, is not
   registered. The classic algebra registers it, unless the extents of the
   two maps do not intersect. If a map e1 has two areas, one left and one
   right of the area of a1, this expression leaves out `a1 & e1`, where
   the classic algebra registers it without areas:

   ```sh
   C = A & E
   ```

5. **Precedence.** `&&` binds stronger than `||`, and conditions can be
   grouped with parentheses. The classic algebra evaluates conditions
   from left to right and does not accept parentheses around conditions.
   The first expression takes all maps of A, because `td(A) == 1` is true
   for each of them; the classic algebra reads it as the second expression
   and takes none:

   ```sh
   C = if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)
   C = if((td(A) == 1 || td(A) == 2) && td(A) == 3, A)
   ```

6. **Conditions joined with or.** If a map of the conclusion of an `if`
   has several related condition maps, both algebras join their
   conditions with and; written as `{during,|}`, the relation joins them
   with or, a form that the classic algebra does not read. The first
   expression takes b2, whose maps of A both start after day 1, the second
   also b1, which contains a map of A that starts on day 2:

   ```sh
   C = if({during}, start_day(A) > 1, B)
   C = if({during,|}, start_day(A) > 1, B)
   ```

7. **td() of a time instance** is null instead of an error, so a condition
   on it is neither true nor false. This expression gives no map; the
   classic algebra stops with an error:

   ```sh
   C = if(td(I) > 0, I)
   ```

   A temporal variable that a map does not have, such as `end_doy()` of a
   time instance, is an error in both algebras.

8. **More syntax.** The temporal neighbourhood modifier of
   *t.rast.algebra*, such as `A[1]` and `A[-1]`, applies to vector
   datasets. Comparisons and temporal functions may stand anywhere in a
   condition, also with the number on the left, in arithmetic and after a
   minus sign, and a dataset may have the name of a function. The classic
   algebra reports a syntax error for each of these expressions; the last
   one intersects a dataset named `td` with B:

   ```sh
   C = A[1]
   C = A[-1]
   C = if(2 < start_day(A), A)
   C = if(start_day(A) + 1 > 3, A)
   C = if(-start_day(A) < -2, A)
   C = td {&,during} B
   ```

   The hash operator may also stand in arithmetic within a condition; the
   classic algebra reads it only directly before a comparison:

   ```sh
   C = if(A {#,during} B + 1 > 1, A)
   ```

9. **Negative buffer.** A negative size in `buff_t()` shrinks the maps
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

10. **merge() of buffers.** The new algebra takes two maps with equal
    content and time stamps as one map. The classic algebra, as the
    previous implementation, makes a new map for each buffer of
    `buff_p()`, `buff_l()` and `buff_a()`, and `merge()` keeps such a map
    next to an equal one. This expression gives the buffers of the maps of
    A once in the new algebra and twice in the classic algebra:

    ```sh
    C = merge(buff_p(A, 1), buff_p(A, 1))
    ```

In Python, both algebras raise `SyntaxError` for an expression they cannot
read. For one they cannot compute, such as `if(end_doy(I) > 0, I)`, the
new algebra raises `ValueError` or `TypeError`, where the classic algebra
raises `FatalError`. Both raise `FatalError` for a missing dataset and,
without overwrite, for an existing result. The tool stops with the error
message in both algebras.

Two corrections apply to both algebras, and to *t.rast.algebra*,
*t.rast3d.algebra* and *t.select* as well, so **-c** gives the rules of
the previous algebra, not the results of a particular release. First,
`if({R}, condition, conclusion)` reads "condition R conclusion":
`if({contains}, start_doy(A) > 0, B)` gives the maps of B that lie within
a map of A. The code that *t.vect.algebra* shares with *t.select* read such
relations the other way round before; *t.vect.algebra* of GRASS 8.4 stops
with an error on conditions on temporal variables. Second, with a temporal
relation beyond `equal`, the else part of a condition on temporal
variables also takes the maps that no condition map is related to. Figure
A3 of Gebbert, Leppelt and Pebesma (2019) needs both: A has maps from day
1 to 3, 3 to 5 and 5 to 7 of January 2001, B has daily maps from day 1 to
10, and this expression gives the first two maps of A and the maps of B
from day 5 on, as the figure shows:

```sh
C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)
```

Results that rely on the previous reading direction or else rule need the
GRASS version they were computed with. The section "Core and classic
algebra" in the NOTES of [t.rast.algebra](t.rast.algebra.md) describes
both corrections.

#### Corrections to the classic algebra

The classic algebra gives the results of the previous implementation, with
the exceptions below. In these cases the previous implementation ended in
an error that had no reason or reported the wrong error. **-c** now gives
the result described here; the new algebra never had these errors. Results
of earlier GRASS versions that used one of these forms need a new run.

1. **tsnap() and tshift() of no maps.** If the expression inside has no
   maps, the result is empty like any other empty result: the classic
   algebra creates no dataset, and an enclosing expression goes on with no
   maps. Earlier versions ended in an error. No daily map of A contains a
   map of B of two days, so both expressions give an empty result:

   ```sh
   C = tsnap(A {:,contains} B)
   C = tshift(A {:,contains} B, "1 day")
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

3. **Overlay with an unknown number of areas.** An intermediate map that
   `buff_p()` leaves empty, because the input has no points, has no known
   number of areas. It counts as a map without areas: *v.overlay* is not
   run, a warning says so, and the result is dropped. Earlier versions ran
   *v.overlay* on the map, which failed. A has no points, so this
   expression gives no map:

   ```sh
   C = buff_p(A, 1) ^ B
   ```

4. **Selection with a time instance on relative time.** With the temporal
   operator `i`, the time stamp of the result is the time instance. Earlier
   versions failed with a `TypeError` for a selection on relative time. If A
   has maps of relative time that contain the time instances of I, this
   expression gives maps with the instances as time:

   ```sh
   C = A {:,contains,i} I
   ```

#### Differences from the previous implementation

The differences in message texts, in the debug output of the Python
parser, in the order of errors and in the error for an existing result that
[t.rast.algebra](t.rast.algebra.md) lists apply here likewise, as do the
items on lists of absolute and relative time and on the relation `equals`,
the two that change the outcome of an expression. The previous
implementation refuses `equals` with a syntax error.

## REFERENCES

[PLY(Python-Lex-Yacc)](https://www.dabeaz.com/ply/)

Gebbert, S., Leppelt, T., Pebesma, E., 2019. A topology based
spatio-temporal map algebra for big data analysis. Data 4, 86.
<https://doi.org/10.3390/data4020086>

## SEE ALSO

*[t.select](t.select.md)*

## AUTHORS

Thomas Leppelt, Soeren Gebbert, Thünen Institute of Climate-Smart
Agriculture
