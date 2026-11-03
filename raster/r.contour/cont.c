/****************************************************************************
 *
 * MODULE:       r.contour
 *
 * AUTHOR(S):    Terry Baker - CERL
 *               Andrea Aime <aaime liberto it>
 *
 * PURPOSE:      Produces a vector map of specified contours from a
 *               raster map layer.
 *
 * SPDX-FileCopyrightText: 2001 GRASS Development Team
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 ***************************************************************************/
/* Algorithm comment from Jim Westervelt:
   It appears that the code is doing a linear interpolation between cells and
   finding where a given contour crosses through each cell.  In the end,
   strings of coordinates are generated for user selected contours.  In GRASS,
   these are lines and not necessarily polygons.
 */

#include <stdio.h>
#include <math.h>
#include <grass/gis.h>
#include <grass/raster.h>
#include <grass/vector.h>
#include <grass/glocale.h>
#include "local_proto.h"

struct cell {
    DCELL z[4];
    int r, c;
    int edge;
};

/* Flags of a cell (four nodes) in the array square. A cell is part of the
   surface when all four nodes have values. Its edge e is a border edge when
   the cell across it is not part of the surface, because it lies outside the
   region or has a null node. A null node counts as a node outside the region:
   lines end at the last edge between two nodes with values, as at the border
   of the region. NEXT_TO_NULL marks a cell on the surface with a border edge
   to a cell with a null node. */
#define ON_SURFACE   16
#define BORDER(e)    (1 << (e))
#define NEXT_TO_NULL 32

static unsigned char **mark_squares(DCELL **, int, int, int *);
static int counts_edges(unsigned char);
static int getnewcell(struct cell *, int, int, DCELL **, unsigned char **);
static void newedge(struct cell *);
static int findcrossing(struct cell *, double, struct Cell_head,
                        struct line_pnts *);
static void getpoint(struct cell *curr, double, struct Cell_head,
                     struct line_pnts *);

void contour(double levels[], int nlevels, struct Map_info Map, DCELL **z,
             struct Cell_head Cell, int n_cut)
{
    /* Lines with an end are started from the border edges in this order:
       top, bottom, left, right. */
    static const int border_order[4] = {0, 2, 3, 1};
    int nrow, ncol;         /* number of rows and columns in current region */
    int startrow, startcol; /* start row and col of current line */
    int n, i, j, k, pass;   /* loop counters */
    double level;           /* current contour level */
    char **hit;             /* array of flags--1 if Cell has been hit;  */
    char **used;            /* edges a line has passed, see counts_edges */
    unsigned char **square; /* ON_SURFACE and BORDER flags of each cell */
    int has_nulls;          /* 1 if a cell is not part of the surface */
    /* per edge and row: columns of the first and last cell with that
       border edge */
    int *first[4], *last[4];
    int edge;  /* border edge of the current start */
    int entry; /* edge by which the line entered a cell */

    /*  0 if Cell is still to be checked */
    struct line_pnts *Points;
    struct line_cats *Cats;
    int outside; /* 1 if line is exiting the surface; 0 otherwise */
    struct cell current;
    int p1, p2;     /* indexes to end points of cell edges */
    int min_points; /* fewest points of a line that is written */

    Points = Vect_new_line_struct();
    Cats = Vect_new_cats_struct();

    nrow = Cell.rows;
    ncol = Cell.cols;

    /* A traced line has a single point where the level touches the surface
       only around a node: when every crossing on the edges around a node
       lies closer to it than the coordinates can tell apart, getpoint()
       adds the node once. This happens at a node whose neighbors all lie on
       one side of the level and whose value is the level (displaceMatrix()
       moves the value 0 by nothing and other values by so little that the
       points become one at large coordinates) or differs from it by a few
       units in the last place, also at small coordinates (seen 2026-11-03
       with tests/r_contour_single_point_test.py). Lines do not run through
       cells with a null node, so nodes of the level that no cell of the
       surface joins, as on a staircase of null cells, are such points too.
       A single point is no line, and Vect_break_lines() in main.c ends
       r.contour on it ("Intersection with points is not yet supported"), so
       it is never written, whatever cut says. */
    min_points = (n_cut > 2) ? n_cut : 2;

