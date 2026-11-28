#include <grass/raster.h>
#include "raster3d_intern.h"

/*---------------------------------------------------------------------------*/

/* The value of the cell (x, y, z) of the map as the file holds it, without
 * the mask; the NULL-value outside the region of the map. */
static double double_region_value(RASTER3D_Map *map, int x, int y, int z);

static float float_region_value(RASTER3D_Map *map, int x, int y, int z)
{
    int tileIndex, offs;
    float *tile;
    float value;

    if (map->typeIntern == DCELL_TYPE)
        return (float)double_region_value(map, x, y, z);

    /* In case of region coordinates out of bounds, return the Null value */
    if (x < 0 || y < 0 || z < 0 || x >= map->region.cols ||
        y >= map->region.rows || z >= map->region.depths) {
        Rast3d_set_null_value(&value, 1, FCELL_TYPE);
        return value;
    }

    Rast3d_coord2tile_index(map, x, y, z, &tileIndex, &offs);
    tile = (float *)Rast3d_get_tile_ptr(map, tileIndex);

    if (tile == NULL)
        Rast3d_fatal_error(
            "Rast3d_get_float_region: error in Rast3d_get_tile_ptr."
            "Region coordinates x %i y %i z %i  tile index %i offset %i",
            x, y, z, tileIndex, offs);

    return tile[offs];
}

static double double_region_value(RASTER3D_Map *map, int x, int y, int z)
{
    int tileIndex, offs;
    double *tile;
    double value;

    if (map->typeIntern == FCELL_TYPE)
        return (double)float_region_value(map, x, y, z);

    /* In case of region coordinates out of bounds, return the Null value */
    if (x < 0 || y < 0 || z < 0 || x >= map->region.cols ||
        y >= map->region.rows || z >= map->region.depths) {
        Rast3d_set_null_value(&value, 1, DCELL_TYPE);
        return value;
    }

    Rast3d_coord2tile_index(map, x, y, z, &tileIndex, &offs);
    tile = (double *)Rast3d_get_tile_ptr(map, tileIndex);

    if (tile == NULL)
        Rast3d_fatal_error(
            "Rast3d_get_double_region: error in Rast3d_get_tile_ptr."
            "Region coordinates x %i y %i z %i  tile index %i offset %i",
            x, y, z, tileIndex, offs);

    return tile[offs];
}

static void value_region(RASTER3D_Map *map, int x, int y, int z, void *value,
                         int type)
{
    if (type == FCELL_TYPE) {
        *((float *)value) = float_region_value(map, x, y, z);
        return;
    }

    *((double *)value) = double_region_value(map, x, y, z);
}

/*---------------------------------------------------------------------------*/

/*!
 * \brief
 *
 * Returns in <em>*value</em> the resampled cell-value of the cell with
 * window-coordinate <em>(x, y, z)</em>.  The value returned is of
 * <em>type</em>. This function invokes a fatal error if an error occurs.
 * If the mask is turned on for <em>map</em>, the value is the NULL-value
 * where the 3d-mask is NULL at the centre of the cell of the window.
 *
 *  \param map
 *  \param x
 *  \param y
 *  \param z
 *  \param value
 *  \param type
 *  \return void
 */
void Rast3d_get_value(RASTER3D_Map *map, int x, int y, int z, void *value,
                      int type)
{
    if (!Rast3d_mask_applies_to(map)) {
        map->resampleFun(map, x, y, z, value, type);
        return;
    }

    /* The resampling function reads the values of the cells of the map, and
     * these would be masked at the centres of the cells of the map. With the
     * mask on another grid than the map, that hides or shows a cell of the
     * window by the mask somewhere else in the same cell of the map
     * (measured 05.11.2026 with a mask null in the lower half of the upper
     * of two layers and tbres=0.5: r3.out.ascii -m masked no cell,
     * r3.univar one).
     * So the resampling reads without the mask, whatever function it is,
     * and the mask applies at the cell of the window. */
    map->useMask = 0;
    map->resampleFun(map, x, y, z, value, type);
    map->useMask = 1;

    if (Rast3d_is_masked(map, x, y, z))
        Rast3d_set_null_value(value, 1, type);
}

/*---------------------------------------------------------------------------*/

/*!
 * \brief
 *
 * Is equivalent to
 * <tt>Rast3d_get_value (map, x, y, z, &value, FCELL_TYPE);</tt> return value.
 *
 *  \param map
 *  \param x
 *  \param y
 *  \param z
 *  \return float
 */
float Rast3d_get_float(RASTER3D_Map *map, int x, int y, int z)
{
    float value;

    Rast3d_get_value(map, x, y, z, &value, FCELL_TYPE);
    return value;
}

/*---------------------------------------------------------------------------*/

/*!
 * \brief
 *
 * Is equivalent
 * to <tt>Rast3d_get_value (map, x, y, z, &value, DCELL_TYPE);</tt> return
 * value.
 *
 *  \param map
 *  \param x
 *  \param y
 *  \param z
 *  \return double
 */
double Rast3d_get_double(RASTER3D_Map *map, int x, int y, int z)
{
    double value;

    Rast3d_get_value(map, x, y, z, &value, DCELL_TYPE);
    return value;
}

