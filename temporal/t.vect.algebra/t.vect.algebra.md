## DESCRIPTION

*t.vect.algebra* applies temporal and spatial operations to space time vector
datasets (STVDS) and registers the result in a new STVDS. An expression can
select maps by their temporal relations, overlay vector maps that are related
in time, buffer the points, lines and areas of maps, and shift, snap and buffer
the time stamps of maps. The expressions can be nested and evaluated in
conditional statements. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets and temporal relations. *[t.rast.algebra](t.rast.algebra.md)* and
*[t.rast3d.algebra](t.rast3d.algebra.md)* are the same algebra for raster and
3D raster datasets, and *[t.select](t.select.md)* selects maps from datasets of
every type.

The tool has two required options and two flags:

- **expression** holds the statement `result = expression`. The statement
    structure is similar to *[r.mapcalc](r.mapcalc.md)*. **result** is the name
    of the new space time vector dataset, which the tool creates in the current
    mapset, and the right side of the equality sign is an expression of
    datasets, operators and functions of the temporal vector algebra described
    below. The tool needs the whole statement as one **quoted** value:
    `expression="sel_equal = A : B"`. A dataset in another mapset is named with
    its mapset (`A@t_vect_algebra`); a name without mapset is looked up in the
    current mapset first, then in the mapsets of the search path, and with
    **-c** in the current mapset only. The tool does not overwrite an existing
    result dataset
    unless the global flag **--overwrite** is given.
- **basename** is the prefix of the names of the vector maps that the tool
    creates. A numerical suffix separated by an underscore makes the names
    unique: `sel_during_0`, `sel_during_1`. The number counts the maps that
    are registered: a map that is left out because it has no primitives (see
    the NOTES) leaves no gap. The classic algebra numbers the maps it
    registers without a gap as well.
    A map that an expression leaves unchanged is registered in the result
    dataset as it is and gets no new name.
- **-s** checks the spatial topology of temporally related maps: the algebra
    then uses two temporally related maps together only if they are also related
    in space. The default is a temporal evaluation only. The flag applies
    wherever the algebra evaluates the topology of maps: in selections, in the
    hash operator, in the conditions of if statements and in comparison
    operators. The spatial relations of two maps are *equivalent* (equal
    spatial extents), *cover* and *covered*, *overlap*, *in* and *contain*, and
    *meet*. They can also be named in the curly brackets of an operator, for
    example `{&,equal|overlap}`; the maps then need this spatial relation in
    addition to the temporal one. Such a name builds the spatial topology for
    its operator also without **-s**. The classic algebra does not read such
    names and stops with an error. A spatial relation without a temporal one
    (`{&,equivalent}`) is an error. The example "Check the spatial topology"
    shows **-s**.
- **-c** computes the expression with the rules of the classic algebra, as the
    releases before GRASS 8.6 did, instead of the rules of the algebra core. The
    flag takes precedence over the environment variable
    `GRASS_TEMPORAL_ALGEBRA=classic`; see "Core and classic algebra" in the
    NOTES. The example "Use the classic algebra" shows **-c**.

The result dataset has the temporal type of its input datasets. An expression
can combine datasets of one temporal type only; the example "Relative time
and datasets of another mapset" shows absolute and relative time and datasets
of another mapset. If an expression
gives no map, the tool creates an empty result dataset and warns that the
result is empty; the exit status is 0. The classic algebra creates no dataset
for an empty result.

Examples of every operator and function in this manual are in the EXAMPLES
section. Their datasets are created by the example "Create the datasets of the
examples", which the others
build on.

## TEMPORAL VECTOR ALGEBRA

The temporal algebra provides a wide range of temporal operators and
functions that are presented in the following sections.

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
relation. The "Temporal selection operators" example shows each of these
rules.

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
without processing vector data. The algebra provides a
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

means: select all parts of space time dataset A that are not equal
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

The first and the "Temporal selection operators" example run these
selections.

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

The "Conditions" example evaluates `start_date()`, `start_month()`,
`start_day()` and `td()`.

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
an error; `l` is the default.

```sh
C = if({equal}, A {#, contains} B > 2, A {:, contains} B)
```

This expression selects all maps from A that temporally contains more than
2 maps from B and stores them in space time dataset C. The leading
equal statement in the if condition specifies the temporal relation
between the if and then part of the if expression. This is very
important, so we do not need to specify a global time reference (a space
time dataset) for temporal processing. The "Conditions" example runs this
expression, a comparison operator and the rejected temporal operator.

Furthermore the temporal algebra allows temporal buffering, shifting and
snapping with the functions buff_t(), tshift() and tsnap() respectively.

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
GRASS 8.6 with the correction of item 11 under "Corrections to the classic
algebra", one day here, and ends the instance of March 31 on April 1.

The function merge(A, B) gives the maps of both datasets in one dataset.

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

The operators have the same precedence: an expression is evaluated from left
to right, and parentheses group it differently. The "Overlay operators"
example shows `A | B & A` and `A | (B & A)`.

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

### Expressions of the paper

Spatio-temporal intersect all maps from space time dataset A with all
maps from space time dataset B which have equal time stamps and are
temporary before a given date and store them in space time dataset D.

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

The "Conditions" example runs the first and the third form on the datasets of
the first example, the first with an empty result, as all maps start after
2005. The example "Expression of the paper with points" runs the second form
on datasets of points.

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

A computed map without primitives, such as the intersection of two maps
without common area, is not registered. When an intermediate map of a longer
expression has no areas, the tool leaves out the result map that depends on it
and warns with the message "Result map `<name>` is left out: intermediate map
`<name>` has no areas"; `A | (B & A)` in the "Overlay operators" example does
this for its third map. The computed maps after a left-out map take its
number; a map registered unchanged keeps its name.

### Core and classic algebra

Since GRASS 8.6, *t.vect.algebra* computes its expressions with the functions
of the Python package `grass.temporal.algebra`, as *t.rast.algebra* does. The
implementation used before, the reference implementation in
`grass.temporal.classic`, stays in the source code, and its rules stay
available as the classic algebra, so that published results remain
reproducible. The classic algebra is a set of rules of the same functions: it
reads the syntax of the reference implementation and applies its rules for
relations, order and results. The flag **-c** selects it for one call, the
environment variable `GRASS_TEMPORAL_ALGEBRA=classic` for a whole session or
script; `GRASS_TEMPORAL_ALGEBRA=core` or an unset or empty variable selects the
new algebra, and the flag takes precedence over the variable. In Python,
`TemporalVectorAlgebraParser` takes the keyword `classic=True` for the same
purpose.

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

2. **Empty results.** An expression that gives no map creates an empty
    space time dataset; the classic algebra creates none. No daily map of A
    contains a map of B of two days, so this expression gives an empty
    dataset:

    ```sh
    C = A {:,contains} B
    ```

3. **Maps without primitives.** A computed map without primitives, such
    as the intersection of two maps without common area, is not
    registered. The classic algebra registers it, unless the extents of the
    two maps do not intersect. If a map e1 has two areas, one left and one
    right of the area of a1, this expression leaves out `a1 & e1`, where
    the classic algebra registers it without areas:

    ```sh
    C = A & E
    ```

4. **Precedence.** `&&` binds stronger than `||`, and conditions can be
    grouped with parentheses. The classic algebra evaluates conditions
    from left to right and does not accept parentheses around conditions.
    The first expression takes all maps of A, because `td(A) == 1` is true
    for each of them; the classic algebra reads it as the second expression
    and takes none:

    ```sh
    C = if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)
    C = if((td(A) == 1 || td(A) == 2) && td(A) == 3, A)
    ```

5. **Conditions joined with or.** If a map of the conclusion of an `if`
    has several related condition maps, both algebras join their
    conditions with and; written as `{during,|}`, the relation joins them
    with or, a form that the classic algebra does not read. The first
    expression takes b2, whose maps of A both start after day 1, the second
    also b1, which contains a map of A that starts on day 2:

    ```sh
    C = if({during}, start_day(A) > 1, B)
    C = if({during,|}, start_day(A) > 1, B)
    ```

6. **td() of a time instance** is null instead of an error, so a condition
    on it is neither true nor false. This expression gives no map; the
    classic algebra stops with an error:

    ```sh
    C = if(td(I) > 0, I)
    ```

    A temporal variable that a map does not have, such as `end_doy()` of a
    time instance, is an error in both algebras.

7. **More syntax.** The temporal neighbourhood modifier of
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