    /* A line runs through cells of four nodes, which needs two rows and two
       columns. With fewer there is no cell and no line. */
    if (nrow < 2 || ncol < 2) {
        G_warning(_("The region has fewer than two rows or columns, "
                    "no contour lines are created"));
        Vect_destroy_line_struct(Points);
        Vect_destroy_cats_struct(Cats);
        return;
    }

    hit = (char **)G_malloc((nrow - 1) * sizeof(char *));
    for (i = 0; i < nrow - 1; i++)
        hit[i] = (char *)G_malloc((ncol - 1) * sizeof(char));

    used = (char **)G_malloc((nrow - 1) * sizeof(char *));
    for (i = 0; i < nrow - 1; i++)
        used[i] = (char *)G_malloc((ncol - 1) * sizeof(char));

    square = mark_squares(z, nrow, ncol, &has_nulls);

    /* The border passes visit only the columns between the first and the
       last cell of a row that has the edge, so that without null cells they
       visit the cells on the border of the region, as before, and not every
       cell four times for each level. */
    for (k = 0; k < 4; k++) {
        first[k] = (int *)G_malloc((nrow - 1) * sizeof(int));
        last[k] = (int *)G_malloc((nrow - 1) * sizeof(int));
        for (i = 0; i < nrow - 1; i++) {
            first[k][i] = 0;
            last[k][i] = -1;
            for (j = 0; j < ncol - 1; j++) {
                if (square[i][j] & BORDER(k)) {
                    if (last[k][i] < 0)
                        first[k][i] = j;
                    last[k][i] = j;
                }
            }
        }
    }

    G_message(n_("Writing vector contour (one level)...",
                 "Writing vector contours (total levels %d)...", nlevels),
              nlevels);