/*---------------------------------------------------------------------------*/

/*!
 * \brief
 *
 * Returns in <em>value</em> the value of the <em>map</em> which corresponds to
 * window coordinates <em>(north, east, top)</em>.  The
 * value is resampled using the resampling function specified for <em>map</em>.
 * The <em>value</em> is of <em>type</em>. If the mask is turned on for
 * <em>map</em>, the value is masked as Rast3d_get_value() masks the cell of
 * the window that holds the location.
 *
 *  \param map
 *  \param north
 *  \param east
 *  \param top
 *  \param value
 *  \param type
 *  \return void
 */
void Rast3d_get_window_value(RASTER3D_Map *map, double north, double east,
                             double top, void *value, int type)
{
    int col, row, depth;

    Rast3d_location2coord(&(map->window), north, east, top, &col, &row, &depth);

    /* if (row, col, depth) outside window return NULL value */
    if ((row < 0) || (row >= map->window.rows) || (col < 0) ||
        (col >= map->window.cols) || (depth < 0) ||
        (depth >= map->window.depths)) {
        Rast3d_set_null_value(value, 1, type);
        return;
    }

    Rast3d_get_value(map, col, row, depth, value, type);
}

/*---------------------------------------------------------------------------*/

/*!
 * \brief
 *
 * Returns in <em>value</em> the value of the <em>map</em> which corresponds to
 * region coordinates <em>(north, east, top)</em>. If the mask is turned on
 * for <em>map</em>, the value is the NULL-value where the 3d-mask is NULL at
 * the location <em>(north, east, top)</em>.
 *
 *  \param map
 *  \param north
 *  \param east
 *  \param top
 *  \param value
 *  \param type
 *  \return void
 */
void Rast3d_get_region_value(RASTER3D_Map *map, double north, double east,
                             double top, void *value, int type)
{
    int row, col, depth;

    Rast3d_location2coord(&(map->region), north, east, top, &col, &row, &depth);

    /* if (row, col, depth) outside region return NULL value */
    if ((row < 0) || (row >= map->region.rows) || (col < 0) ||
        (col >= map->region.cols) || (depth < 0) ||
        (depth >= map->region.depths)) {
        Rast3d_set_null_value(value, 1, type);
        return;
    }

    /* Get the value from the map in map-region resolution */
    value_region(map, col, row, depth, value, type);

    /* The value is read at a location, so the mask applies there rather
     * than at the centre of the cell of the map: r3.cross.rast reads its
     * cross section this way at the cells of the current region. */
    if (Rast3d_mask_applies_to(map) &&
        Rast3d_mask_is_null_at_location(north, east, top))
        Rast3d_set_null_value(value, 1, type);
}

/*---------------------------------------------------------------------------*/

/*!
 * \brief
 *
 * Is equivalent to <tt>Rast3d_get_value_region (map, x, y, z, &value,
 * FCELL_TYPE);</tt> return value.
 *
 *  \param map
 *  \param x
 *  \param y
 *  \param z
 *  \return float
 */
float Rast3d_get_float_region(RASTER3D_Map *map, int x, int y, int z)
{
    float value = float_region_value(map, x, y, z);

    if (Rast3d_mask_applies_to(map) &&
        Rast3d_mask_is_null_at_cell(&map->region, x, y, z))
        Rast3d_set_null_value(&value, 1, FCELL_TYPE);
    return value;
}

/*---------------------------------------------------------------------------*/

/*!
 * \brief
 *
 * Is equivalent to <tt>Rast3d_get_value_region (map, x, y, z, &value,
 * DCELL_TYPE);</tt> return value.
 *
 *  \param map
 *  \param x
 *  \param y
 *  \param z
 *  \return double
 */
double Rast3d_get_double_region(RASTER3D_Map *map, int x, int y, int z)
{
    double value = double_region_value(map, x, y, z);

    if (Rast3d_mask_applies_to(map) &&
        Rast3d_mask_is_null_at_cell(&map->region, x, y, z))
        Rast3d_set_null_value(&value, 1, DCELL_TYPE);
    return value;
}

/*---------------------------------------------------------------------------*/

/*!
 * \brief
 *
 * Returns in <em>*value</em> the cell-value of the cell with
 * region-coordinate <em>(x, y, z)</em>.  The value returned is of
 * <em>type</em>. Here <em>region</em> means the coordinate in the cube of data
 * in the file, i.e. ignoring geographic coordinates. In case the region
 * coordinates are out of bounds, the Null value will be returned. This function
 * invokes a fatal error if an error occurs. If the mask is turned on for
 * <em>map</em>, the value is the NULL-value where the 3d-mask is NULL at the
 * centre of the cell of the map.
 *
 *  \param map
 *  \param x
 *  \param y
 *  \param z
 *  \param value
 *  \param type
 *  \return void
 */
void Rast3d_get_value_region(RASTER3D_Map *map, int x, int y, int z,
                             void *value, int type)
{
    if (type == FCELL_TYPE) {
        *((float *)value) = Rast3d_get_float_region(map, x, y, z);
        return;
    }

    *((double *)value) = Rast3d_get_double_region(map, x, y, z);
}
