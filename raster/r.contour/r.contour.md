## DESCRIPTION

*r.contour* produces a vector map of specified contours from input
raster map. Contours can be produced using a comma-separated list of
values in **levels**, or at some regular increment using the **step**
parameter, optionally limited by **minlevel** and **maxlevel**.

With **step**, the levels are the values `a + k * step` for whole numbers
`k` (negative ones included). The anchor `a` is **minlevel** if it is given,
else 0. Only levels between **minlevel** and **maxlevel** (where given) and
between the minimum and maximum cell value of the **input** raster map are
created; both ends are included. A **maxlevel** that is not on the grid is
not a level itself. If the values of the map lie wholly outside the limits,
no level and no line is created. A **minlevel** above **maxlevel** is an
error. With a list of **levels**, **minlevel** and **maxlevel** are ignored,
as is the step.

A cell whose value equals a level is moved off the level by a tiny amount
before the lines are traced, so that the lines do not run exactly through the
cell centres. A level equal to the lowest or the highest value in the current
region still gets a line through the cells of that value; a value held by a
single cell gives a single point, which is not written (see **cut**).

## NOTES

If the input map has no values, *r.contour* warns and creates an empty vector
map, with a step as with a list of levels.

If the region has fewer than two rows or columns, no cell lies between four
values and no line can be traced. *r.contour* then warns once, also with
**--quiet**, and creates an empty vector map.

Null cells, also the cells outside a raster mask, count as cells outside the
region. A contour line ends between the last two cells with values, as at the
border of the region, so a map whose null cells surround a rectangle gives the
same lines as the same map in the region of that rectangle. Closed lines
are created also where they run only through the cells at the border of the
region or along null cells.

*r.contour* will either step through incremental contours or produce
contours from a list of levels, not both. If both a list of levels and a
step are specified, the list will be produced and the step will be
ignored.

Zero is treated as a valid data value by *r.contour*.

If a contour level exactly matches a category value in the raster map,
the contour line may backtrack on itself, causing illegal arcs to be
produced in the output vector map.

The optional **cut** parameter sets the minimum number of points of a
contour line in the **output** vector map; lines with fewer points are left
out. It acts like a filter, omitting spurs, small closed lines, etc., making
the output more generalized. The points are counted after the traced lines
have been snapped, broken at intersections and merged; snapping joins points
that lie very close together, as on a line through cells whose value equals
the level. Lines joined at their end points, such as the pieces of a line
broken where it touches another one, count as one group: the group is kept
or left out whole, with each joint counted once, so that no line gets a gap.
A single point is never written, whatever **cut** says.

## EXAMPLES

In the Spearfish dataset, produce a vector contour map from input raster
*elevation.dem* with contour levels from 1000m to 2000m, 100m contour
step, and a minimum of 200 input raster points contributing to the
contour line:

```sh
r.contour input=elevation.dem output=elevation_dem_contours \
          minlevel=1000 maxlevel=2000 step=100 cut=200
```

For an example of using levels with *r.contour* this example uses the
elevation map from the North Carolina database:

```sh
g.region raster=elevation
r.contour in=elevation out=contours levels=60,90,120,150 --o
d.mon wx0
d.rast elevation_shade
d.vect contours color=red
```

![r.contours example](r_contour_using_levels.png)  
*Contour lines shown on shaded terrain map*

For an example of using steps with *r.contour* this example uses the
LiDAR data derived elevation map from the North Carolina database:

```sh
g.region raster=elev_lid792_1m -p
r.contour input=elev_lid792_1m output=elev_lid792_1m_contours \
          minlevel=100 maxlevel=150 step=10
```

## AUTHORS

Terry Baker, U.S. Army Construction Engineering Research Laboratory  
3/2001: cut parameter and fixes by Andrea Aime (<aaime@libero.it>)