    for (n = 0; n < nlevels; n++) {
        level = levels[n];
        G_percent(n + 1, nlevels, 2); /* print progress */

        /* initialize hit array */
        for (i = 0; i < nrow - 1; i++) {
            for (j = 0; j < ncol - 1; j++) {
                hit[i][j] = 0;
                used[i][j] = 0;
            }
        }

        /* Start a line at each crossed border edge. Without null cells these
           are the edges on the border of the region, visited in the same
           order as before: the top and the bottom row of cells from left to
           right, then the left and the right column of cells from top to
           bottom. A null cell counts as a cell outside the region, so the
           edges along null cells are border edges too. */
        for (k = 0; k < 4; k++) {
            edge = border_order[k];
            for (startrow = 0; startrow <= nrow - 2; startrow++) {
                for (startcol = first[edge][startrow];
                     startcol <= last[edge][startrow]; startcol++) {
                    if (!(square[startrow][startcol] & BORDER(edge)))
                        continue;
                    /* look for starting point of new line */
                    if (counts_edges(square[startrow][startcol])
                            ? used[startrow][startcol] & (1 << edge)
                            : hit[startrow][startcol])
                        continue;
                    current.r = startrow;
                    current.c = startcol;
                    current.edge = edge;

                    outside = getnewcell(&current, nrow, ncol, z, square);

                    p1 = current.edge;
                    p2 = (current.edge + 1) % 4;
                    if (!checkedge(current.z[p1], current.z[p2], level))
                        continue;

                    getpoint(&current, level, Cell, Points);
                    /* while not off an edge, follow line */
                    while (!outside) {
                        entry = current.edge;
                        hit[current.r][current.c] |=
                            findcrossing(&current, level, Cell, Points);
                        used[current.r][current.c] |=
                            (1 << entry) | (1 << current.edge);
                        newedge(&current);
                        outside = getnewcell(&current, nrow, ncol, z, square);
                    }
                    if (Points->n_points >= min_points) {
                        Vect_reset_cats(Cats);
                        Vect_cat_set(Cats, 1, n + 1);
                        Vect_write_line(&Map, GV_LINE, Points, Cats);
                    }
                    Vect_reset_line(Points);
                }
            }
        }

        /* Check each interior Cell for closed lines. The first pass takes
           the cells without a border edge: without null cells these are the
           cells off the border of the region, as before; within null cells
           around a rectangle they are the cells the region of that rectangle
           checks, in the same order, so a closed line starts at the same
           point there. The second pass, only for a map with null cells,
           takes the other interior cells, those along null cells (a cell on
           the surface with a border edge has flags above ON_SURFACE). Before
           2026-11-02 the search went over all interior cells and found a
           closed line that runs only through cells along null cells; the
           second pass keeps it. The region of the rectangle loses such a
           line, because a closed line that runs only through the cells
           along the border of the region is not searched, then as now. */
        for (pass = 0; pass < (has_nulls ? 2 : 1); pass++) {
            for (startrow = 1; startrow <= nrow - 3; startrow++) {
                for (startcol = 1; startcol <= ncol - 3; startcol++) {
                    /* look for starting point of new line */
                    if (pass == 0 ? square[startrow][startcol] != ON_SURFACE
                                  : square[startrow][startcol] <= ON_SURFACE)
                        continue;
                    if (hit[startrow][startcol])
                        continue;
                    current.r = startrow;
                    current.c = startcol;
                    current.edge = 0;
                    p1 = current.edge;
                    p2 = current.edge + 1;

                    outside = getnewcell(&current, nrow, ncol, z, square);
                    if (outside ||
                        !checkedge(current.z[p1], current.z[p2], level))
                        continue;

                    getpoint(&current, level, Cell, Points);
                    hit[current.r][current.c] |=
                        findcrossing(&current, level, Cell, Points);
                    newedge(&current);
                    outside = getnewcell(&current, nrow, ncol, z, square);

                    /* while not back to starting point, follow line */
                    while (!outside &&
                           ((current.edge != 0) || ((current.r != startrow) ||
                                                    (current.c != startcol)))) {
                        hit[current.r][current.c] |=
                            findcrossing(&current, level, Cell, Points);
                        newedge(&current);
                        outside = getnewcell(&current, nrow, ncol, z, square);
                    }
                    /* A trace of the second pass that leaves the surface is
                       a piece of a line with ends that the border passes
                       lost: both ends lie in saddle cells on the border of
                       the region whose hit flag the other segment set (at
                       null cells the passes ask the edge, see
                       counts_edges). The region of the rectangle loses that
                       line as well, and the piece would end inside the
                       surface, so it is not written. */
                    if (pass == 1 && outside) {
                        Vect_reset_line(Points);
                        continue;
                    }
                    if (Points->n_points >= min_points) {
                        Vect_reset_cats(Cats);
                        Vect_cat_set(Cats, 1, n + 1);
                        Vect_write_line(&Map, GV_LINE, Points, Cats);
                    }
                    Vect_reset_line(Points);
                }
            }
        }
    } /* for levels */

    for (k = 0; k < 4; k++) {
        G_free(first[k]);
        G_free(last[k]);
    }
    for (i = 0; i < nrow - 1; i++) {
        G_free(hit[i]);
        G_free(used[i]);
        G_free(square[i]);
    }
    G_free(hit);
    G_free(used);
    G_free(square);
    Vect_destroy_line_struct(Points);
    Vect_destroy_cats_struct(Cats);
}

