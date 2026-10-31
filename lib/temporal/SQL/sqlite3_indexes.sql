-- Create the indexes of the temporal database on SQLite
--
-- SPDX-FileCopyrightText: 2013-2026 GRASS Development Team
-- SPDX-License-Identifier: GPL-2.0-or-later
--
-- Author: Soeren Gebbert

-- SQLite indexes every primary key itself, so only indexes on more columns
-- than the key are created here. Older databases also have an index on id
-- alone for most tables; they keep it.
--
-- The time indexes start with the id: they cover the join of a time table with
-- the other tables of a map on the id, they do not serve a condition on the time
-- alone, which scans the table (checked 31.10.2026 with EXPLAIN QUERY PLAN on
-- raster_absolute_time). PostgreSQL indexes (start_time, end_time) without
-- the id.

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
