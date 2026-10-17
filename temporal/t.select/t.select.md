## DESCRIPTION

*t.select* performs selection of maps that are registered in space time
datasets using temporal algebra.

### PROGRAM USE

The module expects an **expression** as input parameter in the following
form:

`"result = expression"`

The statement structure is similar to r.mapcalc, see
[r.mapcalc](r.mapcalc.md). Where **result** represents the name of a
space time dataset (STDS)that will contain the result of the calculation
that is given as **expression** on the right side of the equality sign.
These expression can be any valid or nested combination of temporal
operations and functions that are provided by the temporal algebra.  
The temporal algebra works with space time datasets of any type (STRDS,
STR3DS and STVDS). The algebra provides methods for map selection from
STDS based on their temporal relations. It is also possible to
temporally shift maps, to create temporal buffer and to snap time
instances to create a valid temporal topology. Furthermore expressions
can be nested and evaluated in conditional statements (if, else
statements). Within if-statements the algebra provides temporal
variables like start time, end time, day of year, time differences or
number of maps per time interval to build up conditions. These
operations can be assigned to space time datasets or to the results of
operations between space time datasets.

The type of the input space time datasets must be defined with the input
parameter **type**. Possible options are STRDS, STVDS or STR3DS. The
default is set to space time raster datasets (STRDS).

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

Maps whose temporal extent is changed by a temporal operator (for example
`{:,during,r}`) cannot stay the maps of the input dataset. They are copied
to new maps that are named after the result dataset: the dataset `C` in
`C = A {:,during,r} B` contains the maps `C_1`, `C_2` and so on. Existing
maps with these names are only overwritten with the **--overwrite** flag.
Maps whose extent is not changed are registered in the result dataset
without being copied.

## TEMPORAL ALGEBRA

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

### Core and classic algebra

Since GRASS 8.6, *t.select* selects with the functions of the Python package
`grass.temporal.algebra`, as *t.rast.algebra* and *t.vect.algebra* do. The
previous implementation stays available as the classic algebra, so that
published results remain reproducible. The classic algebra is a set of
rules of the same functions: it reads the syntax of the previous
implementation and applies its rules for relations and order. The flag
**-c** selects it for one call, the environment variable
`GRASS_TEMPORAL_ALGEBRA=classic` for a whole session or script;
`GRASS_TEMPORAL_ALGEBRA=core` or an unset or empty variable selects the
new algebra, and the flag takes precedence over the variable.

*t.select* only selects and retimes maps, it computes none, so most
differences between the two algebras do not reach it. An expression that
selects no map creates an empty space time dataset in both algebras. These
points differ:

1. **Spatial relations need -s.** A spatial relation in an operator, such as
   `{:,equal|overlap}`, is read only by the new algebra, needs the flag
   **-s** and a temporal relation to go with it; without the flag the
   algebra stops with an error. The classic algebra reports an error for
   the name of a spatial relation, with and without **-s**.

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

5. **Mixing dataset types.** The classic algebra can pull maps of another
   dataset type into a selection with `strds()`, `str3ds()` and `stvds()`;
   the new algebra does not, and reports a syntax error. Use **-c** for such
   an expression. The functions are written in lower case, `str3ds(A)`; the
   classic algebra also reads the capitals of the paper, `STRDS(A)`,
   `STR3DS(A)` and `STVDS(A)`, which the previous implementation refused. A
   capital name is a function only before an opening parenthesis, so that a
   dataset may be named `STRDS`. Other spellings, such as `Str3ds(A)`, are a
   syntax error.

6. **Copy names in a mixed result.** When a result mixes maps registered
   unchanged with retimed maps, the copied maps are named `<result>_1`,
   `<result>_2`, ... in the time order of the result. The classic algebra
   numbers them by their position among all result maps, so the suffixes can
   differ; the maps and their time stamps are the same. If three maps are
   registered unchanged before three copies, the copies are `C_1` to `C_3`
   in the new algebra and `C_4` to `C_6` in the classic one:

   ```sh
   C = merge(A {:,during,l} D, A {:,during,r} D)
   ```

7. **Negative buffer.** A negative size in `buff_t()` shrinks the maps
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

In Python, both algebras raise `SyntaxError` for an expression they cannot
read, and `FatalError` for a missing dataset and, without overwrite, for an
existing result. The new algebra raises `ValueError` for an expression it
reads but cannot select, such as `A + B`, and for a spatial relation without
**-s**, where the classic algebra raises `SyntaxError`. The tool stops with
the error message in both algebras.

Two corrections apply to both algebras, and to *t.rast.algebra*,
*t.rast3d.algebra* and *t.vect.algebra* as well, so **-c** gives the rules of
the previous algebra, not the results of a particular release. First,
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

The classic algebra gives the results of the previous implementation, with
the exceptions below. In these cases the previous implementation ended in
an error that had no reason or reported the wrong error. **-c** now gives
the result described here; the new algebra never had these errors. Results
of earlier GRASS versions that used one of these forms need a new run.

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

#### Differences from the previous implementation

The differences in message texts, in the debug output of the Python
parser, in the order of errors and in the error for an existing result that
[t.rast.algebra](t.rast.algebra.md) lists apply here likewise. Three points
change the outcome of an expression. The previous implementation refused the
relation name `equals` and the capital function names `STRDS(A)`,
`STR3DS(A)` and `STVDS(A)` with a syntax error, where the classic algebra
reads them as `equal` and as the functions in lower case. A relation over a
list that mixes maps of absolute and of relative time, which stopped the
previous implementation with a `TypeError`, selects maps here, as in
*t.rast.algebra*: maps of the two types relate to nothing.

## EXAMPLES

Select all maps from space time dataset A which have equal time stamps
with space time dataset B and C and are earlier that Jan. 1. 2005 and
store them in space time dataset D.

```sh
D = if(start_date(A) < "2005-01-01", A : B : C)
```

Select all maps from space time dataset A which contains more than three
maps of space time dataset B, else select maps from C with time stamps
that are not equal to A and store them in space time dataset D.

```sh
D = if(A {#, contains} B > 3, A {:, contains} B, C)
```

Select all maps from space time dataset B which are during the temporal
buffered space time dataset A with a map interval of three days, else
select maps from C and store them in space time dataset D.

```sh
D = if({contains}, td(buff_t(A, "1 days")) == 3, B, C)
```

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
