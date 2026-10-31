/*!
   \file lib/temporal/lib/connect.c

   \brief Temporal GIS Library - connect to TGIS DB

   SPDX-FileCopyrightText: 2012 GRASS Development Team
   SPDX-License-Identifier: GPL-2.0-or-later

   \author Soeren Gebbert
   Code is based on the dbmi library written by
   Joel Jones (CERL/UIUC) and Radim Blazek
 */

#include <stdio.h>
#include <string.h>

#include <grass/temporal.h>
#include <grass/glocale.h>

/*!
 * \brief Get TGIS driver name
 *
 * \return pointer to TGIS driver name
 * \return NULL if not set
 */
char *tgis_get_driver_name(void)
{
    const char *drv;

    if ((drv = G_getenv_nofatal2("TGISDB_DRIVER", G_VAR_MAPSET)))
        return G_store(drv);

    return NULL;
}

/*!
 * \brief Get TGIS database name
 *
 * \return pointer to TGIS database name
 * \return NULL if not set
 */
char *tgis_get_database_name(void)
{
    const char *drv;

    if ((drv = G_getenv_nofatal2("TGISDB_DATABASE", G_VAR_MAPSET)))
        return G_store(drv);

    return NULL;
}

/*!
   \brief Set Temporal GIS DB connection settings

   This function sets environmental variables as TGISDB_DRIVER, TGISDB_DATABASE.

   \param connection pointer to dbConnection with default settings

   \return DB_OK
 */
int tgis_set_connection(dbConnection *connection)
{
    if (connection->driverName)
        G_setenv2("TGISDB_DRIVER", connection->driverName, G_VAR_MAPSET);

    if (connection->databaseName)
        G_setenv2("TGISDB_DATABASE", connection->databaseName, G_VAR_MAPSET);

    return DB_OK;
}

/*!
   \brief Get Temporal GIS DB connection settings

   \param[out] connection pointer to dbConnection to be modified

   \return DB_OK
 */
int tgis_get_connection(dbConnection *connection)
{
    G_zero(connection, sizeof(dbConnection));

    connection->driverName =
        (char *)G_getenv_nofatal2("TGISDB_DRIVER", G_VAR_MAPSET);
    connection->databaseName =
        (char *)G_getenv_nofatal2("TGISDB_DATABASE", G_VAR_MAPSET);

    return DB_OK;
}

#define DRIVER_NAME   0
#define DATABASE_NAME 1

/* Reads one variable from the VAR file of a mapset with the rules of the file
 * reader in libgis: the text before the first colon is the name, a line with
 * an empty name or value is skipped, and the last line of a name wins.
 *
 * The reader of libgis is not used because the only way to point it at
 * another mapset is G_create_alt_env(), and an environment made that way can
 * never be freed. That lost about 1.2 kB per call (growth of 48,444 kB over
 * 40,000 calls, measured 31.10.2026 with a C program reading /proc/self/statm
 * around the calls). */
static char *read_mapset_variable(const char *gisdbase, const char *location,
                                  const char *mapset, const char *name)
{
    /* As in libgis, a line may be as long as a path. */
    char buf[GPATH_MAX + 16];
    char path[GPATH_MAX];
    char *found = NULL;
    FILE *fd;

    snprintf(path, sizeof(path), "%s/%s/%s/VAR", gisdbase, location, mapset);
    if (!(fd = fopen(path, "r")))
        return NULL;

    while (G_getl2(buf, sizeof buf, fd)) {
        char *key = buf;
        char *value = strchr(buf, ':');

        if (!value)
            continue;

        *value++ = '\0';
        G_strip(key);
        G_strip(value);
        if (*key && *value && strcmp(key, name) == 0) {
            G_free(found);
            found = G_store(value);
        }
    }
    fclose(fd);

    return found;
}

static char *get_mapset_connection_name(const char *mapset, int contype)
{
    const char *gisdbase = G_getenv_nofatal("GISDBASE");
    const char *location = G_getenv_nofatal("LOCATION_NAME");
    const char *name;

    G_debug(1, "Checking mapset <%s>", mapset);
    /* The name is joined to a path, so a name with path parts would reach
     * a directory outside the project. */
    if (!*mapset || strchr(mapset, '/') || strcmp(mapset, ".") == 0 ||
        strcmp(mapset, "..") == 0) {
        G_warning(_("Mapset <%s> does not exist."), mapset);
        return NULL;
    }
    /* Only a missing mapset is refused. G_mapset_permissions2() returns 0 for
     * a mapset of another owner, but it does not check the access privileges
     * of a different user properly, so a warning would be misleading. Reading
     * fails by itself if it is not allowed. */
    if (G_mapset_permissions2(gisdbase, location, mapset) == -1) {
        G_warning(_("Mapset <%s> does not exist."), mapset);
        return NULL;
    }

    name = contype == DATABASE_NAME ? "TGISDB_DATABASE" : "TGISDB_DRIVER";

    return read_mapset_variable(gisdbase, location, mapset, name);
}

/*!
 * \brief Get TGIS driver name from a specific mapset
 *
 * This function give a warning in case the mapset does not exists
 * or it is not allowed to access the mapset. NULL is returned in this case.
 *
 * \param mapset The name of the mapset to receive the driver name from
 *
 * \return pointer to TGIS driver name
 * \return NULL if not set
 */
char *tgis_get_mapset_driver_name(const char *mapset)
{
    return get_mapset_connection_name(mapset, DRIVER_NAME);
}

/*!
 * \brief Get TGIS database name
 *
 * This function give a warning in case the mapset does not exists
 * or it is not allowed to access the mapset. NULL is returned in this case..
 *
 * \param mapset The name of the mapset to receive the driver name from

 * \return pointer to TGIS database name
 * \return NULL if not set
 */
char *tgis_get_mapset_database_name(const char *mapset)
{
    return get_mapset_connection_name(mapset, DATABASE_NAME);
}