/***************************************************************************
mark_squares
returns the ON_SURFACE and BORDER flags of every cell of four nodes and sets
has_nulls to 1 if a cell is not part of the surface, else to 0
***************************************************************************/
static unsigned char **mark_squares(DCELL **z, int nrow, int ncol,
                                    int *has_nulls)
{
    unsigned char **square;
    int r, c;

    *has_nulls = 0;
    square = (unsigned char **)G_malloc((nrow - 1) * sizeof(unsigned char *));
    for (r = 0; r < nrow - 1; r++) {
        square[r] = (unsigned char *)G_malloc((ncol - 1) * sizeof(char));
        for (c = 0; c < ncol - 1; c++) {
            if (Rast_is_d_null_value(&z[r][c]) ||
                Rast_is_d_null_value(&z[r][c + 1]) ||
                Rast_is_d_null_value(&z[r + 1][c + 1]) ||
                Rast_is_d_null_value(&z[r + 1][c])) {
                square[r][c] = 0;
                *has_nulls = 1;
            }
            else
                square[r][c] = ON_SURFACE;
        }
    }
    for (r = 0; r < nrow - 1; r++) {
        for (c = 0; c < ncol - 1; c++) {
            if (!(square[r][c] & ON_SURFACE))
                continue;
            if (r == 0)
                square[r][c] |= BORDER(0);
            else if (!(square[r - 1][c] & ON_SURFACE))
                square[r][c] |= BORDER(0) | NEXT_TO_NULL;
            if (c == ncol - 2)
                square[r][c] |= BORDER(1);
            else if (!(square[r][c + 1] & ON_SURFACE))
                square[r][c] |= BORDER(1) | NEXT_TO_NULL;
            if (r == nrow - 2)
                square[r][c] |= BORDER(2);
            else if (!(square[r + 1][c] & ON_SURFACE))
                square[r][c] |= BORDER(2) | NEXT_TO_NULL;
            if (c == 0)
                square[r][c] |= BORDER(3);
            else if (!(square[r][c - 1] & ON_SURFACE))
                square[r][c] |= BORDER(3) | NEXT_TO_NULL;
        }
    }
    return square;
}

/***************************************************************************
counts_edges
returns 1 if the border passes ask the cell whether the start edge was passed
by a line (bit per edge in used), 0 if they ask whether the cell was hit

The flag in hit marks a saddle cell (four crossings) once a segment through
its edge 0 is traced. If the other segment ends on a border edge of the cell,
a border pass that asks hit never starts it, and the line is lost unless it
is traced from its other end. The edge is asked instead
- in a cell with border edges on two opposite sides, which lies in a strip
  one cell wide (in a region of two rows or two columns every cell does):
  both segments of a saddle there end on border edges;
- in a cell next to a cell with a null node: before 2026-11-02 lines were
  not started at null cells, so these lines were drawn from inside and must
  not be lost now.
Other cells, those at the border of a region of three rows and columns or
more, ask hit as before, so the lines of maps without null cells stay the
same, including the lines lost there.
***************************************************************************/
static int counts_edges(unsigned char flags)
{
    return (flags & NEXT_TO_NULL) ||
           (flags & (BORDER(0) | BORDER(2))) == (BORDER(0) | BORDER(2)) ||
           (flags & (BORDER(1) | BORDER(3))) == (BORDER(1) | BORDER(3));
}

/***************************************************************************
getnewcell
if cell is in range and part of the surface (no null node), finds data values
of corner points of current cell
 returns 0
else returns 1
***************************************************************************/
static int getnewcell(struct cell *current, int nrow, int ncol, DCELL **z,
                      unsigned char **square)
{

    if ((current->r >= 0) && (current->r <= nrow - 2) && (current->c >= 0) &&
        (current->c <= ncol - 2) &&
        (square[current->r][current->c] & ON_SURFACE)) {
        current->z[0] = z[current->r][current->c];
        current->z[1] = z[current->r][current->c + 1];
        current->z[2] = z[current->r + 1][current->c + 1];
        current->z[3] = z[current->r + 1][current->c];

        return 0;
    }
    return 1;
}

/*******************************************************************
newedge-updates edge number and row and col to those of next cell
*******************************************************************/
static void newedge(struct cell *current)
{
    switch (current->edge) {
    case 0:
        current->r -= 1;
        current->edge = 2;
        break;
    case 1:
        current->c += 1;
        current->edge = 3;
        break;
    case 2:
        current->r += 1;
        current->edge = 0;
        break;
    case 3:
        current->c -= 1;
        current->edge = 1;
        break;
    default:
        G_fatal_error(_("Illegal edge number"));
    }
}

