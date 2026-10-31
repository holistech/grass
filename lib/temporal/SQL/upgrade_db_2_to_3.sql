--#############################################################################
-- This SQL script upgrades TGIS DB from version 2 to version 3.
--
-- Author: Martin Landa landa.martin <at> gmail <dot> com
--#############################################################################

-- raster_metadata_table.sql
ALTER TABLE raster_metadata
 ADD COLUMN semantic_label VARCHAR;

-- strds_metadata_table.sql
ALTER TABLE strds_metadata
 ADD COLUMN number_of_semantic_labels INTEGER;
-- Version 2 knows no semantic labels, so a dataset with maps has none. A new
-- database counts 0 when the first map is registered; empty datasets keep NULL.
UPDATE strds_metadata
  SET number_of_semantic_labels = 0
  WHERE number_of_maps > 0;

-- sqlite3_indexes.sql: the indexes that came after version 2 was released.
-- IF NOT EXISTS keeps the script safe for a database that already has them.
CREATE INDEX IF NOT EXISTS raster_spatial_extent_index_bbox
 ON raster_spatial_extent (id, north, south, east, west);
CREATE INDEX IF NOT EXISTS raster3d_spatial_extent_index_bbox
 ON raster3d_spatial_extent (id, north, south, east, west, top, bottom);
CREATE INDEX IF NOT EXISTS vector_spatial_extent_index_bbox
 ON vector_spatial_extent (id, north, south, east, west, top, bottom);
CREATE INDEX IF NOT EXISTS raster_metadata_index_semantic_label
 ON raster_metadata (id, semantic_label);

-- tgis_metadata
UPDATE tgis_metadata
  SET value = '3'
  WHERE key = 'tgis_db_version';
