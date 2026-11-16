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

#ifndef __LOCAL_PROTO_H__
#define __LOCAL_PROTO_H__

/* The lowest (index 0) and the highest (index 1) value read, when it is a
   level that would get no line after the move of displaceMatrix(). While
   the line of that level is traced, these cells take the value outward,
   else the value inward, see displaceMatrix(). */
struct extremes {
    int used[2];           /* 1 if the value is such a level, else 0 */
    DCELL value[2];        /* the value, which is the level */
    DCELL inward[2];       /* the cells while other levels are traced */
    DCELL outward[2];      /* the cells while this level is traced */
    unsigned char **cells; /* bit 1 << k marks a cell of value k, NULL if
                              no value is used */
};

/* cont.c */
void contour(double *, int, struct Map_info, DCELL **, struct Cell_head, int,
             const struct extremes *);
int checkedge(DCELL, DCELL, double);

/* main.c */
DCELL **get_z_array(int, int, int);
double *getlevels(struct Option *, struct Option *, struct Option *,
                  struct Option *, struct FPRange *, int *);
void displaceMatrix(DCELL **, int, int, double *, int, struct extremes *);

#endif /* __LOCAL_PROTO_H__ */
