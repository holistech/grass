#include <stdio.h>
#include <grass/gis.h>
#include "raster3d_intern.h"

/*--------------------------------------------------------------------------*/

/* the standard g3d file format is used to store the mask values. a NULL-value
   is stored for values which are masked out and a "0." is stored for values
   which are not masked out. to improve compression, the precision is set to
   0 and RLE encoding is used.
 */

/*--------------------------------------------------------------------------*/

static int Rast3d_maskMapExistsVar = 0;
static RASTER3D_Map *Rast3d_maskMap;

/*--------------------------------------------------------------------------*/
static void dummy(void)
{
    return;
}

static float RASTER3D_MASKNUMmaskValue;

/* Call to dummy() to match void return type of Rast3d_set_null_value() */
#define RASTER3D_MASKNUM(map, Xmask, Ymask, Zmask, VALUEmask, TYPEmask)  \
                                                                         \
    (RASTER3D_MASKNUMmaskValue =                                         \
         Rast3d_getMaskFloat(map, Xmask, Ymask, Zmask),                  \
     ((Rast3d_is_null_value_num(&RASTER3D_MASKNUMmaskValue, FCELL_TYPE)) \
          ? Rast3d_set_null_value(VALUEmask, 1, TYPEmask)                \
          : dummy()))

/*--------------------------------------------------------------------------*/

int Rast3d_mask_close(void)
{
    /* No Idea if this is correct return value */
    if (!Rast3d_maskMapExistsVar)
        return 1;

    Rast3d_maskMapExistsVar = 0;

    if (!Rast3d_close(Rast3d_maskMap)) {
        Rast3d_error("Rast3d_mask_close: error closing mask");

        return 0;
    }

    return 1;
}

/*--------------------------------------------------------------------------*/

/*!
 * \brief
 *
 *  Returns 1 if the 3d mask file exists.
 *
 *  \return int
 */
int Rast3d_mask_file_exists(void)
{
    return G_find_file_misc(RASTER3D_DIRECTORY, RASTER3D_CELL_ELEMENT,
                            RASTER3D_MASK_MAP, G_mapset()) != NULL;
}

/*--------------------------------------------------------------------------*/

static int maskOpenOldCacheDefault = RASTER3D_USE_CACHE_DEFAULT;

int Rast3d_mask_open_old(void)
{
    RASTER3D_Region region;

    /* No Idea if this is correct return value */
    if (Rast3d_maskMapExistsVar)
        return 1;

    Rast3d_maskMapExistsVar = Rast3d_mask_file_exists();

    if (!Rast3d_maskMapExistsVar)
        return 1;

    if ((Rast3d_maskMap = Rast3d_open_cell_old(
             RASTER3D_MASK_MAP, G_mapset(), RASTER3D_DEFAULT_WINDOW, FCELL_TYPE,
             maskOpenOldCacheDefault)) == NULL) {
        Rast3d_error("Rast3d_mask_open_old: cannot open mask");

        return 0;
    }

    Rast3d_get_region_struct_map(Rast3d_maskMap, &region);
    Rast3d_set_window_map(Rast3d_maskMap, &region);

    return 1;
}

/*--------------------------------------------------------------------------*/

/* The value of the mask at the location (north, east, top). */
static float mask_value_at_location(double north, double east, double top)
{
    float value;

    Rast3d_get_region_value(Rast3d_maskMap, north, east, top, &value,
                            FCELL_TYPE);
    return value;
}

/* The value of the mask at the centre of the cell (x, y, z) of the grid that
 * cells describes. Used for the cells of the map: the value read there is
 * the value of that cell, and for a mask on the grid of the map its centre
 * lies inside the cell of the mask with the same number, never on a
 * border. */