9. **merge() of buffers.** The new algebra takes two maps with equal
    content and time stamps as one map. The classic algebra, as the
    reference implementation, makes a new map for each buffer of
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
the classic algebra, not the results of a particular release. First,
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
from day 5 on, as the figure shows (see the example "Figure A3 of the
publication"):

```sh
C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)
```

Results that rely on the previous reading direction or else rule need the
GRASS version they were computed with. The section "Core and classic
algebra" in the NOTES of [t.rast.algebra](t.rast.algebra.md) describes
both corrections.

#### Corrections to the classic algebra

The classic algebra gives the results of the releases before GRASS 8.6, with the
exceptions below. In these cases those releases computed wrongly, ended in an
error that had no reason, or reported the wrong error. **-c** now gives the
result described here. The reference implementation was corrected in the same
way, except in items 8 and 9: it still takes the time of a partner whose box
only touches, and it still raises the `CalledModuleError` of a failed module.
The new algebra never had these errors; only the items on month steps, on dates
beyond the year 9999, on a failed module and on the granularity concerned the
library and with it both algebras. Results of earlier GRASS versions that used
one of these forms need a new run.

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

5. **A spatial relation without a temporal one.** An operator with spatial
    relation names only, such as `A {&,equivalent,l} B`, related no map, because
    maps are related by their temporal relations, and gave an empty result
    without a message. It stops now with the error "equivalent is a spatial
    relation and needs a temporal one, as in equal|overlap", as in the new
    algebra. A selection in braces, which refuses spatial names with a syntax
    error, gives this error too when the names are spatial only. Write a
    temporal relation beside the spatial one:

    ```sh
    C = A {&,equal|equivalent,l} B
    ```

6. **Month and year steps from the end of a month.** `tshift()` and `buff_t()`
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

7. **A date beyond the year 9999.** A step that ends behind the year 9999 or
    before the year 1, for example `buff_t(A, "365 days")` on a map that ends on
    1 December 9999, ended with a traceback ("date value out of range") in both
    algebras. It now ends with the error "... is beyond the year 9999" or "...
    is before the year 1"; no map and no dataset is created.

8. **A selection with r or u under -s and maps whose boxes only touch.** With
    **-s** two maps are related when they are related in time and in space;
    boxes that meet at an edge or a corner only are not related in space. A
    selection such as `A {:,precedes,r} B` took the time of every map that was
    related in time, also of one whose box only touches the box of the map of A,
    and the last such map won. An inverse selection such as
    `A {!:,precedes,r} B` kept a map without a related partner, as it should,
    but gave it the time of a partner that only touches it. The time is now
    taken only from maps that are related in time and in space, and `!:` keeps a
    map without such a partner with its own time. For example, a map of A from 1
    to 2 January whose box meets at a corner the box of a map of B from 2 to 3
    January keeps the time 1 to 2 January in the inverse selection above, where
    it took 2 to 3 January. Without **-s** nothing changes.

9. **A failed module.** If a module fails while the maps are computed, for
    example *v.patch*, both algebras ended with a Python traceback. They now end
    with an error that names the module and its return code, such as
    `Module <v.patch> failed with return code 1, see the error output above`;
    the cause is in the error output of the module above it. No dataset is
    created.

10. **The relation equals.** The releases before GRASS 8.6 refused the spelling
    `equals` of the paper with a syntax error. The classic algebra reads it as
    `equal`, as the new algebra does.

11. **The granularity of steps over a year and of a time of the day.** The
    granularity of a dataset, which `tsnap()` uses for the end of a last time
    instance, counted a step between the first days of two months more than a
    year apart by the difference of the months only: 1 January 2024 to 1 March
    2025 gave 2 months and now gives 14 months. A step whose two ends lie at the
    same time of the day other than midnight counted in hours or minutes: time
    instances at 10:30 ten days apart had the granularity `14400 minutes` and
    now have `10 days`. A time of the day that differs between the two ends
    still counts: from 10:30 to 11:30 ten days later the granularity is
    `241 hours`.

#### Differences from the reference implementation

The differences in message texts, in the debug output of the Python
parser, in the order of errors and in the error for an existing result that
[t.rast.algebra](t.rast.algebra.md) lists apply here likewise, as does the
item on lists of absolute and relative time, the one that changes the outcome
of an expression.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_vect_algebra` and sets the computational region
to North Carolina with cells of 1 km; the later examples work in this mapset
and region. The algebra works on times and shapes, not on measurements, so the
datasets are small sketches of squares, lines and points a few meters wide
near the point (300000, 100000) in the region.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_vect_algebra -->

<!-- markdownlint-disable MD046 -->

### Create the datasets of the examples

The examples build on each other and use the same datasets, which this example
creates. All vector areas are squares of 10 by 10 meters, made with
*[v.in.region](v.in.region.md)* from a small region. The coordinates x and y in
the descriptions count meters east and north of the point (300000, 100000), so
x = 20 is 300020 in the map; the extent columns of
*[t.vect.list](t.vect.list.md)* show the full values. The position of a square
is given by its west and south edge.

- `A` holds the daily maps `a1`, `a2` and `a3` from 1 March 2026, squares at
    x = 0, 20 and 40, y = 0 to 10.
- `B` holds the daily maps `b1`, `b2` and `b3` of the same days, squares at
    x = 5, 25 and 70, y = 5 to 15. So `b1` overlaps `a1` in a square of 5 by 5
    meters, area 25, `b2` overlaps `a2` the same way, and `b3` is far from `a3`.
- `W` holds two maps of two days, `w1` from 1 to 3 March at x = 5 and `w2`
    from 3 to 5 March at x = 45, y = 0 to 10. In time, `w1` contains `a1` and
    `a2` (`a1` starts together with it, `a2` finishes together with it), and
    `w2` contains `a3`.
- `P` holds the daily maps `p1`, `p2` and `p3` with one, two and three points
    at y = 5, ten meters apart, starting at x = 5.
- `L` holds the daily maps `l1` and `l2`, each with one line of length 10 meters
    at y = 5, from x = 0 and x = 20.
- `C` holds the maps `c1` and `c2`, copies of `w1` and `w2` with the same two
    times. It is the else part of an expression of the paper in the
    "Conditions" example.
- The map `ev` is a square at x = 20 with the time of one day, 2 to 3 March.
    It is in no dataset; the "Temporal selection" example refers to it with
    `tmap(ev)`.

The tool calls of the following examples use the datasets by name.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_algebra
    g.region raster=elev_state_500m res=1000 -a
    x0=300000
    y0=100000
    for square in "a1 0 10 0" "a2 20 30 0" "a3 40 50 0" "b1 5 15 5" \
        "b2 25 35 5" "b3 70 80 5" "w1 5 15 0" "w2 45 55 0" "ev 20 30 0"; do
        set -- $square
        g.region w=$((x0 + $2)) e=$((x0 + $3)) s=$((y0 + $4)) n=$((y0 + $4 + 10))
        v.in.region output=$1
    done
    g.region raster=elev_state_500m res=1000 -a
    for line in "l1 0" "l2 20"; do
        set -- $line
        printf "L 2 1\n $((x0 + $2)) $((y0 + 5))\n $((x0 + $2 + 10)) $((y0 + 5))\n 1 1\n" | \
            v.in.ascii -n input=- output=$1 format=standard
    done
    for count in 1 2 3; do
        seq 1 $count | awk -v x0=$x0 -v y0=$y0 \
            '{ print x0 + 10 * $1 - 5 "," y0 + 5 "," $1 }' | \
            v.in.ascii input=- output=p$count separator=comma
    done
    for dataset in A B W P L C; do
        t.create type=stvds output=$dataset title="$dataset" \
            description="Dataset $dataset of the t.vect.algebra examples"
    done
    t.register -i type=vector input=A maps=a1,a2,a3 \
        start=2026-03-01 increment="1 day"
    t.register -i type=vector input=B maps=b1,b2,b3 \
        start=2026-03-01 increment="1 day"
    t.register type=vector input=W maps=w1 start=2026-03-01 end=2026-03-03
    t.register type=vector input=W maps=w2 start=2026-03-03 end=2026-03-05
    t.register -i type=vector input=P maps=p1,p2,p3 \
        start=2026-03-01 increment="1 day"
    t.register -i type=vector input=L maps=l1,l2 \
        start=2026-03-01 increment="1 day"
    t.register type=vector maps=ev start=2026-03-02 end=2026-03-03
    for k in 1 2; do
        g.copy vector=w$k,c$k
    done
    t.register type=vector input=C maps=c1 start=2026-03-01 end=2026-03-03
    t.register type=vector input=C maps=c2 start=2026-03-03 end=2026-03-05
    ```

    ```sh
    t.vect.list input=A columns=name,start_time,end_time,west,east,south,north
    ```

    ```text
    name|start_time|end_time|west|east|south|north
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00|300000.0|300010.0|100000.0|100010.0
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00|300020.0|300030.0|100000.0|100010.0
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00|300040.0|300050.0|100000.0|100010.0
    ```

    ```sh
    t.vect.list input=B columns=name,start_time,end_time,west,east,south,north
    ```

    ```text
    name|start_time|end_time|west|east|south|north
    b1|2026-03-01 00:00:00|2026-03-02 00:00:00|300005.0|300015.0|100005.0|100015.0
    b2|2026-03-02 00:00:00|2026-03-03 00:00:00|300025.0|300035.0|100005.0|100015.0
    b3|2026-03-03 00:00:00|2026-03-04 00:00:00|300070.0|300080.0|100005.0|100015.0
    ```

    ```sh
    t.vect.list input=W columns=name,start_time,end_time,west,east,south,north
    ```

    ```text
    name|start_time|end_time|west|east|south|north
    w1|2026-03-01 00:00:00|2026-03-03 00:00:00|300005.0|300015.0|100000.0|100010.0
    w2|2026-03-03 00:00:00|2026-03-05 00:00:00|300045.0|300055.0|100000.0|100010.0
    ```

    ```sh
    t.vect.list input=P columns=name,start_time,end_time,points
    ```

    ```text
    name|start_time|end_time|points
    p1|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    p2|2026-03-02 00:00:00|2026-03-03 00:00:00|2
    p3|2026-03-03 00:00:00|2026-03-04 00:00:00|3
    ```

    ```sh
    t.vect.list input=L columns=name,start_time,end_time,lines
    ```

    ```text
    name|start_time|end_time|lines
    l1|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    l2|2026-03-02 00:00:00|2026-03-03 00:00:00|1
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    from grass.tools import Tools

    tools = Tools()

    tools.g_mapset(flags="c", mapset="t_vect_algebra")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    x0, y0 = 300000, 100000
    squares = [
        ("a1", 0, 10, 0),
        ("a2", 20, 30, 0),
        ("a3", 40, 50, 0),
        ("b1", 5, 15, 5),
        ("b2", 25, 35, 5),
        ("b3", 70, 80, 5),
        ("w1", 5, 15, 0),
        ("w2", 45, 55, 0),
        ("ev", 20, 30, 0),
    ]
    for name, west, east, south in squares:
        tools.g_region(w=x0 + west, e=x0 + east, s=y0 + south, n=y0 + south + 10)
        tools.v_in_region(output=name)
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for name, west in (("l1", 0), ("l2", 20)):
        line = f"L 2 1\n {x0 + west} {y0 + 5}\n {x0 + west + 10} {y0 + 5}\n 1 1\n"
        tools.v_in_ascii(input=StringIO(line), output=name, format="standard", flags="n")
    for count in (1, 2, 3):
        points = "".join(f"{x0 + 10 * i - 5},{y0 + 5},{i}\n" for i in range(1, count + 1))
        tools.v_in_ascii(input=StringIO(points), output=f"p{count}", separator="comma")
    for dataset in ("A", "B", "W", "P", "L", "C"):
        tools.t_create(
            type="stvds",
            output=dataset,
            title=dataset,
            description=f"Dataset {dataset} of the t.vect.algebra examples",
        )
    tools.t_register(
        type="vector",
        input="A",
        maps="a1,a2,a3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_register(
        type="vector",
        input="B",
        maps="b1,b2,b3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_register(
        type="vector", input="W", maps="w1", start="2026-03-01", end="2026-03-03"
    )
    tools.t_register(
        type="vector", input="W", maps="w2", start="2026-03-03", end="2026-03-05"
    )
    tools.t_register(
        type="vector",
        input="P",
        maps="p1,p2,p3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_register(
        type="vector",
        input="L",
        maps="l1,l2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_register(type="vector", maps="ev", start="2026-03-02", end="2026-03-03")
    for k in (1, 2):
        tools.g_copy(vector=f"w{k},c{k}")
    tools.t_register(
        type="vector", input="C", maps="c1", start="2026-03-01", end="2026-03-03"
    )
    tools.t_register(
        type="vector", input="C", maps="c2", start="2026-03-03", end="2026-03-05"
    )
    ```

    ```python
    columns = "name,start_time,end_time,west,east,south,north"
    print(tools.t_vect_list(input="A", columns=columns).text)
    ```

    ```text
    name|start_time|end_time|west|east|south|north
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00|300000.0|300010.0|100000.0|100010.0
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00|300020.0|300030.0|100000.0|100010.0
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00|300040.0|300050.0|100000.0|100010.0
    ```

    ```python
    print(tools.t_vect_list(input="B", columns=columns).text)
    ```

    ```text
    name|start_time|end_time|west|east|south|north
    b1|2026-03-01 00:00:00|2026-03-02 00:00:00|300005.0|300015.0|100005.0|100015.0
    b2|2026-03-02 00:00:00|2026-03-03 00:00:00|300025.0|300035.0|100005.0|100015.0
    b3|2026-03-03 00:00:00|2026-03-04 00:00:00|300070.0|300080.0|100005.0|100015.0
    ```

    ```python
    print(tools.t_vect_list(input="W", columns=columns).text)
    ```

    ```text
    name|start_time|end_time|west|east|south|north
    w1|2026-03-01 00:00:00|2026-03-03 00:00:00|300005.0|300015.0|100000.0|100010.0
    w2|2026-03-03 00:00:00|2026-03-05 00:00:00|300045.0|300055.0|100000.0|100010.0
    ```

    ```python
    columns = "name,start_time,end_time,points"
    print(tools.t_vect_list(input="P", columns=columns).text)
    ```

    ```text
    name|start_time|end_time|points
    p1|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    p2|2026-03-02 00:00:00|2026-03-03 00:00:00|2
    p3|2026-03-03 00:00:00|2026-03-04 00:00:00|3
    ```

    ```python
    columns = "name,start_time,end_time,lines"
    print(tools.t_vect_list(input="L", columns=columns).text)
    ```

    ```text
    name|start_time|end_time|lines
    l1|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    l2|2026-03-02 00:00:00|2026-03-03 00:00:00|1
    ```

### Select maps by their temporal relation

The first block selects the maps of `A` that are equal in time to a map of `B`,
all three. Each result map is a map of `A`: the selection registers the maps
as they are, so the result dataset `sel_equal` has no new vector maps. The
second block selects the maps of `A` that are not equal to the single map
`ev`, which has the time of `a2`: `a1` and `a3`. The third block selects the
maps of `A` that are during a map of `W` and gives them the time of that map,
**r** for the right operand. The maps `a1` and `a2` are both during `w1`, so
they get the time 1 to 3 March, and `a3` gets 3 to 5 March. A map with a new
time stamp is a new vector map, named after **basename**, so the names are
`sel_during_0`, `sel_during_1` and `sel_during_2`. The result dataset of
every block is named in the expression, and **basename** is the prefix of the
new maps; the examples give both the same name.

=== "Command line"

    ```sh
    t.vect.algebra expression="sel_equal = A : B" basename=sel_equal
    t.vect.list input=sel_equal columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="sel_not_ev = A !: tmap(ev)" basename=sel_not_ev
    t.vect.list input=sel_not_ev columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="sel_during = A {:,during,r} W" \
        basename=sel_during
    t.vect.list input=sel_during columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    sel_during_0|2026-03-01 00:00:00|2026-03-03 00:00:00
    sel_during_1|2026-03-01 00:00:00|2026-03-03 00:00:00
    sel_during_2|2026-03-03 00:00:00|2026-03-05 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    columns = "name,start_time,end_time"
    tools.t_vect_algebra(expression="sel_equal = A : B", basename="sel_equal")
    print(tools.t_vect_list(input="sel_equal", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```python
    tools.t_vect_algebra(expression="sel_not_ev = A !: tmap(ev)", basename="sel_not_ev")
    print(tools.t_vect_list(input="sel_not_ev", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```python
    tools.t_vect_algebra(expression="sel_during = A {:,during,r} W", basename="sel_during")
    print(tools.t_vect_list(input="sel_during", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    sel_during_0|2026-03-01 00:00:00|2026-03-03 00:00:00
    sel_during_1|2026-03-01 00:00:00|2026-03-03 00:00:00
    sel_during_2|2026-03-03 00:00:00|2026-03-05 00:00:00
    ```

### Check the spatial topology

Without **-s** the selection `A : B` takes the maps by time only: the squares of
`a3` and `b3` have the same day, so all three maps of `A` are selected. With
**-s** the algebra also asks for a spatial relation of the two maps. `a1` and
`b1` overlap and so do `a2` and `b2`, but `a3` is at x = 40 to 50 and `b3` at
x = 70 to 80, and `a3` is left out.

=== "Command line"

    ```sh
    t.vect.algebra expression="space_free = A : B" basename=space_free
    t.vect.list input=space_free columns=name
    ```

    ```text
    name
    a1
    a2
    a3
    ```

    ```sh
    t.vect.algebra -s expression="space_checked = A : B" basename=space_checked
    t.vect.list input=space_checked columns=name
    ```

    ```text
    name
    a1
    a2
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_vect_algebra(expression="space_free = A : B", basename="space_free")
    print(tools.t_vect_list(input="space_free", columns="name").text)
    ```

    ```text
    name
    a1
    a2
    a3
    ```

    ```python
    tools.t_vect_algebra(
        expression="space_checked = A : B", basename="space_checked", flags="s"
    )
    print(tools.t_vect_list(input="space_checked", columns="name").text)
    ```

    ```text
    name
    a1
    a2
    ```

### Use the classic algebra

The expression `W {:,contains,r} A` selects the maps of `W` that contain a map
of `A`, with the time of that map of `A`. `w1` contains `a1` and `a2`, `w2`
contains `a3`. The algebra core gives one map per related pair, three maps with
the times of `a1`, `a2` and `a3`. The classic algebra, selected with **-c**,
keeps only the last pair of each map of `W`, so it gives two maps, the times of
`a2` and `a3`. The second pair of blocks gives an expression with no result:
no map of `A` contains a map of `W`. The core creates an empty dataset
(`number_of_maps` 0), the classic algebra no dataset, and the tool ends with
status 0 in both cases and warns that the result is empty.

=== "Command line"

    ```sh
    t.vect.algebra expression="right_core = W {:,contains,r} A" \
        basename=right_core
    t.vect.list input=right_core columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    right_core_0|2026-03-01 00:00:00|2026-03-02 00:00:00
    right_core_1|2026-03-02 00:00:00|2026-03-03 00:00:00
    right_core_2|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra -c expression="right_classic = W {:,contains,r} A" \
        basename=right_classic
    t.vect.list input=right_classic columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    right_classic_0|2026-03-02 00:00:00|2026-03-03 00:00:00
    right_classic_1|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="empty_core = A {:,contains} W" basename=empty_core
    t.vect.algebra -c expression="empty_classic = A {:,contains} W" \
        basename=empty_classic
    t.list type=stvds columns=name,number_of_maps format=csv mapset=. \
        where="name LIKE 'empty%'"
    ```

    ```text
    name,number_of_maps
    empty_core,0
    ```

=== "Python (grass.tools)"

    ```python
    columns = "name,start_time,end_time"
    tools.t_vect_algebra(
        expression="right_core = W {:,contains,r} A", basename="right_core"
    )
    print(tools.t_vect_list(input="right_core", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    right_core_0|2026-03-01 00:00:00|2026-03-02 00:00:00
    right_core_1|2026-03-02 00:00:00|2026-03-03 00:00:00
    right_core_2|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```python
    tools.t_vect_algebra(
        expression="right_classic = W {:,contains,r} A",
        basename="right_classic",
        flags="c",
    )
    print(tools.t_vect_list(input="right_classic", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    right_classic_0|2026-03-02 00:00:00|2026-03-03 00:00:00
    right_classic_1|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```python
    tools.t_vect_algebra(expression="empty_core = A {:,contains} W", basename="empty_core")
    tools.t_vect_algebra(
        expression="empty_classic = A {:,contains} W",
        basename="empty_classic",
        flags="c",
    )
    print(
        tools.t_list(
            type="stvds",
            columns="name,number_of_maps",
            format="csv",
            mapset=".",
            where="name LIKE 'empty%'",
        ).text
    )
    ```

    ```text
    name,number_of_maps
    empty_core,0
    ```

### Temporal selection operators

<!-- example: shell-only -->

Each block selects from `A` or `W` and lists the result. The datasets are those
of the example "Create the datasets of the examples". The items follow the
order of the blocks; item 7 has two blocks.

1. `{:,starts}` takes the maps of `A` that start together with a map of `W`
    and end before it: `a1` starts `w1` and `a3` starts `w2`, so `a1` and `a3`.
2. `{!:,starts}` is the complement: `a2`.
3. **during** is inclusive. `a1` starts and `a2` finishes together with `w1`,
    `a3` starts together with `w2`, and `{:,during}` takes all three.
4. `W {:,contains} A` takes the maps of `W` that contain a map of `A`,
    `contains` including the maps that start or finish together: `w1` and `w2`.
5. **precedes** needs maps that touch. `tshift(B, "2 days")` has the maps from
    3 to 4, 4 to 5 and 5 to 6 March. `a1` (1 to 2 March) is separated from the
    first by a gap and gets no partner; `a2` ends where the first map starts
    and `a3` where the second starts. The result is `a2` and `a3`.
6. `equals` is read as `equal`, the spelling of the paper.
7. `{:,equal|overlap}` combines the temporal relation `equal` with the spatial
    relation `overlap`. `a1` and `b1` overlap, and so do `a2` and `b2`, but not
    `a3` and `b3`. The spatial relation is evaluated although the call has no
    **-s**: the result has two maps, where `A : B` has three. The classic
    algebra does not read spatial names in the braces; the second block, with
    **-c**, stops with an error.
8. Selections are applied from left to right: `A : B !: tmap(ev)` selects the
    maps of `A` that are equal to a map of `B`, and from them the maps that
    are not equal to `ev`, which has the time of `a2`: `a1` and `a3`.

=== "Command line"

    ```sh
    t.vect.algebra expression="sel_starts = A {:,starts} W" basename=sel_starts
    t.vect.list input=sel_starts columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="sel_not_starts = A {!:,starts} W" \
        basename=sel_not_starts
    t.vect.list input=sel_not_starts columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    ```

    ```sh
    t.vect.algebra expression="sel_inclusive = A {:,during} W" \
        basename=sel_inclusive
    t.vect.list input=sel_inclusive columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="sel_contains = W {:,contains} A" \
        basename=sel_contains
    t.vect.list input=sel_contains columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    w1|2026-03-01 00:00:00|2026-03-03 00:00:00
    w2|2026-03-03 00:00:00|2026-03-05 00:00:00
    ```

    ```sh
    t.vect.algebra expression="sel_gap = A {:,precedes} tshift(B, \"2 days\")" \
        basename=sel_gap
    t.vect.list input=sel_gap columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="sel_equals = A {:,equals} B" basename=sel_equals
    t.vect.list input=sel_equals columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="sel_overlap = A {:,equal|overlap} B" \
        basename=sel_overlap
    t.vect.list input=sel_overlap columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    ```

    ```sh
    if ! t.vect.algebra -c expression="sel_overlap_classic = A {:,equal|overlap} B" \
        basename=sel_overlap_classic 2>&1; then
        echo "t.vect.algebra failed"
    fi
    ```

    ```text
    ERROR: Unpermitted temporal relation name 'overlap'
    t.vect.algebra failed
    ```

    ```sh
    t.vect.algebra expression="sel_chain = A : B !: tmap(ev)" basename=sel_chain
    t.vect.list input=sel_chain columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

### Overlay operators

<!-- example: shell-only -->

The overlay operators combine the maps of two datasets that are related in
time, by default equal, with *v.overlay* or *v.patch*. The areas of the result
maps follow from the squares of the example "Create the datasets of the
examples": `a1` (x = 0 to 10, y = 0 to 10) and `b1` (x = 5 to 15, y = 5 to
15) overlap in a square of 5 by 5. The items
follow the order of the blocks; item 6 has two blocks.

1. `A & B` is the intersection. The pair `a1`, `b1` has the common area 25, the
    pair `a2`, `b2` too, and `a3` and `b3` have none. A map without areas is not
    registered, so the result has two maps. The second command prints the area
    of the first result map in square meters.
2. `A | B` is the union. The pair `a1`, `b1` gives three areas, 75 only in
    `a1`, 25 in both and 75 only in `b1`; the pair `a3`, `b3` gives its two
    squares, so the result has the areas 3, 3 and 2.
3. `A ^ B` is the symmetric difference: the 75 only in `a1` and the 75 only in
    `b1`, two areas with a centroid for each overlapping pair. The common square
    stays in the map as a third area without a centroid, so `areas` is 3 and
    `centroids` is 2.
4. `A ~ B` is the complement of `B` in `A`: the 75 of `a1` outside `b1`. One
    area for each pair: `a3` does not overlap `b3` and stays whole, with the
    area 100.
5. `P + L` patches the maps of two datasets with *v.patch*: `p1` and `l1`,
    one point and one line, and `p2` and `l2`, two points and one line. `p3`
    has no partner in `L`.
6. `A {&,during} W` intersects each map of `A` with the maps of `W` that
    contain it. `a2` does not touch `w1`, so its intersection has no areas and
    is left out, and the result has the maps 0 and 1. The classic algebra, in
    the second block with **-c**, numbers them in the same way.
7. The temporal operator after the relation sets the time of the result maps.
    **r** takes the time of the map of `W`, 1 to 3 and 3 to 5 March; **u** takes
    the union of both times, the same here, as the maps of `A` lie in the maps of
    `W`; without an operator the time is that of the left map.
8. With several related maps the operators aggregate: `W {&,contains} A`
    overlays `w1` with `a1` and `a2` into one map, and `w2` with `a3`. The first
    has no area, as `a1` and `a2` do not touch, and is left out; the second,
    `ov_agg_0`, has the area 50, the square x = 45 to 50.
9. The overlay operators have the same precedence and are evaluated from left
    to right, so `A | B & A` is `(A | B) & A`: the union of each pair
    intersected with the map of `A`, with the areas 2, 2 and 1. With parentheses,
    `A | (B & A)` first intersects `B` and `A`. `a3 & b3` has no areas, so the
    third map is left out and the result has the areas 2 and 2.
10. `merge(A, B)` puts the maps of both datasets into one dataset. The maps of
    the same day are listed by the order of their names.

=== "Command line"

    ```sh
    t.vect.algebra expression="ov_and = A & B" basename=ov_and
    t.vect.list input=ov_and columns=name,start_time,end_time,areas
    v.to.db -p map=ov_and_0 option=area units=meters
    ```

    ```text
    name|start_time|end_time|areas
    ov_and_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    ov_and_1|2026-03-02 00:00:00|2026-03-03 00:00:00|1
    cat|area
    1|25
    ```

    ```sh
    t.vect.algebra expression="ov_or = A | B" basename=ov_or
    t.vect.list input=ov_or columns=name,start_time,end_time,areas
    v.to.db -p map=ov_or_0 option=area units=meters
    ```

    ```text
    name|start_time|end_time|areas
    ov_or_0|2026-03-01 00:00:00|2026-03-02 00:00:00|3
    ov_or_1|2026-03-02 00:00:00|2026-03-03 00:00:00|3
    ov_or_2|2026-03-03 00:00:00|2026-03-04 00:00:00|2
    cat|area
    1|75
    2|25
    3|75
    ```

    ```sh
    t.vect.algebra expression="ov_xor = A ^ B" basename=ov_xor
    t.vect.list input=ov_xor columns=name,start_time,end_time,areas,centroids
    v.to.db -p map=ov_xor_0 option=area units=meters
    ```

    ```text
    name|start_time|end_time|areas|centroids
    ov_xor_0|2026-03-01 00:00:00|2026-03-02 00:00:00|3|2
    ov_xor_1|2026-03-02 00:00:00|2026-03-03 00:00:00|3|2
    ov_xor_2|2026-03-03 00:00:00|2026-03-04 00:00:00|2|2
    cat|area
    1|75
    2|75
    ```

    ```sh
    t.vect.algebra expression="ov_not = A ~ B" basename=ov_not
    t.vect.list input=ov_not columns=name,start_time,end_time,areas
    v.to.db -p map=ov_not_0 option=area units=meters
    ```

    ```text
    name|start_time|end_time|areas
    ov_not_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    ov_not_1|2026-03-02 00:00:00|2026-03-03 00:00:00|1
    ov_not_2|2026-03-03 00:00:00|2026-03-04 00:00:00|1
    cat|area
    1|75
    ```

    ```sh
    t.vect.algebra expression="ov_patch = P + L" basename=ov_patch
    t.vect.list input=ov_patch columns=name,start_time,end_time,points,lines
    ```

    ```text
    name|start_time|end_time|points|lines
    ov_patch_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1|1
    ov_patch_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2|1
    ```

    ```sh
    t.vect.algebra expression="ov_during = A {&,during} W" basename=ov_during
    t.vect.list input=ov_during columns=name,start_time,end_time,areas
    ```

    ```text
    name|start_time|end_time|areas
    ov_during_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    ov_during_1|2026-03-03 00:00:00|2026-03-04 00:00:00|1
    ```

    ```sh
    t.vect.algebra -c expression="ov_during_classic = A {&,during} W" \
        basename=ov_during_classic
    t.vect.list input=ov_during_classic columns=name,start_time,end_time,areas
    ```

    ```text
    name|start_time|end_time|areas
    ov_during_classic_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    ov_during_classic_1|2026-03-03 00:00:00|2026-03-04 00:00:00|1
    ```

    ```sh
    t.vect.algebra expression="ov_right = A {&,during,r} W" basename=ov_right
    t.vect.list input=ov_right columns=name,start_time,end_time,areas
    t.vect.algebra expression="ov_union = A {&,during,u} W" basename=ov_union
    t.vect.list input=ov_union columns=name,start_time,end_time,areas
    ```

    ```text
    name|start_time|end_time|areas
    ov_right_0|2026-03-01 00:00:00|2026-03-03 00:00:00|1
    ov_right_1|2026-03-03 00:00:00|2026-03-05 00:00:00|1
    name|start_time|end_time|areas
    ov_union_0|2026-03-01 00:00:00|2026-03-03 00:00:00|1
    ov_union_1|2026-03-03 00:00:00|2026-03-05 00:00:00|1
    ```

    ```sh
    t.vect.algebra expression="ov_agg = W {&,contains} A" basename=ov_agg
    t.vect.list input=ov_agg columns=name,start_time,end_time,areas
    v.to.db -p map=ov_agg_0 option=area units=meters
    ```

    ```text
    name|start_time|end_time|areas
    ov_agg_0|2026-03-03 00:00:00|2026-03-05 00:00:00|1
    cat|area
    1|50
    ```

    ```sh
    t.vect.algebra expression="ov_left = A | B & A" basename=ov_left
    t.vect.list input=ov_left columns=name,start_time,end_time,areas
    t.vect.algebra expression="ov_group = A | (B & A)" basename=ov_group
    t.vect.list input=ov_group columns=name,start_time,end_time,areas
    ```

    ```text
    name|start_time|end_time|areas
    ov_left_0|2026-03-01 00:00:00|2026-03-02 00:00:00|2
    ov_left_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2
    ov_left_2|2026-03-03 00:00:00|2026-03-04 00:00:00|1
    name|start_time|end_time|areas
    ov_group_0|2026-03-01 00:00:00|2026-03-02 00:00:00|2
    ov_group_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2
    ```

    ```sh
    t.vect.algebra expression="ov_merge = merge(A, B)" basename=ov_merge
    t.vect.list input=ov_merge columns=name,start_time,areas \
        order=start_time,name
    ```

    ```text
    name|start_time|areas
    a1|2026-03-01 00:00:00|1
    b1|2026-03-01 00:00:00|1
    a2|2026-03-02 00:00:00|1
    b2|2026-03-02 00:00:00|1
    a3|2026-03-03 00:00:00|1
    b3|2026-03-03 00:00:00|1
    ```

### Buffers and temporal functions

<!-- example: shell-only -->

The buffer functions make areas around the points, lines or areas of each map
and keep its time. The size is in meters. The temporal functions change the
time of the maps and copy the maps whose time changes.

1. `buff_p(P, 1)` buffers the points of `p1`, `p2` and `p3`: one, two and three
    circles, as the points are ten meters apart.
2. `buff_p(P, 6)` has a radius larger than half the distance of the points, so
    the circles of one map merge into one area.
3. `buff_l(L, 2)` buffers the lines: one area for each map.
4. `buff_a(A, 2)` buffers the areas: one area for each map.
5. The result of a buffer is a vector dataset, so `buff_a(buff_p(P, 1), 1)`
    buffers the circles again and keeps their number.
6. `buff_t(W, "1 day")` extends each map by one day at both ends: 28 February
    to 4 March, and 2 to 6 March.
7. `tshift(A, "1 day")` moves the maps by one day.
8. `tsnap(A)` snaps the maps to a valid topology. `A` has no gaps, so nothing
    changes and the result registers the maps `a1`, `a2` and `a3` themselves.
9. `tshift(A, "1 day") : A` selects the shifted maps that are equal in time to
    a map of `A`: the shifted `a1` (2 to 3 March) and `a2` (3 to 4 March).

=== "Command line"

    ```sh
    t.vect.algebra expression="buf_p = buff_p(P, 1)" basename=buf_p
    t.vect.list input=buf_p columns=name,start_time,end_time,points,areas
    ```

    ```text
    name|start_time|end_time|points|areas
    buf_p_0|2026-03-01 00:00:00|2026-03-02 00:00:00|0|1
    buf_p_1|2026-03-02 00:00:00|2026-03-03 00:00:00|0|2
    buf_p_2|2026-03-03 00:00:00|2026-03-04 00:00:00|0|3
    ```

    ```sh
    t.vect.algebra expression="buf_p_wide = buff_p(P, 6)" basename=buf_p_wide
    t.vect.list input=buf_p_wide columns=name,start_time,end_time,areas
    ```

    ```text
    name|start_time|end_time|areas
    buf_p_wide_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    buf_p_wide_1|2026-03-02 00:00:00|2026-03-03 00:00:00|1
    buf_p_wide_2|2026-03-03 00:00:00|2026-03-04 00:00:00|1
    ```

    ```sh
    t.vect.algebra expression="buf_l = buff_l(L, 2)" basename=buf_l
    t.vect.list input=buf_l columns=name,start_time,end_time,lines,areas
    ```

    ```text
    name|start_time|end_time|lines|areas
    buf_l_0|2026-03-01 00:00:00|2026-03-02 00:00:00|0|1
    buf_l_1|2026-03-02 00:00:00|2026-03-03 00:00:00|0|1
    ```

    ```sh
    t.vect.algebra expression="buf_a = buff_a(A, 2)" basename=buf_a
    t.vect.list input=buf_a columns=name,start_time,end_time,areas
    ```

    ```text
    name|start_time|end_time|areas
    buf_a_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    buf_a_1|2026-03-02 00:00:00|2026-03-03 00:00:00|1
    buf_a_2|2026-03-03 00:00:00|2026-03-04 00:00:00|1
    ```

    ```sh
    t.vect.algebra expression="buf_twice = buff_a(buff_p(P, 1), 1)" \
        basename=buf_twice
    t.vect.list input=buf_twice columns=name,start_time,end_time,areas
    ```

    ```text
    name|start_time|end_time|areas
    buf_twice_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    buf_twice_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2
    buf_twice_2|2026-03-03 00:00:00|2026-03-04 00:00:00|3
    ```

    ```sh
    t.vect.algebra expression="buf_time = buff_t(W, \"1 day\")" basename=buf_time
    t.vect.list input=buf_time columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    buf_time_0|2026-02-28 00:00:00|2026-03-04 00:00:00
    buf_time_1|2026-03-02 00:00:00|2026-03-06 00:00:00
    ```

    ```sh
    t.vect.algebra expression="shifted = tshift(A, \"1 day\")" basename=shifted
    t.vect.list input=shifted columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    shifted_0|2026-03-02 00:00:00|2026-03-03 00:00:00
    shifted_1|2026-03-03 00:00:00|2026-03-04 00:00:00
    shifted_2|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```sh
    t.vect.algebra expression="snapped = tsnap(A)" basename=snapped
    t.vect.list input=snapped columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="shifted_eq = tshift(A, \"1 day\") : A" \
        basename=shifted_eq
    t.vect.list input=shifted_eq columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    shifted_eq_0|2026-03-02 00:00:00|2026-03-03 00:00:00
    shifted_eq_1|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

### Conditions

<!-- example: shell-only -->

An `if` statement takes the maps of its conclusion for which the condition is
true. The first argument in braces names the temporal relation between the
condition and the conclusion; without it the maps must be equal in time. The
items follow the order of the blocks; item 1 has two blocks.

1. The first form of the paper compares the start date with 1 January 2005.
    All maps of `A` start in March 2026, so the condition is false for all of
    them: the tool warns, and the result dataset `D` is empty
    (`number_of_maps` 0). The second block moves the date to 3 March 2026, so
    the maps of `A` before it, `a1` and `a2`, are intersected with the maps of
    `B`.
2. With an else part, the maps of `B` replace the maps for which the condition
    is false: `b1`, as `a1` starts on day 1, and `a2` and `a3`.
3. Conditions join with `&&` and `||`: `a1` and `a2` start in March before the
    3rd.
4. `td(A)` is the length of each map in days, 1 for all maps of `A`.
5. The form of the paper with `td()` and `buff_t()`, with the dataset `C` of
    the first example as else part: the buffer of 1 day on both sides makes
    each map of `A` 3 days long, so the condition is true and the result `E`
    holds the maps of `B` that are within the buffered maps of `A`, here all
    three.
6. With 4 days the condition is false and the else part, `C`, is the result:
    `c1` and `c2`.
7. The relation names the maps of the condition and of the conclusion:
    `{contains}` reads "condition contains conclusion". `w1` starts on day 1,
    `w2` on day 3, so the condition is true for `w2`, and the maps of `A`
    within `w2` are `a3`.
8. The hash operator counts the maps of `A` that `W` contains: two for `w1`,
    one for `w2`. The condition selects `w1`, and the conclusion is the same
    selection with the maps of `W` that contain a map of `A`, so the result
    is `w1`.
9. The comparison operator joins two conditions on different datasets:
    `start_day(A) > 1` is true for `a2` and `a3`, `start_day(B) < 3` for `b1`
    and `b2`, and `&&` with the relation `equal` makes `a2` the only match.
10. The hash operator takes no temporal operator other than **l**. The block
    shows the error.
11. When a map has several related condition maps, the conditions are joined
    with and. With `{during}` the maps of `A` are the condition and the maps of
    `W` the conclusion: `w1` has `a1` (start day 1) and `a2` (start day 2),
    `w2` has `a3` (start day 3). Joined with and, `w1` fails because of
    `a1`, so only `w2` remains. Written `{during,|}`, the relation joins the
    conditions with or, and `w1` is true because of `a2`.

=== "Command line"

    ```sh
    t.vect.algebra expression="D = if(start_date(A) < \"2005-01-01\", A & B)" \
        basename=d
    t.list type=stvds columns=name,number_of_maps format=csv mapset=. \
        where="name = 'D'"
    ```

    ```text
    name,number_of_maps
    D,0
    ```

    ```sh
    t.vect.algebra expression="if_date = if(start_date(A) < \"2026-03-03\", A & B)" \
        basename=if_date
    t.vect.list input=if_date columns=name,start_time,end_time,areas
    ```

    ```text
    name|start_time|end_time|areas
    if_date_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    if_date_1|2026-03-02 00:00:00|2026-03-03 00:00:00|1
    ```

    ```sh
    t.vect.algebra expression="if_else = if({equal}, start_day(A) > 1, A, B)" \
        basename=if_else
    t.vect.list input=if_else columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    b1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="if_and = if(start_month(A) == 3 && start_day(A) < 3, A)" \
        basename=if_and
    t.vect.list input=if_and columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    ```

    ```sh
    t.vect.algebra expression="if_td = if(td(A) == 1, A)" basename=if_td
    t.vect.list input=if_td columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a1|2026-03-01 00:00:00|2026-03-02 00:00:00
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="E = if({contains}, td(buff_t(A, \"1 days\")) == 3, B, C)" \
        basename=e
    t.vect.list input=E columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    b1|2026-03-01 00:00:00|2026-03-02 00:00:00
    b2|2026-03-02 00:00:00|2026-03-03 00:00:00
    b3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="F = if({contains}, td(buff_t(A, \"1 days\")) == 4, B, C)" \
        basename=f
    t.vect.list input=F columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    c1|2026-03-01 00:00:00|2026-03-03 00:00:00
    c2|2026-03-03 00:00:00|2026-03-05 00:00:00
    ```

    ```sh
    t.vect.algebra expression="if_relation = if({contains}, start_day(W) > 1, A)" \
        basename=if_relation
    t.vect.list input=if_relation columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a3|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.algebra expression="if_hash = if({equal}, W {#, contains} A > 1, W {:, contains} A)" \
        basename=if_hash
    t.vect.list input=if_hash columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    w1|2026-03-01 00:00:00|2026-03-03 00:00:00
    ```

    ```sh
    t.vect.algebra expression="if_compare = if({equal}, start_day(A) > 1 {&&, equal, l} start_day(B) < 3, A)" \
        basename=if_compare
    t.vect.list input=if_compare columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    a2|2026-03-02 00:00:00|2026-03-03 00:00:00
    ```

    ```sh
    if ! t.vect.algebra expression="if_reject = if({equal}, W {#, contains, r} A > 1, W)" \
        basename=if_reject 2>&1; then
        echo "t.vect.algebra failed"
    fi
    ```

    ```text
    ERROR: The hash operator keeps the time stamps of the left maps, so it
           takes no temporal reference other than l
    t.vect.algebra failed
    ```

    ```sh
    t.vect.algebra expression="if_and_join = if({during}, start_day(A) > 1, W)" \
        basename=if_and_join
    t.vect.list input=if_and_join columns=name,start_time,end_time
    t.vect.algebra expression="if_or_join = if({during,|}, start_day(A) > 1, W)" \
        basename=if_or_join
    t.vect.list input=if_or_join columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    w2|2026-03-03 00:00:00|2026-03-05 00:00:00
    name|start_time|end_time
    w1|2026-03-01 00:00:00|2026-03-03 00:00:00
    w2|2026-03-03 00:00:00|2026-03-05 00:00:00
    ```

### Relative time and datasets of another mapset

The datasets `R` and `S` have relative time in hours: `R` holds the maps `r1`
and `r2` for the hours 0 to 1 and 1 to 2, copies of `a1` and `a2`, and `S`
holds `s1` and `s2`, copies of `b1` and `b2`. The algebra works as with
absolute time. The overlay `R & S` gives two maps with one area each, and
`tshift(R, 1)` shifts the maps by one hour. The third block shows that an
expression cannot mix the two temporal types.

The last blocks switch to a new mapset `t_vect_algebra_2`, set the region again
and use the datasets of `t_vect_algebra`. A dataset name without mapset is
looked up in the current mapset and then in the search path, which does not
hold `t_vect_algebra`, so `A` is not found, and `A@t_vect_algebra` names the
dataset. The overlay creates its new maps in the
current mapset, `t_vect_algebra_2`. The selection registers the maps of
`t_vect_algebra` as they are, so the result dataset in `t_vect_algebra_2` holds
maps from `t_vect_algebra`.

=== "Command line"

    ```sh
    for k in 1 2; do
        g.copy vector=a$k,r$k
        g.copy vector=b$k,s$k
    done
    t.create type=stvds temporaltype=relative output=R title="R" \
        description="Relative time, hours"
    t.create type=stvds temporaltype=relative output=S title="S" \
        description="Relative time, hours"
    t.register -i type=vector input=R maps=r1,r2 start=0 increment=1 unit=hours
    t.register -i type=vector input=S maps=s1,s2 start=0 increment=1 unit=hours
    t.vect.algebra expression="rel_and = R & S" basename=rel_and
    t.vect.list input=rel_and columns=name,start_time,end_time,areas
    t.vect.algebra expression="rel_shift = tshift(R, 1)" basename=rel_shift
    t.vect.list input=rel_shift columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time|areas
    rel_and_0|0|1|1
    rel_and_1|1|2|1
    name|start_time|end_time
    rel_shift_0|1|2
    rel_shift_1|2|3
    ```

    ```sh
    if ! t.vect.algebra expression="rel_mixed = R & A" basename=rel_mixed 2>&1; then
        echo "t.vect.algebra failed"
    fi
    ```

    ```text
    ERROR: Series of different temporal types or units cannot be related
    t.vect.algebra failed
    ```

    ```sh
    g.mapset -c mapset=t_vect_algebra_2
    g.region raster=elev_state_500m res=1000 -a
    t.vect.algebra expression="far_and = A@t_vect_algebra & B@t_vect_algebra" \
        basename=far_and
    t.vect.list input=far_and columns=name,mapset,start_time,areas
    t.vect.algebra expression="far_sel = A@t_vect_algebra : B@t_vect_algebra" \
        basename=far_sel
    t.vect.list input=far_sel columns=id,mapset,start_time
    ```

    ```text
    name|mapset|start_time|areas
    far_and_0|t_vect_algebra_2|2026-03-01 00:00:00|1
    far_and_1|t_vect_algebra_2|2026-03-02 00:00:00|1
    id|mapset|start_time
    a1@t_vect_algebra|t_vect_algebra|2026-03-01 00:00:00
    a2@t_vect_algebra|t_vect_algebra|2026-03-02 00:00:00
    a3@t_vect_algebra|t_vect_algebra|2026-03-03 00:00:00
    ```

    ```sh
    if ! t.vect.algebra expression="far_missing = A : B" basename=far_missing 2>&1; then
        echo "t.vect.algebra failed"
    fi
    ```

    ```text
    ERROR: Space time vector dataset <A@t_vect_algebra_2> not found
    t.vect.algebra failed
    ```

=== "Python (grass.tools)"

    ```python
    for k in (1, 2):
        tools.g_copy(vector=f"a{k},r{k}")
        tools.g_copy(vector=f"b{k},s{k}")
    for dataset in ("R", "S"):
        tools.t_create(
            type="stvds",
            temporaltype="relative",
            output=dataset,
            title=dataset,
            description="Relative time, hours",
        )
    tools.t_register(
        type="vector",
        input="R",
        maps="r1,r2",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.t_register(
        type="vector",
        input="S",
        maps="s1,s2",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.t_vect_algebra(expression="rel_and = R & S", basename="rel_and")
    columns = "name,start_time,end_time,areas"
    print(tools.t_vect_list(input="rel_and", columns=columns).text)
    tools.t_vect_algebra(expression="rel_shift = tshift(R, 1)", basename="rel_shift")
    columns = "name,start_time,end_time"
    print(tools.t_vect_list(input="rel_shift", columns=columns).text)
    ```

    ```text
    name|start_time|end_time|areas
    rel_and_0|0|1|1
    rel_and_1|1|2|1
    name|start_time|end_time
    rel_shift_0|1|2
    rel_shift_1|2|3
    ```

    ```python
    from grass.tools import ToolError

    try:
        tools.t_vect_algebra(expression="rel_mixed = R & A", basename="rel_mixed")
    except ToolError as error:
        print(error.stderr.strip())
        print("t.vect.algebra failed")
    ```

    ```text
    ERROR: Series of different temporal types or units cannot be related
    t.vect.algebra failed
    ```

    ```python
    tools.g_mapset(mapset="t_vect_algebra_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.t_vect_algebra(
        expression="far_and = A@t_vect_algebra & B@t_vect_algebra",
        basename="far_and",
    )
    columns = "name,mapset,start_time,areas"
    print(tools.t_vect_list(input="far_and", columns=columns).text)
    tools.t_vect_algebra(
        expression="far_sel = A@t_vect_algebra : B@t_vect_algebra",
        basename="far_sel",
    )
    print(tools.t_vect_list(input="far_sel", columns="id,mapset,start_time").text)
    ```

    ```text
    name|mapset|start_time|areas
    far_and_0|t_vect_algebra_2|2026-03-01 00:00:00|1
    far_and_1|t_vect_algebra_2|2026-03-02 00:00:00|1
    id|mapset|start_time
    a1@t_vect_algebra|t_vect_algebra|2026-03-01 00:00:00
    a2@t_vect_algebra|t_vect_algebra|2026-03-02 00:00:00
    a3@t_vect_algebra|t_vect_algebra|2026-03-03 00:00:00
    ```

    ```python
    try:
        tools.t_vect_algebra(expression="far_missing = A : B", basename="far_missing")
    except ToolError as error:
        print(error.stderr.strip())
        print("t.vect.algebra failed")
    ```

    ```text
    ERROR: Space time vector dataset <A@t_vect_algebra_2> not found
    t.vect.algebra failed
    ```

### Expression of the paper with points

The expression of the paper that buffers points needs datasets of points: the
datasets `A` and `B` of the first example hold areas, and `buff_p()` of a map
without points gives nothing, so the result would be empty. The example creates
the mapset `t_vect_algebra_3` and sets its region. There `A` and `B` are new
datasets of points, copies of `p1`, `p2` and `p3`, each with the days 1 and 2
March. `A` has one and two points and `B` two and three, ten meters apart. The
buffers have the radius 1, so every point has its own circle. The relations in
the braces cover every case in which two maps overlap in time, and the temporal
operator **i** gives the result the intersection of both times, here the day.
The first day has one common circle, the second two.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_algebra_3
    g.region raster=elev_state_500m res=1000 -a
    for k in 1 2; do
        g.copy vector=p$k@t_vect_algebra,pa$k
        g.copy vector=p$((k + 1))@t_vect_algebra,pb$k
    done
    for dataset in A B; do
        t.create type=stvds output=$dataset title="$dataset" \
            description="Points of the paper expression"
    done
    t.register -i type=vector input=A maps=pa1,pa2 \
        start=2026-03-01 increment="1 day"
    t.register -i type=vector input=B maps=pb1,pb2 \
        start=2026-03-01 increment="1 day"
    ```

    ```sh
    t.vect.algebra expression="D = buff_p(A, 1) {&,overlaps|overlapped|equal|during|contains,i} buff_p(B, 1)" \
        basename=d
    t.vect.list input=D columns=name,start_time,end_time,areas
    ```

    ```text
    name|start_time|end_time|areas
    d_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    d_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_vect_algebra_3", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for k in (1, 2):
        tools.g_copy(vector=f"p{k}@t_vect_algebra,pa{k}")
        tools.g_copy(vector=f"p{k + 1}@t_vect_algebra,pb{k}")
    for dataset, maps in (("A", "pa1,pa2"), ("B", "pb1,pb2")):
        tools.t_create(
            type="stvds",
            output=dataset,
            title=dataset,
            description="Points of the paper expression",
        )
        tools.t_register(
            type="vector",
            input=dataset,
            maps=maps,
            start="2026-03-01",
            increment="1 day",
            flags="i",
        )
    ```

    ```python
    tools.t_vect_algebra(
        expression="D = buff_p(A, 1) {&,overlaps|overlapped|equal|during|contains,i} buff_p(B, 1)",
        basename="d",
    )
    print(tools.t_vect_list(input="D", columns="name,start_time,end_time,areas").text)
    ```

    ```text
    name|start_time|end_time|areas
    d_0|2026-03-01 00:00:00|2026-03-02 00:00:00|1
    d_1|2026-03-02 00:00:00|2026-03-03 00:00:00|2
    ```

### Figure A3 of the publication

Figure A3 of Gebbert, Leppelt and Pebesma (2019) shows the expression of the
NOTES (section "Core and classic algebra") on datasets of January 2001. The
example creates the mapset `t_vect_algebra_4`, sets its region and creates new
datasets `A` and `B` there, so that the expression can be written as it is
printed. Their maps are copies of the squares `a1` and `b1` of the first
example: `A` has three maps of two days from 1 to 7 January 2001, `B` ten daily
maps from 1 to 10 January. The result `C` holds the first two maps of `A`,
whose start is not after 3 January, and the maps of `B` from day 5 on, which
no such map of `A` contains or equals. The maps are registered as they are,
not copied. The classic algebra (**-c**) gives the same maps.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_algebra_4
    g.region raster=elev_state_500m res=1000 -a
    for i in 1 2 3; do
        g.copy vector=a1@t_vect_algebra,fig_a_$i
    done
    for i in $(seq 1 10); do
        g.copy vector=b1@t_vect_algebra,fig_b_$i
    done
    t.create type=stvds output=A title="Figure A3, A" \
        description="Three maps of two days in January 2001"
    t.register -i type=vector input=A maps=fig_a_1,fig_a_2,fig_a_3 \
        start=2001-01-01 increment="2 days"
    t.create type=stvds output=B title="Figure A3, B" \
        description="Ten daily maps in January 2001"
    t.register -i type=vector input=B \
        maps=$(seq -s, -f "fig_b_%g" 1 10) start=2001-01-01 increment="1 day"
    t.vect.algebra \
        expression='C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)' \
        basename=fig
    t.vect.list input=C columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    fig_a_1|2001-01-01 00:00:00|2001-01-03 00:00:00
    fig_a_2|2001-01-03 00:00:00|2001-01-05 00:00:00
    fig_b_5|2001-01-05 00:00:00|2001-01-06 00:00:00
    fig_b_6|2001-01-06 00:00:00|2001-01-07 00:00:00
    fig_b_7|2001-01-07 00:00:00|2001-01-08 00:00:00
    fig_b_8|2001-01-08 00:00:00|2001-01-09 00:00:00
    fig_b_9|2001-01-09 00:00:00|2001-01-10 00:00:00
    fig_b_10|2001-01-10 00:00:00|2001-01-11 00:00:00
    ```

    ```sh
    t.vect.algebra -c --overwrite \
        expression='C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)' \
        basename=figc
    t.vect.list input=C columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    fig_a_1|2001-01-01 00:00:00|2001-01-03 00:00:00
    fig_a_2|2001-01-03 00:00:00|2001-01-05 00:00:00
    fig_b_5|2001-01-05 00:00:00|2001-01-06 00:00:00
    fig_b_6|2001-01-06 00:00:00|2001-01-07 00:00:00
    fig_b_7|2001-01-07 00:00:00|2001-01-08 00:00:00
    fig_b_8|2001-01-08 00:00:00|2001-01-09 00:00:00
    fig_b_9|2001-01-09 00:00:00|2001-01-10 00:00:00
    fig_b_10|2001-01-10 00:00:00|2001-01-11 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_vect_algebra_4", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for i in range(1, 4):
        tools.g_copy(vector=f"a1@t_vect_algebra,fig_a_{i}")
    for i in range(1, 11):
        tools.g_copy(vector=f"b1@t_vect_algebra,fig_b_{i}")
    tools.t_create(
        type="stvds",
        output="A",
        title="Figure A3, A",
        description="Three maps of two days in January 2001",
    )
    tools.t_register(
        type="vector",
        input="A",
        maps="fig_a_1,fig_a_2,fig_a_3",
        start="2001-01-01",
        increment="2 days",
        flags="i",
    )
    tools.t_create(
        type="stvds",
        output="B",
        title="Figure A3, B",
        description="Ten daily maps in January 2001",
    )
    tools.t_register(
        type="vector",
        input="B",
        maps=",".join(f"fig_b_{i}" for i in range(1, 11)),
        start="2001-01-01",
        increment="1 day",
        flags="i",
    )
    tools.t_vect_algebra(
        expression='C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)',
        basename="fig",
    )
    print(tools.t_vect_list(input="C", columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    fig_a_1|2001-01-01 00:00:00|2001-01-03 00:00:00
    fig_a_2|2001-01-03 00:00:00|2001-01-05 00:00:00
    fig_b_5|2001-01-05 00:00:00|2001-01-06 00:00:00
    fig_b_6|2001-01-06 00:00:00|2001-01-07 00:00:00
    fig_b_7|2001-01-07 00:00:00|2001-01-08 00:00:00
    fig_b_8|2001-01-08 00:00:00|2001-01-09 00:00:00
    fig_b_9|2001-01-09 00:00:00|2001-01-10 00:00:00
    fig_b_10|2001-01-10 00:00:00|2001-01-11 00:00:00
    ```

    ```python
    tools.t_vect_algebra(
        expression='C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)',
        basename="figc",
        flags="c",
        overwrite=True,
    )
    print(tools.t_vect_list(input="C", columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    fig_a_1|2001-01-01 00:00:00|2001-01-03 00:00:00
    fig_a_2|2001-01-03 00:00:00|2001-01-05 00:00:00
    fig_b_5|2001-01-05 00:00:00|2001-01-06 00:00:00
    fig_b_6|2001-01-06 00:00:00|2001-01-07 00:00:00
    fig_b_7|2001-01-07 00:00:00|2001-01-08 00:00:00
    fig_b_8|2001-01-08 00:00:00|2001-01-09 00:00:00
    fig_b_9|2001-01-09 00:00:00|2001-01-10 00:00:00
    fig_b_10|2001-01-10 00:00:00|2001-01-11 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## REFERENCES

[PLY(Python-Lex-Yacc)](https://www.dabeaz.com/ply/)

Gebbert, S., Leppelt, T., Pebesma, E., 2019. A topology based
spatio-temporal map algebra for big data analysis. Data 4, 86.
<https://doi.org/10.3390/data4020086>

## SEE ALSO

*[r.mapcalc](r.mapcalc.md), [t.list](t.list.md),
[t.rast.algebra](t.rast.algebra.md), [t.rast3d.algebra](t.rast3d.algebra.md),
[t.register](t.register.md), [t.select](t.select.md),
[t.vect.list](t.vect.list.md), [v.buffer](v.buffer.md),
[v.in.region](v.in.region.md), [v.overlay](v.overlay.md),
[v.patch](v.patch.md)*,
[temporal data processing](temporalintro.md)

## AUTHORS

Thomas Leppelt, Soeren Gebbert, Thünen Institute of Climate-Smart
Agriculture
