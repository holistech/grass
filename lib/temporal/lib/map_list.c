/*!
   \file lib/temporal/lib/map_list.c

   \brief Temporal GIS Library - list of time stamped maps

   SPDX-FileCopyrightText: 2001 GRASS Development Team
   SPDX-License-Identifier: GPL-2.0-or-later

   Derived from the integer list functions of the GIS library
   (lib/gis/list.c, original author CERL, update to GRASS 5.7 by
   Radim Blazek).
 */

#include <stdlib.h>

#include <grass/gis.h>
#include <grass/temporal.h>

/*!
 * \brief Free a tgisMapList and all maps in it
 *
 * Frees the name and the mapset of every map, the map itself, the array and
 * the list. The maps must have been allocated with the G_malloc() family and
 * their names with G_store(), as tgis_map_list_insert() does, because a map
 * on the stack or with a string literal as name cannot be freed.
 *
 * \param list The pointer to a list from tgis_new_map_list(); not used
 *        afterwards
 */
void tgis_free_map_list(tgisMapList *list)
{
    if (list->values) {
        int i;

        for (i = 0; i < list->n_values; i++) {
            if (list->values[i]->name)
                G_free(list->values[i]->name);
            if (list->values[i]->mapset)
                G_free(list->values[i]->mapset);
            G_free(list->values[i]);
        }
        G_free(list->values);
    }
    G_free(list);
}

/*!
 * \brief Return a new, empty tgisMapList
 *
 * If the allocation fails, G_fatal_error() will be invoked by the allocation
 * function.
 *
 * \return The pointer to a new allocated list, to be freed with
 *         tgis_free_map_list()
 */
tgisMapList *tgis_new_map_list(void)
{
    tgisMapList *list = G_malloc(sizeof(tgisMapList));

    list->values = NULL;
    tgis_init_map_list(list);
    return list;
}

/*!
 * \brief Empty a tgisMapList and free the maps in it
 *
 * Frees the maps as tgis_free_map_list() does, but keeps the list itself, so
 * it can be filled again.
 *
 * The list must be initialized: a structure that is not zeroed has
 * garbage in \c values and this function would free it.
 *
 * \param list The pointer to an initialized tgisMapList
 */
void tgis_init_map_list(tgisMapList *list)
{
    if (list->values) {
        int i;

        for (i = 0; i < list->n_values; i++) {
            if (list->values[i]->name)
                G_free(list->values[i]->name);
            if (list->values[i]->mapset)
                G_free(list->values[i]->mapset);
            G_free(list->values[i]);
        }
        G_free(list->values);
    }

    list->values = NULL;
    list->n_values = 0;
    list->alloc_values = 0;
}

/*!
 * \brief Add a map to tgisMapList
 *
 * This function adds a tgisMap to the list but does not check for duplicates.
 * In case reallocation fails, G_fatal_error() will be invoked by the
 * allocation function.
 *
 * The content of the map will not be copied, the pointer to the map is
 * stored and the list owns the map from now on: tgis_free_map_list() frees
 * it with G_free(), so it must come from the G_malloc() family and its name
 * and mapset from G_store().
 *
 * \param list The tgisMapList pointer
 * \param map A pointer to a tgisMap struct that should be added
 */
void tgis_map_list_add(tgisMapList *list, tgisMap *map)
{
    if (list->n_values == list->alloc_values) {
        size_t size = (list->n_values + 1000) * sizeof(tgisMap *);
        void *p = G_realloc((void *)list->values, size);

        list->values = (tgisMap **)p;
        list->alloc_values = list->n_values + 1000;
    }

    list->values[list->n_values] = map;
    list->n_values++;
}

/*!
 * \brief Insert map information into tgisMapList
 *
 * This function allocates a tgisMap, fills it with the provided information
 * and adds it to the list.
 * In case allocation fails, G_fatal_error() will be invoked by the
 * allocation function.
 *
 * All arguments are deep copied to the new allocated tgisMap struct.
 *
 * \param list The tgisMapList pointer
 * \param name The name of the map
 * \param mapset The name of the mapset
 * \param ts A pointer to the timestamp of the map; a timestamp with neither
 *        one nor two values leaves the time stamp of the map empty
 */
void tgis_map_list_insert(tgisMapList *list, const char *name,
                          const char *mapset, const struct TimeStamp *ts)
{
    tgisMap *map = G_calloc(1, sizeof(tgisMap));

    map->name = G_store(name);
    map->mapset = G_store(mapset);

    if (ts->count == 1)
        G_set_timestamp(&(map->ts), &(ts->dt[0]));
    if (ts->count == 2)
        G_set_timestamp_range(&(map->ts), &(ts->dt[0]), &(ts->dt[1]));

    tgis_map_list_add(list, map);
}