static float mask_value_at_cell(const RASTER3D_Region *cells, int x, int y,
                                int z)
{
    double north, east, top;

    north = ((double)cells->rows - y - 0.5) / (double)cells->rows *
                (cells->north - cells->south) +
            cells->south;
    east =
        ((double)x + 0.5) / (double)cells->cols * (cells->east - cells->west) +
        cells->west;
    top = ((double)z + 0.5) / (double)cells->depths *
              (cells->top - cells->bottom) +
          cells->bottom;

    return mask_value_at_location(north, east, top);
}

/* The value of the mask at the centre of the cell (x, y, z) of the window of
 * map. The centre comes from Rast3d_coord2location(), the arithmetic with
 * which Rast3d_nearest_neighbor() finds the cell of the map whose value it
 * reads: on a border between two cells of the map, the formula of
 * mask_value_at_cell() could round to the other side, and a mask on the grid
 * of the map then hid a value by the mask of the neighbouring cell
 * (measured 2026-11-06 with cells of 0.1 and a region shifted by half a
 * cell: the cell of value 5 was hidden by the mask of the cell of 4). */
static float Rast3d_getMaskFloat(RASTER3D_Map *map, int x, int y, int z)
{
    double north, east, top;

    Rast3d_coord2location(&map->window, (double)x + 0.5, (double)y + 0.5,
                          (double)z + 0.5, &north, &east, &top);
    return mask_value_at_location(north, east, top);
}

/*--------------------------------------------------------------------------*/

/* Returns 1 if the read functions mask the values they read from map: the
 * mask is loaded and turned on for map, and map is open for reading. A map
 * open for writing keeps the former behaviour, in which only a tile read
 * back from its file is masked (Rast3d_read_tile()), because masking the
 * values a tool reads back from its own output would write the mask into
 * the output where the tool keeps an earlier value. */
int Rast3d_mask_applies_to(RASTER3D_Map *map)
{
    return Rast3d_maskMapExistsVar && map->useMask &&
           map->operation == RASTER3D_READ_DATA;
}

/* Returns 1 if the mask is null at the centre of the cell (x, y, z) of the
 * grid that cells describes. The mask has to be loaded. */
int Rast3d_mask_is_null_at_cell(const RASTER3D_Region *cells, int x, int y,
                                int z)
{
    float value = mask_value_at_cell(cells, x, y, z);

    return Rast3d_is_null_value_num(&value, FCELL_TYPE);
}

/* Returns 1 if the mask is null at the location (north, east, top). The
 * mask has to be loaded. */
int Rast3d_mask_is_null_at_location(double north, double east, double top)
{
    float value = mask_value_at_location(north, east, top);

    return Rast3d_is_null_value_num(&value, FCELL_TYPE);
}

/*--------------------------------------------------------------------------*/

/*!
 * \brief
 *
 *  This function should be used to adjust the cache size used for the
 * 3d-mask. First the open 3d-mask is closed and then opened again with
 * a cache size as specified with <em>cache</em>.
 *
 *  \param cache
 *  \return 1 ... if successful
 *          0 ... otherwise.
 */
int Rast3d_mask_reopen(int cache)
{
    int tmp;

    if (Rast3d_maskMapExistsVar)
        if (!Rast3d_mask_close()) {
            Rast3d_error("Rast3d_mask_reopen: error closing mask");

            return 0;
        }

    tmp = maskOpenOldCacheDefault;
    maskOpenOldCacheDefault = cache;

    if (!Rast3d_mask_open_old()) {
        Rast3d_error("Rast3d_mask_reopen: error opening mask");

        return 0;
    }

    maskOpenOldCacheDefault = tmp;
    return 1;
}

/*--------------------------------------------------------------------------*/

/*!
 * \brief
 *
 *  Returns 1 if the cell with cell-coordinates <em>(x, y, z)</em> of the
 *  current window of <em>map</em> is masked out, that is if the 3d-mask is
 *  NULL at the centre of that cell, computed as Rast3d_nearest_neighbor()
 *  computes it, so that the mask and the value come from the same location.
 *  Returns 0 otherwise. This is the rule that Rast3d_get_value() applies for
 *  a map with the mask turned on.
 *
 *  \param x
 *  \param y
 *  \param z
 *  \return int
 */
