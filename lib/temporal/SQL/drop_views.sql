--#############################################################################
-- This SQL script drops all existing vies (used by upgrade_temporal_database())
--
-- Author: Martin Landa landa.martin <at> gmail <dot> com
--#############################################################################

-- raster_views
DROP VIEW IF EXISTS raster_view_abs_time;
DROP VIEW IF EXISTS raster_view_rel_time;

-- raster3d_views
DROP VIEW IF EXISTS raster3d_view_abs_time;
DROP VIEW IF EXISTS raster3d_view_rel_time;

-- vector_views
DROP VIEW IF EXISTS vector_view_abs_time;
DROP VIEW IF EXISTS vector_view_rel_time;

-- strds_views
DROP VIEW IF EXISTS strds_view_abs_time;
DROP VIEW IF EXISTS strds_view_rel_time;

-- str3ds_views
DROP VIEW IF EXISTS str3ds_view_abs_time;
DROP VIEW IF EXISTS str3ds_view_rel_time;

-- stvds_views
DROP VIEW IF EXISTS stvds_view_abs_time;
DROP VIEW IF EXISTS stvds_view_rel_time;
