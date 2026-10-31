--#############################################################################
-- This SQL script generates the postgresql indexes
--
-- Author: Soeren Gebbert soerengebbert <at> googlemail <dot> com
--#############################################################################

CREATE INDEX raster_relative_time_index ON raster_relative_time (start_time, end_time);
CREATE INDEX raster_absolute_time_index ON raster_absolute_time (start_time, end_time);

CREATE INDEX raster3d_relative_time_index ON raster3d_relative_time (start_time, end_time);
CREATE INDEX raster3d_absolute_time_index ON raster3d_absolute_time (start_time, end_time);

CREATE INDEX vector_relative_time_index ON vector_relative_time (start_time, end_time);
CREATE INDEX vector_absolute_time_index ON vector_absolute_time (start_time, end_time);

CREATE INDEX raster_spatial_extent_index_bbox ON raster_spatial_extent (id, north, south, east, west);
CREATE INDEX raster3d_spatial_extent_index_bbox ON raster3d_spatial_extent (id, north, south, east, west, top, bottom);
CREATE INDEX vector_spatial_extent_index_bbox ON vector_spatial_extent (id, north, south, east, west, top, bottom);

CREATE INDEX raster_metadata_index_semantic_label ON raster_metadata (id, semantic_label);
