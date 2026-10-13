## DESCRIPTION

*t.rast3d.algebra* performs temporal and spatial map algebra operations
on space time 3D raster datasets (STR3DS) by using the temporal 3D
raster algebra.

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
this spatial relation in addition to the temporal one. The relation is
evaluated in three dimensions: two maps with the same depth range are not
related as *overlap*, even if they overlap in the horizontal plane.

Maps that are related in space are computed in the current 3D region, in
both algebras: *r3.mapcalc* cannot compute in the union of the regions of
its input maps.

### Core and classic algebra

Since GRASS 8.6, *t.rast3d.algebra* computes its expressions with the
functions of the Python package `grass.temporal.algebra`, as
*t.rast.algebra* does. The previous implementation stays available as the
classic algebra, so that published results remain reproducible. The flag
**-c** selects it for one call, the environment variable
`GRASS_TEMPORAL_ALGEBRA=classic` for a whole session or script;
`GRASS_TEMPORAL_ALGEBRA=core` or an unset variable selects the new
algebra, and the flag takes precedence over the variable. In Python,
`TemporalRaster3DAlgebraParser` takes the keyword `classic=True` for the
same purpose. The granularity mode (**-g**) always uses the classic
algebra.

The two algebras differ in the following points. The examples use four
daily 3D raster maps in A with the values 1 to 4, two maps of two days in B
that start with A, and time instances in I.

1. **One result per conclusion map.** If a map of the conclusion of an
   `if` has several related condition maps, their conditions are joined
   with and; written as `{during,|}`, the relation joins them with or. The
   classic algebra gives one result for each pair of condition map and
   conclusion map, so that a conclusion map can occur several times, and
   does not read the form `{during,|}`. The first expression keeps the
   cells of B where both maps of A within the map of B are greater than 1,
   the second where one of them is:

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
   all of its related right maps in every result. The first expression
   gives four maps, the time stamps of A with the values of B; the classic
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
   `if()` of *r3.mapcalc* with two arguments. A map that is false
   everywhere is not registered unless **-n** is set. This expression
   registers the maps of value 3 and 4, with **-n** also the first two
   maps as null maps; the classic algebra registers four maps, the first
   two with the value 0:

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
   time datasets. This expression is a syntax error in the classic
   algebra:

   ```sh
   C = A * (map(L) + 1)
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

In Python, both algebras raise `SyntaxError` for an expression they cannot
read. For one they cannot compute, such as `if(end_doy(I) > 0, I)`, the new
algebra raises `ValueError` or `TypeError`, where the classic algebra
raises `FatalError`. Both raise `FatalError` for a missing dataset and,
without overwrite, for an existing result. Without
`tgis.init(raise_fatal_error=True)`, the classic algebra raises
`SystemExit` instead of `FatalError` for some of these errors, such as an
existing result. The tool stops with the error message in both algebras.

Two corrections apply to both algebras, and to *t.rast.algebra*,
*t.select* and *t.vect.algebra* as well, so **-c** gives the rules of the
previous algebra, not the results of a particular release. First,
`if({R}, condition, conclusion)` reads "condition R conclusion":
`if({contains}, start_doy(A) > 0, B)` gives the maps of B that lie within
a map of A, where earlier versions gave the maps of B that contain a map of
A. Second, with a temporal relation beyond `equal`, the else part of a
condition on temporal variables also takes the maps that no condition map
is related to. Figure A3 of Gebbert, Leppelt and Pebesma (2019) needs both:
A has maps from day 1 to 3, 3 to 5 and 5 to 7 of January 2001, B has daily
maps from day 1 to 10, and this expression gives the first two maps of A
and the maps of B from day 5 on, as the figure shows:

```sh
C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)
```

Results that rely on the previous reading direction or else rule need the
GRASS version they were computed with. The section "Core and classic
algebra" in the NOTES of [t.rast.algebra](t.rast.algebra.md) describes
both corrections.

## REFERENCES

[PLY(Python-Lex-Yacc)](https://www.dabeaz.com/ply/)

Gebbert, S., Leppelt, T., Pebesma, E., 2019. A topology based
spatio-temporal map algebra for big data analysis. Data 4, 86.
<https://doi.org/10.3390/data4020086>

## SEE ALSO

*[t.rast.algebra](t.rast.algebra.md),
[t.rast3d.mapcalc](t.rast3d.mapcalc.md), [r.mapcalc](r.mapcalc.md),
[t.vect.algebra](t.vect.algebra.md), [t.select](t.select.md)*

## AUTHORS

Thomas Leppelt, Sören Gebbert, Thünen Institute of Climate-Smart
Agriculture
