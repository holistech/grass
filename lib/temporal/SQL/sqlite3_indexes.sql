--#############################################################################
-- This SQL script generates the sqlite3 indexes
--
-- Author: Soeren Gebbert soerengebbert <at> googlemail <dot> com
--#############################################################################

-- SQLite indexes every primary key itself, so only indexes on more columns
-- than the key are created here. Older databases also have an index on id
-- alone for most tables; they keep it.

-- Indexes for raster, vector and 3D raster maps

CREATE INDEX raster_relative_time_index ON raster_relative_time (id, start_time, end_time);
CREATE INDEX raster_absolute_time_index ON raster_absolute_time (id, start_time, end_time);
CREATE INDEX raster_spatial_extent_index_bbox ON raster_spatial_extent (id, north, south, east, west);

CREATE INDEX raster3d_relative_time_index ON raster3d_relative_time (id, start_time, end_time);
CREATE INDEX raster3d_absolute_time_index ON raster3d_absolute_time (id, start_time, end_time);
CREATE INDEX raster3d_spatial_extent_index_bbox ON raster3d_spatial_extent (id, north, south, east, west, top, bottom);

CREATE INDEX vector_relative_time_index ON vector_relative_time (id, start_time, end_time);
CREATE INDEX vector_absolute_time_index ON vector_absolute_time (id, start_time, end_time);
CREATE INDEX vector_spatial_extent_index_bbox ON vector_spatial_extent (id, north, south, east, west, top, bottom);

CREATE INDEX raster_metadata_index_semantic_label ON raster_metadata (id, semantic_label);