int Rast3d_is_masked(RASTER3D_Map *map, int x, int y, int z)
{
    if (!Rast3d_maskMapExistsVar)
        return 0;

    RASTER3D_MASKNUMmaskValue = Rast3d_getMaskFloat(map, x, y, z);
    return (Rast3d_is_null_value_num(&RASTER3D_MASKNUMmaskValue, FCELL_TYPE));
}

/*--------------------------------------------------------------------------*/

/*!
 * \brief
 *
 * Replaces the value stored in <em>value</em> with the NULL-value if
 * <em>Rast3d_is_masked (x, y, z)</em> returns 1. Does nothing otherwise.
 * <em>value</em> is assumed to be of<em>type</em>.
 *
 *  \param map
 *  \param x
 *  \param y
 *  \param z
 *  \param value
 *  \param type
 *  \return void
 */
void Rast3d_mask_num(RASTER3D_Map *map, int x, int y, int z, void *value,
                     int type)
{
    if (!Rast3d_maskMapExistsVar)
        return;
    RASTER3D_MASKNUM(map, x, y, z, value, type);
}

/*--------------------------------------------------------------------------*/

/*!
 * \brief
 *
 *  Same as <em>Rast3d_mask_num (x, y, z, value, FCELL_TYPE)</em>.
 *
 *  \param map
 *  \param x
 *  \param y
 *  \param z
 *  \param value
 *  \return void
 */
void Rast3d_mask_float(RASTER3D_Map *map, int x, int y, int z, float *value)
{
    if (!Rast3d_maskMapExistsVar)
        return;
    RASTER3D_MASKNUM(map, x, y, z, value, FCELL_TYPE);
}

/*--------------------------------------------------------------------------*/

/*!
 * \brief
 *
 * Same as <em>Rast3d_mask_num (x, y, z, value, DCELL_TYPE)</em>.
 *
 *  \param map
 *  \param x
 *  \param y
 *  \param z
 *  \param value
 *  \return void
 */
void Rast3d_mask_double(RASTER3D_Map *map, int x, int y, int z, double *value)
{
    if (!Rast3d_maskMapExistsVar)
        return;
    RASTER3D_MASKNUM(map, x, y, z, value, DCELL_TYPE);
}

/*--------------------------------------------------------------------------*/

/*!
 * \brief
 *
 *  Replaces the values stored in <em>tile</em> (with <em>tileIndex</em>) with
 *  NULL-values where the 3d-mask is NULL at the centre of the cell in the
 *  region of <em>map</em>, whatever the current window. Does not change
 *  the remaining values. The values are assumed to be of <em>type</em>.
 *  Whether replacement is performed or not only depends on location of the
 *  cells of the tile and not on the status of the mask for <em>map</em>
 *  (i.e. turned on or off).
 *
 *  Rast3d_read_tile() calls it for a map with the mask turned on. The tiles
 *  that a map open for reading keeps in its cache are not masked: the read
 *  functions apply the mask to each value they read (see Rast3d_mask_on()).
 *
 *  \param map
 *  \param tileIndex
 *  \param tile
 *  \param type
 *  \return void
 */