/***********************************************************************
  findcrossing-- decides which edge exit point from cell is on and changes
  value of edge.
  Returns 1 if the cell need not be checked again: always with two
  crossings, with four (a saddle) if the line entered or left by edge 0;
  0 otherwise.
****************************************************************************/
static int findcrossing(struct cell *current, double level,
                        struct Cell_head Cell, struct line_pnts *Points)
{
    int i, j;
    int numcross;   /* number of crossings found in this Cell */
    int edgehit[4]; /* hit flag for each edge of Cell */
    int cellhit = 0;
    double mid;

    numcross = 0;
    for (i = 0; i < 4; i++) {
        edgehit[i] = 0;
        edgehit[i] = checkedge(current->z[i], current->z[(i + 1) % 4], level);
        if (edgehit[i])
            numcross++;
    }
    if (numcross == 2) {
        cellhit = 1;
        edgehit[current->edge] = 0;
        for (j = 0; j < 4; j++) {
            if (edgehit[j]) {
                current->edge = j;
                getpoint(current, level, Cell, Points);
                break;
            }
        }
    }
    else {
        /* Four crossings, a saddle. All four nodes of a cell on the surface
           have values (getnewcell), so going round the cell the level is
           crossed an even number of times, and the edge the line entered by
           is one of them: there are two or four crossings. Before 2026-11-02
           a cell with a null node could have one or three, and r.contour
           counted them and warned "crossings found". */
        if (current->edge == 0)
            cellhit = 1;

        mid =
            (current->z[0] + current->z[1] + current->z[2] + current->z[3]) / 4;
        if (checkedge(mid, current->z[current->edge], level))
            current->edge = (current->edge == 0) ? 3 : current->edge - 1;
        else
            current->edge = (current->edge == 3) ? 0 : current->edge + 1;
        getpoint(current, level, Cell, Points);

        if (current->edge == 0)
            cellhit = 1;
    }

    return cellhit;
}

/************************************************************************
getpoint-- finds crossing point using linear interpolation,
          converts from row-column to x-y space, and adds point to current line.
************************************************************************/
static void getpoint(struct cell *curr, double level, struct Cell_head Cell,
                     struct line_pnts *Points)
{
    double x, y;
    double ratio;
    int p1, p2;

    p1 = curr->edge;
    p2 = (curr->edge + 1) % 4;
    /* Every caller has checked that the level lies between the two values
       (checkedge), which is false for equal values and for a null value
       (NaN), so the denominator is not zero and both values are numbers. */
    ratio = (level - curr->z[p1]) / (curr->z[p2] - curr->z[p1]);

    switch (curr->edge) {

    case 0:
        y = curr->r;
        x = curr->c + ratio;
        break;
    case 1:
        y = curr->r + ratio;
        x = curr->c + 1;
        break;
    case 2:
        y = curr->r + 1;
        x = curr->c + 1 - ratio;
        break;
    case 3:
        y = curr->r + 1 - ratio;
        x = curr->c;
        break;
    default:
        G_fatal_error(_("Edge number out of range"));
    }
    /* convert r/c values to x/y values */

    y = Cell.north - (y + .5) * Cell.ns_res;
    x = Cell.west + (x + .5) * Cell.ew_res;

    if (Points->n_points == 0 ||
        (Points->n_points > 0 && (Points->x[Points->n_points - 1] != x ||
                                  Points->y[Points->n_points - 1] != y))) {
        Vect_append_point(Points, x, y, level);
    }
}

/***********************************************************************
checkedge--returns 1 if level is between values d1 & d2;
                   0 otherwise.
*********************************************************************/
int checkedge(DCELL d1, DCELL d2, double level)
{
    if (((d1 <= level) && (d2 > level)) || ((d1 > level) && (d2 <= level)))
        return 1;

    return 0;
}

/*********************************************************************/
