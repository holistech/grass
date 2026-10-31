/*!
   \file lib/db/dbmi_base/default_name.c

   \brief Temporal GIS Library (base) - default settings

   SPDX-FileCopyrightText: 2012-2014 GRASS Development Team
   SPDX-License-Identifier: GPL-2.0-or-later

   \author Soeren Gebbert
   Code is based on the dbmi library written by
   Joel Jones (CERL/UIUC) and Radim Blazek
 */

#include <stdio.h>

#include <grass/gis.h>
#include <grass/temporal.h>

/*!
   \brief Get default TGIS driver name

   \return pointer to default TGIS driver name
 */
const char *tgis_get_default_driver_name(void)
{
    return TGISDB_DEFAULT_DRIVER;
}

/*!
   \brief Get default TGIS database name for the sqlite connection

   The default name is $GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db

   \return pointer to default TGIS database name
 */
char *tgis_get_default_database_name(void)
{
    char default_connection[2048];

    snprintf(default_connection, 2048, "$GISDBASE/$LOCATION_NAME/$MAPSET/%s",
             TGISDB_DEFAULT_SQLITE_PATH);

    return G_store(default_connection);
}

/*!
   \brief Sets up TGIS database connection settings using GRASS default

   \return returns DB_OK
 */
int tgis_set_default_connection(void)
{
    dbConnection connection = {0};
    char *db_name = tgis_get_default_database_name();

    connection.driverName = (char *)tgis_get_default_driver_name();
    connection.databaseName = db_name;
    tgis_set_connection(&connection);
    G_free(db_name);

    return DB_OK;
}
