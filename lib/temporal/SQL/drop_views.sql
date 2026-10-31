-- Drop all views of the temporal database so that they can be created anew
--
-- SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
-- SPDX-License-Identifier: GPL-2.0-or-later
--
-- Author: Martin Landa

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
