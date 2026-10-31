#ifndef GRASS_TEMPORAL_H
#define GRASS_TEMPORAL_H

#include <grass/datetime.h>
#include <grass/gis.h>
#include <grass/dbmi.h>

#define TGISDB_DEFAULT_DRIVER      "sqlite"
/* Default path in the current location */
#define TGISDB_DEFAULT_SQLITE_PATH "tgis/sqlite.db"

int tgis_set_connection(dbConnection *connection);
int tgis_get_connection(dbConnection *connection);
const char *tgis_get_default_driver_name(void);
char *tgis_get_default_database_name(void);
char *tgis_get_driver_name(void);
char *tgis_get_database_name(void);
char *tgis_get_mapset_driver_name(const char *);
char *tgis_get_mapset_database_name(const char *);
int tgis_set_default_connection(void);

/*! A simple structure to organize time stamped maps */
typedef struct _tgisMap {
    char *name;
    char *mapset;
    struct TimeStamp ts;
} tgisMap;

/*!
   \brief List of tgisMap struct's

   This structure is used to store lists of time stamped maps
   using the tgisMap structure internally.
 */
typedef struct _tgisMapList {
    /*!
       \brief Array of tgisMap struct's
     */
    tgisMap **values;
    /*!
       \brief Number of tgisMap struct's in the list
     */
    int n_values;
    /*!
       \brief Allocated space for tgisMap struct's
     */
    int alloc_values;
} tgisMapList;

/* map_list.c */
void tgis_init_map_list(tgisMapList *list);
void tgis_free_map_list(tgisMapList *list);
tgisMapList *tgis_new_map_list(void);

/*! Insert a new map to the map list */
void tgis_map_list_insert(tgisMapList *list, char *name, char *mapset,
                          struct TimeStamp *ts);
/*! Add a new map to the map list */
void tgis_map_list_add(tgisMapList *list, tgisMap *map);

#endif