void Rast3d_mask_tile(RASTER3D_Map *map, int tileIndex, void *tile, int type)
{
    int nofNum, rows, cols, depths, xRedundant, yRedundant, zRedundant;
    int x, y, z, xLength, yLength, dx, dy, dz, length;
    float maskValue;

    if (!Rast3d_maskMapExistsVar)
        return;

    nofNum = Rast3d_compute_clipped_tile_dimensions(map, tileIndex, &rows,
                                                    &cols, &depths, &xRedundant,
                                                    &yRedundant, &zRedundant);
    Rast3d_tile_index_origin(map, tileIndex, &x, &y, &z);

    if (nofNum == map->tileSize) {
        /*AV*/
        /* BEGIN OF ORIGINAL CODE */
        /*
         *    Rast3d_get_tile_dimensions_map (map, &rows, &cols, &depths);
         */
        /*AV*/
        /* BEGIN OF MY CODE */
        Rast3d_get_tile_dimensions_map(map, &cols, &rows, &depths);
        /* END OF MY CODE */
        xRedundant = yRedundant = 0;
    }

    rows += y;
    cols += x;
    depths += z;
    length = Rast3d_length(type);
    xLength = xRedundant * length;
    yLength = map->tileX * yRedundant * length;

    /* The cells of a tile are cells of the map, not of the current window,
     * so their location comes from the region of the map. With the window
     * the mask was looked up at other locations whenever the window
     * differed from the map (measured 04.11.2026 with r3.out.ascii -m: a
     * mask of the upper of two layers hid nothing with tbres=0.5). */
    for (dz = z; dz < depths; dz++) {
        for (dy = y; dy < rows; dy++) {
            for (dx = x; dx < cols; dx++) {
                maskValue = mask_value_at_cell(&map->region, dx, dy, dz);
                if (Rast3d_is_null_value_num(&maskValue, FCELL_TYPE))
                    Rast3d_set_null_value(tile, 1, type);
                tile = (char *)tile + length;
            }

            tile = (char *)tile + xLength;
        }
        tile = (char *)tile + yLength;
    }
}

/*--------------------------------------------------------------------------*/

/*!
 * \brief
 *
 *  Turns on the mask for <em>map</em>.
 *
 *  For a map open for reading, the read functions then replace a value with
 *  the NULL-value where the 3d-mask is NULL at the location of the value
 *  read: Rast3d_get_value() and the functions based on it at the centre of
 *  the cell of the current window, Rast3d_get_window_value() at the centre of
 *  the cell of the current window that holds the location,
 *  Rast3d_get_region_value() at the location itself, and
 *  Rast3d_get_value_region(), Rast3d_get_float_region(),
 *  Rast3d_get_double_region() and Rast3d_get_block() at the centre of the
 *  cell of the map. Rast3d_read_tile() masks the tile at the centres of the
 *  cells of the map. The mask can be turned on and off at any time.
 *
 *  For a map open for writing, only a tile read back from the file is
 *  masked, at the centres of the cells of the map. Do not invoke this
 *  function after the first tile has been read since the result might be
 *  inconsistent cell-values.
 *
 *  \param map
 *  \return void
 */
void Rast3d_mask_on(RASTER3D_Map *map)
{
    map->useMask = 1;
}

/*!
 * \brief
 *
 *  Turns off the mask for <em>map</em>.
 * This is the default. For a map open for writing, do not invoke this
 * function after the first tile has been read since the result might be
 * inconsistent cell-values (see Rast3d_mask_on()).
 *
 *  \param map
 *  \return void
 */
void Rast3d_mask_off(RASTER3D_Map *map)
{
    map->useMask = 0;
}

/*!
 * \brief
 *
 *  Returns 1 if the mask for <em>map</em>
 * is turned on. Returns 0 otherwise.
 *
 *  \param map
 *  \return int
 */
int Rast3d_mask_is_on(RASTER3D_Map *map)
{
    return map->useMask;
}

/*!
 * \brief
 *
 * Returns 1 if the mask for <em>map</em> is turned off. Returns 0 otherwise.
 *
 *  \param map
 *  \return int
 */
int Rast3d_mask_is_off(RASTER3D_Map *map)
{
    return !map->useMask;
}

/*!
 * \brief
 *
 * Returns the name of the 3d mask file.
 *
 *  \return char *
 */
const char *Rast3d_mask_file(void)
{
    return RASTER3D_MASK_MAP;
}

/*!
 * \brief
 *
 * Returns 1 if the 3d mask is loaded.
 *
 *  \return int
 */
int Rast3d_mask_map_exists(void)
{
    return Rast3d_maskMapExistsVar;
}
